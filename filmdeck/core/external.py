"""Starting other programs: NegPy and the file manager."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from pathlib import Path


def negpy_candidates() -> list[Path]:
    """Where a NegPy AppImage or launcher usually is (NegPy ships an AppImage for Linux)."""
    home = Path.home()
    found: list[Path] = []
    on_path = shutil.which("NegPy") or shutil.which("negpy")
    if on_path:
        found.append(Path(on_path))
    for pattern in (
        str(home / "Applications" / "NegPy*.AppImage"),
        str(home / "Downloads" / "NegPy*.AppImage"),
        str(home / "NegPy*.AppImage"),
        str(home / ".local" / "bin" / "NegPy*"),
        str(home / "Desktop" / "NegPy*.AppImage"),
        str(home / "Applications" / "negpy*.AppImage"),
        str(home / "Downloads" / "negpy*.AppImage"),
    ):
        found.extend(Path(p) for p in sorted(glob.glob(pattern)))
    seen, unique = set(), []
    for p in found:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def find_negpy(configured: str = "") -> Path | None:
    """The configured path if it is usable, else the first usable candidate."""
    if configured:
        p = Path(configured).expanduser()
        return p if p.is_file() and os.access(p, os.X_OK) else None
    for p in negpy_candidates():
        if p.is_file() and os.access(p, os.X_OK):
            return p
    return None


def launch_detached(argv: list[str]) -> None:
    """Start a program that must outlive FilmDeck and not share its terminal."""
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
