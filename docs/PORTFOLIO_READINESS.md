# Portfolio readiness — Step 16

Reviewed 2026-10-23 (Asia/Kolkata). **Ready for a reviewed Git commit and a separately
approved redeployment.** Changes are local; nothing was committed, pushed or deployed.
The live URL https://resolveflow-ai-rosy.vercel.app/demo still serves `be7efbc`.
Step 15D hosted evidence remains historical evidence for that exact commit.

## What the portfolio demonstrates

| Area | Implemented full application | Hosted recruiter demonstration |
| --- | --- | --- |
| Full-stack | Typed Next.js UI, FastAPI routes, PostgreSQL migrations and tenant-scoped authorization | Standalone Next.js on Vercel Hobby; no login required |
| ML classification | Trained TF-IDF/logistic regression with abstention; separately evaluated synthetic corpus | Authored categories; no live classifier or confidence score |
| Retrieval/RAG | Local Sentence Transformer embeddings, pgvector retrieval, bounded context and validated citations | Five authored passages, keyword search and linked example citations |
| Generation | Provider-neutral Gemini adapter; one previously approved synthetic live test | Precomputed drafts; live inference disabled, no API key required |
| Orchestration | Seven-stage LangGraph with durable PostgreSQL checkpoints and exact-revision approval | Bounded replay of authored stages, not a real graph/model execution |
| Background processing | PostgreSQL outbox, RQ/Valkey workers, bounded recovery/cancellation | No worker, queue, database or delivery action |
| Security | Server-side tenancy, session/CSRF checks and private documents | Isolated fixtures, validated tab-local journal, real API blocked |
| Analytics | Authorized workspace aggregates and diagnostics | Calculated fixture/local-edit metrics; no invented model performance |

The full backend is implemented and locally tested in earlier steps, **not deployed
on Vercel**. Step 16 makes no new backend reliability or model-quality claim.

## First-minute presentation review

The landing page already offers a clear support-operations value proposition and
**Explore Live Demo** entry. Preserve that design. The demo overview now explicitly
names ticket triage, citation-backed drafts and human review, and suggests starting
with a workflow before inspecting architecture. The synthetic/precomputed notice
remains visible throughout. No credentials, setup or technical instructions block
entry. The architecture screen explains ML, RAG, LangGraph, durable workers and
tenant boundaries without suggesting those services run in this demonstration.

Suggested recruiter walkthrough:

1. Open the demo and choose **Explore a workflow**.
2. Inspect the evidence citation, show/replay stages, review the exact example draft.
3. Record a local decision; inspect tickets/search and analytics; reset if desired.
4. Open **Under the hood** to discuss full-stack architecture and deployment scope.

This is an editorial review, not a measured recruiter comprehension/usability study.
Keep the public demo link prominent in a portfolio. Describe it as an interactive
synthetic demonstration of the implemented local application. Do not advertise
live inference, commercial availability, production accuracy or customer delivery.

## Targeted improvements

- Demo text links, navigation, buttons and disclosure summaries have 44px minimum
  target dimensions; landing header links also get 44px targets. Card links retain
  their full-card hit area. The labeled review checkbox is 24px within a 44px row.
- Keyboard skip link now targets a programmatically focusable content section.
  Textareas, disclosure summaries and focusable regions have explicit focus styles.
- Ticket table retains every column. Added visible scroll/keyboard instructions,
  a named focusable region with associated description, column scopes and stable
  scrollbar space. Arrow-key scrolling works; no sticky elements added.
- Demo analytics switches to one column below 1000px to avoid cramped tablet charts.
- Architecture copy and README/demo documentation now distinguish the deployed
  standalone demo from the local full stack. Step 14 architecture claims are dated
  as historical; hosted verification keeps its original deployed-commit findings.
- Existing state/data contracts, provider interfaces, authentication, workers and
  backend configuration remain unchanged. No dependency was added or upgraded.

## Actual local checks

