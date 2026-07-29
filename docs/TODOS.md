# TODOS — proyecto-distribuidora

Task backlog derived from the gap analysis in `docs/requirements.md`'s "Implementation
Status & Known Issues" section. Ordered by priority; Tier 1 blocks everything after it.
Update checkboxes as items land; don't reorder history, append new items at the end of
their tier.

## Sprint 1 addendum — Account provisioning redesign (DR-08) — DONE 2026-07-16

Not in the original Tier 1 scope — added after testing surfaced two real gaps: creating
a Distributor was a two-step superuser+/admin/ flow, and STORE_OWNER accounts had no
self-service path despite that role being the least technical.

- [x] `Distributor.invite_token` field + `regenerate_invite_token()` (migration
      `0004_distributor_invite_token.py`, backfilled for existing rows).
- [x] Combined superuser onboarding: `crear_distribuidor` now creates the `Distributor`
      + its first `DISTRIBUTOR` user atomically (`DistributorOnboardingForm`).
- [x] Store-owner self-registration via per-distributor invite link:
      `accounts/join/<token>/` (`registrar_tienda`), no public distributor picker,
      auto-login on success, new store starts with no vendor assigned (existing DR-01
      message covers it).
- [x] Invite link shown + regenerable from the distributor's own dashboard
      (`accounts/index.html`).
- [x] Fixed a pre-existing broken-link bug found along the way: the superuser-only
      Distributor templates linked "Volver"/"Cancelar" to `index_accounts`, which is
      `role_required('DISTRIBUTOR')` — a plain superuser (no `role`) got 403 clicking
      them. Now point to `admin:index`.
- Documented as DR-08 in `docs/requirements.md`. Verified via `manage.py check` and a
  test-client smoke test (combined onboarding, join-link happy path, bogus token 404,
  regenerate invalidates the old token).
- **Known gap, not closed:** no rate-limiting/CAPTCHA on the join endpoint, no email
  verification for self-registered store owners.

## Tier 1 — Foundational (Sprint 1, blocks everything else) — DONE 2026-07-16

- [x] Consolidate the two `base.html` files — merged into
      `proyectoDistribuidora/templates/base.html` (the one in `TEMPLATES[0]['DIRS']`);
      the shadowed `catalog/templates/base.html` copy was removed.
- [x] `accounts/decorators.py` — `role_required(*roles)` and `superuser_required` added.
- [x] RBAC applied everywhere — `accounts`, `catalog`, `orders`, `deliveries`, `audit`
      views all decorated; `catalog` upgraded from bare `@login_required`.
- [x] Tenant isolation applied — every queryset scoped by `distributor` (directly or via
      `vendor__distributor`/`store__distributor`/`order__store__distributor`), including
      the DRF catalog viewsets (`get_queryset` + `perform_create` distributor stamping +
      cross-tenant FK validation on `owner`/`vendor`/`product`). Also closed two
      tenant-leak holes found along the way: `distributor` was a raw client-editable
      field on `StoreForm`/`ProductForm`/`UserCreateForm` — removed, now stamped
      server-side; `DeliveryConfirmationForm` let the caller set `delivery_user` to
      anyone — removed, now set from `request.user`.
- [x] Password reset flow — `solicitar_reset_password`/`confirmar_reset_password` views,
      forms, templates, and URLs added; `EMAIL_BACKEND` set to console for local dev.
- [x] `Distributor` CRUD scoped to `@superuser_required`; `accounts/index` split from a
      loop-over-all-distributors view into a single-tenant user-management page.
- Verified via `manage.py check`, `makemigrations --check`, and a Django test-client
  smoke test (role block, tenant isolation, superuser gate, anonymous redirect,
  password-reset token issuance) — all passed.

## Tier 2 — Order lifecycle correctness (Sprint 3) — DONE 2026-07-16

- [x] Fix price/state integrity bugs: `OrderForm` now only exposes `store`;
      `OrderItemForm` drops `unit_price_at_time` (server-snapshot from
      `Product.unit_price` on create and edit). Bonus: `product` choices scoped to the
      order's vendor's inventory (FR-05.3), closing that gap as a side effect.
- [x] Dedicated `aceptar_pedido`/`rechazar_pedido`/`despachar_pedido` views —
      `transaction.atomic()` + `select_for_update()` on `VendorInventory`, per-item
      insufficient-stock errors, order stays `PENDING` on failure. Replaced the old
      generic `editar_pedido`/`eliminar_pedido` (removed — they let status be set
      directly, bypassing the state machine).
