# 📘 Benutzerhandbuch — DJ Gadget AI-Suite Pro

**Version 3.3.1 · November 2026 · Developed by @bagueDev · Kontakt: achten.enteral.5z@icloud.com**

Dieses Handbuch vereint die bisherigen Einzel-Handbücher (v1.0, v1.4, v1.5, v1.6.3, V2.0) in einem Dokument und ist auf Stand v3.3.1 aktualisiert. Die Originale liegen im Ordner `Doku und Handbuch/Archiv/`. Detail-Changelogs (v1.5, v1.7, v1.8, v2.0) liegen separat als `.docx`.

---

## 1. Willkommen & Philosophie 🎧

Die DJ Gadget AI-Suite Pro ist das Schweizer Taschenmesser für DJs, Produzenten und Musiker: analysieren, samplen, trennen, komponieren, texten und brainstormen — alles in einer App.

- **100 % Offline:** keine Cloud, kein Abo. Alle KIs (Demucs, Whisper, Llama) laufen lokal auf deinem Rechner.
- **All-in-One:** ersetzt Analyzer-, Tagging-, Stems-, Transkriptions- und Chat-Spezialtools.
- **High-End-Qualität:** Demucs (Stems), Faster-Whisper (Lyrics), llama-server mit Metal-Beschleunigung (Chat).
- **Formate:** MP3, WAV, FLAC, M4A, AIFF — inkl. Cover-Tagging auch bei WAV/AIFF.

## 2. Installation & Ordnerstruktur 🚀

### Die goldene Ordnerstruktur
Die App ist portabel — lege sie mit diesen Ordnern zusammen ab (fehlende Ordner erstellt die App selbst):

```
📱 DJ Gadget AI-Suite Pro.app   (das Programm)
📁 AI_Models                    (deine .gguf Chat-Modelle)
📁 Offline_Models               (Demucs-Modelle + demucs-mlx-Cache)
📁 Whisper_Models               (Transkriptions-Modelle)
📁 Chat_History                 (automatisch gespeicherte Chats)
```

### Erster Start auf macOS
- Ordner auf die Festplatte (oder USB-Stick, inkl. Modell-Ordner) kopieren.
- Rechtsklick auf die App → „Öffnen" → bestätigen (Gatekeeper, nur einmal).
- Der erste Start kann 10–20 Sekunden dauern (KI-Engines werden geprüft).
- Oben im Header die Schriftgröße (12–20) anpassen.

## 3. Oberfläche: Header, Tabs, Footer 🖥️

### Header (oben)
- Musik-Ordner-Pfad + 📂 Öffnen
- Schriftgröße 12–20
- Dark/Light/System-Modus
- ℹ️ About-Fenster (Version, Lizenzen, Kontakt, F2)

### Tabs (Mitte)
🔍 Playlist & BPM Analyzer · ✏️ Metadata Editor · ✂️ Stems AI · 🎹 Melody Lab · 📝 Transcriber · 🤖 AI Chat · 📝 Log

### Footer (unten) — Export
- Playlist benennen
- Rekordbox XML (Pioneer), M3U (Traktor/Serato/VLC), JSON (Backup/Dev)
- 💾 EXPORT speichert in den Musik-Ordner
- **🔄 UPDATE** überschreibt die zuletzt exportierte oder importierte Playlist-Datei mit der aktuellen Liste, statt eine neue Datei anzulegen.
  - Vor dem Überschreiben erscheint eine **Rückfrage** mit den betroffenen Dateien und der Track-Anzahl.
  - Die alte Version wird als **`<datei>.bak`** daneben gesichert. Es gibt immer nur eine Sicherung: das nächste Update überschreibt sie.
  - ⚠️ **Filter aktiv?** Geschrieben werden nur die sichtbaren Tracks; die Rückfrage warnt dich in dem Fall. Im Zweifel erst den Filter zurücksetzen.
  - ⚠️ **Importierte Rekordbox-XML:** Update ersetzt die ganze Datei durch die aktuelle Liste. Nicht auf die Original-Sammlung anwenden, sondern auf eine Kopie.

