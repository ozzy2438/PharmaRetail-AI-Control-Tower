# ADR-001: Snowflake foundation isolation and access model

- Status: Accepted
- Date: 2026-07-10

## Context

PharmaRetail AI Control Tower will evolve into a governed pharmacy-retail data and AI platform. Its Snowflake foundation must isolate project workloads, control cost, support dbt Cloud later, and expose only curated data to a future AI application. The existing `ABS_DATA` schema belongs to another scope and must not be changed or used.

## Decision

Create a dedicated `PHARMARETAIL_AI_CONTROL_TOWER` database with six managed-access schemas and a dedicated `WH_PHARMARETAIL` warehouse. Use `XSMALL` compute, 60-second auto-suspend, auto-resume and a monthly resource monitor. Implement independent least-privilege workload roles beneath `PHARMARETAIL_ADMIN`, which itself sits beneath `SYSADMIN`.

## Rationale

- A separate database provides an explicit security, ownership, lifecycle and cost boundary and eliminates accidental dependency on `ABS_DATA`.
- `XSMALL` is sufficient for foundation validation and early development while keeping idle and test cost low.
- Managed-access schemas centralise grant decisions with the schema owner rather than individual object creators.
- Independent ENGINEER, DBT, AI_APP and READONLY roles prevent privilege coupling between human engineering, transformation service, runtime application and consumption workloads.
- ACCOUNTADMIN is restricted to initial account-level bootstrap and resource-monitor operations; daily work uses project roles.

## Consequences

Future scripts must explicitly grant new object types and future privileges. AI_APP cannot query raw or modelling schemas. READONLY cannot access anything outside MARTS. DBT cannot create objects in RAW, GOVERNANCE or AI_LOGS. Query tags must be set by every deployment, dbt Cloud job and AI application connection.

## Future integrations

dbt Cloud will use `PHARMARETAIL_DBT` with separate development, staging and production environments and schema targets. The AI runtime will use `PHARMARETAIL_AI_APP`, read only approved MARTS and GOVERNANCE objects, and write only controlled AI_LOGS records. Neither integration token is stored in this repository; GitHub Environment or service-specific secret stores will provide credentials.
