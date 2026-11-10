"""One scan session: everything behind the Start button.

The flow runs in its own thread and talks to the GUI through one callback that
receives ``Event`` objects (the GUI hands them over to its own thread). It
holds the rules that keep the scanner safe:

* a single driver process at a time, the scanner is checked read-only first;
* an abort is Ctrl-C (SIGINT) for the driver, never a kill, and always ends
  with "power-cycle the scanner";
* the driver's own files are never moved or deleted (see ``exporter``).

Events: state, strip_started, progress, frame_written, log, prompt (prompt_kind, text),
exported, ask_next, strip_done, finished.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import driver as drv
from . import exporter, paths
from .config import Settings
from .margins import MarginTracker, OffsetAdvice
from .parser import ScannerStatus, classify_failure, classify_line, parse_status
from .runner import ProcessRunner

STRIP_MODE = "strip"
FILM_MODE = "film"
FRAMES_PER_STRIP = 6
LOG_KEEP = 20
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    kind: str
    data: dict = field(default_factory=dict)


@dataclass
class SessionResult:
    kind: str                       # ok | partial | error | cancelled
    code: str = ""                  # error code, see classify_failure (+ driver_old, no_space, no_write, export_failed, internal)
    detail: str = ""                # last lines of the driver output, for the details box
    power_cycle: bool = False       # the scanner must be switched off and on before the next scan
    images_total: int = 0           # delivered images in the film folder
    images_new: int = 0             # added by this session
    missing: list[int] = field(default_factory=list)
    missing_details: list[exporter.MissingImage] = field(default_factory=list)   # number, the driver's reason, full scan
    offset_advice: OffsetAdvice | None = None   # measured from the driver's margins, see core/margins.py
    strips: int = 0
    final_dir: Path | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class _Outcome:
    kind: str                       # ok | partial | error | cancelled
    rc: int = 0
    code: str = ""
    power_cycle: bool = False
    output: str = ""


def check_scanner(driver: drv.Driver) -> ScannerStatus:
    """Read-only look at the scanner (``of135i status``). Never call while a session runs."""
    rc, out, err = drv.run_short(driver, drv.status_argv(), 30.0)
    status = parse_status(rc, out, err)
    log.info("scanner check: rc=%s ok=%s error=%r\n%s", rc, status.ok, status.error, _tail((out + "\n" + err).strip()))
    return status


@dataclass
class EjectResult:
    ok: bool
    code: str = ""
    detail: str = ""
    power_cycle: bool = False


def eject_holder(driver: drv.Driver, *, runner_cls=ProcessRunner, timeout: float = 300.0) -> EjectResult:
    """``of135i eject`` for the "holder is stuck" case. Never call while a session runs.

    The driver decides whether it may eject (it refuses an unsafe start state itself and does a cold
    initialisation first after a power cycle). A process that does not end within ``timeout`` gets Ctrl-C,
    never a kill, and the answer is "power-cycle the scanner".
    """
    runner = runner_cls(drv.eject_argv(), drv.environment(driver))
    log.info("eject: $ %s", " ".join(drv.eject_argv()))
    try:
        runner.start()
    except OSError as e:
        log.error("eject: cannot start the driver: %s", e)
        return EjectResult(False, "internal", f"cannot start the driver: {e}")
    rc = runner.wait(timeout)
    if rc is None:
        runner.interrupt()
        runner.wait(60.0)
        log.error("eject: no end after %.0f s, sent Ctrl-C\n%s", timeout, _tail(runner.output()))
        return EjectResult(False, "interrupted", runner.output(), True)
    out = runner.output()
    if rc == 0:
        log.info("eject: ok\n%s", _tail(out))
        return EjectResult(True, detail=_tail(out))
    code, power = classify_failure(rc, out)
    log.error("eject: failed rc=%s code=%s power_cycle=%s\n%s", rc, code, power, _tail(out))
    return EjectResult(False, code, _tail(out), power)


def estimate_bytes(dpi: int, frames: int) -> int:
    """Disk space a strip needs before the overscan files are cleaned up.

    A 24x36 mm frame is dpi/25.4 pixels per mm; 6 bytes per pixel for the RGB
    image, and about the same again for overscan, IR and the safety margin of
    the driver's working files (measured as roughly 2.4x the image size).
    """
    width, height = 24.0 / 25.4 * dpi, 36.0 / 25.4 * dpi
    return int(width * height * 6 * 2.4 * frames)


def _free_bytes(path: Path) -> int:
    p = path
    while not p.exists() and p != p.parent:
        p = p.parent
    return shutil.disk_usage(p).free


def existing_images(scan_root: Path, name: str) -> int:
    """How many images the film folder ``name`` already holds (0 for a new film)."""
    index = exporter.read_index(scan_root / name / ".driver", name)
    if not index:
        return 0
    return sum(1 for i in index["images"] if i.get("status") == "delivered")


def _tail(text: str, lines: int = 14) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


class ScanSession:
    def __init__(self, settings: Settings, driver: drv.Driver, name: str, mode: str,
                 listener: Callable[[Event], None], *, frames: list[int] | None = None,
                 runner_cls=ProcessRunner, free_bytes: Callable[[Path], int] = _free_bytes,
                 scanner_check: Callable[[drv.Driver], ScannerStatus] = check_scanner):
        if mode not in (STRIP_MODE, FILM_MODE):
            raise ValueError(mode)
        self.settings = dataclasses.replace(settings)   # the GUI may change its copy while this runs
        self.driver = driver
        self.name = name
        self.mode = mode
        self.frames = sorted(set(frames or settings.frames))      # apertures of the first (or only) strip
        drv.frames_spec(self.frames)                                # rejects anything outside 1..6 right here
        self._listener = listener
        self._runner_cls = runner_cls
        self._free_bytes = free_bytes
        self._scanner_check = scanner_check
        self._runner: ProcessRunner | None = None
        self._runner_lock = threading.Lock()
        self._cancel = threading.Event()
        self._next_event = threading.Event()
        self._next_choice = False
        self._next_frames: list[int] = list(range(1, FRAMES_PER_STRIP + 1))
        self._thread: threading.Thread | None = None
        self._log_file = None
        self._margins = MarginTracker()
        self._known_missing: set[int] = set()      # reserved before this run: not reported again
        self.result: SessionResult | None = None
        self.final_dir = self.settings.scan_root() / name
        self.stage_dir = self.final_dir / ".driver"

    # ------------------------------------------------------------------ control (GUI thread)
    def start(self) -> None:
        self._thread = threading.Thread(target=self._main, name="scan-session", daemon=True)
        self._thread.start()

    @property
    def running(self) -> bool:
        return bool(self._thread) and self._thread.is_alive()

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def answer_prompt(self) -> None:
        """The user did what the driver's prompt asked (magazine reinserted)."""
        with self._runner_lock:
            if self._runner:
                self._runner.send_enter()

    def answer_next(self, proceed: bool, frames: list[int] | None = None) -> None:
        """Another strip (``proceed``) with these apertures (default: all six), or the film is finished."""
        if frames:
            drv.frames_spec(frames)
            self._next_frames = sorted(set(frames))
        else:
            self._next_frames = list(range(1, FRAMES_PER_STRIP + 1))
        self._next_choice = proceed
        self._next_event.set()

    def cancel(self) -> None:
        self._cancel.set()
        self._next_choice = False
        self._next_event.set()
        with self._runner_lock:
            if self._runner:
                self._runner.interrupt()

    # ------------------------------------------------------------------ flow (session thread)
    def _emit(self, kind: str, **data) -> None:
        try:
            self._listener(Event(kind, data))
        except Exception:  # a broken listener must not stop a scan in progress
            pass

    def _log(self, line: str) -> None:
        if self._log_file:
            try:
                self._log_file.write(line + "\n")
                self._log_file.flush()
            except OSError:
                pass

    def _open_log(self) -> None:
        try:
            paths.log_dir().mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            self._log_file = open(paths.log_dir() / f"{stamp}-{self.name}.log", "w", encoding="utf-8")
            logs = sorted(paths.log_dir().glob("[0-9]*-*.log"))     # scan logs only, not filmdeck.log
            for old in logs[:-LOG_KEEP]:
                old.unlink(missing_ok=True)
        except OSError:
            self._log_file = None

    def _main(self) -> None:
        self._open_log()
        try:
            result = self._flow()
        except Exception as e:  # last resort: report instead of dying silently
            result = SessionResult("error", "internal", f"{type(e).__name__}: {e}", final_dir=self.final_dir)
            log.exception("scan %s: internal error", self.name)
        summary = (f"== result: kind={result.kind} code={result.code!r} power_cycle={result.power_cycle} "
                   f"images={result.images_total} new={result.images_new} detail={result.detail!r}")
        self._log(summary)
        log.info("scan %s: %s", self.name, summary)
        if self._log_file:
            self._log_file.close()
        self.result = result
        self._emit("finished", result=result)

    def _error(self, code: str, detail: str = "", power: bool = False) -> SessionResult:
        return SessionResult("error", code, detail, power, final_dir=self.final_dir)

    def _flow(self) -> SessionResult:
        s, d = self.settings, self.driver
        if d.too_old:
            return self._error("driver_old", d.version)
        frames = self.frames
        try:
            self.stage_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return self._error("no_write", f"{self.stage_dir}: {e}")
        if not os.access(self.stage_dir, os.W_OK):
            return self._error("no_write", str(self.stage_dir))
        need, free = estimate_bytes(s.dpi, len(frames) if self.mode == STRIP_MODE else FRAMES_PER_STRIP), \
            self._free_bytes(self.final_dir)
        if free < need:
            return self._error("no_space", f"{free // 2**20} MB free, about {need // 2**20} MB needed")

        self._emit("state", state="preflight")
        status = self._scanner_check(d)
        if not status.ok:
            return self._error(status.error or "status_failed", status.raw, status.power_cycle)
        if status.start_state == "unsafe":
            return self._error("unsafe_state", status.raw, True)
        if status.magazine is False:
            return self._error("no_magazine", status.raw)
        if self._cancel.is_set():
            return SessionResult("cancelled", final_dir=self.final_dir)

        self._known_missing = exporter.missing_numbers(self.stage_dir, self.name)
        strips, new_total, partial = 0, 0, False
        export = exporter.ExportResult()
        warnings: list[str] = []
        while True:
            strips += 1
            outcome = self._scan_strip(strips, frames)
            export = self._export()
            warnings += export.warnings
            new_total += len(export.new_images)
            if outcome.kind == "ok" and not export.index_found:
                return self._finish("error", "export_failed", "the driver wrote no album index",
                                    False, strips, new_total, export, warnings)
            if outcome.kind in ("error", "cancelled"):
                return self._finish(outcome.kind, outcome.code, _tail(outcome.output), outcome.power_cycle,
                                    strips, new_total, export, warnings)
            partial = partial or outcome.kind == "partial"
            self._emit("strip_done", strip=strips, images=len(export.images), new=len(export.new_images),
                       missing=[m.number for m in export.missing])
            if self.mode == STRIP_MODE or self._cancel.is_set():
                break
            if not self._ask_next():
                break
            frames = self._next_frames
        kind = "partial" if (partial or export.missing) else "ok"
        return self._finish(kind, "", "", False, strips, new_total, export, warnings)

    def _finish(self, kind: str, code: str, detail: str, power: bool, strips: int, new_total: int,
                export: exporter.ExportResult, warnings: list[str]) -> SessionResult:
        advice = self._margins.advice(self.settings.position_offset_mm or 0.0) if export.missing else None
        return SessionResult(kind, code, detail, power, images_total=len(export.images), images_new=new_total,
                             missing=[m.number for m in export.missing], missing_details=list(export.missing),
                             offset_advice=advice, strips=strips, final_dir=self.final_dir, warnings=warnings)

    def _ask_next(self) -> bool:
        self._next_choice = False
        self._next_event.clear()
        self._emit("ask_next")
        self._next_event.wait()
        return self._next_choice and not self._cancel.is_set()

    def _export(self) -> exporter.ExportResult:
        s = self.settings
        self._emit("state", state="exporting")
        try:
            result = exporter.export_album(self.stage_dir, self.name, self.final_dir, bits=s.bit_depth,
                                           export_ir=s.use_ir and s.export_ir, keep_overscan=s.keep_overscan,
                                           preview_size=s.preview_size)
        except Exception as e:
            result = exporter.ExportResult(index_found=True, warnings=[f"export failed: {type(e).__name__}: {e}"])
        result.missing = [m for m in result.missing if m.number not in self._known_missing]
        self._emit("exported", images=result.images, missing=result.missing, warnings=result.warnings)
        return result

    def _scan_strip(self, strip_no: int, frames: list[int]) -> _Outcome:
        s = self.settings
        assume_loaded = False
        if strip_no > 1 and s.fast_next_strip:
            # The magazine with the next strip is pushed in by now. The driver refuses this
            # (before any write) when the scanner was power-cycled; then the full load is used.
            self._emit("state", state="loading", strip=strip_no)
            rc, out = self._run(drv.load_argv(True), strip_no)
            if rc == 0:
                assume_loaded = True
            else:
                code, power = classify_failure(rc, out)
                if code != "cold":
                    return _Outcome("error", rc, code, power, out)
        if self._cancel.is_set():
            return _Outcome("cancelled")
        opts = drv.DigitizeOptions(
            stage_dir=str(self.stage_dir), album=self.name, frames=drv.frames_spec(frames), dpi=s.dpi,
            ir=s.use_ir, dust_clean=s.dust_clean, rotate=s.rotate, write_cal_data=s.write_cal_data,
            position_offset_mm=s.position_offset_mm, assume_loaded=assume_loaded)
        self._emit("strip_started", strip=strip_no, frames=len(frames), frame_numbers=list(frames),
                   full_load=not assume_loaded)
        self._emit("state", state="scanning", strip=strip_no)
        rc, out = self._run(drv.digitize_argv(opts), strip_no)
        cancelled = self._cancel.is_set()
        if rc == 0:
            return _Outcome("ok", rc, output=out)
        if rc in (4, 5):
            return _Outcome("partial", rc, "coverage" if rc == 4 else "eject_warning", False, out)
        code, power = classify_failure(rc, out)
        if rc == 130 and cancelled:
            return _Outcome("cancelled", rc, "interrupted", True, out)
        return _Outcome("error", rc, code, power, out)

    def _run(self, argv: list[str], strip_no: int) -> tuple[int, str]:
        def on_line(stream: str, line: str) -> None:
            self._log(line)
            self._margins.feed(line)
            parsed = classify_line(line)
            if parsed.kind == "wrote_main":
                self._emit("frame_written", strip=strip_no, frame=parsed.data["frame"], path=parsed.data["path"])
            elif parsed.kind != "text":
                self._emit("progress", step=parsed.kind, **parsed.data)
            self._emit("log", stream=stream, line=line)

        def on_prompt(kind: str, text: str) -> None:
            self._emit("prompt", prompt_kind=kind, text=text)

        self._log("$ " + " ".join(argv))
        runner = self._runner_cls(argv, drv.environment(self.driver), on_line=on_line, on_prompt=on_prompt)
        try:
            runner.start()
        except OSError as e:
            return 127, f"error: cannot start the driver: {e}"
        with self._runner_lock:
            self._runner = runner
            if self._cancel.is_set():
                runner.interrupt()
        try:
            rc = runner.wait()
        finally:
            with self._runner_lock:
                self._runner = None
        return (rc if rc is not None else 1), runner.output()
