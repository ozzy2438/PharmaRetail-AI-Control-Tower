"""The controlled Stockout Investigation Agent orchestrator.

The plan is fixed and deterministic: the agent scans for prompt injection,
verifies the caller may investigate at all, then calls the seven allowlisted
tools in a constant order, assembles a fully-cited structured result, and
records every step to the append-only audit sink. It never runs free SQL,
never calls a tool outside the allowlist, and never takes an external action —
it only drafts, and every draft requires human approval.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timezone

from scripts.governed_rag import PROMPT_INJECTION_PATTERNS, GovernedRetriever
from scripts.stockout_agent.contracts import (
    ALLOWLISTED_TOOLS,
    ActionDraft,
    AgentContext,
    AuditRecord,
    Citation,
    Finding,
    InvestigationRequest,
    InvestigationResult,
    ToolInvocation,
)
from scripts.stockout_agent.gateway import (
    AuditSink,
    DataGateway,
    InMemoryAuditSink,
    InMemoryGateway,
)
from scripts.stockout_agent.tools import AllowlistToolset, ToolResult

# Fixed investigation plan. Every entry must be on the allowlist.
INVESTIGATION_PLAN: tuple[str, ...] = (
    "get_stockout_metrics",
    "get_inventory_position",
    "get_supplier_performance",
    "get_promotion_impact",
    "search_policy_docs",
    "draft_action_plan",
)
POLICY_QUERY = (
    "stockout replenishment supplier escalation days of cover OTIF threshold recommended action"
)


def _default_clock() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_injection(text: str) -> bool:
    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in PROMPT_INJECTION_PATTERNS
    )


class StockoutInvestigationAgent:
    def __init__(
        self,
        gateway: DataGateway | None = None,
        retriever: GovernedRetriever | None = None,
        audit_sink: AuditSink | None = None,
        clock: Callable[[], str] = _default_clock,
    ) -> None:
        self._gateway = gateway or InMemoryGateway()
        self._retriever = retriever or GovernedRetriever.from_corpus()
        self._audit_sink = audit_sink or InMemoryAuditSink()
        self._clock = clock
        self._toolset = AllowlistToolset(self._gateway, self._retriever, self._audit_sink)
        # Guard: the plan may never contain a non-allowlisted tool.
        for name in INVESTIGATION_PLAN:
            if name not in ALLOWLISTED_TOOLS:
                raise ValueError(f"Plan step '{name}' is not on the allowlist")

    @property
    def toolset(self) -> AllowlistToolset:
        return self._toolset

    @property
    def audit_sink(self) -> AuditSink:
        return self._audit_sink

    def investigate(
        self, request: InvestigationRequest, context: AgentContext
    ) -> InvestigationResult:
        trace: list[ToolInvocation] = []
        sequence = 0

        def audit(tool: str, action: str, obj: str, result: ToolResult) -> None:
            nonlocal sequence
            sequence += 1
            trace.append(
                ToolInvocation(
                    sequence=sequence,
                    tool_name=tool,
                    arguments=(
                        ("region", request.region),
                        ("category", request.category),
                        ("as_of_date", request.as_of_date.isoformat()),
                    ),
                    row_count=result.row_count,
                    outcome=result.outcome,
                )
            )
            self._toolset.log_ai_interaction(
                AuditRecord(
                    query_hash=request.query_hash,
                    sequence=sequence,
                    actor=context.user,
                    actor_role=context.role,
                    tool_name=tool,
                    action_name=action,
                    object_name=obj,
                    row_count=result.row_count,
                    outcome=result.outcome,
                    refused=result.outcome in {"REFUSED", "DENIED"},
                    refusal_reason=None if result.outcome == "OK" else result.outcome,
                    citation_count=len(result.citations),
                    event_timestamp=self._clock(),
                )
            )

        # 1. Prompt-injection guardrail, before any data access.
        if _is_injection(request.question):
            return self._refuse(request, context, "PROMPT_INJECTION", trace)

        # 2. Authorisation: can this caller run an investigation at all?
        if not context.can_investigate():
            return self._refuse(request, context, "ACCESS_DENIED", trace)

        # 3. Fixed tool plan.
        stockouts = self._toolset.get_stockout_metrics(context, request)
        audit("get_stockout_metrics", "READ", "FCT_STOCKOUT_EVENT", stockouts)
        inventory = self._toolset.get_inventory_position(context, request)
        audit("get_inventory_position", "READ", "FCT_INVENTORY_SNAPSHOT", inventory)
        supplier = self._toolset.get_supplier_performance(context, request)
        audit("get_supplier_performance", "READ", "FCT_SUPPLIER_DELIVERY", supplier)
        promotion = self._toolset.get_promotion_impact(context, request)
        audit("get_promotion_impact", "READ", "FCT_PROMOTION", promotion)
        policy = self._toolset.search_policy_docs(context, POLICY_QUERY, request.as_of_date)
        audit("search_policy_docs", "RETRIEVE", "GOVERNANCE.DOCUMENT_CHUNKS", policy)

        # No stockout signal within scope -> honest, non-fabricated empty answer.
        if stockouts.outcome != "OK":
            result = self._no_signal(request, context, trace, policy)
            self._final_audit(request, context, result, sequence)
            return result

        findings = self._build_findings(stockouts, inventory, supplier, promotion, policy)
        drivers = self._drivers(stockouts, inventory, supplier)
        supporting = self._supporting_citations(stockouts, supplier, policy)
        drafts_result = self._toolset.draft_action_plan(context, request, supporting, drivers)
        audit("draft_action_plan", "DRAFT", "AI_LOGS.AGENT_ACTION_DRAFT", drafts_result)

        citations = self._collect_citations(findings, drafts_result.drafts)
        uncertainty = self._uncertainty(inventory, supplier, promotion, policy)
        result = InvestigationResult(
            query_hash=request.query_hash,
            request=request,
            context_role=context.role,
            refused=False,
            refusal_reason=None,
            summary=self._summary(request, stockouts, supplier, promotion, inventory),
            findings=findings,
            recommended_actions=drafts_result.drafts,
            citations=citations,
            tool_trace=tuple(trace),
            uncertainty=uncertainty,
            human_approval_required=bool(drafts_result.drafts),
        )
        self._final_audit(request, context, result, sequence)
        return result

    # -- assembly helpers -----------------------------------------------------
    def _build_findings(
        self,
        stockouts: ToolResult,
        inventory: ToolResult,
        supplier: ToolResult,
        promotion: ToolResult,
        policy: ToolResult,
    ) -> tuple[Finding, ...]:
        payload = stockouts.payload
        findings = [
            Finding(
                code="STOCKOUT_SPIKE",
                statement=(
                    f"Stockout events rose from {payload['prior_events']} to "
                    f"{payload['current_events']} in scope, with estimated lost sales of "
                    f"{payload['estimated_lost_sales']} across stores {payload['affected_stores']}."
                ),
                metrics=(
                    ("current_events", str(payload["current_events"])),
                    ("prior_events", str(payload["prior_events"])),
                    ("estimated_lost_sales", str(payload["estimated_lost_sales"])),
                    ("dominant_root_cause", str(payload["dominant_root_cause"])),
                ),
                citations=stockouts.citations,
            )
        ]
        if supplier.outcome == "OK" and supplier.payload["worst_supplier_otif_drop"] > 0:
            sp = supplier.payload
            findings.append(
                Finding(
                    code="SUPPLIER_OTIF_DECLINE",
                    statement=(
                        f"Supplier {sp['worst_supplier']} OTIF fell to "
                        f"{sp['worst_supplier_otif_current']} from "
                        f"{sp['worst_supplier_otif_prior']}."
                    ),
                    metrics=(
                        ("worst_supplier", str(sp["worst_supplier"])),
                        ("otif_current", str(sp["worst_supplier_otif_current"])),
                        ("otif_prior", str(sp["worst_supplier_otif_prior"])),
                    ),
                    citations=supplier.citations,
                )
            )
        if promotion.outcome == "OK" and promotion.payload["uplift_surprise"] > 0:
            pp = promotion.payload
            findings.append(
                Finding(
                    code="PROMO_UNDERFORECAST",
                    statement=(
                        f"Promotion uplift ran at {pp['avg_actual_uplift']} versus an expected "
                        f"{pp['avg_expected_uplift']} ({pp['uplift_surprise_pct']} above forecast)."
                    ),
                    metrics=(
                        ("avg_actual_uplift", str(pp["avg_actual_uplift"])),
                        ("avg_expected_uplift", str(pp["avg_expected_uplift"])),
                        ("uplift_surprise", str(pp["uplift_surprise"])),
                    ),
                    citations=promotion.citations,
                )
            )
        if inventory.outcome == "OK" and inventory.payload["stores_below_cover_threshold"] > 0:
            ip = inventory.payload
            findings.append(
                Finding(
                    code="LOW_DAYS_OF_COVER",
                    statement=(
                        f"{ip['stores_below_cover_threshold']} store(s) sit below "
                        f"{ip['cover_threshold_days']} days of cover (min "
                        f"{ip['min_days_of_cover']})."
                    ),
                    metrics=(
                        ("stores_below_cover_threshold", str(ip["stores_below_cover_threshold"])),
                        ("min_days_of_cover", str(ip["min_days_of_cover"])),
                    ),
                    citations=inventory.citations,
                )
            )
        if policy.outcome == "OK":
            findings.append(
                Finding(
                    code="POLICY_GUIDANCE",
                    statement=str(policy.payload["answer"]),
                    metrics=(("uncertainty", str(policy.payload["uncertainty"])),),
                    citations=policy.citations,
                )
            )
        return tuple(findings)

    @staticmethod
    def _drivers(
        stockouts: ToolResult, inventory: ToolResult, supplier: ToolResult
    ) -> dict[str, object]:
        drivers: dict[str, object] = {
            "affected_skus": stockouts.payload.get("affected_skus", []),
            "low_cover_stores": inventory.payload.get("low_cover_stores", []),
        }
        if supplier.outcome == "OK":
            drivers.update(
                {
                    "worst_supplier": supplier.payload["worst_supplier"],
                    "worst_supplier_otif_current": supplier.payload["worst_supplier_otif_current"],
                    "worst_supplier_otif_prior": supplier.payload["worst_supplier_otif_prior"],
                }
            )
        return drivers

    @staticmethod
    def _supporting_citations(
        stockouts: ToolResult, supplier: ToolResult, policy: ToolResult
    ) -> tuple[Citation, ...]:
        citations: list[Citation] = list(stockouts.citations)
        citations.extend(supplier.citations)
        citations.extend(policy.citations)
        return tuple(dict.fromkeys(citations))

    @staticmethod
    def _collect_citations(
        findings: tuple[Finding, ...], drafts: tuple[ActionDraft, ...]
    ) -> tuple[Citation, ...]:
        citations: list[Citation] = []
        for finding in findings:
            citations.extend(finding.citations)
        for draft in drafts:
            citations.extend(draft.citations)
        return tuple(dict.fromkeys(citations))

    @staticmethod
    def _uncertainty(
        inventory: ToolResult, supplier: ToolResult, promotion: ToolResult, policy: ToolResult
    ) -> str:
        if policy.outcome != "OK":
            return "HIGH"
        complete = all(
            result.outcome == "OK" for result in (inventory, supplier, promotion)
        )
        return "LOW" if complete else "MEDIUM"

    @staticmethod
    def _summary(
        request: InvestigationRequest,
        stockouts: ToolResult,
        supplier: ToolResult,
        promotion: ToolResult,
        inventory: ToolResult,
    ) -> str:
        payload = stockouts.payload
        parts = [
            f"In {request.region} / {request.category} over the last {request.window_days} days, "
            f"stockout events rose from {payload['prior_events']} to {payload['current_events']} "
            f"(estimated lost sales {payload['estimated_lost_sales']})."
        ]
        if supplier.outcome == "OK" and supplier.payload["worst_supplier_otif_drop"] > 0:
            parts.append(
                f"Primary driver: supplier {supplier.payload['worst_supplier']} OTIF fell to "
                f"{supplier.payload['worst_supplier_otif_current']}."
            )
        if promotion.outcome == "OK" and promotion.payload["uplift_surprise"] > 0:
            parts.append(
                f"Promotion uplift exceeded forecast by {promotion.payload['uplift_surprise_pct']}."
            )
        if inventory.outcome == "OK":
            parts.append(
                f"{inventory.payload['stores_below_cover_threshold']} store(s) below "
                f"{inventory.payload['cover_threshold_days']} days of cover."
            )
        parts.append("Human approval is required before any action is taken.")
        return " ".join(parts)

    def _no_signal(
        self,
        request: InvestigationRequest,
        context: AgentContext,
        trace: list[ToolInvocation],
        policy: ToolResult,
    ) -> InvestigationResult:
        findings: tuple[Finding, ...] = ()
        if policy.outcome == "OK":
            findings = (
                Finding(
                    code="POLICY_GUIDANCE",
                    statement=str(policy.payload["answer"]),
                    metrics=(("uncertainty", str(policy.payload["uncertainty"])),),
                    citations=policy.citations,
                ),
            )
        return InvestigationResult(
            query_hash=request.query_hash,
            request=request,
            context_role=context.role,
            refused=False,
            refusal_reason=None,
            summary=(
                f"No stockout signal was found in scope for {request.region} / "
                f"{request.category} over the last {request.window_days} days."
            ),
            findings=findings,
            recommended_actions=(),
            citations=tuple(policy.citations),
            tool_trace=tuple(trace),
            uncertainty="LOW",
            human_approval_required=False,
        )

    def _refuse(
        self,
        request: InvestigationRequest,
        context: AgentContext,
        reason: str,
        trace: list[ToolInvocation],
    ) -> InvestigationResult:
        sequence = len(trace) + 1
        self._toolset.log_ai_interaction(
            AuditRecord(
                query_hash=request.query_hash,
                sequence=sequence,
                actor=context.user,
                actor_role=context.role,
                tool_name="orchestrator",
                action_name="REFUSE",
                object_name="INVESTIGATION",
                row_count=0,
                outcome="REFUSED",
                refused=True,
                refusal_reason=reason,
                citation_count=0,
                event_timestamp=self._clock(),
            )
        )
        return InvestigationResult(
            query_hash=request.query_hash,
            request=request,
            context_role=context.role,
            refused=True,
            refusal_reason=reason,
            summary=f"Request refused: {reason}.",
            findings=(),
            recommended_actions=(),
            citations=(),
            tool_trace=tuple(trace),
            uncertainty="HIGH",
            human_approval_required=False,
        )

    def _final_audit(
        self,
        request: InvestigationRequest,
        context: AgentContext,
        result: InvestigationResult,
        sequence: int,
    ) -> None:
        self._toolset.log_ai_interaction(
            AuditRecord(
                query_hash=request.query_hash,
                sequence=sequence + 1,
                actor=context.user,
                actor_role=context.role,
                tool_name="orchestrator",
                action_name="COMPLETE",
                object_name="INVESTIGATION",
                row_count=len(result.findings),
                outcome="OK",
                refused=False,
                refusal_reason=None,
                citation_count=len(result.citations),
                event_timestamp=self._clock(),
            )
        )
