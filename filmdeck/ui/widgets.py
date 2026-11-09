"""Small reusable widgets."""

from __future__ import annotations

from PIL import Image
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QListView, QListWidget, QListWidgetItem,
                               QPushButton, QWidget)

from . import style

ICON = QSize(200, 136)


def pil_to_qimage(img: Image.Image) -> QImage:
    img = img.convert("RGB")
    data = img.tobytes()
    return QImage(data, img.width, img.height, 3 * img.width, QImage.Format_RGB888).copy()


def _placeholder() -> QPixmap:
    pm = QPixmap(ICON)
    pm.fill(QColor(style.PANEL_HI))
    p = QPainter(pm)
    p.setPen(QColor(style.BORDER))
    p.drawRoundedRect(pm.rect().adjusted(1, 1, -2, -2), 6, 6)
    p.end()
    return pm


class FrameList(QListWidget):
    """The scanned frames of this session, as thumbnails with a label.

    Items are keyed by the driver's file path while the scan runs ("S1 F3"); once
    the images are published to the film folder the label becomes the picture number.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.IconMode)
        self.setIconSize(ICON)
        self.setGridSize(QSize(ICON.width() + 24, ICON.height() + 50))
        self.setResizeMode(QListView.Adjust)
        self.setMovement(QListView.Static)
        self.setWrapping(True)
        self.setWordWrap(True)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setSpacing(4)
        self._items: dict[str, QListWidgetItem] = {}
        self._placeholder = QIcon(_placeholder())

    def add_pending(self, key: str, label: str) -> None:
        if key in self._items:
            return
        item = QListWidgetItem(self._placeholder, label)
        item.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.addItem(item)
        self._items[key] = item
        self.scrollToItem(item)

    def set_thumbnail(self, key: str, image: QImage) -> None:
        item = self._items.get(key)
        if item is not None:
            item.setIcon(QIcon(QPixmap.fromImage(image)))

    def relabel(self, key: str, label: str, tooltip: str = "") -> bool:
        item = self._items.get(key)
        if item is None:
            return False
        item.setText(label)
        item.setToolTip(tooltip)
        return True

    def labels(self) -> list[str]:
        return [self.item(i).text() for i in range(self.count())]

    def clear_frames(self) -> None:
        self.clear()
        self._items.clear()


class FrameToggles(QWidget):
    """The six apertures of the strip holder as buttons: pressed = scan it, released = skip it.

    At least one stays pressed (a scan of nothing makes no sense), so the last one cannot be released.
    """

    changed = Signal()

    def __init__(self, parent=None, count: int = 6):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self._buttons: dict[int, QPushButton] = {}
        for n in range(1, count + 1):
            b = QPushButton(str(n))
            b.setCheckable(True)
            b.setChecked(True)
            b.setMinimumWidth(40)
            b.toggled.connect(lambda on, n=n: self._toggled(n, on))
            lay.addWidget(b)
            self._buttons[n] = b

    def selected(self) -> list[int]:
        return [n for n, b in self._buttons.items() if b.isChecked()]

    def set_selected(self, frames) -> None:
        wanted = {n for n in frames if n in self._buttons} or set(self._buttons)
        for n, b in self._buttons.items():
            b.blockSignals(True)
            b.setChecked(n in wanted)
            b.blockSignals(False)
        self.changed.emit()

    def _toggled(self, n: int, on: bool) -> None:
        if not on and not self.selected():
            b = self._buttons[n]
            b.blockSignals(True)
            b.setChecked(True)
            b.blockSignals(False)
            return
        self.changed.emit()
