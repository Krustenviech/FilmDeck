"""All texts of the program, German and English.

Placeholders are ``{name}``; both languages must use the same ones (tests/test_strings.py
checks this, and that every key used in the source exists).
"""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {}


def _t(key: str, de: str, en: str) -> None:
    assert key not in STRINGS, key
    STRINGS[key] = {"de": de, "en": en}


# ----------------------------------------------------------------------------- window, top bar
_t("app.title", "FilmDeck – Plustek OpticFilm 135i", "FilmDeck – Plustek OpticFilm 135i")
_t("top.check", "Scanner prüfen", "Check scanner")
_t("top.options", "Optionen", "Options")
_t("top.eject", "Auswerfen …", "Eject …")
_t("top.eject_tip", "Filmhalter auswerfen, wenn er klemmt oder nach einem Fehler noch im Scanner steckt",
   "Eject the film holder if it is stuck or still inside after an error")
_t("top.driver", "Treiber {version}", "Driver {version}")
_t("top.driver_demo", "Demo-Treiber {version}", "Demo driver {version}")
_t("top.driver_none", "Kein Treiber installiert", "No driver installed")

_t("scanner.checking", "Scanner wird geprüft …", "Checking the scanner …")
_t("scanner.unknown", "Scannerstatus unbekannt", "Scanner status unknown")
_t("scanner.unsafe", "Scanner unsicher – bitte aus- und einschalten", "Scanner not safe – please power-cycle it")
_t("scanner.ready_magazine", "Scanner bereit – Filmhalter erkannt", "Scanner ready – film holder detected")
_t("scanner.ready_no_magazine", "Scanner bereit – kein Filmhalter eingesteckt", "Scanner ready – no film holder inserted")
_t("scanner.no_driver", "Kein Treiber", "No driver")

# ----------------------------------------------------------------------------- update banner and dialog
_t("banner.update", "Neue Treiberversion {new} verfügbar (installiert: {installed}).",
   "New driver version {new} available (installed: {installed}).")
_t("banner.up_to_date", "Der Treiber ist aktuell (Version {version}).", "The driver is up to date (version {version}).")
_t("banner.notes", "Neuerungen", "What's new")
_t("banner.update_now", "Jetzt aktualisieren", "Update now")

_t("upd.title", "Treiber-Update", "Driver update")
_t("upd.versions", "Installiert: {installed}  →  Neu: {new}", "Installed: {installed}  →  New: {new}")
_t("upd.notes_online", "Die Neuerungen stehen online:", "The release notes are online:")
_t("upd.no_notes", "Es sind keine Neuerungen angegeben.", "No release notes were provided.")
_t("upd.ignore", "Diese Version ignorieren", "Skip this version")
_t("upd.later", "Später", "Later")
_t("upd.install", "Jetzt installieren", "Install now")
_t("upd.installing", "Treiber wird heruntergeladen und installiert …", "Downloading and installing the driver …")
_t("upd.busy", "Während eines Scans wird nicht aktualisiert.", "No updates while a scan is running.")
_t("upd.not_managed",
   "Dieser Treiber liegt in einem eigenen Ordner und wird nicht von FilmDeck verwaltet. Bitte dort selbst "
   "aktualisieren (git pull) oder in den Optionen zum verwalteten Treiber wechseln.",
   "This driver lives in a folder of your own and is not managed by FilmDeck. Update it there yourself "
   "(git pull) or switch to the managed driver in the options.")
_t("upd.done", "Treiber {version} ist installiert.", "Driver {version} is installed.")
_t("upd.failed", "Update fehlgeschlagen", "Update failed")
_t("upd.failed_text", "Der bisherige Treiber bleibt aktiv. Fehler: {error}",
   "The previous driver stays active. Error: {error}")
_t("upd.rolled_back", "Zurück auf die vorige Treiberversion ({name}).", "Rolled back to the previous driver version ({name}).")

_t("drv.install.title", "Treiber installieren", "Install the driver")
_t("drv.install.button", "Treiber {version} installieren", "Install driver {version}")
_t("drv.offline.title", "Treiber nicht verfügbar", "Driver not available")
_t("drv.offline.text",
   "Der Scanner-Treiber (opticfilm135i-linux) ist noch nicht installiert und konnte nicht heruntergeladen werden. "
   "Bitte die Internetverbindung prüfen oder in den Optionen einen vorhandenen Treiberordner wählen.",
   "The scanner driver (opticfilm135i-linux) is not installed yet and could not be downloaded. Please check the "
   "internet connection or pick an existing driver folder in the options.")

