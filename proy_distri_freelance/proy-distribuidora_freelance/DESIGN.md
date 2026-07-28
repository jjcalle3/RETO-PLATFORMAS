---
name: ISBEN Solutions Distribuidora
description: Warm-operational B2B distribution platform for order management, inventory, and delivery tracking, built for small Ecuadorian distributors.
colors:
  ink: "#231A16"
  cream: "#FFF8F0"
  canvas: "#FFFFFF"
  border: "#E4D8CC"
  orange: "#FB4318"
  gold: "#FFC22F"
  slate: "#6B5D55"
  status-pending: "#B8860B"
  status-accepted: "#FFC22F"
  status-dispatched: "#1E6FBF"
  status-awaiting: "#0E8074"
  status-success: "#2E7D32"
  status-muted: "#6B5D55"
  status-error: "#B3261E"
  status-pending-text: "#7A5A08"
  status-accepted-text: "#7A5C00"
  status-dispatched-text: "#12507F"
  status-delivered-text: "#0B5A51"
  status-confirmed-text: "#1E5A21"
  status-rejected-text: "#4A4038"
  status-delivery-issue-text: "#7A1712"
typography:
  display:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "28px"
    fontWeight: 700
    lineHeight: 1.15
  headline:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.3
  title:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    letterSpacing: "0.02em"
  data:
    fontFamily: "IBM Plex Mono, monospace"
    fontSize: "14px"
    fontWeight: 400
    letterSpacing: "normal"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
  full: "9999px"
spacing:
  2xs: "2px"
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  2xl: "48px"
  3xl: "64px"
components:
  button-primary:
    backgroundColor: "{colors.orange}"
    textColor: "{colors.ink}"
    rounded: "{rounded.full}"
    typography: "{typography.body}"
    padding: "0.85rem 1.75rem"
  button-primary-hover:
    backgroundColor: "{colors.orange}"
    textColor: "{colors.ink}"
    rounded: "{rounded.full}"
  button-secondary:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 18px"
  input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "8px"
  card:
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.md}"
  status-pill-pending:
    backgroundColor: "rgba(184, 134, 11, 0.16)"
    textColor: "#7A5A08"
    rounded: "{rounded.full}"
    typography: "{typography.label}"
    padding: "4px 12px"
  status-pill-accepted:
    backgroundColor: "rgba(255, 194, 47, 0.24)"
    textColor: "#7A5C00"
    rounded: "{rounded.full}"
    typography: "{typography.label}"
    padding: "4px 12px"
  status-pill-dispatched:
    backgroundColor: "rgba(30, 111, 191, 0.14)"
    textColor: "#12507F"
    rounded: "{rounded.full}"
    typography: "{typography.label}"
    padding: "4px 12px"
  status-pill-delivered:
    backgroundColor: "rgba(14, 128, 116, 0.14)"
    textColor: "#0B5A51"
    rounded: "{rounded.full}"
    typography: "{typography.label}"
    padding: "4px 12px"
  status-pill-confirmed:
    backgroundColor: "rgba(46, 125, 50, 0.14)"
    textColor: "#1E5A21"
    rounded: "{rounded.full}"
    typography: "{typography.label}"
    padding: "4px 12px"
  status-pill-rejected:
    backgroundColor: "rgba(107, 93, 85, 0.14)"
    textColor: "#4A4038"
    rounded: "{rounded.full}"
    typography: "{typography.label}"
    padding: "4px 12px"
  status-pill-delivery-issue:
    backgroundColor: "rgba(179, 38, 30, 0.14)"
    textColor: "#7A1712"
    rounded: "{rounded.full}"
    typography: "{typography.label}"
    padding: "4px 12px"
---

# Design System — ISBEN Solutions Distribuidora

## Product Context
- **What this is:** A Django-based B2B distribution management platform. A distributor manages products/inventory, vendors process store orders, delivery personnel confirm deliveries, and store owners browse and order.
- **Who it's for:** Four internal roles who use this daily as their primary work tool: Distributor (admin/ops), Vendor (sales/fulfillment), Store Owner (ordering customer), Delivery (field staff, often on a phone).
- **Space/industry:** B2B distribution / order management, Ecuador (Loja), Spanish-language UI.
- **Project type:** Internal operational web app (server-rendered Django), plus a small public marketing homepage.
- **The memorable thing:** Operational control + speed — a user should feel like nothing falls through the cracks and the app is responsive enough to use between deliveries, not just at a desk.

