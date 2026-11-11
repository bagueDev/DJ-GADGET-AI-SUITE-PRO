# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import customtkinter as ctk
import logging

# Warnungen landen über den Handler in main.py im Log-Tab
log = logging.getLogger("djgadget")
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import threading
import subprocess
from helpers import get_executable_path, reveal_in_finder

# In den Tabs (Analyze, Stems, etc.)
def get_worker_cmd(worker_type):
    # 1. Start mit der Binary (im Build) oder Python (im Dev)
    cmd = [sys.executable]
    
    # 2. Im Dev-Modus muss der Pfad zur main.py als erstes Argument dazu
    if not getattr(sys, 'frozen', False):
        main_script = os.path.abspath(sys.modules['__main__'].__file__)
        cmd.append(main_script)
    
    # 3. Worker-Flags anhängen
    cmd.extend(["--worker", worker_type])
    return cmd

# Beispiel-Aufruf:
# args = get_worker_cmd("analyzer") + [input_path, output_csv, ...]
# subprocess.Popen(args, ...)

class TranscribeTab(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.app = main_app
        
        # Batch State
        self.selected_files = []
        self.stop_batch = False
        
        # --- UI SETUP ---
        ctk.CTkLabel(self, text="🎙️ Vocal Transcriber (Batch Processing)", font=("Arial", 20, "bold")).pack(pady=10)
        ctk.CTkLabel(self, text="📁➕📁 Choose multiple files, ❌🗑️ Remove unwanted items, ▶️📦📦📦 and start the batch.", text_color="gray").pack(pady=(0, 10))
        
        # 1. DATEI LISTE (Warteschlange)
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="x", padx=20, pady=5)
        # Button hinzufügen
        btn_box = ctk.CTkFrame(list_frame, fg_color="transparent")
        btn_box.pack(pady=5)
        ctk.CTkButton(btn_box, text="📂 Add Files (+)", command=self.browse_add, width=180).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text="🚫 Remove Selected ", command=self.remove_selected, fg_color="#AA0000", width=150).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text="🗑️ Clear all", command=self.clear_list, fg_color="gray", width=100).pack(side="left", padx=5)
        self.undo_stack = []
        self.btn_undo = ctk.CTkButton(
            btn_box, 
            text="↩️ Undo", 
            command=self.undo_action, 
            fg_color="#5E35B1",    # Dein Lila
            hover_color="#7B1FA2", # Ein helleres Lila für den Hover
            state="disabled", 
            width=100
        )
        self.btn_undo.pack(side="left", padx=5)
        
       # 1. Button in die bestehende btn_box packen
        ctk.CTkButton(btn_box, text="🔄 Sync Playlist", command=self.sync_from_playlist, fg_color="#2b5e2b", width=150).pack(side="left", padx=5)
        
        # 2. Kontext-Menü Objekt erstellen (noch unsichtbar)
        self.list_context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#007aff")
        self.list_context_menu.add_command(label="🗑️ Remove from List", command=self.remove_selected)
        self.list_context_menu.add_separator()
        self.list_context_menu.add_command(label="🔄 Sync from Playlist", command=self.sync_from_playlist)
        self.list_context_menu.add_separator()
        self.list_context_menu.add_command(label="🔍 Send to Analyzer", command=self.send_to_analyzer)
        self.list_context_menu.add_command(label="📂 Show in Finder", command=self.open_in_finder)

        # 3. NEU: Container für Liste + Cover erstellen (Kind von list_frame)
        list_container = ctk.CTkFrame(list_frame, fg_color="transparent")
        list_container.pack(fill="both", expand=True, padx=5, pady=5)

        # 3.1. Scrollbar rechts
        sb = ctk.CTkScrollbar(list_container, orientation="vertical")

        # 3.2. Listbox links (mit Link zur Scrollbar)
        self.file_listbox = tk.Listbox(list_container, 
                                       bg="#2b2b2b", 
                                       fg="white", 
                                       selectbackground="#007aff", 
                                       borderwidth=0, 
                                       font=("Arial", 13), 
                                       selectmode="extended",
                                       yscrollcommand=sb.set)
        self.file_listbox.pack(side="left", fill="both", expand=True)

        # 3.3 Scrollbar verknüpfen
        sb.pack(side="left", fill="y", padx=(0, 10)) # Kleiner Abstand zum Cover
        sb.configure(command=self.file_listbox.yview)

        # 5. NEU: Das Cover-Label daneben (Kind von list_container!)
        self.side_cover_label = ctk.CTkLabel(list_container, text="🎵", width=150, height=150, 
                                             fg_color=("#dbdbdb", "#1a1a1a"), corner_radius=8)
        self.side_cover_label.pack(side="right", padx=(10, 0))

        # 6. Alle Bindings für die Listbox
        self.file_listbox.bind("<Button-3>", self.show_context_menu)
        self.file_listbox.bind("<Button-2>", self.show_context_menu)
        self.file_listbox.bind("<Control-Button-1>", self.show_context_menu)
        self.file_listbox.bind('<<ListboxSelect>>', self.update_side_preview) # Für das Cover-Update
        
        # 7. Count Label (wieder direkt in list_frame, unter den Container)
        self.count_label = ctk.CTkLabel(list_frame, text="0 🗂️ Files in the queue", text_color="gray", font=("Arial", 12))
        self.count_label.pack(pady=(0, 5))
        
        # 2. OPTIONEN
        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.pack(pady=10)
        
        ctk.CTkLabel(opts, text="🧠📏 Model Size:").pack(side="left", padx=5)
        self.trans_model_var = ctk.StringVar(value="small")
        self.trans_model_combo = ctk.CTkOptionMenu(opts, variable=self.trans_model_var, values=["tiny", "base", "small", "medium"])
        self.trans_model_combo.pack(side="left", padx=5)
        
        # Refresh & Offline Buttons
        ctk.CTkButton(opts, text="🔄", width=30, command=self.refresh_whisper_models).pack(side="left", padx=2)
        ctk.CTkButton(opts, text="⬇️ Offline Load", width=120, fg_color="gray", command=self.download_whisper_trigger).pack(side="left", padx=20)
        
        # 3. ACTION
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        self.btn_trans_start = ctk.CTkButton(btn_frame, text="📝 RUN", fg_color="#007aff", height=50, font=("Arial", 14, "bold"), command=self.start_batch)
        self.btn_trans_start.pack(side="left", padx=10)
        
        self.btn_stop = ctk.CTkButton(btn_frame, text="⏹ STOP", fg_color="#AA0000", height=50, state="disabled", command=self.stop_processing)
        self.btn_stop.pack(side="left", padx=10)
        
        # Status & Konsole
        self.trans_status = ctk.CTkLabel(self, text="☝️❕: 📤 Exports .txt, .lrc (Karaoke) & .srt (Subtitles) directly to source folder", text_color="gray")
        self.trans_status.pack(pady=5)
        
        self.trans_console = ctk.CTkTextbox(self, height=200, font=("Consolas", 14))
        self.trans_console.pack(fill="both", expand=True, pady=10, padx=20)
                # --- NEU: Rechtsklick-Menü für die Konsole ---
        self.console_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white")
        self.console_menu.add_command(label="📋 Copy", command=self.copy_console_text)
        self.console_menu.add_separator()
        self.console_menu.add_command(label="🗑️ Clear Log", command=lambda: self.trans_console.delete("1.0", "end"))

        # Bindings (Windows/Mac)
        self.trans_console.bind("<Button-3>", self.show_console_menu)
        self.trans_console.bind("<Button-2>", self.show_console_menu)
        self.trans_console.bind("<Control-Button-1>", self.show_context_menu)
        
        self.is_transcribing = False # <--- NEU
        
        # Initialer Check
        self.refresh_whisper_models()

    # --- FILE MANAGEMENT ---
    def browse_add(self):
        files = filedialog.askopenfilenames(filetypes=[("Media", "*.mp3 *.wav *.m4a *.mp4 *.mov *.mkv *.flac *.aiff")])
        self.app.lift()
        self.app.focus_force()
        if files:
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self.update_listbox()

    def remove_selected(self):
        selection = self.file_listbox.curselection()
        if not selection: return
        
        self.undo_stack.append([self.selected_files[i] for i in selection])
        self.btn_undo.configure(state="normal", fg_color="#5E35B1")

        for index in reversed(selection):
            del self.selected_files[index]
        self.update_listbox()

    def clear_list(self):
        if not self.selected_files: return
        self.undo_stack.append(list(self.selected_files))
        self.btn_undo.configure(state="normal", fg_color="#5E35B1")
        self.selected_files = []
        self.update_listbox()

    def undo_action(self):
        if not self.undo_stack: return
        last_deleted = self.undo_stack.pop()
        for p in last_deleted:
            if p not in self.selected_files: self.selected_files.append(p)
        
        if not self.undo_stack: self.btn_undo.configure(state="disabled", fg_color="#5E35B1")
        self.update_listbox()

    def update_listbox(self):
        self.file_listbox.delete(0, tk.END)
        for f in self.selected_files:
            self.file_listbox.insert(tk.END, os.path.basename(f))
        self.count_label.configure(text=f"{len(self.selected_files)} 🗂️ Files in Queue")

    # --- MODEL LOGIC ---
    def get_whisper_offline_dir(self):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
            if "Contents/MacOS" in base: 
                base = os.path.abspath(os.path.join(base, "../../.."))
        else: 
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        p = os.path.join(base, "Whisper_Models")
        if not os.path.exists(p): 
            try: os.makedirs(p)
            except Exception as e: log.warning("Could not create folder %s: %s", p, e)
        return p

    def refresh_whisper_models(self):
        d = self.get_whisper_offline_dir()
        found = []
        if os.path.exists(d):
            found = [f for f in os.listdir(d) if os.path.isdir(os.path.join(d, f))]
        defaults = ["tiny", "base", "small", "medium"]
        all_models = sorted(list(set(defaults + found)))
        self.trans_model_combo.configure(values=all_models)

    def download_whisper_trigger(self):
        model = self.trans_model_combo.get()
        dest = self.get_whisper_offline_dir()
        messagebox.showinfo("Download", f"Load '{model}'...\nwait for log output .")
        self.app.lift()
        self.app.focus_force()
        self.trans_console.delete("1.0", "end")
        self.trans_status.configure(text=f"⬇️ Downloading {model}...", text_color="orange")
        threading.Thread(target=self.run_trans_download, args=(model, dest), daemon=True).start()

    def run_trans_download(self, model, dest):
        args = [sys.executable]
        if not getattr(sys, 'frozen', False):
            args.append(os.path.abspath(sys.modules['__main__'].__file__))
        
        args.extend(["--worker", "transcriber", "--download", model, dest])
        
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in p.stdout:
                if self.app.closing: break
                self.after(0, lambda l=line: self.trans_log(l))
            p.wait()
            self.after(0, lambda: self.trans_done_dl(p.returncode==0))
        except Exception as e: 
            self.after(0, lambda: self.trans_log(str(e)))

    def trans_done_dl(self, success):
        if success: messagebox.showinfo("Info", "Download done ✅ ")
        
        else: messagebox.showerror("Error", "Download failed  ⚠️")
         # --- FOKUS ZURÜCKHOLEN ---
        self.app.after(100, lambda: self.app.lift())
        self.app.after(110, lambda: self.app.focus_force())

    # --- BATCH PROCESSING LOGIC ---
    def stop_processing(self):
        self.stop_batch = True
        self.trans_console.insert("end", "\n!!! ⚠️ Stop batch after current Track ⚠️\n")
        self.trans_console.see("end")

    def start_batch(self):
        if not self.selected_files: return
        
        m = self.trans_model_var.get()
        off_dir = self.get_whisper_offline_dir()
        
        # Check offline model path
        pot_path = os.path.join(off_dir, m)
        final_model = pot_path if os.path.exists(pot_path) else m
        
        self.stop_batch = False
        self.btn_trans_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.trans_console.delete("1.0", "end")
        self.trans_status.configure(text=f"⚙️ Batch has started ({len(self.selected_files)} Files)...", text_color="orange")
        
                # --- NEU: Animation starten ---
        self.is_transcribing = True
        self.animate_transcription()
        # ------------------------------
        
        # Kopie der Liste für den Thread
        files_to_process = list(self.selected_files)
        
        threading.Thread(target=self.run_batch_process, args=(files_to_process, final_model, off_dir), daemon=True).start()

    def run_batch_process(self, files, model, off_dir):
        total = len(files)
        for i, fpath in enumerate(files):
            if self.stop_batch or self.app.closing: break
            
            fname = os.path.basename(fpath)
            out_dir = os.path.dirname(fpath)
            self.after(0, lambda idx=i, n=fname: self.update_ui_progress(idx, total, n))
            
            # v3.1 Dispatcher Logik
            args = [sys.executable]
            if not getattr(sys, 'frozen', False):
                args.append(os.path.abspath(sys.modules['__main__'].__file__))
            
            # WICHTIG: Hier stand bei dir "--worker analyzer" -> korrigiert zu "transcriber"
            args.extend(["--worker", "transcriber", fpath, out_dir, model, off_dir or "NONE"])
            
            try:
                p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in p.stdout:
                    if self.app.closing: p.terminate(); break
                    self.after(0, lambda l=line: self.trans_log(l))
                p.wait()
                # >>> HIER IST DER NEUE AUTOMATISMUS <<<
                # Sobald der Worker fertig ist, erstellen wir sofort die SRT
                self.convert_lrc_to_srt_auto(fpath)
                # --------------------------------------
            except Exception as e: 
                self.after(0, lambda: self.trans_log(str(e)))

        self.after(0, self.batch_done)
    
    def animate_transcription(self, step=0):
        if not self.is_transcribing: return
        
        chars = ["◐", "◓", "◑", "◒"]

        char = chars[step % len(chars)]
        
        # Aktuellen Text beibehalten, nur das Symbol am Ende ändern
        current_text = self.trans_status.cget("text").split("  ")[0]
        self.trans_status.configure(text=f"{current_text}  {char}")
        
        self.after(500, lambda: self.animate_transcription(step + 1))    

    def update_ui_progress(self, current, total, name):
        msg = f"\n--------------------------------------------------\nTranscribing [{current+1}/{total}]: {name}\n--------------------------------------------------\n"
        self.trans_console.insert("end", msg)
        self.trans_console.see("end")

    def trans_log(self, txt):
        # 1. Prüfen: Ist der User gerade ganz unten?
        is_at_bottom = self.trans_console.yview()[1] > 0.99
        
        self.trans_console.insert("end", txt)
        
        # 2. Nur scrollen, wenn der User vorher unten war
        if is_at_bottom:
            self.trans_console.see("end")

    def batch_done(self):
                # --- NEU: Animation stoppen ---
        self.is_transcribing = False
        # -
        self.btn_trans_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.trans_status.configure(text="Batch done ✅", text_color="green")
                # 2. Timer: Nach 5 Sekunden Reset auf Standard-Text (inkl. .srt Hinweis)
        default_msg = "☝️❕: 📤 Exports .txt, .lrc (Karaoke) & .srt (Subtitles) directly to source folder"
        self.after(5000, lambda: self.trans_status.configure(text=default_msg, text_color="gray"))

        if not self.stop_batch:
            messagebox.showinfo("Done", "All files have been processed 📁✔️")
            self.app.lift()
            self.app.focus_force()

    def set_font_size(self, size):
        self.trans_console.configure(font=("Consolas", size))
        self.file_listbox.configure(font=("Arial", size))
    def sync_from_playlist(self):
        if hasattr(self.app, 'analyze_tab'):
            ids = self.app.analyze_tab.tree.get_children()
            if not ids:
                messagebox.showinfo("Info", "Analyzer list is empty 🚫")
                self.app.lift()
                self.app.focus_force()
                return
            
            added = 0
            for i in ids:
                path = self.app.analyze_tab.data_map[i]['Pfad']
                if path not in self.selected_files:
                    self.selected_files.append(path)
                    added += 1
            
            self.update_listbox()
            self.trans_console.insert("end", f"✅ Imported {added} files from Analyzer.\n")
            
    def load_external_files(self, file_paths):
        added = 0
        for p in file_paths:
            if p not in self.selected_files:
                self.selected_files.append(p)
                added += 1
        self.update_listbox()
        self.trans_console.insert("end", f"📥 Received {added} files from Analyzer.\n") 
        
    def show_context_menu(self, event):
        idx = self.file_listbox.nearest(event.y)
        if idx >= 0:
            # Falls das Item unter der Maus noch nicht selektiert ist, selektiere es
            if idx not in self.file_listbox.curselection():
                self.file_listbox.selection_clear(0, "end")
                self.file_listbox.selection_set(idx)
        self.list_context_menu.tk_popup(event.x_root, event.y_root)  
        
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
    def update_side_preview(self, event=None):
        selection = self.file_listbox.curselection()
        if not selection: return
        
        # Pfad aus der Liste holen
        fpath = self.selected_files[selection[-1]]
        
        from helpers import extract_cover_data
        from PIL import Image
        import io
        
        data = extract_cover_data(fpath)
        if data:
            try:
                img = Image.open(io.BytesIO(data))
                img.thumbnail((140, 140))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(140, 140))
                self.side_cover_label.configure(image=ctk_img, text="")
            except:
                self.side_cover_label.configure(image="", text="🎵")
        else:
            self.side_cover_label.configure(image="", text="🎵")  
            
    def send_to_analyzer(self):
        """Sammelt markierte Pfade aus der Listbox und schickt sie an den Analyzer"""
        selection = self.file_listbox.curselection()
        if not selection: return

        files_to_send = []
        
        for idx in selection:
            try:
                path = self.selected_files[idx]
                if path and os.path.exists(path):
                    files_to_send.append(path)
            except IndexError:
                continue

        if files_to_send:
            # --- NEU: Log-Eintrag ---
            count = len(files_to_send)
            self.app.log_tab.log(f"🚀 Sending {count} files from Transcriper to Analyzer...")
            # ------------------------
            
            self.app.analyze_tab.load_external_files(files_to_send)                
                
    def lrc_to_srt_timestamp(self, lrc_time):
        """Wandelt 'MM:SS.xx' (LRC) in 'HH:MM:SS,ms' (SRT) um."""
        try:
            # LRC Format ist meistens MM:SS.xx (z.B. 03:12.50)
            parts = lrc_time.split(':')
            minutes = int(parts[0])
            
            sec_parts = parts[1].split('.')
            seconds = int(sec_parts[0])
            milliseconds = int(sec_parts[1]) * 10 # LRC hat oft nur 2 Stellen (10ms), SRT braucht 3
            
            hours = minutes // 60
            minutes = minutes % 60
            
            return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"
        except Exception as e:
            log.warning("Unreadable LRC timestamp %r, using 00:00:00 in the SRT: %s", lrc_time, e)
            return "00:00:00,000"       
                    
    def convert_lrc_to_srt_auto(self, media_path):
        """Hintergrund-Prozess: Wandelt die frische LRC sofort in SRT um."""
        try:
            base_path = os.path.splitext(media_path)[0]
            lrc_path = base_path + ".lrc"
            srt_path = base_path + ".srt"
            
            if not os.path.exists(lrc_path):
                return # Keine LRC da, also können wir nichts tun

            # 1. Lesen
            with open(lrc_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 2. Schreiben
            with open(srt_path, "w", encoding="utf-8") as srt:
                counter = 1
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line.startswith("["): continue
                    
                    parts = line.split("]", 1)
                    if len(parts) < 2: continue
                    
                    time_raw = parts[0].replace("[", "")
                    text = parts[1].strip()
                    
                    start_srt = self.lrc_to_srt_timestamp(time_raw)
                    
                    # Endzeit berechnen (Start der nächsten Zeile)
                    end_srt = ""
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        if next_line.startswith("["):
                            next_raw = next_line.split("]", 1)[0].replace("[", "")
                            end_srt = self.lrc_to_srt_timestamp(next_raw)
                    
                    # Fallback für letzte Zeile (+3 Sek)
                    if not end_srt:
                        end_srt = start_srt.replace(",000", ",999") 

                    srt.write(f"{counter}\n{start_srt} --> {end_srt}\n{text}\n\n")
                    counter += 1
                    
        except Exception as e:
            print(f"Auto-SRT Error: {e}")  
            
    def show_console_menu(self, event):
        """Zeigt das Menü an der Maus-Position"""
        try:
            self.console_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.console_menu.grab_release()

    def copy_console_text(self):
        """Smart Copy: Kopiert Auswahl ODER alles, wenn nichts markiert ist."""
        try:
            # 1. Versuch: Markierten Text holen
            text = self.trans_console.get("sel.first", "sel.last")
        except:
            # 2. Fallback: Nichts markiert? Dann alles holen!
            text = self.trans_console.get("1.0", "end")

        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update() # Damit es sicher im Zwischenspeicher landet 
            
    def open_in_finder(self):
        selection = self.file_listbox.curselection()
        if selection:
            idx = selection[0] # Nimm das erste markierte
            if idx < len(self.selected_files):
                path = self.selected_files[idx]
                reveal_in_finder(path)        