"""Start the program: ``python -m filmdeck`` (or the AppImage)."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import traceback

from . import APP_ID, APP_NAME, __version__


def _setup_logging() -> None:
    from .core import paths
    try:
        paths.log_dir().mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(paths.log_dir() / "filmdeck.log", encoding="utf-8")
    except OSError:
        return
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    def hook(kind, value, tb):
        logging.error("uncaught exception\n%s", "".join(traceback.format_exception(kind, value, tb)))
        sys.__excepthook__(kind, value, tb)

    sys.excepthook = hook


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="filmdeck", description=f"{APP_NAME} – scan program for the Plustek OpticFilm 135i")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument("--demo", action="store_true", help="use the built-in demo driver instead of a real scanner")
    parser.add_argument("--selftest", action="store_true",
                        help="check this installation (dependencies, window, one demo scan) and exit")
    args, qt_args = parser.parse_known_args(argv if argv is not None else sys.argv[1:])
    if args.selftest:
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")      # CI machines have no screen
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        from .selftest import run
        return run()
    if args.demo:
        os.environ["FILMDECK_DEMO"] = "1"

    # A SIGINT that is ignored here would be inherited by the driver and make "cancel" do nothing.
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    _setup_logging()

    from PySide6.QtWidgets import QApplication

    from . import i18n
    from .core.config import Settings
    from .ui import style
    from .ui.mainwindow import MainWindow

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APP_ID)
    style.apply(app)

    settings = Settings.load()
    i18n.set_language(settings.language)
    logging.info("%s %s started (python %s, %s)", APP_NAME, __version__, sys.version.split()[0],
                 os.environ.get("APPIMAGE") or "not an AppImage")
    window = MainWindow(settings)
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
