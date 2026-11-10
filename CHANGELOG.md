# Changelog

Versions follow [Semantic Versioning](https://semver.org/). While the major version is 0, anything may still change.
The version number lives in one place: `filmdeck/__init__.py` (`__version__`). A release is a git tag `vX.Y.Z` with the same number.

All of this was written by an AI (Claude) together with the repository owner; see the README.

## [0.1.3] – 2026-11-10

From the second and third real scans on a Steam Deck (a second strip into the same folder, a cancelled scan, eject).

### Added
- An info button (**?**, bottom right) with a short text: what FilmDeck is, the link to this repository, the MIT licence, the driver **opticfilm135i-linux** by cgillinger with its link and what it does, the AI notice, NegPy, and where the log files are.
- Options → Driver names the driver (opticfilm135i-linux, by cgillinger, GPL-2.0) and links to it.
- A window icon (the desktop showed its generic one before).

### Changed
- The footer and Options call the driver by its name, **opticfilm135i-linux**, instead of "Driver", and say "installed by FilmDeck" instead of "managed by FilmDeck".
- The USB access text in Options names the Steam Deck and other Linux systems.
- The summary after an incomplete scan no longer says the film opening was "not verified"; it says there is no file for those numbers.

### Fixed
- The button "Black & White" was shown as "Black_white": Qt took the "&" for a shortcut marker.
- A frame that was lost because a scan was cancelled was reported as "film opening not found reliably (scan)", and again after every later strip. It is now explained as "not scanned to the end", and only in the run that lost it.

## [0.1.2] – 2026-11-09

From the first real scan on a Steam Deck (6 frames, colour, 600 dpi), where frame 4 was scanned but the driver refused to crop it.

### Added
- When a frame is missing, FilmDeck now says why (the driver's reason in plain words, and that the number stays reserved) and, where it can be worked out from the driver's output, which *position offset* to use. A button applies the advised value in one click.
- The uncropped full scan of a refused frame is kept as `<name>_NN_overscan.tiff`.
- Checked against driver v0.2.12 (strip path unchanged) as well as v0.2.11.

### Changed
- The single strip / whole film switch moved to the top of the left panel.
- All buttons and fields are 75 % of their former height.
- The text for the position offset in *Options* was shortened.

## [0.1.1] – 2026-11-08

### Changed
- `filmdeck.log` was empty after a normal start. It now records the driver that was found, every scanner check, eject, update-check failures, driver install/rollback and the result of each scan; the per-scan log gets a result line too. Rotation only touches the per-scan logs.
- README and the internal-error message say which files to send when reporting a problem.

## [0.1.0] – 2026-11-08

First version. Not yet tried on a real scanner when it was built.

- Scan one strip (frames 1–6, each can be switched off) or a whole film (one folder, numbered without gaps).
- TIFF output with 48 / 24 / 16 / 8 bit and a very small JPEG preview per image; colour (C-41, infrared on) or black & white (infrared off); 600–7200 dpi.
- One `YY-MM-Film-Camera` name field with saveable film and camera presets; changeable save folder.
- Driver update check at start with release notes, one-click install and rollback.
- Eject button, button to start NegPy, German and English.
- AppImage for x86_64 Linux.
