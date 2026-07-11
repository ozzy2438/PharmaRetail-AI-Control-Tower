# Phase 3 security closure gate

Phase 4 must not be declared complete until every live item below is evidenced.

## Incident record

- Postmortem/incident: GitHub issue #17, “Rotate SVC_PHARMARETAIL_DBT key:
  private key leaked in public CI logs”.
- Root cause: the decoded PEM was written to `$GITHUB_ENV`; GitHub masked the
  stored base64 secret but not the decoded multiline value.
- Corrective action: all three protected Environment secrets were replaced,
  Snowflake's `RSA_PUBLIC_KEY` was rotated in PR #18, and the workflow was
  changed to decode and use the key inside one shell step only.
- The affected workflow run `29143718966` now returns GitHub API 404, confirming
  its logs were removed.

## Non-secret key fingerprints

- Retired dbt public key: `SHA256:ebk0nSNvIjRPLpLlpAkWjbUWVssyQiVzk+T1KpgsLoY=`
- Expected active dbt public key: `SHA256:LL6crTqYxltfSP/w572ZpNs9ij3wbh5mySlcCk7fmp8=`

The Phase 4 bootstrap evidence must show the active fingerprint on
`SVC_PHARMARETAIL_DBT` and no retired secondary key. Because the private key is
never exported from the protected secret store, invalidation is proved by the
Snowflake-side public-key replacement plus a successful connection with the
new key; the retired private key can no longer satisfy authentication.

Development bootstrap run `29154521116` successfully reapplied the active key,
created the security evidence record, and left no secondary RSA key configured.

## Secret absence checks

- Full git-history pattern scan contains no PEM private-key block.
- `dbt-run.yml` contract test rejects executable `$GITHUB_ENV` usage.
- PR CI runs gitleaks and GitGuardian.
- The active private key value cannot and must not be printed for comparison;
  absence is established through secret scanners and log pattern scans.

## dbt Cloud statement

dbt Cloud SaaS was not used. The implemented stack is dbt-core + GitHub Actions
with PR, deploy and scheduled jobs plus dbt docs/lineage artifacts. A future
human-created dbt Cloud account remains an explicit known limitation, not an
implied implementation.
