# Snowflake foundation setup

## Connection method

Foundation automation uses the Python Snowflake Connector. All connection values are read from process environment variables. Base variables are always required:

- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_ROLE`
- `SNOWFLAKE_WAREHOUSE`
- `SNOWFLAKE_DATABASE`

Exactly one authentication path must also be provided:

- **Key-pair (BAU/service identity)**: `SNOWFLAKE_PRIVATE_KEY` (PEM text, optionally encrypted) and, if encrypted, `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`. This is the only path used by the `SVC_PHARMARETAIL_CICD` service identity; see [Identities](#identities) below. In CI, the GitHub Environment secret `SNOWFLAKE_SERVICE_PRIVATE_KEY` stores the PEM **base64-encoded** (a single line) because GitHub Actions log masking is not reliable for multi-line secrets; the workflow decodes it into `SNOWFLAKE_PRIVATE_KEY` without ever echoing the decoded value.
- **Password (bootstrap human identity only)**: `SNOWFLAKE_PASSWORD`. Reserved for the manual, ACCOUNTADMIN-only bootstrap path run by a human operator.

Secrets must come from a local ignored `.env` assignment loaded by a safe parser, or from a protected GitHub Environment secret. Never execute `source .env`, print environment contents, or pass a password/private key as a command-line argument. The bootstrap connection omits warehouse and database parameters until those objects exist.

## Identities

Three distinct Snowflake identities are used, and none is a substitute for any other:

| Identity | Type | Auth | Role | Used for |
|---|---|---|---|---|
| `OMRUM` | Human | Password | `ACCOUNTADMIN`, `PHARMARETAIL_ADMIN` | Manual, human-approved `bootstrap` deployment mode only |
| `SVC_PHARMARETAIL_CICD` | `TYPE = SERVICE` | RSA key-pair | `PHARMARETAIL_ADMIN` | Automated `bau` deployment mode (push-triggered `development`, dispatched `staging`/`production`) |
| `SVC_PHARMARETAIL_DBT` | `TYPE = SERVICE` | RSA key-pair | `PHARMARETAIL_DBT` | dbt jobs only (PR, deployment, scheduled transformation runs) |

`SVC_PHARMARETAIL_CICD` and `SVC_PHARMARETAIL_DBT` cannot authenticate interactively or with a password; `TYPE = SERVICE` disallows both. `SVC_PHARMARETAIL_CICD` holds the same `PHARMARETAIL_ADMIN` role BAU deployments already used. `SVC_PHARMARETAIL_DBT` holds only `PHARMARETAIL_DBT` — it cannot deploy foundation SQL, write to RAW, or touch GOVERNANCE/AI_LOGS. dbt jobs never use `OMRUM` or `SVC_PHARMARETAIL_CICD`. See `infra/snowflake/07_service_identity.sql`, `infra/snowflake/09_dbt_service_identity.sql`, [ADR-002](adr/ADR-002-service-identity.md) and [ADR-003](adr/ADR-003-dbt-service-identity.md).

The human `OMRUM` credential remains password-based because it is also the account's `ACCOUNTADMIN` bootstrap path, and rotating it to key-pair/SSO is out of scope for this change. This is a documented, accepted residual risk, not a blocker — see the runbook's [Credential rotation](snowflake_runbook.md#credential-rotation) section.

## Script order

Run scripts in numeric order with `ACCOUNTADMIN` only for the bootstrap operations that require it:

1. `01_roles.sql`
2. `02_warehouse.sql`
3. `03_database_schemas.sql`
4. `04_grants.sql`
5. `05_resource_monitor.sql`
6. `06_validation.sql`
7. `07_service_identity.sql`
8. `08_raw_tables.sql`
9. `09_dbt_service_identity.sql`

`scripts/deploy_snowflake.py` discovers only numeric scripts and excludes `rollback.sql`. It sets a deployment query tag and stops on the first error. Rollback is intentionally manual. BAU mode (see the runbook) executes `04_grants.sql`, `06_validation.sql` and `08_raw_tables.sql`; `07_service_identity.sql` and `09_dbt_service_identity.sql` run only in the manual `bootstrap` mode, like the other ACCOUNTADMIN-only scripts, since `CREATE USER` requires account-level authority.

## Foundation objects

- Database: `PHARMARETAIL_AI_CONTROL_TOWER`
- Warehouse: `WH_PHARMARETAIL` (`XSMALL`, 60-second auto-suspend, auto-resume)
- Resource monitor: `RM_PHARMARETAIL_MONTHLY`
- Schemas: `RAW`, `STAGING`, `INTERMEDIATE`, `MARTS`, `GOVERNANCE`, `AI_LOGS`
- Roles: `PHARMARETAIL_ADMIN`, `PHARMARETAIL_ENGINEER`, `PHARMARETAIL_DBT`, `PHARMARETAIL_AI_APP`, `PHARMARETAIL_READONLY`
- Service identities: `SVC_PHARMARETAIL_CICD` (`TYPE = SERVICE`, key-pair auth, `PHARMARETAIL_ADMIN` role), `SVC_PHARMARETAIL_DBT` (`TYPE = SERVICE`, key-pair auth, `PHARMARETAIL_DBT` role)

All six project schemas use managed access. The default `PUBLIC` schema is removed from the dedicated database. `ABS_DATA` is never referenced.

## Validation queries

`06_validation.sql` reports current context, warehouse configuration, database schemas, role grants, future grants, resource-monitor configuration and smoke-test outcomes. Validation sessions use explicit query tags.

SQLFluff 4.2 does not parse Snowflake's documented `RESOURCE MONITOR` grammar. `05_resource_monitor.sql` is therefore excluded from SQLFluff, protected by a focused SQL contract test, and syntax-validated through execution in the real Snowflake account. All other foundation SQL is linted and parsed by SQLFluff.

## Errors encountered and resolutions

- The repository initially had no base commit; a documented one-time baseline exception established `main` before PR enforcement.
- The connector's `execute_stream` API required a file-like input in the installed version. Deployment was corrected to use `execute_string` and covered by a regression test.
- A legacy local `.env` was not shell-compatible and was accidentally treated as a shell file. The credential was not committed; subsequent operations use an exact-key parser and never source `.env`.
- BAU deployments originally authenticated as the human bootstrap user with a shared password secret. `07_service_identity.sql` and the key-pair authentication path (ADR-002) removed that dependency for routine automation without touching existing roles, warehouse or schemas.

No secret value should appear in setup logs, PR comments, Actions logs or screenshots.
