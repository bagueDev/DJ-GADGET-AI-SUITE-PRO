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
        intervals = SCALES.get(scale, SCALES["Minor"])
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
            current_mode = "Triads (3-Note)" if energy < 0.7 else mode            
            # Wenn Energie SEHR niedrig ist (Intro), spielen wir nur eine lange Fläche (Pad)
            # anstatt der rhythmischen Stabs
            current_pattern = [0] if energy < 0.4 else pattern
            current_dur = steps_per_bar if energy < 0.4 else dur
            # ... (Hier nutzt du jetzt 'current_mode' beim Bauen der Akkord-Noten 
            # und 'current_pattern'/'current_dur' in der Rhythmus-Schleife) ...
            prog_data = PROGRESSIONS.get(progression_name)
            
            if prog_data and not progression_name.strip().startswith("---"):
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
                    # Schwebend: Sekunde statt Terz
                    chord_notes.append(scale_notes[idx + 1])
                    chord_notes.append(scale_notes[idx + 4])
                
                elif "Sus4" in current_mode:
                    # Spannung: Quarte statt Terz
                    chord_notes.append(scale_notes[idx + 3])
                    chord_notes.append(scale_notes[idx + 4])
                
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
        print(f"❌ Chord Rhythm Error: {e}"); return None, None
            
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
def create_melody_files(root, scale, bpm, bars, time_sig, octave, mode, density, swing, human, sound, genre, prog, output_dir, arr_mode="♾️ Infinite Loop"):
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
        scale_notes = [base_note_ref + i for i in intervals]
        # Wir erweitern scale_notes um 2 Oktaven, damit der Harmony-Link genug Futter hat
        for oct_off in [12, 24]:
            scale_notes += [base_note_ref + oct_off + i for i in intervals]
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
        prog_data = None
        if prog and not prog.strip().startswith("---"):
            for key in PROGRESSIONS.keys():
                if key != "Random" and key in prog:
                    prog_data = PROGRESSIONS[key]; break

        generated_events = [] 
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
                candidates = [new_index, max(0, new_index-1), min(len(allowed_notes)-1, new_index+1)]
                best_note_idx = new_index
                
                for c_idx in candidates:
                    note_val = allowed_notes[c_idx]
                    if (note_val % 12) == chord_root or ((note_val % 12) - chord_root) % 12 in allowed_steps:
                        best_note_idx = c_idx
                        if is_downbeat and (note_val % 12) == chord_root:
                            break
                
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
        print(f"❌ Melody Error: {e}")
        return None, None   
# ==========================================
# TEIL 2: DRUM GENERATOR (NEU!)
# ==========================================
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
                    except: pass
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
            if bar > 0 and bar % 2 == 0 and random.random() < 0.6:
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
            use_ride = (energy >= 0.8)

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
                    if "Breakbeat" in genre:
                        # Amen-Style Snare-Roll am Taktende (Crescendo)
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

                # 2. HOUSE
                elif "House" in genre:
                    current_hp = hp_a if bar % 2 == 0 else hp_b
                    if step_in_bar in [0, 4, 8, 12] and energy >= 0.3:
                        events.append((step, 36, 118))
                    if step_in_bar in current_hp["c"] and energy >= 0.5:
                        events.append((step, 39, 120 if step_in_bar in [4, 12] else 75))
                    if step_in_bar in current_hp["s"] and energy >= 0.6 and random.random() < prob:
                        events.append((step, 37, random.randint(75, 95)))
                    # Ghost-Clap + offene Hat als Variation
                    if step_in_bar == 15 and energy >= 0.6 and random.random() < prob * 0.4:
                        events.append((step, 39, random.randint(50, 65)))
                    if step_in_bar == 14 and energy >= 0.7 and random.random() < prob * 0.35:
                        events.append((step, 46, 85))

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
                if "Breakbeat" in genre:
                    current_amen = amen_a if bar % 2 == 0 else amen_b
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
                    if step_in_bar == 11 and energy >= 0.6 and random.random() < 0.6:
                        events.append((step, 40, 45))
                    # 16tel-Hats mit Akzenten + Open Hats auf Offbeats
                    if random.random() < (prob * energy):
                        v_hat = 118 if step_in_bar % 4 == 0 else (55 if step_in_bar % 4 == 2 else 80)
                        n_hat = 46 if step_in_bar in current_amen["open"] else 42
                        events.append((step, n_hat, v_hat))

                # 4. DRUM AND BASS (Rolling & Simon V)
                elif "DnB" in genre:
                    current_kick_pattern = p_a if bar % 2 == 0 else p_b
                    if step_in_bar in current_kick_pattern and energy >= 0.3:
                        events.append((step, 36, 120 if step_in_bar == 0 else 105))
                    if step_in_bar in [4, 12] and energy >= 0.5:
                        events.append((step, 38, 120)) 
                    # Rolling Hats (SampleFocus Style)
                    pos_in_quad = step_in_bar % 4
                    dnb_v_pattern = [115, 45, 85, 40]
                    if random.random() < (prob * energy):
                        is_offbeat = step_in_bar in [2, 6, 10, 14]
                        n_hat = 46 if (is_offbeat and random.random() < 0.3) else 42
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
                elif "Reggae" in genre:
                    if step_in_bar in rp["k"] and energy >= 0.3:
                        events.append((step, 36, 120))
                    if step_in_bar in rp["s"] and energy >= 0.5:
                        events.append((step, 37, 115))
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
                    current_comp = random.choice(jazz_comp_pool)
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
                    if random.random() < (prob * energy):
                        # Nutzt Ride (51) bei hoher Energie, sonst Closed Hat (42)
                        hat_n = 51 if (use_ride and energy > 0.7) else 42
                        events.append((step, hat_n, int(100 * energy)))                   
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
                        if human:
                            # ±5ms Timing-Streuung (menschlicher Groove)
                            start_sample = max(0, start_sample + random.randint(-220, 220))
                        gain = vel / 127.0
                        end_sample = start_sample + len(sample)
                        if end_sample < len(audio_buffer):
                            audio_buffer[start_sample:end_sample] += (sample * gain)
                    
                    first = False
                last_tick = current_tick
            
        # --- 6. SPEICHERN ---
        mid.save(mid_path)
        
        m = np.max(np.abs(audio_buffer))
        if m > 0: audio_buffer = audio_buffer / m * 0.8
        sf.write(wav_path, audio_buffer, sr)

        return wav_path, mid_path

    except Exception as e:
        print(f"Drum Gen Error: {e}")
        return None, None
