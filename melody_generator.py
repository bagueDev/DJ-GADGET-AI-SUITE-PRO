# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import os
import random
import numpy as np
import librosa
import soundfile as sf
import math

try:
    from mido import Message, MidiFile, MidiTrack, MetaMessage
except ImportError:
    print("❌ ERROR: 'mido' library missing.")
        
import sys
import os
import threading
import functools
import zlib
import logging

# Warnungen landen über den Handler in main.py im Log-Tab
log = logging.getLogger("djgadget")

# Letzter Fehler pro Thread, damit die GUI die echte Ursache im Log zeigen kann
# (in der gebauten App gibt es kein Terminal für die print-Ausgaben).
_tls = threading.local()

def clear_last_error():
    _tls.error = None

def get_last_error():
    return getattr(_tls, "error", None)

def get_last_progression():
    """Progression, die der letzte Full Loop dieses Threads tatsächlich benutzt hat."""
    return getattr(_tls, "progression", None)

def get_last_kick_steps():
    """Kick-Positionen (absolute 16tel-Schritte) des letzten Drum-Laufs dieses Threads."""
    return getattr(_tls, "kick_steps", None)

def get_last_chords():
    """Akkordfolge des letzten audio_to_midi-Laufs im Chords-Modus (Liste von Namen)."""
    return getattr(_tls, "chords", None)

def get_last_key():
    """Geschätzte Tonart des letzten Chords-Laufs als Paar, z.B. 'A minor / C major'."""
    return getattr(_tls, "key", None)

def get_last_bpm():
    """BPM, mit dem der letzte audio_to_midi-Lauf dieses Threads geschrieben hat."""
    return getattr(_tls, "bpm", None)

# --- Seed: reproduzierbare Ergebnisse ---------------------------------------
# Der Generator würfelt über die globalen Zufallsgeneratoren (random, np.random).
# Das Lock sorgt dafür, dass immer nur eine Generierung gleichzeitig würfelt,
# sonst würden sich z.B. Vorschau und Generate gegenseitig die Zahlen wegnehmen.
_GEN_LOCK = threading.RLock()

def _seeded(fn):
    """Macht eine Generator-Funktion per seed=... reproduzierbar.

    Jede Funktion bekommt einen eigenen, aus Seed + Funktionsname abgeleiteten
    Startwert. Innere Aufrufe (Full Loop -> Drums, Chords, ...) erben den Seed,
    deshalb ergibt z.B. die Melodie allein dieselben Noten wie im Full Loop.
    """
    @functools.wraps(fn)
    def wrapper(*args, seed=None, **kwargs):
        with _GEN_LOCK:
            outer = getattr(_tls, "seed", None)
            if seed is None: seed = outer
            if seed is None:
                return fn(*args, **kwargs)
            _tls.seed = seed
            try:
                derived = zlib.crc32(f"{int(seed)}:{fn.__name__}".encode())
                random.seed(derived)
                np.random.seed(derived)
                return fn(*args, **kwargs)
            finally:
                _tls.seed = outer
    return wrapper

def _report_error(label, e):
    _tls.error = f"{label}: {type(e).__name__}: {e}"
    print(f"❌ {_tls.error}")

def get_base_path():
    """Findet den Ordner, in dem die App oder das Skript liegt."""
    if getattr(sys, 'frozen', False):
        # Wir laufen als fertiges macOS-Bundle (.app)
        # Bei PyInstaller 6.x (onedir) liegen die --add-data Assets unter sys._MEIPASS.
        # Fallback: 3 Ebenen hoch vom Binärpfad, um zum Ordner NEBEN der .app zu kommen.
        meipass = getattr(sys, '_MEIPASS', '')
        if meipass and os.path.isdir(os.path.join(meipass, "samples")):
            return meipass
        return os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../../.."))
    else:
        # Wir laufen als normales Python-Skript
        return os.path.dirname(os.path.abspath(__file__))

# Diese Variable nutzen wir jetzt überall im Backend
BASE_PATH = get_base_path()
SAMPLES_DIR = os.path.join(BASE_PATH, "samples")    

# --- MUSIK THEORIE DATEN ---
NOTES = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
SCALES = {
    # --- BASICS ---
    "Major": [0, 2, 4, 5, 7, 9, 11], 
    "Minor": [0, 2, 3, 5, 7, 8, 10],
    "Pentatonic Major": [0, 2, 4, 7, 9],
    "Pentatonic Minor": [0, 3, 5, 7, 10],
    "Blues": [0, 3, 5, 6, 7, 10],
    # --- ORCHESTRAL & CINEMATIC ---
    "Locrian": [0, 1, 3, 5, 6, 8, 10],
    "Melodic Minor": [0, 2, 3, 5, 7, 9, 11],
    "Lydian": [0, 2, 4, 6, 7, 9, 11],
    "Dorian": [0, 2, 3, 5, 7, 9, 10],
    "Phrygian": [0, 1, 3, 5, 7, 8, 10],
    # --- EXOTIC & WORLD ---
    "Double Harmonic (Byzantine)": [0, 1, 4, 5, 7, 8, 11],
    "Hungarian Minor": [0, 2, 3, 6, 7, 8, 11],
    "Hirajoshi (Japanese)": [0, 2, 3, 7, 8],
    "Harmonic Minor": [0, 2, 3, 5, 7, 8, 11],
    # --- JAZZ & MODERN ---
    "Mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "Lydian Dominant": [0, 2, 4, 6, 7, 9, 10],
    "Super Locrian (Altered)": [0, 1, 3, 4, 6, 8, 10],
    "Whole Tone": [0, 2, 4, 6, 8, 10],
    "Chromatic": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
}
# --- NEUE DATEN FÜR PROGRESSIONEN ---
# --- DAS ERWEITERTE REZEPTBUCH (Vollständig) ---
PROGRESSIONS = {
    "Random": None,
    "--- 🎧 TOP 5 HITS ---": None,
    "⭐Pop Anthem: 1-5-6-4": [0, 4, 5, 3],
    "⭐ Universal Pop: 4-1-5-6": [3, 0, 4, 5],
    "🌅 Dreamy Pop: 1-6-2-5": [0, 5, 1, 4],
    "⚡ Energetic Pop: 5-6-4-1": [4, 5, 3, 0],
    "🎶 Indie Pop: 6-1-3-7": [5, 0, 2, 6],
    "🔄 Retro Pop: 1-6-4-5": [0, 5, 3, 4],
    "💔 Emotional: 6-4-1-5": [5, 3, 0, 4],
    "🎼 Circle of 5ths: 1-4-7-3": [0, 3, 6, 2],
    "--- 🏠 HOUSE ---": None,
    "🏠Deep House: 1-7-6-5": [0, 6, 5, 4],
    "🌞 Piano House: 4-3-6-5": [3, 2, 5, 4],
    "🌀 Melodic House: 6-1-3-7": [5, 0, 2, 6],
    "🔊 Techno/Minimal: 1-5 Loop": [0, 4],
    "🏝️ Tropical House: 1-5-6-4": [0, 4, 5, 3],
    "🏠 Classic House: 1-4 Loop": [0, 3],
    "🕺 Soulful: 2-5-1-6": [1, 4, 0, 5],
    "--- 🚀 DRUM & BASS ---": None,
    "🚀 Liquid DnB: 6-4-1-5": [5, 3, 0, 4],
    "🌫 Liquid Alt: 4-6-1-5": [3, 5, 0, 4],
    "🔥 Neurofunk: 1-b2-b3-b2": [0, "b1", "b2", "b1"],
    "🌌 Atmospheric: 1-2-4-2": [0, 1, 3, 1],
    "🧊 Minimal DnB: 1-5": [0, 4],
    "--- 🎛️ HIP HOP & TRAP ---": None,
    "🥁 Boom Bap: 1-4": [0, 3],
    "🌑 Dark Trap: 6-5-4-5": [5, 4, 3, 4],
    "🎷 Jazz-Hop: 2-5-1-4": [1, 4, 0, 3],
    "🎹 Soul / RnB: 1-3-4-3": [0, 2, 3, 2],
    "🧨 Drill: 6-b6-5-b5": [5, "b5", 4, "b4"],
    "🌤 Lo-Fi: 1-3-2-5": [0, 2, 1, 4],
    "🎛️ Modern Trap: 1-6 Tension": [0, 5],    
    "--- 🦁 REGGAE & DUB ---": None,
    "🎸 Reggae: I-IV Loop": [0, 3],
    "🌅 Reggae: Chill (I-ii)": [0, 1],
    "🇯🇲 Reggae: Roots (i-VII)": [0, 6],
    "☀️ Reggae: Positive (I-IV-V-IV)": [0, 3, 4, 3],
    "❤️ Reggae: Lovers Rock (I-vi-IV-V)": [0, 5, 3, 4],
    "--- 🌍 STYLE / WORLD ---": None,
    "🕌 Middle Eastern: 1-b2-b3-5": [0, "b1", "b2", 4],
    "🇧🇷 Samba: 2-5-3-6": [1, 4, 2, 5],
    "🇪🇸 Flamenco: 1-b7-b6-5": [0, "b6", "b5", 4],
    "🇯🇵 Japanese: 1-b3-4-b6": [0, "b2", 3, "b5"],
    "🕌 Oriental: 1-b1-2-3": [0, "b1", 2, 3],
    "--- 🎷 JAZZ LIBRARY ---": None,
    "🎷 Jazz: Major ii-V-I": [1, 4, 0],           # Der absolute Standard
    "🎻 Jazz: Minor ii-V-I": [1, 4, 0],           # (Wird über Moll-Skalen zum "Diminished" Vibe)
    "🔄 Jazz: Rhythm Changes": [0, 5, 1, 4],       # Die Basis von "I Got Rhythm"
    "🔥 Jazz: Tritone Sub": [1, "b1", 0],         # ii - bII7 - I (Extrem edel!)
    "🌃 Jazz: Romantic (IV-iv-I)": [3, "b3", 0],   # Der "Moon River" Effekt
    "🏃 Jazz: Giant": [0, "b2", 4, "b6", 1] # Ein Hauch von "Giant Steps"
    
}

def harmony_intervals(scale):
    """Tonleiter, aus der Akkorde, Bass, Pads und Strings gebaut werden.

    Die Progression-Presets zählen Stufen einer Sieben-Ton-Leiter (1-5-6-4 ...) und stapeln
    Terzen. Bei Skalen mit 5, 6 oder 12 Tönen zeigen diese Stufen auf falsche Töne und es
    entstehen keine Dreiklänge. Dort wird deshalb die passende Dur- oder Moll-Leiter genommen
    (kleine Terz ohne große -> Moll, sonst Dur). Die MELODIE bleibt in der gewählten Skala –
    Pentatonik oder Blues über normalen Akkorden ist der übliche Fall.
    """
    intervals = SCALES.get(scale, SCALES["Minor"])
    if len(intervals) == 7:
        return intervals
    return SCALES["Minor"] if (3 in intervals and 4 not in intervals) else SCALES["Major"]

def _prog_key(name):
    """Vergleichsschlüssel ohne Emojis/Leerzeichen, damit GUI-Name und Rezept
    nicht an einem fehlenden Leerzeichen scheitern."""
    return "".join(c for c in str(name).lower() if c.isascii() and (c.isalnum() or c in "-#/()"))

_PROG_LOOKUP = {_prog_key(k): v for k, v in PROGRESSIONS.items() if v}

def resolve_progression(name):
    """Rezept zu einem Preset-Namen; None bei 'Random', Trennzeilen und Unbekanntem."""
    if not name or str(name).strip().startswith("---"):
        return None
    return _PROG_LOOKUP.get(_prog_key(name))

def pick_random_progression():
    """Name eines zufälligen Presets (damit alle Spuren dieselbe Harmonie bekommen)."""
    return random.choice([k for k, v in PROGRESSIONS.items() if v])

GENRE_PROFILES = {
    "Random": {
        "bpm": 124,
        "scale_suggestion": "Major",
        "sound_suggestion": "sine",
        "chord_mode": "Triads (3-Note)",
        "bass_style": "Simple (Root)"
    },
    "Techno/Trance": {
        "bpm": 128,
        "scale_suggestion": "Phrygian",
        "sound_suggestion": "saw",
        "chord_mode": "Power (5ths)",
        "bass_style": "Busy (Melodic)"
    },
    "House/Deep": {
        "bpm": 124,
        "scale_suggestion": "Dorian",
        "sound_suggestion": "epiano",
        "chord_mode": "7ths (4-Note)",
        "bass_style": "Steady (Groove)"
    },
    "Synthpop/80s": {
        "bpm": 120,
        "scale_suggestion": "Major",
        "sound_suggestion": "saw",
        "chord_mode": "Triads (3-Note)",
        "bass_style": "Steady (Groove)"
    },
    "HipHop": {
        "bpm": 90,
        "scale_suggestion": "Minor",
        "sound_suggestion": "epiano",
        "chord_mode": "7ths (4-Note)",
        "bass_style": "Steady (Groove)"
    },
    "Trap": {
        "bpm": 145,
        "scale_suggestion": "Phrygian",
        "sound_suggestion": "saw",
        "chord_mode": "Melody (Mono)",
        "bass_style": "Busy (Melodic)"
    },
    "DnB/Breakbeat": {
        "bpm": 174,
        "scale_suggestion": "Major",
        "sound_suggestion": "epiano",
        "chord_mode": "9ths (5-Note)",
        "bass_style": "Busy (Melodic)"
    },
    "DnB/Rolling": {
        "bpm": 174,
        "scale_suggestion": "Major",
        "sound_suggestion": "epiano",
        "chord_mode": "9ths (5-Note)",
        "bass_style": "Busy (Melodic)"
    },
    "Jazz": {
        "bpm": 130,
        "scale_suggestion": "Dorian",
        "sound_suggestion": "epiano",
        "chord_mode": "6/9 (Jazz)",
        "bass_style": "Jazz Walking"
    },
    "Reggae": {
        "bpm": 75,
        "scale_suggestion": "Minor",
        "sound_suggestion": "epiano",
        "chord_mode": "Triads (3-Note)",
        "bass_style": "Busy (Melodic)"
    },
    "Oriental": {
        "bpm": 110,
        "scale_suggestion": "Double Harmonic (Byzantine)",
        "sound_suggestion": "epiano",
        "chord_mode": "Melody (Mono)",
        "bass_style": "Simple (Root)"
    },
    "Ambient": {
        "bpm": 65,
        "scale_suggestion": "Lydian",
        "sound_suggestion": "sine",
        "chord_mode": "9ths (5-Note)",
        "bass_style": "Simple (Root)"
    }
}
# --- BASS RHYTHM TRESOR (Hard-Grid für maximale Tightness) ---
BASS_PATTERNS = {
    # Klassische Modi (Standardisiert)
    "Simple (Root)": [(0, 16)],
    "Jazz Walking": [(0, 4), (4, 4), (8, 4), (12, 4)],   
    # Stranjah & Pro Patterns
    "Standard 1/4s": [(0, 4), (4, 4), (8, 4), (12, 4)],
    "Driving 1/8s": [(0, 2), (2, 2), (4, 2), (6, 2), (8, 2), (10, 2), (12, 2), (14, 2)],
    "Offbeat Start (Beat 2)": [(4, 12)],
    "Fake Triplet (3-3-2)": [(0, 6), (6, 6), (12, 4)],
    "The Donk (Dotted 1/8s)": [(0, 3), (3, 3), (6, 3), (9, 3), (12, 4)],
    "Footwork (Hectic)": [(0, 3), (3, 3), (6, 2), (8, 3), (11, 3), (14, 2)],
    "Dembow (Reggaeton)": [(0, 4), (4, 4), (8, 3), (11, 3), (14, 2)],
    "Neuro Roller": [(0, 4), (4, 3), (7, 3), (10, 3), (13, 3)],
    "Syncopator (Complex)": [(0, 6), (6, 2), (8, 3), (11, 5)]
} 

