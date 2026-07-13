"""Agent, citation, determinism and audit tests for the Stockout agent."""

from __future__ import annotations

import json
from datetime import date

import pytest

from scripts.stockout_agent import (
    ALLOWLISTED_TOOLS,
    AgentContext,
    InvestigationRequest,
    StockoutInvestigationAgent,
)
from scripts.stockout_agent.gateway import InMemoryAuditSink, InMemoryDraftSink
from scripts.stockout_agent.orchestrator import INVESTIGATION_PLAN
from scripts.stockout_agent.tools import ToolError

AS_OF = date(2026, 2, 2)
FIXED_CLOCK = "2026-02-02T00:00:00+00:00"


def _request(question: str = "Why did stockouts increase?", category: str = "pain relief"):
    return InvestigationRequest(
        question=question, region="Melbourne", category=category,
        window_days=14, as_of_date=AS_OF,
    )


def _analyst() -> AgentContext:
    return AgentContext(user="analyst1", role="PHARMARETAIL_SUPPLY_CHAIN_ANALYST")


def _agent(sink: InMemoryAuditSink | None = None) -> StockoutInvestigationAgent:
    return StockoutInvestigationAgent(
        audit_sink=sink or InMemoryAuditSink(), clock=lambda: FIXED_CLOCK
    )


def test_allowlist_has_exactly_seven_named_tools() -> None:
    assert ALLOWLISTED_TOOLS == (
        "get_stockout_metrics",
        "get_inventory_position",
        "get_supplier_performance",
        "get_promotion_impact",
        "search_policy_docs",
        "draft_action_plan",
        "log_ai_interaction",
    )
    assert len(ALLOWLISTED_TOOLS) == 7


def test_plan_only_references_allowlisted_tools() -> None:
    assert set(INVESTIGATION_PLAN).issubset(set(ALLOWLISTED_TOOLS))


def test_full_investigation_returns_cited_findings_and_drafts() -> None:
    result = _agent().investigate(_request(), _analyst())
    codes = {finding.code for finding in result.findings}
    assert not result.refused
    assert {
        "STOCKOUT_SPIKE",
        "SUPPLIER_OTIF_DECLINE",
        "PROMO_UNDERFORECAST",
        "LOW_DAYS_OF_COVER",
        "POLICY_GUIDANCE",
    }.issubset(codes)
    assert len(result.recommended_actions) == 2
    assert result.human_approval_required is True


def test_result_is_json_serialisable() -> None:
    result = _agent().investigate(_request(), _analyst())
    encoded = json.dumps(result.to_dict())
    assert '"citation_coverage": 1.0' in encoded


def test_citation_coverage_is_full_and_every_finding_is_cited() -> None:
    result = _agent().investigate(_request(), _analyst())
    assert result.citation_coverage() == 1.0
    assert all(finding.citations for finding in result.findings)


def test_data_findings_cite_governed_marts() -> None:
    result = _agent().investigate(_request(), _analyst())
    data_findings = [f for f in result.findings if f.code != "POLICY_GUIDANCE"]
    for finding in data_findings:
        assert finding.citations
        assert all(
            citation.kind == "DATA" and citation.reference.startswith("PHARMARETAIL.MARTS.")
            for citation in finding.citations
        )


def test_recommended_actions_carry_policy_citation() -> None:
    result = _agent().investigate(_request(), _analyst())
    for action in result.recommended_actions:
        kinds = {citation.kind for citation in action.citations}
        assert "POLICY" in kinds


def test_toolset_rejects_non_allowlisted_tool() -> None:
    agent = _agent()
    assert agent.toolset.is_allowlisted("get_stockout_metrics")
    assert not agent.toolset.is_allowlisted("run_sql")
    with pytest.raises(ToolError):
        agent.toolset.resolve("run_sql")


def test_every_allowlisted_tool_is_resolvable() -> None:
    agent = _agent()
    for name in ALLOWLISTED_TOOLS:
        assert callable(agent.toolset.resolve(name))


def test_audit_log_records_every_step_and_is_append_only() -> None:
    sink = InMemoryAuditSink()
    _agent(sink).investigate(_request(), _analyst())
    # six tool steps + one completion record.
    assert len(sink.records) == 7
    audit_ids = [record.audit_id for record in sink.records]
    assert len(set(audit_ids)) == len(audit_ids)
    # The sink exposes no mutation or deletion API.
    assert not hasattr(sink, "update")
    assert not hasattr(sink, "delete")


def test_agent_only_drafts_and_never_takes_external_action() -> None:
    result = _agent().investigate(_request(), _analyst())
    for action in result.recommended_actions:
        assert action.requires_human_approval is True
        assert action.status == "DRAFT_PENDING_APPROVAL"
        assert action.target_system.endswith("DRAFT")


def test_investigation_is_deterministic_across_runs() -> None:
    first = _agent().investigate(_request(), _analyst()).to_dict()
    second = _agent().investigate(_request(), _analyst()).to_dict()
    assert first == second


def test_audit_ids_are_deterministic_across_runs() -> None:
    sink_a, sink_b = InMemoryAuditSink(), InMemoryAuditSink()
    _agent(sink_a).investigate(_request(), _analyst())
    _agent(sink_b).investigate(_request(), _analyst())
    assert [r.audit_id for r in sink_a.records] == [r.audit_id for r in sink_b.records]


def test_no_stockout_signal_returns_honest_empty_answer() -> None:
    # No fixture data exists for vitamins; the agent must not fabricate findings.
    result = _agent().investigate(_request(category="vitamins"), _analyst())
    assert not result.refused
    assert "No stockout signal" in result.summary
    assert result.recommended_actions == ()
    assert all(finding.code == "POLICY_GUIDANCE" for finding in result.findings)


def test_drafts_are_persisted_append_only_and_approval_pending() -> None:
    drafts = InMemoryDraftSink()
    agent = StockoutInvestigationAgent(
        audit_sink=InMemoryAuditSink(), draft_sink=drafts, clock=lambda: FIXED_CLOCK
    )
    result = agent.investigate(_request(), _analyst())
    # Every produced draft is persisted as a row.
    assert len(drafts.records) == len(result.recommended_actions) == 2
    assert all(record.requires_human_approval for record in drafts.records)
    assert all(record.status == "DRAFT_PENDING_APPROVAL" for record in drafts.records)
    # Deterministic, unique draft ids; no mutation/deletion API.
    ids = [record.draft_id for record in drafts.records]
    assert len(set(ids)) == len(ids)
    assert not hasattr(drafts, "update") and not hasattr(drafts, "delete")


def test_no_signal_persists_no_drafts() -> None:
    drafts = InMemoryDraftSink()
    agent = StockoutInvestigationAgent(
        audit_sink=InMemoryAuditSink(), draft_sink=drafts, clock=lambda: FIXED_CLOCK
    )
    agent.investigate(_request(category="vitamins"), _analyst())
    assert drafts.records == ()
