# Recruiter walkthrough — three minutes

Use [the public demo](https://resolveflow-ai-rosy.vercel.app/demo). All records and
workflow results are synthetic. No account, backend or API key is needed. This script
targets **3:00**, including navigation; use **Show all stages** rather than waiting for
animation. A longer technical discussion can follow the demonstration.

| Time | Show | Say |
| --- | --- | --- |
| 0:00–0:25 | Overview | “ResolveFlow AI combines support-ticket classification, semantic retrieval, Gemini-powered RAG and human review. I built the local full application; this public demo uses synthetic records and authored workflow examples, with live AI disabled.” |
| 0:25–0:50 | **Ticket inbox** → a ticket | “The product organizes requests, assignments and internal notes. In the full backend these operations use authenticated, tenant-scoped PostgreSQL records. Edits here stay in this browser tab.” |
| 0:50–1:25 | **AI workflows** → **A grounded refund response** → **Show all stages** | “This is a replay, not a model call. The full LangGraph graph coordinates classification, priority, retrieval, context, generation, verification and approval. Classification uses trained logistic regression; priority uses rules; only generation may call Gemini.” |
| 1:25–2:05 | **Inspect source [refund-1]**; return to the workflow; read the draft and review acknowledgment | “The full system embeds documents and queries locally, retrieves authorized pgvector chunks and checks generated quotes against those sources. Similarity and valid citations do not prove correctness. A person reviews this exact draft. Approval records an internal decision; it does not issue a refund or send a message.” |
| 2:05–2:30 | **Analytics** → **Under the hood** | “These charts summarize synthetic records and local edits, not AI accuracy. The architecture separates the public Next.js demo from the real FastAPI, PostgreSQL, ML and worker runtime.” |
| 2:30–3:00 | Remain on **Under the hood** | “The full backend commits accepted work to a PostgreSQL outbox before Valkey/RQ delivery. LangGraph checkpoints preserve progress and review pauses; stable draft identities constrain duplicates. Authorization is checked again after slow work. Local recovery is tested; external email, off-host recovery and commercial operations remain unfinished.” |

For the review interaction, advance to the final stage, read the evidence and check
**I reviewed this exact example draft and its sources.** Then optionally choose
**Approve example**, **Request revision** or **Reject example**. These affect only
synthetic tab-local records. Local ticket edits do not regenerate the authored draft.

## One-minute introduction without screen sharing

“ResolveFlow AI is my AI/ML engineering portfolio project for evidence-based support
triage and response review. The full application combines scikit-learn classification,
Sentence Transformers and pgvector retrieval, structured Gemini generation, and a
seven-stage LangGraph workflow. I also built the FastAPI APIs, Next.js interface,
tenant authorization and durable RQ background processing. The key challenge was
preserving evidence, exact-draft approval and safe recovery across interruptions.
Evaluation uses explicitly synthetic datasets, not customer accuracy claims. You can
explore the hosted demo without credentials; it replays examples while the full AI
and database stack runs locally.”

## Optional technical follow-up

Use the [case study](AI_ENGINEERING_CASE_STUDY.md),
[architecture diagram](SYSTEM_ARCHITECTURE_OVERVIEW.md),
[evidence](PORTFOLIO_EVIDENCE.md) and [interview guide](TECHNICAL_INTERVIEW_GUIDE.md).
Discuss the classifier's grouped split and low suggestion coverage, or trace an
interrupted job. Do not present old test counts as a newly executed demonstration.

The repository is private: a source link does not grant recruiter access. Share
materials only through separately authorized access. A real local workflow demonstration
should use the existing isolated harness with fixture generation, not casually enable
Gemini. **Reset demo** clears only the current tab's demo records. Step 23 changes
no hosted files and makes no adoption, business-impact or production-uptime claims.