## Aesthetic Direction
- **Direction:** Warm Operational — industrial/utilitarian bones (grid-disciplined, data-dense, function-first) wrapped in a warm, human brand instead of the cold enterprise blue-gray every competing distribution tool (Ordoro, Cin7, Zoho Inventory) defaults to.
- **Decoration level:** Minimal-to-intentional. Typography and color-coded status carry the weight; a few intentional touches (soft card shadows, the same button lift/shadow hover already built for the homepage CTA) tie the app to the marketing site.
- **Mood:** Confident and warm, not clinical. Should read as "a real company built this for us," not "generic admin template."
- **Reference:** The existing marketing homepage (`templates/home.html` + `static/css/home-tailwind.css`) is the source of truth — the app was extending an existing brand, not inventing a new one.

## Typography
- **Display/Hero:** Space Grotesk — already the brand's display face (declared in `home-tailwind-src.css` as `--font-display`). Normally treated as an overused "safe Inter alternative" in general design advice, but here it's inherited identity, not a fresh generic pick, so it stays.
- **Body/UI/Labels:** Public Sans — already declared as `--font-body`. Clean, humanist, built for interface clarity.
- **Data/Tables:** IBM Plex Mono with tabular figures — already declared as `--font-mono` but currently unused anywhere in the app. Apply to prices, quantities, SKUs, order IDs. Aligned digits and mono spacing make dense tables scan faster — the single highest-leverage typography change for the "speed" half of the memorable thing.
- **Code:** IBM Plex Mono.
- **Loading:** Self-hosted or Google Fonts, `font-display: swap`, with the existing system-font stack (`"Segoe UI", Arial, Helvetica, sans-serif`) as fallback.
- **Scale:**
  - Display/H1: 28–32px, bold, tight leading (1.1–1.2)
  - H2 (page titles): 22–24px, bold
  - H3 (section titles): 18px, semibold
  - Body: 14–15px, normal weight, 1.5 line-height
  - Table data (numeric): 14px, IBM Plex Mono, tabular-nums
  - Small/muted (timestamps, captions): 12–13px, slate

