"""The options dialog. Edits a copy of the settings; the caller applies it on OK."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import QGuiApplication, QRegularExpressionValidator
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPlainTextEdit,
                               QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget)

from .. import DRIVER_URL
from ..core import external, paths
from ..core.config import ROTATE_CHOICES, Settings
from ..core.driver import Driver
from ..i18n import tr


def _page() -> tuple[QScrollArea, QVBoxLayout]:
    """A scrollable tab page (the options must stay usable on a small window)."""
    inner = QWidget()
    lay = QVBoxLayout(inner)
    lay.setContentsMargins(18, 16, 18, 16)
    lay.setSpacing(12)
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.NoFrame)
    area.setWidget(inner)
    return area, lay


def _row(*widgets, stretch_index: int = 0) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(10)
    for i, w in enumerate(widgets):
        row.addWidget(w, 1 if i == stretch_index else 0)
    return row


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setProperty("muted", True)
    return label


class OptionsDialog(QDialog):
    check_updates_requested = Signal()
    rollback_requested = Signal()
    doctor_requested = Signal()

    def __init__(self, parent, settings: Settings, driver: Driver | None, *, busy: bool, update_state: dict):
        super().__init__(parent)
        self.setWindowTitle(tr("opt.title"))
        self.setModal(True)
        self.resize(900, 620)
        self._settings = dataclasses.replace(settings, films=list(settings.films), cameras=list(settings.cameras))
        self._driver = driver
        self._driver_path = settings.driver_path
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 12)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        self.tabs.addTab(self._general_tab(), tr("opt.tab.general"))
        self.tabs.addTab(self._scan_tab(), tr("opt.tab.scan"))
        self.tabs.addTab(self._files_tab(), tr("opt.tab.files"))
        self.tabs.addTab(self._presets_tab(), tr("opt.tab.presets"))
        self.tabs.addTab(self._driver_tab(busy, update_state), tr("opt.tab.driver"))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr("opt.ok"))
        buttons.button(QDialogButtonBox.Ok).setObjectName("primary")
        buttons.button(QDialogButtonBox.Cancel).setText(tr("opt.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    # ------------------------------------------------------------------ tabs
    def _general_tab(self) -> QWidget:
        s = self._settings
        page, lay = _page()
        lay.addWidget(QLabel(tr("opt.language")))
        self.cb_language = QComboBox()
        self.cb_language.addItem("Deutsch", "de")
        self.cb_language.addItem("English", "en")
        self.cb_language.setCurrentIndex(self.cb_language.findData(s.language))
        lay.addWidget(self.cb_language)

        lay.addWidget(QLabel(tr("opt.scan_dir")))
        self.ed_scan_dir = QLineEdit(s.scan_dir)
        self.ed_scan_dir.setPlaceholderText(str(paths.default_scan_dir()))
        browse = QPushButton(tr("opt.browse"))
        browse.clicked.connect(lambda: self._pick_dir(self.ed_scan_dir))
        lay.addLayout(_row(self.ed_scan_dir, browse))

        lay.addWidget(QLabel(tr("opt.negpy")))
        self.ed_negpy = QLineEdit(s.negpy_path)
        found = external.find_negpy("")
        self.ed_negpy.setPlaceholderText(str(found) if found else tr("opt.negpy_none"))
        pick = QPushButton(tr("opt.browse"))
        pick.clicked.connect(self._pick_negpy)
        lay.addLayout(_row(self.ed_negpy, pick))
        lay.addWidget(_hint(tr("opt.negpy_hint")))

        self.ck_updates = QCheckBox(tr("opt.check_updates"))
        self.ck_updates.setChecked(s.check_updates)
        lay.addWidget(self.ck_updates)
        lay.addWidget(QLabel(tr("opt.channel")))
        self.cb_channel = QComboBox()
        self.cb_channel.addItem(tr("opt.channel.release"), "release")
        self.cb_channel.addItem(tr("opt.channel.master"), "master")
        self.cb_channel.setCurrentIndex(self.cb_channel.findData(s.update_channel))
        lay.addWidget(self.cb_channel)
        lay.addWidget(_hint(tr("opt.channel_hint")))
        lay.addStretch(1)
        return page

    def _scan_tab(self) -> QWidget:
        s = self._settings
        page, lay = _page()
        lay.addWidget(QLabel(tr("opt.rotate")))
        self.cb_rotate = QComboBox()
        for deg in ROTATE_CHOICES:
            self.cb_rotate.addItem(f"{deg}°", deg)
        self.cb_rotate.setCurrentIndex(self.cb_rotate.findData(s.rotate))
        lay.addWidget(self.cb_rotate)
        lay.addWidget(_hint(tr("opt.rotate_hint")))

        self.ck_dust = QCheckBox(tr("opt.dust"))
        self.ck_dust.setChecked(s.dust_clean)
        lay.addWidget(self.ck_dust)
        lay.addWidget(_hint(tr("opt.dust_hint")))

        self.ck_fast = QCheckBox(tr("opt.fast_next"))
        self.ck_fast.setChecked(s.fast_next_strip)
        lay.addWidget(self.ck_fast)
        lay.addWidget(_hint(tr("opt.fast_next_hint")))

        self.ck_offset_default = QCheckBox(tr("opt.offset_default"))
        self.ck_offset_default.setChecked(s.position_offset_mm is None)
        self.ed_offset = QLineEdit(f"{(s.position_offset_mm or 0.0):.2f}")
        self.ed_offset.setValidator(QRegularExpressionValidator(QRegularExpression(r"^-?\d?[.,]?\d{0,2}$")))
        self.ed_offset.setMaximumWidth(140)
        self.ed_offset.setEnabled(s.position_offset_mm is not None)
        self.ck_offset_default.toggled.connect(lambda on: self.ed_offset.setEnabled(not on))
        lay.addWidget(QLabel(tr("opt.offset")))
        lay.addLayout(_row(self.ck_offset_default, self.ed_offset, QLabel("mm"), stretch_index=0))
        lay.addWidget(_hint(tr("opt.offset_hint")))
        lay.addStretch(1)
        return page

    def _files_tab(self) -> QWidget:
        s = self._settings
        page, lay = _page()
        lay.addWidget(QLabel(tr("opt.preview")))
        self.cb_preview = QComboBox()
        for size, key in ((0, "opt.preview.off"), (160, "opt.preview.tiny"), (320, "opt.preview.small"),
                          (640, "opt.preview.medium")):
            self.cb_preview.addItem(tr(key), size)
        self.cb_preview.setCurrentIndex(self.cb_preview.findData(s.preview_size))
        lay.addWidget(self.cb_preview)
        lay.addWidget(_hint(tr("opt.preview_hint")))

        self.ck_ir = QCheckBox(tr("opt.export_ir"))
        self.ck_ir.setChecked(s.export_ir)
        lay.addWidget(self.ck_ir)
        lay.addWidget(_hint(tr("opt.export_ir_hint")))

        self.ck_overscan = QCheckBox(tr("opt.keep_overscan"))
        self.ck_overscan.setChecked(s.keep_overscan)
        lay.addWidget(self.ck_overscan)
        lay.addWidget(_hint(tr("opt.keep_overscan_hint")))

        self.ck_cal = QCheckBox(tr("opt.cal_data"))
        self.ck_cal.setChecked(s.write_cal_data)
        lay.addWidget(self.ck_cal)
        lay.addWidget(_hint(tr("opt.cal_data_hint")))
        lay.addWidget(_hint(tr("opt.bits_hint")))
        lay.addStretch(1)
        return page

    def _presets_tab(self) -> QWidget:
        page, lay = _page()
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        self._lists: dict[str, QListWidget] = {}
        self._new: dict[str, QLineEdit] = {}
        for col, (kind, title) in enumerate((("films", tr("opt.films")), ("cameras", tr("opt.cameras")))):
            grid.addWidget(QLabel(title), 0, col)
            lst = QListWidget()
            lst.addItems(getattr(self._settings, kind))
            lst.setMinimumHeight(220)
            self._lists[kind] = lst
            grid.addWidget(lst, 1, col)
            edit = QLineEdit()
            edit.setPlaceholderText(tr("opt.new_entry"))
            self._new[kind] = edit
            add = QPushButton(tr("opt.add"))
            add.clicked.connect(lambda _=False, k=kind: self._add_preset(k))
            edit.returnPressed.connect(lambda k=kind: self._add_preset(k))
            grid.addLayout(_row(edit, add), 2, col)
            rem = QPushButton(tr("opt.remove"))
            rem.clicked.connect(lambda _=False, k=kind: self._remove_preset(k))
            grid.addWidget(rem, 3, col)
        lay.addLayout(grid)
        lay.addWidget(_hint(tr("opt.presets_hint")))
        lay.addStretch(1)
        return page

    def _driver_tab(self, busy: bool, update_state: dict) -> QWidget:
        page, lay = _page()
        self.lb_driver = QLabel()
        self.lb_driver.setWordWrap(True)
        self.lb_driver.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.lb_driver)
        self.lb_driver_link = QLabel(tr("opt.driver_link", url=DRIVER_URL))
        self.lb_driver_link.setTextFormat(Qt.RichText)
        self.lb_driver_link.setOpenExternalLinks(True)
        self.lb_driver_link.setWordWrap(True)
        lay.addWidget(self.lb_driver_link)
        self._refresh_driver_label(update_state)
        self.btn_check = QPushButton(tr("opt.check_now"))
        self.btn_check.clicked.connect(self.check_updates_requested)
        self.btn_rollback = QPushButton(tr("opt.rollback"))
        self.btn_rollback.clicked.connect(self.rollback_requested)
        self.btn_rollback.setEnabled(bool(update_state.get("previous")) and not busy)
        self.btn_check.setEnabled(not busy)
        lay.addLayout(_row(self.btn_check, self.btn_rollback, stretch_index=-1))
        self.btn_custom = QPushButton(tr("opt.custom_driver"))
        self.btn_custom.clicked.connect(self._pick_driver)
        self.btn_managed = QPushButton(tr("opt.managed_driver"))
        self.btn_managed.clicked.connect(self._use_managed)
        lay.addLayout(_row(self.btn_custom, self.btn_managed, stretch_index=-1))
        self.btn_doctor = QPushButton(tr("opt.doctor"))
        self.btn_doctor.clicked.connect(self.doctor_requested)
        self.btn_doctor.setEnabled(self._driver is not None and not busy)
        lay.addWidget(self.btn_doctor)
        lay.addWidget(_hint(tr("opt.doctor_hint")))

        box = QGroupBox(tr("opt.usb_title"))
        inner = QVBoxLayout(box)
        inner.addWidget(_hint(tr("opt.usb_text")))
        self.usb_commands = QPlainTextEdit(self._usb_commands())
        self.usb_commands.setReadOnly(True)
        self.usb_commands.setMaximumHeight(120)
        inner.addWidget(self.usb_commands)
        copy = QPushButton(tr("dlg.copy"))
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.usb_commands.toPlainText()))
        inner.addWidget(copy)
        lay.addWidget(box)
        lay.addStretch(1)
        return page

    # ------------------------------------------------------------------ helpers
    def _usb_commands(self) -> str:
        if self._driver is not None:
            rule = self._driver.root / "udev" / "60-of135i.rules"
        else:
            rule = paths.driver_root_dir() / "current" / "udev" / "60-of135i.rules"
        return (f"sudo cp '{rule}' /etc/udev/rules.d/\n"
                "sudo udevadm control --reload-rules && sudo udevadm trigger\n"
                "# Steam Deck / SteamOS: " + tr("opt.usb_readonly") + "\n"
                "# sudo steamos-readonly disable   ...   sudo steamos-readonly enable")

    def _refresh_driver_label(self, update_state: dict | None = None) -> None:
        d = self._driver
        if d is None:
            self.lb_driver.setText(tr("opt.driver_none"))
            return
        where = tr("opt.driver_demo") if d.demo else (tr("opt.driver_managed") if d.managed else tr("opt.driver_custom"))
        source = ""
        if d.source and d.source.get("label"):
            source = "\n" + tr("opt.driver_source", label=d.source["label"])
        self.lb_driver.setText(tr("opt.driver_info", version=d.version, where=where, path=str(d.root)) + source)

    def set_driver_info(self, driver: Driver | None, update_state: dict) -> None:
        self._driver = driver
        self._refresh_driver_label(update_state)
        self.btn_rollback.setEnabled(bool(update_state.get("previous")))
        self.usb_commands.setPlainText(self._usb_commands())

    def _pick_dir(self, edit: QLineEdit) -> None:
        start = edit.text() or str(paths.default_scan_dir().parent)
        chosen = QFileDialog.getExistingDirectory(self, tr("opt.pick_folder"), start)
        if chosen:
            edit.setText(chosen)

    def _pick_negpy(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(self, tr("opt.pick_negpy"), str(Path.home()))
        if chosen:
            self.ed_negpy.setText(chosen)

    def _pick_driver(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, tr("opt.pick_driver"), str(Path.home()))
        if chosen:
            self._driver_path = chosen

    def _use_managed(self) -> None:
        self._driver_path = ""

    def _add_preset(self, kind: str) -> None:
        text = self._new[kind].text()
        if self._settings.add_preset(kind, text):
            self._lists[kind].addItem(" ".join(text.split()))
        self._new[kind].clear()

    def _remove_preset(self, kind: str) -> None:
        for item in self._lists[kind].selectedItems():
            self._settings.remove_preset(kind, item.text())
            self._lists[kind].takeItem(self._lists[kind].row(item))

    # ------------------------------------------------------------------ result
    def _offset_value(self) -> float | None:
        """The typed offset in mm (comma or point), limited to +-5 mm; unreadable text means "driver default"."""
        try:
            return round(max(-5.0, min(5.0, float(self.ed_offset.text().replace(",", ".")))), 2)
        except ValueError:
            return None

    def values(self) -> Settings:
        s = self._settings
        s.language = self.cb_language.currentData()
        s.scan_dir = self.ed_scan_dir.text().strip()
        s.negpy_path = self.ed_negpy.text().strip()
        s.check_updates = self.ck_updates.isChecked()
        s.update_channel = self.cb_channel.currentData()
        s.rotate = self.cb_rotate.currentData()
        s.dust_clean = self.ck_dust.isChecked()
        s.fast_next_strip = self.ck_fast.isChecked()
        s.position_offset_mm = None if self.ck_offset_default.isChecked() else self._offset_value()
        s.preview_size = self.cb_preview.currentData()
        s.export_ir = self.ck_ir.isChecked()
        s.keep_overscan = self.ck_overscan.isChecked()
        s.write_cal_data = self.ck_cal.isChecked()
        s.driver_path = self._driver_path
        return s
