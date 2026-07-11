# Changelog

## 0.6.0 - 2026-07-11

### Phase 4 operational data and governance

- Added six governed operational MARTS models and three reusable intermediate models using fixed dates and versioned deterministic hash seeds.
- Added all seven required root-cause scenarios, exact inventory equation/continuity, supplier OTIF, promotion, incident and stockout-island logic.
- Expanded dbt coverage from 96 to 147 tests and added live double-run fingerprint verification.
- Added store, area and national supply-chain personas; row access and masking policies; explicit AI_APP MARTS grants; append-only audit logging; query tags; leakage and future-grant validation.
- Added Phase 3 security-closure evidence and explicitly retained dbt Cloud SaaS as a known limitation.

## 0.5.0 - 2026-07-11

### dbt transformation pipeline

- Added a dbt-core project (`dbt/pharma_retail/`) transforming `RAW` into `STAGING` (5 models) → `INTERMEDIATE` (4 models) → `MARTS` (5 models: `dim_store`, `dim_product`, `dim_date`, `fct_sales_daily`, `fct_returns`), authenticating only as `SVC_PHARMARETAIL_DBT`.
- `fct_sales_daily`/`fct_returns` are built from the real UCI dataset and join `dim_date` (a real relationship); they deliberately do not join `dim_store`/`dim_product`, which come from an unrelated synthetic seed with no shared key — documented in `dbt/pharma_retail/README.md` rather than papered over with a fabricated join.
- Generic tests (unique/not_null/relationships/accepted_values), custom positivity tests (quantity/price via `dbt_utils.expression_is_true`), source freshness, and singular row-count/revenue reconciliation tests between `RAW` and `MARTS`.
- Three GitHub Actions workflows (PR job, deployment job, scheduled job) share one reusable workflow; results are posted as PR comments and always written to the job step summary; `dbt docs`/lineage and run artifacts are uploaded on every run.
- Runs on dbt-core via GitHub Actions, not dbt Cloud SaaS — that requires a human to create an account, connect the repo and generate an API token. `docs/snowflake_runbook.md` documents both what was actually built and the manual steps for connecting real dbt Cloud later, if wanted.
- No existing role, grant, warehouse, database, schema or RAW table was modified.

## 0.4.0 - 2026-07-11

### dbt service identity

- Added a dedicated `SVC_PHARMARETAIL_DBT` service identity (`TYPE = SERVICE`, RSA key-pair authentication) scoped to the existing `PHARMARETAIL_DBT` role only — no ADMIN, no ACCOUNTADMIN.
- dbt jobs never use the human bootstrap user or the foundation CI/CD identity; all three identities are independent (ADR-003).
- No existing role, grant, warehouse, database, schema or RAW table was modified.

## 0.3.0 - 2026-07-11

### Data ingestion

- Added RAW landing tables (`08_raw_tables.sql`) for the five existing processed/quarantine datasets plus a `RAW.LOAD_AUDIT` audit table, deployed via the existing BAU pipeline under `PHARMARETAIL_ADMIN`.
- Added a contract-driven loader (`scripts/load_raw_data.py`) that is idempotent (truncate-and-reload), records row counts/null summaries/duplicate counts/file checksums/status for every run, and generates a source-to-target reconciliation report.
- Added `contracts/uci_returns.yml` and `contracts/uci_invalid_price.yml` to match the existing contract pattern, and corrected `contracts/dim_store.yml`'s `postcode` to `nullable: true` to match the documented seed data.
- Added a cross-check test verifying `08_raw_tables.sql` columns never drift from their contracts.
- Added a new, separately-dispatched `Snowflake Data Load` workflow reusing the Phase 1 service identity; no new Snowflake identity was introduced.
- No dataset was downloaded; only already-processed local files were loaded.

## 0.2.0 - 2026-07-10

### Service identity and connection hardening

- Added a dedicated `SVC_PHARMARETAIL_CICD` service identity (`TYPE = SERVICE`, RSA key-pair authentication) scoped to the existing `PHARMARETAIL_ADMIN` role, with no new privilege grants.
- Routed BAU deployments (push-triggered `development`, dispatched `staging`/`production`) through the service identity; the manual, `ACCOUNTADMIN`-only `bootstrap` mode continues to use the human `OMRUM` credential.
- Extended Snowflake connection configuration and deployment tooling to support key-pair authentication alongside the existing password path, with unit test coverage for both.
- Documented the identity model (ADR-002), updated the security matrix, setup guide and credential-rotation runbook, and recorded the human bootstrap password as an accepted, documented residual risk.

## 0.1.0 - 2026-07-10

### Snowflake foundation

- Established PR-based GitHub governance, CI gates, protected environments and production approval.
- Added environment-only Snowflake connection and controlled deployment automation.
- Created five least-privilege project roles and validated their hierarchy.
- Provisioned an isolated database, six managed-access schemas and an XSMALL warehouse.
- Added a 20-credit monthly resource monitor with notification and suspension triggers.
- Added current/future grants, automated allow/deny smoke tests, manual rollback guidance, security matrix, ADR and BAU runbook.
- Documented the planned dbt Cloud Jobs integration without creating dbt models.
