# Third-party components

FilmDeck's own code is under the [MIT licence](LICENSE). The AppImage also contains the programs and libraries below, each under its own licence. This list is for orientation; the licence texts that matter are the ones of the upstream projects and the ones installed together with each Python package inside the AppImage (`*.dist-info/licenses/`).

| Component | Licence | Upstream |
|---|---|---|
| Python (python-build-standalone) | PSF-2.0, plus the licences of the libraries it bundles | https://github.com/astral-sh/python-build-standalone |
| Qt for Python (PySide6-Essentials) and the Qt libraries | LGPL-3.0 | https://doc.qt.io/qtforpython-6/ |
| numpy | BSD-3-Clause | https://numpy.org |
| Pillow | HPND (MIT-CMU) | https://python-pillow.org |
| tifffile | BSD-3-Clause | https://github.com/cgohlke/tifffile |
| pyusb | BSD-3-Clause | https://github.com/pyusb/pyusb |
| libusb-1.0 | LGPL-2.1-or-later | https://libusb.info |

**LGPL libraries (Qt, libusb).** They are used unmodified, as separate shared libraries. An AppImage can be unpacked (`./FilmDeck-<version>-x86_64.AppImage --appimage-extract`), so they can be replaced by other builds of the same libraries. The source code of every version is available from the upstream projects.

**Not included.**
- The scanner driver [opticfilm135i-linux](https://github.com/cgillinger/opticfilm135i-linux) by cgillinger (GPL-2.0). FilmDeck downloads it at run time from the author's GitHub repository and runs it as a separate program (`python -m of135i`).
- [NegPy](https://github.com/marcinz606/NegPy), which FilmDeck only starts on request.

This list was written by an AI (Claude) from the build script and the usual licences of these projects; if you find a mistake, please open an issue.
