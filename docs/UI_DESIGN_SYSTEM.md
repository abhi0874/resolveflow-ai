# ResolveFlow AI UI design system

Step 28C.1 — single-red palette and bold capsules, 2026-10-29. Not deployed.
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
| Only brand red / primary / hover / focus | `#E51838` | `#E51838` |
| Capsule surface | `#000000` | `#FFFFFF` |

`--brand-red` is declared once; legacy accent/primary token names reference it.
There is no alternate red, red color mix, red gradient or tinted red surface.
Small text on charcoal and soft-white surfaces uses neutral foreground colors.
Green success, amber warning and violet review states remain distinct and labeled.
Error/urgent/destructive states combine explicit labels with the single red border
or marker and readable neutral text. Reset remains outlined rather than filled;
disabled primary actions use neutral surfaces, not opacity-dimmed red.
`design-system.css` owns theme tokens; `globals.css` retains component geometry.

## Reusable section capsules

`.section-capsule` styles Capabilities, Our approach and Engineering navigation,
plus the existing hero, workflow-illustration, capabilities, approach and foundation
section labels. Navigation remains real links; static labels remain semantic spans.

- Background: exactly black (`#000000`) in Dark Mode, white (`#FFFFFF`) in Light Mode.
- Text and border: exactly `#E51838` in both themes, including hover.
- Border: `1.5px solid`; fully rounded `9999px` radius. Browser rasterization may
  quantize a fractional CSS border to device pixels.
- Typography: **700 bold**, uppercase, `.65rem`, `1.5` line height and `.08em`
  tracking. Compact mobile navigation uses `.6rem` / `.04em`, retaining weight 700.
- Balanced `7px 13px` padding; navigation links retain at least 44px height.
  Labels wrap within their available width; static labels do not gain button roles.
- Hover uses a small translation and neutral shadow, never a different red shade.
  No color transition is applied to capsule foreground/background, preserving their
  contrast during theme switches. Reduced motion removes translation and transition.

Calculated WCAG contrast: red on black **4.519:1**, red on white (and white labels
on red buttons) **4.647:1**, above the normal-text AA threshold. The same red on
`#171719` is only **3.853:1**, so small text there is neutral; red remains suitable
for non-text borders/graphics (3:1 threshold). The pure capsule surfaces are
intentional accessibility constraints. These checks do not establish complete
WCAG 2.2 AA compliance or replace assistive-technology testing.

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
uses the single-red outline and a neutral surface/text, distinct from filled primary
brand actions. Knowledge/example cards use neutral top borders to avoid repeated red strips. Tables retain labeled
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
`.cache/verification/step28c/`. Step 28C.1 evidence is under
`.cache/verification/step28c1/`, including capsule close-ups and final screenshots. Regression checks also cover 768px and 320px.
No backend, CSP, API, dependency or deployment configuration changes. Physical-device,
Safari/Firefox and authenticated full-backend journeys remain unverified in this step.

Step 28C.1 final verification: 23 browser tests passed (20.3s), TypeScript, ESLint
and demo production build passed. Capsule checks cover 1440/1024/768/390/320px,
both themes, exact colors and weight, keyboard/hover and neutral disabled actions.
44 screenshots were captured locally; required screens and close-ups were visually
reviewed. No console/page errors or unexpected requests occurred in final captures.
Existing axe checks and extra open-dialog checks passed in both themes. See the
Step 28C.1 status record for full evidence and known testing limitations.
