"""Governed data access. No component may run free-form SQL.

Two gateways implement the same read-only surface:

* ``InMemoryGateway`` serves the deterministic fixture dataset and powers the
  offline test/smoke path.
* ``SnowflakeGateway`` runs a fixed set of parameterised statements against the
  governed Phase 4 marts as ``PHARMARETAIL_AI_APP``. Table names are constants
  and every user-supplied value is passed as a bind parameter, so the class
  cannot express an ad-hoc query.

Two audit sinks implement an append-only log: ``InMemoryAuditSink`` for tests
and ``SnowflakeAuditSink`` which only ever INSERTs into
``AI_LOGS.AGENT_INTERACTION_AUDIT``.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Protocol

from scripts.stockout_agent.contracts import AuditRecord, DraftRecord
from scripts.stockout_agent.fixtures import (
    GatewayDataset,
    InventoryRow,
    PromotionRow,
    StockoutRow,
    SupplierRow,
    default_dataset,
)


class DataGateway(Protocol):
    """Read-only, parameter-only access to governed operational marts."""

    def stockout_events(
        self, region: str, category: str, as_of: date, window_days: int
    ) -> tuple[StockoutRow, ...]: ...

    def inventory_position(
        self, region: str, category: str, as_of: date
    ) -> tuple[InventoryRow, ...]: ...

    def supplier_performance(
        self, region: str, category: str
    ) -> tuple[SupplierRow, ...]: ...

    def promotion_impact(
        self, region: str, category: str
    ) -> tuple[PromotionRow, ...]: ...


class AuditSink(Protocol):
    def append(self, record: AuditRecord) -> None: ...


class DraftSink(Protocol):
    def append(self, record: DraftRecord) -> None: ...


class InMemoryGateway:
    """Serve the frozen fixture dataset, filtered by data scope only."""

    def __init__(self, dataset: GatewayDataset | None = None) -> None:
        self._dataset = dataset or default_dataset()

    def stockout_events(
        self, region: str, category: str, as_of: date, window_days: int
    ) -> tuple[StockoutRow, ...]:
        earliest = as_of - timedelta(days=window_days * 2)
        rows = [
            row
            for row in self._dataset.stockouts
            if row.region == region
            and row.category == category
            and earliest < row.stockout_start_date <= as_of
        ]
        rows.sort(key=lambda row: (row.stockout_start_date, row.store_id, row.product_id))
        return tuple(rows)

    def inventory_position(
        self, region: str, category: str, as_of: date
    ) -> tuple[InventoryRow, ...]:
        rows = [
            row
            for row in self._dataset.inventory
            if row.region == region and row.category == category and row.snapshot_date == as_of
        ]
        rows.sort(key=lambda row: (row.store_id, row.product_id))
        return tuple(rows)

    def supplier_performance(self, region: str, category: str) -> tuple[SupplierRow, ...]:
        rows = [
            row
            for row in self._dataset.supplier
            if row.region == region and row.category == category
        ]
        rows.sort(key=lambda row: (row.supplier_id, row.window, row.store_id, row.product_id))
        return tuple(rows)

    def promotion_impact(self, region: str, category: str) -> tuple[PromotionRow, ...]:
        rows = [
            row
            for row in self._dataset.promotion
            if row.region == region and row.category == category
        ]
        rows.sort(key=lambda row: (row.store_id, row.product_id))
        return tuple(rows)


class InMemoryAuditSink:
    """Append-only in-memory audit log. Records cannot be mutated or removed."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)

    @property
    def records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records)


class InMemoryDraftSink:
    """Append-only in-memory draft log. Records cannot be mutated or removed."""

    def __init__(self) -> None:
        self._records: list[DraftRecord] = []

    def append(self, record: DraftRecord) -> None:
        self._records.append(record)

    @property
    def records(self) -> tuple[DraftRecord, ...]:
        return tuple(self._records)


# --- Snowflake implementations (parameterised, deploy-time verified) ----------
# These run only against the real account through the existing deploy path; the
# unit suite exercises the in-memory gateway. Every statement below is a
# constant with bind parameters — there is no code path that interpolates a
# user value into SQL.

_STOCKOUT_SQL = """
select s.store_id, s.region, s.product_id, p.category,
       s.stockout_start_date, s.stockout_end_date, s.stockout_days,
       s.estimated_lost_sales, s.severity, s.likely_root_cause
from PHARMARETAIL.MARTS.FCT_STOCKOUT_EVENT as s
join PHARMARETAIL.MARTS.DIM_PRODUCT as p on s.product_id = p.product_id
where s.region = %(region)s
  and p.category = %(category)s
  and s.stockout_start_date > %(earliest)s
  and s.stockout_start_date <= %(as_of)s
order by s.stockout_start_date, s.store_id, s.product_id
"""

_INVENTORY_SQL = """
select i.store_id, i.region, i.product_id, p.category, i.snapshot_date,
       i.closing_stock, i.on_order_qty, i.days_of_cover, i.supplier_id
from PHARMARETAIL.MARTS.FCT_INVENTORY_SNAPSHOT as i
join PHARMARETAIL.MARTS.DIM_PRODUCT as p on i.product_id = p.product_id
where i.region = %(region)s
  and p.category = %(category)s
  and i.snapshot_date = %(as_of)s
order by i.store_id, i.product_id
"""

