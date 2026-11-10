# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import threading
import subprocess
import sys
import pandas as pd
import pygame
import soundfile as sf
import numpy as np
import time
import math
import librosa
import io
from PIL import Image
from helpers import (get_executable_path, CAMELOT_COLORS, import_playlist_file, 
                     show_details_popup, read_tags_quick, extract_cover_data,
                     reveal_in_finder, get_raw_metadata_string)

def get_worker_cmd(worker_type):
    cmd = [sys.executable]
    if not getattr(sys, 'frozen', False):
        main_script = os.path.abspath(sys.modules['__main__'].__file__)
        cmd.append(main_script)
    cmd.extend(["--worker", worker_type])
    return cmd

class AnalyzeTab(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.app = main_app
        
        # --- DATA STATE ---
        self.all_tracks = []
        self.data_map = {}
        # Zuletzt importierte/exportierte Playlist-Pfade (für Update-Button)
        self.last_playlist_paths = []
        self.filter_active = False  # True, solange die Tabelle nur einen gefilterten Ausschnitt zeigt
        self.drag_item = None
        self.undo_stack = []
        
        # --- PLAYER & ENGINE STATE ---
        self.current_playing_path = None
        self.playing_file = None
        self.is_paused = False
        self.manual_stop = False
        self.playback_offset = 0.0
        self.total_duration = 0.0
        self.track_bpm = 0
        
        # --- SAMPLER / PRO-LOOP STATE ---
        self.sampler_in = None
        self.sampler_out = None
        self.detected_beats = None
        self.is_looping = False
        self.exit_pending = False
        self.loop_channel = pygame.mixer.Channel(5)
        self.current_loop_sound = None
        self.loop_start_time = 0
        self.current_loop_duration = 0
        self.target_sync_time = 0
        
        # --- SCAN STATE ---
        self.is_scanning = False
        self.is_loading = False
        
        self.setup_ui()

    def setup_ui(self):
        # --- 1. FOLDER SELECTION ---
        folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        folder_frame.pack(fill="x", pady=(5, 0))
        ctk.CTkLabel(folder_frame, text="🗂️ Path:").pack(side="left", padx=5)
        self.local_path_entry = ctk.CTkEntry(folder_frame, placeholder_text="📄🎧 Please choose a valid file or folder!")
        self.local_path_entry.pack(side="left", fill="x", expand=True, padx=5)
        if self.app.path_entry.get(): self.local_path_entry.insert(0, self.app.path_entry.get())
        
        ctk.CTkButton(folder_frame, text="📂 Open", width=80, command=self.browse_local).pack(side="left", padx=5)
        ctk.CTkButton(folder_frame, text="📄 File+", width=80, fg_color="#444", command=self.add_files_dialog).pack(side="left", padx=5)
        #ctk.CTkButton(folder_frame, text="📜 Playlist", width=80, fg_color="#444", command=self.import_playlist_dialog).pack(side="left", padx=5)

       # --- 2. ACTION BAR ---
        act = ctk.CTkFrame(self)
        act.pack(fill="x", pady=5)
        self.var_write_tags = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(act, text="🏷️⚡ Auto-Tag", variable=self.var_write_tags, text_color="#ff5555", width=80).pack(side="left", padx=10)
        self.var_snap = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(act, text="🧲 Snap", variable=self.var_snap, width=60).pack(side="left", padx=10)
        self.var_polish = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(act, text="✨ Polish", variable=self.var_polish, width=60).pack(side="left", padx=5)
        self.var_trim = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(act, text="✂️ Auto-Trim", variable=self.var_trim).pack(side="left", padx=10)
        
        self.btn_scan = ctk.CTkButton(act, text="🎧🔍 Start Scan", command=self.start_scan_thread, width=120, fg_color="#007aff")
        self.btn_scan.pack(side="right", padx=10)
        self.btn_stop_scan = ctk.CTkButton(act, text="⏹ Stop Import", command=self.stop_scan_process, width=40, fg_color="#AA0000", state="disabled")
        self.btn_stop_scan.pack(side="right", padx=2)
        
        self.bpm_max = ctk.CTkEntry(act, width=40, placeholder_text="Max"); self.bpm_max.pack(side="right", padx=2)
        ctk.CTkLabel(act, text="-").pack(side="right")
        self.bpm_min = ctk.CTkEntry(act, width=40, placeholder_text="Min"); self.bpm_min.pack(side="right", padx=2)
        ctk.CTkLabel(act, text="⏱️ BPM:").pack(side="right")

        # --- 3. COCKPIT (Dual Column) ---
        cockpit = ctk.CTkFrame(self, border_width=1, border_color="gray")
        cockpit.pack(fill="x", pady=5, padx=5)

        # Left Column: Audio Controls
        left_controls = ctk.CTkFrame(cockpit, fg_color="transparent")
        left_controls.pack(side="left", fill="both", expand=True, padx=5, pady=5)
# Zeile A: Transport (Das präzise verzahnte Grid)
        row_transport = ctk.CTkFrame(left_controls, fg_color="transparent")
        row_transport.pack(fill="x", pady=(0, 35))

        # Spalte 5 (Status) bekommt das Gewicht, um den Rest nach links zu schieben
        row_transport.grid_columnconfigure(5, weight=1)

        # 1. Transport-Buttons (Spalte 0-3, nehmen 2 Reihen ein für die vertikale Zentrierung)
        ctk.CTkButton(row_transport, text="⏪ -10s", width=50, command=lambda: self.seek_rel(-10), fg_color="#555").grid(row=0, column=0, rowspan=2, padx=5, pady=4)
        
        self.btn_play = ctk.CTkButton(row_transport, text="▶ Play", width=60, command=self.toggle_play, fg_color="#00AA00")
        self.btn_play.grid(row=0, column=1, rowspan=2, padx=5, pady=5)
        
        ctk.CTkButton(row_transport, text="⏹ Stop", width=50, command=self.stop_track, fg_color="#AA0000").grid(row=0, column=2, rowspan=2, padx=5, pady=4)
        
        ctk.CTkButton(row_transport, text="⏩ +10s", width=50, command=lambda: self.seek_rel(10), fg_color="#555").grid(row=0, column=3, rowspan=2, padx=5, pady=4)

        # 2. Die Zeit-Anzeige (Spalte 4, ebenfalls 2 Reihen hoch)
        self.lbl_time = ctk.CTkLabel(row_transport, text="00:00 / 00:00", text_color="cyan", font=("Consolas", 14, "bold"))
        self.lbl_time.grid(row=0, column=4, rowspan=2, padx=10, sticky="n", pady=(25, 0))

        # 3. STATUS TITEL (Reihe 0, Spalte 5) -> Untenbündig mit der Zeit
        self.lbl_status_title = ctk.CTkLabel(row_transport, text="🟢 Ready to play.", text_color="#00AA00", font=("Arial", 12, "bold"))
        self.lbl_status_title.grid(row=0, column=5, padx=10, sticky="sw", pady=(25, 0)) # sw = Süd-West

        # 4. STATUS ARTIST (Reihe 1, Spalte 5) -> Obenbündig direkt darunter
        self.lbl_status_artist = ctk.CTkLabel(row_transport, text="", text_color="gray", font=("Arial", 12))
        self.lbl_status_artist.grid(row=1, column=5, padx=10, sticky="nw") # nw = Nord-West

        row_sm = ctk.CTkFrame(left_controls, fg_color="transparent")
        row_sm.pack(fill="x", pady=5)
        ctk.CTkLabel(row_sm, text="🎛️ SAMPLER").pack(side="left", padx=10)
        ctk.CTkButton(row_sm, text="IN [I]", width=50, command=self.set_in).pack(side="left", padx=4)
        ctk.CTkButton(row_sm, text="🔁 Preview", width=80, command=self.preview_loop, fg_color="#007aff").pack(side="left", padx=5)
        ctk.CTkButton(row_sm, text="➡️ Exit", width=60, command=self.exit_loop, fg_color="#5E35B1").pack(side="left", padx=2)
        ctk.CTkButton(row_sm, text="OUT [O]", width=50, command=self.set_out).pack(side="left", padx=4)
        self.lbl_loop_info = ctk.CTkLabel(row_sm, text="🟢🔁 Ready for Looping", text_color="#00AA00")
        self.lbl_loop_info.pack(side="left", padx=6)
        
        # Zeile C: Smart Tools
        row_tools = ctk.CTkFrame(left_controls, fg_color="transparent")
        row_tools.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(row_tools, text="🔁✨ Smart Loop").pack(side="left", padx=8)
        for b in [2, 4, 8, 16, 32]:
            ctk.CTkButton(row_tools, text=str(b), width=50, command=lambda x=b: self.set_smart_bar(x)).pack(side="left", padx=4)
                        
        

        # Right Column: Visual Display
        right_display = ctk.CTkFrame(cockpit, fg_color="transparent", width=320)
        right_display.pack(side="right", fill="both", padx=10, pady=5)
        self.ana_cover_label = ctk.CTkLabel(right_display, text="🎵", width=150, height=150, fg_color="#1a1a1a", corner_radius=10)
        self.ana_cover_label.pack(pady=5)
        
        self.slider_container = ctk.CTkFrame(right_display, fg_color="transparent", height=30)
        self.slider_container.pack(fill="x")
        self.play_slider = ctk.CTkSlider(self.slider_container, from_=0, to=100, command=self.on_slider_seek)
        self.play_slider.pack(fill="x", pady=5)
        
        self.marker_in = ctk.CTkFrame(self.slider_container, width=4, height=15, fg_color="#00FF00")
        self.marker_out = ctk.CTkFrame(self.slider_container, width=4, height=15, fg_color="#FF0000")
        
        self.lbl_ana_title = ctk.CTkLabel(right_display, text="No track selected", font=("Arial", 12, "bold"), wraplength=280)
        self.lbl_ana_title.pack()
        self.lbl_ana_artist = ctk.CTkLabel(right_display, text="", text_color="gray")
        self.lbl_ana_artist.pack()

        
        # --- 4. FILTER BAR & UNDO ---
        filter_bar = ctk.CTkFrame(self, height=40)
        filter_bar.pack(fill="x", pady=5)
        ctk.CTkLabel(filter_bar, text="🔍Search").pack(side="left", padx=10)
        self.f_bpm_min = ctk.CTkEntry(filter_bar, width=85, placeholder_text="🐢BPM Min"); self.f_bpm_min.pack(side="left", padx=2)
        self.f_bpm_max = ctk.CTkEntry(filter_bar, width=90, placeholder_text="🐇BPM Max"); self.f_bpm_max.pack(side="left", padx=2)
        self.f_key = ctk.CTkEntry(filter_bar, width=60, placeholder_text="🔑 Key"); self.f_key.pack(side="left", padx=10)
        self.f_name = ctk.CTkEntry(filter_bar, placeholder_text="🔤 Name search...")
        
        self.f_name.pack(side="left", padx=10)
        self.f_bpm_min.bind("<KeyRelease>", lambda e: self.apply_filter())
        self.f_bpm_max.bind("<KeyRelease>", lambda e: self.apply_filter())
        self.f_key.bind("<KeyRelease>", lambda e: self.apply_filter())
        self.f_name.bind("<KeyRelease>", lambda e: self.apply_filter())

        ctk.CTkButton(filter_bar, text="🚀Go", width=40, command=self.apply_filter).pack(side="left", padx=2)
        ctk.CTkButton(filter_bar, text="📋All", width=40, command=self.reset_filter, fg_color="gray").pack(side="left", padx=2)
        
        self.btn_undo = ctk.CTkButton(filter_bar, text="↩️ Undo", command=self.undo_delete, fg_color="#5E35B1", state="disabled", width=60)
        self.btn_undo.pack(side="right", padx=5)
        ctk.CTkButton(filter_bar, text="🗑️ Clear List", width=80, command=self.clear_playlist, fg_color="gray").pack(side="right", padx=5)
        ctk.CTkButton(filter_bar, text="🚫 Remove", width=60, command=self.delete_row, fg_color="#AA0000").pack(side="right", padx=5)
        self.btn_save_loop = ctk.CTkButton(filter_bar, text="💾 Save Loop", width=80, fg_color="#E65100", command=self.save_cut).pack(side="right", padx=5)

        # --- 5. TREEVIEW ---
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, pady=5)
        style = ttk.Style()
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", rowheight=30)
        cols = ("#", "BPM", "Time", "Camelot", "Key", "Tags", "Filename")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode="extended")
        
        self.tree.heading("#", text="#")
        self.tree.heading("BPM", text="🥁⏱️ BPM", command=lambda: self.sort_tree("BPM", False))
        self.tree.heading("Time", text="🎶⏱️ Duration", command=lambda: self.sort_tree("Time", False))
        self.tree.heading("Camelot", text="🔑 Camelot", command=lambda: self.sort_tree("Camelot", False))
        self.tree.heading("Key", text="🔑 Key", command=lambda: self.sort_tree("Key", False))
        self.tree.heading("Tags", text="📍 Status", command=lambda: self.sort_tree("Tags", False))
        self.tree.heading("Filename", text="📝  Filename", command=lambda: self.sort_tree("Filename", False)) 
        
        self.tree.column("#", width=25, anchor="center")
        self.tree.column("BPM", width=25, anchor="center")
        self.tree.column("Time", width=30, anchor="center") # <--- NEU
        self.tree.column("Camelot", width=20, anchor="center")
        self.tree.column("Key", width=30, anchor="center")
        self.tree.column("Tags", width=50, anchor="center")
        self.tree.column("Filename", width=450)
           
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set); vsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        for k, c in CAMELOT_COLORS.items(): self.tree.tag_configure(k, background=c, foreground="white")
        
        self.tree.bind("<Button-3>", lambda e: self.bpm_menu.tk_popup(e.x_root, e.y_root))
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind("<Double-1>", lambda e: self.toggle_play())

        # --- RECHTSKLICK MENÜ FÜR BPM ---
        self.bpm_menu = tk.Menu(self, tearoff=0)
        self.bpm_menu.add_command(label="📄 Details", command=self.show_track_details)
        self.bpm_menu.add_command(label="📂 Show in Finder", command=self.open_current_in_finder)
        self.bpm_menu.add_command(label="🔄 Rescan Selection", command=self.rescan_multiple_tracks)
        self.bpm_menu.add_separator()
        self.bpm_menu.add_command(label="✏️ Meta Editor", command=self.send_to_editor)
        self.bpm_menu.add_command(label="✂️ Stems AI", command=self.send_to_stems)
        self.bpm_menu.add_command(label="📝 Transcribe", command=self.send_to_trans)
        self.bpm_menu.add_separator()
        self.bpm_menu.add_command(label="2️⃣ BPM (2x)", command=lambda: self.modify_bpm(2.0))
        self.bpm_menu.add_command(label="2️⃣ BPM (/2)", command=lambda: self.modify_bpm(0.5))
        
        # Bindings für Rechtsklick auf die Tabelle
        self.tree.bind("<Button-3>", self.show_bpm_menu) # Windows/Linux
        self.tree.bind("<Button-2>", self.show_bpm_menu) # Mac (oft)
        self.tree.bind("<Control-Button-1>", self.show_bpm_menu) # Mac (Ctrl+Klick)
        # Von der Suche (Name) zur Liste springen
        self.f_name.bind("<Tab>", self.focus_on_playlist)

        # Von der Liste zum nächsten Element (z.B. Remove Button) springen
        # 'tk_focusNext' findet das nächste logische Widget
        self.tree.bind("<Tab>", lambda e: e.widget.tk_focusNext().focus_set() or "break")
        # Drag & Drop Bindings
        self.tree.bind("<Button-1>", self.on_drag_start)
        self.tree.bind("<ButtonRelease-1>", self.on_drag_release)        


    # --- PRO AUDIO ENGINE (TRAKTOR-STYLE) ---

    def play_track(self):
        sel = self.tree.selection()
        if not sel: return
        iid = sel[0]
        if iid in self.data_map:
            t = self.data_map[iid]
            fpath = t['Pfad']
            if not os.path.exists(fpath): return
            
            try:
                        # 1. Alles Audio stoppen
                self.stop_audio_fully()
                       # --- DIESE ZEILEN MÜSSEN REIN ---
                self.sampler_in = None
                self.sampler_out = None
                self.is_looping = False
                self.current_loop_duration = 0
                self.loop_start_time = 0
                self.exit_pending = False
                self.is_looping = False
                
                # Marker grafisch verstecken
                self.marker_in.place(relx=-1)
                self.marker_out.place(relx=-1)
                # -------------------------------
                pygame.mixer.music.load(fpath)
                pygame.mixer.music.play()                
                # --- PLAYER STATE ---
                self.current_playing_path = fpath
                self.playing_file = t['Dateiname']
                self.track_bpm = float(t.get('BPM', 120))
                try: self.total_duration = sf.info(fpath).duration
                except: self.total_duration = 0.0
                
                self.is_paused = False
                self.playback_offset = 0.0
                self.btn_play.configure(text="⏸ Pause", fg_color="#FFA500")
                
                # 1. Tags für die Statuszeile lesen
                # 1. Tags lesen
                from helpers import read_tags_quick
                tags = read_tags_quick(fpath)
               # WICHTIG: Diese zwei Variablen fest an die Klasse binden (self.)
               
                self.current_playing_artist = tags.get('artist') or "Unknown Artist"
                self.current_playing_title = tags.get('title') or t.get('Dateiname', "Unknown")
        
                # 2. BPM Logik
                if self.track_bpm == 0 and tags.get('bpm'):
                    try: self.track_bpm = float(tags.get('bpm'))
                    except: self.track_bpm = 0
                bpm_disp = int(self.track_bpm) if self.track_bpm > 0 else "?"

                # 3. Texte für die Anzeige kürzen (bevor wir sie zusammenbauen)
                short_title = self.current_playing_title[:30] + "..." if len(self.current_playing_title) > 33 else self.current_playing_title
                short_artist = self.current_playing_artist[:35] + "..." if len(self.current_playing_artist) > 38 else self.current_playing_artist

                # 4. UI AKTUALISIEREN (Nur einmal aufrufen!)
                # Obere Zeile: Titel + BPM
                self.lbl_status_title.configure(text=f"▶ {short_title} ({bpm_disp} BPM)", text_color="#00AA00")
                # Untere Zeile: Artist
                self.lbl_status_artist.configure(text=short_artist)
                
                # Update das rechte Info-Panel (Cover/Großer Titel)
                self.update_ui_info(t)
                
                # --- NEU: Detail-Fenster updaten! ---
                self.update_info_window(fpath)
                #
                
                self.update_timer()
                #threading.Thread(target=self.analyze_beats_bg, args=(fpath,), daemon=True).start()    
            except Exception as e: 
                print(f"Play Error: {e}")
                    
                pygame.mixer.music.play()
                
                self.current_playing_path = fpath
                self.playing_file = t['Dateiname']
                self.track_bpm = float(t.get('BPM', 120))
                
                try: self.total_duration = sf.info(fpath).duration
                except: self.total_duration = 0.0
                
                self.is_paused = False
                self.playback_offset = 0.0
                self.sampler_in = None
                self.sampler_out = None
                self.is_looping = False
                self.exit_pending = False
                self.loop_start_time = 0
                self.lbl_loop_info.configure(text="-")
                
                self.btn_play.configure(text="⏸ Pause", fg_color="#FFA500")
                # Name kürzen für Anzeige
                disp_name = self.playing_file
                if len(disp_name) > 55: disp_name = disp_name[:52] + "..."
                
                # BPM holen
                bpm_disp = int(self.track_bpm) if self.track_bpm else "?"

                # Neue Anzeige: ▶ Name (124 BPM)
                self.lbl_status_title.configure(text=f"▶ {disp_name} ({bpm_disp} BPM)", text_color="#00AA00")
                self.lbl_status_artist.configure(text="artist")
                
                self.update_visual_markers()
                
                self.update_timer()
                #threading.Thread(target=self.analyze_beats_bg, args=(fpath,), daemon=True).start()
                
            except Exception as e: print(e)

    def preview_loop(self):
        """Erstellt den Loop und spielt ihn auf Deck B (RAM) ab."""
        if not self.current_playing_path or self.sampler_in is None or self.sampler_out is None: return
        
        self.is_looping = True
        self.exit_pending = False
        self.lbl_status_title.configure(text="🔁 Looping (Processing)...", text_color="cyan")
        
        # Berechnung im Hintergrund, damit GUI nicht ruckelt
        threading.Thread(target=self._run_loop_generation, daemon=True).start()

    def _run_loop_generation(self):
        try:
            # 1. Audio schneiden
            data, sr = sf.read(self.current_playing_path)
            
            # WICHTIG: NumPy-Werte in reine Python-Floats wandeln (Verhindert Crash!)
            s_in = float(self.sampler_in)
            s_out = float(self.sampler_out)
            
            # Sicherheits-Check: Indices berechnen
            start_idx = max(0, int(s_in * sr))
            end_idx = min(len(data), int(s_out * sr))
            
            # Loop extrahieren
            cut = data[start_idx:end_idx]
            
            # 2. Speichern
            import tempfile
            temp_f = os.path.join(tempfile.gettempdir(), f"loop_cache_{int(time.time())}.wav")
            sf.write(temp_f, cut, sr)
            
            # 3. Sound-Objekt erstellen
            self.current_loop_sound = pygame.mixer.Sound(temp_f)
            self.current_loop_duration = len(cut) / sr
            
            # 4. Deck Swap im Main-Thread
            self.after(0, self._finalize_deck_swap)
            
        except Exception as e:
            print(f"Loop Gen Error: {e}")
            self.is_looping = False
            self.after(0, lambda: self.lbl_status_title.configure(text="❌ Loop Error", text_color="red"))

    def _finalize_deck_swap(self):
        """Schaltet um: Deck A (Music) aus -> Deck B (Loop) an"""
        try:
            # Musik stoppen und RAM freigeben
            pygame.mixer.music.stop()
            pygame.mixer.music.unload() 
            
            # Loop starten (Channel 5)
            self.loop_channel.set_volume(1.0)
            self.loop_channel.play(self.current_loop_sound, loops=-1)
            
            # Timing
            self.loop_start_time = time.perf_counter()
            self.btn_play.configure(text="⏹ Stop Loop", fg_color="#AA0000")
            self.lbl_status_title.configure(text="🔁 LOOPING (RAM)", text_color="cyan")
            
            # Timer starten
            self.update_timer()
            
        except Exception as e:
            print(f"Deck Swap Error: {e}")
            # Hier kein stop_track, damit wir nicht versehentlich alles killen
            
    def finalize_loop_start(self, temp_f):
        """Wird aufgerufen, wenn die Datei fertig ist - startet den Sound"""
        try:
            self.current_loop_sound = pygame.mixer.Sound(temp_f)
            pygame.mixer.music.stop()
            
            self.loop_channel.set_volume(1.0)
            self.loop_channel.play(self.current_loop_sound, loops=-1)
            
            # JETZT erst wird der Loop für den Timer scharf geschaltet!
            self.loop_start_time = time.perf_counter()
            self.is_looping = True 
            
            self.btn_play.configure(text="⏹ Stop Loop", fg_color="#AA0000")
            self.lbl_status_title.configure(text="🔁 LOOPING...", text_color="cyan")
            # Original im Hintergrund vorladen
            self.after(50, lambda: pygame.mixer.music.load(self.current_playing_path))
        except:
            self.reset_sampler_state()

        def load_loop_thread():
            try:
                data, sr = sf.read(self.current_playing_path)
                s_f, e_f = int(self.sampler_in * sr), int(self.sampler_out * sr)
                cut = data[max(0, s_f):min(len(data), e_f)]
                
                import tempfile
                temp_f = os.path.join(tempfile.gettempdir(), f"loop_{int(time.time())}.wav")
                sf.write(temp_f, cut, sr)
                
                self.current_loop_duration = len(cut) / sr
                self.current_loop_sound = pygame.mixer.Sound(temp_f)
                
                # Switch Decks: Music Stop -> Channel Start
                pygame.mixer.music.stop()
                self.loop_channel.set_volume(1.0)
                self.loop_channel.play(self.current_loop_sound, loops=-1)
                self.loop_start_time = time.perf_counter()
                
                # Pre-load Deck B (Original)
                self.after(50, lambda: pygame.mixer.music.load(self.current_playing_path))
                self.after(0, lambda: self.btn_play.configure(text="⏹ Stop Loop", fg_color="#AA0000"))
                self.after(0, lambda: self.lbl_status_title.configure(text="🔁 LOOPING (READY)", text_color="cyan"))
            except Exception as e: print(f"Loop Error: {e}")

        threading.Thread(target=load_loop_thread, daemon=True).start()

    def exit_loop(self):
        """
        Plant den Ausstieg. 
        TRICK: Wir feuern den Übergang 200ms FRÜHER ab, damit das Audio 
        Zeit hat, anzulaufen ("Pre-Roll").
        """
        if not self.is_looping or self.exit_pending or self.current_loop_duration <= 0: return

        # 1. Wo sind wir im Loop?
        elapsed = time.perf_counter() - self.loop_start_time
        time_remaining = self.current_loop_duration - (elapsed % self.current_loop_duration)
        
        self.exit_pending = True
        self.lbl_status_title.configure(text="➡ Exiting Loop (Syncing)...", text_color="orange")

        # 2. Die Pre-Roll Zeit (Puffer für macOS CoreAudio)
        LATENCY_PRE_ROLL = 0.20  # 200ms Vorlaufzeit
        
        # Berechne, wann wir feuern müssen
        wait_time = time_remaining - LATENCY_PRE_ROLL
        
        # Falls wir schon zu nah am Ende sind (< 200ms), feuern wir sofort!
        if wait_time <= 0:
            delay_ms = 1
        else:
            delay_ms = int(wait_time * 1000)

        # Timer setzen
        self.after(delay_ms, self.perform_seamless_transition)

    def perform_seamless_transition(self):
        """
        PLATINUM SYNC FINAL:
        - Startet 200ms im Voraus (Back-Timing) für Sync-Sicherheit.
        - Fadet den Loop aber in 40ms aus (Phasing-Killer).
        """
        if not self.exit_pending: return

        try:
            if self.sampler_out is None:
                self.exit_pending = False
                return

            # 1. Float erzwingen
            s_out = float(self.sampler_out)
            
            # 2. Back-Timing (200ms Sicherheitspuffer lassen!)
            # Das muss zum Wert in 'exit_loop' passen (dort ca. 0.20)
            PRE_ROLL_OFFSET = 0.20 
            
            start_pos = max(0.0, s_out - PRE_ROLL_OFFSET)

            # 3. Deck A (Original) starten
            pygame.mixer.music.load(self.current_playing_path)
            pygame.mixer.music.play(start=start_pos)
            
            # GUI Sync
            self.playback_offset = start_pos
            self.playback_start_time = time.time() - start_pos

            # 4. Deck B (Loop) - DER PHASING KILLER
            # Obwohl wir 200ms Vorlauf haben, blenden wir den Loop 
            # schon nach 40ms aus. Der Rest ist reines Original-Signal.
            if hasattr(self, 'loop_channel') and self.loop_channel.get_busy():
                self.loop_channel.fadeout(40) 
            else:
                self.is_looping = False

            # Aufräumen
            self.exit_pending = False
            try:
                self._finalize_audio_ui()
            except: pass

        except Exception as e:
            print(f"SYNC WARNING: {e}")
            self.exit_pending = False
            
    def _fade_out_loop_worker(self, steps, step_time):
        """
        Hilfsfunktion: Reduziert die Lautstärke des Loops schrittweise,
        während Deck A im Hintergrund den Puffer füllt.
        """
        if steps <= 0:
            # Ende des Fades: Loop komplett stoppen
            if hasattr(self, 'loop_channel'):
                self.loop_channel.stop()
                # Lautstärke für den nächsten Loop wieder hochsetzen (wichtig!)
                self.loop_channel.set_volume(1.0) 
            
            self.is_looping = False
            return

        # Lautstärke reduzieren
        if hasattr(self, 'loop_channel'):
            current_vol = self.loop_channel.get_volume()
            # Linearer Fade-Out
            new_vol = max(0, current_vol - (current_vol / steps))
            self.loop_channel.set_volume(new_vol)

        # Nächsten Schritt planen (ohne GUI-Blockade)
        self.after(step_time, lambda: self._fade_out_loop_worker(steps - 1, step_time))

    def _finalize_audio_ui(self):
        """Stellt die Song-Infos nach dem Loop-Exit wieder her"""
        self.btn_play.configure(text="⏸ Pause", fg_color="#FFA500")
        
        # Song-Infos wiederherstellen
        bpm_disp = int(self.track_bpm) if self.track_bpm else "?"
        title = getattr(self, 'current_playing_title', "Unknown Track")
        artist = getattr(self, 'current_playing_artist', "Unknown Artist")
        
        self.lbl_status_title.configure(text=f"▶ {title[:30]} ({bpm_disp} BPM)", text_color="#00AA00")
        self.lbl_status_artist.configure(text=artist[:35])
        # --- DATEN-REINIGUNG ---
        self.sampler_in = None
        self.sampler_out = None
        self.marker_in.place(relx=-1)
        self.marker_out.place(relx=-1)
        
        # Sampler Reset
        self.lbl_loop_info.configure(text="🟢🔁 Ready for Looping", text_color="#00AA00")
        self.sampler_in = self.sampler_out = None
        self.marker_in.place(relx=-1)
        self.marker_out.place(relx=-1)
        
        self.update_timer()

    def stop_audio_fully(self):
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        self.loop_channel.stop()
        pygame.mixer.stop()
        self.is_looping = self.exit_pending = self.is_paused = False

    def stop_track(self):
        self.manual_stop = True
        self.stop_audio_fully()
        # --- DATEN-REINIGUNG (Wichtig für Smart Loops!) ---
        self.sampler_in = None
        self.sampler_out = None
        
        # Visuelle Marker verstecken
        self.marker_in.place(relx=-1)
        self.marker_out.place(relx=-1)
        self.btn_play.configure(text="▶ Play", fg_color="#00AA00")
        self.lbl_time.configure(text="00:00 / 00:00")
        self.play_slider.set(0)
        self.lbl_status_title.configure(text="🟥 Stopped", text_color="gray")
        self.after(2000, self.reset_status_to_ready)
        self.lbl_loop_info.configure(text="🟢🔁 Ready for Looping", text_color="#00AA00")

    def show_bpm_menu(self, event):
        # 1. Welches Item ist unter der Maus?
        item_under_mouse = self.tree.identify_row(event.y)
        
        if item_under_mouse:
            # 2. Hol die aktuelle Auswahl
            current_selection = self.tree.selection()
            
            # 3. WICHTIG: Nur ummarkieren, wenn das Item unter der Maus 
            # noch NICHT Teil der Auswahl ist.
            if item_under_mouse not in current_selection:
                self.tree.selection_set(item_under_mouse)
            
            # Menü anzeigen
            try:
                self.bpm_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.bpm_menu.grab_release()
                
    
    def toggle_play(self):
        if self.is_looping: self.stop_track(); return
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.btn_play.configure(text="⏸ Pause", fg_color="#FFA500")
            self.update_timer()
        elif pygame.mixer.music.get_busy():
            pygame.mixer.music.pause(); self.is_paused = True
            self.btn_play.configure(text="▶ Resume", fg_color="#00AA00")
        else: self.play_track()

    # --- DATA & LIST MANAGEMENT ---

    def import_playlist_dialog(self):
        f = filedialog.askopenfilename(filetypes=[("Playlist", "*.xml *.m3u *.m3u8 *.json")])
        if not f: 
            self.app.focus_force() # Falls User abbricht, Fokus zurück
            return
        
        new_tracks = import_playlist_file(f)

        # Pfad der importierten Playlist merken (für Update-Button)
        self.last_playlist_paths = [f]

        if not new_tracks:
            messagebox.showwarning("Info", "No tracks found 🚫")
            self.app.focus_force() # Falls not found, Fokus zurück
            return
                # --- FIX: Tracks zur internen Datenbank hinzufügen ---
        self.all_tracks.extend(new_tracks)
        # ----
            
        count = 0
        for t in new_tracks:
            self.ins(t)
            count += 1
            
        self.renum()
        # NEU: Ersten Track wählen
        self.select_first_track()        
        messagebox.showinfo("Import", f"{count} files imported ✅")
        self.app.lift()
        self.app.focus_force() # Falls erfolgreich, Fokus zurück

    def delete_row(self):
        selection = self.tree.selection()
        if not selection: return
        
        # Speichere den Zustand VOR dem Löschen
        deleted_items = []
        for item_id in selection:
            # Wir speichern Values, Tags und das Daten-Objekt
            vals = self.tree.item(item_id)['values']
            tags = self.tree.item(item_id)['tags']
            data = self.data_map.get(item_id)
            
            deleted_items.append({
                'values': vals,
                'tags': tags,
                'data': data
            })
            
            # Löschen
            self.tree.delete(item_id)
            if item_id in self.data_map: del self.data_map[item_id]
            
        # Auf den Stack legen
        self.undo_stack.append(deleted_items)
        
        # Button aktivieren
        self.btn_undo.configure(state="normal", fg_color="#5E35B1")
        self.renum()


    def undo_delete(self):
        if not self.undo_stack: return
        last = self.undo_stack.pop()
        for it in last:
            iid = self.tree.insert('', 'end', values=it['values'], tags=it['tags'])
            self.data_map[iid] = it['data']
            if it['data'] not in self.all_tracks: self.all_tracks.append(it['data'])
        if not self.undo_stack: self.btn_undo.configure(state="disabled")

    def clear_playlist(self):
        if not self.tree.get_children(): return
        items = []
        for iid in self.tree.get_children():
            items.append({'values': self.tree.item(iid)['values'], 'tags': self.tree.item(iid)['tags'], 'data': self.data_map[iid]})
        self.undo_stack.append(items)
        self.btn_undo.configure(state="normal")
        self.tree.delete(*self.tree.get_children())
        self.data_map = {}
        self.all_tracks = []
        self.filter_active = False
        self.app.log_tab.log("Playlist cleared 🗑️") 

    def apply_filter(self):
        self.tree.delete(*self.tree.get_children())
        self.data_map = {}
        
        # 1. Filter-Werte abrufen
        try: 
            mi = float(self.f_bpm_min.get())
            ma = float(self.f_bpm_max.get())
        except: 
            mi = 0
            ma = 999
            
        k = self.f_key.get().lower().strip()
        n = self.f_name.get().lower().strip()   # <--- Name-Filter
        self.filter_active = bool(k or n or (mi, ma) != (0, 999))
        
        # 2. Schleife durch alle Tracks
        for t in self.all_tracks:
            bpm = float(t.get('BPM', 0))

            # Key/Camelot
            key_match = (
                not k or
                k in str(t.get('Camelot', '')).lower() or
                k in str(t.get('Key', '')).lower()
            )

            # Name (Dateiname)
            name_match = (
                not n or
                n in str(t.get('Dateiname', '')).lower()
            )

            # Alle Bedingungen müssen erfüllt sein
            if mi <= bpm <= ma and key_match and name_match:
                self.ins(t)
                
        self.renum()


    def reset_filter(self):
        self.f_name.delete(0, "end") # NEU
        self.f_bpm_min.delete(0,"end"); self.f_bpm_max.delete(0,"end"); self.f_key.delete(0,"end")
        self.tree.delete(*self.tree.get_children()); self.data_map = {}; self.filter_active = False
        for t in self.all_tracks: self.ins(t)
        self.renum()

    def modify_bpm(self, factor):
        sel = self.tree.selection()
        for iid in sel:
            if iid in self.data_map:
                t = self.data_map[iid]
                try:
                    new_b = round(float(t.get('BPM', 0)) * factor, 2)
                    t['BPM'] = new_b
                    v = list(self.tree.item(iid, 'values'))
                    v[1] = new_b
                    self.tree.item(iid, values=v)
                except: pass

    # --- SCAN & WORKER LOGIC ---

    def start_scan_thread(self):
        # 1. Pfad-Ermittlung (Deine Logik: Erst lokal, dann global)
        f = self.local_path_entry.get()
        if not os.path.isdir(f): 
            f = self.app.path_entry.get()
            if not os.path.isdir(f): 
                messagebox.showerror("Error", "Please select a valid folder! 📁")
                self.app.lift()
                self.app.focus_force()
                return

        # 2. VORAB-PRÜFUNG AUF DATEIEN (Deine Sicherheitsprüfung)
        audio_exts = ('.mp3', '.wav', '.aiff', '.aif', '.flac', '.m4a')
        files_found = []
        for root, dirs, files in os.walk(f): 
            for file in files: 
                if file.lower().endswith(audio_exts): 
                    files_found.append(file) 
                    break 
        
        if not files_found:
            messagebox.showwarning("No Files", "No supported audio files found in this folder 📂🚫")
            self.app.lift()
            self.app.focus_force()
            return 

        # 3. ENGINE & UI STATUS SETZEN
        self.is_scanning = True
        self.is_loading = True          # Aktiviert das Pulsieren
        self.animate_loading()          # Startet die Animation
        
        self.btn_scan.configure(state="disabled")
        self.btn_stop_scan.configure(state="normal")
        
        # 4. TEMP-DATEI DEFINIEREN
        import tempfile
        self.current_scan_csv = os.path.join(tempfile.gettempdir(), f"full_scan_{int(time.time())}.csv")
        
        # 5. UI VORBEREITEN
        self.app.global_progress.set(0)
        self.app.tabview.set(self.app.tab_name_log)
        
        # 6. PARAMETER HOLEN
        mi = self.bpm_min.get() if self.bpm_min.get().isdigit() else "0"
        ma = self.bpm_max.get() if self.bpm_max.get().isdigit() else "999"
        w_tags = "True" if self.var_write_tags.get() else "False"
        
        # 7. WORKER THREAD STARTEN
        # Übergibt den Pfad und die Parameter an run_analysis
        threading.Thread(target=self.run_analysis, args=(f, w_tags, mi, ma), daemon=True).start()

    def run_analysis(self, f, w, mi, ma):
        import tempfile
        # Temp-CSV Pfad erstellen
        temp_csv = os.path.join(tempfile.gettempdir(), f"full_scan_{int(time.time())}.csv")

        # 1. v3.1 Dispatcher Logik (Dev-Mode vs. Frozen)
        args = [sys.executable]
        if not getattr(sys, 'frozen', False):
            main_script = os.path.abspath(sys.modules['__main__'].__file__)
            args.append(main_script)
        
        # Worker-Flags anhängen
        args.extend(["--worker", "analyzer", f, temp_csv, w, mi, ma])
            
        self.after(0, lambda: self.app.log_tab.log("🔍 Scanning and analyzing folder..."))
        
        try:
            # Subprozess starten
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            
            while True:
                # Abbruch-Check (User hat Stop gedrückt oder App schließt)
                if self.app.closing or not self.is_scanning: 
                    p.terminate()
                    break
                
                l = p.stdout.readline()
                # Wenn Stream zu Ende und Prozess fertig -> raus aus Schleife
                if not l and p.poll() is not None: 
                    break
                
                if l:
                    l = l.strip()
                    if l.startswith("PROGRESS:"):
                        # Sobald echte Daten kommen: Pulsieren stoppen
                        self.is_loading = False 
                        
                        try:
                            # Format: PROGRESS:1/10:filename.mp3
                            pts = l.split(":", 2) # Wir splitten max 2x (wegen Pfaden mit Doppelpunkten)
                            if len(pts) >= 2:
                                counts = pts[1].split("/")
                                val = int(counts[0]) / int(counts[1])
                                # Fortschrittsbalken im UI füllen
                                self.after(0, lambda v=val: self.app.global_progress.set(v))
                                
                                # Dateiname ins Log schreiben (falls vorhanden)
                                if len(pts) > 2:
                                    filename = pts[2]
                                    self.after(0, lambda x=filename: self.app.log_tab.log(f"📝 Analyzing: {x}"))
                        except: 
                            pass

            # Warten, bis der Prozess wirklich abgewickelt ist
            p.wait()

            # Erfolgskontrolle
            if not self.app.closing and self.is_scanning and p.returncode == 0:
                # ERFOLG: Daten einlesen
                self.after(0, lambda: self.finish_scan(temp_csv))
            else:
                # ABBRUCH oder FEHLER
                self.after(0, self.reset_scan_buttons)
                
        except Exception as e:
            print(f"Run Analysis Error: {e}")
            self.after(0, self.reset_scan_buttons)

    
    def finish_scan(self, csv): # Die Variable heißt hier 'csv'
        self.reset_scan_buttons() 
        
        if os.path.exists(csv): # Geändert von csv_path zu csv
            try:
                df = pd.read_csv(csv)
                
                # Falls 'Time' fehlt, leere Spalte (verhindert Absturz)
                if 'Time' not in df.columns:
                    df['Time'] = "--:--"
                
                # Sortierung wie in deinem alten Stand
                if 'BPM' in df.columns: 
                    df = df.sort_values(by='BPM')
                
                new_tracks = df.to_dict('records')
                
                for t in new_tracks:
                    # --- BEATS KONVERTIEREN (WICHTIG!) ---
                    if 'Beats' in t and isinstance(t['Beats'], str) and t['Beats'].strip():
                        try:
                            t['detected_beats'] = np.array([float(x) for x in t['Beats'].split(";")])
                        except:
                            t['detected_beats'] = None
                    else:
                        t['detected_beats'] = None
                    # --------------------------------------
                    
                    self.all_tracks.append(t)
                    self.ins(t) # Fügt den Track zur Liste (Treeview) hinzu
                
                self.renum() # Nummern korrigieren
                
                self.app.log_tab.log(f"✅ Scan finished: {len(new_tracks)} files added.")
                self.select_first_track()    
                
                # Messagebox mit Parent-Bindung für den Fokus
                messagebox.showinfo("Import", f"{len(new_tracks)} files imported successfully ✅", parent=self.app)
                
                self.app.lift()
                self.app.focus_force()
                self.app.tabview.set(self.app.tab_name_analyze)
                
                # Datei löschen
                os.remove(csv)
                
            except Exception as e:
                self.app.log_tab.log(f"❌ Critical Import Error: {e}")     

    def rescan_multiple_tracks(self):
        sel = self.tree.selection()
        if not sel: return
        self.is_scanning = True
        self.btn_scan.configure(state="disabled")
        self.btn_stop_scan.configure(state="normal")
        self.app.log_tab.log(f"🔄 Starting rescan for {len(sel)} tracks...")
        threading.Thread(target=self.run_multi_rescan, args=(list(sel),), daemon=True).start()

    def run_multi_rescan(self, ids):
        import tempfile
        total = len(ids)
        for i, iid in enumerate(ids):
            if not self.is_scanning: break
            t = self.data_map.get(iid)
            if not t: continue
            self.after(0, lambda x=iid: self.tree.set(x, column="Tags", value="⏳..."))
            t_csv = os.path.join(tempfile.gettempdir(), f"rescan_{i}.csv")
            cmd = get_worker_cmd("analyzer") + [t['Pfad'], t_csv, "True", "0", "999"]
            subprocess.run(cmd, capture_output=True)
            if os.path.exists(t_csv):
                df = pd.read_csv(t_csv)
                if not df.empty:
                    new_d = df.to_dict('records')[0]
                    self.data_map[iid] = new_d
                    self.after(0, lambda x=iid, d=new_d: self.update_single_tree_row(x, d))
                os.remove(t_csv)
            self.after(0, lambda v=(i+1)/total: self.app.global_progress.set(v))
        self.after(0, self.reset_scan_buttons)
        # Abschluss
        
        self.after(0, lambda: self.app.log_tab.log("✅ Multi-Rescan finished."))
                # --- HIER NACH DER MESSAGEBOX ---
        self.app.lift()
        self.app.focus_force() 
        

    def update_single_tree_row(self, iid, d):
        """Aktualisiert eine einzelne Zeile nach dem Rescan und schaltet das Label auf Grün"""
        # 1. BEATS KONVERTIEREN (Wichtig: Das fehlte oft beim Rescan!)
        if 'Beats' in d and isinstance(d['Beats'], str) and d['Beats'].strip():
            try:
                d['detected_beats'] = np.array([float(x) for x in d['Beats'].split(";")])
            except:
                d['detected_beats'] = None
        else:
            d['detected_beats'] = None

        # 2. Daten in der internen Map speichern
        self.data_map[iid] = d

        # 3. Werte in der Tabelle (Treeview) anzeigen
        old_n = self.tree.item(iid, 'values')[0]
        vals = (old_n, d['BPM'], d.get('Time','--:--'), d.get('Camelot','-'), d['Key'], d.get('Tags','-'), d['Dateiname'])
        self.tree.item(iid, values=vals)
        
        # Farbe aktualisieren (Camelot Tag)
        tag = d.get('Camelot', '-') if d.get('Camelot') in CAMELOT_COLORS else ''
        self.tree.item(iid, tags=(tag,))

        # 4. UI REFRESH: Wenn der bearbeitete Track gerade markiert ist, Label auf Grün!
        sel = self.tree.selection()
        if sel and sel[0] == iid:
            self.detected_beats = d['detected_beats'] # Magnet sofort laden
            if self.detected_beats is not None:
                self.lbl_loop_info.configure(text="🟢 Quantized (Snap OK)", text_color="#00AA00")
            else:
                self.lbl_loop_info.configure(text="⚪ No Beatgrid", text_color="gray")

    def reset_scan_buttons(self):
        self.is_scanning = False
        self.is_loading = False     # <--- NEU (Stoppt Pulsieren)
        self.btn_scan.configure(state="normal")
        self.btn_stop_scan.configure(state="disabled")

    # --- UI HELPERS ---

    def update_timer(self):
        if (pygame.mixer.music.get_busy() or self.is_looping) and not self.is_paused:
            
            # --- FIX: Sicherheits-Check für sampler_in ---
            # Wir prüfen: Ist Looping an? Haben wir eine Dauer? UND ist sampler_in noch da?
            if self.is_looping and self.current_loop_duration > 0 and self.sampler_in is not None:
                # Präzise Loop-Position berechnen
                elapsed = time.perf_counter() - self.loop_start_time
                curr = self.sampler_in + (elapsed % self.current_loop_duration)
            else:
                # Normalfall (oder wenn Daten während des Übergangs kurz fehlen)
                curr = self.get_current_time()

            # Anzeige aktualisieren
            self.lbl_time.configure(text=f"{self.format_time(curr)} / {self.format_time(self.total_duration)}")
            
            if self.total_duration > 0:
                # Slider nur updaten, wenn er nicht gerade gezogen wird (optional, aber gut)
                # Hier einfach setzen:
                self.play_slider.set((curr / self.total_duration) * 100)
            
            self.after(500, self.update_timer)

        # Fall B: Musik ist aus (und nicht pausiert) 🔇
        elif not pygame.mixer.music.get_busy() and not self.is_paused:

            # Prüfen, ob wir zum nächsten Song springen dürfen
            if not getattr(self, 'manual_stop', False):
                self.lbl_status_title.configure(text="🟡 Next track...", text_color="yellow")
                self.lbl_status_artist.configure(text="Loading upcoming song...")
                self.play_next_track()
                return 
            else:
                self.lbl_status_title.configure(text="🏁 Track End.", text_color="gray")
                self.lbl_status_artist.configure(text="")
                
    def update_ui_info(self, track):
        """Aktualisiert Cover, Titel und Artist zentral"""
        fpath = track['Pfad']
        
        # 1. Frische Tags direkt aus der Datei lesen
        from helpers import read_tags_quick
        tags = read_tags_quick(fpath)
        
        # Daten aus den Tags extrahieren
        artist = tags.get('artist')
        title = tags.get('title')
        
        # Fallback: Wenn Tags leer sind, nimm den Dateinamen
        if not title:
            title = track.get('Dateiname', 'Unknown Title')
        if not artist or artist == "-":
            artist = "Unknown Artist"
        
        # Kürzen für die Optik
        if len(title) > 50: title = title[:47] + "..."
        if len(artist) > 50: artist = artist[:47] + "..."
        
        # UI Texte setzen
        self.lbl_ana_title.configure(text=f"💿 {title}")
        self.lbl_ana_artist.configure(text=f"👤 {artist}")
        
        # 2. Cover laden (Logik bleibt gleich)
        from helpers import extract_cover_data
        from PIL import Image
        import io
        
        data = extract_cover_data(fpath)
        if data:
            try:
                img = Image.open(io.BytesIO(data))
                img.thumbnail((180, 180))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(180, 180))
                self.ana_cover_label.configure(image=ctk_img, text="")
            except:
                self.ana_cover_label.configure(image="", text="🎵")
        else:
            self.ana_cover_label.configure(image="", text="🎵")

    def format_time(self, s):
        return f"{int(s//60):02d}:{int(s%60):02d}"

    def get_current_time(self):
        if not pygame.mixer.music.get_busy() and not self.is_paused: return 0.0
        return (pygame.mixer.music.get_pos() / 1000.0) + self.playback_offset

    def on_slider_seek(self, v):
        if self.is_looping or not self.current_playing_path: return
        pos = (v / 100) * self.total_duration
        pygame.mixer.music.play(start=pos)
        self.playback_offset = pos; self.is_paused = False
        self.btn_play.configure(text="⏸ Pause", fg_color="#FFA500")

    def ins(self, t):
        tag = t.get('Camelot', '-') if t.get('Camelot') in CAMELOT_COLORS else ''
        v = (len(self.tree.get_children())+1, t['BPM'], t.get('Time','--:--'), t.get('Camelot','-'), t['Key'], t.get('Tags','-'), t['Dateiname'])
        iid = self.tree.insert('', 'end', values=v, tags=(tag,))
        self.data_map[iid] = t

    def sort_tree(self, col, rev):
        # 1. Visuelle Sortierung (Treeview)
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]

        # Weiche: Zahlen oder Text?
        if col in ("#", "BPM"):
            def num_key(item):
                val = item[0]
                if val == "▶": return -1.0 
                try: return float(val)
                except: return 0.0
            l.sort(key=num_key, reverse=rev)
        else:
            try: l.sort(key=lambda x: str(x[0]).lower(), reverse=rev)
            except: pass

        # Zeilen neu anordnen
        for i, (_, k) in enumerate(l): self.tree.move(k, '', i)
        
        # Header Befehl umdrehen
        self.tree.heading(col, command=lambda: self.sort_tree(col, not rev))

        # --- NEU: HARD SYNC (Datenbank sortieren) ---
        # Wir sortieren jetzt auch die interne Liste self.all_tracks,
        # damit die Ordnung beim Tab-Wechsel bleibt.
        
        # Mapping: Welcher Header gehört zu welchem Daten-Feld?
        col_map = {
            "BPM": "BPM",
            "Time": "Time",
            "Camelot": "Camelot",
            "Key": "Key",
            "Tags": "Tags",
            "Filename": "Dateiname" # Wichtig: Header heißt Filename, Daten heißen Dateiname
        }

        if col in col_map:
            key_name = col_map[col]
            try:
                if col == "BPM":
                    # Zahlen-Sortierung für Datenbank
                    self.all_tracks.sort(key=lambda x: float(x.get(key_name, 0)), reverse=rev)
                else:
                    # Text-Sortierung für Datenbank
                    self.all_tracks.sort(key=lambda x: str(x.get(key_name, "")).lower(), reverse=rev)
            except Exception as e:
                print(f"Data Sort Error: {e}")
        # --------------------------------------------

    def set_in(self):
        self.sampler_in = self.get_snapped_time(self.get_current_time())
        self.lbl_loop_info.configure(text=f"🔽 IN: {self.sampler_in:.2f}s", text_color="#00FF00")
        self.update_visual_markers()

    def set_out(self):
        if self.sampler_in is None: return
        self.sampler_out = self.get_snapped_time(self.get_current_time())
        if self.sampler_out <= self.sampler_in: return
        self.lbl_loop_info.configure(text="🔼 OUT SET", text_color="#FF0000")
        self.update_visual_markers()

    def get_snapped_time(self, t):
        if not self.var_snap.get() or self.detected_beats is None: return t
        idx = (np.abs(self.detected_beats - t)).argmin()
        return self.detected_beats[idx]

    def set_smart_bar(self, b):
        if not self.current_playing_path: return
        
        # 1. Falls kein IN-Punkt da ist, setzen (nutzt dein set_in mit Snap)
        
        self.set_in()
            
        # 2. Schläge berechnen (1 Bar = 4 Beats)
        needed_beats = b * 4
        
        # 3. FALL A: BEATGRID VORHANDEN (Präzisions-Modus)
        if self.detected_beats is not None and len(self.detected_beats) > 0:
            try:
                # Finde den Index des aktuellen IN-Punktes im Grid
                idx = (np.abs(self.detected_beats - self.sampler_in)).argmin()
                target_idx = idx + needed_beats
                
                # Setze OUT exakt auf den Schlag im Grid
                if target_idx < len(self.detected_beats):
                    self.sampler_out = self.detected_beats[target_idx]
                else:
                    self.sampler_out = self.detected_beats[-1]
                    
                self.lbl_loop_info.configure(text=f"🤖 Smart {b}B (Grid-Locked)", text_color="#00AA00")
            except:
                # Sicherheits-Fallback auf Mathe
                self.sampler_out = self.sampler_in + ((60/self.track_bpm)*needed_beats)
        
        # 4. FALL B: KEIN GRID DA (Deine bewährte Mathe-Logik)
        elif self.track_bpm > 0:
            self.sampler_out = self.sampler_in + ((60/self.track_bpm)*needed_beats)
            self.lbl_loop_info.configure(text=f"🤖 Smart {b}B (Math-Only)", text_color="orange")

        # 5. UI & Audio starten
        self.update_visual_markers()
        self.preview_loop()

    def update_visual_markers(self):
        if self.total_duration <= 0: return
        p, s = 0.025, 0.95
        if self.sampler_in: self.marker_in.place(relx=p+(self.sampler_in/self.total_duration)*s, rely=0.5, anchor="center")
        if self.sampler_out: self.marker_out.place(relx=p+(self.sampler_out/self.total_duration)*s, rely=0.5, anchor="center")

    def save_cut(self):
        if not self.current_playing_path or self.sampler_in is None or self.sampler_out is None: return
        f = filedialog.asksaveasfilename(defaultextension=".wav")
        if f:
            d, sr = sf.read(self.current_playing_path)
            sf.write(f, d[int(self.sampler_in*sr):int(self.sampler_out*sr)], sr)
            messagebox.showinfo("Saved", f"Loop saved: {f}")
        self.app.lift()
        self.app.focus_force()    

    def show_track_details(self, event=None):
        """Öffnet Details. Verhindert Mehrfach-Fenster bei gedrückter Taste."""
        
        # 1. TÜRSTEHER: Ist das Fenster schon offen?
        if hasattr(self, 'info_window') and self.info_window is not None and self.info_window.winfo_exists():
            # Ja -> Nur nach vorne holen und Fokus geben
            self.info_window.lift()
            self.info_window.focus()
            return # WICHTIG: Hier abbrechen!

        # 2. Wenn nicht offen -> Neu erstellen
        sel = self.tree.selection()
        if not sel: return
        
        # Pfad holen (Sicherheits-Check falls ID nicht in Map)
        if sel[0] in self.data_map:
            path = self.data_map[sel[0]]['Pfad']
            self.info_window, self.info_textbox = show_details_popup(self, path)
        self.app.lift()
        self.app.focus_force() # Falls erfolgreich, Fokus zurück

    def update_info_window(self, path):
        """Aktualisiert das Detail-Fenster, falls es offen ist."""
        # Prüfen: Existiert das Fenster noch?
        if hasattr(self, 'info_window') and self.info_textbox and self.info_window is not None and self.info_window.winfo_exists():
            try:
                # Neuen Text holen
                text = get_raw_metadata_string(path)
                
                # Textfeld beschreiben (erst entsperren, dann schreiben, dann sperren)
                self.info_textbox.configure(state="normal")
                self.info_textbox.delete("0.0", "end")
                self.info_textbox.insert("0.0", text)
                self.info_textbox.configure(state="disabled")
                
                # Fenster nach vorne holen (optional, damit es nicht verschwindet)
                # self.info_window.lift() 
            except: pass

    def open_current_in_finder(self):
        sel = self.tree.selection()
        if sel and sel[0] in self.data_map:
            path = self.data_map[sel[0]]['Pfad']
            reveal_in_finder(path)

    def send_to_editor(self):
        p = self.get_selected_paths()
        if p: self.app.editor_tab.load_external_files(p); self.app.tabview.set(self.app.tab_name_editor)

    def send_to_stems(self):
        p = self.get_selected_paths()
        if p: self.app.stems_tab.load_external_files(p); self.app.tabview.set(self.app.tab_name_stems)

    def send_to_trans(self):
        p = self.get_selected_paths()
        if p: self.app.trans_tab.load_external_files(p); self.app.tabview.set(self.app.tab_name_transcribe)

    def get_selected_paths(self):
        return [self.data_map[i]['Pfad'] for i in self.tree.selection() if i in self.data_map]

    def reset_status_to_ready(self):
        """Setzt den Haupt-Status zurück, wenn keine Musik läuft"""
        # Nur zurücksetzen, wenn nicht in der Zwischenzeit ein neues Lied gestartet wurde
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            self.lbl_status_title.configure(text="🟢 Ready for play.", text_color="#00AA00")
            
            self.lbl_status_artist.configure(text="")
            
    def reset_loop_info(self):
        """Setzt die Anzeige zurück, falls kein neuer Punkt gesetzt wurde"""
        if self.sampler_in is None:
            self.lbl_loop_info.configure(text="🟢🔁 Ready for Looping",text_color="#00AA00")        

    def browse_local(self):
        f = filedialog.askdirectory()
                # --- HIER NACH DER MESSAGEBOX ---
        
        if f: 
            self.local_path_entry.delete(0, "end"); self.local_path_entry.insert(0, f)
            self.app.path_entry.delete(0, "end"); self.app.path_entry.insert(0, f)
        self.app.lift()
        self.app.focus_force()   

    def add_files_dialog(self):
        # Mehrere Dateien auswählen
        files = filedialog.askopenfilenames(filetypes=[("Audio", "*.mp3 *.wav *.flac *.aiff *.aif *.m4a")])
          # --- FALL A: ABBRUCH ---
        if not files: 
            self.app.lift()
            self.app.focus_force()
            return
        
        # --- FALL B: DATEIEN GEWÄHLT ---
        # App wieder nach vorne holen, bevor der Scan-Thread startet
        self.app.lift()
        self.app.focus_force()
                # --- NEU: Buttons umschalten ---
        self.is_scanning = True
        self.btn_scan.configure(state="disabled")
        self.btn_stop_scan.configure(state="normal")
        # -------------------------------        
        # Parameter holen
        mi = self.bpm_min.get() if self.bpm_min.get().isdigit() else "0"
        ma = self.bpm_max.get() if self.bpm_max.get().isdigit() else "999"
        w_tags = "True" if self.var_write_tags.get() else "False"
                # NEU: Tab wechseln & Balken resetten
        self.app.tabview.set(self.app.tab_name_log)
        # KEINE Animation, sondern Start bei 0
        self.app.global_progress.set(0)
        self.is_loading = True
        self.animate_loading()
        # ------------------------------        
        count = len(files)
        plural = "" if count == 1 else "s"

        self.app.log_tab.log(f"Add {count} file{plural} 📁...")
        
        # Thread starten, damit GUI nicht einfriert
        threading.Thread(target=self.run_add_files_batch, args=(files, w_tags, mi, ma), daemon=True).start() 

    def load_external_files(self, files):
        """
        Empfängt Dateien und zeigt den Log-Eintrag SOFORT an.
        """
        if not files: return

        # 1. UI vorbereiten
        self.is_scanning = True
        self.btn_scan.configure(state="disabled")
        self.btn_stop_scan.configure(state="normal")
        
        # 2. Loggen & Tab wechseln
        count = len(files)
        self.app.log_tab.log(f"📥 Receiving {count} files from external tab...")        
        self.app.tabview.set(self.app.tab_name_log)
        self.app.lift()         
        # --- DER FIX: UI-Update erzwingen! ---
        # Damit wird der Text sofort sichtbar gezeichnet.
        self.app.update_idletasks() 
        # -------------------------------------
        # 3. Lade-Animation starten
        self.app.global_progress.set(0)
        self.is_loading = True
        self.animate_loading()
        
        # 4. Parameter lesen
        mi = self.bpm_min.get() if self.bpm_min.get().isdigit() else "0"
        ma = self.bpm_max.get() if self.bpm_max.get().isdigit() else "999"
        w_tags = "True" if self.var_write_tags.get() else "False"
        
        # 5. Prozess starten
        threading.Thread(target=self.run_add_files_batch, args=(files, w_tags, mi, ma), daemon=True).start()
        
    def run_add_files_batch(self, files, w_tags, mi, ma):
        import tempfile, time, uuid
        total = len(files)
        
        # --- 1. DIE SCHLEIFE (Nur für die Analyse der einzelnen Dateien) ---
        for i, fpath in enumerate(files):
            if not self.is_scanning or self.app.closing: 
                break

            unique_id = uuid.uuid4().hex[:8]
            temp_csv = os.path.join(tempfile.gettempdir(), f"pro_add_{unique_id}.csv")
            cmd = get_worker_cmd("analyzer") + [fpath, temp_csv, w_tags, mi, ma]
            
            try:
                self.after(0, lambda n=os.path.basename(fpath): self.app.log_tab.log(f"🔍 Analyzing: {n}"))
                
                # Führt die Analyse aus
                subprocess.run(cmd, capture_output=True, text=True)
                
                # Daten importieren (Fortschrittsbalken und CSV einlesen)
                self.after(0, lambda v=(i+1)/total: self.app.global_progress.set(v))
                self.after(0, lambda c=temp_csv: self.finish_add_file(c))
                
            except Exception as e:
                print(f"Error at file {i}: {e}")

        # --- 2. NACH DER SCHLEIFE (Einmalige Finalisierung für alle Dateien) ---
        # Dieser Teil ist jetzt korrekt eingerückt und läuft erst, wenn alle Dateien fertig sind.
        
        self.after(500, self.reset_scan_buttons)
        
        if self.is_scanning:
            # Tab-Wechsel und Progress-Reset
            self.after(600, lambda: self.app.tabview.set(self.app.tab_name_analyze))
            self.after(700, lambda: self.app.global_progress.set(1.0))
            
            def finalize_import():
                count = len(files)
                msg = f"{count} track{'s' if count != 1 else ''} added successfully ✅"
                
                # Markiert den ersten Track und lädt die Infos
                self.select_first_track()
                
                # Zeigt die Erfolgsmeldung (nur 1x!)
                messagebox.showinfo("Import Success", msg, parent=self.app)
                
                # Fokus zurück auf die App und die Liste
                self.app.lift()
                self.app.focus_force()
                self.tree.focus_set()
            
            # Finalisierung nach 800ms starten
            self.after(800, finalize_import)
    
    def finish_add_file(self, csv_path):
        """Liest das Ergebnis ein und konvertiert die Beats für den Snap-Effekt"""
        if os.path.exists(csv_path):
            try:
                # 1. Lade die temporäre CSV
                df = pd.read_csv(csv_path)
                
                if not df.empty:
                    # Nimm die Daten der neuen Datei
                    new_data = df.to_dict('records')[0]
                    
                    # --- FIX: BEATS KONVERTIEREN (Das hat hier gefehlt!) ---
                    if 'Beats' in new_data and isinstance(new_data['Beats'], str) and new_data['Beats'].strip():
                        try:
                            # Wandelt den Text "1.2;2.4" wieder in ein Zahlen-Array um
                            new_data['detected_beats'] = np.array([float(x) for x in new_data['Beats'].split(";")])
                        except:
                            new_data['detected_beats'] = None
                    else:
                        new_data['detected_beats'] = None
                    # -------------------------------------------------------

                    # In interne Liste und Tabelle einfügen
                    self.all_tracks.append(new_data)
                    self.ins(new_data)
                    self.renum()
                    
                    # Zum neuen Eintrag scrollen
                    children = self.tree.get_children()
                    if children:
                        self.tree.see(children[-1])
                
                # Datei löschen
                os.remove(csv_path)
            except Exception as e:
                self.app.log_tab.log(f"Import Error in File+: {e}")
               
                        
                
    def analyze_beats_bg(self, p):
        try:
            y, sr = librosa.load(p, sr=22050, mono=True, duration=120)
            _, b = librosa.beat.beat_track(y=y, sr=sr)
            self.detected_beats = librosa.frames_to_time(b, sr=sr)
        except: pass

    def stop_scan_process(self):
        """Bricht den laufenden Scan ab"""
        self.is_scanning = False
        
        self.app.log_tab.log("🛑 Abort requested...")
        self.btn_stop_scan.configure(state="disabled")
    #-----------------drag and drop in der Ülaylist------------#
    def on_tree_select(self, event):
        sel = self.tree.selection()
        if sel and sel[0] in self.data_map:
                        # --- WICHTIG: ALTES GEDÄCHTNIS LÖSCHEN ---
            self.reset_sampler_state()
            
            # --- 2. UI-RESET (Marker verstecken) ---
            self.marker_in.place(relx=-1)
            self.marker_out.place(relx=-1)
            
            # --- 3. NEUE DATEN LADEN ---
            track = self.data_map[sel[0]]
            self.last_selected_path = track['Pfad']
            
            # Beatgrid aus dem Speicher holen (On-the-fly)
            self.detected_beats = track.get('detected_beats')
            
            # --- 4. STATUS LABEL AKTUALISIEREN ---
            if self.detected_beats is not None and len(self.detected_beats) > 0:
                self.lbl_loop_info.configure(text="🟢 Quantized (Snap OK)", text_color="#00AA00")
            else:
                self.lbl_loop_info.configure(text="⚪ No Beatgrid", text_color="gray")
            
            # --- 5. RECHTES PANEL UPDATEN (Cover/Titel) ---
            self.update_ui_info(track)
    
    def renum(self):
        for i, id in enumerate(self.tree.get_children()): self.tree.set(id, column="#", value=i+1) 
    
    def on_drag_start(self, event): i = self.tree.identify_row(event.y); self.drag_item = i if i else None
    
    def on_drag_release(self, event):
        """Verschiebt die Zeile an die neue Position und nummeriert neu"""
        if not getattr(self, 'drag_item', None):
            return
            
        # Ziel-Zeile unter der Maus finden
        target_item = self.tree.identify_row(event.y)
        
        if target_item and target_item != self.drag_item:
            # Index der Zielzeile ermitteln
            target_index = self.tree.index(target_item)
            # Verschieben
            self.tree.move(self.drag_item, '', target_index)
            # Zahlen in der Spalte "#" korrigieren
            self.renum()
            
        self.drag_item = None
    #---------------------------------------------------------#        
    def focus_on_playlist(self, event=None):
        """Springt zurück zum aktuell spielenden oder zuletzt markierten Track"""
        # 1. Welchen Pfad suchen wir? 
        # Prio 1: Was gerade läuft. Prio 2: Was zuletzt angeklickt wurde.
        target_path = getattr(self, 'current_playing_path', None) or getattr(self, 'last_selected_path', None)
        
        found_id = None
        
        if target_path:
            # Wir gehen alle sichtbaren Zeilen durch und suchen den Pfad
            for iid in self.tree.get_children():
                if iid in self.data_map and self.data_map[iid]['Pfad'] == target_path:
                    found_id = iid
                    break
        
        # 2. Wenn gefunden, dorthin springen
        if found_id:
            self.tree.selection_set(found_id)
            self.tree.focus(found_id)
            self.tree.see(found_id)
            self.update_ui_info(self.data_map[found_id])
        else:
            # Nur wenn das Lied nicht in der Liste ist (z.B. weggefiltert), nimm das erste
            self.select_first_track()

        self.tree.focus_set()
        return "break"
        
        
    def play_next_track(self):
        """Wählt den nächsten Track in der Liste und spielt ihn"""
        sel = self.tree.selection()
        if not sel: return
        
        current_id = sel[0]
        all_ids = self.tree.get_children()
        
        try:
            current_index = all_ids.index(current_id)
            next_index = current_index + 1
            
            # Gibt es noch einen nächsten Track?
            if next_index < len(all_ids):
                next_id = all_ids[next_index]
                
                # 1. Markierung verschieben
                self.tree.selection_set(next_id)
                self.tree.focus(next_id)
                self.tree.see(next_id) # Automatisch hinscrollen
                
                # 2. Abspielen
                self.play_track()
            else:
                self.lbl_status_title.configure(text="Playlist End 🏁.", text_color="gray")
                self.lbl_status_artist.configure(text="")
        except:
            pass
        
    def seek_rel(self, seconds):
        if not self.current_playing_path: return
        try:
            current_ms = pygame.mixer.music.get_pos()
            if current_ms == -1: return
            current_sec = (current_ms / 1000.0) + self.playback_offset
            new_pos = max(0, current_sec + seconds)
            pygame.mixer.music.play(start=new_pos)
            self.playback_offset = new_pos
            self.is_paused = False
            self.btn_play.configure(text="⏸ Pause", fg_color="#FFA500")
            self.update_timer()
        except: pass
        
    def set_font_size(self, size):
        style = ttk.Style()
        style.configure("Treeview", font=('Arial', size), rowheight=int(size*2.2))
        style.configure("Treeview.Heading", font=('Arial', size, 'bold'))
            # Titel bekommt die volle gewählte Größe
        self.lbl_ana_title.configure(font=("Arial", size, "bold"))
        
        # Artist etwas kleiner (z.B. 2 Stufen weniger, aber mindestens 12)
        self.lbl_ana_artist.configure(font=("Arial", max(12, size - 2)))    
        
    def animate_loading(self, step=0):
            if not self.is_loading: return
            # Lässt den Balken weich hin und her pulsieren
            val = (math.sin(step * 0.15) + 1) / 2 
            self.app.global_progress.set(val)
            self.after(50, lambda: self.animate_loading(step + 1))
            
    def select_first_track(self):
        """Markiert automatisch den ersten Track in der Liste"""
        children = self.tree.get_children()
        if children:
            first_id = children[0]
            # 1. In der Tabelle markieren
            self.tree.selection_set(first_id)
            # 2. Den Fokus für Tastatur-Navigation setzen
            self.tree.focus(first_id)
            # 3. Sicherstellen, dass er sichtbar ist
            self.tree.see(first_id)
            # 4. Cover und Titel im UI laden
            # --- DIESE ZEILE IST DER SCHLÜSSEL ---
        # 2. UI (Cover/Titel) laden
        if first_id in self.data_map:
            self.update_ui_info(self.data_map[first_id])
            
        # 3. Fokus erzwingen (mit kleiner Verzögerung für macOS)
        self.after(100, lambda: self.tree.focus_set()) 
        
    def set_smart_bar(self, bars):
        """Setzt den OUT-Punkt basierend auf dem echten Beat-Grid (Traktor-Style)"""
        if not self.current_playing_path: return
        
        # 1. Sicherstellen, dass ein IN-Punkt existiert
        if self.sampler_in is None:
            self.set_in()
            
        # 2. Wie viele Beats brauchen wir? (1 Bar = 4 Beats)
        needed_beats = bars * 4
        
        # 3. Beat-Grid Navigation (Die präzise Methode)
        if self.detected_beats is not None and len(self.detected_beats) > 0:
            # Finde den Index des aktuellen IN-Punktes im Grid
            idx = (np.abs(self.detected_beats - self.sampler_in)).argmin()
            
            # Ziel-Index berechnen (IN-Index + Anzahl Beats)
            target_idx = idx + needed_beats
            
            # Prüfen, ob der Song lang genug ist
            if target_idx < len(self.detected_beats):
                self.sampler_out = self.detected_beats[target_idx]
                self.lbl_loop_info.configure(text=f"🤖 Smart {bars}B (Grid-Locked)", text_color="#00AA00")
            else:
                # Fallback falls Ende erreicht
                self.sampler_out = self.detected_beats[-1]
        
        # 4. Mathematischer Fallback (nur falls kein Grid vorhanden ist)
        elif self.track_bpm > 0:
            duration = (60.0 / self.track_bpm) * needed_beats
            self.sampler_out = self.sampler_in + duration
            self.lbl_loop_info.configure(text=f"🤖 Smart {bars}B (Math-Only)", text_color="orange")

        # 5. UI Update & Loop starten
        self.update_visual_markers()
        self.preview_loop()   
        
    def reset_sampler_state(self):
            """Löscht alle Loop-Daten und stoppt das 'Festfressen' 🧹"""
            self.is_looping = False
            self.exit_pending = False
            self.sampler_in = None
            self.sampler_out = None
            self.current_loop_duration = 0
            self.loop_start_time = 0
            
            # Marker verstecken
            self.marker_in.place(relx=-1)
            self.marker_out.place(relx=-1)
            self.lbl_loop_info.configure(text="🟢 Ready", text_color="#00AA00")                                      