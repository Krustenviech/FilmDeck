"""Command line of the demo driver.

Behaviour is steered by environment variables so tests (and curious users) can
provoke the situations a real scanner produces:

  OF135I_DEMO_SPEED     seconds per frame (default 0.4)
  OF135I_DEMO_STATE     file that remembers "the scanner has been loaded" (default: temp dir)
  OF135I_DEMO_SCENARIO  comma separated: no_scanner, no_permission, no_magazine, unsafe, busy, eject_fail,
                        cold (a --next-strip is refused), load_fail, coverage_fail:K,
                        empty_from:K, scan_fail:K

The album numbering is a port of of135i/digitize.py (album_plan / album_sync, MIT) so the
index.json that FilmDeck reads has the real layout; tests compare it with the real driver.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import tifffile

from . import __version__

REINSERT_PROMPT = ("JOG done. Now take the magazine FULLY OUT of the slot, then insert it fresh all the way "
                   "to the mechanical stop.\nPress Enter when it is at the stop (Ctrl-C aborts; a power "
                   "cycle is then required): ")
POWER_CYCLE = ("The scanner session is marked failed. Power the scanner OFF and ON again; restarting this "
               "program is NOT sufficient.")
DPI_CHOICES = (600, 1200, 2400, 3600, 7200)
HOLDER_FRAMES = 6
MANIFEST = "manifest.jsonl"


def scenarios() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for part in os.environ.get("OF135I_DEMO_SCENARIO", "").split(","):
        part = part.strip()
        if part:
            key, _, arg = part.partition(":")
            out[key] = arg or None
    return out


def state_file() -> Path:
    return Path(os.environ.get("OF135I_DEMO_STATE") or Path(tempfile.gettempdir()) / "of135i-demo-state")


def get_state() -> str:
    """"cold" (power-cycled or failed), "warm" (loaded and ejected since power-on) or "loaded"."""
    try:
        return state_file().read_text().strip() or "cold"
    except OSError:
        return "cold"


def set_state(value: str) -> None:
    if value == "cold":
        state_file().unlink(missing_ok=True)
    else:
        state_file().write_text(value + "\n")


def speed() -> float:
    try:
        return float(os.environ.get("OF135I_DEMO_SPEED", "0.4"))
    except ValueError:
        return 0.4


def err(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- shared checks

def device_problem(sc: dict) -> int | None:
    if "no_scanner" in sc:
        err("error: Plustek OpticFilm 135i (07b3:1436) not found on the host USB bus")
        return 1
    if "no_permission" in sc:
        err("error: USBError: [Errno 13] Access denied (insufficient permissions)")
        return 1
    if "busy" in sc:
        err("error: another of135i process holds the scanner")
        return 3
    return None


# ---------------------------------------------------------------- commands

def cmd_version(_args) -> int:
    print(f'of135i {__version__} "Demo" (driver revision demo, python {sys.version.split()[0]}, pyusb demo)')
    return 0


def cmd_status(_args) -> int:
    sc = scenarios()
    bad = device_problem(sc)
    if bad is not None:
        return bad
    print("reg 0x01 = 0x22")
    print("  start state: " + ("unsafe" if "unsafe" in sc else "cold-never-homed" if get_state() == "cold" else "idle-homed"))
    print("reg 0x101 = 0x08")
    print("magazine: not detected" if "no_magazine" in sc
          else "magazine: sensor reports present (does not prove it is locked)")
    print("button: idle")
    return 0


def full_load(sc: dict) -> int:
    print("running the vendor app-start jog ...", flush=True)
    time.sleep(speed())
    try:
        input(REINSERT_PROMPT)
    except (EOFError, KeyboardInterrupt):
        err("interrupted at the reinsert prompt. " + POWER_CYCLE)
        set_state("cold")
        return 130
    if "load_fail" in sc:
        err("error: the load feed did not engage. " + POWER_CYCLE)
        set_state("cold")
        return 1
    print("running the vendor load sequence ...", flush=True)
    time.sleep(speed())
    print("load sequence completed", flush=True)
    set_state("loaded")
    return 0


def cmd_load(args) -> int:
    sc = scenarios()
    bad = device_problem(sc)
    if bad is not None:
        return bad
    if "no_magazine" in sc:
        err("error: no magazine present in the slot (loader sensor clear)")
        return 1
    if args.next_strip:
        if "cold" in sc or get_state() == "cold":
            err("refused: --next-strip: the scanner is COLD (reg 0x01 = 0x00); a full load is needed first")
            return 1
        print("running the vendor load sequence ...", flush=True)
        time.sleep(speed())
        print("load sequence completed", flush=True)
        set_state("loaded")
        return 0
    return full_load(sc)


def cmd_eject(_args) -> int:
    sc = scenarios()
    bad = device_problem(sc)
    if bad is not None:
        return bad
    if "unsafe" in sc:
        err("refused: unsafe start state (reg 0x01 is neither 0x22 nor 0x00); power-cycle the scanner")
        return 1
    if "no_magazine" in sc:
        print("ejected", flush=True)          # the real driver also reports success when there is nothing to eject
        return 0
    print("ejecting ...", flush=True)
    time.sleep(speed())
    if "eject_fail" in sc:
        err("error: the eject did not complete. Power the scanner off and on again")
        set_state("cold")
        return 1
    print("ejected", flush=True)
    set_state("warm")
    return 0


def cmd_doctor(_args) -> int:
    print("DEMO driver: there is no hardware report without a scanner.")
    return 0


def parse_frames(spec: str) -> list[int]:
    frames: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-", 1))
            if hi < lo:
                raise ValueError(f"descending range {part!r}")
            frames.extend(range(lo, hi + 1))
        else:
            frames.append(int(part))
    if not frames or any(f < 1 or f > HOLDER_FRAMES for f in frames):
        raise ValueError(f"frames must be 1-{HOLDER_FRAMES}")
    return frames


def synthetic(frame: int, h: int, w: int, ir: bool = False) -> np.ndarray:
    """A plausible raw negative: orange film base, a darker/lighter blob per frame."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * (0.35 + 0.05 * frame), w * (0.3 + 0.07 * frame)
    blob = np.exp(-(((yy - cy) / (h * 0.3)) ** 2 + ((xx - cx) / (w * 0.25)) ** 2))
    if ir:
        return (60000 - 4000 * blob).astype(np.uint16)
    rgb = np.stack([52000 - 18000 * blob, 33000 - 14000 * blob, 21000 - 9000 * blob], axis=-1)
    rgb += (xx / w)[..., None] * 2500
    return np.clip(rgb, 0, 65535).astype(np.uint16)


