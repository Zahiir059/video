"""SQLite project history."""
from __future__ import annotations

import json
import sqlite3
import threading
import time

from .config import DATA_DIR


class Database:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.con = sqlite3.connect(str(DATA_DIR / "projects.db"), check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        with self.lock:
            self.con.execute("""CREATE TABLE IF NOT EXISTS projects(
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, created REAL,
                original_path TEXT, output_path TEXT, thumb_path TEXT, out_thumb_path TEXT,
                style TEXT, prompt TEXT, negative TEXT, provider TEXT, status TEXT,
                favorite INTEGER DEFAULT 0, error TEXT, params TEXT, kind TEXT DEFAULT 'ai')""")
            self.con.execute("UPDATE projects SET status='Interrupted' WHERE status='Processing'")
            self.con.commit()

    def add(self, **f) -> int:
        f.setdefault("created", time.time())
        if isinstance(f.get("params"), dict):
            f["params"] = json.dumps(f["params"])
        cols = ",".join(f)
        with self.lock:
            cur = self.con.execute(f"INSERT INTO projects({cols}) VALUES({','.join('?' * len(f))})",
                                   list(f.values()))
            self.con.commit()
            return int(cur.lastrowid)

    def update(self, pid: int, **f) -> None:
        if not f:
            return
        sets = ",".join(k + "=?" for k in f)
        with self.lock:
            self.con.execute(f"UPDATE projects SET {sets} WHERE id=?", list(f.values()) + [pid])
            self.con.commit()

    def get(self, pid: int):
        with self.lock:
            return self.con.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()

    def delete(self, pid: int) -> None:
        with self.lock:
            self.con.execute("DELETE FROM projects WHERE id=?", (pid,))
            self.con.commit()

    def list(self, search: str = "", favorites: bool = False, kind: str | None = None, limit: int = 500):
        q = "SELECT * FROM projects WHERE 1=1"
        a: list = []
        if search:
            q += " AND (name LIKE ? OR style LIKE ? OR prompt LIKE ?)"
            a += [f"%{search}%"] * 3
        if favorites:
            q += " AND favorite=1"
        if kind:
            q += " AND kind=?"
            a.append(kind)
        q += " ORDER BY created DESC LIMIT ?"
        a.append(limit)
        with self.lock:
            return self.con.execute(q, a).fetchall()

    def recent(self, n: int = 4):
        return self.list(limit=n)
