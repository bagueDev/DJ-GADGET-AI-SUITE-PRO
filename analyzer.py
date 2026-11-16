# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import os
import sys
import pandas as pd
import numpy as np
import librosa
import warnings
import mutagen
from mutagen.id3 import ID3, TKEY, TBPM, APIC, TIT2, TPE1, TALB, ID3NoHeaderError
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm
from mutagen.wave import WAVE
from mutagen.aiff import AIFF 
import multiprocessing
from pathlib import Path

# Warnungen aus
warnings.filterwarnings("ignore")
# WICHTIG: Begrenzt Numba auf einen Thread, um Segfaults auf dem Mac zu vermeiden
#os.environ["OMP_NUM_THREADS"] = "1"
#os.environ["NUMBA_NUM_THREADS"] = "1"

# M4A: übliches Feld für die Tonart (so lesen es auch rekordbox, Traktor und Serato)
M4A_KEY_ATOM = "----:com.apple.iTunes:initialkey"

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aiff', '.aif', '.flac', '.m4a'}

CAMELOT_MAJOR = {
    'B': '1B', 'F#': '2B', 'Gb': '2B', 'C#': '3B', 'Db': '3B', 'G#': '4B', 'Ab': '4B',
    'D#': '5B', 'Eb': '5B', 'A#': '6B', 'Bb': '6B', 'F': '7B', 'C': '8B',
    'G': '9B', 'D': '10B', 'A': '11B', 'E': '12B'
}

CAMELOT_MINOR = {
    'G#': '1A', 'Ab': '1A', 'D#': '2A', 'Eb': '2A', 'A#': '3A', 'Bb': '3A', 
    'F': '4A', 'C': '5A', 'G': '6A', 'D': '7A', 'A': '8A', 
    'E': '9A', 'B': '10A', 'F#': '11A', 'Gb': '11A', 'C#': '12A', 'Db': '12A'
}

def get_camelot(key_note, mode):
    if not key_note: return "-"
    key_note = key_note.replace(" sharp", "#").replace(" flat", "b")
    if mode == 'major':
        return CAMELOT_MAJOR.get(key_note, "-")
    else:
        return CAMELOT_MINOR.get(key_note, "-")

