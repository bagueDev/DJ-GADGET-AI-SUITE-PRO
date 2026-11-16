# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import customtkinter as ctk
import logging

# Warnungen landen über den Handler in main.py im Log-Tab
log = logging.getLogger("djgadget")
from tkinter import filedialog, messagebox
import os
import sys
import threading
import subprocess
import json
import time
import webbrowser
# WICHTIG: RightClickMenu hier importieren
from helpers import (get_executable_path, export_chat_html, RightClickMenu, get_llama_server_override,
                     set_llama_server_override, clear_llama_server_override,
                     get_chat_extra_flags, set_chat_extra_flags,
                     get_chat_mcp_proxy, set_chat_mcp_proxy)

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

class ChatTab(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.app = main_app
        self.chat_process = None
        self.chat_history = []
        self.is_thinking = False
        self.is_loading_model = False
        self.webui_port = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1) 
        
        # Row 0: Model Ordner & History
        row0 = ctk.CTkFrame(self, fg_color="transparent")
        row0.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(row0, text="🧠📁  Model Folder:").pack(side="left", padx=5)
        self.chat_model_dir_entry = ctk.CTkEntry(row0)
        self.chat_model_dir_entry.insert(0, self.get_default_models_dir())
        self.chat_model_dir_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # RECHTSKLICK AKTIVIEREN
        RightClickMenu(self.chat_model_dir_entry)

        ctk.CTkButton(row0, text="📂", width=40, command=self.browse_model_dir).pack(side="left", padx=2)
        
        # History Controls
        ctk.CTkButton(row0, text="💾 Save", width=60, fg_color="#E65100", command=self.save_history_json).pack(side="right", padx=5)
        self.history_combo = ctk.CTkOptionMenu(row0, width=130, command=self.load_history_json)
        self.history_combo.set("📜 History...")
        self.history_combo.pack(side="right", padx=5)

        # Row 0b: llama-server Binary Override (optional)
        srv_box = ctk.CTkFrame(self, fg_color="transparent")
        srv_box.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 0))
        row_srv = ctk.CTkFrame(srv_box, fg_color="transparent")
        row_srv.pack(fill="x")
        ctk.CTkLabel(row_srv, text="🔧 Server-Binary (optional):").pack(side="left", padx=5)
        self.chat_server_entry = ctk.CTkEntry(row_srv)
        self.chat_server_entry.pack(side="left", fill="x", expand=True, padx=5)
        RightClickMenu(self.chat_server_entry)
        ctk.CTkButton(row_srv, text="📂", width=30, command=self.browse_server_binary).pack(side="left", padx=2)
        ctk.CTkButton(row_srv, text="🗑️", width=30, command=self.clear_server_binary, fg_color="gray").pack(side="left", padx=2)
        self.lbl_server_status = ctk.CTkLabel(row_srv, text="", text_color="gray", width=200)
        self.lbl_server_status.pack(side="left", padx=5)

        # Row 0c: zusätzliche llama-server-Flags (optional, für Fortgeschrittene)
        row_flags = ctk.CTkFrame(srv_box, fg_color="transparent")
        row_flags.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(row_flags, text="⚙️ Extra server flags (optional):").pack(side="left", padx=5)
        self.chat_flags_entry = ctk.CTkEntry(row_flags, placeholder_text="e.g. --cache-type-k q8_0 --cache-type-v q8_0   (applied on 🚀 Start)")
        self.chat_flags_entry.pack(side="left", fill="x", expand=True, padx=5)
        RightClickMenu(self.chat_flags_entry)
        # MCP-Proxy des llama-servers: nur auf Wunsch (Standard aus), gilt ab dem nächsten 🚀 Start
        self.chat_mcp_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row_flags, text="🔌 MCP proxy (Web UI)", variable=self.chat_mcp_var,
                        width=20).pack(side="left", padx=5)

        # Row 1: Model
        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 0))

        ctk.CTkLabel(row1, text="🧠 GGUF:").pack(side="left", padx=5)
        self.chat_model_combo = ctk.CTkOptionMenu(row1, width=200)
        self.chat_model_combo.pack(side="left", padx=5)
        ctk.CTkButton(row1, text="🔄", width=30, command=self.refresh_chat_models).pack(side="left", padx=2)

        # Row 1a: Sampling-Regler, erste Reihe (3 Stück)
        row1a = ctk.CTkFrame(self, fg_color="transparent")
        row1a.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 0))

        # Sliders mit Werten
        ctk.CTkLabel(row1a, text="🌡️ Temp:").pack(side="left", padx=(15, 2))
        self.lbl_temp = ctk.CTkLabel(row1a, text="0.70", text_color="#00AA00", width=30); self.lbl_temp.pack(side="left")
        self.chat_temp_slider = ctk.CTkSlider(row1a, from_=0.1, to=2.0, width=80, command=lambda v: self.lbl_temp.configure(text=f"{v:.2f}")); self.chat_temp_slider.set(0.7); self.chat_temp_slider.pack(side="left", padx=2)

        ctk.CTkLabel(row1a, text="🔢 MaxT:").pack(side="left", padx=(10, 2))
        self.lbl_tok = ctk.CTkLabel(row1a, text="4096", text_color="#00AA00", width=50); self.lbl_tok.pack(side="left")
        self.chat_tokens_slider = ctk.CTkSlider(row1a, from_=512, to=32768, width=96, number_of_steps=63, command=lambda v: self.lbl_tok.configure(text=f"{int(v)}")); self.chat_tokens_slider.set(4096); self.chat_tokens_slider.pack(side="left", padx=2)

        # Repetition Penalty
        ctk.CTkLabel(row1a, text="🚫🔁 Rep:").pack(side="left", padx=(10, 2))
        self.lbl_rep = ctk.CTkLabel(row1a, text="1.10", text_color="#00AA00", width=30); self.lbl_rep.pack(side="left")
        self.chat_rep_slider = ctk.CTkSlider(row1a, from_=1.0, to=1.5, width=80, command=lambda v: self.lbl_rep.configure(text=f"{v:.2f}")); self.chat_rep_slider.set(1.1); self.chat_rep_slider.pack(side="left", padx=2)

        # Row 1b: Sampling-Regler, zweite Reihe (3 Stück)
        row1b = ctk.CTkFrame(self, fg_color="transparent")
        row1b.grid(row=4, column=0, sticky="ew", padx=10, pady=(2, 5))

        # Nucleus Sampling (Top-P)
        ctk.CTkLabel(row1b, text="🎯 TopP:").pack(side="left", padx=(15, 2))
        self.lbl_topp = ctk.CTkLabel(row1b, text="0.95", text_color="#00AA00", width=30); self.lbl_topp.pack(side="left")
        self.chat_topp_slider = ctk.CTkSlider(row1b, from_=0.1, to=1.0, width=80, command=lambda v: self.lbl_topp.configure(text=f"{v:.2f}")); self.chat_topp_slider.set(0.95); self.chat_topp_slider.pack(side="left", padx=2)

        # Top-K Sampling
        ctk.CTkLabel(row1b, text="🔝 TopK:").pack(side="left", padx=(10, 2))
        self.lbl_topk = ctk.CTkLabel(row1b, text="40", text_color="#00AA00", width=30); self.lbl_topk.pack(side="left")
        self.chat_topk_slider = ctk.CTkSlider(row1b, from_=1, to=100, width=80, number_of_steps=99, command=lambda v: self.lbl_topk.configure(text=f"{int(v)}")); self.chat_topk_slider.set(40); self.chat_topk_slider.pack(side="left", padx=2)
        # --- Context Size Slider (in zweiter Regler-Reihe) ---

        ctk.CTkLabel(row1b, text="🧠 Ctx:").pack(side="left", padx=(10, 2))

        self.lbl_n_ctx = ctk.CTkLabel(row1b, text="4096", text_color="#00AA00", width=50)
        self.lbl_n_ctx.pack(side="left")

        # Erst Verdopplungen bis 16k, dann 8k-Schritte bis 128k, dann bis 256k
        self.ctx_values = [512, 1024, 2048, 4096, 8192, 16384] + list(range(24576, 131073, 8192)) + [256000]

        self.slider_n_ctx = ctk.CTkSlider(
            row1b, 
            from_=0, 
            to=len(self.ctx_values) - 1, 
            number_of_steps=len(self.ctx_values) - 1,
            width=120,
            command=self.update_ctx_label
        )
        self.slider_n_ctx.set(20) # Startet bei 256000 Context

        self.slider_n_ctx = ctk.CTkSlider(
            row1b, 
            from_=0, 
            to=len(self.ctx_values) - 1, 
            number_of_steps=len(self.ctx_values) - 1,
            width=120,
            command=self.update_ctx_label # Diese Funktion erstellen wir gleich
        )
        self.slider_n_ctx.set(3) 
        self.slider_n_ctx.pack(side="left", padx=2)

        # Row 2: System Prompt & Start
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.grid(row=5, column=0, sticky="ew", padx=10, pady=0)
        ctk.CTkLabel(row2, text="🖥️  System:").pack(side="left", padx=(15, 5))
        self.chat_sys_prompt = ctk.CTkEntry(row2)
        self.chat_sys_prompt.insert(0, "You are a helpful assistant for musicians..")
        self.chat_sys_prompt.pack(side="left", fill="x", expand=True, padx=5)
        
        # RECHTSKLICK AKTIVIEREN
        RightClickMenu(self.chat_sys_prompt)
        
        self.btn_load_chat = ctk.CTkButton(row2, text="🚀 Start", width=80, command=self.start_chat_engine, fg_color="#007aff"); self.btn_load_chat.pack(side="left", padx=10)
        self.btn_stop_chat = ctk.CTkButton(row2, text="⏹ STOP", width=80, command=self.stop_chat_engine, fg_color="#AA0000", state="disabled"); self.btn_stop_chat.pack(side="left", padx=2)
        
        # Clear Context Button
        self.btn_clear = ctk.CTkButton(row2, text="🗑️ Clear Context", width=40, command=self.clear_context, fg_color="gray", state="disabled")
        self.btn_clear.pack(side="left", padx=2)

        # Row 3: Display
        self.chat_display = ctk.CTkTextbox(
            self, 
            fg_color=("#DFDFDF", "#1a1a1a"), # (Hellgrau für Light, Dunkel für Dark)
            text_color=("#000000", "#FFFFFF"), # (Schwarz für Light, Weiß für Dark)
            font=("Arial", 14)
        )        
        self.chat_display.grid(row=6, column=0, sticky="nsew", padx=10, pady=5)
        
        # RECHTSKLICK AKTIVIEREN
        RightClickMenu(self.chat_display)
        
        # Row 4: Input & Stats
        row4 = ctk.CTkFrame(self)
        row4.grid(row=7, column=0, sticky="ew", padx=10, pady=10)
        
        # NEU: Textbox statt Entry (Höhe 50 für ca. 2-3 Zeilen)
        self.chat_input = ctk.CTkTextbox(row4, height=70, font=("Arial", 14))
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # NEU: Smart Enter Logik
        self.chat_input.bind("<Return>", self.on_enter_pressed)
        
        # Rechtsklick Menü wieder anhängen
        RightClickMenu(self.chat_input)
        
        ctk.CTkButton(row4, text="💬 Send", width=100, command=self.send_chat_message).pack(side="right")
        # Bricht nur die laufende Antwort ab – das Modell bleibt geladen (anders als ⏹ STOP)
        self.btn_cancel_reply = ctk.CTkButton(row4, text="✋ Stop reply", width=100, command=self.cancel_reply,
                                              fg_color="gray", state="disabled")
        self.btn_cancel_reply.pack(side="right", padx=5)
        ctk.CTkButton(row4, text="📄🌐HTML Export", width=100, command=self.export_chat, fg_color="green").pack(side="right", padx=5)
        self.btn_webui = ctk.CTkButton(row4, text="🌐 Web UI", width=100, command=self.open_web_ui, state="disabled")
        self.btn_webui.pack(side="right", padx=5)
        self.lbl_stats = ctk.CTkLabel(row4, text="Idle", text_color="gray", font=("Consolas", 12)); self.lbl_stats.pack(side="right", padx=10)
            
        # Init
        self.refresh_chat_models()
        self.refresh_history_list()
        self._load_server_override()
        self.is_generating = False
        saved_flags = get_chat_extra_flags()
        if saved_flags:
            self.chat_flags_entry.insert(0, saved_flags)
        self.chat_mcp_var.set(get_chat_mcp_proxy())

    # --- MODEL & PATH LOGIC ---
    def get_default_models_dir(self):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
            if "Contents/MacOS" in base: base = os.path.abspath(os.path.join(base, "../../.."))
        else: base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "AI_Models")
        if not os.path.exists(path): 
            try: os.makedirs(path)
            except Exception as e: log.warning("Could not create folder %s: %s", path, e)
        return path

    def browse_model_dir(self):
        d = filedialog.askdirectory()
        self.app.lift()
        self.app.focus_force()
        if d:
            self.chat_model_dir_entry.delete(0, "end")
            self.chat_model_dir_entry.insert(0, d)
            self.refresh_chat_models()

    def _load_server_override(self):
        try:
            p = get_llama_server_override()
        except Exception:
            p = None
        if p:
            self.chat_server_entry.delete(0, "end")
            self.chat_server_entry.insert(0, p)
            self.lbl_server_status.configure(text="✅ Override aktiv", text_color="#00AA00")
        else:
            self.chat_server_entry.delete(0, "end")
            self.lbl_server_status.configure(text="Standard (gebündelt)", text_color="gray")

    def browse_server_binary(self):
        f = filedialog.askopenfilename(
            title="llama-server Binary wählen",
            filetypes=[("Executable", "*"), ("All files", "*.*")])
        self.app.lift()
        self.app.focus_force()
        if not f:
            return
        if not os.path.isfile(f):
            messagebox.showerror("Fehler", "Datei nicht gefunden.")
            self.app.lift()
            self.app.focus_force()
            return
        if not os.access(f, os.X_OK):
            messagebox.showwarning("Warnung", "Datei ist nicht ausführbar (chmod +x nötig). Trotzdem speichern?")
            self.app.lift()
            self.app.focus_force()
        if set_llama_server_override(f):
            self.chat_server_entry.delete(0, "end")
            self.chat_server_entry.insert(0, f)
            self.lbl_server_status.configure(text="✅ Override aktiv", text_color="#00AA00")
            messagebox.showinfo("Info", f"Server-Binary gespeichert:\n{f}\n\nWird beim nächsten Chat-Start verwendet.")
            self.app.lift()
            self.app.focus_force()
        else:
            messagebox.showerror("Fehler", "Config konnte nicht geschrieben werden.")
            self.app.lift()
            self.app.focus_force()

    def clear_server_binary(self):
        try:
            removed = clear_llama_server_override()
        except Exception as e:
            log.warning("Could not remove the server override: %s", e)
            removed = False
        if not removed:
            # Nicht "entfernt" melden, wenn die Einstellung noch in der Datei steht
            messagebox.showerror("Fehler", "Override konnte nicht entfernt werden.\nDetails stehen im Log-Tab.")
            self.app.lift()
            self.app.focus_force()
            return
        self.chat_server_entry.delete(0, "end")
        self.lbl_server_status.configure(text="Standard (gebündelt)", text_color="gray")
        messagebox.showinfo("Info", "Override entfernt — nutzt wieder die gebündelte Binary.")
        self.app.lift()
        self.app.focus_force()

    def refresh_chat_models(self):
        d = self.chat_model_dir_entry.get()
        if not os.path.isdir(d):
            self.chat_model_combo.configure(values=["Folder not found"])
            self.btn_load_chat.configure(state="disabled")
            return
        models = [f for f in os.listdir(d) if f.endswith(".gguf")]
        if not models:
            models = ["No .gguf files are currently loaded."]
            self.btn_load_chat.configure(state="disabled")
        else:
            self.btn_load_chat.configure(state="normal")
        self.chat_model_combo.configure(values=models)
        self.chat_model_combo.set(models[0])
        
    def animate_loading_model(self, step=0):
        if not self.is_loading_model: return
        dots = "." * (step % 4)
        self.lbl_stats.configure(text=f"Loading Model{dots}", text_color="orange")
        self.after(500, lambda: self.animate_loading_model(step + 1))    

    # --- HISTORY LOGIC ---
    def get_history_dir(self):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
            if "Contents/MacOS" in base: base = os.path.abspath(os.path.join(base, "../../.."))
        else: base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p = os.path.join(base, "Chat_History")
        if not os.path.exists(p): 
            try: os.makedirs(p)
            except Exception as e: log.warning("Could not create folder %s: %s", p, e)
        return p

    def refresh_history_list(self):
        d = self.get_history_dir()
        if os.path.exists(d):
            files = [f for f in os.listdir(d) if f.endswith(".json")]
            files.sort(reverse=True)
            if files: self.history_combo.configure(values=files)
            else: self.history_combo.configure(values=["(Leer)"])

    def save_history_json(self):
        if not self.chat_history: return
        name = f"Chat_{time.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        path = os.path.join(self.get_history_dir(), name)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.chat_history, f, indent=4)
            self.refresh_history_list()
            messagebox.showinfo("Saved", f"Chat saved 💾:\n{name}")
            self.app.lift()
            self.app.focus_force()
        except Exception as e: print(e)

    def load_history_json(self, filename):
        if filename == "(Leer)" or filename == "📜 History...": return
        path = os.path.join(self.get_history_dir(), filename)
        if not os.path.exists(path): return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.chat_history = json.load(f)
            self.chat_display.configure(state="normal")
            self.chat_display.delete("1.0", "end")
            for msg in self.chat_history:
                sender = "You" if msg['role'] == "User" else "AI"
                if msg['role'] == "Assistant": sender = "AI"
                self.chat_display.insert("end", f"\n[{sender}]: {msg['content']}\n")
            self.chat_display.see("end")
            self.chat_display.configure(state="disabled")
            self.lbl_stats.configure(text="History loaded.")
            # Läuft die Engine schon, bekommt das Modell den geladenen Verlauf sofort.
            # (Sonst wird er beim nächsten 🚀 Start übergeben.)
            self._send_history()
        except Exception as e:
            messagebox.showerror("Error", f"Load error ⚠️: {e}")

    # --- CHAT ENGINE LOGIC ---
    def start_chat_engine(self):
        d = self.chat_model_dir_entry.get()
        m = self.chat_model_combo.get()
        path = os.path.join(d, m)
        if not os.path.exists(path): return
        
        sys_p = self.chat_sys_prompt.get()
        temp = self.chat_temp_slider.get()
        tok = self.chat_tokens_slider.get()
        pen = self.chat_rep_slider.get()
        topp = self.chat_topp_slider.get()
        topk = int(self.chat_topk_slider.get())
        
        self.btn_load_chat.configure(state="disabled")
        self.btn_stop_chat.configure(state="normal")
        self.btn_clear.configure(state="normal")
        self.is_loading_model = True
        self.animate_loading_model()
        
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"\nSYSTEM: Start Chat 💬..\nModel: {m}\n")
        self.chat_display.configure(state="disabled")
        
        flags = self.chat_flags_entry.get().strip()
        set_chat_extra_flags(flags)   # für den nächsten App-Start merken
        mcp = bool(self.chat_mcp_var.get())
        set_chat_mcp_proxy(mcp)
        self.is_generating = False
        threading.Thread(target=self.run_chat_process, args=(path, sys_p, temp, tok, pen, topp, topk, flags, mcp), daemon=True).start()

    def open_web_ui(self):
        """Öffnet die native llama.cpp WebUI im Systembrowser."""
        if not self.webui_port or not self.chat_process or self.chat_process.poll() is not None:
            messagebox.showinfo("Info", "Starte zuerst den Chat (🚀 Start).")
            self.app.lift()
            self.app.focus_force()
            return
        webbrowser.open(f"http://127.0.0.1:{self.webui_port}/")

    def stop_chat_engine(self):
        self.is_loading_model = False # <--- ABSCHALTEN
        self.is_thinking = False      # <--- ABSCHALTEN
        if self.chat_process:
            proc, self.chat_process = self.chat_process, None
            # Erst "quit" schicken, damit der Worker den llama-server sauber herunterfährt und
            # das Modell aus dem Speicher verschwindet. Reagiert er nicht, wird er beendet.
            try:
                proc.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
                proc.stdin.flush()
                proc.stdin.close()
            except Exception:
                pass

            def _reap(p=proc):
                try:
                    p.wait(timeout=12)
                except Exception:
                    p.terminate()   # der Worker fängt das ab und räumt trotzdem auf
                    try:
                        p.wait(timeout=8)
                    except Exception:
                        p.kill()
            threading.Thread(target=_reap, daemon=True).start()
        self.is_generating = False
        self.btn_cancel_reply.configure(state="disabled", fg_color="gray")
        self.btn_load_chat.configure(state="normal", text="🚀 Start ", fg_color="#007aff")
        self.btn_stop_chat.configure(state="disabled")
        self.btn_clear.configure(state="disabled")
        self.webui_port = None
        self.after(0, lambda: self.btn_webui.configure(state="disabled", text="🌐 Web UI"))
        self.update_chat_ui("System", "Chat ended 📴")
        self.lbl_stats.configure(text="Stopped")

    def clear_context(self):
        if self.chat_process:
            try:
                self._send_cmd({"cmd": "reset"})
                self.chat_display.configure(state="normal")
                self.chat_display.delete("1.0", "end")
                self.chat_display.insert("end", "SYSTEM: 🧹 Context cleared.\n")
                self.chat_display.configure(state="disabled")
                self.chat_history = []
            except Exception as e:
                self.update_chat_ui("Error", f"Reset failed ❌: {e}")

    def run_chat_process(self, model_path, sys_prompt, temp, tok, pen, topp=0.95, topk=40, extra_flags="", mcp_proxy=False):
           # 1. Index vom Slider holen (0, 1, 2...)
        idx = int(self.slider_n_ctx.get())
            # 2. Echten Context-Wert aus der Liste ziehen
        ctx_size = self.ctx_values[idx]
    
        # v3.1 nutzt sys.executable als Basis
        args = [sys.executable]
        
        if not getattr(sys, 'frozen', False):
            # Im Dev-Mode: Pfad zur main.py (Dispatcher) hinzufügen
            import __main__
            args.append(os.path.abspath(__main__.__file__))
        
        # Worker-Flags und Chat-Parameter
        args.extend([
            "--worker", "chatbot",
            model_path,
            sys_prompt,
            str(temp),
            str(int(tok)),
            str(pen),
            str(int(ctx_size)), # <--- NEU
            str(topp),
            str(int(topk)),
            extra_flags,
            "1" if mcp_proxy else "0",
        ])
            
        try:
            # Nutze 'args' statt 'cmd'
            self.chat_process = subprocess.Popen(
                args, 
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1
            )
            # Eigene Referenz: self.chat_process wird beim Stoppen auf None gesetzt,
            # während diese Schleife noch die letzten Zeilen des Workers liest.
            proc = self.chat_process
            
            # Initialisiere die Variable am Anfang, um UnboundLocalError zu vermeiden
            line = "" 

            while True:
                if self.app.closing: break
                
                # Zeile lesen
                line = proc.stdout.readline()
                if not line: break 
                
                line = line.strip()
                if not line: continue
                
                # --- SOFORT-CHECK AUF READY ---
                if "READY" in line:
                    self.is_loading_model = False
                    self.after(0, lambda: self.btn_load_chat.configure(text="🚀 Start", fg_color="green"))
                    self.after(0, lambda: self.lbl_stats.configure(text="✅ Ready", text_color="green"))

                try:
                    # JSON parsen
                    data = json.loads(line)
                    if "chunk" in data:
                        self.is_loading_model = False
                        self.is_thinking = False
                        self.after(0, lambda t=data["chunk"]: self.append_stream(t))
                    
                    if "sys" in data:
                        # Auch im JSON nach READY suchen
                        if "READY" in data["sys"]:
                            self.is_loading_model = False
                            # Steht schon ein Gespräch im Fenster (geladene History oder vorherige
                            # Sitzung), bekommt das frisch gestartete Modell es mit.
                            self.after(0, self._send_history)
                        self.after(0, lambda t=data["sys"]: self.update_chat_ui("System", t))

                    if "error" in data:
                        # Früher wurde das ignoriert: die Anzeige blieb endlos bei "Thinking"
                        self.is_thinking = False
                        self.after(0, lambda t=data["error"]: self.update_chat_ui("Error", f"❌ {t}"))
                        self.after(0, lambda: self.lbl_stats.configure(text="Error", text_color="red"))

                    if data.get("done"):
                        self.is_thinking = False
                        self.after(0, lambda c=bool(data.get("cancelled")), f=bool(data.get("failed")): self._reply_finished(c, f))

                    if "webui_port" in data:
                        self.webui_port = int(data["webui_port"])
                        self.after(0, lambda: self.btn_webui.configure(state="normal"))
                        
                    if "stats" in data:
                        self.after(0, lambda s=data["stats"]: self.lbl_stats.configure(text=s))
                        
                except json.JSONDecodeError:
                    # --- FILTER: Technische Logs unterdrücken ---
                    # Wir ignorieren Zeilen, die mit '[' beginnen oder Hardware-Keywords enthalten
                    is_technical = line.startswith("[") or any(k in line.lower() for k in ["llama", "ggml", "metal", "slot"])
                    
                    if not is_technical:
                        current_text = line 
                        self.after(0, lambda t=current_text: self.update_chat_ui("System", t))

            # Der Worker hat sich von selbst beendet (Modell nicht ladbar, falsches Flag, Absturz):
            # Oberfläche zurücksetzen, sonst bleibt "Start" gesperrt und die Lade-Anzeige blinkt weiter.
            if self.chat_process is proc and not self.app.closing:
                self.after(0, lambda: self.stop_chat_engine() if self.chat_process is proc else None)

        except Exception as e:
            self.after(0, lambda t=str(e): self.update_chat_ui("Error", t))
       
          
    def on_enter_pressed(self, event):
        # Wenn Shift gedrückt ist -> Neue Zeile erlauben
        if event.state & 0x0001: 
            return None 
        # Sonst -> Senden und Zeilenumbruch verhindern
        else:
            self.send_chat_message()
            return "break" # Verhindert, dass das Enter im Feld landet    

    def send_chat_message(self, event=None):
        if not self.chat_process:
            self.is_loading_model = False # <--- SICHERHEITSHALBER AUS
            messagebox.showwarning("!", "Start first 🚀")
            self.app.lift()
            self.app.focus_force()
            return
                # NEU: Text aus Textbox lesen ("1.0" bis "end")
        msg = self.chat_input.get("1.0", "end").strip()
        
        if not msg: return
                # NEU: Textbox leeren
        self.chat_input.delete("1.0", "end")
        
        self.update_chat_ui("You", msg)
        self.is_thinking = True
        self.animate_thinking()
        
        try:
            # Als JSON-Zeile: Zeilenumbrüche im Text bleiben erhalten (Songtexte, Listen),
            # und die Regler gelten so, wie sie JETZT stehen – nicht nur wie beim Start.
            self._send_cmd({"cmd": "chat", "text": msg, "params": {
                "temperature": float(self.chat_temp_slider.get()),
                "max_tokens": int(self.chat_tokens_slider.get()),
                "repeat_penalty": float(self.chat_rep_slider.get()),
                "top_p": float(self.chat_topp_slider.get()),
                "top_k": int(self.chat_topk_slider.get()),
            }})
            self.is_generating = True
            self.btn_cancel_reply.configure(state="normal", fg_color="#AA0000")
        except Exception as e:
            self.is_thinking = False
            self.update_chat_ui("Error", f"❌ Could not send the message: {e}")

    def _send_cmd(self, cmd):
        """Schickt ein Kommando als eine JSON-Zeile an den Chat-Worker."""
        self.chat_process.stdin.write(json.dumps(cmd, ensure_ascii=False) + "\n")
        self.chat_process.stdin.flush()

    def _send_history(self):
        """Übergibt das Gespräch aus dem Fenster an das Modell (nur Fragen und Antworten)."""
        if not self.chat_process or self.chat_process.poll() is not None:
            return
        messages = [{"role": m["role"], "content": m["content"]} for m in self.chat_history
                    if m.get("role") in ("User", "AI", "Assistant") and str(m.get("content", "")).strip()]
        if not messages:
            return
        try:
            self._send_cmd({"cmd": "history", "messages": messages})
        except Exception as e:
            self.update_chat_ui("Error", f"❌ Could not restore the conversation: {e}")

    def cancel_reply(self):
        """Bricht nur die laufende Antwort ab; das Modell bleibt geladen."""
        if not self.chat_process or not self.is_generating:
            return
        try:
            self._send_cmd({"cmd": "cancel"})
            self.lbl_stats.configure(text="Stopping reply...", text_color="yellow")
        except Exception as e:
            self.update_chat_ui("Error", f"❌ Could not stop the reply: {e}")

    def _reply_finished(self, cancelled=False, failed=False):
        self.is_generating = False
        self.btn_cancel_reply.configure(state="disabled", fg_color="gray")
        if cancelled:
            self.update_chat_ui("System", "✋ Reply stopped.")
            self.lbl_stats.configure(text="Stopped reply", text_color="gray")
        elif not failed:
            self.lbl_stats.configure(text_color="gray")

    def update_chat_ui(self, sender, text):
                # 1. Prüfen: Ist der User ganz unten?
        is_at_bottom = self.chat_display.yview()[1] > 0.99
        self.chat_display.configure(state="normal")
        if sender == "You":
            self.chat_history.append({"role": "User", "content": text})
            self.chat_display.insert("end", f"\n👤 YOU: {text}\n")
                        # Bei eigenen Nachrichten IMMER scrollen
            self.chat_display.see("end") 
        elif sender == "Bot":
            self.chat_history.append({"role": "AI", "content": text})
            self.chat_display.insert("end", f"🤖 AI: {text}\n")
            if is_at_bottom: self.chat_display.see("end")
        else:
            self.chat_display.insert("end", f"[{sender}]: {text}\n")
            if is_at_bottom: self.chat_display.see("end")
            
        
        self.chat_display.configure(state="disabled")

    def append_stream(self, text):
        self.is_loading_model = False # <--- STOPPT LADEN-BLINKEN
        self.is_thinking = False      # STOPPT THINKING-BLINKEN
       
                # 1. Prüfen: Ist der User gerade ganz unten? (1.0 = 100%)
        # Wir nehmen > 0.99, um kleine Ungenauigkeiten zu tolerieren
        is_at_bottom = self.chat_display.yview()[1] > 0.99
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text)
                # 2. Nur scrollen, wenn der User vorher unten war
        if is_at_bottom:
            self.chat_display.see("end")
        
        self.chat_display.configure(state="disabled")
        
        if self.chat_history and self.chat_history[-1]['role'] == "AI":
            self.chat_history[-1]['content'] += text
        elif text.strip():
             self.chat_history.append({"role": "AI", "content": text})

    def animate_thinking(self, step=0):
        self.is_loading_model = False # <--- WENN WIR DENKEN, IST DAS LADEN VORBEI
        if not self.is_thinking: return
        dots = "." * (step % 4)
        self.lbl_stats.configure(text=f"Thinking 🤔{dots}")
        self.after(500, lambda: self.animate_thinking(step + 1))

    def export_chat(self):
        if not self.chat_history: return
        f = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML", "*.html")])
        if f:
                        # HIER GEÄNDERT: Wir übergeben den vollen Pfad 'f'
            path = export_chat_html(self.chat_history, f)
            messagebox.showinfo("Export", f"Saved 💾:\n{path}")
            self.app.lift()
            self.app.focus_force()

    def set_font_size(self, size):
        # 1. Chat-Verlauf (Textbox)
        self.chat_display.configure(font=("Arial", size))
        
        # 2. Eingabefeld (Entry oder Textbox)
        self.chat_input.configure(font=("Arial", size))
        
        # 3. Optional: Labels für Einstellungen (Temp, Tokens, Ctx)
        # Falls du diese auch skalieren willst:
        f_style = ("Arial", max(11, size - 2)) # Etwas kleiner als der Chat-Text
        
        # Hier die Namen deiner Labels einfügen, falls vorhanden:
        # self.lbl_temp.configure(font=f_style)
        # self.lbl_tok.configure(font=f_style)
        
    def update_ctx_label(self, v):
        # Holt den echten Wert aus der Liste basierend auf dem Slider-Index
        val = self.ctx_values[int(v)]
        self.lbl_n_ctx.configure(text=str(val))        