# ----------------------------------------------------------------------------- main form
_t("mode.strip", "Einzelner Streifen", "Single strip")
_t("mode.film", "Ganzer Film", "Whole film")

_t("form.name", "Name / Ordner", "Name / folder")
_t("form.name_placeholder", "JJ-MM-Film-Kamera", "YY-MM-Film-Camera")
_t("form.name_auto", "Name aus Datum, Film und Kamera neu bilden", "Rebuild the name from date, film and camera")
_t("form.existing", "Diesen Film gibt es schon mit {n} Bildern – neue Bilder werden ab Nr. {next} angehängt.",
   "This film already has {n} images – new images are added from no. {next}.")
_t("form.film", "Film", "Film")
_t("form.film_placeholder", "z. B. Kodak Gold", "e.g. Kodak Gold")
_t("form.camera", "Kamera", "Camera")
_t("form.camera_placeholder", "z. B. Nikon F3", "e.g. Nikon F3")
_t("form.save_preset", "In der Auswahl speichern", "Save to the drop-down list")
_t("form.type", "Filmtyp", "Film type")
_t("form.type.c41", "Farbe (C-41)", "Colour (C-41)")
_t("form.type.bw", "Schwarzweiß", "Black & white")
_t("form.dpi", "Auflösung", "Resolution")
_t("form.bits", "Bit-Tiefe", "Bit depth")
_t("form.bits.48", "48 Bit – Farbe, 16 Bit je Kanal", "48 bit – colour, 16 bit per channel")
_t("form.bits.24", "24 Bit – Farbe, 8 Bit je Kanal", "24 bit – colour, 8 bit per channel")
_t("form.bits.16", "16 Bit – Graustufen", "16 bit – greyscale")
_t("form.bits.8", "8 Bit – Graustufen", "8 bit – greyscale")
_t("form.size_hint", "ca. {mb} MB je Bild", "about {mb} MB per image")
_t("form.size_hint_ir", "ca. {mb} MB je Bild, dazu eine Infrarot-Datei", "about {mb} MB per image, plus an infrared file")
_t("form.dpi_7200_hint",
   "7200 dpi tastet doppelt so fein ab wie die 3600 dpi des Sensors: vierfache Dateigröße, sehr lange Scanzeit und viel "
   "Arbeitsspeicher, der Gewinn an echtem Detail ist meist klein.",
   "7200 dpi samples twice as finely as the sensor's 3600 dpi: four times the file size, a very long scan and a lot of "
   "memory; the gain in real detail is usually small.")
_t("form.frames", "Zu scannende Bilder", "Frames to scan")
_t("form.frames_first", "Bilder des 1. Streifens", "Frames of strip 1")
_t("form.frames_hint",
   "Ein Bild anklicken, um es auszulassen (z. B. eine leere Öffnung). Das spart Scanzeit; die Nummern der "
   "übrigen Bilder bleiben lückenlos.",
   "Click a frame to skip it (e.g. an empty opening). That saves scan time; the remaining images stay numbered "
   "without gaps.")
_t("form.film_hint",
   "Alle Streifen landen als eine Filmrolle im selben Ordner, die Bilder werden lückenlos durchnummeriert. "
   "Nach jedem Streifen wirst du nach dem nächsten gefragt und wählst dort dessen Bilder. Ein leeres Bild nach "
   "dem Film beendet den Streifen automatisch.",
   "All strips end up in the same folder as one film roll, numbered without gaps. After every strip you are "
   "asked for the next one and choose its frames there. An empty frame after the film ends the strip "
   "automatically.")
_t("form.dir", "Speicherort", "Save to")

_t("btn.start_strip", "Streifen scannen", "Scan strip")
_t("btn.start_film", "Ganzen Film scannen", "Scan whole film")
_t("btn.cancel", "Abbrechen", "Cancel")
_t("btn.new_film", "Neuer Film", "New film")
_t("btn.negpy", "NegPy starten", "Start NegPy")
_t("btn.folder", "Ordner öffnen", "Open folder")
_t("log.show", "Protokoll anzeigen", "Show log")
_t("log.hide", "Protokoll ausblenden", "Hide log")
_t("frame.pending", "S{strip} · {frame}", "S{strip} · {frame}")

