"""Getting results from worker threads into the GUI thread.

The scan session, the update check and the other slow jobs run in threads. A
Qt signal emitted from such a thread and received by an object that lives in
the GUI thread is delivered in the GUI thread, which is all this module relies on.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class SessionBridge(QObject):
    """Hand a ScanSession's events to the GUI thread: ``session = ScanSession(..., bridge.emit)``."""

    event = Signal(object)

    def emit(self, ev) -> None:
        self.event.emit(ev)


class _Signals(QObject):
    done = Signal(object, object)       # result, exception
    progress = Signal(int, int)


class _Job(QRunnable):
    def __init__(self, fn: Callable, signals: _Signals, with_progress: bool):
        super().__init__()
        self._fn, self._signals, self._with_progress = fn, signals, with_progress

    def run(self) -> None:
        try:
            if self._with_progress:
                result = self._fn(self._signals.progress.emit)
            else:
                result = self._fn()
        except Exception as e:  # reported to the GUI, never lost
            self._signals.done.emit(None, e)
        else:
            self._signals.done.emit(result, None)


def run_async(parent: QObject, fn: Callable, on_done: Callable[[object, Exception | None], None],
              on_progress: Callable[[int, int], None] | None = None) -> None:
    """Run ``fn`` in the thread pool; ``on_done(result, error)`` runs in the GUI thread.

    With ``on_progress`` given, ``fn`` is called with a ``progress(done, total)`` callable.
    """
    signals = _Signals(parent)

    def finish(result, error):
        signals.deleteLater()
        on_done(result, error)

    signals.done.connect(finish)
    if on_progress is not None:
        signals.progress.connect(on_progress)
    QThreadPool.globalInstance().start(_Job(fn, signals, on_progress is not None))
