"""The main window driven like a user would, offscreen, against the demo driver."""

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QCheckBox, QLabel  # noqa: E402

from filmdeck import i18n  # noqa: E402
from filmdeck.core.config import Settings  # noqa: E402
from filmdeck.ui import style  # noqa: E402
from filmdeck.ui.dialogs import InfoDialog  # noqa: E402
from filmdeck.ui.mainwindow import MainWindow  # noqa: E402


@pytest.fixture(scope="session")
def app():
    app = QApplication.instance() or QApplication([])
    style.apply(app)
    return app


@pytest.fixture
def window(app, demo, tmp_path):
    i18n.set_language("en")
    settings = Settings(scan_dir=str(tmp_path / "scans"), preview_size=160, language="en")
    w = MainWindow(settings, autostart=False)
    w.resize(1280, 800)
    w.show()
    yield w
    w._session = None
    w.close()
    i18n.set_language("de")


def pump(app, until, timeout=30.0, answer=None):
    """Run the event loop until ``until()``; ``answer(dialog)`` may react to every open dialog once."""
    end = time.time() + timeout
    seen = set()
    while time.time() < end:
        app.processEvents()
        if answer:
            for dlg in list(window_dialogs(app)):
                if id(dlg) not in seen:
                    seen.add(id(dlg))
                    answer(dlg)
        if until():
            return True
        time.sleep(0.01)
    return False


def window_dialogs(app):
    return [w for w in app.topLevelWidgets() if isinstance(w, InfoDialog) and w.isVisible()]


def press(dialog, key):
    dialog.button(key).click()


def test_form_defaults_and_choices(window):
    assert window.ed_name.text().count("-") == 1 and len(window.ed_name.text()) == 5        # YY-MM
    assert window.frames.selected() == [1, 2, 3, 4, 5, 6]
    assert [window.cb_bits.itemData(i) for i in range(window.cb_bits.count())] == [48, 24, 16, 8]
    assert [window.cb_dpi.itemData(i) for i in range(window.cb_dpi.count())] == [600, 1200, 2400, 3600, 7200]
    assert window.cb_film.count() == 2 and window.cb_camera.count() == 0
    assert window.btn_start.isEnabled() and not window.btn_negpy.isEnabled()


def test_name_follows_film_and_camera_until_edited(window):
    window.cb_film.setEditText("Kodak Gold")
    window.cb_camera.setEditText("Nikon F3")
    assert window.ed_name.text().endswith("-Kodak_Gold-Nikon_F3")
    window.ed_name.setText("my-own")
    window.ed_name.textEdited.emit("my-own")
    window.cb_film.setEditText("Portra")
    assert window.ed_name.text() == "my-own"
    window.btn_name_auto.click()
    assert window.ed_name.text().endswith("-Portra-Nikon_F3")


def test_frame_toggles_keep_one_selected(window):
    for n in (1, 2, 3, 4, 5):
        window.frames._buttons[n].setChecked(False)
    assert window.frames.selected() == [6]
    window.frames._buttons[6].setChecked(False)
    assert window.frames.selected() == [6]
    window.frames._buttons[1].setChecked(True)
    assert window.frames.selected() == [1, 6]


def test_dpi_7200_shows_warning_and_size_follows_bits(window):
    window.cb_dpi.setCurrentIndex(window.cb_dpi.findData(3600))
    window.cb_bits.setCurrentIndex(window.cb_bits.findData(48))
    assert "104 MB" in window.lb_size.text() and "7200" not in window.lb_size.text()
    window.cb_bits.setCurrentIndex(window.cb_bits.findData(8))
    assert "17 MB" in window.lb_size.text()
    window.cb_dpi.setCurrentIndex(window.cb_dpi.findData(7200))
    assert "7200" in window.lb_size.text()


def test_language_switch_retranslates(window):
    assert window.btn_start.text().endswith("Scan strip")
    i18n.set_language("de")
    window.retranslate()
    assert window.btn_start.text().endswith("Streifen scannen") and window.lb_name.text() == "Name / Ordner"
    i18n.set_language("en")
    window.retranslate()
    assert window.lb_frames.text() == "Frames to scan"
    window._on_mode(1)
    assert window.lb_frames.text() == "Frames of strip 1" and window.btn_start.text().endswith("Scan whole film")


