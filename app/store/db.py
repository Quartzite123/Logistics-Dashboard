"""SQLite database layer.

Schema overview:
    shipments_raw            — append-only audit archive of every uploaded row
    shipments_latest         — one row per LRN, dedup-winner, + stored derived SLA cols
    sla_matrix_live          — current 5×5 matrix used by uploads
    sla_matrix_draft         — staged edits before Apply
    pincode_master_live      — current 22 K pincode → zone + ODA master
    pincode_master_draft     — staged edits before Apply
"""
from __future__ import annotations

import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

from .schema import (
    RAW_COLUMNS,
    DERIVED_COLUMNS,
    DB_COL,
    sqlite_type,
)

# Under stlite / Pyodide (sys.platform == "emscripten") the filesystem is
# virtual and resets on reload. We mount Pyodide's IDBFS at /persist and keep
# the SQLite DB there so it survives app closes on phone/desktop. syncfs(True)
# loads previously persisted data on startup; syncfs(False) flushes writes back
# to IndexedDB after commits.
_IDBFS_MOUNTED = False


def _mount_idbfs() -> None:
    """Mount Pyodide's IDBFS for persistent storage (no-op outside WASM)."""
    global _IDBFS_MOUNTED
    if _IDBFS_MOUNTED or sys.platform != "emscripten":
        return
    try:
        import pyodide_js

        try:
            pyodide_js.FS.mkdir("/persist")
        except Exception:
            pass  # directory already exists
        pyodide_js.FS.mount(pyodide_js.FS.filesystems.IDBFS, {}, "/persist")

        # Load any previously persisted data from IndexedDB (syncfs(True)).
        loaded = False

        def _cb(err):
            nonlocal loaded
            loaded = True

        pyodide_js.FS.syncfs(True, _cb)
        import time
        for _ in range(50):
            if loaded:
                break
            time.sleep(0.1)
        _IDBFS_MOUNTED = True
    except Exception as e:  # pragma: no cover - WASM-only path
        print(f"IDBFS mount failed, falling back to MEMFS: {e}")


if sys.platform == "emscripten":
    _mount_idbfs()
    DB_PATH = Path("/persist/kiirus.db") if _IDBFS_MOUNTED else Path("/kiirus.db")
else:
    DB_PATH = Path(__file__).resolve().parent.parent.parent / "kiirus.db"


def sync_to_idb() -> None:
    """Flush filesystem writes back to IndexedDB. Called after write commits."""
    if sys.platform != "emscripten" or not _IDBFS_MOUNTED:
        return
    try:
        import pyodide_js
        pyodide_js.FS.syncfs(False, lambda err: None)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# connection management
# ---------------------------------------------------------------------------

def get_conn() -> sqlite3.Connection:
    """Return a SQLite connection with sensible defaults."""
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    # WAL's -wal/-shm sidecar files don't sync cleanly through IDBFS, so use the
    # single-file DELETE journal under Pyodide; keep WAL everywhere else.
    if sys.platform == "emscripten":
        conn.execute("PRAGMA journal_mode=DELETE;")
    else:
        conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def cursor():
    """Context manager that yields a cursor and commits/rolls back on exit."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
        sync_to_idb()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# schema creation
# ---------------------------------------------------------------------------

def _raw_columns_ddl() -> str:
    """DDL fragment for the 41 raw columns + provenance columns."""
    pieces = []
    for col in RAW_COLUMNS:
        pieces.append(f'  "{DB_COL[col]}" {sqlite_type(col)}')
    return ",\n".join(pieces)


def _derived_columns_ddl() -> str:
    """DDL fragment for the 7 derived SLA columns."""
    types = {
        "_origin_zone": "TEXT",
        "_destination_zone": "TEXT",
        "_oda": "TEXT",                  # 'YES' | 'NO' | 'UNKNOWN'
        "_expected_tat_days": "INTEGER",
        "_actual_tat_days": "INTEGER",
        "_tat_variance_days": "INTEGER",
        "_sla_status": "TEXT",           # 'Early' | 'On Time' | 'Late' | NULL
    }
    pieces = [f'  "{c}" {types[c]}' for c in DERIVED_COLUMNS]
    return ",\n".join(pieces)


SCHEMA_SQL = f"""
-- ---- shipments_raw: every uploaded row, audit archive ----------------------
CREATE TABLE IF NOT EXISTS shipments_raw (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    _upload_batch_id  TEXT    NOT NULL,
    _upload_filename  TEXT    NOT NULL,
    _uploaded_at      TEXT    NOT NULL,
{_raw_columns_ddl()}
);
CREATE INDEX IF NOT EXISTS idx_raw_lrn ON shipments_raw(lrn);
CREATE INDEX IF NOT EXISTS idx_raw_batch ON shipments_raw(_upload_batch_id);

