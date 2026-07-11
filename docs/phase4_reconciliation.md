# Phase 4 reconciliation report

## Contracted counts

| Model | Expected rows | Live rows | Status |
|---|---:|---:|---|
| `dim_supplier` | 30 | pending protected workflow | Pending |
| `int_operational_scope` | 3,000 | pending protected workflow | Pending |
| `fct_inventory_snapshot` | 270,000 | pending protected workflow | Pending |
| `fct_supplier_delivery` | 39,000 | pending protected workflow | Pending |
| `fct_incident` | 3,000 | pending protected workflow | Pending |
| `fct_promotion` | deterministic scenario allocation | pending protected workflow | Pending |
| `fct_stockout_event` | derived stockout islands | pending protected workflow | Pending |

The deployment workflow replaces pending values with evidence from the dbt run
summary and deterministic fingerprint output. Phase 4 is not complete while any
row remains pending.

## Reconciliation controls

- Inventory receipts equal delivered quantities on actual delivery dates.
- Inventory equation and day-to-day continuity return zero failing rows.
- Every eligible zero-closing-stock day belongs to exactly one stockout island.
- Scope, inventory, delivery and incident counts match deterministic contracts.
- Running the Phase 4 generation twice returns identical count/hash pairs.
