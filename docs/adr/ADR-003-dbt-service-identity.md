# ADR-003: Dedicated service identity for dbt transformations

- Status: Accepted
- Date: 2026-07-11

## Context

ADR-002 introduced `SVC_PHARMARETAIL_CICD`, bound to `PHARMARETAIL_ADMIN`, to separate foundation BAU deployment automation from the human bootstrap user. dbt transformation jobs (STAGING/INTERMEDIATE/MARTS modelling) are a distinct workload from foundation deployment: they need to read RAW and read/write STAGING/INTERMEDIATE/MARTS, and nothing else. Using `SVC_PHARMARETAIL_CICD` for dbt would give every dbt job `PHARMARETAIL_ADMIN` — full ownership of the database, all schemas and all grants — far beyond what a transformation job needs, and would couple two operationally independent workloads (foundation deployment, dbt modelling) to one credential.

## Decision

Create a third Snowflake user, `SVC_PHARMARETAIL_DBT`, with `TYPE = SERVICE` and RSA key-pair authentication, granted only the existing `PHARMARETAIL_DBT` role. dbt jobs (PR, deployment, scheduled) authenticate exclusively as this identity. Neither the human `OMRUM` nor `SVC_PHARMARETAIL_CICD` is used for dbt.

## Rationale

- `PHARMARETAIL_DBT` already has exactly the privilege dbt modelling needs (read RAW, create/read/write STAGING/INTERMEDIATE/MARTS, no RAW writes, no GOVERNANCE/AI_LOGS, no ACCOUNTADMIN) — see `docs/snowflake_security_matrix.md`. Binding a dedicated identity to it, rather than reusing `PHARMARETAIL_ADMIN`, keeps a dbt job compromise or misconfiguration contained to the modelling schemas it's supposed to touch.
- `TYPE = SERVICE` disallows password/MFA/interactive login, consistent with `SVC_PHARMARETAIL_CICD` and the same reasoning in ADR-002.
- Following the exact `07_service_identity.sql` pattern (bootstrap-only `CREATE USER`/`ALTER USER` reconcile, `ACCOUNTADMIN`-gated) keeps identity provisioning consistent and auditable across all three identities.
- Three independent identities (human bootstrap, foundation CI/CD, dbt) mean a credential rotation or incident on one workload never requires touching the other two.

## Consequences

- Three new GitHub Environment items per environment: `SNOWFLAKE_DBT_USER` (variable), `SNOWFLAKE_DBT_PRIVATE_KEY` and `SNOWFLAKE_DBT_PRIVATE_KEY_PASSPHRASE` (secrets, base64-encoded PEM per the existing multi-line-secret-masking rationale).
- No existing role, grant, warehouse, database, schema or RAW table is modified. `PHARMARETAIL_DBT`'s privilege boundary is unchanged; only its identity binding is new.
- dbt jobs cannot create schemas (no `CREATE SCHEMA` grant exists for `PHARMARETAIL_DBT`), so PR, deployment and scheduled dbt runs all target the same physical `STAGING`/`INTERMEDIATE`/`MARTS` schemas — there is no isolated per-environment dbt schema today. This is an accepted simplification while the project has a single maintainer and no downstream consumers of MARTS yet (RAG/agent/dashboard are explicitly out of scope until a later phase); revisit with a scoped `CREATE SCHEMA` grant increment and a `generate_schema_name` override if concurrent PR/production consumers ever coexist.
- Rotation follows the same routine (non-exceptional) procedure as `SVC_PHARMARETAIL_CICD`.
