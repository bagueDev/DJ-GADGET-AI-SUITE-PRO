# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import numpy # WICHTIG: Zuerst!
import sys, os, platform, multiprocessing, certifi, ssl
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
# Erst danach:

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Modelle, die demucs-mlx (fp32, mlx-community) liefern kann.
SUPPORTED_MLX_MODELS = {
    "htdemucs", "htdemucs_ft", "htdemucs_6s",
    "hdemucs_mmi", "mdx", "mdx_extra", "mdx_q", "mdx_extra_q",
}
VALID_OTHER_METHODS = {"add", "minus", "none"}
SAMPLE_RATE = 44100


def get_device_strategy():
    return "mps" if platform.machine() == 'arm64' else "cpu"


def mlx_available():
    try:
        import demucs_mlx  # noqa: F401
        import mlx.core  # noqa: F401
        return True
    except Exception:
        return False


def resolve_backend(requested="auto", model="htdemucs"):
    """Auto: ARM + MLX importierbar + Modell unterstützt -> mlx, sonst torch."""
    requested = (requested or "auto").lower()
    if requested in ("mlx", "torch"):
        if requested == "mlx" and (not mlx_available() or model not in SUPPORTED_MLX_MODELS):
            print(f"--- Backend mlx nicht verfügbar für {model}, Fallback torch ---")
            return "torch"
        return requested
    # auto
    if platform.machine() == 'arm64' and mlx_available() and model in SUPPORTED_MLX_MODELS:
        return "mlx"
    return "torch"


def _track_dir(output_dir, model, file_path):
    base = os.path.splitext(os.path.basename(file_path))[0]
    d = os.path.join(output_dir, model, base)
    os.makedirs(d, exist_ok=True)
    return d


def _filter_keep_stems(track_dir, keep_stems):
    """Löscht nicht gewählte Stems (keep_stems='all' oder Kommaliste)."""
    if not keep_stems or keep_stems == "all":
        return
    keep = {s.strip() for s in keep_stems.split(",") if s.strip()}
    keep.add("vocals")  # vocals immer behalten (two_stems-Logik braucht sie)
    for f in os.listdir(track_dir):
        if f.endswith(".wav") and os.path.splitext(f)[0] not in keep and f != "no_vocals.wav":
            try:
                os.remove(os.path.join(track_dir, f))
            except OSError:
                pass


def run_torch_separation(file_path, output_dir, model="htdemucs", keep_stems="all",
                         offline_dir=None, two_stems=False, other_method="add"):
    import demucs.separate
    if offline_dir:
        os.environ["TORCH_HOME"] = offline_dir
        os.environ["XDG_CACHE_HOME"] = offline_dir

    args = ["-n", model, "-d", get_device_strategy(), "--jobs", "0",
            "-o", output_dir, file_path]
    if two_stems:
        args.extend(["--two-stems", "vocals"])
        if other_method in VALID_OTHER_METHODS:
            args.extend(["--other-method", other_method])

    demucs.separate.main(args)

    if not two_stems:
        _filter_keep_stems(_track_dir(output_dir, model, file_path), keep_stems)


def run_mlx_separation(file_path, output_dir, model="htdemucs", keep_stems="all",
                       offline_dir=None, two_stems=False, other_method="add"):
    import numpy as np
    import soundfile as sf
    from demucs_mlx import Separator

    repo = None
    if offline_dir:
        cand = os.path.join(offline_dir, "demucs-mlx")
        if os.path.isdir(cand):
            repo = cand

    print(f"--- MLX Separation: {model} (fp32) ---")
    sep = Separator(model=model, repo=repo)
    origin, stems = sep.separate_audio_file(file_path)

    track_dir = _track_dir(output_dir, model, file_path)

    def to_stereo(a):
        arr = np.asarray(a, dtype=np.float32)
        if arr.ndim == 1:
            arr = np.stack([arr, arr], axis=-1)
        elif arr.ndim == 2:
            # (channels, samples) -> (samples, channels)
            if arr.shape[0] <= 2 and arr.shape[1] > arr.shape[0]:
                arr = arr.T
        else:  # (batch?, ...) defensiv auf 2D bringen
            arr = arr.reshape(arr.shape[-2], arr.shape[-1])
            if arr.shape[0] <= 2 and arr.shape[1] > arr.shape[0]:
                arr = arr.T
        if arr.shape[1] == 1:
            arr = np.repeat(arr, 2, axis=1)
        return np.clip(arr, -1.0, 1.0)

    if two_stems:
        vocals = to_stereo(stems["vocals"])
        sf.write(os.path.join(track_dir, "vocals.wav"), vocals, SAMPLE_RATE)
        if other_method != "none":
            if other_method == "minus":
                try:
                    orig = to_stereo(origin)
                    n = min(len(orig), len(vocals))
                    no_voc = orig[:n] - vocals[:n]
                except Exception:
                    no_voc = sum(
                        to_stereo(v) for k, v in stems.items() if k != "vocals"
                    )
            else:  # add
                no_voc = sum(
                    to_stereo(v) for k, v in stems.items() if k != "vocals"
                )
            sf.write(os.path.join(track_dir, "no_vocals.wav"),
                     np.clip(no_voc, -1.0, 1.0), SAMPLE_RATE)
    else:
        for name, data in stems.items():
            sf.write(os.path.join(track_dir, f"{name}.wav"),
                     to_stereo(data), SAMPLE_RATE)
        _filter_keep_stems(track_dir, keep_stems)


def run_separation(file_path, output_dir, model="htdemucs", keep_stems="all",
                   offline_dir=None, two_stems=False, backend="auto",
                   other_method="add"):
    try:
        print(f"--- Separation Start: {os.path.basename(file_path)} ---")
        chosen = resolve_backend(backend, model)
        print(f"--- Backend: {chosen} | Modell: {model} | other_method: {other_method} ---")
        if chosen == "mlx":
            try:
                run_mlx_separation(file_path, output_dir, model, keep_stems,
                                   offline_dir, two_stems, other_method)
            except Exception as e:
                print(f"!!! MLX fehlgeschlagen ({e}), Fallback torch !!!")
                run_torch_separation(file_path, output_dir, model, keep_stems,
                                     offline_dir, two_stems, other_method)
        else:
            run_torch_separation(file_path, output_dir, model, keep_stems,
                                 offline_dir, two_stems, other_method)

        # Cleanup Logik (gekürzt)
        print("✅ SEP_DONE")
    except Exception as e: print(f"CRITICAL ERROR: {e}")


def main_worker():
    args = sys.argv[1:]
    if "--worker" in args:
        args = args[args.index("separator")+1:]

    if len(args) >= 4:
        off = args[4] if len(args) > 4 and args[4] != "NONE" else None
        two = True if len(args) > 5 and args[5] == "True" else False
        backend = args[6] if len(args) > 6 and args[6] not in ("NONE", "") else "auto"
        other_method = args[7] if len(args) > 7 and args[7] in VALID_OTHER_METHODS else "add"
        run_separation(args[0], args[1], args[2], args[3], off, two, backend, other_method)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main_worker()
