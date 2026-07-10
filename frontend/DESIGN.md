# DESIGN.md — arvel-ecommerce-kit design system ("BestShop" v6)

The documented contract the whole SPA conforms to. It **ratifies** the existing token
system in `src/styles/tokens.css` — it does not redesign it. Values below are copied from
that file; `tokens.css` is the single source of truth and this doc mirrors it. If the two
ever disagree, `tokens.css` wins and this file is the bug.

House rule, non-negotiable: **components never hardcode color, space, radius, or type.**
They reference `var(--token)`. A raw hex/px color value in a component is a defect, not a
style choice (see Findings).

Conventions in this doc:

- Every token is listed with its **light** value and, where it changes, its **dark** value
  (`[data-theme='dark']`). A token with no dark entry keeps its light value in both themes.
- Tokens whose value is `var(--other)` resolve through the referenced token — so an accent
  that points at `--orange-600` re-themes automatically when `--orange-600` flips in dark.

---

## 1. Structure — two registers, two themes

One stylesheet drives everything through four combinations:

- **Theme** is set by `[data-theme='dark']` on a root element. It re-declares the surface,
  text, border, chrome, accent-in-dark, and status-background tokens. Light is the `:root`
  default.
- **Register** is a class on a layout root:
  - `.shop` — the storefront. Follows the theme `--bg` (paper white in light, graphite in dark).
  - `.console` — the admin. Sets `--bg: var(--canvas)` so it sits on the slightly deeper
    canvas one step down from the storefront's paper.

Everything else is component-scoped and reads tokens. The four states an interface can be
in — **empty, loading, error, populated** — are the designer's responsibility on every
screen, not just the happy path (Cart empty vs. filled, Catalog loading vs. results vs. zero
results, form submit error, etc.).

---

## 2. Token catalog

Every custom property in `tokens.css`, by category. No token in the file is omitted here;
nothing here is absent from the file (that equivalence is a mechanical acceptance check — see
the K1 handoff).

### 2.1 Brand ramp — Paper · Charcoal · Orange · Peach

The CTA "ramp" is the load-bearing idea: **one orange family, split by job.** A deep,
text-safe ramp (`700/600/500`) drives buttons and interactive states where the orange must
also carry white text or sit under text; a separate **bright** graphic orange
(`--orange-bright`) is for decoration only — badges, the announcement marquee — where it is
never a text foreground on a light surface (it would fail contrast). Never use `--orange-bright`
as text on paper.

| Token             | Light     | Dark      | For                                |
| ----------------- | --------- | --------- | ---------------------------------- |
| `--orange-700`    | `#9a3d08` | `#f0752a` | ramp — pressed/darkest accent      |
| `--orange-600`    | `#c2410c` | `#ff8a3d` | ramp — base accent (buttons)       |
| `--orange-500`    | `#e85d04` | `#ffa05c` | ramp — hover; "text-safe CTA ramp" |
| `--orange-bright` | `#ff8a00` | —         | graphic only: badges, marquee      |
| `--ink-950`       | `#121214` | —         | ink scale (shadows, deepest)       |
| `--ink-900`       | `#18181b` | —         | ink scale                          |
| `--ink-800`       | `#232326` | —         | neutral ink                        |
| `--peach-100`     | `#f7e5d2` | —         | hero band tint (light)             |
| `--peach-200`     | `#f3d9bd` | —         | hero band tint, deeper             |

### 2.2 Neutrals & surfaces

White cards on a cool-neutral canvas in light; cool-neutral blacks with clearly-elevated
surfaces in dark. Separation is done by **borders**, not shadows (see Elevation).

The **photo-well** (`--photo-well`) is a deliberate exception to theming: product photography
sits in a _fixed light tile in both themes_. White-background product shots read as designed
"framed tiles" in dark mode instead of blown-out holes punched in a dark page. In dark,
`ProductCard` additionally insets the tile and dims the image ~12% so warm photo-whites don't
glare — a documented pattern, not an ad-hoc filter.

