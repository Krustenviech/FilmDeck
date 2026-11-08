"""``filmdeck --selftest``: checks that this installation (source, venv or AppImage) is complete.

It imports every dependency, builds the main window, and runs one complete scan against the built-in demo
driver in a temporary folder. It never touches a real scanner and never writes outside its temporary folder.
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
from pathlib import Path


def _check_imports(say) -> list[str]:
    problems = []
    for name in ("numpy", "PIL", "tifffile", "usb.core", "PySide6.QtWidgets"):
        try:
            __import__(name)
        except Exception as e:                     # noqa: BLE001 - report whatever is wrong
            problems.append(f"cannot import {name}: {e}")
    if not problems:
        import usb.backend.libusb1 as libusb1
        backend = libusb1.get_backend()
        # without libusb the driver cannot reach a scanner; the demo scan below still works
        say("libusb: " + ("found" if backend is not None else "NOT FOUND (a real scanner will not work)"))
        if backend is None:
            problems.append("libusb-1.0 was not found")
    return problems


def _check_window(say, scan_dir: Path) -> list[str]:
    from PySide6.QtWidgets import QApplication

    from .core.config import Settings
    from .ui import style
    from .ui.mainwindow import MainWindow

    app = QApplication.instance() or QApplication([])
    style.apply(app)
    window = MainWindow(Settings(scan_dir=str(scan_dir)), autostart=False)
    window.show()
    app.processEvents()
    ok = window.driver is not None and window.driver.demo
    window.close()
    say("window: " + ("ok" if ok else "FAILED"))
    return [] if ok else ["the main window did not find the demo driver"]


def _check_scan(say, scan_dir: Path) -> list[str]:
    from .core import driver as drv
    from .core.config import Settings
    from .core.session import ScanSession

    settings = Settings(scan_dir=str(scan_dir), dpi=600, bit_depth=24, frames=[1, 2], preview_size=160)
    driver = drv.locate(settings)
    if driver is None:
        return ["demo driver not found"]
    done = threading.Event()
    holder: dict = {}

    def listener(event) -> None:
        if event.kind == "prompt":
            holder["session"].answer_prompt()
        elif event.kind == "finished":
            holder["result"] = event.data["result"]
            done.set()

    session = ScanSession(settings, driver, "selftest", "strip", listener, frames=[1, 2])
    holder["session"] = session
    session.start()
    if not done.wait(180):
        session.cancel()
        return ["the demo scan did not finish within 3 minutes"]
    session.join()
    result = holder["result"]
    files = sorted(p.name for p in (scan_dir / "selftest").glob("*.tiff"))
    say(f"demo scan: {result.kind}, {result.images_total} images, files {files}")
    problems = []
    if result.kind != "ok" or result.images_total != 2:
        problems.append(f"demo scan ended with {result.kind} ({result.code}): {result.detail}")
    if len(files) < 2:
        problems.append("the demo scan wrote no images")
    return problems


def run(say=print) -> int:
    names = ("FILMDECK_HOME", "FILMDECK_DEMO", "OF135I_DEMO_SPEED", "OF135I_DEMO_STATE", "OF135I_DEMO_SCENARIO")
    saved = {k: os.environ.get(k) for k in names}
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="filmdeck-selftest-") as tmp:
        root = Path(tmp)
        os.environ.update(FILMDECK_HOME=str(root / "home"), FILMDECK_DEMO="1", OF135I_DEMO_SPEED="0.01",
                          OF135I_DEMO_STATE=str(root / "state"))
        os.environ.pop("OF135I_DEMO_SCENARIO", None)
        try:
            say(f"python: {sys.version.split()[0]} ({sys.executable})")
            problems += _check_imports(say)
            problems += _check_window(say, root / "scans")
            problems += _check_scan(say, root / "scans")
        except Exception as e:                      # noqa: BLE001
            problems.append(f"unexpected error: {type(e).__name__}: {e}")
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    for p in problems:
        say("PROBLEM: " + p)
    say("selftest FAILED" if problems else "selftest OK")
    return 1 if problems else 0
