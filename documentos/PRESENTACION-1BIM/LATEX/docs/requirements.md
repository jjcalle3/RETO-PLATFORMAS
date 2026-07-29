# Requirements — ISBER Solutions Distribution Platform

**Project:** proyecto-distribuidora  
**Client:** ISBER Solutions, Loja, Ecuador  
**Team:** 2 students, 1 semester (~3 months build time)  
**Status:** Pre-implementation (architecture approved, eng review cleared)  
**Last updated:** 2026-05-24

---

## MoSCoW Key

| Label | Meaning |
|-------|---------|
| **M** | Must have — MVP cannot ship without this |
| **S** | Should have — important but not a blocker |
| **C** | Could have — desirable if time permits |
| **W** | Won't have — explicitly deferred to post-MVP roadmap |

---

## Entity Model

### Entities & Cardinalities

```
Distributor  ||--o{ User           : "has many"
Distributor  ||--o{ Store          : "owns"
Distributor  ||--o{ Product        : "manages catalog"
User         ||--o{ Store          : "STORE_OWNER owns"
User         ||--o{ VendorInventory: "VENDOR holds"
Store        ||--o{ Order          : "places"
User         ||--o{ Order          : "VENDOR processes"
Order        ||--o{ OrderItem      : "contains"
Product      ||--o{ OrderItem      : "referenced by"
Product      ||--o{ VendorInventory: "stocked in"
Order        ||--o| DeliveryConfirmation : "confirmed by"
User         ||--o{ DeliveryConfirmation : "DELIVERY submits"
User         ||--o{ AuditLog       : "generates"
User         ||--o{ PasswordResetToken : "requests"
```

### ER Diagram (Mermaid)

```mermaid
erDiagram
    Distributor {
        string id PK
        string name
        string email
    }
    User {
        string id PK
        string email
        string passwordHash
        Role role
        string distributorId FK
    }
    Store {
        string id PK
        string name
        string distributorId FK
        string ownerId FK
    }
    Product {
        string id PK
        string name
        string description
        decimal unitPrice
        string distributorId FK
    }
    VendorInventory {
        string vendorId FK
        string productId FK
        int quantity
    }
    Order {
        string id PK
        string storeId FK
        string vendorId FK
        OrderStatus status
        string previousOrderId FK "nullable — links resubmissions to their rejected predecessor"
        datetime createdAt
        datetime updatedAt
    }
    OrderItem {
        string id PK
        string orderId FK
        string productId FK
        int quantity
        decimal unitPriceAtTime
    }
    DeliveryConfirmation {
        string id PK
        string orderId FK
        string deliveryUserId FK
        string photoPublicId
        datetime confirmedAt
    }
    PasswordResetToken {
        string id PK
        string userId FK
        string token
        datetime expiresAt
        datetime usedAt
    }
    AuditLog {
        string id PK
        string userId FK
        string action
        string entityType
        string entityId
        datetime timestamp
        json details
    }

    Distributor ||--o{ User : "has"
    Distributor ||--o{ Store : "owns"
    Distributor ||--o{ Product : "manages"
    User ||--o{ Store : "owns (STORE_OWNER)"
    User ||--o{ Order : "processes (VENDOR)"
    User ||--o{ DeliveryConfirmation : "submits (DELIVERY)"
    User ||--o{ AuditLog : "generates"
    User ||--o{ PasswordResetToken : "requests"
    Store ||--o{ Order : "places"
    Order ||--o{ OrderItem : "contains"
    Product ||--o{ OrderItem : "appears in"
    Product ||--o{ VendorInventory : "stocked in"
    Order ||--o| DeliveryConfirmation : "confirmed by"
    Order ||--o| Order : "resubmitted as (previousOrderId)"
```

### Order Status State Machine

```
PENDING → ACCEPTED → DISPATCHED → DELIVERED
PENDING → REJECTED → (new Order with previousOrderId pointing back)
```

---

## System Architecture

### Logical Architecture

The logical architecture describes **what** the system does and how responsibilities are organized across layers — independent of any deployment or infrastructure choice. The system follows Django's MVT (Model-View-Template) pattern mapped onto five layers:

| # | Layer | Responsibility |
|---|-------|----------------|
| ① | Presentation | Renders HTML responses and runs the client-side polling loop |
| ② | Application | Receives HTTP requests, enforces RBAC, executes business rules |
| ③ | Cross-Cutting | RBAC guard, tenant isolation, and audit trail — applied across all apps |
| ④ | Domain Model | The entities and their relationships (see ER Diagram) |
| ⑤ | Data Access | Translates ORM calls into SQL; owns transactional integrity |

```mermaid
graph TD

    subgraph P["① Presentation Layer"]
        T["Django Template Engine\nHTML · Tailwind CSS · per-role templates"]
        J["JS Polling Module\nsetInterval 30 s · fetch /api/orders/pending/"]
    end

    subgraph A["② Application Layer"]
        AC["accounts/\nViews · Forms\nlogin · logout · password reset\n@role_required decorator"]
        CA["catalog/\nViews · Forms\nProduct · Store · VendorInventory CRUD"]
        OR["orders/\nViews · Forms · API endpoint\nOrder state machine\nsubmit · accept · reject · dispatch"]
        DE["deliveries/\nViews · Forms\nDelivery confirmation\nphoto public_id validation"]
    end

    subgraph CC["③ Cross-Cutting Concerns"]
        RB["RBAC\n@role_required on every view\nrole re-checked server-side"]
        TN["Tenant Isolation\ndistributorId filter\napplied on every QuerySet"]
        AU["Audit Trail\nAuditLog entry written\non every state transition"]
    end

    subgraph D["④ Domain Model"]
        M["User · Distributor · Store · Product\nVendorInventory · Order · OrderItem\nDeliveryConfirmation · AuditLog · PasswordResetToken"]
    end

    subgraph L["⑤ Data Access Layer"]
        O["Django ORM\nQuerySet API\ntransaction.atomic() + select_for_update()  ← inventory race lock\nselect_related() · prefetch_related()  ← N+1 prevention"]
    end

    P     -->|"HTTP request"| A
    A     --> CC
    A     --> D
    D     --> L
    A     -->|"HTTP response · rendered template"| P
```

---

### Physical Architecture

The physical architecture describes **where** the system runs — which processes exist, on what infrastructure, and how they communicate over the network.

```mermaid
graph LR

    subgraph CLIENTS["Client Devices"]
        MB["Mobile Browser\nStore Owner · Delivery Personnel\n360 px min width"]
        DB["Desktop Browser\nDistributor · Vendor"]
    end

    subgraph RW["Railway Cloud Project"]
        subgraph APP["App Service — single Gunicorn process"]
            GN["Gunicorn WSGI\nlistens on $PORT"]
            DJ["Django 4.2\nMiddleware Stack\nWhiteNoise · Auth · Session"]
        end
        PG[("PostgreSQL\nDatabase Service\nRailway-managed\ndj-database-url")]
    end

    subgraph EXT["External Cloud Services"]
        CLD["Cloudinary\nPhoto CDN\nfree tier · upload preset"]
        RS["Resend\nSMTP Relay\nfree tier · port 587"]
    end

    MB & DB -->|"HTTPS · TLS 1.3\nrequest / response"| GN
    GN      --> DJ
    DJ      -->|"TCP · SSL · port 5432\nSQL — scoped by distributorId"| PG
    MB & DB -->|"HTTPS\nbrowser-direct upload\nunsigned upload preset"| CLD
    DJ      -->|"HTTPS · Python SDK\npublic_id validation"| CLD
    DJ      -->|"SMTP · TLS · port 587\npassword reset email"| RS
```