# ----------------------------------------------------------------------------- status line
_t("status.ready", "Bereit", "Ready")
_t("status.ready_hint",
   "Name, Filmtyp und Auflösung wählen und den Scan starten. Wann du den Filmhalter einschieben musst, "
   "sagt dir das Programm.",
   "Choose name, film type and resolution, then start the scan. The program tells you when to push in the film holder.")
_t("status.no_driver", "Kein Treiber installiert", "No driver installed")
_t("status.no_driver_hint",
   "FilmDeck braucht den Treiber opticfilm135i-linux von cgillinger. Er wird beim Start zur Installation "
   "angeboten, oder du wählst in den Optionen einen vorhandenen Treiberordner.",
   "FilmDeck needs the opticfilm135i-linux driver by cgillinger. It is offered for installation at start-up, "
   "or you can pick an existing driver folder in the options.")
_t("status.name_missing", "Bitte einen Namen eingeben", "Please enter a name")
_t("status.preset_saved", "„{name}“ wurde in der Auswahl gespeichert", "“{name}” was saved to the list")
_t("status.preset_exists", "Steht schon in der Auswahl (oder ist leer)", "Already in the list (or empty)")
_t("status.preflight", "Scanner wird geprüft …", "Checking the scanner …")
_t("status.jog", "Scanner fährt in die Ausgangsposition …", "The scanner moves to its start position …")
_t("status.reinsert", "Bitte Filmhalter neu einschieben", "Please re-insert the film holder")
_t("status.loading", "Streifen wird eingezogen …", "Loading the strip …")
_t("status.loading_hint", "Der Scanner zieht den Streifen ein. Bitte nichts anfassen.",
   "The scanner is pulling in the strip. Please do not touch anything.")
_t("status.next_strip_loading", "Streifen {strip} wird eingezogen …", "Loading strip {strip} …")
_t("status.next_strip_wait", "Bereit für den nächsten Streifen", "Ready for the next strip")
_t("status.scanning", "Scanne Bild {frame} von {total} (Streifen {strip})", "Scanning frame {frame} of {total} (strip {strip})")
_t("status.scanning_hint", "Das dauert je nach Auflösung mehrere Minuten. Scanner nicht ausschalten und nicht bewegen.",
   "Depending on the resolution this takes several minutes. Do not switch off or move the scanner.")
_t("status.empty_stop", "Leere Öffnung erkannt – der Rest des Streifens wird übersprungen",
   "Empty aperture found – the rest of the strip is skipped")
_t("status.exporting", "Bilder werden in den Filmordner übernommen …", "Moving the images into the film folder …")
_t("status.ejected", "Filmhalter wurde ausgeworfen", "The film holder was ejected")
_t("status.close_blocked", "Während eines Scans kann das Programm nicht geschlossen werden.",
   "The program cannot be closed while a scan is running.")

# ----------------------------------------------------------------------------- questions during a scan
_t("dlg.ok", "OK", "OK")
_t("dlg.close", "Schließen", "Close")
_t("dlg.copy", "Kopieren", "Copy")
_t("dlg.continue", "Weiter", "Continue")
_t("dlg.abort", "Abbrechen", "Abort")

_t("dlg.reinsert.title", "Filmhalter neu einschieben", "Re-insert the film holder")
_t("dlg.reinsert.text",
   "Den Filmhalter jetzt ganz aus dem Schacht ziehen und frisch bis zum mechanischen Anschlag wieder einschieben. "
   "Danach bestätigen.",
   "Pull the film holder completely out of the slot and push it in again, fresh, all the way to the mechanical "
   "stop. Then confirm.")
_t("dlg.reinsert.go", "Filmhalter sitzt am Anschlag", "Film holder is at the stop")

_t("dlg.prompt.title", "Frage vom Treiber", "Question from the driver")
_t("dlg.prompt.text", "Der Treiber wartet auf eine Bestätigung:\n\n{text}", "The driver is waiting for a confirmation:\n\n{text}")

_t("dlg.next.title", "Nächster Streifen", "Next strip")
_t("dlg.next.text",
   "Bisher {images} Bilder im Film. Für den nächsten Streifen: Filmhalter aus dem Scanner nehmen, neuen Streifen "
   "einlegen und den Halter bis zum Anschlag einschieben. Dann „Nächster Streifen“ drücken. Ist der Film zu Ende, "
   "„Film beenden“ wählen.",
   "{images} images in the film so far. For the next strip: take the film holder out of the scanner, insert a new "
   "strip and push the holder in to the stop. Then press “Next strip”. If the film is finished, choose “Finish film”.")
