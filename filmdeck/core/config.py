"""User settings, stored as JSON.

Loading is forgiving: unknown keys are ignored and a value that is missing or
not allowed falls back to its default, so a hand-edited or older file never
stops the program from starting.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path

from . import paths

DPI_CHOICES = (600, 1200, 2400, 3600, 7200)
BIT_CHOICES = (48, 24, 16, 8)       # 48 = RGB 16 bit/channel, 24 = RGB 8 bit/channel, 16 = grey 16 bit, 8 = grey 8 bit
ROTATE_CHOICES = (0, 90, 180, 270)
PREVIEW_CHOICES = (0, 160, 320, 640)  # JPEG long edge in pixels, 0 = no JPEG files
FILM_TYPES = ("c41", "bw")
LANGUAGES = ("de", "en")
CHANNELS = ("release", "master")
MAX_FRAMES = 6

_ALLOWED = {
    "language": LANGUAGES,
    "film_type": FILM_TYPES,
    "dpi": DPI_CHOICES,
    "bit_depth": BIT_CHOICES,
    "rotate": ROTATE_CHOICES,
    "preview_size": PREVIEW_CHOICES,
    "update_channel": CHANNELS,
}


@dataclass
class Settings:
    language: str = "de"
    scan_dir: str = ""                      # "" = default (~/Pictures/Filmscans)
    film_type: str = "c41"                  # c41 = colour with IR, bw = black and white without IR
    dpi: int = 3600
    bit_depth: int = 48
    frames: list[int] = field(default_factory=lambda: list(range(1, MAX_FRAMES + 1)))  # apertures to scan (first strip)
    rotate: int = 0
    dust_clean: bool = True                 # IR dust removal (only with IR)
    export_ir: bool = True                  # keep the IR channel next to the image (NegPy reads NAME_ir.tiff)
    keep_overscan: bool = False             # keep the large <frame>.overscan.tiff files
    write_cal_data: bool = False            # driver's per-frame calibration dump (13 MB each), for bug reports
    position_offset_mm: float | None = None  # per-unit frame position offset, None = driver default
    fast_next_strip: bool = True            # load the next strip of a film without the jog (driver: --next-strip)
    preview_size: int = 320
    films: list[str] = field(default_factory=lambda: ["Kodak Gold", "Harman Phoenix II"])
    cameras: list[str] = field(default_factory=list)
    last_film: str = ""
    last_camera: str = ""
    negpy_path: str = ""
    check_updates: bool = True
    update_channel: str = "release"
    driver_path: str = ""                   # "" = managed install, otherwise a folder that contains of135i/
    ignored_update: str = ""                # version the user chose to ignore

    # ------------------------------------------------------------------ derived
    @property
    def use_ir(self) -> bool:
        return self.film_type == "c41"

    def scan_root(self) -> Path:
        return Path(self.scan_dir).expanduser() if self.scan_dir else paths.default_scan_dir()

    # ------------------------------------------------------------------ io
    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        s = cls()
        if not isinstance(data, dict):
            return s
        for f in fields(cls):
            if f.name not in data:
                continue
            value = _coerce(f.name, data[f.name], getattr(s, f.name))
            if value is not _INVALID:
                setattr(s, f.name, value)
        return s

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or paths.settings_file()
        try:
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return cls()

    def save(self, path: Path | None = None) -> None:
        path = path or paths.settings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    # ------------------------------------------------------------------ presets
    def add_preset(self, kind: str, name: str) -> bool:
        """Add a film or camera name (kind = "films" | "cameras"); False if empty or present."""
        name = " ".join(name.split())
        items = getattr(self, kind)
        if not name or name in items:
            return False
        items.append(name)
        return True

    def remove_preset(self, kind: str, name: str) -> bool:
        items = getattr(self, kind)
        if name in items:
            items.remove(name)
            return True
        return False


_INVALID = object()


def _coerce(key: str, value, default):
    if key in _ALLOWED:
        return value if value in _ALLOWED[key] and not isinstance(value, bool) else _INVALID
    if key == "frames":
        ok = (isinstance(value, list) and value
              and all(isinstance(x, int) and not isinstance(x, bool) and 1 <= x <= MAX_FRAMES for x in value))
        return sorted(set(value)) if ok else _INVALID
    if key == "position_offset_mm":
        if value is None:
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool) and -5.0 <= float(value) <= 5.0:
            return float(value)
        return _INVALID
    if isinstance(default, bool):
        return value if isinstance(value, bool) else _INVALID
    if isinstance(default, list):
        if isinstance(value, list) and all(isinstance(x, str) for x in value):
            seen: list[str] = []
            for x in value:
                x = " ".join(x.split())
                if x and x not in seen:
                    seen.append(x)
            return seen
        return _INVALID
    if isinstance(default, str):
        return value if isinstance(value, str) else _INVALID
    return _INVALID