def test_strip_scan_with_chosen_frames(app, window, tmp_path):
    window.cb_film.setEditText("Kodak Gold")
    window.cb_camera.setEditText("Nikon F3")
    window.frames.set_selected([2, 3, 6])
    window.btn_c41.setChecked(True)
    window.cb_dpi.setCurrentIndex(window.cb_dpi.findData(600))
    window.cb_bits.setCurrentIndex(window.cb_bits.findData(24))
    window.btn_start.click()
    assert window._session is not None and not window.btn_start.isVisible() and window.btn_cancel.isVisible()
    assert not window.btn_options.isEnabled() and not window.btn_eject.isEnabled()

    def answer(dlg):
        press(dlg, "go")                                  # "film holder is at the stop"

    assert pump(app, lambda: window._session is None, answer=answer), window.lb_status.text()
    folder = window._last_dir
    assert folder is not None and folder.name.endswith("-Kodak_Gold-Nikon_F3")
    files = sorted(p.name for p in folder.glob("*.tiff"))
    assert len(files) == 6 and files[0].endswith("_01.tiff") and files[1].endswith("_01_ir.tiff")      # 3 images + IR
    assert window.frame_list.count() == 3 and window.frame_list.labels() == ["01", "02", "03"]
    assert window.lb_status.text() == "Scan finished" and window.btn_negpy.isEnabled() and window.btn_folder.isEnabled()
    assert window.btn_start.isVisible() and window.btn_options.isEnabled() and window.btn_eject.isEnabled()
    import tifffile
    arr = tifffile.imread(str(folder / files[0]))
    assert arr.dtype.name == "uint8" and arr.ndim == 3                                              # 24 bit chosen
    assert (folder / ".previews").is_dir()


def test_film_scan_two_strips_with_frame_choice(app, window):
    window.cb_film.setEditText("Harman")
    window._on_mode(1)
    window.btn_mode_film.setChecked(True)
    window.frames.set_selected([3, 4])
    window.cb_dpi.setCurrentIndex(window.cb_dpi.findData(600))
    window.btn_start.click()
    asked = []

    def answer(dlg):
        if "dlg_next" in dlg.windowTitle() or dlg.windowTitle() == "Next strip":
            asked.append(dlg)
            toggles = dlg.findChildren(type(window.frames))[0]
            assert toggles.selected() == [1, 2, 3, 4, 5, 6]
            toggles.set_selected([1, 2])
            press(dlg, "next" if len(asked) == 1 else "finish")
        else:
            press(dlg, "go")

    assert pump(app, lambda: window._session is None, answer=answer), window.lb_status.text()
    assert len(asked) == 2
    assert window.frame_list.count() == 2 + 2 and window.frame_list.labels() == ["01", "02", "03", "04"]
    assert window.lb_status.text() == "Scan finished"


def test_cancel_needs_confirmation_and_demands_power_cycle(app, window):
    window.btn_start.click()
    pump(app, lambda: bool(window_dialogs(app)), 10)
    reinsert = window_dialogs(app)[0]
    press(reinsert, "go")
    pump(app, lambda: window.frame_list.count() >= 1, 20)
    window.btn_cancel.click()
    pump(app, lambda: any(d.windowTitle() == "Cancel the scan?" for d in window_dialogs(app)), 5)
    dlg = [d for d in window_dialogs(app) if d.windowTitle() == "Cancel the scan?"][0]
    press(dlg, "stop")
    seen = []

    def answer(d):
        seen.append(d.windowTitle())
        press(d, "later")

    assert pump(app, lambda: window._session is None, 20, answer=answer)
    pump(app, lambda: "Restart the scanner" in seen, 5, answer=answer)
    assert "Restart the scanner" in seen and window._power_cycle_required
    window.btn_start.click()                                   # blocked until the user confirms the restart
    assert window._session is None
    pump(app, lambda: any(d.windowTitle() == "Restart the scanner" for d in window_dialogs(app)), 5)
    press([d for d in window_dialogs(app) if d.windowTitle() == "Restart the scanner"][0], "done")
    assert not window._power_cycle_required


def test_eject_needs_the_confirmation_checkbox(app, window):
    window.btn_eject.click()
    pump(app, lambda: bool(window_dialogs(app)), 5)
    dlg = window_dialogs(app)[0]
    assert dlg.windowTitle() == "Eject the film holder" and not dlg.button("go").isEnabled()
    dlg.findChildren(QCheckBox)[0].setChecked(True)
    assert dlg.button("go").isEnabled()
    press(dlg, "go")
    assert pump(app, lambda: window.lb_status.text() == "Film holder ejected", 20), window.lb_status.text()
    assert pump(app, lambda: not window._checking, 10)                    # the scanner is looked at again afterwards
    assert not window._ejecting and window.btn_start.isEnabled() and window.btn_eject.isEnabled()


def test_eject_failure_demands_power_cycle(app, window, monkeypatch):
    monkeypatch.setenv("OF135I_DEMO_SCENARIO", "eject_fail")
    window.btn_eject.click()
    pump(app, lambda: bool(window_dialogs(app)), 5)
    dlg = window_dialogs(app)[0]
    dlg.findChildren(QCheckBox)[0].setChecked(True)
    press(dlg, "go")
    assert pump(app, lambda: window.lb_status.text() == "Eject failed", 20), window.lb_status.text()
    pump(app, lambda: any(d.windowTitle() == "Restart the scanner" for d in window_dialogs(app)), 5)
    assert window._power_cycle_required
    for d in window_dialogs(app):
        press(d, "later")


