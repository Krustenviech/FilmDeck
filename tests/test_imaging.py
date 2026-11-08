import numpy as np
import pytest
import tifffile

from filmdeck.core import imaging


def write16(path, arr, dpi=(3600, 3600)):
    tifffile.imwrite(str(path), arr, photometric="rgb", compression=None, metadata=None,
                     resolution=dpi, resolutionunit="INCH")


@pytest.fixture
def src(tmp_path):
    rng = np.random.default_rng(1)
    arr = rng.integers(0, 65536, (40, 60, 3), dtype=np.uint16)
    arr[0, 0] = (0, 0, 0)
    arr[0, 1] = (65535, 65535, 65535)
    p = tmp_path / "f1.tiff"
    write16(p, arr, (2400, 3600))
    return p, arr


def test_rgb8_values(src, tmp_path):
    p, arr = src
    out = tmp_path / "o.tiff"
    imaging.convert_tiff(p, out, 24)
    got = tifffile.imread(str(out))
    assert got.dtype == np.uint8 and got.shape == arr.shape
    assert tuple(got[0, 0]) == (0, 0, 0) and tuple(got[0, 1]) == (255, 255, 255)
    expected = np.rint(arr.astype(np.float64) * 255 / 65535).astype(np.uint8)
    assert np.abs(got.astype(int) - expected.astype(int)).max() <= 1


def test_gray16_values_and_resolution(src, tmp_path):
    p, arr = src
    out = tmp_path / "g.tiff"
    imaging.convert_tiff(p, out, 16)
    got = tifffile.imread(str(out))
    assert got.dtype == np.uint16 and got.shape == arr.shape[:2]
    assert got[0, 0] == 0 and got[0, 1] == 65535
    assert np.abs(got.astype(np.int64) - np.rint(arr.astype(np.float64).mean(axis=2))).max() <= 1
    x, y, unit = imaging.read_resolution(out)
    assert (x[0] / x[1], y[0] / y[1]) == (2400.0, 3600.0) and unit == "INCH"
    with tifffile.TiffFile(str(out)) as tf:
        assert tf.pages[0].photometric.name == "MINISBLACK"


def test_convert_many_rows_exercises_chunking(tmp_path):
    arr = np.full((1300, 8, 3), 40000, dtype=np.uint16)
    p = tmp_path / "big.tiff"
    write16(p, arr)
    imaging.convert_tiff(p, tmp_path / "o.tiff", 16)
    assert (tifffile.imread(str(tmp_path / "o.tiff")) == 40000).all()


def test_convert_rejects_wrong_input(tmp_path):
    p = tmp_path / "gray.tiff"
    tifffile.imwrite(str(p), np.zeros((4, 4), np.uint16))
    with pytest.raises(imaging.ImagingError):
        imaging.convert_tiff(p, tmp_path / "o.tiff", 24)
    assert not (tmp_path / "o.tiff").exists() and not (tmp_path / "o.tiff.partial").exists()
    with pytest.raises(ValueError):
        imaging.convert_tiff(p, tmp_path / "o.tiff", 48)


def test_preview(src, tmp_path):
    p, _ = src
    img = imaging.make_preview(p, 32)
    assert max(img.size) <= 32 and img.mode == "RGB"
    dst = tmp_path / "sub" / "p.jpg"
    imaging.save_preview_jpeg(p, dst, 32)
    assert dst.stat().st_size > 0 and not list(dst.parent.glob("*.partial"))
    flat = tmp_path / "flat.tiff"
    write16(flat, np.full((20, 20, 3), 1000, np.uint16))
    assert imaging.make_preview(flat, 16).size[0] <= 16   # a flat image must not divide by zero


def test_gray8_values_resolution_and_bounds(src, tmp_path):
    p, arr = src
    out = tmp_path / "g8.tiff"
    imaging.convert_tiff(p, out, 8)
    got = tifffile.imread(str(out))
    assert got.dtype == np.uint8 and got.shape == arr.shape[:2]
    assert got[0, 0] == 0 and got[0, 1] == 255
    expected = np.rint(arr.astype(np.float64).mean(axis=2) * 255 / 65535)
    assert np.abs(got.astype(int) - expected).max() <= 1
    x, y, _unit = imaging.read_resolution(out)
    assert (x[0] / x[1], y[0] / y[1]) == (2400.0, 3600.0)


def test_convert_refuses_48_bit(src, tmp_path):
    p, _ = src
    with pytest.raises(ValueError):
        imaging.convert_tiff(p, tmp_path / "x.tiff", 48)
