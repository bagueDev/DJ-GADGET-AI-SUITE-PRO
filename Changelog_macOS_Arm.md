# Changelog

All notable changes to **DJ Gadget AI-Suite Pro** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - Oktober 2026

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
- About-Fenster zeigte `Version 3.0` – jetzt `3.1.2` (passend zu Titel + Build); Kontakt-E-Mail aktualisiert.
- Genre-Dropdown im Melody-Tab war nach Refactoring unsichtbar (fehlende `.grid()`-Zeile) – wiederhergestellt.



## [2.5.0] - 2026-08-12

### ✨ Initial ARM/Metal release
- App fully rebuilt as a single binary for **Apple Silicon (ARM)**.
- **Chat engine on GPU (Metal)** via native `llama-server` subprocess (replaces unstable in-process `llama-cpp-python`).
  - Flash attention enabled, Metal offload `-ngl 99`.
- Workers (analyzer / separator / transcriber / chatbot) run as separate subprocesses from one bundle.

---

### ✨ macOS ARM -Edition 2026-08-08
- **Port Status 
  - v2.5 Done
  - V3.0 in progress!
---
[2.5.0]: https://github.com/baguedev/DJ-GADGET-AI-SUITE-PRO/releases/tag/v2.5.0
