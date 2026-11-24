"""Paths, limits, settings and secure API-key storage."""
from __future__ import annotations

import atexit
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

APP_NAME = "Cartoon AI"
APP_VERSION = "1.0.0"
MAX_SECONDS = 10.0          # strict AI limit
MAX_FILE_MB = 300
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".wmv", ".flv", ".mpg", ".mpeg", ".3gp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma"}
KEY_SERVICE = "CartoonAI"
DEFAULT_MODEL = "philz1337x/video-style-transfer"


def _base() -> Path:
    override = os.environ.get("CARTOONAI_DATA")
    if override:
        return Path(override)
    if sys.platform == "win32":
        root = os.environ.get("APPDATA") or str(Path.home())
    else:
        root = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(root) / "CartoonAI"


DATA_DIR = _base()
LIB_DIR = DATA_DIR / "library"
for _sub in ("originals", "outputs", "thumbs", "edits", "exports"):
    (LIB_DIR / _sub).mkdir(parents=True, exist_ok=True)

TMP_DIR = Path(tempfile.mkdtemp(prefix="cartoonai_"))


@atexit.register
def _cleanup_tmp() -> None:
    shutil.rmtree(TMP_DIR, ignore_errors=True)


class Settings:
    DEFAULTS = {
        "theme": "dark",
        "style": "anime",
        "model": DEFAULT_MODEL,
        "force_demo": False,
        "last_dir": str(Path.home()),
    }

    def __init__(self) -> None:
        self.path = DATA_DIR / "settings.json"
        self.data = dict(self.DEFAULTS)
        try:
            self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
        except Exception:
            pass

    def get(self, key, default=None):
        return self.data.get(key, self.DEFAULTS.get(key, default))

    def set(self, key, value) -> None:
        self.data[key] = value
        try:
            self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except Exception:
            pass


# ---- API key: Windows Credential Manager (never written to disk by us) ----------
def _keyring():
    import keyring
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring
        return WinVaultKeyring()
    return keyring.get_keyring()


def get_api_key() -> str:
    try:
        key = _keyring().get_password(KEY_SERVICE, "replicate")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("REPLICATE_API_TOKEN", "").strip()


def set_api_key(key: str) -> tuple[bool, str]:
    try:
        _keyring().set_password(KEY_SERVICE, "replicate", key.strip())
        return True, "API key saved in Windows Credential Manager."
    except Exception as e:  # no keyring backend etc.
        return False, ("Could not store the key securely (" + str(e) + "). "
                       "You can set the REPLICATE_API_TOKEN environment variable instead.")


def delete_api_key() -> None:
    try:
        _keyring().delete_password(KEY_SERVICE, "replicate")
    except Exception:
        pass
