"""Tiny SQLite store so we only alert once per posting."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "seen.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute(
        "CREATE TABLE IF NOT EXISTS seen ("
        " site TEXT, job_id TEXT, first_seen TEXT DEFAULT CURRENT_TIMESTAMP,"
        " PRIMARY KEY (site, job_id))"
    )
    return c


def filter_new(jobs):
    """Return only jobs we haven't recorded before, and record them."""
    fresh = []
    with _conn() as c:
        for j in jobs:
            cur = c.execute(
                "SELECT 1 FROM seen WHERE site=? AND job_id=?", (j.site, j.job_id)
            )
            if cur.fetchone() is None:
                c.execute(
                    "INSERT INTO seen (site, job_id) VALUES (?, ?)",
                    (j.site, j.job_id),
                )
                fresh.append(j)
    return fresh
