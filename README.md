# PharmaRetail AI Control Tower

Production-style pharmacy-retail data and AI platform built around Snowflake,
dbt-core, governed operational data, and auditable delivery controls.

The current implementation covers the Snowflake foundation, reconciled RAW
ingestion, the dbt transformation pipeline, and the Phase 4 operational data
and governance layer used to investigate stockouts. RAG, agents, UI, API,
dashboard, SOP embedding, and model evaluation are deliberately not Phase 4.

## Implemented data flow

```text
RAW -> STAGING -> INTERMEDIATE -> MARTS
                                  |
                                  +-> deterministic inventory, delivery,
                                      stockout, promotion and incident facts
GOVERNANCE -> row access + masking + role scope
AI_LOGS    -> controlled append-only operational audit
```

The future Stockout Investigation Agent will consume only approved governed
MARTS models. It must not query RAW or ungoverned intermediate data.

## Phase 4 operational models

- `dim_supplier`
- `fct_inventory_snapshot`
- `fct_supplier_delivery`
- `fct_stockout_event`
- `fct_promotion`
- `fct_incident`

Generation uses committed store/product/date dimensions, a fixed 2026-01-01 to
2026-03-31 operating window, and versioned Snowflake hash seeds. No public
dataset, `random()`, current timestamp, or non-repeatable input is used.

See [Phase 4 operational data](docs/phase4_operational_data.md), the
[security matrix](docs/snowflake_security_matrix.md), and the
[Snowflake runbook](docs/snowflake_runbook.md).

## Important dbt limitation

This repository uses **dbt-core through GitHub Actions**, not dbt Cloud SaaS.
PR, deployment and scheduled jobs, docs, lineage and artifacts are implemented,
but no dbt Cloud account, environment, scheduler or API token exists. Do not
describe this project as using dbt Cloud SaaS.

## Delivery model

Every phase follows issue → feature branch → commit → push → PR → CI → review →
merge. Snowflake account-level bootstrap remains human-gated under `OMRUM`;
routine deployments use service identities with RSA key-pair authentication.

## Security note

The dbt service key exposed by an earlier public CI log was rotated and the
affected run was deleted. The workflow now decodes keys only inside a single
shell step and never writes decoded key material to `$GITHUB_ENV`. See the
[Phase 3 security closure](docs/phase3_security_closure.md).
