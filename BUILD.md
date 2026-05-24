# Kiirus Xpress dashboard — build & run notes

Reference implementation of the spec in [README.md](./README.md).

## Run locally for development

Requires Python 3.11–3.13 and `pip`.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open the URL printed by Streamlit (typically http://localhost:8501).

On first launch the app creates `kiirus.db` (SQLite, single file) in the
project root and seeds the 5×5 region matrix from
[app/reference/matrix.csv](./app/reference/matrix.csv) plus the bundled
state→zone fallback (Indian states → 5 zones).

## Try it with the sample data

The repo ships with the sample Delhivery file
`Kiirus Automation file UPDATED (1).xlsx`. From the running app:

1. Open the **Landing** section.
2. Drag the .xlsx into the upload panel on the left.
3. Click **Process & Update**.
4. KPI cards populate; switch sections via the left sidebar.

## Run the tests

```bash
pytest tests/ -v
```

22 tests cover the dedup tie-break ladder and the SLA / TAT formulas.

## Project layout

```
liirus/
├── README.md              ← full spec / hand-off doc
├── BUILD.md               ← this file
├── requirements.txt
├── streamlit_app.py       ← top-level entry point used by `streamlit run`
├── manifest.json          ← PWA manifest
├── stlite/                ← static-bundle entry for browser-only deployment
│   ├── index.html
│   └── sw.js              ← service worker for offline PWA
├── app/
│   ├── main.py            ← sidebar nav + page routing
│   ├── pipeline/          ← ingest, dedup, zones, oda, sla
│   ├── store/             ← SQLite schema + seed + queries
│   ├── components/        ← layout, kpi_cards, chart_pair, chart_heatmap,
│   │                        data_table, modals
│   ├── sections/          ← landing, tat, transit, customize, edit
│   └── reference/
│       └── matrix.csv     ← bundled 5×5 SLA matrix
├── tests/                 ← pytest unit tests (dedup + sla)
└── Kiirus Automation file UPDATED (1).xlsx   ← sample input
```

## Deploy as a PWA (the recommended path)

The README's recommended distribution path is to package the app as a
[stlite](https://stlite.net) bundle and host it as static files. After a
one-time browser visit, the PWA installs to the desktop / phone home screen
and runs fully offline.

The [stlite/index.html](./stlite/index.html) file is the bundle entry point.
To test locally:

```bash
# from the project root
python -m http.server 8000
# then open http://localhost:8000/stlite/
```

For a real deployment, push the entire repo (or a curated subset of
`stlite/`, `app/`, `manifest.json`) to any HTTPS static host:

- **GitHub Pages** — push to a repo, enable Pages.
- **Cloudflare Pages** — connect repo, no build command.
- **nginx on a VPS** — serve the folder.

Founders then visit the URL once on each device:

- **Desktop (Chrome/Edge)** — click the "Install" icon in the address bar.
- **Phone (Chrome/Safari)** — tap "Add to Home Screen" / "Install app".

After install, the app icon appears as a native app and works without any
network connection.

## Why not PyInstaller / Docker?

Both were considered (README §3.4) and rejected:

- **PyInstaller** can produce a single Windows `.exe` of ~200–300 MB, but
  Streamlit's PyInstaller support is fragile (custom hooks needed for
  `streamlit/static`, `streamlit/runtime`, vega/altair schemas), and it
  doesn't solve mobile.
- **Docker** requires Docker Desktop on the founder's laptop (WSL2 + ~3 GB
  idle RAM + license check). Not "no friction" for a non-technical user.

The stlite PWA path beats both on distribution friction *and* mobile reach.

## Notes for future implementers

- **Forward-only retroactivity** (README §16.7, §19): Edits to the matrix or
  pincode master do NOT recompute SLA for past shipments. The only exception
  is the *first* pincode-master load, which calls `recompute_all_sla()` to
  back-fill historical rows that were N/A before.
- **Derived SLA columns are stored, not computed** at render. They live as
  physical columns on `shipments_latest` (`_origin_zone`, `_destination_zone`,
  `_oda`, `_expected_tat_days`, `_actual_tat_days`, `_tat_variance_days`,
  `_sla_status`).
- **`Days in Transit` and `Stuck`** are computed live (today − Pickup Date)
  but use the *stored* `_expected_tat_days` for the Stuck threshold, so
  matrix edits don't change the Stuck flag of already-loaded shipments.
- **Column names**: stored as snake_case in SQLite (e.g. `order_id`), mapped
  back to display labels (e.g. `Order id`) at query time via the
  `DB_COL` / `DISPLAY_COL` dicts in `app/store/schema.py`.
- **Pincode editor** never renders all 22 K rows. Search-by-pincode-or-city
  surfaces ≤200 matching rows; bulk re-upload replaces the master in one shot.
