# Changelog

All notable changes to **DJ Gadget AI-Suite Pro** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.3.0] - 2026-11-01

### ⚡ Stems – MLX-Backend für Apple Silicon (🎧)
- **Demucs `4.0.1 → 4.1.0`** – inkl. neuem `--other-method` (`add`/`minus`/`none` steuert, wie `no_vocals` gebaut wird: Stems summieren, Original-minus-Stem oder verwerfen).
- **Neuer MLX-Fast-Path (`demucs-mlx`, fp32)** – native Apple-Silicon-Inferenz via Metal, ca. 2–3× schneller als Torch-MPS bei gleichem Output-Layout (`Stems/<Modell>/<Song>/*.wav`).
- **Backend-Auto (`separator.py`)** – ARM + MLX verfügbar → MLX, sonst Torch (Fallback für Intel-Macs/Linux bleibt erhalten, inkl. automatischem Fallback bei MLX-Fehler).
- **Stems-Tab UI** – neues Backend-Dropdown (Auto / MLX / Torch) + `no_*`-Dropdown (`add`/`minus`/`none`); „Offline Load" lädt den MLX-Modell-Cache jetzt wirklich nach `Offline_Models/demucs-mlx` vorab.
- **Schlankes ARM-Bundle** – `app_build_arm_single.sh` packt `demucs_mlx`/`mlx`/`safetensors` ein und schließt `torch`/`torchaudio` aus (~1 GB kleiner).

### 🥁 Drums – mehr Abwechslung, weniger Looping (🎹)
- **Phrasen-Wechsel** – alle 2 Takte werden mit 60 % Chance frische Pattern gewürfelt (statt 8 Takte `ABABABAB`); `pick_pair()` garantiert A≠B.
- **Pools verdoppelt** – HipHop- und Trap-Kick-Pools von 4 auf je 8 Pattern erweitert.
- **Hats & Ghosts** – HipHop (8tel-Hats mit Akzenten + Open-Hat), Trap (dichte Hats + Offbeat-Öffnung), Ghost-Snare (HipHop), Ghost-Clap + offene Hat (House), Offbeat-Hats (Synthpop).
- **Sound-Round-Robin** – jeder Drumsound rotiert durch 3 leicht verstimmte Varianten (0/+35/−40 Cent) gegen den Maschinengewehr-Effekt.
- **Timing-Jitter** – Humanize streut jetzt auch Timing (±5 ms Audio, ±6 Ticks MIDI), nicht nur Velocity.

### 🎹 Melody Lab – Robustheit & UX (🎹)
- **Zentrales Input-Sanitizing** – BPM (20–300) + Bars (1–**128** statt 512, echter RAM-Schutz) in allen Pfaden (Generate, Preview, Full Loop); stürzt nie mehr ab.
- **Gehärtete Worker-Wrapper** – alle `_run_*`-Threads + Converter mit try/except; Status bleibt nie hängen, Fehler landen im Log.
- **Preview-Debounce (400 ms)** – schnelles Durchklicken rendert nur 1× statt 5 Threads.
- **Generations-Counter** – veraltete Ergebnisse werden verworfen (kein Last-Writer-Wins mehr).
- **Full Loop mit Fortschritt + Stop** – `Creating Loop (2/6): 🎹 Chords...` via `progress_cb`-Hook, ⏹ Stop-Button bricht zwischen den Stems ab (Backend-Kwargs abwärtskompatibel).
- **Künstliche Delays (800/1200 ms) entfernt**, Generate-Buttons während Läufen gesperrt, Temp-Ordner werden beim Start aufgeräumt.
- **Progression-Header** im Melody-Pfad abgefangen (→ Random), Toggle-Logik tabellarisch, Genre-Dropdown-Regression gefixt.

### 🐛 Fixed
- About-Fenster zeigte `Version 3.0` – jetzt `3.3` (passend zu Titel + Build); Kontakt-E-Mail aktualisiert.
- Genre-Dropdown im Melody-Tab war nach Refactoring unsichtbar (fehlende `.grid()`-Zeile) – wiederhergestellt.
- Tippfehler „ore folder" → „or folder" im Analyzer-Pfad-Eingabefeld.
- JSON-Export-Fehler `Object of type ndarray is not JSON serializable` behoben (numpy-Typen werden jetzt konvertiert).
- „Que" → „Queue" Tippfehler im Transcriber (2 Stellen).

### ✨ Features
- **Playlist Update-Button** (🔄 UPDATE) – aktualisiert bestehende Playlist-Dateien in place (XML/M3U/JSON) ohne neue Datei zu erstellen.
- **CORS-Hardening** – llama-server nur für localhost-Origins (`--cors-origins`), verhindert Prompt-Injection über bösartige Websites.

