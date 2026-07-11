# Snowflake security matrix

The matrix reflects direct role privileges. Validation sessions explicitly run `USE SECONDARY ROLES NONE` so broader roles assigned to an administrator do not mask privilege leakage.

## Identities

| Identity | Type | Authentication | Roles granted | Permitted use |
|---|---|---|---|---|
| `OMRUM` | Human | Password | `ACCOUNTADMIN`, `PHARMARETAIL_ADMIN` | `bootstrap` deployment mode only (manual, approved change window) |
| `SVC_PHARMARETAIL_CICD` | `TYPE = SERVICE` | RSA key-pair | `PHARMARETAIL_ADMIN` | `bau` deployment mode only (automated foundation/RAW DDL) |
| `SVC_PHARMARETAIL_DBT` | `TYPE = SERVICE` | RSA key-pair | `PHARMARETAIL_DBT` | dbt jobs only (PR/deployment/scheduled transformation runs) |

`TYPE = SERVICE` users cannot authenticate with a password, complete MFA, or log in through the Snowflake UI; the key-pair is the only credential. `SVC_PHARMARETAIL_CICD` holds no `ACCOUNTADMIN` privilege and cannot run `01_roles.sql`, `02_warehouse.sql`, `03_database_schemas.sql`, `05_resource_monitor.sql`, `07_service_identity.sql` or `09_dbt_service_identity.sql`, all of which require `ACCOUNTADMIN` and stay on the human bootstrap path. `SVC_PHARMARETAIL_DBT` holds neither `ACCOUNTADMIN` nor `PHARMARETAIL_ADMIN`: it cannot deploy foundation SQL, cannot write to RAW, and cannot touch GOVERNANCE or AI_LOGS — its ceiling is exactly `PHARMARETAIL_DBT` (read RAW, read/write STAGING/INTERMEDIATE/MARTS). dbt jobs never use `OMRUM` or `SVC_PHARMARETAIL_CICD`. The residual risk of `OMRUM`'s password-based bootstrap credential is accepted and documented in [ADR-002](adr/ADR-002-service-identity.md); it is not eliminated by this change.

| Role | Warehouse | Database and schemas | Create | Read | Write | Explicitly denied/not granted |
|---|---|---|---|---|---|---|
| `PHARMARETAIL_ADMIN` | Owns and manages `WH_PHARMARETAIL` | Owns the database and all six managed-access schemas | All project objects | All project objects | All project objects | No privileges outside the dedicated project boundary are introduced |
| `PHARMARETAIL_ENGINEER` | USAGE, OPERATE, MONITOR | USAGE on database, RAW, STAGING, INTERMEDIATE, MARTS | Tables/views/sequences in modelling schemas; stages/file formats in RAW | Current and future tables/views in RAW through MARTS | DML on current and future tables in RAW through MARTS | GOVERNANCE and AI_LOGS |
| `PHARMARETAIL_DBT` | USAGE, MONITOR | USAGE on database and RAW through MARTS | Tables/views/sequences only in STAGING, INTERMEDIATE, MARTS | RAW plus all modelling schemas | DML only in STAGING, INTERMEDIATE, MARTS | Create in RAW; all GOVERNANCE and AI_LOGS access |
| `PHARMARETAIL_AI_APP` | USAGE | USAGE on database, MARTS, GOVERNANCE, AI_LOGS | None | Current/future MARTS and GOVERNANCE tables/views | INSERT only to current/future administrator-created AI_LOGS tables | RAW, STAGING, INTERMEDIATE; log-table creation, update, delete and truncate |
| `PHARMARETAIL_READONLY` | USAGE | USAGE on database and MARTS | None | Current/future MARTS tables/views | None | RAW, STAGING, INTERMEDIATE, GOVERNANCE and AI_LOGS |

## Role hierarchy

`PHARMARETAIL_ADMIN` inherits the four independent workload roles. It is granted beneath `SYSADMIN`. Workload roles do not inherit one another. `ACCOUNTADMIN` is reserved for bootstrap actions that require account-level authority, including initial role creation, warehouse/database creation and resource-monitor assignment.

## Future grants

Future table and view grants mirror the matrix so new objects do not silently lose required access. The validated grant counts are:

- ENGINEER: 24
- DBT: 20
- AI_APP: 5
- READONLY: 2

Managed-access schemas ensure object creators cannot bypass the central grant model.
