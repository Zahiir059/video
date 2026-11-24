"""Background workers so the UI never freezes."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from .providers import ProviderError


class GenerateWorker(QThread):
    progress = Signal(int, str)
    succeeded = Signal(str)
    failed = Signal(str, bool)

    def __init__(self, provider, video, style, prompt, negative, params, parent=None):
        super().__init__(parent)
        self.provider, self.video, self.style = provider, video, style
        self.prompt, self.negative, self.params = prompt, negative, params
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            path = self.provider.generate(self.video, self.style, self.prompt, self.negative, self.params,
                                          lambda p, m: self.progress.emit(p, m), lambda: self._cancel)
            self.succeeded.emit(path)
        except ProviderError as e:
            self.failed.emit(str(e), e.retryable)
        except Exception as e:  # never let a thread crash the app
            self.failed.emit("Unexpected error: " + str(e), False)


class FuncWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, parent=None):
        super().__init__(parent)
        self.fn, self.args = fn, args

    def run(self) -> None:
        try:
            self.done.emit(self.fn(*self.args))
        except Exception as e:
            self.failed.emit(str(e))