_t("dlg.next.frames", "Welche Bilder hat der nächste Streifen?", "Which frames does the next strip have?")
_t("dlg.next.go", "Nächster Streifen", "Next strip")
_t("dlg.next.finish", "Film beenden", "Finish film")

_t("dlg.cancel.title", "Scan abbrechen?", "Cancel the scan?")
_t("dlg.cancel.text",
   "Wenn du jetzt abbrichst, muss der Scanner danach aus- und wieder eingeschaltet werden. Bereits fertige Bilder "
   "bleiben erhalten.",
   "If you cancel now, the scanner has to be switched off and on again afterwards. Images that are already finished "
   "are kept.")
_t("dlg.cancel.keep", "Weiter scannen", "Keep scanning")
_t("dlg.cancel.stop", "Scan abbrechen", "Cancel scan")

_t("dlg.power.title", "Scanner neu starten", "Restart the scanner")
_t("dlg.power.text",
   "Der Scanner ist in einem unsicheren Zustand (Scan abgebrochen oder fehlgeschlagen). Bitte den Scanner "
   "ausschalten, einige Sekunden warten und wieder einschalten. Erst danach kann wieder gescannt werden.",
   "The scanner is in an unsafe state (scan aborted or failed). Please switch the scanner off, wait a few seconds "
   "and switch it on again. Only then can you scan again.")
_t("dlg.power.done", "Scanner wurde neu gestartet", "I restarted the scanner")
_t("dlg.power.later", "Später", "Later")

_t("dlg.eject.title", "Filmhalter auswerfen", "Eject the film holder")
_t("dlg.eject.text",
   "Nur verwenden, wenn der Filmhalter klemmt oder nach einem Fehler noch im Scanner steckt.\n\n"
   "Wenn der letzte Scan fehlgeschlagen ist oder abgebrochen wurde: Scanner ZUERST aus- und wieder einschalten, "
   "einige Sekunden warten, dann erst auswerfen. Der Treiber verweigert das Auswerfen aus einem unsicheren Zustand.",
   "Only use this if the film holder is stuck or is still inside the scanner after an error.\n\n"
   "If the last scan failed or was cancelled: FIRST switch the scanner off and on again, wait a few seconds, and "
   "only then eject. The driver refuses to eject from an unsafe state.")
_t("dlg.eject.confirm", "Scanner wurde aus- und wieder eingeschaltet", "Scanner was switched off and on again")
_t("dlg.eject.go", "Jetzt auswerfen", "Eject now")
_t("status.ejecting", "Filmhalter wird ausgeworfen …", "Ejecting the film holder …")
_t("status.ejecting_hint", "Das kann bis zu einer Minute dauern. Scanner nicht ausschalten.",
   "This can take up to a minute. Do not switch off the scanner.")
_t("eject.done.title", "Filmhalter ausgeworfen", "Film holder ejected")
_t("eject.done.text", "Du kannst den Halter jetzt aus dem Scanner nehmen.", "You can take the holder out of the scanner now.")
_t("eject.failed.title", "Auswerfen fehlgeschlagen", "Eject failed")
_t("eject.failed.text", "{detail}", "{detail}")

# ----------------------------------------------------------------------------- NegPy
_t("negpy.missing.title", "NegPy nicht gefunden", "NegPy not found")
_t("negpy.missing.text",
   "NegPy wurde nicht gefunden. Bitte in den Optionen die NegPy-Datei (AppImage) auswählen.",
   "NegPy was not found. Please pick the NegPy file (AppImage) in the options.")
_t("negpy.started", "NegPy wurde gestartet", "NegPy was started")
_t("negpy.hint", "Der Ordnerpfad liegt in der Zwischenablage: {folder}\nIn NegPy „Add Folder“ wählen und einfügen.",
   "The folder path is on the clipboard: {folder}\nIn NegPy choose “Add Folder” and paste it.")
_t("negpy.failed", "NegPy konnte nicht gestartet werden", "NegPy could not be started")

