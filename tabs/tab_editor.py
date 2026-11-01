# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
from helpers import read_tags_quick, get_executable_path, extract_cover_data, RightClickMenu, show_details_popup, get_raw_metadata_string, CAMELOT_COLORS, get_open_key, reveal_in_finder
import os
import sys
import subprocess
import threading
import io

class EditorTab(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.app = main_app
        self.editor_files = []
        self.current_editor_file = None
        self.current_cover_path = None
        
        # Platzhalter Bild
        self.placeholder_img = Image.new("RGBA", (200, 200), (50, 50, 50, 255)) 
        self.persistent_image = ctk.CTkImage(light_image=self.placeholder_img, dark_image=self.placeholder_img, size=(220, 200))
        
        self.info_window = None
        self.info_textbox = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT SIDE (Liste) ---
        f_left = ctk.CTkFrame(self)
        f_left.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        btn_w = 150
        ctk.CTkLabel(f_left, text="📁 Files 📁").pack(pady=5)
        ctk.CTkButton(f_left, text="🔄 Sync Playlist", command=self.load_files, width=btn_w,fg_color="#2b5e2b").pack(pady=5)
        ctk.CTkButton(f_left, text="📄 File+", command=self.add_single_files, width=btn_w, fg_color="#444").pack(pady=5)
        ctk.CTkButton(f_left, text="🚫 Remove Selected", command=self.remove_from_list, width=btn_w, fg_color="#AA0000").pack(pady=5)
        # In EditorTab.__init__
        ctk.CTkButton(f_left, text="🗑️ Clear all", command=self.clear_list, width=btn_w, fg_color="gray").pack(pady=5)
        self.undo_stack = []
        self.btn_undo = ctk.CTkButton(f_left, text="↩️ Undo", command=self.undo_action, 
                                    fg_color="#5E35B1", hover_color="#7B1FA2", 
                                    state="disabled", width=btn_w)
        self.btn_undo.pack(pady=5)
        
        # --- LISTE MIT SCROLLBAR (Container) ---
        # Wir bauen einen unsichtbaren Rahmen, damit Liste & Scrollbar zusammenbleiben
        list_container = ctk.CTkFrame(f_left, fg_color="transparent")
        list_container.pack(fill="both", expand=True, padx=5, pady=5)

        # 1. Die Scrollbar erstellen
        scrollbar = ctk.CTkScrollbar(list_container, orientation="vertical")
        scrollbar.pack(side="right", fill="y")

        # 2. Die Listbox erstellen (mit Link zur Scrollbar)
        self.file_listbox = tk.Listbox(list_container, 
                                       bg="#2b2b2b", 
                                       fg="white", 
                                       selectbackground="#007aff", 
                                       borderwidth=0, 
                                       font=("Arial", 14), 
                                       selectmode="extended",
                                       yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side="left", fill="both", expand=True)

        # 3. Scrollbar mit Liste verknüpfen (Rückrichtung)
        scrollbar.configure(command=self.file_listbox.yview)
        
        # --- RECHTSKLICK MENÜ FÜR LISTE ---
        self.list_context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#007aff")
        self.list_context_menu.add_command(label="🗑️ Remove from List", command=self.remove_from_list)
        self.list_context_menu.add_separator()
        self.list_context_menu.add_command(label="🔄 Sync/Reload", command=self.load_files)
        self.list_context_menu.add_separator()
        self.list_context_menu.add_command(label="🔍 Send to Analyzer", command=self.send_to_analyzer)
        self.list_context_menu.add_command(label="📂 Show in Finder", command=self.open_in_finder)
        
        # Bindings
        self.file_listbox.bind('<<ListboxSelect>>', self.on_select)
        self.file_listbox.bind("<Button-3>", self.show_context_menu) # Mac/Win Rechtsklick
        self.file_listbox.bind("<Button-2>", self.show_context_menu) # Mac Trackpad
        self.file_listbox.bind("<Control-Button-1>", self.show_context_menu) # Mac Ctrl+Klick

        # --- RIGHT SIDE (Editor) ---
        f_right = ctk.CTkScrollableFrame(self, label_text="🧩 Metadata Editor 🧩") 
        f_right.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        self.cover_label = ctk.CTkLabel(f_right, text="", image=self.persistent_image, width=200, height=200, fg_color="#1a1a1a", corner_radius=10)
        self.cover_label.pack(pady=15)
        
        ctk.CTkButton(f_right, text="🖼️ Change Cover", command=self.browse_cover).pack(pady=5)
        
        ff = ctk.CTkFrame(f_right, fg_color="transparent")
        ff.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(ff, text="🧑‍🎤 Artist:").pack(anchor="w")
        self.entry_artist = ctk.CTkEntry(ff, height=35)
        self.entry_artist.pack(fill="x", pady=(0, 10))
        RightClickMenu(self.entry_artist)

        ctk.CTkLabel(ff, text="📝 Title:").pack(anchor="w")
        self.entry_title = ctk.CTkEntry(ff, height=35)
        self.entry_title.pack(fill="x", pady=(0, 10))
        RightClickMenu(self.entry_title)

        # --- ALBUM & TRACK ROW (Nebeneinander) ---
        row_alb_trk = ctk.CTkFrame(ff, fg_color="transparent")
        row_alb_trk.pack(fill="x", pady=(0, 10))

        # Album (Links, nimmt den meisten Platz)
        alb_frame = ctk.CTkFrame(row_alb_trk, fg_color="transparent")
        alb_frame.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkLabel(alb_frame, text="📀 Album:").pack(anchor="w")
        self.entry_album = ctk.CTkEntry(alb_frame, height=35)
        self.entry_album.pack(fill="x")
        RightClickMenu(self.entry_album)

        # Track Nr (Rechts, klein)
        trk_frame = ctk.CTkFrame(row_alb_trk, fg_color="transparent")
        trk_frame.pack(side="right", fill="x", padx=(5, 0))

        ctk.CTkLabel(trk_frame, text="🔢 Trk:").pack(anchor="w")
        self.entry_track = ctk.CTkEntry(trk_frame, height=35, width=60) # Schmaler
        self.entry_track.pack(fill="x")
        RightClickMenu(self.entry_track)
        
        # --- NEU: Musik-Metadaten ---
# --- NEU: Musik-Metadaten (alles nebeneinander) ---
        meta_row = ctk.CTkFrame(ff, fg_color="transparent")
        meta_row.pack(fill="x", pady=(0, 10))

        # --- BPM ---
        bpm_frame = ctk.CTkFrame(meta_row, fg_color="transparent")
        bpm_frame.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkLabel(bpm_frame, text="⏱️ BPM:").pack(anchor="w")
        self.entry_bpm = ctk.CTkEntry(bpm_frame, height=35)
        self.entry_bpm.pack(fill="x")
        RightClickMenu(self.entry_bpm)

        # --- Key ---
        key_frame = ctk.CTkFrame(meta_row, fg_color="transparent")
        key_frame.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkLabel(key_frame, text="🎹 Key:").pack(anchor="w")
        self.entry_key = ctk.CTkEntry(key_frame, height=35)
        self.entry_key.pack(fill="x")
        RightClickMenu(self.entry_key)

        # --- Camelot ---
        camelot_frame = ctk.CTkFrame(meta_row, fg_color="transparent")
        camelot_frame.pack(side="left", fill="x", expand=True, padx=(5, 0))

        ctk.CTkLabel(camelot_frame, text="🔢 Camelot:").pack(anchor="w")
        self.entry_camelot = ctk.CTkEntry(camelot_frame, height=35)
        self.entry_camelot.pack(fill="x")
        RightClickMenu(self.entry_camelot)

        
        ctk.CTkButton(f_right, text="ℹ️ Meta Details", command=self.show_more_info, fg_color="#555").pack(fill="x", padx=20, pady=(20, 5))
        ctk.CTkButton(f_right, text="💾 Save", command=self.save, fg_color="#E65100", height=40, font=("Arial", 15, "bold")).pack(fill="x", padx=20, pady=20)
        
        self.lbl_status = ctk.CTkLabel(f_right, text="")
        self.lbl_status.pack(pady=10)

    # --- LOGIK ---

    def show_context_menu(self, event):
        # Zeile unter Maus wählen, falls nichts gewählt ist
        idx = self.file_listbox.nearest(event.y)
        if idx >= 0 and idx not in self.file_listbox.curselection():
            self.file_listbox.selection_clear(0, "end")
            self.file_listbox.selection_set(idx)
            self.on_select(None)
        self.list_context_menu.tk_popup(event.x_root, event.y_root)

    def on_select(self, e):
        selection = self.file_listbox.curselection()
        if not selection: return
        
        idx = selection[-1] 
        p = self.editor_files[idx]
        self.current_editor_file = p
        self.current_cover_path = None

        # 1. DATEN LADEN & VORBEREITEN
        t = read_tags_quick(p)
        c_code = t.get('camelot', '').strip().upper()
        mode = ctk.get_appearance_mode()
        # Traktor Code berechnen
        traktor_code = get_open_key(c_code)
        
        # 2. FARBE BERECHNEN (Inklusive Light-Mode Korrektur)
        # Wir holen die Grundfarbe aus deinen Helpers
        c_color = CAMELOT_COLORS.get(c_code, "white")

        if mode == "Light":
            # Falls kein Key da ist oder die Farbe weiß wäre -> auf Weiß nicht lesbar -> Schwarz nutzen
            if c_color == "white" or not c_code:
                c_color = "black"
            # Helle Neon-Farben (Gelb/Limette) für helle Hintergründe abdunkeln
            elif c_color in ["#FFFF00", "#CCFF90", "#DFFF00"]: 
                c_color = "#A15200" # Ein dunkleres Gold/Braun

        # 3. FELDER LEEREN & TEXT EINFÜGEN
        # Wir leeren erst alles, damit keine Reste bleiben
        for entry in [self.entry_artist, self.entry_title, self.entry_album, 
                      self.entry_bpm, self.entry_key, self.entry_camelot, self.entry_track]:
            entry.delete(0, "end")

        self.entry_artist.insert(0, t.get('artist', ''))
        self.entry_title.insert(0, t.get('title', ''))
        self.entry_album.insert(0, t.get('album', ''))
        self.entry_bpm.insert(0, t.get('bpm', ''))
        self.entry_key.insert(0, t.get('key', ''))
        self.entry_camelot.insert(0, t.get('camelot', ''))
        self.entry_track.insert(0, t.get('tracknumber', ''))
        
        # 4. STYLING ANWENDEN (Farbe auf alle Felder übertragen)
        # Jetzt nutzen wir die in Schritt 2 berechnete 'c_color'
        self.entry_artist.configure(text_color=c_color)
        self.entry_title.configure(text_color=c_color)
        self.entry_album.configure(text_color=c_color)
        self.entry_bpm.configure(text_color=c_color)
        self.entry_key.configure(text_color=c_color)
        self.entry_camelot.configure(text_color=c_color)
        self.entry_track.configure(text_color=c_color)

        # 5. COVER & INFO-WINDOW UPDATE
        data = extract_cover_data(p)
        if data:
            try:
                pil_img = Image.open(io.BytesIO(data))
                pil_img = ImageOps.fit(pil_img, (200, 200), method=Image.Resampling.LANCZOS)
                self.persistent_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
            except: 
                self.persistent_image = self.get_default_image()
        else:
            self.persistent_image = self.get_default_image()
            
        self.cover_label.configure(image=self.persistent_image)
        #self.lbl_status.configure(text=os.path.basename(p), text_color="gray")
        # Du könntest es z.B. in das Status-Label schreiben:
        self.lbl_status.configure(text=f"{os.path.basename(p)} | Open Key: {traktor_code}")
        self.update_info_window(p)
    def save(self):
        if not self.current_editor_file: return
        self.lbl_status.configure(text="Saving 💾...", text_color="yellow")
        
        # v3.1 Dispatcher Logik
        args = [sys.executable]
        if not getattr(sys, 'frozen', False):
            main_script = os.path.abspath(sys.modules['__main__'].__file__)
            args.append(main_script)
        
        args.extend([
            "--worker", "analyzer", "--tag", 
            self.current_editor_file, 
            self.entry_artist.get() or " ", 
            self.entry_title.get() or " ", 
            self.entry_album.get() or " ", 
            self.current_cover_path or "NONE",
            self.entry_bpm.get() or "NONE",     # NEU
            self.entry_key.get() or "NONE",     # NEU
            self.entry_camelot.get() or "NONE",  # NEU
            self.entry_track.get() or "0"   # <--- NEU: Track Nummer
        ])
        
        def run():
            subprocess.run(args)
            self.after(0, lambda: self.lbl_status.configure(text="✅ Saved!", text_color="green"))
            self.app.lift()
            self.app.focus_force()
            self.after(0, lambda: self.update_info_window(self.current_editor_file))
            
        threading.Thread(target=run, daemon=True).start()

    def load_files(self):
        source_paths = []
        if hasattr(self.app, 'analyze_tab'):
            ids = self.app.analyze_tab.tree.get_children()
            if ids:
                source_paths = [self.app.analyze_tab.data_map[i]['Pfad'] for i in ids if i in self.app.analyze_tab.data_map]

        if not source_paths:
            f = self.app.path_entry.get()
            if os.path.isdir(f):
                for x in os.listdir(f):
                    if x.lower().endswith(('.mp3','.wav','.flac','.m4a','.aiff','.aif')):
                        source_paths.append(os.path.join(f, x))

        added = 0
        for p in source_paths:
            if p not in self.editor_files:
                self.editor_files.append(p)
                self.file_listbox.insert("end", os.path.basename(p))
                added += 1
        self.lbl_status.configure(text=f"Added {added} files 🔄", text_color="green")
        self.app.lift()
        self.app.focus_force()        

    def remove_from_list(self):
        selection = self.file_listbox.curselection()
        if not selection: return
        
        # DATEN FÜR UNDO SPEICHERN
        deleted_data = []
        for idx in selection:
            deleted_data.append(self.editor_files[idx])
        self.undo_stack.append(deleted_data)
        self.btn_undo.configure(state="normal", fg_color="#5E35B1")

        # Eigentliches Löschen (wie bisher)
        for idx in reversed(selection):
            self.file_listbox.delete(idx)
            del self.editor_files[idx]
        
        self.lbl_status.configure(text=f"Removed {len(deleted_data)} items 🗑️")

    def load_external_files(self, file_paths):
        added = 0
        for path in file_paths:
            if path not in self.editor_files:
                self.editor_files.append(path)
                self.file_listbox.insert("end", os.path.basename(path))
                added += 1
        self.lbl_status.configure(text=f"Imported {added} files ✅", text_color="green")

    def get_default_image(self):
        img = Image.new("RGBA", (200, 200), (40, 40, 40, 255))
        return ctk.CTkImage(light_image=img, dark_image=img, size=(200, 200))

    def browse_cover(self):
        f = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg")])
        self.app.lift()
        self.app.focus_force() # Falls erfolgreich, Fokus zurück
        if f:
            self.current_cover_path = f
            i = Image.open(f)
            i = ImageOps.fit(i, (200, 200), method=Image.Resampling.LANCZOS)
            self.persistent_image = ctk.CTkImage(light_image=i, dark_image=i, size=i.size)
            self.cover_label.configure(image=self.persistent_image)
            self.entry_track.delete(0, "end")

    def show_more_info(self):
        if not self.current_editor_file: return
        if self.info_window is None or not self.info_window.winfo_exists():
            self.info_window, self.info_textbox = show_details_popup(self, self.current_editor_file)
        else:
            self.info_window.lift()
            self.update_info_window(self.current_editor_file)

    def update_info_window(self, path):
        if self.info_window and self.info_textbox and self.info_window.winfo_exists():
            text = get_raw_metadata_string(path)
            self.info_textbox.configure(state="normal")
            self.info_textbox.delete("0.0", "end")
            self.info_textbox.insert("0.0", text)
            self.info_textbox.configure(state="disabled")

    def add_single_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Audio", "*.mp3 *.wav *.flac *.m4a *.aiff *.aif")])
        self.app.lift()
        self.app.focus_force()
        for f in files:
            if f not in self.editor_files:
                self.editor_files.append(f)
                self.file_listbox.insert("end", os.path.basename(f))

    def set_font_size(self, size):
    # 1. Linke Seite (Liste)
        self.file_listbox.configure(font=("Arial", size))
        
        # 2. Rechte Seite (Eingabefelder)
        # Wir nutzen "bold", damit die Farben kräftiger wirken
        f_style = ("Arial", size, "bold")
        
        self.entry_artist.configure(font=f_style)
        self.entry_title.configure(font=f_style)
        self.entry_album.configure(font=f_style)
        self.entry_bpm.configure(font=f_style)
        self.entry_key.configure(font=f_style)
        self.entry_camelot.configure(font=f_style)
    
    def clear_list(self):
        if not self.editor_files: return
    
        # Komplette Liste in den Undo-Stack
        self.undo_stack.append(list(self.editor_files))
        self.btn_undo.configure(state="normal", fg_color="#5E35B1")
        # 1. Listen leeren
        self.file_listbox.delete(0, tk.END)
        self.editor_files = []
        self.current_editor_file = None
        
        # 2. Editor-Felder zurücksetzen
        self.entry_artist.delete(0, "end")
        self.entry_title.delete(0, "end")
        self.entry_album.delete(0, "end")
        self.entry_bpm.delete(0, "end")
        self.entry_key.delete(0, "end")
        self.entry_camelot.delete(0, "end")
                
        # 3. Bild auf Platzhalter zurücksetzen
        self.persistent_image = self.get_default_image()
        self.cover_label.configure(image=self.persistent_image)
        
        # 4. Status-Update
        self.lbl_status.configure(text="List cleared 🗑️", text_color="gray")   
    # Und als neue Methode im EditorTab:
    def update_camelot_color(self):
        code = self.entry_camelot.get().strip().upper()
        color = CAMELOT_COLORS.get(code, "white")
        self.entry_camelot.configure(text_color=color) 
    def undo_action(self):
        if not self.undo_stack: return
        
        # Letzte Löschung holen
        last_deleted = self.undo_stack.pop()
        
        # Wieder hinzufügen (mit Duplikats-Check)
        added = 0
        for path in last_deleted:
            if path not in self.editor_files:
                self.editor_files.append(path)
                self.file_listbox.insert("end", os.path.basename(path))
                added += 1
                
        # Button deaktivieren, wenn Stack leer
        if not self.undo_stack:
            self.btn_undo.configure(state="disabled", fg_color="#5E35B1")
            
        self.lbl_status.configure(text=f"Restored {added} items ↩️")   
        
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

    def send_to_analyzer(self):
        """Sammelt markierte Pfade aus der Listbox und schickt sie an den Analyzer"""
        # 1. Auswahl aus der Listbox holen (gibt Indizes zurück, z.B. (0, 2, 5))
        selection = self.file_listbox.curselection()
        
        if not selection: return

        files_to_send = []
        
        # 2. Die echten Pfade aus der editor_files Liste holen
        for idx in selection:
            try:
                # Wir greifen direkt auf die Liste zu
                path = self.editor_files[idx]
                if path and os.path.exists(path):
                    files_to_send.append(path)
            except IndexError:
                continue

        # 3. Absenden an den Analyzer
        if files_to_send:
            count = len(files_to_send)
            self.app.log_tab.log(f"🚀 Sending {count} files from Editor to Analyzer...")
            # Die Brücke: Wir rufen die Funktion im Analyzer auf
            self.app.analyze_tab.load_external_files(files_to_send) 

    def open_in_finder(self):
        selection = self.file_listbox.curselection()
        if selection:
            idx = selection[0] # Nimm das erste markierte
            if idx < len(self.editor_files):
                path = self.editor_files[idx]
                reveal_in_finder(path)                         