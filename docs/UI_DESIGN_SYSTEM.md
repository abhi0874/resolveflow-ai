# ResolveFlow AI UI design system

Step 28C — final local visual QA, 2026-10-29. Not deployed.
Supersedes Step 28A's warm palette while preserving its layouts and interactions.

## Tokens and visual direction

Black dominates the default theme. Blood-red actions, selected navigation, focus
rings and workflow progress provide restrained emphasis. Cards and headings are
predominantly neutral. No glow, remote fonts or new dependencies.

| Role | Dark (default) | Light |
| --- | --- | --- |
| Page | `#080808` | `#F6F5F6` |
| Surface | `#111113` | `#FCFBFC` |
| Elevated | `#171719` | `#FFFFFF` |
| Hover | `#252527` | `#E6E3E7` |
| Text | `#F5F3F3` | `#171719` |
| Secondary text | `#ABABAB` | `#606064` |
| Border | `#333336` | `#D5D2D7` |
| Control boundary | `#747478` | `#858189` |
| Primary / hover | `#C91F32` / `#DF3046` | same |
| Deep crimson | `#841521` | same |
| Small accent text / focus | `#EF6979` | `#AF192B` |

White primary-button text maintains contrast on both red shades. Accent text uses
contrast-adjusted shades rather than small dark-red text on black. Green success,
amber warning and violet review states remain distinct and include text labels.
`design-system.css` owns theme tokens; `globals.css` retains component geometry.
Legacy dark status selectors follow the explicit theme, not the OS preference.

## Theme selection and persistence

The sun/Light and moon/Dark segmented control appears in the landing header and
workspace toolbar, including the technical case study and mobile layouts. Native
buttons expose accessible labels and aria-pressed state; Tab, Enter and Space work.
The default is dark even when the operating system prefers light.

A single localStorage key, `resolveflow-theme`, stores only `light` or `dark`.
`public/theme-init.js` is a small synchronous same-origin head script that restores
that preference before body parsing. It requires no CSP changes. Root hydration
suppression is limited to the HTML element whose theme attribute is intentionally
updated before React hydration. Button state uses useSyncExternalStore with a stable
server snapshot, document theme snapshot and cleaned-up change subscriptions.
There is no competing provider. Selection persists across navigation, refreshes
and later same-origin visits; storage events synchronize open tabs. Blocked storage
falls back to dark on reload while in-page selection remains usable. No cookie,
credential, API request or demo-data mutation is involved.

## Typography, surfaces and interactions

Device-local Avenir Next / Avenir / Segoe UI / Arial / sans-serif throughout.
Strong, compact sans-serif headings replace the editorial serif treatment. Existing
4px spacing rhythm, roughly 10px controls and 16px cards keep layouts consistent.

The system covers landing, overview, tickets, knowledge passages, workflow replay,
human approval, analytics, architecture, forms and dialogs. Existing reset dialog
retains focus containment, Escape and opener restoration. Its destructive confirmation
uses a danger-colored outline and tinted surface, distinct from filled primary brand
actions. Knowledge/example cards use neutral top borders to avoid repeated red strips. Tables retain labeled
keyboard scrolling. Native dropdowns keep their platform behavior. Synthetic-data
and precomputed-workflow labels remain visible; existing business rules are unchanged.

## Motion and accessibility

160ms hover/press feedback, 220ms theme/control transitions, 280ms section/chart
entrances, with cubic-bezier(.2,.7,.2,1) easing and small translations. Text is not
faded at entrance, avoiding transient contrast loss. No continuous animation;
loading skeleton remains bounded to three cycles. Charts animate their container,
not data values. Workflow replay timing and human approval gates are unchanged.
Reduced-motion disables animations, transitions and smooth scrolling.

Desktop sidebar becomes a mobile grid at 750px. Workflow nodes use four columns,
two below 1200px and one below 380px. Header controls reflow at 1000px and 480px.
Demo touch targets are at least 44px; visible focus and textual statuses remain.
Both themes undergo the existing contrast and axe WCAG 2.0/2.1 A/AA checks.
This is not a claim of complete WCAG certification or manual screen-reader testing.

## Verification

See PROJECT_STATUS.md for final fresh counts. Local screenshots cover seven screens
at 1440px and 390px in both themes, plus diagram and dialog captures, under ignored
`.cache/verification/step28b/`; final captures and interaction measurements are in
`.cache/verification/step28c/`. Regression checks also cover 768px and 320px.
No backend, CSP, API, dependency or deployment configuration changes. Physical-device,
Safari/Firefox and authenticated full-backend journeys remain unverified in this step.