# ----------------------------------------------------------------------------- results
_t("res.ok.title", "Scan fertig", "Scan finished")
_t("res.ok.text", "{new} neue Bilder gespeichert, {total} im Film.\n{folder}", "{new} new images saved, {total} in the film.\n{folder}")
_t("res.partial.title", "Scan fertig, aber nicht vollständig", "Scan finished, but incomplete")
_t("res.partial.text",
   "{new} neue Bilder gespeichert. Für die Bilder Nr. {missing} gibt es keine Datei; ihre Nummern bleiben "
   "reserviert.\n{folder}",
   "{new} new images saved. There is no file for images no. {missing}; their numbers stay reserved.\n{folder}")
_t("miss.title.one", "Bild {numbers} fehlt", "Image {numbers} is missing")
_t("miss.title.many", "Bilder {numbers} fehlen", "Images {numbers} are missing")
_t("miss.reason.lead",
   "Bild {number} wurde gescannt, aber nicht gespeichert: Der Anfang der Bildöffnung lag zu nah am Rand des Scanbereichs.",
   "Image {number} was scanned but not saved: the start of the film opening was too close to the edge of the scan area.")
_t("miss.reason.trail",
   "Bild {number} wurde gescannt, aber nicht gespeichert: Das Ende der Bildöffnung lag zu nah am Rand des Scanbereichs.",
   "Image {number} was scanned but not saved: the end of the film opening was too close to the edge of the scan area.")
_t("miss.reason.both",
   "Bild {number} wurde gescannt, aber nicht gespeichert: Die Bildöffnung lag auf beiden Seiten zu nah am Rand.",
   "Image {number} was scanned but not saved: the film opening was too close to the edge on both sides.")
_t("miss.reason.other",
   "Bild {number} wurde gescannt, aber nicht gespeichert: Die Bildöffnung wurde nicht sicher erkannt ({reason}).",
   "Image {number} was scanned but not saved: the film opening was not found reliably ({reason}).")
_t("miss.reason.stage",
   "Für Bild {number} gibt es keine Datei: Es wurde nicht zu Ende gescannt, zum Beispiel weil der Scan abgebrochen wurde.",
   "There is no file for image {number}: it was not scanned to the end, for example because the scan was cancelled.")
_t("miss.reserved.one", "Die Nummer bleibt reserviert.", "The number stays reserved.")
_t("miss.reserved.many", "Die Nummern bleiben reserviert.", "The numbers stay reserved.")
_t("miss.overscan",
   "Der ganze Scan von Bild {number} (nicht zugeschnitten) liegt als {file} im Filmordner.",
   "The whole scan of image {number} (not cropped) is in the film folder as {file}.")
_t("miss.advice",
   "Dein Scanner sitzt etwa {shift} mm {direction} als vom Treiber angenommen (gemessen an {frames} Bildern). "
   "Stelle unter Optionen → Scan „Bildlage verschieben“ auf {suggested} mm und scanne neu.",
   "Your scanner sits about {shift} mm {direction} than the driver assumes (measured over {frames} images). "
   "Set “Shift the frame position” in Options → Scan to {suggested} mm and scan again.")
_t("miss.earlier", "früher", "earlier")
_t("miss.later", "später", "later")
_t("miss.hint_generic",
   "Passiert das öfter, hilft „Bildlage verschieben“ unter Optionen → Scan.",
   "If this happens often, “Shift the frame position” in Options → Scan helps.")
_t("miss.apply", "Bildlage {value} mm übernehmen", "Use frame shift {value} mm")
_t("miss.applied", "Bildlage auf {value} mm gestellt", "Frame shift set to {value} mm")
_t("res.cancelled.title", "Scan abgebrochen", "Scan cancelled")
_t("res.cancelled.text", "Der Scan wurde beendet. {new} Bilder sind gespeichert.", "The scan was stopped. {new} images are saved.")
_t("res.cancelled.power",
   "Der Scan wurde abgebrochen. {new} Bilder sind gespeichert. Der Scanner muss jetzt aus- und wieder eingeschaltet werden.",
   "The scan was cancelled. {new} images are saved. The scanner must now be switched off and on again.")
_t("res.power_cycle_hint", "Bitte den Scanner aus- und wieder einschalten, bevor du erneut scannst.",
   "Please switch the scanner off and on again before you scan again.")
_t("res.kept_images", "{new} bereits fertige Bilder bleiben erhalten.", "{new} images that were already finished are kept.")

# ----------------------------------------------------------------------------- error codes (title + text each)
_t("err.busy.title", "Scanner ist belegt", "Scanner is busy")
_t("err.busy.text", "Ein anderes Programm oder ein anderer Treiber-Prozess benutzt den Scanner. Beende es und versuche es erneut.",
   "Another program or driver process is using the scanner. Close it and try again.")
