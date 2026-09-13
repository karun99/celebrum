"""SQLite storage layer for Celebrum.

The Memory Graph is a neuron/synapse graph database (inspired by the 
Neural Research OS / OI neuron graph and PGMem's heterogeneous graph):
nodes are *neurons* (facts, preferences, decisions, milestones, identity,
value, trait, persona signals), edges are *synapses* (typed relationships
such as related_to, contradicts, supports, evidence_for, led_to, knows).

Schema
------
nodes(node_id, kind, content, source, ts, confidence, meta)
edges(src, dst, rel, weight, ts)                     -- synapse
meta(key, value)                                     -- persona, guardrails, ptm, snapshots
audit(seq, ts, actor, action, risk, details, result) -- append-only truth/action log
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes(
    node_id   TEXT PRIMARY KEY,
    kind      TEXT NOT NULL,
    content   TEXT NOT NULL,
    source    TEXT,
    ts        TEXT,
    confidence REAL DEFAULT 0.5,
    meta      TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS edges(
    src     TEXT NOT NULL,
    dst     TEXT NOT NULL,
    rel     TEXT NOT NULL,
    weight  REAL DEFAULT 1.0,
    ts      TEXT,
    PRIMARY KEY(src, dst, rel)
);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);
CREATE TABLE IF NOT EXISTS meta(
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS audit(
    seq       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT,
    actor     TEXT,
    action    TEXT,
    risk      TEXT,
    details   TEXT,
    result    TEXT
);
"""


class Store:
    """Thread-safe sqlite3 wrapper with schema bootstrapping."""

    def __init__(self, path: str):
        self.path = str(path)
        os.makedirs(os.path.dirname(os.path.abspath(self.path)) or ".", exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self._lock:
            # WAL + NORMAL: durable enough for a local brain, avoids fsync stalls.
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    # ---- nodes -----------------------------------------------------------
    def add_node(self, node_id, kind, content, source=None, ts=None,
                 confidence=0.5, meta=None) -> None:
        if ts is None:
            ts = now_iso()
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO nodes(node_id,kind,content,source,ts,confidence,meta) "
                "VALUES(?,?,?,?,?,?,?)",
                (node_id, kind, content, source, ts, float(confidence),
                 json.dumps(meta or {}, ensure_ascii=False)),
            )
            self.conn.commit()

    def get_node(self, node_id):
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM nodes WHERE node_id=?", (node_id,)).fetchone()

    def delete_node(self, node_id) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM nodes WHERE node_id=?", (node_id,))
            self.conn.execute("DELETE FROM edges WHERE src=? OR dst=?", (node_id, node_id))
            self.conn.commit()

    def delete_all(self) -> int:
        with self._lock:
            c1 = self.conn.execute("DELETE FROM nodes").rowcount
            self.conn.execute("DELETE FROM edges")
            self.conn.commit()
            return c1

    def all_nodes(self):
        with self._lock:
            return self.conn.execute("SELECT * FROM nodes").fetchall()

    def bulk_add_nodes(self, rows) -> None:
        """Single-transaction insert for bulk seeding/perf benches.

        rows: iterable of (node_id, kind, content, source, ts, confidence, meta_json)
        """
        with self._lock:
            self.conn.executemany(
                "INSERT OR REPLACE INTO nodes(node_id,kind,content,source,ts,confidence,meta) "
                "VALUES(?,?,?,?,?,?,?)", rows)
            self.conn.commit()

    def bulk_add_edges(self, rows) -> None:
        with self._lock:
            self.conn.executemany(
                "INSERT OR REPLACE INTO edges(src,dst,rel,weight,ts) VALUES(?,?,?,?,?)", rows)
            self.conn.commit()

    def count_nodes(self) -> int:
        with self._lock:
            return self.conn.execute("SELECT COUNT(*) c FROM nodes").fetchone()["c"]

    def count_by_kind(self):
        with self._lock:
            rows = self.conn.execute(
                "SELECT kind, COUNT(*) c FROM nodes GROUP BY kind").fetchall()
        return {r["kind"]: r["c"] for r in rows}

    # ---- edges (synapses) -------------------------------------------------
    def add_edge(self, src, dst, rel, weight=1.0, ts=None) -> None:
        if ts is None:
            ts = now_iso()
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO edges(src,dst,rel,weight,ts) VALUES(?,?,?,?,?)",
                (src, dst, rel, float(weight), ts),
            )
            self.conn.commit()

    def edges_for(self, node_id, direction="both"):
        with self._lock:
            if direction in ("out", "both"):
                rows = self.conn.execute(
                    "SELECT src,dst,rel,weight,ts FROM edges WHERE src=?", (node_id,)).fetchall()
                for r in rows:
                    yield r
            if direction in ("in", "both"):
                rows = self.conn.execute(
                    "SELECT src,dst,rel,weight,ts FROM edges WHERE dst=?", (node_id,)).fetchall()
                for r in rows:
                    yield r

    def all_edges(self):
        with self._lock:
            return self.conn.execute("SELECT * FROM edges").fetchall()

    def contradiction_edges(self):
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM edges WHERE rel='contradicts'").fetchall()

    # ---- meta ------------------------------------------------------------
    def get_meta(self, key, default=None):
        with self._lock:
            row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (TypeError, ValueError):
            return row["value"]

    def set_meta(self, key, value) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                (key, json.dumps(value, ensure_ascii=False)),
            )
            self.conn.commit()

    # ---- audit ------------------------------------------------------------
    def log(self, actor, action, risk="low", details=None, result="ok") -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO audit(ts,actor,action,risk,details,result) VALUES(?,?,?,?,?,?)",
                (now_iso(), actor, action, risk,
                 json.dumps(details or {}, ensure_ascii=False), result),
            )
            self.conn.commit()

    def audit_tail(self, n=50):
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM audit ORDER BY seq DESC LIMIT ?", (n,)).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        with self._lock:
            self.conn.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass