"""Deterministic in-memory dataset used for offline tests and local smoke runs.

These rows intentionally reproduce the Phase 6 narrative in ``project.md`` (a
Melbourne pain-relief stockout spike driven by a supplier OTIF collapse and an
under-forecast promotion) and add an out-of-scope Sydney store so row-level
access control can be proven. Nothing here is random; the same rows are
returned on every call so investigation output is byte-for-byte reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class StockoutRow:
    store_id: str
    region: str
    product_id: str
    category: str
    stockout_start_date: date
    stockout_end_date: date
    stockout_days: int
    estimated_lost_sales: float
    severity: str
    likely_root_cause: str


@dataclass(frozen=True)
class InventoryRow:
    store_id: str
    region: str
    product_id: str
    category: str
    snapshot_date: date
    closing_stock: int
    on_order_qty: int
    days_of_cover: float
    supplier_id: str


@dataclass(frozen=True)
class SupplierRow:
    supplier_id: str
    store_id: str
    region: str
    product_id: str
    category: str
    window: str  # "PRIOR" | "CURRENT"
    otif: float
    ordered_qty: int
    delivered_qty: int
    late_delivery_flag: int


@dataclass(frozen=True)
class PromotionRow:
    promotion_id: str
    store_id: str
    region: str
    product_id: str
    category: str
    expected_uplift: float
    actual_uplift: float
    discount_pct: int


@dataclass(frozen=True)
class GatewayDataset:
    stockouts: tuple[StockoutRow, ...]
    inventory: tuple[InventoryRow, ...]
    supplier: tuple[SupplierRow, ...]
    promotion: tuple[PromotionRow, ...]


MELBOURNE = "MELBOURNE"
SYDNEY = "SYDNEY"
PAIN_RELIEF = "pain relief"
SUPPLIER_A = "SUP-A"
SKU_1 = "SKU-10483"
SKU_2 = "SKU-11820"
MEL_STORES = ("MEL-001", "MEL-002", "MEL-003", "MEL-004", "MEL-005", "MEL-006")


def _prior_stockouts() -> tuple[StockoutRow, ...]:
    # Prior 14-day window (2026-01-06..2026-01-19): two mild events.
    return (
        StockoutRow(
            "MEL-001", MELBOURNE, SKU_1, PAIN_RELIEF,
            date(2026, 1, 9), date(2026, 1, 10), 2, 180.0, "MEDIUM", "REPLENISHMENT_GAP",
        ),
        StockoutRow(
            "MEL-002", MELBOURNE, SKU_2, PAIN_RELIEF,
            date(2026, 1, 14), date(2026, 1, 15), 2, 165.0, "MEDIUM", "REPLENISHMENT_GAP",
        ),
    )


def _current_stockouts() -> tuple[StockoutRow, ...]:
    # Current 14-day window (2026-01-20..2026-02-02): the spike under investigation.
    return (
        StockoutRow(
            "MEL-001", MELBOURNE, SKU_1, PAIN_RELIEF,
            date(2026, 1, 22), date(2026, 1, 27), 6, 620.0, "CRITICAL", "SUPPLIER_DELAY",
        ),
        StockoutRow(
            "MEL-002", MELBOURNE, SKU_1, PAIN_RELIEF,
            date(2026, 1, 23), date(2026, 1, 26), 4, 410.0, "HIGH", "SUPPLIER_DELAY",
        ),
        StockoutRow(
            "MEL-003", MELBOURNE, SKU_2, PAIN_RELIEF,
            date(2026, 1, 24), date(2026, 1, 27), 4, 395.0, "HIGH", "PROMO_UPLIFT",
        ),
        StockoutRow(
            "MEL-004", MELBOURNE, SKU_2, PAIN_RELIEF,
            date(2026, 1, 28), date(2026, 1, 30), 3, 260.0, "HIGH", "PROMO_UPLIFT",
        ),
    )


def _sydney_stockouts() -> tuple[StockoutRow, ...]:
    # Out-of-scope region/store, used to prove access filtering.
    return (
        StockoutRow(
            "SYD-001", SYDNEY, SKU_1, PAIN_RELIEF,
            date(2026, 1, 25), date(2026, 1, 28), 4, 300.0, "HIGH", "SUPPLIER_DELAY",
        ),
    )


def _inventory() -> tuple[InventoryRow, ...]:
    as_of = date(2026, 2, 2)
    # Six Melbourne stores below two days of cover on the affected SKUs.
    low_cover = tuple(
        InventoryRow(
            store, MELBOURNE, SKU_1 if index % 2 == 0 else SKU_2, PAIN_RELIEF,
            as_of, closing_stock=index, on_order_qty=40 + index,
            days_of_cover=round(0.5 + index * 0.2, 2), supplier_id=SUPPLIER_A,
        )
        for index, store in enumerate(MEL_STORES)
    )
    sydney = (
        InventoryRow(
            "SYD-001", SYDNEY, SKU_1, PAIN_RELIEF,
            as_of, closing_stock=1, on_order_qty=30, days_of_cover=0.8, supplier_id=SUPPLIER_A,
        ),
    )
    return low_cover + sydney


def _supplier() -> tuple[SupplierRow, ...]:
    def row(store: str, region: str, window: str, otif: float, delivered: int, late: int):
        return SupplierRow(
            SUPPLIER_A, store, region, SKU_1, PAIN_RELIEF, window, otif, 100, delivered, late
        )

    return (
        row("MEL-001", MELBOURNE, "PRIOR", 0.91, 91, 9),
        row("MEL-002", MELBOURNE, "PRIOR", 0.91, 91, 9),
        row("MEL-001", MELBOURNE, "CURRENT", 0.72, 72, 28),
        row("MEL-002", MELBOURNE, "CURRENT", 0.72, 72, 28),
        row("SYD-001", SYDNEY, "CURRENT", 0.70, 70, 30),
    )


def _promotion() -> tuple[PromotionRow, ...]:
    return (
        PromotionRow(
            "PROMO-2026-01-MEL-003", "MEL-003", MELBOURNE, SKU_2, PAIN_RELIEF, 0.35, 0.73, 20
        ),
        PromotionRow(
            "PROMO-2026-01-MEL-004", "MEL-004", MELBOURNE, SKU_2, PAIN_RELIEF, 0.35, 0.73, 20
        ),
        PromotionRow(
            "PROMO-2026-01-SYD-001", "SYD-001", SYDNEY, SKU_1, PAIN_RELIEF, 0.35, 0.40, 15
        ),
    )


def default_dataset() -> GatewayDataset:
    """Return the frozen demonstration dataset."""
    return GatewayDataset(
        stockouts=_prior_stockouts() + _current_stockouts() + _sydney_stockouts(),
        inventory=_inventory(),
        supplier=_supplier(),
        promotion=_promotion(),
    )