#### Physical nodes

| Node | Type | Hosts | Notes |
|------|------|-------|-------|
| **Client Browser** | User device | HTML templates, JS polling | Mobile or desktop; no native app |
| **Railway App Service** | Managed PaaS container | Gunicorn + Django + WhiteNoise | Single process; scales vertically on Railway free tier |
| **Railway PostgreSQL** | Managed DB service | All relational data | Same Railway project; connected via `DATABASE_URL` |
| **Cloudinary** | External CDN/storage | Delivery confirmation photos | Browser uploads directly; Django validates `public_id` server-side |
| **Resend** | External SMTP relay | Password reset emails | Django SMTP backend points to `smtp.resend.com:587` |

#### Network flows

| Flow | Protocol | Direction | Trigger |
|------|----------|-----------|---------|
| Page request / response | HTTPS | Browser → Railway → Browser | Any user action |
| Order polling | HTTPS (JSON) | Browser → Railway | Every 30 s on vendor dashboard |
| Database queries | TCP/SSL · PostgreSQL wire | Django → Railway PostgreSQL | Every view that reads/writes data |
| Photo upload | HTTPS (multipart) | Browser → Cloudinary | Delivery confirmation form |
| Photo validation | HTTPS (Python SDK) | Django → Cloudinary | After delivery confirmation submit |
| Password reset email | SMTP · TLS | Django → Resend | Password reset request |

---

## Component Diagram

### Layers

The system is structured in four horizontal layers. Each layer communicates only with the layer directly adjacent to it; no layer skips over another.

| Layer | Responsibility |
|-------|----------------|
| **Client** | Renders HTML responses and runs the JS polling loop |
| **Application** | Handles HTTP, enforces RBAC, executes business logic |
| **Data Access** | Translates ORM calls into SQL; guarantees transactional integrity |
| **External Services** | PostgreSQL, Cloudinary, Resend — managed outside the app |

---

### Diagram

```mermaid
graph TB

    subgraph BROWSER["Browser — Client Layer"]
        TMPL["HTML Templates\nbase.html + per-role views\nTailwind CSS"]
        POLL["JS Polling Module\nsetInterval 30 s\nfetch /api/orders/pending/"]
    end

    subgraph DJANGO["Django 4.2 — Railway Application Layer"]
        GUN["Gunicorn\nWSGI entry point\nProcfile: web: gunicorn distribuidora.wsgi"]

        subgraph MWS["Middleware Stack"]
            SEC["SecurityMiddleware"]
            WN["WhiteNoiseMiddleware\nserves static files"]
            SESS["SessionMiddleware"]
            AUTHMW["AuthenticationMiddleware"]
        end

        ROUTER["URL Router\ndistribuidora/urls.py"]

        subgraph APPS["Application Components"]
            ACC["accounts/\n─────────────────\nProvides: login · logout\npassword reset flow\n@role_required decorator\nCustom User: AbstractUser\n+ role CharField\n+ distributor FK"]

            CAT["catalog/\n─────────────────\nProvides: Product CRUD\nStore CRUD\nVendorInventory assignment\nRequires: DISTRIBUTOR role"]

            ORD["orders/\n─────────────────\nProvides: order submit\naccept · reject · dispatch\nGET /api/orders/pending/\nRequires: inventory check\ntransaction.atomic()"]

            DEL["deliveries/\n─────────────────\nProvides: delivery confirmation\nphoto public_id validation\nstatus → DELIVERED\nRequires: Cloudinary SDK"]
        end

        ORM["Django ORM\n─────────────────────────────────────────\nselect_related() · prefetch_related()  — N+1 prevention\ntransaction.atomic() + select_for_update()  — inventory race lock\ndistributorId filter on every query  — tenant isolation"]
    end

    subgraph EXT["External Services"]
        PG[("Railway PostgreSQL\nPrimary database\ndj-database-url")]
        CLD["Cloudinary\nPhoto storage\nUpload preset\nPython SDK"]
        RSN["Resend\nSMTP relay\nDjango SMTP backend"]
    end

    %% Client → App
    TMPL        -->|"HTTP request"| GUN
    POLL        -->|"GET /api/orders/pending/"| GUN

    %% App internal flow
    GUN         --> SEC --> WN --> SESS --> AUTHMW --> ROUTER
    ROUTER      -->|"/accounts/"| ACC
    ROUTER      -->|"/catalog/"| CAT
    ROUTER      -->|"/orders/"| ORD
    ROUTER      -->|"/deliveries/"| DEL

    %% Apps → ORM
    ACC         --> ORM
    CAT         --> ORM
    ORD         --> ORM
    DEL         --> ORM

    %% ORM → DB
    ORM         -->|"SQL — scoped by distributorId"| PG

    %% Apps → External
    DEL         -->|"Python SDK\nvalidate public_id"| CLD
    ACC         -->|"Django SMTP backend\npassword reset email"| RSN

    %% App → Client (response)
    ACC         -->|"HTTP response\nrendered template"| TMPL
    CAT         -->|"HTTP response\nrendered template"| TMPL
    ORD         -->|"HTTP response\nrendered template / JSON"| TMPL
    DEL         -->|"HTTP response\nrendered template"| TMPL
```

---

### Component Interface Summary

