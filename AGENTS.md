# ResolveFlow AI development instructions

- Read `README.md`, `docs/ARCHITECTURE.md`, `docs/PROJECT_PLAN.md`, and
  `docs/PROJECT_STATUS.md` before changing the project.
- Work only on the step explicitly authorized by the user. Step 1 covers
  initialization and documentation only. Stop at its completion; a later user
  instruction can authorize the next step without changing this file first.
- During Step 1, do not install dependencies, scaffold applications, create
  database tables, configure credentials, deploy, purchase services, or create
  custom Codex agent TOML files. Modify files only inside this repository.
- Preserve the requested stack: Next.js/TypeScript/Tailwind/shadcn/ui; Python/
  FastAPI; PostgreSQL/pgvector; LangGraph; scikit-learn/sentence-transformers;
  Redis/Python workers; Pytest/Vitest/Playwright.
- The requested primary development agent is GPT-6 Astra. Document this
  preference without claiming that repository instructions select the active
  model. Do not create agent configuration or delegate unnecessarily.
- Keep local development possible without paid services. Use deterministic
  provider fixtures for routine tests; real Gemini inference is opt-in, bounded,
  and free-tier only. Do not introduce paid APIs, paid hosting, or billing.
  External deployment or service activation requires explicit user approval.
- Start application inference with `gemini-3.6-flash`. Keep model selection
  configurable and provider SDK types behind adapters. Do not silently substitute
  another model. Keep embeddings separate from response generation.
- Implement genuine LangGraph state transitions, durable checkpoints, and human
  approval in the appropriate future phase. Never send a generated response
  without authorized human approval of that exact draft revision.
- Use typed interfaces, focused modules, validated inputs, explicit error
  handling, migrations, reproducible lockfiles, and environment-based settings.
  Keep domain logic independent of hosting and provider SDKs.
- Enforce tenant authorization server-side, including retrieval, worker jobs,
  graph checkpoints, and analytics. Treat documents and model output as
  untrusted. Never commit secrets or real customer data.
- Preserve existing user changes. Prefer small, reviewable changes; avoid
  speculative infrastructure and new services.
- Verify behavior with checks appropriate to the change. Future code needs
  focused unit/integration tests and end-to-end coverage of critical journeys.
  Never claim unrun tests passed or planned controls are implemented.
- Update `docs/PROJECT_STATUS.md` after each authorized step with evidence,
  remaining prerequisites, and blockers. Keep plans distinct from shipped work.
