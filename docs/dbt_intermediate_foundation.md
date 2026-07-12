# dbt Intermediate Foundation

## Scope

Phase 4 adds three governed, date-grained intermediate models without changing
RAW or STAGING objects:

| Model | Grain | Purpose |
| --- | --- | --- |
| `int_sales_daily` | `store_id + product_id + date` | Daily sales measures and customer anonymity rate |
| `int_returns_daily` | `store_id + product_id + date` | Daily returned units, value and transactions |
| `int_store_product_daily` | `store_id + product_id + date` | Full-outer-joined sales/returns net measures and flags |

The models are materialized as tables in `PHARMARETAIL_AI_CONTROL_TOWER.INTERMEDIATE`.
The existing compatibility aliases in the first two models preserve the legacy
date/country marts while downstream migration is staged; they are not part of
the new governed contract.

## Deterministic key mapping

The UCI sales and returns sources do not contain the synthetic `store_id` and
`product_id` keys. Each source line is mapped to the existing `stg_store` and
`stg_product` dimensions using the stable expression
`hash(invoice_number, stock_code, 'intermediate-map-v1')`.

The absolute hash is reduced modulo a count of dimension rows, and the result
selects a zero-based `row_number()` ordered by the stable dimension key. The
same invoice/stock-code pair therefore resolves to the same store/product on
every run, with no new data downloaded and no source rows rewritten. Both
models use the identical mapping version so their grains join consistently.

## Reconciliation and business rules

Custom dbt data tests reconcile the model totals to STAGING:

- `int_sales_daily.units_sold = sum(stg_uci_sales.quantity)`
- `int_sales_daily.gross_sales = sum(stg_uci_sales.line_revenue)`
- `int_returns_daily.returned_units = sum(abs(stg_uci_returns.quantity))`
- `int_returns_daily.return_value = sum(abs(stg_uci_returns.line_return_value))`

The combined model is a full outer join so sales-only and return-only days are
retained. It enforces:

```
net_units = units_sold - returned_units
net_sales = gross_sales - return_value
return_rate = returned_units / units_sold (0 when units_sold = 0)
```

Schema tests cover unique grain, required IDs/dates, store/product/date
relationships, non-negative measures, and sales/return flag consistency.

## Verification

Run from `dbt/pharma_retail`:

```bash
dbt compile
dbt build --select intermediate
```

The PR workflow also selects the three foundation nodes so their schema and
reconciliation tests run on every change. Snowflake credentials remain
GitHub-environment secrets; no dbt Cloud SaaS account is required.
