# Recruiter walkthrough — three to five minutes

Use [ResolveFlow AI's public demo](https://resolveflow-ai-rosy.vercel.app/demo).
All people, tickets, policies and workflow outputs shown there are synthetic.
This walkthrough needs no account, API key or local backend. Do not enter private data.

## 0:00–0:35 — explain the problem and scope

“ResolveFlow AI helps a support team triage tickets, find policy evidence and review
a response before approving it. This hosted demo uses authored examples and browser-local
state. The separate local application implements the real Python, ML and workflow stack.”

Open the overview and choose **Explore a workflow**. Establish the scope before
playing the stages; animations are not evidence that a model is executing.

## 0:35–1:40 — evidence before the answer

Inspect the ticket, linked source passage and draft. Follow a citation into the
knowledge view, then return to the workflow.

“In the full application, a local Sentence Transformer embeds the query and pgvector
ranks actual chunks inside the user's workspace. RAG bounds the evidence sent to the
configured Gemini adapter. The response must satisfy a structured schema and quote
supplied chunks. Here you are viewing fixed passages and a precomputed draft; demo
search is keyword-based. A valid quote does not prove the whole answer is correct.”

## 1:40–2:40 — coordination and human review

Replay the seven stages and inspect the immutable example draft. Complete the review
acknowledgment and record an example approval, rejection or revision request.

“The full graph uses genuine LangGraph transitions. Classification calls a trained
TF-IDF/logistic-regression model; priority uses rules. Retrieval, context, generation,
verification and human approval reuse existing services. PostgreSQL stores checkpoints
at a real review pause. Resume checks the saved decision against the exact draft and
current sources and permissions. Approval records internal completion; it sends nothing.”

Do not describe this click as a live graph execution or crash-recovery test. Revision
requests do not edit the existing draft; a new draft needs a new review.

## 2:40–3:30 — product workflow and reliability

Open tickets, filter or edit a synthetic ticket, then inspect analytics. Explain that
the demo calculates analytics from its local records; it is not a model-quality dashboard.

“The full backend accepts work into a PostgreSQL outbox before a dispatcher publishes
UUID messages to Valkey/RQ. Workers resume checkpointed work and reuse stable draft
identities. Tests cover broker loss and interrupted workers. This is at-least-once
processing with application idempotency, not an exactly-once guarantee.”

## 3:30–4:30 — architecture and evidence

Open **Under the hood**. Show [the architecture diagram](SYSTEM_ARCHITECTURE_OVERVIEW.md)
and [portfolio evidence](PORTFOLIO_EVIDENCE.md) if the reviewer has local documents or
separately authorized source access.

“The local implementation uses Next.js, FastAPI, PostgreSQL/pgvector, scikit-learn,
Sentence Transformers, LangGraph and RQ. Fresh tests exercise actual local services;
only generation is deterministic in routine end-to-end tests. One historical bounded
Gemini smoke call verified structured communication. No live model is needed for this demo.”

For a five-minute version, explain grouped synthetic train/test separation and the
classifier's low suggestion coverage. Mention external production email, independent
backups, production hosting and representative quality testing as remaining work.
Do not substitute synthetic metrics for customer outcomes or production readiness.

## Optional technical follow-up, separate from this public walkthrough

Offer the [case study](AI_ENGINEERING_CASE_STUDY.md) and
[interview guide](TECHNICAL_INTERVIEW_GUIDE.md). The GitHub repository is private;
a link alone does not grant access. Do not change visibility or grant access without
separate authorization. A local real-workflow demonstration should use the existing
isolated browser harness with fixture generation, never enable Gemini casually.

The demo's **Reset demo** clears only its own tab-local data. Current deployment
identity is historical Step 17B evidence; Step 20 does not redeploy or verify a new
public release. No adoption, revenue, latency improvement or uptime claim is made.
