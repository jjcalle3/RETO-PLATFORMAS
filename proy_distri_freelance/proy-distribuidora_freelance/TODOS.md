# TODOS

## Feature ideas

- [ ] **Low-stock severity tiers on the distributor dashboard** — the current "Inventario por almacén" table (accounts/templates/accounts/dashboard.html) shows raw quantity vs. threshold with no visual severity. Add a two-tier badge (e.g. `Crítico` when stock is near/at 0, `Bajo` when under threshold but not critical) so distributors can triage restocking at a glance instead of scanning every row. Surfaced during `/design-consultation` (2026-07-24) — came out of a design mockup that included this and the user wanted it captured for later rather than built immediately.
- [ ] **Delivery photo-capture UI** — `DeliveryConfirmation.photo_public_id` (deliveries/models.py) implies a photo-at-delivery flow, but there's no UI for it anywhere and photo storage is explicitly out of scope per CLAUDE.md. Needs product scoping first: is a photo required or optional at confirm time? Where is it actually stored/displayed? Surfaced during `/plan-design-review` (2026-07-24) — deferred rather than designing a UI for an unscoped flow.
