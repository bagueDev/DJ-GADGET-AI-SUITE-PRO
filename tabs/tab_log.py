# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import customtkinter as ctk
import time

class LogTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.log_text = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 14))
        self.log_text.pack(fill="both", expand=True)
    
    def log(self, msg):
        # 1. Prüfen: Ist der User gerade ganz unten?
        # yview()[1] gibt die Position des unteren Rands an (1.0 = ganz unten)
        is_at_bottom = self.log_text.yview()[1] > 0.99
        
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{time.strftime('%H:%M:%S')} > {msg}\n")
        # 2. Nur automatisch nach unten springen, wenn man schon unten war
        if is_at_bottom:
            self.log_text.see("end")
        
        self.log_text.configure(state="disabled")
        
    def set_font_size(self, size):
        self.log_text.configure(font=("Consolas", size))