# ==========================================
# TEIL 3: AUDIO TO MIDI (Converter)
# ==========================================
def audio_to_midi(audio_path, output_midi_path, mode, duration, sensitivity, smooth):
    try:
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
        track.append(MetaMessage('set_tempo', tempo=500000)) # 120 BPM
        
        ticks_per_sec = 2 * mid.ticks_per_beat
        events = []

        # --- A. MELODY (Pitch - PYIN) ---
        if "melody" in str(mode).lower():
            fmin = librosa.note_to_hz('C2')
            fmax = librosa.note_to_hz('C6')
            f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=fmin, fmax=fmax, sr=sr)
            midi_notes = librosa.hz_to_midi(f0)
            times = librosa.times_like(f0, sr=sr)
            
            current_note = None
            start_time = 0
            for i, (note, is_voiced, prob) in enumerate(zip(midi_notes, voiced_flag, voiced_probs)):
                if is_voiced and prob > sensitivity:
                    note_int = int(round(note))
                    if current_note is None:
                        current_note = note_int
                        start_time = times[i]
                    elif current_note != note_int:
                        end_time = times[i]
                        if (end_time - start_time) > 0.05:
                            events.append((start_time, end_time, current_note))
                        current_note = note_int
                        start_time = times[i]
                else:
                    if current_note is not None:
                        end_time = times[i]
                        if (end_time - start_time) > 0.05:
                            events.append((start_time, end_time, current_note))
                        current_note = None

        # --- B. DRUMS (Smart Onset + Frequency) ---
        else:
            # 1. Onset Detection (Rhythmus)
            # Wir nutzen 'delta' basierend auf Sensitivity, um mehr Schläge zu finden.
            # Sensitivity 0.1 -> Delta 0.25 (Streng)
            # Sensitivity 0.5 -> Delta 0.05 (Sehr empfindlich)
            delta_val = max(0.05, 0.3 - (sensitivity * 0.5))
            
            onset_frames = librosa.onset.onset_detect(
                y=y, sr=sr, 
                backtrack=True, 
                units='frames', 
                delta=delta_val
            )
            
            # 2. Frequenz-Analyse (Kick vs. Snare Unterscheidung)
            # Wir berechnen den "Spectral Centroid" (Helligkeit) für den ganzen Song
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            times = librosa.frames_to_time(onset_frames, sr=sr)
            
            for i, frame in enumerate(onset_frames):
                t = times[i]
                
                # Wir schauen uns die Helligkeit an diesem Zeitpunkt an
                # (Sicherheitscheck, falls Frame out of bounds)
                if frame < len(spectral_centroids):
                    brightness = spectral_centroids[frame]
                else:
                    brightness = 0
                
                # ENTSCHEIDUNG: Kick oder Snare?
                # Tiefe Frequenz (< 1500 Hz) -> Kick (C1 / 36)
                # Hohe Frequenz (> 1500 Hz) -> Snare (D1 / 38)
                if brightness < 1800:
                    note = 36 # Kick
                else:
                    note = 38 # Snare
                
                events.append((t, t + 0.1, note))

        # 3. Schreiben
        if not events:
            print("❌ No notes detected. Try increasing sensitivity.")
            return False

        events.sort(key=lambda x: x[0])
        last_time_ticks = 0
        
        for start, end, note in events:
            start_ticks = int(start * ticks_per_sec)
            delta_on = max(0, start_ticks - last_time_ticks)
            track.append(Message('note_on', note=note, velocity=100, time=delta_on))
            
            end_ticks = int(end * ticks_per_sec)
            duration_ticks = max(20, end_ticks - start_ticks)
            track.append(Message('note_off', note=note, velocity=0, time=duration_ticks))
            
            last_time_ticks = start_ticks + duration_ticks

        mid.save(output_midi_path)
        print(f"✅ MIDI saved: {output_midi_path}")
        return True

    except Exception as e:
        print(f"MIDI Error: {e}")
        return False

