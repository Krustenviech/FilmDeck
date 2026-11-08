"""The main window: settings on the left, progress and thumbnails on the right."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
                               QToolButton, QVBoxLayout, QWidget)

from .. import __version__, i18n
from ..core import driver as drv
from ..core import external, imaging, naming, paths, update
from ..core.config import BIT_CHOICES, DPI_CHOICES, Settings
from ..core.session import (FILM_MODE, FRAMES_PER_STRIP, STRIP_MODE, ScanSession, SessionResult, check_scanner,
                            eject_holder, existing_images)
from ..i18n import tr
from . import messages, style
from .bridge import SessionBridge, run_async
from .dialogs import InfoDialog, TextDialog, UpdateDialog
from .options import OptionsDialog
from .widgets import FrameList, FrameToggles, pil_to_qimage

THUMB_EDGE = 280
LEVEL_COLORS = {"ok": style.OK, "warn": style.WARN, "error": style.ERR, "info": style.TEXT}


def _label(object_name: str = "") -> QLabel:
    label = QLabel()
    if object_name:
        label.setObjectName(object_name)
    return label


def _checkable(button: QPushButton) -> QPushButton:
    button.setCheckable(True)
    return button


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, *, autostart: bool = True):
        super().__init__()
        self.settings = settings
        self.driver: drv.Driver | None = drv.locate(settings)
        self._session: ScanSession | None = None
        self._bridge = SessionBridge(self)
        self._bridge.event.connect(self._on_event)
        self._mode = STRIP_MODE
        self._name_manual = False
        self._power_cycle_required = False
        self._checking = False
        self._ejecting = False
        self._update_info: update.UpdateInfo | None = None
        self._last_dir: Path | None = None
        self._strip_frames = 0
        self._strip_no = 1
        self._strip_written = 0
        self._dialogs: list = []
        self._options: OptionsDialog | None = None
        self.setMinimumSize(1000, 620)
        self.resize(1240, 740)
        self._build()
        self._fill_presets()
        self._settings_to_ui()
        self.retranslate()
        if autostart:
            QTimer.singleShot(0, self._startup)

    # ================================================================== building
    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.lb_dot = QLabel("●")
        self.lb_scanner = QLabel()
        self.btn_check = QPushButton()
        self.btn_check.clicked.connect(self._check_scanner)
        self.lb_driver = _label()
        self.lb_driver.setProperty("muted", True)
        self.btn_options = QPushButton()
        self.btn_options.clicked.connect(self._open_options)
        self.btn_mode_strip = _checkable(QPushButton())
        self.btn_mode_film = _checkable(QPushButton())
        self.mode_group = QButtonGroup(self)
        for i, b in enumerate((self.btn_mode_strip, self.btn_mode_film)):
            self.mode_group.addButton(b, i)
            b.setMinimumWidth(190)
        self.btn_mode_strip.setChecked(True)
        self.mode_group.idClicked.connect(self._on_mode)
        self.btn_eject = QPushButton()
        self.btn_eject.clicked.connect(self._ask_eject)
        for w in (self.lb_dot, self.lb_scanner, self.btn_check, self.btn_eject):
            top.addWidget(w)
        top.addStretch(1)
        top.addWidget(self.btn_mode_strip)
        top.addWidget(self.btn_mode_film)
        top.addStretch(1)
        top.addWidget(self.btn_options)
        root.addLayout(top)

        self.banner = QFrame()
        self.banner.setObjectName("banner")
        bl = QHBoxLayout(self.banner)
        bl.setContentsMargins(14, 8, 14, 8)
        self.lb_banner = QLabel()
        self.lb_banner.setWordWrap(True)
        self.btn_banner_notes = QPushButton()
        self.btn_banner_action = QPushButton()
        self.btn_banner_close = QPushButton("✕")
        self.btn_banner_close.setFixedWidth(56)
        bl.addWidget(self.lb_banner, 1)
        for b in (self.btn_banner_notes, self.btn_banner_action, self.btn_banner_close):
            bl.addWidget(b)
        self.btn_banner_notes.clicked.connect(self._show_update_notes)
        self.btn_banner_action.clicked.connect(self._banner_action)
        self.btn_banner_close.clicked.connect(self._banner_close)
        self.banner.hide()
        root.addWidget(self.banner)
        self._banner_kind = ""

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_settings_panel(), 0)
        body.addWidget(self._build_progress_panel(), 1)
        root.addLayout(body, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        self.btn_start = QPushButton()
        self.btn_start.setObjectName("primary")
        self.btn_start.clicked.connect(self._start)
        self.btn_cancel = QPushButton()
        self.btn_cancel.setObjectName("danger")
        self.btn_cancel.clicked.connect(self._ask_cancel)
        self.btn_cancel.hide()
        self.btn_new = QPushButton()
        self.btn_new.clicked.connect(self._new_film)
        self.btn_negpy = QPushButton()
        self.btn_negpy.clicked.connect(self._start_negpy)
        self.btn_folder = QPushButton()
        self.btn_folder.clicked.connect(self._open_folder)
        for b in (self.btn_negpy, self.btn_folder):
            b.setEnabled(False)
        bottom.addWidget(self.btn_start)
        bottom.addWidget(self.btn_cancel)
        bottom.addStretch(1)
        bottom.addWidget(self.btn_new)
        bottom.addWidget(self.btn_negpy)
        bottom.addWidget(self.btn_folder)
        root.addLayout(bottom)

    def _build_settings_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(540)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(4, 4, 4, 4)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        form = QWidget()
        scroll.setWidget(form)
        g = QGridLayout(form)
        g.setContentsMargins(14, 12, 14, 12)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.setColumnStretch(1, 1)

        self.lb_name = QLabel()
        self.ed_name = QLineEdit()
        self.ed_name.textEdited.connect(self._on_name_edited)
        self.btn_name_auto = QToolButton()
        self.btn_name_auto.setText("↺")
        self.btn_name_auto.clicked.connect(self._reset_name)
        g.addWidget(self.lb_name, 0, 0)
        g.addWidget(self.ed_name, 0, 1)
        g.addWidget(self.btn_name_auto, 0, 2)
        self.lb_existing = _label()
        self.lb_existing.setWordWrap(True)
        self.lb_existing.setProperty("muted", True)
        g.addWidget(self.lb_existing, 1, 1, 1, 2)

        self.lb_film = QLabel()
        self.cb_film = QComboBox()
        self.cb_film.setEditable(True)
        self.cb_film.setInsertPolicy(QComboBox.NoInsert)
        self.cb_film.editTextChanged.connect(self._recompose_name)
        self.btn_add_film = QToolButton()
        self.btn_add_film.setText("＋")
        self.btn_add_film.clicked.connect(lambda: self._add_preset("films", self.cb_film))
        g.addWidget(self.lb_film, 2, 0)
        g.addWidget(self.cb_film, 2, 1)
        g.addWidget(self.btn_add_film, 2, 2)

        self.lb_camera = QLabel()
        self.cb_camera = QComboBox()
        self.cb_camera.setEditable(True)
        self.cb_camera.setInsertPolicy(QComboBox.NoInsert)
        self.cb_camera.editTextChanged.connect(self._recompose_name)
        self.btn_add_camera = QToolButton()
        self.btn_add_camera.setText("＋")
        self.btn_add_camera.clicked.connect(lambda: self._add_preset("cameras", self.cb_camera))
        g.addWidget(self.lb_camera, 3, 0)
        g.addWidget(self.cb_camera, 3, 1)
        g.addWidget(self.btn_add_camera, 3, 2)

        self.lb_type = QLabel()
        types = QHBoxLayout()
        self.btn_c41 = _checkable(QPushButton())
        self.btn_bw = _checkable(QPushButton())
        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.btn_c41, 0)
        self.type_group.addButton(self.btn_bw, 1)
        self.type_group.idClicked.connect(lambda _i: self._update_size_hint())
        types.addWidget(self.btn_c41, 1)
        types.addWidget(self.btn_bw, 1)
        g.addWidget(self.lb_type, 4, 0)
        g.addLayout(types, 4, 1, 1, 2)

        self.lb_dpi = QLabel()
        self.cb_dpi = QComboBox()
        for dpi in DPI_CHOICES:
            self.cb_dpi.addItem(f"{dpi} dpi", dpi)
        self.cb_dpi.currentIndexChanged.connect(self._update_size_hint)
        g.addWidget(self.lb_dpi, 5, 0)
        g.addWidget(self.cb_dpi, 5, 1, 1, 2)

        self.lb_bits = QLabel()
        self.cb_bits = QComboBox()
        for bits in BIT_CHOICES:
            self.cb_bits.addItem("", bits)
        self.cb_bits.currentIndexChanged.connect(self._update_size_hint)
        g.addWidget(self.lb_bits, 6, 0)
        g.addWidget(self.cb_bits, 6, 1, 1, 2)
        self.lb_size = _label()
        self.lb_size.setWordWrap(True)
        self.lb_size.setProperty("muted", True)
        g.addWidget(self.lb_size, 7, 1, 1, 2)

        self.lb_frames = QLabel()
        self.lb_frames.setWordWrap(True)
        self.frames = FrameToggles()
        g.addWidget(self.lb_frames, 8, 0)
        g.addWidget(self.frames, 8, 1, 1, 2)
        self.lb_frames_hint = QLabel()
        self.lb_frames_hint.setWordWrap(True)
        self.lb_frames_hint.setProperty("muted", True)
        g.addWidget(self.lb_frames_hint, 9, 1, 1, 2)

        self.lb_dir = QLabel()
        self.ed_dir = QLineEdit()
        self.btn_browse = QToolButton()
        self.btn_browse.setText("…")
        self.btn_browse.clicked.connect(self._browse_dir)
        g.addWidget(self.lb_dir, 10, 0)
        g.addWidget(self.ed_dir, 10, 1)
        g.addWidget(self.btn_browse, 10, 2)
        g.setRowStretch(11, 1)
        return panel

    def _build_progress_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(8)
        self.lb_status = _label("status")
        self.lb_status.setWordWrap(True)
        self.lb_detail = QLabel()
        self.lb_detail.setWordWrap(True)
        self.lb_detail.setProperty("muted", True)
        self.lb_detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.hide()
        self.frame_list = FrameList()
        self.btn_log = _checkable(QPushButton())
        self.btn_log.toggled.connect(self._toggle_log)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(3000)
        self.log.setMaximumHeight(150)
        self.log.hide()
        lay.addWidget(self.lb_status)
        lay.addWidget(self.lb_detail)
        lay.addWidget(self.progress)
        lay.addWidget(self.frame_list, 1)
        footer = QHBoxLayout()
        footer.addWidget(self.btn_log)
        footer.addStretch(1)
        footer.addWidget(self.lb_driver)
        lay.addLayout(footer)
        lay.addWidget(self.log)
        return panel

    # ================================================================== texts
    def retranslate(self) -> None:
        self.setWindowTitle(tr("app.title"))
        self.btn_check.setText(tr("top.check"))
        self.btn_options.setText("⚙  " + tr("top.options"))
        self.btn_banner_notes.setText(tr("banner.notes"))
        self.btn_mode_strip.setText(tr("mode.strip"))
        self.btn_mode_film.setText(tr("mode.film"))
        self.lb_name.setText(tr("form.name"))
        self.btn_name_auto.setToolTip(tr("form.name_auto"))
        self.ed_name.setPlaceholderText(tr("form.name_placeholder"))
        self.lb_film.setText(tr("form.film"))
        self.cb_film.lineEdit().setPlaceholderText(tr("form.film_placeholder"))
        self.btn_add_film.setToolTip(tr("form.save_preset"))
        self.lb_camera.setText(tr("form.camera"))
        self.cb_camera.lineEdit().setPlaceholderText(tr("form.camera_placeholder"))
        self.btn_add_camera.setToolTip(tr("form.save_preset"))
        self.lb_type.setText(tr("form.type"))
        self.btn_c41.setText(tr("form.type.c41"))
        self.btn_bw.setText(tr("form.type.bw"))
        self.lb_dpi.setText(tr("form.dpi"))
        self.lb_bits.setText(tr("form.bits"))
        for i, bits in enumerate(BIT_CHOICES):
            self.cb_bits.setItemText(i, tr(f"form.bits.{bits}"))
        self.btn_eject.setText(tr("top.eject"))
        self.btn_eject.setToolTip(tr("top.eject_tip"))
        self.lb_dir.setText(tr("form.dir"))
        self.ed_dir.setPlaceholderText(str(paths.default_scan_dir()))
        self.btn_browse.setToolTip(tr("opt.browse"))
        self.btn_log.setText(tr("log.hide") if self.btn_log.isChecked() else tr("log.show"))
        self.btn_new.setText(tr("btn.new_film"))
        self.btn_negpy.setText(tr("btn.negpy"))
        self.btn_folder.setText(tr("btn.folder"))
        self.btn_cancel.setText("■  " + tr("btn.cancel"))
        self._refresh_start_text()
        self._update_driver_label()
        self._update_size_hint()
        self._update_existing_hint()
        self._update_mode_widgets()
        if not self._session:
            self._set_idle_status()
        if self._banner_kind == "update" and self._update_info:
            self._show_update_banner()

    def _refresh_start_text(self) -> None:
        self.btn_start.setText("▶  " + tr("btn.start_film" if self._mode == FILM_MODE else "btn.start_strip"))

    def _update_driver_label(self) -> None:
        d = self.driver
        if d is None:
            text = tr("top.driver_none")
        elif d.demo:
            text = tr("top.driver_demo", version=d.version)
        else:
            text = tr("top.driver", version=d.version)
        self.lb_driver.setText(text + "   ·   FilmDeck " + __version__)

    def _set_idle_status(self) -> None:
        if self.driver is None:
            self._set_status(tr("status.no_driver"), tr("status.no_driver_hint"), "warn")
        else:
            self._set_status(tr("status.ready"), tr("status.ready_hint"), "info")

    def _set_status(self, title: str, detail: str = "", level: str = "info") -> None:
        self.lb_status.setText(title)
        self.lb_status.setStyleSheet(f"color: {LEVEL_COLORS.get(level, style.TEXT)};")
        self.lb_detail.setText(detail)
        self.lb_detail.setVisible(bool(detail))

    # ================================================================== settings <-> widgets
    def _fill_presets(self) -> None:
        for combo, items, current in ((self.cb_film, self.settings.films, self.settings.last_film),
                                      (self.cb_camera, self.settings.cameras, self.settings.last_camera)):
            text = combo.currentText() or current
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(items)
            combo.setCurrentIndex(-1)
            combo.setEditText(text)
            combo.blockSignals(False)

    def _settings_to_ui(self) -> None:
        s = self.settings
        for w in (self.cb_dpi, self.cb_bits):
            w.blockSignals(True)
        self.cb_dpi.setCurrentIndex(self.cb_dpi.findData(s.dpi))
        self.cb_bits.setCurrentIndex(self.cb_bits.findData(s.bit_depth))
        for w in (self.cb_dpi, self.cb_bits):
            w.blockSignals(False)
        (self.btn_c41 if s.film_type == "c41" else self.btn_bw).setChecked(True)
        self.frames.set_selected(s.frames)
        self.ed_dir.setText(s.scan_dir)
        self._name_manual = False
        self._recompose_name()

    def _collect_settings(self) -> None:
        s = self.settings
        s.dpi = self.cb_dpi.currentData()
        s.bit_depth = self.cb_bits.currentData()
        s.film_type = "c41" if self.btn_c41.isChecked() else "bw"
        s.frames = self.frames.selected()
        s.scan_dir = self.ed_dir.text().strip()
        s.last_film = " ".join(self.cb_film.currentText().split())
        s.last_camera = " ".join(self.cb_camera.currentText().split())

    # ================================================================== form behaviour
    def _on_mode(self, index: int) -> None:
        self._mode = STRIP_MODE if index == 0 else FILM_MODE
        self._update_mode_widgets()
        self._refresh_start_text()

    def _update_mode_widgets(self) -> None:
        strip = self._mode == STRIP_MODE
        self.lb_frames.setText(tr("form.frames" if strip else "form.frames_first"))
        self.lb_frames_hint.setText(tr("form.frames_hint" if strip else "form.film_hint"))

    def _update_size_hint(self, *_args) -> None:
        dpi, bits = self.cb_dpi.currentData(), self.cb_bits.currentData()
        if dpi is None or bits is None:
            return
        per_pixel = {48: 6, 24: 3, 16: 2, 8: 1}[bits]
        mb = round((24 / 25.4 * dpi) * (36 / 25.4 * dpi) * per_pixel / 1e6)
        with_ir = self.btn_c41.isChecked() and self.settings.export_ir
        text = tr("form.size_hint_ir" if with_ir else "form.size_hint", mb=mb)
        if dpi >= 7200:
            text += "\n" + tr("form.dpi_7200_hint")
        self.lb_size.setText(text)

    def _recompose_name(self, *_args) -> None:
        if not self._name_manual:
            self.ed_name.setText(naming.compose_name(self.cb_film.currentText(), self.cb_camera.currentText()))
        self._update_existing_hint()

    def _on_name_edited(self, _text: str) -> None:
        self._name_manual = True
        self._update_existing_hint()

    def _reset_name(self) -> None:
        self._name_manual = False
        self._recompose_name()

    def _update_existing_hint(self) -> None:
        name = naming.sanitize_name(self.ed_name.text())
        count = existing_images(self._scan_root(), name) if name else 0
        self.lb_existing.setText(tr("form.existing", n=count, next=count + 1) if count else "")
        self.lb_existing.setVisible(bool(count))

    def _scan_root(self) -> Path:
        text = self.ed_dir.text().strip()
        return Path(text).expanduser() if text else paths.default_scan_dir()

    def _browse_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, tr("opt.pick_folder"), str(self._scan_root()))
        if chosen:
            self.ed_dir.setText(chosen)
            self._update_existing_hint()

    def _add_preset(self, kind: str, combo: QComboBox) -> None:
        if self.settings.add_preset(kind, combo.currentText()):
            self._collect_settings()
            self._fill_presets()
            self.settings.save()
            self._set_status(tr("status.preset_saved", name=combo.currentText()), "", "ok")
        else:
            self._set_status(tr("status.preset_exists"), "", "info")

    def _toggle_log(self, on: bool) -> None:
        self.log.setVisible(on)
        self.btn_log.setText(tr("log.hide") if on else tr("log.show"))

    def _set_controls_enabled(self, enabled: bool) -> None:
        for w in (self.btn_mode_strip, self.btn_mode_film, self.ed_name, self.btn_name_auto, self.cb_film,
                  self.cb_camera, self.btn_add_film, self.btn_add_camera, self.btn_c41, self.btn_bw, self.cb_dpi,
                  self.cb_bits, self.frames, self.ed_dir, self.btn_browse, self.btn_options, self.btn_new):
            w.setEnabled(enabled)
        self.btn_start.setEnabled(enabled and not self._checking)
        self.btn_check.setEnabled(enabled)
        self.btn_eject.setEnabled(enabled)

    # ================================================================== startup, scanner, driver
    def _startup(self) -> None:
        if self.driver is None:
            self._offer_driver_install()
            return
        self._check_scanner()
        if self.settings.check_updates and not self.driver.demo:
            self._check_updates(manual=False)

    def _check_scanner(self) -> None:
        if self._session or self.driver is None or self._checking or self._ejecting:
            return
        self._checking = True
        self.btn_start.setEnabled(False)
        self.lb_dot.setStyleSheet(f"color: {style.MUTED};")
        self.lb_scanner.setText(tr("scanner.checking"))
        driver = self.driver
        run_async(self, lambda: check_scanner(driver), self._on_scanner_status)

    def _on_scanner_status(self, status, error) -> None:
        self._checking = False
        self.btn_start.setEnabled(self._session is None)
        if error is not None or status is None:
            self.lb_dot.setStyleSheet(f"color: {style.ERR};")
            self.lb_scanner.setText(tr("scanner.unknown"))
            return
        if not status.ok:
            title, _ = messages.describe_error(status.error or "status_failed", status.raw)
            self.lb_dot.setStyleSheet(f"color: {style.ERR};")
            self.lb_scanner.setText(title)
            self.lb_scanner.setToolTip(status.raw)
            return
        self.lb_scanner.setToolTip("")
        if status.power_cycle:
            self.lb_dot.setStyleSheet(f"color: {style.ERR};")
            self.lb_scanner.setText(tr("scanner.unsafe"))
        elif status.magazine:
            self.lb_dot.setStyleSheet(f"color: {style.OK};")
            self.lb_scanner.setText(tr("scanner.ready_magazine"))
        else:
            self.lb_dot.setStyleSheet(f"color: {style.WARN};")
            self.lb_scanner.setText(tr("scanner.ready_no_magazine"))

    def _relocate_driver(self) -> None:
        self.driver = drv.locate(self.settings)
        self._update_driver_label()
        if not self._session:
            self._set_idle_status()

    def _offer_driver_install(self) -> None:
        self._set_status(tr("status.no_driver"), tr("status.no_driver_hint"), "warn")
        self.lb_scanner.setText(tr("scanner.no_driver"))
        run_async(self, lambda: update.check_release("0.0.0"), self._on_driver_offer)

    def _on_driver_offer(self, info, error) -> None:
        if error is not None or info is None:
            self._show_dialog(InfoDialog(self, tr("drv.offline.title"), tr("drv.offline.text"),
                                         [("options", tr("top.options"), ""), ("ok", tr("dlg.ok"), "primary")]),
                              lambda key: self._open_options() if key == "options" else None)
            return
        self._update_info = info
        dlg = UpdateDialog(self, tr("drv.install.title"), "", info.remote.label, info.remote.notes, can_install=True,
                           install_label=tr("drv.install.button", version=info.remote.label))
        dlg.install_requested.connect(lambda: self._install_remote(info.remote, dlg))
        self._show_dialog(dlg)

    # ------------------------------------------------------------------ update
    def _check_updates(self, manual: bool) -> None:
        if self.driver is None or self.driver.demo:
            return
        version, source, channel = self.driver.version, self.driver.source, self.settings.update_channel
        run_async(self, lambda: update.check(version, source, channel),
                  lambda info, err: self._on_update_info(info, manual))

    def _on_update_info(self, info, manual: bool) -> None:
        self._update_info = info
        if info is None:
            if manual and self.driver:
                self._show_banner("ok", tr("banner.up_to_date", version=self.driver.version), "uptodate")
            return
        if info.remote.ref == self.settings.ignored_update and not manual:
            return
        self._show_update_banner()

    def _show_update_banner(self) -> None:
        info = self._update_info
        if info is None:
            return
        self._show_banner("info", tr("banner.update", new=info.remote.label, installed=info.installed), "update")

    def _show_banner(self, level: str, text: str, kind: str) -> None:
        self._banner_kind = kind
        self.lb_banner.setText(text)
        self.banner.setProperty("level", {"ok": "ok", "error": "error"}.get(level, ""))
        self.banner.style().unpolish(self.banner)
        self.banner.style().polish(self.banner)
        is_update = kind == "update"
        self.btn_banner_notes.setVisible(is_update)
        self.btn_banner_action.setVisible(is_update)
        self.btn_banner_action.setText(tr("banner.update_now"))
        self.btn_banner_action.setEnabled(bool(self.driver and (self.driver.managed or self.driver.demo)))
        self.banner.show()

    def _banner_action(self) -> None:
        if self._banner_kind == "update" and self._update_info:
            self._install_remote(self._update_info.remote, None)

    def _banner_close(self) -> None:
        if self._banner_kind == "update" and self._update_info:
            self.settings.ignored_update = self._update_info.remote.ref
            self.settings.save()
        self.banner.hide()
        self._banner_kind = ""

    def _show_update_notes(self) -> None:
        info = self._update_info
        if not info:
            return
        managed = bool(self.driver and self.driver.managed)
        reason = "" if managed else tr("upd.not_managed")
        if self._session:
            reason = tr("upd.busy")
        dlg = UpdateDialog(self, tr("upd.title"), info.installed, info.remote.label, info.remote.notes,
                           can_install=managed and not self._session, blocked_reason=reason)
        dlg.install_requested.connect(lambda: self._install_remote(info.remote, dlg))
        dlg.ignore_requested.connect(self._banner_close)
        self._show_dialog(dlg)

    def _install_remote(self, remote: update.Remote, dlg: UpdateDialog | None) -> None:
        if self._session:
            self._set_status(tr("upd.busy"), "", "warn")
            return
        self.banner.hide()
        self._set_status(tr("upd.installing"), "", "info")

        def job(progress):
            return update.install(remote, verify=_verify_driver, progress=progress)

        run_async(self, job, lambda res, err: self._on_installed(res, err, dlg),
                  lambda done, total: dlg.set_progress(done, total) if dlg else None)

    def _on_installed(self, result, error, dlg: UpdateDialog | None) -> None:
        if error is not None:
            self._set_status(tr("upd.failed"), str(error), "error")
            if dlg:
                dlg.set_result(False, tr("upd.failed_text", error=str(error)))
            return
        self._relocate_driver()
        self._update_info = None
        version = self.driver.version if self.driver else "?"
        self._show_banner("ok", tr("upd.done", version=version), "installed")
        if dlg:
            dlg.set_result(True, tr("upd.done", version=version))
        self._check_scanner()
        if self._options:
            self._options.set_driver_info(self.driver, update.read_state())

    def _rollback(self) -> None:
        if self._session:
            return
        try:
            name = update.rollback()
        except update.UpdateError as e:
            self._set_status(tr("upd.failed"), str(e), "error")
            return
        self._relocate_driver()
        self._show_banner("ok", tr("upd.rolled_back", name=name), "installed")
        if self._options:
            self._options.set_driver_info(self.driver, update.read_state())

    def _run_doctor(self) -> None:
        if self._session or self.driver is None:
            return
        driver = self.driver
        run_async(self, lambda: drv.run_short(driver, drv.doctor_argv(), 120.0),
                  lambda res, err: self._show_dialog(TextDialog(
                      self, tr("opt.doctor"), (res[1] + "\n" + res[2]).strip() if res else str(err))))

    # ================================================================== options
    def _open_options(self) -> None:
        if self._session:
            return
        self._collect_settings()
        dlg = OptionsDialog(self, self.settings, self.driver, busy=False, update_state=update.read_state())
        dlg.check_updates_requested.connect(lambda: self._check_updates(manual=True))
        dlg.rollback_requested.connect(self._rollback)
        dlg.doctor_requested.connect(self._run_doctor)
        dlg.accepted.connect(lambda: self._apply_options(dlg.values()))
        dlg.finished.connect(lambda _r: setattr(self, "_options", None))
        self._options = dlg
        dlg.open()

    def _apply_options(self, new: Settings) -> None:
        driver_changed = new.driver_path != self.settings.driver_path
        language_changed = new.language != self.settings.language
        self.settings = new
        self.settings.save()
        i18n.set_language(new.language)
        self._fill_presets()
        self.ed_dir.setText(new.scan_dir)
        if language_changed:
            self.retranslate()
        if driver_changed:
            self._relocate_driver()
            self._check_scanner()
        self._update_existing_hint()

    # ================================================================== scanning
    def _start(self) -> None:
        if self._session or self._checking or self._ejecting:
            return
        if self._power_cycle_required:
            self._show_power_cycle()
            return
        if self.driver is None:
            self._offer_driver_install()
            return
        name = naming.sanitize_name(self.ed_name.text())
        if not name:
            self._set_status(tr("status.name_missing"), "", "error")
            return
        self.ed_name.setText(name)
        self._collect_settings()
        self.settings.save()
        self.frame_list.clear_frames()
        self.log.clear()
        self.banner.hide()
        self._banner_kind = ""
        self._last_dir = None
        frames = self.frames.selected()
        self._strip_frames = len(frames)
        self._strip_written = 0
        self._set_controls_enabled(False)
        for b in (self.btn_negpy, self.btn_folder):
            b.setEnabled(False)
        self.btn_start.hide()
        self.btn_cancel.show()
        self._set_status(tr("status.preflight"), "", "info")
        self.progress.setRange(0, 0)
        self.progress.show()
        self._session = ScanSession(self.settings, self.driver, name, self._mode, self._bridge.emit,
                                    frames=frames)
        self._session.start()

    def _on_event(self, ev) -> None:
        d = ev.data
        if ev.kind == "state":
            self._on_state(d["state"], d)
        elif ev.kind == "strip_started":
            self._strip_frames, self._strip_written, self._strip_no = d["frames"], 0, d["strip"]
            self.progress.setRange(0, d["frames"])
            self.progress.setValue(0)
            if d["full_load"]:
                self._set_status(tr("status.loading"), tr("status.loading_hint"), "info")
        elif ev.kind == "progress":
            self._on_progress(d)
        elif ev.kind == "frame_written":
            self._on_frame(d)
        elif ev.kind == "log":
            self.log.appendPlainText(d["line"])
        elif ev.kind == "prompt":
            self._on_prompt(d["prompt_kind"], d["text"])
        elif ev.kind == "exported":
            self._on_exported(d)
        elif ev.kind == "ask_next":
            self._on_ask_next()
        elif ev.kind == "finished":
            self._on_finished(d["result"])

    def _on_state(self, state: str, data: dict) -> None:
        if state == "preflight":
            self._set_status(tr("status.preflight"), "", "info")
        elif state == "loading":
            self.progress.setRange(0, 0)
            self._set_status(tr("status.next_strip_loading", strip=data.get("strip", 0)), "", "info")
        elif state == "scanning":
            self._set_status(tr("status.scanning", frame=1, total=self._strip_frames, strip=self._strip_no),
                             tr("status.scanning_hint"), "info")
        elif state == "exporting":
            self._set_status(tr("status.exporting"), "", "info")
            self.progress.setRange(0, 0)

    def _on_progress(self, d: dict) -> None:
        step = d.get("step")
        if step == "load_jog":
            self._set_status(tr("status.jog"), "", "info")
        elif step == "load_seq":
            self._set_status(tr("status.loading"), tr("status.loading_hint"), "info")
        elif step == "load_done":
            self.progress.setRange(0, self._strip_frames)
            self.progress.setValue(self._strip_written)
            self._set_status(tr("status.scanning", frame=1, total=self._strip_frames, strip=self._strip_no),
                             tr("status.scanning_hint"), "info")
        elif step == "stopping":
            self._set_status(tr("status.empty_stop"), "", "info")
            self.progress.setValue(self._strip_frames)
        elif step == "ejected":
            self._set_status(tr("status.ejected"), "", "info")

    def _on_frame(self, d: dict) -> None:
        self._strip_written += 1
        self.progress.setRange(0, self._strip_frames)           # a reinsert question had made it a busy bar
        self.progress.setValue(min(self._strip_written, self._strip_frames))
        key = _key(d["path"])
        self.frame_list.add_pending(key, tr("frame.pending", strip=d["strip"], frame=d["frame"]))
        path = d["path"]
        run_async(self, lambda: imaging.make_preview(path, THUMB_EDGE),
                  lambda img, err: self.frame_list.set_thumbnail(key, pil_to_qimage(img)) if err is None else None)
        if self._strip_written < self._strip_frames:
            self._set_status(tr("status.scanning", frame=self._strip_written + 1, total=self._strip_frames,
                                strip=d["strip"]), tr("status.scanning_hint"), "info")

    def _on_exported(self, d: dict) -> None:
        for img in d["images"]:
            self.frame_list.relabel(_key(str(img.source)), f"{img.number:02d}", str(img.path))
        for warning in d["warnings"]:
            self.log.appendPlainText("! " + warning)

    # ------------------------------------------------------------------ questions from the session
    def _on_prompt(self, kind: str, text: str) -> None:
        self.progress.setRange(0, 0)
        if kind == "reinsert":
            self._set_status(tr("status.reinsert"), "", "warn")
            dlg = InfoDialog(self, tr("dlg.reinsert.title"), tr("dlg.reinsert.text"),
                             [("abort", tr("dlg.abort"), ""), ("go", tr("dlg.reinsert.go"), "primary")],
                             closable=False)
        else:
            dlg = InfoDialog(self, tr("dlg.prompt.title"), tr("dlg.prompt.text", text=text),
                             [("abort", tr("dlg.abort"), ""), ("go", tr("dlg.continue"), "primary")],
                             closable=False)
        self._show_dialog(dlg, self._on_prompt_answer)

    def _on_prompt_answer(self, key: str) -> None:
        if not self._session:
            return
        if key == "go":
            self._session.answer_prompt()
            self._set_status(tr("status.loading"), tr("status.loading_hint"), "info")
        else:
            self._session.cancel()

    def _on_ask_next(self) -> None:
        self.progress.hide()
        self._set_status(tr("status.next_strip_wait"), "", "warn")
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(tr("dlg.next.frames")))
        toggles = FrameToggles()
        toggles.set_selected(range(1, FRAMES_PER_STRIP + 1))
        lay.addWidget(toggles)
        dlg = InfoDialog(self, tr("dlg.next.title"), tr("dlg.next.text", images=self.frame_list.count()),
                         [("finish", tr("dlg.next.finish"), ""), ("next", tr("dlg.next.go"), "primary")],
                         closable=False, extra=box)
        self._show_dialog(dlg, lambda key: self._on_next_answer(key, toggles.selected()))

    def _on_next_answer(self, key: str, frames: list[int]) -> None:
        if self._session:
            self.progress.show()
            self._session.answer_next(key == "next", frames)

    def _ask_cancel(self) -> None:
        if not self._session:
            return
        dlg = InfoDialog(self, tr("dlg.cancel.title"), tr("dlg.cancel.text"),
                         [("keep", tr("dlg.cancel.keep"), "primary"), ("stop", tr("dlg.cancel.stop"), "danger")])
        self._show_dialog(dlg, lambda key: self._session.cancel() if key == "stop" and self._session else None)

    # ------------------------------------------------------------------ eject (holder stuck)
    def _ask_eject(self) -> None:
        if self._session or self._checking or self._ejecting or self.driver is None:
            return
        confirm = QCheckBox(tr("dlg.eject.confirm"))
        dlg = InfoDialog(self, tr("dlg.eject.title"), tr("dlg.eject.text"),
                         [("cancel", tr("dlg.abort"), ""), ("go", tr("dlg.eject.go"), "primary")], extra=confirm)
        go = dlg.button("go")
        go.setEnabled(False)
        confirm.toggled.connect(go.setEnabled)
        self._show_dialog(dlg, lambda key: self._eject() if key == "go" else None)

    def _eject(self) -> None:
        driver = self.driver
        if driver is None or self._session or self._ejecting:
            return
        self._ejecting = True
        self._set_controls_enabled(False)
        self.btn_start.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.show()
        self._set_status(tr("status.ejecting"), tr("status.ejecting_hint"), "info")
        run_async(self, lambda: eject_holder(driver), self._on_ejected)

    def _on_ejected(self, result, error) -> None:
        self._ejecting = False
        self.progress.hide()
        self._set_controls_enabled(True)
        if error is not None or result is None:
            self._set_status(tr("err.internal.title"), tr("err.internal.text", detail=str(error)), "error")
            return
        if result.ok:
            self._power_cycle_required = False      # the driver only ejects from a safe start state
            self._set_status(tr("eject.done.title"), tr("eject.done.text"), "ok")
            self._check_scanner()
            return
        if result.code == "scan_failed":
            title, text = tr("eject.failed.title"), tr("eject.failed.text", detail=result.detail)
        else:
            title, text = messages.describe_error(result.code, result.detail, self.driver.version if self.driver else "")
        if result.power_cycle:
            text += "\n\n" + tr("res.power_cycle_hint")
        self._set_status(title, text, "error")
        if result.detail:
            self.log.appendPlainText(result.detail)
        if result.power_cycle:
            self._power_cycle_required = True
            self._show_power_cycle()
        else:
            self._check_scanner()

    # ------------------------------------------------------------------ end of a session
    def _on_finished(self, result: SessionResult) -> None:
        self._session = None
        self.progress.hide()
        self.btn_cancel.hide()
        self.btn_start.show()
        self._set_controls_enabled(True)
        level, title, text = messages.describe(result, self.driver.version if self.driver else "")
        self._set_status(title, text, level)
        if result.detail and result.kind == "error":
            self.log.appendPlainText(result.detail)
            self.btn_log.setChecked(True)
        self._last_dir = result.final_dir if result.images_total else None
        has_images = bool(self._last_dir and self._last_dir.exists())
        self.btn_negpy.setEnabled(has_images)
        self.btn_folder.setEnabled(has_images)
        self._update_existing_hint()
        if result.power_cycle:
            self._power_cycle_required = True
            self._show_power_cycle()
        else:
            self._check_scanner()

    def _show_power_cycle(self) -> None:
        dlg = InfoDialog(self, tr("dlg.power.title"), tr("dlg.power.text"),
                         [("later", tr("dlg.power.later"), ""), ("done", tr("dlg.power.done"), "primary")],
                         closable=False)
        self._show_dialog(dlg, self._on_power_answer)

    def _on_power_answer(self, key: str) -> None:
        if key == "done":
            self._power_cycle_required = False
            self._check_scanner()

    def _new_film(self) -> None:
        if self._session:
            return
        self.frame_list.clear_frames()
        self.log.clear()
        self._name_manual = False
        self._recompose_name()
        self._last_dir = None
        self.btn_negpy.setEnabled(False)
        self.btn_folder.setEnabled(False)
        self._set_idle_status()

    # ================================================================== NegPy, folder
    def _start_negpy(self) -> None:
        exe = external.find_negpy(self.settings.negpy_path)
        if exe is None:
            self._show_dialog(InfoDialog(self, tr("negpy.missing.title"), tr("negpy.missing.text"),
                                         [("options", tr("top.options"), ""), ("ok", tr("dlg.ok"), "primary")]),
                              lambda key: self._open_options() if key == "options" else None)
            return
        folder = str(self._last_dir) if self._last_dir else ""
        if folder:
            QGuiApplication.clipboard().setText(folder)
        try:
            external.launch_detached([str(exe)])
        except OSError as e:
            self._set_status(tr("negpy.failed"), str(e), "error")
            return
        self._set_status(tr("negpy.started"), tr("negpy.hint", folder=folder), "ok")

    def _open_folder(self) -> None:
        if self._last_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_dir)))

    # ================================================================== helpers
    def _show_dialog(self, dlg, on_choice=None) -> None:
        self._dialogs.append(dlg)
        if on_choice is not None and hasattr(dlg, "chosen"):
            dlg.chosen.connect(on_choice)
        dlg.finished.connect(lambda _r, d=dlg: self._dialogs.remove(d) if d in self._dialogs else None)
        dlg.open()

    def closeEvent(self, event) -> None:
        if self._session or self._ejecting:
            self._set_status(tr("status.close_blocked"), "", "warn")
            event.ignore()
            return
        self._collect_settings()
        self.settings.save()
        event.accept()


def _key(path: str) -> str:
    try:
        return str(Path(path).resolve())
    except OSError:
        return path


def _verify_driver(folder: Path) -> bool:
    """A freshly downloaded driver must at least start before it becomes the active one."""
    version = drv.read_version(folder)
    if not version:
        return False
    rc, _out, _err = drv.run_short(drv.Driver(folder, version, True), drv.version_argv(), 30.0)
    return rc == 0