## 4. Analyzer — Playlist & BPM 🔍

- **Folder Scan / File+:** ganze Ordner oder einzelne Tracks laden; mehrfach ausführbar ohne Listenverlust.
- **Smart Analysis:** BPM, Tonart (Camelot), Tracklänge. BPM-Range (Min/Max) gegen Halftime-Fehler — z. B. 160–190 für DnB (174 statt 87).
- **Auto-Tag ⚠️:** schreibt BPM + Key direkt in die Datei (nur diese zwei Felder, Rest bleibt erhalten).
- **Tabelle:** sortieren, filtern (BPM-Range, Key wie 8A, Textsuche — kombinierbar), `D` zum Löschen, `Z`/↩️ Undo.
- Rescan einzelner Tracks (0-BPM-Fälle), x2//2-Korrektur per Rechtsklick.
- **Pro-Player & Sampler:** Play/Pause (Toggle), Stop, ±10 s Spulen; IN/OUT-Punkte; 🧲 Snap to Beat (magnetisches Taktgitter); Smart Loops 2/4/8/16/32 Bars ab aktueller Position; 🔁 Preview-Loop; ➡️ Exit Loop (phasenrein); 💾 Save Loop als WAV (✨ Polish: Normalisierung + Micro-Fades).

## 5. Metadata Editor ✏️

- Links Liste, rechts Live-Vorschau (Cover + Tags); ℹ️ More/Raw-Data-Fenster mit Bitrate/ISRC/Encoder (aktualisiert live).
- Cover tauschen (JPG/PNG, auch WAV/AIFF); Artist/Title/Album (+ BPM/Key/Camelot/Track) bearbeiten; 💾 SPEICHERN schreibt permanent (ID3v2.3).
- Rechtsklick: Copy/Paste in allen Feldern; Sync aus Analyzer (T).

## 6. Stems AI ✂️ (Stand v3.3)

- **Demucs 4.1.0 + MLX-Backend:** trennt Drums/Bass/Vocals/Other (Standard), + Piano/Gitarre mit `htdemucs_6s`.
- **Backend-Wahl:** Auto (ARM Mac → schneller MLX-Pfad, sonst Torch), MLX (ARM, schnell) oder Torch — Fallback automatisch.
- **Modelle:** `htdemucs` (Standard), `htdemucs_ft` (feiner, langsamer), `htdemucs_6s` (6 Spuren), `mdx`/`mdx_extra(_q)` (Torch, max. Qualität, viel RAM).
- **no_*-Methode (Instrumental Mode):** `add` = Stems summieren · `minus` = Original-minus-Stem (exakt) · `none` = nur Vocals speichern.
- Batch-Queue (über Nacht laufen lassen), Stem-Auswahl spart Platz, ⬇️ Offline Load lädt Modelle einmalig mit Internet (danach bunker-fähig).

## 7. Melody Lab 🎹

### Generator
- **Modi:** 🎶 Melody (Mono/Power/Triads/7ths/9ths/Sus/Add9/6-9), 🥁 Drums (Genre-Pattern-Pools, Phrasen-Wechsel alle 2 Takte), 🎹 Chords (Voicings inkl. Smart Smooth).
- **Genre** (13), **Skala** (19, inkl. Exoten), Root-Key, Taktart (4/4, 3/4, 6/8), Oktavlage, Chord-Progression-Presets (~40).
- **Regler:** Density, Swing, 🤖➡️🧑 Humanize (Velocity + Timing). Sound: sine/saw/square/epiano.
- **🎲 Generate**, **✨ Full Loop** (alle 6 Spuren + Fortschritt + ⏹ Stop), ▶ Play, 💾 MIDI (DAW-Export). Max. 128 Bars (RAM-Schutz).
- Dropdown-Wechsel (Genre, Waveform, Progression, Voicing) spielen automatisch eine 2-Bar-Vorschau ab. Dein generiertes Ergebnis bleibt dabei erhalten: ▶ Play und 💾 MIDI beziehen sich weiter auf die volle Sequenz. Während einer laufenden Generierung gibt es keine Vorschau.
- **Progression „Random":** Im Full Loop wird einmal ein Preset gewürfelt, das alle Spuren gemeinsam spielen; welches es war, steht im Log. Im einzelnen Chords-Modus bleibt „Random" eine zufällige Stufe pro Takt.

