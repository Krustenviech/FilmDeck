"""Finding the driver and building its command lines.

The driver (``of135i``) is run as a separate process with the Python that runs
FilmDeck, with ``PYTHONPATH`` pointing at the driver folder. A separate process
keeps the driver's own safety layer (one process owns the scanner, abort means
power-cycle) exactly as its author designed it, and lets the driver be updated
without touching FilmDeck.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import paths
from .config import Settings

log = logging.getLogger(__name__)

# --album and --position-offset exist from this release on.
MIN_VERSION = (0, 2, 11)
SOURCE_FILE = ".filmdeck-source.json"

_VERSION_RE = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class Driver:
    root: Path                     # folder that contains of135i/
    version: str                   # e.g. "0.2.11"
    managed: bool                  # installed (and updatable) by FilmDeck
    demo: bool = False
    source: dict | None = None     # what FilmDeck wrote at install time (tag, sha, ...)

    @property
    def version_tuple(self) -> tuple[int, ...] | None:
        return parse_version(self.version)

    @property
    def too_old(self) -> bool:
        v = self.version_tuple
        return v is None or v < MIN_VERSION


def parse_version(text: str) -> tuple[int, ...] | None:
    m = _SEMVER_RE.match((text or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def read_version(root: Path) -> str | None:
    try:
        text = (root / "of135i" / "__init__.py").read_text(encoding="utf-8")
    except OSError:
        return None
    m = _VERSION_RE.search(text)
    return m.group(1) if m else None


def _read_source(root: Path) -> dict | None:
    try:
        return json.loads((root / SOURCE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def demo_root() -> Path:
    return Path(__file__).resolve().parent.parent / "demo"


def demo_enabled() -> bool:
    return os.environ.get("FILMDECK_DEMO") == "1"


def locate(settings: Settings) -> Driver | None:
    """The driver to use, or None when there is none (or the folder is not a driver)."""
    found = _locate(settings)
    if found is None:
        log.info("driver: none found (custom path: %r)", settings.driver_path or None)
    else:
        log.info("driver: %s at %s (%s)", found.version, found.root,
                 "demo" if found.demo else "managed" if found.managed else "custom folder")
    return found


def _locate(settings: Settings) -> Driver | None:
    if demo_enabled():
        root = demo_root()
        return Driver(root, read_version(root) or "0.0.0", managed=False, demo=True)
    if settings.driver_path:
        root = Path(settings.driver_path).expanduser()
        version = read_version(root)
        return Driver(root, version, managed=False) if version else None
    current = paths.driver_root_dir() / "current"
    if current.exists():
        root = current.resolve()
        version = read_version(root)
        if version:
            return Driver(root, version, managed=True, source=_read_source(root))
    return None


# --------------------------------------------------------------------- commands

def python_executable() -> str:
    return os.environ.get("FILMDECK_PYTHON") or sys.executable


def environment(driver: Driver) -> dict:
    env = dict(os.environ)
    old = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(driver.root) + (os.pathsep + old if old else "")
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def base_argv() -> list[str]:
    # No -I: isolated mode would ignore PYTHONPATH.
    return [python_executable(), "-u", "-m", "of135i"]


def frames_spec(frames) -> str:
    """The driver's --frames value for a set of apertures: [1, 2, 3] -> "1-3", [1, 2, 6] -> "1-2,6", [4] -> "4"."""
    numbers = sorted(set(frames))
    if not numbers or numbers[0] < 1 or numbers[-1] > 6:
        raise ValueError("a strip holds frames 1 to 6")
    parts, start, prev = [], numbers[0], numbers[0]
    for n in numbers[1:] + [None]:
        if n is not None and n == prev + 1:
            prev = n
            continue
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        if n is not None:
            start = prev = n
    return ",".join(parts)


@dataclass(frozen=True)
class DigitizeOptions:
    stage_dir: str
    album: str
    frames: str
    dpi: int
    ir: bool
    dust_clean: bool = True
    rotate: int = 0
    write_cal_data: bool = False
    position_offset_mm: float | None = None
    assume_loaded: bool = False


def digitize_argv(o: DigitizeOptions) -> list[str]:
    argv = base_argv() + ["digitize", "-o", o.stage_dir, "--album", o.album,
                          "--frames", o.frames, "--dpi", str(o.dpi)]
    if not o.ir:
        argv.append("--no-ir")
    elif not o.dust_clean:
        argv.append("--no-clean")
    if o.rotate:
        argv += ["--rotate", str(o.rotate)]
    if not o.write_cal_data:
        argv.append("--no-cal-data")
    if o.position_offset_mm is not None:
        argv += ["--position-offset", repr(float(o.position_offset_mm))]
    if o.assume_loaded:
        argv.append("--assume-loaded")
    return argv


def load_argv(next_strip: bool) -> list[str]:
    return base_argv() + ["load"] + (["--next-strip"] if next_strip else [])


def status_argv() -> list[str]:
    return base_argv() + ["status"]


def version_argv() -> list[str]:
    return base_argv() + ["version"]


def doctor_argv() -> list[str]:
    return base_argv() + ["doctor"]


def eject_argv() -> list[str]:
    return base_argv() + ["eject"]


def run_short(driver: Driver, argv: list[str], timeout: float = 30.0) -> tuple[int, str, str]:
    """Run a quick, non-interactive driver command and return (rc, stdout, stderr)."""
    try:
        p = subprocess.run(argv, env=environment(driver), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout:.0f} s"
    except OSError as e:
        return 127, "", f"error: cannot start {argv[0]}: {e}"
    return p.returncode, p.stdout, p.stderr