-- ---- shipments_latest: one row per LRN, dedup-winner, with derived SLA ----
CREATE TABLE IF NOT EXISTS shipments_latest (
{_raw_columns_ddl()},
{_derived_columns_ddl()},
    _source_raw_id    INTEGER REFERENCES shipments_raw(id),
    _updated_at       TEXT    NOT NULL,
    PRIMARY KEY (lrn)
);
CREATE INDEX IF NOT EXISTS idx_latest_status     ON shipments_latest(current_status);
CREATE INDEX IF NOT EXISTS idx_latest_pickup     ON shipments_latest(pickup_date);
CREATE INDEX IF NOT EXISTS idx_latest_company    ON shipments_latest(order_id);
CREATE INDEX IF NOT EXISTS idx_latest_sla_status ON shipments_latest(_sla_status);

-- ---- 5x5 SLA matrix (live + draft) ----------------------------------------
CREATE TABLE IF NOT EXISTS sla_matrix_live (
    origin_zone      TEXT NOT NULL,
    destination_zone TEXT NOT NULL,
    days             INTEGER NOT NULL,
    PRIMARY KEY (origin_zone, destination_zone)
);
CREATE TABLE IF NOT EXISTS sla_matrix_draft (
    origin_zone      TEXT NOT NULL,
    destination_zone TEXT NOT NULL,
    days             INTEGER NOT NULL,
    PRIMARY KEY (origin_zone, destination_zone)
);

-- ---- Pincode master (live + draft) ----------------------------------------
-- One row per pincode. ODA flag drives Expected TAT adjustment.
CREATE TABLE IF NOT EXISTS pincode_master_live (
    pincode TEXT PRIMARY KEY,
    city    TEXT,
    state   TEXT,
    zone    TEXT NOT NULL,
    oda     TEXT NOT NULL CHECK (oda IN ('YES', 'NO'))
);
CREATE TABLE IF NOT EXISTS pincode_master_draft (
    pincode TEXT PRIMARY KEY,
    city    TEXT,
    state   TEXT,
    zone    TEXT NOT NULL,
    oda     TEXT NOT NULL CHECK (oda IN ('YES', 'NO'))
);
CREATE INDEX IF NOT EXISTS idx_pincode_city ON pincode_master_live(city);

-- ---- State → Zone fallback (built into seed; used when pincode is unknown)
CREATE TABLE IF NOT EXISTS state_zone_fallback (
    state TEXT PRIMARY KEY,
    zone  TEXT NOT NULL
);

-- ---- Upload history (small) -----------------------------------------------
CREATE TABLE IF NOT EXISTS uploads (
    batch_id   TEXT PRIMARY KEY,
    filename   TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    rows_in    INTEGER NOT NULL,
    rows_new   INTEGER NOT NULL,
    rows_updated INTEGER NOT NULL,
    rows_skipped INTEGER NOT NULL
);

-- ---- Origin city recents (fast-path cache for origin_lookup) --------------
CREATE TABLE IF NOT EXISTS origin_recents (
    city_name  TEXT PRIMARY KEY,
    state      TEXT NOT NULL,
    zone       TEXT NOT NULL,
    last_seen  TEXT NOT NULL,
    seen_count INTEGER NOT NULL DEFAULT 1
);
"""


def init_db() -> None:
    """Create all tables if they do not exist. Safe to call repeatedly."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with cursor() as cur:
        cur.executescript(SCHEMA_SQL)


def reset_db() -> None:
    """Delete the SQLite file. Useful during development."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()
