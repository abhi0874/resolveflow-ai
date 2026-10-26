import Link from "next/link";

const stages = [
  ["Classification", "Traditional ML", "TF-IDF features and logistic regression suggest a category. Low scores and unknown vocabulary abstain; a person accepts the suggestion."],
  ["Priority analysis", "Deterministic rules", "Bounded phrase rules recommend urgency. This stage is not a second language model."],
  ["Knowledge retrieval", "Local embeddings + SQL", "Sentence Transformers embeds the query. pgvector ranks current, authorized passages using exact cosine search."],
  ["Context preparation", "Deterministic code", "Reload current sources, verify fingerprints and bound the evidence. Insufficient evidence is an explicit outcome."],
  ["Response generation", "Gemini through AIProvider", "The configurable Gemini 3.6 Flash adapter generates structured drafts. This is the only stage that may call Gemini; routine tests use fixtures."],
  ["Citation verification", "Validation + freshness checks", "Check schema, source identifiers and supporting quotations. Mechanical citation validity does not prove factual correctness."],
  ["Human approval", "Durable review interrupt", "Pause for review of the exact draft revision. Resume reads the saved decision and rechecks sources and current permissions. No customer message is sent."],
];
const ingestion = ["Private document upload", "Bounded text extraction", "Deterministic chunks", "Local Sentence Transformers", "PostgreSQL / pgvector"];

