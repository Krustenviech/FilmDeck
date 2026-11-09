"""From the driver's album to the finished film folder.

The driver keeps its own working tree (``<film>/.driver/``): one ``roll-NNN``
directory per strip and an *album* that numbers the photographs through all
strips of the film (``--album``, driver issue #65). FilmDeck never moves or
deletes a driver image. It reads the album's ``index.json`` and publishes:

    <film>/<NAME>_01.tiff          48 bit: a hard link (a copy where the file
    <film>/<NAME>_01_ir.tiff       system has none), 24/16 bit: converted
    <film>/.previews/<NAME>_01.jpg small JPEG, hidden so NegPy does not import it

The ``_ir`` name is the one NegPy recognises as the IR channel of ``<NAME>_01``.
Re-running is harmless: files that already exist are kept.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import imaging
from .naming import image_filename

PREVIEW_DIR = ".previews"


@dataclass(frozen=True)
class ExportedImage:
    number: int
    path: Path
    ir_path: Path | None
    preview: Path | None
    source: Path
    new: bool


@dataclass(frozen=True)
class MissingImage:
    number: int
    reason: str                       # the driver's own words (English)
    overscan: Path | None = None      # its full scan, published as <name>_NN_overscan.tiff (not cropped)


@dataclass
class ExportResult:
    index_found: bool = False
    images: list[ExportedImage] = field(default_factory=list)
    missing: list[MissingImage] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def new_images(self) -> list[ExportedImage]:
        return [i for i in self.images if i.new]


def album_index_path(stage_dir: str | Path, album: str) -> Path:
    return Path(stage_dir) / album / "index.json"


def read_index(stage_dir: str | Path, album: str) -> dict | None:
    try:
        data = json.loads(album_index_path(stage_dir, album).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("images"), list) else None


def _link_or_copy(src: Path, dst: Path) -> None:
    try:
        os.link(src, dst)
        return
    except FileExistsError:
        raise
    except OSError:
        pass  # no hard links here (exFAT, another file system): copy
    tmp = dst.with_name(dst.name + ".partial")
    try:
        shutil.copyfile(src, tmp)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()


def _nonempty(path: Path) -> bool:
    try:
        return path.stat().st_size > 0
    except OSError:
        return False


def _publish_full_scan(stage_dir: str | Path, final: Path, album: str, number: int, item: dict, bits: int,
                       warnings: list[str]) -> Path | None:
    """A frame the driver refused to crop (``aperture coverage NOT verified``) keeps its full scan in the
    staging folder. Publish it as ``<name>_NN_overscan.tiff`` so the picture is not lost; it is never
    cropped here, and the number stays reserved for ``of135i recrop``."""
    try:
        roll = f"{item.get('prefix') or ''}roll-{int(item['roll']):03d}"
        src = Path(stage_dir) / roll / f"f{int(item['frame'])}.overscan.tiff"
    except (KeyError, TypeError, ValueError):
        return None
    if not _nonempty(src):
        return None
    dest = final / image_filename(album, number, "_overscan")
    try:
        if not dest.exists():
            if bits == 48:
                _link_or_copy(src, dest)
            else:
                imaging.convert_tiff(src, dest, bits)
        return dest if _nonempty(dest) else None
    except (OSError, imaging.ImagingError, ValueError) as e:
        warnings.append(f"#{number}: could not publish the full scan: {e}")
        return None


def _remove_stale_partials(folder: Path) -> None:
    if folder.is_dir():
        for p in folder.glob("*.partial"):
            try:
                p.unlink()
            except OSError:
                pass


def export_album(stage_dir: str | Path, album: str, final_dir: str | Path, *,
                 bits: int, export_ir: bool, keep_overscan: bool,
                 preview_size: int) -> ExportResult:
    result = ExportResult()
    index = read_index(stage_dir, album)
    if index is None:
        return result
    result.index_found = True
    final = Path(final_dir)
    final.mkdir(parents=True, exist_ok=True)
    previews = final / PREVIEW_DIR
    _remove_stale_partials(final)
    _remove_stale_partials(previews)

    for item in sorted(index["images"], key=lambda i: int(i.get("number", 0))):
        number = int(item["number"])
        if item.get("status") != "delivered":
            overscan = _publish_full_scan(stage_dir, final, album, number, item, bits, result.warnings)
            result.missing.append(MissingImage(number, str(item.get("reason") or "not delivered"), overscan))
            continue
        src = Path(item.get("source") or "")
        if not src.is_absolute() or not _nonempty(src):
            result.warnings.append(f"#{number}: source file missing: {src}")
            continue
        dest = final / image_filename(album, number)
        created = False
        try:
            if not dest.exists():
                if bits == 48:
                    _link_or_copy(src, dest)
                else:
                    imaging.convert_tiff(src, dest, bits)
                created = True
            if not _nonempty(dest):
                raise OSError(f"{dest.name} is empty")
        except (OSError, imaging.ImagingError, ValueError) as e:
            result.warnings.append(f"#{number}: export failed: {e}")
            continue

        ir_dest = None
        ir_src = src.with_name(f"{src.stem}-ir.tiff")
        if export_ir and _nonempty(ir_src):
            ir_dest = final / image_filename(album, number, "_ir")
            try:
                if not ir_dest.exists():
                    _link_or_copy(ir_src, ir_dest)
            except OSError as e:
                result.warnings.append(f"#{number}: IR export failed: {e}")
                ir_dest = None

        preview = None
        if preview_size:
            preview = previews / f"{album}_{number:02d}.jpg"
            try:
                if not preview.exists():
                    imaging.save_preview_jpeg(src, preview, preview_size)
            except Exception as e:  # a preview must never stop a scan
                result.warnings.append(f"#{number}: preview failed: {e}")
                preview = None

        if not keep_overscan:
            for leftover in (src.with_name(f"{src.stem}.overscan.tiff"),
                             src.with_name(f"{src.stem}-ir.overscan.tiff")):
                try:
                    leftover.unlink()
                except FileNotFoundError:
                    pass
                except OSError as e:
                    result.warnings.append(f"could not remove {leftover.name}: {e}")

        result.images.append(ExportedImage(number, dest, ir_dest, preview, src, created))
    return result