### 🔐 Lizenz & Open Source
- **GPLv3** als Projekt-Lizenz: `LICENSE`-Datei (vollständiger GPLv3-Text), `THIRD_PARTY_LICENSES.md` (Lizenzen aller Dependencies).
- **Copyright-Header** in allen `.py`-Dateien (`Copyright (C) 2026 Bascharan Guersoy (@bagueDev)`).
- **Produktkey-System entfernt** (`license_guard.py` gelöscht, Lizenz-Check in `main.py` entfernt).
- About-Fenster: Copyright + „Licensed under GPLv3" + Button „View Full License".
- „All rights reserved" → GPLv3-Hinweis.

### 🔧 Infrastruktur
- **llama-server aktualisiert** auf 0.8.0-dev (build 12032, commit dde879bc4) — ersetzt 9687 (b4024af6c).
- **Config-Datei Override** (`~/.djgadget/chat_server.json`) — eigene llama-server-Binary nutzen ohne Rebuild (Env-Var → Config → bundled → dev).
- **Chat-Tab UI** — neue Zeile „🔧 Server-Binary (optional)" mit Datei-Picker (📂) und Löschen (🗑️).
- **Chat-Tab Regler** — TopP (🎯) und TopK (🔝) Slider hinzugefügt (2-reihiges Layout: Temp/MaxT/Rep + TopP/TopK/Ctx).
- **`.gitignore`** erstellt — venv, build, dist, Modelle, Binaries, Backups ausgeschlossen.
- **Samples umbenannt** mit `bagueDEV_`-Prefix (24 Dateien), `sample_map` aktualisiert.
- **Build-Skript bereinigt** — `--collect-all "llama_cpp"` entfernt (verhindert dylib-Konflikt mit neuer Binary), `license_guard` entfernt.

---

## [3.1.2] - 2026-08-11

### 🥁 DnB/Breakbeat – Amen-Break-Engine (🎹)
- **Neues Genre „DnB/Rolling"** – trennt den bisherigen 2-Step-Stil (Rolling Hats, SampleFocus-Logik) vom neuen Breakbeat-Sound.
- **„DnB/Breakbeat" spielt jetzt echte Amen-Patterns** – neuer `amen_pool` (Classic Amen, Jungle Roller, Techstep) mit den Signature-Merkmalen: „phat" 4 (Kick+Snare zusammen), Ghost-Snares (Velocity 35–55, Dichte-gesteuert), Flam vor der 4 (Schritt 11), 16tel-Hats mit Akzentmuster + Open Hats auf Offbeats.
- **Amen-„Break"-Fill** – im 8-Takt-Fill spielt Breakbeat statt Toms eine Snare-Rat-a-tat-Roll mit Crescendo (echtes Break-Taktende).
- Beide Varianten: 2 Muster pro Klick, wechseln pro Takt; Zwei-Takt-Zyklus beibehalten. Rolling-Logik komplett unverändert.

### ⚠️ Notes
- Build-Ergebnis: `dist/DJ Gadget AI-Suite Pro v3.1.2 @bagueDEV ARM.app` + `.dmg`.

---

## [3.1.1] - 2026-08-11

### 🎛️ Melody Lab – Musiklogik-Härtung (🎹)
- **Synthpop/Trap/HipHop spielten DnB-Beats** – nach der Genre-Auswahl überschrieb eine pauschale Zeile `p_a/p_b` immer mit dem DnB-Pool. Jetzt saubere if/elif-Kette: jedes Genre (Synthpop, Trap, HipHop, DnB) bekommt seine eigenen Kick-Patterns.
- **Power-Chords (2 Noten) + Inversion = Absturz** – `apply_voicing()` griff bei „1st/2nd Inversion" auf `notes[2]` zu (IndexError) → Chords stürzten still ab. Inversion wird bei <3 Noten jetzt übersprungen.
- **Genre „Random" (und „Ambient") hatten fast keine Drums** – fielen nur auf die globalen Fallback-Hats zurück. Neuer `else`-Zweig: solider Basic 4/4 (Kick auf jedem Viertel, Snare auf 2+4).
- **Reggaeton hatte keine Drums** – neuer Dembow-Branch bindet die vorher toten Latin-Patterns `samba_kick` (Kick-Puls) und `bossa_rim` (Rimshots) ein + Offbeat-Hats.
- **Bass ignorierte die Taktart** – `create_bass_files()` rechnete immer mit 16 Steps. Jetzt 12 Steps bei 3/4 & 6/8 (Muster-Positionen werden skaliert), passend zu Drums/Chords.

