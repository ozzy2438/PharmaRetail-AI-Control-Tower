# Changelog

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
