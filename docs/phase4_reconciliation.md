# Phase 4 reconciliation report

## Contracted counts

| Model | Expected rows | Live rows | Status |
|---|---:|---:|---|
| `dim_supplier` | 30 | 30 | PASS |
| `int_operational_scope` | 3,000 | 3,000 | PASS |
| `fct_inventory_snapshot` | 270,000 | 270,000 | PASS |
| `fct_supplier_delivery` | 39,000 | 39,000 | PASS |
| `fct_incident` | 3,000 | 3,000 | PASS |
| `fct_promotion` | deterministic scenario allocation | 423 | PASS |
| `fct_stockout_event` | derived stockout islands | 1,385 | PASS |

Evidence: PR dbt run `29154732088` and governance-enabled deploy
`29155251662`. The full dbt build returned `PASS=170, WARN=0, ERROR=0`.

## Deterministic fingerprints

| Model | `HASH_AGG(*)` |
|---|---:|
| `DIM_SUPPLIER` | `6761210856789760675` |
| `FCT_INCIDENT` | `542729752245523445` |
| `FCT_INVENTORY_SNAPSHOT` | `-4375621901124324368` |
| `FCT_PROMOTION` | `-8200453710208283558` |
| `FCT_STOCKOUT_EVENT` | `1219586913608838440` |
| `FCT_SUPPLIER_DELIVERY` | `3706819069310192392` |

The before/after dictionaries were identical and the workflow emitted
`phase4_deterministic_regeneration=PASS`.

## Reconciliation controls

- Inventory receipts equal delivered quantities on actual delivery dates.
- Inventory equation and day-to-day continuity return zero failing rows.
- Every eligible zero-closing-stock day belongs to exactly one stockout island.
- Scope, inventory, delivery and incident counts match deterministic contracts.
- Running the Phase 4 generation twice returns identical count/hash pairs.
