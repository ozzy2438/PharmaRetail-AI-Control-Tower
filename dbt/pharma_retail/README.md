# pharma_retail dbt project

Transforms Snowflake `RAW` (Phase 2 data ingestion) into `STAGING` → `INTERMEDIATE` → `MARTS`, using the `SVC_PHARMARETAIL_DBT` service identity (ADR-003). dbt-core, run via GitHub Actions — see [Running dbt](#running-dbt) for why this isn't dbt Cloud SaaS.

## Why the UCI sales facts don't join to `dim_store`/`dim_product`

This is a deliberate modelling boundary, not an oversight. The project has two unrelated data sources loaded into `RAW` in Phase 2:

- **UCI Online Retail II** (`RAW.UCI_SALES`, `RAW.UCI_RETURNS`, `RAW.UCI_INVALID_PRICE`): real transactional data from a single UK-based online retailer. Its product identifier is `stock_code` (e.g. `85123A`); it has no store dimension at all — it is one retailer, not a chain.
- **Synthetic seeds** (`RAW.STORE_SEED`, `RAW.PRODUCT_SEED`): a fully synthetic 300-row pharmacy-retail product catalog (`product_id`: `PRD0001`–`PRD0300`) and a 100-row Australian Chemist Warehouse store list derived from OSM, built for this project's pharmacy-retail narrative (see `docs/data_readiness.md`).

`stock_code` and `product_id` are different, unrelated identifier spaces — there is no real key linking a UCI sales line to a row in `dim_product`, and no key linking it to a row in `dim_store` at all. Fabricating a join between them (e.g. a hash-based or arbitrary assignment) would misrepresent the data in a project whose whole premise is governed, auditable analytics — worse than not joining at all.

**What this phase does instead:**

- `dim_store` and `dim_product` are built as correct, standalone, fully-tested dimensions from their own seeds — ready for the synthetic, store/product-keyed operational fact tables (inventory, stockout, supplier delivery, promotion) planned for a later phase, per the project roadmap.
- `fct_sales_daily` and `fct_returns` are built from the real UCI data at `(date_day, country)` grain — `country` is the finest location-like dimension UCI actually has. They join to `dim_date` (a real, valid relationship for any date-grained fact) and nothing else.
- `int_product_sales_summary` aggregates by UCI's own `stock_code`, explicitly not `dim_product.product_id`. `int_store_sales_summary` aggregates by `country`, explicitly not `dim_store.store_id`. Both say so in their header comments.

This isn't a limitation to route around quietly — a future phase that generates synthetic sales/inventory data explicitly keyed to `store_id`/`product_id`/`date` (as the project roadmap already anticipates) is the correct way to get store- and product-scoped fact tables, not a fake join here.

## Layout

```text
models/
  staging/       -- typed, renamed 1:1 passthroughs of RAW (views)
  intermediate/  -- reusable aggregation logic, not exposed to consumers (tables)
  marts/         -- dimensional/semantic consumption layer (tables)
tests/           -- singular reconciliation tests
macros/          -- generate_schema_name override (see below)
```

Every model directory maps to the identically-named Snowflake schema (`STAGING`, `INTERMEDIATE`, `MARTS` — already created in `infra/snowflake/03_database_schemas.sql`) via the `generate_schema_name` macro override in `macros/get_custom_schema.sql`, which ignores dbt's default `<profile_schema>_<custom_schema>` concatenation.

## Running dbt

`SVC_PHARMARETAIL_DBT` has no `CREATE SCHEMA` grant (ADR-003), so there is no isolated per-environment schema today: PR, deployment and scheduled runs all target the same physical `STAGING`/`INTERMEDIATE`/`MARTS` schemas. This is safe right now because every model here is a deterministic transformation of `RAW` (nothing manually curated lives in these schemas) and nothing outside this phase consumes them yet.

This project runs on **dbt-core via GitHub Actions**, not dbt Cloud SaaS — creating a dbt Cloud account requires a human to sign up, connect the repository and generate an API token, none of which an agent can do. Everything else — the dbt project itself (100% portable to real dbt Cloud later, since dbt Cloud runs the same project), PR/deployment/scheduled automation, docs and lineage — is delivered via `.github/workflows/dbt-*.yml`.

```bash
cd dbt/pharma_retail
dbt deps
DBT_QUERY_TAG=PHARMARETAIL_DBT_PR dbt build       # PR job
DBT_QUERY_TAG=PHARMARETAIL_DBT_DEPLOY dbt build   # deployment job (on merge)
DBT_QUERY_TAG=PHARMARETAIL_DBT_SCHEDULED dbt build   # scheduled job
dbt docs generate
```

There is a single dbt profile target (`default`); `DBT_QUERY_TAG` only labels the run for Snowflake's query history — it does not change where models land, since all three GitHub Environments currently resolve to the same schemas (see above). All required `SNOWFLAKE_*` environment variables are documented in the GitHub Actions workflows and `docs/snowflake_setup.md`.
