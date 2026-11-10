# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import sys
import os
#os.environ['NUMBA_NUM_THREADS'] = '1'
#os.environ['NUMBA_THREADING_LAYER'] = 'workqueue'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
# Erst danach:
import shutil
import threading
import pandas as pd
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time
import urllib.parse
from PIL import Image, ImageTk 
import mutagen
import pygame
import soundfile as sf

# Importiere die Tabs aus dem Unterordner
from tabs.tab_analyze import AnalyzeTab
from tabs.tab_editor import EditorTab
from tabs.tab_stems import StemsTab
from tabs.tab_melody import MelodyTab
from tabs.tab_transcribe import TranscribeTab
from tabs.tab_chat import ChatTab
from tabs.tab_log import LogTab

from helpers import perform_export, perform_update, safe_playlist_name, EXPORT_EXTENSIONS, ShortcutOverviewWindow

# Setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
pygame.mixer.init()

class DJApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DJ Gadget AI Suite Pro 2026 v3.3 @bagueDev")
        self.geometry("1200x800")
        self.closing = False 
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.about_window = None
        
        # Layout Grid
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- 1. HEADER ---
        self.header = ctk.CTkFrame(self, height=60, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        # Globaler Pfad (wird mit Analyze-Tab synchronisiert)
        self.path_entry = ctk.CTkEntry(self.header, placeholder_text="Music directory path..")
        #self.path_entry.pack(side="left", fill="x", expand=True, padx=10)
        
        #ctk.CTkButton(self.header, text="📂 Open", width=80, command=self.browse_folder).pack(side="left")
        
        ctk.CTkLabel(self.header, text="Font Size 🔠 ", font=("Arial", 12)).pack(side="left", padx=(20, 5))
        self.font_menu = ctk.CTkOptionMenu(self.header, values=["12", "14", "16", "18", "20"], width=60, command=self.change_font_size)
        self.font_menu.set("14")
        self.font_menu.pack(side="left")
        # --- Appearance Mode (Dark/Light) ---
        ctk.CTkLabel(self.header, text="🌓 Mode:").pack(side="left", padx=(20, 5))
        self.appearance_mode_menu = ctk.CTkOptionMenu(
            self.header, 
            values=["Dark", "Light", "System"], 
            width=100, 
            command=self.change_appearance_mode
        )
        self.appearance_mode_menu.set("Dark") # Standardwert
        self.appearance_mode_menu.pack(side="left", padx=10)
        
        # NEU: Info Button ganz links
        ctk.CTkButton(self.header, text="ℹ️", width=30, command=self.open_about_window).pack(side="left", padx=4)
        # ? Button (Standard CustomTkinter Style - Blau)
        self.btn_help = ctk.CTkButton(self.header, text="?", width=30, 
                                      font=("Arial", 15, "bold"),
                                      command=self.open_shortcuts)
        self.btn_help.pack(side="left", padx=5)

        # --- GLOBAL VOLUME CONTROL (Oben Rechts) ---
        # Container für Lautstärke
        vol_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        vol_frame.pack(side="right", padx=20)

        # Mute Button
        self.btn_global_mute = ctk.CTkButton(vol_frame, text="🔊", width=30, 
                                             fg_color="transparent", hover_color="#333", 
                                             font=("Arial", 16),
                                             command=self.toggle_global_mute)
        self.btn_global_mute.pack(side="left", padx=(0, 5))

        # Slider
        self.global_vol_slider = ctk.CTkSlider(vol_frame, from_=0, to=100, 
                                               command=self.set_global_volume, 
                                               width=130, height=20,
                                               progress_color="transparent")
        self.global_vol_slider.set(80)
        self.global_vol_slider.pack(side="left")

        # Variablen für den Status
        self.is_muted = False
        self.last_vol_memory = 1.0

        # --- 2. PROGRESS ---
        self.global_progress = ctk.CTkProgressBar(self, height=15)
        self.global_progress.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.global_progress.set(0)

        # --- 3. TABS ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Namen definieren (wichtig für Zugriff aus anderen Tabs)
        self.tab_name_analyze = "🔍 Playlist & BPM"
        self.tab_name_editor = "✏️ Metadata"
        self.tab_name_stems = "✂️ Stems AI"
        self.tab_name_melody = "🎹 Melody Lab"
        self.tab_name_transcribe = "📝 Transcriber" 
        self.tab_name_chat = "🤖 AI Chat"
        self.tab_name_log = "📝 Log"
        
        # Tabs erstellen
        t_an = self.tabview.add(self.tab_name_analyze)
        t_ed = self.tabview.add(self.tab_name_editor)
        t_st = self.tabview.add(self.tab_name_stems)
        t_mel = self.tabview.add(self.tab_name_melody)
        t_tra = self.tabview.add(self.tab_name_transcribe)
        t_cha = self.tabview.add(self.tab_name_chat)
        t_log = self.tabview.add(self.tab_name_log)

        # Tab-Klassen laden und "self" (die App) übergeben
        self.log_tab = LogTab(t_log)
        self.log_tab.pack(fill="both", expand=True)

        self.analyze_tab = AnalyzeTab(t_an, self)
        self.analyze_tab.pack(fill="both", expand=True)
        
        self.editor_tab = EditorTab(t_ed, self)
        self.editor_tab.pack(fill="both", expand=True)
        
        self.stems_tab = StemsTab(t_st, self)
        self.stems_tab.pack(fill="both", expand=True)
        
        self.melody_tab = MelodyTab(t_mel, self)
        self.melody_tab.pack(fill="both", expand=True)
        
        self.trans_tab = TranscribeTab(t_tra, self)
        self.trans_tab.pack(fill="both", expand=True)
        
        self.chat_tab = ChatTab(t_cha, self)
        self.chat_tab.pack(fill="both", expand=True)

        # --- 4. FOOTER ---
        self.footer = ctk.CTkFrame(self, height=50)
        self.footer.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(self.footer, text="🛠️ Developer: @bagueDev | DJGAIS Pro Edition", text_color="gray", font=("Arial", 11)).pack(side="left", padx=10)
        
        self.var_rb = ctk.BooleanVar(value=True)
        self.var_m3u = ctk.BooleanVar(value=True)
        self.var_json = ctk.BooleanVar(value=True)
            # --- NEU: IMPORT BUTTON ---
        # Ruft die Funktion im Analyze-Tab auf
        ctk.CTkButton(self.footer, text="📥 IMPORT", command=lambda: self.analyze_tab.import_playlist_dialog(), fg_color="#555", width=100).pack(side="right", padx=5)
        # --------------------------

        ctk.CTkButton(self.footer, text="💾 EXPORT", command=self.do_export_main, fg_color="green", width=100).pack(side="right", padx=10)
        ctk.CTkButton(self.footer, text="🔄 UPDATE", command=self.do_update_main, fg_color="#007aff", width=100).pack(side="right", padx=5)
        
        self.playlist_name_entry = ctk.CTkEntry(self.footer, placeholder_text="Playlist Name...", width=150)
        self.playlist_name_entry.pack(side="right", padx=10)
        ctk.CTkLabel(self.footer, text="Name:").pack(side="right", padx=2)
        
        ctk.CTkCheckBox(self.footer, text="JSON", variable=self.var_json, width=60).pack(side="right", padx=5)
        ctk.CTkCheckBox(self.footer, text="M3U", variable=self.var_m3u, width=60).pack(side="right", padx=5)
        ctk.CTkCheckBox(self.footer, text="XML", variable=self.var_rb, width=60).pack(side="right", padx=5)
        
     
        # KEYBOARD SHORTCUTS BINDING
        self.bind("<Key>", self.handle_shortcuts)
        # Globaler Shortcut für Hilfe
        self.bind("<F1>", self.open_shortcuts)
        # Globaler Shortcut für Hilfe
        self.bind("<F2>", self.open_about_window)

        # --- SICHERHEIT: Cmd+W im Hauptfenster ignorieren ---
        # Verhindert, dass die App aus Versehen geschlossen wird.
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        self.bind("<Command-w>", lambda event: "break")
        self.bind("<Control-w>", lambda event: "break")

    def on_closing(self):
        self.closing = True
        pygame.mixer.music.stop()
        # Chat Prozess killen, falls er läuft
        if hasattr(self.chat_tab, 'chat_process') and self.chat_tab.chat_process:
            self.chat_tab.chat_process.terminate()
        self.destroy()

    def browse_folder(self):
        # Globale Ordnerwahl (Header)
        f = filedialog.askdirectory()
        if f: 
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, f)
            
            # Sync zu den Tabs
            if hasattr(self.analyze_tab, 'local_path_entry'):
                self.analyze_tab.local_path_entry.delete(0, "end")
                self.analyze_tab.local_path_entry.insert(0, f)
                # Automatisch Editor laden
                self.editor_tab.load_files()
        self.lift()
        self.focus_force()    

    def change_font_size(self, choice):
        size = int(choice)
        # Ruft die set_font_size Methode in jedem Tab auf
        self.log_tab.set_font_size(size)
        self.analyze_tab.set_font_size(size)
        self.editor_tab.set_font_size(size)
        self.stems_tab.set_font_size(size)
        # melody hat keine Liste/Text, daher optional
        self.trans_tab.set_font_size(size)
        self.chat_tab.set_font_size(size)

    def do_export_main(self):
        # 1. Daten prüfen
        if not hasattr(self.analyze_tab, 'data_map') or not hasattr(self.analyze_tab, 'tree'): 
            return
        
        ids = self.analyze_tab.tree.get_children()
        if not ids: 
            messagebox.showwarning("Info", "No tracks in the list 🚫")
            self.lift()
            self.focus_force()
            return

        track_list = [self.analyze_tab.data_map[i] for i in ids if i in self.analyze_tab.data_map]
        
        # 2. Formate prüfen
        formats = []
        if self.var_rb.get(): formats.append("Rekordbox")
        if self.var_m3u.get(): formats.append("M3U")
        if self.var_json.get(): formats.append("JSON")
        
        if not formats: 
            messagebox.showwarning("Info", "No format chosen 🚫 ")
            self.lift()
            self.focus_force()
            return
        
        # 3. Name holen
        pl_name = self.playlist_name_entry.get()
        if not pl_name.strip(): 
            pl_name = f"Import {time.strftime('%Y-%m-%d')}"
            
        # --- NEU: ZIEL-ORDNER WÄHLEN ---
        target = filedialog.askdirectory(title="Choose playlist location 📍 ")
        if not target: return # Abbrechen, wenn User nichts wählt
        # -------------------------------

        # 4. Ausführen
        msg = perform_export(track_list, target, formats, pl_name)
        self.log_tab.log(msg)
        messagebox.showinfo("Export", msg)
        self.lift()
        self.focus_force()

        # Zuletzt exportierte Pfade merken (für Update-Button)
        if msg.startswith("✅"):
            safe_name = safe_playlist_name(pl_name)
            self.analyze_tab.last_playlist_paths = [
                os.path.join(target, f"{safe_name}{EXPORT_EXTENSIONS[fmt]}") for fmt in formats
            ]

    def do_update_main(self):
        # 1. Daten prüfen
        if not hasattr(self.analyze_tab, 'data_map') or not hasattr(self.analyze_tab, 'tree'):
            return

        ids = self.analyze_tab.tree.get_children()
        if not ids:
            messagebox.showwarning("Info", "No tracks in the list 🚫")
            self.lift()
            self.focus_force()
            return

        track_list = [self.analyze_tab.data_map[i] for i in ids if i in self.analyze_tab.data_map]

        # 2. Pfad prüfen
        paths = list(getattr(self.analyze_tab, 'last_playlist_paths', []))
        if not paths:
            messagebox.showwarning("Info", "Keine Playlist zum Aktualisieren.\nBitte zuerst importieren oder exportieren. 🚫")
            self.lift()
            self.focus_force()
            return

        msgs = []
        existing = []
        for p in paths:
            if os.path.exists(p):
                existing.append(p)
            else:
                msgs.append(f"❌ Datei nicht gefunden: {os.path.basename(p)}")

        # 3. Rückfrage: Update überschreibt die Datei(en) komplett
        if existing:
            question = (
                f"Diese Datei(en) werden komplett mit den {len(track_list)} Tracks der Liste überschrieben:\n\n"
                + "\n".join(existing)
                + "\n\nDie alte Version wird als .bak daneben gesichert."
            )
            if getattr(self.analyze_tab, 'filter_active', False):
                question += "\n\n⚠️ Filter aktiv: Es werden nur die sichtbaren Tracks geschrieben!"
            ok = messagebox.askyesno("Update", question + "\n\nFortfahren?", icon="warning")
            self.lift()
            self.focus_force()
            if not ok:
                return

        # 4. Aktualisieren
        for p in existing:
            msg = perform_update(track_list, p)
            msgs.append(msg)
            self.log_tab.log(msg)

        self.analyze_tab.last_playlist_paths = existing
        messagebox.showinfo("Update", "\n".join(msgs))
        self.lift()
        self.focus_force()

    def open_shortcuts(self, event=None):
        """Öffnet das Hilfe-Fenster"""
        ShortcutOverviewWindow(self)

    def handle_shortcuts(self, event):
        # 1. Grundlegende Informationen holen
        current_tab = self.tabview.get()
        key = event.keysym.lower()
        is_mod = event.state & 0x8 or event.state & 0x4
         # 1. Liste IMMER definieren (ganz oben)
        tabs = [self.tab_name_analyze, self.tab_name_editor, self.tab_name_stems, 
            self.tab_name_melody, self.tab_name_transcribe, self.tab_name_chat,self.tab_name_log]
       
        
        # 2. GLOBALER FOKUS-CHECK
        # Wir wollen keine Shortcuts auslösen, wenn der User in IRGENDEINEM Feld schreibt
        focused_widget = self.focus_get()
        if isinstance(focused_widget, (tk.Entry, ctk.CTkEntry, ctk.CTkTextbox)):
            return # Abbrechen, User schreibt gerade

        # ---------------------------------------------------------
        # TABS SPEZIFISCHE SHORTCUTS
        # ---------------------------------------------------------

        # A. ANALYZER TAB
        if current_tab == self.tab_name_analyze:
            if key == "space":
                self.analyze_tab.toggle_play()
                
            elif key == "i":
                self.analyze_tab.set_in()
            elif key == "o":
                self.analyze_tab.set_out()
            elif key == "p":
                self.analyze_tab.preview_loop()
            elif key == "s":
                self.analyze_tab.stop_track()  
            elif key == "z":
                self.analyze_tab.undo_delete()  
            # WICHTIG: Prüfe, dass is_mod (Cmd/Strg) NICHT gedrückt ist!
            elif key == "left" and not is_mod: 
                self.analyze_tab.seek_rel(-10)
                
            elif key == "right" and not is_mod:
                self.analyze_tab.seek_rel(10)
        
                self.analyze_tab.seek_rel(10) 
            elif key == "1": self.analyze_tab.set_smart_bar(2)
            elif key == "2": self.analyze_tab.set_smart_bar(4)
            elif key == "3": self.analyze_tab.set_smart_bar(8)
            elif key == "4": self.analyze_tab.set_smart_bar(16)
            elif key == "5": self.analyze_tab.set_smart_bar(32)  
            elif key == "return": 
                self.analyze_tab.start_scan_thread()
            elif key == "l": 
                self.analyze_tab.save_cut()
            elif key == "numbersign": 
                self.browse_folder()
            elif key == "plus":
                self.analyze_tab.add_files_dialog()             
            elif key == "r":
                self.analyze_tab.delete_row() 
            elif key == "k":
                self.analyze_tab.exit_loop()
            elif key == "j":
                self.analyze_tab.import_playlist_dialog()
            elif key == "h":
                self.do_export_main()
            elif key == "escape":
                self.analyze_tab.stop_scan_process()
            elif key == "c":
                self.analyze_tab.clear_playlist()   
            elif key == "m":
                self.analyze_tab.show_track_details() 
            elif key == "0":
                self.volume_up()
            elif key == "9":
                self.volume_down()

        # B. STEMS TAB
        elif current_tab == self.tab_name_stems:
            if key == "escape":
                self.stems_tab.stop_processing()
            elif key == "return":
                self.stems_tab.start()
            if key == "numbersign":
                self.stems_tab.browse_add()
            if key == "r":
                self.stems_tab.remove_selected()
            if key == "c":
                self.stems_tab.clear_list()
            if key == "z":
                self.stems_tab.undo_action() 
            if key == "t":
                self.stems_tab.sync_from_playlist() 
            if is_mod and event.keysym == "9":
                self.volume_down()
                return "break"
            if is_mod and event.keysym == "0":
                self.volume_up()
                return "break"

        # C. CHAT TAB
        elif current_tab == self.tab_name_chat:
            # Hier keine Buchstaben-Shortcuts (da man hier schreibt)
            # Aber z.B. Escape zum Stoppen der KI
            if key == "escape":
                self.chat_tab.stop_chat_engine()
            if is_mod and event.keysym == "numbersign":
                self.chat_tab.browse_model_dir()
                return "break"   
            
            if is_mod and event.keysym == "plus":
                self.chat_tab.start_chat_engine()
                return "break"   
            if is_mod and event.keysym == "s":
                self.chat_tab.save_history_json()
                return "break" 
            if is_mod and event.keysym == "e":
                self.chat_tab.export_chat()
                return "break" 
            if is_mod and event.keysym == "d":
                self.chat_tab.clear_context()
                return "break"
            if is_mod and event.keysym == "9":
                self.volume_down()
                return "break"
            if is_mod and event.keysym == "0":
                self.volume_up()
                return "break"

        # D. TRANSCRIBER TAB
        elif current_tab == self.tab_name_transcribe:
            if key == "escape":
                self.trans_tab.stop_processing()
            if key == "return":
                self.trans_tab.start_batch()
            if key == "numbersign":
                self.trans_tab.browse_add()
            if key == "r":
                self.trans_tab.remove_selected()
            if key == "c":
                self.trans_tab.clear_list()
            if key == "z":
                self.trans_tab.undo_action() 
            if key == "t":
                self.trans_tab.sync_from_playlist() 
            if is_mod and event.keysym == "9":
                self.volume_down()
                return "break"
            if is_mod and event.keysym == "0":
                self.volume_up()
                return "break"

        # E. MELODY TAB
        elif current_tab == self.tab_name_melody:
            if key == "space":
                self.melody_tab.play()
            elif key == "return":
                self.melody_tab.generate()
            elif key == "plus" or key == "kp_add": # Normales Plus und Nummernblock-Plus
                self.melody_tab.generate_full_loop()

            if is_mod and event.keysym == "9":
                self.volume_down()
                return "break"
            if is_mod and event.keysym == "0":
                self.volume_up()
                return "break"
            if is_mod and event.keysym == "s":
                self.melody_tab.save_midi()
                return "break"
                
        # F. Editor TAB
        elif current_tab == self.tab_name_editor:
            if key == "numbersign":
                self.editor_tab.add_single_files()
            elif key == "r":
                self.editor_tab.remove_from_list() 
            if key == "c":
                self.editor_tab.clear_list()
            if key == "z":
                self.editor_tab.undo_action()
            if key == "v":
                self.editor_tab.browse_cover()
            if key == "t":
                self.editor_tab.load_files()
            if key == "m":
                self.editor_tab.show_more_info()          
            if is_mod and event.keysym == "s":
                self.editor_tab.save()
                return "break"
            if is_mod and event.keysym == "9":
                self.volume_down()
                return "break"
            if is_mod and event.keysym == "0":
                self.volume_up()
                return "break"

        # G. Log TAB
        elif current_tab == self.tab_name_log:
            if is_mod and event.keysym == "9":
                self.volume_down()
                return "break"
            if is_mod and event.keysym == "0":
                self.volume_up()
                return "break"

            # 2. In handle_shortcuts einbauen:
        if is_mod and key in ["right", "left"]:
            
            current = self.tabview.get()
            idx = tabs.index(current)
        
            if key == "right":
                new_idx = (idx + 1) % len(tabs)
            else:
                new_idx = (idx - 1) % len(tabs)
                
            self.focus_set() # <--- NEU: Zieht den Fokus vom Textfeld auf das Hauptfenster    
            self.tabview.set(tabs[new_idx])
            return "break" # <--- WICHTIG: Stoppt das Springen in Feldern! 

    def set_global_volume(self, value):
        """Steuert die Lautstärke global und synchronisiert den Analyzer."""
        import pygame # Sicherstellen, dass pygame bekannt ist

        vol = float(value) / 100.0

        # 1. Pygame Mixer direkt steuern (Global)
        try:
            pygame.mixer.music.set_volume(vol)
        except: pass

        # 2. Analyzer Tab synchronisieren (für Loops & Crossfades)
        if hasattr(self, 'analyze_tab'):
            self.analyze_tab.current_volume = vol
            # Falls gerade ein Loop läuft, auch den anpassen
            if hasattr(self.analyze_tab, 'loop_channel') and self.analyze_tab.loop_channel:
                self.analyze_tab.loop_channel.set_volume(vol)

        # 3. Icon Update
        if self.is_muted and vol > 0:
            self.is_muted = False
            self.btn_global_mute.configure(text="🔊", text_color="white")
        elif vol == 0:
            self.is_muted = True
            self.btn_global_mute.configure(text="🔇", text_color="red")

    def toggle_global_mute(self):
        if not self.is_muted:
            # MUTE
            self.last_vol_memory = self.global_vol_slider.get()
            self.global_vol_slider.set(0)
            self.set_global_volume(0)
            self.is_muted = True
            self.btn_global_mute.configure(text="🔇", text_color="red")
        else:
            # UNMUTE
            restore = self.last_vol_memory if self.last_vol_memory > 0 else 50
            self.global_vol_slider.set(restore)
            self.set_global_volume(restore)
            self.is_muted = False
            self.btn_global_mute.configure(text="🔊", text_color="white")

    def volume_up(self):
        """Lauter (Max 100)"""
        current = self.global_vol_slider.get()
        new_val = min(100, current + 5) # +5% Schritte
        self.global_vol_slider.set(new_val)
        self.set_global_volume(new_val)

    def volume_down(self):
        """Leiser (Min 0)"""
        current = self.global_vol_slider.get()
        new_val = max(0, current - 5)   # -5% Schritte
        self.global_vol_slider.set(new_val)
        self.set_global_volume(new_val)

    def change_appearance_mode(self, new_mode):
        # Dieser eine Befehl ändert das gesamte Theme der App sofort
        ctk.set_appearance_mode(new_mode) 
            # Den Analyzer-Tab informieren, falls er schon existiert
         # Alle Tabs mit Listboxen aktualisieren
        self.editor_tab.update_ui_colors(new_mode)
        self.stems_tab.update_ui_colors(new_mode)
        self.trans_tab.update_ui_colors(new_mode)
    def update_ui_colors(self, mode):
        if mode.lower() == "light":
            # Helle Farben für die Liste
            bg = "#ffffff"
            fg = "#000000"
            sel_bg = "#007aff" # Mac-Blau
        else:
            # Dunkle Farben (dein Standard)
            bg = "#2b2b2b"
            fg = "#ffffff"
            sel_bg = "#1f538d"

        # Die Listbox in diesem Tab anpassen
        self.file_listbox.configure(
            bg=bg, 
            fg=fg, 
            selectbackground=sel_bg,
            highlightthickness=0
        )    
            
    def open_about_window(self, event=None):

        # 1. TÜRSTEHER: Ist das Fenster schon offen?
        if self.about_window is not None and self.about_window.winfo_exists():
            self.about_window.lift()        # Nach vorne holen
            self.about_window.focus_force() # Aktivieren
            return # Abbruch!

        # 2. Fenster erstellen (in self speichern!)
        self.about_window = ctk.CTkToplevel(self)
        self.about_window.title("Über DJ Gadget AI-Suite Pro")
        self.about_window.geometry("369x409")

        self.about_window.resizable(True, True)
        self.about_window.attributes("-topmost", True)

        # Fokus setzen
        self.about_window.lift()
        self.about_window.focus_force()

        about = self.about_window
        # --- FIX: Cmd+W abfangen ---
        def close_about(event=None):
            self.about_window.destroy()
            self.about_window = None # Wichtig: Speicher leeren!
            return "break"

        about.bind("<Command-w>", close_about)
        about.bind("<Control-w>", close_about)
        # ---------------------------

        # 1. Titel & Dev
        ctk.CTkLabel(about, text="© DJ Gadget AI-Suite Pro", font=("Arial", 18, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(about, text=" © Version 3.3 | Build 2026 ", text_color="gray").pack()
        ctk.CTkLabel(about, text="Bascharan Guersoy ©", text_color="#007aff", font=("Arial", 12, "bold")).pack(pady=2)
        ctk.CTkLabel(about, text="Developed by @bagueDev", text_color="#007aff", font=("Arial", 12, "bold")).pack(pady=6)
        ctk.CTkLabel(about, text="Copyright © 2026 Bascharan Guersoy (@bagueDev)", text_color="gray", font=("Arial", 10)).pack(pady=1)
        ctk.CTkLabel(about, text="Licensed under GPLv3 — free & open source", text_color="gray", font=("Arial", 10)).pack(pady=1)
        
        def open_license():
            import os
            license_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LICENSE")
            if os.path.exists(license_path):
                os.system(f'open "{license_path}"')
            else:
                messagebox.showinfo("License", "LICENSE file not found.\nSee https://www.gnu.org/licenses/gpl-3.0.html")
        
        ctk.CTkButton(about, text="📜 View Full License (GPLv3)", width=200, command=open_license, fg_color="gray").pack(pady=5)
        
        ctk.CTkLabel(about, text="© achten.enteral.5z@icloud.com", text_color="#007aff", font=("Arial", 10, "bold")).pack(pady=1)
        
        # 2. Lizenz-Textfeld (Scrollbar)
        license_text = """
CONTRIBUTORS & LICENSES

This software ("DJ Gadget AI‑Suite Pro") uses various open‑source libraries.
A huge thank‑you to all developers and contributors who made these tools possible! 🎉


--- GUI & SYSTEM ---
• Python (PSF License)
• CustomTkinter (MIT License) – Tom Schimansky
• Pillow (HPND License) – Image Processing 🖼️


--- ARTIFICIAL INTELLIGENCE ---
• Demucs (MIT License) – Meta Research (Stems) 🎧
• Faster‑Whisper (MIT License) – Guillaume Klein (Lyrics) 🎤
• CTranslate2 (MIT License) – Inference Engine ⚙️
• Llama‑cpp‑python (MIT License) – Andrei Betlen (Chat) 💬
• PyTorch (BSD‑Style License) – Machine‑Learning Framework 🔥


--- AUDIO & MUSIC ---
• Librosa (ISC License) – Audio Analysis 🎶
• Soundfile (BSD License) – Audio I/O 🔊
• PyGame (LGPL License) – Audio Player ▶️
• MidiUtil (MIT License) – MIDI Generation 🎹
• Mutagen (GPLv2 License) * – Metadata Processing 🏷️


--- MATHEMATICS & DATA ---
• NumPy (BSD License)
• SciPy (BSD License)
• Pandas (BSD 3‑Clause License)


--- LEGAL NOTICE ---
This software uses the library "Mutagen",
which is licensed under the GNU General Public License (GPLv2).
Mutagen has been used without modification.
More information: https://mutagen.readthedocs.io/ 📚

This software does not include any AI model weights.
It functions solely as a client for loading and running
external GGUF models and other models such as Demucs or Whisper.

All used models are subject to their respective licenses
(e.g., MIT, CC‑BY‑NC, Llama Community License, or others).
Please review the license of each model before using it
for commercial purposes. ⚠️


--- DISCLAIMER ---
This software is provided "as is", without any express or implied
warranty. Use at your own risk. ⚡

No liability is assumed for data loss, incorrect results,
hardware damage, or any other damages arising from the use
of this software.

        """        
        textbox = ctk.CTkTextbox(about, width=450, height=400)
        textbox.pack(pady=10, padx=10)
        textbox.insert("0.0", license_text)
        textbox.configure(state="disabled") # Read-only
        
        # 3. Schließen Button
        ctk.CTkButton(about, text="Close", command=close_about).pack(pady=10)                                                       

if __name__ == "__main__":
    # Prüfen: Wurde die App als Worker gestartet?
    is_worker = len(sys.argv) > 1 and sys.argv[1] == "--worker"

    # WICHTIG für macOS/Windows Builds mit Multiprocessing
    import multiprocessing
    multiprocessing.freeze_support()

    # Prüfen: Wurde die App als Worker gestartet?
    if is_worker:
        worker_type = sys.argv[2]
        
        try:
            if worker_type == "analyzer":
                import analyzer
                analyzer.main_worker()  # <--- DIESER AUFRUF HAT GEFEHLT!
                # Falls analyzer.py eine main() hat: analyzer.main()
            elif worker_type == "separator":
                import separator
                separator.main_worker()
            elif worker_type == "transcriber":
                import transcriber
                transcriber.main_worker()
            elif worker_type == "chatbot":
                import chatbot
                chatbot.main_worker()
            
            else:
                print(f"Unbekannter Worker-Typ: {worker_type}")
            
            # WICHTIG: Nach dem Worker den Prozess beenden!
            sys.exit(0) 
            
        except Exception as e:
            print(f"Worker Fehler ({worker_type}): {e}")
            sys.exit(1)

    else:
        # Normaler Start: GUI öffnen
        # Nur hier darf die GUI initialisiert werden
        app = DJApp()
        app.mainloop()