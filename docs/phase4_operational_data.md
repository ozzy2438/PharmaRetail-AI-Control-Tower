# Phase 4 operational data layer

## Scope and grain

Phase 4 adds six MARTS models for future stockout investigation. It does not add
RAG, an LLM agent, UI, API, dashboard, SOP embedding, or model evaluation.

| Model | Grain | Purpose |
|---|---|---|
| `dim_supplier` | supplier | Thirty deterministic supplier records and lead-time contract |
| `fct_inventory_snapshot` | date × store × product | Reconciled daily inventory equation and expected demand |
| `fct_supplier_delivery` | supplier order | Ordered/delivered quantities, dates, delay and OTIF |
| `fct_stockout_event` | consecutive stockout island | Start/end, duration, lost units and ground truth |
| `fct_promotion` | store × product × campaign | Discount and expected/actual uplift |
| `fct_incident` | store × product × scenario | Severity, status, escalation and detected time |

## Deterministic generation

- Inputs are existing `dim_store`, `dim_product`, and `dim_date` keys.
- The first 30 ordered product keys and all 100 stores form 3,000 operating
  series; dates are fixed to 2026-01-01 through 2026-03-31.
- Every pseudo-variable is derived with a named, versioned Snowflake `HASH`
  seed. No `RANDOM`, current date, external download or runtime-dependent seed
  is used.
- `validate_phase4_determinism.py` fingerprints all six models with row count +
  `HASH_AGG(*)`, reruns `dbt run --select tag:phase4`, and requires identical
  fingerprints.

Seven scenario classes are stored as `ground_truth_root_cause`:

1. `SUPPLIER_DELAY`
2. `PROMOTION_UPLIFT`
3. `REPLENISHMENT_FAILURE`
4. `UNEXPECTED_DEMAND_SPIKE`
5. `INVENTORY_DISCREPANCY`
6. `COLD_CHAIN_INCIDENT`
7. `PRODUCT_RECALL`

## Inventory and stockout rules

Every snapshot reconciles exactly:

```text
opening_stock + received_qty - sold_qty + adjustment_qty = closing_stock
```

Daily opening stock equals the prior day's closing stock. Sold quantity is
bounded by available inventory. Recall, cold-chain write-off and discontinued
states suppress sales. A stockout day requires `closing_stock = 0` and
`expected_demand > 0`; consecutive days are collapsed into one event.

## Tests and lineage

The dbt manifest contains 23 models and 147 tests after Phase 4. New tests cover
keys, required fields, relationships, inventory non-negativity/equation/daily
continuity, delivery and promotion dates, OTIF domain, stockout intervals,
discontinued sales, receipt reconciliation, scenario coverage and expected
row counts. Exact live results are captured in
`docs/phase4_reconciliation.md` and uploaded dbt artifacts.

```text
dim_store ----+
dim_product --+--> int_operational_scope --> int_supplier_orders
dim_date -----+              |                       |
                             v                       +--> fct_supplier_delivery
                    int_inventory_daily_inputs
                             |
                             v
                  fct_inventory_snapshot --> fct_stockout_event
                             |
                             +--> fct_promotion / fct_incident
```
