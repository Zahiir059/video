"""Provider interface. Only controls a provider really supports are listed in `capabilities`;
the Studio screen builds its widgets from that list (no fake controls)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


class ProviderError(Exception):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


@dataclass
class Capability:
    key: str
    label: str
    kind: str                         # "slider" | "int" | "choice"
    default: float | int = 0
    minimum: float = 0
    maximum: float = 1
    step: float = 1
    choices: list = field(default_factory=list)   # [(label, value)]
    help: str = ""


ProgressFn = Callable[[int, str], None]      # percent (-1 = unknown), message


class Provider:
    id = "base"
    name = "Base"
    is_demo = False
    supports_prompt = True
    supports_negative = True
    capabilities: list[Capability] = []
    description = ""

    def configured(self) -> bool:
        return True

    def test_connection(self) -> str:
        return "OK"

    def generate(self, video: str, style, prompt: str, negative: str, params: dict,
                 report: ProgressFn, cancelled: Callable[[], bool]) -> str:
        """Return the path of the generated video. Raise ProviderError on failure."""
        raise NotImplementedError
