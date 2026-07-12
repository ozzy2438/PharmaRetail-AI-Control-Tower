# Governed SOP RAG security

## Access control

The retrieval layer maps Snowflake roles to `PUBLIC`, `INTERNAL` and
`RESTRICTED` access levels. Filtering occurs before scoring, so an unauthorised
chunk cannot influence ranking, uncertainty or answer text.

| Role | Allowed document levels |
|---|---|
| ADMIN, AI_APP, SUPPLY_CHAIN_ANALYST | PUBLIC, INTERNAL, RESTRICTED |
| AREA_MANAGER, STORE_MANAGER | PUBLIC, INTERNAL |
| READONLY | PUBLIC |

Country, business-unit, document-ID and effective-date filters are combined with
the role filter. Unknown roles receive no document access.

## Guardrails

- Medical diagnosis, dosing, treatment, contraindication, medicine selection,
  patient suitability and emergency analysis are refused with the effective
  Medical Advice Boundary Policy citation where available.
- Attempts to reveal prompts, bypass access, assume an administrator identity,
  disable citations or execute code/SQL are refused before retrieval.
- No eligible source produces `NO_AUTHORISED_SOURCE`, not a guessed answer.
- Non-refusal policy answers require citations containing title, version,
  section and effective date.
- Expired and not-yet-effective documents are filtered before ranking.

## Audit minimisation

`RETRIEVAL_AUDIT` stores a query hash rather than raw prompt text. It records
actor, role, metadata filters, retrieved chunk IDs, citation count, uncertainty,
refusal reason, outcome and latency. It must not store credentials, patient
details, prescription data or unnecessary personal information. AI_APP receives
`SELECT, INSERT` only; it receives no update or delete grant.

## Threat model and residual risks

- Regex prompt-injection detection is a deterministic baseline and will not
  identify every linguistic or encoded attack.
- AI_APP can read all governed chunks because it retrieves on behalf of multiple
  personas; caller-role binding must remain trusted and server-side in a future
  API.
- Primary and foreign keys on standard Snowflake tables are metadata controls;
  ingestion reconciliation remains required. CHECK and NOT NULL constraints are
  enforced.
- Hashed lexical embeddings can collide and have limited semantic recall.
- Source text is synthetic and requires legal, clinical, compliance and business
  owner approval before any real operational use.

No Agent, UI, API or autonomous action is introduced in Phase 5.
