# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Four internal roles, each using the app as their primary daily work tool (confirmed via live QA across all 4 roles):

- **Distributor** — the tenant owner/admin. Manages the product catalog, inventory, warehouses, users, and store invitations; monitors order flow and resolves delivery issues. Works at a desk.
- **Vendor** — sales/fulfillment staff assigned to specific stores. Accepts or rejects incoming pending orders (with atomic stock deduction), dispatches accepted orders, resolves delivery issues. Polls for new orders every 30s.
- **Store Owner** — the ordering customer. Browses the active product catalog, builds a cart, submits orders to their assigned vendor, tracks order status, confirms receipt or reports a delivery problem.
- **Delivery** — field staff. Confirms dispatched orders as delivered from a queue. Phone-only, often outdoors, one-handed use, sometimes with unreliable connectivity.

## Product Purpose

A B2B distribution management platform: a distributor manages products/inventory across warehouses, vendors process store orders against that inventory, delivery personnel confirm physical deliveries, and store owners browse a catalog and place orders — all within one multi-tenant system rooted at `Distributor`. Success means an order can move from placed → accepted (with correct, race-safe stock deduction) → dispatched → delivered → confirmed (or flagged as a delivery issue and resolved) with a complete audit trail at every step, and every role only ever sees their own distributor's data.

## Positioning

Existing B2B distribution/order-management tools (Cin7, Zoho Inventory, Ordoro) are built for larger operations with correspondingly larger price tags and complexity. This system's assigned angle is the opposite: radical simplicity and affordability for a small Ecuadorian distributor (the brief's client, ISBEN Solutions, in Loja) — four straightforward roles, no enterprise feature sprawl, built to be affordable for a business that current tools price out rather than a stripped-down enterprise product.

## Operating Context

- Spanish-language UI throughout (Ecuador, Loja).
- Distributor and Vendor roles work primarily at a desk; Store Owner varies; Delivery is phone-only, frequently outdoors with unreliable connectivity — the one role most likely to have a degraded experience if not designed for deliberately.
- Order state machine (fully enforced server-side): `PENDING → ACCEPTED → DISPATCHED → DELIVERED → CONFIRMED`, with `PENDING → REJECTED` and `DELIVERED → DELIVERY_ISSUE → CONFIRMED` branches. A resubmission after rejection creates a new order linked via `previous_order`.
- Vendor dashboard polls `GET /api/orders/pending/` every 30 seconds for new orders (no page reload) — this is the closest thing to a real-time requirement in the product.
- Stock is centralized per-warehouse (not per-vendor); accepting an order runs stock-check + deduction + status transition inside one atomic transaction with row-level locking, so concurrent accepts on the same low-stock item can't oversell.

## Capabilities and Constraints

- **RBAC + tenant isolation:** every queryset scoped by `distributor`, directly or transitively; enforced via `@role_required` decorators and DRF permission classes. Confirmed architecturally sound during this session's QA pass (no cross-tenant leakage observed across all 4 roles).
- **Audit trail:** every order status transition, inventory deduction, and account-lifecycle event writes an `AuditLog` entry.
- **Notifications:** in-app only (no email/push) on order accept/reject/dispatch/deliver/issue/resolution.
- **Delivery photo capture:** the data model has a `photo_public_id` field, but this was explicitly descoped from the brief (photo-based proof-of-delivery was dropped in favor of a store-owner-confirms-receipt flow) — the field exists but has no validation or UI. Do not design a photo-capture flow without product scoping first (tracked in `TODOS.md`).
- **Production deployment:** not yet wired up — no WhiteNoise, no `dj-database-url`, no Procfile/Gunicorn, console-only email backend. SQLite by default; PostgreSQL is supported via env flag but not the deployed default.
- **Undocumented/unresolved as of last requirements pass:** a duplicate `base.html` template-shadowing bug, and a catalog DRF API (`/api/stores/`, `/api/products/`, `/api/inventory/`) added outside the original architecture that is not yet tenant/role-scoped — not production-safe as-is. See `docs/requirements.md` for full detail; do not assume these are resolved without checking current code.

## Brand Commitments

- Name/wordmark: "ISBEN Solutions" (styled as "ISBEN **Solutions**" in the logo lockup, with a small distributor-specific suffix e.g. "Distribuidora" in some contexts).
- An existing marketing homepage (`templates/home.html` + `static/css/home-tailwind.css`) already establishes a real brand: warm palette (ink `#231A16`, cream `#FFF8F0`, orange `#FB4318`, gold `#FFC22F`, slate `#6B5D55`), Space Grotesk display + Public Sans body + IBM Plex Mono data font. This is binding — confirmed via `/design-consultation` (2026-07-24) as the source of truth to unify the logged-in app with, not replace.
- `ClaudeDesign.md` (repo root) is a standing, binding anti-generic-design ruleset for this project — hard bans on purple/gradients/glassmorphism/generic SaaS patterns, specificity requirements for typography and composition. Treat it as a durable constraint on all future design work, not a one-time note.

## Evidence on Hand

- No real customers, testimonials, case studies, or press — this is a course project with an assigned (real-world-modeled but not commercially live) client. Do not fabricate any of the above.
- Real, working reference material instead: a fully functional Django implementation (RBAC, tenant isolation, full order lifecycle, audit trail, browse-first cart flow, delivery queue) verified end-to-end via live QA on 2026-07-24 across all 4 roles — this is the strongest "evidence" available and should be treated as ground truth over any stale doc.
- `docs/requirements.md` is the authoritative functional/non-functional requirements source but contains a documented divergence log — always cross-check against current code rather than trusting it at face value.

## Product Principles

1. **Tenant isolation is non-negotiable.** Every feature, every view, every query must be scoped to the acting user's distributor — this is architecturally enforced, not a convention to remember.
2. **The order state machine is the spine of the product.** New features should fit into or extend the existing PENDING→ACCEPTED→DISPATCHED→DELIVERED→CONFIRMED(/REJECTED/DELIVERY_ISSUE) flow, not create parallel status logic.
3. **Design for the role with the worst conditions, not the best.** Delivery staff are phone-only, often outdoors, sometimes offline — solve for them explicitly rather than assuming desk conditions.
4. **Affordable simplicity over feature parity.** When a decision could go toward "match what Cin7/Zoho does" or "keep it radically simpler," default to simpler — that's the product's actual reason to exist.
5. **Real data over decoration.** KPIs, stats, and status indicators must reflect real, sourced numbers from the system — never a placeholder or decorative stat block.

## Accessibility & Inclusion

- Delivery role: minimum 44×44px touch targets (one-handed, sometimes gloved use); computed contrast constraint already established in `DESIGN.md` — brand orange as text (not fill) on the cream background falls below WCAG AA for body text (~3.4:1), so darker text colors are required for on-cream text in that role's UI.
- No other accessibility requirement has been explicitly assigned by the brief; treat standard WCAG AA as the working baseline until told otherwise.