| Token            | Light              | Dark      | For                                                           |
| ---------------- | ------------------ | --------- | ------------------------------------------------------------- |
| `--white`        | `#ffffff`          | —         | literal white                                                 |
| `--bg`           | `#ffffff`          | `#131417` | page background (`.shop`); `.console` overrides to `--canvas` |
| `--canvas`       | `#f5f5f4`          | `#0e0f12` | the deeper canvas; console background                         |
| `--surface`      | `#ffffff`          | `#1a1c21` | cards, panels, raised surface                                 |
| `--surface-2`    | `#f5f5f4`          | `#232630` | inset surface: inputs, wells, secondary fills                 |
| `--photo-well`   | `#f4f4f2`          | `#f4f4f2` | product photo tile — fixed light in both themes               |
| `--band`         | `var(--peach-100)` | `#1a1d26` | tinted section band                                           |
| `--hero-band`    | `var(--peach-100)` | `#1a1d26` | hero band tint                                                |
| `--border`       | `#e9e8e4`          | `#2a2c33` | default hairline border                                       |
| `--border-2`     | `#d8d6d0`          | `#383b44` | stronger border (inputs, dividers)                            |
| `--text`         | `#18181b`          | `#f2f3f5` | body/primary text                                             |
| `--text-muted`   | `#54555a`          | `#a6a9b1` | secondary text (passes AA on surface)                         |
| `--text-subtle`  | `#6e6f75`          | `#878b94` | tertiary/label/placeholder text                               |
| `--text-inverse` | `#ffffff`          | `#131417` | text on an inverted fill                                      |

### 2.3 Charcoal chrome (storefront nav)

The reference's signature dark nav bar, kept dark in both themes.

| Token           | Light                  | Dark      | For                          |
| --------------- | ---------------------- | --------- | ---------------------------- |
| `--nav-bg`      | `#1b1b1e`              | `#0b0c0e` | nav / dark chrome background |
| `--nav-text`    | `#d9d8d4`              | `#a6a9b1` | nav link text                |
| `--nav-text-hi` | `#ffffff`              | `#ffffff` | nav active/hover text        |
| `--nav-active`  | `var(--orange-bright)` | —         | nav active indicator         |

### 2.4 Semantic — accent, status, focus

`--accent` and its hover/press states point at the ramp, so they re-theme in dark for free.
The **accent-text** token is the single most important accessibility contract in the system
(see §4.1).

| Token                | Light                  | Dark       | For                                                                                               |
| -------------------- | ---------------------- | ---------- | ------------------------------------------------------------------------------------------------- |
| `--accent`           | `var(--orange-600)`    | (via ramp) | primary action fill                                                                               |
| `--accent-hover`     | `var(--orange-500)`    | (via ramp) | action hover fill                                                                                 |
| `--accent-press`     | `var(--orange-700)`    | (via ramp) | action pressed fill                                                                               |
| `--on-accent`        | `#ffffff`              | `#1f1204`  | text/icon on `--accent` fill (white on orange-600 = 5.4:1 in light; ink on bright orange in dark) |
| `--accent-text`      | `#b33a05`              | `#ffa05c`  | **the ONLY token allowed as accent-colored text** — see §4.1                                      |
| `--accent-bright`    | `var(--orange-bright)` | (via ramp) | graphic accent (badges)                                                                           |
| `--on-accent-bright` | `#221100`              | `#221100`  | ink on the bright graphic orange                                                                  |
| `--star`             | `#f5a623`              | `#ffc24d`  | rating star fill (graphic)                                                                        |
| `--success`          | `#3f7a4e`              | —          | success base                                                                                      |
| `--success-bg`       | `#e4f0e6`              | `#14281b`  | success surface                                                                                   |
| `--success-fg`       | `#2e5e3b`              | `#7ed495`  | text on success surface                                                                           |
| `--danger`           | `#b03a3a`              | —          | danger base                                                                                       |
| `--danger-bg`        | `#f7e3e1`              | `#301719`  | danger/error surface                                                                              |
| `--danger-fg`        | `#8e2f2f`              | `#ff9b95`  | text on danger surface                                                                            |
| `--warn`             | `#b0803a`              | —          | warning base                                                                                      |
| `--warn-bg`          | `#f6ecd8`              | `#2c230f`  | warning surface                                                                                   |
| `--warn-fg`          | `#7e5820`              | `#e9c063`  | text on warning surface                                                                           |
| `--info`             | `#3b6e9e`              | —          | info base                                                                                         |
| `--info-bg`          | `#e2ecf5`              | `#122334`  | info surface                                                                                      |
| `--info-fg`          | `#2c5479`              | `#8fc1ee`  | text on info surface                                                                              |
| `--sale`             | `#c62828`              | `#ff6b6b`  | sale price (red)                                                                                  |
| `--sale-bg`          | `#fdebea`              | `#31191c`  | sale surface                                                                                      |
| `--focus`            | `var(--orange-600)`    | `#ff8a3d`  | focus ring color (see §4.2)                                                                       |
| `--stock-good`       | `#22c55e`              | —          | admin stock-bar fill: healthy (graphic, AA-exempt §4.1)                                           |
| `--stock-low`        | `#f59e0b`              | —          | admin stock-bar fill: low (graphic, AA-exempt §4.1)                                               |
| `--stock-out`        | `#ef4444`              | —          | admin stock-bar fill: out (graphic, AA-exempt §4.1)                                               |

