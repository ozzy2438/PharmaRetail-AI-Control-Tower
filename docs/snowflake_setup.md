# Snowflake foundation setup

## Connection method

Foundation automation uses the Python Snowflake Connector. All connection values are read from process environment variables:

- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_ROLE`
- `SNOWFLAKE_WAREHOUSE`
- `SNOWFLAKE_DATABASE`

Secrets must come from a local ignored `.env` assignment loaded by a safe parser, or from a protected GitHub Environment secret. Never execute `source .env`, print environment contents, or pass a password as a command-line argument. The bootstrap connection omits warehouse and database parameters until those objects exist.

## Script order

Run scripts in numeric order with `ACCOUNTADMIN` only for the bootstrap operations that require it:

1. `01_roles.sql`
2. `02_warehouse.sql`
3. `03_database_schemas.sql`
4. `04_grants.sql`
5. `05_resource_monitor.sql`
6. `06_validation.sql`

`scripts/deploy_snowflake.py` discovers only numeric scripts and excludes `rollback.sql`. It sets a deployment query tag and stops on the first error. Rollback is intentionally manual.

## Foundation objects

- Database: `PHARMARETAIL_AI_CONTROL_TOWER`
- Warehouse: `WH_PHARMARETAIL` (`XSMALL`, 60-second auto-suspend, auto-resume)
- Resource monitor: `RM_PHARMARETAIL_MONTHLY`
- Schemas: `RAW`, `STAGING`, `INTERMEDIATE`, `MARTS`, `GOVERNANCE`, `AI_LOGS`
- Roles: `PHARMARETAIL_ADMIN`, `PHARMARETAIL_ENGINEER`, `PHARMARETAIL_DBT`, `PHARMARETAIL_AI_APP`, `PHARMARETAIL_READONLY`

All six project schemas use managed access. The default `PUBLIC` schema is removed from the dedicated database. `ABS_DATA` is never referenced.

## Validation queries

`06_validation.sql` reports current context, warehouse configuration, database schemas, role grants, future grants, resource-monitor configuration and smoke-test outcomes. Validation sessions use explicit query tags.

SQLFluff 4.2 does not parse Snowflake's documented `RESOURCE MONITOR` grammar. `05_resource_monitor.sql` is therefore excluded from SQLFluff, protected by a focused SQL contract test, and syntax-validated through execution in the real Snowflake account. All other foundation SQL is linted and parsed by SQLFluff.

## Errors encountered and resolutions

- The repository initially had no base commit; a documented one-time baseline exception established `main` before PR enforcement.
- The connector's `execute_stream` API required a file-like input in the installed version. Deployment was corrected to use `execute_string` and covered by a regression test.
- A legacy local `.env` was not shell-compatible and was accidentally treated as a shell file. The credential was not committed; subsequent operations use an exact-key parser and never source `.env`.

No secret value should appear in setup logs, PR comments, Actions logs or screenshots.