def apply_envelope(signal, attack=0.03, release=0.1, mode="exponential", sr=44100):
    """Garantierte Nullpunkt-Landung und sanftes Einblenden."""
    n = len(signal)
    if n == 0: return signal
    
    t = np.linspace(0, n/sr, n)
    envelope = np.ones(n)
    
    # 1. Attack (Sanfter Einschwingvorgang)
    attack_samples = min(int(attack * sr), n // 4)
    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
    # 2. Release (Ausklingen)
    if mode == "exponential":
        # Wir kombinieren Exponential mit einem winzigen linearen Fade am Ende,
        # um sicherzugehen, dass wir bei EXAKT Null landen.
        decay = np.exp(-7 * t) 
        # Die letzten 10ms werden hart auf Null gefaded
        fade_out_len = min(int(0.01 * sr), n // 2)
        if fade_out_len > 0:
            fade_out = np.linspace(1, 0, fade_out_len)
            decay[-fade_out_len:] *= fade_out
        envelope = envelope * decay
            
    return signal * envelope

def soft_clipper(signal, threshold=0.8):
    """Simuliert analoge Sättigung (kein hartes Knacken bei Spitzen)."""
    # Alles über dem Threshold wird sanft abgerundet (np.tanh Effekt)        
    return np.tanh(signal)

def apply_stereo_chorus(signal, sr=44100, depth=0.002, rate=0.5):
    """Verwandelt ein Mono-Signal in ein breites Stereo-Signal."""
    # Erstellt einen leeren Stereo-Puffer (2 Spalten: Links, Rechts)
    stereo = np.zeros((len(signal), 2))
    
    # Links bleibt das Original (leicht leiser für Headroom)
    stereo[:, 0] = signal * 0.7
    
    # Rechts erstellen wir die Kopie mit winziger Verzögerung
    # Ein Delay von ca. 20-30ms erzeugt die Breite
    delay_samples = int(0.025 * sr) 
    right_channel = np.zeros_like(signal)
    right_channel[delay_samples:] = signal[:-delay_samples]
    
    # Rechts mischen wir noch ein ganz leichtes "Eiern" (LFO) dazu für den Chorus-Vibe
    stereo[:, 1] = right_channel * 0.7
    
    return stereo

def get_waveform(freq, t, wave_type="sine", vel=100):
    """Erzeugt hochwertige Hybrid-Sounds."""
    # Velocity-Faktor (0.0 bis 1.0)
    v = vel / 127.0
        # WICHTIG: Wir brauchen t_local (startet bei 0) für die Lautstärke-Form
    # t ist die absolute Zeit (z.B. 1.5s, 1.51s...)
    t_local = t - t[0] if len(t) > 0 else t
    
    if wave_type == "saw":
        return 2.0 * (t * freq - np.floor(0.5 + t * freq))
    
    elif wave_type == "square":
        return np.sign(np.sin(2 * np.pi * freq * t))
    
    elif wave_type == "epiano":
        # --- DREI-SCHICHTEN EPiano ---
        # Schicht 1: Der warme Körper (Sinus + leichte Verstimmung für Breite)
        body = np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(2 * np.pi * (freq + 0.5) * t)
        
        # Schicht 2: Die Glocke (Tine) - Hoher metallischer Ping
        # Wird bei hoher Velocity (v) lauter und präsenter
        tine_freq = freq * 4 # 2 Oktaven höher
        tine = np.sin(2 * np.pi * tine_freq * t) * np.exp(-40 * t) * (0.3 + v * 0.4)
        
        # Schicht 3: Die Wärme (Subtiler Grundton)
        warmth = 0.1 * np.sin(2 * np.pi * (freq * 0.5) * t_local)
        
        return (body * 0.6 + tine + warmth)
    
    else: # "sine" (Optimiert & Lautstärke-sicher)
        # Wir gewichten die Wellen: 0.95 + 0.05 = 1.00 (Perfekter Pegel)
        fundamental = 0.95 * np.sin(2 * np.pi * freq * t)
        harmonic = 0.05 * np.sin(2 * np.pi * (freq * 2) * t)
        return fundamental + harmonic
    
def get_chromatic_note(scale_notes, step):
    """Hilfsfunktion: Wandelt Rezepte wie 'b1' in echte Midi-Noten um."""
    if isinstance(step, int):
        return scale_notes[step]
    
    # Wenn step ein String ist, z.B. "b1" (erniedrigte 2. Stufe)
    try:
        if step.startswith("b"):
            index = int(step[1:]) # Die Zahl nach dem 'b'
            return scale_notes[index] - 1
        elif step.startswith("#"):
            index = int(step[1:]) # Die Zahl nach dem '#'
            return scale_notes[index] + 1
    except (IndexError, ValueError):
        return scale_notes[0] # Fallback
    return scale_notes[0]

@_seeded
def create_chord_files(root, scale, bpm, bars, progression_name, mode, output_dir, voicing_style="Root Position", sound="sine", genre="Ambient", density=80, swing=0, time_sig="4/4", human=False, arr_mode="♾️ Infinite Loop"):
    try:
        os.makedirs(output_dir, exist_ok=True)
        total_bars = int(bars)
        print(f"🎹 Generating Rhythmic Chords: {progression_name} ({genre})")
        
        wav_path = os.path.join(output_dir, "generated_chords.wav")
        mid_path = os.path.join(output_dir, "generated_chords.mid")

        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)
        track.append(MetaMessage('track_name', name='Chords'))
        track.append(MetaMessage('set_tempo', tempo=int(60000000 / bpm)))

        # 1. Zeit-Raster & Skala
        steps_per_bar = 12 if ("3/4" in time_sig or "6/8" in time_sig) else 16
        intervals = harmony_intervals(scale)
        base_note_ref = NOTES.get(root, 0) + 48 
        scale_notes = [base_note_ref + i for i in intervals]
        for oct_off in [12, 24]: scale_notes += [base_note_ref + oct_off + i for i in intervals]

        # 2. Rhythmus-Template festlegen
        if "Techno" in genre: pattern, dur = [0, 4, 8, 12], 1
        elif "House" in genre: pattern, dur = [2, 6, 10, 14], 2
        elif "DnB" in genre: pattern, dur = [0, 3, 10], 2
        elif "HipHop" in genre or "Trap" in genre: pattern, dur = [0, 6], 4
        elif "Jazz" in genre: pattern, dur = [0, 3, 7, 10], 2
        else: pattern, dur = [0], steps_per_bar # Ambient/Pop = Lange Fläche

        # 3. MIDI & AUDIO LOOP
        sr, sec_per_step = 44100, (60 / bpm) / 4
        ticks_per_step = mid.ticks_per_beat // 4
        audio_buffer = np.zeros(int((total_bars * steps_per_bar * sec_per_step + 1.5) * sr))
        T_master = np.linspace(0, len(audio_buffer)/sr, len(audio_buffer), False)
        
        last_chord = None
        last_msg_tick = 0
        prob = density / 100.0

        for bar in range(total_bars):
            energy = get_arrangement_energy(bar, total_bars, arr_mode)
            # --- NEU: ENERGIE & SPRUNG-ERKENNUNG (Zuerst berechnen!) ---
            energy = get_arrangement_energy(bar, total_bars, arr_mode)
            energy_prev = get_arrangement_energy(bar-1, total_bars, arr_mode) if bar > 0 else 0
            
            # Ein Sprung passiert, wenn die Energie von unter 0.8 auf über 0.8 geht
            is_energy_jump = (energy >= 0.8 and energy_prev < 0.8)
            # -----------------------------------------------------------
            # --- DYNAMISCHE HARMONIE-DICHTE ---
            # Wenn Energie niedrig ist, nutzen wir nur einfache Dreiklänge
            # "Melody (Mono)" ist kein Akkord-Typ -> Dreiklänge (sonst bestünde die Akkordspur nur aus Grundtönen)
            chord_type = "Triads (3-Note)" if "Melody" in mode else mode
            current_mode = "Triads (3-Note)" if energy < 0.7 else chord_type
            # Wenn Energie SEHR niedrig ist (Intro), spielen wir nur eine lange Fläche (Pad)
            # anstatt der rhythmischen Stabs
            current_pattern = [0] if energy < 0.4 else pattern
            current_dur = steps_per_bar if energy < 0.4 else dur
            # ... (Hier nutzt du jetzt 'current_mode' beim Bauen der Akkord-Noten 
            # und 'current_pattern'/'current_dur' in der Rhythmus-Schleife) ...
            prog_data = resolve_progression(progression_name)
            
            if prog_data:
                step_data = prog_data[bar % len(prog_data)]
                
                # --- FIX: Wir bestimmen den Basis-Index (0-6) direkt ---
                if isinstance(step_data, str):
                    base_idx = int(step_data[1:]) # z.B. bei "b5" ist der Index 5
                else:
                    base_idx = step_data
                
                # Die echte MIDI-Note (evtl. chromatisch verschoben)
                root_note = get_chromatic_note(scale_notes, step_data)
                # Wir nutzen base_idx für die Terzschichtung
                idx = base_idx 
            else:
                idx = random.randint(0, 6)
                root_note = scale_notes[idx]

            # 2. AKKORD BAUEN (Dynamische Logik für alle Modi)
            chord_notes = [root_note]
            try:
                # --- A: Die Basis-Schichtung ---
                if any(m in current_mode for m in ["Triads", "7ths", "9ths", "Add9", "6/9"]):
                    # Klassisch: Terz und Quinte hinzufügen
                    chord_notes.append(scale_notes[idx + 2])
                    chord_notes.append(scale_notes[idx + 4])
                
                elif "Sus2" in current_mode:
                    # Schwebend: große Sekunde statt Terz. Liegt in der Skala an dieser Stufe nur
                    # eine kleine Sekunde (reibt), wird die große genommen.
                    second = scale_notes[idx + 1]
                    chord_notes.append(second if second - root_note == 2 else root_note + 2)
                    chord_notes.append(root_note + 7)  # Sus-Akkorde immer mit reiner Quinte
                
                elif "Sus4" in current_mode:
                    # Spannung: reine Quarte statt Terz. Liegt in der Skala an dieser Stufe eine
                    # übermäßige Quarte (Tritonus), wird die reine genommen.
                    fourth = scale_notes[idx + 3]
                    chord_notes.append(fourth if fourth - root_note == 5 else root_note + 5)
                    chord_notes.append(root_note + 7)  # Sus-Akkorde immer mit reiner Quinte
                
                elif "Power" in current_mode:
                    # Nur die Quinte (Rock/Techno)
                    chord_notes.append(scale_notes[idx + 4])
                # --- B: Die Erweiterungen (Farbtöne) ---
                # Septime hinzufügen bei 7ths und 9ths
                if "7ths" in current_mode or "9ths" in current_mode:
                    chord_notes.append(scale_notes[idx + 6])
                # None (9te) hinzufügen bei 9ths und Add9
                if any(m in current_mode for m in ["9ths", "Add9"]):
                    chord_notes.append(scale_notes[idx + 8])

                # Speziell für 6/9 Jazz-Akkorde
                if "6/9" in current_mode:
                    chord_notes.append(scale_notes[idx + 5]) # Die Sechste
                    chord_notes.append(scale_notes[idx + 8]) # Die Neunte

            except IndexError:
                pass # Falls wir am oberen Ende der Skala sind, spielen wir weniger Noten

            chord_notes = apply_voicing(chord_notes, voicing_style, last_chord)
            last_chord = chord_notes

            # Den Akkord rhythmisch innerhalb des Taktes spielen
            for step_in_bar in current_pattern:
                if random.random() > prob and step_in_bar != 0: continue # Density Check
                
                abs_step = (bar * steps_per_bar) + step_in_bar
                
                # Timing mit Swing
                curr_time = abs_step * sec_per_step
                curr_tick = abs_step * ticks_per_step
                if abs_step % 2 != 0:
                    shift = (sec_per_step * (swing / 100) * 0.6)
                    curr_time += shift
                    curr_tick += int(ticks_per_step * (swing / 100) * 0.6)

                # MIDI
                delta = curr_tick - last_msg_tick
                
                # --- ZUERST DIE VELOCITY BERECHNEN ---
                # Der erste Schlag im Takt (step_in_bar == 0) bekommt den Akzent
                # --- NEU: DYNAMISCHE CHORD-VELOCITY (Arrangement-Aware) ---
                if step_in_bar == 0 and is_energy_jump:
                    # Wenn wir in den Chorus springen: Maximaler Glanz!
                    chord_vel = 120 
                else:
                    # Basis-Lautstärke (90) + Akzent auf der Eins (20)
                    # Das Ganze wird mit der aktuellen Energie des Taktes multipliziert
                    base_chord_v = 90
                    accent_v = 20 if step_in_bar == 0 else 0
                    chord_vel = int((base_chord_v + accent_v) * energy)
                
                # Humanize & Sicherheits-Leitplanke
                if human: 
                    chord_vel += random.randint(-8, 8)
                chord_vel = max(0, min(127, chord_vel)) 
                # ---------------------------------------------------------
                # --- DANN DIE NOTEN SCHREIBEN ---
                for i, n in enumerate(chord_notes):
                    # Wir nutzen hier jetzt die Variable 'chord_vel'
                    track.append(Message('note_on', note=n, velocity=chord_vel, time=delta if i==0 else 0, channel=0))
                
                for i, n in enumerate(chord_notes):
                    track.append(Message('note_off', note=n, velocity=0, time=dur * ticks_per_step if i==0 else 0, channel=0))
                
                last_msg_tick = curr_tick + (dur * ticks_per_step)
                # AUDIO
                s_idx = int(np.round(curr_time * sr))
                e_idx = s_idx + int(np.round((current_dur * sec_per_step + 0.4) * sr))
                if e_idx < len(audio_buffer):
                    t_slice = T_master[s_idx:e_idx]
                    mixed_wave = np.zeros_like(t_slice)
                    gain = 0.3 / len(chord_notes)
                    for n in chord_notes:
                        freq = 440.0 * (2.0 ** ((n - 69) / 12.0))
                        mixed_wave += get_waveform(freq, t_slice, sound) * gain
                    audio_buffer[s_idx:e_idx] += apply_envelope(mixed_wave, attack=0.03, mode="exponential")

        mid.save(mid_path)
                
        # 2. Audio-Finalisierung (Limiter & Normalisierung)
        if np.max(np.abs(audio_buffer)) > 0:
            audio_buffer = audio_buffer / np.max(np.abs(audio_buffer))
            audio_buffer = soft_clipper(audio_buffer)
            audio_buffer = audio_buffer * 0.85
        # 3. Stereo-Check & Speichern
        # Wir prüfen den Namen der Datei: Wenn es NICHT die Drums sind -> Stereo
        if "drums" not in wav_path.lower():
            # Hier rufen wir die neue Chorus-Funktion auf
            stereo_signal = apply_stereo_chorus(audio_buffer)
            sf.write(wav_path, stereo_signal, sr)
        else:
            # Drums bleiben Mono für mehr Druck in der Mitte
            sf.write(wav_path, audio_buffer, sr)

        return wav_path, mid_path
    except Exception as e:
        _report_error("Chord Rhythm Error", e); return None, None
            
def apply_voicing(chord_notes, style, last_chord=None):
    """Sortiert die Noten des Akkords um, um Inversions zu erzeugen."""
    notes = sorted(chord_notes)
    
    if style == "Root Position" or len(notes) < 2:
        return notes
    
    # Power-Chords (2 Noten) haben keine Terz → Inversion nicht anwendbar
    if len(notes) < 3:
        return notes
    
    if style == "1st Inversion":
        # Die tiefste Note eine Oktave nach oben
        return sorted([notes[1], notes[2], notes[0] + 12] + notes[3:])
        
    if style == "2nd Inversion":
        # Die zwei tiefsten Noten eine Oktave nach oben
        return sorted([notes[2], notes[0] + 12, notes[1] + 12] + notes[3:])
    
    if style == "Smart Smooth" and last_chord:
        # Die "Magie": Wir suchen die Umkehrung mit dem geringsten Abstand zum Vorgänger
        target_avg = sum(last_chord) / len(last_chord)
        best_voicing = notes
        min_distance = 999
        
        # Wir prüfen 3 Oktav-Varianten des Akkords
        for shift in [-12, 0, 12]:
            shifted_chord = [n + shift for n in notes]
            # Wir testen zusätzlich die 3 Umkehrungen innerhalb dieses Shifts
            for i in range(len(shifted_chord)):
                # Simuliere Umkehrung
                test_voicing = sorted(shifted_chord[i:] + [n + 12 for n in shifted_chord[:i]])
                avg = sum(test_voicing) / len(test_voicing)
                dist = abs(avg - target_avg)
                
                if dist < min_distance:
                    min_distance = dist
                    best_voicing = test_voicing
        return best_voicing

    return notes
# ==========================================
# TEIL 1: MELODY GENERATOR
# ==========================================
@_seeded
def create_melody_files(root, scale, bpm, bars, time_sig, octave, mode, density, swing, human, sound, genre, prog, output_dir, arr_mode="♾️ Infinite Loop", motif=True):
    try:
        # In jeder der Generierungs-Funktionen ganz oben einfügen:
        os.makedirs(output_dir, exist_ok=True)
        print(f"🎹 Generating: {root} {scale} ({mode}) in {time_sig}...")
        wav_path = os.path.join(output_dir, "generated_melody.wav")
        mid_path = os.path.join(output_dir, "generated_melody.mid")
        
        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)
        track.append(MetaMessage('track_name', name='Lead Melody'))
        track.append(MetaMessage('set_tempo', tempo=int(60000000 / bpm)))
        
        # 1. Noten-Pool berechnen
        octave_map = {"Bass (Low)": 36, "Deep (Mid-Low)": 48, "Mid (Standard)": 60, "Lead (High)": 72}
        base_note = NOTES.get(root, 0) + octave_map.get(octave, 60)
        intervals = SCALES.get(scale, SCALES["Minor"])
        
        # --- NEU: Basis-Skala für den Harmony-Link definieren ---
        base_note_ref = NOTES.get(root, 0) + 48 # Referenz auf mittlerer Tonhöhe
        # (Akkord-Stufen aus der Sieben-Ton-Leiter; die Melodietöne unten bleiben in der gewählten Skala)
        harm = harmony_intervals(scale)
        scale_notes = [base_note_ref + i for i in harm]
        # Wir erweitern scale_notes um 2 Oktaven, damit der Harmony-Link genug Futter hat
        for oct_off in [12, 24]:
            scale_notes += [base_note_ref + oct_off + i for i in harm]
        # --------------------------------------------------------
        
        # Pool über 3 Oktaven
        allowed_notes = []
        for oct_offset in [-12, 0, 12]:
            for interval in intervals: allowed_notes.append(base_note + oct_offset + interval)
        allowed_notes.sort()

        # 2. Time Signature
        steps_per_bar = 16
        if "3/4" in time_sig: steps_per_bar = 12
        elif "6/8" in time_sig: steps_per_bar = 12
        
        total_steps = int(bars) * steps_per_bar
        prob = density / 100.0
        
        # --- 3. GENERIERUNG MIT HARMONY-LINK ---
        # Erst das Rezept finden (wie bei den Chords)
        # --- 3. GENERIERUNG MIT DYNAMISCHER SKALEN-EVOLUTION ---
        prog_data = resolve_progression(prog)

        generated_events = []

        if motif:
            # --- MOTIV-ENGINE -------------------------------------------------
            # Statt jede Note einzeln zu würfeln, wird pro Energie-Stufe ein
            # eintaktiges Motiv A (und ein Kontrast-Motiv B) erfunden und in
            # 4-Takt-Phrasen wiederverwendet:   A | A' (Ende variiert) | B | A (Schluss)
            # Ein Motiv = Liste (Startschritt, Dauer, Stufen-Abstand zum Anker).
            # Der Anker folgt dem Akkord-Grundton, das Motiv wandert also mit
            # der Progression mit (Sequenz) und bleibt trotzdem erkennbar.
            n_pool = len(allowed_notes)
            home = n_pool // 2
            jump_range = 5 if ("Jazz" in genre or "Arp" in genre) else 2
            low_steps = [0, 2, 4, 7, 9] if "Major" in scale else [0, 2, 3, 7, 8]
            motifs = {}

            def _clamp_off(o):
                return max(-4, min(5, o))

            def _make_motif(lengths, first_offset):
                best = []
                for _ in range(4):  # ein paar Versuche, damit das Motiv nicht leer bleibt
                    cand, pos, off = [], 0, first_offset
                    while pos < steps_per_bar:
                        if random.random() < prob:
                            dur = min(random.choice(lengths), steps_per_bar - pos)
                            if cand:
                                move = random.randint(-jump_range, jump_range)
                                if move == 0 and random.random() < 0.7:
                                    move = random.choice([-1, 1])  # Tonwiederholung nur gelegentlich
                                off = _clamp_off(off + move)
                            cand.append((pos, dur, off))
                            pos += dur
                        else:
                            pos += 1
                    if len(cand) > len(best): best = cand
                    if len(best) >= 2: break
                return best or [(0, min(lengths[-1], steps_per_bar), first_offset)]

            def _vary(m):
                """Gleicher Rhythmus, anderes Ende (letzte 1-2 Töne verschoben)."""
                m = list(m)
                k = 1 if len(m) < 4 else 2
                for i in range(max(0, len(m) - k), len(m)):
                    pos, dur, off = m[i]
                    m[i] = (pos, dur, _clamp_off(off + random.choice([-2, -1, 1, 2])))
                return m

            def _cadence(m):
                """Phrasenschluss: letzter Ton landet auf dem Akkord-Grundton und wird gehalten."""
                m = list(m)
                pos, dur, _ = m[-1]
                m[-1] = (pos, min(steps_per_bar - pos, max(dur, 4)), 0)
                return m

            def _anchor(chord_root):
                """Skalenton, der dem Akkord-Grundton am nächsten kommt – möglichst in der Mitte des Tonbereichs."""
                def pc_dist(i):
                    d = (allowed_notes[i] - chord_root) % 12
                    return min(d, 12 - d)
                return min(range(n_pool), key=lambda i: (pc_dist(i), abs(i - home)))

            for bar in range(int(bars)):
                energy = get_arrangement_energy(bar, int(bars), arr_mode)
                # Regie wie bisher: Atempause im 3. Takt jedes 4er-Blocks, Stille bei wenig Energie
                is_breathing = (bar % 4 == 2) and "Infinite" not in arr_mode
                if is_breathing or energy < 0.6:
                    generated_events.extend([(None, 1)] * steps_per_bar)
                    continue

                high = energy >= 0.8  # Chorus: längere Töne, volle Skala / Verse: kürzer, pentatonisch
                if ("A", high) not in motifs:
                    lengths = [2, 4] if high else [1, 2]
                    motifs[("A", high)] = _make_motif(lengths, 0)
                    motifs[("B", high)] = _make_motif(lengths, random.choice([2, 4]))

                role, phrase = bar % 4, bar // 4
                if role == 0:   m = motifs[("A", high)]
                elif role == 1: m = _vary(motifs[("A", high)])
                elif role == 2: m = motifs[("B", high)] if phrase % 2 == 0 else _vary(motifs[("B", high)])
                else:           m = _cadence(motifs[("A", high)])

                if prog_data:
                    chord_root = get_chromatic_note(scale_notes, prog_data[bar % len(prog_data)]) % 12
                else:
                    chord_root = NOTES.get(root, 0)
                anchor = _anchor(chord_root)
                # Töne des Akkords in diesem Takt: Grundton + Terz + Quinte, von der Stufe aus in
                # Skalenschritten gestapelt – genau so baut auch die Akkordspur ihre Dreiklänge.
                if prog_data:
                    step_d = prog_data[bar % len(prog_data)]
                    degree = int(step_d[1:]) if isinstance(step_d, str) else step_d
                else:
                    degree = 0
                chord_pcs = {chord_root, scale_notes[degree + 2] % 12, scale_notes[degree + 4] % 12}
                last_idx = None

                onsets = {pos: (dur, off) for pos, dur, off in m}
                pos = 0
                while pos < steps_per_bar:
                    if pos not in onsets:
                        generated_events.append((None, 1))
                        pos += 1
                        continue
                    dur, off = onsets[pos]
                    idx = max(0, min(n_pool - 1, anchor + off))
                    if not high and (allowed_notes[idx] - chord_root) % 12 not in low_steps:
                        # Verse: auf den reduzierten Tonvorrat ausweichen (Nachbarton, zufällige Richtung)
                        nb = [i for i in (idx - 1, idx + 1) if 0 <= i < n_pool]
                        random.shuffle(nb)
                        idx = next((i for i in nb if (allowed_notes[i] - chord_root) % 12 in low_steps), idx)
                    # Gewichtige Töne (Viertel oder länger, oder auf Schlag 1 und 3) dürfen sich nicht
                    # mit dem Akkord reiben: Liegt der Ton einen Halbton neben einem Akkordton, rückt er
                    # einen Skalenschritt auf einen Akkordton. Spannungstöne mit Ganzton-Abstand (None,
                    # Sexte ...) und kurze Durchgangstöne bleiben, sonst wird die Linie zum Akkord-Arpeggio.
                    pc = allowed_notes[idx] % 12
                    if ((dur >= 4 or pos % 8 == 0) and pc not in chord_pcs
                            and any((pc - c) % 12 in (1, 11) for c in chord_pcs)):
                        # Erst die direkten Nachbarn; bei Skalen mit großen Tonabständen (Pentatonik)
                        # liegt der nächste Akkordton manchmal zwei Schritte entfernt.
                        for reach in (1, 2):
                            nb = [i for i in (idx - reach, idx + reach)
                                  if 0 <= i < n_pool and allowed_notes[i] % 12 in chord_pcs]
                            if nb:
                                fresh = [i for i in nb if i != last_idx]   # möglichst keine Tonwiederholung erzeugen
                                idx = random.choice(fresh or nb)
                                break
                    last_idx = idx
                    notes_to_play = [allowed_notes[idx]]
                    if "Triads" in mode and energy > 0.9:
                        notes_to_play += [allowed_notes[i] for i in (idx + 2, idx + 4) if i < n_pool]
                    generated_events.append((notes_to_play, dur))
                    pos += dur

        else:
            # --- ALTER ZUFALLS-MODUS (jede Note einzeln gewürfelt) ---
            step = 0
            last_note_index = len(allowed_notes) // 2 
        
            while step < total_steps:
                # --- 1. ZEIT-VARIABLEN ZUERST DEFINIEREN ---
                current_bar = step // steps_per_bar
                is_downbeat = (step % steps_per_bar == 0)
            
                # Energie für diesen Takt holen
                energy = get_arrangement_energy(current_bar, int(bars), arr_mode)            
                # --- 2. REGIE-CHECKS (BREATHING & MUTE) ---            
                # A: Melodic Breathing (Pause in jedem 3. Takt eines 4er Blocks)
                is_breathing = (current_bar % 4 == 2) and "Infinite" not in arr_mode
            
                # B: Mute-Matrix (Melodie schweigt bei niedriger Energie)
                is_muted = (energy < 0.6)

                if is_breathing or is_muted:
                    generated_events.append((None, 1))
                    step += 1
                    continue # Jetzt ist es sicher, weil die Variablen oben definiert wurden!

                # --- 3. ECHTE GENERIERUNG ---
                if random.random() < prob:
                    # Harmonischen Anker für DIESEN Takt finden (Harmony-Link)
                    if prog_data:
                        step_in_prog = prog_data[current_bar % len(prog_data)]
                        chord_root = get_chromatic_note(scale_notes, step_in_prog) % 12
                    else:
                        chord_root = NOTES.get(root, 0)

                    # Tonvorrat anpassen (Verse vs. Chorus)
                    if energy < 0.8:
                        allowed_steps = [0, 2, 4, 7, 9] if "Major" in scale else [0, 2, 3, 7, 8]
                    else:
                        allowed_steps = SCALES.get(scale, [0, 2, 4, 5, 7, 9, 11])

                    # Random Walk & Magnetismus
                    jump_range = 5 if ("Jazz" in genre or "Arp" in genre) else 2
                    new_index = max(0, min(len(allowed_notes)-1, last_note_index + random.randint(-jump_range, jump_range)))
                
                    # Kandidaten prüfen (Magnet-Logik)
                    # Der gewürfelte Ton hat Vorrang; die Nachbarn (in zufälliger Reihenfolge,
                    # damit es keinen Drall nach oben oder unten gibt) sind nur Ausweichtöne.
                    neighbors = [max(0, new_index-1), min(len(allowed_notes)-1, new_index+1)]
                    random.shuffle(neighbors)
                    candidates = [new_index] + neighbors

                    def _rel(c_idx):
                        return (allowed_notes[c_idx] % 12 - chord_root) % 12

                    best_note_idx = None
                    if is_downbeat:
                        # Auf der Eins zieht der Akkord-Grundton
                        best_note_idx = next((c for c in candidates if _rel(c) == 0), None)
                    if best_note_idx is None:
                        best_note_idx = next((c for c in candidates if _rel(c) == 0 or _rel(c) in allowed_steps), new_index)

                    new_index = best_note_idx
                    root_note = allowed_notes[new_index]
                    last_note_index = new_index
                
                    notes_to_play = [root_note]

                    # Polyphonie bei hoher Energie
                    try:
                        if "Triads" in mode and energy > 0.9:
                            notes_to_play.append(allowed_notes[new_index + 2])
                            notes_to_play.append(allowed_notes[new_index + 4])
                    except: pass

                    # Dauer
                    lengths = [1, 2] if energy < 0.8 else [2, 4]
                    duration = random.choice(lengths)
                    if step + duration > total_steps: duration = total_steps - step
                
                    generated_events.append((notes_to_play, duration))
                    step += duration
                else:
                    generated_events.append((None, 1))
                    step += 1
        

        # 4. MIDI schreiben
        ticks_per_16th = mid.ticks_per_beat // 4
        current_step = 0  # Wir müssen mitzählen, bei welchem Step wir sind
        last_event_tick = 0 # Wir merken uns den letzten geschriebenen Tick

        for notes, duration_steps in generated_events:
            # 1. Start-Zeitpunkt dieses Events mit Swing berechnen
            start_tick = current_step * ticks_per_16th
            if current_step % 2 != 0:
                start_tick += int(ticks_per_16th * (swing / 100) * 0.6)
                
            # 2. End-Zeitpunkt dieses Events mit Swing berechnen
            end_step = current_step + duration_steps
            end_tick = end_step * ticks_per_16th
            if end_step % 2 != 0:
                end_tick += int(ticks_per_16th * (swing / 100) * 0.6)

            # Die tatsächliche MIDI-Dauer
            duration_ticks = end_tick - start_tick
            
            if notes is not None:
                                # --- VELOCITY PAINTING (MELODY) ---
                # Wenn die Note auf der "Eins" startet, bekommt sie mehr Gewicht
                is_downbeat = (current_step % steps_per_bar == 0)
                base_vel = 112 if is_downbeat else 92
                
                vel = base_vel
                if human: vel += random.randint(-10, 10)
                vel = max(1, min(127, vel))
                
                # Delta für Note_ON berechnen (Abstand zum letzten Event)
                delta_on = start_tick - last_event_tick
                
                # Noten einschalten
                for i, n in enumerate(notes):
                    track.append(Message('note_on', note=n, velocity=vel, time=delta_on if i == 0 else 0, channel=1))
                
                # Noten ausschalten (nach duration_ticks)
                for i, n in enumerate(notes):
                    track.append(Message('note_off', note=n, velocity=0, time=duration_ticks if i == 0 else 0, channel=1))
                
                # Wir merken uns, dass wir jetzt am Ende dieser Note sind
                last_event_tick = start_tick + duration_ticks
            else:
                # Bei einer Pause schieben wir nur den Zeiger weiter
                pass
            
            # Den Schritt-Zähler erhöhen
            current_step += duration_steps
        mid.save(mid_path)        
        
        # --- 5. MASTER-BUFFER AUDIO (MIT SICHERHEITS-LEITPLANKEN) ---
        sr = 44100
        sec_per_16th = (60 / bpm) / 4
        total_duration_sec = total_steps * sec_per_16th
        # Großzügiger Buffer (1s extra) gegen End-of-File Fehler
        audio_buffer = np.zeros(int((total_duration_sec + 1.0) * sr))
        T_master = np.linspace(0, len(audio_buffer)/sr, len(audio_buffer), False)
        
        current_step = 0
        for notes, duration_steps in generated_events:
            # Gleiches Timing wie im MIDI
            start_time = current_step * sec_per_16th
            if current_step % 2 != 0:
                start_time += (sec_per_16th * (swing / 100) * 0.6)
            
            dur_midi_sec = duration_steps * sec_per_16th
            release_time = 0.4 # Puffer für das Ausklingen
            dur_calc_sec = dur_midi_sec + release_time 

            if notes and len(notes) > 0:
                # LEITPLANKE: Sample-genaue Indizes & Buffer-Limitierung
                start_idx = int(np.round(start_time * sr))
                num_samples = int(np.round(dur_calc_sec * sr))
                end_idx = min(start_idx + num_samples, len(audio_buffer))
                
                if start_idx < end_idx:
                    t_slice = T_master[start_idx:end_idx]
                    mixed_wave = np.zeros_like(t_slice)
                    
                    # LEITPLANKE: Headroom (0.2 statt 0.3) gegen Übersteuerung im Mix
                    gain_per_note = 0.2 / len(notes)
                    
                    for n in notes:
                        freq = 440.0 * (2.0 ** ((n - 69) / 12.0))
                        mixed_wave += get_waveform(freq, t_slice, sound) * gain_per_note
                    
                    # LEITPLANKE: Saubere Hüllkurve
                    clean_note = apply_envelope(mixed_wave, attack=0.03, mode="exponential")
                    
                    # Nur so viel addieren, wie in den Slice passt
                    audio_buffer[start_idx:end_idx] += clean_note[:(end_idx - start_idx)]

            current_step += duration_steps
        # --- 6. FINALISIERUNG (MASTERING) ---
        if np.max(np.abs(audio_buffer)) > 0:
            # Normalisierung & Soft-Clipping gegen das "Abschmieren"
            audio_buffer = audio_buffer / np.max(np.abs(audio_buffer))
            audio_buffer = soft_clipper(audio_buffer)
            audio_buffer = audio_buffer * 0.85

        sf.write(wav_path, audio_buffer, sr)
        return wav_path, mid_path

    except Exception as e:
        _report_error("Melody Error", e)
        return None, None   
