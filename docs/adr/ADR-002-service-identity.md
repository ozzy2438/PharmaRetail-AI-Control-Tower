# ADR-002: Dedicated service identity for BAU Snowflake automation

- Status: Accepted
- Date: 2026-07-10

## Context

ADR-001 established the Snowflake foundation and its least-privilege role hierarchy. BAU deployments (push-triggered `development`, and `bau`-mode `staging`/`production` dispatch) have authenticated as the human bootstrap user `OMRUM` with a password stored in a GitHub Environment secret. PR #8 recorded this explicitly as a remaining risk: automation and a human operator shared one credential and one identity. The `ACCOUNTADMIN`-only `bootstrap` mode also uses `OMRUM`, and that account-level access must remain human-gated; it is not being changed here.

## Decision

Create a dedicated Snowflake user, `SVC_PHARMARETAIL_CICD`, with `TYPE = SERVICE` and RSA key-pair authentication, granted only the existing `PHARMARETAIL_ADMIN` role. Route the `bau` deployment mode through this identity. Keep the `bootstrap` mode (`ACCOUNTADMIN`, all numeric scripts including `07_service_identity.sql` itself) on the human `OMRUM` password credential, since bootstrap already requires a human-approved change window and `ACCOUNTADMIN` should not be delegated to an automated identity.

## Rationale

- `TYPE = SERVICE` users cannot authenticate with a password, complete MFA, or sign in through the Snowflake UI, so the automation credential cannot be reused for interactive/human access and vice versa.
- Key-pair authentication removes the need for automation to hold a long-lived shared secret that is also a human's login credential; the private key is scoped, rotatable independently, and never doubles as anyone's personal password.
- Granting `SVC_PHARMARETAIL_CICD` only `PHARMARETAIL_ADMIN` (the same role BAU already used) keeps this a pure identity-separation change with no privilege expansion, consistent with ADR-001's least-privilege model.
- Leaving `bootstrap`/`ACCOUNTADMIN` on the human identity avoids granting the highest-privilege account role to an automated credential, and matches the existing runbook expectation that bootstrap requires manual approval.

## Consequences

- BAU deployments no longer depend on the human password secret; only `bootstrap` does.
- Two new GitHub Environment secrets (`SNOWFLAKE_SERVICE_PRIVATE_KEY`, `SNOWFLAKE_SERVICE_PRIVATE_KEY_PASSPHRASE`) and one new variable (`SNOWFLAKE_SERVICE_USER`) are introduced per environment; existing `SNOWFLAKE_USER`/`SNOWFLAKE_PASSWORD` are unchanged and now used only for `bootstrap`.
- Key rotation for the service identity follows the routine procedure in the runbook; it no longer requires rotating a credential a human also uses to sign in.
- **Accepted residual risk**: `OMRUM`'s password-based bootstrap credential still exists and is not eliminated by this decision. It is documented, not silently carried forward. Rotating it to key-pair or SSO-backed access, or otherwise reducing bootstrap's blast radius, is deferred to a future change and does not block this or subsequent phases.
- Future dbt Cloud and AI application integrations (planned in ADR-001) should use their own dedicated service credentials rather than reusing `SVC_PHARMARETAIL_CICD`, which is scoped specifically to foundation BAU deployment.
