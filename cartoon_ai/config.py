"""Non-secret settings (JSON). API keys are NOT stored here, see secrets_store.py."""
from __future__ import annotations

import json

from . import paths

DEFAULTS = {
    "theme": "dark",
    "provider": "replicate",
    "model": "luma/modify-video",
    # Placeholders {video} {prompt} {mode} are filled in at run time.
    # Check the model's "API" tab on replicate.com and edit if field names differ.
    "template": '{"video": "{video}", "prompt": "{prompt}", "mode": "{mode}"}',
}


class Config:
    def __init__(self) -> None:
        self.data = dict(DEFAULTS)
        try:
            with open(paths.config_path(), "r", encoding="utf-8") as f:
                self.data.update(json.load(f))
        except Exception:
            pass

    def get(self, k: str):
        return self.data.get(k, DEFAULTS.get(k))

    def set(self, k: str, v) -> None:
        self.data[k] = v
        self.save()

    def save(self) -> None:
        try:
            paths.ensure()
            with open(paths.config_path(), "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass
