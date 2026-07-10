# Snowflake security matrix

The matrix reflects direct role privileges. Validation sessions explicitly run `USE SECONDARY ROLES NONE` so broader roles assigned to an administrator do not mask privilege leakage.

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
