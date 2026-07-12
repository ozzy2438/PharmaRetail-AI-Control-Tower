# Governed SOP RAG architecture

## Scope

Phase 5 provides deterministic, source-backed SOP retrieval. It does not call an
LLM, implement an agent, expose an API or UI, or execute an operational action.
The answer composer is extractive so a response cannot introduce policy text
that was absent from an authorised effective chunk.

```text
versioned Markdown SOPs
        |
        v
metadata validation -> section chunking -> 64-d hashed lexical embedding
        |                                      |
        +------------------+-------------------+
                           v
Snowflake GOVERNANCE
  DOCUMENT_REGISTRY / DOCUMENT_CHUNKS / EMBEDDING_METADATA
                           |
role + country + business unit + effective-date filters
                           |
prompt/medical guardrails -> lexical ranker -> extractive answer + citations
                           |
                           v
                 RETRIEVAL_AUDIT
```

## Chunk and embedding contract

Each Markdown `## [SECTION-ID]` block becomes exactly one chunk. Chunk IDs and
content hashes are SHA-256 derived from document ID, version, section ID and
normalised text. The embedding baseline is a dependency-free 64-dimensional
signed feature-hashing vector named `DETERMINISTIC_HASHED_LEXICAL_V1`.

This baseline is deliberately local and reproducible. It proves metadata,
filtering, citation, audit and evaluation controls without introducing a hosted
embedding service, API secret, model drift or new dataset. It is not represented
as a Snowflake Cortex or neural semantic embedding.

## Retrieval sequence

1. Reject prompt-injection patterns before retrieval.
2. Route medical-advice requests to the medical boundary refusal.
3. Convert the actor role to allowed access levels.
4. Filter by country, optional business unit/document IDs and as-of date.
5. Rank only eligible chunks using IDF-weighted lexical overlap.
6. Refuse when no eligible chunk reaches the relevance threshold.
7. Compose an extractive answer from the highest-ranked sections.
8. Emit title, version, section and effective date for every citation.
9. Return `LOW`, `MEDIUM` or `HIGH` uncertainty plus a numeric score.
10. Persist non-sensitive retrieval evidence to the controlled audit table.

Runtime requests default the as-of date to the current date. Evaluation and
reconciliation always pass `2026-07-01` explicitly so regression results remain
deterministic. Country, business-unit and document-ID filter values are
normalised to uppercase before matching.

## Snowflake objects

| Object | Purpose |
|---|---|
| `DOCUMENT_REGISTRY` | Version, effective window, ownership and source registry |
| `DOCUMENT_CHUNKS` | Section text, replicated filters, hashes and embedding payload |
| `EMBEDDING_METADATA` | Model/version/dimension/provider lineage per chunk |
| `RAG_ROLE_ACCESS_SCOPE` | Governed role-to-access-level mapping |
| `RETRIEVAL_AUDIT` | Append-only retrieval/refusal/citation evidence |

The corpus and registry are additive to the existing schemas. No RAW, dbt or
Phase 4 model is rebuilt or repurposed.
