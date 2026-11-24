from __future__ import annotations

from PySide6.QtCore import QEventLoop, QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import QProgressDialog

from .providers import Cancelled, ProviderError


class JobWorker(QThread):
    """Runs one AI job off the UI thread."""

    status = Signal(str)
    finished_ok = Signal(str)
    failed = Signal(str, bool)
    cancelled_sig = Signal()

    def __init__(self, provider, req, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.req = req
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            out = self.provider.run(self.req, self.status.emit, lambda: self._cancel)
            self.finished_ok.emit(out)
        except Cancelled:
            self.cancelled_sig.emit()
        except ProviderError as e:
            self.failed.emit(str(e), bool(e.retriable))
        except Exception as e:  # never let a thread crash the app
            self.failed.emit(f"Unexpected error: {e}", True)


class _FuncWorker(QThread):
    done = Signal(object, object)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn(), None)
        except Exception as e:
            self.done.emit(None, e)


class _Waiter(QObject):
    def __init__(self, loop, box):
        super().__init__()
        self.loop, self.box = loop, box

    @Slot(object, object)
    def got(self, result, err):
        self.box["r"], self.box["e"] = result, err
        self.loop.quit()


def run_blocking(parent, text: str, fn):
    """Run fn() in a thread while showing a busy dialog; re-raises its exception."""
    dlg = QProgressDialog(text, None, 0, 0, parent)
    dlg.setWindowModality(Qt.WindowModal)
    dlg.setMinimumDuration(0)
    dlg.setCancelButton(None)
    dlg.setWindowTitle("Cartoon AI")
    dlg.show()
    loop = QEventLoop()
    box: dict = {}
    waiter = _Waiter(loop, box)
    w = _FuncWorker(fn)
    w.done.connect(waiter.got, Qt.QueuedConnection)
    w.start()
    loop.exec()
    w.wait()
    dlg.close()
    if box.get("e") is not None:
        raise box["e"]
    return box.get("r")