def test_scanner_check_shows_state(app, window, monkeypatch):
    window._check_scanner()
    assert pump(app, lambda: not window._checking, 10)
    assert window.lb_scanner.text() == "Scanner ready – film holder detected"
    monkeypatch.setenv("OF135I_DEMO_SCENARIO", "no_scanner")
    window._check_scanner()
    assert pump(app, lambda: not window._checking, 10)
    assert window.lb_scanner.text() == "No scanner found"


def test_scan_errors_are_explained(app, window, monkeypatch):
    monkeypatch.setenv("OF135I_DEMO_SCENARIO", "no_magazine")
    window.btn_start.click()
    assert pump(app, lambda: window._session is None, 20)
    assert pump(app, lambda: not window._checking, 10)
    assert window.lb_status.text() == "No film holder detected" and window.btn_start.isEnabled()
    assert not window._power_cycle_required


def test_close_is_blocked_while_scanning(app, window):
    window.btn_start.click()
    assert window._session is not None
    assert window.close() is False
    pump(app, lambda: bool(window_dialogs(app)), 10)
    press(window_dialogs(app)[0], "abort")
    pump(app, lambda: window._session is None, 20, answer=lambda d: press(d, "later"))


def test_options_dialog_roundtrip_and_offset_parsing(app, window):
    window._open_options()
    pump(app, lambda: window._options is not None, 5)
    dlg = window._options
    values = dlg.values()
    assert values.position_offset_mm is None and values.films == window.settings.films
    dlg.ck_offset_default.setChecked(False)
    for typed, expected in (("0,35", 0.35), ("-1.5", -1.5), ("9", 5.0), ("-", None)):
        dlg.ed_offset.setText(typed)
        assert dlg.values().position_offset_mm == expected, typed
    dlg.ed_offset.setText("0,2")
    dlg.accept()
    app.processEvents()
    assert window.settings.position_offset_mm == 0.2
    window._open_options()
    pump(app, lambda: window._options is not None, 5)
    assert window._options.ed_offset.text() == "0.20" and not window._options.ck_offset_default.isChecked()
    window._options.reject()


def test_selftest_passes_with_the_demo_driver(app):
    from filmdeck import selftest
    lines = []
    assert selftest.run(lines.append) in (0, 1)
    assert not any("demo scan" in p and "PROBLEM" in p for p in lines), lines
    assert any(l.startswith("window: ok") for l in lines) and any(l.startswith("demo scan: ok, 2 images") for l in lines), lines


def test_refused_frame_is_explained_and_the_advised_offset_can_be_applied(app, window, monkeypatch):
    monkeypatch.setenv("OF135I_DEMO_SCENARIO", "early:0.5,tight:3")
    window.frames.set_selected([1, 2, 3, 4])
    window.cb_dpi.setCurrentIndex(window.cb_dpi.findData(600))
    window.btn_start.click()
    shown = []

    def answer(dlg):
        if "go" in dlg._buttons:
            press(dlg, "go")
        else:
            shown.append(dlg)

    assert pump(app, lambda: window._session is None and bool(shown), 30, answer=answer), window.lb_status.text()
    dlg = shown[0]
    text = "\n".join(label.text() for label in dlg.findChildren(QLabel))
    assert dlg.windowTitle() == "Image 03 is missing"
    assert "start of the film opening was too close" in text and "_03_overscan.tiff" in text
    assert "about 0.5 mm earlier than the driver assumes" in text and "to −0.5 mm" in text
    assert window.settings.position_offset_mm is None and "apply" in dlg._buttons
    press(dlg, "apply")
    assert window.settings.position_offset_mm == -0.5
    assert window.lb_status.text() == "Frame shift set to −0.5 mm"
    from filmdeck.core.config import Settings as _S
    assert _S.load().position_offset_mm == -0.5            # saved, not only in memory


def test_mode_switch_sits_in_the_settings_panel_above_the_name(app, window):
    form_panel = window.btn_mode_strip.parentWidget()
    assert form_panel is window.btn_mode_film.parentWidget()
    assert window.ed_name.window() is window and form_panel.isAncestorOf(window.ed_name)
    assert window.btn_mode_strip.mapTo(window, window.btn_mode_strip.rect().topLeft()).y() < \
        window.ed_name.mapTo(window, window.ed_name.rect().topLeft()).y()
    assert window.btn_options.mapTo(window, window.btn_options.rect().topLeft()).y() < \
        window.btn_mode_strip.mapTo(window, window.btn_mode_strip.rect().topLeft()).y()


def test_black_and_white_button_shows_its_ampersand(app, window):
    from filmdeck import i18n
    try:
        i18n.set_language("en")
        window.retranslate()
        # Qt writes one visible "&" in a button as "&&"; a single one would underline the next letter instead
        assert window.btn_bw.text() == "Black && White"
    finally:
        i18n.set_language("de")
        window.retranslate()


def test_window_icon_file_ships_with_the_package():
    from pathlib import Path

    import filmdeck
    icon = Path(filmdeck.__file__).with_name("filmdeck.png")
    assert icon.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