def write_tiff(path: Path, arr: np.ndarray, dpi: int) -> None:
    photometric = "rgb" if arr.ndim == 3 else "minisblack"
    tifffile.imwrite(str(path), arr, photometric=photometric, compression=None, metadata=None,
                     resolution=(dpi, dpi), resolutionunit="INCH")


def roll_dirname(roll: int) -> str:
    return f"roll-{roll:03d}"


def next_roll(out: Path) -> int:
    nums = {int(m.group(1)) for p in out.glob("roll-*") if (m := re.fullmatch(r"roll-(\d+)", p.name))}
    for rec in read_manifest(out):
        if "roll" in rec:
            nums.add(int(rec["roll"]))
    return max(nums, default=0) + 1


def read_manifest(out: Path) -> list[dict]:
    p = out / MANIFEST
    if not p.exists():
        return []
    records = []
    for line in p.read_text().splitlines():
        try:
            records.append(json.loads(line))
        except ValueError:
            pass
    return records


def check_album_name(name: str) -> str:
    s = (name or "").strip()
    if not s or s in (".", "..") or "/" in s or "\\" in s or s == MANIFEST or re.search(r"roll-\d+$", s):
        raise ValueError(f"album name {name!r} is not a plain directory name")
    return s


def album_plan(out: Path, name: str) -> list[dict]:
    newest: dict = {}
    for r in read_manifest(out):
        if "roll" in r:
            newest[int(r["roll"])] = r
    items, n = [], 0
    for roll in sorted(newest):
        rec = newest[roll]
        if rec.get("album") != name:
            continue
        for e in sorted(rec.get("per_frame") or [], key=lambda x: int(x["frame"])):
            if e.get("film_present") is False:
                continue
            frame = int(e["frame"])
            path = out / roll_dirname(roll) / f"f{frame}.tiff"
            n += 1
            if path.is_file():
                items.append({"number": n, "prefix": "", "roll": roll, "frame": frame, "status": "delivered",
                              "source": str(path), "diag": str(path.with_name(f"f{frame}.diag.json"))})
            else:
                items.append({"number": n, "prefix": "", "roll": roll, "frame": frame, "status": "missing",
                              "source": None, "reason": e.get("coverage_reason") or "not delivered"})
    return items