### ⚠️ Notes
- Build-Ergebnis: `dist/DJ Gadget AI-Suite Pro v3.1.1 @bagueDEV ARM.app` + `.dmg`.

---

## [3.1.0] - 2026-08-11

### 🐛 Melody Lab Fixes (🎹)
- **Chords-Preview repariert** – die Vorschau übergab die Argumente in falscher Reihenfolge und ohne `sound`/`genre`/`human` → Thread stürzte still ab (TypeError). Jetzt mit korrekten 15 Args (inkl. `sound`, `genre`, `time_sig`, `human`).
- **Humanize-Schalter wirkt jetzt wirklich** – Chords-Generierung übergab das Checkbox-**Objekt** statt des Bool-Werts → Humanize lief immer. Jetzt `bool(self.mel_human.get())`.
- **Drums-Ausgabe-Ort korrigiert** – `output_dir`/`time_sig` waren im Drum-Wrapper vertauscht → Dateien landeten im Ordner `"4/4"` statt im Temp-Verzeichnis.
- **Arrangement Structure wirkt jetzt überall** – `get_arrangement_energy()` (Intro/Verse/Chorus/Drop-Logik) wurde nur beim Full Loop durchgereicht; jetzt auch bei Melody/Chords/Drums Einzelgenerierung **und** Preview.
- **Genre „Random"** hat jetzt ein Profil in `GENRE_PROFILES` (setzt Defaults statt stille No-op).

### 🧠 Chat-Tab (🧠)
- **`🤖 Tools`-Dropdown entfernt** – die eingebauten llama-server-Agent-Tools (inkl. `exec_shell_command`) werden nicht mehr angeboten; Tools laufen ausschließlich über **MCP** (`--ui-mcp-proxy` + WebUI). `--tools`-Flag und Parameter-Kette (UI → Worker → Server) komplett entfernt.
- **Stabiler WebUI-Port 8080** – llama-server startet jetzt auf einem festen Port (`FIXED_PORT = 8080`, Fallback auf freien Port falls belegt). Dadurch bleibt die Browser-Origin stabil: **MCP-Server-Konfiguration (LocalStorage) und Chatverläufe (IndexedDB) der WebUI überleben App-Neustarts**. (Hinweis: MCP-Server einmalig unter `127.0.0.1:8080` neu eintragen.)

### ⚠️ Notes
- Chat engine (llama-server GPU/Metal) ansonsten unverändert.
- Alte Ordnerkopien (`gadget arm/`, `Archiv_basis_golden/`) bleiben unberührt – nur Root-Dateien werden gebaut.

---

## [3.0.0] - 2026-08-10

### ⭐ Highlights
- **🎹 Melody Lab complete overhaul** – full 6-track loop generation engine
- **⌨️ Shortcut Cheat-Sheet** – new built-in help window with all keyboard commands
- **🔊 Global Volume Control** – master mute + volume slider in the header
- **✏️ Metadata Editor upgrade** – track number support, scrollbar, Send-to-Analyzer, Show-in-Finder
- **🔐 Product Activation** – license key check on first launch

### ✨ Melody Lab (🎹)
- Integrated the advanced `melody_generator` engine:
  - **19 scales** (Major, Minor, Pentatonic, Blues, Phrygian, ...)
  - **45+ chord progressions** across 6 categories
  - **10 genre profiles** with smart BPM/parameter defaults
  - **Hybrid drum sounds** – 12 real percussion samples with synthesized fallbacks
  - **3 generator modes**: Melody, Chords, Drums (+ dedicated preview)
  - **🎼 Full Loop**: 6-track stereo loop (Melody + Chords + Drums + Bass + Pads/Keys + Arp) with **MIDI merge** via `mido`
  - **Voicing styles**, bass complexity, arrangement modes, humanize & swing controls
  - **Audio → MIDI converter** with sensitivity / smoothing / duration options
- Added `samples/` folder (drum one-shots) bundled into the app.
- Fixed a converter crash where the duration dropdown widget was never created (`midi_conv_len`).

### ✏️ Metadata Editor (✏️)
- **Track number field** – edit/save `tracknumber` (`TRCK`/`tracknumber`/`trkn` tags) for MP3, FLAC, M4A, WAV, AIFF
- **File list scrollbar** (clean container with `CTkScrollbar`)
- Context menu: **"🔍 Send to Analyzer"** – push selected files straight into Playlist & BPM analysis
- Context menu: **"📂 Show in Finder"** – reveal the file in Finder/Explorer
- **Better cover cropping** via `ImageOps.fit` (exact 200×200, no ratio offset)
- UI polish: "🔄 Sync Playlist" label, larger placeholder

