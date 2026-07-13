# Phase 6 — Live smoke with the AI_APP key-pair identity

The live smoke runs the agent end-to-end against the real account as the
least-privilege `SVC_PHARMARETAIL_AI_APP` service identity (key-pair auth only,
never a password). The code is in `scripts/run_stockout_investigation_live.py`
and the `Stockout Agent Live Smoke` workflow. The steps below are the
**privileged, human-performed provisioning** — they require ACCOUNTADMIN and
handle key material, so they are done by an operator, not by CI or the agent.

## 1. Generate a key-pair (private key never leaves the operator / secret store)

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out ai_app_key.p8 -nocrypt
openssl rsa -in ai_app_key.p8 -pubout -out ai_app_key.pub
# The .pub contents (base64 body, no header/footer) are non-secret.
```

## 2. Register the identity (ACCOUNTADMIN bootstrap)

Paste the public-key body into `infra/snowflake/13_ai_app_service_identity.sql`
in place of `REPLACE_WITH_AI_APP_RSA_PUBLIC_KEY`, then deploy it through the
human-gated bootstrap path (`Snowflake Deploy` → `workflow_dispatch`,
`deployment_mode = bootstrap`). This creates `SVC_PHARMARETAIL_AI_APP` with
`PHARMARETAIL_AI_APP` only — SELECT on the approved MARTS and INSERT on the
`AI_LOGS` agent tables, no UPDATE/DELETE, no ADMIN.

## 3. Store secrets in the GitHub Environment

In the target Environment (e.g. `development`), set:

| Kind | Name | Value |
| --- | --- | --- |
| Variable | `SNOWFLAKE_ACCOUNT` | account identifier |
| Variable | `SNOWFLAKE_AI_APP_USER` | `SVC_PHARMARETAIL_AI_APP` |
| Variable | `SNOWFLAKE_AI_APP_ROLE` | `PHARMARETAIL_AI_APP` |
| Variable | `SNOWFLAKE_WAREHOUSE` | `WH_PHARMARETAIL` |
| Variable | `SNOWFLAKE_DATABASE` | `PHARMARETAIL_AI_CONTROL_TOWER` |
| Secret | `SNOWFLAKE_AI_APP_PRIVATE_KEY` | `base64 -w0 ai_app_key.p8` output |
| Secret | `SNOWFLAKE_AI_APP_PRIVATE_KEY_PASSPHRASE` | passphrase, if the key is encrypted |

```bash
gh secret set SNOWFLAKE_AI_APP_PRIVATE_KEY --env development < <(base64 -w0 ai_app_key.p8)
```

## 4. Run the live smoke

`Actions` → `Stockout Agent Live Smoke` → `Run workflow`, choosing the
Environment. It connects as the AI_APP identity, auto-discovers a
`(region, category)` with stockouts, runs the investigation through
`SnowflakeGateway` / `SnowflakeAuditSink`, and asserts:

- `reads_marts` — governed MARTS are readable,
- `writes_audit` — append-only audit rows are written,
- `draft_requires_approval` — every action is a draft pending human approval,
- `update_denied` / `delete_denied` — the app role cannot mutate the audit table,
- `scope_narrows_no_leakage` — store scope narrows the result set.

The report is uploaded as `agent-live-smoke-report`.

## 5. Rotate and remove the plaintext bootstrap password

The old human bootstrap password must not remain in plaintext:

```sql
USE ROLE ACCOUNTADMIN;
ALTER USER OMRUM SET PASSWORD = '<new-strong-password>' MUST_CHANGE_PASSWORD = TRUE;
```

Then remove the value from any local `.env` (the repo's `.env` no longer
contains it) and prefer key-pair auth for all automation. Rotating the account
password is an ACCOUNTADMIN action performed by the operator; it is not done by
the agent or CI.