# ==========================================
# TEIL 2: DRUM GENERATOR (NEU!)
# ==========================================
@_seeded
def create_drum_files(genre, bpm, bars, density, swing, human, output_dir,time_sig="4/4",arr_mode="♾️ Infinite Loop"):
    try:
        # 1. Grund-Setup
        os.makedirs(output_dir, exist_ok=True)
                # --- DIESE ZEILE HINZUFÜGEN ---
        steps_per_bar = 12 if ("3/4" in time_sig or "6/8" in time_sig) else 16
        total_steps = int(bars) * steps_per_bar
        # -----
        sr = 44100
        print(f" drum Generating Hybrid Drums: {genre}...")
        
        wav_path = os.path.join(output_dir, "generated_drums.wav")
        mid_path = os.path.join(output_dir, "generated_drums.mid")
        
        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)
        track.append(MetaMessage('track_name', name='Drums (Ch 10)'))
        track.append(MetaMessage('set_tempo', tempo=int(60000000 / bpm)))
        
        # MIDI Nummern (Vollständiges Pro-Set)
        KICK, RIMSHOT, SNARE, CLAP, SNARE2 = 36, 37, 38, 39, 40
        CHH, OHH, RIDE, CRASH = 42, 46, 51, 49
        TOM_L, TOM_M, TOM_H = 45, 47, 50
                
        # --- 2. DIE SYNTHESE-REZEPTE (Müssen oben stehen!) ---
        def make_kick():
            t = np.linspace(0, 0.2, int(sr*0.2), False)
            # Nutzt apply_envelope (muss im Script global definiert sein)
            return apply_envelope(0.8 * np.sin(2 * np.pi * (150 * np.exp(-15 * t)) * t), 0.005, 0.1)
            
        def make_snare():
            t = np.linspace(0, 0.15, int(sr*0.15), False)
            return apply_envelope(0.5 * np.random.uniform(-1, 1, len(t)), 0.01, 0.1)
            
        def make_clap():
            t = np.linspace(0, 0.02, int(sr*0.02), False)
            noise = np.random.uniform(-1, 1, len(t))
            impulse = apply_envelope(noise, 0.002, 0.01)
            return np.concatenate([impulse, impulse * 0.7, impulse * 0.5])

        def make_hat(long=False):
            dur = 0.3 if long else 0.05
            t = np.linspace(0, dur, int(sr*dur), False)
            return apply_envelope(0.3 * np.random.uniform(-1, 1, len(t)), 0.005, dur*0.8)
        # --- ERWEITERTE SYNTHESE-REZEPTE ---
        def make_snare2():
            # Kurze, trockene Ghost-Snare
            t = np.linspace(0, 0.08, int(sr*0.08), False)
            noise = np.random.uniform(-1, 1, len(t))
            return apply_envelope(0.4 * noise, 0.005, 0.05)

        def make_tom(freq_start):
            # Toms sind wie Kicks, nur höher und länger
            t = np.linspace(0, 0.3, int(sr*0.3), False)
            freq_env = freq_start * np.exp(-10 * t)
            wave = np.sin(2 * np.pi * freq_env * t)
            return apply_envelope(0.7 * wave, 0.01, 0.2)

        def make_cymbal(duration, vol):
            # Crash und Ride nutzen gefiltertes Rauschen
            t = np.linspace(0, duration, int(sr*duration), False)
            noise = np.random.uniform(-1, 1, len(t))
            # Ein simpler Hochpass-Effekt: Wir nehmen nur die Differenzen der Samples
            high_pass_noise = np.diff(noise, prepend=0)
            return apply_envelope(vol * high_pass_noise, 0.01, duration*0.7)

        # --- 3. HYBRID LOGIK (Samples laden oder Synthese) ---
        samples_path = SAMPLES_DIR
        sample_map = {
            36: "bagueDEV_kick.wav", 37: "bagueDEV_rimshot.wav", 38: "bagueDEV_snare.wav",
            39: "bagueDEV_clap.wav", 40: "bagueDEV_snare2.wav", 42: "bagueDEV_hh_closed.wav",
            45: "bagueDEV_tom_low.wav", 46: "bagueDEV_hh_open.wav", 47: "bagueDEV_tom_mid.wav",
            49: "bagueDEV_crash.wav", 50: "bagueDEV_tom_high.wav", 51: "bagueDEV_ride.wav"
        }
        
        def load_hybrid_sample(midi_note, fallback_func):
            filename = sample_map.get(midi_note)
            if filename:
                path = os.path.join(SAMPLES_DIR, filename)
                if os.path.exists(path):
                    try:
                        audio, _ = librosa.load(path, sr=sr)
                        return audio
                    except Exception as e:
                        log.warning("Drum sample %s could not be loaded, using the synthetic sound: %s", filename, e)
            return fallback_func()
        # Jetzt alle Sounds in ein Dictionary laden
        # Alle 12 Sounds laden (Hybrid: Datei oder Synthese)
        drum_sounds = {
            36: load_hybrid_sample(36, make_kick),
            37: load_hybrid_sample(37, lambda: apply_envelope(np.random.uniform(-0.5, 0.5, int(sr*0.02)), 0.002, 0.01)),
            38: load_hybrid_sample(38, make_snare),
            39: load_hybrid_sample(39, make_clap),
            40: load_hybrid_sample(40, make_snare2),
            42: load_hybrid_sample(42, lambda: make_hat(False)),
            45: load_hybrid_sample(45, lambda: make_tom(120)), # Low Tom
            46: load_hybrid_sample(46, lambda: make_hat(True)),
            47: load_hybrid_sample(47, lambda: make_tom(180)), # Mid Tom
            49: load_hybrid_sample(49, lambda: make_cymbal(1.5, 0.4)), # Crash
            50: load_hybrid_sample(50, lambda: make_tom(250)), # High Tom
            51: load_hybrid_sample(51, lambda: make_cymbal(0.6, 0.3))  # Ride
        }
        # --- 3b. SOUND-VARIANTEN (Round-Robin gegen Maschinengewehr-Effekt) ---
        # Jeder Drumsound bekommt 3 leicht verstimmte Varianten (0 / +35 / -40 Cent).
        # Beim Rendern rotieren die Hits durch die Varianten — klingt menschlicher,
        # kostet einmalig Millisekunden beim Laden.
        def _detune(audio, cents):
            try:
                a = np.asarray(audio, dtype=np.float32)
                if len(a) < 16:
                    return a
                factor = 2.0 ** (cents / 1200.0)
                n = max(8, int(len(a) / factor))
                old_idx = np.linspace(0, len(a) - 1, len(a))
                new_idx = np.linspace(0, len(a) - 1, n)
                return np.interp(new_idx, old_idx, a).astype(np.float32)
            except Exception:
                return np.asarray(audio, dtype=np.float32)
        drum_variants = {}
        for _note, _snd in drum_sounds.items():
            try:
                _base = np.asarray(_snd, dtype=np.float32)
                drum_variants[_note] = [_base, _detune(_base, 35), _detune(_base, -40)]
            except Exception:
                drum_variants[_note] = [np.asarray(_snd)]
        drum_rr = {}
        # --- SYNTHPOP / 80s PATTERN POOL ---
        # --- SYNTHPOP / 80s KICK POOL (Einfache Listen) ---
        sp_pool = [
            [0, 4, 8, 12],       # 1. Four-on-the-Floor
            [0, 6, 8, 14],       # 2. Syncopated (Take On Me Style)
            [0, 4, 8, 10, 12],   # 3. Gated Drive
            [0, 10, 14],         # 4. Modern Pop Pulse
            [0, 2, 4, 8, 10, 12] # 5. Energetic Disco
        ]
        
        # --- TECHNO PATTERN POOL (Berlin & Detroit Styles) ---
        # k = Kick-Positionen (meist 4/4), p = Percussion/Rimshot
        tech_pool = [
            {"name": "Minimal", "k": [0, 4, 8, 12], "p": [3, 11]},
            {"name": "Driving", "k": [0, 4, 8, 12], "p": [2, 6, 10, 14]},
            {"name": "Industrial", "k": [0, 4, 8, 12], "p": [0, 4, 8, 12]}, # Ride-Akzente
            {"name": "Peaktime", "k": [0, 1, 4, 5, 8, 9, 12, 13], "p": [2, 6, 10, 14]} # Double-Kick Logic
        ]

        # --- HOUSE PATTERN POOL (Chicago & Deep House) ---
        # c = Ghost-Claps, s = Shaker/Rim
        house_pool = [
            {"name": "Classic Jack", "c": [4, 12, 15], "s": [2, 6, 10, 14]},
            {"name": "Deep Soul", "c": [4, 12], "s": [3, 7, 11, 15]},
            {"name": "Tech-House", "c": [4, 12, 7], "s": [1, 3, 5, 9, 11, 13]},
            {"name": "Disco-Pump", "c": [4, 12], "s": [0, 2, 4, 6, 8, 10, 12, 14]}
        ]

        # Phrasen-Paare: garantiert A != B (sonst AAAAAAAA statt ABAB).
        # (Vor allen Genre-Auswahlen definiert, da überall genutzt.)
        def pick_pair(pool):
            a = random.choice(pool)
            if len(pool) < 2:
                return a, a
            b = random.choice(pool)
            guard = 0
            while b == a and guard < 8:
                b = random.choice(pool)
                guard += 1
            return a, b

        # Auswahl basierend auf Genre (Paare garantiert verschieden)
        if "Techno" in genre:
            tp_a, tp_b = pick_pair(tech_pool)
        elif "House" in genre:
            hp_a, hp_b = pick_pair(house_pool)
        # --- JAZZ COMPING POOL (UAH & Drumeo Figuren) ---
        # Snare-Akzente, die unabhängig vom Ride laufen
        jazz_comp_pool = [
            [6], [14], [6, 14], [3, 4], [11], [3, 11], [] # Verschiedene Offbeat-Figuren
        ]
        
        # --- LATIN PATTERNS (UAH Audition Standard) ---
        bossa_rim = [0, 3, 6, 10, 13] # Die klassische Bossa-Clave
        samba_kick = [0, 3, 4, 7, 8, 11, 12, 15] # Der treibende Samba-Puls
        
        # --- ORIENTAL MAQAM POOL (Dum/Tek Logik) ---
        # k = Dum (Kick), s = Tek (Rimshot)
        ori_pool = [
            {"name": "Maqsum", "k": [0, 10], "s": [4, 8, 12]}, 
            {"name": "Saidi",  "k": [0, 8, 9], "s": [4, 12]},
            {"name": "Baladi", "k": [0, 2, 8, 10], "s": [4, 12]},
            {"name": "Malfuf", "k": [0, 8], "s": [3, 6, 11, 14]}
        ]
        # Wahl für diesen Durchlauf
        op = random.choice(ori_pool)
        
        # --- DnB PATTERN POOL (Simon V inspiriert) ---
        dnb_pool = [
            [0, 10],             # 1. Classic 2-Step
            [0, 3, 10],          # 2. The Roller
            [0, 2, 10],          # 3. The Double
            [0, 7, 9],           # 4. Syncopated Jungle
            [0, 3, 7, 11],       # 5. Amen Style
            [0, 8, 10],          # 6. Broken Step
            [0, 11],             # 7. Minimalist
            [0, 3, 10, 14]       # 8. The Heavy
        ]
        # --- HIP-HOP POOL (Boom Bap / Lo-Fi) ---
        hp_pool = [
            [0, 10], [0, 3, 10], [0, 11], [0, 3, 7, 11],
            [0, 7, 10], [0, 3, 6, 10], [0, 10, 12], [3, 10],
        ]
        # --- TRAP POOL (Modern Halftime Patterns) ---
        tp_pool = [
            [0, 6, 11],       # Der Standard "Bounce"
            [0, 9, 14],       # Aggressives Ende
            [0, 6, 13, 14],   # Rolling Kicks
            [0, 11, 13],      # Minimal & Deep
            [0, 7, 13],       # Offbeat Bounce
            [0, 6, 10, 14],   # Driving Halftime
            [0, 3, 11],       # Sparse Dark
            [6, 11, 14],      # Kickless Start
        ]

        # Wähle die Muster basierend auf dem gewählten Genre
        # (Ein if/elif-Zweig je Genre, damit kein Pool überschrieben wird)
        if "Synthpop" in genre:
            p_a, p_b = pick_pair(sp_pool)
        elif "Trap" in genre:
            p_a, p_b = pick_pair(tp_pool)
        elif "HipHop" in genre:
            p_a, p_b = pick_pair(hp_pool)
        elif "DnB" in genre:
            p_a, p_b = pick_pair(dnb_pool)
        else: # Default (u.a. Random): HipHop-Pattern als Basis
            p_a, p_b = pick_pair(hp_pool)
            
       # --- REGGAE PATTERN POOL (One-Drop, Steppers, Rockers) ---
        re_pool = [
            {"k": [8], "s": [8]},              # 1. Pure One-Drop (Kick/Snare nur auf 8)
            {"k": [0, 4, 8, 12], "s": [8]},     # 2. Steppers (Kick auf jedem Viertel)
            {"k": [0, 3, 8, 11], "s": [4, 12]}, # 3. Rockers (Syncopated Kick, Snare auf 4/12)
            {"k": [8, 10], "s": [8]}           # 4. Dub Style (One-Drop mit extra Kick)
        ]
        # Wir wählen für diesen "Generate"-Klick ein festes Muster aus
        rp = random.choice(re_pool)

        # --- AMEN BREAK POOL (DnB/Breakbeat: "phat" 4 + Ghost-Snares + Break-Feeling) ---
        amen_pool = [
            {"name": "Classic Amen",  "kick": [0, 6, 10, 12], "snare": [4, 12], "ghost": [6, 11, 14], "open": [10]},
            {"name": "Jungle Roller", "kick": [0, 3, 10, 12], "snare": [4, 12], "ghost": [5, 11, 14], "open": [6, 14]},
            {"name": "Techstep",      "kick": [0, 7, 10],     "snare": [4, 12], "ghost": [9, 11, 13], "open": [2]}
        ]
        # Zwei feste Amen-Varianten für diesen Klick (wechseln pro Takt)
        amen_a, amen_b = pick_pair(amen_pool)

        # --- DnB-GROOVE: Zutaten, die über eine 8-Takt-Sektion gleich bleiben ---
        # Hats als festes Muster statt Münzwurf pro Schritt: jede 16tel-Position
        # (0-3 im Viertel) hat ein Gewicht; Density/Energie legen die Schwelle fest,
        # ab der eine Position mitspielt. So dünnt Density das Muster aus,
        # ohne dass die Löcher in jedem Takt woanders sitzen.
        dnb_hat_pool = [
            {"name": "Rolling 16ths", "w": [1.0, 0.35, 0.8, 0.3]},
            {"name": "Shuffle",       "w": [1.0, 0.15, 0.8, 0.6]},
            {"name": "Straight 8ths", "w": [1.0, 0.1, 0.85, 0.1]},
        ]
        dnb_ghost_pool = [[7], [9], [7, 9], [15], [9, 15], [7, 15]]   # leise Snares um die Hauptschläge
        dnb_open_pool = [[10], [14], [6, 14], [2, 10]]                # offene Hat (Offbeats)

        def roll_dnb_section():
            return random.choice(dnb_hat_pool), random.choice(dnb_ghost_pool), random.choice(dnb_open_pool)
        dnb_hat, dnb_ghost, dnb_open = roll_dnb_section()
        is_dnb = "DnB" in genre

        # Hat-Muster für Genres ohne eigene Hat-Logik: (Note, Velocity, Gewicht) je 16tel-Position
        fallback_hats = {
            "House":  [(42, 70, 0.45), (42, 55, 0.25), (46, 105, 1.0), (42, 60, 0.3)],   # offene Hat auf dem Offbeat
            "Techno": [(42, 90, 0.7),  (42, 60, 0.3),  (46, 100, 1.0), (42, 70, 0.4)],
            "":       [(42, 95, 1.0),  (42, 50, 0.15), (42, 75, 0.8),  (42, 50, 0.15)],  # Standard: 8tel
        }
        hat_table = next(v for k, v in fallback_hats.items() if k in genre)

        # --- 4. GENRE LOGIK (Vollständiges Drumset & Transition-Logik) ---
        total_steps = int(bars) * steps_per_bar
        events = [] 
        prob = density / 100.0

        for bar in range(int(bars)):
            bar_start = bar * steps_per_bar
            
            # --- 1. REGIE: ENERGIE-FAHRPLAN ---
            energy = get_arrangement_energy(bar, int(bars), arr_mode)
            energy_prev = get_arrangement_energy(bar-1, int(bars), arr_mode) if bar > 0 else 0
            energy_next = get_arrangement_energy(bar+1, int(bars), arr_mode) if bar < int(bars)-1 else 1.0
            
            # --- 1b. PHRASEN-WECHSEL: alle 2 Takte frische Muster würfeln,
            # damit lange Loops nicht ABABABAB klingen (gleiche Engine-Reihenfolge
            # wie unten: Breakbeat vor DnB prüfen!)
            # DnB: der 2-Takt-Groove bleibt eine ganze 8-Takt-Sektion stehen (A B A B'),
            # erst danach wird (mit 50 %) neu gewürfelt.
            if is_dnb:
                reroll = bar > 0 and bar % 8 == 0 and random.random() < 0.5
                if reroll:
                    dnb_hat, dnb_ghost, dnb_open = roll_dnb_section()
            else:
                reroll = bar > 0 and bar % 2 == 0 and random.random() < 0.6
            if reroll:
                if "Techno" in genre:
                    tp_a, tp_b = pick_pair(tech_pool)
                elif "House" in genre:
                    hp_a, hp_b = pick_pair(house_pool)
                elif "Synthpop" in genre:
                    p_a, p_b = pick_pair(sp_pool)
                elif "Trap" in genre:
                    p_a, p_b = pick_pair(tp_pool)
                elif "HipHop" in genre:
                    p_a, p_b = pick_pair(hp_pool)
                elif "Breakbeat" in genre:
                    amen_a, amen_b = pick_pair(amen_pool)
                elif "DnB" in genre:
                    p_a, p_b = pick_pair(dnb_pool)
                elif "Reggae" in genre:
                    rp = random.choice(re_pool)
                elif "Oriental" in genre:
                    op = random.choice(ori_pool)

            # --- 2. ÜBERGANGS-ERKENNUNG ---
            # Ein Sprung passiert, wenn wir von leise auf laut wechseln (z.B. Verse -> Chorus)
            is_energy_jump = (energy >= 0.8 and energy_prev < 0.8)
            # Ein Build-up ist der Takt DIREKT vor einem Energie-Sprung
            is_build_up = (energy_next >= 0.8 and energy < 0.8)
            # Ein normaler Fill-Takt alle 8 Bars (falls kein Build-up ist)
            is_fill_bar = (bar % 8 == 7 and not is_build_up)
            
            # 3. IMPACT (Crash-Becken auf der "Eins" bei Sektions-Starts)
            if is_energy_jump or bar == 0:
                events.append((bar_start, 49, 127)) # Max Power Crash

            # Ride-Becken statt Hi-Hat bei hoher Energie (Refrain-Feeling)
            # (im Infinite-Loop ist die Energie immer 1.0 – dort bleibt es bei Hi-Hats)
            use_ride = (energy >= 0.8) and "Infinite" not in arr_mode
            # Jazz: eine Comping-Figur pro Takt
            current_comp = random.choice(jazz_comp_pool) if "Jazz" in genre else []
            # DnB: jeder 4. Takt ist der Turnaround (Extra-Kick auf der 4-und, Ghost davor)
            is_turnaround = is_dnb and bar % 4 == 3

            # --- 4. STEP-SCHLEIFE (Rhythmus-Generierung) ---
            for step_in_bar in range(steps_per_bar):
                step = bar_start + step_in_bar
                
                # A: THE SILENT GAP (Kurze Stille vor dem Knall)
                # In den letzten 4 Steps vor einem Energie-Sprung (Drop) herrscht Stille
                if is_build_up and step_in_bar >= (steps_per_bar - 4):
                    continue 

                # B: BUILD-UP LOGIK (Snare-Rolls vor dem Drop)
                if is_build_up:
                    # Snare beschleunigt: Schlägt auf 0, 4, 8, 10, 12, 13, 14, 15
                    roll_steps = [0, 4, 8, 10, 12, 13, 14, 15]
                    if step_in_bar in roll_steps:
                        v_roll = int(85 + (step_in_bar * 2.5)) # Wird lauter (Crescendo)
                        events.append((step, 38, v_roll))
                    # Schnelle Hi-Hats dazu
                    if step_in_bar % 2 == 0:
                        events.append((step, 42, 90))
                    continue # Rest des normalen Patterns überspringen

                # C: ÜBERGANGS-FILLS (Toms alle 8 Takte, bei Breakbeat Amen-Rat-a-tat)
                if is_fill_bar and step_in_bar >= (steps_per_bar - 4):
                    if is_dnb:
                        # Snare-Roll am Taktende (Crescendo) statt Toms
                        events.append((step, 38, int(95 + (step_in_bar - 12) * 8)))
                    elif energy >= 0.4:
                        tom_note = 50 if step_in_bar == 12 else (47 if step_in_bar == 14 else 45)
                        if random.random() < 0.8:
                            events.append((step, tom_note, random.randint(90, 110)))
                    continue 

                # --- D: GENRE-LOGIK (Die Arbeitstiere) ---
                # 1. TECHNO
                if "Techno" in genre:
                    current_tp = tp_a if bar % 2 == 0 else tp_b
                    if step_in_bar in current_tp["k"] and energy >= 0.3:
                        events.append((step, 36, 125 if step_in_bar == 0 else 115))
                    if step_in_bar in current_tp["p"] and energy >= 0.6 and random.random() < prob:
                        events.append((step, 37, random.randint(80, 100)))
                    # Dezenter Clap auf 2 und 4
                    if step_in_bar in [4, 12] and energy >= 0.5:
                        events.append((step, 39, 95))

                # 2. HOUSE
                elif "House" in genre:
                    current_hp = hp_a if bar % 2 == 0 else hp_b
                    if step_in_bar in [0, 4, 8, 12] and energy >= 0.3:
                        events.append((step, 36, 118))
                    if step_in_bar in current_hp["c"] and energy >= 0.5:
                        events.append((step, 39, 120 if step_in_bar in [4, 12] else 75))
                    if step_in_bar in current_hp["s"] and energy >= 0.6 and random.random() < prob:
                        events.append((step, 37, random.randint(75, 95)))
                    # Ghost-Clap als Variation (nicht, wenn das Muster dort schon einen Clap hat).
                    # Die offene Hat kommt aus dem festen Hat-Muster weiter unten.
                    if (step_in_bar == 15 and 15 not in current_hp["c"] and energy >= 0.6
                            and random.random() < prob * 0.4):
                        events.append((step, 39, random.randint(50, 65)))

                # 3. SYNTHPOP
                elif "Synthpop" in genre:
                    current_sp = p_a if bar % 2 == 0 else p_b
                    if step_in_bar in current_sp and energy >= 0.3:
                        events.append((step, 36, 122 if step_in_bar == 0 else 110))
                    if step_in_bar in [4, 12] and energy >= 0.5:
                        events.append((step, 38, 115))
                        events.append((step, 39, 85))
                    # Offbeat-Hats (80s-Drive) + offene Hat als Akzent
                    if step_in_bar % 2 == 1 and energy >= 0.5 and random.random() < prob * 0.7:
                        events.append((step, 42, random.randint(60, 85)))
                    if step_in_bar == 14 and energy >= 0.7 and random.random() < prob * 0.3:
                        events.append((step, 46, 90))

                # 4a. DNB / BREAKBEAT (Amen Break Engine: Ghosts, Flam, "phat" 4)
                elif "Breakbeat" in genre:
                    current_amen = amen_a if bar % 2 == 0 else amen_b
                    if is_turnaround:
                        current_amen = dict(current_amen,
                                            kick=sorted(set(current_amen["kick"]) | {14}),
                                            ghost=sorted(set(current_amen["ghost"]) | {15}))
                    # Kick (die 4 wird von der Snare unterstützt = "phat")
                    if step_in_bar in current_amen["kick"] and energy >= 0.3:
                        events.append((step, 36, 122 if step_in_bar == 0 else 108))
                    # Snare auf 2 und 4
                    if step_in_bar in current_amen["snare"] and energy >= 0.5:
                        events.append((step, 38, 118))
                    # Ghost-Snares (leise, Dichte-gesteuert)
                    if step_in_bar in current_amen["ghost"] and energy >= 0.6 and random.random() < prob:
                        events.append((step, 40, random.randint(35, 55)))
                    # Flam/Ghost direkt vor der 4 (Schritt 11)
                    if (step_in_bar == 11 and 11 not in current_amen["ghost"] and energy >= 0.6
                            and random.random() < 0.6):
                        events.append((step, 40, 45))
                    # Hats als Muster mit Akzenten + Open Hats auf Offbeats
                    if dnb_hat["w"][step_in_bar % 4] > 1.0 - (prob * energy):
                        v_hat = 118 if step_in_bar % 4 == 0 else (55 if step_in_bar % 4 == 2 else 80)
                        n_hat = 46 if step_in_bar in current_amen["open"] else 42
                        events.append((step, n_hat, v_hat))

                # 4. DRUM AND BASS (Rolling & Simon V)
                elif "DnB" in genre:
                    current_kick_pattern = p_a if bar % 2 == 0 else p_b
                    if is_turnaround:
                        current_kick_pattern = sorted(set(current_kick_pattern) | {14})
                    if step_in_bar in current_kick_pattern and energy >= 0.3:
                        events.append((step, 36, 120 if step_in_bar == 0 else 105))
                    if step_in_bar in [4, 12] and energy >= 0.5:
                        events.append((step, 38, 120)) 
                    # Ghost-Snares (leise, feste Positionen pro Sektion; ab Density 40)
                    if energy >= 0.6 and prob >= 0.4 and (step_in_bar in dnb_ghost or (is_turnaround and step_in_bar == 15)):
                        events.append((step, 40, random.randint(35, 55)))
                    # Rolling Hats als festes Muster (Density dünnt aus)
                    pos_in_quad = step_in_bar % 4
                    dnb_v_pattern = [115, 45, 85, 40]
                    if dnb_hat["w"][pos_in_quad] > 1.0 - (prob * energy):
                        n_hat = 46 if step_in_bar in dnb_open else 42
                        events.append((step, n_hat, dnb_v_pattern[pos_in_quad]))

                # 5. HIPHOP / TRAP
                elif "HipHop" in genre or "Trap" in genre:
                    current_pattern = p_a if bar % 2 == 0 else p_b
                    if step_in_bar in current_pattern and energy >= 0.3:
                        events.append((step, 36, 122 if step_in_bar == 0 else 110))
                    pos_snare = [8] if "Trap" in genre else [4, 12]
                    if step_in_bar in pos_snare and energy >= 0.5:
                        events.append((step, 39 if "Trap" in genre else 38, 115))
                    # Ghost-Snare (leise, Dichte-gesteuert)
                    if step_in_bar == 14 and energy >= 0.6 and random.random() < prob * 0.5:
                        events.append((step, 40, random.randint(35, 55)))
                    # Hi-Hats: HipHop 8tel mit Akzenten, Trap dichter mit Offbeat-Öffnung
                    if "Trap" in genre:
                        if step_in_bar % 2 == 0 and energy >= 0.4 and random.random() < prob:
                            v_hat = 112 if step_in_bar % 4 == 0 else (70 if step_in_bar % 4 == 2 else 88)
                            n_hat = 46 if (step_in_bar == 14 and random.random() < 0.35) else 42
                            events.append((step, n_hat, v_hat))
                        elif step_in_bar % 2 == 1 and energy >= 0.8 and random.random() < prob * 0.4:
                            events.append((step, 42, random.randint(55, 75)))
                    else:
                        if step_in_bar % 2 == 0 and energy >= 0.4 and random.random() < prob:
                            v_hat = 108 if step_in_bar % 4 == 0 else 78
                            n_hat = 46 if (step_in_bar == 14 and random.random() < 0.3) else 42
                            events.append((step, n_hat, v_hat))

                # 6. REGGAE / ORIENTAL / JAZZ (Analog zu den Vorlagen weiterführen...)
                # ... (Hier deine restlichen Genres einfügen) ...
                # 6. REGGAE
                elif "Reggae" in genre and "Reggaeton" not in genre:
                    if step_in_bar in rp["k"] and energy >= 0.3:
                        events.append((step, 36, 120))
                    if step_in_bar in rp["s"] and energy >= 0.5:
                        events.append((step, 37, 115))
                    # 8tel-Hats mit Betonung auf dem Offbeat (Skank-Feeling)
                    if step_in_bar % 2 == 0 and energy >= 0.4 and [0.9, 1.0][step_in_bar % 4 == 2] > 1.0 - prob:
                        events.append((step, 42, 100 if step_in_bar % 4 == 2 else 65))
                # 8. ORIENTAL
                elif "Oriental" in genre:
                    if step_in_bar in op["k"] and energy >= 0.3:
                        events.append((step, 36, 122))
                    if step_in_bar in op["s"] and energy >= 0.5:
                        events.append((step, 37, 110))
                        
                # --- JAZZ & LATIN (UAH & Drumeo Professional) ---
                elif "Jazz" in genre:
                    # 1. TAKT-ABHÄNGIGE MUSTER DEFINIEREN
                    if steps_per_bar == 12: # --- JAZZ WALTZ (3/4) ---
                        ride_pattern = [0, 4, 5, 8, 9]  # "Dinn - ding-da - ding-da"
                        hat_pattern  = [4, 8]           # Chick auf 2 und 3
                        kick_feather = [0, 4, 8]        # Leises Feathering auf den Vierteln
                    else: # --- CLASSIC SWING (4/4) ---
                        ride_pattern = [0, 6, 8, 14]    # "Dinn - ding-da - Dinn - ding-da"
                        hat_pattern  = [4, 12]          # Chick auf 2 und 4
                        kick_feather = [0, 4, 8, 12]    # Leises Feathering auf allen Vierteln

                    # 2. RIDE-BECKEN (Der Dirigent)
                    if step_in_bar in ride_pattern and energy >= 0.2:
                        # Akzent auf den Hauptschlägen (0, 8 bzw. 0, 4)
                        is_main_beat = step_in_bar in [0, 8, 4]
                        v_ride = 112 if is_main_beat else 88
                        events.append((step, 51, v_ride))

                    # 3. HI-HAT PEDAL (Der Herzschlag / UAH Gesetz)
                    if step_in_bar in hat_pattern and energy >= 0.4:
                        events.append((step, 42, 95))

                    # 4. KICK-FEATHERING (Die unsichtbare Stütze)
                    if step_in_bar in kick_feather:
                        # Jazz-Kicks sind extrem leise (30-45), außer bei Akzenten
                        v_kick = random.randint(30, 45)
                        events.append((step, 36, v_kick))
                    
                    # 5. INDEPENDENT COMPING (Snare-Variationen)
                    # Wir wählen für jeden Takt eine Figur aus dem UAH-Pool
                    if step_in_bar in current_comp and energy >= 0.6 and random.random() < prob:
                        # Akzentuierte Snare (38) oder Snare 2 (40) für Ghost-Vibe
                        events.append((step, random.choice([38, 40]), random.randint(75, 100)))

                # 9. REGGAETON (Dembow: Samba-Kick-Puls + Bossa-Rim)
                elif "Reggaeton" in genre:
                    if step_in_bar in samba_kick and energy >= 0.3:
                        events.append((step, 36, 118))
                    if step_in_bar in bossa_rim and energy >= 0.5 and random.random() < prob:
                        events.append((step, 37, 100))
                    if step_in_bar in [4, 12] and energy >= 0.6:
                        events.append((step, 39, 115))
                    # Hats auf den Offbeats (Dembow-Feeling)
                    if step_in_bar % 2 == 1 and random.random() < (prob * energy):
                        events.append((step, 42, 90))

                # 10. DEFAULT (Random/Ambient & Unbekannte): Solider Basic 4/4
                else:
                    if step_in_bar in [0, 4, 8, 12] and energy >= 0.3:
                        events.append((step, 36, 118))
                    if step_in_bar in [4, 12] and energy >= 0.5:
                        events.append((step, 38, 110))

                # --- E: GLOBAL FALLBACK HI-HATS ---
                # Dieser Block greift nur, wenn das Genre KEINE eigene Hut-Logik hat
                genres_with_custom_hats = ["Jazz", "DnB", "Reggae", "Reggaeton", "Trap", "HipHop", "Synthpop"]
                
                if not any(g in genre for g in genres_with_custom_hats):
                    hat_n, hat_v, hat_w = hat_table[step_in_bar % 4]
                    if hat_w > 1.0 - (prob * energy):
                        # Ride (51) statt Closed Hat im Refrain eines Arrangements – nur auf den 8teln
                        if use_ride and hat_n == 42 and "House" not in genre and "Techno" not in genre:
                            hat_n = 51 if step_in_bar % 2 == 0 else None
                        if hat_n is not None:
                            events.append((step, hat_n, int(hat_v * (0.6 + 0.4 * energy))))
        # Kick-Positionen für den Bass merken (Full Loop koppelt den Bass daran)
        _tls.kick_steps = sorted({st for st, note, vel in events if note == 36 and vel >= 60})

        # --- 5. MIDI & AUDIO TIMING (Swing & Humanize) ---
        timeline = {}
        for step, note, vel in events:
            if step not in timeline: timeline[step] = []
            timeline[step].append((note, vel))
            
        ticks_per_16th = mid.ticks_per_beat // 4
        sec_per_16th = (60 / bpm) / 4
        audio_buffer = np.zeros(int((total_steps + 2) * sec_per_16th * sr))
        last_tick = 0
        
        for step in range(total_steps):
            current_tick = step * ticks_per_16th
            time_in_sec = step * sec_per_16th

            # HUMANIZE-TIMING (Drums): minimale MIDI-Streuung
            if human and step % 2 == 1:
                current_tick = max(0, current_tick + random.randint(-6, 6))
            
            # SWING
            if step % 2 != 0:
                shift_ticks = int(ticks_per_16th * (swing / 100) * 0.6)
                current_tick += shift_ticks
                time_in_sec += (sec_per_16th * (swing / 100) * 0.6)
            
            if step in timeline:
                delta = current_tick - last_tick
                start_sample = int(time_in_sec * sr)
                
                first = True
                for note, vel in timeline[step]:
                    # MIDI
                    # --- VELOCITY PAINTING (DRUMS) ---
                    pos_in_bar = step % steps_per_bar
                    if pos_in_bar == 0: vel += 15 # Die "1" betonen
                    elif pos_in_bar == (steps_per_bar // 2): vel += 8 # Die "3" betonen
                    
                    if human: 
                        vel = max(1, min(127, vel + random.randint(-12, 12)))
                    d = delta if first else 0
                    
                                    # --- LEITPLANKE: IMMER ABSICHERN ---
                # Diese Zeile sorgt dafür, dass der Wert NIEMALS über 127 geht
                    vel = max(0, min(127, vel))
                # -----------------------------------
                    track.append(Message('note_on', note=note, velocity=vel, time=max(0, d), channel=9))
                    track.append(Message('note_off', note=note, velocity=0, time=0, channel=9))
                    
                    # AUDIO (Round-Robin durch Sound-Varianten + Humanize-Jitter)
                    variants = drum_variants.get(note)
                    if variants:
                        _i = drum_rr.get(note, 0) % len(variants)
                        sample = variants[_i]
                        drum_rr[note] = _i + 1
                    else:
                        sample = drum_sounds.get(note)
                    if sample is not None:
                        hit_start = start_sample
                        if human:
                            # ±5ms Timing-Streuung pro Schlag (menschlicher Groove)
                            hit_start = max(0, start_sample + random.randint(-220, 220))
                        gain = vel / 127.0
                        # Ragt der Ausklang über das Dateiende, wird er abgeschnitten –
                        # der Schlag selbst bleibt hörbar (vorher fiel er komplett weg).
                        end_sample = min(hit_start + len(sample), len(audio_buffer))
                        if hit_start < end_sample:
                            audio_buffer[hit_start:end_sample] += (sample[:end_sample - hit_start] * gain)
                    
                    first = False
                last_tick = current_tick
            
        # --- 6. SPEICHERN ---
        mid.save(mid_path)
        
        m = np.max(np.abs(audio_buffer))
        if m > 0: audio_buffer = audio_buffer / m * 0.8
        # Kurzes Ausblenden am Dateiende, damit abgeschnittene Ausklänge nicht knacken
        fade = min(len(audio_buffer), int(0.01 * sr))
        if fade > 0: audio_buffer[-fade:] *= np.linspace(1.0, 0.0, fade)
        sf.write(wav_path, audio_buffer, sr)

        return wav_path, mid_path

    except Exception as e:
        _report_error("Drum Gen Error", e)
        return None, None
# ==========================================
# TEIL 3: AUDIO TO MIDI (Converter)
# ==========================================
def audio_to_midi(audio_path, output_midi_path, mode, duration, sensitivity, smooth, bpm=None,
                  separate=False, quantize=False):
    """Experimentelle Audio->MIDI-Erkennung (regelbasiert, kein trainiertes Modell).

    bpm=None/0 -> Tempo wird aus dem Audio erkannt und an den gefundenen Einsätzen
                  nachgeschärft. Das Tempo landet in der MIDI-Datei und bestimmt die
                  Umrechnung Sekunden -> Beats.
    separate   -> für komplette Mixe: Drums-Modus analysiert nur den Schlag-Anteil,
                  Melody-Modus nur den Ton-Anteil. Bei trockenen Loops/Stems aus lassen
                  (erzeugt dort Fehltreffer).
    quantize   -> Noten auf das 16tel-Raster ziehen; der Clip beginnt auf einem Beat.
    """
    try:
        _tls.bpm = None
        _tls.chords = None
        _tls.key = None
        print(f"Converting: {os.path.basename(audio_path)}...")
        
        # 1. Audio laden
        y, sr = librosa.load(audio_path, sr=22050, mono=True)
        if duration > 0:
            max_samples = int(duration * sr)
            if len(y) > max_samples: y = y[:max_samples]

        # 2. MIDI Setup
        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)

        bpm_auto = not bpm or bpm <= 0
        if bpm_auto:
            try:
                detected, _ = librosa.beat.beat_track(y=y, sr=sr)
                bpm = float(np.atleast_1d(detected)[0])
            except Exception as e:
                print(f"⚠️ BPM detection failed ({e}), using 120.")
                bpm = 0
            if not (20 <= bpm <= 300): bpm = 120.0

        events = []  # (Start s, Ende s, Note, Velocity)
        is_drum_mode = False

        mode_l = str(mode).lower()
        is_chord_mode = "chord" in mode_l
        tempo_events = None   # Einsätze, an denen das Tempo/Raster ausgerichtet wird (Standard: die Noten)
        chord_markers = []    # (Start s, Akkordname) für MIDI-Marker

        # --- 0. CHORDS: hier nur die Anschläge fürs Tempo sammeln; die Akkorde selbst
        #        werden weiter unten bestimmt, wenn Tempo und Beat-Raster feststehen ---
        if is_chord_mode:
            o_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
            o_fr = librosa.onset.onset_detect(onset_envelope=o_env, sr=sr, hop_length=512, backtrack=False, units='frames')
            o_t = librosa.frames_to_time(o_fr, sr=sr, hop_length=512)
            tempo_events = [(float(t), 0.0, 0, float(o_env[f])) for f, t in zip(o_fr, o_t)]

        # --- A. MELODY (Pitch - PYIN) ---
        elif "melody" in mode_l:
            fmin = librosa.note_to_hz('C2')
            fmax = librosa.note_to_hz('C6')
            # Nur den "Ton"-Anteil analysieren: Schlagzeug stört die Tonhöhen-Erkennung
            y_mel = librosa.effects.harmonic(y) if separate else y
            f0, voiced_flag, voiced_probs = librosa.pyin(y_mel, fmin=fmin, fmax=fmax, sr=sr)
            midi_notes = librosa.hz_to_midi(f0)
            times = librosa.times_like(f0, sr=sr)
            
            # Pro Analyse-Frame (~23 ms) eine Note, -1 = kein Ton
            frame_notes = np.full(len(midi_notes), -1, dtype=int)
            ok = np.asarray(voiced_flag, dtype=bool) & (np.asarray(voiced_probs) > sensitivity) & np.isfinite(midi_notes)
            frame_notes[ok] = np.round(midi_notes[ok]).astype(int)

            min_len = 0.05
            if smooth:
                # Medianfilter über 5 Frames (~115 ms): entfernt kurze Ausreißer
                # (Vibrato, Oktavsprünge) und schließt Mini-Lücken in gehaltenen Tönen.
                from scipy.signal import medfilt
                if len(frame_notes) >= 5:
                    frame_notes = medfilt(frame_notes.astype(float), kernel_size=5).astype(int)
                min_len = 0.09

            # Frames zu Noten zusammenfassen
            hop = float(times[1] - times[0]) if len(times) > 1 else 0.023
            # Neue Anschläge: trennt wiederholte gleiche Töne, die sonst zu EINER langen Note verschmelzen.
            # Nicht bei Smooth – dort sollen kurze Aussetzer (Gesang) gerade verbunden werden.
            attack_frames = set()
            if not smooth:
                att_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
                att = librosa.onset.onset_detect(onset_envelope=att_env, sr=sr, hop_length=512,
                                                 backtrack=False, delta=0.1, units='frames')
                # Nur deutliche Anschläge (absolute Schwelle): librosa normiert die Kurve, sodass
                # sonst auch ein Dauerton oder Vibrato in viele "Anschläge" zerfällt.
                attack_frames = set(int(f) for f in att if att_env[f] >= 2.0)

            raw = []  # [Start, Ende, Note, beginnt_mit_Anschlag]
            current_note, start_time, by_attack = -1, 0.0, False
            for i, n in enumerate(frame_notes):
                new_attack = (n == current_note and n >= 0 and i in attack_frames
                              and (times[i] - start_time) >= 0.09)
                if n != current_note or new_attack:
                    if current_note >= 0: raw.append([start_time, times[i], current_note, by_attack])
                    current_note, start_time, by_attack = n, times[i], new_attack
            if current_note >= 0 and len(times):
                raw.append([start_time, times[-1] + hop, current_note, by_attack])  # Ton klingt bis zum Dateiende

            if smooth:
                # Gleiche Note nach winziger Pause (< 60 ms) = ein gehaltener Ton
                # (außer die zweite beginnt mit einem echten Anschlag)
                merged = []
                for ev in raw:
                    if merged and merged[-1][2] == ev[2] and (ev[0] - merged[-1][1]) < 0.06 and not ev[3]:
                        merged[-1][1] = ev[1]
                    else:
                        merged.append(ev)
                raw = merged

            events = [(st, en, n, 100) for st, en, n, _ in raw if (en - st) > min_len]

        # --- B. DRUMS (getrennte Schlag-Erkennung pro Frequenzbereich) ---
        else:
            # Statt EINER Helligkeits-Schwelle für den ganzen Mix wird in drei
            # Frequenzbereichen getrennt nach Schlägen gesucht. So können Kick und
            # Hi-Hat gleichzeitig erkannt werden, und dunkles oder helles Material
            # kippt nicht mehr komplett auf eine Note.
            is_drum_mode = True
            hop = 256  # ~12 ms Zeitauflösung
            D = librosa.stft(y, n_fft=1024, hop_length=hop)
            if separate:
                # Nur den "Schlag"-Anteil analysieren: gehaltene Töne (Bass, Flächen, Gesang)
                # sollen nicht als Kick oder Snare zählen
                _, D = librosa.decompose.hpss(D)
            S = np.abs(D) ** 2
            freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
            S_db = librosa.power_to_db(S, ref=np.max, top_db=60)
            # Ein paar stille Frames voranstellen, damit auch ein Schlag ganz am
            # Dateianfang als Anstieg erkannt wird (wird unten wieder abgezogen).
            lead = 4
            S_db = np.pad(S_db, ((0, 0), (lead, 0)), constant_values=float(S_db.min()))

            KICK_N, SNARE_N, HAT_N = 36, 38, 42
            KICK_RATIO = 0.8   # Tiefen müssen mind. 80 % so stark ansteigen wie die Mitten
            bands = {KICK_N: (40, 130), SNARE_N: (800, 3500), HAT_N: (6000, 11000)}

            # Sensitivity 0.1 -> Delta 0.25 (streng) ... 0.5 -> 0.05 (sehr empfindlich)
            delta_val = max(0.05, 0.3 - (sensitivity * 0.5))
            wait = max(1, int(0.03 * sr / hop))        # mind. 30 ms zwischen zwei Schlägen pro Instrument
            tol = max(1, int(0.025 * sr / hop))        # "gleichzeitig" = innerhalb 25 ms

            GATE_DB = 18.0     # ein Schlag muss bis auf 18 dB an den lautesten seines Bereichs herankommen
            envs, peaks, levels = {}, {}, {}
            for note, (lo, hi) in bands.items():
                band = S_db[(freqs >= lo) & (freqs < hi)]
                levels[note] = band.max(axis=0) if band.size else np.zeros(S_db.shape[1])
                # center=False: sonst verschiebt librosa die Kurve um ~46 ms nach hinten
                env = librosa.onset.onset_strength(S=band, sr=sr, hop_length=hop, aggregate=np.mean, center=False)
                envs[note] = env
                peaks[note] = float(env.max()) if len(env) else 0.0
            top = max(peaks.values()) if peaks else 0.0

            hits = {n: [] for n in bands}  # Note -> [(Frame, Stärke 0..1)]
            for note, env in envs.items():
                # Bereich ohne echte Schläge (nur Übersprechen/Rauschen) auslassen
                if top <= 0 or peaks[note] < 0.2 * top:
                    continue
                frames = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=hop,
                                                    delta=delta_val, wait=wait, backtrack=False, units='frames')
                # Lautstärke-Prüfung: ein Schlag muss in seinem Bereich auch wirklich laut werden
                # (nicht nur relativ zu vorheriger Stille ansteigen)
                lvl = levels[note]
                floor = float(lvl.max()) - GATE_DB
                hits[note] = [(int(f), float(env[f] / peaks[note])) for f in frames
                              if float(lvl[int(f):int(f) + 4].max()) >= floor]

            def _near(frame, others):
                return any(abs(frame - f) <= tol for f, _ in others)

            def _val(env, frame):
                return float(env[max(0, frame - tol):frame + tol + 1].max())

            # Übersprechen aufräumen (Werte = Anstieg in dB, zwischen den Bereichen vergleichbar):
            # - Der Anschlag-Klick einer Kick liegt auch in den Mitten. Als Snare/Clap zählt ein
            #   Schlag auf einer Kick nur, wenn die Mitten deutlich über dem üblichen Kick-Klick liegen.
            # - Eine Hi-Hat reicht nach unten in die Mitten, ist dort aber viel schwächer als in den Höhen.
            # - Das Rauschen einer Snare reicht bis in die Höhen -> dort keine zusätzliche Hat.
            l_env, m_env, h_env = envs[KICK_N], envs[SNARE_N], envs[HAT_N]
            # - Der Knall einer Snare streut auch in die Tiefen. Eine Kick ist es nur, wenn die
            #   Tiefen dort mindestens so stark ansteigen wie die Mitten.
            kick_hits = [(f, st) for f, st in hits[KICK_N] if _val(l_env, f) >= KICK_RATIO * _val(m_env, f)]
            hits[KICK_N] = kick_hits
            click = float(np.percentile([_val(m_env, f) for f, _ in kick_hits], 30)) if kick_hits else 0.0
            snares, on_kick = [], []
            for f, st in hits[SNARE_N]:
                m, h = _val(m_env, f), _val(h_env, f)
                if _near(f, kick_hits):
                    on_kick.append((f, st))
                    if m < 1.4 * click:
                        continue  # nur der Klick der Kick
                elif m < 0.6 * h:
                    continue      # Hi-Hat, keine Snare
                snares.append((f, st))
            if not snares:
                # Liegt jede Snare auf einer Kick, gibt es keinen "reinen" Kick-Klick zum Vergleich
                snares = [(f, st) for f, st in on_kick if st >= 0.5]
            hats = [(f, st) for f, st in hits[HAT_N] if not _near(f, snares)]
            hits[SNARE_N], hits[HAT_N] = snares, hats

            min_gap = 0.06 if smooth else 0.0  # Smooth: Doppelschläge pro Instrument zusammenfassen
            for note, lst in hits.items():
                last_t = -1.0
                for f, st in lst:
                    t = float(librosa.frames_to_time(max(0, f - lead), sr=sr, hop_length=hop))
                    if (t - last_t) < min_gap:
                        continue
                    last_t = t
                    events.append((t, t + 0.05, note, int(55 + 70 * min(1.0, st))))

        # 3. Schreiben
        if not events and not is_chord_mode:
            _tls.error = "No notes detected. Try increasing sensitivity."
            print(f"❌ {_tls.error}")
            return False
        if tempo_events is None:
            tempo_events = events

        # --- TEMPO: automatisch erkanntes BPM an den Einsätzen nachschärfen ---
        # Gesucht wird im Bereich ±4 % das Tempo, bei dem die Einsätze am besten auf ein
        # 16tel-Raster fallen (die Grob-Erkennung liegt oft 1 % daneben).
        def _grid_fit(tempo, t, wgt):
            g = 60.0 / tempo / 4.0
            z = np.sum(wgt * np.exp(2j * np.pi * t / g))
            return abs(z) / max(1e-9, float(np.sum(wgt))), float(np.angle(z) / (2 * np.pi) * g)

        ev_t = np.array([e[0] for e in tempo_events], dtype=float)
        ev_w = np.array([e[3] * (2.0 if (is_drum_mode and e[2] == 36) else 1.0) for e in tempo_events], dtype=float)
        if bpm_auto and len(tempo_events) >= 8:
            # Neben dem Grobwert auch typische Verwechslungen prüfen (z.B. 93 statt 140).
            # Eine Alternative gewinnt nur, wenn sie deutlich besser aufs Raster passt.
            # (Halbes/doppeltes Tempo lässt sich so NICHT unterscheiden – beide passen gleich gut.)
            coarse, best_fit, ref_fit = bpm, -1.0, 0.0
            for ratio in (1.0, 1.5, 4.0 / 3.0, 2.0 / 3.0, 0.75):
                base = coarse * ratio
                if not (60 <= base <= 200):
                    continue
                cands = base * (1.0 + np.linspace(-0.04, 0.04, 161))
                # auch das doppelte Tempo werten: bei Halftime-Erkennung liegen die echten 16tel dazwischen
                fits = [max(_grid_fit(c, ev_t, ev_w)[0], _grid_fit(2 * c, ev_t, ev_w)[0]) for c in cands]
                top_i = int(np.argmax(fits))
                if ratio == 1.0:
                    ref_fit = fits[top_i]
                if fits[top_i] > best_fit and (ratio == 1.0 or fits[top_i] > ref_fit + 0.15):
                    best_fit, bpm = fits[top_i], float(cands[top_i])
        bpm = round(float(bpm), 2)
        _tls.bpm = bpm
        print(f"Tempo: {bpm} BPM")
        track.append(MetaMessage('set_tempo', tempo=int(round(60_000_000 / bpm))))
        ticks_per_sec = (bpm / 60.0) * mid.ticks_per_beat

        # --- CHORDS: ein Akkord pro halbem Takt, auf dem Beat-Raster ---
        if is_chord_mode:
            NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            beat = 60.0 / bpm
            # Wo liegen die Beats? Phase aus den Anschlägen (wie beim Raster)
            phase = 0.0
            if len(ev_t):
                z = np.sum(ev_w * np.exp(2j * np.pi * ev_t / beat))
                phase = float(np.angle(z) / (2 * np.pi) * beat) % beat

            # Nur der Ton-Anteil zählt; Schlagzeug verschmiert die Tonhöhen
            y_h = librosa.effects.harmonic(y)
            chroma = librosa.feature.chroma_cqt(y=y_h, sr=sr, hop_length=512)            # alle Oktaven: welche Töne klingen?
            bass_c = librosa.feature.chroma_cqt(y=y_h, sr=sr, hop_length=512,
                                                fmin=librosa.note_to_hz('C1'), n_octaves=2)  # Tiefen: Hinweis auf den Grundton
            fr_t = librosa.times_like(chroma, sr=sr, hop_length=512)
            rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
            rms = np.pad(rms, (0, max(0, chroma.shape[1] - len(rms))))[:chroma.shape[1]]
            loud = float(rms.max()) if len(rms) else 0.0

            # 24 Muster: Dur- und Moll-Dreiklänge auf allen 12 Grundtönen
            templates = []
            for r in range(12):
                for suffix, third in (("", 4), ("m", 3)):
                    v = np.zeros(12); v[[r, (r + third) % 12, (r + 7) % 12]] = 1.0
                    templates.append((r, third, NOTE_NAMES[r] + suffix, v / np.linalg.norm(v)))

            def _classify(t0, t1):
                """Bester Akkord im Zeitfenster -> (Grundton, Terz, Name, Güte) oder None bei Stille."""
                idx = np.where((fr_t >= t0) & (fr_t < t1))[0]
                if len(idx) == 0 or loud <= 0 or float(rms[idx].mean()) < 0.05 * loud:
                    return None
                c = chroma[:, idx].mean(axis=1); c = c / max(1e-9, np.linalg.norm(c))
                b = bass_c[:, idx].mean(axis=1); b = b / max(1e-9, float(b.max()))
                # Übereinstimmung mit dem Muster + Bonus, wenn der Bass den Grundton spielt
                # (trennt z.B. C-Dur von A-Moll, die zwei Töne gemeinsam haben)
                scored = [(float(c @ v) + 0.25 * float(b[r]), float(c @ v), r, third, name) for r, third, name, v in templates]
                score, fit, r, third, name = max(scored)
                # Gleichmäßiges Rauschen passt zu jedem Dreiklang mit genau 0,5. Die Schwelle liegt
                # knapp darüber; höher wäre strenger, kostet im vollen Mix aber echte Akkorde.
                if fit < 0.53:
                    return None
                return (r, third, name, score)

            def _segments(offset):
                """Fenster von je 2 Beats; offset=1 -> ein einzelner Auftakt-Beat vorweg."""
                bounds, t = [], phase
                if offset:
                    bounds.append((t, t + beat)); t += beat
                total = len(y) / sr
                while t + beat <= total + 1e-6:
                    bounds.append((t, min(t + 2 * beat, total))); t += 2 * beat
                return [(a, b2, _classify(a, b2)) for a, b2 in bounds]

            # Welche Zählung passt besser (Wechsel auf Beat 1/3 oder 2/4)? Die mit den klareren Akkorden.
            options = [_segments(0), _segments(1)]
            def _quality(segs):
                sc = [c[3] for _, _, c in segs if c]
                return float(np.mean(sc)) if sc else -1.0
            segs = max(options, key=_quality)

            # Gleiche Nachbarn zu einem gehaltenen Akkord verbinden
            merged = []
            for t0, t1, c in segs:
                if c is None:
                    continue
                if merged and merged[-1][2][2] == c[2] and abs(merged[-1][1] - t0) < 1e-6:
                    merged[-1][1] = t1
                else:
                    merged.append([t0, t1, c])
            if not merged:
                _tls.error = "No chords detected."
                print(f"❌ {_tls.error}")
                return False

            for t0, t1, (r, third, name, _) in merged:
                st_s, en_s = t0 - phase, t1 - phase - 0.02 * beat   # Clip beginnt auf dem ersten Beat
                events.append((st_s, en_s, 36 + r, 90))                               # Bass: Grundton
                for semis in (0, third, 7):
                    events.append((st_s, en_s, 48 + r + semis, 80))                   # Dreiklang ab C3
                chord_markers.append((st_s, name))
            _tls.chords = [m[2][2] for m in merged]

            # Tonart schätzen: aus den erkannten Akkorden (welche Tonart enthält sie, und welcher
            # Akkord ist das Zentrum?) plus der mittleren Tonverteilung (Krumhansl-Profile).
            prof_maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
            prof_min = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
            mean_c = chroma.mean(axis=1)
            total_len = sum(t1 - t0 for t0, t1, _ in merged)
            share = {}  # Akkordname -> Zeitanteil
            for t0, t1, c in merged:
                share[c[2]] = share.get(c[2], 0.0) + (t1 - t0) / total_len
            # Stufen-Dreiklänge (Halbtonabstand zum Grundton, Suffix) in Dur bzw. natürlichem Moll
            diatonic = {False: [(0, ""), (2, "m"), (4, "m"), (5, ""), (7, ""), (9, "m")],
                        True:  [(0, "m"), (3, ""), (5, "m"), (7, "m"), (8, ""), (10, "")]}
            first_name, last_name = merged[0][2][2], merged[-1][2][2]
            cands = []
            for r in range(12):
                for is_min, prof in ((False, prof_maj), (True, prof_min)):
                    tonic = NOTE_NAMES[r] + ("m" if is_min else "")
                    cover = sum(share.get(NOTE_NAMES[(r + semis) % 12] + suf, 0.0) for semis, suf in diatonic[is_min])
                    profile = float(np.corrcoef(mean_c, np.roll(prof, r))[0, 1])
                    score = (cover + 0.6 * share.get(tonic, 0.0) + 0.15 * (first_name == tonic)
                             + 0.1 * (last_name == tonic) + 0.3 * profile)
                    cands.append((score, r, is_min))
            key_score, key_r, key_minor = max(cands)
            # Dur und parallele Moll-Tonart haben dieselben Töne und lassen sich an einer
            # Akkordschleife oft nicht unterscheiden -> beide nennen, die wahrscheinlichere zuerst.
            if key_minor:
                relative = f"{NOTE_NAMES[(key_r + 3) % 12]} major"
            else:
                relative = f"{NOTE_NAMES[(key_r + 9) % 12]} minor"
            _tls.key = f"{NOTE_NAMES[key_r]} {'minor' if key_minor else 'major'} / {relative}"
            try:
                track.append(MetaMessage('key_signature', key=NOTE_NAMES[key_r] + ('m' if key_minor else '')))
            except Exception:
                pass  # nicht jede Kreuz-Schreibweise ist als MIDI-Tonart gültig
            print(f"Key: {_tls.key} | Chords: {' | '.join(_tls.chords)}")

        # --- RASTER: Noten auf 16tel ziehen, Clip-Anfang auf einen Beat legen ---
        # (Chords liegen bereits exakt auf dem Beat-Raster)
        if quantize and not is_chord_mode:
            # Unter 100 BPM auf 32tel rastern: ist das Tempo nur halb so schnell erkannt
            # (87 statt 174), bleiben die echten 16tel so trotzdem erhalten.
            per_beat = 8 if bpm < 100 else 4
            grid = 60.0 / bpm / per_beat
            z = np.sum(ev_w * np.exp(2j * np.pi * ev_t / grid))
            phase = float(np.angle(z) / (2 * np.pi) * grid)  # Versatz des Rasters gegenüber dem Dateianfang
            steps = np.round((ev_t - phase) / grid).astype(int)
            # Welche Rasterposition ist der Beat? Die mit den meisten/lautesten Einsätzen.
            beat_pos = int(np.argmax([ev_w[(steps % per_beat) == k].sum() for k in range(per_beat)]))
            steps -= beat_pos
            if steps.min() < 0:
                steps += per_beat * int(np.ceil(-steps.min() / float(per_beat)))  # um ganze Beats nach hinten
            best = {}
            for (st_s, en_s, note, vel), step in zip(events, steps):
                length = 1 if is_drum_mode else max(1, int(round((en_s - st_s) / grid)))
                key = (int(step), note)
                if key not in best or vel > best[key][3]:      # doppelte Treffer auf einem Schritt: der lautere bleibt
                    best[key] = (step * grid, (step + length) * grid - (grid * 0.5 if is_drum_mode else 0.0), note, vel)
            events = sorted(best.values(), key=lambda e: e[0])
            if not is_drum_mode:
                # Einstimmig: keine Note darf in die nächste hineinragen
                events = [(st_s, min(en_s, events[i + 1][0]) if i + 1 < len(events) else en_s, note, vel)
                          for i, (st_s, en_s, note, vel) in enumerate(events)]
                events = [e for e in events if e[1] > e[0]]

        # Alle Note-On/Off mit absoluter Zeit sammeln und dann sortiert schreiben.
        # (Vorher wurde ein Schlag nach hinten geschoben, wenn der vorige noch "klang" –
        # bei dichten Hats oder gleichzeitigen Schlägen stimmte das Timing nicht.)
        channel = 9 if is_drum_mode else 0  # Kanal 10 = Drums (General MIDI)
        raw_msgs = []  # (Ticks, Rang, Nachricht) – bei gleicher Zeit: erst Off, dann Marker, dann On
        for start, end, note, vel in events:
            start_ticks = int(round(start * ticks_per_sec))
            end_ticks = max(start_ticks + 20, int(round(end * ticks_per_sec)))
            raw_msgs.append((start_ticks, 2, Message('note_on', note=note, velocity=vel, channel=channel)))
            raw_msgs.append((end_ticks, 0, Message('note_off', note=note, velocity=0, channel=channel)))
        for start, text in chord_markers:
            raw_msgs.append((int(round(start * ticks_per_sec)), 1, MetaMessage('marker', text=text)))
        raw_msgs.sort(key=lambda m: (m[0], m[1]))

        last_ticks = 0
        for ticks, _, msg in raw_msgs:
            msg.time = ticks - last_ticks
            track.append(msg)
            last_ticks = ticks

        mid.save(output_midi_path)
        print(f"✅ MIDI saved: {output_midi_path}")
        return True

    except Exception as e:
        _report_error("MIDI Error", e)
        return False