- [x] Added `cancelar_pedido` (STORE_OWNER, PENDING-only) — wasn't in the original Tier 2
      list, but needed once the generic edit/delete views were removed; implements
      US-23 early (was slated for Tier 4).
- [x] `GET /api/orders/pending/` (root `urls.py`) — vendor-scoped JSON endpoint, distinct
      from the catalog DRF API. 30s JS polling on `orders/index.html` prepends new
      `PENDING` orders without a reload (FR-06.6, FR-10.1, US-10).
- [x] Store-owner order status view (FR-05.5) — satisfied by the existing role-scoped
      `index`/`ver_pedido` views once status display was cleaned up; no separate page
      needed.
- Documented as a resolved section in `docs/requirements.md`'s Implementation Status.
  Verified via `manage.py check` and a test-client smoke test: full lifecycle
  (create → accept w/ stock deduction → dispatch), insufficient-stock rollback,
  reject-with-reason, cancel, and the polling endpoint.
- **Not done, still open:** `AuditLog` writes on transitions and in-app notifications on
  transition are Tier 3/4 as originally planned — accept/reject/dispatch/cancel don't
  write audit entries or notify the store owner yet.

## Sprint addendum — Delivery confirmation redesign (DR-09) — DONE 2026-07-18

Not in the original Tier 3 scope — replaces the Cloudinary item below entirely, not
just the SDK piece. Store-owner attestation replaces photo proof as the source of
truth for delivery correctness.

- [x] `Order.status` gains `DELIVERY_ISSUE` / `CONFIRMED`; `DELIVERED` is now
      non-terminal (migration `orders/0003_order_issue_description_...`).
- [x] `deliveries.crear_confirmacion` now transitions `Order` to `DELIVERED` and
      notifies the store owner — closed a pre-existing gap where this view never
      touched `Order.status` at all. `DeliveryConfirmationForm`'s `order` field is
      now scoped to `DISPATCHED` orders only.
- [x] `DeliveryConfirmation.photo_public_id` made optional (`blank=True`), never
      validated — no Cloudinary dependency.
- [x] New `orders/` views: `confirmar_recepcion`, `reportar_incidencia`,
      `resolver_incidencia` — see DR-09 in `docs/requirements.md` for the full flow.
- [x] `AuditLog` writes on `order_confirmed` / `delivery_issue_resolved` (scoped to
      just these two new transitions, not a general audit-writing pass).
- [x] `Notification` writes on delivered / issue-reported / issue-resolved /
      confirmed (first real use of the `Notification` model — Tier 4's "wire
      creation on every order transition" is still open for the older
      accept/reject/dispatch transitions).
- Verified via `manage.py migrate` + a Django test-client smoke test covering both
  paths (happy-path confirm, and report-issue → resolve-issue) plus a 404 guard-rail
  check (vendor can't resolve an order that isn't in `DELIVERY_ISSUE`).
- **Known gap, not closed:** issue resolution is notes-only — no inventory
  adjustment, partial fulfillment, or redelivery tracking (see Tier 4).

## Tier 3 — Delivery, audit, dashboard (Sprints 2 & 4) — DONE 2026-07-19

- [x] ~~Cloudinary upload preset + server-side `public_id` validation~~ —
      **superseded by DR-09**, not implemented: photo proof is dropped from scope
      entirely, not just the Cloudinary SDK piece.
- [x] `AuditLog` writes backfilled onto `aceptar_pedido` (+ per-item deduction detail
      and an `order_accept_failed` entry on insufficient stock, FR-09.3),
      `rechazar_pedido`, `despachar_pedido`, `cancelar_pedido`, and
      `deliveries.crear_confirmacion`'s `DELIVERED` transition. Every order status
      transition now has an audit entry, matching the DR-09 transitions that already
      had one.
- [x] Distributor operations dashboard (`accounts/dashboard.html`,
      `/accounts/dashboard/`) — orders grouped by status, 20 most recent orders,
      inventory per product per vendor with a low-stock row highlight (FR-08.1,
      FR-08.3). Linked from the nav for `DISTRIBUTOR` users only.
- [x] `Order` gained a composite index on `(vendor, status)` and one on `store`
      (NFR-02.6, migration `orders/0004_...`). Fixed N+1s (NFR-02.5) across every
      list view that joins related data: `orders/` index/detail (store, vendor),
      `pending_orders_api` (item count was one `COUNT` query per order, now a single
      `annotate`), `catalog/index.html` (store/product/inventory joins),
      `deliveries/index.html` (order, delivery_user), `audit/index.html` (user).
