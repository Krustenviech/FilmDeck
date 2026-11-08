"""Reading the driver's TIFFs, converting the bit depth, making JPEG previews.

The driver writes the raw linear negative as 16-bit RGB TIFF (``of135i/image.py``
there). Nothing here inverts or colour-corrects: the converted files are still
negatives, the preview only stretches the contrast so a dark linear file is
visible.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

_CHUNK_ROWS = 512


class ImagingError(RuntimeError):
    pass


def read_tiff(path: str | Path) -> np.ndarray:
    return tifffile.imread(str(path))


def read_resolution(path: str | Path):
    """(x, y, unit) of the first page as tifffile reports them, or None."""
    with tifffile.TiffFile(str(path)) as tf:
        tags = tf.pages[0].tags
        x, y, unit = tags.get("XResolution"), tags.get("YResolution"), tags.get("ResolutionUnit")
        if x is None or y is None:
            return None
        unit_name = getattr(unit.value, "name", None) if unit is not None else None
        return x.value, y.value, unit_name or "INCH"


def to_rgb8(arr: np.ndarray) -> np.ndarray:
    """16-bit RGB -> 8-bit RGB, round(v * 255 / 65535)."""
    out = np.empty(arr.shape, dtype=np.uint8)
    for i in range(0, arr.shape[0], _CHUNK_ROWS):
        block = arr[i:i + _CHUNK_ROWS].astype(np.uint32)
        out[i:i + _CHUNK_ROWS] = (block * 255 + 32767) // 65535
    return out


def to_gray16(arr: np.ndarray) -> np.ndarray:
    """16-bit RGB -> 16-bit grey, the mean of the three channels (rounded).

    For a black-and-white negative the channels carry the same picture, the
    mean averages out the noise of the three sensor lines.
    """
    out = np.empty(arr.shape[:2], dtype=np.uint16)
    for i in range(0, arr.shape[0], _CHUNK_ROWS):
        block = arr[i:i + _CHUNK_ROWS].astype(np.uint32)
        out[i:i + _CHUNK_ROWS] = (block[..., 0] + block[..., 1] + block[..., 2] + 1) // 3
    return out


def to_gray8(arr: np.ndarray) -> np.ndarray:
    """16-bit RGB -> 8-bit grey (the 16-bit grey mean, then round(v * 255 / 65535))."""
    out = np.empty(arr.shape[:2], dtype=np.uint8)
    for i in range(0, arr.shape[0], _CHUNK_ROWS):
        block = arr[i:i + _CHUNK_ROWS].astype(np.uint32)
        grey = (block[..., 0] + block[..., 1] + block[..., 2] + 1) // 3
        out[i:i + _CHUNK_ROWS] = (grey * 255 + 32767) // 65535
    return out


def convert_tiff(src: str | Path, dst: str | Path, bits: int) -> None:
    """Write ``dst`` as 24-bit RGB, 16-bit grey or 8-bit grey from the driver's 48-bit file.

    The resolution tags are copied from ``src`` (the driver stores the real
    sampling resolution there). ``dst`` appears atomically.
    """
    if bits not in (24, 16, 8):
        raise ValueError("convert_tiff handles 24, 16 and 8 bit only; 48 bit is the source file")
    arr = read_tiff(src)
    if arr.dtype != np.uint16 or arr.ndim != 3 or arr.shape[2] != 3:
        raise ImagingError(f"{src}: expected 16-bit RGB, got {arr.dtype} {arr.shape}")
    res = read_resolution(src)
    if bits == 24:
        out, photometric = to_rgb8(arr), "rgb"
    elif bits == 16:
        out, photometric = to_gray16(arr), "minisblack"
    else:
        out, photometric = to_gray8(arr), "minisblack"
    del arr
    kwargs = {}
    if res is not None:
        kwargs = {"resolution": (res[0], res[1]), "resolutionunit": res[2]}
    dst = Path(dst)
    tmp = dst.with_name(dst.name + ".partial")
    try:
        tifffile.imwrite(str(tmp), out, photometric=photometric, compression=None, metadata=None, **kwargs)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()


def make_preview(path: str | Path, long_edge: int) -> Image.Image:
    """A small viewable image of a (negative) scan.

    Subsamples by striding (memory-mapped, so a 7200 dpi file is not loaded as
    a whole), stretches the contrast with one global black and white point so
    the colour of the film base is kept, and applies display gamma.
    """
    if long_edge < 16:
        raise ValueError("long_edge too small")
    try:
        data = tifffile.memmap(str(path))
    except Exception:  # compressed or tiled file: fall back to reading it
        data = tifffile.imread(str(path))
    h, w = data.shape[:2]
    step = max(1, max(h, w) // (long_edge * 2))
    small = np.asarray(data[::step, ::step]).astype(np.float32)
    lo, hi = np.percentile(small, (0.5, 99.5))
    if hi <= lo:
        hi = lo + 1.0
    view = np.clip((small - lo) / (hi - lo), 0.0, 1.0) ** (1 / 2.2)
    img = Image.fromarray((view * 255 + 0.5).astype(np.uint8))
    img.thumbnail((long_edge, long_edge), Image.Resampling.LANCZOS)
    return img


def save_preview_jpeg(src: str | Path, dst: str | Path, long_edge: int) -> None:
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".partial")
    try:
        make_preview(src, long_edge).save(tmp, format="JPEG", quality=80)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()
