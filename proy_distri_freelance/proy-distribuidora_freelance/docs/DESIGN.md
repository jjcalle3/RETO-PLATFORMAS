# Design System — ISBEN SOLUTION

**Last updated:** 2026-07-19
**Source:** brand sheet provided directly (colors + typeface names); logo files in `proyectoDistribuidora/static/media/`.

> **Naming discrepancy — unresolved.** The brand assets and this document say **"ISBEN SOLUTION"**. Every other project document (`docs/requirements.md`, `CLAUDE.md`, `README.md`, in-app headings, code comments) says **"ISBEN Solutions"** (with an R, plural). Nobody has confirmed which is the typo. Until someone does, treat both spellings as referring to the same client — don't silently "correct" one to match the other.

---

## Brand colors

| Swatch | Hex | CMYK | Role |
|---|---|---|---|
| 🟧 Color 1 (left) | `#FB4318` | C0 M79 Y95 K0 | Primary — orange |
| 🟨 Color 2 (right) | `#FFC22F` | C0 M22 Y93 K0 | Secondary — gold |

In the logo, both colors run as a diagonal gradient (orange → gold) through the isotype, and split across the wordmark: "ISBEN" set in the orange, "SOLUTION" set in the gold.

### Gap: not yet applied to the running app

`proyectoDistribuidora/static/css/styles.css` currently uses a placeholder palette that has nothing to do with this brand:

```css
--color-primary: #034275;       /* dark blue */
--color-primary-light: #258ead;
--color-error: #b3261e;
```

Wiring `#FB4318` / `#FFC22F` into `styles.css` (and adding a logo `<img>` to `base.html`'s header, which is currently plain text) is **not done in this pass** — this document only records the tokens as given, so implementing them is a well-defined future task.

---

## Typography

| Given name | Likely role (inferred, not confirmed) |
|---|---|
| Futura | Display / headings / wordmark — matches the geometric, wide-tracked lettering visible in the logo |
| Verdana | Body / UI text — highly legible on screen, installed everywhere; a safe fallback since Futura isn't universally available in browsers without a webfont license |

**This role mapping is an inference**, not something the brand sheet specified explicitly — only the two names were given, "TIPOGRAFIA / VERDANA / FUTURA", with no stated pairing. Confirm with whoever supplied the sheet before wiring it into CSS.

Neither typeface is applied yet — `styles.css` currently uses `"Segoe UI", Arial, Helvetica, sans-serif`.

---

## Logo assets (`proyectoDistribuidora/static/media/`)

| File | Variant | Background | Suggested use |
|---|---|---|---|
| `logos_1.png` | Vertical lockup — isotype above wordmark | White | Tall/narrow spaces: splash screen, login card |
| `logos_2.png` | Horizontal lockup — isotype left of wordmark | White | Nav bar header, wide banners |
| `iso_1.png` | Isotype only (leopard/jaguar head, gradient-outline) | White | Favicon source, small UI marks |
| `iso_2.png` | Isotype only — near-identical to `iso_1.png` | White | Appears to be a duplicate/alt export; confirm which is canonical before picking one |
| `iso_perfil.png` | Isotype, reversed to white | Orange→gold gradient fill | Avatar/profile picture, placements on dark or colored backgrounds |
| `logos_1 - copia.jpg.jpeg` | JPEG export of `logos_1.png` | White | Likely a duplicate left over from export — candidate for cleanup |
| `logos_ISBEN.jpg.jpeg` | JPEG export (unreviewed) | — | Likely a duplicate — candidate for cleanup |

**None of these are referenced from any template yet.** `templates/base.html`'s header is still plain text (`<h1>ISBEN Solutions — Distribuidora</h1>`), no `<img>`. Wiring in a logo is listed as a future-task item in `docs/ux-navigation-wireframes.md`.

### Icon motif

The isotype is a leopard/jaguar head in profile, its fur rendered as a scattered pattern of circles and half-circles trailing off the back of the head. Distinctive enough to reuse elsewhere in future polish work — as a loading spinner, an empty-state illustration, or a subtle watermark.

---

## Open questions for whoever owns the brand sheet

1. Is the client name "ISBEN" or "ISBEN"? The client name is ISBEN
2. Confirm the Futura/Verdana role split (display vs. body) — It could be use in either way, its not specified
3. `iso_1.png` vs `iso_2.png` — are these meant to be identical, or is one a stale export?
4. Are the two `.jpg.jpeg` files intentional (e.g., a specific export a stakeholder requested) or leftover clutter?