def create_bass_files(root, scale, bpm, bars, genre, prog, output_dir, bass_style="Steady (Groove)", density=80, swing=0, time_sig="4/4", arr_mode="♾️ Infinite Loop"):
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
        intervals = SCALES.get(scale, SCALES["Minor"])
        base_note_ref = NOTES.get(root, 0) + 36 
        scale_notes = []
        for oct_off in [0, 12, 24]:
            for i in intervals: scale_notes.append(base_note_ref + oct_off + i)

        # Smart Progression Lookup
        prog_data = None
        for key in PROGRESSIONS.keys():
            if key != "Random" and key in prog:
                prog_data = PROGRESSIONS[key]; break

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
            if current_style in BASS_PATTERNS:
                pattern_to_use = BASS_PATTERNS[current_style]
            else:
                # Dynamische Genre-Raster für "Steady" und "Busy"
                if "House" in genre or "Reggae" in genre:
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
                s_pos_s = int(s_pos * step_scale)
                # Dichte prüfen (die Eins bleibt fast immer)
                if random.random() > (prob * energy) and s_pos_s != 0: continue
                
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
        
        last_tick = 0
        for step, note, vel, dur in events:
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
        print(f"❌ Bass Error: {e}"); return None, None
                                
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
        wav_b, mid_b = create_bass_files(root, scale, bpm, bars, genre, prog, output_dir, bass_style, density, swing, time_sig,arr_mode)
        if _stopped():
            print("⏹ FULL LOOP STOPPED BY USER (nach Bass)")
            return None, None

        print("-> Step 4: Generating Melody...")
        _step(4, "🎶 Melody...")
        wav_m, mid_m = create_melody_files(root, scale, bpm, bars, time_sig, octave, mode, density, swing, human, sound, genre, prog, output_dir, arr_mode)
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
        sf.write(full_wav_path, final_mix, sr)

        print("✅ --- FULL 6-TRACK LOOP COMPLETED ---")
        return full_wav_path, full_mid_path

    except Exception as e:
        print(f"❌ CRITICAL FULL LOOP ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    
def generate_pad_midi(root, scale, bars, prog, output_dir):
    """Spur 5: Erzeugt lange, liegende Akkorde auf Kanal 4 (Chromatisch sicher)."""
    mid_path = os.path.join(output_dir, "generated_pads.mid")
    mid = MidiFile(); track = MidiTrack(); mid.tracks.append(track)
    track.append(MetaMessage('track_name', name='Ambient Pads'))
    
    intervals = SCALES.get(scale, SCALES["Minor"])
    base_note = NOTES.get(root, 0) + 48 
    scale_notes = []
    for oct_off in [0, 12, 24]:
        for i in intervals: scale_notes.append(base_note + oct_off + i)
    
    prog_data = None
    for key in PROGRESSIONS.keys():
        if key != "Random" and key in prog:
            prog_data = PROGRESSIONS[key]; break
    
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

def generate_strings_midi(root, scale, bars, prog, genre, output_dir):
    """Spur 6: Erzeugt intelligente Streicher auf Kanal 5 (Chromatisch sicher)."""
    mid_path = os.path.join(output_dir, "generated_strings.mid")
    mid = MidiFile(); track = MidiTrack(); mid.tracks.append(track)
    track.append(MetaMessage('track_name', name='Orchestral Strings'))
    
    intervals = SCALES.get(scale, SCALES["Minor"])
    base_note_ref = NOTES.get(root, 0) + 60 
    scale_notes = []
    for oct_off in [0, 12, 24]:
        for i in intervals: scale_notes.append(base_note_ref + oct_off + i)
    
    prog_data = None
    for key in PROGRESSIONS.keys():
        if key != "Random" and key in prog:
            prog_data = PROGRESSIONS[key]; break

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