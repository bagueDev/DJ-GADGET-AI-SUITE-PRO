<div align="center">

# 🎧 DJ Gadget AI-Suite Pro

### Dein Player ist ein Sampler. Hören. Loopen. Zerlegen. Nachfragen.

**Die kostenlose, quelloffene KI-Workstation für DJs, Producer und Musik-Creator, die auf deinem eigenen Rechner läuft.**
Bibliothek, Sampler, Stem-Trennung, Transkription, Melodie- & MIDI-Generator und ein auf Musik getunter lokaler LLM-Chat in einer App.

![Platform](https://img.shields.io/badge/macOS-12%2B-000000?style=for-the-badge&logo=apple)
![Apple Silicon](https://img.shields.io/badge/Apple%20Silicon-MLX%20%2B%20Metal-blue?style=for-the-badge)
![Intel](https://img.shields.io/badge/Intel-aus%20Quellcode-lightgrey?style=for-the-badge)
![Version](https://img.shields.io/badge/Version-3.3.1-orange?style=for-the-badge)
![License](https://img.shields.io/badge/Lizenz-GPLv3-blue?style=for-the-badge)
![Local](https://img.shields.io/badge/läuft-100%25%20lokal-success?style=for-the-badge&logo=shield)

[English version](README.md)

<a href="https://youtube.com/shorts/aAOCQz_gQw0"><img src="https://img.youtube.com/vi/aAOCQz_gQw0/maxresdefault.jpg" alt="DJ Gadget AI-Suite Pro – Promo-Video auf YouTube" width="560"></a>

▶️ **[Promo-Video auf YouTube ansehen](https://youtube.com/shorts/aAOCQz_gQw0)**

</div>

![DJ Gadget AI-Suite Pro – Player & Sampler](docs/screenshots/player-sampler.png)

<!-- TODO: kurzes GIF einfügen: Loop setzen, während die Playlist läuft → Save Loop → WAV liegt im Ordner -->

---

## ✨ Der Workflow

Du hörst deine Playlist und plötzlich passiert *dieser* Moment. Was jetzt?

1. **Hören → schneiden.** Loop setzen, während der Track weiterläuft, einmal klicken, und ein sauberes, am Grid ausgerichtetes WAV ist gespeichert. Kein Umweg über die DAW.
2. **Zerlegen.** Rechtsklick auf den Track und direkt an Stems AI senden: Vocals, Drums, Bass, Instrumentals, auch als Batch.
3. **Nachfragen.** Du hängst fest? Frag den eingebauten, auf Musik getunten LLM-Chat.
4. **Weitergehen.** Echter Webzugriff nötig? Verbinde einen MCP-Server mit dem llama.cpp-Chat (optional).
5. **Zu MIDI machen.** Erzeuge Melodien, Akkorde und Drums im Melody Lab oder wandle ein Sample in MIDI um. Transkribiere Songtexte aus einem Song oder Video.

Alles bleibt in einer App. Tracks wandern per Rechtsklick zwischen den Tabs.

## 🎛️ Der Sampler (im Player eingebaut)

Früher: Track in die DAW laden, schneiden, Downbeat suchen, aufs Grid ziehen, Fades setzen, bouncen.
Jetzt: Loop setzen, *Save Loop* klicken, fertig.

- **IN / OUT**-Punkte, während der Track weiterläuft (Tasten `I` / `O`)
- **🧲 Snap to Beat**: magnetisches Taktgitter, Loops landen auf dem Takt
- **✂️ Auto-Trim**: etwas schief geloopt? Die Loop-Punkte werden aufs Grid angepasst
- **Smart Loops**: Loops bis 32 Takte ab der aktuellen Position
- **🔁 Preview** und **➡️ Exit Loop** (phasenrein, ohne Sprung)
- **💾 Save Loop als WAV** mit **✨ Polish**: Normalisierung + Micro-Fades (keine Klicks)

## 🧰 Die Tabs

### 🔍 Playlist & BPM Analyzer
Ordner oder einzelne Dateien scannen und **BPM, Tonart (Camelot) und Länge** erhalten. Nach BPM-Bereich, Key oder Name sortieren und filtern. Mit einem BPM-Bereich (z. B. 160–190 für DnB) vermeidest du Halftime-Fehler. Trotzdem falsch? Rechtsklick → **BPM (2x)** oder **BPM (/2)**.

> ⚠️ **Aktiviere *Auto-Tag* vor dem Scan**, wenn BPM und Key in deine Dateien geschrieben werden sollen. Es werden nur diese beiden Felder angefasst, Artist, Titel, Album und Cover bleiben erhalten.

![Rechtsklick-Menü](docs/screenshots/context-menu.png)

Das Rechtsklick-Menü bietet außerdem **Details, Show in Finder, Rescan, Meta Editor, Stems AI und Transcribe**, damit Tracks ohne Neuladen zwischen den Tabs wandern.

### ✏️ Metadata Editor
Artist, Titel, Album, Tracknummer, BPM, Key und Camelot bearbeiten. Cover tauschen (auch bei WAV/AIFF), Rohdaten (Bitrate, ISRC, Encoder) über *Meta Details* ansehen, dann **Save**. Tags werden als ID3v2.3 geschrieben.

![Metadata Editor](docs/screenshots/metadata.png)

### ✂️ Stems AI
Demucs 4.1.0 mit MLX-Backend auf Apple Silicon. Vier Stems (Vocals, Drums, Bass, Other) oder **sechs Stems mit Piano und Gitarre** (`htdemucs_6s`). Mit **Instrumental-Modus**, Batch-Queue und Stem-Auswahl.

![Stems AI](docs/screenshots/stems.png)

### 🎹 Melody Lab
Erzeugt **Melodien, Drums und Akkorde** als MIDI.

- 13 Genres, 19 Skalen, Key, BPM, Takte, Taktart, Oktavlage, Density, Swing, **Humanize**, Complexity
- ~40 Akkordfolgen-Presets (z. B. *Liquid DnB: 6-4-1-5*) und Arrangement-Presets (z. B. *DnB Journey*)
- **Full Loop** rendert alle Spuren auf einmal, **MIDI**-Export für jede DAW
- **Audio → MIDI**-Converter: Sample laden, Melodie oder Drums als MIDI erhalten

Die Generierung basiert auf Mustern und Musiktheorie (kein Cloud-Modell), läuft also sofort und offline.

![Melody Lab](docs/screenshots/melody-lab.png)

### 📝 Transcriber
Faster-Whisper, offline. Ausgabe als `.txt` und **`.lrc`** mit Zeitstempeln. Batch-Queue. Tipp: vorher die Vocals mit Stems AI isolieren.

![Transcriber](docs/screenshots/transcriber.png)

### 🤖 AI Chat
Beliebige GGUF-Modelle über llama.cpp (Metal-beschleunigt) mit einem Systemprompt für Musik, Verlauf, HTML-Export und der **nativen llama.cpp-Weboberfläche** im Browser.

**Optionaler Webzugriff per MCP:** Setze im Chat-Tab den Haken bei **🔌 MCP proxy (Web UI)**, bevor du 🚀 Start drückst (standardmäßig aus). Trage dann die URL deines eigenen MCP-Servers ein oder nutze **V.I.N.C.E.N.T.** (unser Open-Source-MCP-Server, [github.com/bagueDev](https://github.com/bagueDev)). Verbinde nur Server, denen du vertraust, denn sie geben dem Modell Werkzeuge in die Hand.

**OpenAI-kompatible API:** Wenn die Chat-Engine läuft, bietet DJ Gadget einen lokalen OpenAI-kompatiblen Endpunkt unter `http://127.0.0.1:8080/v1`. Jedes OpenAI-kompatible Tool (Aider, Continue, Cursor, Windsurf, eigene Skripte) kann ihn als Backend nutzen — einfach die Base-URL setzen. Kein separater Server nötig.

![AI Chat](docs/screenshots/ai-chat.png)

### 📝 Log
Fortschritt und Fehlermeldungen aller Worker. Der erste Blick bei Problemen.

### Export
Playlists als **Rekordbox XML**, **M3U** (Traktor / Serato / VLC) oder **JSON**.

## 🔒 Privatsphäre

- Kein Account, kein Abo, keine Telemetrie, kein Upload deiner Audiodaten.
- **Standardmäßig lokal:** Demucs (Stems), Faster-Whisper (Lyrics) und llama.cpp (Chat) laufen auf deinem Rechner.
- Modelle lädst du einmalig mit den *Offline Load*-Buttons. Danach läuft alles auch ohne WLAN (Club-Modus).
- Webzugriff gibt es nur, wenn **du** einen MCP-Server mit dem Chat verbindest.

## 💻 Voraussetzungen

- **macOS 12 (Monterey)** oder neuer
- **Apple Silicon (M1–M4):** MLX-Backend für Stems, Metal für den Chat
- **Intel-Macs:** aus dem Quellcode startbar (CPU/Torch-Pfad, Stems brauchen länger). Der Download ist vorerst nur für Apple Silicon; ein Intel-Build ist geplant.
- **RAM:** mindestens 8 GB, empfohlen 16 GB+
- **Speicher:** ca. 750 MB App (rund 320 MB Download), dazu die KI-Modelle, die du lädst
- Windows & Linux: geplant, noch nicht verfügbar

## 🚀 Installation

1. Neuesten Build unter **[Releases](../../releases)** herunterladen. Die DMG ist für Macs mit **Apple Silicon** (M1 oder neuer); auf Intel-Macs startet sie nicht.
2. App neben den Modell-Ordnern ablegen (fehlende Ordner werden automatisch erstellt):
   ```
   DJ Gadget AI-Suite Pro.app
   AI_Models/        ← deine .gguf Chat-Modelle
   Offline_Models/   ← Demucs-Modelle
   Whisper_Models/   ← Transkriptions-Modelle
   Chat_History/     ← gespeicherte Chats
   ```
3. Erster Start: macOS blockiert die App, weil sie nicht von Apple beglaubigt ist. Einmal versuchen zu öffnen, dann unter **Systemeinstellungen → Datenschutz & Sicherheit** auf **Dennoch öffnen** klicken (nur einmal nötig). Auf älteren macOS-Versionen geht auch **Rechtsklick → Öffnen**. Der Start kann 10–20 s dauern, weil die Engines geprüft werden.

Es sind keine KI-Modelle enthalten. Die App ist portabel und läuft auch vom USB-Stick.

## 📖 Dokumentation

- Benutzerhandbuch: [`BENUTZERHANDBUCH.md`](BENUTZERHANDBUCH.md) (als Word-Datei in [`docs/`](docs/))
- Tastenkürzel: **F1** oder der **?**-Button in der App, oder [`SHORTCUTS.md`](SHORTCUTS.md)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)

## ⚖️ Verantwortungsvoll samplen

Sampling ist ein kreatives Werkzeug. Nutze es für eigene Musik, lizenziertes Material oder Material, an dem du die Rechte hast. Für den Umgang mit exportierten Samples bist du selbst verantwortlich.

## 🤝 Mitmachen & Support

Issues und Pull Requests sind willkommen. Bug gefunden? Eröffne ein Issue und hänge die Ausgabe des **Log**-Tabs an.

## 📜 Lizenz

Veröffentlicht unter der **GNU General Public License v3.0**, siehe [`LICENSE`](LICENSE). Du darfst den Code nutzen, untersuchen, ändern und weitergeben, abgeleitete Werke müssen aber unter derselben Lizenz offen bleiben.
Drittkomponenten (Demucs, Faster-Whisper, llama.cpp, MLX u. a.) behalten ihre eigenen Lizenzen, siehe [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). Heruntergeladene Modelle unterliegen ihren eigenen Bedingungen.

---

<div align="center">

Entwickelt von **[@bagueDev](https://github.com/bagueDev)**: DJ, Producer, Entwickler. Gemacht für Creator.

</div>
