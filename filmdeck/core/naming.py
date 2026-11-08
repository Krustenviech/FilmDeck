"""Film folder names: ``YY-MM-Film-Kamera``.

The same string is the folder below the scan directory, the album name given to
the driver and the prefix of every file (``26-11-Kodak_Gold-Nikon_F3_01.tiff``).
It has to be a plain directory name, so everything that is not safe in a file
name on any common file system (the SD card may be exFAT) is removed.
"""

from __future__ import annotations

import datetime as _dt
import re

_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
MAX_NAME_LENGTH = 100


def sanitize_part(text: str) -> str:
    """One name part: spaces become ``_``, forbidden characters are dropped."""
    text = _FORBIDDEN.sub("", text or "")
    text = re.sub(r"\s+", "_", text.strip())
    return text.strip("._-")


def sanitize_name(text: str) -> str:
    """A whole name typed by the user. Keeps ``-`` between parts."""
    text = _FORBIDDEN.sub("", text or "")
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip("._-")
    return text[:MAX_NAME_LENGTH].rstrip("._-")


def date_prefix(today: _dt.date | None = None) -> str:
    today = today or _dt.date.today()
    return f"{today:%y}-{today:%m}"


def compose_name(film: str, camera: str, today: _dt.date | None = None) -> str:
    """``YY-MM-Film-Kamera``; empty parts are left out."""
    parts = [date_prefix(today), sanitize_part(film), sanitize_part(camera)]
    return sanitize_name("-".join(p for p in parts if p))


def image_filename(name: str, number: int, suffix: str = "") -> str:
    """``<name>_<NN><suffix>.tiff``; the number has at least two digits."""
    return f"{name}_{number:02d}{suffix}.tiff"