| Check | Result |
| --- | --- |
| Demo production build, Node 24.22.1 | Passed, webpack production output |
| TypeScript | Passed (`next typegen` and `tsc --noEmit`) |
| ESLint | Passed, zero warnings |
| Ruff lint | Passed |
| Ruff format | Passed, 118 files already formatted |
| Demo suite | **15 passed**, zero retries (13 existing checks plus two new scenarios) |
| Keyboard | Tab reaches skip link after hydration; Enter focuses content; table focus outline and ArrowRight scrolling pass |
| Target dimensions/layout | Six demo views at 1440/768/390/320px: visible demo link/button/summary targets at least 44px, one h1, no document overflow |
| Contrast | Foreground/muted tokens on background/surface >=4.5:1 in light and dark |
| axe-core | Five critical pages in both themes, zero WCAG 2 A/AA and 2.1 AA tagged violations |
| Existing behavior | Ticket edits/search/filter/create, persistence/reset, documents/citations, review safeguards, analytics, safe errors, links and API/live-generation rejection pass |
| Visual review | Local mobile tickets and tablet analytics screenshots inspected; target spacing, visible hint and wider charts preserved design |

The new tests initially exposed test-harness assumptions: Tab was sent before
client hydration, and the contrast parser did not expand optimized three-digit hex
colors. Both test issues were corrected without weakening assertions. Final suite
passed. axe-core was already installed and recorded in the existing lockfile via
lint dependencies; no package changes were needed.

Local screenshot evidence is ignored, not uploaded:
[mobile tickets](../.cache/verification/step16/mobile-tickets.png),
[tablet analytics](../.cache/verification/step16/tablet-analytics.png),
[desktop](../.cache/verification/step16/desktop.png),
[workflow](../.cache/verification/step16/mobile-workflow.png).
Only the owned temporary Next.js demo server was started/stopped; no backend services
were needed. No live Gemini request occurred. Tests explicitly reject enabling
public inference and verify the reserved route remains fail-closed.

## Accessibility and release limits

Automated checks and keyboard/visual inspection are scoped evidence, not a blanket
WCAG certification. No screen-reader audit, real iOS/Android/Safari hardware test,
zoom/high-contrast exhaustive test, user study or physical MacBook-off test was run.
The ticket table still scrolls horizontally on narrow screens, now with instructions.
Tablet charts are wider but the page is longer. Static main text-token contrast
checks do not establish every possible tooltip/disabled-state contrast combination.

Existing development-only lint dependency advisories, absent CSP, unverified exact
Hobby usage charges and finite free-hosting capacity remain as documented in Step
15D. No new audit of external advisories or account billing occurred in Step 16.
The full application was not rebuilt/retested end-to-end because its runtime logic
was unchanged; landing header CSS is shared, while other polish is scoped to demo.

## Files in this step and next gate

Application: `apps/web/src/app/globals.css`, demo `tickets.tsx`, `demo-app.tsx`,
`architecture.tsx`; verification: `apps/web/tests-demo/demo.spec.ts`.
Documentation: `README.md`, `docs/ARCHITECTURE.md`, `docs/RECRUITER_DEMO.md`,
`docs/PROJECT_STATUS.md`, `docs/HOSTED_DEMO_VERIFICATION.md`, this report.
Earlier uncommitted `docs/VERCEL_DEPLOYMENT.md` work is preserved.

Review these local changes together with the existing uncommitted Step 15C–15D
reports before staging. A later authorized commit/push may trigger Vercel through
Git integration; do not push until a deployment is approved. After an approved
redeployment, repeat hosted acceptance against the new commit. Stop after Step 16.

## Step 17A release security gate

Step 17A supersedes the earlier absent-CSP and uncommitted-release notes above.
The local release now includes an enforced production-demo baseline CSP and
**16 passing demo tests**, production build, TypeScript, ESLint and Ruff checks.
CSP preserves inline hydration/styles; strict nonce-based XSS protection remains
future work. Five development-only audit entries remain, runtime audit is clean,
and no compatible fix was identified. See [DEMO_SECURITY.md](DEMO_SECURITY.md).

Release identifier: **Step 17A, 2026-10-23**, commit subject
`chore: polish recruiter demo and harden release`, parent `be7efbc`.
Resolve its immutable Git hash after creation with:

```bash
git log -1 --format=%H --fixed-strings --grep='chore: polish recruiter demo and harden release'
```

A commit cannot embed its own resulting hash; the completion report records that
hash, and this documentation is part of the release commit. Ready for a separately
approved push/redeployment with the documented limitations. No push, Vercel change
or live Gemini request was performed in Step 17A.
