# Third-Party Licenses

DJ Gadget AI-Suite Pro uses the following open-source libraries. Their licenses are listed below.

## Core Framework
- **Python** — PSF License — https://www.python.org/
- **CustomTkinter** — MIT License — Tom Schimansky — https://github.com/TomSchimansky/CustomTkinter
- **Tkinter** — PSF License
- **Pillow** — HPND License — https://python-pillow.org/

## Audio & Music
- **librosa** — ISC License — https://librosa.org/
- **soundfile** — BSD License — https://github.com/bastibe/python-soundfile
- **pygame** — LGPL License — https://www.pygame.org/
- **mutagen** — GPLv2 License — https://mutagen.readthedocs.io/
- **MIDIUtil** — MIT License — https://github.com/MarkCWirt/MIDIUtil
- **audioread** — MIT License
- **pydub** — MIT License
- **soxr** — LGPL License

## AI / Machine Learning
- **Demucs** — MIT License — Meta Research — https://github.com/facebookresearch/demucs
- **demucs-mlx** — MIT License — https://github.com/ssmall256/demucs-mlx
- **Faster-Whisper** — MIT License — Guillaume Klein — https://github.com/SYSTRAN/faster-whisper
- **CTranslate2** — MIT License — https://github.com/OpenNMT/CTranslate2
- **llama.cpp** — MIT License — https://github.com/ggml-org/llama.cpp
- **MLX** — MIT License — Apple — https://github.com/ml-explore/mlx
- **PyTorch** — BSD-Style License — https://pytorch.org/
- **torchaudio** — BSD License
- **NumPy** — BSD License — https://numpy.org/
- **SciPy** — BSD License — https://scipy.org/
- **scikit-learn** — BSD License
- **Numba** — BSD License

## Data & Utilities
- **pandas** — BSD 3-Clause License — https://pandas.pydata.org/
- **matplotlib** — PSF-based License
- **networkx** — BSD License
- **PyYAML** — MIT License
- **requests / urllib3 / httpx** — Apache 2.0 / MIT
- **huggingface_hub** — Apache 2.0

## Build & Packaging
- **PyInstaller** — GPLv2 (with exception) — https://pyinstaller.org/

## Legal Notice
This software uses **Mutagen**, which is licensed under the GNU General Public License (GPLv2). Mutagen has been used without modification.

This software does not include any AI model weights. It functions solely as a client for loading and running external GGUF models and other models such as Demucs or Whisper. All used models are subject to their respective licenses (e.g., MIT, CC-BY-NC, Llama Community License, or others). Please review the license of each model before using it for commercial purposes.

## License of this Software
DJ Gadget AI-Suite Pro is licensed under the **GNU General Public License v3.0** (GPLv3). See [LICENSE](../LICENSE) for the full text.
EOF
echo "THIRD_PARTY_LICENSES.md created"