- Bonus fix found along the way: `deliveries/index.html`'s "Foto ID (Cloudinary)"
  column header was stale after DR-09 — relabeled "Foto ID (opcional, sin validar)".
- Verified via `manage.py check`, `makemigrations --check`, and `manage.py migrate`.

## Tier 4 — Secondary features (Sprint 5) — DONE 2026-07-19

- [x] Notifications — writes added on `aceptar_pedido`/`rechazar_pedido`/
      `despachar_pedido` (the DR-09 transitions and `deliveries.crear_confirmacion`
      already had them; `cancelar_pedido` deliberately doesn't notify — it's the
      store owner's own action, no FR-10 sub-item covers it). Unread count via a new
      `accounts.context_processors.notifications` context processor, shown in the nav
      for any authenticated role (not just `STORE_OWNER` — `VENDOR`/`DELIVERY` get
      DR-09 notifications too). New `/accounts/notifications/` list page with
      mark-as-read / mark-all-read.
- [x] Dashboard filters (date range, vendor, store, status) + summary metrics (total,
      fulfilled = `CONFIRMED`, rejected, avg fulfillment time) — all on
      `/accounts/dashboard/` via GET params, filters apply to both the order list and
      the metrics.
- [x] Low-stock alert badge — summary banner on the dashboard + the existing
      per-row highlight, now with the same ⚠ text marker `catalog/index.html`
      already had (the dashboard's inventory table only had the CSS highlight
      before this pass).
- Verified via `manage.py check` and a test-client smoke test: notification created +
  correct message on accept, unread count shown in the nav, notifications list page,
  mark-as-read flips `is_read`, dashboard filters (vendor/status combos) correctly
  include/exclude orders, low-stock banner appears once inventory drops below
  threshold.

## Tier 4.5 — Product Catalog Expansion: Inventory, Discounts, Multi-Warehouse (Sprint 7) — DONE 2026-07-21

Scoped via `/office-hours` + `/plan-eng-review` on 2026-07-21 — design
doc at `~/.gstack/projects/astalberto-proyecto-distribuidora/Josue-master-design-20260721-163841.md`.
Approach B ("ideal architecture") chosen over a flat-field minimal extension because the
business's own multi-warehouse requirement (Ecuador distributor, currently one warehouse)
would otherwise force a second migration later. Ships as one PR, not staged.
**Re-confirmed (2026-07-21, CEO review, cross-model check):** the project stays
local-execution only for now with no deployment planned, which reopened the question of
whether Warehouse/StockLevel is over-scoped. Project owner confirmed multi-warehouse
growth and eventual deployment are real future plans, not speculative — building the
real model now while the data is still empty is cheaper than migrating populated data
later. Architecture stands as decided.

- [x] `Category` and `Brand` as real FK'd models (not free text) — referential integrity
      for filtering, replaces the free-text approach considered and rejected in review.
- [x] `Warehouse` model (single row today) + `StockLevel(product, warehouse)`, **replacing
      `VendorInventory` as the lock target** in `orders/views.py`'s `aceptar_pedido`
      (currently `VendorInventory.objects.select_for_update().filter(vendor=..., product_id__in=...)`
      at `orders/views.py:158`). Decided during eng review over keeping `StockLevel` as
      display-only, specifically to avoid the catalog UI and the order-accept flow
      disagreeing about what's in stock. **Regression risk:** this touches the Tier 2
      concurrency-critical path — the existing concurrent-accept and insufficient-stock
      rollback tests must be re-verified against the new lock target, not just covered by
      new tests in isolation.
  - **Confirmed by the project owner, who runs the business (2026-07-21): stock is
    centralized, not per-vendor.** (A cross-model outside-voice pass flagged this as
    needing verification with someone who actually has authority over how the business
    operates, not just a coding-session guess — confirmed the answerer has that
    authority.) An outside-voice cross-model review caught that `VendorInventory` isn't just a stock
    count — `orders/forms.py:57-61` filters which products a store owner can even order
    to `Product.objects.filter(inventory__vendor=vendor, is_active=True)` (FR-05.3: each
    vendor was previously assumed to personally carry a subset of the catalog,
    route/van-sales style). **Resolved (via `/plan-ceo-review`, 2026-07-21):** `FR-05.3`'s
    filter is replaced with "any active product in the distributor's catalog is
    orderable" — `OrderItemForm`'s `product` queryset drops the `inventory__vendor=vendor`
    filter entirely, keeping only `is_active` (now `status=ACTIVE`). No new
    vendor↔product assignment model. Update `docs/requirements.md`'s FR-05.3 text to
    match, since the old wording will otherwise describe behavior that no longer exists.
  - **Accepted tradeoff:** centralizing locks widens `select_for_update()` contention from
    per-vendor to tenant-wide on every accept (today, two different vendors' accepts never
    contend; after this change, they can). No action required unless accept-time latency
    becomes a real problem — noted here so it isn't mistaken for a bug later.
  - `OrderItem` gets an explicit `warehouse` FK in this pass (not deferred) so
    `aceptar_pedido`'s `StockLevel` lock is scoped by `(product, warehouse)` from day one
    — otherwise "multi-warehouse ready" is cosmetic, since accept-time deduction would have
    nowhere to route once a second warehouse exists.
- [x] `Product.status` (Active/Inactive/Discontinued) replaces `is_active` (DR-06)
      outright. Data migration required: `is_active=True → ACTIVE`,
      `is_active=False → INACTIVE` — never auto-map to `DISCONTINUED`, which is a distinct
      explicit action. Out-of-stock is derived automatically from `StockLevel`, never a
      manual toggle.
- [x] `sku`/`barcode` unique **per distributor**, via `UniqueConstraint(distributor, sku)`
      (mirrors `VendorInventory`'s `unique_vendor_product` pattern at
      `catalog/models.py:85-90`) — not field-level `unique=True`, which would wrongly
      enforce global uniqueness across tenants.
- [x] `Discount` model: `discount_type` (PERCENTAGE or FIXED_AMOUNT), date-range window,
      stacking rule (at most one active discount per product), `current_price` computed as
      a property (never stored — expiry needs no cleanup job), clamped at zero.
      Product list/search views must `prefetch_related` discounts so `current_price` stays
      O(1) query per page, not O(n) — the same N+1 class Tier 3 already fixed once for FK
      joins.
- [x] `ProductImage` (FK to `Product`, one `is_main` flag) via local Django `ImageField` —
      not Cloudinary, to avoid introducing a second upload mechanism ahead of the
      still-unwired Cloudinary target `CLAUDE.md` already documents for delivery photos.
- [x] `ProductForm` adopts the `distributor=` kwarg pattern already used by
      `StoreForm`/`VendorInventoryForm` (`catalog/forms.py:13-17`, `:33-36`) to scope the
      new `Category`/`Brand` querysets to the caller's tenant — same class of bug Tier 1
      already fixed once for `distributor` itself.
- [x] `catalog/api_views.py`'s `ProductSerializer`/`ProductViewSet` updated in this same
      pass (not deferred) to expose the new fields, following the existing cross-tenant FK
      rejection pattern already used for `owner`/`vendor`/`product`.
- [x] `AuditLog` entries on product create/update/deactivate — reuses the existing app
      (Tier 3 already proved this pattern on order transitions), no new dependency
      (`django-simple-history` considered and rejected in review).
- [x] CSV import tool for the initial catalog bulk load — accepted in `/plan-ceo-review`
      (2026-07-21) specifically to close the Status Quo pain named in the design doc
      (manual re-entry from the distributor's existing spreadsheet). Ships in this same
      pass, not deferred. See `~/.gstack/projects/astalberto-proyecto-distribuidora/ceo-plans/2026-07-21-catalog-expansion.md`.
      **Failure handling:** row-level skip, not all-or-nothing — valid rows import, invalid
      rows (duplicate SKU, missing category, malformed data) are skipped and listed in a
      per-row error report so the user can fix and re-import just the failures.
      **Guardrails (Section 3, CEO review):** file size cap, content-type/extension check,
      and formula-injection sanitization (strip leading `=`/`+`/`-`/`@` from cell values
      before storage) — closes CSV-upload attack surface that doesn't exist anywhere else
      in this codebase today.
- [x] Bundled low-stock digest notification — single `Notification` summarizing every
      product crossing `low_stock_threshold`, instead of one notification per product.
      Small extension of the existing `Notification` model (already used for order
      events). Accepted in `/plan-ceo-review` (2026-07-21). **Trigger:** checked inside
      `crear_producto`/`editar_producto`'s save path (same synchronous request-response
      pattern as the rest of this codebase) — reflects state as of the last edit, not a
      scheduled sweep; no new background-job infrastructure introduced.
- [x] **IVA/tax handling — RESOLVED (2026-07-21):** `unit_price` is **IVA-exclusive**.
      Ecuador's 15% IVA is calculated on top wherever a final charged amount is shown or
      computed, never baked into the stored price. Keeps the tax rate changeable in one
      place if it changes again, and keeps discount-percentage math (`Discount.current_price`)
      computed against a clean base price.
- [x] **`unit_of_measure` — RESOLVED (2026-07-21):** fixed `choices=` `CharField`, not a
      separate lookup model. Closed set: `PIECE`, `BOX`, `PACK`, `BOTTLE`, `KG`, `LITER`.
      Adding a 7th unit later is a code change + migration, not a data-entry task —
      accepted tradeoff for simplicity on a field that changes rarely.
- [x] **Barcode format — RESOLVED (2026-07-21):** free text, no EAN-13/UPC validation.
      Ecuadorian retail commonly mixes real GS1 barcodes with internally-assigned codes for
      repackaged/bulk goods; a strict validator would reject real products that don't have
      a manufacturer barcode.
- Implemented 2026-07-21: `catalog` migrations `0004`-`0007`, `orders` migration `0006`.
  `VendorInventory` and its CRUD screens (W-08, the old "Asignar Inventario" flow) removed
  entirely per the same session's decision — replaced by `StockLevel` + `editar_stock`
  (per-product, single default warehouse today) and the dashboard's "Inventario por
  almacén" table. Verified via `manage.py check`, `makemigrations --check`, `manage.py
  migrate` against the real dev DB (1 pre-existing product correctly backfilled: sku,
  status, placeholder category/brand), and 24 automated tests (`manage.py test catalog
  orders`) covering: SKU uniqueness per distributor, `Discount.current_price` (percentage,
  fixed-amount, expired, clamped-at-zero, overlap rejection), stock derivation, tenant
  scoping on `ProductForm`/catalog views, CSV import (row-level skip + formula-injection
  sanitization), the FR-05.3 resolution (`OrderItemForm` no longer vendor-scoped), and the
  Tier 2 regression suite re-verified against `StockLevel` (deduction, insufficient-stock
  rollback, sequential double-spend, **and a real multi-threaded concurrent-accept test**
  — exactly one of two simultaneous accepts wins). Also live-smoke-tested every new/changed
  view via Django's test client against the running dev DB, which caught and fixed one bug
  not covered by the automated suite: `gestionar_descuento`/`editar_stock`/`quitar_descuento`
  URLs declared `<int:id>` but the views expected `product_id` — a `TypeError` at request
  time invisible to `manage.py check`.
- **Not done, deferred:** CSV import has no downloadable template file (the required-columns
  list is just prose on the import screen); `docs.requirements.md`'s DR-06 note about
  deactivated-but-still-acceptable products isn't re-verified against the new `status`
  field (behavior should be unchanged since `ACTIVE`-only scoping didn't change, but no
  dedicated test asserts it). Both are small, low-risk follow-ups, not launch blockers.

## Deferred from CEO review (2026-07-21) — not yet scheduled

Surfaced during `/plan-ceo-review`'s expansion scan on Tier 4.5, deliberately deferred
rather than bundled into that PR. See
`~/.gstack/projects/astalberto-proyecto-distribuidora/ceo-plans/2026-07-21-catalog-expansion.md`
for full reasoning.

- [ ] Barcode camera-scan search (mobile web) — reads a barcode via device camera instead
      of typing it, for warehouse staff doing physical counts. Needs camera permission
      handling + a barcode-decoding dependency; do once the `barcode` field has real
      production data and its format is settled (see Tier 4.5's open barcode-format
      decision above).
- [ ] Price-history timeline view per product — built from `AuditLog` entries Tier 4.5 is
      already writing on every product change. Zero-risk future add since the data exists
      either way; build once there's enough history to make a timeline meaningful.

## Tier 5 — Automated test hardening (Sprint 6)

Project stays local-execution only for now — no deployment planned (confirmed
2026-07-21). Deploy config work is dropped, not deferred (see "Out of scope" below).
Tests are kept: they protect against regressions regardless of deployment status, and
Tier 4.5's `VendorInventory` → `StockLevel` migration explicitly depends on the
concurrent-accept and insufficient-stock tests below being re-verified.

- [ ] Unit tests: order state transitions, price-snapshot logic, password reset token
      expiry/single-use.
- [ ] Integration tests: atomic accept race condition (concurrent accepts, exactly one
      succeeds), rollback leaves order+inventory unchanged, tenant isolation
      (Distributor A can't read Distributor B's data).
- [ ] Playwright e2e: the 4 critical paths (place order → accept → dispatch → deliver;
      distributor dashboard view) + the error path + the security/RBAC path.

**Out of scope (not deferred — no deployment planned):** production deploy config
(WhiteNoise, `dj-database-url`, Procfile/Gunicorn, real Cloudinary/Resend credentials).
Revisit only if a deployment target is actually decided.

## Tier 6 — ISBEN Roadmap (Sprint 8+) — sequenced 2026-07-21

Scoped via `/plan-ceo-review` on 2026-07-21 on a 5-item roadmap pasted by the project owner
(rebrand, role-based nav, distributor/sales management, super-admin dashboard, store-location
maps). Reviewed as SELECTIVE EXPANSION mode: the five items don't share risk, effort, or
urgency — bundling them into one plan/PR would stall the easy 80% behind the hardest 20%
(super-admin/SaaS foundation, a genuine architecture pivot, not a feature). Split into 5
independently-reviewed, independently-shippable plans instead.

**Confirmed sequencing (project owner, 2026-07-21):** 3 → 1 → 5 → 4 → 2. Item 4 (Super
Admin) introduces a new access tier (today "super admin" is just Django's raw
`is_superuser` flag — not in `accounts.Role`, not in the role-based permission system at
all) that item 2's nav redesign has a soft dependency on; building item 2 before item 4
risks a partial redo once the super-admin tier lands. Items 3, 1, and 5 have no
cross-dependencies and were sequenced by effort/risk (quick low-risk win first, mechanical
work next, isolated integration third).

- [x] **Item 3 — Distributor invitation links — DONE 2026-07-21.** Replaced manual
      superuser-driven `Distributor` account creation with a self-service, single-use
      invitation-link flow, mirroring the existing `Distributor.invite_token` /
      `accounts/join/<token>/` pattern already shipped for STORE_OWNER self-registration
      (Sprint 1 addendum, above). Also closes the sales-rep (VENDOR) assignment bug.
      `/plan-ceo-review` + `/plan-eng-review` both complete: 11-section CEO review,
      4-section eng review, 2-round adversarial spec review (quality 9/10), and TWO
      outside-voice passes (Claude subagent, Codex not installed) that together caught and
      fixed: a real defect (original nav placement was unreachable by superusers), a
      strategic over-build (rate-limiting/configurable-expiry cut as prod-hardening for a
      threat model this local-only project doesn't have — revoke initially cut alongside
      them then restored since it guards operator mistakes, not just adversaries), a
      critical transaction-scope ambiguity that could have silently defeated the
      concurrency lock, an incomplete test spec that would have shipped flaky under
      SQLite, a missing `on_delete=SET_NULL` on the new audit FK, and a pre-existing
      unrelated bug in `crear_distribuidor`'s success redirect (superusers 403'd on it) —
      full plan at
      `~/.gstack/projects/astalberto-proyecto-distribuidora/ceo-plans/2026-07-21-distributor-invitations.md`.
      **Implemented:** `DistributorInvitation` model (`accounts/models.py`, migration
      `0006_distributorinvitation`) extending `PasswordResetToken`'s expiry/single-use
      shape plus a minimal revoke; `emitir_invitacion`/`invitaciones`/
      `revocar_invitacion`/`registrar_distribuidor` views (`accounts/views.py`) with a
      single nested `transaction.atomic()` + `select_for_update()` covering token
      validation AND entity creation together (documented SQLite caveat — no-op there,
      real row lock only under Postgres); `AuditLog` on issue/redeem/revoke; conditional
      auto-email (only fires when `target_email` is set) with a graceful failure
      fallback; `crear_distribuidor`'s redirect fixed to point at the invitations list
      instead of the 403-triggering `index`; `StoreForm` vendor/owner querysets
      (`catalog/forms.py`) now filter by role AND distributor together. Verified via
      `manage.py check`, `makemigrations --check` (clean), 28 new automated tests
      (`accounts.tests` + 2 in `catalog.tests`, all 52 project tests passing) — including
      a genuine threaded concurrency test mirroring `OrderAcceptConcurrencyTest` — and a
      manual smoke test against the real dev DB (superuser issues → redeems → auto-login →
      dashboard; revoke; `crear_distribuidor` redirect regression check), all green.
      Documented as `DR-10` in `docs/requirements.md`.
      **Known pre-existing gap surfaced, not fixed (out of scope):** the dev DB is
      missing an `accounts_user_groups` table (same schema-drift bug flagged during
      Tier 4.5), which blocks deleting any `User`/`Distributor` row via the ORM — hit
      during smoke-test cleanup, so a handful of harmless `smoketest-*@test.com` /
      `debug-*@test.com` throwaway rows were left in the dev DB rather than risk touching
      an unrelated schema issue.
  - [ ] Deferred from item 3's review: rate-limiting on the join endpoint + configurable
        expiry-at-issuance — cut from item 3 itself after outside-voice review found this
        project has no live deployment for the adversarial threat model rate-limiting
        defends against (configurable expiry is separately low-value at v1's low volume).
        P3 — revisit rate-limiting once a real deployment target exists; configurable
        expiry can revisit independently if the fixed 7-day default proves too rigid.
  - [ ] Deferred from item 3's review: shared token/expiry base class across
        `Distributor.invite_token`, `PasswordResetToken`, `DistributorInvitation` (3-way
        duplication once item 3 ships). P3 — regression risk on 2 existing models outweighs
        the DRY win right now; revisit once the pattern proves itself a third time.
  - [ ] Deferred from item 3's review: CAPTCHA on `accounts/join-distributor/<token>/`.
        P3 — blocked on an actual deployment target existing (needs a public domain +
        registered site keys, per the local-only constraint above).
  - [ ] Deferred from item 3's review: backport rate-limiting to `registrar_tienda`'s
        existing join endpoint, closing the gap the Sprint 1 addendum already flagged ("no
        rate-limiting/CAPTCHA on the join endpoint"). P3 — now depends on the
        rate-limiting deferral above landing first, since item 3 no longer builds a
        mechanism to backport.
  - [ ] Deferred from item 3's review: `confirmar_reset_password` has the same
        TOCTOU redemption race that `DistributorInvitation`'s design specifically accounts
        for (no `select_for_update()` on `PasswordResetToken` lookup-and-mark-used). P2 —
        low real-world exploitability but a real gap in a security-sensitive flow, now
        that it's been noticed.
- [x] **Item 1 — Rebrand ISBER → ISBEN — DONE 2026-07-22 (bundled with Item 2).** All 8
      remaining ISBER occurrences replaced with ISBEN across `templates/base.html`,
      `templates/home.html`, `accounts/views.py`, `settings.py`, `static/css/styles.css`,
      `docs/requirements.md`, `docs/DESIGN.md`, `docs/ux-navigation-wireframes.md`,
      `README.md`, and `PRESENTACION-1BIM/main.tex`.
- [x] **Item 5 — Store location maps — DONE 2026-07-22.** Interactive Leaflet.js map
      (OpenStreetMap tiles — no API key, no billing) accessible to the DISTRIBUTOR role at
      `/catalog/stores/map/`. **What shipped:** `latitude` + `longitude` optional
      DecimalField(9,6) added to `Store` (migration `catalog/0008`); `StoreForm` updated to
      expose both fields so distributors can set coordinates when creating/editing a store;
      `mapa_tiendas` view serializes located stores to JSON and renders markers (clicking a
      marker shows name + address popup); stores without coordinates are listed separately
      below the map with edit links; map auto-centers on the average of all markers (falls
      back to Loja, Ecuador when no stores are mapped yet) and calls `fitBounds` when there
      are multiple markers; "Mapa" nav link added to the DISTRIBUTOR navbar.
      **Scope note:** distributor physical location not mapped — Distributor has no address
      field and is the admin entity rather than a delivery destination; can be added in a
      future sprint by adding address/lat/lng to `Distributor` if needed.
- [x] **Item 4 — Super Administrator dashboard + multi-tenant SaaS foundation — DONE 2026-07-22.**
      PoC (Approach B) implemented after a dedicated `/office-hours` design pass.
      **What shipped:**
      - `SUPER_ADMIN` added to `accounts.Role` — RBAC now covers the operator tier with one
        decorator (`@superuser_required`), no parallel `is_superuser` branch needed.
      - `TenantStatus` (ACTIVE/SUSPENDED/TRIAL/CANCELLED) and `TenantPlan` (FREE/STANDARD/PREMIUM)
        added to `Distributor` (migration `0007`). `plan` is the billing extensibility hook —
        no payment plumbing yet, intentional.
      - `create_superuser` auto-sets `role=SUPER_ADMIN`; the decorator also accepts bare
        `is_superuser=True` for backward compat with existing users.
      - `/accounts/admin-panel/` operator dashboard: all distributors with status/plan/user-count,
        links to tenant detail pages.
      - `/accounts/admin-panel/distributors/<id>/` tenant detail: info card, user list with
        impersonate links, last 20 AuditLog entries, Activate/Suspend action buttons.
      - Activate/Suspend endpoints (POST-only), each writing an `AuditLog` entry.
      - `django-impersonate==1.9.1` wired in: `impersonate.middleware.ImpersonateMiddleware`,
        `impersonate.urls` at `/impersonate/`. Signals connect to AuditLog for
        `impersonation_started` / `impersonation_ended` with both operator and target email stamped.
      - `TenantStatusMiddleware`: SUSPENDED tenants see a 403 page on all non-exempt paths;
        exemptions: `/login/`, `/logout/`, `/admin-panel/`, `/admin/`, `/impersonate/`.
      - Impersonation banner in `base.html` (visible during active impersonation sessions).
      - Superuser home (`/`) now redirects directly to the operator dashboard.
      - `manage.py check` → 0 issues.
      **Open for future sprints:** billing/Stripe webhook to populate `plan`, `suspended_at`
      timestamp + scheduled hard-delete policy, cross-tenant platform-wide analytics view.
- [x] **Item 2 — Role-based navigation/UX redesign — DONE 2026-07-22.** Replaced the flat
      shared nav with per-role menus: DISTRIBUTOR sees Dashboard/Catálogo/Pedidos/Usuarios/
      Auditoría/Notificaciones; VENDOR and STORE_OWNER see Pedidos/Notificaciones; DELIVERY
      sees Entregas/Notificaciones; superuser sees Crear distribuidor/Invitaciones/Admin.
      Login redirects each role directly to their primary page (DISTRIBUTOR → dashboard,
      VENDOR/STORE_OWNER → orders, DELIVERY → deliveries, superuser → superuser home).
      Unauthenticated home redesigned as a landing page explaining the platform.
      All `admin:index` back-links in superuser templates replaced with `{% url 'home' %}`.
      ISBEN rebrand (Items 1 + 2 bundled): all 8 remaining ISBER occurrences across views,
      settings, CSS, and docs replaced with ISBEN.

## Cross-cutting / housekeeping

- [x] Tenant/role-scope the DRF catalog API (`catalog/api_views.py`) — done as part of
      Tier 1 (see above): `IsDistributor` permission + tenant-scoped `get_queryset` +
      cross-tenant FK rejection on create.
- [x] Decide on the committed `proyectoDistribuidora.zip` at the repo root — very
      likely an accidental commit, not evaluated further here.
- [ ] Either actually adopt Tailwind or drop the claim — current CSS
      (`static/css/styles.css`) is hand-written, not Tailwind, despite an earlier commit
      message claiming otherwise.

## Config / Settings menu — deferred sub-items (2026-07-26)

The self-service Configuración hub shipped (profile name, change password, notification
preferences, STORE_OWNER store self-edit, DISTRIBUTOR business profile + invite link,
VENDOR order-alert prefs, plus the global `TIME_ZONE=America/Guayaquil` fix). These were
scoped out in the CEO review and deferred here:

- [ ] **Per-tenant timezone setting** — let each DISTRIBUTOR pick their zone, activated
      per-request via middleware. The global Guayaquil default covers the single-region case
      today; this only matters for multi-region distributors.
- [ ] **Verified email change** — self-service change of the login email (USERNAME_FIELD)
      with a confirmation link to the new address before it takes effect. Account-takeover
      surface; needs its own token flow (mirror PasswordResetToken) and review.
- [ ] **2FA (TOTP) login** — opt-in authenticator-app second factor from Seguridad, with
      recovery codes and lockout handling.
- [ ] **Profile avatar** — blocked on the media/image pipeline decision (local vs Cloudinary,
      see the Tier 4.5 image-storage note).
- [ ] **Default-warehouse selector (DISTRIBUTOR)** — needs an `is_default` flag on Warehouse
      + selection logic; `Warehouse.get_or_create_default` is single-row per distributor today.
