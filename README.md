# Kiirus Xpress — Logistics Intelligence Dashboard

> **Spec hand-off document.** This file captures every design decision, constraint, data shape, business rule, UI behaviour and architectural choice agreed during the design conversation. It is written to be self-sufficient: an implementing engineer (human or LLM) should be able to build the project end-to-end from this file alone, without needing to reconstruct prior conversations.

---

## Table of contents

1. [Project overview](#1-project-overview)
2. [Hard constraints](#2-hard-constraints)
3. [Recommended tech stack](#3-recommended-tech-stack)
4. [Distribution / deployment model](#4-distribution--deployment-model)
5. [Source data files](#5-source-data-files)
6. [The raw 41-column Delhivery schema](#6-the-raw-41-column-delhivery-schema)
7. [Data pipeline overview](#7-data-pipeline-overview)
8. [Deduplication engine](#8-deduplication-engine)
9. [Two-table architecture](#9-two-table-architecture)
10. [SLA / TAT / ODA domain logic](#10-sla--tat--oda-domain-logic)
11. [UI navigation — five sections](#11-ui-navigation--five-sections)
12. [Section 1 — Landing page](#12-section-1--landing-page)
13. [Section 2 — TAT Analysis](#13-section-2--tat-analysis)
14. [Section 3 — Transit](#14-section-3--transit)
15. [Section 4 — Customize](#15-section-4--customize)
16. [Section 5 — Edit](#16-section-5--edit)
17. [Cross-cutting feature — Visualizations](#17-cross-cutting-feature--visualizations)
18. [Cross-cutting feature — Resizable layout & fullscreen](#18-cross-cutting-feature--resizable-layout--fullscreen)
19. [Architectural implication — derived SLA columns are stored](#19-architectural-implication--derived-sla-columns-are-stored)
20. [On hold (blocked on data delivery)](#20-on-hold-blocked-on-data-delivery)
21. [Data discrepancies and the decisions made](#21-data-discrepancies-and-the-decisions-made)
22. [Suggested project file layout](#22-suggested-project-file-layout)
23. [Verification / acceptance tests](#23-verification--acceptance-tests)
24. [Glossary](#24-glossary)

---

## 1. Project overview

A fully local, offline-capable logistics analytics dashboard for **Kiirus Xpress** (logistics startup, founders are non-technical). The dashboard ingests raw shipment Excel files exported from Delhivery (the courier partner), deduplicates them, computes SLA/TAT performance, and presents an executive overview plus operational drilldowns.

**Primary user**: a single founder per laptop. Used by 1–2 people total at the company.

**Primary use cases**:
- Upload the latest Delhivery export → see updated dashboard.
- Check today's KPIs (Total Orders, Delivered, In Transit, SLA %, etc.).
- Inspect SLA performance per shipment (TAT Analysis).
- Triage shipments stuck in transit (Transit).
- Build ad-hoc filtered queries (Customize).
- Maintain the SLA reference data — the 5×5 region matrix and the 22 K-row pincode master (Edit).
- View progress from a phone on weekends, when the laptop is at the office. (Mobile + truly offline.)

---

## 2. Hard constraints

| # | Constraint | Reason |
|---|---|---|
| 1 | **No cloud dependency.** Nothing on AWS / GCP / Azure / Render / etc. | Founder preference; data is operational + commercially sensitive. |
| 2 | **No internet dependency during operation.** | Must work in airport lounges, weekend home Wi-Fi, etc. |
| 3 | **No Gmail IMAP / no scheduled fetch.** | Earlier idea, scrapped — too brittle, too many auth touchpoints. |
| 4 | **Files are uploaded manually** through the dashboard UI. | Simpler ops, founders already export the file weekly. |
| 5 | **Minimal install friction on founder laptops.** Target: ≤ 3 install steps, ideally a single click. | Founders are non-technical. |
| 6 | **Low RAM / disk footprint, runs on older laptops.** Should not lag on 8 GB RAM Windows machines with browser open. | Founder hardware varies. |
| 7 | **Mobile access required, fully offline.** Founder leaves laptop at office, wants weekend visibility from phone. *Local Wi-Fi access from phone (laptop must be on) is **not sufficient**.* | Stated explicitly during design. |
| 8 | **Founder edits to reference data must not retroactively rewrite history.** Past shipments keep their SLA values; matrix / ODA edits affect only future uploads. | Audit trust. |

---

## 3. Recommended tech stack

The combination of constraints 1 + 2 + 7 (no cloud, no internet, truly offline mobile with no laptop dependency) narrows the realistic options drastically. The recommended path is:

### 3.1 Primary recommendation: **stlite (Streamlit-on-WebAssembly) packaged as a PWA**

| Layer | Choice | Notes |
|---|---|---|
| App framework | **stlite** (Streamlit ported to WASM via Pyodide) | Runs the entire Python app — pandas, plotly, openpyxl — inside the browser. No server. https://stlite.net |
| Language | Python 3.11+ (Pyodide-compatible build) | All business logic stays in Python. |
| Data store | **SQLite via `sql.js`** (browser-side SQLite) **or** **IndexedDB** (browser persistent storage) | Pyodide can drive both. Whichever the implementer finds cleaner; SQLite preferred for queryability. |
| Charts | **Plotly** (`plotly.express`, `plotly.graph_objects`) | Works under Pyodide. Has built-in fullscreen via modebar; we use a custom click-to-fullscreen overlay on top. |
| Excel I/O | **openpyxl** + **pandas** | Both work under Pyodide. |
| Tables | Streamlit `st.dataframe` / `st.data_editor` | For the 22 K pincode editor, paginate + search-only (do NOT render all rows). |
| Distribution | **PWA install** (mobile + desktop) **and/or stlite-desktop** (Electron wrap) | Both produce a single artifact with no Python install required. |

### 3.2 Why stlite was chosen

The unique selling point: **the entire Python pipeline runs inside the user's browser tab as WebAssembly**. After a one-time ~30–50 MB cached download, the app:

- Runs **truly offline on a phone** (a PWA installed to the home screen). The phone does not need the laptop to be on.
- Distributes as **a single static bundle** (`index.html` + assets). Hostable on a USB stick, a free GitHub Pages domain, or a small file share.
- Requires **no Python install**, **no Docker**, **no admin rights** on the founder's laptop.
- Same codebase serves desktop browser, installable PWA, and (via stlite-desktop) a Windows .exe.

### 3.3 Concessions made because of the stlite choice

To stay inside Streamlit's UI primitives, the spec walks back three "nice-to-have" UI behaviours that were earlier discussed:

| Originally specced | stlite-compatible substitute |
|---|---|
| Drag-to-resize panels (VS Code style) | **Preset ratio buttons** above the layout: `60/40 · 50/50 · 70/30 · Table only · Charts only`. Functionally equivalent, less elegant. |
| Click-anywhere-on-chart → custom fullscreen modal | Use **Plotly's built-in fullscreen icon** in the chart modebar. Native, free, slightly less discoverable. |
| Inline-edit the entire 22 K-row pincode table | **Search-and-edit only** (already in spec), plus bulk re-upload for mass changes. The full table is never rendered. |

### 3.4 Alternatives considered (and why not)

| Alternative | Why rejected |
|---|---|
| Streamlit + Postgres + Docker (original idea) | Docker Desktop on Windows = WSL2 + 3–4 GB idle RAM + license check + install friction. Founders are non-technical. Postgres is overkill for 1–50 K rows. |
| Streamlit + PyInstaller bundle | PyInstaller's Streamlit support is finicky (custom hooks for `streamlit/static`, `streamlit/runtime`, vega/altair); Streamlit's own team flags it as fragile. Solves desktop but **does not solve offline mobile**. |
| Reflex (Python compiled to Next.js) | Better mobile UX, but PWA + true offline + client-side Python pipeline is not native — would require either porting the pipeline to JS or running Pyodide inside Reflex, both significant work. |
| Dash (Plotly) | Same problem as Reflex: Python backend stays server-side. Doesn't solve offline mobile. |
| FastAPI + React/Svelte PWA | Most flexible, best mobile, biggest build effort. Frontend skill set required. Pipeline still needs to be ported to JS for true offline-on-phone, OR ship with Pyodide bundled. Equivalent total effort to stlite with much more code. |
| Native mobile app (React Native / Flutter) | Out of scope; effectively a separate product. |

### 3.5 Database choice — SQLite, not Postgres

| Reason | Detail |
|---|---|
| Data scale | ~1 K shipment rows now, ~50 K projected; 22 K pincode master. SQLite handles this easily. |
| Operations | Single user, single laptop. No concurrent writes. |
| Backup | Copy one file. |
| Footprint | No separate server process; ~300 MB less RAM than Postgres. |
| Pyodide compatibility | `sql.js` runs SQLite under WebAssembly; works inside the browser tab. |

Postgres is reserved for if/when multi-user / networked operation becomes a real requirement.

### 3.6 Resource targets

| Mode | Disk | RAM peak | Older laptop OK |
|---|---|---|---|
| stlite-desktop Electron .exe | ~150 MB | 300–500 MB | 8 GB very smooth, 4 GB tight if browser open |
| Phone PWA (after first install) | ~50 MB cached | 200–400 MB | Any phone < 5 years old runs it fine |
| First-load (browser, before cache) | ~30–50 MB download | — | One-time, then instant on every subsequent open |

---

## 4. Distribution / deployment model

### 4.1 Founder onboarding flow (recommended)

1. Implementer hosts the static bundle at a stable URL (e.g. a GitHub Pages domain, a small Cloudflare Pages site, or even a self-hosted nginx behind dynamic DNS). The hosting must be HTTPS (PWA install requires it).
2. Founder receives one link.
3. On their laptop: open link in Chrome/Edge → click the "Install" icon in the address bar → app appears as a desktop icon, opens in its own window (looks native).
4. On their phone: open the same link in Chrome/Safari → tap "Add to Home Screen" → app appears as a phone icon.
5. After step 3 / 4, the app **runs fully offline forever** on that device.

### 4.2 Air-gapped fallback

If the founder cannot accept any one-time hit to a hosted URL:

- Ship the bundle on a USB stick.
- Founder copies the folder to their machine.
- Run a one-line local server to serve the folder over `http://localhost:8000`.
- Use a small wrapper exe (or `stlite-desktop`) to do this transparently — single double-click experience.
- Caveat: PWA install-to-home-screen requires HTTPS; pure local file:// loses the PWA install path but the app still works in any browser tab.

### 4.3 Updates

- New version → re-deploy bundle → the PWA's service worker detects new version on next open → prompts the founder to refresh.
- No re-installation needed.

---

## 5. Source data files

These four files live in the project folder during design. They drive both the schema and the test data.

| # | File | Shape | Role |
|---|---|---|---|
| 1 | `Kiirus Automation file UPDATED (1).xlsx` | 959 rows × 41 columns | The **raw 41-column Delhivery export**. Primary input that the dashboard ingests. Currently the only sample available. |
| 2 | `kiirus Xpress Pvt Ltd Updated_Project File (1).csv` | 6 × 6 (5×5 matrix + header row + header column) | The **5×5 region-to-region SLA matrix**. Diagonal = 4 days. Final, in active use. |
| 3 | `Green_red-yellow.xlsx` | 959 × 19 | **Visual reference only** for the TAT-tab row colour coding. Despite the filename, the file itself contains **no actual cell fill colours**. Its `Status` column wording (`"Early by N day(s)"`, `"Delivered exactly on time"`, `"Late by N day(s)"`, `"Not yet delivered"`) is illustrative — the actual schema uses the cleaner `Early / On Time / Late` triplet plus a signed `TAT Variance`. |
| 4 | `Percetaged_file.xlsx` | 22 × 8 | Reference for the per-company aggregate view (now folded into Section 4 Customize, not a standalone section). |

**Missing — to be delivered later**: a single 22 K-row Excel/CSV mapping `Pincode → City → State → Zone → ODA (YES/NO)`. Until this lands, every feature that depends on Region or ODA is **unconfigured but built**. Logic is in place; it just returns `N/A` until the master file is loaded.

### 5.1 SLA matrix (file 2) verbatim

```
            West  South  North  East  North-East
West          4     6      6     7     10
South         6     4      6     7     10
North         6     6      4     7      8
East          7     7      7     4      6
North-East   10    10      8     6      4
```

Diagonal cells = 4 days (intra-zone). Off-diagonal max = 10 days (West ↔ North-East).

### 5.2 Per-company aggregate reference (file 4) — column shape

`Company, Total Orders, Order Share (%), Delivered, In Transit, On Time (%), Early (%), Late (%)`

Our Aggregate view extends this with `Pending count, RTO count, SLA % combined, ODA %` — see Section 15.

---

## 6. The raw 41-column Delhivery schema

The Delhivery export columns, in file order, with the data type pandas infers and notes on use:

| # | Excel col | Column name | Type | Notes / use |
|---|---|---|---|---|
| 1 | A | `LRN` | int | **Primary key.** Unique shipment identifier. |
| 2 | B | `Order id` | string | **Misnamed — actually contains the COMPANY/CLIENT NAME** (e.g. `KENSTAR`, `CLAD METAL`). This is the column the Aggregate view groups by. **Do NOT rename in storage** — UI maps `Order id → Company` at render time. |
| 3 | C | `No of boxes` | int | Optional table column. |
| 4 | D | `Client` | string | **Useless for analytics** — every row is `kiirus b2bc`. Do not group on it. |
| 5 | E | `Manifest Date` | datetime | **Cell format is broken in the source** (`'mmss.0'` → Excel shows only `mm:ss.t`, hiding the date). The underlying value is correct; pandas reads it fine. **Ignored for SLA**. |
| 6 | F | `Pickup Date` | datetime | **Reliable.** Drives `Actual TAT` start date. |
| 7 | G | `Expected Date` | datetime | Delhivery's own expected date. **Deprecated** — Expected TAT comes from the 5×5 matrix instead. |
| 8 | H | `Invoice Number` | string | Prefixed with a back-tick (` ` `1125-…` ). Display-only. |
| 9 | I | `Consignee name` | string | Optional table column. |
| 10 | J | `Origin City` | string | 958/959 are `Aurangabad` (Maharashtra → West zone). Used to derive Origin Zone. |
| 11 | K | `Destination City` | string | 212 distinct values. Used informationally. |
| 12 | L | `Client Location/warehouse` | string | Mostly `kiirus b2bc`; occasional brand-specific values. Display-only. |
| 13 | M | `Pick up Address` | float (mostly null) | Ignore. |
| 14 | N | `Pin code` | int | **Drives Region + ODA lookup** via the 22 K master. |
| 15 | O | `Dispatch Count` | int | Optional. |
| 16 | P | `First dispatch date` | datetime | Optional. |
| 17 | Q | `Last dispatch date` | datetime | Optional. |
| 18 | R | `Last Scan Location` | string | Useful in Transit. |
| 19 | S | `Last Scan Date` | datetime | Useful in Transit. |
| 20 | **T** | **`Current Status`** | string | **Primary lifecycle column.** Values: `Manifested · Dispatched · In Transit · Pending · Delivered · RTO`. |
| 21 | U | `Status Type` | string | Auxiliary. **Ignored for dedup.** |
| 22 | **V** | **`Remarks`** | string | **Dedup tie-breaker.** 13 distinct values. Contains progression text like `"Delivered to Consignee"`, `"Out for Delivery"`, `"Consignment Reached at Destination"`. |
| 23 | W | `Promise Date` | datetime | Optional. |
| 24 | X | `Delivered Date` | datetime | **Reliable.** Drives `Actual TAT` end date. |
| 25 | Y | `Payment Type` | string | `Pre-paid` or `COD`. |
| 26 | Z | `Master Waybill` | int | Optional. |
| 27 | AA | `Additional Remarks` | string | POD audit notes (`"Clean POD | As per DS Model System audit"`, etc.). **NOT used for dedup.** Optional table column for display. |
| 28 | AB | `Return Promise Date` | datetime | Optional. |
| 29 | AC | `Transaction Type` | float | Mostly null. Ignore. |
| 30 | AD | `Transaction Mode` | float | Mostly null. Ignore. |
| 31 | AE | `First Pending Date` | datetime | Optional, useful in Transit for Pending rows. |
| 32 | AF | `Package Amount` | float | Optional. |
| 33 | AG | `Weight` | float | Optional. |
| 34 | AH | `First attempt date` | datetime | Optional. |
| 35 | AI | `Last Attempt date` | datetime | Optional. |
| 36 | AJ | `Attempt Count` | float | Optional, useful in Transit. |
| 37 | AK | `First Return Date` | datetime | Optional. |
| 38 | AL | `Invoice Zone` | string | **Delhivery billing zone** (B/D1/D2/E/F). **Has nothing to do with the 5×5 geographic zones.** Do NOT use for SLA matrix lookup. |
| 39 | AM | `RVP/ Forward identifier` | string | Optional. |
| 40 | AN | `PUR ID` | string | Optional. |
| 41 | AO | `State` | string | **Drives Region lookup** when no pincode hit. |

### 6.1 Distribution snapshot (from the sample file)

- `Current Status` distribution: Delivered 856 · In Transit 71 · Pending 16 · Dispatched 11 · RTO 4 · Manifested 1.
- 959 unique LRNs / 959 rows → **no duplicates yet** in the current snapshot. Dedup is forward-looking.
- 21 distinct companies in `Order id` (KENSTAR is dominant at 638 / 66.5 %).
- Origin City: 958 Aurangabad, 1 Delhi.
- Date ranges in the sample: late Nov 2025 → early Feb 2026.

---

## 7. Data pipeline overview

```
Founder selects one or more Delhivery .xlsx files in the upload panel
        │
        ▼
Files parsed (openpyxl + pandas), 41-column schema validated
        │
        ▼
Each row inserted into shipments_raw with upload metadata
        │
        ▼
Deduplication engine merges new rows with existing shipments_latest
   (lifecycle rank → remarks rank → timestamp → upload batch)
        │
        ▼
Derived SLA columns computed and STORED on each row in shipments_latest:
   Origin Zone, Destination Zone, ODA flag, Expected TAT, Actual TAT,
   TAT Variance, SLA Status
        │
        ▼
Dashboard re-renders from shipments_latest
```

Key rules:
- **Dedup is lifecycle-based, not upload-order-based.** Uploading an older file after a newer one cannot regress a shipment's state.
- **Derived SLA columns are stored, not computed at render.** Founder edits to the matrix or ODA master do NOT rewrite history (see §19).

---

## 8. Deduplication engine

### 8.1 Primary key

`LRN` (Excel column A, integer). The same LRN may appear across multiple uploaded files representing different lifecycle snapshots.

### 8.2 Tie-break ladder (highest priority first)

| Level | Rule | Source column |
|---|---|---|
| 1 | **Higher Current Status rank wins.** See table below. | `Current Status` (col T) |
| 2 | If Status ranks tie, **higher Remarks-progression rank wins.** Keyword match on the `Remarks` cell text. | `Remarks` (col V) |
| 3 | If still tied, **latest operational timestamp wins.** Use `Last Scan Date` if present, else `Delivered Date`, else `Pickup Date`. | various |
| 4 | If still tied, **latest upload batch wins.** | upload metadata |

### 8.3 Current Status rank table

| Status | Rank |
|---|---|
| Manifested | 1 |
| Dispatched | 2 |
| In Transit | 3 |
| Pending | 4 *(operational discovery: Pending often = exception/reattempt, more advanced than In Transit)* |
| Delivered | 5 |
| RTO | 5 *(terminal, equal-rank with Delivered — both are final outcomes; tie-breaks below them go to Remarks)* |

### 8.4 Remarks-progression rank — keyword matching

Lowercase substring match against the `Remarks` cell:

| Keyword pattern (substring) | Rank |
|---|---|
| `manifested` | 1 |
| `dispatched` | 2 |
| `reached hub` | 3 |
| `in transit` | 4 |
| `reached destination` | 5 |
| `out for delivery` | 6 |
| `delivered` | 7 |

If no keyword matches, treat rank as 0 (lowest) for tie-break purposes.

> **Important:** the column used here is `Remarks` (col V — 13 distinct progression values). NOT `Additional Remarks` (col AA — POD audit text only, 28 values, contains no progression signal).

### 8.5 Regression prevention

A lower-rank state must NOT overwrite a higher-rank state in `shipments_latest`. This is implicit in the tie-break ladder but state explicitly: **uploading an outdated snapshot of a shipment is a no-op.**

### 8.6 Notes for the implementer

- All 959 rows in the current sample have unique LRNs — no live dedup data yet. Build with synthetic duplicates for testing (§23).
- `Status Type` (col U) is intentionally NOT part of the ladder.
- `Client` (col D) is intentionally NOT used.

---

## 9. Two-table architecture

### 9.1 `shipments_raw`

- Append-only audit archive.
- Every row from every uploaded file, including duplicates, including superseded snapshots.
- Adds upload metadata columns: `_upload_batch_id`, `_upload_filename`, `_uploaded_at`.
- Used for: audit trail, debugging, future "why did dedup pick row X over row Y" drilldown.

### 9.2 `shipments_latest`

- One row per LRN — the dedup-winner.
- All 41 raw columns +**stored** derived SLA columns:
  - `_origin_zone` (string, one of the 5 zones)
  - `_destination_zone` (string, one of the 5 zones)
  - `_oda` (`YES` / `NO` / `UNKNOWN`)
  - `_expected_tat_days` (int, may be null if zones unresolved)
  - `_actual_tat_days` (int, null unless Delivered with both Pickup and Delivered Date)
  - `_tat_variance_days` (signed int, `_actual_tat − _expected_tat`)
  - `_sla_status` (`Early` / `On Time` / `Late`, null unless both above are non-null)
- All dashboard sections read from this table.

### 9.3 Storage choice

Both tables live in one SQLite DB file (or, equivalently, two object stores in IndexedDB). One file = trivial backup. See §3.5.

---

## 10. SLA / TAT / ODA domain logic

### 10.1 Actual TAT

```
Actual TAT (days) = (Delivered Date :: date) − (Pickup Date :: date)
```

- **Date-only** subtraction. Time component is **stripped**.
- Reason: avoid false fractional-day variances when the courier scans a delivery just after midnight.
- Computed only for rows where `Current Status = Delivered` AND both dates non-null. Otherwise `Actual TAT = null`.

### 10.2 Expected TAT

```
Expected TAT (days) = MATRIX[ Origin Zone ][ Destination Zone ]
                      + (1 if destination_pincode is ODA else 0)
```

- `MATRIX` is the 5×5 region SLA matrix (§5.1), editable via Section 5.
- Origin Zone and Destination Zone are derived from the 22 K pincode master, falling back to State if pincode is unrecognised. If neither resolves, Expected TAT is `null`.
- ODA flag comes from the same 22 K master. If unknown, treat as `NO` (no penalty).

### 10.3 SLA classification

```
if   Actual TAT  <  Expected TAT  →  Early
elif Actual TAT  =  Expected TAT  →  On Time
elif Actual TAT  >  Expected TAT  →  Late
```

If `Actual TAT` or `Expected TAT` is null, `SLA Status` is null (do not classify).

### 10.4 SLA compliance

```
SLA % combined = (count(Early) + count(On Time)) / count(Delivered shipments)
```

### 10.5 TAT Variance

```
TAT Variance (days) = Actual TAT − Expected TAT
```

Signed integer. Negative = early; zero = on time; positive = late.

### 10.6 Storage decision

Store **both** `SLA Status` (3-bucket category) AND `TAT Variance` (signed int) on each shipment row. Render any human-friendly text (e.g. `"Early by 2 days"`) at display time from these two columns. Do not store the human text.

### 10.7 Same-day-delivery edge case

- A shipment picked up and delivered on the same date → `Actual TAT = 0`.
- Matrix never returns 0 (diagonal = 4); `Expected TAT ≥ 4 + ODA adj`.
- So same-day delivery → variance ≤ −4 → `SLA Status = Early`. Correct.

---

## 11. UI navigation — five sections

Left-panel navigation, in order:

| # | Section | One-line purpose |
|---|---|---|
| 1 | **Landing** | Executive KPI snapshot + file upload. |
| 2 | **TAT Analysis** | Per-shipment SLA inspection (Delivered-only). |
| 3 | **Transit** | Per-shipment triage of non-Delivered shipments. |
| 4 | **Customize** | Ad-hoc filtered table. Toggle: row-level Detail OR per-company Aggregate. |
| 5 | **Edit** | Maintain the 5×5 matrix and the 22 K pincode master. |

Sections 1–4 use the **resizable layout** described in §18 (table on the left, charts on the right). Section 5 uses full screen width with no charts.

---

## 12. Section 1 — Landing page

### 12.1 Layout

```
┌──────────────────────────────────────────────────────────────┐
│  KPI cards row 1: Total Orders | Delivered | In Transit       │
│  KPI cards row 2: Pending | RTO | Date Range                  │
│  KPI cards row 3: Early | On Time | SLA | Late                │
│  KPI cards row 4: ODA | Non-ODA                               │
├────────────────────────────────┬─────────────────────────────┤
│  60% — Upload / Process panel  │  40% — Charts:               │
│  · file picker (multi-file)    │  · top: fixed pie            │
│  · preview table               │    (Overall Delivery Perf.)  │
│  · "Process & Update" button   │  · bottom: selectable chart  │
└────────────────────────────────┴─────────────────────────────┘
```

KPI cards span the full width on top. The resizable 60/40 split sits below.

### 12.2 KPI definitions

| KPI | Definition |
|---|---|
| Total Orders | `count(distinct LRN in shipments_latest)` |
| Delivered | `count where Current Status = Delivered` |
| In Transit | `count where Current Status = In Transit` |
| Pending | `count where Current Status = Pending` |
| RTO | `count where Current Status = RTO` |
| Early | `count where SLA Status = Early` |
| On Time | `count where SLA Status = On Time` |
| SLA | `count(Early) + count(On Time)` |
| Late | `count where SLA Status = Late` |
| ODA | `count where _oda = YES` |
| Non-ODA | `count where _oda = NO` |
| Date Range | `min(Pickup Date) → max(Pickup Date)` (or `Delivered Date` if no Pickup Date) |

### 12.3 Each KPI card content

- KPI name (label)
- Big number (count)
- Sub-line: percentage (where applicable). E.g. `Delivered: 856 (89.3 %)`.

### 12.4 Upload panel

- Multi-file `.xlsx` picker.
- Preview area shows the first 5 rows of each selected file.
- "Process & Update" button: runs the pipeline (§7), then refreshes the dashboard.
- Validation: schema check → must contain at minimum `LRN, Current Status, Pickup Date, Remarks` columns; warn if any of the 41 expected columns are missing.

### 12.5 Charts on Landing

- **Top fixed pie**: Overall Delivery Performance — `Early / On Time / Late / Not Yet Delivered` (matches PDF p4).
- **Bottom selectable chart**: see §17.

---

## 13. Section 2 — TAT Analysis

### 13.1 Inclusion rule

Process **only** rows where:
- `Current Status = Delivered`
- `Pickup Date is not null`
- `Delivered Date is not null`

All other shipments are excluded.

### 13.2 Layout

Resizable 60/40 split (§18). Left = the TAT spreadsheet table. Right = chart pair.

### 13.3 Table

Spreadsheet-style: vertical + horizontal scroll, sortable columns, column show/hide checkbox dropdown.

#### 13.3.1 Default visible columns

`LRN · Order id (Company) · Current Status · Pickup Date · Delivered Date · ODA · Expected TAT · Actual TAT · TAT Variance · SLA Status`

#### 13.3.2 Optional toggleable columns

`Consignee name · Additional Remarks · No of boxes · Weight · Payment Type · Package Amount · Pin code · Origin Zone · Destination Zone`

### 13.4 SLA filter dropdown (above the table)

Values: `All · Early · On Time · Late`. Default: `All`.

### 13.5 Sort By controls (above the table)

Explicit `Sort By: [column ▾]` + `Direction: [Asc / Desc]`. In addition to clickable column headers. Default: `Pickup Date · Desc`.

### 13.6 Row colour coding

| SLA Status | Row colour |
|---|---|
| Early | Light Green |
| On Time | Light Blue |
| Late | Light Red |

### 13.7 Charts on TAT

- **Top fixed pie**: Early / On Time / Late split (Delivered shipments only).
- **Bottom selectable chart**: see §17.

---

## 14. Section 3 — Transit

### 14.1 Inclusion rule

`Current Status ∈ {Manifested, Dispatched, In Transit, Pending, RTO}`.

RTO is included for visibility but visually de-emphasised (see §14.6).

### 14.2 Layout

Resizable 60/40 split. Left = the Transit spreadsheet. Right = chart pair.

### 14.3 Table

Single unified spreadsheet. Same UX pattern as TAT (sortable, scrollable, column show/hide).

#### 14.3.1 Status dropdown filter (above the table)

Values: `All · Manifested · Dispatched · In Transit · Pending · RTO`. Default: `All`.

#### 14.3.2 Sort By controls

Explicit `Sort By: [column ▾]` + `Direction`. Default = the built-in sort described in §14.5.

#### 14.3.3 Default visible columns

| # | Column |
|---|---|
| 1 | Current Status |
| 2 | Remarks |
| 3 | Days in Transit |
| 4 | Stuck |
| 5 | Pickup Date |
| 6 | Destination City |
| 7 | State |
| 8 | Pin code |

> Note: `LRN`, `Order id (Company)`, `Consignee` are in the **optional** toggles per the founder's explicit pick. Implementer may surface a "Show LRN" quick toggle for drilldown convenience.

#### 14.3.4 Optional toggleable columns

`LRN · Order id (Company) · Consignee name · Last Scan Date · Last Scan Location · Additional Remarks · Promise Date · Expected Date · Attempt Count · No of boxes · Weight · Payment Type · Package Amount · First Pending Date · Master Waybill · ODA · Origin Zone · Destination Zone`

### 14.4 Derived columns specific to Transit

| Column | Formula |
|---|---|
| **Days in Transit** | `(today :: date) − (Pickup Date :: date)` in days. **`N/A` if Pickup Date is null.** Computed at render time so the value reflects "now", not the last-upload date. |
| **Stuck** (boolean) | `Days in Transit > _expected_tat_days`. `N/A` if either side is N/A. `_expected_tat_days` is the **stored** value from upload time (not recomputed against the current matrix). |

### 14.5 Default sort

1. Stuck rows first, sub-sorted by `Days in Transit` desc.
2. Non-Stuck rows next, sub-sorted by `Days in Transit` desc.
3. RTO rows interleave naturally by sort, but always render with grey shading (overrides Remarks-bucket colour).

### 14.6 Row colour coding (Transit-specific)

Coloured **by Remarks progression bucket**, not by Stuck flag. Rationale: Remarks captures *where the shipment is operationally*, which is the most actionable signal in Transit.

| Bucket | Colour | Triggering keyword groups (case-insensitive substring) |
|---|---|---|
| Early-stage | Light blue | `manifested`, `dispatched` |
| Mid-transit | Light yellow | `reached hub`, `in transit` |
| Late-transit | Light green | `reached destination`, `out for delivery` |
| Exception | Light orange | anything not matched above (e.g. `"Reattempt as per NDR"`, `"Not Attempted"`, `"Package found in Audit"`) |
| RTO | Light grey | `Current Status = RTO`. **Overrides every other colour.** |

> The Stuck flag is shown via a small ⚠ icon **inside the Stuck column**; it does NOT change the row colour. The default Stuck-first sort is the primary way founders find stuck rows.

### 14.7 Charts on Transit

- **Top fixed pie**: status distribution (Manifested / Dispatched / In Transit / Pending / RTO).
- **Bottom selectable chart**: see §17.

---

## 15. Section 4 — Customize

### 15.1 Purpose

Ad-hoc query view. Founder defines their own filtered slice of the data. Two output modes via a top toggle:

- **Detail** — one row per shipment matching filters.
- **Aggregate** — one row per company in the filtered set.

This subsumes what was earlier discussed as a separate "Aggregate" tab.

### 15.2 Layout (top to bottom, inside the 60% left pane)

1. **View-mode toggle**: `Detail | Aggregate`.
2. **Filter panel**.
3. **Sort By** dropdown + **Asc / Desc** toggle.
4. **Column picker** (Detail mode only — checkbox dropdown).
5. **Apply** button + **Export** button.
6. **Table area** — empty until Apply is clicked.

The right 40% is the chart pair (§17).

### 15.3 Default state on entry

- Filter panel renders with safe defaults: date range = all-time, every other filter unset.
- Table area is **empty** until Apply is clicked. Forces deliberate querying; avoids re-rendering on every keystroke.

### 15.4 Apply mode

Explicit Apply button. Filter values live in session state; the table renders only on click. Two reasons:
1. Matches the "empty until applied" semantic.
2. Prevents partial-state re-renders mid-typing on the date pickers and multi-selects.

### 15.5 Filters

| Filter | Type | Options |
|---|---|---|
| Pickup Date | From / To date pickers | Any date in dataset |
| Origin Zone | Multi-select | West / South / North / East / North-East |
| Destination Zone | Multi-select | West / South / North / East / North-East |
| Company | Multi-select | All distinct `Order id` values |
| ODA | Tri-state | YES / NO / Both |
| Current Status | Multi-select | Manifested / Dispatched / In Transit / Pending / Delivered / RTO |

> SLA bucket and Stuck filters intentionally omitted for v1. Add later if founders ask.

### 15.6 Detail view

- One row per matching shipment.
- All 41 raw columns + all derived columns (`_origin_zone`, `_destination_zone`, `_oda`, `_expected_tat_days`, `_actual_tat_days`, `_tat_variance_days`, `_sla_status`, `Days in Transit`, `Stuck`) toggleable.
- Default visible: `LRN · Order id (Company) · Current Status · Pickup Date · Delivered Date · Destination City · State · Pin code`.
- Default sort: `Pickup Date · Desc`.

### 15.7 Aggregate view

One row per company (post-filter). **Fixed columns, no column picker:**

| # | Column | Definition |
|---|---|---|
| 1 | Company | `Order id` |
| 2 | Total Orders | `count(LRN)` |
| 3 | Order Share % | `Total Orders / sum(Total Orders) over all companies in filtered set` |
| 4 | Delivered | `count where Current Status = Delivered` |
| 5 | In Transit | `count where Current Status = In Transit` |
| 6 | **Pending** | `count where Current Status = Pending` *(added vs reference file)* |
| 7 | **RTO** | `count where Current Status = RTO` *(added)* |
| 8 | On Time % | `count(SLA = On Time) / Delivered` |
| 9 | Early % | `count(SLA = Early) / Delivered` |
| 10 | Late % | `count(SLA = Late) / Delivered` |
| 11 | **SLA % combined** | `(Early + On Time) / Delivered` *(added)* |
| 12 | **ODA %** | `count(_oda = YES) / Total Orders` *(added)* |

Default sort: `Total Orders · Desc` (matches Percetaged_file's natural ordering).

### 15.8 Export button

Downloads whichever table is currently rendered (Detail or Aggregate, post-filter) as `.xlsx` (and/or `.csv`).

### 15.9 Charts on Customize

- **Top fixed pie**: SLA status of the filtered set.
- **Bottom selectable chart**: see §17. **This is the only section where Heatmap is available.**

---

## 16. Section 5 — Edit

### 16.1 Purpose

Operator UI to view and modify the two reference datasets that drive SLA: the 5×5 region matrix and the 22 K pincode master.

### 16.2 Layout

- **No charts.** Edit uses full screen width.
- Two sub-tabs at the top: **Region Matrix** | **Pincode Master**.

### 16.3 Edit flow (identical on both sub-tabs)

1. **View mode (default)** — dataset rendered read-only. "Edit" button visible.
2. Click **Edit** → first warning modal: *"Changes cannot be reverted once applied. Continue?"* Confirm → enter edit mode.
3. **Edit mode** — cells inline-editable. "Save" and "Discard" buttons visible.
4. Click **Save** → second warning modal: *"Save these changes to the staging draft?"* Confirm → edits persist to a **draft** (separate table / object store). Banner appears: *"Draft saved. Apply to make changes live."*
5. Click **Apply** → third warning modal: *"Apply this draft live? This will change SLA calculations for all FUTURE uploads. Past shipments are not affected."* Confirm → draft promoted to live. Draft cleared. Edit mode exits.
6. **Discard** at any point in edit mode throws away the draft and returns to view mode.

### 16.4 Region Matrix sub-tab

- Inline-editable 5×5 grid with row/column labels = `West, South, North, East, North-East`.
- Diagonal cells (e.g. West–West) are editable.
- **Edit scope**: cell values only. Cannot add/remove zones (matrix structure fixed at 5×5).
- **Validation on Save**: each cell must be a non-negative integer.

### 16.5 Pincode Master sub-tab

22 K rows. **Never render the full table.** Two access patterns instead:

#### A. Search-and-edit (inline)

- Search box at the top, accepts either `Pincode` (numeric) or `City` name (substring match).
- Matching rows render in a small table, inline-editable in edit mode.
- **"Add Row"** button inserts a blank row at the top with fields `Pincode, City, State, Zone, ODA`.

#### B. Bulk re-upload

- "Upload new pincode file" button → replaces the entire master with a fresh Excel.
- Same Save→Apply flow.
- Suited for receiving an updated master from the field team.

#### Validation on Save

- `Pincode`: 6 digits, unique across the master.
- `Zone`: must be one of the 5 zones.
- `ODA`: must be `YES` or `NO`.
- `State`: free text (not validated against a list).

### 16.6 Save → Apply semantics

- **Save** persists edits to a staging draft, separate from the live copy. Dashboard continues to use the live copy.
- **Apply** promotes the draft to live, replacing the previous live copy. Future uploads consult the new live copy.
- **Implicit discard**: if the founder navigates away without applying, the draft persists for the next session. No auto-Apply, no auto-Discard.

### 16.7 Retroactivity — forward-only

**Apply does NOT recompute SLA fields for previously-uploaded shipments.** Each row in `shipments_latest` retains the SLA values computed at its own upload time (i.e. the matrix and ODA master in effect at that moment). New uploads use the new live values.

This is a deliberate choice for audit trust. See §19 for the architectural implication.

### 16.8 Audit log

None for v1. The two-stage Save→Apply with three warnings is the only safeguard. Single-founder local tool — adding an audit log is over-engineering for v1. Revisit if a second user appears.

---

## 17. Cross-cutting feature — Visualizations

### 17.1 Scope

Applies to Landing, TAT, Transit, Customize. **Edit has no charts.**

### 17.2 The Big 4 chart types

`Pie · Line · Bar · Heatmap`. Heatmap is **only available in Customize** (where Region is a primary filter dimension).

### 17.3 Per-section "top fixed pie"

| Section | Top pie shows |
|---|---|
| Landing | Overall Delivery Performance — `Early / On Time / Late / Not Yet Delivered` (all shipments) |
| TAT | `Early / On Time / Late` (Delivered-only) |
| Transit | Status distribution — `Manifested / Dispatched / In Transit / Pending / RTO` |
| Customize | SLA status of the filtered set |

### 17.4 "Bottom selectable chart"

Two dropdowns above the chart:

- **Chart type**: `Line · Bar · Pie · Heatmap` *(Heatmap only in Customize)*
- **Dimension**: `Per-company · Per-region · Month-on-month · By status`

Common pairings (worth pre-testing):

| Type × Dimension | Renders as | Reference |
|---|---|---|
| Bar × Per-company | Grouped bar per company (Early / On Time / Late %) | PDF p6 |
| Line × Month-on-month | Volume + SLA trend lines | PDF p7 |
| Pie × Per-region | Order share by destination zone | — |
| Bar × Per-status | Stacked status counts per period | PDF p9–12 |

All charts must respect the section's active filters (TAT's SLA dropdown, Transit's status dropdown, Customize's full filter panel post-Apply).

### 17.5 Customize Heatmap — full polish

Base reference: **State × Month — Late Delivery % Heatmap** (PDF p8). With three improvements over the reference:

#### 17.5.1 Volume-aware cell display

Each cell shows `% (n=count)` — e.g. `100 % (n=1)` is visually distinguishable from `100 % (n=50)`. Hover tooltip shows the full breakdown: total volume, on-time count, late count, average TAT.

> *Fixes the biggest misreading risk in the original heatmap: a state with one late shipment currently shows the same red intensity as a state with all 50 shipments late.*

#### 17.5.2 Rows sorted by total volume desc

High-volume states sit at the top of the heatmap. Founder attention lands on what matters operationally first.

#### 17.5.3 Two toggles above the heatmap

| Toggle | Values |
|---|---|
| **Granularity** | `State` / `Zone` |
| **Metric** | `Late %` / `SLA % combined` / `Avg TAT` |

Colour scale: green (good) → red (bad). Inverts for `SLA %` (high SLA % = green, low = red).

---

## 18. Cross-cutting feature — Resizable layout & fullscreen

### 18.1 Page layout

Initial ratio: **60% left (table or upload panel) / 40% right (chart pair)**. Applies to Landing, TAT, Transit, Customize. Edit uses full width.

The right 40% splits vertically:
- **Top half**: fixed pie chart (content per §17.3).
- **Bottom half**: selectable chart (per §17.4).

### 18.2 Resizing the splits

Originally specced as VS-Code-style drag handles. **Walked back to preset ratio buttons** because of the stlite UI primitives (§3.3):

A small toolbar above each laid-out section offers:

| Preset | Left % | Right % | Shortcut name |
|---|---|---|---|
| 60/40 (default) | 60 | 40 | Balanced |
| 50/50 | 50 | 50 | Even |
| 70/30 | 70 | 30 | Table-heavy |
| Table only | 100 | 0 | Hide charts |
| Charts only | 0 | 100 | Hide table |

A second toolbar inside the right pane offers the same idea for the top-pie / bottom-chart vertical split: `50/50 (default) · 70/30 (pie-heavy) · 30/70 (selectable-heavy) · Pie only · Selectable only`.

Both preset selections persist in session state across page navigations.

### 18.3 Fullscreen on charts

Originally specced as click-anywhere → custom modal. **Walked back to Plotly's built-in fullscreen icon** in the chart's modebar (top-right on hover). Native, free, no custom modal layer needed.

If the implementer has cycles, the click-anywhere → modal is still the nicer UX and can be added later.

---

## 19. Architectural implication — derived SLA columns are stored

Because of the §16.7 "forward-only" retroactivity rule, the derived SLA columns must be **physical columns on `shipments_latest`**, populated at upload time, never derived at render time.

Affected columns:

| Column | Stored at upload? | Recomputed on matrix/ODA edit? |
|---|---|---|
| `_origin_zone` | ✓ stored | ✗ stays as captured at upload |
| `_destination_zone` | ✓ stored | ✗ stays as captured at upload |
| `_oda` | ✓ stored | ✗ stays as captured at upload |
| `_expected_tat_days` | ✓ stored | ✗ stays as captured at upload |
| `_actual_tat_days` | ✓ stored | (independent of edits — derived only from Pickup/Delivered Date) |
| `_tat_variance_days` | ✓ stored | ✗ stays as captured at upload |
| `_sla_status` | ✓ stored | ✗ stays as captured at upload |
| `Days in Transit` | **derived live** | `today − Pickup Date` |
| `Stuck` | **derived live** but uses stored `_expected_tat_days` | Matrix edits do NOT change Stuck flag of already-loaded shipments |

This is the schema-shaping decision that flows from the founder's "edits don't rewrite history" requirement.

---

## 20. On hold (blocked on data delivery)

### 20.1 Region mapping

- The 22 K pincode → zone master file has not been delivered yet.
- Each pincode must be mapped to one of: `West / South / North / East / North-East`.
- **Border-town nuance**: some neighbouring towns straddle zone boundaries and should share TAT in practice. To be discussed with the founder when the file lands.
- **Build the logic now** (lookup function, fallback to State, override mechanism). **Configure the data later.**

### 20.2 ODA master

- Same 22 K pincode file is expected to carry the `ODA` (`YES` / `NO`) flag in its own column.
- Single combined master.
- Cannot configure now; the ingestion path (one row per pincode) and Section 5 editor are designed against this assumption.

### 20.3 Behaviour until the master arrives

- `_origin_zone`, `_destination_zone`, `_oda`, `_expected_tat_days`, `_tat_variance_days`, `_sla_status` are all `null` for every row.
- TAT-related KPI cards show `N/A` until the master is loaded.
- Transit's `Stuck` flag is always `N/A`.
- Customize's heatmap is empty.
- The dashboard remains useful for: counts, status breakdowns, raw-column inspection, dedup.

---

## 21. Data discrepancies and the decisions made

These were uncovered while inspecting the sample files. Each is settled — listed here so the implementer doesn't re-discover them.

| # | Discrepancy | Decision |
|---|---|---|
| 1 | `Order id` (col B) actually contains the Company name (KENSTAR, CLAD METAL, …). | **Do NOT rename in storage.** Internal logic maps `Order id → Company` at render. Keeps founders' raw-Excel intuition intact. |
| 2 | Raw file has no `Origin Region` or `Destination Region` columns. | Derive from pincode (via 22 K master), fall back to `State`. Persist as `_origin_zone` / `_destination_zone`. |
| 3 | No ODA pincode master file delivered yet. | Section 5 editor is designed; pipeline returns `N/A` ODA / Expected TAT / SLA fields until the master is loaded. |
| 4 | Two "Remarks" columns (`Remarks` col V, `Additional Remarks` col AA) — design doc was ambiguous. | **Dedup tie-break uses `Remarks` (col V).** `Additional Remarks` is POD-audit text only, NOT used for dedup; available as an optional display column. |
| 5 | `Client` column is `kiirus b2bc` for every row. | Useless for grouping. Ignored. |
| 6 | Sample file has zero LRN duplicates (959 unique / 959 rows). | Dedup engine is forward-looking. Test with synthetic duplicates (§23). |
| 7 | `Invoice Zone` (B / D1 / D2 / E / F) is Delhivery's billing zone, not geographic. | Do NOT use for the 5×5 SLA lookup. Available as an optional display column only. |
| 8 | The Green/red/yellow demo file's `Status` text uses `"Early by N day(s)"` etc. | Storage uses clean 3-bucket `SLA Status` + signed `TAT Variance`. Human text rendered at display time. |
| 9 | The Green/red/yellow demo includes 99 "Not yet delivered" rows in its TAT table. | Design says TAT-tab is Delivered-only. Stick with design. The Landing page's Overall Delivery pie includes all shipments (so "Not Yet Delivered" appears there). |
| 10 | The demo TAT file shows 3 rows with `Expected TAT = 0`. | Artefact of the old logic (which used Delhivery's `Expected Date` minus Pickup Date). New logic uses the matrix; diagonal = 4. The 0 rows just confirm the old derivation was broken; ignored. |
| 11 | `Manifest Date` looks like gibberish in Excel (`48:51.7`). | Cell number-format is `'mmss.0'` — Excel hides the date and shows only minutes/seconds.tenths. Underlying datetime is fine; pandas reads it correctly. Manifest Date is unused for SLA per design; no action required. |
| 12 | Percetaged_file aggregate columns omit Pending, RTO, SLA % combined, ODA %. | Customize's Aggregate view adds these four (§15.7). |
| 13 | The Green/red/yellow file has no actual cell fill colours despite the filename. | The colour scheme is implemented in the dashboard render (§13.6, §14.6), not parsed from the file. |
| 14 | Origin City is 958 Aurangabad / 1 Delhi. | Origin Zone is currently almost-constant (West). The Origin Zone filter in Customize is forward-looking for when Kiirus expands beyond Aurangabad. |

---

## 22. Suggested project file layout

```
liirus/
├── README.md                 ← this file
├── pyproject.toml            ← deps: streamlit, pandas, openpyxl, plotly
├── stlite/                   ← stlite bundle output, served as static
│   └── index.html
├── app/
│   ├── main.py               ← stlite entry point; navigation between sections
│   ├── pipeline/
│   │   ├── ingest.py         ← parse Delhivery xlsx, write to shipments_raw
│   │   ├── dedup.py          ← lifecycle-rank dedup, write to shipments_latest
│   │   ├── sla.py            ← Expected TAT, Actual TAT, Variance, SLA Status
│   │   ├── zones.py          ← pincode → zone lookup, fallback to state
│   │   └── oda.py            ← pincode → ODA YES/NO lookup
│   ├── sections/
│   │   ├── landing.py
│   │   ├── tat.py
│   │   ├── transit.py
│   │   ├── customize.py
│   │   └── edit.py
│   ├── components/
│   │   ├── kpi_cards.py
│   │   ├── chart_pair.py     ← top-pie + bottom-selectable
│   │   ├── chart_heatmap.py  ← Customize only, full-polish version
│   │   ├── data_table.py     ← shared sortable/filterable table widget
│   │   ├── layout.py         ← preset ratio toolbar, vertical split toolbar
│   │   └── modals.py         ← warning dialogs for Edit
│   ├── store/
│   │   ├── db.py             ← SQLite (sql.js) schema + CRUD
│   │   ├── migrations.py     ← initial schema, schema bumps
│   │   └── seed.py           ← load matrix from CSV, load ODA master
│   └── reference/
│       ├── matrix.csv        ← bundled copy of the 5×5
│       └── pincode_master.xlsx  ← placeholder until real file arrives
├── tests/
│   ├── test_dedup.py         ← synthetic duplicates, lifecycle-rank checks
│   ├── test_sla.py           ← matrix lookup, ODA adjustment, edge cases
│   ├── test_pipeline.py      ← end-to-end ingest+dedup+sla
│   └── fixtures/
│       └── sample_delhivery.xlsx
└── manifest.json             ← PWA manifest (icon, theme, name)
```

This is a suggestion, not a contract — the implementer can restructure as they prefer.

---

## 23. Verification / acceptance tests

### 23.1 Dedup

1. **Synthetic duplicate, lifecycle rank wins**: insert two rows with same LRN, one `Current Status = In Transit`, one `Delivered`. After dedup, `shipments_latest` has the Delivered row.
2. **Synthetic duplicate, Remarks tie-break**: two rows both `In Transit`, one with `Remarks = "Reached Hub"`, one with `Remarks = "Out for Delivery"`. After dedup, Out for Delivery wins.
3. **Synthetic duplicate, timestamp tie-break**: two rows identical on Status and Remarks, different `Last Scan Date`. Latest scan wins.
4. **Regression block**: load File A (LRN 123 = Delivered), then File B (LRN 123 = In Transit). After load of B, LRN 123 in `shipments_latest` is still Delivered.

### 23.2 SLA

5. **Matrix lookup**: pick 5 sample LRNs across different zones, manually compute `MATRIX[O][D]`, confirm `_expected_tat_days` matches.
6. **ODA adjustment**: pick a shipment whose destination pincode is flagged ODA, confirm `_expected_tat_days` is matrix value + 1.
7. **Same-day delivery**: synthetic shipment with Pickup Date = Delivered Date, confirm `_actual_tat_days = 0` and `SLA Status = Early`.
8. **Date-only stripping**: pickup at `2025-12-01 23:55`, delivered at `2025-12-02 00:05`. Confirm `_actual_tat_days = 1`, NOT 0.

### 23.3 Edit forward-only

9. Load 100 shipments. Note each row's `_expected_tat_days`. Open Section 5, change West→West from 4 to 6, Save, Apply. Confirm: existing 100 rows still show their original `_expected_tat_days`. Upload a new file → its rows use the new value.

### 23.4 UI

10. **TAT tab inclusion**: confirm only `Current Status = Delivered` rows with non-null Pickup AND Delivered Date appear. All others are absent.
11. **Transit tab inclusion**: confirm exactly the complement of TAT — every non-Delivered row appears, RTO included with grey shading.
12. **Customize empty default**: navigate to Customize, see filter panel and empty table. Set Pickup Date range, click Apply, see results.
13. **Customize Detail / Aggregate toggle**: with the same filters set, toggle between Detail and Aggregate; confirm row counts make sense (Detail rows ≥ Aggregate rows).
14. **Customize Aggregate columns**: confirm all 12 columns including the four added ones (Pending, RTO, SLA % combined, ODA %).

### 23.5 Charts

15. **Top fixed pie per section**: confirm Landing pie has 4 slices including "Not Yet Delivered"; TAT pie has 3 slices; Transit pie has 5 slices; Customize pie reflects filtered set.
16. **Heatmap volume display**: in Customize, run a filter, switch bottom chart to Heatmap. Confirm cells show `% (n=count)` and rows are sorted by total volume desc.
17. **Heatmap toggles**: switch granularity State ↔ Zone, confirm row count changes (Zone view = max 5 rows).

### 23.6 Distribution

18. **PWA install on phone**: open the deployed URL in mobile Chrome / Safari, install to home screen, **turn off Wi-Fi / mobile data**, open the installed app, confirm it loads and all sections work with the data that was synced before.
19. **Cold load size**: first-visit network transfer total < 60 MB.
20. **Subsequent open speed**: cached load < 3 seconds.

### 23.7 Resource

21. Run on an 8 GB RAM Windows laptop with Chrome + Word + Slack open. Confirm RAM usage stays < 500 MB and the dashboard does not visibly lag during navigation.

---

## 24. Glossary

| Term | Meaning |
|---|---|
| **LRN** | Unique shipment identifier in Delhivery's data. Primary key. |
| **TAT** | Turnaround Time. Days from Pickup to Delivery. |
| **Actual TAT** | Days actually taken. `Delivered Date − Pickup Date`. |
| **Expected TAT** | Days that should have been taken per the SLA matrix + ODA adjustment. |
| **TAT Variance** | `Actual − Expected`. Signed integer days. |
| **SLA Status** | `Early` / `On Time` / `Late`, derived from TAT Variance sign. |
| **SLA compliance** | `(Early + On Time) / Delivered`. |
| **ODA** | Out of Delivery Area. A pincode flag; ODA destinations get `+1` day on Expected TAT. |
| **5×5 matrix** | Region-to-Region SLA expectation table. Zones: West, South, North, East, North-East. |
| **Dedup** | Per-LRN merge of multiple snapshots into one "winner" using lifecycle rank. |
| **Stuck** | Transit-tab boolean. `Days in Transit > stored Expected TAT`. |
| **stlite** | Streamlit ported to WebAssembly via Pyodide. Runs the whole Python app in the browser. |
| **PWA** | Progressive Web App. Installable from a browser; works offline once installed. |
| **Pyodide** | The Python-on-WebAssembly runtime that powers stlite. |
| **Apply (Edit section)** | Promote a draft edit of the matrix / pincode master to live. Forward-only — does not rewrite history. |

---

*End of specification. The implementer can read this file straight through and have the complete picture.*
