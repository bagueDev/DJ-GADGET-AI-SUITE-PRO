# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import sys, os, datetime, multiprocessing
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
# Erst danach:

try:
    from faster_whisper import WhisperModel, download_model
except ImportError:
    print("ERROR: faster-whisper not installed."); sys.exit(1)

def format_timestamp(seconds):
    td = datetime.timedelta(seconds=seconds)
    return f"[{int(td.total_seconds()//60):02d}:{int(td.total_seconds()%60):02d}.{int(td.microseconds/10000):02d}]"

def run_transcription(file_path, output_dir, model_name, offline_dir=None):
    try:
        print(f"SYSTEM: 🔄Load Model '{model_name}'..."); sys.stdout.flush()
        model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=offline_dir)
        
        print(f"SYSTEM: 🚀Start Transcription..."); sys.stdout.flush()
        segments, _ = model.transcribe(
            file_path, 
            beam_size=5, 
            word_timestamps=True, 
            vad_filter=False, 
            condition_on_previous_text=True
        )
        
        base = os.path.splitext(os.path.basename(file_path))[0]
        with open(os.path.join(output_dir, f"{base}_lyrics.txt"), "w", encoding="utf-8") as f_t, \
             open(os.path.join(output_dir, f"{base}.lrc"), "w", encoding="utf-8") as f_l:
            f_l.write(f"[ti:{base}]\n")
            for s in segments:
                print(f"[{s.start:.1f}s] {s.text.strip()}"); sys.stdout.flush()
                f_t.write(f"{s.text.strip()}\n")
                f_l.write(f"{format_timestamp(s.start)}{s.text.strip()}\n")
        print("✅TRANS_DONE -> Auto-Generated .txt,.lrc,.srt")
    except Exception as e: print(f"❌CRITICAL ERROR: {e}")

def download_offline_model(model_name, output_dir):
    try:
        download_model(model_name, output_dir=output_dir)
        print("✅DOWNLOAD_DONE")
    except Exception as e: print(f"❌DOWNLOAD_ERROR: {e}")

def main_worker():
    args = sys.argv[1:]
    if "--worker" in args:
        args = args[args.index("transcriber")+1:]
    if not args: return

    if args[0] == "--download":
        download_offline_model(args[1], args[2])
    elif len(args) >= 3:
        off = args[3] if len(args) > 3 and args[3] != "NONE" else None
        run_transcription(args[0], args[1], args[2], off)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main_worker()