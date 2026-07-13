# Phase 6 — Stockout Investigation Agent

A deterministic, governed agent that answers questions such as *"Why did
stockouts increase for pain relief in Melbourne over the last 14 days?"* using
only approved data and returning a fully-cited, structured JSON result. It is a
backend/agent workflow only — no UI is introduced in this phase.

## Design principles

| Principle | How it is enforced |
| --- | --- |
| No free SQL | The agent can only call the seven allowlisted tools. `SnowflakeGateway` runs a fixed set of constant statements with bind parameters; there is no code path that interpolates a user value into SQL. |
| Allowlisted tools only | `orchestrator.INVESTIGATION_PLAN` is validated against `ALLOWLISTED_TOOLS` at construction, and `AllowlistToolset.resolve` refuses any other name. |
| Role / store / region access | `AgentContext.store_is_visible` mirrors the Snowflake `OPERATIONAL_STORE_REGION_POLICY` row-access policy and `USER_STORE_SCOPE` / `USER_REGION_SCOPE` tables. Every data tool filters rows before computing any metric. |
| Citation required | Every `Finding` carries at least one `Citation` (governed mart or SOP). `InvestigationResult.citation_coverage()` reports the covered share. |
| Human approval before action | The agent never contacts an external system. `draft_action_plan` only produces `ActionDraft`s with `requires_human_approval = True` and `status = "DRAFT_PENDING_APPROVAL"`. |
| Append-only audit | `log_ai_interaction` writes immutable `AuditRecord`s. The Snowflake table grants `INSERT` only — never `UPDATE`/`DELETE`. |
| Prompt-injection defence | The free-text question is scanned with the Phase 5 `PROMPT_INJECTION_PATTERNS` before any data access; a match refuses the request. |
| Determinism | No randomness or wall-clock value enters the result. Identical inputs yield byte-for-byte identical `to_dict()` output; audit ids are deterministic hashes. |

## Allowlisted tools

| Tool | Reads | Purpose |
| --- | --- | --- |
| `get_stockout_metrics` | `MARTS.FCT_STOCKOUT_EVENT` | Current vs prior-window events, affected stores/SKUs, lost sales. |
| `get_inventory_position` | `MARTS.FCT_INVENTORY_SNAPSHOT` | Stores below the days-of-cover threshold, on-order units. |
| `get_supplier_performance` | `MARTS.FCT_SUPPLIER_DELIVERY` | OTIF decline per supplier (current vs prior). |
| `get_promotion_impact` | `MARTS.FCT_PROMOTION` | Expected vs actual uplift surprise. |
| `search_policy_docs` | Phase 5 `GovernedRetriever` | Cited SOP guidance with role-based access and refusal guardrails. |
| `draft_action_plan` | — | Produces draft replenishment/escalation actions (approval required). |
| `log_ai_interaction` | `AI_LOGS.AGENT_INTERACTION_AUDIT` | Appends one immutable audit row per step. |

## Components

- `scripts/stockout_agent/contracts.py` — immutable contracts and the access model.
- `scripts/stockout_agent/gateway.py` — `InMemoryGateway` (fixtures) and `SnowflakeGateway` (parameterised); `InMemoryAuditSink` and `SnowflakeAuditSink`.
- `scripts/stockout_agent/fixtures.py` — deterministic demonstration dataset.
- `scripts/stockout_agent/tools.py` — the seven allowlisted tools.
- `scripts/stockout_agent/orchestrator.py` — the fixed, controlled investigation plan.
- `scripts/run_stockout_investigation.py` — offline structured-JSON smoke entrypoint.
- `infra/snowflake/12_phase6_agent.sql` — append-only `AGENT_INTERACTION_AUDIT` and `AGENT_ACTION_DRAFT` tables plus grants.

## Snowflake objects

`infra/snowflake/12_phase6_agent.sql` (deployed through the existing ordered
`scripts/deploy_snowflake.py` path as `PHARMARETAIL_ADMIN`):

- `PHARMARETAIL_AI_CONTROL_TOWER.AI_LOGS.AGENT_INTERACTION_AUDIT` — append-only interaction log; `INSERT` granted to `PHARMARETAIL_AI_APP`, `SELECT` to admin/analyst reviewers.
- `PHARMARETAIL_AI_CONTROL_TOWER.AI_LOGS.AGENT_ACTION_DRAFT` — append-only action drafts, constrained to `REQUIRES_HUMAN_APPROVAL = TRUE` and `STATUS = 'DRAFT_PENDING_APPROVAL'`.

No new read surface is added: the agent reads only the Phase 4 marts already
granted to `PHARMARETAIL_AI_APP` in `phase4_model_grants.sql`.

## Tests

Run with `python -m pytest tests/test_stockout_agent.py tests/test_stockout_agent_security.py`:

- **Agent / orchestration** — full investigation shape, allowlist enforcement, JSON serialisation, honest empty answer when there is no signal.
- **RLS / leakage** — store-manager, area-manager, national and unassigned scopes; readonly denial; out-of-scope stores never appear in output.
- **Citation** — full coverage, data findings cite governed marts, actions carry a policy citation.
- **Prompt injection** — parametrised injection strings refuse before any tool runs, and the refusal is audited.
- **Determinism** — repeated runs produce identical results and identical audit ids; gateway statements use bind parameters only.

## Production wiring

The offline path uses `InMemoryGateway` + `InMemoryAuditSink`. Production swaps
in `SnowflakeGateway(connection)` and `SnowflakeAuditSink(connection)` using a
`PHARMARETAIL_AI_APP` connection; the orchestrator, tools, access model and
contracts are unchanged. Live execution against the real account happens through
the existing deploy/runbook path, not from local developer machines.