### 🔍 Playlist & BPM (🔍)
- **`load_external_files()`** – receive files from the Metadata Editor (log entry, loading animation, batch analysis)
- **Numeric table sorting** – BPM and # columns now sort numerically (`9 → 10 → 100`) instead of as strings; the internal track list is hard-synced so the order survives tab switches
- Context menu: **"📂 Show in Finder"** – reveal the selected file in Finder/Explorer
- **Single-instance details window** – "📄 Details" lifts the already-open window instead of opening duplicates; it auto-refreshes when a new track starts playing

### 🛠️ Under the Hood
- **`analyzer.py`**: `write_metadata()` accepts a new `track` argument with per-format tag support; `--tag` worker reads the 10th argument (backwards compatible).
- **`helpers.py`**: new `ShortcutOverviewWindow` (shortcut cheat-sheet) and `reveal_in_finder()`.

### ✂️ Stems AI (✂️)
- Context menu: **"🔍 Send to Analyzer"** – push selected files straight into Playlist & BPM analysis
- Context menu: **"📂 Show in Finder"** – reveal the file in Finder/Explorer
- File list **scrollbar** (cleaner list navigation)

### 🎙️ Vocal Transcriber (🎙️)
- **Auto-SRT**: after every transcription a `.srt` subtitle file is automatically generated from the fresh `.lrc` (Karaoke) in the source folder
- Context menu: **"🔍 Send to Analyzer"** + **"📂 Show in Finder"**
- Console context menu: **"📋 Copy"** (selection or all) / **"🗑️ Clear Log"**
- File list **scrollbar**
- **Video support**: file dialog now accepts `.mp4`, `.mov`, `.mkv` (besides audio)
- Status hint now mentions `.srt` export + auto-reset to default text after batch
- **`transcriber.py`**: transcription uses `word_timestamps=True`, `vad_filter=False`, `condition_on_previous_text=True` for more precise timings

### ⌨️ Shortcuts & UI (⌨️)
- Chat-Tab: **"🌐 Web UI"** button (enabled once the model is loaded) opens the native llama.cpp web interface in your browser at the live server port
- Chat-Tab: **"🤖 Tools"** dropdown enables llama-server built-in agent tools (`all`, or `read_file`, `write_file`, `edit_file`, `grep_search`, …) — passed to the server via `--tools`
- Chat-Tab: **MCP proxy** is now enabled on the llama-server (`--ui-mcp-proxy 1`) so the WebUI can reach MCP servers
- Chat-Tab: **Max-Token slider** reworked — 512-token steps up to 32768, default **4096**, 20 % narrower
- **`F1`** – open Shortcut Cheat-Sheet, **`F2`** / `ℹ️` – About window
- **`Cmd + 9` / `Cmd + 0`** – volume down / up in **every** tab
- **Melody Lab**: `Space` = play/pause, `Return` = generate, `+` = full loop, `Cmd + S` = save MIDI
- **Playlist**: `0`/`9` volume, `M` = track details
- **Improved About window**: single-instance guard, `Cmd+W` handling, resizable

### 🐛 Fixed
- Melody Lab shortcuts referenced non-existent methods (`play_generated_melody` / `generate_melody`) – now correctly wired to `play()` / `generate()`.

### ⚠️ Notes
- **`license_guard.py`** added: the app asks for a product key on first launch. Workers (analysis/separation/transcription/chat) are **not** blocked by the activation check.
- Chat engine (llama-server GPU/Metal) untouched in this release.

---

## [2.5.0] - 2026-06-17

### ✨ Initial ARM/Metal release
- App fully rebuilt as a single binary for **Apple Silicon (ARM)**.
- **Chat engine on GPU (Metal)** via native `llama-server` subprocess (replaces unstable in-process `llama-cpp-python`).
  - Flash attention enabled, Metal offload `-ngl 99`.
- Workers (analyzer / separator / transcriber / chatbot) run as separate subprocesses from one bundle.

---

[3.3.0]: https://github.com/baguedev/DJ-GADGET-AI-SUITE-PRO/releases/tag/v3.3.0
[3.1.0]: https://github.com/baguedev/DJ-GADGET-AI-SUITE-PRO/releases/tag/v3.1.0
[3.0.0]: https://github.com/baguedev/DJ-GADGET-AI-SUITE-PRO/releases/tag/v3.0.0
[2.5.0]: https://github.com/baguedev/DJ-GADGET-AI-SUITE-PRO/releases/tag/v2.5.0