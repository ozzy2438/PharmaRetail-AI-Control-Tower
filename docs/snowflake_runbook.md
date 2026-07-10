# Snowflake foundation runbook

## Operating model

Built using a production-style team delivery workflow, including issues, feature branches, pull requests, CI gates and documented reviews.

The repository is currently maintained by one person. It must not be represented as delivery by an active multi-person team.

## Deployment

1. Create or link a GitHub issue.
2. Branch from protected `main`.
3. Make focused Conventional Commits.
4. Open a draft PR with security, cost, test and rollback sections.
5. Wait for SQL lint/parse, Python lint/tests, changed-file control, secret scanning, GitGuardian and the aggregate CI gate.
6. Add validation evidence and a documented review comment.
7. Mark ready and merge only when required checks pass.

The Snowflake Deploy workflow never runs on `pull_request`. A merge that changes Snowflake foundation paths deploys to the protected `development` GitHub Environment in `bau` mode. Staging and production promotions use `workflow_dispatch`. Production requires environment approval.

Deployment modes:

- `bau`: connects as the `SVC_PHARMARETAIL_CICD` service identity (key-pair auth, `PHARMARETAIL_ADMIN` role) and executes only `04_grants.sql` and `06_validation.sql`.
- `bootstrap`: connects as the human `OMRUM` identity (password auth) and manually executes all numeric foundation scripts, including `07_service_identity.sql`. It requires an approved change window and `ACCOUNTADMIN`; it is not a daily operating mode.

GitHub Environment variables provide account, role, warehouse and database identifiers, plus a per-mode user (`SNOWFLAKE_SERVICE_USER` for `bau`, `SNOWFLAKE_USER` for `bootstrap`). `SNOWFLAKE_SERVICE_PRIVATE_KEY`/`SNOWFLAKE_SERVICE_PRIVATE_KEY_PASSPHRASE` and `SNOWFLAKE_PASSWORD` exist only as Environment secrets. Logs mask the private key, passphrase and password before validation or deployment begins. See [Identities](snowflake_setup.md#identities) for which credential backs each mode.

## Validation

Run `06_validation.sql` for read-only inventory. Run `scripts/validate_snowflake_foundation.py` for structural checks and allow/deny smoke tests. The validator:

- verifies warehouse, schemas, roles, resource monitor and future grants;
- disables secondary roles during isolation tests;
- creates fixed-name temporary smoke fixtures;
- validates ENGINEER RAW creation;
- validates READONLY MARTS access and RAW denial;
- validates AI_APP curated reads, log inserts and RAW denial;
- validates DBT STAGING creation and RAW-create denial;
- removes all fixtures and suspends the warehouse in a `finally` cleanup path.

Never load local credentials by sourcing `.env`. A local launcher may parse only the exact `SNOWFLAKE_PASSWORD=` assignment into process memory; it must not print the value or pass it as a command-line argument.

## Incident response

1. Stop deployments and open an incident issue.
2. Suspend `WH_PHARMARETAIL` if cost, runaway-query or access risk is active.
3. Preserve query IDs, query tags, role/session context and GitHub run URLs without copying secrets.
4. Determine whether the issue is configuration drift, credential misuse, privilege leakage or warehouse consumption.
5. Revoke the narrowest affected grant or rotate the affected credential.
6. Re-run structural and negative-access validation.
7. Document cause, impact, corrective action and residual risk in the incident and PR.

## Resource-monitor alarm

`RM_PHARMARETAIL_MONTHLY` has a 20-credit monthly quota. It notifies at 50% and 75%, suspends after active statements complete at 90%, and suspends immediately at 100%.

On notification:

1. Confirm account-administrator notification preferences are enabled in Snowflake.
2. Inspect tagged queries for unexpected role, duration or frequency.
3. Suspend the warehouse manually if consumption is unexplained.
4. Do not increase quota without an approved issue describing cause, expected credits and expiry/review date.

## Credential rotation

### Service identity (`SVC_PHARMARETAIL_CICD`, key-pair, routine)

1. Generate a new RSA key pair locally; never generate it inside a shared or logged shell session.
2. Set the new public key with `ALTER USER SVC_PHARMARETAIL_CICD SET RSA_PUBLIC_KEY = '...'` (or `RSA_PUBLIC_KEY_2` for a zero-downtime rollover, then remove the old key after cutover) during an approved `bootstrap` change window.
3. Replace `SNOWFLAKE_SERVICE_PRIVATE_KEY` and `SNOWFLAKE_SERVICE_PRIVATE_KEY_PASSPHRASE` independently in development, staging and production GitHub Environments.
4. Do not place the new private key or passphrase in an issue, PR, Actions input, shell command argument or screenshot.
5. Run connection configuration validation, then a tagged `bau` connection test.
6. Unset the retired public key and attach value-free evidence to the issue.

### Human bootstrap identity (`OMRUM`, password, exceptional)

1. Rotate the Snowflake credential through the approved identity channel.
2. Replace `SNOWFLAKE_PASSWORD` independently in development, staging and production GitHub Environments.
3. Do not place the new value in an issue, PR, Actions input, shell command argument or screenshot.
4. Run connection configuration validation, then a tagged `bootstrap` connection test.
5. Revoke or expire the old credential and attach value-free evidence to the issue.

This path is reserved for the manual, ACCOUNTADMIN-gated `bootstrap` mode; routine BAU deployments no longer depend on it (see [ADR-002](adr/ADR-002-service-identity.md)).

## Rollback

Rollback is manual because automatic destructive recovery could remove governed data or audit logs. Follow `infra/snowflake/rollback.sql` checkpoint by checkpoint only after data disposition and dependency review. Prefer reverting a grant or configuration change over full teardown. Never run the rollback script as part of a failure hook.

## BAU checklist

- Confirm the active role is `PHARMARETAIL_ADMIN` or a narrower workload role, never ACCOUNTADMIN.
- Confirm the query tag identifies the application/job and environment.
- Confirm warehouse size remains XSMALL and auto-suspend remains 60 seconds.
- Review resource-monitor usage and recent failures.
- Review role/future-grant drift before approving security changes.
- Run smoke tests after access-control or managed-schema changes.

## dbt Cloud Jobs preparation

No dbt project or model is created in this foundation phase. The planned integration is:

| Environment | Snowflake role | dbt target pattern | Job purpose |
|---|---|---|---|
| Development | `PHARMARETAIL_DBT` | Developer-isolated schema suffixes | Interactive development only |
| Staging | `PHARMARETAIL_DBT` | Controlled staging target | Integration and deployment rehearsal |
| Production | `PHARMARETAIL_DBT` | STAGING/INTERMEDIATE/MARTS | Scheduled governed transformations |

Planned jobs:

- PR job: defer/state-aware build of changed models plus tests; no production mutation.
- Deployment job: merge-triggered staging build, then approved production promotion.
- Scheduled production job: freshness-sensitive source ingestion checks followed by build/test and artifacts.

GitHub Actions will call the dbt Cloud Administrative API using a `DBT_CLOUD_API_TOKEN` stored only in a protected GitHub Environment secret. Account ID, job ID and environment ID will be non-secret Environment variables. The trigger action will record only dbt Cloud run IDs and URLs, poll completion, and fail the GitHub job on a failed/cancelled dbt run. Token values and API authorization headers must never be logged.

Future automation insertion points:

- add a PR workflow job after the dbt project exists;
- add staging and production deployment jobs behind existing GitHub Environments;
- add scheduled production invocation with concurrency control;
- add dbt artifacts and test evidence to PR comments;
- keep Snowflake grants and dbt environment credentials independently reviewable.
