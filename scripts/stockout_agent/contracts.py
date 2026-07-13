"""Immutable contracts and the role/store/region access model for the agent.

Everything here is deterministic and dependency-free so that identical inputs
always produce byte-for-byte identical structured output. Access scope mirrors
the Snowflake ``GOVERNANCE.USER_STORE_SCOPE`` / ``USER_REGION_SCOPE`` tables and
the ``OPERATIONAL_STORE_REGION_POLICY`` row-access policy created in
``infra/snowflake/10_phase4_governance.sql``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date

# The seven — and only seven — tools the orchestrator is permitted to call.
# The orchestrator refuses any name outside this tuple.
ALLOWLISTED_TOOLS: tuple[str, ...] = (
    "get_stockout_metrics",
    "get_inventory_position",
    "get_supplier_performance",
    "get_promotion_impact",
    "search_policy_docs",
    "draft_action_plan",
    "log_ai_interaction",
)

# Data-access breadth per role, mirroring the Phase 4 row-access policy.
SCOPE_NATIONAL = "NATIONAL"
SCOPE_REGION = "REGION"
SCOPE_STORE = "STORE"
SCOPE_NONE = "NONE"

ROLE_DATA_SCOPE: dict[str, str] = {
    "PHARMARETAIL_ADMIN": SCOPE_NATIONAL,
    "PHARMARETAIL_AI_APP": SCOPE_NATIONAL,
    "PHARMARETAIL_SUPPLY_CHAIN_ANALYST": SCOPE_NATIONAL,
    "PHARMARETAIL_AREA_MANAGER": SCOPE_REGION,
    "PHARMARETAIL_STORE_MANAGER": SCOPE_STORE,
    "PHARMARETAIL_READONLY": SCOPE_NONE,
}


class AccessDeniedError(RuntimeError):
    """Raised when a context is not permitted to run an investigation at all."""


@dataclass(frozen=True)
class AgentContext:
    """Who is asking, in which role, and what store/region scope they hold."""

    user: str
    role: str
    allowed_store_ids: tuple[str, ...] = ()
    allowed_regions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "user", self.user.strip().upper())
        object.__setattr__(self, "role", self.role.strip().upper())
        object.__setattr__(
            self,
            "allowed_store_ids",
            tuple(sorted({value.strip().upper() for value in self.allowed_store_ids})),
        )
        object.__setattr__(
            self,
            "allowed_regions",
            tuple(sorted({value.strip().upper() for value in self.allowed_regions})),
        )

    @property
    def scope_kind(self) -> str:
        return ROLE_DATA_SCOPE.get(self.role, SCOPE_NONE)

    def can_investigate(self) -> bool:
        return self.scope_kind != SCOPE_NONE

    def store_is_visible(self, store_id: str, region: str) -> bool:
        """Row-level visibility decision, identical in spirit to the SQL policy."""
        scope = self.scope_kind
        if scope == SCOPE_NATIONAL:
            return True
        if scope == SCOPE_STORE:
            return store_id.strip().upper() in self.allowed_store_ids
        if scope == SCOPE_REGION:
            return region.strip().upper() in self.allowed_regions
        return False


@dataclass(frozen=True)
class InvestigationRequest:
    """A structured stockout investigation. No free SQL ever crosses this line."""

    question: str
    region: str
    category: str
    window_days: int = 14
    as_of_date: date = field(default_factory=date.today)
    country: str = "AU"

    def __post_init__(self) -> None:
        object.__setattr__(self, "region", self.region.strip().upper())
        object.__setattr__(self, "category", self.category.strip().lower())
        object.__setattr__(self, "country", self.country.strip().upper())
        if self.window_days <= 0:
            raise ValueError("window_days must be positive")

    @property
    def query_hash(self) -> str:
        payload = "|".join(
            (
                self.question.strip().lower(),
                self.region,
                self.category,
                str(self.window_days),
                self.as_of_date.isoformat(),
                self.country,
            )
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Citation:
    """A provenance record. ``DATA`` cites a governed mart; ``POLICY`` a SOP."""

    kind: str  # "DATA" | "POLICY"
    reference: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "reference": self.reference, "detail": self.detail}


@dataclass(frozen=True)
class Finding:
    """A single evidenced statement. Every finding must carry >=1 citation."""

    code: str
    statement: str
    metrics: tuple[tuple[str, str], ...]
    citations: tuple[Citation, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "statement": self.statement,
            "metrics": {key: value for key, value in self.metrics},
            "citations": [citation.to_dict() for citation in self.citations],
        }


@dataclass(frozen=True)
class ActionDraft:
    """A proposed action. Always a draft; never executed against any system."""

    title: str
    body: str
    target_system: str
    priority: str
    citations: tuple[Citation, ...]
    requires_human_approval: bool = True
    status: str = "DRAFT_PENDING_APPROVAL"

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "body": self.body,
            "target_system": self.target_system,
            "priority": self.priority,
            "requires_human_approval": self.requires_human_approval,
            "status": self.status,
            "citations": [citation.to_dict() for citation in self.citations],
        }


@dataclass(frozen=True)
class ToolInvocation:
    """One recorded, allowlisted tool call for the audit trail."""

    sequence: int
    tool_name: str
    arguments: tuple[tuple[str, str], ...]
    row_count: int
    outcome: str

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "tool_name": self.tool_name,
            "arguments": {key: value for key, value in self.arguments},
            "row_count": self.row_count,
            "outcome": self.outcome,
        }


@dataclass(frozen=True)
class InvestigationResult:
    """The full structured answer. ``to_dict`` yields deterministic JSON."""

    query_hash: str
    request: InvestigationRequest
    context_role: str
    refused: bool
    refusal_reason: str | None
    summary: str
    findings: tuple[Finding, ...]
    recommended_actions: tuple[ActionDraft, ...]
    citations: tuple[Citation, ...]
    tool_trace: tuple[ToolInvocation, ...]
    uncertainty: str
    human_approval_required: bool

    def citation_coverage(self) -> float:
        """Share of findings that carry at least one citation (1.0 == full)."""
        if not self.findings:
            return 1.0
        covered = sum(1 for finding in self.findings if finding.citations)
        return round(covered / len(self.findings), 4)

    def to_dict(self) -> dict[str, object]:
        return {
            "query_hash": self.query_hash,
            "request": {
                "question": self.request.question,
                "region": self.request.region,
                "category": self.request.category,
                "window_days": self.request.window_days,
                "as_of_date": self.request.as_of_date.isoformat(),
                "country": self.request.country,
            },
            "context_role": self.context_role,
            "refused": self.refused,
            "refusal_reason": self.refusal_reason,
            "summary": self.summary,
            "findings": [finding.to_dict() for finding in self.findings],
            "recommended_actions": [action.to_dict() for action in self.recommended_actions],
            "citations": [citation.to_dict() for citation in self.citations],
            "citation_coverage": self.citation_coverage(),
            "tool_trace": [call.to_dict() for call in self.tool_trace],
            "uncertainty": self.uncertainty,
            "human_approval_required": self.human_approval_required,
        }


@dataclass(frozen=True)
class AuditRecord:
    """One append-only audit row. ``audit_id`` is deterministic and unique."""

    query_hash: str
    sequence: int
    actor: str
    actor_role: str
    tool_name: str
    action_name: str
    object_name: str
    row_count: int
    outcome: str
    refused: bool
    refusal_reason: str | None
    citation_count: int
    event_timestamp: str

    @property
    def audit_id(self) -> str:
        payload = f"{self.query_hash}|{self.sequence}|{self.tool_name}|{self.action_name}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "audit_id": self.audit_id,
            "query_hash": self.query_hash,
            "sequence": self.sequence,
            "actor": self.actor,
            "actor_role": self.actor_role,
            "tool_name": self.tool_name,
            "action_name": self.action_name,
            "object_name": self.object_name,
            "row_count": self.row_count,
            "outcome": self.outcome,
            "refused": self.refused,
            "refusal_reason": self.refusal_reason,
            "citation_count": self.citation_count,
            "event_timestamp": self.event_timestamp,
        }


@dataclass(frozen=True)
class DraftRecord:
    """One append-only action-draft row. ``draft_id`` is deterministic/unique.

    Persisting a draft never takes an external action: the row always carries
    ``requires_human_approval = True`` and ``status = 'DRAFT_PENDING_APPROVAL'``.
    """

    query_hash: str
    sequence: int
    actor: str
    title: str
    body: str
    target_system: str
    priority: str
    citation_count: int
    created_at: str
    requires_human_approval: bool = True
    status: str = "DRAFT_PENDING_APPROVAL"

    @property
    def draft_id(self) -> str:
        payload = f"{self.query_hash}|{self.sequence}|{self.title}|{self.target_system}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "draft_id": self.draft_id,
            "query_hash": self.query_hash,
            "sequence": self.sequence,
            "actor": self.actor,
            "title": self.title,
            "body": self.body,
            "target_system": self.target_system,
            "priority": self.priority,
            "status": self.status,
            "requires_human_approval": self.requires_human_approval,
            "citation_count": self.citation_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_action(
        cls,
        action: "ActionDraft",
        *,
        query_hash: str,
        sequence: int,
        actor: str,
        created_at: str,
    ) -> "DraftRecord":
        # A DraftRecord may only ever be built from an approval-required draft.
        if not action.requires_human_approval or action.status != "DRAFT_PENDING_APPROVAL":
            raise ValueError("Only approval-pending drafts may be persisted")
        return cls(
            query_hash=query_hash,
            sequence=sequence,
            actor=actor,
            title=action.title,
            body=action.body,
            target_system=action.target_system,
            priority=action.priority,
            citation_count=len(action.citations),
            created_at=created_at,
        )
