"""Where Cartoon AI keeps its files. Nothing is written outside this folder."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def data_dir() -> Path:
    env = os.environ.get("CARTOON_DATA")
    if env:
        p = Path(env)
    elif os.name == "nt":
        p = Path(os.environ.get("APPDATA", str(Path.home()))) / "CartoonAI"
    else:
        p = Path.home() / ".cartoon_ai"
    return p


def videos_dir() -> Path:
    return data_dir() / "videos"


def thumbs_dir() -> Path:
    return data_dir() / "thumbs"


def work_dir() -> Path:
    """Temporary files. Emptied at start and exit."""
    return Path(tempfile.gettempdir()) / "CartoonAI_work"


def db_path() -> Path:
    return data_dir() / "projects.db"


def config_path() -> Path:
    return data_dir() / "config.json"


def ensure() -> None:
    for d in (data_dir(), videos_dir(), thumbs_dir(), work_dir()):
        d.mkdir(parents=True, exist_ok=True)


def clear_work() -> None:
    d = work_dir()
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)


def work_file(name: str) -> str:
    work_dir().mkdir(parents=True, exist_ok=True)
    return str(work_dir() / name)
