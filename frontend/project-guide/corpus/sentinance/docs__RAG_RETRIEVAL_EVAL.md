# RAG retrieval evaluation

**What is measured:** the production `RAGService` path (`add_news` → Qdrant upsert → `search`) on a fixed, labelled, **synthetic** corpus. The corpus has 36 crypto-news items written for this repo and 24 paraphrased queries with 27 relevant pairs. It deliberately includes near-misses: ETF inflows vs outflows, exchange hack vs outage, approval vs rejection.

**How:** CI job *RAG Retrieval Evaluation (Qdrant)* runs `apps/api/evals/rag_retrieval_eval.py` against a `qdrant/qdrant:v1.13.4` service container. It embeds with `BAAI/bge-small-en-v1.5` through FastEmbed, which needs no API key. Production uses Gemini embeddings, which CI can't call, so these scores describe this corpus and model, not production retrieval.

## Results (first measured run, 23 Nov 2026, GitHub Actions ubuntu-latest CPU)

| Metric | Dense (BGE-small + Qdrant) | BM25 keyword baseline |
| --- | --- | --- |
| Recall@1 | 0.917 | 0.625 |
| Recall@3 | 0.951 | 0.896 |
| Recall@5 | 0.979 | 0.896 |
| MRR@10 | 0.979 | 0.755 |
| Hit@1 | 0.958 | 0.625 |

- **Latency** (embed query + search): p50 8.7 ms, p95 13.5 ms.
- **The service's 0.65 relevance cut-off** discarded 0 of the 27 relevant hits in the top 5.

## Gate

CI fails if recall@5 < 0.90, MRR@10 < 0.90, or dense MRR is not above BM25.

## Limits

- The corpus is small and synthetic, and the queries were written by the same author as the documents.
- A Gemini-embedding run, and a larger corpus with independent query writers, would be the next steps.
