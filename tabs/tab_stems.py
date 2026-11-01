# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import threading
import subprocess
from helpers import get_executable_path,reveal_in_finder

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

class StemsTab(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.app = main_app
        self.selected_files = []
        self.stop_batch = False
        
        # --- UI LAYOUT ---
        
        # Titel
        ctk.CTkLabel(self, text="🎶✂️ Music Separation (Batch Processing)", font=("Arial", 20, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(self, text="📁➕📁 Choose multiple files, ❌🗑️ Remove unwanted items, ▶️📦📦📦 and start the batch.", text_color="gray").pack(pady=(0, 10))
        
# --- SECTION 1: DATEI AUSWAHL & LISTE ---
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=20, pady=5)
        
        # Buttons für Auswahl
        btn_box = ctk.CTkFrame(top_frame, fg_color="transparent")
        btn_box.pack(pady=5)
        ctk.CTkButton(btn_box, text="📂 Add Files (+)", command=self.browse_add, width=180).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text="🚫 Remove Selected ", command=self.remove_selected, fg_color="#AA0000", width=150).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text="🗑️ Clear all ", command=self.clear_list, fg_color="gray", width=100).pack(side="left", padx=5)
        
        self.undo_stack = []
        self.btn_undo = ctk.CTkButton(
            btn_box, text="↩️ Undo", command=self.undo_action, 
            fg_color="#5E35B1", hover_color="#7B1FA2", 
            state="disabled", width=100
        )
        self.btn_undo.pack(side="left", padx=5)
        
        ctk.CTkButton(btn_box, text="🔄 Sync Playlist", command=self.sync_from_playlist, fg_color="#2b5e2b", width=150).pack(side="left", padx=5)
        
        # Kontext-Menü erstellen
        self.list_context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#007aff")
        self.list_context_menu.add_command(label="🗑️ Remove from List", command=self.remove_selected)
        self.list_context_menu.add_separator()
        self.list_context_menu.add_command(label="🔄 Sync from Playlist", command=self.sync_from_playlist)
        self.list_context_menu.add_separator()
        self.list_context_menu.add_command(label="🔍 Send to Analyzer", command=self.send_to_analyzer)
        self.list_context_menu.add_command(label="📂 Show in Finder", command=self.open_in_finder)     

        # --- NEU: Container für Liste + Cover (Kind von top_frame) ---
        list_container = ctk.CTkFrame(top_frame, fg_color="transparent")
        list_container.pack(fill="both", expand=True, padx=10, pady=5)

        # 1. Scrollbar erstellen (noch nicht packen)
        sb = ctk.CTkScrollbar(list_container, orientation="vertical")

        # 2. Die Liste (WICHTIG: yscrollcommand hinzufügen)
        self.file_listbox = tk.Listbox(
            list_container, 
            bg="#2b2b2b", fg="white", 
            selectbackground="#1f538d", 
            selectmode="extended", 
            borderwidth=0, highlightthickness=0, 
            font=("Arial", 13), height=12,
            yscrollcommand=sb.set  # <--- Verknüpfung zur Scrollbar
        )
        self.file_listbox.pack(side="left", fill="both", expand=True)

        # 3. Scrollbar packen (WICHTIG: side="left")
        # Wir packen sie LINKS, damit sie direkt an der Liste klebt.
        sb.pack(side="left", fill="y", padx=(0, 10)) # Kleiner Abstand zum Cover
        
        # Scrollbar Befehl setzen
        sb.configure(command=self.file_listbox.yview)

        # 4. Das Cover-Label (ganz rechts)
        self.side_cover_label = ctk.CTkLabel(
            list_container, text="🎵", width=150, height=150, 
            fg_color=("#dbdbdb", "#1a1a1a"), corner_radius=8
        )
        # Cover bleibt rechts
        self.side_cover_label.pack(side="right", padx=(0, 0))

        # Bindings
        self.file_listbox.bind("<Button-3>", self.show_context_menu)
        self.file_listbox.bind("<Button-2>", self.show_context_menu)
        self.file_listbox.bind("<Control-Button-1>", self.show_context_menu)
        self.file_listbox.bind('<<ListboxSelect>>', self.update_side_preview) # <--- WICHTIG für Cover-Update        
        # Info Label (Anzahl)
        self.count_label = ctk.CTkLabel(top_frame, text="0 📂 Files in queue", text_color="gray", font=("Arial", 12))
        self.count_label.pack(pady=(0, 5))

        # --- SECTION 2: OPTIONEN ---
        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.pack(pady=5)
        
        ctk.CTkLabel(opts, text="🪄 Demucs").pack(side="left", padx=5)
        self.model_var = ctk.StringVar(value="htdemucs")
        ctk.CTkOptionMenu(opts, variable=self.model_var, values=["htdemucs", "htdemucs_ft", "htdemucs_6s", "mdx", "mdx_extra", "mdx_extra_q"]).pack(side="left", padx=5)
        ctk.CTkLabel(opts, text="⚙️ Backend").pack(side="left", padx=(10, 5))
        self.backend_var = ctk.StringVar(value="Auto")
        ctk.CTkOptionMenu(opts, variable=self.backend_var, values=["Auto", "MLX (ARM, schnell)", "Torch"]).pack(side="left", padx=5)
        ctk.CTkLabel(opts, text="🎚️ no_*").pack(side="left", padx=(10, 5))
        self.other_method_var = ctk.StringVar(value="add")
        ctk.CTkOptionMenu(opts, variable=self.other_method_var, values=["add", "minus", "none"]).pack(side="left", padx=5)
        ctk.CTkButton(opts, text="⬇️ Offline Load", width=120, fg_color="gray", command=self.dl_trigger).pack(side="left", padx=20)
       # NEU: Instrumental Mode Checkbox
        self.v_inst_mode = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opts, text="⚡ Instrumental Mode (Fast)", variable=self.v_inst_mode, text_color="#00AA00").pack(side="left", padx=10)
        
        # Checkboxen
        sf = ctk.CTkFrame(self); sf.pack(pady=5, padx=20, fill="x")
        self.v_voc = ctk.BooleanVar(value=True); ctk.CTkCheckBox(sf, text="🎤 Vocals", variable=self.v_voc).pack(side="left", padx=10)
        self.v_drum = ctk.BooleanVar(value=True); ctk.CTkCheckBox(sf, text="🥁 Drums", variable=self.v_drum).pack(side="left", padx=10)
        self.v_bass = ctk.BooleanVar(value=True); ctk.CTkCheckBox(sf, text="🎸 Bass", variable=self.v_bass).pack(side="left", padx=10)
        self.v_other = ctk.BooleanVar(value=True); ctk.CTkCheckBox(sf, text="🎛️ Other", variable=self.v_other).pack(side="left", padx=10)
                # NEU:
        self.v_piano = ctk.BooleanVar(value=False); ctk.CTkCheckBox(sf, text="🎹 Piano", variable=self.v_piano).pack(side="left", padx=10)
        self.v_guitar = ctk.BooleanVar(value=False); ctk.CTkCheckBox(sf, text="🎸 Guitar", variable=self.v_guitar).pack(side="left", padx=10)
        
        # --- SECTION 3: ACTION ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        self.btn_start = ctk.CTkButton(btn_frame, text="✂️ RUN ", fg_color="#007aff", height=50, font=("Arial", 14, "bold"), command=self.start)
        self.btn_start.pack(side="left", padx=10)
        self.btn_stop = ctk.CTkButton(btn_frame, text="⏹ STOP", fg_color="#AA0000", height=50, state="disabled", command=self.stop_processing)
        self.btn_stop.pack(side="left", padx=10)
        
        # Konsole
        self.console = ctk.CTkTextbox(self, height=150, font=("Consolas", 11))
        self.console.pack(fill="both", expand=True, pady=10, padx=20)

    # --- LOGIC: FILE MANAGEMENT ---
    def browse_add(self):
        # Mehrere Dateien hinzufügen (nicht überschreiben)
        files = filedialog.askopenfilenames(filetypes=[("Audio", "*.mp3 *.wav *.flac *.aiff *.aif *.AIFF *.AIF")])
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
        
        # Undo-Speicher
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
            # Zeige nur Dateinamen an, nicht den ganzen Pfad (übersichtlicher)
            self.file_listbox.insert(tk.END, os.path.basename(f))
        
        count = len(self.selected_files)
        self.count_label.configure(text=f"{count} 📂 Files in queue")

    # --- LOGIC: PROCESSING ---
    def get_off_dir(self):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
            if "Contents/MacOS" in base: base = os.path.abspath(os.path.join(base, "../../.."))
        else: base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p = os.path.join(base, "Offline_Models")
        if not os.path.exists(p): 
            try: os.makedirs(p)
            except: pass
        return p

    def dl_trigger(self):
        # Lädt den Modell-Cache vorab in den Hintergrund (MLX fp32 bevorzugt,
        # Torch-Modelle werden beim ersten Run von Demucs selbst geladen).
        model = self.model_var.get()
        off = self.get_off_dir()
        self.console.insert("end", f"⬇️ Lade Modell-Cache für {model} ...\n")
        self.console.see("end")

        def _dl():
            try:
                import platform
                use_mlx = platform.machine() == 'arm64'
                try:
                    import demucs_mlx  # noqa: F401
                except Exception:
                    use_mlx = False
                if use_mlx:
                    from demucs_mlx import Separator
                    import os as _os
                    repo = _os.path.join(off, "demucs-mlx")
                    _os.makedirs(repo, exist_ok=True)
                    Separator(model=model, repo=repo)
                    self.after(0, lambda: self.console.insert("end", f"✅ MLX-Cache bereit: {repo}\n"))
                else:
                    self.after(0, lambda: self.console.insert("end", "ℹ️ Torch-Modus: Modelle werden beim ersten Run geladen.\n"))
            except Exception as e:
                self.after(0, lambda err=e: self.console.insert("end", f"❌ Cache-Download fehlgeschlagen: {err}\n"))
            self.after(0, lambda: self.console.see("end"))
            self.app.after(100, lambda: self.app.lift())
            self.app.after(110, lambda: self.app.focus_force())

        threading.Thread(target=_dl, daemon=True).start()
        
    def stop_processing(self):
        self.stop_batch = True
        self.console.insert("end", "\n!!! ❌Stop batch after current track !!!\n")
        self.console.see("end")

    def start(self):
        if not self.selected_files:
            messagebox.showwarning("!", "⭕Queue is empty!")
            self.app.lift()
            self.app.focus_force()
            return
            
        keep = []
        if self.v_voc.get(): keep.append("vocals")
        if self.v_drum.get(): keep.append("drums")
        if self.v_bass.get(): keep.append("bass")
        if self.v_other.get(): keep.append("other")
                # NEU:
        if self.v_piano.get(): keep.append("piano")
        if self.v_guitar.get(): keep.append("guitar")
        if not keep: 
            messagebox.showwarning("!", "👉 Please select at least 1 stem!")
            self.app.lift()
            self.app.focus_force()
            return
        
        self.stop_batch = False
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.insert("end", f"🟢 Run batch with {len(self.selected_files)} Files...\n")
        
        off = self.get_off_dir()
        model = self.model_var.get()
        stems_str = ",".join(keep)
     
        # Kopie der Liste übergeben, damit Änderungen während des Laufs nicht crashen
        files_to_process = list(self.selected_files)
        
         # NEU: Flag auslesen ("True" oder "False" als String für das Skript)
        is_two_stems = "True" if self.v_inst_mode.get() else "False"

        # NEU: Backend + other-method auslesen (Worker-Positionen 7+8, abwärtskompatibel)
        _b = self.backend_var.get()
        backend = "mlx" if _b.startswith("MLX") else ("torch" if _b == "Torch" else "auto")
        other_method = self.other_method_var.get()
        if other_method not in ("add", "minus", "none"):
            other_method = "add"

        # NEU: is_two_stems als letztes Argument übergeben
        threading.Thread(target=self.run_batch, args=(files_to_process, model, stems_str, off, is_two_stems, backend, other_method), daemon=True).start()

    def run_batch(self, files, model, stems, off, two_stems, backend="auto", other_method="add"):
        total = len(files)
        for i, fpath in enumerate(files):
            if self.stop_batch or self.app.closing: break
            
            fname = os.path.basename(fpath)
            out = os.path.join(os.path.dirname(fpath), "Stems")
            if not os.path.exists(out): os.makedirs(out)
            
            self.after(0, lambda idx=i, n=fname: self.update_ui_progress(idx, total, n))
            
            # v3.1 Dispatcher Logik
            args = [sys.executable]
            if not getattr(sys, 'frozen', False):
                # Im Dev-Mode: Pfad zur main.py hinzufügen
                args.append(os.path.abspath(sys.modules['__main__'].__file__))
            
            # Korrekter Worker-Aufruf
            args.extend([
                "--worker", "separator",
                fpath,
                out,
                model,
                stems,
                off or "NONE",
                two_stems,
                backend,
                other_method
            ])
            
            try:
                p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in p.stdout:
                    if self.app.closing: p.terminate(); break
                    self.after(0, lambda l=line: self.smart_log(l))
                p.wait()
            except Exception as e:
                self.after(0, lambda err=e: self.smart_log(f"Error: {err}\n"))

        self.after(0, self.batch_done)
        
    def update_ui_progress(self, current, total, name):
        msg = f"\n>>> Processing [{current+1}/{total}]: {name} <<<\n"
        self.console.insert("end", msg)
        self.console.see("end")

    def batch_done(self):
        self.btn_start.configure(state="normal", text="✂️ Run batch")
        self.btn_stop.configure(state="disabled")
        if not self.stop_batch:
            messagebox.showinfo("✅ Done", "Batch📦 processing completed ✅")
            self.app.lift()
            self.app.focus_force()
    def smart_log(self, text):
        """Fügt Text hinzu, scrollt aber nur mit, wenn man schon unten ist."""
        # 1. Prüfen: Ist der User gerade ganz unten? (1.0 = 100%)
        # Wir nehmen > 0.99 als Toleranz
        is_at_bottom = self.console.yview()[1] > 0.99
        
        self.console.insert("end", text)
        
        # 2. Nur scrollen, wenn der User vorher unten war
        if is_at_bottom:
            self.console.see("end")        

    def set_font_size(self, size):
        self.console.configure(font=("Consolas", size))
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
            self.console.insert("end", f"✅ Imported {added} files from Analyzer.\n") 
    def load_external_files(self, file_paths):
        added = 0
        for p in file_paths:
            if p not in self.selected_files:
                self.selected_files.append(p)
                added += 1
        self.update_listbox()
        self.console.insert("end", f"📥 Received {added} files from Analyzer.\n")   
        
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
            self.app.log_tab.log(f"🚀 Sending {count} files from Stems AI to Analyzer...")
            # ------------------------
            
            self.app.analyze_tab.load_external_files(files_to_send)
            
    def open_in_finder(self):
        selection = self.file_listbox.curselection()
        if selection:
            idx = selection[0] # Nimm das erste markierte
            if idx < len(self.selected_files):
                path = self.selected_files[idx]
                reveal_in_finder(path)                                     