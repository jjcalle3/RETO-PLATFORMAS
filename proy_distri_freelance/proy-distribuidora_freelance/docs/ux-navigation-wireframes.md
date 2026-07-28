# UX Navigation Flows & Conceptual Wireframes
# ISBEN Solutions Distribution Platform

**Author:** UX/Product Design
**Based on:** `docs/requirements.md` (business rules) + the actual running code as of 2026-07-19
**Design tokens:** see [`DESIGN.md`](DESIGN.md) (brand colors, typography, logo assets — not yet applied to the app)
**Last updated:** 2026-07-21 (added Tier 4.5 planned screens — see note below)
**Roles in scope:** DISTRIBUTOR · VENDOR · STORE_OWNER · DELIVERY

> **Tier 4.5 additions (2026-07-21, via `/plan-design-review`):** W-07, W-06, and
> W-17 are extended below and two new screens (W-07b, W-20) are added for the
> Product Catalog Expansion (`docs/TODOS.md` Tier 4.5 — SKU, barcode, category,
> brand, discounts, images, CSV import). **These are planned, not yet
> implemented** — marked `[PLANNED]` throughout, same convention as the rest of
> this document distinguishing built vs. aspirational. Decided this session:
> these screens stay unstyled, matching the current plain-table/Django-default
> look — no brand tokens from DESIGN.md are wired in.

> **This revision replaces the original pre-implementation draft (2026-07-01).** That draft described an aspirational UI (multi-step wizards, JS modals, stat cards, Cloudinary photo gating) written before any of it was built. The actual app is plain server-rendered Django templates with `<table border="1">` layouts, browser `confirm()` dialogs instead of modals, and no client-side framework. Every flow and wireframe below is corrected to match what's actually running; the original aspirational design is preserved as **🔮 Future Upgrade** call-outs so the vision isn't lost, just clearly labeled as not-yet-built.
>
> **Naming note:** this document (like the rest of the codebase) says "ISBEN Solutions." The brand/logo assets say "ISBEN SOLUTION." See `DESIGN.md` for the unresolved discrepancy.

---

## Table of Contents

