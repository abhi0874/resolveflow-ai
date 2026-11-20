# ResolveFlow AI | Resume, portfolio and interview copy

[Public GitHub repository](https://github.com/abhi0874/resolveflow-ai) · [Live recruiter demo](https://resolveflow-ai-showcase.vercel.app/)

## Best three resume bullets for AI/ML engineering

- Built an experimental seven-class scikit-learn classifier that scored 87.14% accuracy and 0.8701 macro-F1 against baseline scores of 67.62% and 0.6585 on the same 210 synthetic tickets, using word TF-IDF, MiniLM embeddings and logistic regression. The candidate remains inactive. [Paired model evaluation](evaluation/PUBLIC_EVIDENCE.md#classifier-evaluation)
- Retrieved a relevant policy at rank one for 19/21 answerable synthetic queries versus 11/21 with keyword TF-IDF, using 384-dimensional MiniLM embeddings and workspace-scoped cosine search in PostgreSQL/pgvector. [Retrieval benchmark](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/docs/evaluation/retrieval-v1.json)
- Built a seven-stage LangGraph workflow with PostgreSQL checkpoints and RQ/Valkey workers, verifying in isolated tests that it resumed after a broker restart with the same approved draft and recovered from a worker interruption with one persisted draft. [Recovery tests](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/apps/api/tests/test_jobs.py) · [Recorded verification summary](evaluation/PUBLIC_EVIDENCE.md#recorded-workflow-backup-and-release-checks)

## Six alternative accomplishments by role

Choose bullets suited to the job. The nine candidates include the three above. Remove evidence links when space is tight.

- **ML evaluation:** Identified a generalization gap in a frozen classifier, from 41/42 correct on short synthetic requests to 193/265 on a stress set, by evaluating grouped variants with typos, competing intents and missing context. [Two synthetic evaluations](evaluation/PUBLIC_EVIDENCE.md#research-and-timing-context)
- **Applied ML:** Measured 113 correct category suggestions out of 118 at 56.19% coverage on a 210-ticket synthetic challenge by evaluating the inactive hybrid classifier with its fixed 0.45 score threshold. [Suggestion evaluation](evaluation/PUBLIC_EVIDENCE.md#classifier-evaluation)
- **Generative AI:** Found that only 3/7 citation-valid drafts contained every required term by scoring term coverage separately from retrieval hits and quote validity in a deterministic RAG benchmark. [Per-case results](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/docs/evaluation/rag-v1.json)
- **Generative AI:** Verified 7/7 citation-valid drafts on answerable synthetic cases and 5/5 expected abstentions by running a deterministic fixture generator with real MiniLM/pgvector retrieval and validating draft quotations against source passages. [RAG evaluation](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/docs/evaluation/rag-v1.json) · [Review implementation](https://github.com/abhi0874/resolveflow-ai/blob/d2af3ec4ab99cba381ef30e91c2274284733f8ab/apps/api/src/resolveflow/rag/service.py)
- **Backend:** Verified an encrypted local recovery path against 24 table fingerprints by restoring a PostgreSQL snapshot from a copied restic repository into an isolated database and checking schema revision and data integrity. [Recorded verification summary](evaluation/PUBLIC_EVIDENCE.md#recorded-workflow-backup-and-release-checks)
- **Full stack:** Shipped a Next.js recruiter demo verified across 23 hosted browser/API scenarios by building responsive ticket, citation and human-review flows over synthetic browser-local data. [Release suite](https://github.com/abhi0874/resolveflow-ai/tree/d2af3ec4ab99cba381ef30e91c2274284733f8ab/apps/web/tests-demo) · [Demo](https://resolveflow-ai-showcase.vercel.app/)

## One-line description

ResolveFlow AI is a support workspace that classifies tickets, retrieves policy evidence and routes grounded drafts to a human reviewer, with a public synthetic demo of the workflow.

## Three-line description

Built a Python/FastAPI support application with scikit-learn ticket classification and MiniLM semantic search over private workspace documents in pgvector.\
Connected a Gemini RAG adapter to a PostgreSQL-checkpointed LangGraph workflow so reviewers can trace a proposed answer to its sources.\
Published a responsive Next.js recruiter demo that replays synthetic examples without live AI calls.

## GitHub README overview

ResolveFlow AI helps a support agent answer three questions: What is the customer asking for? Which policy supports a reply? Who approved that wording? The local application combines a seven-class classifier, workspace-scoped vector retrieval and a Gemini generation adapter. LangGraph pauses for review, while PostgreSQL preserves the draft and its supporting evidence across worker restarts.

Try the refund scenario in the public showcase. Inspect its policy citation, replay the workflow and decide whether to approve the example. The showcase uses synthetic tickets and precomputed drafts. [Open the demo](https://resolveflow-ai-showcase.vercel.app/demo)

## LinkedIn project description

I built ResolveFlow AI to explore how a support team could use AI recommendations while keeping the evidence and the final decision visible. The local system combines Python, FastAPI, scikit-learn, MiniLM, pgvector, a Gemini RAG adapter and LangGraph. On the same 210 synthetic tickets, my inactive hybrid classifier candidate reached 87.14% accuracy versus 67.62% for the baseline. In a separate deterministic RAG evaluation, all seven answerable cases had valid citations and three contained every required term. The public demo lets you inspect sources and review a precomputed draft yourself. [Explore ResolveFlow AI](https://resolveflow-ai-showcase.vercel.app/)

## 30-second elevator pitch

I built ResolveFlow AI around a support agent reviewing a refund request. The local system classifies the ticket, finds the relevant policy and prepares a cited draft for a person to approve. I compared keyword and semantic retrieval on the same synthetic questions. MiniLM ranked the right policy first in 19 of 21 answerable cases, compared with 11 for keyword search. You can follow that decision from ticket to citation to approval in the public synthetic demo.

## Two-minute technical interview explanation

Imagine a customer asks whether a purchase qualifies for a refund. The agent needs a policy, but finding that policy doesn't tell us whether the customer's refund has been processed. I built ResolveFlow AI so the application keeps those questions separate.

In the local app, FastAPI checks the user's session and workspace permissions before reading the ticket. A scikit-learn classifier suggests one of seven categories from the title and description. The active baseline uses word TF-IDF and logistic regression. I also built a candidate that adds MiniLM embeddings. On the same 210 synthetic tickets it got 183 correct, compared with 142 for the baseline. It had more training examples as well, so I present that as a comparison of two complete models. I kept it inactive pending stronger evidence on unfamiliar inputs.

For the answer itself, I embed document passages locally and search authorized records in pgvector. The Gemini adapter receives bounded context and asks for a structured draft with quotations. I check that each quotation actually occurs in its cited chunk. In a 12-case deterministic benchmark, all seven answerable cases had valid citations and all five unsupported cases abstained. Only three answers contained every required term. That result changed how I explain grounding: checking a source is valuable, but completeness needs its own measurement.

The last design decision was what happens while a reviewer is away. LangGraph checkpoints the workflow in PostgreSQL. RQ and Valkey carry background work, and a database outbox preserves the work to be dispatched. When a reviewer returns, the application checks the exact draft and evidence before recording their decision. The public Next.js showcase replays that journey with synthetic examples so a recruiter can try it without credentials.

## Interview follow-ups

| Likely question | What to explain |
|---|---|
| Why use a classifier and a generator? | Category suggestion has seven known outputs, cheap local inference and measurable error. Drafting needs retrieved policy language, provenance and review. |
| How did you guard against leakage? | Group related scenarios before splitting, fit vocabulary and IDF only on training folds, freeze model and challenge before prediction, then report same-author synthetic limitations. |
| Why keep V1 active? | Accuracy among suggestions depends on coverage. The experimental V3 candidate achieved 72.83% on a harder synthetic stress set, and later scope-rejection gates failed. No independent customer benchmark justified promotion. |
| What does a citation guarantee? | A cited passage and exact quotation exist. A separately assessed claim could still omit a condition, misinterpret the policy or infer private account status. |
| Why keep job state in PostgreSQL? | A broker interruption can separate a committed workflow from a queue delivery. The outbox preserves dispatch intent. Checkpoints, bounded retries and stable draft identity support recovery. |
| What would you measure next? | Use independently reviewed tickets, measure unsupported suggestions as well as full accuracy, and evaluate claim correctness, completeness, abstention and latency under representative load. |

Figures are synthetic evaluation or historical test results. The [public evidence summary](evaluation/PUBLIC_EVIDENCE.md) contains the aggregates and identifies the local records used as sources. The public showcase runs precomputed examples. Commercial deployment, actual customer impact and general 95% accuracy remain unverified. [Master profile and sources](AI_PORTFOLIO_PROFILE.md)