def write_metadata(file_path, artist, title, album, cover_path, bpm, key, camelot, track="0"):
    try:
        from mutagen.id3 import TIT2, TPE1, TALB, TBPM, TKEY, TRCK
        ext = os.path.splitext(file_path)[1].lower()
        def clean(val): return val if val != "NONE" else ""
        if not os.path.isfile(file_path):
            print(f"Tag error: file not found: {file_path}", file=sys.stderr)
            return False
        # Tracknummer: leer, "NONE" oder "0" heißt "nicht anfassen". Der Standardwert "0" wurde
        # früher wirklich geschrieben – Auto-Tag setzte so bei jedem Scan die Tracknummer auf 0.
        track_val = clean(track).strip()
        if track_val == "0":
            track_val = ""
        img_data = None
        mime_type = "image/jpeg"
        if cover_path and cover_path != "NONE" and os.path.exists(cover_path):
            with open(cover_path, 'rb') as f: img_data = f.read()
            if cover_path.lower().endswith('.png'): mime_type = "image/png"

        if ext == '.mp3':
            try: tags = ID3(file_path)
            except ID3NoHeaderError: tags = ID3()   # Datei hat noch keine Tags
            if clean(artist): tags.add(TPE1(encoding=3, text=clean(artist)))
            if clean(title): tags.add(TIT2(encoding=3, text=clean(title)))
            if clean(album): tags.add(TALB(encoding=3, text=clean(album)))
            if clean(bpm): tags.add(TBPM(encoding=3, text=clean(bpm)))
            if clean(camelot): tags.add(TKEY(encoding=3, text=clean(camelot)))
            if track_val: tags.add(TRCK(encoding=3, text=track_val))
            if img_data: tags.add(APIC(encoding=3, mime=mime_type, type=3, desc=u'Cover', data=img_data))
            tags.save(file_path, v2_version=3)
        elif ext == '.flac':
            audio = FLAC(file_path)
            if clean(artist): audio['artist'] = clean(artist)
            # Neu geschriebene Felder: nur wenn wirklich Text drin steht. Der Editor schickt für
            # leere Felder ein Leerzeichen – damit soll kein vorhandener Titel überschrieben werden.
            if clean(title).strip(): audio['title'] = clean(title)
            if clean(album).strip(): audio['album'] = clean(album)
            if img_data:
                pic = Picture()
                pic.type, pic.mime, pic.desc, pic.data = 3, mime_type, u'Cover', img_data
                audio.clear_pictures()
                audio.add_picture(pic)
            if clean(bpm): audio['bpm'] = clean(bpm)
            if clean(camelot): audio['initialkey'] = clean(camelot)
            if track_val: audio['tracknumber'] = track_val
            audio.save()
        elif ext == '.m4a':
            audio = MP4(file_path)
            # (wie bei FLAC: leere Felder überschreiben nichts)
            if clean(artist).strip(): audio['\xa9ART'] = clean(artist)
            if clean(title).strip():  audio['\xa9nam'] = clean(title)
            if clean(album).strip():  audio['\xa9alb'] = clean(album)
            if img_data:
                fmt = MP4Cover.FORMAT_PNG if mime_type == "image/png" else MP4Cover.FORMAT_JPEG
                audio['covr'] = [MP4Cover(img_data, imageformat=fmt)]
            if clean(bpm): 
                try: audio['tmpo'] = [int(float(clean(bpm)))]
                except Exception as e: print(f"Tag warning: BPM {bpm!r} not written to {file_path}: {e}", file=sys.stderr)
            if clean(camelot):
                # Früher landete der Camelot-Code im Kommentarfeld und überschrieb dort,
                # was der Nutzer eingetragen hatte. Der Kommentar bleibt jetzt unberührt.
                audio[M4A_KEY_ATOM] = [MP4FreeForm(clean(camelot).encode("utf-8"))]
            if track_val:
                # "3" oder "3/12" (Nummer/Gesamtzahl)
                try:
                    num, _, total = track_val.partition("/")
                    audio['trkn'] = [(int(num), int(total) if total.strip() else 0)]
                except Exception as e: print(f"Tag warning: track number {track!r} not written to {file_path}: {e}", file=sys.stderr)
            audio.save()
        elif ext in ['.wav', '.aiff', '.aif']:
            audio = WAVE(file_path) if ext == '.wav' else AIFF(file_path)
            if audio.tags is None: audio.add_tags()
            if clean(artist): audio.tags.add(TPE1(encoding=3, text=clean(artist)))
            if clean(title):  audio.tags.add(TIT2(encoding=3, text=clean(title)))
            if clean(album):  audio.tags.add(TALB(encoding=3, text=clean(album)))
            if clean(bpm):    audio.tags.add(TBPM(encoding=3, text=clean(bpm)))
            if clean(camelot): audio.tags.add(TKEY(encoding=3, text=clean(camelot)))
            if track_val:  audio.tags.add(TRCK(encoding=3, text=track_val))
            if img_data:
                # (APIC kommt aus dem Import am Dateianfang. Ein Import HIER machte APIC zur
                # lokalen Variable der ganzen Funktion – der MP3-Zweig oben stürzte dadurch
                # mit Cover ab, und der Fehler wurde verschluckt.)
                audio.tags.add(APIC(encoding=3, mime=mime_type, type=3, desc=u'Cover', data=img_data))
            audio.save(v2_version=3)
        else:
            print(f"Tag error: {ext or 'this file type'} is not supported for tag writing ({file_path})", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"Tag error: could not write tags to {file_path}: {type(e).__name__}: {e}", file=sys.stderr)
        return False
    