_t("err.bad_args.title", "Einstellung nicht akzeptiert", "Setting not accepted")
_t("err.bad_args.text",
   "Der Treiber (Version {version}) hat die Optionen nicht akzeptiert. Vielleicht ist er zu alt – dann den Treiber aktualisieren.\n\n{detail}",
   "The driver (version {version}) did not accept the options. It may be too old – update the driver.\n\n{detail}")
_t("err.no_scanner.title", "Kein Scanner gefunden", "No scanner found")
_t("err.no_scanner.text",
   "USB-Kabel und Netzteil prüfen und den Scanner einschalten. Danach oben „Scanner prüfen“ drücken.\n\n{detail}",
   "Check the USB cable and the power supply and switch the scanner on. Then press “Check scanner” at the top.\n\n{detail}")
_t("err.no_permission.title", "Keine USB-Berechtigung", "No USB permission")
_t("err.no_permission.text",
   "Der Zugriff auf den Scanner ist nicht erlaubt, die udev-Regel des Treibers fehlt vermutlich. Die Anleitung "
   "steht in Optionen → Treiber.\n\n{detail}",
   "Access to the scanner is not allowed; the driver's udev rule is probably missing. The instructions are in "
   "Options → Driver.\n\n{detail}")
_t("err.no_backend.title", "USB-Bibliothek fehlt", "USB library missing")
_t("err.no_backend.text", "pyusb oder libusb wurde nicht gefunden.\n\n{detail}", "pyusb or libusb was not found.\n\n{detail}")
_t("err.no_magazine.title", "Kein Filmhalter erkannt", "No film holder detected")
_t("err.no_magazine.text",
   "Der Sensor meldet keinen Filmhalter im Schacht. Halter einschieben und erneut starten.",
   "The sensor reports no film holder in the slot. Insert the holder and start again.")
_t("err.cold.title", "Scanner noch nicht geladen", "Scanner not loaded yet")
_t("err.cold.text",
   "Der Scanner wurde seit dem letzten Laden aus- und eingeschaltet. Ein Streifen muss zuerst mit dem vollständigen "
   "Ladevorgang geladen werden.",
   "The scanner was power-cycled since the last load. A strip has to be loaded with the full load procedure first.")
_t("err.unsafe_state.title", "Scanner in unsicherem Zustand", "Scanner in an unsafe state")
_t("err.unsafe_state.text", "Bitte den Scanner aus- und wieder einschalten.\n\n{detail}",
   "Please switch the scanner off and on again.\n\n{detail}")
_t("err.load_failed.title", "Laden fehlgeschlagen", "Loading failed")
_t("err.load_failed.text",
   "Der Filmhalter wurde nicht eingezogen. Scanner aus- und einschalten, Halter ganz herausziehen und neu versuchen.\n\n{detail}",
   "The film holder was not pulled in. Power-cycle the scanner, pull the holder all the way out and try again.\n\n{detail}")
_t("err.interrupted.title", "Unterbrochen", "Interrupted")
_t("err.interrupted.text", "Der Treiber wurde unterbrochen.\n\n{detail}", "The driver was interrupted.\n\n{detail}")
_t("err.scan_failed.title", "Scan fehlgeschlagen", "Scan failed")
_t("err.scan_failed.text", "{detail}", "{detail}")
_t("err.status_failed.title", "Scannerstatus nicht lesbar", "Cannot read the scanner status")
_t("err.status_failed.text", "{detail}", "{detail}")
_t("err.driver_old.title", "Treiber zu alt", "Driver too old")
_t("err.driver_old.text", "FilmDeck braucht den Treiber ab Version 0.2.11 (installiert: {version}). Bitte aktualisieren.",
   "FilmDeck needs driver version 0.2.11 or newer (installed: {version}). Please update.")
_t("err.no_space.title", "Zu wenig Speicherplatz", "Not enough disk space")
_t("err.no_space.text", "Auf dem Speicherort ist nicht genug Platz für diesen Scan. Anderen Speicherort wählen oder Platz schaffen.\n\n{detail}",
   "The save location does not have enough free space for this scan. Choose another location or free some space.\n\n{detail}")
