"""Dialogs. All are opened with ``open()`` (modal, but the event loop keeps running, so
the scan session carries on in the background while a question is on screen)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar, QPushButton,
                               QTextBrowser, QVBoxLayout, QWidget)

from ..i18n import tr


class InfoDialog(QDialog):
    """A message with a few big buttons. ``chosen`` carries the key of the pressed button."""

    chosen = Signal(str)

    def __init__(self, parent, title: str, text: str, buttons: list[tuple[str, str, str]], *,
                 details: str = "", closable: bool = True, level: str = "info", extra: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self._closable = closable
        self._answered = False
        self._buttons: dict[str, QPushButton] = {}
        self.setMinimumWidth(600)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(14)
        head = QLabel(title)
        head.setObjectName("heading")
        head.setWordWrap(True)
        lay.addWidget(head)
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(body)
        if details:
            box = QPlainTextEdit(details)
            box.setReadOnly(True)
            box.setMaximumHeight(170)
            lay.addWidget(box)
        if extra is not None:
            lay.addWidget(extra)
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addStretch(1)
        for key, label, kind in buttons:
            b = QPushButton(label)
            if kind:
                b.setObjectName(kind)
            b.clicked.connect(lambda _=False, k=key: self._answer(k))
            row.addWidget(b)
            self._buttons[key] = b
        lay.addLayout(row)

    def button(self, key: str) -> QPushButton:
        return self._buttons[key]

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # word-wrapped text needs more height at 600 px than at its natural width: make sure nothing is cut off,
        # also where the window system does not enforce the layout's minimum size
        need = self.layout().totalHeightForWidth(self.width())
        if need > self.height():
            self.resize(self.width(), need)

    def _answer(self, key: str) -> None:
        self._answered = True
        self.chosen.emit(key)
        self.accept()

    def reject(self) -> None:   # Esc and the window's close button
        if self._closable:
            if not self._answered:
                self.chosen.emit("close")
            super().reject()


class UpdateDialog(QDialog):
    """What is new in a driver version, and the button to install it."""

    install_requested = Signal()
    ignore_requested = Signal()

    def __init__(self, parent, title: str, installed: str, new: str, notes: str, *, can_install: bool,
                 blocked_reason: str = "", install_label: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(760, 560)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(12)
        head = QLabel(title)
        head.setObjectName("heading")
        lay.addWidget(head)
        versions = QLabel(tr("upd.versions", installed=installed, new=new) if installed else new)
        versions.setProperty("muted", True)
        lay.addWidget(versions)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        if notes.startswith("http"):
            self.browser.setHtml(f'<p>{tr("upd.notes_online")}</p><p><a href="{notes}">{notes}</a></p>')
        else:
            self.browser.setMarkdown(notes or tr("upd.no_notes"))
        lay.addWidget(self.browser, 1)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        lay.addWidget(self.progress)
        self.message = QLabel(blocked_reason)
        self.message.setWordWrap(True)
        self.message.setVisible(bool(blocked_reason))
        lay.addWidget(self.message)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.btn_ignore = QPushButton(tr("upd.ignore"))
        self.btn_ignore.clicked.connect(self._ignore)
        self.btn_later = QPushButton(tr("upd.later"))
        self.btn_later.clicked.connect(self.reject)
        self.btn_install = QPushButton(install_label or tr("upd.install"))
        self.btn_install.setObjectName("primary")
        self.btn_install.setEnabled(can_install)
        self.btn_install.clicked.connect(self._install)
        row.addWidget(self.btn_ignore)
        row.addStretch(1)
        row.addWidget(self.btn_later)
        row.addWidget(self.btn_install)
        lay.addLayout(row)

    def _install(self) -> None:
        for b in (self.btn_install, self.btn_ignore, self.btn_later):
            b.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.message.setText(tr("upd.installing"))
        self.message.setVisible(True)
        self.install_requested.emit()

    def _ignore(self) -> None:
        self.ignore_requested.emit()
        self.accept()

    def set_progress(self, done: int, total: int) -> None:
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(min(done, total))

    def set_result(self, ok: bool, text: str) -> None:
        self.progress.setVisible(False)
        self.message.setText(text)
        self.message.setVisible(True)
        self.btn_later.setText(tr("dlg.close"))
        self.btn_later.setEnabled(True)
        if ok:
            self.btn_install.setVisible(False)
            self.btn_ignore.setVisible(False)
        else:
            self.btn_install.setEnabled(True)


class AboutDialog(QDialog):
    """The info box: what FilmDeck is, where it comes from, links (opened in the browser)."""

    def __init__(self, parent, title: str, html: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(720, 600)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(14)
        head = QLabel(title)
        head.setObjectName("heading")
        lay.addWidget(head)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        self.view.document().setDefaultStyleSheet("h3 { margin-top: 14px; margin-bottom: 2px; }")
        self.view.setHtml(html)
        lay.addWidget(self.view, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        close = QPushButton(tr("dlg.close"))
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        lay.addLayout(row)


class TextDialog(QDialog):
    """Read-only text with a copy button (hardware report, commands)."""

    def __init__(self, parent, title: str, text: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(780, 520)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 20)
        head = QLabel(title)
        head.setObjectName("heading")
        lay.addWidget(head)
        self.box = QPlainTextEdit(text)
        self.box.setReadOnly(True)
        lay.addWidget(self.box, 1)
        row = QHBoxLayout()
        copy = QPushButton(tr("dlg.copy"))
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.box.toPlainText()))
        close = QPushButton(tr("dlg.close"))
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        row.addWidget(copy)
        row.addStretch(1)
        row.addWidget(close)
        lay.addLayout(row)
