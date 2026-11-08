# FilmDeck

[English version → README.md](README.md)

Ein kleines, einfaches Scan-Programm für den **Plustek OpticFilm 135i** (Kleinbild-Filmscanner) unter Linux und am Steam Deck (Desktop-Modus).
Es ist eine Oberfläche für den Community-Treiber [opticfilm135i-linux](https://github.com/cgillinger/opticfilm135i-linux) von cgillinger (das Kommandozeilenprogramm `of135i`) und macht nur das, was nötig ist, um Kleinbild-Negative in einen Ordner zu bekommen, fertig für [NegPy](https://github.com/marcinz606/NegPy):

- **einen Streifen** scannen (1–6 Bilder, jedes Bild einzeln abwählbar) oder einen **ganzen Film** (Streifen für Streifen, ein Ordner, lückenlos nummeriert)
- Name und Ordner in einem Feld: `JJ-MM-Film-Kamera`, mit Auswahllisten für Filme und Kameras, die du oft benutzt
- Farbe (C-41, Infrarot an) oder Schwarzweiß (Infrarot aus), Auflösung 600–7200 dpi, TIFF-Ausgabe mit 48 / 24 / 16 / 8 Bit
- eine sehr kleine JPEG-Vorschau je Bild
- ein Knopf, der danach NegPy startet
- prüft beim Start, ob es eine neue Treiberversion gibt, zeigt die Neuerungen und installiert sie per Klick (mit Rückgängig-Funktion)
- Deutsch und Englisch, umschaltbar

Es **invertiert, korrigiert und bearbeitet nichts**. Gescannt werden Negative; Invertieren und Bearbeiten passiert in NegPy.

---

## Mit KI gemacht – bitte lesen

**Dieses Programm und diese Dokumentation hat eine KI geschrieben: Claude (Claude Sonnet 5.5 von Anthropic), in mehreren Chat-Sitzungen mit dem Besitzer dieses Repositorys (Krustenviech).** Der Besitzer hat festgelegt, was das Programm können soll, und probiert es am echten Scanner aus; Claude hat Code, Tests, Build-Skripte und diesen Text geschrieben.

Was das praktisch heißt:

- Kein menschlicher Entwickler hat den Code Zeile für Zeile geprüft.
- Es gibt rund 100 automatische Tests (gegen einen eingebauten *Demo-Treiber* und gegen den Quelltext des echten Treibers), und das AppImage hat einen Selbsttest. **Das ersetzt keinen echten Scan.** Stand Version 0.1.0 wurde das Programm **noch nicht mit einem echten Scanner ausgeführt**; den ersten Lauf macht der Besitzer. Siehe [Stand](#stand).
- Den Scanner bewegt der Treiber, nicht dieses Programm. FilmDeck hält sich an die Sicherheitsregeln des Treibers (siehe [Sicherheit](#sicherheit)); wenn etwas seltsam aussieht, gilt zuerst die Dokumentation des Treibers.

---

## Stand

| | |
|---|---|
| Funktioniert, automatisch getestet | Streifen- und Ganzfilm-Scan gegen den Demo-Treiber (inkl. gewählter Bilder, mehrere Streifen, Abbruch, Fehler, Auswerfen), Dateinamen und Nummerierung, 48/24/16/8-Bit-Umwandlung, Update-/Rückgängig-Logik des Treibers, alle Texte in beiden Sprachen, das AppImage (gebaut und selbstgetestet) |
| Gegen den Quelltext des echten Treibers geprüft | Jede Kommandozeile, die FilmDeck baut, wird vom echten `of135i`-Argument-Parser akzeptiert; das Ausgabeformat `wrote …` und die Rückfragen sind mit dem Code des Treibers abgeglichen |
| **Noch nicht getestet** | Alles, was den echten Scanner braucht: Laden, Scannen, Filmhalter neu einschieben, Abbruch, Auswerfen |
| Nicht unterstützt | Andere Scanner; Invertieren / Bearbeiten; andere Prozessor-Architekturen (das AppImage ist x86_64) |

---

## Installation (Steam Deck / Linux, x86_64)

1. **AppImage holen:** `FilmDeck-<Version>-x86_64.AppImage` aus den *Releases* des Repositorys (oder als *Actions*-Artefakt), oder selbst bauen: `bash packaging/build-appimage.sh`.
2. Ausführbar machen und starten (im Desktop-Modus):
   ```bash
   chmod +x FilmDeck-*-x86_64.AppImage
   ./FilmDeck-*-x86_64.AppImage
   ```
   Falls es über FUSE meckert: `APPIMAGE_EXTRACT_AND_RUN=1 ./FilmDeck-*.AppImage`.
3. **Erster Start:** Der Treiber ist nicht im AppImage enthalten. FilmDeck bietet an, ihn aus cgillingers Repository herunterzuladen, und legt ihn in `~/.local/share/filmdeck/driver/` ab.
4. **USB-Berechtigung (einmalig):** damit der Scanner ohne Root benutzbar ist, die udev-Regel des Treibers installieren:
   ```bash
   bash packaging/install-udev.sh
   ```
   (Dieselben Befehle stehen in *Optionen → Treiber*.) Unter SteamOS entsperrt das Skript dafür kurz das Systemlaufwerk und sperrt es wieder. Danach USB-Kabel des Scanners abziehen und wieder einstecken.
5. **NegPy (optional):** das NegPy-AppImage nach `~/Applications` oder `~/Downloads` legen oder in *Optionen → Allgemein* auswählen.

Alles, was das AppImage braucht, steckt darin (Python, Qt, numpy, Pillow, tifffile, pyusb, libusb). Es setzt nur die üblichen Desktop-Bibliotheken eines Linux-Desktops voraus (X11 oder Wayland, `libxcb-cursor`).

Aus dem Quelltext: `pip install .` und `filmdeck` (braucht Python 3.12 oder neuer und libusb).

---

## Bedienung

Obere Leiste: Scannerstatus (grün = bereit), **Scanner prüfen**, **Auswerfen …**, der Umschalter **Einzelner Streifen / Ganzer Film** und **Optionen**.

**Einzelner Streifen**

1. *Name / Ordner* ausfüllen (oder aus Datum und den beiden Listen `JJ-MM-Film-Kamera` bilden lassen; frei änderbar, der Knopf ↺ bildet ihn neu). Oft benutzte Filme und Kameras mit **＋** in der Auswahl speichern.
2. *Filmtyp* wählen (C-41 Farbe = Infrarot an, Schwarzweiß = Infrarot aus), *Auflösung* und *Bit-Tiefe*.
3. *Zu scannende Bilder*: alle sechs sind an. Ein Bild anklicken lässt es aus, z. B. eine leere Öffnung am Streifenanfang. Das spart Scanzeit, und die übrigen Bilder werden trotzdem lückenlos nummeriert.
4. **Streifen scannen.** Das Programm bittet dich, den Filmhalter herauszuziehen und bis zum Anschlag neu einzuschieben – genau dann, wenn der Treiber danach fragt – und scannt dann.

**Ganzer Film**

Gleiches Formular; *Bilder des 1. Streifens* gilt für den ersten Streifen. Nach jedem Streifen fragt ein Dialog nach dem nächsten; dort wählst du, welche Bilder dieser Streifen hat (Standard: alle sechs; ein leeres Bild nach dem Film beendet den Streifen von selbst). Alle Streifen landen im selben Ordner und werden über die Streifen hinweg `01, 02, 03 …` nummeriert (die *Album*-Funktion des Treibers).

**Nach dem Scan:** Während des Scans erscheinen Vorschaubilder. **NegPy starten** öffnet NegPy und legt den Pfad des Filmordners in die Zwischenablage (NegPy kennt keine Kommandozeilenoption zum Öffnen eines Ordners: *Add Folder* wählen und einfügen). **Ordner öffnen** öffnet ihn im Dateimanager. **Neuer Film** leert die Anzeige und bildet einen neuen Namen.

**Wenn etwas schiefgeht:** *Abbrechen* fragt nach; nach einem Abbruch oder fehlgeschlagenen Scan muss der Scanner aus- und wieder eingeschaltet werden, und das Programm sperrt neue Scans, bis du das bestätigst. **Auswerfen …** befreit einen klemmenden Filmhalter: Es warnt zuerst, du musst bestätigen, dass der Scanner neu gestartet wurde, und dann läuft das `eject` des Treibers.

---

## Was auf der Platte landet

```
<Speicherort>/26-11-Kodak_Gold-Nikon_F3/
    26-11-Kodak_Gold-Nikon_F3_01.tiff        das Bild (48, 24, 16 oder 8 Bit)
    26-11-Kodak_Gold-Nikon_F3_01_ir.tiff     Infrarotkanal (C-41, wenn aktiviert; NegPy erkennt ihn)
    26-11-Kodak_Gold-Nikon_F3_02.tiff
    ...
    .previews/…_01.jpg                       kleine JPEG-Vorschauen (optional)
    .driver/                                 die eigenen Dateien des Treibers; nicht anfassen
```

- Standard-Speicherort: `~/Pictures/Filmscans`, im Hauptfenster und in den Optionen änderbar.
- Leerzeichen im Namen werden zu `_`, in Dateinamen nicht erlaubte Zeichen entfernt, die Teile mit `-` verbunden.
- Gibt es den Ordner schon, werden neue Bilder mit den nächsten Nummern angehängt, und das Formular weist darauf hin.
- **Bit-Tiefe.** Scanner/Treiber liefern immer 16 Bit je Farbkanal (= 48 Bit RGB). Das ist *48 Bit* und das, was du für NegPy behalten solltest. *24 Bit* (RGB, 8 Bit je Kanal), *16 Bit* (Grau) und *8 Bit* (Grau) rechnet FilmDeck nach dem Scan daraus um. 32 Bit gibt es nicht. Der Hersteller nennt als Ausgabe Farbe 24/48 Bit und Grau 8/16 Bit.
- **Auflösung.** 3600 dpi ist die native Auflösung des Sensors. 7200 dpi tastet doppelt so fein ab (die Notizen des Treibers nennen es echte Hardware-Überabtastung): vierfache Dateigröße, sehr lange Scanzeit, viel Arbeitsspeicher, und der Gewinn an echtem Detail ist meist klein. 48 Bit bei 3600 dpi sind etwa 104 MB je Bild, bei 7200 dpi etwa 416 MB.

---

## Optionen

*Allgemein:* Sprache, Standard-Speicherort, NegPy-Datei, Treiber-Update-Prüfung beim Start, Update-Quelle (veröffentlichte Versionen oder neuester Stand `master`).
*Scan:* Bild drehen, Staubentfernung per Infrarot (nur Farbe), schnellerer nächster Streifen (überspringt die Initialisierung, solange der Scanner nicht ausgeschaltet wurde), Bildlage verschieben.
*Dateien:* Vorschaugröße (keine / 160 / 320 / 640 px), Infrarot-Datei, gesamte Abtastfläche behalten (Overscan), Kalibrierdaten behalten.
*Listen:* deine Filme und Kameras.
*Treiber:* Version und Ort, jetzt nach Update suchen, vorige Version wiederherstellen, eigenen Treiberordner wählen, Hardware-Bericht (`of135i doctor`, nur lesend), USB-Einrichtung.

Einstellungen liegen in `~/.config/filmdeck/settings.json`, Protokolle in `~/.local/share/filmdeck/logs/`. Wenn du ein Problem meldest, hänge das neueste Protokoll an.

---

## Treiber-Updates

Beim Start fragt FilmDeck bei GitHub die neueste Version (oder `master`, falls gewählt) von cgillingers Treiber ab. Gibt es eine neuere, erscheint ein Banner mit **Neuerungen** (Release-Notes) und **Jetzt aktualisieren**. Die neue Version wird heruntergeladen, sicher entpackt, **einmal testweise gestartet** und erst dann die aktive; die vorige bleibt erhalten, damit *Optionen → Treiber → Vorige Version wiederherstellen* es rückgängig machen kann. Während eines Scans wird nichts aktualisiert. Ein Treiber in einem eigenen Ordner wird nie angefasst. FilmDeck braucht Treiber ab Version 0.2.11.

---

## Sicherheit

FilmDeck startet den Treiber als eigenen Prozess und hält sich an seine Regeln:

- Immer nur ein Treiberprozess; der Scannerstatus wird nur gelesen, wenn sonst nichts läuft.
- Ein Scan wird mit Ctrl-C-Semantik (SIGINT) abgebrochen, nie hart beendet. Nach Abbruch oder Fehler gilt der Scanner als *unsicher*, bis du ihn aus- und wieder einschaltest.
- Auswerfen nur über den Treiber, der einen unsicheren Zustand selbst verweigert.
- Die Sicherheitsoption `--cal-wait-scanstop` des Treibers bleibt auf ihrem Standard (die Korrektur zu [Issue #35](https://github.com/cgillinger/opticfilm135i-linux/issues/35)); sie wird nicht als Einstellung angeboten.
- Deine Scans werden von FilmDeck nie gelöscht oder verschoben; die Originale des Treibers bleiben in `.driver/`.

---

## Probleme

| Meldung / Symptom | Was tun |
|---|---|
| *Keine USB-Berechtigung* | udev-Regel installieren (`packaging/install-udev.sh`), Scanner neu einstecken |
| *Kein Scanner gefunden* | Scanner einschalten, Kabel und Netzteil prüfen, *Scanner prüfen* drücken |
| *Scanner ist belegt* | Ein anderer Treiberprozess oder ein anderes Programm benutzt ihn; beenden |
| *Laden fehlgeschlagen* / *unsicher* | Scanner aus- und einschalten, Halter herausziehen, neu versuchen; klemmt er, nach dem Neustart *Auswerfen …* benutzen |
| AppImage startet nicht (FUSE) | `APPIMAGE_EXTRACT_AND_RUN=1 ./FilmDeck-*.AppImage` |
| Qt-Fehler zum `xcb`-Plugin | `xcb-util-cursor` installieren (`libxcb-cursor0` bei Debian/Ubuntu) |
| Alles andere | Optionen → Treiber → *Hardware-Bericht* und das Protokoll in `~/.local/share/filmdeck/logs/` |

---

## Für Entwickler

```
filmdeck/
  core/      Treiberaufrufe, Ausgabe-Parser, Scan-Sitzung, Export, Update, Einstellungen, Namen (kein GUI-Code)
  ui/        PySide6-Hauptfenster, Dialoge, Optionen, Gestaltung
  demo/      Ersatz für den Treiber (kein Scanner nötig)
  strings.py alle Texte, Deutsch und Englisch
tests/       rund 100 Tests; test_gui.py steuert das echte Fenster offscreen
packaging/   AppImage-Build, udev-Installer, Desktop-Datei, Icon
```

```bash
pip install ".[test]"
QT_QPA_PLATFORM=offscreen pytest -q                         # Demo-Treiber; Vertragstests werden übersprungen
git clone https://github.com/cgillinger/opticfilm135i-linux ../driver
OF135I_SRC=../driver QT_QPA_PLATFORM=offscreen pytest -q    # prüft auch Argument-Parser und Ausgabe des echten Treibers
python -m filmdeck --demo                                  # Programm ohne Scanner ausprobieren
python -m filmdeck --selftest                              # Abhängigkeiten + Fenster + ein Demo-Scan
```

Der Demo-Treiber kann Probleme vortäuschen: `OF135I_DEMO_SCENARIO` auf eine kommagetrennte Liste aus `no_scanner, no_permission, no_magazine, unsafe, busy, cold, load_fail, eject_fail, coverage_fail:K, empty_from:K, scan_fail:K` setzen.

Wie ein Scan läuft: Die Sitzung ruft `python -m of135i digitize … --album <Name>` auf (der erste Streifen lädt interaktiv, spätere nutzen `load --next-strip` und `digitize --assume-loaded`), liest die Ausgabe als rohe Bytes (die Rückfrage zum Filmhalter hat kein Zeilenende) und veröffentlicht danach die Bilder des Treibers im Filmordner als `<Name>_NN.tiff` (Hardlinks bei 48 Bit, sonst umgewandelte Dateien).

Die CI (`.github/workflows/build.yml`) führt die Tests samt Vertragstests gegen den aktuellen Treiber aus, baut das AppImage, lässt dessen Selbsttest laufen und hängt es an Releases, die aus `v*`-Tags entstehen.

---

## Lizenz und Danksagung

- **Die Lizenz von FilmDeck ist noch nicht gewählt** (der Besitzer entscheidet). Bis eine Lizenzdatei hinzukommt, sind alle Rechte vorbehalten.
- Der Scanner-Treiber [opticfilm135i-linux](https://github.com/cgillinger/opticfilm135i-linux) (GPL-2.0) ist weder Teil dieses Repositorys noch des AppImages; er wird zur Laufzeit heruntergeladen und als eigenes Programm aufgerufen.
- [NegPy](https://github.com/marcinz606/NegPy) ist ein eigenes Programm und wird nur auf Wunsch gestartet.
- Das AppImage bündelt Python (python-build-standalone), Qt for Python / PySide6 (LGPL-3.0), numpy, Pillow, tifffile, pyusb und libusb (LGPL-2.1), jeweils unter eigener Lizenz.
- Plustek und OpticFilm sind Marken ihrer Inhaber; dieses Projekt steht in keiner Verbindung zu Plustek.