_t("err.no_write.title", "Speicherort nicht beschreibbar", "Save location not writable")
_t("err.no_write.text", "In den Zielordner kann nicht geschrieben werden.\n\n{detail}", "Cannot write to the target folder.\n\n{detail}")
_t("err.export_failed.title", "Bilder konnten nicht übernommen werden", "Images could not be moved")
_t("err.export_failed.text",
   "Der Scan ist fertig, aber die Bilder konnten nicht in den Filmordner übernommen werden. Die Originale liegen im "
   "versteckten Ordner „.driver“ im Filmordner.\n\n{detail}",
   "The scan is finished, but the images could not be moved into the film folder. The originals are in the hidden "
   "“.driver” folder inside the film folder.\n\n{detail}")
_t("err.internal.title", "Interner Fehler", "Internal error")
_t("err.internal.text", "{detail}\n\nBitte filmdeck.log und das neueste Protokoll unter ~/.local/share/filmdeck/logs/ mitschicken.",
   "{detail}\n\nPlease send filmdeck.log and the newest log in ~/.local/share/filmdeck/logs/ along.")

# ----------------------------------------------------------------------------- options
_t("opt.title", "Optionen", "Options")
_t("opt.ok", "Übernehmen", "Apply")
_t("opt.cancel", "Abbrechen", "Cancel")
_t("opt.browse", "Auswählen …", "Browse …")
_t("opt.tab.general", "Allgemein", "General")
_t("opt.tab.scan", "Scan", "Scan")
_t("opt.tab.files", "Dateien", "Files")
_t("opt.tab.presets", "Listen", "Lists")
_t("opt.tab.driver", "Treiber", "Driver")

_t("opt.language", "Sprache", "Language")
_t("opt.scan_dir", "Standard-Speicherort", "Default save location")
_t("opt.pick_folder", "Ordner wählen", "Choose a folder")
_t("opt.negpy", "NegPy (Programmdatei)", "NegPy (program file)")
_t("opt.negpy_none", "nicht gefunden – bitte auswählen", "not found – please pick it")
_t("opt.negpy_hint",
   "Leer lassen, dann sucht FilmDeck NegPy selbst (z. B. als AppImage im Home-Ordner oder in ~/Applications).",
   "Leave empty and FilmDeck looks for NegPy itself (e.g. an AppImage in your home folder or ~/Applications).")
_t("opt.pick_negpy", "NegPy auswählen", "Choose NegPy")
_t("opt.check_updates", "Beim Start nach einem neuen Treiber suchen", "Look for a new driver at start-up")
_t("opt.channel", "Update-Quelle", "Update source")
_t("opt.channel.release", "Veröffentlichte Versionen (empfohlen)", "Published releases (recommended)")
_t("opt.channel.master", "Neuester Stand (master)", "Latest state (master)")
_t("opt.channel_hint", "„Neuester Stand“ kann noch ungetestete Änderungen enthalten.",
   "“Latest state” may contain changes that are not tested yet.")

_t("opt.rotate", "Bild drehen", "Rotate image")
_t("opt.rotate_hint", "Dreht jedes Bild beim Scan, falls der Streifen anders herum im Halter liegt.",
   "Rotates every image while scanning, in case the strip sits the other way round in the holder.")
_t("opt.dust", "Staub und Kratzer mit Infrarot entfernen (nur Farbfilm)", "Remove dust and scratches with infrared (colour film only)")
_t("opt.dust_hint", "Schwarzweißfilm wird immer ohne Infrarot gescannt.", "Black & white film is always scanned without infrared.")
_t("opt.fast_next", "Nächster Streifen ohne neues Initialisieren", "Next strip without re-initialising")
_t("opt.fast_next_hint",
   "Spart Zeit bei Filmen mit mehreren Streifen. Funktioniert nur, solange der Scanner nicht ausgeschaltet wurde; "
   "sonst lädt das Programm automatisch vollständig.",
   "Saves time on films with several strips. Only works while the scanner has not been switched off; otherwise "
   "the program automatically does the full load.")
_t("opt.offset", "Bildlage verschieben", "Shift the frame position")
_t("opt.offset_default", "Voreinstellung des Treibers", "Driver default")
_t("opt.offset_hint",
   "−3 bis +3 mm. Negativ: Scanbereich beginnt früher. Den passenden Wert nennt FilmDeck, wenn ein Bild fehlt.",
   "−3 to +3 mm. Negative: the scan area starts earlier. FilmDeck names the right value when an image is missing.")

