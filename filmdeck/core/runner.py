"""Running one interactive driver command.

One reader thread reads stdout and stderr as raw bytes (the driver's prompt has
no newline, so line-based reading would never see it), splits them into lines,
and reports a prompt as soon as it appears. Callbacks are called from that
thread; the GUI hands them over to its own thread.
"""

from __future__ import annotations

import codecs
import os
import re
import select
import signal
import subprocess
import threading
import time
from collections.abc import Callable

from .parser import REINSERT_MARKER

_SPLIT = re.compile(r"\r\n|\n|\r")
# Fallback for a changed prompt text: only something that clearly asks for Enter.
_ENTER_PROMPT = re.compile(r"\benter\b.*[:?]\s*$", re.IGNORECASE)


class ProcessRunner:
    def __init__(self, argv: list[str], env: dict, *,
                 on_line: Callable[[str, str], None] | None = None,
                 on_prompt: Callable[[str, str], None] | None = None,
                 idle_prompt_seconds: float = 3.0):
        self.argv = argv
        self.env = env
        self._on_line = self._guard(on_line)
        self._on_prompt = self._guard(on_prompt)
        self._idle = idle_prompt_seconds
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._lines: list[str] = []
        self._lock = threading.Lock()
        self.returncode: int | None = None

    @staticmethod
    def _guard(callback):
        """A callback that raises must not kill the reader thread: the driver would block on a full pipe."""
        def call(*args):
            if callback is None:
                return
            try:
                callback(*args)
            except Exception:
                pass
        return call

    # ------------------------------------------------------------------ control
    def start(self) -> None:
        self._proc = subprocess.Popen(self.argv, env=self.env, stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self._thread = threading.Thread(target=self._read_loop, name="driver-reader", daemon=True)
        self._thread.start()

    def send_enter(self) -> None:
        """Answer the pending prompt (the user has done what it asked)."""
        try:
            assert self._proc and self._proc.stdin
            self._proc.stdin.write(b"\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError, AssertionError):
            pass

    def interrupt(self) -> None:
        """Ctrl-C for the driver: it stops cleanly, marks the session failed and exits 130."""
        if self._proc and self._proc.poll() is None:
            self._proc.send_signal(signal.SIGINT)

    def kill(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.kill()

    def wait(self, timeout: float | None = None) -> int | None:
        """Exit code, or None if the process is still running after ``timeout``."""
        assert self._proc
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
        if self._thread:
            self._thread.join(timeout=5)
        self.returncode = self._proc.returncode
        return self.returncode

    @property
    def running(self) -> bool:
        return bool(self._proc) and self._proc.poll() is None

    def output(self) -> str:
        with self._lock:
            return "\n".join(self._lines)

    # ------------------------------------------------------------------ reading
    def _read_loop(self) -> None:
        assert self._proc and self._proc.stdout and self._proc.stderr
        streams = {self._proc.stdout.fileno(): "out", self._proc.stderr.fileno(): "err"}
        decoders = {fd: codecs.getincrementaldecoder("utf-8")(errors="replace") for fd in streams}
        partial = {fd: "" for fd in streams}
        last_activity = time.monotonic()
        open_fds = set(streams)
        while open_fds:
            ready, _, _ = select.select(list(open_fds), [], [], 0.25)
            for fd in ready:
                try:
                    data = os.read(fd, 65536)
                except OSError:
                    data = b""
                if not data:
                    open_fds.discard(fd)
                    tail = partial[fd] + decoders[fd].decode(b"", final=True)
                    partial[fd] = ""
                    if tail.strip():
                        self._emit(streams[fd], tail)
                    continue
                last_activity = time.monotonic()
                partial[fd] = self._feed(streams[fd], partial[fd] + decoders[fd].decode(data))
            self._check_prompt(partial, streams, last_activity)

    def _feed(self, stream: str, buffer: str) -> str:
        """Emit the complete lines of ``buffer``, return the unfinished rest.

        Empty lines are dropped, so a ``\\r\\n`` split across two reads is harmless.
        """
        *complete, rest = _SPLIT.split(buffer)
        for line in complete:
            if line.strip():
                self._emit(stream, line)
        return rest

    def _emit(self, stream: str, line: str) -> None:
        line = line.rstrip()
        with self._lock:
            self._lines.append(line)
        if REINSERT_MARKER in line:
            self._on_prompt("reinsert", line)
        self._on_line(stream, line)

    def _check_prompt(self, partial: dict, streams: dict, last_activity: float) -> None:
        """Look at the unfinished stdout line: a prompt waits there, it has no newline.

        A detected prompt is removed from ``partial`` so it is reported once; the
        driver prints nothing more until it gets its answer.
        """
        for fd, text in partial.items():
            if streams[fd] != "out" or not text:
                continue
            if REINSERT_MARKER in text:
                partial[fd] = ""
                self._on_prompt("reinsert", text.strip())
            elif (self._idle and time.monotonic() - last_activity >= self._idle
                  and _ENTER_PROMPT.search(text)):
                partial[fd] = ""
                self._on_prompt("unknown", text.strip())
