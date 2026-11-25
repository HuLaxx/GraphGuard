# Project guide: a cited RAG assistant for this site

A floating "Ask GraphGuard" assistant that answers visitors' questions about GraphGuard, the sibling projects (FleetFlow, GraphGuard, Sentinance) and Rahul Khanke's skills, tools, experience and education. Every answer comes from a curated knowledge base and cites the documents it used.

The same implementation ships in all three repositories; only `src/lib/project-guide/config.ts` (project name, theme, suggested questions) differs.

## How it works

```
repo docs + profile ──sync-corpus──▶ project-guide/corpus/*.md
                                        │ build-index (heading-aware chunks, ~170 words, overlap)
                                        ▼
                     src/lib/project-guide/knowledge.generated.json   (committed, deterministic)
                                        │
 visitor ─▶ ProjectGuide widget ─▶ POST /api/project-guide ─▶ BM25 retrieval ─▶ top 6 passages
                                                              │                   │
                                              no confident match          LLM configured?
                                                    │                   yes │          │ no / error
                                             polite refusal        grounded answer   extractive answer
                                                                   with [n] citations  (quoted sentences)
```

- **Retrieval** (`src/lib/project-guide/core.ts`, zero dependencies): BM25 over chunk text, with title and heading terms boosted, light stemming, query expansion for synonyms ("tech stack", "k8s", "chatbot"), typo correction against the corpus vocabulary ("grapgh gua" → GraphGuard), project routing (questions naming a project favour that project; questions about Rahul go to the profile), and a two-chunks-per-document diversity cap.
- **Refusal**: a question is answered only when the corpus covers enough of its IDF-weighted terms, or it names a project, or it is clearly about Rahul. Otherwise the guide says it could not find the answer and suggests what it can answer, without calling a model.
- **Generation**: any OpenAI-compatible chat-completions endpoint. The system prompt restricts the model to the numbered passages, requires citations, preserves the docs' evidence boundaries (synthetic vs production, draft vs merged) and forbids presenting personal-project technology as employer experience. Citations to passages that were not supplied are stripped.
- **No key, no problem**: without an LLM key, or if the call fails or times out, the guide returns the most relevant sentences from the same passages, with citations, and labels the answer as quoted.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASSISTANT_LLM_API_KEY` or `GROQ_API_KEY` | unset (extractive mode) | API key for the chat-completions endpoint |
| `ASSISTANT_LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Any OpenAI-compatible base URL |
| `ASSISTANT_LLM_MODEL` | `openai/gpt-oss-120b` | Model name |
| `ASSISTANT_LLM_TIMEOUT_MS` | `12000` | Falls back to extractive answers after this |
| `ASSISTANT_LLM_DISABLED` | unset | Set to `1` to force extractive mode |

Set the key in the Vercel project's environment variables; nothing else is needed. `GET /api/project-guide` reports the index size and whether an LLM is configured.

The route also applies a best-effort, per-instance limit of 20 questions per minute per client, caps questions at 600 characters and sanitises chat history (user/assistant turns only, last 6, 1,500 characters each).

## Updating the knowledge base

```bash
# from this frontend folder, with FleetFlow, GraphGuard and Sentinance cloned side by side
node project-guide/scripts/sync-corpus.ts --root ../..      # copy the docs listed in project-guide/sources.json
node project-guide/scripts/build-index.ts                    # rebuild knowledge.generated.json
node project-guide/scripts/eval.ts                           # check retrieval quality
```

`project-guide/sources.json` lists the documents per project. Evidence-backed docs are included; aspirational specs and plans are left out so the guide does not present plans as shipped work. Hand-written files live in `project-guide/corpus/profile/` (about Rahul) and `project-guide/corpus/curated/` (one "at a glance" page per project). Requires Node 22.18 or newer (native TypeScript).

## Tests and measured retrieval quality

```bash
node --test project-guide/tests/core.check.ts                # 21 unit tests
node project-guide/scripts/build-index.ts --check            # committed index is current
node project-guide/scripts/eval.ts --min-hit5 0.9            # retrieval gate used in CI
```

`project-guide/eval/golden.json` holds a development set (47 answerable, 3 off-topic questions) used while tuning and a holdout set (25 answerable, 7 off-topic) written after the first tuning pass. One generic rule (treating known synonyms as understood when scoring coverage) changed after the holdout was first run. A case passes when any chunk from an expected document is in the top k.

Measured on 26 November 2026, Node 22, Linux x64, 614 chunks from 72 documents, home project GraphGuard:

| Set | hit@1 | hit@3 | hit@5 | MRR@10 | Off-topic refused | False refusals |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Development | 91.5% | 97.9% | 97.9% | 0.947 | 100% (3/3) | 0% |
| Holdout | 88.0% | 96.0% | 96.0% | 0.907 | 71.4% (5/7) | 0% |

Retrieval latency over 4,100 in-process searches: p50 0.12 ms, p95 0.48 ms, p99 0.65 ms. Index build at cold start: about 56 ms. These are retrieval-only numbers on a small, self-written question set; they do not measure LLM answer quality or end-to-end HTTP latency.

Known gaps: lexical retrieval cannot reject off-topic questions that reuse corpus words ("write python code to reverse a string", "best pizza in Glasgow"); in LLM mode the system prompt makes the model decline these, in extractive mode they return loosely related quotes. Dense retrieval (for example Qdrant, as Sentinance's own RAG evaluation uses) would improve paraphrase matching at the cost of an embedding dependency.

CI: `.github/workflows/project-guide.yml` runs the unit tests, index freshness check, retrieval gate (hit@5 at least 90%, refusal at least 60%, false refusals at most 5%) and a type-check, plus a Chromium end-to-end job against the real route handler (`e2e/project-guide.spec.ts`).