### 2.5 Category tiles

Ink text on linen tints; used behind ≥24px bold category labels. Three keep their light value
in dark (`--cat-orange`, `--cat-teal`, `--cat-indigo`); three lighten for dark contrast.

| Token          | Light     | Dark      |
| -------------- | --------- | --------- |
| `--cat-violet` | `#6b5a70` | `#9d89a6` |
| `--cat-blue`   | `#33506b` | `#6e8fb3` |
| `--cat-orange` | `#b0803a` | —         |
| `--cat-teal`   | `#3e6b78` | —         |
| `--cat-rose`   | `#a56b76` | `#c795a0` |
| `--cat-indigo` | `#4a4a63` | —         |

### 2.6 Admin sidebar chrome

Paper chrome in light, charcoal in dark; ink text, orange active.

| Token            | Light                                                    | Dark      |
| ---------------- | -------------------------------------------------------- | --------- |
| `--side-bg`      | `#ffffff`                                                | `#101114` |
| `--side-bg-2`    | `#f5f5f4`                                                | `#1a1b20` |
| `--side-active`  | `color-mix(in srgb, var(--orange-600) 12%, transparent)` | `…18%…`   |
| `--side-text`    | `#54555a`                                                | `#a6a9b1` |
| `--side-text-hi` | `#18181b`                                                | `#f2f3f5` |
| `--side-border`  | `#e9e8e4`                                                | `#2a2c33` |

### 2.7 Typography

`--font-display` (bold geometric display — uppercase heroes, headings, prices);
`--font-text` (body); `--font-mono` (IDs/slugs/tabular). The Arabic faces are bundled into the
display/text stacks so RTL renders in-family. Headings (`h1–h4`) use the display font with
tight tracking + tight leading globally.

| Token               | Value                                                                   |
| ------------------- | ----------------------------------------------------------------------- |
| `--font-display`    | `'Archivo', 'Cairo', 'Inter', ui-sans-serif, system-ui, sans-serif`     |
| `--font-text`       | `'Inter', 'IBM Plex Sans Arabic', ui-sans-serif, system-ui, sans-serif` |
| `--font-mono`       | `ui-monospace, 'SF Mono', Menlo, monospace`                             |
| `--text-2xs`        | `0.6875rem`                                                             |
| `--text-xs`         | `0.75rem`                                                               |
| `--text-sm`         | `0.875rem`                                                              |
| `--text-base`       | `1rem`                                                                  |
| `--text-lg`         | `1.125rem`                                                              |
| `--text-xl`         | `1.375rem`                                                              |
| `--text-2xl`        | `1.75rem`                                                               |
| `--text-3xl`        | `2.25rem`                                                               |
| `--text-4xl`        | `3rem`                                                                  |
| `--text-5xl`        | `3.5rem`                                                                |
| `--leading-tight`   | `1.15`                                                                  |
| `--leading-snug`    | `1.4`                                                                   |
| `--leading-normal`  | `1.6`                                                                   |
| `--weight-regular`  | `400`                                                                   |
| `--weight-medium`   | `500`                                                                   |
| `--weight-semibold` | `600`                                                                   |
| `--weight-bold`     | `700`                                                                   |
| `--tracking-tight`  | `-0.01em`                                                               |
| `--tracking-wide`   | `0.08em`                                                                |