_t("opt.preview", "Vorschaubilder (JPEG)", "Preview images (JPEG)")
_t("opt.preview.off", "Keine", "None")
_t("opt.preview.tiny", "Winzig (160 px)", "Tiny (160 px)")
_t("opt.preview.small", "Klein (320 px)", "Small (320 px)")
_t("opt.preview.medium", "Mittel (640 px)", "Medium (640 px)")
_t("opt.preview_hint", "Liegen im versteckten Ordner „.previews“ im Filmordner.",
   "They are kept in the hidden “.previews” folder inside the film folder.")
_t("opt.export_ir", "Infrarot-Datei zu jedem Farbbild speichern (…_ir.tiff)", "Save an infrared file next to every colour image (…_ir.tiff)")
_t("opt.export_ir_hint", "NegPy erkennt diese Datei als Infrarotkanal.", "NegPy recognises this file as the infrared channel.")
_t("opt.keep_overscan", "Gesamte Abtastfläche behalten (Overscan)", "Keep the whole scanned area (overscan)")
_t("opt.keep_overscan_hint", "Große Zusatzdateien; nur für Fehlersuche oder eigenes Nachbeschneiden.",
   "Large extra files; only for troubleshooting or cropping on your own.")
_t("opt.cal_data", "Kalibrierdaten zu jedem Bild speichern", "Save calibration data with every image")
_t("opt.cal_data_hint", "Je Bild etwa 13 MB zusätzlich. Normalerweise ausgeschaltet lassen.",
   "About 13 MB extra per image. Normally leave this off.")
_t("opt.bits_hint",
   "Ausgabe ist immer TIFF. Der Scanner liefert 48 Bit (Farbe, 16 Bit je Kanal, beste Qualität). 24 Bit (Farbe), "
   "16 und 8 Bit (Graustufen) rechnet FilmDeck nach dem Scan daraus um.",
   "Output is always TIFF. The scanner delivers 48 bit (colour, 16 bit per channel, best quality). FilmDeck "
   "converts 24 bit (colour) and 16 and 8 bit (greyscale) from that after the scan.")

_t("opt.films", "Filme", "Films")
_t("opt.cameras", "Kameras", "Cameras")
_t("opt.new_entry", "Neuer Eintrag", "New entry")
_t("opt.add", "Hinzufügen", "Add")
_t("opt.remove", "Entfernen", "Remove")
_t("opt.presets_hint", "Diese Listen erscheinen als Auswahl im Hauptfenster.", "These lists appear as drop-downs in the main window.")

_t("opt.check_now", "Jetzt nach Update suchen", "Check for updates now")
_t("opt.rollback", "Vorige Version wiederherstellen", "Restore the previous version")
_t("opt.custom_driver", "Eigenen Treiberordner wählen …", "Choose your own driver folder …")
_t("opt.managed_driver", "Verwalteten Treiber verwenden", "Use the managed driver")
_t("opt.pick_driver", "Treiberordner wählen (der Ordner mit „of135i“)", "Choose the driver folder (the one containing “of135i”)")
_t("opt.doctor", "Hardware-Bericht (doctor)", "Hardware report (doctor)")
_t("opt.doctor_hint", "Liest nur aus und verändert nichts am Scanner. Nützlich, wenn etwas nicht klappt.",
   "Read-only; changes nothing on the scanner. Useful when something does not work.")
_t("opt.driver_none", "Kein Treiber installiert.", "No driver installed.")
_t("opt.driver_demo", "Demo", "demo")
_t("opt.driver_managed", "von FilmDeck verwaltet", "managed by FilmDeck")
_t("opt.driver_custom", "eigener Ordner", "own folder")
_t("opt.driver_info", "Version {version} ({where})\n{path}", "Version {version} ({where})\n{path}")
_t("opt.driver_source", "Quelle: {label}", "Source: {label}")
_t("opt.usb_title", "USB-Zugriff einrichten (einmalig)", "Set up USB access (once)")
_t("opt.usb_text",
   "Wenn der Scanner „Keine USB-Berechtigung“ meldet, diese Befehle im Terminal ausführen. Der Scanner muss danach "
   "einmal aus- und wieder eingesteckt werden.",
   "If the scanner reports “No USB permission”, run these commands in a terminal. Afterwards unplug the scanner "
   "and plug it in again once.")
_t("opt.usb_readonly", "SteamOS schützt das Systemlaufwerk; vorher entsperren, danach wieder sperren.",
   "SteamOS protects the system drive; unlock it first and lock it again afterwards.")
