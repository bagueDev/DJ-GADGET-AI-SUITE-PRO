# Third-Party Licenses

DJ Gadget AI-Suite Pro is licensed under the **GNU GPL v3.0** (see `LICENSE`).
It uses the following third-party components, which keep their own licenses.
No AI model weights are shipped with the app; models you download are subject to their own terms.

> **TODO before release:** verify this list against the real dependency list of the build
> (`pip freeze` / `requirements.txt`, bundled binaries) and check each license text.
> Entries marked "(verify)" are from general knowledge and must be confirmed.

| Component | Purpose | License |
|---|---|---|
| [Demucs](https://github.com/facebookresearch/demucs) 4.1.0 | Stem separation | MIT (verify) |
| MLX / demucs-mlx backend | Fast stems on Apple Silicon | MIT (verify exact package) |
| [PyTorch](https://pytorch.org) | Torch backend (Intel / fallback) | BSD-3-Clause (verify) |
| [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) | Transcription | MIT (verify) |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) (`llama-server`, web UI) | Local LLM chat | MIT (verify) |
| [Mutagen](https://github.com/quodlibet/mutagen) (if used) | Audio tagging | GPL-2.0-or-later (verify; compatible with GPLv3) |
| *Audio / GUI / beat-detection libraries* | *Fill in: e.g. Qt/PySide, librosa, ffmpeg* | *Fill in. Note: Qt/PySide and ffmpeg builds can be LGPL/GPL, check linking and build flags* |

## Model weights (not shipped)

Weights for Demucs, Whisper and your GGUF chat models are downloaded by the user
and are governed by their respective licenses (some have non-commercial or
usage-restricted terms). Check the license on each model's download page.

Full license texts of the components above must be included in the distributed app
(e.g. in the About window / `licenses/` folder).
