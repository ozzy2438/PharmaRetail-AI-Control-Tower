# Snowflake RAW foundation

## Scope

This phase creates the `PHARMARETAIL` database, its empty downstream schemas, and five
source-aligned RAW tables. It loads only the existing processed and quarantine files. It does
not regenerate source files, enrich missing postcodes, create dbt models or marts, or implement
AI, RAG, agents, or dashboards.

## Object structure

| Object type | Objects |
|---|---|
| Database | `PHARMARETAIL` |
| Schemas | `RAW`, `STAGING`, `MARTS`, `GOVERNANCE`, `AI_LOGS` |
| RAW tables | `STORE_SEED`, `PRODUCT_SEED`, `UCI_SALES`, `UCI_RETURNS`, `UCI_INVALID_PRICE` |
| Load support | `RAW.RAW_LOAD_STAGE`, `RAW.SEED_CSV_FORMAT`, `RAW.CLEAN_PARQUET_FORMAT` |

`STAGING`, `MARTS`, and `AI_LOGS` are created but intentionally remain empty in this phase.

## SQL execution order

Run these files explicitly, in order, from the repository root:

1. `infra/snowflake/01_create_foundation.sql`
2. `infra/snowflake/02_create_raw_tables.sql`
3. `infra/snowflake/03_load_raw_data.sql`
4. `infra/snowflake/04_validate_raw_load.sql`

The load script uses Snowflake `PUT`, so it must run through SnowSQL or a Snowflake driver with
access to the local repository paths. It stages each unchanged source file, truncates only its
matching RAW target, performs an explicitly typed `COPY INTO`, and removes the staged copy after
loading. `FORCE = TRUE` makes a deliberate full reload reproducible despite Snowflake load history.

Parquet timestamps are stored as nanoseconds and loaded with
`TO_TIMESTAMP_NTZ(..., 9)`. CSV postcodes are loaded as strings so values such as `0800` retain
their leading zero. Every table adds only `_SOURCE_FILE` and `_LOADED_AT` lineage columns.
`STORE_SEED` also derives `POSTCODE_AVAILABLE_FLAG` from the nullable source postcode.

## Source-to-RAW mapping and reconciliation

| Source file | RAW table | Expected rows | Validation |
|---|---|---:|---|
| `data/processed/dim_store_seed.csv` | `RAW.STORE_SEED` | 100 | `04_validate_raw_load.sql` |
| `data/processed/dim_product_seed.csv` | `RAW.PRODUCT_SEED` | 300 | `04_validate_raw_load.sql` |
| `data/processed/uci_sales_clean.parquet` | `RAW.UCI_SALES` | 1,007,913 | `04_validate_raw_load.sql` |
| `data/processed/uci_returns_clean.parquet` | `RAW.UCI_RETURNS` | 19,104 | `04_validate_raw_load.sql` |
| `data/quarantine/uci_invalid_price.parquet` | `RAW.UCI_INVALID_PRICE` | 6,019 | `04_validate_raw_load.sql` |

The validation SQL returns one row per check and marks it `PASS` only when actual and expected
values match. It checks row counts, store and product ID nulls/duplicates, UCI identity nulls,
exact UCI duplicates, timestamp/numeric Snowflake types, and postcode flag consistency.

UCI invoice lines do not have a single source primary key: an invoice legitimately contains
multiple stock lines. Their RAW identity check therefore requires `invoice`, `stock_code`, and
`invoice_date`, while duplicate validation uses every source business column.

## Known data limitations

- `STORE_SEED.POSTCODE` remains nullable. The source contains 70 populated and 30 null postcodes;
  validation requires `POSTCODE_AVAILABLE_FLAG` to contain 70 `TRUE` and 30 `FALSE` values.
- Null UCI `customer_id` values are retained exactly as supplied by the cleaned source and remain
  governed by `is_customer_identified`.
- `UCI_INVALID_PRICE` remains isolated from sales and returns; no quarantine row is repaired here.
- Loading is a full truncate-and-reload, not incremental or CDC ingestion.
- Snowflake execution requires account, user, role, warehouse, database, and exactly one supported
  authentication method in the environment. Local source and SQL validation can run without them,
  but warehouse row reconciliation cannot.
