# Kiirus Xpress — Complete Project Context

> **Purpose of this file.** Single, self-sufficient document covering the full state of the project: what it is, what each file does, how the data pipeline works, every UI behaviour, and every design decision that was made along the way. Hand this file to any LLM elsewhere and it should have the complete picture without needing the prior conversation.

---

## Table of contents

1. [Project overview](#1-project-overview)
2. [Hard constraints](#2-hard-constraints)
3. [Tech stack](#3-tech-stack)
4. [High-level architecture](#4-high-level-architecture)
5. [Repository layout — every file](#5-repository-layout--every-file)
6. [Source data files (sample data)](#6-source-data-files-sample-data)
7. [The raw 41-column Delhivery schema](#7-the-raw-41-column-delhivery-schema)
8. [SQLite schema](#8-sqlite-schema)
9. [Data pipeline — end to end](#9-data-pipeline--end-to-end)
10. [Deduplication engine](#10-deduplication-engine)
11. [SLA / TAT / ODA domain logic](#11-sla--tat--oda-domain-logic)
12. [Zone resolution + ODA lookup](#12-zone-resolution--oda-lookup)
13. [Database tables (live + draft pattern)](#13-database-tables-live--draft-pattern)
14. [Routing + sidebar](#14-routing--sidebar)
15. [Section 1 — Landing](#15-section-1--landing)
16. [Section 2 — TAT Analysis](#16-section-2--tat-analysis)
17. [Section 3 — Transit](#17-section-3--transit)
18. [Section 4 — Customize](#18-section-4--customize)
19. [Section 5 — Edit](#19-section-5--edit)
20. [Cross-cutting — Charts](#20-cross-cutting--charts)
21. [Cross-cutting — Layout (resizable split)](#21-cross-cutting--layout-resizable-split)
22. [Cross-cutting — Theme + design tokens](#22-cross-cutting--theme--design-tokens)
23. [Cross-cutting — Upload dialog](#23-cross-cutting--upload-dialog)
24. [Cross-cutting — Confirm-button helper](#24-cross-cutting--confirm-button-helper)
25. [Architectural invariant — derived SLA columns are stored](#25-architectural-invariant--derived-sla-columns-are-stored)
26. [Data discrepancies + decisions made](#26-data-discrepancies--decisions-made)
27. [Tests](#27-tests)
28. [Running locally](#28-running-locally)
29. [Deployment plan (stlite PWA)](#29-deployment-plan-stlite-pwa)
30. [Open items / known issues](#30-open-items--known-issues)

---

## 1. Project overview

A **fully local, offline-capable logistics analytics dashboard** for **Kiirus Xpress** (a small logistics startup; founders are non-technical). The dashboard:

- Ingests raw shipment Excel files exported from **Delhivery** (the courier partner).
- Deduplicates per-LRN snapshots using a lifecycle-rank tie-break ladder.
- Computes SLA / TAT performance per shipment.
- Surfaces an executive KPI snapshot, plus operational drilldowns (delivered triage, in-flight triage, ad-hoc filtered queries, reference-data maintenance).

**Primary user**: one founder per laptop. Used by ~1–2 people total at the company.

**Primary use cases**:
- Upload the latest Delhivery export → see updated dashboard.
- Check today's KPIs (Total Orders, Delivered, In Transit, Pending, RTO, SLA %, ODA / Non-ODA, Date Range, Early / On Time / Late).
- Inspect SLA performance per shipment (TAT Analysis section).
- Triage non-Delivered shipments (Transit section, with a "Stuck" flag).
- Build ad-hoc filtered queries (Customize section, with row-Detail and per-company-Aggregate views).
- Maintain the SLA reference data (Edit section: 5×5 region matrix + 22K pincode → zone + ODA master).
- View progress from a phone on weekends, when the laptop is at the office (mobile, truly offline — planned stlite PWA distribution).

---

## 2. Hard constraints

| # | Constraint | Why |
|---|---|---|
| 1 | **No cloud dependency.** Nothing on AWS / GCP / Azure / Render / etc. | Founder preference; data is operational + commercially sensitive. |
| 2 | **No internet dependency during operation.** | Must work in airport lounges, weekend home Wi-Fi outages, etc. |
| 3 | **No Gmail IMAP / no scheduled fetch.** | Earlier idea, scrapped — brittle, too many auth touchpoints. |
| 4 | **Files are uploaded manually** through the dashboard UI. | Simpler ops; founders already export the file weekly. |
| 5 | **Minimal install friction on founder laptops** (≤ 3 install steps, ideally a single click). | Founders are non-technical. |
| 6 | **Low RAM / disk footprint, runs on older laptops** (≥ 8 GB RAM, comfortable with a browser open). | Founder hardware varies. |
| 7 | **Mobile access required, fully offline.** Local-Wi-Fi-to-laptop is **not sufficient** — laptop is at office on weekends. | Stated explicitly during design. |
| 8 | **Founder edits to reference data must NOT retroactively rewrite history.** Past shipments keep their SLA values; matrix / ODA edits affect only future uploads. | Audit trust. |
| 9 | **Laptop and phone are independent installs.** No sync between them. Each device uploads its own copy of the Delhivery file. | Forced by constraints 1 + 2 + 7. |

---

## 3. Tech stack

**Local development (current state):**

| Layer | Choice | Version |
|---|---|---|
| App framework | **Streamlit** | ≥ 1.32, < 2.0 |
| Language | **Python** | 3.11+ (tested under 3.13) |
| Data store | **SQLite** | stdlib `sqlite3` |
| Data manipulation | **pandas** | ≥ 2.0 |
| Excel I/O | **openpyxl** | ≥ 3.1 |
| Charts | **Plotly** | ≥ 5.18 |
| Numerics | **numpy** | ≥ 1.26 |
| Column DnD widget | **streamlit-sortables** | ≥ 0.3 |

**Distribution (planned)** — **stlite** (Streamlit ported to WebAssembly via Pyodide). Produces a single static HTML bundle that runs the entire Python pipeline inside the browser tab — no server, no Python install, truly offline once cached. Installable as a **PWA** (Progressive Web App) on both desktop and mobile via the browser's "Install" action.

`requirements.txt`:
```
streamlit>=1.32,<2.0
pandas>=2.0
openpyxl>=3.1
plotly>=5.18
numpy>=1.26
streamlit-sortables>=0.3
```

`manifest.json` (PWA) — already present at repo root, points to `icons/icon-192.png` and `icons/icon-512.png`.

---

## 4. High-level architecture

```
Founder selects one or more Delhivery .xlsx files in the Upload dialog
                          │
                          ▼
        pipeline.ingest.ingest_file(file_like, filename)
              │ openpyxl + pandas read sheet 0
              │ validate REQUIRED_COLUMNS = {LRN, Current Status, Pickup Date, Remarks}
              │ append every row to shipments_raw (audit archive, never deleted)
              │ uuid batch_id + uploaded_at timestamp on every row
              │
              ▼
        pipeline.dedup.merge_into_latest(new_rows, existing_by_lrn)
              │ group new rows by LRN
              │ for each LRN: combine with existing-latest, pick winner by:
              │   1. status rank   (Manifested 1, …, Delivered 5, RTO 5)
              │   2. remarks rank  (regex keywords on Remarks col V)
              │   3. operational timestamp (Last Scan > Delivered > Pickup)
              │   4. upload batch order
              │ output: (to_insert, to_update, skipped_regressions)
              │
              ▼
        pipeline.sla.compute_row(winner)
              │ origin zone:  Origin City → State → zone (hardcoded city map for now)
              │ destination zone: pincode master → state→zone fallback
              │ ODA flag:    pincode master lookup (UNKNOWN = treat as NO)
              │ Expected TAT: matrix[origin][dest] + (1 if ODA else 0)
              │ Actual TAT:  Delivered Date :: date − Pickup Date :: date (Delivered only)
              │ Variance:    Actual − Expected
              │ SLA Status:  sign of Variance (Early / On Time / Late)
              │
              ▼
        UPSERT shipments_latest with raw cols + 7 stored derived cols
              │ (one row per LRN, primary key = lrn)
              │
              ▼
        store.queries.load_latest() → pd.DataFrame
              │
              ▼
        Dashboard sections render from this DataFrame
              │
              │  ┌─ Landing       (KPIs + chart pair + Upload trigger)
              │  ├─ TAT Analysis  (Delivered-only table + chart pair)
              │  ├─ Transit       (non-Delivered + Stuck flag + chart pair)
              │  ├─ Customize     (filter + Detail/Aggregate + heatmap)
              │  └─ Edit          (5×5 matrix + 22K pincode master)
              ▼
        UI flows redirect or open dialogs; no further pipeline runs until next upload.
```

Two governing rules everywhere:

1. **Dedup is lifecycle-based, NOT upload-order-based.** Uploading an older snapshot after a newer one CANNOT regress a shipment.
2. **Derived SLA columns are STORED at upload time**, not recomputed on render. Founder edits to the matrix or ODA master affect only future uploads (see §25).

---

## 5. Repository layout — every file

```
liirus/
├── README.md                   ← original spec doc (unchanged)
├── BUILD.md                    ← engineering notes (running, distribution sketch)
├── PROJECT_CONTEXT.md          ← this file
├── streamlit_app.py            ← repo-root entry: adds repo to sys.path, calls app.main.main()
├── requirements.txt            ← Python deps (Streamlit, pandas, openpyxl, plotly, numpy, streamlit-sortables)
├── manifest.json               ← PWA manifest (name, theme color, icons)
├── kiirus Xpress Pvt Ltd Updated_Project File (1).csv   ← 5×5 SLA matrix sample
├── kiirus.db                   ← SQLite database (gitignored if needed; auto-created)
│
├── app/
│   ├── __init__.py             ← empty
│   ├── main.py                 ← Streamlit entry — set_page_config, init_db, seed, inject CSS,
│   │                              render sidebar nav, route to current section
│   ├── assets/
│   │   ├── README.md           ← instructions: drop logo at app/assets/logo.png
│   │   └── logo.png            ← (optional) brand logo; emoji fallback if missing
│   │
│   ├── pipeline/               ← Pure data logic, no UI
│   │   ├── __init__.py         ← empty
│   │   ├── ingest.py           ← Excel → shipments_raw → merge → shipments_latest + stored SLA
│   │   ├── dedup.py            ← Lifecycle-rank dedup (status / remarks / timestamp / batch)
│   │   ├── sla.py              ← Expected/Actual TAT, Variance, classify_sla, compute_row
│   │   ├── zones.py            ← pincode→zone + state→zone fallback (with lru_cache)
│   │   └── oda.py              ← pincode→ODA (YES/NO/UNKNOWN) lookup
│   │
│   ├── store/                  ← SQLite layer
│   │   ├── __init__.py         ← empty
│   │   ├── schema.py           ← RAW_COLUMNS (41), DERIVED_COLUMNS (7), DATE/INT/FLOAT sets,
│   │   │                          DB_COL display→snake_case map, sqlite_type(), ZONES = 5 zones
│   │   ├── db.py               ← connection, cursor() ctx mgr, SCHEMA_SQL, init_db, reset_db
│   │   ├── seed.py             ← seed matrix from CSV, state→zone fallback dict, get_live_matrix()
│   │   └── queries.py          ← load_latest(), load_raw_for_lrn(), counts, history
│   │
│   ├── sections/               ← One file per left-panel section
│   │   ├── __init__.py         ← empty
│   │   ├── landing.py          ← KPI cards + chart pair, Upload trigger in header
│   │   ├── tat.py              ← Delivered-only spreadsheet + chart pair
│   │   ├── transit.py          ← Non-Delivered triage + Stuck flag + chart pair
│   │   ├── customize.py        ← Filter panel + Detail/Aggregate toggle + chart pair + heatmap
│   │   └── edit.py             ← Region Matrix tab + Pincode Master tab, Save→Apply flow
│   │
│   ├── components/             ← Reusable UI building blocks
│   │   ├── __init__.py         ← empty
│   │   ├── theme.py            ← Tokens (DARK/LIGHT), CSS injection, Plotly defaults, format_int_for_display
│   │   ├── kpi_cards.py        ← 12 KPI cards in 4 rows (3/3/4/2), inline styles via t()
│   │   ├── data_table.py       ← column_picker (drag-and-drop via streamlit-sortables),
│   │   │                          sort_controls, render_table (pill styler for status cells)
│   │   ├── chart_pair.py       ← Top fixed pie + bottom selectable chart (Line/Bar/Pie [+Heatmap in Customize])
│   │   ├── chart_heatmap.py    ← Customize-only State×Month or Zone×Month heatmap with toggles
│   │   ├── chart_expand.py     ← Click-to-expand modal (st.dialog) with breakdown stats
│   │   ├── layout.py           ← horizontal_split (60/40 presets) + vertical_split (50/50 presets)
│   │   ├── modals.py           ← confirm_button (two-step inline confirm pattern)
│   │   └── upload_dialog.py    ← st.dialog: file picker → preview → process → close + refresh
│   │
│   └── reference/
│       └── matrix.csv          ← Bundled copy of the 5×5 matrix (loaded on first run)
│
└── tests/
    ├── __init__.py             ← empty
    ├── test_dedup.py           ← status_rank, remarks_rank, pick_winner, merge_into_latest, regression block
    └── test_sla.py             ← actual_tat_days, expected_tat_days (with mocked matrix), classify_sla
```

Total source: ~4,345 LOC across 30 Python files.

---

## 6. Source data files (sample data)

| # | File | Shape | Role |
|---|---|---|---|
| 1 | `Kiirus Automation file UPDATED (1).xlsx` | 959 rows × 41 cols | Raw Delhivery export. Primary input the dashboard ingests. Currently only sample. |
| 2 | `kiirus Xpress Pvt Ltd Updated_Project File (1).csv` | 6×6 (5×5 matrix + header row + header col) | 5×5 region-to-region SLA matrix. Diagonal = 4 days. Final, in active use. Auto-loaded into `sla_matrix_live`. |
| 3 | `Green_red-yellow.xlsx` | 959 × 19 | **Visual reference only** for the TAT-tab row colour coding. File contains no actual cell fill colours — the `Status` text wording (`"Early by N day(s)"`, etc.) is illustrative; the actual schema uses `Early / On Time / Late` + signed `TAT Variance`. |
| 4 | `Percetaged_file.xlsx` | 22 × 8 | Reference for per-company aggregate view (now folded into Customize Section, see §18). |

**Missing — to be delivered later**: a single 22 K-row Excel/CSV mapping `Pincode → City → State → Zone → ODA (YES/NO)`. Until this lands, every feature that depends on Region or ODA is **unconfigured but built** — logic returns `N/A` / `UNKNOWN`.

### 6.1 SLA matrix (file 2) verbatim

```
            West  South  North  East  North-East
West          4     6      6     7     10
South         6     4      6     7     10
North         6     6      4     7      8
East          7     7      7     4      6
North-East   10    10      8     6      4
```

Diagonal cells = 4 days (intra-zone). Off-diagonal max = 10 days (West ↔ North-East).

### 6.2 Per-company aggregate reference (file 4) — column shape

`Company, Total Orders, Order Share (%), Delivered, In Transit, On Time (%), Early (%), Late (%)`

Our implementation extends this with `Pending count, RTO count, SLA % combined, ODA %` → 12 columns total. See §18.7.

---

## 7. The raw 41-column Delhivery schema

| # | Excel col | Column name | Type | Notes |
|---|---|---|---|---|
| 1 | A | `LRN` | int | **Primary key.** Unique shipment identifier. |
| 2 | B | `Order id` | string | **Misnamed — actually contains COMPANY/CLIENT NAME** (e.g. `KENSTAR`, `CLAD METAL`). The Aggregate view groups by this. **Do NOT rename in storage** — UI maps `Order id → Company` at render time. |
| 3 | C | `No of boxes` | int | Optional column. |
| 4 | D | `Client` | string | **Useless** — every row says `kiirus b2bc`. Do not group on it. |
| 5 | E | `Manifest Date` | datetime | Cell format is `'mmss.0'` in source (Excel shows `mm:ss.t`, hides the date). Underlying value is fine; pandas reads it correctly. **Ignored for SLA.** |
| 6 | F | `Pickup Date` | datetime | **Reliable.** Drives `Actual TAT` start date. |
| 7 | G | `Expected Date` | datetime | Delhivery's expected date. **Deprecated** — Expected TAT comes from the matrix. |
| 8 | H | `Invoice Number` | string | Prefixed with a back-tick. Display-only. |
| 9 | I | `Consignee name` | string | Optional column. |
| 10 | J | `Origin City` | string | 958/959 are `Aurangabad`. Used to derive Origin Zone via tiny hardcoded map. |
| 11 | K | `Destination City` | string | Informational. |
| 12 | L | `Client Location/warehouse` | string | Mostly `kiirus b2bc`; occasional brand-specific. Display-only. |
| 13 | M | `Pick up Address` | float (mostly null) | Ignore. |
| 14 | N | `Pin code` | int | **Drives Region + ODA lookup** via 22K master. |
| 15 | O | `Dispatch Count` | int | Optional. |
| 16 | P | `First dispatch date` | datetime | Optional. |
| 17 | Q | `Last dispatch date` | datetime | Optional. |
| 18 | R | `Last Scan Location` | string | Useful in Transit. |
| 19 | S | `Last Scan Date` | datetime | Useful in Transit (also dedup tie-break level 3). |
| 20 | **T** | **`Current Status`** | string | **Primary lifecycle column.** Values: `Manifested · Dispatched · In Transit · Pending · Delivered · RTO`. |
| 21 | U | `Status Type` | string | Auxiliary. **Ignored for dedup.** |
| 22 | **V** | **`Remarks`** | string | **Dedup tie-breaker.** 13 distinct values. Progression text like `"Delivered to Consignee"`, `"Out for Delivery"`, `"Consignment Reached at Destination"`. |
| 23 | W | `Promise Date` | datetime | Optional. |
| 24 | X | `Delivered Date` | datetime | **Reliable.** Drives `Actual TAT` end date. |
| 25 | Y | `Payment Type` | string | `Pre-paid` or `COD`. |
| 26 | Z | `Master Waybill` | int | Optional. |
| 27 | AA | `Additional Remarks` | string | POD audit notes (`"Clean POD \| As per DS Model System audit"`, etc.). **NOT used for dedup.** Optional display column. |
| 28 | AB | `Return Promise Date` | datetime | Optional. |
| 29 | AC | `Transaction Type` | float | Mostly null. Ignore. |
| 30 | AD | `Transaction Mode` | float | Mostly null. Ignore. |
| 31 | AE | `First Pending Date` | datetime | Useful in Transit for Pending rows. |
| 32 | AF | `Package Amount` | float | Optional. |
| 33 | AG | `Weight` | float | Optional. |
| 34 | AH | `First attempt date` | datetime | Optional. |
| 35 | AI | `Last Attempt date` | datetime | Optional. |
| 36 | AJ | `Attempt Count` | float | Useful in Transit. |
| 37 | AK | `First Return Date` | datetime | Optional. |
| 38 | AL | `Invoice Zone` | string | **Delhivery billing zone** (B/D1/D2/E/F). Has nothing to do with the 5×5 geographic zones. Do NOT use for SLA matrix lookup. |
| 39 | AM | `RVP/ Forward identifier` | string | Optional. |
| 40 | AN | `PUR ID` | string | Optional. |
| 41 | AO | `State` | string | **Drives Region lookup** when no pincode hit. |

### 7.1 Distribution snapshot (current sample file)

- `Current Status`: Delivered 856 · In Transit 71 · Pending 16 · Dispatched 11 · RTO 4 · Manifested 1
- 959 unique LRNs / 959 rows → **no duplicates yet**. Dedup is forward-looking.
- 21 distinct companies in `Order id` (KENSTAR is dominant at 638 / 66.5 %).
- Origin City: 958 Aurangabad, 1 Delhi.
- Date range: late Nov 2025 → early Feb 2026.

### 7.2 Display ↔ DB column mapping

`schema.to_db_col()` converts display names to SQLite-safe snake_case. Examples:

| Display | DB column |
|---|---|
| `LRN` | `lrn` |
| `Order id` | `order_id` |
| `Pick up Address` | `pick_up_address` |
| `RVP/ Forward identifier` | `rvp_forward_identifier` |
| `Last Scan Date` | `last_scan_date` |

Bidirectional dicts `DB_COL` and `DISPLAY_COL` are pre-built in `schema.py`.

---

## 8. SQLite schema

Database file: `<repo_root>/kiirus.db`. Auto-created on first launch by `init_db()`.

### 8.1 `shipments_raw` — append-only audit archive

```sql
CREATE TABLE shipments_raw (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    _upload_batch_id  TEXT    NOT NULL,
    _upload_filename  TEXT    NOT NULL,
    _uploaded_at      TEXT    NOT NULL,
    -- 41 raw columns, all stored as TEXT/INTEGER/REAL per schema.sqlite_type()
    lrn               INTEGER,
    order_id          TEXT,
    no_of_boxes       INTEGER,
    -- ... (all 41 columns from §7) ...
    state             TEXT
);
CREATE INDEX idx_raw_lrn ON shipments_raw(lrn);
CREATE INDEX idx_raw_batch ON shipments_raw(_upload_batch_id);
```

Used for:
- Full audit trail of every uploaded row (nothing is ever deleted).
- Future "why did dedup pick row X over row Y?" drilldown (`load_raw_for_lrn(lrn)`).
- Debugging / rollback.

### 8.2 `shipments_latest` — one row per LRN (dedup winner) + stored derived SLA

```sql
CREATE TABLE shipments_latest (
    -- 41 raw columns (same as shipments_raw)
    lrn               INTEGER,
    -- ... (41 raw cols) ...
    -- 7 derived SLA columns (computed at upload time)
    _origin_zone       TEXT,        -- 'West' | 'South' | 'North' | 'East' | 'North-East' | NULL
    _destination_zone  TEXT,        -- same
    _oda               TEXT,        -- 'YES' | 'NO' | 'UNKNOWN'
    _expected_tat_days INTEGER,     -- matrix[origin][dest] + (1 if ODA else 0)
    _actual_tat_days   INTEGER,     -- Delivered_Date::date − Pickup_Date::date (Delivered only)
    _tat_variance_days INTEGER,     -- Actual − Expected
    _sla_status        TEXT,        -- 'Early' | 'On Time' | 'Late' | NULL
    -- provenance
    _source_raw_id     INTEGER REFERENCES shipments_raw(id),
    _updated_at        TEXT NOT NULL,
    PRIMARY KEY (lrn)
);
CREATE INDEX idx_latest_status     ON shipments_latest(current_status);
CREATE INDEX idx_latest_pickup     ON shipments_latest(pickup_date);
CREATE INDEX idx_latest_company    ON shipments_latest(order_id);
CREATE INDEX idx_latest_sla_status ON shipments_latest(_sla_status);
```

Used for:
- All dashboard reads (`load_latest()` returns a pandas DataFrame).
- The dedup engine writes here via UPSERT (`ON CONFLICT(lrn) DO UPDATE …`).

### 8.3 Reference tables (live + draft pairs)

```sql
-- 5x5 SLA matrix
CREATE TABLE sla_matrix_live  (origin_zone TEXT, destination_zone TEXT, days INTEGER, PRIMARY KEY (origin_zone, destination_zone));
CREATE TABLE sla_matrix_draft (origin_zone TEXT, destination_zone TEXT, days INTEGER, PRIMARY KEY (origin_zone, destination_zone));

-- Pincode master
CREATE TABLE pincode_master_live  (pincode TEXT PRIMARY KEY, city TEXT, state TEXT, zone TEXT NOT NULL, oda TEXT NOT NULL CHECK (oda IN ('YES','NO')));
CREATE TABLE pincode_master_draft (pincode TEXT PRIMARY KEY, city TEXT, state TEXT, zone TEXT NOT NULL, oda TEXT NOT NULL CHECK (oda IN ('YES','NO')));
CREATE INDEX idx_pincode_city ON pincode_master_live(city);

-- State → Zone fallback (used when pincode lookup misses)
CREATE TABLE state_zone_fallback (state TEXT PRIMARY KEY, zone TEXT NOT NULL);
```

The live/draft split implements the **Save → Apply** workflow in the Edit section (see §19). Drafts persist across sessions; only **Apply** copies draft → live.

### 8.4 `uploads` — upload history

```sql
CREATE TABLE uploads (
    batch_id     TEXT PRIMARY KEY,
    filename     TEXT NOT NULL,
    uploaded_at  TEXT NOT NULL,
    rows_in      INTEGER NOT NULL,
    rows_new     INTEGER NOT NULL,
    rows_updated INTEGER NOT NULL,
    rows_skipped INTEGER NOT NULL
);
```

### 8.5 Connection management

`store/db.py` exposes `get_conn()` (returns `sqlite3.Connection` with `Row` factory) and `cursor()` (context manager that auto-commits / rolls back / closes).

---

## 9. Data pipeline — end to end

### 9.1 Ingest (`app/pipeline/ingest.py`)

```python
def ingest_file(file_like, filename: str) -> dict:
    df = _read_workbook(file_like)              # pandas + openpyxl
    warnings = validate_schema(df)              # raises IngestError if REQUIRED_COLUMNS missing
    batch_id = str(uuid.uuid4())
    uploaded_at = datetime.utcnow().isoformat()

    rows = [...]                                # each row dict-augmented with batch/file/timestamp

    raw_id_by_index = _insert_raw(rows, ...)    # → shipments_raw
    incoming_lrns = {r["LRN"] for r in rows}
    existing_by_lrn = _fetch_latest_by_lrn(incoming_lrns)
    to_insert, to_update, skipped = merge_into_latest(rows, existing_by_lrn)
    n_inserted = _upsert_latest(to_insert + to_update, raw_id_by_index)
    _record_upload(batch_id, filename, uploaded_at, len(rows), len(to_insert), len(to_update), len(skipped))

    return summary_dict
```

`REQUIRED_COLUMNS = {"LRN", "Current Status", "Pickup Date", "Remarks"}` — missing any of these raises `IngestError`. Missing optional columns trigger a warning (stored as NULL). Unexpected columns trigger a warning (ignored).

`_normalise_value(col, v)` coerces each cell:
- Dates → ISO string (`pd.to_datetime(...).isoformat()`).
- INT_COLUMNS → `int()` or None.
- FLOAT_COLUMNS → `float()` or None.
- All others → `str()`.

`recompute_all_sla()` exists as a one-time helper for first-time pincode-master load (when historical rows are still N/A). After that, the §25 forward-only rule kicks in and matrix/ODA edits do NOT call this function.

### 9.2 Output of `ingest_file()`

```python
{
    "batch_id": "uuid-string",
    "filename": "Kiirus Automation file UPDATED (1).xlsx",
    "rows_in": 959,
    "rows_new": 942,
    "rows_updated": 17,
    "rows_skipped": 0,
    "warnings": ["3 optional column(s) missing — will be stored as NULL: ...", "..."]
}
```

---

## 10. Deduplication engine

`app/pipeline/dedup.py`. Per-LRN merge using a 4-level tie-break ladder.

### 10.1 Status rank (level 1)

```python
STATUS_RANK = {
    "Manifested": 1, "Dispatched": 2, "In Transit": 3,
    "Pending":    4, "Delivered":   5, "RTO":         5,
}
```

Note: **Pending = 4** is operationally further along than In Transit — derived from real data inspection (Pending often = exception / reattempt). Delivered and RTO are both terminal (rank 5).

### 10.2 Remarks rank (level 2)

Lowercase regex match against the `Remarks` cell. Patterns checked best-rank-first:

```python
REMARKS_PATTERNS: list[tuple[re.Pattern, int]] = [
    (re.compile(r"\bdelivered\b"),                         7),
    (re.compile(r"out for delivery"),                      6),
    (re.compile(r"reached\s+(?:at\s+)?destination"),       5),
    (re.compile(r"in transit"),                            4),
    (re.compile(r"reached\s+(?:at\s+)?hub"),               3),
    (re.compile(r"dispatched"),                            2),
    (re.compile(r"manifested"),                            1),
]
```

If no match: rank = 0. The regex tolerates Delhivery's verbose strings (e.g. `"Consignment Reached at Destination"`).

> **Important:** The column used is `Remarks` (col V — 13 distinct progression values). NOT `Additional Remarks` (col AA — POD audit text only, 28 values, no progression signal).

### 10.3 Operational timestamp (level 3)

```python
def _operational_timestamp(row):
    for col in ("Last Scan Date", "Delivered Date", "Pickup Date"):
        ts = _coerce_ts(row.get(col))
        if ts is not None:
            return ts
    return None
```

### 10.4 Upload batch (level 4)

Lexicographic comparison of `_upload_batch_id` (UUIDs). Last-batch wins — true tie-breaker only.

### 10.5 The picker

```python
def pick_winner(rows: list[dict]) -> dict:
    if len(rows) == 1:
        return rows[0]
    def sort_key(r):
        return (
            status_rank(r.get("Current Status")),
            remarks_rank(r.get("Remarks")),
            _operational_timestamp(r) or datetime.min,
            r.get("_upload_batch_id") or "",
        )
    return max(rows, key=sort_key)
```

### 10.6 Merge

```python
def merge_into_latest(new_rows, existing_by_lrn):
    new_by_lrn = group_by_lrn(new_rows)            # in case batch has dups for same LRN
    to_insert, to_update, skipped = [], [], []

    for lrn, candidates in new_by_lrn.items():
        existing = existing_by_lrn.get(lrn)
        all_candidates = candidates + ([existing] if existing else [])
        winner = pick_winner(all_candidates)

        if existing is None:
            to_insert.append(winner)
        elif winner is existing:
            skipped.append({"lrn": lrn, "reason": "existing has higher lifecycle rank"})
        else:
            to_update.append(winner)

    return to_insert, to_update, skipped
```

**Regression prevention** falls out naturally: when the existing row beats every incoming candidate, the LRN is added to `skipped` and `shipments_latest` is not touched.

### 10.7 Sample data caveat

All 959 LRNs are unique in the current sample. **Dedup is forward-looking** — real validation will happen with the next upload, OR via synthetic tests (`tests/test_dedup.py`).

---

## 11. SLA / TAT / ODA domain logic

`app/pipeline/sla.py`. Pure functions; no side effects; testable in isolation.

### 11.1 Actual TAT

```python
def actual_tat_days(pickup, delivered, current_status):
    if current_status != "Delivered":
        return None
    p = _to_date(pickup)
    d = _to_date(delivered)
    if p is None or d is None:
        return None
    return (d - p).days
```

**Date-only subtraction.** Time component stripped. Reason: avoid false fractional-day variances when the courier scans a delivery just after midnight. Computed ONLY for `Current Status = Delivered` rows with both dates non-null.

`_to_date()` accepts `datetime`, `date`, or string in multiple formats (`%Y-%m-%d %H:%M:%S`, `%Y-%m-%d`, `%d/%m/%Y`, `%m/%d/%Y`, `%d-%m-%Y`). Falls back to `pd.to_datetime` as last resort.

### 11.2 Expected TAT

```python
def expected_tat_days(origin_zone, destination_zone, oda_flag):
    if not origin_zone or not destination_zone:
        return None
    matrix = get_live_matrix()                   # loaded from sla_matrix_live
    base = matrix.get((origin_zone, destination_zone))
    if base is None:
        return None
    return base + (1 if oda_flag == "YES" else 0)
```

- **Matrix lookup** on `(origin_zone, destination_zone)`.
- **ODA adjustment** = +1 day if ODA. UNKNOWN treated as NO (no penalty).
- Returns None if either zone is missing or matrix has no entry.

### 11.3 Classify SLA

```python
def classify_sla(actual, expected):
    if actual is None or expected is None:
        return None
    if actual < expected: return "Early"
    if actual == expected: return "On Time"
    return "Late"
```

### 11.4 Variance

`TAT Variance = Actual − Expected`. Signed integer days. Negative = early; zero = on time; positive = late.

### 11.5 SLA % combined

`(count(Early) + count(On Time)) / count(Delivered)` — used in KPI cards (§15) and Customize Aggregate view (§18.7).

### 11.6 Same-day delivery edge case

Pickup == Delivered → Actual = 0; matrix diagonal = 4 → Variance ≤ −4 → **Early**. (See `test_same_day_delivery_is_early` in `tests/test_sla.py`.)

### 11.7 `compute_row(raw)` — packs all 7 derived fields

```python
{
    "_origin_zone":        ...,
    "_destination_zone":   ...,
    "_oda":                'YES' | 'NO' | 'UNKNOWN',
    "_expected_tat_days":  int | None,
    "_actual_tat_days":    int | None,
    "_tat_variance_days":  int | None,
    "_sla_status":         'Early' | 'On Time' | 'Late' | None,
}
```

Origin zone: derived from `Origin City` via a tiny hardcoded map (`_ORIGIN_CITY_TO_ZONE = {"Aurangabad": "West", "Delhi": "North"}`). Extends as Kiirus adds origin cities.

Destination zone: `resolve_zone(pin_code, state)` — pincode lookup first, state fallback.

ODA: `lookup_oda(pin_code)` — pincode master lookup, returns `'UNKNOWN'` if missing.

---

## 12. Zone resolution + ODA lookup

### 12.1 `app/pipeline/zones.py`

```python
@lru_cache(maxsize=1)
def _state_zone_map() -> dict[str, str]:
    return {state: zone from state_zone_fallback table}

def lookup_zone_by_pincode(pincode) -> Optional[str]:
    return zone where pincode = ? in pincode_master_live

def lookup_zone_by_state(state) -> Optional[str]:
    return _state_zone_map().get(state.strip())

def resolve_zone(pincode, state) -> Optional[str]:
    """Pincode wins; state is the fallback. None if neither resolves."""
    z = lookup_zone_by_pincode(pincode)
    if z is not None:
        return z
    return lookup_zone_by_state(state)

def clear_caches() -> None:
    """Called after pincode master edits."""
    _state_zone_map.cache_clear()
```

### 12.2 `app/pipeline/oda.py`

```python
def lookup_oda(pincode) -> str:
    """Returns 'YES' | 'NO' | 'UNKNOWN'."""
    if pincode is None or str(pincode).strip() in ('', 'nan'):
        return "UNKNOWN"
    row = SELECT oda FROM pincode_master_live WHERE pincode = ?
    return row[0] if row else "UNKNOWN"
```

### 12.3 State → Zone fallback table

Seeded once from `app/store/seed.py::STATE_ZONE` dict. Covers all 28 Indian states + UTs:

| Zone | States |
|---|---|
| West | Maharashtra, Gujarat, Goa, Rajasthan, Madhya Pradesh, Chhattisgarh, Daman and Diu, Dadra and Nagar Haveli |
| South | Karnataka, Tamil Nadu, Kerala, Andhra Pradesh, Telangana, Puducherry, Lakshadweep |
| North | Delhi, Haryana, Punjab, Uttar Pradesh, Uttarakhand, Himachal Pradesh, J&K, Ladakh, Chandigarh |
| East | West Bengal, Bihar, Jharkhand, Odisha/Orissa, Andaman and Nicobar Islands |
| North-East | Assam, Arunachal Pradesh, Meghalaya, Manipur, Mizoram, Nagaland, Tripura, Sikkim |

Editable in code only (`seed.py`) — not via the dashboard. The Edit section maintains the pincode master, not this fallback.

---

## 13. Database tables (live + draft pattern)

For both the SLA matrix and the pincode master, there are two tables:

```
sla_matrix_live      ← used by uploads, used by every read
sla_matrix_draft     ← staging area for pending edits (initially empty)

pincode_master_live  ← used by uploads, used by every read
pincode_master_draft ← staging area for pending edits (initially empty)
```

**Save → Apply lifecycle:**

1. **View mode** — user sees `*_live`.
2. **Edit** — user clicks Edit, modifies cells.
3. **Save** — edits write to `*_draft`. Live untouched.
4. **Apply** — `DELETE FROM *_live; INSERT INTO *_live SELECT * FROM *_draft; DELETE FROM *_draft;` — live is replaced. Future uploads consult new live.
5. **Discard** — `DELETE FROM *_draft;` — draft is thrown away.

Drafts persist across sessions. Implicit-discard does not happen — leaving the page keeps the draft staged for next session.

Both Edit sub-tabs show a yellow `draft-banner` div when their draft table has any rows.

---

## 14. Routing + sidebar

`app/main.py`. Renders the sidebar (brand block, nav, theme toggle, footer) and dispatches to the active section's `render()` function.

### 14.1 NAV_ITEMS registry

```python
NAV_ITEMS: list[tuple[str, str, str, callable]] = [
    ("Landing",      "▣", "Overview",       landing.render),
    ("TAT Analysis", "◷", "Delivered SLA",  tat.render),
    ("Transit",      "⛟", "In flight",      transit.render),
    ("Customize",    "≡", "Ad-hoc query",   customize.render),
    ("Edit",         "✎", "Reference data", edit.render),
]
```

### 14.2 Current state

`st.session_state["current_section"]` tracks the active section (default: `"Landing"`). Inactive nav rows are rendered as `st.sidebar.button(...)` with a multi-line label (icon + label + sublabel separated by `\n`). The active row is rendered as a styled HTML div (yellow tint + dot indicator) — NOT a button.

**Known issue with this pattern:** the active row (div, fixed `min-height: 56px`) and inactive rows (Streamlit buttons with default padding) can render at slightly different heights, causing a layout jump when switching active section. There is a CSS rule in `theme.py` that sets `min-height: 56px !important; padding: 10px 12px !important;` on sidebar buttons to match the active row dimension. This works in most cases but the exact height match depends on Streamlit's internal button DOM, which has changed across versions. See §30.

**Alternative pattern** (built and reverted): full HTML anchor approach with `?section=X` query-param routing. Replaces all 5 rows with identical `<a href>` anchors so dimensions are guaranteed identical. The user reverted to the button approach for reasons of simplicity, so the current code uses buttons.

### 14.3 Brand block

`_render_brand_block()` renders:
- Logo image (`app/assets/logo.png` if present) OR yellow-tinted box with 📦 emoji.
- "Kiirus Xpress" wordmark + "LOGISTICS / INTELLIGENCE" tagline.
- Yellow accent divider.
- "WORKSPACE" section label.

### 14.4 Theme toggle

`_render_theme_toggle()` — `st.sidebar.toggle("🌗 Light mode", value=(mode == "light"))`. On change, sets `st.session_state["theme_mode"]` and calls `st.rerun()`. The new CSS is injected on the next run by `inject_global_css()`.

### 14.5 Footer

`_render_footer()` — three lines:
- 🟢 Local-only
- 🟢 Offline-ready
- Built for Kiirus Xpress

---

## 15. Section 1 — Landing

### 15.1 Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Landing                                            ↑ Upload new file(s) │
│  ───                                                                     │
│  ┌─ Total Orders ─┐  ┌─ Delivered ──┐  ┌─ In Transit ─┐                │
│  │     959        │  │     856      │  │      71       │                │
│  │ all shipments  │  │ 89.3% of 959 │  │ 7.4% of 959   │                │
│  └────────────────┘  └──────────────┘  └───────────────┘                │
│  ┌─ Pending ──────┐  ┌─ RTO ────────┐  ┌─ Date Range ─┐                │
│  │     16         │  │      4       │  │ 25-Nov-25 →  │                │
│  │ 1.7% of 959    │  │ 0.4% of 959  │  │ 24-Feb-26    │                │
│  └────────────────┘  └──────────────┘  └───────────────┘                │
│  ┌─ Early ─┐ ┌─ On Time ─┐ ┌─ SLA (E+OT) ─┐ ┌─ Late ─┐                 │
│  │  549    │ │   161     │ │     710       │ │  146   │                 │
│  └─────────┘ └───────────┘ └───────────────┘ └────────┘                 │
│  ┌─ ODA ───────────┐  ┌─ Non-ODA ────────┐                              │
│  │       0          │  │       0           │                            │
│  └──────────────────┘  └───────────────────┘                            │
│                                                                          │
│  ─── Charts (top fixed pie + bottom selectable, stacked vertically) ──── │
│  Overall Delivery Performance pie                                        │
│  [Line/Bar/Pie selector]  ×  [Per-company/Per-region/Month/Status]      │
└──────────────────────────────────────────────────────────────────────────┘
```

### 15.2 KPI cards (`app/components/kpi_cards.py`)

12 cards in 4 rows: 3 / 3 / 4 / 2. Each card has:
- 11px uppercase label
- 32px tabular-mono JetBrains Mono yellow value
- 12px muted sub-line (percentage)
- 18px padding, 12px radius, 1px border
- Hover: 2px lift + yellow border + yellow glow shadow

Inline styles use literal color values resolved via `t()` at render time (not CSS vars) — because Streamlit's nested DOM sometimes breaks CSS var inheritance for inline styles. See `_styles()` in `kpi_cards.py`.

Date Range card uses 15px white text instead of 32px yellow numerics — yellow is reserved for counts/percentages.

### 15.3 Spec revision: Upload is NO LONGER inline

Originally the Landing page had a 60/40 split with Upload on the left and charts on the right. **Revised per `CLAUDE_CODE_UI_PROMPT.md`:**
- KPI cards span full width on top.
- Below the cards: a vertically stacked chart pair (no Upload widget).
- The `↑ Upload new file(s)` button in the section header opens a modal `st.dialog` containing the file picker, preview, and Process button. Same drawer trigger exists on TAT, Transit, Customize. Edit has no upload button.

### 15.4 Charts

`chart_pair.render(df, section_key="landing", top_box, bottom_box)`:
- **Top pie**: `Overall Delivery Performance` — Early / On Time / Late / Not Yet Delivered (all 959 shipments). Non-Delivered rows are bucketed as "Not Yet Delivered".
- **Bottom selectable**: see §20.

---

## 16. Section 2 — TAT Analysis

### 16.1 Inclusion rule

Only rows where:
- `Current Status == "Delivered"`
- `Pickup Date` is not null
- `Delivered Date` is not null

### 16.2 Layout

`layout.horizontal_split(section_key="tat", default="60/40")` — preset-ratio toolbar above the section split into table (left) + chart pair (right). User can pick `60/40 · 50/50 · 70/30 · Table only · Charts only`.

### 16.3 Table

Spreadsheet via `st.dataframe`. Default visible columns:
`LRN · Order id (Company) · Current Status · Pickup Date · Delivered Date · ODA · Expected TAT · Actual TAT · TAT Variance · SLA Status`

Optional toggleable (via drag-and-drop column picker):
`Consignee name · Additional Remarks · No of boxes · Weight · Payment Type · Package Amount · Pin code · Origin Zone · Destination Zone`

Display labels (rename map): `_oda → ODA`, `_expected_tat_days → Expected TAT`, etc.

### 16.4 SLA filter dropdown

`All · Early · On Time · Late`. Default: `All`. Filters the rows shown.

### 16.5 Sort By + Direction

Explicit `Sort By: [column]` + `Direction: [Asc/Desc]`. Default: `Pickup Date · Desc`.

### 16.6 Row styling (pill-only, NOT full-row tint)

The original spec called for a 3px colored left-border SLA accent via `box-shadow: inset 3px 0 0 <color>` on the first cell. **Reverted** — Streamlit's `st.dataframe` is a React (glide-data-grid) component that does NOT reliably render `box-shadow`, `padding`, `border`, or `text-align` from pandas Stylers. The attempt produced visible white bands over LRN cells.

**Current approach**: status-like columns (`SLA Status`, `_sla_status`, `Current Status`, `Stuck`, `ODA`, `_oda`) render as pills via `background-color: <tint> color: <bold-color> font-weight: 600` on those cells only. Other cells stay default. The `row_classifier` parameter to `data_table.render_table()` is accepted for API compatibility but ignored.

### 16.7 Charts

- **Top pie**: SLA distribution among Delivered shipments — `Early / On Time / Late`.
- **Bottom selectable**: see §20.

---

## 17. Section 3 — Transit

### 17.1 Inclusion rule

`Current Status ∈ {Manifested, Dispatched, In Transit, Pending, RTO}`.

### 17.2 Derived columns

- **Days in Transit** = `(today − Pickup Date::date)` days. NaN if Pickup Date null.
- **Stuck** = `"⚠ Stuck"` if `Days in Transit > _expected_tat_days`, `""` otherwise. NaN-safe.

### 17.3 Layout + status filter

Same 60/40 split. Status filter dropdown: `All · Manifested · Dispatched · In Transit · Pending · RTO`.

### 17.4 Default sort

Two-key sort: `_stuck_rank` (1 if Stuck, else 0) desc, then `Days in Transit` desc. Stuck rows always float to the top.

### 17.5 Default visible columns

`Current Status · Remarks · Days in Transit · Stuck · Pickup Date · Destination City · State · Pin code`

### 17.6 Optional toggleable

`LRN · Order id · Consignee name · Last Scan Date · Last Scan Location · Additional Remarks · Promise Date · Expected Date · Attempt Count · No of boxes · Weight · Payment Type · Package Amount · First Pending Date · Master Waybill · ODA · Origin Zone · Destination Zone`

### 17.7 Row styling (pill on Stuck only)

Pills applied to status-like cells via `_pill_styler` (same as TAT). Stuck cells with value `"⚠ Stuck"` get red pill styling.

The row-bucket classifier (Remarks → bucket) is computed but unused for styling (see §16.6).

### 17.8 Charts

- **Top pie**: in-flight status distribution (Manifested / Dispatched / In Transit / Pending / RTO).
- **Bottom selectable**: see §20.

---

## 18. Section 4 — Customize

### 18.1 Layout (top to bottom)

1. Section header with `↑ Upload` trigger.
2. View-mode segmented control: `Detail | Aggregate`.
3. Filter panel inside `st.expander("Filters", expanded=True)`.
4. `Apply` button — required to render the table (default state is empty).
5. Sort-By + Direction (for Detail view).
6. Column picker (Detail view only).
7. Export CSV button.
8. Table area (left 60%) + chart pair with heatmap (right 40%).

### 18.2 Filter panel

| Filter | Widget | Source |
|---|---|---|
| Pickup Date range | `st.date_input(value=(min, max))` | min/max of `Pickup Date` in the data |
| Origin Zone | multi-select w/ All/Clear buttons | `ZONES` constant |
| Destination Zone | multi-select w/ All/Clear buttons | `ZONES` constant |
| Company | multi-select w/ All/Clear buttons | distinct `Order id` |
| ODA | selectbox `Both / YES / NO` | static |
| Current Status | multi-select w/ All/Clear buttons | all 6 statuses |

Multi-selects use a helper `_multiselect_with_all(label, options, key)` that adds two small buttons above the picker — `All` (populates with all options) and `Clear` (empties). Empty = no filter (every value matches). See `_multiselect_with_all` in `customize.py`.

### 18.3 Apply gate

```python
if apply_clicked:
    st.session_state["_customize_applied"] = True
    st.session_state["_customize_filters"] = filters

if not st.session_state.get("_customize_applied", False):
    st.caption("Set filters above, then click **Apply** to populate the table.")
    return
```

### 18.4 Detail view

- Default visible columns: `LRN · Order id · Current Status · Pickup Date · Delivered Date · Destination City · State · Pin code`
- All-toggleable: above + raw columns (`Consignee name`, `Remarks`, etc.) + derived (`_oda`, `_expected_tat_days`, `_actual_tat_days`, `_tat_variance_days`, `_sla_status`, `_origin_zone`, `_destination_zone`).
- Sort By: any visible column. Default: `Pickup Date · Desc`.
- Same table widget as TAT/Transit (pill styling on status columns).

### 18.5 Aggregate view (per-company breakdown)

12 columns, fixed (no column picker):

| # | Column | Definition |
|---|---|---|
| 1 | Company | `Order id` |
| 2 | Total Orders | `count(LRN)` |
| 3 | Order Share % | `100 × Total / sum(Total over all companies in filtered set)` |
| 4 | Delivered | `count where Current Status == "Delivered"` |
| 5 | In Transit | `count where Current Status == "In Transit"` |
| 6 | Pending | `count where Current Status == "Pending"` (added vs reference file) |
| 7 | RTO | `count where Current Status == "RTO"` (added) |
| 8 | On Time % | `100 × count(SLA="On Time") / Delivered` |
| 9 | Early % | `100 × count(SLA="Early") / Delivered` |
| 10 | Late % | `100 × count(SLA="Late") / Delivered` |
| 11 | SLA % combined | `100 × (Early + On Time) / Delivered` (added) |
| 12 | ODA % | `100 × count(_oda="YES") / Total Orders` (added) |

Default sort: `Total Orders · Desc`.

### 18.6 Export

`st.download_button("Export CSV", ...)` — downloads whatever table is currently rendered (Detail or Aggregate, post-filter).

### 18.7 Charts

- **Top pie**: SLA status of the filtered set (Early / On Time / Late / Not Yet Delivered).
- **Bottom selectable**: see §20. **This is the only section where Heatmap is available** (`allow_heatmap=True`).

---

## 19. Section 5 — Edit

Two sub-tabs: `Region Matrix | Pincode Master`. No charts on this section.

### 19.1 Region Matrix sub-tab (`_render_matrix_tab`)

States:
- **View mode (default)**: read-only 5×5 grid via `st.dataframe(df.style.apply(_style))`. Diagonal cells get yellow-soft tint.
- **Edit mode**: `st.data_editor(num_rows="fixed")`. User edits cells.
- **Draft staged**: if `sla_matrix_draft` has rows, show yellow `draft-banner` div, then read-only draft preview + Apply / Discard buttons.

Transitions:
1. **Enter Edit** — `confirm_button("Edit matrix", warning="Changes cannot be reverted once applied. Continue?")`. On Confirm, `st.session_state["_matrix_editing"] = True`.
2. **Save** — validate (every cell must be non-negative int), `_save_matrix_draft(edited)` writes to `sla_matrix_draft`. Banner appears.
3. **Apply** — `confirm_button("Apply draft → live", warning="This will change SLA for FUTURE uploads. Past not affected. Cannot be reverted.")`. On Confirm, `_apply_matrix_draft()` does `DELETE FROM live; INSERT INTO live SELECT FROM draft; DELETE FROM draft;`.
4. **Discard** — `DELETE FROM sla_matrix_draft;`.

Edit scope: cell values only. Matrix structure fixed at 5×5.

### 19.2 Pincode Master sub-tab (`_render_pincode_tab`)

**Search-and-edit (inline) — pattern A:**
- `st.text_input("Search by pincode or city name")`.
- Matches: pincode prefix (numeric query) or city substring (case-insensitive).
- Results rendered in pages of 25 via `st.data_editor(num_rows="dynamic")`.
- Page nav: `← Previous / Next →` buttons + "Page X of Y" centered caption.
- Column config: `zone` is a Selectbox with `ZONES` options; `oda` is a Selectbox with `["YES", "NO"]`.
- Validation on Save: `pincode` is 6 digits + unique; `zone` ∈ ZONES; `oda` ∈ {YES, NO}.
- Save → `pincode_master_draft` via UPSERT (`ON CONFLICT(pincode) DO UPDATE …`).
- Apply → INSERT INTO live ... ON CONFLICT DO UPDATE (preserves rows not in draft). Then `DELETE FROM pincode_master_draft;` and `zones_clear_caches()`.

**Bulk re-upload — pattern B:**
- `st.file_uploader("Replace entire pincode master with .xlsx")`.
- Required columns: `pincode, zone, oda` (case-insensitive). `city` and `state` optional.
- Preview first 20 rows.
- Replace flow: `confirm_button(...)` → `_replace_live_pincodes(df)` → `DELETE FROM live; INSERT FROM file;` → `zones_clear_caches()`.
- **First-time-load special case**: if `n_before == 0`, also call `recompute_all_sla()` to populate derived columns on existing historical rows. After that first load, the §25 forward-only rule applies.

### 19.3 Edit has no chart pair and no upload button

The section title is rendered with `render_section_header("Edit", show_upload_button=False)`. Full screen width used for the matrix/editor.

### 19.4 Audit log: none for v1

The two-stage Save→Apply with three confirmation warnings (Edit → Save → Apply) is the only safeguard. Single-founder local tool; an audit log would be over-engineering. Revisit if a second user appears.

---

## 20. Cross-cutting — Charts

`app/components/chart_pair.py`. Used by Landing, TAT, Transit, Customize.

### 20.1 Top fixed pie

Per section:
- Landing: Overall Delivery Performance (Early/On Time/Late/Not Yet Delivered, all shipments).
- TAT: SLA distribution among Delivered.
- Transit: in-flight status distribution.
- Customize: SLA status of the filtered set.

Style: donut (`hole=0.5`), inside-slice text shows `"{value:,} ({percent})"` in dark text on coloured slices, hover tooltip with full breakdown, horizontal legend at bottom.

### 20.2 Bottom selectable chart

Two dropdowns: **Chart type** × **Dimension**.

Chart types: `Line · Bar · Pie` (+ `Heatmap` in Customize only).
Dimensions: `Per-company · Per-region · Month-on-month · By status`.

`_dimension_frame(df, dim)` produces a 2-column DataFrame:
- Per-company: top 25 by count, descending.
- Per-region: groupby `_destination_zone`.
- Month-on-month: `Pickup Date.dt.to_period("M")`.
- By status: groupby `Current Status`.

The chart respects the section's active filters (TAT SLA dropdown, Transit status dropdown, Customize full filter panel post-Apply).

### 20.3 Click-to-expand (`chart_expand.py`)

`render_chart_with_expand(fig, key, title, stats_df, extra_md)` renders the chart inline + a small `⛶ Expand` button. Clicking opens `st.dialog(width="large")` with:
- Enlarged chart (height bumped to 520px).
- Extra Markdown line (e.g. `**Total shipments:** 959`).
- Breakdown table (Category / Count / Percent for pies; Dim/Count/Percent for bar+line; top-25 worst cells for heatmap).

Payload is stashed in `st.session_state["_chart_expand_payload"]` to survive the dialog open.

### 20.4 Customize Heatmap (`chart_heatmap.py`)

Only available in Customize. Base reference: State × Month — Late Delivery %.

**Volume-aware cell display**: cells show `"{percent}% (n={count})"` so 1-shipment cells aren't visually equivalent to 50-shipment cells.

**Rows sorted by total volume desc**: highest-volume states/zones at the top.

**Two toggles above the heatmap:**
- Granularity: `State / Zone`
- Metric: `Late % / SLA % combined / Avg TAT`

Color scales differ per metric:
- `Late %`: green (0) → yellow (50) → red (100).
- `SLA % combined`: dark (0) → grey (50) → green (100) — high = good.
- `Avg TAT`: black → yellow gradient, zmin/zmax = data range.

---

## 21. Cross-cutting — Layout (resizable split)

`app/components/layout.py`.

### 21.1 Horizontal split (table vs charts)

`horizontal_split(section_key, default="60/40")`:

| Preset | Left % | Right % | Use case |
|---|---|---|---|
| 60/40 | 60 | 40 | Balanced (default) |
| 50/50 | 50 | 50 | Even |
| 70/30 | 70 | 30 | Table-heavy |
| Table only | 100 | 0 | Hide charts |
| Charts only | 0 | 100 | Hide table |

Returns `(left_col, right_col)`. Either may be `None` when the preset is `Table only` / `Charts only`. The preset selector is `st.segmented_control` with persistence via session state (keyed per section so each tab remembers its own choice).

### 21.2 Vertical split (pie vs selectable inside the right pane)

`vertical_split(section_key, container)`:

| Preset | Top % | Bottom % |
|---|---|---|
| 50/50 | 50 | 50 | Default |
| 70/30 | 70 | 30 | Pie-heavy |
| 30/70 | 30 | 70 | Selectable-heavy |
| Pie only | 100 | 0 | — |
| Selectable only | 0 | 100 | — |

Returns `(top_container, bottom_container)`. Streamlit can't truly stack-and-size containers, so the two child containers are returned in document order; the caller is responsible for filling them.

### 21.3 Original spec (reverted): drag-handle resize

Originally specced as VS-Code-style drag handles. Walked back to preset ratio buttons because Streamlit has no native drag-resize and the available custom components are fragile. Preset buttons functionally equivalent, less elegant.

---

## 22. Cross-cutting — Theme + design tokens

`app/components/theme.py`. Central design system.

### 22.1 Token dicts

Two dicts: `DARK` (default) and `LIGHT`. Cover:
- **Surfaces**: `bg_base`, `surface_1/2/3`, `sidebar_bg`
- **Borders**: `border_default`, `border_strong`, `sidebar_border`
- **Text**: `text_primary`, `text_muted`, `text_dim`, sidebar variants
- **Accent**: `yellow_primary`, `yellow_strong`, `yellow_soft`, `yellow_edge`, `yellow_glow`, `yellow_glow_strong`
- **Status (shared between modes)**: `STATUS_EARLY` `#4ADE80`, `STATUS_ONTIME` `#60A5FA`, `STATUS_LATE` `#F87171`, `STATUS_RTO`, `STATUS_PENDING`, `STATUS_NA`
- **Status tints (rgba)**: `STATUS_SOFT[name]`
- **Motion**: `transition_fast` (150ms cubic-bezier), `transition_med` (250ms)
- **Shadows**: `shadow_card`, `shadow_hover`, `shadow_kpi_hover`
- **Input**: `input_bg`, `input_border`
- **Footer dot**: `footer_dot`

### 22.2 Accessors

```python
def current_mode() -> str:
    return st.session_state.get("theme_mode", "dark")

def tokens() -> dict:
    return LIGHT if current_mode() == "light" else DARK

def t(key: str) -> str:
    return tokens()[key]
```

Components call `t("surface_1")` etc. to read mode-aware colors at render time.

### 22.3 Plotly defaults

```python
def get_plotly_layout() -> dict:
    return dict(
        paper_bgcolor=t("surface_1"),
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t("text_primary"), family="Inter, system-ui, sans-serif", size=12),
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(gridcolor=t("border_default"), zerolinecolor=t("border_default"),
                   tickfont=dict(color=t("text_primary"))),
        yaxis=dict(gridcolor=t("border_default"), zerolinecolor=t("border_default"),
                   tickfont=dict(color=t("text_primary"))),
        legend=dict(font=dict(color=t("text_primary"))),
    )

def apply_plotly_defaults(fig):
    fig.update_layout(**get_plotly_layout())
    fig.update_xaxes(tickfont=dict(color=t("text_primary")))
    fig.update_yaxes(tickfont=dict(color=t("text_primary")))
    return fig
```

`SERIES_COLORS = ["#FFD60A", STATUS_ONTIME, STATUS_EARLY, STATUS_LATE, STATUS_PENDING]` — used by bar/line cycle.
`HEATMAP_COLORSCALE = [[0.0, "#0A0A0B"], [1.0, "#FFD60A"]]` — black → yellow gradient.

### 22.4 Global CSS

`inject_global_css()` (called at top of `main.py` on every rerun) calls `_build_css(tokens())` which f-string-interpolates the active token set into a giant CSS string and `st.markdown(..., unsafe_allow_html=True)`s it.

Sections covered:
- CSS custom properties (`:root, .stApp, [data-testid="stApp"]`).
- Scrollbar colours.
- App shell backgrounds (aggressive selectors: data-testid AND `[class*="appview-container"]` / `[class*="stMain"]` / `[class*="block-container"]` to beat Streamlit's emotion-cache classes).
- Full-viewport width (`.block-container { max-width: 100% !important }`).
- Typography (h1-h6 sizes, body, labels).
- Sidebar nav + brand block + theme toggle + footer styling.
- KPI cards (hover lift + yellow glow).
- Buttons (primary + secondary, with yellow hover).
- Inputs / selects (focus ring in yellow).
- Segmented control (active = yellow-soft + yellow text).
- Dataframe + Plotly chart container (1px border, 12px radius, hover yellow glow).
- Expander, tabs, dialog, alerts.
- Draft banner.
- Streamlit's own theme variables (`--background-color`, `--text-color`, etc.) overridden for parity with our palette.

The CSS is regenerated on every theme toggle. Streamlit re-runs the script, `inject_global_css()` injects the new CSS, all the variable-driven styles flip.

### 22.5 Backwards-compat constants

Legacy constants are still exported but defined from `DARK`:
```python
BG_BASE = DARK["bg_base"]
SURFACE_1 = DARK["surface_1"]
TEXT_PRIMARY = DARK["text_primary"]
YELLOW_PRIMARY = DARK["yellow_primary"]
YELLOW_SOFT = DARK["yellow_soft"]
PLOTLY_LAYOUT = get_plotly_layout()
```

These exist for back-compat where components imported them directly. New code should prefer `t(key)`.

### 22.6 `format_int_for_display(df)`

Helper that coerces all numeric columns in `INTEGER_DISPLAY_COLUMNS` (Expected TAT, Actual TAT, Variance, Days in Transit, LRN, Pin code, etc.) to `Int64` dtype so they render as integers like `4` instead of floats like `4.000000`. Called by `data_table.render_table()` and `customize._render_aggregate()`.

---

## 23. Cross-cutting — Upload dialog

`app/components/upload_dialog.py`. `@st.dialog("Upload new file(s)", width="large")` decorator on `open_upload_dialog()`.

Flow:
1. `st.file_uploader(type=["xlsx"], accept_multiple_files=True)`.
2. Per-file preview (first 5 rows) in an expander.
3. `Process & Update` button (primary, disabled until at least one file picked) + `Cancel` (secondary).
4. On process: loop files, call `ingest_file(f, filename)`, collect summary. Display per-file `st.success` or `st.error`. Show warnings.
5. If all succeeded: set `st.session_state["_upload_complete_refresh"] = True` and `st.rerun()`. Dialog auto-closes on rerun and the underlying section refreshes its `load_latest()`.

Invoked from each section's header via `render_section_header("Section Name", show_upload_button=True)` which returns True when the `↑ Upload new file(s)` button is clicked.

---

## 24. Cross-cutting — Confirm-button helper

`app/components/modals.py`.

```python
def confirm_button(label, warning, section_key, on_confirm=None, button_type="primary") -> bool:
    """Two-step confirm pattern (Streamlit's true modal is limited / poor under stlite).
    First click → 'armed' state + show warning.
    Second click on '✓ Confirm <label>' → invoke on_confirm + return True.
    Cancel button drops the armed state.
    """
```

Used throughout the Edit section for the Save → Apply → Discard flow. Returns `True` only on the second (confirm) click — the caller's `if confirm_button(...)` then runs the post-action UI update.

---

## 25. Architectural invariant — derived SLA columns are stored

Because of the §2 constraint #8 (edits don't rewrite history), the derived SLA columns must be **physical columns on `shipments_latest`**, populated at upload time, NEVER derived at render time.

| Column | Stored at upload? | Recomputed on matrix/ODA edit? |
|---|---|---|
| `_origin_zone` | ✓ stored | ✗ stays as captured |
| `_destination_zone` | ✓ stored | ✗ stays as captured |
| `_oda` | ✓ stored | ✗ stays as captured |
| `_expected_tat_days` | ✓ stored | ✗ stays as captured |
| `_actual_tat_days` | ✓ stored | (independent of edits) |
| `_tat_variance_days` | ✓ stored | ✗ stays as captured |
| `_sla_status` | ✓ stored | ✗ stays as captured |
| `Days in Transit` (Transit section only) | **derived live** at render — `today − Pickup Date` | always live |
| `Stuck` flag (Transit section only) | **derived live** but uses stored `_expected_tat_days` | matrix edits do NOT change Stuck flag of already-loaded shipments |

There is ONE exception to the forward-only rule: `recompute_all_sla()` in `ingest.py` is called by `_replace_live_pincodes()` in the Edit section when `n_before == 0` — i.e. the first-time load of the pincode master. Before that load, every historical row has `_oda = "UNKNOWN"` and zone columns NULL; after that load, the historical rows are backfilled once and the forward-only rule kicks in from then on.

---

## 26. Data discrepancies + decisions made

| # | Discrepancy | Decision |
|---|---|---|
| 1 | `Order id` (col B) actually contains the Company name (KENSTAR, CLAD METAL, …). | **Do NOT rename in storage.** Internal logic maps `Order id → Company` at render. Keeps founders' raw-Excel intuition intact. |
| 2 | Raw file has no `Origin Region` or `Destination Region` columns. | Derive from pincode (via 22 K master), fall back to `State`. Persist as `_origin_zone` / `_destination_zone`. |
| 3 | No ODA pincode master file delivered yet. | Edit section is designed; pipeline returns `N/A` ODA / Expected TAT / SLA fields until the master is loaded. |
| 4 | Two "Remarks" columns (`Remarks` col V, `Additional Remarks` col AA) — design doc was ambiguous. | **Dedup tie-break uses `Remarks` (col V).** `Additional Remarks` is POD-audit text only, NOT used for dedup. |
| 5 | `Client` column is `kiirus b2bc` for every row. | Useless for grouping. Ignored. |
| 6 | Sample file has zero LRN duplicates (959 unique / 959 rows). | Dedup engine is forward-looking. Test with synthetic duplicates (`tests/test_dedup.py`). |
| 7 | `Invoice Zone` (B / D1 / D2 / E / F) is Delhivery's billing zone, not geographic. | Do NOT use for the 5×5 SLA lookup. Available as an optional display column only. |
| 8 | The Green/red/yellow demo file's `Status` text uses `"Early by N day(s)"` etc. | Storage uses clean 3-bucket `SLA Status` + signed `TAT Variance`. Human text rendered at display time. |
| 9 | The Green/red/yellow demo includes 99 "Not yet delivered" rows in its TAT table. | Design says TAT-tab is Delivered-only. Stick with design. Landing's Overall Delivery pie includes all shipments. |
| 10 | The demo TAT file shows 3 rows with `Expected TAT = 0`. | Artefact of the old logic (which used Delhivery's `Expected Date` minus Pickup Date). New logic uses the matrix; diagonal = 4. |
| 11 | `Manifest Date` looks like gibberish in Excel (`48:51.7`). | Cell number-format is `'mmss.0'` — Excel hides the date and shows only mm:ss.t. Underlying datetime is fine; pandas reads it correctly. Manifest Date is unused for SLA per design. |
| 12 | Percetaged_file aggregate columns omit Pending, RTO, SLA % combined, ODA %. | Customize's Aggregate view adds these four (§18.5). |
| 13 | The Green/red/yellow file has no actual cell fill colours despite the filename. | The colour scheme is implemented in the dashboard render (§16, §17), not parsed from the file. |
| 14 | Origin City is 958 Aurangabad / 1 Delhi. | Origin Zone is currently almost-constant (West). The Origin Zone filter in Customize is forward-looking for when Kiirus expands beyond Aurangabad. |
| 15 | Initial spec called for drag-resize panels (VS Code style). | Walked back to preset ratio buttons because Streamlit has no native drag-resize and custom components are fragile. |
| 16 | Initial spec called for SLA-status left-border row accent via `box-shadow: inset 3px 0 0 color`. | Walked back. Streamlit's `st.dataframe` is glide-data-grid React; doesn't render box-shadow reliably. Result was white bands over LRN cells. Now: pill styling on status columns only. |

---

## 27. Tests

Two test files, 22 tests, all passing.

### 27.1 `tests/test_dedup.py`

Tests the dedup engine in isolation (no DB needed — `pick_winner` and `merge_into_latest` are pure):

- `test_status_rank_table` — verifies the 6-entry rank dict
- `test_remarks_rank_keywords` — regex matches against real Delhivery strings
- `test_lifecycle_rank_wins` — Delivered beats In Transit
- `test_remarks_breaks_status_tie` — Out for Delivery beats Reached Hub
- `test_timestamp_breaks_status_and_remarks_tie` — newer Last Scan wins
- `test_regression_blocked` — uploading In Transit after Delivered is a no-op
- `test_merge_inserts_new_lrn` — fresh LRN → to_insert
- `test_merge_updates_when_new_wins` — existing Dispatched + incoming Delivered → to_update

### 27.2 `tests/test_sla.py`

Tests SLA computation. `get_live_matrix` is mocked with `@patch("app.pipeline.sla.get_live_matrix")` so the test doesn't need the DB.

- `test_actual_tat_basic` — 4-day delivery
- `test_actual_tat_same_day_pickup_and_delivery` — = 0
- `test_actual_tat_strips_time_across_midnight` — 23:55 → 00:05 = 1 day, NOT 0
- `test_actual_tat_none_if_not_delivered`
- `test_actual_tat_none_if_missing_date`
- `test_expected_tat_diagonal_no_oda` — West→West = 4
- `test_expected_tat_oda_adds_one` — base + 1 if ODA
- `test_expected_tat_unknown_oda_no_penalty` — UNKNOWN treated as NO
- `test_expected_tat_missing_zone` — None if either zone or matrix entry missing
- `test_classify_early / on_time / late / null_inputs`
- `test_same_day_delivery_is_early` — covers the diagonal-4 + actual-0 edge case

Run: `python -m pytest tests/ -q`.

---

## 28. Running locally

### 28.1 Install

```bash
cd /path/to/liirus
python -m pip install -r requirements.txt
```

### 28.2 Run

```bash
streamlit run streamlit_app.py
# or
python -m streamlit run streamlit_app.py --server.headless true --server.port 8501
```

Open `http://localhost:8501`.

### 28.3 On first run

- `init_db()` creates `kiirus.db` in the repo root.
- `seed_all_if_empty()` loads the 5×5 matrix from `app/reference/matrix.csv` into `sla_matrix_live` and seeds `state_zone_fallback` from `seed.py::STATE_ZONE`.
- `inject_global_css()` injects the theme stylesheet.
- The sidebar renders (defaulting to Landing).
- Landing shows "No data yet — open Upload from the header above to load a Delhivery file."
- Click `↑ Upload new file(s)` in the header → modal opens → drop in `Kiirus Automation file UPDATED (1).xlsx` → click `Process & Update` → dashboard refreshes with 959 rows.

### 28.4 Reset

```bash
rm kiirus.db   # wipes everything; next launch re-seeds matrix + state fallback
```

---

## 29. Deployment plan (stlite PWA)

This is the planned distribution path (not yet implemented):

1. **Pin Pyodide-compatible deps** — `pandas`, `openpyxl`, `plotly` all work under Pyodide. `streamlit-sortables` may need a JS-only fallback.
2. **Build stlite bundle** via `npx stlite-cli build .` (or equivalent). Produces a single static `index.html` + assets directory.
3. **Host the bundle** at a stable HTTPS URL (GitHub Pages, Cloudflare Pages, or a self-hosted nginx). HTTPS is mandatory for PWA install.
4. **Each device installs once** — open URL in Chrome / Edge / Safari → click "Install" in the address bar (desktop) or "Add to Home Screen" (mobile). App becomes a standalone icon.
5. After install, the app runs **fully offline forever** on that device (cached via service worker).
6. **Per-device data** — each install has its own browser-side SQLite (via `sql.js` or IndexedDB). Founders upload their own copy of the Delhivery file on each device they want to use; no cross-device sync (constraint #9).
7. Updates: re-deploy bundle → service worker detects new version → prompts refresh on next open.

The `manifest.json` is already present at the repo root, ready for PWA install. Icons at `icons/icon-192.png` and `icons/icon-512.png` need to be added.

---

## 30. Open items / known issues

### 30.1 Sidebar height jump between active / inactive nav rows

The active nav row is a styled `<div>` (markdown) with explicit `min-height: 56px`; inactive rows are `st.button` widgets with Streamlit's default padding. The CSS attempts to match via `[data-testid="stSidebar"] .stButton > button { min-height: 56px !important; padding: 10px 12px !important; ... }`. Match is close but not always pixel-perfect across Streamlit versions; a small layout shift on click can occur. **Workaround tried**: replace all 5 rows with HTML anchors (`<a href="?section=X">`) so dimensions are guaranteed identical. The user reverted to the button approach. If exact stability becomes critical, the HTML-anchor approach can be reinstated.

### 30.2 Light mode parity

The CSS is exhaustive and targets every Streamlit container including emotion-cache class patterns. Light mode flips:
- Page background, header, sidebar
- KPI cards (white bg, dark text)
- Plotly chart containers
- Tables, expanders, modals, dialogs, tabs, dropdowns, inputs, segmented controls, alerts
- Scrollbars

Edge case: any code that imports a backwards-compat constant directly (`from .theme import TEXT_PRIMARY`) will get the dark-mode value regardless of toggle. The chart components have been migrated to `t("text_primary")`. Any new component code should prefer `t()`.

### 30.3 Pincode master not loaded

Until the 22 K pincode file arrives, `_origin_zone` / `_destination_zone` / `_oda` / `_expected_tat_days` / `_tat_variance_days` / `_sla_status` are mostly NULL (origin_zone resolves via the hardcoded city map for Aurangabad/Delhi only; destination_zone falls back to state-zone). KPI cards show small counts for `Early/On Time/Late/SLA/ODA/Non-ODA`. The 22K-row file will trigger `recompute_all_sla()` once on first load (see §25).

### 30.4 Origin zone derivation

Currently `_ORIGIN_CITY_TO_ZONE = {"Aurangabad": "West", "Delhi": "North"}` in `sla.py`. Extend this dict as Kiirus adds origin cities. Alternative: derive from `Origin City` → look up state → state→zone fallback. Not yet implemented because Aurangabad covers 99.9% of current shipments.

### 30.5 Chart container hover lift may displace neighboring content

`[data-testid="stPlotlyChart"]:hover { transform: translateY(-1px); }` — minor reflow. Acceptable.

### 30.6 No `@st.cache_data` on heavy reads

`load_latest()` runs on every section render with no caching. For ~50 K rows it's fast enough; consider adding `@st.cache_data` (with proper TTL or version-bumping on upload) when the dataset grows.

### 30.7 No raw-archive drilldown UI

`store/queries.py::load_raw_for_lrn(lrn)` exists but is not surfaced anywhere in the UI. Future feature: an LRN inspector that shows every shipments_raw row for a given LRN and highlights which one won dedup.

### 30.8 Backups

The SQLite file is the entire app state. Recommend periodic `cp kiirus.db backups/kiirus-YYYY-MM-DD.db`. No automated backup in v1.

---

*End of context document. An LLM reading this file straight through has the complete picture: structure, data model, business logic, UI behaviour, design decisions, known issues. Refer to the README.md for the original product spec; this file documents the current implementation state.*