export function DemoArchitecture() {
  return <div className="engineering-study">
    <header className="demo-heading compact">
      <span className="eyebrow">ENGINEERING CASE STUDY</span>
      <h1>Under the hood</h1>
      <p>From a support request to an evidence-backed draft: classification, retrieval and durable human review in one application.</p>
      <p>Support teams need more than a fluent answer. ResolveFlow AI separates triage, policy evidence and approval so each decision can be inspected and interrupted work can be recovered.</p>
      <div className="ticket-actions"><Link className="action-button" href="/demo/workflows/billing">Explore a workflow</Link><Link className="subtle-button" href="/">Back to landing page</Link></div>
    </header>

    <div className="demo-detail-grid">
      <section className="workspace-card"><span className="eyebrow">PUBLIC VERCEL DEMO</span><h2>Self-contained Next.js</h2><p>You are exploring synthetic tickets and documents, precomputed drafts and authored workflow replay. Search uses browser keywords; edits and analytics use tab-local records.</p><p><strong>Live Gemini inference is disabled.</strong> No Python backend, PostgreSQL database, RQ worker or local ML model runs in this demonstration.</p></section>
      <section className="workspace-card"><span className="eyebrow">LOCALLY IMPLEMENTED FULL APPLICATION</span><h2>Durable support operations</h2><p>The full application implements real classification, semantic retrieval, Gemini RAG integration, persistent LangGraph execution and tenant-scoped storage. Routine tests run real local services with deterministic generation.</p><p>The complete Python backend is not currently hosted on Vercel. Local verification is not a claim of commercial production readiness.</p></section>
    </div>

    <section className="workspace-card" aria-labelledby="system-architecture">
      <span className="eyebrow">01 / SYSTEM DESIGN</span><h2 id="system-architecture">Architecture & execution boundaries</h2>
      <p>Next.js and TypeScript provide the interface. FastAPI and Python own authentication, workspace RBAC and domain operations. PostgreSQL stores tickets, documents, vectors, job records and checkpoints.</p>
      <figure className="engineering-diagram">
        <figcaption>Full application data flow — implemented locally</figcaption>
        <ol className="engineering-flow" aria-label="Background execution data flow">
          <li><strong>Next.js / TypeScript</strong><span>Same-origin interface</span></li>
          <li><strong>FastAPI</strong><span>Session, CSRF and tenant authorization</span></li>
          <li><strong>PostgreSQL outbox</strong><span>Persist accepted work before delivery</span></li>
          <li><strong>Valkey / Redis + RQ</strong><span>Dispatcher publishes job identifiers</span></li>
          <li><strong>Python job worker</strong><span>Runs the LangGraph orchestrator</span></li>
        </ol>
        <div className="engineering-storage"><strong>Persistent state: PostgreSQL / pgvector</strong><p>Business records and evidence • exact-draft reviews • durable job state • LangGraph checkpoints</p></div>
      </figure>
      <p>RQ workers are infrastructure processes. The seven stages below are specialized logical workers within graph execution, not seven independently deployed LLM agents. Checkpoints persist during execution and at review pauses, not only at the end.</p>
      <p>Authorization is checked inside services and workers, including retrieval and resume. The public demo is a separate Next.js runtime with no connection to this backend.</p>
    </section>

    <section className="workspace-card" aria-labelledby="workflow-design">
      <span className="eyebrow">02 / ORCHESTRATION</span><h2 id="workflow-design">Seven stages, explicit responsibilities</h2>
      <p>LangGraph expresses typed state transitions, conditional failure exits and a persistent human-review interrupt. It coordinates service calls; it does not autonomously choose arbitrary tools.</p>
      <ol className="engineering-stages">{stages.map(([title, kind, body], index) => <li key={title}><span className="eyebrow">{String(index + 1).padStart(2, "0")} / {kind}</span><h3>{title}</h3><p>{body}</p></li>)}</ol>
      <p>Failed or cancelled work exits safely. A saved approval is bound to the exact draft; changes to the ticket, evidence or permissions can invalidate resume. Revision requests require a deliberate new draft and review.</p>
    </section>

    <div className="demo-detail-grid">
      <section className="workspace-card"><span className="eyebrow">03 / TRADITIONAL ML</span><h2>A measurable classification baseline</h2><p>scikit-learn fits TF-IDF word features and logistic regression on training records only. Paired scenario phrasings stay together across the grouped train, validation and test split.</p><p>The selected immutable model is stored as validated data-only JSON. Scores are uncalibrated suggestions, not certainty. Low scores and zero-vocabulary inputs abstain; category acceptance remains a human action.</p><p>Traditional ML keeps this bounded seven-category task local and inspectable. A more complex model would need a measured benefit on representative data.</p></section>
      <section className="workspace-card"><span className="eyebrow">04 / RAG</span><h2>Evidence before generation</h2><ol className="engineering-ingestion" aria-label="Document ingestion pipeline">{ingestion.map(label => <li key={label}>{label}</li>)}</ol><p>A query is embedded in the same 384-dimensional MiniLM space, then exact cosine search filters by workspace and source freshness. Bounded context goes through AIProvider to Gemini; structured output and quoted passages are validated before human review.</p><p>Extraction and indexing are synchronous services. Similarity ranks evidence; it does not prove an answer. Missing evidence leads to abstention instead of an invented policy. Source checks reduce risk but cannot eliminate hallucinations.</p></section>
    </div>

    <section className="workspace-card"><span className="eyebrow">05 / ENGINEERING EVIDENCE</span><h2>Recorded results, with their limits</h2><p>These are dated engineering measurements from synthetic datasets and local tests. They are not live demo telemetry, customer accuracy, business impact or uptime figures.</p>
      <dl className="engineering-evidence">
        <div><dt>Classification · recorded October 19, 2026</dt><dd><strong>0.784580 macro F1</strong><p>baseline-v1: 280 synthetic examples, seven categories, grouped 168/56/56 split. Held-out accuracy: 44/56. At threshold 0.45, only 13/56 receive a suggestion; 43 abstain. Re-evaluation reproduced the saved result in Step 20.</p></dd></div>
        <div><dt>Retrieval · recorded October 20, 2026</dt><dd><strong>0.928571 Recall@5</strong><p>14 synthetic documents, 24 queries; metric covers 21 answerable queries. Three no-answer cases abstained. This small corpus does not establish real-world retrieval quality or scale.</p></dd></div>
        <div><dt>Local regression · October 25, 2026, Step 20</dt><dd><strong>317 backend · 29 full browser · 16 demo tests</strong><p>Recorded passing tests use real local PostgreSQL, models, workers and Mailpit with deterministic generation. Full and demo builds, TypeScript, ESLint and Ruff passed. These counts are historical, not tests performed by this page.</p></dd></div>
        <div><dt>Gemini transport · October 20, 2026</dt><dd><strong>One approved synthetic smoke request</strong><p>STOP finish reason; JSON, schema and citation checks passed. Zero retries, 1,024-token output cap and 25-second timeout. This verifies past transport compatibility, not broad answer quality or current availability.</p></dd></div>
      </dl>
      <p>The deterministic RAG evaluation also exposed a limitation: only 3 of 7 cited answers covered every required term. A mechanically valid citation can still accompany an incomplete answer.</p>
    </section>

    <div className="demo-scenario-grid">
      <article className="workspace-card"><h2>Recovery without blind retries</h2><p>A PostgreSQL outbox records accepted work before broker publication. A dispatcher reconciles it into RQ. Delivery identities, ownership locks and stable draft reservations constrain duplicate persistence. Transient job recovery has bounded attempts; Gemini requests use zero automatic retries.</p><p>Checkpoints preserve progress, but an ambiguous interrupted generation fails closed rather than automatically spending another provider call. Transport is at-least-once, not universally exactly-once. Local encrypted backups and isolated restores address a different failure: lost persistent data.</p></article>
      <article className="workspace-card"><h2>Security & operational visibility</h2><p>Argon2id passwords, hashed opaque sessions, CSRF checks and workspace permissions protect the API. Tenant predicates and composite relationships constrain records; workers reauthorize. Application isolation is not PostgreSQL row-level security.</p><p>Authorized SQL analytics report ticket, job and review outcomes with explicit denominators. Errors use safe categories, not private ticket bodies or hidden model reasoning. Human approval records internal completion; no customer delivery connector is implemented.</p></article>
    </div>

    <section className="workspace-card"><span className="eyebrow">06 / TRADEOFFS & NEXT GATES</span><h2>Honest boundaries</h2><p>PostgreSQL keeps relational evidence and vectors together; exact search favors simplicity over unmeasured large-corpus performance. Provider SDKs stay behind AIProvider, separate from embeddings. The public Next.js demo makes the interaction explorable without pretending to host the full backend.</p><p>Commercial operation still requires external SMTP and invitation delivery, independent key custody and off-host recovery, least-privilege infrastructure, supervision, quotas, retention and representative load/security/quality studies. Automatic backups remain intentionally inactive.</p><p>All public examples are synthetic. Do not enter private information. Browser-local changes can be reset; this is not an offline PWA. No customer adoption, revenue or production uptime is claimed.</p><div className="ticket-actions"><Link className="action-button" href="/demo/workflows/billing">Inspect the example draft</Link><Link className="subtle-button" href="/demo">Return to demo overview</Link></div></section>
  </div>;
}
