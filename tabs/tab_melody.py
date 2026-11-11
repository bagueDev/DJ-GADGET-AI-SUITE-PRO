# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
import pygame
import shutil
import sys
import tempfile
import secrets

try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import melody_generator
except ImportError:
    melody_generator = None
    
    

class MelodyTab(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.app = main_app
        self.gen_wav = None
        self.gen_mid = None
        self.gen_seed = None   # Seed des aktuellen Ergebnisses (für Status & Dateiname)
        self.bind("<Button-1>", lambda e: self.focus_set())
        # P1/P2-State: Zähler pro Generierungsart (stale Results verwerfen),
        # Busy-Guard gegen Thread-Stau, Preview-Debounce, Full-Loop-Stop.
        self._counters = {"gen": 0, "preview": 0, "loop": 0}
        self._busy_kind = None
        self._preview_after_id = None
        self._full_loop_stop = threading.Event()
        # P2: Alte Temp-Renderings beim Start aufräumen
        for _tmp in ("DJ_Suite_Melody", "DJ_Suite_Preview", "DJ_Suite_FullLoop"):
            try:
                shutil.rmtree(os.path.join(tempfile.gettempdir(), _tmp), ignore_errors=True)
            except Exception:
                pass
        
        # --- SECTION 1: GENERATOR ---
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(pady=5)
        ctk.CTkLabel(top_bar, text="🎹 Generator Mode:", font=("Arial", 16, "bold")).pack(side="left", padx=10)
        
        # DER SWITCH (Melody vs Drums)
        # Ändere diese Zeile in deiner __init__:
        self.gen_type = ctk.CTkOptionMenu(
            top_bar, 
            values=["🎶 Melody", "🥁 Drums", "🎹 Chords"], # <--- Chords hier hinzufügen
            command=self.toggle_generator_mode
        )
        self.gen_type.pack(side="left")
               
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(pady=5, padx=20, fill="x")
        
        # --- DYNAMISCHE UI ELEMENTE ---
        # --- Spalten-Konfiguration für das Split-Layout ---
        self.grid_frame.columnconfigure(2, minsize=60) # Puffer-Platz in der Mitte
        self.grid_frame.columnconfigure(4, weight=1)   # Die rechte Seite darf sich dehnen

        # ==========================================
        # LINKE SEITE: Einstellungen (Kompakt untereinander)
        # ==========================================

        # Reihe 0: Genre
        ctk.CTkLabel(self.grid_frame, text="🎼 Genre:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.mel_genre = ctk.CTkOptionMenu(
        self.grid_frame, 
        values=["Techno/Trance", "House/Deep", "Synthpop/80s", "HipHop", "Trap", "DnB/Breakbeat", "DnB/Rolling", "Jazz", "Reggae", "Reggaeton", "Oriental", "Ambient", "Random"], 
        command=self.handle_genre_change,
        width=140
             )
        self.mel_genre.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Reihe 1: Key
        self.lbl_root = ctk.CTkLabel(self.grid_frame, text="🔑🎵 Key:")
        self.lbl_root.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        self.mel_root = ctk.CTkOptionMenu(self.grid_frame, values=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'], width=140)
        self.mel_root.grid(row=0, column=3, padx=10, pady=5, sticky="w")

        # Reihe 2: Scale
        self.lbl_scale = ctk.CTkLabel(self.grid_frame, text="🎼 Scale:")
        self.lbl_scale.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.mel_scale = ctk.CTkOptionMenu(self.grid_frame, values=[
            "Major", 
            "Minor", 
            "Pentatonic Major", 
            "Pentatonic Minor",
            "Blues",
            "Locrian", 
            "Melodic Minor", 
            "Lydian", 
            "Dorian", 
            "Phrygian",
            "Double Harmonic (Byzantine)", 
            "Hungarian Minor", 
            "Hirajoshi (Japanese)", 
            "Harmonic Minor",
            "Mixolydian", 
            "Lydian Dominant", 
            "Super Locrian (Altered)", 
            "Whole Tone", 
            "Chromatic"
        ], width=140)
        self.mel_scale.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Reihe 3: BPM
        ctk.CTkLabel(self.grid_frame, text="🥁⏱️ BPM:").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.mel_bpm = ctk.CTkEntry(self.grid_frame, width=140)
        self.mel_bpm.insert(0, "124")
        self.mel_bpm.grid(row=1, column=3, padx=10, pady=5, sticky="w")
        # Registriere die Validierung
        vcmd = (self.register(self.only_numbers), '%S')

        # Beim BPM Feld hinzufügen:
        self.mel_bpm.configure(validate="key", validatecommand=vcmd)
        # --- Bindings für BPM-Feld ---
        # Enter bestätigt die Zahl und nimmt den Fokus weg
        self.mel_bpm.bind("<Return>", lambda e: self.focus_set())
        # Leertaste im BPM-Feld löst direkt 'generate' aus, statt ein Leerzeichen zu tippen
        self.mel_bpm.bind("<space>", lambda e: self.generate_from_entry())
        self.mel_bpm.bind("<plus>", lambda e: self.generate_from_entry("full"))

        # Reihe 4: Bars
        # --- ZEILE 4: BARS (Jetzt als Eingabefeld statt Dropdown) ---
        ctk.CTkLabel(self.grid_frame, text="🧱 Bars:").grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.mel_bars = ctk.CTkEntry(self.grid_frame, width=140)
        self.mel_bars.insert(0, "8") # Standardwert: 8 Takte
        self.mel_bars.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.mel_bars.configure(validate="key", validatecommand=vcmd)
        # --- Bindings für Bars-Feld ---
        # Enter bestätigt die Zahl und nimmt den Fokus weg
        self.mel_bars.bind("<Return>", lambda e: self.focus_set())
        # Leertaste im Bars-Feld löst direkt 'generate' aus
        self.mel_bars.bind("<space>", lambda e: self.generate_from_entry())
        self.mel_bars.bind("<plus>", lambda e: self.generate_from_entry("full"))

        # Reihe 5: Time Sig
        ctk.CTkLabel(self.grid_frame, text="⏱️ Time Sig:").grid(row=2, column=2, padx=10, pady=5, sticky="w")
        self.mel_time = ctk.CTkOptionMenu(self.grid_frame, values=["4/4", "3/4", "6/8"], width=140)
        self.mel_time.grid(row=2, column=3, padx=10, pady=5, sticky="w")

        # Reihe 6: Octave
        self.lbl_oct = ctk.CTkLabel(self.grid_frame, text="🎵 Octave:")
        self.lbl_oct.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.mel_oct = ctk.CTkOptionMenu(self.grid_frame, values=["Bass (Low)",  "Deep (Mid-Low)", "Mid (Standard)", "Lead (High)"], width=140)
        self.mel_oct.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        # Reihe 7: Mode (Polyphonie)
        self.lbl_mode = ctk.CTkLabel(self.grid_frame, text="🎼 Mode:")
        self.lbl_mode.grid(row=3, column=2, padx=10, pady=5, sticky="w")
        self.mel_mode = ctk.CTkOptionMenu(self.grid_frame, values=[
            "Melody (Mono)", 
            "Power (5ths)", 
            "Triads (3-Note)", 
            "7ths (4-Note)", 
            "9ths (5-Note)",
            "Sus2 (Open)", 
            "Sus4 (Tension)", 
            "Add9 (Lush)", 
            "6/9 (Jazz)"
        ], width=140)       
        self.mel_mode.grid(row=3, column=3, padx=10, pady=5, sticky="w")
        # --- ZEILE 5: SOUND-TYP ---
        self.lbl_sound = ctk.CTkLabel(self.grid_frame, text="🔊 Waveform:")
        self.lbl_sound.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        

        self.mel_sound = ctk.CTkOptionMenu(self.grid_frame, values=["sine", "saw", "square","epiano"], width=140)
        self.mel_sound.grid(row=5, column=1, padx=10, pady=5, sticky="w")
        self.mel_sound.configure(command=self.trigger_preview)
        # ==========================================
        # RECHTE SEITE: Akkord-Progression (Oben fixiert)
        # ==========================================
        right_padding = (15, 15) # Einheitlicher Abstand zwischen den Boxen
        self.lbl_prog = ctk.CTkLabel(self.grid_frame, text="🎼 Chord Progression Preset:", font=("Arial", 13, "bold"))
        self.lbl_prog.grid(row=0, column=5, padx=right_padding, pady=(10, 0), sticky="w")

        self.mel_prog = ctk.CTkOptionMenu(self.grid_frame, values=[
            "Random",
            "--- 🎧 TOP 5 HITS ---",
        "⭐ Pop Anthem: 1-5-6-4",
        "⭐ Universal Pop: 4-1-5-6",
        "🌅 Dreamy Pop: 1-6-2-5",
        "⚡ Energetic Pop: 5-6-4-1",
        "🎶 Indie Pop: 6-1-3-7",
        "🔄 Retro Pop: 1-6-4-5",
        "💔 Emotional: 6-4-1-5",
        "🎼 Circle of 5ths: 1-4-7-3",
        "--- 🏠 HOUSE ---",
        "🏠Deep House: 1-7-6-5",
        "🌞 Piano House: 4-3-6-5",
        "🌀 Melodic House: 6-1-3-7",
        "🔊 Techno/Minimal: 1-5 Loop",
        "🏝️ Tropical House: 1-5-6-4",
        "🏠Classic House: 1-4 Loop",
        "🕺 Soulful: 2-5-1-6",
        "--- 🚀 DRUM & BASS ---",
        "🚀 Liquid DnB: 6-4-1-5",
        "🌫 Liquid Alt: 4-6-1-5",
        "🔥 Neurofunk: 1-b2-b3-b2",
        "🌌 Atmospheric: 1-2-4-2",
        "🧊 Minimal DnB: 1-5",
        "--- 🎛️ HIP HOP & TRAP ---",
        "🥁 Boom Bap: 1-4",
        "🎷 Jazz-Hop: 2-5-1-4",
        "🌑 Dark Trap: 6-5-4-5",
        "🎹 Soul / RnB: 1-3-4-3",
        "🧨 Drill: 6-b6-5-b5",
        "🌤 Lo-Fi: 1-3-2-5",
        "🎛️ Modern Trap: 1-6 Tension",
        "--- 🎷 JAZZ LIBRARY ---",
        "🎷 Jazz: Major ii-V-I",
        "🎻 Jazz: Minor ii-V-I",
        "🔄 Jazz: Rhythm Changes",
        "🔥 Jazz: Tritone Sub",
        "🌃 Jazz: Romantic (IV-iv-I)",
        "🏃 Jazz: Giant",
                
        "--- 🦁 REGGAE & DUB ---",
        "🎸 Reggae: I-IV Loop",
        "🌅 Reggae: Chill (I-ii)",
        "🇯🇲 Reggae: Roots (i-VII)",
        "☀️ Reggae: Positive (I-IV-V-IV)",
        "❤️ Reggae: Lovers Rock (I-vi-IV-V)",
        "--- 🌍 STYLE / WORLD ---",
        "🕌 Middle Eastern: 1-b2-b3-5",
        "🇧🇷 Samba: 2-5-3-6",
        "🇪🇸 Flamenco: 1-b7-b6-5",
        "🇯🇵 Japanese: 1-b3-4-b6",
        "🕌 Oriental: 1-b1-2-3"

        ], width=180, height=35)
        # Etwas größer für die rechte Seite
        self.mel_prog.grid(row=1, column=5, padx=right_padding, pady=(5,10), sticky="w")
        self.mel_prog.configure(command=self.trigger_preview)

        # Kleiner Info-Text unter der Progression (optional)
        self.lbl_prog_info = ctk.CTkLabel(self.grid_frame, text="Select a chord recipe to\nforce specific harmonics.", 
                                        font=("Arial", 11), text_color="gray", justify="left")
        self.lbl_prog_info.grid(row=2, column=5, padx=(20, 10), sticky="w")
        
        # Definiere hier am Anfang der Widget-Konfiguration die Standardwerte:
        is_chords = False  # Beim Start ist "Melody" aktiv, also ist Chords False
        is_melody = True
        # --- VOICING STYLE (Rechte Seite, unter Progression) ---
        self.lbl_voicing = ctk.CTkLabel(self.grid_frame, text="🎹 Voicing / Inversion:", font=("Arial", 13, "bold"))
        self.lbl_voicing.grid(row=0, column=4, padx=right_padding, pady=(10, 0), sticky="w")

        self.mel_voicing = ctk.CTkOptionMenu(self.grid_frame, values=[
            "Root Position", 
            "1st Inversion", 
            "2nd Inversion", 
            "Smart Smooth"
        ], width=180,height=35)
        self.mel_voicing.grid(row=1, column=4, padx=right_padding, pady=(5, 10), sticky="w")
        self.mel_voicing.configure(command=self.trigger_preview)

        # In der toggle_generator_mode Funktion musst du das Menü auch aktivieren/deaktivieren:
        # (Füge das einfach zu deiner bestehenden toggle_generator_mode hinzu)
        state_v = "normal" if is_chords else "disabled"
        self.mel_voicing.configure(state=state_v, fg_color="#E65100" if is_chords else "gray")
        self.lbl_voicing.configure(text_color="white" if is_chords else "gray")
        
        
        # --- ARRANGEMENT MODE (Rechte Seite, unter Bass Complexity) ---
        self.lbl_arrangement = ctk.CTkLabel(self.grid_frame, text="🎬 Arrangement Structure:", font=("Arial", 13, "bold"))
        self.lbl_arrangement.grid(row=0, column=6, padx=right_padding, pady=(10, 0), sticky="w")

        self.mel_arrangement = ctk.CTkOptionMenu(self.grid_frame, values=[
            "♾️ Infinite Loop", 
            "📻 Radio Edit (Pop)", 
            "💃 Club Mix (Extended)",
            "🚀 DnB Journey",
            "🗽 East Coast Style", 
            "🌴 Westcoast Style",  
            "🧨 Trap/HipHop Hook",
            "🌊 Ambient Wave", 
            "💥 Impact / Trailer", 
            "🎬 Cinematic Build"
        ], width=140, height=35)
        self.mel_arrangement.grid(row=1, column=6, padx=right_padding, pady=(5, 10), sticky="w")
        # Arrangement-Menü aktivieren
        active_arr = is_chords or is_melody
        state_arr = "normal" if active_arr else "disabled"
        color_arr = "#E65100" if is_chords else ("#3B8ED0" if is_melody else "gray")

        self.mel_arrangement.configure(state=state_arr, fg_color=color_arr)
        self.lbl_arrangement.configure(text_color="white" if active_arr else "gray")                                
        
        # --- BASS STYLE (Rechte Seite, unter Voicing) ---
        self.lbl_bass_style = ctk.CTkLabel(self.grid_frame, text="🎸 Complexity:", font=("Arial", 13, "bold"))
        self.lbl_bass_style.grid(row=5, column=2, padx=(10, 5), pady=(5, 10), sticky="nw")

        self.mel_bass_style = ctk.CTkOptionMenu(self.grid_frame, values=[
            "Simple (Root)", 
            "Steady (Groove)", 
            "Busy (Melodic)", 
            "Jazz Walking",
            "--- 💎 PATTERNS ---",
            "Standard 1/4s",
            "Driving 1/8s",
            "Offbeat Start (Beat 2)",
            "Fake Triplet (3-3-2)",
            "The Donk (Dotted 1/8s)",
            "Footwork (Hectic)",
            "Dembow (Reggaeton)",
            "Neuro Roller",
            "Syncopator (Complex)"
        ], width=140)
        self.mel_bass_style.grid(row=5, column=3, padx=(10, 5), pady=(5, 10), sticky="nw")
        
        
        # --------------Sliders
        slider_frame = ctk.CTkFrame(self, fg_color="transparent")
        slider_frame.pack(pady=5, fill="x", padx=50)
        
        ctk.CTkLabel(slider_frame, text="🌀 Density:").pack(side="left", padx=5)
        self.mel_density = ctk.CTkSlider(slider_frame, from_=10, to=100, width=100)
        self.mel_density.set(80)
        self.mel_density.pack(side="left", padx=5)
        
        ctk.CTkLabel(slider_frame, text="🕺 Swing:").pack(side="left", padx=(20, 5))
        self.mel_swing = ctk.CTkSlider(slider_frame, from_=0, to=100, width=100)
        self.mel_swing.set(0)
        self.mel_swing.pack(side="left", padx=5)
        
        # Seed: gleiche Zahl + gleiche Einstellungen = gleiches Ergebnis
        ctk.CTkLabel(slider_frame, text="🎲 Seed:").pack(side="left", padx=(20, 5))
        # Bewusst ohne placeholder_text: die Nur-Ziffern-Validierung würde verhindern,
        # dass CustomTkinter den Platzhalter wieder löscht ("123456random").
        self.mel_seed = ctk.CTkEntry(slider_frame, width=80)
        self.mel_seed.pack(side="left", padx=5)
        self.mel_seed.configure(validate="key", validatecommand=vcmd)
        self.mel_seed.bind("<Return>", lambda e: self.focus_set())
        self.mel_seed_lock = ctk.CTkCheckBox(slider_frame, text="🔒 Lock", width=70)
        self.mel_seed_lock.pack(side="left", padx=5)

        self.mel_human = ctk.CTkCheckBox(slider_frame, text="🤖➡️🧑  Humanize")
        self.mel_human.pack(side="right", padx=20)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        self.btn_generate = ctk.CTkButton(btn_frame, text="🎲 Generate", command=self.generate, font=("Arial", 14, "bold"), fg_color="#E65100")
        self.btn_generate.pack(side="left", padx=10)
        self.btn_play = ctk.CTkButton(btn_frame, text="▶ Play", command=self.play, state="disabled", fg_color="gray")
        self.btn_play.pack(side="left", padx=5)
        
        # Neben dem normalen Generate-Button
        self.btn_full_loop = ctk.CTkButton(
            btn_frame, 
            text="✨ Full Loop", 
            command=self.generate_full_loop, 
            font=("Arial", 14, "bold"), 
            fg_color="#6200EA", # Lila für "Special"
            hover_color="#3700B3"
        )
        self.btn_full_loop.pack(side="left", padx=10)
        self.btn_stop_loop = ctk.CTkButton(
            btn_frame,
            text="⏹ Stop",
            command=self.stop_full_loop,
            fg_color="gray",
            state="disabled",
            width=70
        )
        self.btn_stop_loop.pack(side="left", padx=5)
        
        self.btn_save_midi = ctk.CTkButton(btn_frame, text="💾 MIDI", command=self.save_midi, state="disabled", fg_color="gray")
        self.btn_save_midi.pack(side="left", padx=5)
        
        
        self.mel_status = ctk.CTkLabel(self, text="", text_color="gray")
        self.mel_status.pack()
        
        # --- SECTION 2: CONVERTER (Bleibt gleich) ---
        ctk.CTkFrame(self, height=2, fg_color="gray").pack(fill="x", pady=20)
        ctk.CTkLabel(self, text="🔊 Audio to MIDI Converter (experimental)", font=("Arial", 18, "bold")).pack(pady=5)
        
        mid_box = ctk.CTkFrame(self)
        mid_box.pack(pady=10, fill="x", padx=50)
        self.audio_midi_entry = ctk.CTkEntry(mid_box, placeholder_text="📄🎧 Audio File (MP3/WAV).....")
        self.audio_midi_entry.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(mid_box, text="📂", width=40, command=self.browse_audio_midi_file).pack(side="left", padx=5)
        
        # Parameter für Converter
        conv_opts = ctk.CTkFrame(self, fg_color="transparent")
        conv_opts.pack(pady=5)
        self.midi_conv_mode = ctk.CTkOptionMenu(conv_opts, values=["🎶 Melody", "🥁 Drums", "🎹 Chords"], width=100)
        self.midi_conv_mode.pack(side="left", padx=5)
        # Threshold (Sensitivity) MIT WERT-ANZEIGE
        ctk.CTkLabel(conv_opts, text="🪶 Sens:").pack(side="left", padx=(15, 2))
        
        self.lbl_thresh = ctk.CTkLabel(conv_opts, text="0.10", text_color="#007aff", width=30)
        self.lbl_thresh.pack(side="left")
        self.midi_thresh = ctk.CTkSlider(
            conv_opts, 
            from_=0.0, 
            to=0.5, 
            width=80,
            command=lambda v: self.lbl_thresh.configure(text=f"{v:.2f}")
        )
        self.midi_thresh.set(0.1)
        self.midi_thresh.pack(side="left", padx=5)
        
        # Smoothing
        self.midi_smooth = ctk.CTkCheckBox(conv_opts, text="🧽 Smooth")
        self.midi_smooth.pack(side="left", padx=10)

        # BPM des Quell-Audios (leer = automatisch erkennen)
        ctk.CTkLabel(conv_opts, text="🥁 BPM:").pack(side="left", padx=(10, 2))
        self.midi_conv_bpm = ctk.CTkEntry(conv_opts, width=60, placeholder_text="auto")
        self.midi_conv_bpm.pack(side="left", padx=5)

        # Dauer
        ctk.CTkLabel(conv_opts, text="⏱ Dauer:").pack(side="left", padx=(10, 2))
        self.midi_conv_len = ctk.CTkOptionMenu(conv_opts, values=["20s", "10s", "40s", "Full"], width=70)
        self.midi_conv_len.set("20s")
        self.midi_conv_len.pack(side="left", padx=5)
        
        # Zweite Options-Zeile: Quelle & Raster
        conv_opts2 = ctk.CTkFrame(self, fg_color="transparent")
        conv_opts2.pack(pady=2)
        # Full mix: für ganze Lieder – trennt vor der Erkennung Schlag- und Ton-Anteil.
        # Bei trockenen Loops/Stems aus lassen (erzeugt dort Fehltreffer).
        self.midi_full_mix = ctk.CTkCheckBox(conv_opts2, text="🎚 Full mix (whole song)")
        self.midi_full_mix.pack(side="left", padx=10)
        # Grid: Noten auf das 16tel-Raster ziehen (braucht ein stimmiges BPM)
        self.midi_grid = ctk.CTkCheckBox(conv_opts2, text="🧲 Snap to 1/16 grid")
        self.midi_grid.pack(side="left", padx=10)
        ctk.CTkLabel(self, text="Rule-based detection, results vary. Best with a dry loop or a stem from Stems AI.",
                     font=("Arial", 11), text_color="gray").pack()

        ctk.CTkButton(mid_box, text="⚡ CONVERT", command=self.convert_audio_midi, fg_color="#007aff").pack(side="right", padx=5)
        self.midi_conv_status = ctk.CTkLabel(self, text="Ready.", text_color="gray")
        self.midi_conv_status.pack()

    def toggle_generator_mode(self, mode):
        is_chords = "Chords" in mode
        is_drums = "Drums" in mode
        is_melody = "Melody" in mode

        def _apply(widget, label, active, active_color):
            state = "normal" if active else "disabled"
            widget.configure(state=state, fg_color=active_color if active else "gray")
            if label is not None:
                label.configure(text_color="white" if active else "gray")

        # (Widget, Label, aktiv-wenn, Aktiv-Farbe)
        prog_active = is_chords or is_melody
        prog_color = "#E65100" if is_chords else "#3B8ED0"
        _apply(self.mel_prog, self.lbl_prog, prog_active, prog_color)
        _apply(self.mel_voicing, self.lbl_voicing, is_chords, "#E65100")
        _apply(self.mel_bass_style, self.lbl_bass_style, prog_active, prog_color)
        _apply(self.mel_oct, self.lbl_oct, is_melody, "#3B8ED0")
        common_active = is_melody or is_chords
        for w, lbl in ((self.mel_sound, self.lbl_sound),
                       (self.mel_root, self.lbl_root),
                       (self.mel_scale, self.lbl_scale),
                       (self.mel_mode, self.lbl_mode)):
            _apply(w, lbl, common_active, "#3B8ED0")
        # Arrangement: bei Drums deaktiviert (Drums-Threads ignorieren es sonst still)
        arr_active = is_chords or is_melody
        arr_color = "#E65100" if is_chords else "#3B8ED0"
        self.mel_arrangement.configure(
            state="normal" if arr_active else "disabled",
            fg_color=arr_color if arr_active else "gray")
        self.lbl_arrangement.configure(text_color="white" if arr_active else "gray")    
    def add_log(self, msg):
        """Schickt eine Nachricht an den Log-Tab."""
        if hasattr(self.app, 'log_tab'):
            self.app.log_tab.log(msg)    

    def _sanitize_inputs(self):
        """Liest BPM & Bars, clamp auf gültige Bereiche, schreibt zurück.
        Gibt (bpm:int, bars:int) zurück. Stürzt nie ab (P1)."""
        genre_default = 124
        try:
            if melody_generator and hasattr(melody_generator, "GENRE_PROFILES"):
                genre_default = melody_generator.GENRE_PROFILES.get(
                    self.mel_genre.get(), {}).get("bpm", 124)
        except Exception:
            pass
        try:
            bpm_raw = self.mel_bpm.get().strip()
            bpm = int(bpm_raw) if bpm_raw else genre_default
        except (ValueError, AttributeError):
            bpm = genre_default
            self.add_log("⚠️ Invalid BPM. Resetting to default.")
        bpm = max(20, min(300, bpm))
        try:
            bars_raw = self.mel_bars.get().strip()
            bars = int(bars_raw) if bars_raw else 4
        except (ValueError, AttributeError):
            bars = 4
            self.add_log("⚠️ Invalid Bars. Resetting to 4.")
        bars = max(1, min(128, bars))  # RAM-Schutz (128 ≈ 8 Min. @124 BPM)
        try:
            self.mel_bpm.delete(0, "end")
            self.mel_bpm.insert(0, str(bpm))
            self.mel_bars.delete(0, "end")
            self.mel_bars.insert(0, str(bars))
        except Exception:
            pass
        if bars > 64:
            self.add_log(f"⏳ Rendering long sequence ({bars} bars). Please wait...")
        return bpm, bars

    def _current_seed(self):
        """Seed aus dem Feld (None, wenn leer/ungültig)."""
        try:
            raw = self.mel_seed.get().strip()
            return int(raw) % 1_000_000 if raw else None
        except (ValueError, AttributeError):
            return None

    def _next_seed(self):
        """Seed für eine neue Generierung: bei 🔒 Lock der Wert im Feld,
        sonst neu gewürfelt. Schreibt den benutzten Wert ins Feld zurück."""
        seed = self._current_seed() if self.mel_seed_lock.get() else None
        if seed is None:
            seed = secrets.randbelow(1_000_000)
        self.mel_seed.delete(0, "end")
        self.mel_seed.insert(0, str(seed))
        return seed

    def _set_busy(self, kind):
        """Sperrt Generate/FullLoop während kind läuft (P2: kein Thread-Stau)."""
        self._busy_kind = kind
        busy = kind is not None
        state = "disabled" if busy else "normal"
        try:
            self.btn_generate.configure(state=state)
            self.btn_full_loop.configure(state=state)
        except Exception:
            pass

    def generate(self):
                # --- NEU: Bestehendes Playback sofort stoppen ---
        pygame.mixer.music.stop()
        self.update_play_button_state(False)

        if not melody_generator: return
        if self._busy_kind is not None:
            self.add_log("⏳ Generation already running. Please wait or stop it.")
            return

        mode_type = self.gen_type.get()
        output_dir = os.path.join(tempfile.gettempdir(), "DJ_Suite_Melody")

        # --- SICHERER DATEN-CHECK (zentral, P1) ---
        bpm, bars = self._sanitize_inputs()
        seed = self._next_seed()
        self.add_log(f"🎲 Seed: {seed}")
        self._counters["gen"] += 1
        counter = self._counters["gen"]
        self._set_busy("gen")

        self.mel_status.configure(text="Generating...", text_color="yellow")


        # WICHTIG: Nutze jetzt in den Threads unten die Variable 'bars'
        # (die Zahl), nicht mehr 'self.mel_bars.get()' (den Text)!

        if "Drums" in mode_type:
            threading.Thread(target=self._run_drum_gen, args=(
                self.mel_genre.get(), bpm, bars, int(self.mel_density.get()),
                int(self.mel_swing.get()), bool(self.mel_human.get()), output_dir, self.mel_time.get(),
                self.mel_arrangement.get(), "gen", counter, seed,
            )).start()

        elif "Chords" in mode_type:
            prog = self.mel_prog.get()
            self.add_log(f"🎹 Starting Chord Generation: {self.mel_root.get()} {self.mel_scale.get()} - {prog}")
            if prog.strip().startswith("---"):
                self.add_log("⚠️ Info: Header selected, switching to Random mode.")
                prog = "Random"

            threading.Thread(target=self._run_chord_gen, args=(
                self.mel_root.get(), self.mel_scale.get(), bpm, bars,
                prog, self.mel_mode.get(), output_dir, self.mel_voicing.get(),
                self.mel_sound.get(), self.mel_genre.get(), # Genre
                int(self.mel_density.get()), # Density
                int(self.mel_swing.get()),   # Swing
                self.mel_time.get(),         # Time Sig
                bool(self.mel_human.get()),  # Humanize
                self.mel_arrangement.get(),  # Arrangement
                "gen", counter, seed,
            )).start()

        else: # Melody
            #else: # Melody Mode
            # Wir holen die Progression für den Harmony-Link
            prog = self.mel_prog.get()
            if prog.strip().startswith("---"):
                self.add_log("⚠️ Info: Header selected, switching to Random mode.")
                prog = "Random"
            self.add_log(f"🎶 Starting Melody Generation: {self.mel_root.get()} {self.mel_scale.get()} (Link: {prog})")

            # DER THREAD-AUFRUF (Exakt 15 Argumente in args)
            threading.Thread(target=self._run_mel_gen, args=(
                self.mel_root.get(),         # 1
                self.mel_scale.get(),        # 2
                bpm,                         # 3
                bars,                        # 4
                self.mel_time.get(),         # 5
                self.mel_oct.get(),          # 6
                self.mel_mode.get(),         # 7
                int(self.mel_density.get()), # 8
                int(self.mel_swing.get()),   # 9
                bool(self.mel_human.get()),  # 10
                self.mel_sound.get(),        # 11
                self.mel_genre.get(),        # 12
                prog,                        # 13
                output_dir,                  # 14
                self.mel_arrangement.get(),  # 15
                "gen", counter, seed,
            )).start()
                    
    def trigger_preview(self, value):
        # 1. Sicherheits-Check: Ist es eine Trennlinie?
        if isinstance(value, str) and value.startswith("---"):
            return
        # P2: Debounce (400ms) — schnelles Durchklicken startet nur 1 Render
        try:
            if self._preview_after_id is not None:
                self.after_cancel(self._preview_after_id)
        except Exception:
            pass
        self._preview_after_id = self.after(400, self._do_preview)

    def _do_preview(self):
        self._preview_after_id = None
        if self._busy_kind is not None:
            return  # Während einer Generierung keine Vorschau (würde nur dahinter warten)
        # 2. Laufende Musik sofort stoppen
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        # 3. Parameter sammeln (zentral sanitized, P1 — stürzt nie ab)
        mode_type = self.gen_type.get()
        bpm, _ = self._sanitize_inputs()
        preview_bars = 2 # Kurz und knackig für die Vorschau

        # Separater Ordner für Previews (um Hauptdateien nicht zu überschreiben)
        preview_dir = os.path.join(tempfile.gettempdir(), "DJ_Suite_Preview")

        # Vorschau nutzt den Seed im Feld: gleiche Noten, neuer Sound/neue Einstellung
        seed = self._current_seed()

        self.mel_status.configure(text="Preview...", text_color="#007aff")
        self._counters["preview"] += 1
        counter = self._counters["preview"]

        # 4. Den passenden Thread starten (ähnlich wie generate)
        if "Drums" in mode_type:
            threading.Thread(target=self._run_drum_gen, args=(
                self.mel_genre.get(), bpm, preview_bars,
                int(self.mel_density.get()), int(self.mel_swing.get()),
                bool(self.mel_human.get()), preview_dir, self.mel_time.get(),
                self.mel_arrangement.get(), "preview", counter, seed,
            ), daemon=True).start()

        elif "Chords" in mode_type:
            prog = self.mel_prog.get()
            if prog.strip().startswith("---"):
                prog = "Random"
            threading.Thread(target=self._run_chord_gen, args=(
                self.mel_root.get(), self.mel_scale.get(), bpm, preview_bars,
                prog, self.mel_mode.get(), preview_dir,
                self.mel_voicing.get(), self.mel_sound.get(), self.mel_genre.get(),
                int(self.mel_density.get()), int(self.mel_swing.get()),
                self.mel_time.get(), bool(self.mel_human.get()),
                self.mel_arrangement.get(), "preview", counter, seed,
            ), daemon=True).start()

        else: # Melody
            prog = self.mel_prog.get()
            if prog.strip().startswith("---"):
                prog = "Random"
            threading.Thread(target=self._run_mel_gen, args=(
                self.mel_root.get(), self.mel_scale.get(), bpm, preview_bars,
                self.mel_time.get(), self.mel_oct.get(), self.mel_mode.get(),
                int(self.mel_density.get()), int(self.mel_swing.get()),
                bool(self.mel_human.get()), self.mel_sound.get(),
                self.mel_genre.get(), prog, preview_dir,
                self.mel_arrangement.get(), "preview", counter, seed,
            ), daemon=True).start()
    # Neuer Wrapper für den Chord-Thread
    # --- 1. CHORD GENERATOR WRAPPER ---
    def _run_chord_gen(self, root, scale, bpm, bars, prog, mode, output_dir, voicing, sound, genre, density, swing, time_sig, human, arr_mode, kind="gen", counter=0, seed=None):
        try:
            melody_generator.clear_last_error()
            w, m = melody_generator.create_chord_files(
                root, scale, bpm, bars, prog, mode, output_dir, voicing, sound, genre, density, swing, time_sig, human, arr_mode, seed=seed
            )
        except Exception as e:
            self.after(0, lambda err=e: self._fail(kind, counter, err))
            return
        err = melody_generator.get_last_error()
        self.after(0, lambda: self.done(w, m, kind, counter, err, seed))

    # --- 2. MELODY GENERATOR WRAPPER ---
    def _run_mel_gen(self, root, scale, bpm, bars, time_sig, octave, mode, density, swing, human, sound, genre, prog, output_dir, arr_mode, kind="gen", counter=0, seed=None):
        try:
            melody_generator.clear_last_error()
            w, m = melody_generator.create_melody_files(
                root, scale, bpm, bars, time_sig, octave, mode, density, swing, human, sound, genre, prog, output_dir, arr_mode, seed=seed
            )
        except Exception as e:
            self.after(0, lambda err=e: self._fail(kind, counter, err))
            return
        err = melody_generator.get_last_error()
        self.after(0, lambda: self.done(w, m, kind, counter, err, seed))

    # --- 3. DRUM GENERATOR WRAPPER ---
    def _run_drum_gen(self, genre, bpm, bars, density, swing, human, output_dir, time_sig, arr_mode, kind="gen", counter=0, seed=None):
        try:
            melody_generator.clear_last_error()
            w, m = melody_generator.create_drum_files(
                genre, bpm, bars, density, swing, human, output_dir, time_sig, arr_mode, seed=seed
            )
        except Exception as e:
            self.after(0, lambda err=e: self._fail(kind, counter, err))
            return
        err = melody_generator.get_last_error()
        self.after(0, lambda: self.done(w, m, kind, counter, err, seed))
        
    def _finish_busy(self, kind):
        if self._busy_kind == kind:
            self._set_busy(None)
        if kind == "loop":
            try:
                self.btn_stop_loop.configure(state="disabled", fg_color="gray")
            except Exception:
                pass

    def _fail(self, kind, counter, err):
        """Fehlerpfad (P1): stale Results ignorieren, Status nie hängen lassen."""
        if counter != self._counters.get(kind, 0):
            return
        if kind == "loop" and self._full_loop_stop.is_set():
            self.mel_status.configure(text="⏹ Stopped", text_color="gray")
            self.add_log("⏹ Full Loop stopped by user.")
        else:
            self.mel_status.configure(text="❌ Error", text_color="red")
            self.add_log(f"❌ Generation failed: {err}")
        self._finish_busy(kind)

    def done(self, w, m, kind="gen", counter=0, err=None, seed=None):
        """Wird aufgerufen, wenn der Thread fertig ist."""
        if counter != self._counters.get(kind, 0):
            return  # Veraltetes Ergebnis (P2) — neuere Generierung läuft
        if not w:
            # Generator hat abgebrochen (Stop) oder ist gescheitert -> gemeinsamer Fehlerpfad
            self._fail(kind, counter, err or "no output (see terminal)")
            return
        if kind == "preview":
            self._play_preview(w)
        else:
            self.show_ready_status(w, m, seed)
        self._finish_busy(kind)

    def _play_preview(self, w):
        """Spielt die 2-Takt-Vorschau ab, ohne das generierte Ergebnis
        (gen_wav / gen_mid für Play & MIDI-Export) zu ersetzen."""
        if self._busy_kind is not None:
            self.mel_status.configure(text="Generating...", text_color="yellow")
        elif self.gen_wav:
            self.mel_status.configure(text="✅ Ready!" + (f"  (Seed {self.gen_seed})" if self.gen_seed is not None else ""), text_color="green")
        else:
            self.mel_status.configure(text="", text_color="gray")
        try:
            pygame.mixer.music.load(w)
            pygame.mixer.music.play()
        except Exception as e:
            self.add_log(f"❌ Preview Playback Error: {e}")
                    
    def show_ready_status(self, w, m, seed=None):
        """Finaler Status nach der künstlichen Verzögerung (UX-Delay Phase 2)."""
        self.gen_wav = w
        self.gen_mid = m
        self.gen_seed = seed
        
        # Finale Meldung
        self.mel_status.configure(text="✅ Ready!" + (f"  (Seed {seed})" if seed is not None else ""), text_color="green")
        
        # Buttons freischalten
        self.btn_play.configure(state="normal", fg_color="#007aff")
        self.btn_save_midi.configure(state="normal", fg_color="green")
        
        # Log-Eintrag
        filename = os.path.basename(w)
        self.add_log(f"✅ Success! Sequence created: {filename}")        

    def play(self):
        """Wechselt zwischen Play und Stop."""
        if not self.gen_wav or not os.path.exists(self.gen_wav):
            return

        # Prüfen, ob der Mixer gerade beschäftigt ist (Musik läuft)
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            self.update_play_button_state(False)
            self.add_log("⏹ Playback stopped.")
        else:
            try:
                pygame.mixer.music.load(self.gen_wav)
                pygame.mixer.music.play()
                self.update_play_button_state(True)
                self.add_log(f"▶ Playing: {os.path.basename(self.gen_wav)}")
                
                # Starte die automatische Überwachung des Endes
                self.monitor_playback()
            except Exception as e:
                self.add_log(f"❌ Playback Error: {e}")

    def save_midi(self):
        if self.gen_mid:
            name = os.path.splitext(os.path.basename(self.gen_mid))[0]
            if self.gen_seed is not None: name += f"_seed{self.gen_seed}"
            f = filedialog.asksaveasfilename(defaultextension=".mid", initialfile=name + ".mid")
            if f:
                shutil.copy2(self.gen_mid, f)
                self.add_log(f"✅ MIDI saved to: {os.path.basename(f)}")
                
                # --- DIESE ZEILEN STEHLEN DEN FOKUS ZURÜCK ---
                self.app.lift()          # Bringt das Fenster nach vorne
                self.app.focus_force()   # Erzwingt den Keyboard-Fokus
                # ---------------------------------------------

    # ... (Restliche Converter Funktionen: browse_audio_midi_file, convert_audio_midi etc. bleiben gleich) ...
    def browse_audio_midi_file(self):
        f = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.flac *.aiff")])
        if f: 
            self.audio_midi_entry.delete(0, "end")
            self.audio_midi_entry.insert(0, f)
            # BPM-Feld aus dem Analyzer vorbelegen (leer = Auto-Erkennung)
            self.midi_conv_bpm.delete(0, "end")
            bpm = self._analyzer_bpm(f)
            if bpm:
                self.midi_conv_bpm.insert(0, f"{bpm:g}")
                self.add_log(f"🥁 BPM from Analyzer: {bpm:g} ({os.path.basename(f)})")
            self.app.lift()
            self.app.focus_force()

    def _analyzer_bpm(self, path):
        """BPM des Tracks aus dem Analyzer-Tab (None, wenn dort nicht gescannt)."""
        try:
            tab = self.app.analyze_tab
            target = os.path.realpath(path)
            tracks = list(getattr(tab, "data_map", {}).values()) + list(getattr(tab, "all_tracks", []))
            for t in tracks:
                p = t.get("Pfad")
                if p and os.path.realpath(p) == target:
                    bpm = float(t.get("BPM", 0) or 0)
                    if 20 <= bpm <= 300:
                        return bpm
        except Exception as e:
            self.add_log(f"⚠️ Analyzer BPM lookup failed: {e}")
        return None

    def convert_audio_midi(self):
        if not melody_generator: messagebox.showerror("Error", "melody_generator missing!"); return
        fpath = self.audio_midi_entry.get()
        if not os.path.exists(fpath): return
        
        mode = self.midi_conv_mode.get().lower()
        
        # Dauer parsen
        dur_str = self.midi_conv_len.get()
        duration = 20
        if "10s" in dur_str: duration = 10
        elif "20s" in dur_str: duration = 20
        elif "40s" in dur_str: duration = 40
        elif "Full" in dur_str: duration = 0
        
        # Neue Parameter
        thresh = self.midi_thresh.get()
        smooth = bool(self.midi_smooth.get())
        
        # BPM: leer = automatisch erkennen, sonst 20-300 (Komma oder Punkt)
        bpm = None
        bpm_raw = self.midi_conv_bpm.get().strip().replace(",", ".")
        if bpm_raw:
            try:
                bpm = float(bpm_raw)
            except ValueError:
                bpm = 0
            if not (20 <= bpm <= 300):
                self.midi_conv_status.configure(text="❌ BPM must be 20-300 (or empty = auto)", text_color="red")
                return
        bpm_source = "manual" if bpm else "detected"
        if not bpm:
            # Pfad getippt/eingefügt statt per 📂 gewählt -> trotzdem Analyzer fragen
            bpm = self._analyzer_bpm(fpath)
            if bpm: bpm_source = "analyzer"

        out_path = os.path.splitext(fpath)[0] + "_extracted.mid"
        # Vorhandene Datei nicht stillschweigend überschreiben:
        # Yes = überschreiben, No = unter anderem Namen speichern, Cancel = abbrechen
        if os.path.exists(out_path):
            choice = messagebox.askyesnocancel(
                "File exists",
                f"{os.path.basename(out_path)} already exists.\n\n"
                "Yes = overwrite it\nNo = save under a different name\nCancel = do nothing")
            if choice is False:
                # Nächsten freien Namen vorschlagen (…_extracted_2.mid, _3, …)
                base = os.path.splitext(out_path)[0]
                n = 2
                while os.path.exists(f"{base}_{n}.mid"):
                    n += 1
                out_path = filedialog.asksaveasfilename(
                    title="Save MIDI as", defaultextension=".mid", filetypes=[("MIDI", "*.mid")],
                    initialdir=os.path.dirname(out_path), initialfile=os.path.basename(f"{base}_{n}.mid"))
            self.app.lift()
            self.app.focus_force()
            if choice is None or not out_path:
                return

        full_mix = bool(self.midi_full_mix.get())
        grid = bool(self.midi_grid.get())
        self.midi_conv_status.configure(text="Analyze (may take a while)...", text_color="yellow")
        
        threading.Thread(target=self._run_conv, args=(fpath, out_path, mode, duration, thresh, smooth, bpm, bpm_source, full_mix, grid)).start()

    def _run_conv(self, f, o, m, d, t, s, bpm=None, bpm_source="detected", full_mix=False, grid=False):
        err = None
        used_bpm = None
        extra = None  # Chords-Modus: Tonart + Akkordfolge
        try:
            melody_generator.clear_last_error()
            ok = melody_generator.audio_to_midi(f, o, m, d, t, s, bpm, separate=full_mix, quantize=grid)
            used_bpm = melody_generator.get_last_bpm()
            chords = melody_generator.get_last_chords()
            if ok and chords:
                extra = (melody_generator.get_last_key(), chords)
            if not ok: err = melody_generator.get_last_error()
        except Exception as e:
            err = f"Converter crashed: {e}"
            ok = False
        self.after(0, lambda: self.conv_done(ok, o, err, used_bpm, bpm_source, extra))

    def conv_done(self, success, path, err=None, bpm=None, bpm_source="detected", extra=None):
        if not success:
            self.add_log(f"❌ Audio to MIDI failed: {err or 'unknown error'}")
        if success:
            bpm_txt = f"{bpm:g} BPM ({bpm_source})" if bpm else "? BPM"
            self.midi_conv_status.configure(text=f"✅ Saved: {os.path.basename(path)} @ {bpm_txt}", text_color="green")
            self.add_log(f"✅ Audio to MIDI: {os.path.basename(path)} @ {bpm_txt}")
            info = f"MIDI file created:\n{path}\n\nTempo: {bpm_txt}"
            if extra:
                key, chords = extra
                shown = " | ".join(chords[:16]) + (" | ..." if len(chords) > 16 else "")
                self.add_log(f"🎹 Key (approx.): {key}")
                self.add_log(f"🎹 Chords: {' | '.join(chords)}")
                info += f"\n\nKey (approx.): {key}\nChords: {shown}"
            messagebox.showinfo("Success", info)
        else:
            self.midi_conv_status.configure(text="❌ Failure", text_color="red")

    def set_font_size(self, size):
        pass
    
    def generate_full_loop(self):
        """Startet die Generierung aller Spuren gleichzeitig."""
        if not melody_generator: return
        if self._busy_kind is not None:
            self.add_log("⏳ Generation already running. Please wait or stop it.")
            return

        bpm, bars = self._sanitize_inputs()
        seed = self._next_seed()
        self.add_log(f"🎲 Seed: {seed}")
        output_dir = os.path.join(tempfile.gettempdir(), "DJ_Suite_FullLoop")

        self.add_log(f"🚀 GENERATING FULL LOOP: {self.mel_root.get()} {self.mel_scale.get()} - {self.mel_genre.get()}")
        self.mel_status.configure(text="Creating Loop (1/6)...", text_color="purple")
        self._counters["loop"] += 1
        counter = self._counters["loop"]
        self._set_busy("loop")
        self._full_loop_stop.clear()
        try:
            self.btn_stop_loop.configure(state="normal", fg_color="#AA0000")
        except Exception:
            pass

        prog = self.mel_prog.get()
        if prog.strip().startswith("---"):
            self.add_log("⚠️ Info: Header selected, switching to Random mode.")
            prog = "Random"

        # Alle Parameter für alle Module sammeln
        args = (
            self.mel_root.get(),         # 1
            self.mel_scale.get(),        # 2
            bpm,                         # 3
            bars,                        # 4
            self.mel_time.get(),         # 5
            self.mel_oct.get(),          # 6
            self.mel_mode.get(),         # 7
            int(self.mel_density.get()), # 8
            int(self.mel_swing.get()),   # 9
            bool(self.mel_human.get()),  # 10
            self.mel_sound.get(),        # 11
            self.mel_genre.get(),        # 12
            prog,                        # 13
            self.mel_voicing.get(),      # 14
            self.mel_bass_style.get(),   # 15
            self.mel_arrangement.get(),
            output_dir,                  # 16
            "loop", counter, seed,
        )

        threading.Thread(target=self._run_full_loop, args=args, daemon=True).start()

    def stop_full_loop(self):
        """P2: Bricht den Full Loop zwischen den Stems ab."""
        if self._busy_kind != "loop":
            return
        self._full_loop_stop.set()
        self.mel_status.configure(text="Stopping...", text_color="yellow")
        self.add_log("⏹ Stopping Full Loop (finishes current stem)...")

    def _loop_progress(self, step, label, counter):
        if counter != self._counters.get("loop", 0):
            return
        self.after(0, lambda: self.mel_status.configure(
            text=f"Creating Loop ({step}/6): {label}", text_color="purple"))

    def _run_full_loop(self, root, scale, bpm, bars, t_sig, oct, mode, dens, sw, hum, snd, gen, prg, voi, b_style, arr_mode, d, kind="loop", counter=0, seed=None):
        try:
            melody_generator.clear_last_error()
            w, m = melody_generator.create_full_loop(
                root, scale, bpm, bars, t_sig, oct, mode, dens, sw, hum, snd, gen, prg, voi, b_style, arr_mode, d,
                progress_cb=lambda step, label: self._loop_progress(step, label, counter),
                stop_event=self._full_loop_stop, seed=seed)
        except Exception as e:
            self.after(0, lambda err=e: self._fail(kind, counter, err))
            return
        err = melody_generator.get_last_error()
        used_prog = melody_generator.get_last_progression()
        if w and used_prog and used_prog != prg:
            self.after(0, lambda: self.add_log(f"🎲 Random progression used: {used_prog}"))
        self.after(0, lambda: self.done(w, m, kind, counter, err, seed))
        
        
    def update_play_button_state(self, is_playing):
            """Ändert Text und Farbe des Play-Buttons."""
            if is_playing:
                self.btn_play.configure(text="⏹ Stop", fg_color="#E65100") # Orange/Rot für Stop
            else:
                self.btn_play.configure(text="▶ Play", fg_color="#007aff") # Blau für Play

    def monitor_playback(self):
            """Prüft alle 500ms, ob die Musik noch läuft."""
            if pygame.mixer.music.get_busy():
                # Wenn Musik noch läuft, in 500ms wieder prüfen
                self.after(500, self.monitor_playback)
            else:
                # Musik ist von alleine fertig -> Button zurücksetzen
                self.update_play_button_state(False)    
                
    def generate_from_entry(self, mode="single"):
        """Nimmt den Fokus vom Feld und startet die Generierung."""
        # 1. Fokus vom Eingabefeld wegnehmen
        self.focus_set()
        
        # 2. Entscheiden, was generiert werden soll
        if mode == "full":
            self.generate_full_loop()
        else:
            self.generate()
            
        # 3. Das "break" ist wichtig, damit das Zeichen (+ oder Space) 
        # nicht in das Textfeld geschrieben wird
        return "break" 
    
    def apply_genre_defaults(self, genre_name):
        """Findet das passende Profil, auch wenn Emojis im Namen sind."""
        print(f"DEBUG: Genre selected -> {genre_name}") # Zeigt uns im Terminal was passiert

        if not melody_generator or not hasattr(melody_generator, "GENRE_PROFILES"):
            print("DEBUG: GENRE_PROFILES not found in backend!")
            return

        # --- SMART LOOKUP ---
        profile = None
        # Wir suchen, ob ein Schlüssel aus dem Dictionary im gewählten Namen vorkommt
        # (z.B. "Techno" in "🎶 Techno/Trance")
        for key in melody_generator.GENRE_PROFILES.keys():
            if key in genre_name:
                profile = melody_generator.GENRE_PROFILES[key]
                print(f"DEBUG: Profile found for -> {key}")
                break
        
        if profile:
            # 1. BPM automatisch setzen
            self.mel_bpm.delete(0, "end")
            self.mel_bpm.insert(0, str(profile["bpm"]))
            
            # 2. Skala setzen
            self.mel_scale.set(profile["scale_suggestion"])
            
            # 3. Sound setzen
            self.mel_sound.set(profile["sound_suggestion"])
            
            # 4. Mode & Bass Style setzen
            self.mel_mode.set(profile["chord_mode"])
            self.mel_bass_style.set(profile["bass_style"])
            
            # 5. Rückmeldung im Log
            self.add_log(f"📋 Smart-Setup for {genre_name}: {profile['bpm']} BPM")
            
            # UI aktualisieren
            self.toggle_generator_mode(self.gen_type.get())
        else:
            print(f"DEBUG: No profile match for {genre_name}")
            
            
    def handle_genre_change(self, choice):
        """Zentrale Funktion für Genre-Wechsel: BPM anpassen + Preview."""
        # A. Zuerst: Die Standard-Werte (BPM, Skala etc.) laden
        self.apply_genre_defaults(choice)
        
        # B. Danach: Die Audio-Vorschau starten (falls du das noch willst)
        # Wenn du die Vorschau NICHT willst, lösche einfach die nächste Zeile:
        self.trigger_preview(choice)        
        
        
    def only_numbers(self, char):
        """Erlaubt nur Ziffern."""
        return char.isdigit() or char == ""        