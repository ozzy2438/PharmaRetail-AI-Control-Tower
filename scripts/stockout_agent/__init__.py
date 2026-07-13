"""Phase 6 governed Stockout Investigation Agent.

A deterministic, allowlisted, citation-first agent that investigates stockout
increases over the governed Phase 4 operational marts and the Phase 5 SOP RAG
corpus. It performs no free-form SQL, enforces role/store/region access scope,
requires human approval before any external action, and appends every
interaction to an audit trail.
"""

from __future__ import annotations

from scripts.stockout_agent.contracts import (
    ALLOWLISTED_TOOLS,
    AgentContext,
    InvestigationRequest,
    InvestigationResult,
)
from scripts.stockout_agent.orchestrator import StockoutInvestigationAgent

__all__ = [
    "ALLOWLISTED_TOOLS",
    "AgentContext",
    "InvestigationRequest",
    "InvestigationResult",
    "StockoutInvestigationAgent",
]