### Drums & Bass im Full Loop 🥁 (neu in v3.3.1)
- **Bass folgt der Kick:** Bei DnB, Trap und HipHop spielt der Bass mit **Complexity „Steady (Groove)" oder „Busy (Melodic)"** genau auf den Kicks der Drums. Density verändert dort die Hats und Ghost-Snares, nicht mehr die Zahl der Bassnoten.
- Willst du ein eigenes Bass-Muster, wähle unter Complexity eines der festen Patterns (z. B. „Neuro Roller"); die bleiben unabhängig von der Kick.
- **DnB** läuft in 8-Takt-Abschnitten: der Groove bleibt stehen, Takt 4 bekommt eine kleine Variation, Takt 8 einen Snare-Wirbel.

### Motive 🎵 (neu in v3.3.1)
Melodien werden nicht mehr Note für Note gewürfelt, sondern aus einem **Motiv** gebaut: einer kurzen, eintaktigen Figur, die wiederkehrt.

- **Aufbau in 4-Takt-Phrasen:** Takt 1 Motiv A · Takt 2 Motiv A mit anderem Ende · Takt 3 Kontrast-Motiv B · Takt 4 Motiv A mit Schluss auf dem Akkord-Grundton.
- **Mit Progression:** Das Motiv wandert mit den Akkorden mit, bleibt aber erkennbar. Mit „Random" im einzelnen Melody-Modus bleibt es auf dem Grundton.
- **Density** bestimmt, wie viele Töne das Motiv hat. Bei sehr niedriger Density besteht es nur aus ein, zwei Tönen.
- **Arrangements** (Radio Edit, DnB Journey …) bekommen für ruhige und volle Abschnitte je ein eigenes Motiv.
- Gefällt dir ein Motiv nicht: neu generieren. Gefällt es: 🔒 Lock setzen (siehe Seed).

### Seed 🎲 (neu in v3.3.1)
Der Seed ist die Startzahl für den Zufall. **Gleicher Seed + gleiche Einstellungen = exakt dasselbe Ergebnis** (MIDI und Audio), auch nach einem Neustart.

- **Ohne 🔒 Lock:** Jedes Generate / Full Loop würfelt einen neuen Seed (0–999999) und schreibt ihn ins Feld.
- **Mit 🔒 Lock:** Die Zahl im Feld wird benutzt. Du kannst auch eine notierte Zahl von früher eintippen.
- **Wo steht der Seed?** Im Status (`✅ Ready! (Seed 521392)`), im Log und als Vorschlag im Dateinamen beim MIDI-Speichern.

Typische Anwendungen:
- **Gutes Ergebnis festhalten:** Lock setzen, bevor du weiterklickst, oder den Seed aus dem Log notieren.
- **Gleiche Melodie, neuer Sound:** Lock an, Waveform wechseln, neu generieren. Die Noten bleiben gleich.
- **Vorschau passt zum Ergebnis:** Die 2-Bar-Vorschau nutzt den Seed im Feld und entspricht dem Anfang der vollen Sequenz.
- **Einzelspur aus dem Full Loop:** Mit gleichem Seed, gleichen Einstellungen und derselben Progression liefert 🎶 Melody allein dieselbe Melodie wie im Full Loop.

Ändert sich eine Einstellung, die Noten beeinflusst (Skala, Key, Density, Bars, Progression, Arrangement), ändert sich auch das Ergebnis trotz gleichem Seed.

### Audio to MIDI Converter (experimentell)
Der Converter arbeitet mit festen Regeln, nicht mit einem trainierten KI-Modell. Er liefert einen brauchbaren Startpunkt, den du in der DAW nachbearbeitest, keine fertige Transkription.

**Beste Quelle:** ein trockener Loop, eine einzelne Stimme oder ein Stem aus Stems AI (Drums-Stem für 🥁, Vocals-Stem für 🎶).

- **Sample laden** (MP3/WAV/FLAC/AIFF), **Länge** 10/20/40 s oder Full.
- **Modus 🥁 Drums:** sucht getrennt in Tiefen (Kick → C1), Mitten (Snare/Clap → D1) und Höhen (Hi-Hat → F#1). MIDI-Kanal 10, Velocity nach Schlagstärke.
- **Modus 🎶 Melody:** erkennt eine einstimmige Tonhöhe. Akkorde und mehrere Stimmen gleichzeitig gehen nicht.
- **Sens:** höher = mehr Noten, aber auch mehr Fehltreffer.
- **🧽 Smooth:** für Gesang und Vibrato. Glättet die Tonhöhe, verbindet zerhackte gehaltene Töne, verwirft Störnoten. Ohne Smooth werden wiederholte gleiche Töne an jedem neuen Anschlag getrennt (gut für Synths, Klavier, Bass).
- **🥁 BPM:** Tempo des Quell-Audios.
  - Datei per 📂 gewählt und im Analyzer gescannt → das BPM wird automatisch eingetragen.
  - Feld leer → das Tempo wird geschätzt. Bei schnellen Stilen kommt dabei oft das halbe Tempo heraus (87 statt 174); dann den richtigen Wert eintragen.
  - Eigener Wert (20–300) hat immer Vorrang. Das verwendete Tempo steht danach in Status, Log und Dialog.
- **🧲 Snap to 1/16 grid:** zieht alle Noten aufs 16tel-Raster und legt den Clip-Anfang auf einen Beat. Braucht ein stimmiges BPM; am besten das aus dem Analyzer. Für freies Timing (Gesang, Rubato) aus lassen.
- **🎚 Full mix (whole song):** für komplette Lieder. Trennt vor der Erkennung Schlagzeug und Töne. **Bei trockenen Loops und Stems aus lassen**, dort erzeugt es zusätzliche Fehltreffer. Rechnet bei langen Dateien einige Sekunden länger.

**Was du erwarten kannst (Drums):** Kicks werden bei trockenen Loops meist vollständig gefunden. Ein Clap oder eine Snare genau auf einer Kick wird oft nur als Kick erkannt, leise Zwischen-Hats fehlen meist. In einem ganzen Lied können Bass-Einsätze als Kick und Gesang als Snare auftauchen.

**Ausgabe:** `<name>_extracted.mid` neben dem Original; vor dem Überschreiben fragt die App nach. Ohne Grid ist Takt 1 der Anfang der Audiodatei.

## 8. Transcriber 📝

- Faster-Whisper offline (tiny bis medium); ⬇️ Offline-Button lädt Modelle nach `Whisper_Models`.
- Output: `.txt` + `.lrc` (Karaoke mit Zeitstempeln). Tipp: vorher Vocals per Stems isolieren.
- Batch-Queue für mehrere Dateien.

## 9. AI Chat 🤖 (Stand v3.3)

- GGUF-Modelle (z. B. Llama-3/Mistral-Instruct) nach `AI_Models` legen, 🔄 drücken, 🚀 Start (Metal-beschleunigt).
- **Erste Regler-Reihe:** 🌡️ Temp (0,1 faktisch – 1,2+ kreativ), 🔢 MaxT (Antwortlänge), 🚫🔁 Rep-Penalty (gegen Wiederholungen, ca. 1,1–1,2).
- **Zweite Reihe:** 🎯 TopP (0,5 fokussiert – 1,0 offen), 🔝 TopK (wirkt v. a. bei hoher Temp), 🧠 Ctx (512–256k, RAM beachten).
- **🔧 Server-Binary (optional):** eigene llama-server-Binary über Datei-Picker oder `~/.djgadget/chat_server.json` / `LLAMA_SERVER_PATH`. Standard = gebündelt.
- System Prompt = Rolle (z. B. Rap-Coach); 🗑️ Clear Context ohne Neustart; 📜 History als JSON; 🌐 HTML-Export; 🌐 Web UI im Browser.
- **Optionaler Webzugriff per MCP:** MCP-Proxy aktiv. Trage die URL deines eigenen MCP-Servers ein oder nutze V.I.N.C.E.N.T. (Open-Source-MCP-Server). Verbinde nur Server, denen du vertraust.

## 10. Log 📝

Fortschritt in Prozent + Fehlermeldungen aller Worker. Erster Blick bei Problemen.

## 11. Workflows

### Szenario A: DJ-Set vorbereiten
Downloads-Ordner in Tab 1 laden → Scan (Auto-Tag an) → nach Key sortieren → vorhören → Intros samplen → als M3U exportieren.

### Szenario B: Remix
Stems (Vocals) → Analyzer (exakte BPM) → Transcriber (Text) → Melody-Converter (Audio to MIDI) → MIDI in die DAW.

## 12. Performance-Hinweise ⚠️

- Trägheit bei Scan/Separation/Chat ist normal (Deep Learning) — kein Absturz. Buttons 1× klicken, Log abwarten.
- Grafik-Refresh-Trick: Fenster kurz bewegen/größe ändern erzwingt Neuzeichnen.
- Mac wird heiß/laut unter Volllast — normal und sicher. Intel: CPU-Modus, länger einplanen.
- Shortcuts sind in Textfeldern deaktiviert (Schutz vor Fehleingaben).

## 13. Troubleshooting & FAQ 🔧

- **App reagiert nicht:** warten, Log prüfen, nicht wild klicken.
- **Chat wirr/wiederholt sich:** Rep-Penalty hoch, Instruct-Modell prüfen, Engine neu starten.
- **Keine Stems:** ⬇️ Offline Load mit Internet ausgeführt? Log auf Fehler prüfen.
- **Auto-Tag-Datensicherheit:** überschreibt nur BPM + Key; Artist/Title/Album/Cover/Genre bleiben erhalten (MP3 → ID3v2.3).
- **Editor speichert:** nur befüllte Felder + ggf. neues Cover; BPM/Key bleiben erhalten.
- **Melody Lab meldet „❌ Error":** Die genaue Ursache steht im Log-Tab.
- **Audio-to-MIDI liegt in der DAW neben dem Raster:** BPM-Feld im Converter prüfen und das BPM aus dem Analyzer eintragen.
- **Playlist nach 🔄 UPDATE falsch:** Die vorherige Version liegt als `<datei>.bak` im selben Ordner. Zum Wiederherstellen die kaputte Datei löschen und bei der Sicherung die Endung `.bak` entfernen.

## Anhang: Versionen & Quellen

Zusammengeführt aus: Benutzerhandbuch v1.6.3 (Gerüst), DAS HANDBUCH v1.4 (MelodyLab/Workflows/FAQ), v1.5-Handbuch (Batch/Sampler/Tag-FAQ), V2.0-PDF (Performance/Ordnerstruktur), V1.0-PDF (Grundlagen). Originale: Ordner `Doku und Handbuch/Archiv/`. Detail-Changelogs (v1.5, v1.7, v1.8, v2.0) liegen separat.

---

*Entwickelt von **[@bagueDev](https://github.com/bagueDev)**: DJ, Producer, Entwickler. Gemacht für Creator.*
*Licensed under [GPLv3](LICENSE). Siehe auch [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).*