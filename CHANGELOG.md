# Changelog

## Phase 6 — Draft persistence and live-smoke targeting

- Added append-only action-draft persistence: `DraftRecord`, `InMemoryDraftSink`
  and `SnowflakeDraftSink` INSERT approval-pending drafts into
  `AI_LOGS.AGENT_ACTION_DRAFT`; the orchestrator persists every produced draft.
- The live smoke now auto-targets the window in which stockouts actually occur
  (derived from the marts) so the findings/draft path is always exercised, and
  it verifies real draft persistence alongside audit writes.
- Added offline tests for draft persistence (append-only, approval-pending,
  unique ids; none persisted when there is no signal).

## Phase 6 — Live smoke (AI_APP key-pair identity)

- Added `infra/snowflake/13_ai_app_service_identity.sql`: a bootstrap-only,
  key-pair `SVC_PHARMARETAIL_AI_APP` service identity granted `PHARMARETAIL_AI_APP`
  only (MARTS SELECT + AI_LOGS INSERT, no UPDATE/DELETE, no ADMIN).
- Added `scripts/run_stockout_investigation_live.py`: a live smoke that runs the
  agent through `SnowflakeGateway`/`SnowflakeAuditSink` and asserts MARTS reads,
  audit writes, draft human-approval, INSERT-only enforcement (UPDATE/DELETE
  denied) and store-scope narrowing.
- Added the `Stockout Agent Live Smoke` workflow (`agent-live-smoke.yml`),
  environment-gated and key-pair only.
- Added `docs/phase6_live_smoke.md` operator runbook and removed the plaintext
  Snowflake password from the local `.env` template (rotation is an operator
  ACCOUNTADMIN action).

## Phase 6 — Stockout Investigation Agent

- Added a deterministic, allowlisted, citation-first Stockout Investigation Agent
  (`scripts/stockout_agent/`) with a fixed, controlled orchestration plan.
- Added exactly seven allowlisted tools (`get_stockout_metrics`,
  `get_inventory_position`, `get_supplier_performance`, `get_promotion_impact`,
  `search_policy_docs`, `draft_action_plan`, `log_ai_interaction`); no free-form
  SQL is possible and non-allowlisted tool names are refused.
- Enforced role/store/region access scope mirroring the Phase 4 row-access
  policy, mandatory citations on every finding, prompt-injection refusal reusing
  the Phase 5 patterns, and an append-only audit trail.
- The agent takes no external action: it only produces drafts that require human
  approval before any ticket is opened.
- Added `infra/snowflake/12_phase6_agent.sql` with append-only
  `AI_LOGS.AGENT_INTERACTION_AUDIT` and `AGENT_ACTION_DRAFT` tables (INSERT-only
  for `PHARMARETAIL_AI_APP`); no new read surface beyond the existing Phase 4
  mart grants.
- Added 27 agent/RLS/citation/prompt-injection/determinism tests, a dedicated
  `agent-ci.yml` workflow, an offline structured-JSON smoke entrypoint, and
  `docs/phase6_stockout_agent.md`.
- No UI, no new marts, and no changes to existing dbt models were made.

## Phase 5 — Governed SOP RAG

- Added eight versioned synthetic SOP/policy documents and 40 deterministic sections.
- Added governed document registry, chunks, embedding metadata, role scope and retrieval audit.
- Added metadata/effective-date/access filtering, citations, uncertainty and refusal guardrails.
- Added a 36-case CI RAG regression suite and security/evaluation documentation.
- No agent, UI, API, dashboard or autonomous action was added.

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