1. [Global Entry Points & Shared Flows](#1-global-entry-points--shared-flows)
2. [DISTRIBUTOR Flows](#2-distributor-flows)
3. [VENDOR Flows](#3-vendor-flows)
4. [STORE_OWNER Flows](#4-store_owner-flows)
5. [DELIVERY Flows](#5-delivery-flows)
6. [Conceptual Wireframes](#6-conceptual-wireframes)
7. [Appendix: Screen Inventory](#appendix-screen-inventory)
8. [Appendix B: Implementation Status](#appendix-b-implementation-status)

---

## 1. Global Entry Points & Shared Flows

### 1.1 Login Flow (UC-01 · US-01 · FR-01.1, FR-01.2)

Implemented with Django's built-in auth views, not a custom one — `registration/login.html` is the template.

```
[/] Root URL → [Screen: Home] (public link list, not role-gated — see 1.5)

[/login/] Login (django.contrib.auth.views.LoginView)
  ├─► Valid credentials
  │     └─► POST /login/ → LOGIN_REDIRECT_URL = 'home' for EVERY role
  │           (🔮 Future Upgrade: role-based redirect straight to each
  │            role's dashboard/queue, instead of the shared home list)
  │
  └─► Invalid credentials
        └─► [Screen: Login] — "Correo o contraseña incorrectos. Intenta de nuevo."
```

### 1.2 Logout Flow (UC-02 · US-02 · FR-01.5)

```
[Any authenticated screen] → "Cerrar sesión" button (nav, POST form)
  └─► POST /logout/ → Session destroyed → [Screen: Home] (LOGOUT_REDIRECT_URL='home')

[Any protected route after logout]
  └─► role_required redirects unauthenticated users → [Screen: Login]
```

### 1.3 Password Reset Flow (UC-03 · US-03 · FR-01.3, FR-01.4, FR-01.6)

Matches the original design closely — custom-built on the `PasswordResetToken` model (not Django's built-in reset flow).

```
[Screen: Login] → "¿Olvidaste tu contraseña?" link
  └─► [/accounts/password-reset/] Screen: Password Reset — Request
        ├─► Email exists → token created (1h TTL, secrets.token_urlsafe),
        │     email sent via console backend (⚠ not Resend SMTP yet — see below)
        │     └─► [Screen: "Enlace enviado"] — same message either way
        └─► Email not found → same message (no enumeration)

[/accounts/password-reset/<token>/]
  ├─► Token valid → [Screen: Set New Password] → POST → token marked used
  │     → [Screen: Login]
  ├─► Token already used → [Screen: "Enlace inválido"] — "este enlace ya fue utilizado"
  └─► Token expired → [Screen: "Enlace inválido"] — "el enlace ha expirado..."
        → link back to Request screen
```

⚠ **Email backend is `console`, not Resend SMTP** — `settings.EMAIL_BACKEND` prints the reset email to the server log instead of actually sending it. Swapping in real Resend credentials is a deploy-config task (Tier 5), not a UX change.

### 1.4 DISTRIBUTOR Onboarding — NEW, not in the original draft (DR-08)

The original draft had no self-service path for creating a `Distributor` at all. The actual flow is superuser-gated (this deployment serves one real client, not a public multi-tenant signup funnel) but combines company + first admin creation into one step:

```
[Django superuser, via /admin/ or knowing the URL directly]
  └─► [/accounts/distributors/new/] Screen: Crear Distribuidor
        Fields: distributor_name, distributor_email, admin_email,
                admin_password1, admin_password2
        └─► POST → Distributor + first DISTRIBUTOR user created atomically
              └─► [Screen: accounts index] (as the superuser, not logged in as the new admin)
```

(🔮 Future Upgrade: this whole flow currently has no discoverable entry point in the authenticated UI at all — a superuser has to know the URL or use `/admin/`. A small "platform admin" landing page listing existing distributors + a "create new" button would close that.)

### 1.5 STORE_OWNER Self-Registration via Invite Link — NEW, not in the original draft (DR-08)

Designed specifically for non-technical store owners: no signup form to discover, no distributor to pick from a list — the distributor shares a link (WhatsApp, printed QR code) that already knows which tenant it belongs to.

```
[DISTRIBUTOR's own dashboard] → "Enlace de registro para dueños de tienda" box
  shows: https://.../accounts/join/<opaque-token>/
  + "Generar nuevo enlace" button (revokes the old one, issues a new token)

[Store owner taps/scans the link] → [/accounts/join/<token>/]
  ├─► Token matches a Distributor → [Screen: Registrar mi tienda]
  │     Fields: owner_email, owner_password1/2, store_name, store_address, store_phone
  │     └─► POST → User(role=STORE_OWNER) + Store created atomically,
  │           auto-logged-in → [Screen: Home]
  │           (Store starts with NO vendor assigned — DR-01's existing
  │           "no tienes vendedor asignado" message covers this until the
  │           distributor assigns one)
  │
  └─► Token doesn't match any Distributor (bogus/expired link) → 404
```

(🔮 Future Upgrade: an actual rendered QR code image on the distributor dashboard, not just the raw URL as text — the distributor currently has to generate one themselves with an external tool to print it.)

### 1.6 Home Screen — shared landing page (not role-gated)

```
[/] for any authenticated user, regardless of role
  └─► Plain link list: Usuarios · Catálogo · Pedidos · Entregas ·
        Auditoría · Django Admin
```

⚠ This list is **not filtered by role** — a VENDOR sees a "Catálogo" link they'll get a 403 on if clicked (that view is `role_required('DISTRIBUTOR')`). The nav bar (all screens) has the same issue for a few items. (🔮 Future Upgrade: role-scoped home/nav, or redirect straight past this page per role — see 1.1.)

---

## 2. DISTRIBUTOR Flows

### 2.1 User Management (US-24 · FR-02.1)

Different from the original draft's single "create user with a role dropdown" — the role is fixed by which page you're on, to prevent picking the wrong one by mistake (DR-07).

```
[/accounts/users/] Screen: Usuarios — {distributor name}
  ├─► "+ Admin Distribuidor" / "+ Vendedor" / "+ Dueño de Tienda" / "+ Repartidor"
  │     → [/accounts/users/new/<role>/] — role fixed by the link clicked,
  │       no dropdown; email + password only
  │       └─► Valid submit → [Screen: Usuarios]
  │
  └─► Row "Editar" → [/accounts/users/<id>/edit/]
        Fields: email, role (dropdown — can reassign role after creation), is_active
        (distributor is NOT editable here — reassigning a user to a
        different tenant is not something this screen allows)
```

### 2.2 Product Catalog (UC-04 · US-04, US-05, US-06 · FR-03.1–FR-03.4)

Matches the original draft closely, one combined list page instead of a dedicated dashboard route.

```
[/catalog/] Screen: Catálogo (Tiendas + Productos + Inventario, all on one page)
  └─► Productos section
        ├─► "+ Nuevo Producto" → [/catalog/products/new/] → save → back to [/catalog/]
        ├─► Row "Editar" → [/catalog/products/<id>/edit/]
        ├─► Row "Desactivar" (is_active=True → False, DR-06 soft-delete,
        │     no confirmation dialog currently — 🔮 Future Upgrade: add one,
        │     matching NFR-04.6's "critical actions need confirmation")
        └─► Row "Reactivar" (is_active=False → True)
```

### 2.3 Vendor Inventory Assignment (UC-05 · US-07 · FR-03.5, FR-04.1)

```
[/catalog/] → Inventario section → link to /catalog/inventory/assign/<vendor_id>/
  (vendor_id must be looked up from the Usuarios page first — no vendor
  picker on this screen itself; 🔮 Future Upgrade: a vendor dropdown here
  instead of requiring the distributor to already know the ID)
  └─► Select product (dropdown) + quantity → save → VendorInventory upserted
        → back to [/catalog/]
```

### 2.4 Store Management

```
[/catalog/] → Tiendas section
  ├─► "+ Nueva Tienda" → [/catalog/stores/new/]
  │     Fields: name, address, phone_number, owner (dropdown, own tenant only),
  │     vendor (dropdown, own tenant only, nullable per DR-01)
  └─► Row "Editar" → [/catalog/stores/<id>/edit/]
```

### 2.5 Operations Dashboard (UC-06 · US-08 · FR-08.1–FR-08.4)

The one screen that's actually *more* built out than the original draft envisioned — filters and summary metrics were added in the same pass.

```
[/accounts/dashboard/] Screen: Dashboard — {distributor name}
  ├─► Low-stock banner (if any VendorInventory row < threshold) — "⚠ N producto(s) con stock bajo"
  ├─► Filters form (GET params): date_from, date_to, vendor, store, status
  │     → "Filtrar" reloads the page with filtered results applied to
  │       BOTH the order list and the metrics below
  ├─► Summary metrics table: total pedidos · cumplidos (CONFIRMED) ·
  │     rechazados · tiempo promedio de cumplimiento
  ├─► Pedidos por estado (grouped counts)
  ├─► Pedidos (up to 50, newest first) — row links to order detail
  └─► Inventario por vendedor — low-stock rows highlighted + "⚠ Stock bajo" text
```

(🔮 Future Upgrade: the original draft's clickable summary stat-cards that pre-filter the table on click — currently the filters are a separate form, not wired to the metrics cards.)

### 2.6 Audit Log Consultation (UC-07 · US-09 · FR-09.5)

```
[/audit/] Screen: Registro de Auditoría — DISTRIBUTOR only, own-tenant entries only
  Chronological table: timestamp · actor · action · previous_status → new_status · details (raw JSON)
  Read-only, append-only, no delete/edit controls
```

⚠ This is a standalone page (`/audit/`), not reached via a "Ver Auditoría" button from an order detail page as the original draft envisioned — there's currently no link from `ver_pedido.html` to the filtered audit trail for that specific order. (🔮 Future Upgrade: add that link, and render `details` as formatted key/value pairs instead of raw JSON.)

---

## 3. VENDOR Flows

### 3.1 Vendor Order List + Polling (UC-10 · US-10 · FR-06.1, FR-06.6, FR-10.1)

```
[/orders/] Screen: Pedidos (shared template across all 3 order-visible roles;
  VENDOR sees only orders where vendor = self)
  └─► JS polls GET /api/orders/pending/ every 30s
        └─► New PENDING order → row prepended to the table, no page reload
              (no toast/sound — just the new row appearing, plus a text
              status line "N pedido(s) nuevo(s).")
```

### 3.2 Accept Order (UC-11 · US-11 · FR-04.3, FR-04.4, FR-06.2–FR-06.4)

```
[/orders/<id>/] Order detail — status = PENDING, viewer = assigned vendor
  └─► "Aceptar" button (POST form, browser confirm() dialog — not a styled
        modal)
        ├─► Stock sufficient (transaction.atomic + select_for_update)
        │     → inventory deducted · status → ACCEPTED
        │       AuditLog + Notification to store owner written
        │       → same detail page, success message banner
        └─► Insufficient stock → nothing written, order stays PENDING
              → per-item error message banner ("Arroz: disponible 3, solicitado 5")
              AuditLog entry written too (order_accept_failed, FR-09.3)
```

### 3.3 Reject Order (UC-12 · US-12 · FR-06.2, FR-06.4)

```
[/orders/<id>/] — status = PENDING
  └─► "Rechazar" button → [/orders/<id>/reject/] Screen: Rechazar Pedido
        Optional textarea, max 500 chars, browser confirm() on submit
        └─► POST → status → REJECTED, AuditLog + Notification (with reason
              if provided) → back to order detail
```

### 3.4 Dispatch Order (UC-13 · US-13 · FR-06.5)

```
[/orders/<id>/] — status = ACCEPTED
  └─► "Marcar como despachado" button (POST form, confirm())
        → status → DISPATCHED, AuditLog + Notification → same page
```

### 3.5 Resolve a Delivery Issue — NEW, not in the original draft (DR-09)

```
[/orders/<id>/] — status = DELIVERY_ISSUE, viewer = assigned vendor
  └─► "Resolver incidencia" → [/orders/<id>/resolve-issue/]
        Shows the store owner's issue_description (read-only)
        Textarea: resolution_notes (required)
        └─► POST → status → CONFIRMED, AuditLog + Notification to store owner
```

### 3.6 Vendor Inventory View — ⚠ NOT IMPLEMENTED (UC-09 · FR-04.2)

The original draft's "Mi Inventario" screen (a vendor browsing their own stock levels) **was never built.** There is no route under `orders/` or `catalog/` a `VENDOR` can reach to see their own `VendorInventory` rows — `catalog/` is entirely `role_required('DISTRIBUTOR')`. The only place vendor stock is currently visible to a vendor is indirectly, inside the per-item error message when an accept fails from insufficient stock.

(🔮 Future Upgrade: a read-only `VendorInventory.objects.filter(vendor=request.user)` list, e.g. at `/orders/inventory/` or `/catalog/my-inventory/`. This closes UC-09, which UC-11 formally `«include»`s — right now that inclusion is honored functionally, at accept time, just with no dedicated browsing screen.)

---

## 4. STORE_OWNER Flows

### 4.1 Place Order (UC-14 · US-14 · FR-05.1, FR-05.3, FR-05.4 · DR-01)

**Materially simpler than the original draft's 3-step wizard.** No step indicator, no store-selection step (a store owner picks their store via a single dropdown, not a radio-list sub-screen), no review-then-confirm step — items are added one at a time to an already-created PENDING order.

```
[/orders/new/] Screen: Crear Pedido — STORE_OWNER only
  Field: store (dropdown, scoped to stores owned by this user)
  ├─► Store has no vendor assigned → error shown inline on submit:
  │     "Esta tienda no tiene un vendedor asignado. Contacta al distribuidor."
  └─► Store has a vendor → POST creates Order(status=PENDING, vendor=store.vendor)
        → redirects straight to [/orders/<id>/] (the new order's detail page)

[/orders/<id>/] — status = PENDING → "+ Agregar Item" link
  └─► [/orders/<order_id>/items/new/] Screen: Agregar Item
        Fields: product (dropdown, scoped to what the assigned vendor
        actually stocks — FR-05.3), quantity
        └─► POST → unit_price_at_time snapshotted server-side from
              Product.unit_price (never client-supplied, FR-05.4)
              → back to order detail, item appears in the items table
              → repeat "+ Agregar Item" for each product

  Order stays PENDING, editable (items can be added/edited/removed) until
  the store owner is done — there is no explicit "submit/confirm" step
  beyond creating the order itself; it's visible to the vendor (and
  poll-detected) from the moment it's created, even with zero items.
```

(🔮 Future Upgrade — this is where the original draft's vision is genuinely better and worth building: a true 3-step wizard — select store → build the order with a quantity-stepper grid across all available products at once → review totals → confirm — rather than the current "create empty order, then add items one form-submit at a time." The current flow also means a vendor could see and even *accept* a zero-item order before the store owner finishes adding items, since nothing currently blocks acceptance based on item count reaching zero mid-edit — `aceptar_pedido` does check for at least one item, but a race where the store owner is still adding items while the vendor is looking at the order is possible. Worth a NOTES: not exploited in current tests but a real gap if traffic picks up.)

### 4.2 Track Order Status (UC-15 · US-15 · FR-05.5)

```
[/orders/] Screen: Pedidos — STORE_OWNER sees only their own stores' orders
  Row click → [/orders/<id>/] full detail, including any issue-report/
  resolution notes (see 4.4) and rejection reason
```

No separate "Order History" screen from the original draft — `/orders/` serves this role for all three order-visible roles.

### 4.3 Cancel Pending Order (US-23)

```
[/orders/<id>/] — status = PENDING
  └─► "Cancelar pedido" button (POST form, confirm())
        → status → REJECTED, rejection_reason = "Cancelado por el
          propietario de la tienda", AuditLog written
          (no Notification — it's the store owner's own action, nobody
          else needs telling)
```

### 4.4 Confirm Receipt / Report a Delivery Issue — NEW, not in the original draft (DR-09)

This entirely replaces the original draft's photo-upload-gated delivery confirmation (see §5.2) as the actual source of truth for "did this order arrive correctly." `DELIVERED` is **not terminal** — it's "the delivery person says they dropped it off; awaiting the store owner."

```
[/orders/<id>/] — status = DELIVERED
  ├─► "Confirmar recepción" button (confirm()) → POST /orders/<id>/confirm-receipt/
  │     → status → CONFIRMED, AuditLog + Notification to vendor
  │
  └─► "Reportar problema" link → [/orders/<id>/report-issue/]
        Textarea: issue_description (required)
        └─► POST → status → DELIVERY_ISSUE
              Notification to vendor AND to the delivery person who
              confirmed it (if one is on record)
              → vendor later resolves it (see 3.5) → CONFIRMED
```

### 4.5 Resubmit Rejected Order — ⚠ NOT IMPLEMENTED (US-22)

`Order.previous_order` exists on the model (a self-FK meant to link a resubmission back to its rejected predecessor), but **nothing sets it** — there is no "Reenviar pedido" button or `/orders/<id>/resubmit/` route anywhere in the app. A store owner whose order was rejected has to start over with a brand-new, unlinked order via 4.1.

(🔮 Future Upgrade: exactly as the original draft specified — a resubmit action that clones the rejected order's items at *current* catalog prices into a new `PENDING` order with `previous_order` set.)

### 4.6 Notifications (US-16 · FR-10.2–FR-10.4)

**Not STORE_OWNER-exclusive as the original draft assumed** — `VENDOR` and `DELIVERY` also receive notifications now (DR-09's issue-report/resolve flow notifies across roles). The nav item and unread count are visible to any authenticated role.

```
[Any authenticated screen] → nav: "Notificaciones (N)" — N = unread count,
  loaded via a context processor on every page render, any role
  └─► [/accounts/notifications/] Screen: Notificaciones
        ├─► "Marcar todas como leídas" button
        └─► Per-row "Marcar como leída" button (unread rows only)
              Each row links to the related order, if any
```

---

## 5. DELIVERY Flows

### 5.1 Confirmations Screen — different in kind from the original draft (UC-16 · US-17 · FR-07.1)

The original draft's "Cola de Entregas" was a queue of `DISPATCHED` orders awaiting pickup, with a click-through to a per-order confirm screen. **What's actually built is the reverse**: a log of *already-made* confirmations, and a separate, order-list-free "make a new confirmation" form.

```
[/deliveries/queue/] Screen: Cola de Entregas
  Table of EXISTING DeliveryConfirmation rows (order · repartidor · foto ID
  opcional · fecha), own-distributor scope
  → "+ Confirmar Entrega" link (does not require browsing this list first)
```

(🔮 Future Upgrade: this is the clearest remaining gap from the original design intent — rename/restructure so `/deliveries/queue/` actually shows *pending* `DISPATCHED` orders (store name, address, product summary, per UC-16's spec) with a "Confirmar" action per row, and keep the confirmation log as a separate "Historial" screen.)

### 5.2 Confirm Delivery — Cloudinary photo validation superseded by DR-09 (UC-17 · US-18 · FR-07.2–FR-07.5)

```
[/deliveries/new/confirm/] Screen: Confirmar Entrega
  Fields: order (dropdown, scoped to this distributor's DISPATCHED orders
  only), photo_public_id (optional text field), confirmed_at
  └─► POST (transaction.atomic) →
        DeliveryConfirmation created, delivery_user = self (server-side,
        never client-supplied)
        Order.status → DELIVERED (not terminal — see §4.4)
        AuditLog + Notification to store owner
        → [/deliveries/queue/]
```

⚠ **`photo_public_id` is optional and never validated** — per DR-09, photo-based proof-of-delivery was dropped from scope entirely (not just the Cloudinary SDK piece). The store owner's explicit confirm-or-dispute action (§4.4) is the actual source of truth now, not a photo. The original draft's "browser-direct Cloudinary upload, server validates public_id, rejects external URLs" flow does not exist and is not planned — it's superseded, not deferred.

---

## 6. Conceptual Wireframes

Layouts below reflect the actual rendered HTML: plain `<table border="1">` data tables inside the shared `base.html` shell (header with nav + session bar, footer), no cards, no icons, no client-side JS beyond the vendor-dashboard poller. Every screen extends `base.html` and gets its nav/session-bar/messages block for free — that shell isn't repeated in each wireframe below.

---

### W-04 · Global Navigation Shell (Authenticated)

**Template:** `templates/base.html` — shared by every screen.

```
┌──────────────────────────────────────────────────────────────────┐
│  ISBEN Solutions — Distribuidora                                  │
│  [Inicio] [Dashboard]* [Usuarios] [Catálogo] [Pedidos] [Entregas] │
│  [Auditoría] [Notificaciones (N)]      [correo (Rol)] [Cerrar sesión] │
├──────────────────────────────────────────────────────────────────┤
│  {% if messages %} success/error banners {% endif %}              │
│                                                                    │
│  [Page content]                                                   │
│                                                                    │
├──────────────────────────────────────────────────────────────────┤
│  Loja — Ecuador            {current date/time}                    │
└──────────────────────────────────────────────────────────────────┘
```
`*` "Dashboard" link only shown for `DISTRIBUTOR`. Every other nav item is shown to **every** authenticated role regardless of whether they're allowed on that page (see §1.6) — clicking one you can't access 403s.

(🔮 Future Upgrade: role-filtered nav; sidebar layout instead of a flat top nav for desktop, as the original draft envisioned; hamburger collapse under 360px per NFR-04.2 — currently no responsive breakpoint logic exists in `styles.css` at all.)

---

### W-01 · Login

**Route:** `/login/` · **Template:** `catalog/templates/registration/login.html`

```
┌─[Nav Shell]────────────────────────────┐
│  Iniciar sesión                        │
│                                         │
│  [Error text — only on failed attempt] │
│  "Correo o contraseña incorrectos."    │
│                                         │
│  {{ form.as_p }}  ← email + password,  │
│    Django's default AuthenticationForm │
│    rendering, no custom styling        │
│                                         │
│  [Btn: Ingresar]                       │
│  [Link: ¿Olvidaste tu contraseña?]     │
└─────────────────────────────────────────┘
```

---

### W-02 · Password Reset — Request

**Route:** `/accounts/password-reset/` · **Template:** `accounts/solicitar_reset_password.html`

```
┌─[Nav Shell]────────────────────────────┐
│  Recuperar contraseña                  │
│  "Ingresa tu correo electrónico y te   │
│   enviaremos un enlace..."             │
│  {{ formulario.as_p }}  ← email        │
│  [Btn: Enviar enlace]  [Cancelar]      │
└─────────────────────────────────────────┘

→ on submit, always: "accounts/password_reset_solicitado.html"
┌─────────────────────────────────────────┐
│  Enlace enviado                        │
│  "Si el correo ingresado está          │
│   registrado, recibirás un enlace..."  │
│  [Volver a iniciar sesión]             │
└─────────────────────────────────────────┘
```

---

### W-03 · Set New Password / Token Error

**Route:** `/accounts/password-reset/<token>/`

```
┌─[Nav Shell]────────────────────────────┐   ┌─[Nav Shell]────────────────┐
│  Restablecer contraseña                │   │  Enlace inválido           │
│  {{ formulario.as_p }}  ← new pw x2    │   │  "este enlace ya fue       │
│  [Btn: Guardar nueva contraseña]       │   │   utilizado" / "expiró"    │
└─────────────────────────────────────────┘   │  [Solicitar nuevo enlace] │
                                               └─────────────────────────────┘
```

---

### W-04b · Distributor Onboarding (superuser) — NEW

**Route:** `/accounts/distributors/new/` · **Template:** `accounts/crear_distribuidor.html` · **Role:** Django superuser only

```
┌─[Nav Shell]────────────────────────────┐
│  ← Volver (→ /admin/)                  │
│  Crear Distribuidor                    │
│  "Esto crea la distribuidora y su      │
│  primera cuenta de administrador       │
│  (rol DISTRIBUTOR) en un solo paso."   │
│                                         │
│  {{ formulario.as_p }}                 │
│   distributor_name · distributor_email │
│   admin_email · admin_password1/2      │
│                                         │
│  [Btn: Guardar]  [Cancelar]            │
└─────────────────────────────────────────┘
```

---

### W-04c · Store Owner Self-Registration (invite link) — NEW

**Route:** `/accounts/join/<token>/` · **Template:** `accounts/registrar_tienda.html` · **Role:** unauthenticated, token-gated

```
┌─[Nav Shell]────────────────────────────┐
│  Registrar mi tienda — {distribuidor}  │
│  "Completa tus datos para crear tu     │
│  cuenta y empezar a hacer pedidos..."  │
│                                         │
│  {{ formulario.as_p }}                 │
│   owner_email · owner_password1/2      │
│   store_name · store_address · store_phone │
│                                         │
│  [Btn: Crear mi cuenta]                │
└─────────────────────────────────────────┘
```

---

### W-05 · Distributor Operations Dashboard

**Route:** `/accounts/dashboard/` · **Template:** `accounts/dashboard.html` · **Role:** DISTRIBUTOR

```
┌─[Nav Shell]──────────────────────────────────────────────────────┐
│  Dashboard — {distributor name}                                  │
│                                                                   │
│  [⚠ N producto(s) con stock bajo — banner, only if N > 0]        │
│                                                                   │
│  FILTROS (GET form)                                              │
│  [Desde][Hasta][Vendedor ▼][Tienda ▼][Estado ▼] [Filtrar] [Limpiar] │
│                                                                   │
│  RESUMEN                                                          │
│  ┌───────────────────────────┬────────┐                          │
│  │ Total de pedidos          │  N     │                          │
│  │ Cumplidos (confirmados)   │  N     │                          │
│  │ Rechazados                │  N     │                          │
│  │ Tiempo promedio cumplim.  │ Xd Xh  │                          │
│  └───────────────────────────┴────────┘                          │
│                                                                   │
│  PEDIDOS POR ESTADO (table: estado · cantidad)                   │
│                                                                   │
│  PEDIDOS (up to 50, newest first — # links to detail)            │
│                                                                   │
│  INVENTARIO POR VENDEDOR                                          │
│  (rows below threshold highlighted + "⚠ Stock bajo" text)        │
└─────────────────────────────────────────────────────────────────┘
```

(🔮 Future Upgrade: the original draft's clickable stat-cards, product×vendor matrix layout instead of a flat row list, and a proper date-range picker widget instead of two plain `<input type="date">` fields.)

---

### W-06 · Catálogo (Products + Stores + Inventory, one page)

**Route:** `/catalog/` · **Template:** `catalog/index.html` · **Role:** DISTRIBUTOR

```
┌─[Nav Shell]──────────────────────────────────────────────────────┐
│  Tiendas                                    [+ Nueva Tienda]     │
│  (table: nombre · dirección · teléfono · distribuidor · dueño ·  │
│   [Editar][Eliminar])                                            │
│  ──────────                                                       │
│  Productos                                  [+ Nuevo Producto]   │
│                                       [+ Importar CSV] [PLANNED] │
│                                                                    │
│  BUSCAR Y FILTRAR (GET form)                          [PLANNED]  │
│  [Buscar: nombre/SKU/código de barras____] [Categoría ▼]         │
│  [Marca ▼] [Estado de stock ▼: Todos/En stock/Bajo/Agotado]      │
│  [☐ Solo en promoción]  [Buscar]  [Limpiar]                      │
│  Empty state: "No se encontraron productos con estos filtros.    │
│  [Limpiar filtros]" — matches the W-17/W-18 empty-state pattern. │
│                                                                    │
│  (table: sku · nombre · categoría · marca · precio ·             │
│   precio con descuento (si aplica) · estado · stock ·            │
│   [Editar][Desactivar/Reactivar])                    [PLANNED]   │
│  ──────────                                                       │
│  Inventario de Vendedores                                        │
│  "Para asignar inventario usa /catalog/inventory/assign/<id>/    │
│   (obtener ID desde Usuarios)"                                   │
│  (table: vendedor · producto · cantidad (+"⚠ Stock bajo" text)   │
│   · [Editar][Eliminar])                                          │
└─────────────────────────────────────────────────────────────────┘
```

Combines the original draft's separate W-06 (Product List) and W-08 (Assign Inventory grid) into the one real page. (🔮 Future Upgrade: split into separate tabs/pages as the app grows — this single page will get long once a distributor has more than a handful of products/stores.)

`[PLANNED]` rows above are Tier 4.5 additions (search/filter, CSV import entry
point, extended product table columns) — not yet implemented as of this
document's last update.

---

### W-07 · Create / Edit Product

**Route:** `/catalog/products/new/`, `/catalog/products/<id>/edit/` · **Role:** DISTRIBUTOR

**Current (5 fields):**
```
┌─[Nav Shell]────────────────────────────┐
│  ← Volver al Catálogo                  │
│  Crear/Editar Producto                 │
│  {{ formulario.as_p }}                 │
│   name · description · unit_price ·    │
│   is_active · low_stock_threshold      │
│  [Btn: Guardar]  [Cancelar]            │
└─────────────────────────────────────────┘
```

**[PLANNED] Extended (Tier 4.5, 12 fields, grouped):**
```
┌─[Nav Shell]──────────────────────────────────────────────────────┐
│  ← Volver al Catálogo                                             │
│  Crear/Editar Producto                                            │
│                                                                    │
│  ── Identidad ──                                                  │
│   name · sku · barcode                                            │
│  ── Clasificación ──                                               │
│   category (dropdown ▼) · brand (dropdown ▼)                      │
│   unit_of_measure (dropdown ▼: Pieza/Caja/Paquete/Botella/Kg/Litro)│
│  ── Precio y Stock ──                                              │
│   description · unit_price                                        │
│   status (dropdown ▼: Activo/Inactivo/Descontinuado)              │
│   low_stock_threshold                                             │
│  ── Imágenes ──                                                    │
│   main_image (file) · additional_images (file, multiple)          │
│                                                                    │
│  [Btn: Guardar]  [Cancelar]                                       │
│                                                                    │
│  ── shown only when editing an existing product ──                │
│  Descuento actual: {ninguno | "15% hasta 2026-08-01"}             │
│  [link → W-07b: Gestionar descuento]                               │
└────────────────────────────────────────────────────────────────────┘
```

`is_active` boolean is replaced by the `status` dropdown per Tier 4.5's
resolved DR-06 fork. Grouped into 4 plain `<fieldset><legend>` sections — no
CSS/framework needed, still matches the unstyled aesthetic, but scannable at
12 fields where the flat rendering (fine at 5 fields) would not be.

---

### W-07b · Manage Discount — NEW [PLANNED]

**Route:** `/catalog/products/<id>/discount/` · **Role:** DISTRIBUTOR

```
┌─[Nav Shell]────────────────────────────┐
│  ← Volver al producto                  │
│  Gestionar Descuento — {product name}  │
│  Precio regular: ${unit_price}         │
│  {{ formulario.as_p }}                 │
│   discount_type (radio: Porcentaje /   │
│     Monto fijo)                        │
│   discount_value                       │
│   start_date · end_date                │
│  Precio final (calculado): ${preview}  │
│  [Btn: Guardar]  [Btn: Quitar descuento]  [Cancelar]│
└─────────────────────────────────────────┘
```

Separate screen, not inline fields on W-07 — matches the existing pattern of
`VendorInventory` assignment (W-08) being its own screen rather than crammed
into the Product form.

---

### W-20 · CSV Import — NEW [PLANNED]

**Route:** `/catalog/products/import/` · **Role:** DISTRIBUTOR

```
┌─[Nav Shell]────────────────────────────┐
│  ← Volver al Catálogo                  │
│  Importar Productos desde CSV          │
│  "El archivo debe tener las columnas:  │
│  nombre, sku, código de barras,        │
│  categoría, marca, precio, unidad de   │
│  medida, stock mínimo"                 │
│  {{ formulario.as_p }}                 │
│   archivo_csv (file, .csv only)        │
│  [Btn: Importar]  [Cancelar]           │
└─────────────────────────────────────────┘

→ on submit, results screen:
┌─[Nav Shell]────────────────────────────┐
│  Resultado de Importación              │
│  ✓ 47 productos importados             │
│  ⚠ 3 filas omitidas:                   │
│  ┌───────────────────────────────────┐ │
│  │ Fila 12: SKU "ABC123" ya existe   │ │
│  │ Fila 28: categoría "Lacteos" no   │ │
│  │   encontrada                      │ │
│  │ Fila 41: precio inválido          │ │
│  └───────────────────────────────────┘ │
│  [Volver al Catálogo]                  │
└─────────────────────────────────────────┘
```

Row-level skip, not all-or-nothing — valid rows import, invalid rows are
skipped and listed in this report. Loading state: browser's default loading
indicator only, no custom "procesando..." UI — consistent with every other
form submission in this app.

---

### W-08 · Assign Inventory to Vendor

**Route:** `/catalog/inventory/assign/<vendor_id>/` · **Role:** DISTRIBUTOR

```
┌─[Nav Shell]────────────────────────────┐
│  Asignar Inventario — {vendor email}   │
│  {{ formulario.as_p }}                 │
│   product (dropdown) · quantity        │
│  [Btn: Guardar]  [Cancelar]            │
└─────────────────────────────────────────┘
```

---

### W-09 · User Management (Distributor)

**Route:** `/accounts/users/` · **Template:** `accounts/index.html` · **Role:** DISTRIBUTOR

```
┌─[Nav Shell]──────────────────────────────────────────────────────┐
│  Usuarios — {distributor name}                                   │
│  [+ Admin Distribuidor] [+ Vendedor] [+ Dueño de Tienda] [+ Repartidor] │
│                                                                   │
│  Enlace de registro para dueños de tienda                        │
│  {full invite URL as text}   [Generar nuevo enlace]              │
│                                                                   │
│  (table: email · rol · [Editar][Eliminar])                       │
└─────────────────────────────────────────────────────────────────┘
```

No password field on this list screen, no "Active" toggle in the table (it's on the edit form) — different from the original draft's inline table. Role is not user-selectable at creation (see §2.1 — DR-07); it *is* editable afterward via "Editar."

---

### W-10 · Vendor Order List (with Polling)

**Route:** `/orders/` (as VENDOR) · **Template:** `orders/index.html`

```
┌─[Nav Shell]──────────────────────────────────────────────────────┐
│  Pedidos                                                          │
│  {status text — updated by JS poll}                              │
│  (table: # · tienda · vendedor · estado · creado · [Ver])         │
│   ← rows for ALL this vendor's orders (not split into pending/    │
│     accepted sub-tables as the original draft showed)             │
└─────────────────────────────────────────────────────────────────┘
```

JS: `setInterval(30000)` → `fetch('/api/orders/pending/')` → new `PENDING` rows prepended to the same table (no separate "Last updated" timestamp shown). No dedicated "Mi Inventario" section (see §3.6 — not built).

---

### W-11 · Order Detail — Vendor View

**Route:** `/orders/<id>/` (vendor session) · **Template:** `orders/ver_pedido.html`

```
┌─[Nav Shell]──────────────────────────────────────────────────────┐
│  ← Volver a Pedidos                                               │
│  Pedido #001 — {estado}                                          │
│  Tienda / Vendedor / Creado / Actualizado                        │
│  [Motivo de rechazo — if any] [Incidencia reportada — if any]    │
│  [Resolución — if any]                                            │
│  Estado: Pendiente → Aceptado → Despachado → Entregado →         │
│          Confirmado (o Incidencia → Confirmado) | Rechazado      │
│                                                                   │
│  ── if PENDING ──                                                 │
│  [form: Aceptar]  [link→W-11b: Rechazar]                          │
│  ── if ACCEPTED ──                                                │
│  [form: Marcar como despachado]                                  │
│  ── if DELIVERY_ISSUE ──                                          │
│  [link→W-11c: Resolver incidencia]                                │
│                                                                   │
│  Items del Pedido (product · qty · unit price — no edit/delete   │
│  controls for VENDOR, those are STORE_OWNER-only)                │
└─────────────────────────────────────────────────────────────────┘
```

Every action button is a plain `<form method="post">` with `onsubmit="return confirm('...')"` — a native browser dialog, not a styled modal.

---

### W-11b · Reject Order

**Route:** `/orders/<id>/reject/` · **Template:** `orders/rechazar_pedido.html`

```
┌─[Nav Shell]────────────────────────────┐
│  ← Volver al pedido                    │
│  Rechazar Pedido #001                  │
│  Tienda: {store}                       │
│  Motivo (opcional): [textarea]         │
│  [Btn: Rechazar pedido]  [Cancelar]    │
└─────────────────────────────────────────┘
```

---

### W-11c · Resolve Delivery Issue — NEW

**Route:** `/orders/<id>/resolve-issue/` · **Template:** `orders/resolver_incidencia.html`

```
┌─[Nav Shell]────────────────────────────┐
│  ← Volver al pedido                    │
│  Resolver Incidencia — Pedido #001     │
│  Tienda: {store}                       │
│  Problema reportado: {issue_description}│
│  Notas de resolución: [textarea]       │
│  [Btn: Marcar como resuelta] [Cancelar]│
└─────────────────────────────────────────┘
```

---

### W-12 · Store Owner Order List

**Route:** `/orders/` (as STORE_OWNER) — same template/screen as W-10, scoped to the owner's own stores' orders. No separate dashboard with quick-actions/notifications-banner as the original draft (W-12) showed — "Nuevo Pedido" is reached the same way any other role reaches their section, via the nav.

---

### W-13 · Place Order

**Route:** `/orders/new/` · **Template:** `orders/crear_pedido.html` · **Role:** STORE_OWNER

```
┌─[Nav Shell]────────────────────────────┐
│  ← Volver a Pedidos                    │
│  Crear Pedido                          │
│  {{ formulario.as_p }}  ← store (dropdown, own stores only) │
│  [Btn: Guardar]  [Cancelar]            │
└─────────────────────────────────────────┘
      │
      ▼ (on submit, redirects straight into the new order's detail page)
```

Replaces the original draft's W-13/W-14/W-15/W-15b 4-screen wizard (select store → build cart → review → confirm) — see the 🔮 Future Upgrade note in §4.1 for why the wizard is still worth building.

---

### W-14 · Add Item to Order

**Route:** `/orders/<order_id>/items/new/` · **Template:** `orders/crear_item_pedido.html` · **Role:** STORE_OWNER, order must be PENDING

```
┌─[Nav Shell]────────────────────────────┐
│  ← Volver al pedido                    │
│  Agregar Item al Pedido #001           │
│  Tienda / Vendedor / Estado            │
│  {{ formulario.as_p }}                 │
│   product (dropdown, scoped to what    │
│   the vendor stocks) · quantity        │
│  [Btn: Guardar]  [Cancelar]            │
└─────────────────────────────────────────┘
```

No live running total / quantity stepper UI — plain `<select>` + number input, one item per form submission.

---

### W-16 · Order Detail — Store Owner View

**Route:** `/orders/<id>/` (store owner session) — same template as W-11, different action set:

```
── if PENDING ──
[form: Cancelar pedido]   [link: + Agregar Item]
[Editar]/[Eliminar] per item row
── if REJECTED ──
[Motivo de rechazo shown] — no "Reenviar pedido" button (§4.5, not built)
── if DELIVERED ──
[form: Confirmar recepción]   [link→ Reportar problema]
── if DELIVERY_ISSUE / CONFIRMED ──
read-only
```

---

### W-16b · Report Delivery Issue — NEW

**Route:** `/orders/<id>/report-issue/` · **Template:** `orders/reportar_incidencia.html`

```
┌─[Nav Shell]────────────────────────────┐
│  ← Volver al pedido                    │
│  Reportar Incidencia — Pedido #001     │
│  Tienda: {store}                       │
│  Describe el problema: [textarea]      │
│  [Btn: Reportar problema]  [Cancelar]  │
└─────────────────────────────────────────┘
```

---

### W-17 · Notification List — all roles, not STORE_OWNER-exclusive

**Route:** `/accounts/notifications/` · **Template:** `accounts/notificaciones.html`

```
┌─[Nav Shell]──────────────────────────────────────────────────────┐
│  Notificaciones                     [Marcar todas como leídas]   │
│  (table: mensaje · pedido (link) · fecha · estado · [Marcar       │
│   como leída] per unread row)                                    │
│  {empty state: "No tienes notificaciones."}                      │
│                                                                    │
│  [PLANNED, Tier 4.5] Bundled low-stock digest example row:       │
│  "⚠ 4 producto(s) con stock bajo: Arroz, Aceite, Azúcar,          │
│   Leche" | — | 2026-07-22 | No leída | [Marcar como leída]       │
└─────────────────────────────────────────────────────────────────┘
```

No blue-dot/grey-dot visual distinction as the original draft showed — read/unread is a text column ("Leída"/"No leída").

**[PLANNED, Tier 4.5]:** one row per digest event (not one row per product) —
`pedido` column blank for this row type since it's not order-related, same as
the column already tolerating a null order for other non-order notification
types.

---

### W-18 · Delivery Confirmations Log

**Route:** `/deliveries/queue/` · **Template:** `deliveries/index.html` · **Role:** DELIVERY, DISTRIBUTOR

```
┌─[Nav Shell]──────────────────────────────────────────────────────┐
│  Cola de Entregas                      [+ Confirmar Entrega]     │
│  (table: pedido · repartidor · foto ID (opcional, sin validar) · │
│   confirmado en · [Editar][Eliminar — DISTRIBUTOR only])         │
│  {empty state: "No hay confirmaciones de entrega."}               │
└─────────────────────────────────────────────────────────────────┘
```

See §5.1's 🔮 Future Upgrade — this table lists *past* confirmations, not a queue of pending dispatched orders.

---

### W-19 · Confirm Delivery

**Route:** `/deliveries/new/confirm/` · **Template:** `deliveries/crear_confirmacion.html` · **Role:** DELIVERY

```
┌─[Nav Shell]────────────────────────────┐
│  Confirmar Entrega                     │
│  {{ formulario.as_p }}                 │
│   order (dropdown — this distributor's │
│   DISPATCHED orders only)              │
│   photo_public_id (optional text)      │
│   confirmed_at                         │
│  [Btn: Guardar]  [Cancelar]            │
└─────────────────────────────────────────┘
```

No photo upload widget, no Cloudinary integration, no thumbnail preview, no disabled-until-photo-uploaded button state — `photo_public_id` is a plain optional text field per DR-09 (see §5.2).

---

## Appendix: Screen Inventory

| ID | Screen | Route | Template | Role(s) |
|----|--------|-------|----------|---------|
| W-01 | Login | `/login/` | `registration/login.html` | All |
| W-02 | Password Reset Request | `/accounts/password-reset/` | `accounts/solicitar_reset_password.html` | All |
| W-03 | Set New Password | `/accounts/password-reset/<token>/` | `accounts/confirmar_reset_password.html` | All |
| W-04 | Global Nav Shell | — | `templates/base.html` | All |
| W-04b | Distributor Onboarding | `/accounts/distributors/new/` | `accounts/crear_distribuidor.html` | Superuser |
| W-04c | Store Owner Self-Registration | `/accounts/join/<token>/` | `accounts/registrar_tienda.html` | Unauthenticated (token) |
| W-05 | Distributor Dashboard | `/accounts/dashboard/` | `accounts/dashboard.html` | DISTRIBUTOR |
| W-06 | Catálogo | `/catalog/` | `catalog/index.html` | DISTRIBUTOR |
| W-07 | Create/Edit Product | `/catalog/products/new/` etc. | `catalog/crear_producto.html`, `editar_producto.html` | DISTRIBUTOR |
| W-07b | Manage Discount `[PLANNED]` | `/catalog/products/<id>/discount/` | `catalog/gestionar_descuento.html` | DISTRIBUTOR |
| W-08 | Assign Inventory | `/catalog/inventory/assign/<vendor_id>/` | `catalog/crear_inventario.html` | DISTRIBUTOR |
| W-20 | CSV Import `[PLANNED]` | `/catalog/products/import/` | `catalog/importar_productos.html` | DISTRIBUTOR |
| W-09 | User Management | `/accounts/users/` | `accounts/index.html` | DISTRIBUTOR |
| W-10 | Vendor Order List | `/orders/` | `orders/index.html` | VENDOR |
| W-11 | Order Detail — Vendor | `/orders/<id>/` | `orders/ver_pedido.html` | VENDOR |
| W-11b | Reject Order | `/orders/<id>/reject/` | `orders/rechazar_pedido.html` | VENDOR |
| W-11c | Resolve Delivery Issue | `/orders/<id>/resolve-issue/` | `orders/resolver_incidencia.html` | VENDOR |
| W-12 | Store Owner Order List | `/orders/` | `orders/index.html` | STORE_OWNER |
| W-13 | Place Order | `/orders/new/` | `orders/crear_pedido.html` | STORE_OWNER |
| W-14 | Add Item | `/orders/<order_id>/items/new/` | `orders/crear_item_pedido.html` | STORE_OWNER |
| W-16 | Order Detail — Store Owner | `/orders/<id>/` | `orders/ver_pedido.html` | STORE_OWNER |
| W-16b | Report Delivery Issue | `/orders/<id>/report-issue/` | `orders/reportar_incidencia.html` | STORE_OWNER |
| W-17 | Notification List | `/accounts/notifications/` | `accounts/notificaciones.html` | All |
| W-18 | Delivery Confirmations Log | `/deliveries/queue/` | `deliveries/index.html` | DELIVERY, DISTRIBUTOR |
| W-19 | Confirm Delivery | `/deliveries/new/confirm/` | `deliveries/crear_confirmacion.html` | DELIVERY |
| — | Audit Log | `/audit/` | `audit/index.html` | DISTRIBUTOR |
| — | Home | `/` | `templates/home.html` | All (not role-filtered) |

---

## Appendix B: Implementation Status

### Planned, not yet implemented (Tier 4.5)

| Screen | Route | Notes |
|--------|-------|-------|
| W-07 (extended fields) | `/catalog/products/new/` etc. | Grows from 5 to 12 fields; see `docs/TODOS.md` Tier 4.5 |
| W-07b | `/catalog/products/<id>/discount/` | New screen |
| W-06 (search/filter, CSV entry point) | `/catalog/` | Extends existing page |
| W-20 | `/catalog/products/import/` | New screen |
| W-17 (digest row) | `/accounts/notifications/` | Extends existing page, no new route |

Full field lists, states, and design decisions: see the W-07/W-07b/W-06/W-20/W-17
entries above. Design review completed 2026-07-21 via `/plan-design-review`.

### Fully implemented

Every screen listed in the table above is live and reachable in the running app, RBAC-gated by `role_required`/`superuser_required` (`accounts/decorators.py`), and tenant-scoped by `distributor`.

### Known gaps (not implemented, no route/template exists)

| Gap | Related requirement | Notes |
|-----|---------------------|-------|
| Vendor's own inventory view | UC-09, FR-04.2 | §3.6 — only exercised indirectly via accept-time stock errors |
| Resubmit a rejected order | US-22 | §4.5 — `previous_order` field exists on the model, unused |
| Cloudinary photo validation | FR-07.3, NFR-01.5 | **Deliberately superseded** by DR-09, not a gap to close — see §5.2 |
| Delivery queue showing *pending* dispatched orders | UC-16, FR-07.1 | §5.1 — current screen shows past confirmations instead |
| Real Resend SMTP for password reset | FR-01.3 | §1.3 — currently console backend (deploy-config task, Tier 5) |

### 🔮 Future upgrades (working as designed, but the original aspirational UX is worth building later)

- Role-scoped navigation (nav/home currently show every link to every role — §1.6, W-04)
- Role-based post-login redirect instead of the shared home list (§1.1)
- Multi-step order-placement wizard with a live running total (§4.1, W-13/W-14)
- True stat-card dashboard with click-to-filter (§2.5, W-05)
- Rendered QR code for the store-owner invite link, not just raw URL text (§1.5)
- Confirmation modals instead of native browser `confirm()` dialogs, sitewide
- Mobile responsive breakpoints (NFR-04.2 — currently absent from `styles.css`)
- Brand colors/typography/logo applied to the UI (see `DESIGN.md` — currently just recorded as tokens, not wired in anywhere)
- Split the combined `/catalog/` page into separate product/store/inventory views as data volume grows

---

*End of UX Navigation Flows & Conceptual Wireframes document.*
