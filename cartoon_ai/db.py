"""SQLite project history (local only)."""
from __future__ import annotations

import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    style TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Draft',
    original_path TEXT NOT NULL DEFAULT '',
    output_path TEXT NOT NULL DEFAULT '',
    thumb_path TEXT NOT NULL DEFAULT '',
    favorite INTEGER NOT NULL DEFAULT 0,
    provider TEXT NOT NULL DEFAULT '',
    is_demo INTEGER NOT NULL DEFAULT 0,
    prompt TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT '',
    created REAL NOT NULL
);
"""


class Database:
    def __init__(self, path) -> None:
        self.con = sqlite3.connect(str(path))
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        self.con.commit()

    def mark_interrupted(self) -> None:
        self.con.execute("UPDATE projects SET status='Interrupted' WHERE status='Processing'")
        self.con.commit()

    def add(self, **kw) -> int:
        kw.setdefault("created", time.time())
        cols = ",".join(kw)
        q = ",".join("?" for _ in kw)
        cur = self.con.execute(f"INSERT INTO projects ({cols}) VALUES ({q})", list(kw.values()))
        self.con.commit()
        return int(cur.lastrowid)

    def update(self, pid: int, **kw) -> None:
        if not kw:
            return
        sets = ",".join(f"{k}=?" for k in kw)
        self.con.execute(f"UPDATE projects SET {sets} WHERE id=?", [*kw.values(), pid])
        self.con.commit()

    def delete(self, pid: int) -> None:
        self.con.execute("DELETE FROM projects WHERE id=?", (pid,))
        self.con.commit()

    def get(self, pid: int):
        return self.con.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()

    def list(self, search: str = "", flt: str = "All", limit: int = 500):
        where, args = [], []
        if search.strip():
            where.append("(name LIKE ? OR style LIKE ?)")
            s = f"%{search.strip()}%"
            args += [s, s]
        if flt == "Favorites":
            where.append("favorite=1")
        elif flt == "Generated":
            where.append("output_path<>''")
        elif flt == "Originals":
            where.append("original_path<>''")
        sql = "SELECT * FROM projects"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created DESC LIMIT ?"
        return self.con.execute(sql, [*args, limit]).fetchall()
