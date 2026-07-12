# dbt staging foundation

## Scope

This layer defines five sources in `PHARMARETAIL.RAW` and exposes five typed,
one-to-one views in `PHARMARETAIL.STAGING`. It does not modify RAW data or build
intermediate models, marts, inventory, stockout, RAG, AI, or dashboards.

| RAW source | Staging view | Expected rows |
|---|---|---:|
| `RAW.STORE_SEED` | `STAGING.STG_STORE` | 100 |
| `RAW.PRODUCT_SEED` | `STAGING.STG_PRODUCT` | 300 |
| `RAW.UCI_SALES` | `STAGING.STG_UCI_SALES` | 1,007,913 |
| `RAW.UCI_RETURNS` | `STAGING.STG_UCI_RETURNS` | 19,104 |
| `RAW.UCI_INVALID_PRICE` | `STAGING.STG_UCI_INVALID_PRICE` | 6,019 |

All output columns use snake_case names and explicit Snowflake casts. Source
lineage columns `_source_file` and `_loaded_at` are retained. Store postcodes
remain nullable, and `postcode_available_flag` is retained and tested against
postcode nullability.

## Data quality

Schema tests cover required identifiers, store and product uniqueness, accepted
boolean and categorical values, geographic ranges, valid invoice dates, and
numeric business rules. Exact UCI-row uniqueness is tested with each table's
complete business-column combination. Five singular tests reconcile every
staging row count to its RAW source.

No relationships tests are added between UCI transactions and the synthetic
store or product seeds because those datasets have no shared business key.
Adding such a test would assert a fabricated relationship.

## Commands

Run from `dbt/pharma_retail` with Snowflake credentials supplied through a
secure local profile or environment variables:

```bash
dbt debug
dbt compile
dbt build --indirect-selection cautious --select path:models/staging source:raw
```

The cautious scoped build includes source, staging, and reconciliation tests
while intentionally excluding existing intermediate and mart models and tests.