@_seeded
def create_bass_files(root, scale, bpm, bars, genre, prog, output_dir, bass_style="Steady (Groove)", density=80, swing=0, time_sig="4/4", arr_mode="♾️ Infinite Loop", kick_steps=None):
    """kick_steps: Kick-Positionen der Drums (absolute 16tel-Schritte). Sind sie
    gegeben, rastet der Bass bei DnB, Trap und HipHop auf die Kicks ein
    (nur bei den genre-abhängigen Stilen Steady/Busy, nicht bei festen Patterns)."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        wav_path = os.path.join(output_dir, "generated_bass.wav")
        mid_path = os.path.join(output_dir, "generated_bass.mid")
        
        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)
        track.append(MetaMessage('track_name', name='Sub Bass'))
        track.append(MetaMessage('set_tempo', tempo=int(60000000 / bpm)))

        # 1. Zeit-Raster (4/4 = 16 Steps, 3/4 & 6/8 = 12 Steps)
        steps_per_bar = 12 if ("3/4" in time_sig or "6/8" in time_sig) else 16
        step_scale = steps_per_bar / 16.0 # Muster auf die Taktlänge skalieren
        total_steps = int(bars) * steps_per_bar
        prob = density / 100.0

        # 2. Skala & Harmonien
        intervals = harmony_intervals(scale)
        base_note_ref = NOTES.get(root, 0) + 36 
        scale_notes = []
        for oct_off in [0, 12, 24]:
            for i in intervals: scale_notes.append(base_note_ref + oct_off + i)

        # Smart Progression Lookup
        prog_data = resolve_progression(prog)

        # Kick-Kopplung: nur dort, wo Bass und Kick stilistisch zusammengehören.
        # (House/Reggae spielen den Bass bewusst ZWISCHEN den Kicks, Jazz läuft frei.)
        couple = bool(kick_steps) and any(g in genre for g in ("DnB", "Trap", "HipHop"))
        kick_set = sorted(kick_steps) if couple else []
        # Maximale Notenlänge in 16teln: Trap = lange 808, DnB = kurze Sub-Stöße
        lock_cap = 12 if "Trap" in genre else (4 if "DnB" in genre else 6)

        # 3. RHYTHMUS-ENTSCHEIDUNG (Hard-Grid Wahl)
        events = []
        for bar in range(int(bars)):
            energy = get_arrangement_energy(bar, int(bars), arr_mode)
            if energy < 0.2: continue # Mute im Intro/Break

            # Töne für diesen Takt bestimmen
            if prog_data:
                step_data = prog_data[bar % len(prog_data)]
                # --- FIX: Wir bestimmen den Basis-Index (0-6) direkt aus den Daten ---
                if isinstance(step_data, str):
                    base_idx = int(step_data[1:]) # Holt die Zahl aus "b1", "b2" etc.
                else:
                    base_idx = step_data
                
                # Die echte MIDI-Note (evtl. chromatisch verschoben) berechnen
                root_n = get_chromatic_note(scale_notes, step_data)
            else:
                base_idx = 0
                root_n = scale_notes[0]

            # Hilfsnoten sicher berechnen (Quinte und Oktave)
            try:
                # Wir nutzen den base_idx für die Quinte, damit sie zur Skala passt
                fifth_idx = min(base_idx + 4, len(scale_notes)-1)
                fifth_n = scale_notes[fifth_idx]
            except: 
                fifth_n = root_n + 7
            
            octave_n = root_n + 12
            bar_start = bar * steps_per_bar
            current_style = "Simple (Root)" if energy < 0.4 else bass_style

            # --- DAS RASTER FINDEN ---
            pattern_to_use = []
            locked = False  # True = Positionen kommen von der Kick (schon in echten Schritten)
            if current_style in BASS_PATTERNS:
                pattern_to_use = BASS_PATTERNS[current_style]
            else:
                bar_kicks = [k - bar_start for k in kick_set if bar_start <= k < bar_start + steps_per_bar]
                if bar_kicks:
                    # Eine Bassnote pro Kick, gehalten bis zur nächsten Kick (höchstens lock_cap)
                    ends = bar_kicks[1:] + [steps_per_bar]
                    pattern_to_use = [(k, max(1, min(e - k, lock_cap))) for k, e in zip(bar_kicks, ends)]
                    locked = True
                # Dynamische Genre-Raster für "Steady" und "Busy"
                elif "House" in genre or "Reggae" in genre:
                    pattern_to_use = [(2, 2), (6, 2), (10, 2), (14, 2)] # Offbeats
                elif "Techno" in genre or "Synthpop" in genre:
                    pattern_to_use = [(0, 4), (4, 4), (8, 4), (12, 4)] # Viertel
                elif "DnB" in genre:
                    pattern_to_use = [(0, 2), (10, 2)] if bar % 2 == 0 else [(0, 2), (3, 2), (11, 2)]
                elif "Trap" in genre:
                    pattern_to_use = [(0, 12)]
                else:
                    pattern_to_use = [(0, 8), (8, 8)] # Default 2-Step

            # 4. NOTEN IN DEN BAR SCHREIBEN
            for s_pos, s_dur in pattern_to_use:
                # Position an die Taktlänge anpassen (12 Steps bei 3/4 & 6/8)
                s_pos_s = s_pos if locked else int(s_pos * step_scale)
                # Dichte prüfen (die Eins bleibt fast immer). Kick-gekoppelte Noten
                # bleiben alle stehen – sonst reißt die Kopplung an zufälligen Stellen ab.
                if not locked and random.random() > (prob * energy) and s_pos_s != 0: continue
                
                # Note bestimmen (Varianz bei Busy)
                n = root_n
                if ("Busy" in current_style or "Roller" in current_style) and s_pos_s > 0:
                    if random.random() < 0.4: n = random.choice([fifth_n, octave_n])

                # Velocity mit Impact
                energy_prev = get_arrangement_energy(bar-1, int(bars), arr_mode) if bar > 0 else 0
                is_energy_jump = (energy >= 0.8 and energy_prev < 0.8)
                
                if s_pos_s == 0 and is_energy_jump: vel = 127
                else: vel = int((90 + (25 if s_pos_s == 0 else 0)) * energy)
                
                vel = max(0, min(127, vel + random.randint(-5, 5)))
                events.append((bar_start + s_pos_s, n, vel, s_dur))

        # 5. HOCHPRÄZISIONS-MIDI-EXPORT
        sr, ticks_per_16th = 44100, mid.ticks_per_beat // 4
        sec_per_16th = (60 / bpm) / 4
        audio_buffer = np.zeros(int((total_steps * sec_per_16th + 1.5) * sr))
        T_master = np.linspace(0, len(audio_buffer)/sr, len(audio_buffer), False)
        
        def _on_tick(st):
            return st * ticks_per_16th + (int(ticks_per_16th * (swing / 100) * 0.6) if st % 2 != 0 else 0)

        last_tick = 0
        for ev_i, (step, note, vel, dur) in enumerate(events):
            # Timing mit exakter Swing-Kopie der Drums
            abs_on_tick = step * ticks_per_16th
            abs_on_time = step * sec_per_16th
            if step % 2 != 0:
                shift = (swing / 100) * 0.6
                abs_on_tick += int(ticks_per_16th * shift)
                abs_on_time += (sec_per_16th * shift)

            # --- DER TIGHTNESS-TRICK ---
            # Wir lassen am Ende jeder Note 2 Ticks Platz, damit sich Note-Off 
            # und das neue Note-On niemals überschneiden.
            abs_off_tick = abs_on_tick + (dur * ticks_per_16th) - 2 
            if ev_i + 1 < len(events):
                # Bei Swing und engen Abständen nie über den nächsten Einsatz hinaus halten
                abs_off_tick = max(abs_on_tick + 1, min(abs_off_tick, _on_tick(events[ev_i + 1][0]) - 2))

            # MIDI Schreiben
            track.append(Message('note_on', note=note, velocity=vel, time=max(0, abs_on_tick - last_tick), channel=2))
            track.append(Message('note_off', note=note, velocity=0, time=(abs_off_tick - abs_on_tick), channel=2))
            last_tick = abs_off_tick
            
            # AUDIO
            s_idx = int(np.round(abs_on_time * sr))
            e_idx = s_idx + int(np.round((dur * sec_per_16th + 0.4) * sr))
            if e_idx < len(audio_buffer):
                freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
                sub_wave = np.sin(2 * np.pi * freq * T_master[s_idx:e_idx]) * (vel/127) * 0.5
                audio_buffer[s_idx:e_idx] += apply_envelope(sub_wave, attack=0.02, mode="exponential")

        mid.save(mid_path)
        audio_buffer = soft_clipper(audio_buffer) * 0.85
        sf.write(wav_path, audio_buffer, sr)
        return wav_path, mid_path
    except Exception as e:
        _report_error("Bass Error", e); return None, None
                                
@_seeded
def create_full_loop(root, scale, bpm, bars, time_sig, octave, mode, density, swing, human, sound, genre, prog, voicing, bass_style, arr_mode, output_dir, progress_cb=None, stop_event=None):
    try:
        os.makedirs(output_dir, exist_ok=True)
        print("--- 🚀 FULL LOOP MASTER PROCESS STARTED ---")

        def _step(idx, label):
            if progress_cb:
                try: progress_cb(idx, label)
                except Exception: pass

        def _stopped():
            return stop_event is not None and stop_event.is_set()

        # "Random" (oder unbekannt): EIN Preset würfeln, das Chords, Bass, Melodie,
        # Pads und Strings gemeinsam nutzen – sonst spielt jede Spur eine andere Harmonie.
        if resolve_progression(prog) is None:
            prog = pick_random_progression()
            print(f"🎲 Random progression for this loop: {prog}")
        _tls.progression = prog

        # 1. GENERIERUNG (Die 4 Einzelteile)
        print("-> Step 1: Generating Drums...")
        _step(1, "🥁 Drums...")
        wav_d, mid_d = create_drum_files(genre, bpm, bars, density, swing, human, output_dir, time_sig,arr_mode)
        if _stopped():
            print("⏹ FULL LOOP STOPPED BY USER (nach Drums)")
            return None, None

        print("-> Step 2: Generating Chords...")
        _step(2, "🎹 Chords...")
        wav_c, mid_c = create_chord_files(root, scale, bpm, bars, prog, mode, output_dir, voicing, sound, genre, density, swing, time_sig, human,arr_mode)
        if _stopped():
            print("⏹ FULL LOOP STOPPED BY USER (nach Chords)")
            return None, None

        print("-> Step 3: Generating Bass...")
        _step(3, "🎸 Bass...")
        # Sicherstellen, dass create_bass_files existiert und alle Argumente nimmt!
        wav_b, mid_b = create_bass_files(root, scale, bpm, bars, genre, prog, output_dir, bass_style, density, swing, time_sig, arr_mode,
                                         kick_steps=get_last_kick_steps())
        if _stopped():
            print("⏹ FULL LOOP STOPPED BY USER (nach Bass)")
            return None, None

        print("-> Step 4: Generating Melody...")
        _step(4, "🎶 Melody...")
        # Die Melodie bleibt im Full Loop einstimmig. "Mode" beschreibt hier den Akkord-Typ;
        # früher galt er für beide Spuren zugleich (Mono -> Akkordspur nur Grundtöne,
        # Triads -> Melodie in dreistimmigen Blöcken).
        wav_m, mid_m = create_melody_files(root, scale, bpm, bars, time_sig, octave, "Melody (Mono)", density, swing, human, sound, genre, prog, output_dir, arr_mode)
        if _stopped():
            print("⏹ FULL LOOP STOPPED BY USER (nach Melody)")
            return None, None
        
        # NEU: Die 2 Bonus MIDI-Tracks (Kein WAV nötig!)
        _step(5, "🎼 Bonus MIDI + Mix...")
        mid_pads = generate_pad_midi(root, scale, bars, prog, output_dir)
        mid_strings = generate_strings_midi(root, scale, bars, prog, genre, output_dir)
        
        # 2. MIDI MERGE (Alle 6 Spuren zusammenführen)
        full_mid = MidiFile(type=1)
        # Wir fügen alle 6 Dateien zur Liste hinzu
        all_midi_files = [mid_d, mid_b, mid_c, mid_m, mid_pads, mid_strings]
        
        for m_file in all_midi_files:
            if m_file and os.path.exists(m_file):
                temp_mid = MidiFile(m_file)
                for track in temp_mid.tracks:
                    full_mid.tracks.append(track)
        
        full_mid_path = os.path.join(output_dir, "full_loop.mid")
        full_mid.save(full_mid_path)

        if not all([wav_d, wav_c, wav_b, wav_m]):
            print("❌ Error: One of the generators failed (returned None).")
            return None, None

        if _stopped():
            print("⏹ FULL LOOP STOPPED BY USER (vor dem Mix)")
            return None, None

        # 3. AUDIO MIXING ENGINE (Crash-Sicherer Stereo-Mix)
        print("-> Step 6: Mixing Audio Tracks (Stereo Conversion)...")
        sr = 44100
        
        def load_safe(path):
            # Lädt Datei und erzwingt (Samples, Channels) Format
            data, _ = librosa.load(path, sr=sr, mono=False)
            if len(data.shape) == 1: # Wenn Mono (N,) -> mache (N, 2)
                data = np.stack([data, data], axis=1)
            elif data.shape[0] == 2: # Wenn Librosa Stereo (2, N) -> mache (N, 2)
                data = data.T
            return data

        # Wir laden nur die 4 Spuren, die Audio haben
        audio_d = load_safe(wav_d)
        audio_b = load_safe(wav_b)
        audio_c = load_safe(wav_c)
        audio_m = load_safe(wav_m)

        # Längen angleichen
        max_len = max(len(audio_d), len(audio_b), len(audio_c), len(audio_m))
        
        def pad_stereo(data, target):
            if len(data) < target:
                return np.pad(data, ((0, target - len(data)), (0, 0)), mode='constant')
            return data

        # Mixen mit Lautstärke-Verteilung
        final_mix = (pad_stereo(audio_d, max_len) * 0.8) + \
                    (pad_stereo(audio_b, max_len) * 0.8) + \
                    (pad_stereo(audio_c, max_len) * 0.5) + \
                    (pad_stereo(audio_m, max_len) * 0.5)

        # Mastering (Soft Clip & Normalisierung)
        final_mix = np.tanh(final_mix) 
        max_v = np.max(np.abs(final_mix))
        if max_v > 0:
            final_mix = final_mix / max_v * 0.85
        
        full_wav_path = os.path.join(output_dir, "full_loop.wav")
        if _stopped():
            print("⏹ FULL LOOP STOPPED BY USER (nach dem Mix)")
            return None, None
        sf.write(full_wav_path, final_mix, sr)

        print("✅ --- FULL 6-TRACK LOOP COMPLETED ---")
        return full_wav_path, full_mid_path

    except Exception as e:
        _report_error("Full Loop Error", e)
        import traceback
        traceback.print_exc()
        return None, None
    
@_seeded
def generate_pad_midi(root, scale, bars, prog, output_dir):
    """Spur 5: Erzeugt lange, liegende Akkorde auf Kanal 4 (Chromatisch sicher)."""
    mid_path = os.path.join(output_dir, "generated_pads.mid")
    mid = MidiFile(); track = MidiTrack(); mid.tracks.append(track)
    track.append(MetaMessage('track_name', name='Ambient Pads'))
    
    intervals = harmony_intervals(scale)
    base_note = NOTES.get(root, 0) + 48 
    scale_notes = []
    for oct_off in [0, 12, 24]:
        for i in intervals: scale_notes.append(base_note + oct_off + i)
    
    prog_data = resolve_progression(prog)
    
    ticks_per_bar = mid.ticks_per_beat * 4
    last_tick = 0
    
    for bar in range(int(bars)):
        if prog_data:
            step_data = prog_data[bar % len(prog_data)]
            # --- FIX: Wir bestimmen den Index direkt aus dem Rezept ---
            idx = int(step_data[1:]) if isinstance(step_data, str) else step_data
            root_note = get_chromatic_note(scale_notes, step_data)
        else: 
            idx = 0
            root_note = scale_notes[0]
        
        # Pad: Grundton und Quinte (Sicherer Zugriff über idx)
        chord = [root_note, scale_notes[idx + 4]]
        current_start_tick = bar * ticks_per_bar
        
        delta_on = max(0, current_start_tick - last_tick)
        for i, n in enumerate(chord):
            track.append(Message('note_on', note=n, velocity=60, time=delta_on if i == 0 else 0, channel=3))
        
        track.append(Message('note_off', note=chord[0], velocity=0, time=ticks_per_bar, channel=3))
        for n in chord[1:]:
            track.append(Message('note_off', note=n, velocity=0, time=0, channel=3))
        
        last_tick = current_start_tick + ticks_per_bar
            
    mid.save(mid_path)
    return mid_path

@_seeded
def generate_strings_midi(root, scale, bars, prog, genre, output_dir):
    """Spur 6: Erzeugt intelligente Streicher auf Kanal 5 (Chromatisch sicher)."""
    mid_path = os.path.join(output_dir, "generated_strings.mid")
    mid = MidiFile(); track = MidiTrack(); mid.tracks.append(track)
    track.append(MetaMessage('track_name', name='Orchestral Strings'))
    
    intervals = harmony_intervals(scale)
    base_note_ref = NOTES.get(root, 0) + 60 
    scale_notes = []
    for oct_off in [0, 12, 24]:
        for i in intervals: scale_notes.append(base_note_ref + oct_off + i)
    
    prog_data = resolve_progression(prog)

    ticks_per_bar = mid.ticks_per_beat * 4
    ticks_per_16th = mid.ticks_per_beat // 4
    last_tick = 0

    for bar in range(int(bars)):
        if prog_data:
            step_data = prog_data[bar % len(prog_data)]
            # --- FIX: Index direkt aus dem Rezept ---
            idx = int(step_data[1:]) if isinstance(step_data, str) else step_data
            root_n = get_chromatic_note(scale_notes, step_data)
        else: 
            idx = 0
            root_n = scale_notes[0]
        
        octave_n = root_n + 12
        bar_start_tick = bar * ticks_per_bar

        # Rhythmus bestimmen
        if "Oriental" in genre: pattern = [0, 4, 8, 12, 14]
        elif any(g in genre for g in ["House", "Synthpop", "Techno"]): 
            pattern = [0, 2, 4, 6, 8, 10, 12, 14]
        else: pattern = [0] 

        for step in pattern:
            abs_step_tick = bar_start_tick + (step * ticks_per_16th)
            dur_ticks = ticks_per_16th if len(pattern) > 1 else ticks_per_bar
            
            delta_on = max(0, abs_step_tick - last_tick)
            
            if "Oriental" in genre:
                track.append(Message('note_on', note=root_n, velocity=100, time=delta_on, channel=4))
                track.append(Message('note_on', note=octave_n, velocity=100, time=0, channel=4))
                track.append(Message('note_off', note=root_n, velocity=0, time=dur_ticks, channel=4))
                track.append(Message('note_off', note=octave_n, velocity=0, time=0, channel=4))
            else:
                n = octave_n if (step in [2, 6, 10, 14] and len(pattern) > 1) else root_n
                track.append(Message('note_on', note=n, velocity=95, time=delta_on, channel=4))
                track.append(Message('note_off', note=n, velocity=0, time=dur_ticks, channel=4))
            
            last_tick = abs_step_tick + dur_ticks

    mid.save(mid_path)
    return mid_path

def get_arrangement_energy(bar, total_bars, mode):
    """Das mathematische Drehbuch für alle 9 Arrangement-Modi."""
    if "Infinite" in mode or total_bars < 4:
        return 1.0
    
    progress = bar / total_bars
    
    # 1. Radio Edit (Strophe/Refrain Wechsel)
    if "Radio Edit" in mode:
        if progress < 0.1: return 0.2   # Intro
        if progress < 0.3: return 0.5   # Verse 1
        if progress < 0.5: return 1.0   # Chorus 1
        if progress < 0.7: return 0.6   # Verse 2
        if progress < 0.9: return 1.0   # Chorus 2
        return 0.3                      # Outro

    # 2. Club Mix (Langer Aufbau für DJs)
    elif "Club Mix" in mode:
        if progress < 0.2: return 0.3
        if progress < 0.5: return 0.8
        if progress < 0.8: return 1.0
        return 0.4

    # 3. DnB Journey (Pre-Drop & Drop Fokus)
    elif "DnB" in mode:
        if progress < 0.2: return 0.2   # Atmos Intro
        if progress < 0.35: return 0.5  # Build-up
        if progress < 0.4: return 0.0   # THE SILENT GAP (vor dem Drop)
        if progress < 0.7: return 1.0   # DROP A
        if progress < 0.8: return 0.3   # Mid-Break
        return 1.0                      # DROP B / Finale

    # 4. East Coast (Stabiler Loop, Platz für Vocals)
    elif "East Coast" in mode:
        # Wechselt dezent zwischen 0.5 (Verse) und 0.8 (Hook)
        return 0.8 if (int(bar/8) % 2 == 0) else 0.5

    # 5. Westcoast (G-Funk mit Bridge)
    elif "Westcoast" in mode:
        if progress > 0.7 and progress < 0.85: return 0.3 # Die Bridge (Drums aus)
        return 0.9 if (int(bar/8) % 2 == 0) else 0.6
    
    # 6a. Trap/HipHop Hook (REINHEFÜGT: Startet mit dem Refrain)
    elif "Trap" in mode:
        if progress < 0.05: return 0.3  # Ganz kurzes Intro (4 Bars)
        if progress < 0.25: return 1.0  # HOOK 1 (Direkt Vollgas)
        if progress < 0.50: return 0.5  # VERSE 1 (Platz für Rap)
        if progress < 0.70: return 1.0  # HOOK 2
        if progress < 0.90: return 0.5  # VERSE 2
        return 0.3                      # Outro

    # 6. Ambient Wave (Ebbe & Flut)
    elif "Ambient Wave" in mode:
        # Erzeugt eine Sinus-Welle der Energie
        import math
        return 0.4 + 0.4 * math.sin(progress * math.pi * 4)

    # 7. Impact / Trailer (Knall am Anfang)
    elif "Impact" in mode:
        if bar < 4: return 1.0          # Start-Knall
        if progress < 0.2: return 0.1   # Totale Leere danach
        return 0.1 + (progress * 0.9)   # Langer Wiederaufbau

    # 8. Cinematic Build (Stetiger Aufstieg)
    elif "Cinematic" in mode:
        return 0.1 + (progress * 0.9)

    return 1.0