# FilmDeck

A small, simple scan program for the **Plustek OpticFilm 135i** (35 mm film scanner) on Linux and the Steam Deck (desktop mode).
It is a front-end for the community driver [opticfilm135i-linux](https://github.com/cgillinger/opticfilm135i-linux) by cgillinger (the `of135i` command line tool) and does only what is needed to get 35 mm negatives into a folder, ready for [NegPy](https://github.com/marcinz606/NegPy):

- scan **one strip** (1–6 frames, every frame can be switched off) or a **whole film** (strip after strip, one folder, numbered without gaps)
- name and folder in one field: `YY-MM-Film-Camera`, with drop-down lists for films and cameras you use often
- colour (C-41, infrared on) or black & white (infrared off), resolution 600–7200 dpi, TIFF output with 48 / 24 / 16 / 8 bit
- a very small JPEG preview per image
- a button that starts NegPy afterwards
- checks at start-up whether the driver has a new version, shows what is new and installs it with one click (with rollback)
- German and English, switchable

It does **not** invert, colour-correct or edit anything. Scans are negatives; inversion and editing happen in NegPy.

---

## Made with AI – please read

**This program and this documentation were written by an AI: Claude (Claude Sonnet 5.5, by Anthropic), working in a series of chat sessions with the owner of this repository (Krustenviech).** The owner decided what the program should do and is the person who tries it on the real scanner; Claude wrote the code, the tests, the build scripts and this text.

What that means in practice:

- No human developer has reviewed the code line by line.
- There are about 100 automated tests (they run against a built-in *demo driver* and against the real driver's source code), and the AppImage includes a self-test. **None of this replaces a real scan.** Up to now the owner has run **one real strip** with it (6 frames, colour, 600 dpi) and found it working; everything else that needs the scanner is untested. See [Status](#status).
- The scanner is moved by the driver, not by this program. FilmDeck follows the driver's safety rules (see [Safety](#safety)), but if something looks wrong, trust the driver's documentation first.

---

## Status

| | |
|---|---|
| Works, tested automatically | Strip scan and whole-film scan against the demo driver (including chosen frames, several strips, cancel, errors, eject), file naming and numbering, 48/24/16/8-bit conversion, driver update/rollback logic, all texts in both languages, the AppImage (built and self-tested) |
| Checked against the real driver's source | Every command line FilmDeck builds is accepted by the real `of135i` argument parser; the `wrote …` output format and the prompts are matched against the driver's code |
| Tested on a real scanner (once, 2026-11-08) | One colour strip of 6 frames at 600 dpi, 48 bit: start-up, driver download, USB rule, loading with the reinsert prompt, scanning, numbering and files. One frame was refused by the driver (margin too small); the explanation and the offset advice in the program come from that scan |
| **Not yet tested on a real scanner** | Whole film with several strips, black & white, 3600 / 7200 dpi, 24 / 16 / 8 bit on real scans, cancel, eject |
| Not supported | Other scanners; inversion / editing; other CPU architectures (the AppImage is x86_64) |

---

## Install

FilmDeck is one AppImage for any **x86_64 Linux desktop**; nothing in it is specific to the Steam Deck. It was only **tried on a Steam Deck (SteamOS, desktop mode)**. Other distributions should work the same way but nobody has checked yet – if you try one, please open an issue and say what happened.

### Steam Deck (desktop mode)

1. Download `FilmDeck-<version>-x86_64.AppImage` from the repository's [*Releases*](../../releases). Put it somewhere permanent (for example `~/Applications`), not in a temporary folder.
2. Make it executable and start it:
   ```bash
   chmod +x FilmDeck-*-x86_64.AppImage
   ./FilmDeck-*-x86_64.AppImage
   ```
3. **First start:** the driver is not part of the AppImage. FilmDeck offers to download it from cgillinger's repository and keeps it in `~/.local/share/filmdeck/driver/`.
4. **USB permission (once):** so you can use the scanner without root, install the driver's udev rule. The script is not inside the AppImage: download [`packaging/install-udev.sh`](packaging/install-udev.sh) from this repository (open it, *Raw*, save) and run it (the same commands are shown in *Options → Driver*):
   ```bash
   bash install-udev.sh
   ```
   SteamOS keeps the system drive write-protected: the script unlocks it for this one step and locks it again. Then unplug and re-plug the scanner's USB cable. If the scanner is "not found" again after a SteamOS update, run the script once more.
5. **NegPy (optional):** put the NegPy AppImage in `~/Applications` or `~/Downloads`, or choose it in *Options → General*.

### Other Linux (x86_64)

1. Download the AppImage from [*Releases*](../../releases), `chmod +x` it and start it as above.
   - If it complains about FUSE, either install the FUSE 2 library (`libfuse2` / `libfuse2t64` on Debian and Ubuntu, `fuse-libs` on Fedora, `fuse2` on Arch) or start it with `APPIMAGE_EXTRACT_AND_RUN=1 ./FilmDeck-*.AppImage`.
   - If Qt complains about the `xcb` plugin, install `libxcb-cursor0` (Debian/Ubuntu) / `xcb-util-cursor` (Fedora, Arch).
2. **First start:** FilmDeck downloads the driver, as above.
3. **USB permission (once).** Either run `bash packaging/install-udev.sh` from a clone of this repository, or install the rule by hand (it is the same one the driver ships):
   ```bash
   echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="07b3", ATTRS{idProduct}=="1436", MODE="0660", TAG+="uaccess"' \
     | sudo tee /etc/udev/rules.d/60-of135i.rules
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```
   Then unplug and re-plug the scanner's USB cable. `TAG+="uaccess"` gives access to the user who is logged in at the screen (systemd-logind, which almost every desktop distribution uses). Without it, change `MODE`/`GROUP` to a group you are in.
4. **NegPy (optional):** as above.

### What the AppImage contains

Python, Qt (PySide6), numpy, Pillow, tifffile, pyusb and libusb are inside. It only expects the usual libraries of a Linux desktop (X11 or Wayland, `libxcb-cursor`). It is **x86_64 only**; ARM computers (Raspberry Pi, Apple-silicon VMs) are not supported by the AppImage.

### From source

`pip install .` and `filmdeck` (needs Python 3.12 or newer and libusb). Build the AppImage yourself with `bash packaging/build-appimage.sh`.

---

## Using it

Top bar: scanner status (green = ready), **Check scanner**, **Eject …** and **Options**. The mode switch **Single strip / Whole film** is at the top of the left panel, above the name.

**Single strip**

1. Fill in *Name / folder* (or let it build `YY-MM-Film-Camera` from the date and the two lists; edit it freely, the ↺ button rebuilds it). Save films and cameras you use often with **＋**.
2. Choose *Film type* (C-41 colour = infrared on, black & white = infrared off), *Resolution* and *Bit depth*.
3. *Frames to scan*: all six are on. Click a frame to skip it, e.g. an empty opening at the start of a strip. Skipping saves scan time, and the remaining images are still numbered without gaps.
4. **Scan strip.** The program asks you to take the film holder out and push it in again to the stop – exactly when the driver asks for it – then scans.

**Whole film**

Same form; *Frames of strip 1* applies to the first strip. After each strip a dialog asks for the next one, where you choose which frames that strip has (default: all six; an empty frame after the film ends a strip by itself). All strips go into the same folder, numbered `01, 02, 03 …` across strips (the driver's *album* feature).

**After a scan:** thumbnails appear while scanning. **Start NegPy** opens NegPy and puts the film folder's path on the clipboard (NegPy has no command line option to open a folder: choose *Add Folder* and paste). **Open folder** opens it in the file manager. **New film** clears the screen and builds a new name.

**If something goes wrong:** *Cancel* asks for confirmation; after a cancel or a failed scan the scanner must be switched off and on again, and the program blocks new scans until you confirm that. **Eject …** frees a film holder that is stuck: it warns you first, you must tick that the scanner was power-cycled, and then it runs the driver's `eject`.

---

## What you get on disk

```
<save location>/26-11-Kodak_Gold-Nikon_F3/
    26-11-Kodak_Gold-Nikon_F3_01.tiff        the image (48, 24, 16 or 8 bit)
    26-11-Kodak_Gold-Nikon_F3_01_ir.tiff     infrared channel (C-41, if enabled; NegPy recognises it)
    26-11-Kodak_Gold-Nikon_F3_02.tiff
    ...
    26-11-Kodak_Gold-Nikon_F3_04_overscan.tiff   only if the driver refused to crop frame 4 (see below)
    .previews/…_01.jpg                       small JPEG previews (optional)
    .driver/                                 the driver's own files; do not touch
```

- Default save location: `~/Pictures/Filmscans`, changeable in the main window and in the options.
- Spaces in names become `_`, characters not allowed in file names are removed, parts are joined with `-`.
- If the folder already exists, new images are appended with the next numbers and the form says so.
- **Bit depth.** The scanner/driver always delivers 16 bit per colour channel (= 48 bit RGB). That is what *48 bit* is and what you should keep for NegPy. *24 bit* (RGB, 8 bit per channel), *16 bit* (grey) and *8 bit* (grey) are converted by FilmDeck from it after the scan. There is no 32 bit. The manufacturer lists colour 24/48 bit and grey 8/16 bit output.
- **Resolution.** 3600 dpi is the sensor's native resolution. 7200 dpi samples twice as finely (the driver's notes call it true hardware oversampling): files are four times larger, the scan takes very long and needs lots of memory, and the gain in real detail is usually small. 48 bit at 3600 dpi is about 104 MB per image, at 7200 dpi about 416 MB.

---

## Options

*General:* language, default save location, NegPy file, driver update check at start, update source (published releases or latest `master`).
*Scan:* rotate image, dust removal with infrared (colour only), faster next strip (skips the initialisation when the scanner has not been switched off), frame position offset.
*Files:* preview size (none / 160 / 320 / 640 px), infrared file, keep the full scanned area (overscan), keep calibration data.
*Lists:* your films and cameras.
*Driver:* version and location, check for update now, restore the previous version, choose your own driver folder, hardware report (`of135i doctor`, read-only), USB set-up commands.

Settings are stored in `~/.config/filmdeck/settings.json`. Logs are in `~/.local/share/filmdeck/logs/`: `filmdeck.log` records the start, driver found, scanner checks, eject, update checks and crashes (it stays short or even empty when nothing went wrong), and every scan writes its own file `<date>-<name>.log` with the driver commands, the driver's output and the result (the newest 20 are kept). If you report a problem, attach `filmdeck.log` and the newest scan log.

---

## Driver updates

At start-up FilmDeck asks GitHub for the newest release (or `master`, if chosen) of cgillinger's driver. If there is a newer one, a banner appears with **What's new** (release notes) and **Update now**. The new version is downloaded, unpacked safely, **started once as a test**, and only then becomes the active one; the previous version is kept so *Options → Driver → Restore the previous version* can undo it. Nothing is updated while a scan is running. A driver in a folder of your own is never touched. FilmDeck needs driver version 0.2.11 or newer; it has been checked against the source of 0.2.11 and 0.2.12.

---

## Safety

FilmDeck runs the driver as a separate process and follows its rules:

- Only one driver process at a time; the scanner status is read only when nothing else runs.
- A scan is cancelled with Ctrl-C semantics (SIGINT), never killed. After a cancel or failure the scanner is treated as *unsafe* until you power-cycle it.
- Eject only through the driver, which itself refuses an unsafe state.
- The driver's `--cal-wait-scanstop` safety option stays at its default (the fix for [issue #35](https://github.com/cgillinger/opticfilm135i-linux/issues/35)); it is not offered as a setting.
- Your scans are never deleted or moved by FilmDeck; the driver's originals stay in `.driver/`.

---

## Troubleshooting

| Message / symptom | What to do |
|---|---|
| *No USB permission* | Install the udev rule (`packaging/install-udev.sh`), re-plug the scanner |
| *No scanner found* | Switch the scanner on, check cable and power, press *Check scanner* |
| *Scanner busy* | Another driver process or program uses it; close it |
| *Image NN is missing* after a scan | The driver scanned the frame but would not crop it: the film opening was too close to the edge of the scan window (less than 0.15 mm). The number stays reserved and the uncropped scan is saved as `…_NN_overscan.tiff`. FilmDeck measures how far your scanner is off and offers the *Shift the frame position* value that fixes it (Options → Scan; negative = scan area starts earlier) |
| *Loading failed* / *unsafe* | Power-cycle the scanner, pull the holder out, try again; if it is stuck use *Eject …* after the power-cycle |
| AppImage does not start (FUSE) | `APPIMAGE_EXTRACT_AND_RUN=1 ./FilmDeck-*.AppImage` |
| Qt error about the `xcb` plugin | install `xcb-util-cursor` (`libxcb-cursor0` on Debian/Ubuntu) |
| Anything else | Options → Driver → *Hardware report*, and the logs in `~/.local/share/filmdeck/logs/` (`filmdeck.log` + the newest scan log) |

---

## For developers

```
filmdeck/
  core/      driver calls, output parsing, scan session, export, update, settings, naming (no GUI code)
  ui/        PySide6 main window, dialogs, options, styling
  demo/      a stand-in for the driver (no scanner needed)
  strings.py all texts, German and English
tests/       about 100 tests; test_gui.py drives the real window offscreen
packaging/   AppImage build, udev installer, desktop file, icon
```

```bash
pip install ".[test]"
QT_QPA_PLATFORM=offscreen pytest -q                         # demo driver; contract tests are skipped
git clone https://github.com/cgillinger/opticfilm135i-linux ../driver
OF135I_SRC=../driver QT_QPA_PLATFORM=offscreen pytest -q    # also checks the real driver's argument parser and output
python -m filmdeck --demo                                  # try the program without a scanner
python -m filmdeck --selftest                              # dependencies + window + one demo scan
```

The demo driver can fake problems: set `OF135I_DEMO_SCENARIO` to a comma-separated list of `no_scanner, no_permission, no_magazine, unsafe, busy, cold, load_fail, eject_fail, coverage_fail:K, empty_from:K, scan_fail:K`.

How a scan runs: the session calls `python -m of135i digitize … --album <name>` (first strip loads interactively; later strips use `load --next-strip` and `digitize --assume-loaded`), reads its output as raw bytes (the reinsert prompt has no newline), and afterwards publishes the driver's images into the film folder as `<name>_NN.tiff` (hard links for 48 bit, converted files otherwise).

CI (`.github/workflows/build.yml`) runs the tests including the contract tests against the current driver, builds the AppImage, runs its self-test and attaches it to releases made from `v*` tags.

---

## Licence and credits

- FilmDeck is released under the [MIT licence](LICENSE): you may use, copy, change and pass it on, also commercially, as long as the licence text stays with it. It comes without any warranty.
- The scanner driver [opticfilm135i-linux](https://github.com/cgillinger/opticfilm135i-linux) (GPL-2.0) is not part of this repository or the AppImage; it is downloaded at run time and called as a separate program.
- [NegPy](https://github.com/marcinz606/NegPy) is a separate program, started on request.
- The AppImage bundles Python (python-build-standalone), Qt for Python / PySide6 (LGPL-3.0), numpy, Pillow, tifffile, pyusb and libusb (LGPL-2.1), each under its own licence; see [THIRD-PARTY.md](THIRD-PARTY.md).
- Plustek and OpticFilm are trademarks of their owners; this project is not affiliated with Plustek.
