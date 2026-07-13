"""The seven allowlisted tools. No other capability is exposed to the agent.

Every data tool applies the caller's row-level access scope before returning any
metric and attaches a governed-mart citation. ``search_policy_docs`` delegates
to the Phase 5 ``GovernedRetriever`` (identical role names and refusal
guardrails). ``draft_action_plan`` only ever produces a draft that requires
human approval, and ``log_ai_interaction`` appends to the append-only audit
sink.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from statistics import mean

from scripts.governed_rag import GovernedRetriever, RetrievalFilters
from scripts.stockout_agent.contracts import (
    ALLOWLISTED_TOOLS,
    ActionDraft,
    AgentContext,
    AuditRecord,
    Citation,
    InvestigationRequest,
)
from scripts.stockout_agent.gateway import AuditSink, DataGateway

STOCKOUT_MART = "PHARMARETAIL.MARTS.FCT_STOCKOUT_EVENT"
INVENTORY_MART = "PHARMARETAIL.MARTS.FCT_INVENTORY_SNAPSHOT"
SUPPLIER_MART = "PHARMARETAIL.MARTS.FCT_SUPPLIER_DELIVERY"
PROMOTION_MART = "PHARMARETAIL.MARTS.FCT_PROMOTION"
DAYS_OF_COVER_THRESHOLD = 2.0


class ToolError(RuntimeError):
    """Raised when a tool is called outside the allowlist or its contract."""


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    outcome: str  # OK | NO_DATA | DENIED | REFUSED | DRAFT_CREATED | LOGGED
    row_count: int
    payload: dict[str, object] = field(default_factory=dict)
    citations: tuple[Citation, ...] = ()
    drafts: tuple[ActionDraft, ...] = ()


def _data_citation(mart: str, request: InvestigationRequest) -> Citation:
    detail = (
        f"region={request.region}; category={request.category}; "
        f"as_of={request.as_of_date.isoformat()}; window_days={request.window_days}"
    )
    return Citation(kind="DATA", reference=mart, detail=detail)


def _pct(value: float) -> str:
    return f"{round(value * 100, 1)}%"


class AllowlistToolset:
    """Bundles the governed dependencies and exposes exactly seven tools."""

    def __init__(
        self,
        gateway: DataGateway,
        retriever: GovernedRetriever,
        audit_sink: AuditSink,
    ) -> None:
        self._gateway = gateway
        self._retriever = retriever
        self._audit_sink = audit_sink

    # -- tool 1 ---------------------------------------------------------------
    def get_stockout_metrics(
        self, context: AgentContext, request: InvestigationRequest
    ) -> ToolResult:
        rows = self._gateway.stockout_events(
            request.region, request.category, request.as_of_date, request.window_days
        )
        visible = [row for row in rows if context.store_is_visible(row.store_id, row.region)]
        boundary = request.as_of_date.toordinal() - request.window_days
        current = [row for row in visible if row.stockout_start_date.toordinal() > boundary]
        prior = [row for row in visible if row.stockout_start_date.toordinal() <= boundary]
        if not current:
            return ToolResult(
                "get_stockout_metrics", "NO_DATA", len(visible),
                citations=(_data_citation(STOCKOUT_MART, request),),
            )
        severity: dict[str, int] = {}
        for row in current:
            severity[row.severity] = severity.get(row.severity, 0) + 1
        payload = {
            "current_events": len(current),
            "prior_events": len(prior),
            "event_delta": len(current) - len(prior),
            "affected_stores": sorted({row.store_id for row in current}),
            "affected_skus": sorted({row.product_id for row in current}),
            "estimated_lost_sales": round(sum(row.estimated_lost_sales for row in current), 2),
            "severity_breakdown": dict(sorted(severity.items())),
            "dominant_root_cause": _mode([row.likely_root_cause for row in current]),
        }
        return ToolResult(
            "get_stockout_metrics", "OK", len(visible), payload,
            (_data_citation(STOCKOUT_MART, request),),
        )

    # -- tool 2 ---------------------------------------------------------------
    def get_inventory_position(
        self, context: AgentContext, request: InvestigationRequest
    ) -> ToolResult:
        rows = self._gateway.inventory_position(
            request.region, request.category, request.as_of_date
        )
        visible = [row for row in rows if context.store_is_visible(row.store_id, row.region)]
        if not visible:
            return ToolResult(
                "get_inventory_position", "NO_DATA", 0,
                citations=(_data_citation(INVENTORY_MART, request),),
            )
        low_cover = [row for row in visible if row.days_of_cover < DAYS_OF_COVER_THRESHOLD]
        payload = {
            "stores_below_cover_threshold": len({row.store_id for row in low_cover}),
            "cover_threshold_days": DAYS_OF_COVER_THRESHOLD,
            "min_days_of_cover": min(row.days_of_cover for row in visible),
            "on_order_units_total": sum(row.on_order_qty for row in visible),
            "low_cover_stores": sorted({row.store_id for row in low_cover}),
        }
        return ToolResult(
            "get_inventory_position", "OK", len(visible), payload,
            (_data_citation(INVENTORY_MART, request),),
        )

    # -- tool 3 ---------------------------------------------------------------
    def get_supplier_performance(
        self, context: AgentContext, request: InvestigationRequest
    ) -> ToolResult:
        rows = self._gateway.supplier_performance(request.region, request.category)
        visible = [row for row in rows if context.store_is_visible(row.store_id, row.region)]
        if not visible:
            return ToolResult(
                "get_supplier_performance", "NO_DATA", 0,
                citations=(_data_citation(SUPPLIER_MART, request),),
            )
        suppliers: dict[str, dict[str, list[float]]] = {}
        for row in visible:
            window = suppliers.setdefault(row.supplier_id, {"PRIOR": [], "CURRENT": []})
            window.setdefault(row.window, []).append(row.otif)
        worst_supplier = None
        worst_drop = 0.0
        summary: dict[str, dict[str, float]] = {}
        for supplier_id, windows in sorted(suppliers.items()):
            current = round(mean(windows["CURRENT"]), 4) if windows["CURRENT"] else 0.0
            prior = round(mean(windows["PRIOR"]), 4) if windows["PRIOR"] else current
            drop = round(prior - current, 4)
            summary[supplier_id] = {"otif_current": current, "otif_prior": prior, "otif_drop": drop}
            if drop >= worst_drop:
                worst_drop, worst_supplier = drop, supplier_id
        payload = {
            "worst_supplier": worst_supplier,
            "worst_supplier_otif_current": summary[worst_supplier]["otif_current"],
            "worst_supplier_otif_prior": summary[worst_supplier]["otif_prior"],
            "worst_supplier_otif_drop": worst_drop,
            "supplier_summary": summary,
        }
        return ToolResult(
            "get_supplier_performance", "OK", len(visible), payload,
            (_data_citation(SUPPLIER_MART, request),),
        )

    # -- tool 4 ---------------------------------------------------------------
    def get_promotion_impact(
        self, context: AgentContext, request: InvestigationRequest
    ) -> ToolResult:
        rows = self._gateway.promotion_impact(request.region, request.category)
        visible = [row for row in rows if context.store_is_visible(row.store_id, row.region)]
        if not visible:
            return ToolResult(
                "get_promotion_impact", "NO_DATA", 0,
                citations=(_data_citation(PROMOTION_MART, request),),
            )
        expected = round(mean(row.expected_uplift for row in visible), 4)
        actual = round(mean(row.actual_uplift for row in visible), 4)
        surprise = round(actual - expected, 4)
        payload = {
            "promotions": len(visible),
            "avg_expected_uplift": expected,
            "avg_actual_uplift": actual,
            "uplift_surprise": surprise,
            "uplift_surprise_pct": _pct(surprise),
            "promotion_ids": sorted({row.promotion_id for row in visible}),
        }
        return ToolResult(
            "get_promotion_impact", "OK", len(visible), payload,
            (_data_citation(PROMOTION_MART, request),),
        )

    # -- tool 5 ---------------------------------------------------------------
    def search_policy_docs(
        self, context: AgentContext, query: str, as_of: date
    ) -> ToolResult:
        # No business-unit filter: relevant policy spans RETAIL_OPERATIONS
        # (replenishment) and SUPPLY_CHAIN (escalation). Role-based access level
        # still governs what each caller may retrieve.
        result = self._retriever.answer(
            query,
            context.role,
            RetrievalFilters(country="AU", as_of_date=as_of),
        )
        if result.refused:
            return ToolResult(
                "search_policy_docs", "REFUSED", 0,
                payload={"refusal_reason": result.refusal_reason, "answer": result.answer},
                citations=tuple(
                    Citation(kind="POLICY", reference=citation) for citation in result.citations
                ),
            )
        citations = tuple(
            Citation(kind="POLICY", reference=citation) for citation in result.citations
        )
        payload = {
            "answer": result.answer,
            "uncertainty": result.uncertainty,
            "top_citation": result.citations[0] if result.citations else "",
        }
        return ToolResult(
            "search_policy_docs", "OK", len(result.retrieved), payload, citations
        )

    # -- tool 6 ---------------------------------------------------------------
    def draft_action_plan(
        self,
        context: AgentContext,
        request: InvestigationRequest,
        supporting_citations: tuple[Citation, ...],
        drivers: dict[str, object],
    ) -> ToolResult:
        # A draft only. Nothing here contacts an external system or opens a
        # real ticket; ``requires_human_approval`` is always True.
        supplier = drivers.get("worst_supplier", "the primary supplier")
        replenishment = ActionDraft(
            title=f"Emergency replenishment review — {request.category} in {request.region}",
            body=(
                f"Trigger an emergency replenishment review for affected SKUs "
                f"{drivers.get('affected_skus', [])} across stores "
                f"{drivers.get('low_cover_stores', [])} where days-of-cover is below "
                f"{DAYS_OF_COVER_THRESHOLD}."
            ),
            target_system="REPLENISHMENT_QUEUE_DRAFT",
            priority="HIGH",
            citations=supporting_citations,
        )
        escalation = ActionDraft(
            title=f"Supplier escalation draft — {supplier}",
            body=(
                f"Draft a supplier escalation for {supplier}: OTIF fell to "
                f"{drivers.get('worst_supplier_otif_current', 'n/a')} from "
                f"{drivers.get('worst_supplier_otif_prior', 'n/a')}. Route for human approval "
                f"before any ticket is opened."
            ),
            target_system="SUPPLIER_ESCALATION_DRAFT",
            priority="HIGH",
            citations=supporting_citations,
        )
        return ToolResult(
            "draft_action_plan", "DRAFT_CREATED", 2,
            payload={"draft_count": 2},
            drafts=(replenishment, escalation),
        )

    # -- tool 7 ---------------------------------------------------------------
    def log_ai_interaction(self, record: AuditRecord) -> ToolResult:
        self._audit_sink.append(record)
        return ToolResult("log_ai_interaction", "LOGGED", 1, payload={"audit_id": record.audit_id})

    # -- allowlist enforcement ------------------------------------------------
    def is_allowlisted(self, name: str) -> bool:
        return name in ALLOWLISTED_TOOLS

    def resolve(self, name: str):
        if name not in ALLOWLISTED_TOOLS:
            raise ToolError(f"Tool '{name}' is not on the allowlist")
        return getattr(self, name)


def _mode(values: list[str]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    # Deterministic tie-break: highest count, then lexical order.
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