| Component | Provided Interface | Required Interface |
|-----------|-------------------|--------------------|
| **accounts/** | `POST /accounts/login/` · `POST /accounts/logout/` · `POST /accounts/password-reset/` · `@role_required` decorator | Django ORM · Resend SMTP |
| **catalog/** | `GET/POST/PUT/DELETE /catalog/products/` · `GET/POST/PUT /catalog/stores/` · `POST /catalog/inventory/` | Django ORM · `DISTRIBUTOR` role check |
| **orders/** | `POST /orders/` (submit) · `POST /orders/<id>/accept/` · `POST /orders/<id>/reject/` · `POST /orders/<id>/dispatch/` · `GET /api/orders/pending/` | Django ORM · `transaction.atomic()` · `select_for_update()` |
| **deliveries/** | `POST /deliveries/<id>/confirm/` | Django ORM · Cloudinary Python SDK |
| **Django ORM** | `QuerySet` API · `transaction.atomic()` · `select_for_update()` · `select_related()` | Railway PostgreSQL via `dj-database-url` |
| **Gunicorn** | WSGI HTTP server on `0.0.0.0:$PORT` | Django WSGI app (`distribuidora.wsgi`) |
| **WhiteNoise** | Serves `/static/**` directly from process memory | Collected static files (`collectstatic`) |
| **Cloudinary** | Photo upload + CDN delivery | Upload preset (restricts client-direct uploads) |
| **Resend** | SMTP relay on port 465/587 | — |
| **Railway PostgreSQL** | PostgreSQL wire protocol | — |

---

### Key Cross-Cutting Concerns

- **Tenant isolation:** Every ORM query in `accounts/`, `catalog/`, `orders/`, and `deliveries/` applies a `distributorId` filter. This is enforced at the ORM layer, not only at the view layer.
- **Concurrency safety:** The `orders/` component wraps inventory check + deduction + status update in a single `transaction.atomic()` block with `select_for_update()` on the affected `VendorInventory` row. This prevents double-acceptance when two vendors act simultaneously.
- **Static files:** WhiteNoise serves static assets directly from the Gunicorn process — no separate CDN or nginx is required on Railway free tier.
- **Photo fraud prevention:** The `deliveries/` component validates that each submitted `public_id` was generated by the app's own Cloudinary upload preset before persisting the confirmation.

---

## Use Cases

### Use Case Diagram

```mermaid
graph LR
    DIST["👤 DISTRIBUTOR"]
    VEND["👤 VENDOR"]
    STORE["👤 STORE_OWNER"]
    DELIV["👤 DELIVERY"]

    subgraph SYS["ISBER Solutions Platform"]
        UC01(["UC-01 · Login"])
        UC02(["UC-02 · Logout"])
        UC03(["UC-03 · Reset Password"])
        UC04(["UC-04 · Manage Product Catalog"])
        UC05(["UC-05 · Assign Inventory to Vendor"])
        UC06(["UC-06 · View Operations Dashboard"])
        UC07(["UC-07 · Consult Audit Trail"])
        UC08(["UC-08 · Manage Platform Users"])
        UC09(["UC-09 · View Own Inventory"])
        UC10(["UC-10 · View Pending Orders"])
        UC11(["UC-11 · Accept Order"])
        UC12(["UC-12 · Reject Order"])
        UC13(["UC-13 · Mark Order as Dispatched"])
        UC14(["UC-14 · Place Order"])
        UC15(["UC-15 · Track Order Status"])
        UC16(["UC-16 · View Dispatched Orders"])
        UC17(["UC-17 · Confirm Delivery with Photo"])
    end

    DIST --- UC01 & UC02 & UC03 & UC04 & UC05 & UC06 & UC07 & UC08
    VEND --- UC01 & UC02 & UC03 & UC09 & UC10 & UC11 & UC12 & UC13
    STORE --- UC01 & UC02 & UC03 & UC14 & UC15
    DELIV --- UC01 & UC02 & UC03 & UC16 & UC17

    UC11 -. "«include»" .-> UC09
    UC17 -. "«include»" .-> UC16
```

**Relationship notes:**
- `UC-11 «include» UC-09` — accepting an order requires the system to verify the vendor's current inventory level before committing.
- `UC-17 «include» UC-16` — a delivery person must view the dispatched order before they can confirm it.

---

### Use Case Specifications

#### UC-01 — Login

| Attribute | Detail |
|-----------|--------|
| **Actors** | DISTRIBUTOR, VENDOR, STORE_OWNER, DELIVERY |
| **Preconditions** | User has a registered account with an assigned role |
| **Main Flow** | 1. User navigates to `/accounts/login/` · 2. User enters email and password · 3. System validates credentials · 4. System creates a server-side session · 5. System redirects to the user's role dashboard |
| **Alt Flow A1** | Wrong password → generic error message; session not created; no user enumeration |
| **Alt Flow A2** | Account not found → same generic error as A1 (prevents enumeration) |
| **Postconditions** | Authenticated session exists; user is on their role dashboard |
| **Related FR** | FR-01.1, FR-01.2 |

---

#### UC-03 — Reset Password

| Attribute | Detail |
|-----------|--------|
| **Actors** | DISTRIBUTOR, VENDOR, STORE_OWNER, DELIVERY |
| **Preconditions** | User has a registered email address |
| **Main Flow** | 1. User requests password reset with their email · 2. System generates a single-use token with 1 h expiry · 3. System sends reset link via Resend SMTP · 4. User clicks the link · 5. System validates the token (not used, not expired) · 6. User sets a new password · 7. Token is marked as used |
| **Alt Flow A1** | Token already used → error: "este enlace ya fue utilizado" |
| **Alt Flow A2** | Token expired → error: "el enlace ha expirado, solicita uno nuevo" |
| **Alt Flow A3** | Email not found → silent success response (prevents enumeration) |
| **Postconditions** | Password updated; old token invalidated; user can log in with new password |
| **Related FR** | FR-01.3, FR-01.4, FR-01.6 |

---

#### UC-04 — Manage Product Catalog

| Attribute | Detail |
|-----------|--------|
| **Actors** | DISTRIBUTOR |
| **Preconditions** | User is authenticated as DISTRIBUTOR |
| **Main Flow** | 1. Distributor navigates to `/catalog/products/` · 2. Distributor creates a product (name, description, unit price, initial stock) · 3. System saves the product scoped to `distributor.id` · 4. Product appears in the catalog list |
| **Alt Flow A1** | Edit → distributor selects a product, updates fields, system saves new values (does not affect existing `unitPriceAtTime` in past orders) |
| **Alt Flow A2** | Deactivate → product hidden from vendor inventory assignment; existing orders unaffected |
| **Alt Flow A3** | Missing required field → form validation error; product not saved |
| **Postconditions** | Product exists in the catalog and is available for inventory assignment |
| **Related FR** | FR-03.1–FR-03.4 |

---

#### UC-05 — Assign Inventory to Vendor

| Attribute | Detail |
|-----------|--------|
| **Actors** | DISTRIBUTOR |
| **Preconditions** | Product exists in catalog; target user has VENDOR role and belongs to the same distributor |
| **Main Flow** | 1. Distributor selects a vendor and a product · 2. Distributor enters quantity to assign · 3. System creates or updates the `VendorInventory` record · 4. Vendor's inventory is updated immediately |
| **Alt Flow A1** | Quantity = 0 → treated as removing the product from the vendor's inventory |
| **Alt Flow A2** | Negative quantity → validation error |
| **Postconditions** | `VendorInventory` record reflects the new quantity; distributor dashboard shows updated levels |
| **Related FR** | FR-03.5, FR-04.1 |

---

#### UC-11 — Accept Order

| Attribute | Detail |
|-----------|--------|
| **Actors** | VENDOR |
| **Preconditions** | Order exists in `PENDING` status; order is assigned to this vendor |
| **Main Flow** | 1. Vendor views the pending order · 2. Vendor clicks "Aceptar" · 3. System opens a database transaction (`transaction.atomic()`) · 4. System locks the `VendorInventory` rows for the ordered products (`select_for_update()`) · 5. System validates available stock ≥ ordered quantity for all items · 6. System deducts inventory for each item · 7. System transitions order to `ACCEPTED` · 8. System writes an AuditLog entry · 9. Transaction commits |
| **Alt Flow A1** | Insufficient stock for any item → transaction rolled back; order remains `PENDING`; vendor sees per-item error message |
| **Alt Flow A2** | Concurrent accept (two vendors click simultaneously) → only the first transaction succeeds; the second receives A1 error |
| **Postconditions** | Order is `ACCEPTED`; inventory deducted; audit entry recorded; store owner notified (in-app) |
| **Related FR** | FR-04.3, FR-04.4, FR-06.2–FR-06.4, FR-09.1–FR-09.2 |

---

#### UC-12 — Reject Order

| Attribute | Detail |
|-----------|--------|
| **Actors** | VENDOR |
| **Preconditions** | Order exists in `PENDING` status; order is assigned to this vendor |
| **Main Flow** | 1. Vendor views the pending order · 2. Vendor clicks "Rechazar" · 3. System prompts for confirmation · 4. Vendor confirms · 5. System transitions order to `REJECTED` · 6. System writes an AuditLog entry |
| **Alt Flow A1** | Vendor cancels the confirmation prompt → order remains `PENDING` |
| **Postconditions** | Order is `REJECTED`; inventory unchanged; store owner notified (in-app); audit entry recorded |
| **Related FR** | FR-06.2, FR-06.4, FR-09.1 |

---

#### UC-13 — Mark Order as Dispatched

| Attribute | Detail |
|-----------|--------|
| **Actors** | VENDOR |
| **Preconditions** | Order is in `ACCEPTED` status; order is assigned to this vendor |
| **Main Flow** | 1. Vendor views the accepted order · 2. Vendor clicks "Marcar como Despachado" · 3. System confirms intent · 4. System transitions order to `DISPATCHED` · 5. System writes an AuditLog entry · 6. Order becomes visible in the delivery queue |
| **Postconditions** | Order is `DISPATCHED`; delivery personnel can now see it; store owner notified (in-app) |
| **Related FR** | FR-06.5, FR-09.1 |

---

#### UC-14 — Place Order

| Attribute | Detail |
|-----------|--------|
| **Actors** | STORE_OWNER |
| **Preconditions** | User is authenticated as STORE_OWNER; at least one vendor has inventory assigned |
| **Main Flow** | 1. Store owner navigates to "Nuevo Pedido" · 2. System shows available products from the assigned vendor · 3. Store owner selects products and quantities · 4. Store owner submits the order · 5. System validates all products exist in the vendor's `VendorInventory` · 6. System captures `unitPriceAtTime` for each item · 7. System creates the order in `PENDING` status · 8. System confirms submission to the store owner |
| **Alt Flow A1** | One or more products not in vendor inventory → order rejected; per-item error shown; no order created |
| **Alt Flow A2** | Quantity = 0 for any item → validation error before submission |
| **Postconditions** | Order exists in `PENDING` status; vendor sees it in their dashboard within 30 s (polling); store owner can track it |
| **Related FR** | FR-05.1, FR-05.3, FR-05.4 |

---

#### UC-17 — Confirm Delivery with Photo

| Attribute | Detail |
|-----------|--------|
| **Actors** | DELIVERY |
| **Preconditions** | Order is in `DISPATCHED` status and assigned to this delivery person |
| **Main Flow** | 1. Delivery person navigates to the dispatched order · 2. Delivery person uploads a photo using the platform's upload widget · 3. Browser uploads the photo directly to Cloudinary via the upload preset · 4. Cloudinary returns a `public_id` · 5. Delivery person submits the confirmation form with the `public_id` · 6. System validates the `public_id` via the Cloudinary Python SDK · 7. System creates a `DeliveryConfirmation` record storing the `public_id` · 8. System transitions order to `DELIVERED` · 9. System writes an AuditLog entry |
| **Alt Flow A1** | `public_id` not generated by the platform's upload preset → confirmation rejected; order remains `DISPATCHED` |
| **Alt Flow A2** | No photo uploaded → form validation error; submission blocked |
| **Postconditions** | Order is `DELIVERED`; photo stored as `public_id`; distributor sees completed order; audit entry recorded |
| **Related FR** | FR-07.1–FR-07.5, FR-09.1 |

---

## User Stories

Stories are grouped by Epic. Each story maps to one or more use cases and functional requirements.

---

### Epic 1 — Authentication

**US-01** — Iniciar sesión  
*As any user, I want to log in with my email and password so that I can access the features of my assigned role.*  
**Priority:** M | **Related:** UC-01, FR-01.1, FR-01.2  
**Acceptance Criteria:**
- [ ] Given valid credentials, the system creates a session and redirects to the role dashboard.
- [ ] Given invalid credentials, a generic error is shown and no session is created.
- [ ] A user with role VENDOR cannot access `/distributor/*` routes after login.

---

**US-02** — Cerrar sesión  
*As any user, I want to log out so that my session is terminated and no one else can use my account.*  
**Priority:** M | **Related:** UC-02, FR-01.5  
**Acceptance Criteria:**
- [ ] Clicking "Cerrar sesión" destroys the server-side session.
- [ ] After logout, navigating to any protected route redirects to the login page.

---

**US-03** — Recuperar contraseña  
*As any user, I want to reset my password by email so that I can regain access if I forget it.*  
**Priority:** M | **Related:** UC-03, FR-01.3, FR-01.4, FR-01.6  
**Acceptance Criteria:**
- [ ] The reset link arrives in the registered email within 2 minutes.
- [ ] The link expires after 1 hour and shows an error if used afterwards.
- [ ] The link can only be used once; a second use shows an error.
- [ ] After reset, the user can log in with the new password.

---

### Epic 2 — Distributor: Product Catalog

**US-04** — Crear producto  
*As a DISTRIBUTOR, I want to add a new product to the catalog so that vendors can sell it to stores.*  
**Priority:** M | **Related:** UC-04, FR-03.1  
**Acceptance Criteria:**
- [ ] Form requires: name, description, unit price, initial stock quantity.
- [ ] Saved product appears in the catalog list immediately.
- [ ] Product is scoped to the distributor's `id`; other distributors cannot see it.

---

**US-05** — Editar producto  
*As a DISTRIBUTOR, I want to edit a product's price and description so that the catalog stays up to date.*  
**Priority:** M | **Related:** UC-04, FR-03.2  
**Acceptance Criteria:**
- [ ] Price change is reflected immediately in the catalog.
- [ ] All existing orders retain their original `unitPriceAtTime`; historical totals do not change.

---

**US-06** — Desactivar producto  
*As a DISTRIBUTOR, I want to deactivate a product so that vendors can no longer place new orders for it without affecting orders already in progress.*  
**Priority:** S | **Related:** UC-04, FR-03.3  
**Acceptance Criteria:**
- [ ] Deactivated product no longer appears in the vendor's available inventory.
- [ ] Orders that already contain the product are unaffected.

---

**US-07** — Asignar inventario a vendedor  
*As a DISTRIBUTOR, I want to assign a quantity of a product to a specific vendor so that the vendor can fulfil orders for that product.*  
**Priority:** M | **Related:** UC-05, FR-03.5, FR-04.1  
**Acceptance Criteria:**
- [ ] Distributor selects vendor + product + quantity; record is saved immediately.
- [ ] Updated stock level is visible on the operations dashboard.
- [ ] A vendor from a different distributor cannot see this assignment.

---

### Epic 3 — Distributor: Operations

**US-08** — Ver dashboard de operaciones  
*As a DISTRIBUTOR, I want a real-time overview of all orders and current inventory so that I can manage the business without making phone calls.*  
**Priority:** M | **Related:** UC-06, FR-08.1, FR-08.3  
**Acceptance Criteria:**
- [ ] Dashboard shows orders grouped by status (PENDING, ACCEPTED, DISPATCHED, DELIVERED, REJECTED).
- [ ] Dashboard shows stock levels per product per vendor.
- [ ] Data reflects the latest state within one page load.

---

**US-09** — Consultar auditoría de un pedido  
*As a DISTRIBUTOR, I want to see the full history of events for any order so that I can investigate disputes or errors.*  
**Priority:** M | **Related:** UC-07, FR-09.1, FR-09.5  
**Acceptance Criteria:**
- [ ] Audit log for an order shows: timestamp, actor (user name + role), action, previous status, new status.
- [ ] Accessible from the order detail view.
- [ ] Entries are in chronological order and cannot be deleted.

---

### Epic 4 — Vendor: Order Processing

**US-10** — Ver pedidos pendientes  
*As a VENDOR, I want my dashboard to show new pending orders automatically so that I don't miss any without refreshing the page.*  
**Priority:** M | **Related:** UC-10, FR-06.1, FR-06.6, FR-10.1  
**Acceptance Criteria:**
- [ ] Dashboard fetches `/api/orders/pending/` every 30 seconds.
- [ ] New orders appear within 30 seconds of being placed without manual refresh.
- [ ] Only orders assigned to this vendor are shown.

---

**US-11** — Aceptar pedido  
*As a VENDOR, I want to accept a pending order so that inventory is reserved and the store knows their order is being prepared.*  
**Priority:** M | **Related:** UC-11, FR-04.3, FR-06.2–FR-06.4  
**Acceptance Criteria:**
- [ ] On accept, inventory is deducted atomically; no race condition with a concurrent accept.
- [ ] If stock is insufficient, the order stays PENDING and the vendor sees which items failed.
- [ ] Order status changes to ACCEPTED immediately after a successful accept.
- [ ] An AuditLog entry is created capturing the vendor's identity and timestamp.

---

**US-12** — Rechazar pedido  
*As a VENDOR, I want to reject an order I cannot fulfil so that the store owner is notified promptly.*  
**Priority:** M | **Related:** UC-12, FR-06.2, FR-06.4  
**Acceptance Criteria:**
- [ ] A confirmation dialog appears before the rejection is committed.
- [ ] Order transitions to REJECTED; inventory is not affected.
- [ ] Store owner receives an in-app notification of the rejection.

---

**US-13** — Marcar pedido como despachado  
*As a VENDOR, I want to mark an accepted order as dispatched when the goods leave the warehouse so that the delivery team knows what to pick up.*  
**Priority:** M | **Related:** UC-13, FR-06.5  
**Acceptance Criteria:**
- [ ] Only orders in ACCEPTED status can be dispatched.
- [ ] Order appears in the delivery queue immediately after dispatch.
- [ ] Store owner receives an in-app notification.

---

### Epic 5 — Store Owner: Orders

**US-14** — Realizar un pedido  
*As a STORE_OWNER, I want to place an order by selecting products and quantities so that I can restock my store without calling or visiting the distributor.*  
**Priority:** M | **Related:** UC-14, FR-05.1, FR-05.3, FR-05.4  
**Acceptance Criteria:**
- [ ] Order flow completes in 3 steps or fewer from the main screen.
- [ ] If a product is unavailable, a clear per-item error is shown and no order is created.
- [ ] The price recorded on each item matches the catalog price at the time of submission.
- [ ] All interactive elements meet 48 × 48 px minimum tap target size.

---

**US-15** — Rastrear estado del pedido  
*As a STORE_OWNER, I want to see the current status of my orders so that I know when to expect delivery without calling the vendor.*  
**Priority:** M | **Related:** UC-15, FR-05.5  
**Acceptance Criteria:**
- [ ] Orders list shows status label (PENDING / ACCEPTED / DISPATCHED / DELIVERED / REJECTED) for each order.
- [ ] Status is updated on page load without requiring a separate action.

---

**US-16** — Recibir notificaciones de cambio de estado  
*As a STORE_OWNER, I want to see in-app notifications when my order status changes so that I'm informed without having to check manually.*  
**Priority:** S | **Related:** FR-10.2–FR-10.4  
**Acceptance Criteria:**
- [ ] Notification appears when order transitions to ACCEPTED, REJECTED, DISPATCHED, or DELIVERED.
- [ ] Notification identifies the order by a readable reference (e.g., order number + store name).

---

### Epic 6 — Delivery: Confirmation

**US-17** — Ver pedidos despachados asignados  
*As a DELIVERY person, I want to see all dispatched orders on my queue so that I know what I need to deliver today.*  
**Priority:** M | **Related:** UC-16, FR-07.1  
**Acceptance Criteria:**
- [ ] Only orders in DISPATCHED status are shown.
- [ ] Each entry shows: store name, address, product summary, and order date.

---

**US-18** — Confirmar entrega con foto  
*As a DELIVERY person, I want to upload a photo as proof of delivery so that disputes about non-delivery can be resolved with evidence.*  
**Priority:** M | **Related:** UC-17, FR-07.2–FR-07.5  
**Acceptance Criteria:**
- [ ] Photo upload is required; the form cannot be submitted without one.
- [ ] Photo is uploaded directly to Cloudinary; the server validates the `public_id` before accepting.
- [ ] An externally hosted URL submitted manually is rejected.
- [ ] Order transitions to DELIVERED immediately after a successful confirmation.
- [ ] Confirmation is permanent; the photo `public_id` is stored on the delivery record.

---

### Epic 7 — Audit & Notifications

**US-19** — Registro automático de cambios de inventario  
*As a DISTRIBUTOR, I want every inventory deduction to be logged automatically so that I can audit stock discrepancies without relying on manual records.*  
**Priority:** M | **Related:** FR-09.2  
**Acceptance Criteria:**
- [ ] Every successful order acceptance creates an AuditLog entry with: vendor, product, quantity deducted, order ID, timestamp.
- [ ] Failed acceptance attempts (insufficient stock) also create an AuditLog entry.

---

**US-20** — Registro de cambios en el catálogo  
*As a DISTRIBUTOR, I want product catalog changes to be logged so that I can track who modified a price or deactivated a product.*  
**Priority:** S | **Related:** FR-09.4  
**Acceptance Criteria:**
- [ ] Creating, editing, or deactivating a product generates an AuditLog entry with before/after values.
- [ ] The entry captures the distributor user's ID and timestamp.

---

**US-21** — Alerta de stock bajo  
*As a DISTRIBUTOR, I want a visual alert when a vendor's product stock drops below a threshold so that I can restock before an order is rejected due to lack of inventory.*  
**Priority:** S | **Related:** FR-04.5  
**Acceptance Criteria:**
- [ ] A visual indicator (badge or color) appears on the dashboard when any vendor's stock for a product falls below the configured threshold.
- [ ] Threshold is configurable per product (default: 5 units).

---

## Functional Requirements

### FR-01 — Authentication

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-01.1 | **M** | The system must allow users to register with email, password, and a pre-assigned role. |
| FR-01.2 | **M** | The system must authenticate users via email and password. |
| FR-01.3 | **M** | The system must allow users to request a password reset; a one-time link is delivered to the user's registered email. |
| FR-01.4 | **M** | The system must allow users to set a new password using a valid, unexpired reset link. |
| FR-01.5 | **M** | The system must invalidate the user's session on logout. |
| FR-01.6 | **M** | A password reset link must be single-use and expire after 1 hour of issuance. |

---

### FR-02 — Role-Based Access Control (RBAC)

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-02.1 | **M** | The system must support exactly four roles: `DISTRIBUTOR`, `VENDOR`, `STORE_OWNER`, `DELIVERY`. |
| FR-02.2 | **M** | `DISTRIBUTOR` is the top-level role; no role above it exists in the system. |
| FR-02.3 | **M** | Each dashboard area must be accessible exclusively to its corresponding role; unauthorized access attempts must return a 403 response. |
| FR-02.4 | **M** | Every state-changing operation must re-verify the caller's session role server-side; client-supplied role values must never be trusted. |
| FR-02.5 | **M** | All data queries must be scoped to the authenticated user's `distributorId`; cross-tenant data leakage must be architecturally impossible. |

---

### FR-03 — Product Catalog (DISTRIBUTOR)

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-03.1 | **M** | The distributor must be able to create a product with: name, description, unit price, and an initial stock quantity. |
| FR-03.2 | **M** | The distributor must be able to update a product's name, description, and unit price. |
| FR-03.3 | **S** | The distributor must be able to deactivate (soft-delete) a product; active orders referencing it must not be affected. |
| FR-03.4 | **M** | The distributor must be able to view the full product catalog with current prices. |
| FR-03.5 | **M** | The distributor must be able to assign stock quantities to a specific vendor, creating or updating the corresponding `VendorInventory` record. |

---

### FR-04 — Inventory Management

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-04.1 | **M** | The distributor must see current stock levels per product per vendor from the operations dashboard. |
| FR-04.2 | **M** | A vendor must see only their own assigned inventory. |
| FR-04.3 | **M** | Inventory deduction must occur atomically when an order is ACCEPTED, preventing inconsistencies under concurrent accepts for the same product. |
| FR-04.4 | **M** | If inventory is insufficient at acceptance, the operation must be rolled back entirely and the vendor must receive a clear error message. |
| FR-04.5 | **S** | The distributor must receive an alert (visual indicator on dashboard) when any vendor's product stock falls below a configurable threshold. |

---

### FR-05 — Order Creation (STORE_OWNER / VENDOR)

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-05.1 | **M** | A store owner must be able to create an order by selecting products and specifying quantities. |
| FR-05.2 | **S** | A vendor must be able to create an order on behalf of a store they are assigned to. |
| FR-05.3 | **M** | At submit time, the system must validate that all ordered products are available in the target vendor's inventory; if any product is unavailable, the order must be rejected with a per-item error message. |
| FR-05.4 | **M** | The price of each order item must be captured at the moment of order creation and must not change if the catalog price is later updated. |
| FR-05.5 | **M** | A store owner must be able to view the real-time status of all their submitted orders. |

---

### FR-06 — Order Processing (VENDOR)

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-06.1 | **M** | A vendor must see all orders in `PENDING` status assigned to them. |
| FR-06.2 | **M** | A vendor must be able to ACCEPT or REJECT a pending order. |
| FR-06.3 | **M** | On ACCEPT, inventory must be deducted atomically (see FR-04.3). |
| FR-06.4 | **M** | On ACCEPT the order status transitions to `ACCEPTED`; on REJECT, to `REJECTED`. |
| FR-06.5 | **M** | A vendor must be able to mark an accepted order as `DISPATCHED` when goods leave the warehouse. |
| FR-06.6 | **M** | The vendor dashboard must automatically refresh the pending order list at a regular interval without requiring a manual page reload. |

---

### FR-07 — Delivery Confirmation (DELIVERY)

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-07.1 | **M** | Delivery personnel must see all orders in `DISPATCHED` status assigned to their route. |
| FR-07.2 | **M** | Delivery personnel must confirm a delivery by uploading a photo as proof of receipt. |
| FR-07.3 | **M** | The system must reject any delivery confirmation that does not include a photo generated through the platform's own upload flow; externally hosted URLs must not be accepted. |
| FR-07.4 | **M** | On confirmed delivery, the order status must transition to `DELIVERED`. |
| FR-07.5 | **M** | The delivery record must permanently store the unique identifier of the uploaded photo. |

---

### FR-08 — Distributor Dashboard & Reporting

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-08.1 | **M** | The distributor must see a real-time dashboard showing all orders and their current status. |
| FR-08.2 | **S** | The distributor must be able to filter the order history by: date range, vendor, store, and status. |
| FR-08.3 | **M** | The distributor must see an inventory overview showing stock per product per vendor. |
| FR-08.4 | **S** | The distributor must see summary metrics: total orders, fulfilled, rejected, and average fulfillment time — filterable by vendor and period. |
| FR-08.5 | **C** | The distributor must be able to export the order history as a CSV file. |

---

### FR-09 — Audit Trail

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-09.1 | **M** | The system must record an audit log entry for every order status transition, capturing: the user who triggered it, the timestamp, the previous status, and the new status. |
| FR-09.2 | **M** | The system must log every inventory deduction, capturing: the vendor, the product, the quantity deducted, and the order that triggered it. |
| FR-09.3 | **S** | The system must log every failed order acceptance (reason: insufficient stock), capturing: the vendor, the order, and the timestamp. |
| FR-09.4 | **S** | The system must log product catalog changes (create, update, deactivate), capturing the user and the before/after values. |
| FR-09.5 | **M** | The distributor must be able to consult the audit log for any order from the order detail view. |
| FR-09.6 | **C** | The audit log must be append-only; no role may delete or modify existing audit entries. |

---

### FR-10 — Notifications

| ID | Priority | Requirement |
|----|----------|-------------|
| FR-10.1 | **M** | A vendor must be notified (in-app, via dashboard polling) when a new order is assigned to them. |
| FR-10.2 | **S** | A store owner must receive an in-app notification when their order status changes to `ACCEPTED` or `REJECTED`. |
| FR-10.3 | **S** | A store owner must receive an in-app notification when their order is marked `DISPATCHED`. |
| FR-10.4 | **S** | A store owner must receive an in-app notification when their order is confirmed as `DELIVERED`. |
| FR-10.5 | **C** | A vendor must receive an email notification for new orders when they are not actively using the platform. |
| FR-10.6 | **C** | A store owner must receive an email notification on order status changes when they are not actively using the platform. |

---

## Non-Functional Requirements

### NFR-01 — Security

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-01.1 | **M** | User passwords must be stored as one-way cryptographic hashes; plaintext or reversible encryption must never be used. |
| NFR-01.2 | **M** | Route access must be enforced at the server-side routing layer before any page content is rendered. |
| NFR-01.3 | **M** | Every state-changing server operation must independently verify the caller's authenticated role; routing-layer checks alone are not sufficient. |
| NFR-01.4 | **M** | All database queries must include a distributor scope filter; no query may return data belonging to a different distributor. |
| NFR-01.5 | **M** | Delivery photo identifiers must be validated to confirm they originated from the platform's own upload flow; externally supplied identifiers must be rejected. |
| NFR-01.6 | **M** | Password reset tokens must be single-use; a token that has already been used must not be accepted again. |

---

### NFR-02 — Performance & Technical Metrics

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-02.1 | **M** | API response time for list endpoints (orders, inventory) must be ≤ 500 ms at the 95th percentile under normal load. |
| NFR-02.2 | **M** | The platform must support at least 20 concurrent authenticated users without degradation in response time. |
| NFR-02.3 | **S** | System availability must be ≥ 99% during business hours (07:00–20:00 ECT, Monday–Saturday). |
| NFR-02.4 | **S** | The error rate for order-submission requests must not exceed 1% under normal operating conditions. |
| NFR-02.5 | **M** | All list views that join related data must use eager loading; N+1 query patterns are not acceptable. |
| NFR-02.6 | **M** | The `Order` table must have composite indexes on `(vendorId, status)` and on `(storeId)`. |
| NFR-02.7 | **S** | Page Time to First Byte (TTFB) for dashboard pages must be ≤ 1.5 s on a 4G mobile connection. |

---

### NFR-03 — Reliability & Consistency

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-03.1 | **M** | Inventory deduction and order status update on acceptance must execute as a single atomic transaction; partial writes are not acceptable. |
| NFR-03.2 | **M** | If a transaction fails for any reason, the order must remain in its previous status and the triggering user must receive an explicit error message. |
| NFR-03.3 | **S** | The system must handle simultaneous acceptance of the same order by two vendors; only one must succeed. |

---

### NFR-04 — Usability & Accessibility

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-04.1 | **M** | The platform is web-only; no native iOS or Android apps are in scope. |
| NFR-04.2 | **M** | All role dashboards must be mobile-responsive and functional on screens ≥ 360 px wide. |
| NFR-04.3 | **M** | Interactive elements on the store owner and delivery interfaces must have a minimum tap target size of 48 × 48 px. |
| NFR-04.4 | **M** | Text and interactive elements must meet WCAG 2.1 AA contrast ratio (≥ 4.5:1 for normal text, ≥ 3:1 for large text). |
| NFR-04.5 | **M** | The store owner order flow must complete in 3 steps or fewer from the main screen to order confirmation. |
| NFR-04.6 | **M** | Critical actions (place order, confirm delivery) must require explicit confirmation before executing. |
| NFR-04.7 | **S** | All form fields must have visible labels (not placeholder-only) to support users with low digital literacy. |
| NFR-04.8 | **S** | Error messages must describe the problem in plain, non-technical language from the user's perspective. |
| NFR-04.9 | **C** | The store owner interface must support a font size of at least 16 px as the default body text size. |

---

### NFR-05 — Deployment & Infrastructure

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-05.1 | **M** | The application must deploy on the Vercel free tier without requiring paid add-ons. |
| NFR-05.2 | **M** | The database must run on a managed PostgreSQL free tier. |
| NFR-05.3 | **M** | Photo storage must remain within the free-tier limits of the chosen cloud storage provider during MVP usage. |
| NFR-05.4 | **M** | All secrets (database URL, auth secrets, storage keys, email API key) must be injected via environment variables and must never appear in source code or version control. |

---

### NFR-06 — Maintainability

| ID | Priority | Requirement |
|----|----------|-------------|
| NFR-06.1 | **M** | The system must define exactly four roles; no superuser or admin role beyond `DISTRIBUTOR` may exist. |
| NFR-06.2 | **M** | Order state transition logic and inventory deduction must live exclusively in server-side code; client components must not contain business logic. |

---

## Testing Requirements

### TR-01 — Unit Tests

| ID | Priority | Requirement |
|----|----------|-------------|
| TR-01.1 | **S** | Order status transition rules must have unit test coverage for all valid and invalid transitions. |
| TR-01.2 | **S** | The price-snapshot logic (`unitPriceAtTime`) must have unit tests verifying it is captured at creation and does not change on catalog updates. |
| TR-01.3 | **S** | Password reset token expiry and single-use validation must have unit test coverage. |

---

### TR-02 — Integration Tests

| ID | Priority | Requirement |
|----|----------|-------------|
| TR-02.1 | **M** | The order acceptance flow (inventory check + deduction + status update) must have an integration test that verifies atomicity: when stock equals the requested quantity and two concurrent accepts arrive, exactly one succeeds and one fails. |
| TR-02.2 | **S** | The inventory deduction integration test must verify that a failed transaction leaves both the order and inventory in their pre-transaction state. |
| TR-02.3 | **S** | The `distributorId` scoping must have an integration test verifying that a user from Distributor A cannot read data belonging to Distributor B. |

---

### TR-03 — Acceptance Tests (End-to-End)

| ID | Priority | Requirement |
|----|----------|-------------|
| TR-03.1 | **M** | **Critical path 1:** A store owner logs in → creates an order for 3 products → order appears as `PENDING` in their history. |
| TR-03.2 | **M** | **Critical path 2:** A vendor logs in → sees the pending order → accepts it → order status changes to `ACCEPTED`. |
| TR-03.3 | **M** | **Critical path 3:** The vendor marks the order `DISPATCHED` → delivery personnel logs in → uploads a photo → order status changes to `DELIVERED`. |
| TR-03.4 | **M** | **Critical path 4:** The distributor logs in → sees the completed order in the dashboard → views current inventory levels without placing a phone call. |
| TR-03.5 | **S** | **Error path:** A store owner submits an order with a product not in the vendor's inventory → receives a descriptive error message; no order is created. |
| TR-03.6 | **S** | **Security path:** A user attempts to access a route belonging to a different role → receives a 403 response and is redirected to their own dashboard. |

---

## Technical Constraints

> These decisions are fixed for this project due to team constraints, academic requirements, or client agreements. They are not requirements, but they affect implementation choices.

- **Framework:** Django 4.2 MVT (server-rendered templates)
- **ORM:** Django ORM against a PostgreSQL database (Railway)
- **Authentication:** `django.contrib.auth` + custom `AbstractUser` with `role` CharField
- **Password hashing:** Django's default PBKDF2 (built-in, no extra dependency)
- **Email delivery:** Django SMTP backend → Resend SMTP relay (password reset flow)
- **Photo storage:** Cloudinary with an upload preset + Python SDK (server-side validation)
- **Styling:** Tailwind CSS (CDN or django-tailwind)
- **Static files:** WhiteNoise middleware (`collectstatic` on deploy)
- **Deployment target:** Railway (app + PostgreSQL in one project, `dj-database-url`)
- **WSGI server:** Gunicorn (`Procfile: web: gunicorn distribuidora.wsgi`)
- **Polling interval:** 30 seconds (client-side `setInterval` + `fetch()`) — no WebSockets in MVP

---

## Development Methodology — Scrum

### Overview

The team adopts **Scrum** with 2-week sprints over a 13-week semester. With a 2-person team, both members share Development Team responsibilities; roles rotate each sprint to satisfy academic documentation requirements.

| Scrum Role | Assignment |
|------------|------------|
| Product Owner | Rotates each sprint (accountable for backlog prioritization) |
| Scrum Master | Rotates each sprint (accountable for ceremonies and impediments) |
| Development Team | Both students |
| Stakeholder | ISBER Solutions (attends Sprint Review) |

---

### Ceremonies

| Ceremony | When | Duration | Purpose |
|----------|------|----------|---------|
| Sprint Planning | Day 1 of each sprint | 1 h | Select backlog items, break into tasks, assign to Lane A / Lane B |
| Daily Standup | Every weekday | 15 min | What did I do? What will I do? Any blockers? |
| Sprint Review | Last day of each sprint | 30 min | Live demo to ISBER; collect feedback; update backlog |
| Sprint Retrospective | After Sprint Review | 30 min | What went well / what to improve for next sprint |

---

### Definition of Done

A backlog item is **Done** when all of the following are true:

- [ ] All acceptance criteria from the linked requirement ID are met
- [ ] Code reviewed by the other team member (at least one approval)
- [ ] Relevant unit or integration test written and passing (for all **M** items)
- [ ] No known critical bugs introduced
- [ ] Feature deployed and verified on Railway staging environment
- [ ] Audit log entry generated if the feature triggers a state change (FR-09)

---

### Product Backlog

The backlog is ordered by sprint target. Items are identified by requirement ID and MoSCoW priority.

| Backlog Item | Requirement IDs | Priority | Lane | Sprint |
|--------------|----------------|----------|------|--------|
| Project setup: Django, PostgreSQL, Railway, `.env`, `AUTH_USER_MODEL` | — | **M** | Both | 0 |
| Custom User model (`AbstractUser` + `role` + `distributor` FK) | FR-02.1, FR-02.2 | **M** | A | 1 |
| Login / Logout views | FR-01.1, FR-01.2, FR-01.5 | **M** | A | 1 |
| `@role_required` decorator + route protection | FR-02.3, FR-02.4, FR-02.5 | **M** | A | 1 |
| Password reset flow (Django SMTP + Resend) | FR-01.3, FR-01.4, FR-01.6 | **M** | B | 1 |
| Distributor + Store models with `distributor` FK | FR-02.5 | **M** | A | 2 |
| Product CRUD (distributor only) | FR-03.1–FR-03.4 | **M** | A | 2 |
| VendorInventory assignment | FR-03.5, FR-04.1, FR-04.2 | **M** | A | 2 |
| Cloudinary upload preset + `public_id` validation | FR-07.3, FR-07.5 | **M** | B | 2 |
| Order creation with price snapshot (`unit_price_at_time`) | FR-05.1, FR-05.4 | **M** | A | 3 |
| Product availability validation at submit time | FR-05.3 | **M** | A | 3 |
| Vendor order queue view (pending orders) | FR-06.1 | **M** | A | 3 |
| Order accept with `transaction.atomic()` + `select_for_update()` | FR-04.3, FR-04.4, FR-06.2–FR-06.4 | **M** | A | 3 |
| Order reject + dispatch transitions | FR-06.4, FR-06.5 | **M** | A | 3 |
| JS polling module (30 s, vendor dashboard) | FR-06.6, FR-10.1 | **M** | B | 3 |
| Store owner order status view | FR-05.5 | **M** | B | 3 |
| Delivery confirmation view + photo upload | FR-07.1, FR-07.2, FR-07.4 | **M** | A | 4 |
| Audit log on every order status transition | FR-09.1, FR-09.2, FR-09.5 | **M** | B | 4 |
| Distributor operations dashboard (orders + inventory) | FR-08.1, FR-08.3 | **M** | B | 4 |
| DB indexes on `Order(vendor, status)` and `Order(store)` | NFR-02.6 | **M** | B | 4 |
| N+1 prevention with `select_related` on all list views | NFR-02.5 | **M** | A | 4 |
| In-app status notifications for store owner | FR-10.2–FR-10.4 | **S** | B | 5 |
| Dashboard filters (date, vendor, store, status) | FR-08.2 | **S** | A | 5 |
| Summary metrics (total orders, fulfilled, rejected) | FR-08.4 | **S** | A | 5 |
| Audit log for catalog changes and failed accepts | FR-09.3, FR-09.4 | **S** | B | 5 |
| Low-stock alert for distributor | FR-04.5 | **S** | B | 5 |
| Product soft-delete | FR-03.3 | **S** | A | 5 |
| Unit tests: order state transitions, price snapshot, reset token | TR-01.1–TR-01.3 | **S** | Both | 6 |
| Integration tests: atomic accept, rollback, tenant isolation | TR-02.1–TR-02.3 | **M** | Both | 6 |
| E2E tests: 4 critical paths + error + security paths | TR-03.1–TR-03.6 | **M** | Both | 6 |
| Production deploy + `collectstatic` + smoke test | NFR-05.1–NFR-05.4 | **M** | Both | 6 |
| CSV export for order history | FR-08.5 | **C** | A | Backlog |
| Email notifications for all order events | FR-10.5, FR-10.6 | **C** | B | Backlog |
| Append-only audit log enforcement | FR-09.6 | **C** | B | Backlog |

---

### Sprint Plan

```
Sprint 0 — Environment Setup (1 week)
  Goal : Repository, Django project skeleton, Railway + PostgreSQL connected,
         AUTH_USER_MODEL set before first migration, .env configured.
  Done : manage.py runserver works against Railway DB; no migrations pending.

Sprint 1 — Auth & RBAC (weeks 2–3)
  Goal : Any user can register, log in, log out, and reset their password.
         Routes are protected by role; @role_required rejects wrong-role access.
  Lane A: Custom User model → login/logout → @role_required decorator
  Lane B: Password reset flow (Django SMTP → Resend)
  Demo  : Log in as DISTRIBUTOR, attempt /vendor/ → receive 403.

Sprint 2 — Catalog & Inventory (weeks 4–5)
  Goal : Distributor can manage products and assign stock to vendors.
         Cloudinary upload preset is configured and validated server-side.
  Lane A: Store model + distributor FK → Product CRUD → VendorInventory
  Lane B: Cloudinary upload preset + public_id validation logic
  Demo  : Distributor creates a product, assigns 50 units to Vendor A.

Sprint 3 — Order Lifecycle (weeks 6–7)
  Goal : Complete order flow from creation to dispatch.
         Inventory deduction is atomic; vendor dashboard auto-refreshes.
  Lane A: Order creation + price snapshot → availability validation →
          accept (transaction.atomic + select_for_update) → reject → dispatch
  Lane B: JS polling module → store owner order status view
  Demo  : Store places order → vendor accepts → inventory deducted → status DISPATCHED.

Sprint 4 — Delivery, Audit & Dashboard (weeks 8–9)
  Goal : Delivery personnel confirm with photo; distributor sees full picture.
         Audit trail records every state change.
  Lane A: Delivery confirmation view + photo upload → N+1 prevention
  Lane B: Audit log → Distributor dashboard → DB indexes
  Demo  : Delivery uploads photo → order DELIVERED → distributor sees audit trail.

Sprint 5 — Secondary Features (weeks 10–11)
  Goal : Should-have items that complete the product for ISBER.
  Lane A: Dashboard filters + summary metrics → product soft-delete
  Lane B: In-app notifications → catalog/failure audit logs → low-stock alert
  Demo  : Distributor filters orders by vendor; store owner sees ACCEPTED notification.

Sprint 6 — Testing & Ship (weeks 12–13)
  Goal : All M-priority tests passing; app live on Railway production.
  Both  : Unit tests → integration tests (race condition) → Playwright e2e →
          production deploy → ISBER final demo
  Done  : 4 critical Playwright paths green; Railway production URL delivered to ISBER.
```

---

### Velocity & Estimation Notes

- Each sprint has a capacity of approximately **40 developer-hours** (2 students × 20 h/sprint, accounting for classes).
- Items marked **P1** in the design doc map to Sprint 1–3 (core vertical slice).
- Items marked **P2** map to Sprint 4–5 (secondary features and hardening).
- Items marked **P3** (Playwright e2e) are deferred to Sprint 6 to avoid testing incomplete flows.
- If Sprint 5 is not completed, **C-priority items move to Backlog** without affecting the MVP demo.

---

## Out of Scope (MVP)

Explicitly deferred to a post-graduation roadmap:

| Feature | Reason deferred |
|---------|-----------------|
| SRI electronic invoicing | Regulatory complexity exceeds academic timeline |
| Commission calculation | Requires payroll integration out of scope |
| Vendor training module | Nice-to-have, no client urgency |
| Biometric verification | Infrastructure not available |
| Route optimization / geolocation | Third-party API cost and complexity |
| Advanced analytics or AI features | Post-MVP phase |
| Nationwide multi-tenant scaling | Infrastructure upgrade required |
| Email notifications for all events | Phase 2 (only password reset in MVP) |