def detect_key_advanced(y, sr):
    tuning = librosa.estimate_tuning(y=y, sr=sr)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, tuning=tuning)
    mean_chroma = np.mean(chroma, axis=1) 
    
    major_template = [7.00, 3.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    minor_template = [7.00, 3.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
    
    best_corr = -1
    best_key = ("C", "major")
    pitches = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    for i in range(12):
        rot_maj = np.roll(major_template, i)
        rot_min = np.roll(minor_template, i)
        c_maj = np.corrcoef(mean_chroma, rot_maj)[0, 1]
        c_min = np.corrcoef(mean_chroma, rot_min)[0, 1]
        
        if c_maj > best_corr:
            best_corr = c_maj
            best_key = (pitches[i], "major")
        if c_min > best_corr:
            best_corr = c_min
            best_key = (pitches[i], "minor")
    return best_key    

def refine_bpm(y, sr, coarse_bpm, beat_times=None, hop_length=512):
    """Verfeinert das Tempo aus librosa.beat.beat_track.

    beat_track liefert nur Rasterwerte (bei 22050 Hz z. B. 117.45, 123.05, 129.20, 172.27):
    Tracks mit 122 bis 126 BPM landen alle auf 123.05. Hier wird um diesen Rohwert herum (±6 %)
    in 0.02-BPM-Schritten gesucht, bei welchem Tempo die Einsätze des Stücks am regelmäßigsten
    wiederkehren. Ist das Ergebnis nicht eindeutig (Gesang, Flächen, wechselndes Tempo), gilt der
    mittlere Abstand der gefundenen Beats, sonst der Rohwert.
    """
    coarse = float(coarse_bpm)
    if not np.isfinite(coarse) or coarse <= 0:
        return coarse

    # mittlerer Beat-Abstand als zweite Meinung
    regression = None
    if beat_times is not None and len(beat_times) >= 8:
        slope = np.polyfit(np.arange(len(beat_times)), np.asarray(beat_times, dtype=float), 1)[0]
        if slope > 0:
            regression = 60.0 / slope
            if abs(regression - coarse) > coarse * 0.03:
                regression = None   # Beats sind gesprungen, nicht verwenden

    fine = quality = None
    try:
        env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        fps = sr / hop_length
        max_frames = int(8 * 60 * fps)          # höchstens 8 Minuten aus der Mitte
        if len(env) > max_frames:
            start = (len(env) - max_frames) // 2
            env = env[start:start + max_frames]
        if len(env) >= int(20 * fps):           # unter 20 s zu wenig Material
            env = env - env.mean()
            t = np.arange(len(env)) / fps
            cands = np.arange(coarse * 0.94, coarse * 1.06, 0.02)
            score = np.zeros(len(cands))
            for i in range(0, len(cands), 64):  # in Blöcken, damit der Speicher klein bleibt
                block = cands[i:i + 64, None] / 60.0
                for harmonic, weight in ((1, 1.0), (2, 0.7), (4, 0.5)):
                    phase = -2j * np.pi * harmonic * block * t[None, :]
                    score[i:i + 64] += weight * np.abs((env[None, :] * np.exp(phase)).sum(axis=1))
            best = int(np.argmax(score))
            at_edge = best < 3 or best > len(cands) - 4
            far = np.abs(cands - cands[best]) > cands[best] * 0.005
            if not at_edge and far.any():
                # Scheitelpunkt zwischen den Rasterschritten (Parabel durch die drei höchsten Werte)
                a, b, c = score[best - 1], score[best], score[best + 1]
                shift = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
                fine = float(cands[best] + max(-0.5, min(0.5, shift)) * 0.02)
                quality = float(score[best] / (np.median(score[far]) + 1e-9))
    except Exception as e:
        print(f"BPM refine skipped: {e}", file=sys.stderr)

    if fine is not None and (quality >= 8.0 or (regression is not None and abs(fine - regression) <= fine * 0.003)):
        bpm = fine
    elif regression is not None:
        bpm = regression
    else:
        return coarse
    # Messgenauigkeit ist etwa ±0.02 BPM: knapp neben einer ganzen Zahl heißt ganze Zahl
    if abs(bpm - round(bpm)) <= 0.03:
        bpm = float(round(bpm))
    return bpm


def analyze_track(file_path, do_write_tags=False, min_bpm=0, max_bpm=999):
    try:
        # 1. Gesamtdauer ermitteln
        total_duration = librosa.get_duration(path=file_path)
        
        # 2. DEN GANZEN SONG LADEN (für lückenloses Beatgrid) 🚀
        # Wir nutzen sr=22050, das ist der perfekte Kompromiss aus Speed und Präzision
        y, sr = librosa.load(file_path, sr=22050, mono=True)
        
        # --- BEAT TRACKING (Über die volle Länge!) ---
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        # Wir speichern JEDEN Schlag von Sekunde 0 bis Ende
        beats_string = ";".join([str(round(float(t), 3)) for t in beat_times])

        # --- KEY ANALYSE (Nur auf einem Ausschnitt für Speed) ---
        # Wir nehmen 60 Sekunden ab dem 30% Offset
        start_offset_sec = total_duration * 0.3
        start_sample = int(start_offset_sec * sr)
        end_sample = start_sample + int(min(60, total_duration - start_offset_sec) * sr)
        
        y_snippet = y[start_sample:end_sample]
        detected_note, mode = detect_key_advanced(y_snippet, sr)
        camelot = get_camelot(detected_note, mode)

        # --- BPM LOGIK ---
        bpm_val = float(tempo[0]) if np.ndim(tempo) > 0 else float(tempo)
        bpm_val = refine_bpm(y, sr, bpm_val, beat_times)
        if min_bpm > 0 and bpm_val < min_bpm: bpm_val *= 2
        elif max_bpm > 0 and max_bpm < 999 and bpm_val > max_bpm: bpm_val /= 2
        
        bpm_rounded = round(bpm_val, 2)
        bpm_str = "{:.2f}".format(bpm_rounded)
        
        # --- TAGGING ---
        tag_status = "-"
        if str(do_write_tags) == "True" and camelot != "-" and bpm_rounded > 0:
            ok = write_metadata(str(file_path), "NONE", "NONE", "NONE", "NONE", bpm_str, f"{detected_note} {mode}", camelot)
            tag_status = "Saved" if ok else "Failed"

        # --- ZEIT-STRING FÜR DIE LISTE ---
        secs = int(total_duration)
        duration_str = f"{secs // 60:02d}:{secs % 60:02d}"

        return {
            "Dateiname": os.path.basename(file_path),
            "BPM": bpm_rounded,
            "Time": duration_str,
            "Camelot": camelot,
            "Key": f"{detected_note} {mode}",
            "Tags": tag_status,
            "Pfad": str(file_path),
            "Größe": os.path.getsize(file_path),
            "Beats": beats_string # <--- Jetzt lückenlos von 0.0 bis Ende!
        }
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return {"Dateiname": os.path.basename(file_path), "BPM": 0, "Time": "--:--", "Camelot": "-", "Key": "-", "Tags": "Err", "Pfad": str(file_path), "Größe": 0, "Beats": ""}

def main_worker():
    args = sys.argv[1:]
    if "--worker" in args:
        idx = args.index("analyzer")
        args = args[idx+1:]
    
    if not args: return

    if args[0] == "--tag":
        if len(args) >= 8:
            ok = write_metadata(args[1], args[2], args[3], args[4], args[5], args[6], args[7], args[8] if len(args) > 8 else "NONE", args[9] if len(args) > 9 else "0")
            if ok:
                print("✅ TAG_OK")
            else:
                print("❌ TAG_FAILED")
                sys.exit(1)  # der Editor zeigt dann "Save failed" statt "Saved"
        else:
            print("Tag error: too few arguments for --tag", file=sys.stderr)
            print("❌ TAG_FAILED")
            sys.exit(1)
    else:
        if len(args) >= 2:
            input_path = Path(args[0])
            output_csv = args[1]
            write_tags = args[2] if len(args) > 2 else "False"
            min_b = int(args[3]) if len(args) > 3 else 0
            max_b = int(args[4]) if len(args) > 4 else 999

            files = [input_path] if input_path.is_file() else \
                    [f for f in input_path.rglob('*') if f.suffix.lower() in AUDIO_EXTENSIONS and not f.name.startswith('.')]
            
            print(f"START:{len(files)}", flush=True)
            results = []
            for i, f in enumerate(files):
                res = analyze_track(f, write_tags, min_b, max_b)
                results.append(res)
                print(f"PROGRESS:{i+1}/{len(files)}:{res['Dateiname']}", flush=True)
            
            pd.DataFrame(results).to_csv(output_csv, index=False)
            print("✅DONE", flush=True)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main_worker()