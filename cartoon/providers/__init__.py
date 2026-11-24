from __future__ import annotations

from ..config import DEFAULT_MODEL, Settings, get_api_key
from .base import Capability, Provider, ProviderError
from .demo import DemoProvider
from .replicate import ReplicateProvider

__all__ = ["Capability", "Provider", "ProviderError", "make_provider"]


def make_provider(settings: Settings) -> Provider:
    """Add a new service by writing a Provider subclass and returning it here."""
    key = get_api_key()
    if key and not settings.get("force_demo", False):
        return ReplicateProvider(key, settings.get("model", DEFAULT_MODEL) or DEFAULT_MODEL)
    return DemoProvider()
