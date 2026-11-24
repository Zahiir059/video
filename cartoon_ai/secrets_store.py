"""API keys live in the operating system's secure store (Windows Credential Manager),
never in a file and never in the source code."""
from __future__ import annotations

import os

SERVICE = "CartoonAI"
ENV_NAMES = {"replicate": "REPLICATE_API_TOKEN"}


class SecretError(Exception):
    pass


def get_key(provider: str) -> str | None:
    v = None
    try:
        import keyring

        v = keyring.get_password(SERVICE, provider)
    except Exception:
        v = None
    if v:
        return v.strip()
    env = os.environ.get(ENV_NAMES.get(provider, ""), "")
    return env.strip() or None


def set_key(provider: str, value: str) -> None:
    try:
        import keyring

        keyring.set_password(SERVICE, provider, value.strip())
    except Exception as e:
        raise SecretError(f"Could not save the key in the system secure store: {e}")


def delete_key(provider: str) -> None:
    try:
        import keyring

        keyring.delete_password(SERVICE, provider)
    except Exception:
        pass
