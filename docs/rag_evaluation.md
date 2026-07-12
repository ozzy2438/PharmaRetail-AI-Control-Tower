# Phase 5 RAG evaluation

## Dataset

The committed regression set contains 36 cases:

- 10 policy questions
- 8 mixed operational-data + policy questions
- 5 prompt-injection attacks
- 4 access-control cases
- 6 medical-advice requests
- 2 expired-policy cases
- 1 no-source/country case

## Metrics and local result

| Metric | Definition | Target | Result |
|---|---|---:|---:|
| Citation coverage | Citation-bearing required cases / all citation-required cases | 100% | 100% |
| Retrieval relevance hit rate | Cases where an expected document appears in top 3 / labelled retrieval cases | >=90% | 100% |
| Unauthorized leakage | Retrieved chunks above the actor's access level | 0 | 0 |
| Expired document usage | Retrieved chunks outside their effective window | 0 | 0 |
| Medical refusal accuracy | Correct medical-boundary refusals / medical cases | >=95% | 100% |
| Prompt-injection refusal | Correct injection refusals / injection cases | 100% | 100% |
| Access-control accuracy | Correct access outcome / access cases | 100% | 100% |
| Overall regression pass | Fully passing cases / all cases | 100% | 100% (36/36) |

Run locally or in CI:

```bash
python -m scripts.run_rag_evaluation --output rag_evaluation_report.json
```

The JSON artifact contains per-case retrieved document IDs, citations, refusal
reason, uncertainty and latency. CI fails when any required target is missed.

## Interpretation limitation

Relevance is labelled document hit-rate on a small synthetic corpus, not an
estimate of production semantic-search quality. The 100% result demonstrates a
stable regression contract for these 36 cases. A future neural embedding or
reranker must be compared against this baseline on a larger blinded set before
replacement.