_SUPPLIER_SQL = """
select d.supplier_id, d.store_id, d.region, d.product_id, p.category,
       d.otif, d.ordered_qty, d.delivered_qty, d.late_delivery_flag
from PHARMARETAIL.MARTS.FCT_SUPPLIER_DELIVERY as d
join PHARMARETAIL.MARTS.DIM_PRODUCT as p on d.product_id = p.product_id
where d.region = %(region)s
  and p.category = %(category)s
order by d.supplier_id, d.store_id, d.product_id
"""

_PROMOTION_SQL = """
select r.promotion_id, r.store_id, r.region, r.product_id, p.category,
       r.expected_uplift, r.actual_uplift, r.discount_pct
from PHARMARETAIL.MARTS.FCT_PROMOTION as r
join PHARMARETAIL.MARTS.DIM_PRODUCT as p on r.product_id = p.product_id
where r.region = %(region)s
  and p.category = %(category)s
order by r.store_id, r.product_id
"""


class SnowflakeGateway:
    """Parameter-only reader over the governed marts (production path)."""

    def __init__(self, connection: object) -> None:
        self._connection = connection

    def _query(self, sql: str, params: dict[str, object]) -> list[dict[str, object]]:
        cursor = self._connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute(sql, params)
            columns = [column[0].lower() for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def stockout_events(
        self, region: str, category: str, as_of: date, window_days: int
    ) -> tuple[StockoutRow, ...]:
        params = {
            "region": region,
            "category": category,
            "as_of": as_of,
            "earliest": as_of - timedelta(days=window_days * 2),
        }
        return tuple(
            StockoutRow(
                row["store_id"], row["region"], row["product_id"], row["category"],
                row["stockout_start_date"], row["stockout_end_date"], int(row["stockout_days"]),
                float(row["estimated_lost_sales"]), row["severity"], row["likely_root_cause"],
            )
            for row in self._query(_STOCKOUT_SQL, params)
        )

    def inventory_position(
        self, region: str, category: str, as_of: date
    ) -> tuple[InventoryRow, ...]:
        params = {"region": region, "category": category, "as_of": as_of}
        return tuple(
            InventoryRow(
                row["store_id"], row["region"], row["product_id"], row["category"],
                row["snapshot_date"], int(row["closing_stock"]), int(row["on_order_qty"]),
                float(row["days_of_cover"]), row["supplier_id"],
            )
            for row in self._query(_INVENTORY_SQL, params)
        )

    def supplier_performance(self, region: str, category: str) -> tuple[SupplierRow, ...]:
        params = {"region": region, "category": category}
        return tuple(
            SupplierRow(
                row["supplier_id"], row["store_id"], row["region"], row["product_id"],
                row["category"], "CURRENT", float(row["otif"]), int(row["ordered_qty"]),
                int(row["delivered_qty"]), int(row["late_delivery_flag"]),
            )
            for row in self._query(_SUPPLIER_SQL, params)
        )

    def promotion_impact(self, region: str, category: str) -> tuple[PromotionRow, ...]:
        params = {"region": region, "category": category}
        return tuple(
            PromotionRow(
                row["promotion_id"], row["store_id"], row["region"], row["product_id"],
                row["category"], float(row["expected_uplift"]), float(row["actual_uplift"]),
                int(row["discount_pct"]),
            )
            for row in self._query(_PROMOTION_SQL, params)
        )


_AUDIT_INSERT_SQL = """
insert into PHARMARETAIL_AI_CONTROL_TOWER.AI_LOGS.AGENT_INTERACTION_AUDIT (
    AUDIT_ID, EVENT_TIMESTAMP, ACTOR, ACTOR_ROLE, QUERY_HASH, STEP_SEQUENCE,
    TOOL_NAME, ACTION_NAME, OBJECT_NAME, ROW_COUNT, OUTCOME, REFUSED,
    REFUSAL_REASON, CITATION_COUNT
) values (
    %(audit_id)s, %(event_timestamp)s, %(actor)s, %(actor_role)s, %(query_hash)s,
    %(sequence)s, %(tool_name)s, %(action_name)s, %(object_name)s, %(row_count)s,
    %(outcome)s, %(refused)s, %(refusal_reason)s, %(citation_count)s
)
"""


class SnowflakeAuditSink:
    """Append-only INSERT into the governed agent audit table."""

    def __init__(self, connection: object) -> None:
        self._connection = connection

    def append(self, record: AuditRecord) -> None:
        cursor = self._connection.cursor()  # type: ignore[attr-defined]
        try:
            payload = record.to_dict()
            cursor.execute(_AUDIT_INSERT_SQL, payload)
        finally:
            cursor.close()


_DRAFT_INSERT_SQL = """
insert into PHARMARETAIL_AI_CONTROL_TOWER.AI_LOGS.AGENT_ACTION_DRAFT (
    DRAFT_ID, QUERY_HASH, CREATED_AT, ACTOR, TITLE, BODY, TARGET_SYSTEM,
    PRIORITY, STATUS, REQUIRES_HUMAN_APPROVAL, CITATION_COUNT
) values (
    %(draft_id)s, %(query_hash)s, %(created_at)s, %(actor)s, %(title)s, %(body)s,
    %(target_system)s, %(priority)s, %(status)s, %(requires_human_approval)s,
    %(citation_count)s
)
"""


class SnowflakeDraftSink:
    """Append-only INSERT into the governed agent action-draft table."""

    def __init__(self, connection: object) -> None:
        self._connection = connection

    def append(self, record: DraftRecord) -> None:
        cursor = self._connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute(_DRAFT_INSERT_SQL, record.to_dict())
        finally:
            cursor.close()
