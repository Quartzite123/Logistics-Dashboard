# Handoff: Kiirus Xpress Dashboard — Visual Redesign

> **Stack note.** This project runs under **stlite** (Streamlit-on-WebAssembly, see PROJECT_CONTEXT.md §3.1). stlite = Streamlit, so all Streamlit APIs work normally — including `streamlit.components.v1.declare_component`, which is the key tool for this redesign. **Custom HTML/JS components run inside stlite exactly the same as in normal Streamlit** (they're sandboxed iframes — stlite's WASM boundary doesn't see them, they just load over the static bundle).

## Strategy: hybrid Streamlit + Custom Components

The current UI breaks because raw CSS injection on Streamlit's DOM is brittle — Streamlit re-wraps elements and changes class names between versions. **Custom Components solve this for the two pieces that break** (sidebar, KPI grid) by giving us an iframe we fully own. Everything else stays native Streamlit.

| Piece | Approach | Why |
|---|---|---|
| **Sidebar** | Custom Component (HTML/JS) | Eliminates the active-row height jump permanently — we own every pixel of DOM inside the iframe. |
| **KPI grid (12 cards)** | Custom Component (HTML/JS) | Same reason. Inline styles in `kpi_cards.py` are fragile; an iframe component is bulletproof. |
| **Tables (TAT, Transit, Customize)** | Native `st.dataframe` + the pill-styler pattern | `st.dataframe` is already good. Just style the status cells via pandas Styler with the pill colors from this spec. |
| **Charts** | Native Plotly via `st.plotly_chart` | Already in use. Update the Plotly layout defaults to match the design tokens. |
| **Filters, file picker, modals, forms** | Native Streamlit | These were never the problem. |
| **Edit section (matrix + pincode editor)** | Native Streamlit | `st.data_editor` is the right tool. Just inherit the global CSS for typography + tokens. |

This keeps stlite's distribution story 100% intact: still a single static bundle, still installable as a PWA, still offline.

## Overview

This handoff redesigns the visual layer of the Kiirus Xpress logistics dashboard. The Python pipeline, SQLite store, dedup engine, SLA logic, and section logic in `app/` are **already working** and must not be changed. What you are changing is **how the app looks**: the global CSS, the sidebar markup, the KPI card markup, and any inline color/typography decisions in `app/components/`.

The current UI is "too simple and breaks from time to time" — specifically the **sidebar nav row heights jump** when the active item changes (see PROJECT_CONTEXT.md §14.2, known issue), and the **KPI cards** are visually weak. This redesign solves both, and also adds a polished light mode, density modes, and a collapsible sidebar.

## About the Design Files

The files in `reference/` are an **HTML/React prototype** built as the design source of truth — they are not production code to drop in verbatim. The Kiirus app is a Streamlit application; your task is to **recreate the visual system shown in the prototype inside the Streamlit codebase** by:

1. Lifting `reference/styles.css` into `app/components/theme.py`'s `inject_global_css()` function (replacing whatever CSS is there now).
2. Restructuring the **sidebar markup** in `app/main.py` so every nav row uses the same DOM template (`<button class="nav-row">` with grid icon + text + badge), eliminating the active-vs-inactive height mismatch.
3. Restructuring the **KPI card markup** in `app/components/kpi_cards.py` so cards use the `.kpi`, `.kpi-label`, `.kpi-value`, `.kpi-meta` class system from the CSS file instead of inline style strings.
4. Replacing the existing theme tokens in `theme.py` with the CSS-custom-property tokens from `reference/styles.css`.

If a pattern in the HTML prototype cannot be matched in Streamlit (e.g. a circular floating button overlapping a panel edge), prefer the **closest Streamlit-native equivalent** — a `st.button` with the same classes — over hacking around Streamlit's DOM with hacky workarounds.

## Fidelity

**High-fidelity.** Final colors, typography, spacing and interactions. Match pixel-for-pixel where Streamlit allows. The exact tokens are in `reference/styles.css`.

## Source files in this bundle

| File | Role |
|---|---|
| `reference/index.html` | Entry point — sets `<html data-theme data-density data-sidebar>` and loads CSS/JSX. **The `data-*` attrs on `<html>` are the theming hooks.** |
| `reference/styles.css` | **THE design system.** Tokens, sidebar, KPI cards, charts, pills, buttons. Copy this into `theme.py`. |
| `reference/sidebar.jsx` | Sidebar markup reference: brand block, nav rows, theme toggle, status footer, collapse button. |
| `reference/landing.jsx` | KPI card markup reference + chart markup (donut + stacked bar). |
| `reference/stubs.jsx` | Empty-state markup for sections you haven't redesigned yet. |
| `reference/app.jsx` | Shows how the `data-theme` / `data-density` / `data-sidebar` attrs are toggled at runtime. |
| `reference/assets/logo.png` | The Kiirus wordmark (drop into `app/assets/logo.png` if not already there). |
| `screenshots/01-landing-dark.png` | Final dark-mode landing view. |
| `screenshots/02-landing-light.png` | Final light-mode landing view. |
| `screenshots/03-sidebar-collapsed-dark.png` | Sidebar collapsed (icons-only). |

---

## Design Tokens

All tokens live as CSS custom properties on `:root` / `[data-theme="dark"]` / `[data-theme="light"]`. **Do not hardcode hex values anywhere in the app** — read them via `var(--…)` so theme switches work.

### Surfaces (dark)
```
--bg:            #0b0c0d   /* page background */
--bg-elev-1:     #131417   /* card background */
--bg-elev-2:     #1a1c20   /* hover / track */
--bg-elev-3:     #22252a   /* active fill */
--sidebar-bg:    #0e0f11
```

### Surfaces (light)
```
--bg:            #fafaf6
--bg-elev-1:     #ffffff
--bg-elev-2:     #f4f4ee
--bg-elev-3:     #ebebe4
--sidebar-bg:    #f4f4ee
```

### Borders
```
dark  → --border #25272c · --border-strong #34373d · --border-hover #4a4e56
light → --border #e4e4dc · --border-strong #d0d0c6 · --border-hover #a8a89e
```

### Text
```
dark  → --text #f1f1f3 · --text-muted #a3a5ab · --text-dim #6b6e75 · --text-faint #4a4d54
light → --text #19191c · --text-muted #54545a · --text-dim #84848c · --text-faint #b0b0b6
```

### Accent (Kiirus yellow)
```
dark  → --accent #f5c518 · hover #ffd633 · soft rgba(245,197,24,0.14) · ink #0b0c0d
light → --accent #c89b00 · hover #a87f00 · soft rgba(200,155,0,0.12) · ink #ffffff
```

### Status colors
```
ok      green  dark #4ade80   light #16a34a
warn    amber  dark #fbbf24   light #d97706
bad     red    dark #f87171   light #dc2626
info    blue   dark #60a5fa   light #2563eb
neutral grey   dark #a3a5ab   light #54545a
```
All five also have `*-soft` variants (the same color at 14% alpha dark / 10% alpha light) used as pill backgrounds.

### Density (data attribute on `<html>`)
- `data-density="compact"` → 30px row height, 26px KPI value, 14px card padding
- `data-density="balanced"` (default) → 36px row, 32px KPI, 18px card padding
- `data-density="spacious"` → 42px row, 38px KPI, 24px card padding

### Sidebar width (data attribute on `<html>`)
- `data-sidebar="collapsed"` → 64px (icons only)
- `data-sidebar="narrow"` → 220px
- `data-sidebar="standard"` (default) → 264px
- `data-sidebar="wide"` → 304px

### Typography
- UI: **Inter** 400 / 500 / 600 / 700 (load from Google Fonts in Streamlit's `<head>` via `st.markdown(..., unsafe_allow_html=True)`)
- Numerics: **JetBrains Mono** 400 / 500 / 600 — applied with class `.mono` or to any element via `font-family: var(--font-mono)`
- KPI value sizes follow `--kpi-value-size` token

### Radii & shadows
```
--card-radius: 12px (balanced) / 10px (compact) / 14px (spacious)
--shadow-sm: minimal (1px subtle)
--shadow-md: card hover lift
--shadow-lg: dropdowns / modals
```

---

## Screens

### 1. Sidebar

**Purpose**: Navigation between the 5 sections, brand identity, theme toggle, install status.

**Layout** (264px wide standard):
```
┌───────────────────────────────┐  ◀──┐ (chevron button, half-overlapping
│  [logo] Kiirus Xpress         │     │  the right edge, 22px circular)
│         LOGISTICS · INTELL.   │     │
├───────────────────────────────┤     │
│  WORKSPACE                    │     │
│                               │     │
│  [▣] Landing       959        │ ◀── active row: yellow tint bg,
│      Overview                 │      yellow 3px bar at left,
│  [◷] TAT Analysis  856        │      yellow icon
│      Delivered SLA            │
│  [⛟] Transit       103        │ ◀── inactive: transparent bg,
│      In-flight                │      muted text, hover → elev-1
│  [≡] Customize                │
│      Ad-hoc query             │
│  [✎] Edit                     │
│      Reference data           │
│                               │
│  ────────── flex spacer ──────│
│                               │
│  [Dark] [Light]               │ ◀── theme toggle (segmented)
│  ● Local · Offline-ready      │
│  ● kiirus.db · 12.4 MB        │
│  v 1.3.0      BUILT FOR KIIRUS│
└───────────────────────────────┘
```

**Components & exact specs**:

- **Nav row** (THE FIX FOR THE HEIGHT JUMP): every row is a `<button class="nav-row">` with `min-height: var(--nav-row-h)` and a fixed grid `28px 1fr auto`. The active state changes **only** colors + a `::before` left-bar — NEVER the DOM structure. This guarantees identical box dimensions for all rows.
  - Inactive: `color: var(--text-muted)`, transparent bg, hover → `var(--bg-elev-1)` bg + `var(--text)` color
  - Active: `aria-current="true"`, `color: var(--text)`, `background: var(--accent-soft)`, `::before` is a 3px yellow bar at `left: -10px`
  - Icon color: muted by default, `var(--accent)` when active
  - Sublabel: 11px, `var(--text-dim)`
  - Badge: optional, mono font, `var(--bg-elev-2)` bg
- **Brand block**: 36×36 logo box + 14px name + 10px uppercase tag, divided by 1px border below
- **Section label** ("WORKSPACE"): 10px uppercase, 0.16em letter-spacing, `var(--text-dim)`
- **Theme toggle**: segmented `[Dark][Light]`, `aria-pressed` switches the active state
- **Status rows**: 6px dot (`var(--ok)` for "Local · Offline-ready"), 11px text
- **Collapse chevron**: 22px circle, absolute-positioned half-overlapping the right border at `top: 28px; right: -11px`. On hover, fills with yellow.

**Streamlit implementation notes**:
- Render the **entire sidebar** as one big `st.markdown(..., unsafe_allow_html=True)` block — do NOT mix `st.sidebar.button` with HTML divs (that's what causes the height mismatch today). Inside that HTML block, every nav row is a `<a href="?section=landing">` styled as a `.nav-row`. Use Streamlit's query-param routing to read `section` and update `st.session_state["current_section"]`.
- Suppress Streamlit's default sidebar via `section[data-testid="stSidebar"] > div:first-child { padding: 0 !important; background: var(--sidebar-bg); }`
- The collapse button toggles a class on `<body>` (`data-sidebar="collapsed"`) by setting `st.session_state["sidebar_width"]` and re-rendering.

### 2. Landing — Page header

```
Section 01 · Landing                              [Export] [↑ Upload new file]
Operations Snapshot                               (yellow-filled primary)
959 shipments across 21 companies · synced 4 minutes ago
─────────────────────────────────────────────────────────────────────────
```

- Eyebrow: 11px uppercase 0.16em letter-spacing `var(--text-dim)`
- Title: 26px weight 600 `-0.01em` letter-spacing
- Subtitle: 13px `var(--text-muted)`
- Buttons (right-aligned): `.btn` (ghost) + `.btn.btn-primary` (yellow fill)
- 1px bottom border, 20px padding below

### 3. Landing — KPI grid

Four rows in this exact pattern:

| Row | Layout | Cards |
|---|---|---|
| 1 | 3 columns | Total Orders · Delivered · In Transit |
| 2 | 3 columns | Pending · RTO · Date Range |
| 3 | 4 columns | Early · On Time · SLA · Late |
| 4 | 2 columns | ODA · Non-ODA |

**KPI card spec** (per `.kpi`):
```html
<div class="kpi kpi-accent">
  <div class="kpi-label">
    TOTAL ORDERS
    <span class="kpi-label-ic">…icon…</span>
  </div>
  <svg class="kpi-spark">…sparkline…</svg>     <!-- optional, top-right -->
  <div class="kpi-value text-primary">959</div>  <!-- or text-ok / text-warn / text-bad / text-info -->
  <div class="kpi-progress">                     <!-- optional -->
    <div class="kpi-progress-fill ok" style="width: 89.3%"></div>
  </div>
  <div class="kpi-meta">
    <span class="kpi-delta up">+12.4%</span>
    <span>All shipments in pipeline</span>
  </div>
</div>
```

- Card: `var(--bg-elev-1)` bg, 1px `var(--border)`, 12px radius, 18px padding
- Label: 11px uppercase 0.14em letter-spacing `var(--text-dim)`
- Value: **JetBrains Mono**, 32px, weight 500, `letter-spacing: -0.02em`, `font-feature-settings: 'tnum', 'zero'`
  - Color: `var(--accent)` (yellow) for compliance metrics, `var(--ok)` (green) for Delivered/Early, `var(--info)` (blue) for In Transit/On Time, `var(--warn)` (amber) for Pending/ODA, `var(--bad)` (red) for RTO/Late, `var(--text)` (white/black) for Total Orders / Date Range
- Progress bar: 4px high, `var(--bg-elev-2)` track, fill in the matching status color
- Delta pill: mono 11px, 4px radius, `ok-soft` / `bad-soft` / `neutral-soft` bg
- Sparkline: 56×22px, absolute-positioned top-right, 0.7 opacity
- **Hover**: `translateY(-2px)` + `var(--border-hover)` border + `var(--shadow-md)`. With `.kpi-accent`, the hover border is `var(--accent)` and shadow is `var(--accent-glow)`.

**Date Range card** is special: `.kpi-daterange .kpi-value` is 15px text instead of 32px mono, with a `→` arrow in `var(--accent)` between two dates.

**Streamlit implementation notes**:
- The current `kpi_cards.py` uses inline styles via `t()`. **Replace** that with class-based markup. Each `KpiCard()` Python function should emit one `<div class="kpi">…</div>` via `st.markdown(..., unsafe_allow_html=True)`.
- Use `st.columns([1,1,1])` for the 3-card rows, `st.columns(4)` for the 4-card row, `st.columns(2)` for the 2-card row. Put **one** `st.markdown` per column with the kpi HTML.
- The `[data-testid="metric-container"]` Streamlit metric is NOT used — these are custom HTML cards.

### 4. Landing — Charts row

Two-column grid below the KPIs, gap = `var(--card-gap)`.

**Left chart card** — Overall Delivery Performance:
- Donut chart, 128×128, with the SLA % in the center (large yellow mono numeric + "SLA" eyebrow)
- Ring segments: Early (green) · On Time (blue) · Late (red) · Not Yet Delivered (`var(--text-dim)`)
- Legend on the right: swatch + label + mono count + mono percentage, hover row gets `var(--bg-elev-2)` bg
- Title: 13px weight 600. Sub: 11px `var(--text-dim)`. "Live" pill (accent) in the top-right.

**Right chart card** — Per-company breakdown:
- Horizontal stacked bars, 8 companies, 16px tall each
- Each bar splits Early/On Time/Late proportionally, total count at right (mono 11px)
- Two segmented controls in the header: chart type (Bar/Line/Pie) + dimension (Company/Region/Month/Status)
- Bottom legend strip: three color dots + labels

**Streamlit implementation notes**:
- Replace the Plotly chart background defaults to match: `paper_bgcolor: 'rgba(0,0,0,0)'`, `plot_bgcolor: 'rgba(0,0,0,0)'`, `font_color: var(--text-muted)`, `colorway: ['#4ade80', '#60a5fa', '#f87171', '#a3a5ab']` (dark) or `['#16a34a', '#2563eb', '#dc2626', '#54545a']` (light).
- The segmented control buttons aren't Streamlit's `st.radio`; render them as styled `<button class="seg">` elements that post back via query params or session state.

### 5. Pills (used in tables: SLA Status, Stuck, ODA, Current Status)

```html
<span class="pill pill-ok"><span class="dot"></span>Early</span>
<span class="pill pill-info">On Time</span>
<span class="pill pill-bad">Late</span>
<span class="pill pill-warn">Pending</span>
<span class="pill pill-neutral">RTO</span>
<span class="pill pill-accent">YES</span>
```

- 11px weight 600, 3/8px padding, 4px radius
- `*-soft` bg + matching solid text color
- Use these to replace the current pandas Styler approach in `data_table.py` for status columns

---

## Interactions & Behavior

### Theme toggle
- Clicking Dark/Light in the sidebar sets `st.session_state["theme_mode"]` and calls `st.rerun()`.
- The CSS injection in `theme.py` should output the current theme as `<html data-theme="...">` (use `st.markdown` to inject `<script>document.documentElement.dataset.theme = '…';</script>` or render the body container with the attribute).
- All token changes are CSS-only — no recompute, no inline-style flicker.

### Sidebar collapse
- Click the floating chevron → `st.session_state["sidebar_width"]` toggles between the user's last-chosen width and `"collapsed"`.
- Set `data-sidebar="collapsed"` on `<html>`. The CSS handles everything else (hides labels via `.sidebar-brand-text` / `.nav-text` not being rendered, sub-50% width).

### KPI card hover
- `transform: translateY(-2px)` + border color change + shadow. 150ms ease.
- The `.kpi-accent` variant goes yellow on hover (used for cards that drive primary KPIs).

### Nav row active state
- `aria-current="true"` swaps the background to `var(--accent-soft)`, icon to yellow, and shows the 3px left bar. **Box dimensions do not change** — that's the contract.

### Tweaks panel (optional)
- The reference prototype exposes a floating Tweaks panel with Theme / Density / Sidebar width.
- In the Streamlit app these can live in the sidebar footer (Theme is already there) — add a small "Settings" expander with the density and sidebar-width radios.

---

## State Management

These three values drive the entire visual system. Add them to `st.session_state` if not present:

| Key | Values | Default |
|---|---|---|
| `theme_mode` | `'dark'` / `'light'` | `'dark'` |
| `density` | `'compact'` / `'balanced'` / `'spacious'` | `'balanced'` |
| `sidebar_width` | `'collapsed'` / `'narrow'` / `'standard'` / `'wide'` | `'standard'` |

After any change, write the three values into `<html data-theme="…" data-density="…" data-sidebar="…">` via a small `<script>` block emitted by `theme.py`. This is the **only** way the CSS knows which token set to use.

---

## Files to change in the Kiirus codebase

### New files to create

| File | Role |
|---|---|
| `app/components/_html/sidebar/index.html` | Self-contained sidebar HTML — copy the markup from `reference/sidebar.jsx` (rendered to plain HTML). Inlines `styles.css`. |
| `app/components/_html/sidebar/sidebar.js` | Listens for `Streamlit.setComponentReady()`, receives the `active` and `theme` props from Python, posts back `{type: "navigate", section: "..."}` and `{type: "collapse"}` events via `Streamlit.setComponentValue()`. |
| `app/components/_html/kpi_grid/index.html` | Self-contained 12-card grid HTML. Inlines `styles.css`. |
| `app/components/_html/kpi_grid/kpi_grid.js` | Receives `{kpis: [...]}` from Python and renders the cards. |
| `app/components/sidebar_component.py` | Python wrapper using `components.v1.declare_component("kiirus_sidebar", path="_html/sidebar")`. Exposes `render_sidebar(active, theme) -> nav_event` returning the section the user clicked. |
| `app/components/kpi_grid_component.py` | Python wrapper using `components.v1.declare_component("kiirus_kpi", path="_html/kpi_grid")`. Exposes `render_kpi_grid(kpis: dict)`. |
| `app/components/global_styles.py` | A small module that does **only** `<link rel="stylesheet">` injection for Inter + JetBrains Mono fonts and the `<html data-theme data-density data-sidebar>` attribute setter. The bulk of the CSS lives **inside the iframes**, not in the main Streamlit doc. |

### Files to modify

| File | Change |
|---|---|
| `app/components/theme.py` | **TRIM**. Keep only: (a) the three session_state defaults (`theme_mode`, `density`, `sidebar_width`), (b) Plotly default updates, (c) `format_int_for_display`. **REMOVE** all the page-level CSS injection — it now lives inside the components, not in the main doc. |
| `app/main.py` | Replace `_render_brand_block`, `_render_sidebar_nav`, `_render_theme_toggle`, `_render_footer` calls with a single `sidebar_component.render_sidebar(...)` call inside `with st.sidebar:`. Read the returned event and route accordingly. |
| `app/components/kpi_cards.py` | Replace the entire file body with a thin wrapper that builds the `kpis` dict (label + value + color + meta + delta + progress) and hands it to `kpi_grid_component.render_kpi_grid(kpis)`. |
| `app/components/chart_pair.py` | Update Plotly layout defaults to match tokens (transparent bg, font color from token, colorway). Wrap output in `<div class="chart-card">` via `st.markdown`. |
| `app/components/data_table.py` | Replace status-column pandas Styler with pill HTML rendering (use `pd.Series.map` to wrap cell values in `<span class="pill pill-*">`). Inject the pill-only CSS as a small `st.markdown('<style>…</style>', unsafe_allow_html=True)` once per page. |
| `app/sections/landing.py` | Wire up new `render_kpi_grid()` call with the value-color mapping in this README. |
| `app/assets/logo.png` | Confirm present; copy from `reference/assets/logo.png` if missing. |

### Files that must NOT change

- `app/pipeline/*` — pipeline logic is final.
- `app/store/*` — schema is final.
- `app/sections/edit.py`, `app/sections/tat.py`, `app/sections/transit.py`, `app/sections/customize.py` — section *logic* is final; only the *components they use* (data_table, chart_pair) get markup updates.
- `tests/` — keep all tests passing.
- `streamlit_app.py`, `manifest.json`, `requirements.txt` — stlite distribution is unchanged.

### Custom Component implementation pattern (the key bit)

A Streamlit custom component is just a folder with `index.html` that gets served as an iframe. Inside the iframe, you have full DOM control — Streamlit's selectors can't reach you. Communication is via `postMessage`.

```python
# app/components/sidebar_component.py
import os
import streamlit.components.v1 as components

_HERE = os.path.dirname(os.path.abspath(__file__))
_sidebar = components.declare_component(
    "kiirus_sidebar",
    path=os.path.join(_HERE, "_html", "sidebar"),
)

def render_sidebar(active: str, theme: str, density: str, sidebar_width: str):
    """
    Returns the nav event the user clicked, or None.
    Event shape: {"type": "navigate", "section": "..."} | {"type": "toggle_theme"} | {"type": "toggle_collapse"}
    """
    return _sidebar(
        active=active,
        theme=theme,
        density=density,
        sidebar_width=sidebar_width,
        key="kiirus_sidebar",
        default=None,
    )
```

```html
<!-- app/components/_html/sidebar/index.html -->
<!doctype html>
<html data-theme="dark" data-density="balanced" data-sidebar="standard">
<head>
  <meta charset="utf-8"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
  <style>
    /* PASTE THE ENTIRE CONTENTS OF reference/styles.css HERE */
  </style>
</head>
<body>
  <aside class="sidebar"><!-- markup from reference/sidebar.jsx, plain HTML --></aside>
  <script>
    // Streamlit component handshake
    function onMsg(e) {
      if (e.data.type === "streamlit:render") {
        const { active, theme, density, sidebar_width } = e.data.args;
        document.documentElement.dataset.theme = theme;
        document.documentElement.dataset.density = density;
        document.documentElement.dataset.sidebar = sidebar_width;
        document.querySelectorAll(".nav-row").forEach(row => {
          row.setAttribute("aria-current", row.dataset.section === active ? "true" : "false");
        });
      }
    }
    window.addEventListener("message", onMsg);
    parent.postMessage({type: "streamlit:componentReady", apiVersion: 1}, "*");
    parent.postMessage({type: "streamlit:setFrameHeight", height: document.body.scrollHeight}, "*");

    // Wire nav clicks
    document.querySelectorAll(".nav-row").forEach(row => {
      row.addEventListener("click", () => {
        parent.postMessage({
          type: "streamlit:setComponentValue",
          value: {type: "navigate", section: row.dataset.section},
        }, "*");
      });
    });
    // Wire theme toggle + collapse button similarly
  </script>
</body>
</html>
```

```python
# app/main.py — usage
from app.components import sidebar_component

with st.sidebar:
    event = sidebar_component.render_sidebar(
        active=st.session_state["current_section"],
        theme=st.session_state["theme_mode"],
        density=st.session_state["density"],
        sidebar_width=st.session_state["sidebar_width"],
    )

if event:
    if event["type"] == "navigate":
        st.session_state["current_section"] = event["section"]
        st.rerun()
    elif event["type"] == "toggle_theme":
        st.session_state["theme_mode"] = "light" if st.session_state["theme_mode"] == "dark" else "dark"
        st.rerun()
    elif event["type"] == "toggle_collapse":
        st.session_state["sidebar_width"] = "collapsed" if st.session_state["sidebar_width"] != "collapsed" else "standard"
        st.rerun()
```

Same pattern for `kpi_grid_component` — but it's simpler (no events back, just a data input).

### stlite-specific notes

- `components.v1.declare_component(path=...)` works under stlite. The folder is served as part of the static bundle. No special build step.
- Google Fonts loads inside the iframe on first run, then the PWA service worker caches them. Subsequent loads are offline.
- iframe height: post `{type: "streamlit:setFrameHeight", height}` on initial render and on every resize, or stlite gives you a default ~150px iframe.
- Component values round-trip through Pyodide cleanly — `event["type"]` etc. are normal Python dicts in your handler.

---

## Acceptance criteria

1. **Sidebar height jump is gone.** Click through all 5 nav items; no row visually shifts size. Verify with DevTools that every `.nav-row` has identical `getBoundingClientRect()` dimensions regardless of active state.
2. **KPI cards match the screenshots** (`screenshots/01-landing-dark.png`, `screenshots/02-landing-light.png`) pixel-for-pixel — same colors per metric, same number sizes, same hover lift.
3. **Theme toggle works without page flicker.** Dark and light both polished (compare with the two screenshots).
4. **Sidebar collapse chevron** toggles between current width and 64px collapsed state. Labels disappear, icons remain.
5. **No hardcoded hex colors** in any Python file — every color reference goes through a `var(--token)` in CSS or a CSS class.
6. **No regressions**: `pytest` passes; all existing dashboard features (upload, dedup, SLA compute, Edit Save→Apply) work as before.

---

## Asset notes

- The logo is on a black background (PNG, fully opaque, no transparency). In light mode it still works because it sits inside a `var(--bg)` rounded box on light-cream that maintains contrast. If you want a transparent version for light mode, that's a future task — for now the black PNG is fine in both themes.
- Inter and JetBrains Mono are loaded from Google Fonts in `reference/index.html`. Mirror this in Streamlit by injecting a `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap">` via `st.markdown(..., unsafe_allow_html=True)` at app start. (Note: this is one of the few internet-dependent fetches; cache them via the PWA service worker in production per the stlite distribution plan.)

---

## How to verify your implementation

1. Run `streamlit run streamlit_app.py`.
2. Open the Landing page. Compare side-by-side with `screenshots/01-landing-dark.png`.
3. Toggle to light mode in the sidebar. Compare with `screenshots/02-landing-light.png`.
4. Click each nav item — confirm no row-height jump.
5. Click the chevron — sidebar collapses to icons. Compare with `screenshots/03-sidebar-collapsed-dark.png`.
6. Run `pytest` — all tests pass.

If any visual difference from the screenshots, the **screenshots are the source of truth**, not your interpretation of the CSS. Re-check tokens.
