"""Dark theme sized for the Steam Deck screen (1280x800) and fingers.

Fusion is used on every system so the look does not depend on which Qt style
plug-ins the AppImage happens to find. Dark because film is scanned in dim light.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication

from ..core import paths

BG = "#1b1d21"
PANEL = "#25282e"
PANEL_HI = "#2f333b"
BORDER = "#3a3f48"
TEXT = "#e9e6e1"
MUTED = "#9aa0aa"
ACCENT = "#e3a63b"        # film-base amber
ACCENT_TEXT = "#1b1405"
OK = "#5dbb7a"
WARN = "#e3a63b"
ERR = "#e0645c"

TOUCH = 52                # minimum height of anything that is pressed


def apply(app: QApplication) -> None:
    app.setStyle("Fusion")
    font = QFont(app.font())
    font.setPointSizeF(12.5)
    app.setFont(font)
    pal = QPalette()
    for role, color in (
        (QPalette.Window, BG), (QPalette.WindowText, TEXT), (QPalette.Base, "#16181b"),
        (QPalette.AlternateBase, PANEL), (QPalette.Text, TEXT), (QPalette.Button, PANEL_HI),
        (QPalette.ButtonText, TEXT), (QPalette.ToolTipBase, PANEL_HI), (QPalette.ToolTipText, TEXT),
        (QPalette.Highlight, ACCENT), (QPalette.HighlightedText, ACCENT_TEXT),
        (QPalette.PlaceholderText, MUTED), (QPalette.Link, ACCENT),
    ):
        pal.setColor(role, QColor(color))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(MUTED))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(MUTED))
    app.setPalette(pal)
    app.setStyleSheet(stylesheet(_arrow_url(), _check_url()))


def _draw_icon(name: str, draw) -> str:
    """Draw a small image once into the data folder and return its path ("" if that fails; the program
    stays usable). A style sheet that sets borders removes Qt's built-in arrows and check marks."""
    try:
        folder = paths.data_dir() / "ui"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / name
        pm = QPixmap(24, 24)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing)
        draw(painter)
        painter.end()
        return target.as_posix() if pm.save(str(target), "PNG") else ""
    except OSError:
        return ""


def _arrow_url() -> str:
    def draw(p: QPainter) -> None:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(TEXT))
        p.drawPolygon(QPolygonF([QPointF(5, 8), QPointF(19, 8), QPointF(12, 17)]))
    return _draw_icon("arrow-down.png", draw)


def _check_url() -> str:
    def draw(p: QPainter) -> None:
        pen = QPen(QColor("#2a1d05"), 3.2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawPolyline(QPolygonF([QPointF(5.5, 12.5), QPointF(10, 17), QPointF(18.5, 7)]))
    return _draw_icon("check.png", draw)


def stylesheet(arrow_url: str = "", check_url: str = "") -> str:
    extra = ""
    if arrow_url:
        extra += f"\nQComboBox::down-arrow {{ image: url({arrow_url}); width: 24px; height: 24px; }}"
    if check_url:
        extra += f"\nQCheckBox::indicator:checked {{ image: url({check_url}); }}"
    return _STYLESHEET + extra


_STYLESHEET = f"""
QWidget {{ color: {TEXT}; }}
QMainWindow, QDialog {{ background: {BG}; }}
QLabel#muted, QLabel[muted="true"] {{ color: {MUTED}; }}
QLabel#heading {{ font-size: 15pt; font-weight: 600; }}
QLabel#status {{ font-size: 17pt; font-weight: 600; }}
QFrame#panel {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 10px; }}
QFrame#banner {{ background: #3b3015; border: 1px solid {ACCENT}; border-radius: 10px; }}
QFrame#banner[level="error"] {{ background: #3d1f1d; border-color: {ERR}; }}
QFrame#banner[level="ok"] {{ background: #1d3626; border-color: {OK}; }}

QPushButton, QToolButton {{
    background: {PANEL_HI}; border: 1px solid {BORDER}; border-radius: 8px;
    min-height: {TOUCH - 8}px; padding: 4px 16px;
}}
QPushButton:hover, QToolButton:hover {{ border-color: {ACCENT}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled, QToolButton:disabled {{ color: {MUTED}; background: {PANEL}; border-color: {PANEL_HI}; }}
QPushButton:checked, QToolButton:checked {{ background: {ACCENT}; color: {ACCENT_TEXT}; border-color: {ACCENT}; font-weight: 600; }}
QPushButton#primary {{ background: {ACCENT}; color: {ACCENT_TEXT}; border: none; font-size: 15pt; font-weight: 700;
    min-height: {TOUCH}px; padding: 4px 28px; }}
QPushButton#primary:disabled {{ background: {PANEL_HI}; color: {MUTED}; }}
QPushButton#danger {{ background: {ERR}; color: #2a0b09; border: none; font-size: 15pt; font-weight: 700;
    min-height: {TOUCH}px; padding: 4px 28px; }}
QToolButton#segment {{ min-width: 52px; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextBrowser, QListWidget {{
    background: #16181b; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px 10px;
    selection-background-color: {ACCENT}; selection-color: {ACCENT_TEXT};
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ min-height: {TOUCH - 12}px; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{ color: {MUTED}; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ width: 38px; border: none; }}
QComboBox QAbstractItemView {{ background: {PANEL}; selection-background-color: {ACCENT};
    selection-color: {ACCENT_TEXT}; min-height: {TOUCH - 12}px; }}
QComboBox QAbstractItemView::item {{ min-height: {TOUCH - 12}px; }}
QCheckBox {{ spacing: 12px; min-height: {TOUCH - 12}px; }}
QCheckBox::indicator {{ width: 26px; height: 26px; border: 1px solid {BORDER}; border-radius: 6px; background: #16181b; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QProgressBar {{ background: #16181b; border: 1px solid {BORDER}; border-radius: 8px; height: 22px; text-align: center; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 7px; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 8px; top: -1px; background: {PANEL}; }}
QTabBar::tab {{ background: {BG}; padding: 12px 22px; border: 1px solid {BORDER}; border-bottom: none;
    border-top-left-radius: 8px; border-top-right-radius: 8px; min-height: 28px; }}
QTabBar::tab:selected {{ background: {PANEL}; color: {ACCENT}; font-weight: 600; }}
QScrollBar:vertical {{ background: {BG}; width: 22px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 9px; min-height: 48px; margin: 2px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QListWidget::item {{ border-radius: 8px; padding: 4px; }}
QListWidget::item:selected {{ background: {PANEL_HI}; border: 1px solid {ACCENT}; }}
QGroupBox {{ border: 1px solid {BORDER}; border-radius: 8px; margin-top: 18px; padding: 14px 10px 8px 10px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {MUTED}; }}
"""
