import datetime as dt
import json

from filmdeck.core import naming
from filmdeck.core.config import Settings


def test_defaults_are_valid_and_roundtrip(tmp_path):
    s = Settings()
    assert (s.dpi, s.bit_depth, s.film_type, s.language) == (3600, 48, "c41", "de")
    assert s.use_ir and s.films == ["Kodak Gold", "Harman Phoenix II"] and s.cameras == []
    path = tmp_path / "s.json"
    s.film_type, s.dpi, s.position_offset_mm = "bw", 1200, 0.4
    s.add_preset("cameras", "Nikon F3")
    s.save(path)
    again = Settings.load(path)
    assert again.to_dict() == s.to_dict() and not again.use_ir


def test_invalid_values_fall_back_per_field(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"dpi": 5000, "bit_depth": 24, "language": "fr", "frames": [9],
                                "films": ["A", "A", " B  C "], "cameras": "x", "unknown": 1,
                                "position_offset_mm": 99, "check_updates": "yes", "film_type": True}))
    s = Settings.load(path)
    assert s.dpi == 3600 and s.bit_depth == 24 and s.language == "de" and s.frames == [1, 2, 3, 4, 5, 6]
    assert s.films == ["A", "B C"] and s.cameras == [] and s.position_offset_mm is None
    assert s.check_updates is True and s.film_type == "c41"


def test_broken_or_missing_file_gives_defaults(tmp_path):
    assert Settings.load(tmp_path / "none.json").to_dict() == Settings().to_dict()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert Settings.load(bad).to_dict() == Settings().to_dict()


def test_presets():
    s = Settings()
    assert s.add_preset("films", "  Ilford   HP5 ") and "Ilford HP5" in s.films
    assert not s.add_preset("films", "Ilford HP5") and not s.add_preset("films", "   ")
    assert s.remove_preset("films", "Ilford HP5") and not s.remove_preset("films", "Ilford HP5")


def test_compose_name():
    d = dt.date(2026, 11, 7)
    assert naming.compose_name("Kodak Gold", "Nikon F3", d) == "26-11-Kodak_Gold-Nikon_F3"
    assert naming.compose_name("", "", d) == "26-11"
    assert naming.compose_name("Harman Phoenix II", "", d) == "26-11-Harman_Phoenix_II"


def test_sanitize():
    assert naming.sanitize_name("26-11-A/B:C*?") == "26-11-ABC"
    assert naming.sanitize_name("  my film  --  x ") == "my_film_-_x"
    assert naming.sanitize_name("../..") == ""
    assert naming.sanitize_name(".hidden") == "hidden"
    assert len(naming.sanitize_name("x" * 300)) <= naming.MAX_NAME_LENGTH
    assert naming.image_filename("n", 3) == "n_03.tiff"
    assert naming.image_filename("n", 12, "_ir") == "n_12_ir.tiff"
    assert naming.image_filename("n", 123) == "n_123.tiff"


def test_frames_setting_is_sorted_unique_and_validated(tmp_path):
    assert Settings.from_dict({"frames": [6, 2, 2, 1]}).frames == [1, 2, 6]
    for bad in ([], [0], [7], ["1"], [True], 3, "1-6"):
        assert Settings.from_dict({"frames": bad}).frames == [1, 2, 3, 4, 5, 6], bad
    assert Settings.from_dict({"bit_depth": 8}).bit_depth == 8 and Settings.from_dict({"bit_depth": 32}).bit_depth == 48
