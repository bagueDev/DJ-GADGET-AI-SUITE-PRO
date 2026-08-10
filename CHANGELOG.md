# Changelog - DJ Gadget AI-Suite Pro

### ✨ macOS ARM -Edition 2026-08-12
- **Port Status 
  - v2.5 Done
  - V3.0 in progress!

## [Unreleased] - 2026-05-04

### ✨ Status Update
- **Final Test
  - Cleanup
  - Documentation 
  - Beta1 -Status
  - Tutorials / Video's on youtube.com/@bagueDev comming 
  - [Unreleased] - 2026-08-05
  - 

## [Unreleased] - 2026-05-04

### 🔄 Major Update: llama.cpp Upgrade (b7209 → b9022)
- **Upgrade von llama.cpp** von Tag `b7209` (Nov 2025) auf `b9022` (Mai 2026)
- **1813+ neue Commits** integriert
- **GGML Version:** 0.9.4 → 0.10.2
- **llama-cpp-python:** 0.3.16 → 0.3.22

### ✨ New Features
- **Gemma 4 Support** (ab Tag b8665)
  - Gemma 4 MoE Modelle werden jetzt unterstützt
  - Tensor-parallel Fixes für Gemma-4 MoE (#22129)
  - NVFP4 Tensor Support für Gemma 4 (#21971)
  - Spezialisierter Chat-Parser für Gemma 4 (#21418)
  - Gemma 4 Audio Support (mtmd) (#21824)
  - Gemma 4 Vision + Audio Tests (#21806)

### 🛠️ Improvements
- **Metal Backend** verbessert für macOS
- **BLAS Backend** (Accelerate.framework) weiter optimiert
- **Build-System:** CMake-Konfiguration modernisiert
- **Python Bindings:** llama-cpp-python 0.3.22 mit verbesserten Features

### 🐛 Bug Fixes
- Fix: Gemma 4 shared-KV tail attn_k tensors optional on load (#21739)
- Fix: Reasoning budget sampler bei Gemma 4 (#21870)
- Fix: Gemma 4 Chat-Template Edge Cases (#21760, #22420)
- Clip: Fix nb calculation for qwen3-vl (#17594) - schon in b7209 enthalten

### ⚙️ Dependencies
| Paket | Alt | Neu |
|-------|-----|-----|
| llama.cpp | b7209 (7f8ef50cc) | b9022 (d8794eecd) |
| GGML | 0.9.4 | 0.10.2 |
| llama-cpp-python | 0.3.16 | 0.3.22 |
| torch | 2.2.2 | 2.2.2 (unverändert) |
| numpy | 1.26.4 | 1.26.4 (unverändert) |
| faster-whisper | 1.2.1 | 1.2.1 (unverändert) |
| demucs | 4.0.1 | 4.0.1 (unverändert) |

### 🔐 Security
- Build-Prozess (`security_build.sh`) bleibt kompatibel
- Keine Änderungen an den Python-Importen (`from llama_cpp import Llama`)
- Bestehende Build-Pfade und PyInstaller-Konfiguration funktional

---

## [3.1] - 2026-xx-xx

### Features
- Initial Release von DJ Gadget AI-Suite Pro v3.1
- Integration: Whisper (Speech-to-Text), Demucs (Audio Source Separation)
- llama.cpp Integration für lokale LLM-Inferenz
- CustomTkinter GUI

---

## Format
Dieses Changelog folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
