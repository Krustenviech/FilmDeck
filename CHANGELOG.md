# Changelog

Versions follow [Semantic Versioning](https://semver.org/). While the major version is 0, anything may still change.
The version number lives in one place: `filmdeck/__init__.py` (`__version__`). A release is a git tag `vX.Y.Z` with the same number.

All of this was written by an AI (Claude) together with the repository owner; see the README.

## [0.1.4] – 2026-11-10

- Shorter info box (like in other programs): version, AI notice, repository link and licence, the driver opticfilm135i-linux, NegPy, log folder.

## [0.1.3] – 2026-11-10

- New info button **?** with links to this repository, the driver opticfilm135i-linux (cgillinger) and NegPy; the driver is now called by its name in the footer and in Options.
- Fixed: "Black & White" button label; a cancelled scan was wrongly reported as "film opening not found" and again after every later strip.
- Window icon; USB text mentions the Steam Deck and other Linux.

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