Under RTL, no element may carry `letter-spacing` (Arabic is a connected script — tracking
breaks the joins). `base.css` enforces this globally; the Latin wordmark is the one exception.

### 2.8 Space (4px base)

| Token       | Value     |     | Token        | Value    |
| ----------- | --------- | --- | ------------ | -------- |
| `--space-1` | `0.25rem` |     | `--space-8`  | `2rem`   |
| `--space-2` | `0.5rem`  |     | `--space-10` | `2.5rem` |
| `--space-3` | `0.75rem` |     | `--space-12` | `3rem`   |
| `--space-4` | `1rem`    |     | `--space-16` | `4rem`   |
| `--space-5` | `1.25rem` |     | `--space-20` | `5rem`   |
| `--space-6` | `1.5rem`  |     | `--space-24` | `6rem`   |

### 2.9 Radius

Crisp cards; `--radius-full` is the pill/circle (search, view-toggles, badges, touch targets).

| Token           | Value   |
| --------------- | ------- |
| `--radius-sm`   | `5px`   |
| `--radius-md`   | `8px`   |
| `--radius-lg`   | `12px`  |
| `--radius-xl`   | `16px`  |
| `--radius-full` | `999px` |

### 2.10 Elevation (shadow)

Near-shadowless by design — **borders do the separation**, shadows only lift interactive/overlay
surfaces. All four re-declare stronger/darker in dark.

| Token          | Light                           | Dark                          |
| -------------- | ------------------------------- | ----------------------------- |
| `--shadow-1`   | `0 1px 2px rgba(18,18,20,.04)`  | `0 1px 2px rgba(0,0,0,.5)`    |
| `--shadow-2`   | `0 2px 8px rgba(18,18,20,.06)`  | `0 2px 10px rgba(0,0,0,.5)`   |
| `--shadow-3`   | `0 8px 24px rgba(18,18,20,.08)` | `0 10px 28px rgba(0,0,0,.55)` |
| `--shadow-pop` | `0 8px 28px rgba(18,18,20,.12)` | `0 10px 32px rgba(0,0,0,.6)`  |

### 2.11 Motion

| Token           | Value                            |
| --------------- | -------------------------------- |
| `--motion-fast` | `120ms`                          |
| `--motion-base` | `180ms`                          |
| `--motion-slow` | `280ms`                          |
| `--ease`        | `cubic-bezier(0.2, 0, 0, 1)`     |
| `--ease-out`    | `cubic-bezier(0.22, 1, 0.36, 1)` |

All motion is gated behind `prefers-reduced-motion` (see §4.3).

### 2.12 Layout & z-index

| Token             | Value                      |     | Token          | Value |
| ----------------- | -------------------------- | --- | -------------- | ----- |
| `--container-max` | `1320px`                   |     | `--z-header`   | `100` |
| `--container-pad` | `clamp(1rem, 4vw, 2.5rem)` |     | `--z-side`     | `110` |
| `--side-w`        | `248px`                    |     | `--z-dropdown` | `200` |
| `--header-h`      | `64px`                     |     | `--z-overlay`  | `300` |
| `--topbar-h`      | `62px`                     |     | `--z-modal`    | `310` |
|                   |                            |     | `--z-toast`    | `400` |

