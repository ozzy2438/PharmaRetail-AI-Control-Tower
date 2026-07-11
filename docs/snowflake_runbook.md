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

- `bau`: connects as the `SVC_PHARMARETAIL_CICD` service identity (key-pair auth, `PHARMARETAIL_ADMIN` role) and executes `04_grants.sql`, `06_validation.sql` and `08_raw_tables.sql`.
- `bootstrap`: connects as the human `OMRUM` identity (password auth) and manually executes all numeric foundation scripts, including `07_service_identity.sql` and `09_dbt_service_identity.sql`. It requires an approved change window and `ACCOUNTADMIN`; it is not a daily operating mode.

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
3. Replace `SNOWFLAKE_SERVICE_PRIVATE_KEY` (the PEM, **base64-encoded** as a single line — see [setup](snowflake_setup.md#connection-method)) and `SNOWFLAKE_SERVICE_PRIVATE_KEY_PASSPHRASE` independently in development, staging and production GitHub Environments.
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

### dbt service identity (`SVC_PHARMARETAIL_DBT`, key-pair, routine)

1. Generate a new RSA key pair locally; never generate it inside a shared or logged shell session.
2. Set the new public key with `ALTER USER SVC_PHARMARETAIL_DBT SET RSA_PUBLIC_KEY = '...'` (or `RSA_PUBLIC_KEY_2` for a zero-downtime rollover, then remove the old key after cutover) during an approved `bootstrap` change window.
3. Replace `SNOWFLAKE_DBT_PRIVATE_KEY` (base64-encoded, same reasoning as the CI/CD key) and `SNOWFLAKE_DBT_PRIVATE_KEY_PASSPHRASE` independently in development, staging and production GitHub Environments.
4. Do not place the new private key or passphrase in an issue, PR, Actions input, shell command argument or screenshot.
5. Run a tagged dbt job to confirm the new key works before removing the old one.
6. Unset the retired public key and attach value-free evidence to the issue.

This identity is scoped to `PHARMARETAIL_DBT` only (see [ADR-003](adr/ADR-003-dbt-service-identity.md)) and is never used for foundation deployment; `SVC_PHARMARETAIL_CICD` and `OMRUM` are never used for dbt jobs.

## Rollback

Rollback is manual because automatic destructive recovery could remove governed data or audit logs. Follow `infra/snowflake/rollback.sql` checkpoint by checkpoint only after data disposition and dependency review. Prefer reverting a grant or configuration change over full teardown. Never run the rollback script as part of a failure hook.

## BAU checklist

- Confirm the active role is `PHARMARETAIL_ADMIN` or a narrower workload role, never ACCOUNTADMIN.
- Confirm the query tag identifies the application/job and environment.
- Confirm warehouse size remains XSMALL and auto-suspend remains 60 seconds.
- Review resource-monitor usage and recent failures.
- Review role/future-grant drift before approving security changes.
- Run smoke tests after access-control or managed-schema changes.

## dbt jobs

The dbt project (`dbt/pharma_retail/`) runs on **dbt-core via GitHub Actions**, not dbt Cloud SaaS. Creating a dbt Cloud account requires a human to sign up, connect this repository and generate an API token — none of that can be done without a person at the keyboard. Everything else the original plan called for is delivered through dbt-core instead, which produces the identical dbt project (100% portable to real dbt Cloud later, since dbt Cloud runs the same project) with equivalent PR/deployment/scheduled automation:

| Job | Workflow | Trigger | GitHub Environment | Purpose |
|---|---|---|---|---|
| PR job | `dbt-ci.yml` | `pull_request` touching `dbt/**` | `development` | Full `dbt build` (models + tests) on the branch; posts results as a PR comment |
| Deployment job | `dbt-deploy.yml` | `push` to `main` touching `dbt/**`; `workflow_dispatch` for staging/production | `development` (push) or the chosen environment (dispatch) | Confirms `main` still builds cleanly after merge; manual promotion to staging/production |
| Scheduled job | `dbt-scheduled.yml` | daily cron (03:00 UTC) | `development` | Unattended periodic rebuild so MARTS stay fresh even without code changes |

All three call a shared reusable workflow (`dbt-run.yml`) so the actual `dbt build`/`dbt test`/`dbt docs generate`/artifact-upload logic exists in one place. Every job authenticates as `SVC_PHARMARETAIL_DBT` (key-pair auth, `PHARMARETAIL_DBT` role only — see ADR-003); none of them ever use `OMRUM` or `SVC_PHARMARETAIL_CICD`.

The scheduled job targets `development`, not `production`: the `production` GitHub Environment has a required-reviewer protection rule (established in the Snowflake foundation phase) that applies to every job referencing it regardless of trigger type, so a cron-triggered run against `production` would queue for manual approval every day instead of running unattended. Re-pointing it at `production` is a deliberate governance decision for a human to make, not something automation should do silently.

`PHARMARETAIL_DBT` has no `CREATE SCHEMA` grant, so there is no isolated per-environment schema today: PR, deployment and scheduled runs all target the same physical `STAGING`/`INTERMEDIATE`/`MARTS` schemas (see `dbt/pharma_retail/README.md` and ADR-003). This is safe today because every model is a deterministic transformation of `RAW`, with no manually-curated state and no downstream consumers yet.

Results and artifacts:

- `dbt_run_summary.md` (rendered from `run_results.json` by `scripts/summarize_dbt_results.py`) is posted as a PR comment on PR-triggered runs, and always written to the job's step summary regardless of trigger.
- `manifest.json`, `catalog.json`, `run_results.json` and the generated docs `index.html` are uploaded as a build artifact (`dbt-artifacts-<pr|deploy|scheduled>`) on every run, success or failure.

## Manual dbt Cloud setup (if wanted later)

Real dbt Cloud Jobs (its own scheduler and UI, distinct from the GitHub Actions automation above) require a human to:

1. Sign up at `https://cloud.getdbt.com` and create a project pointing at this repository.
2. Add a Snowflake connection using `SVC_PHARMARETAIL_DBT` (key-pair auth) — dbt Cloud needs the private key uploaded through its own UI; it cannot read GitHub Environment secrets.
3. Generate a Service Token (Account Settings → Service Tokens) with Job Admin access.
4. Add `DBT_CLOUD_API_TOKEN` as a GitHub Environment secret, and the account ID / job ID / environment ID as non-secret Environment variables, if GitHub Actions should trigger dbt Cloud jobs remotely instead of running dbt-core directly.
5. Configure PR, deployment and scheduled jobs in the dbt Cloud UI, mirroring the three jobs already running via GitHub Actions above.

None of this is required for the dbt project to work today — it already builds, tests, documents and runs on a schedule without it.