def album_sync(out: Path, name: str) -> dict:
    d = out / check_album_name(name)
    d.mkdir(parents=True, exist_ok=True)
    for child in d.iterdir():
        if child.is_file() and re.fullmatch(r"\d{2,}(\.tiff|\.diag\.json)", child.name):
            child.unlink()
    items = album_plan(out, name)
    for it in items:
        if it["status"] != "delivered":
            continue
        for src, suffix in ((it["source"], ".tiff"), (it.get("diag"), ".diag.json")):
            if src and Path(src).is_file():
                dst = d / f"{it['number']:02d}{suffix}"
                try:
                    os.link(src, dst)
                except OSError:
                    shutil.copy2(src, dst)
    index = {
        "album": name,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "images": [{k: v for k, v in it.items() if k != "diag"} for it in items],
        "delivered": sum(1 for it in items if it["status"] == "delivered"),
        "missing": [it["number"] for it in items if it["status"] == "missing"],
    }
    (d / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    return index


def cmd_digitize(args) -> int:
    sc = scenarios()
    bad = device_problem(sc)
    if bad is not None:
        return bad
    try:
        frames = parse_frames(args.frames)
        album = check_album_name(args.album) if args.album else None
    except ValueError as e:
        err(f"error: {e}")
        return 2
    if "no_magazine" in sc:
        err("error: no magazine present in the slot (loader sensor clear)")
        return 1
    if args.assume_loaded:
        if get_state() != "loaded":
            err("refused: --assume-loaded: the scanner is not loaded")
            return 1
    else:
        rc = full_load(sc)
        if rc:
            return rc
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    roll = next_roll(out)
    rdir = out / roll_dirname(roll)
    rdir.mkdir()
    print(f"=== digitize roll {roll} -> {rdir} ===", flush=True)

    scale = max(1, args.dpi // 600)
    h, w = 120 * scale // 2 + 120, 180 * scale // 2 + 180
    per_frame, images, code = [], [], 0
    empty_from = int(sc["empty_from"]) if sc.get("empty_from") else None
    cov_fail = int(sc["coverage_fail"]) if sc.get("coverage_fail") else None
    fail_at = int(sc["scan_fail"]) if sc.get("scan_fail") else None
    failed = False
    try:
        for f in frames:
            time.sleep(speed())
            if fail_at == f:
                err(f"error: frame {f}: the scan did not complete. " + POWER_CYCLE)
                set_state("cold")
                failed, code = True, 1
                break
            if empty_from is not None and f >= empty_from:
                per_frame.append({"frame": f, "film_present": False})
                print(f"stopping: empty aperture at frame {f} after film; the remaining frames are skipped",
                      flush=True)
                break
            write_tiff(rdir / f"f{f}.overscan.tiff", synthetic(f, h + 20, w + 20), args.dpi)
            if cov_fail == f:
                print(f"warning: frame {f}: coverage not verified; only the overscan file was written "
                      f"(of135i recrop can retry)", flush=True)
                per_frame.append({"frame": f, "film_present": True, "coverage_reason": "coverage not verified"})
                code = 4
                continue
            if args.ir:
                write_tiff(rdir / f"f{f}-ir.overscan.tiff", synthetic(f, h + 20, w + 20, ir=True), args.dpi)
                write_tiff(rdir / f"f{f}-ir.tiff", synthetic(f, h, w, ir=True), args.dpi)
            write_tiff(rdir / f"f{f}.tiff", synthetic(f, h, w), args.dpi)
            (rdir / f"f{f}.diag.json").write_text(json.dumps({"frame": f, "demo": True}) + "\n")
            print(f"wrote {rdir / f'f{f}.tiff'} ({w}x{h}, 16-bit RGB, aperture-registered)", flush=True)
            per_frame.append({"frame": f, "film_present": True, "main": str(rdir / f"f{f}.tiff")})
            images.append(f)
    except KeyboardInterrupt:
        err("interrupted. " + POWER_CYCLE)
        set_state("cold")
        failed, code = True, 130

    record = {"roll": roll, "prefix": "", "dir": str(rdir), "album": album, "dpi": args.dpi,
              "status": "failed" if failed else "ok", "per_frame": per_frame}
    with open(out / MANIFEST, "a") as fh:
        fh.write(json.dumps(record) + "\n")
    if album:
        index = album_sync(out, album)
        print(f"album {album}: this strip is {[i['number'] for i in index['images'] if i['roll'] == roll]}",
              flush=True)
    if failed:
        return code
    print("ejected", flush=True)
    set_state("warm")
    print(f"roll {roll} done: {len(images)} frames -> {rdir}", flush=True)
    return code


# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="of135i")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version").set_defaults(func=cmd_version)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("eject").set_defaults(func=cmd_eject)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    load = sub.add_parser("load")
    load.add_argument("--next-strip", action="store_true")
    load.set_defaults(func=cmd_load)
    dig = sub.add_parser("digitize")
    dig.add_argument("-o", "--out", required=True)
    dig.add_argument("--album")
    dig.add_argument("--frames", default="1-4")
    dig.add_argument("--dpi", type=int, choices=DPI_CHOICES, default=3600)
    dig.add_argument("--no-ir", dest="ir", action="store_false")
    dig.add_argument("--no-clean", action="store_true")
    dig.add_argument("--rotate", type=int, choices=(0, 90, 180, 270), default=0)
    dig.add_argument("--no-cal-data", action="store_true")
    dig.add_argument("--position-offset", type=float)
    dig.add_argument("--assume-loaded", action="store_true")
    dig.set_defaults(func=cmd_digitize)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        err("interrupted. " + POWER_CYCLE)
        set_state("cold")
        return 130