**Breakpoints are NOT tokens.** There is no preprocessor, so a `var()` can't be used inside a
`@media` condition. The two-tier scale is documented in the `tokens.css` header and is the
single source of truth: `640px` (large phone / small tablet) and `1024px` (desktop). Base
(unqueried) styles target the smallest phone; every storefront `@media` should be `min-width`
using one of those two values — do not introduce a third tier. (`--bp-sm`/`--bp-lg` are names
in that comment, not CSS custom properties — don't add them to this catalog.)

### 2.13 Compatibility shim (`--color-*`)

Legacy names from the pre-consolidation apps, aliased to the v6 tokens so ported views inherit
the palette + dark theme unchanged. **New code uses the v6 names above; migrate a view off
these when it's redesigned.** These are live tokens and part of the catalog.

| Token                   | Aliases                                              |
| ----------------------- | ---------------------------------------------------- |
| `--color-bg`            | `var(--bg)`                                          |
| `--color-surface`       | `var(--surface)`                                     |
| `--color-surface-2`     | `var(--surface-2)`                                   |
| `--color-border`        | `var(--border)`                                      |
| `--color-border-strong` | `var(--border-2)`                                    |
| `--color-text`          | `var(--text)`                                        |
| `--color-text-muted`    | `var(--text-muted)`                                  |
| `--color-text-faint`    | `var(--text-subtle)`                                 |
| `--color-text-inverse`  | `var(--on-accent)`                                   |
| `--color-accent`        | `var(--accent)`                                      |
| `--color-accent-hover`  | `var(--accent-hover)`                                |
| `--color-accent-text`   | `var(--on-accent)`                                   |
| `--color-accent-soft`   | `color-mix(in srgb, var(--accent) 14%, transparent)` |
| `--color-danger`        | `var(--danger)`                                      |
| `--color-danger-soft`   | `var(--danger-bg)`                                   |
| `--color-success`       | `var(--success)`                                     |
| `--color-focus`         | `var(--focus)`                                       |

> Note: there is **no `--color-warning` token**, and there is no longer a reference to one —
> the one call site (`ProductDetailView.vue` review stars) was migrated to `--star`, the token
> that already exists for exactly this purpose (rating-star fill). See Findings.

### 2.14 Dataviz (admin dashboard)

The admin `DashboardView` chart/KPI-card palette — graphic-only, exempt from the accent-text
text-contrast rule (§4.1), not theme-aware by design (matches the fixed "vibrant card palette
per design direction"). The view's local `--g-*`/`--c-*` names alias these one-for-one.

| Token              | Value                                       | For                                   |
| ------------------ | ------------------------------------------- | ------------------------------------- |
| `--chart-pink`     | `#d83b7c`                                   | order-status donut segment / KPI tone |
| `--chart-violet`   | `#6f4fe0`                                   | order-status donut segment / KPI tone |
| `--chart-blue`     | `#2f9fd8`                                   | order-status donut segment / KPI tone |
| `--chart-orange`   | `#f2871f`                                   | order-status donut segment / KPI tone |
| `--chart-teal`     | `#16b8a6`                                   | order-status donut segment (5th hue)  |
| `--chart-purple`   | `#7b5cff`                                   | orders trend line + area              |
| `--chart-g-pink`   | `linear-gradient(135deg, #f2618f, #c0206a)` | KPI card fill                         |
| `--chart-g-violet` | `linear-gradient(135deg, #8b62f0, #5b3fd6)` | KPI card fill                         |
| `--chart-g-blue`   | `linear-gradient(135deg, #3fb9e6, #2a86d6)` | KPI card fill                         |
| `--chart-g-orange` | `linear-gradient(135deg, #fbab3c, #f47b20)` | KPI card fill                         |

**Category counts:** brand 9 · neutrals/surfaces 14 · nav chrome 4 · semantic 26 · category
tiles 6 · sidebar 6 · type 22 · space 12 · radius 5 · elevation 4 · motion 5 · layout+z 11 ·
compat shim 17 · dataviz 10. The dark block re-declares existing token _values_; it introduces no new token
names. `.console` overrides `--bg` only.

---

## 3. Component inventory (50 components)

Grouped by area, mapped to the tokens/patterns each leans on. All confirmed reading `var(--token)`
except the Findings in §5. Shared primitives are styled in `base.css` (form controls, focus ring,
links, selection) and `src/admin/styles/list.css` (the whole admin-list system).

### 3.1 Shared primitives (base.css + list.css, not components)

- **Form controls** (`input/select/textarea`) — `--surface-2` fill, `--border-2`, `--radius-md`,
  `--text`, `--text-subtle` placeholder, `accent-color: --accent`. Explicit colors so native
  controls stay legible in dark.
- **Focus ring** — global `:focus-visible` → `2px solid var(--focus)`, `2px` offset (§4.2).
- **Links / selection** — inherit color; selection uses `color-mix(--accent 30%)`.
- **Admin-list system** (`.apage` scope): `.toolbar`, `.viewtog`, `.search`, `.filters`,
  `.notice`, `.bulk`, `.panel`, `.prod/.thumb`, `.stock` bar, `.grid/.card`, `.pager/.empty`,
  `.form/.fld`, full-page editor (`.ehead/.ecard/.ebar/.frow`), locale tabs (`.locs`). All
  surface/border/radius/shadow token-driven.

### 3.2 App shell (2)

| Component             | Uses                                                                        |
| --------------------- | --------------------------------------------------------------------------- |
| `App.vue`             | register root, route transitions (`fade`/`vt`), theme                       |
| `shop/ShopLayout.vue` | `.shop` register, `--nav-*` charcoal chrome, `--header-h`, container tokens |

### 3.3 Storefront components (5)

| Component            | Uses                                                                                                                                                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ProductCard.vue`    | `--surface/--border/--radius-md`, `--photo-well` + dark inset/dim, `--accent-bright`/`--on-accent-bright` deal badge, `--sale` price, `--star`, `--accent-text` (link/heart hover), 44px heart target, `--motion-base` |
| `DealCard.vue`       | deal badge (`--accent-bright`), `--sale`, countdown, card tokens                                                                                                                                                       |
| `CountdownTimer.vue` | `tnum`, `--text`/`--accent`, reduced-motion aware                                                                                                                                                                      |
| `NewsletterBand.vue` | `--band`/`--hero-band`, `--accent` CTA                                                                                                                                                                                 |
| `MobileNav.vue`      | `--nav-*`, `--z-*`, drawer overlay, focus-visible                                                                                                                                                                      |

### 3.4 Storefront views (10)

| Component                                                                  | Uses / notable states                                                                                                                                       |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `HomeView.vue`                                                             | hero `--hero-band`, category tiles (`--cat-*`), product grids; loading/empty                                                                                |
| `CatalogView.vue`                                                          | filter rail, `ProductCard` grid, min-width tiers; loading / zero-results empty                                                                              |
| `ProductDetailView.vue`                                                    | `--photo-well` gallery + `view-transition-name` morph, `--sale`, star review, add-to-bag states, stock/status text (**Finding: raw `--color-*` fallbacks**) |
| `CartView.vue`                                                             | line items, `tnum` totals, **empty state**, success (**Finding: raw fallback**)                                                                             |
| `CheckoutView.vue`                                                         | multi-step form, `--danger-bg/--danger-fg` errors, order summary; submit error/loading                                                                      |
| `DealsView.vue`                                                            | `DealCard` grid, countdowns                                                                                                                                 |
| `OrderDetailView.vue`                                                      | status chips (`--success/--warn/--info/--danger` families), `tnum`                                                                                          |
| `ForgotPasswordView.vue` / `ResetPasswordView.vue` / `VerifyEmailView.vue` | auth forms, `role`/`aria-live` messaging, error/success states                                                                                              |

### 3.5 Account area (7)

`account/AccountLayout.vue` (side-nav shell) + panes `ProfilePane`, `SecurityPane`,
`AddressesPane`, `NotificationsPane`, `OrdersPane`, `WishlistPane`. All use the form primitives,
`--surface`/`--border` cards, status surfaces for save/error feedback; each has empty and
error states (empty wishlist, no orders, save failed).

### 3.6 Admin shell + shared editor (3)

| Component                         | Uses                                                                                                                                  |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `admin/AdminLayout.vue`           | `.console` register, `--side-*` sidebar, `--side-active` orange, `--z-side`, `--on-accent`                                            |
| `admin/components/EditorPage.vue` | `.apage` full-page editor scaffold (`.ehead/.ecard/.ebar`)                                                                            |
| `admin/views/DashboardView.vue`   | KPI cards + charts. **Finding: dataviz palette hardcoded** (`--g-*`/`--c-*`, `#7b5cff`) — an intentional, un-tokenized chart palette. |

### 3.7 Admin list + editor views (23)

Lists: `ProductsView` (origin of `list.css`), `CategoriesView`, `VendorsView`, `CouponsView`,
`DealsView`, `BannersView`, `OrdersView`, `UsersView`, `RolesView`, `ReviewsView`,
`NewsletterView`, `MediaView`, `AuditView`, `SettingsView`, `OrderDetailView`, `LoginView`,
`CallbackView`.
Editors: `ProductEditView`, `CategoryEditView`, `VendorEditView`, `CouponEditView`,
`DealEditView`, `BannerEditView`.
All render through the `.apage` list/editor system — toolbar, filters (`--surface`/`--border`),
`.notice` (`--danger-bg/--danger-fg`), bulk bar (`color-mix(--accent)`), table/card panels,
stock bar (**Finding: hardcoded `#22c55e/#f59e0b/#ef4444`**), locale tabs, sticky save bar.
Each list owns empty (`.empty`), loading, and error (`.notice`) states.

---

## 4. Accessibility rules — WCAG 2.1 AA (enforceable)

These are testable against an axe/a11y pass on the served pages, and precise enough that a
deliberately low-contrast token would violate a stated rule. The enforced merge gate (`npm run a11y`)
is **zero axe serious/critical violations** across the served routes in both themes — a serious or
critical contrast/keyboard/ARIA violation is **blocking** and cannot be waived. Known **moderate**
residue is tracked as debt in §5, not silently ignored: the app shell currently trips
`landmark-no-duplicate-main` / `region` / `heading-order` on several views (a pre-existing structural
markup issue — nested/duplicate `<main>`, content outside landmarks, non-monotonic headings). These
are real WCAG 1.3.1 (A) / 2.4.6 concerns and warrant a dedicated semantic-landmark pass; they are
below the serious/critical bar the gate enforces, so they don't block a merge, but they are debt, not
"done".

### 4.1 Contrast — the structural accent-text rule

**Rule (accent-as-text):** the _only_ token permitted as an accent-colored text foreground is
`--accent-text`. Its value **must** meet WCAG AA for normal text — **≥4.5:1 against `--surface`,
`--surface-2`, AND `--band`** — in **both** themes. No other orange token
(`--accent`, `--orange-*`, `--accent-bright`) may be used as a text color on those surfaces;
those are _fill_ colors, paired with `--on-accent`/`--on-accent-bright` for the text that sits
on them.

Current values pass: light `--accent-text: #b33a05` ≈ 5.96:1 on `--surface`, ≈ 5.4:1 on
`--surface-2`, ≈ 4.9:1 on `--band`; dark `--accent-text: #ffa05c` clears ≥7:1 on all three.
**A deliberately low-contrast edit** — e.g. setting `--accent-text` to a light orange like
`#ff8a3d` in light mode, or using `--accent`/`--orange-bright` directly as link text — drops
below 4.5:1 on `--surface` and **fails this rule.** That is the exact case the K1 handoff's
contrast check is built to catch.

**General text contrast:** all body/label text meets AA against its background — normal text
≥4.5:1, large text (≥24px, or ≥18.66px bold) ≥3:1. `--text` and `--text-muted` clear AA on
`--surface`/`--surface-2`; `--text-subtle` is for tertiary/label/placeholder text and must not
be the sole carrier of essential normal-size copy where it would fall below 4.5:1. Status text
uses the paired `--*-fg` on `--*-bg` (e.g. `--danger-fg` on `--danger-bg`), never the base
`--*` on an arbitrary surface.

**Non-text / graphic exemptions:** `--star`, `--orange-bright` badges, stock-bar fills, and
chart colors are graphic elements — they are not held to 4.5:1, but UI-component and state
boundaries should meet the 3:1 non-text contrast minimum.

### 4.2 Focus visibility

Every interactive element exposes a visible focus indicator. `base.css` gives
`:where(a, button, input, select, textarea, [tabindex]):focus-visible` a `2px solid var(--focus)`
outline at `2px` offset. **Rule:** components must not remove this (no `outline: none` without a
replacement of equal-or-greater visibility), keyboard focus order must follow reading order, and
custom controls (view toggles, locale tabs, drawer triggers, the card heart) must be reachable
and operable by keyboard. `--focus` must maintain ≥3:1 against adjacent colors in both themes.

### 4.3 Reduced motion

All animation/transition is gated. `base.css` under `prefers-reduced-motion: reduce` collapses
every animation/transition to `0.01ms` and disables View-Transition group animations; route
morphs only run under `prefers-reduced-motion: no-preference`. **Rule:** any new motion
(countdown pulse, hover scale, view transition) must respect `prefers-reduced-motion` — no
component may introduce essential motion that ignores the query.

### 4.4 Target size

Primary touch targets are ≥44×44px (the `ProductCard` heart is exactly 44px and comments cite
this doc). **Rule:** interactive controls on touch surfaces target ≥44px; where a control is
visually smaller, its hit area is padded to meet it.

### 4.5 Forms, errors, and live regions

Inputs are labeled (visible `<label>`/`.fld > span`, or `aria-label`). **Rule:** a form
validation error must be programmatically associated with its field and announced — an error
summary or inline message carries `role="alert"` (or lives in an `aria-live="polite"` region for
async/status updates), so screen-reader users get the error without a visual scan. Error styling
uses `--danger-bg`/`--danger-fg` (the `.notice` pattern), never color alone — an icon or text
label accompanies it. Disabled controls set `disabled` (not just opacity).

### 4.6 Theme & register contract

The four combinations — {light, dark} × {`.shop`, `.console`} — are all first-class and must
each pass the contrast rules above. Dark is not an afterthought: it re-declares surfaces, text,
borders, status backgrounds, and the accent-in-dark, and the a11y baseline is asserted in dark as
well as light. The `--photo-well` fixed-light-tile is the one deliberate cross-theme constant and
is expected; it is a framed image tile, not a text surface, so it is not held to text contrast.

---

## 5. Findings (token-discipline defects — for the dev/QA stage, not fixed here)

Design does not modify token values or component code. These are flagged for the dev stage. None
is an AA _token_ failure — the palette itself passes AA; these are hardcoded-value escapes from
the token system and one orphan reference.

1. **RESOLVED (K1 dev stage).** `list.css` stock bars hardcoded `#22c55e / #f59e0b / #ef4444`
   (`.s-green/.s-amber/.s-red`). Mapped to new `--stock-good/--stock-low/--stock-out` tokens
   (§2.4) — same rendered values, no dark-theme entry (graphic fills stay AA-exempt).
2. **RESOLVED (K1 dev stage).** `DashboardView.vue`'s chart palette (`--g-*`, `--c-*`, `#7b5cff`,
   `#fff`) is now backed by the `--chart-*` tokens (§2.14) and `--white`; the view's local
   `--g-*`/`--c-*` names alias the new tokens one-for-one so no rendered value changed.
3. **RESOLVED (K1 dev stage).** The orphan `var(--color-warning, #b45309)` reference in
   `ProductDetailView.vue` (review-star rating color) was migrated to `--star` — the token that
   already exists for exactly this purpose — removing the only call site, so no shim entry was
   needed. The `var(--color-success, #2e7d32)` dead-fallback reads in `ProductDetailView.vue` and
   `CartView.vue` were cleaned up to `var(--color-success)` (the shim already resolves it; the
   literal hex fallback was unreachable).
4. **Tracked as debt, not fixed in K1.** `list.css` uses `@media (max-width: 720px)` — a third
   breakpoint and a `max-width` query, both against the documented two-tier `min-width` scale
   (640/1024). Admin-only; fixing it would change rendered layout behavior outside K1's scope, so
   it is marked `design-exception` in `list.css` and carried in the hardcoded-color/breakpoint
   check baseline instead.
5. **RESOLVED (K1 dev stage).** `tokens.css`'s header comment said it "mirrors
   `projects/arvel-ecommerce-kit/design/DESIGN.md`", a file that doesn't exist. Updated the header
   to point at `frontend/DESIGN.md` — one canonical home, next to the code that reads the tokens.
