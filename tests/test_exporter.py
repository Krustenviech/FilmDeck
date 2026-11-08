import os

import numpy as np
import tifffile

from filmdeck.core import exporter
from tests.conftest import make_demo_stage


def run_export(stage, album, final, **kw):
    args = dict(bits=48, export_ir=True, keep_overscan=False, preview_size=160)
    args.update(kw)
    return exporter.export_album(stage, album, final, **args)


def test_export_48bit_links_and_cleans(tmp_path, monkeypatch):
    stage, album = make_demo_stage(tmp_path, monkeypatch, frames="1-3")
    final = tmp_path / "final"
    r = run_export(stage, album, final)
    assert r.index_found and [i.number for i in r.images] == [1, 2, 3] and not r.missing and not r.warnings
    names = sorted(p.name for p in final.iterdir())
    assert names == [".previews", "film_01.tiff", "film_01_ir.tiff", "film_02.tiff", "film_02_ir.tiff",
                     "film_03.tiff", "film_03_ir.tiff"]
    assert sorted(p.name for p in (final / ".previews").iterdir()) == ["film_01.jpg", "film_02.jpg", "film_03.jpg"]
    src = stage / "roll-001" / "f1.tiff"
    assert os.path.samefile(src, final / "film_01.tiff")          # hard link, no second copy
    roll = stage / "roll-001"
    assert not list(roll.glob("*.overscan.tiff")) and (roll / "f1.tiff").exists() and (roll / "f1-ir.tiff").exists()
    assert tifffile.imread(str(final / "film_01.tiff")).dtype == np.uint16
    assert tifffile.imread(str(final / "film_01_ir.tiff")).ndim == 2


def test_export_is_idempotent_and_keeps_existing(tmp_path, monkeypatch):
    stage, album = make_demo_stage(tmp_path, monkeypatch)
    final = tmp_path / "final"
    first = run_export(stage, album, final)
    assert len(first.new_images) == 3
    again = run_export(stage, album, final)
    assert len(again.images) == 3 and not again.new_images and not again.warnings


def test_export_24_and_16_bit(tmp_path, monkeypatch):
    stage, album = make_demo_stage(tmp_path, monkeypatch, frames="1-2")
    rgb8 = run_export(stage, album, tmp_path / "f24", bits=24)
    assert tifffile.imread(str(rgb8.images[0].path)).dtype == np.uint8
    assert not os.path.samefile(stage / "roll-001" / "f1.tiff", rgb8.images[0].path)
    g16 = run_export(stage, album, tmp_path / "f16", bits=16)
    arr = tifffile.imread(str(g16.images[1].path))
    assert arr.dtype == np.uint16 and arr.ndim == 2
    # the driver's own 48-bit files are untouched
    assert tifffile.imread(str(stage / "roll-001" / "f1.tiff")).shape[2] == 3


def test_export_options_off(tmp_path, monkeypatch):
    stage, album = make_demo_stage(tmp_path, monkeypatch, frames="1-2")
    final = tmp_path / "final"
    r = run_export(stage, album, final, export_ir=False, keep_overscan=True, preview_size=0)
    assert sorted(p.name for p in final.iterdir()) == ["film_01.tiff", "film_02.tiff"]
    assert len(list((stage / "roll-001").glob("*.overscan.tiff"))) == 4     # image + IR overscan, 2 frames
    assert all(i.ir_path is None and i.preview is None for i in r.images)


def test_two_strips_numbered_through(tmp_path, monkeypatch):
    stage, album = make_demo_stage(tmp_path, monkeypatch, frames="1-3", strips=2)
    r = run_export(stage, album, tmp_path / "final")
    assert [i.number for i in r.images] == [1, 2, 3, 4, 5, 6]
    assert r.images[3].source.parent.name == "roll-002"


def test_missing_frame_reserves_number(tmp_path, monkeypatch):
    monkeypatch.setenv("OF135I_DEMO_SCENARIO", "coverage_fail:2")
    import subprocess
    from filmdeck.core import driver as drv
    from filmdeck.core.config import Settings
    monkeypatch.setenv("FILMDECK_DEMO", "1")
    monkeypatch.setenv("OF135I_DEMO_STATE", str(tmp_path / "st"))
    monkeypatch.setenv("OF135I_DEMO_SPEED", "0")
    d = drv.locate(Settings())
    stage = tmp_path / "stage"
    p = subprocess.run(drv.digitize_argv(drv.DigitizeOptions(str(stage), "film", "1-3", 600, True)),
                       env=drv.environment(d), input="\n", capture_output=True, text=True)
    assert p.returncode == 4
    r = run_export(stage, "film", tmp_path / "final")
    assert [i.number for i in r.images] == [1, 3] and [(m.number, m.reason) for m in r.missing] == [
        (2, "coverage not verified")]
    # the overscan file of the undelivered frame must survive (recrop needs it)
    assert (stage / "roll-001" / "f2.overscan.tiff").exists()


def test_no_index_and_stale_partials(tmp_path):
    final = tmp_path / "final"
    final.mkdir()
    (final / "x.tiff.partial").write_bytes(b"1")
    r = exporter.export_album(tmp_path / "nothing", "film", final, bits=48, export_ir=True,
                              keep_overscan=False, preview_size=0)
    assert not r.index_found and not r.images
    assert (final / "x.tiff.partial").exists()        # nothing to do without an index: touch nothing
