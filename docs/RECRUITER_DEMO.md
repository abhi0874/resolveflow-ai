# Recruiter demo — Step 13

The public `/demo` route presents a self-contained synthetic workspace. It requires
JavaScript and Next.js hosting, but no FastAPI, PostgreSQL, Redis/Valkey, Python
worker, embedding model or AI quota. The existing public demo is available at
https://resolveflow-ai-rosy.vercel.app/demo (deployed commit `be7efbc`).
Step 16 improvements are local pending reviewed commit/push and deployment approval.
See [PORTFOLIO_READINESS.md](PORTFOLIO_READINESS.md) for the current review.

## Launch locally

From the repository root, with the locked web dependencies installed:

```bash
npm --prefix apps/web run demo:build
npm --prefix apps/web run demo:start
```

Open http://127.0.0.1:3200/demo. For editing, use `npm --prefix apps/web run demo:dev`
instead of the production start command. These scripts explicitly set demo mode,
live AI disabled and telemetry disabled without editing any private environment file.
Node 24 LTS is the deployment target; Node 24.22.1 was checked locally. Existing
Node 26 development remains supported. Do not run two builds in the same web checkout
simultaneously: both modes use `.next`. Rebuild when changing modes.

## Architecture

`src/lib/app-mode.ts` validates deployment mode (`full` default, `demo` explicit).
The setting is build/start configuration, never a request parameter or cookie.
Full mode retains authenticated `/app` routes and the original FastAPI adapter.
Demo mode blocks the `/api/v1/*` proxy before reading cookies or resolving a backend;
server-side protected data reads return unauthorized, and login/register lead to the
separate public demo. No full-application authorization check is bypassed.

`src/lib/demo/types.ts` defines the typed demo data/action port. `fixtures.ts` provides
independent synthetic records. `store.ts` applies validated, bounded local commands;
`analytics.ts` derives the Step 12 response contract from those records.
`components/demo/` composes the existing tokens, workspace layout styles, buttons,
shared workflow stage visualization and the Step 12 analytics dashboard/charts.
The analytics dashboard accepts an optional typed data source; its default remains
the original authenticated API. Real SQL analytics and the Python provider interfaces
are unchanged. Specialized demo controllers avoid threading simulation flags through
real ticket and workflow business logic.

## Dataset and provenance

Northstar Studio is a fictional organization/workspace. Eight tickets, three agents,
five policy documents/passages and five workflow examples have consistent references.
All names, requests, notes, policies and timestamps were authored for this demo;
no private database records, credentials, model artifacts or customer documents were
exported. Dataset time is deliberately fixed to **October 2026** for reproducibility.
Local mutations use the demonstration observation timestamp, not wall-clock durations.

Workflow examples cover refunds, technical exports, account recovery, insufficient
evidence and sensitive ownership escalation. They are **hand-authored examples**
aligned with the implemented seven-stage graph, not recordings of Gemini execution.
They have no invented similarity/confidence scores. No model or real worker runs when
Replay is clicked. The exact source passage IDs appear in drafts and link to documents;
fixture tests check the relationships. Reference integrity is not a claim of semantic
entailment or external policy correctness.

## Interaction and persistence

- Search/filter the inbox; change local status/assignee; add notes; create up to 20
  temporary tickets. Input lengths are bounded and React renders text safely.
- Search documents by browser keyword matching, inspect passages and follow citations.
  This is explicitly not pgvector semantic search.
- Replay, pause, advance or show all seven workflow stages. Review the immutable draft
  after the final stage. Abstentions cannot be approved; revision/rejection are supported.
  Decisions are internal examples and never send messages or alter accounts.
- Analytics reflect actual synthetic records plus local edits. Rates exclude pending
  decisions from denominators; zero denominators and unrecorded durations are unavailable.
  No background jobs or vector indexes exist in the demo, so those counts are zero.
  Workflow/review times describe fixture timestamps, not measured runtime performance.
- Reset restores fixtures and removes only `resolveflow-demo-v1` from session storage.

The versioned session journal holds at most 100 validated actions and rejects oversized
or corrupt state. It survives refresh/navigation in that tab, not a production database.
Browsers may restore sessions or copy initial session storage to a duplicated tab;
there is no cross-tab synchronization. Storage errors show a notice and retain in-memory
interaction. Reset does not clear real authentication cookies or other storage keys.
Only enter synthetic content. Original workflow inputs remain immutable after ticket
edits; replay is not regeneration. There is no upload, export, backend queue or delivery.

## Verification

```bash
npm --prefix apps/web run demo:build
npm --prefix apps/web run test:demo
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
```

Playwright uses installed Chrome and starts only Next.js on 3200. It forces both API
origins to unreachable loopback port 9, blocks browser calls to `/api/v1` and external
origins, and verifies meaningful local interactions. Direct HTTP checks separately
verify the server proxy rejects real route/session attempts. Existing development
services need not be stopped or disturbed. See PROJECT_STATUS for actual results.

To verify the full application after demo tests:

```bash
NEXT_PUBLIC_APP_MODE=full npm --prefix apps/web run build -- --webpack
cd apps/api
RESOLVEFLOW_AI_LIVE_ENABLED=false .venv/bin/python scripts/local_db.py start
RESOLVEFLOW_AI_LIVE_ENABLED=false .venv/bin/python scripts/local_db.py test
NEXT_PUBLIC_APP_MODE=full RESOLVEFLOW_AI_LIVE_ENABLED=false .venv/bin/python scripts/test_browser.py
```

The isolated harness uses synthetic model fixtures and disposable data, preserving
existing development artifacts. No live provider call is authorized by these commands.

## Recruiter walkthrough and local UI polish

Start with **Explore a workflow**: inspect its source citation and exact draft,
advance to human review, and record an example decision. Then browse tickets,
search documents and inspect analytics. **Under the hood** explains the implemented
FastAPI/PostgreSQL/pgvector, ML, LangGraph and worker system; none of those services
runs in this hosted demonstration. Replay is an authored animation, not inference.

Step 16 enlarges interactive link targets, labels the horizontally scrollable ticket
region, adds a keyboard scrolling hint and column scopes, preserves visible focus,
and stacks tablet charts for readability. These changes are not yet on Vercel.
Reset affects only this tab's demo journal; no customer data or message is changed.

## Steps 28A–28C local UI verification

The black-and-red redesign (superseding the Step 28A warm palette) is local on `codex/step28a-warm-ui`, based on
production commit `8bb8ffd`. Public hosting remains unchanged. See
[UI_DESIGN_SYSTEM.md](UI_DESIGN_SYSTEM.md) for palette, typography, responsive rules,
motion and accessibility decisions.

Use the existing demo build/test/typecheck/lint commands above. The suite retains
all 17 previous checks and adds four scenarios, covering reset-dialog keyboard containment,
Escape and trigger-focus restoration; and reduced-motion navigation/workflow controls; and theme persistence, cross-tab,
pre-paint and blocked-storage behavior.
Original network isolation, CSP, storage validation, approval and console assertions
remain strict. The initial failures in transient fade contrast and modal focus were
fixed in the UI, not suppressed in the tests. Final outcomes are in PROJECT_STATUS.

Screenshots cover landing, overview, tickets, knowledge, workflows, analytics and
architecture, including dark and mobile views. The optional local review server
uses port 3210 to avoid disturbing any existing service; the standard automated
harness still uses 3200. Neither requires a backend. Dark is the default; explicit Light/Dark controls persist a validated browser
preference across routes, reloads and tabs. Native dropdowns remain native and no new
remote font, analytics or motion library is required.
