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