## Color
- **Approach:** Balanced — status color-coding is core to "operational control," so color isn't purely restrained, but every hue is reserved for a specific job (action, status, or brand mark) and never decorative.
- **Ink** `#231A16` — primary text, dark surfaces (sidebar).
- **Cream** `#FFF8F0` — page background. Warm, not stark white or dark-mode-only.
- **Canvas** `#FFFFFF` — cards, table surfaces, form inputs.
- **Orange (primary)** `#FB4318` — primary actions only (Aceptar, Nuevo pedido, Confirmar). One consistent CTA color per screen.
- **Gold (secondary)** `#FFC22F` — secondary accents, hover states, highlight badges. Already paired with orange in the existing brand.
- **Slate (muted)** `#6B5D55` — secondary/muted text, timestamps, captions.
- **Semantic status colors — 6 distinct hues for the app's 7 real order statuses (new — the app currently has no success/warning/info, only `--color-error`).** Found during `/plan-design-review`: a naive 4-color (success/warning/info/error) system leaves Aceptado uncolored and conflates "still open" with "done," and "dead" with "needs urgent action" — both directly undermine the "operational control" goal, since a distributor can't tell those states apart at a glance.
  - `--color-pending: #B8860B`-family amber — **Pendiente** (needs a vendor decision)
  - `--color-accepted: #FFC22F` (existing gold, reused) — **Aceptado** (accepted, not yet dispatched)
  - `--color-info: #1E6FBF`-family blue — **Despachado** (in transit)
  - `--color-awaiting: #0E8074`-family teal (new) — **Entregado** (delivered, but still open — awaiting the store owner's confirmation or issue report; deliberately distinct from Confirmado so "still open" never reads as "done")
  - `--color-success: #2E7D32`-family green — **Confirmado** (terminal, truly done)
  - `--color-muted: #6B5D55` (existing slate, reused) — **Rechazado** (terminal, dead — no action ever needed again; deliberately muted, not red, since red should mean "act now")
  - `--color-error: #B3261E` (existing) — **Problema de Entrega** (needs urgent resolution — the only state that keeps red)
- **Status pills:** every order status renders as a small colored badge using the mapping above, never plain text. Reserve these hues strictly for status — confirmed by research into logistics-dashboard UX (color fatigue is real; saturated color should mean something, not decorate).
- **Dark mode:** not required for this internal tool (all 4 roles work in daylight/retail settings); skip unless requested later.

## Spacing
- **Base unit:** 8px.
- **Density:** Compact for data tables (more orders visible per screen = faster scanning, serves "speed"); comfortable for cards, forms, and the delivery-queue cards used by field staff on mobile.
- **Scale:** 2xs(2) xs(4) sm(8) md(16) lg(24) xl(32) 2xl(48) 3xl(64)

## Layout
- **Sort/priority (orders table, delivery queue):** needs-action states always sort above informational states, then oldest-first within each group. Needs-action = Pendiente, Problema de Entrega. Informational = Aceptado, Despachado, Entregado, Confirmado, Rechazado. This applies to the distributor's orders table, the vendor's pending queue, and the delivery-worker's queue — nothing that needs a human decision should sit below routine rows.
- **Approach:** Grid-disciplined for the app; the existing marketing homepage keeps its creative-editorial layout untouched.
- **Navigation:** Left sidebar (ink `#231A16` background, orange active-state highlight) — **this is a scope change from the current top-nav bar used across all 4 roles.** Approved via the design-mockup comparison; flagged explicitly because it's a bigger structural change than a color/typography reskin. Collapses to a bottom tab bar at **<1024px** (tablets and phones both get the bottom bar, not just phones — deliberate choice to cover the case where field/store staff use a tablet). Sidebar `<nav>` uses `aria-current="page"` on the active item; bottom tab bar uses the same semantic pattern. Full keyboard navigation (Tab/Enter) required on both — no click-only interactions.
- **KPI summary:** card-based metric tiles above data tables on dashboard-style screens (Total pedidos, Cumplidos, Rechazados, Tiempo promedio) — using real, sourced numbers only, never decorative stat blocks. "Cumplidos" counts CONFIRMED status only (not Entregado) — already precisely implemented in `accounts/views.py`, noted here so it doesn't get re-litigated.
- **Max content width:** 1400px (matches existing `.header-row` constraint).
- **Border radius:** sm 4px (inputs, small badges), md 8px (cards, buttons), lg 12px (modals), full 9999px (status pills, matching the homepage's existing `.btn-pill`).

## Motion
- **Approach:** Intentional but restrained. One orchestrated moment beats scattered effects.
- **Reused pattern:** the homepage's existing `.btn-pill-primary:hover { transform: translateY(-5px); box-shadow: 0 5px 0 0 gold }` lift-and-shadow extends to primary buttons in the app, tying both surfaces together.
- **New pattern:** a brief transition flash on a status pill when an order's status actually changes (e.g., right after a vendor accepts an order) — reinforces "responsive," never decorative.
- **Easing:** enter (ease-out), exit (ease-in), move (ease-in-out).
- **Duration:** micro 50–100ms, short 150–250ms, medium 250–400ms.
- Respect `prefers-reduced-motion` throughout.

## Interaction States
Previously unspecified — a critical gap given Delivery staff work outdoors on unreliable connections.

| Feature | Loading | Empty | Error | Success | Offline/Partial |
|---------|---------|-------|-------|---------|------------------|
| Confirmar Entrega (delivery confirm) | N/A — see Offline below | N/A | Card reverts to unconfirmed state, inline error text, retry button reappears | Card moves to history list, brief pill-flash | **Optimistic UI:** tap confirms instantly in the UI (serves "speed"); show a small "Sincronizando…" indicator on the card until the server round-trip completes. On failure, revert the card and show a retry button — never silently lose the tap. |
| Orders table / delivery queue | Skeleton rows matching final row height (no layout shift) | Warm, specific message + primary action — see approved mockup `mobile-delivery-queue-20260724/variant-A.png` ("No hay más entregas pendientes" + illustration + "¡Buen trabajo!"), never a bare "No items found." | Inline banner above the table, plain language, retry action | — | If a background refresh fails, keep showing last-known data with a small "Última actualización: [time]" timestamp rather than blanking the screen — per logistics-dashboard research on data-freshness indicators |
| Cart / checkout (Store Owner) | Button shows spinner, disables during submit | "Sin productos aún. Agrega al menos uno…" (already implemented — keep this pattern) | Form re-renders with field-level error text, values preserved | Redirect to order detail with confirmation message (already implemented) | N/A (desktop/in-store, assume stable connection) |

## What Already Exists (reuse, don't rebuild)
- **jQuery DataTables.js** — already powers every sortable/searchable/paginated table in the app. Stays as-is; the new sort/priority rule (see Layout) should be implemented as DataTables' default ordering, not a custom sort mechanism.
- **`.btn` / `.btn-pill` / `.btn-pill-primary`** CSS classes — already exist, already match the brand. Extend rather than replace.
- **`get_status_display()` pattern** — Django's built-in choices-field display method, already used correctly on the order detail page (fixed everywhere else during this session's `/qa` pass). Status pills should wrap this, not reimplement status-to-label mapping.

## Role-Specific Notes
The system above is universal (colors, type, spacing, status pills, motion) — but page content and available actions remain exactly as implemented today, scoped by role (`@role_required` decorator, `_orders_for()` helper). This design system is a visual layer; it does not change RBAC or tenant isolation.
- **Distributor:** dashboard with KPI cards, orders table, low-stock inventory table.
- **Vendor:** pending-orders queue, accept/reject/dispatch actions.
- **Store Owner:** browse-first product grid, cart, order tracking.
- **Delivery:** card-based delivery queue, optimized for one-handed mobile use — sidebar nav collapses to a bottom tab bar on mobile (see approved mockup `mobile-delivery-queue-20260724/variant-A.png`).
  - **Touch targets:** 44×44px minimum on every tappable element (Confirmar Entrega, Cómo llegar, tab bar icons) — this role is used outdoors, often one-handed, sometimes with gloves.
  - **Outdoor legibility:** computed WCAG contrast — orange `#FB4318` text directly on cream `#FFF8F0` background is ~3.4:1, below the 4.5:1 AA minimum for body text (though it clears the 3:1 threshold for large/bold text and UI components). White button labels on solid orange fill are ~3.55:1 — borderline. **Rule:** never use orange as small/regular-weight body text; reserve it for fills (button backgrounds), large bold labels, and icons. For any orange-on-cream text usage, use a darkened shade (e.g. `#C93611`) that clears 4.5:1, or fall back to ink `#231A16` for body copy.
  - **Photo capture on delivery confirmation:** the data model has a `photo_public_id` field implying a photo-capture flow. Deferred — see `TODOS.md`, needs product scoping before a UI is designed.

## Deferred / Backlog
- Low-stock severity tiers (Crítico / Bajo) on the distributor's inventory table — surfaced during this design pass, logged in `TODOS.md` rather than built now.

## NOT in Scope (considered, explicitly deferred)
- **Delivery photo-capture UI** — real feature gap (`photo_public_id` exists in the data model) but needs product scoping before a UI can be designed. See TODOS.md.
- **Low-stock severity tiers** (Crítico/Bajo) — came out of an early mockup, user wants it as a separate future feature, not part of this design-system pass. See TODOS.md.
- **Dark mode** — not required; all 4 roles work in daylight/retail settings.
- **Icon-in-colored-box KPI card decoration** — flagged as a generic-SaaS pattern risk, user deliberately kept it for scanability. Not deferred — a conscious tradeoff, documented in Decisions Log.

## Implementation Tasks
Synthesized from this review's findings. Each task derives from a specific finding above.

- [x] **T1 (P1, human: ~1h / CC: ~10min)** — Status pills — Implement the 6-hue status-color mapping (Pass 7) as CSS custom properties + a template filter/tag wrapping `get_status_display()`
  - Surfaced by: Pass 7 — Aceptado had no color; Entregado/Confirmado and Rechazado/Problema-de-Entrega collided
  - Files: `static/css/styles.css`, new template tag in `orders/templatetags/`, `orders/templates/orders/index.html`, `accounts/templates/accounts/dashboard.html`
  - Verify: render one order of each of the 7 statuses, confirm all 6 hues are visually distinct
- [x] **T2 (P1, human: ~2h / CC: ~20min)** — Orders table / delivery queue sort — Implement needs-action-first sort via DataTables default ordering
  - Surfaced by: Pass 1 — no sort/priority rule existed
  - Files: `orders/views.py` (`index`, `_orders_for`), `deliveries/views.py` (queue view)
  - Verify: a PENDING order created after a CONFIRMED one appears above it in the table
- [x] **T3 (P2, human: ~3h / CC: ~30min)** — Delivery confirm — optimistic UI with sync indicator and revert-on-failure
  - Surfaced by: Pass 2 — no offline/loading state spec existed
  - Files: `deliveries/templates/deliveries/queue.html`, JS for the confirm action
  - Verify: throttle network in devtools, tap confirm, confirm card shows "Sincronizando…" then either settles or reverts with a retry button
- [x] **T4 (P2, human: ~1h / CC: ~10min)** — Touch targets + contrast fix — audit all Delivery-role interactive elements for 44px min, replace any orange-on-cream text with darkened `#C93611` or ink
  - Surfaced by: Pass 3 / Pass 6 — computed contrast ~3.4:1 for orange text on cream, below 4.5:1 AA
  - Files: `static/css/styles.css`, `deliveries/templates/`
  - Verify: run an automated contrast checker against the rendered delivery queue page
- [x] **T5 (P1, human: ~1-2 days / CC: ~2h)** — Sidebar navigation — implement left sidebar (desktop) collapsing to bottom tab bar at <1024px, with `aria-current` and full keyboard nav
  - Surfaced by: Design-consultation mockup approval + Pass 6 — biggest structural change in this design system
  - Files: `templates/base.html`, `static/css/styles.css`, all role-specific nav includes
  - Verify: test at 375px, 768px, 1024px, 1440px; keyboard-only navigation reaches every nav item
- [x] **T6 (P3, human: ~30min / CC: ~5min)** — Activate IBM Plex Mono for numeric table columns (prices, quantities, SKUs, order IDs)
  - Surfaced by: `/design-consultation` — font already declared but unused
  - Files: `static/css/styles.css`, table templates across `orders/`, `catalog/`
  - Verify: order IDs and prices render in monospace with tabular-nums

_No new tasks from Pass 4 (AI Slop) or Pass 5 (Design System Alignment) — both resolved via documentation/decision, not code._

## Approved Mockups

| Screen/Section | Mockup Path | Direction | Notes |
|----------------|-------------|-----------|-------|
| Distributor dashboard | `~/.gstack/projects/proyecto-distribuidora/designs/design-system-20260724/variant-C.png` | Dark ink sidebar, personalized greeting, low-stock severity tiers (tiers deferred, see TODOS.md) | Sidebar nav approved here became a documented scope change (see Layout section) |
| Mobile delivery queue | `~/.gstack/projects/proyecto-distribuidora/designs/mobile-delivery-queue-20260724/variant-A.png` | Bottom tab bar, illustrated warm empty state, DESPACHADO status pill | Reference for the empty-state pattern in Interaction States above |

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-24 | Initial design system created via `/design-consultation` | Unify the logged-in app with the existing marketing-homepage brand (orange/gold/cream/ink, Space Grotesk + Public Sans) instead of inventing a new one. Activated the already-declared but unused IBM Plex Mono for data. Added a real semantic status-color system (previously only had `--color-error`). |
| 2026-07-24 | Adopted left sidebar nav (was top nav) | Approved via AI mockup comparison (2 variants generated, both independently proposed a sidebar). Explicitly flagged as a bigger structural change than a reskin before the user confirmed. |
| 2026-07-24 | Deferred low-stock severity tiers | Came out of the approved mockup; user wanted it captured as a future feature, not built as part of the design system pass. See `TODOS.md`. |
| 2026-07-24 | Kept icon-in-colored-box KPI card decoration (`/plan-design-review`) | Flagged as a recognizable generic-SaaS pattern per App UI anti-slop rules; user deliberately chose to keep it for quick visual scanning (cart=orders, clock=time). Documented as a conscious tradeoff, not an oversight. |
| 2026-07-24 | Sort/priority rule added: needs-action states above informational states | Closes an Information Architecture gap found in `/plan-design-review` — orders table and delivery queue previously had no specified sort order. |
| 2026-07-24 | Interaction states specified: optimistic-UI delivery confirmation, skeleton loading, warm empty states anchored to the approved mockup | Closes a critical gap — DESIGN.md previously had zero spec for loading/empty/error/offline states, risky given Delivery staff work outdoors on unreliable connections. |
| 2026-07-24 | Delivery role: 44px touch targets, orange-on-cream contrast rule (~3.4:1, below 4.5:1 AA for body text), photo-capture UI deferred to TODOS.md | Closes the weakest part of the User Journey pass — Delivery was the least-designed-for role despite being singled out as needing speed. |
