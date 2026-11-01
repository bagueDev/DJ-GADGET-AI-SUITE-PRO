# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import os
import sys
import time
import platform
import subprocess
import json
import mutagen
import urllib.parse
import tkinter as tk              # Das normale Tkinter (für Menüs)
import customtkinter as ctk       # Das moderne CustomTkinter (für Fenster)
import xml.etree.ElementTree as ET
from xml.dom import minidom
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.wave import WAVE
from mutagen.aiff import AIFF 
from mutagen.id3 import ID3

# --- KONSTANTEN ---
CAMELOT_COLORS = {
    '1A':  "#2E6E32", '1B':  "#3B8F3F",   # Dunkelgrün (Bleibt)
    '2A':  "#49887D", '2B':  '#00695C',   # Dunkles Türkis (Bleibt)
    
    # OPTIMIERT: Blau-Töne etwas lebendiger, damit sie nicht schwarz wirken
    '3A':  '#0288D1', '3B':  '#039BE5',   # Kräftiges Ozeanblau
    '4A':  '#1976D2', '4B':  '#2196F3',   # Strahlendes Königsblau
    
    # OPTIMIERT: Violett/Pink etwas aufgehellt für bessere Sichtbarkeit
    '5A':  "#7551C8", '5B':  "#72589D",   # Sattes Deep Purple
    '6A':  '#C2185B', '6B':  '#D81B60',   # Kräftiges Pink/Beere
    
    '7A':  '#B71C1C', '7B':  '#C62828',   # Dunkelrot (Bleibt)
    '8A':  '#BF360C', '8B':  '#D84315',   # Dunkles Orange‑Rot (Bleibt)
    '9A':  '#E65100', '9B':  '#EF6C00',   # Kräftiges Orange (Bleibt)
    '10A': "#E76705", '10B': "#D7741D",   # Dunkles Gold‑Orange (Bleibt)
    '11A': '#827717', '11B': '#9E9D24',   # Oliv‑Grün (Bleibt)
    '12A': '#33691E', '12B': '#558B2F',   # Dunkles Moosgrün (Bleibt)
}
# Rückwärts-Suche: Camelot -> Musikalische Tonart
# Korrigierte Rückwärts-Suche: Camelot -> Musikalische Tonart
REVERSE_CAMELOT = {
    '1A': 'Ab minor',  '1B': 'B major',
    '2A': 'Eb minor',  '2B': 'F# major',
    '3A': 'Bb minor',  '3B': 'Db major',
    '4A': 'F minor',   '4B': 'Ab major',
    '5A': 'C minor',   '5B': 'Eb major',
    '6A': 'G minor',   '6B': 'Bb major',
    '7A': 'D minor',   '7B': 'F major',
    '8A': 'A minor',   '8B': 'C major',
    '9A': 'E minor',   '9B': 'G major',
    '10A': 'B minor',  '10B': 'D major',
    '11A': 'F# minor', '11B': 'A major',
    '12A': 'Db minor', '12B': 'E major'
}

# --- FUNKTIONEN ---
def get_executable_path(name):
    """Findet den Pfad zum Helfer-Programm (Binary) oder Skript (.py)"""
    if getattr(sys, 'frozen', False):
        # IM APP BUNDLE: Wir suchen die ausführbare Datei (ohne .py)
        base_path = os.path.dirname(sys.executable)
        exe_name = name
        if os.name == 'nt': exe_name += ".exe"
        return sys.executable
    else:
        # IM EDITOR: Wir suchen das .py Skript im Root-Ordner
        # Wir gehen davon aus, dass helpers.py im Root oder in /tabs liegt
        d = os.path.dirname(os.path.abspath(__file__))
        # Falls helpers in /tabs liegt, gehen wir einen Ordner hoch
        if "tabs" in d:
            d = os.path.dirname(d)
        return os.path.join(d, f"{name}.py")

# --- Config-Datei für llama-server Override (chat_server.json) ---
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".djgadget")
CONFIG_FILE = os.path.join(CONFIG_DIR, "chat_server.json")


def get_config_dir():
    """Verzeichnis für App-Config (cross-platform, immer beschreibbar)."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass
    return CONFIG_DIR


def get_llama_server_override():
    """Liest llama_server_path aus chat_server.json. Gibt Pfad oder None zurück."""
    try:
        if not os.path.isfile(CONFIG_FILE):
            return None
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        p = (data or {}).get("llama_server_path", "")
        p = (p or "").strip()
        if p and os.path.isfile(p):
            return p
        return None
    except Exception:
        return None


def set_llama_server_override(path):
    """Schreibt/aktualisiert llama_server_path in chat_server.json."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        data = {}
        if os.path.isfile(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            except Exception:
                data = {}
        data["llama_server_path"] = (path or "").strip()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def clear_llama_server_override():
    """Entfernt den llama_server_path-Eintrag (Fallback auf bundled)."""
    try:
        if not os.path.isfile(CONFIG_FILE):
            return True
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        data.pop("llama_server_path", None)
        if not data:
            try:
                os.remove(CONFIG_FILE)
            except Exception:
                pass
        else:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def read_tags_quick(path):
    # Standardwerte
    info = {
        "artist": "", "title": "", "album": "", 
        "bpm": "", "key": "", "camelot": ""
    }
    try:
        ext = os.path.splitext(path)[1].lower()
        
        # 1. MP3 (ID3 Tags)
        if ext == '.mp3':
            try:
                from mutagen.id3 import ID3
                tags = ID3(path)
                info['artist'] = str(tags.get('TPE1', [''])[0]) if 'TPE1' in tags else ""
                info['title'] = str(tags.get('TIT2', [''])[0]) if 'TIT2' in tags else ""
                info['album'] = str(tags.get('TALB', [''])[0]) if 'TALB' in tags else ""
                info['bpm'] = str(tags.get('TBPM', [''])[0]) if 'TBPM' in tags else ""
                # TKEY wird oft für Key oder Camelot genutzt
                info['camelot'] = str(tags.get('TKEY', [''])[0]) if 'TKEY' in tags else ""
            except: pass

        # 2. FLAC
        elif ext == '.flac':
            try:
                from mutagen.flac import FLAC
                f = FLAC(path)
                info['artist'] = f.get('artist', [''])[0]
                info['title'] = f.get('title', [''])[0]
                info['album'] = f.get('album', [''])[0]
                info['bpm'] = f.get('bpm', [''])[0]
                info['camelot'] = f.get('initialkey', [''])[0]
            except: pass

        # 3. M4A / MP4
        elif ext == '.m4a':
            try:
                from mutagen.mp4 import MP4
                m = MP4(path)
                info['artist'] = m.get('\xa9ART', [''])[0]
                info['title'] = m.get('\xa9nam', [''])[0]
                info['album'] = m.get('\xa9alb', [''])[0]
                # BPM ist bei M4A oft ein Integer im Feld 'tmpo'
                tmpo = m.get('tmpo', [0])[0]
                info['bpm'] = str(tmpo) if tmpo else ""
                info['camelot'] = m.get('\xa9cmt', [''])[0] # Oft im Kommentar
            except: pass

        # 4. WAV / AIFF
        elif ext in ['.wav', '.aiff', '.aif']:
            try:
                from mutagen.wave import WAVE
                from mutagen.aiff import AIFF
                t = WAVE(path) if ext == '.wav' else AIFF(path)
                if t.tags:
                    info['artist'] = str(t.tags.get('TPE1', [''])[0]) if 'TPE1' in t.tags else ""
                    info['title'] = str(t.tags.get('TIT2', [''])[0]) if 'TIT2' in t.tags else ""
                    info['album'] = str(t.tags.get('TALB', [''])[0]) if 'TALB' in t.tags else ""
                    info['bpm'] = str(t.tags.get('TBPM', [''])[0]) if 'TBPM' in t.tags else ""
                    info['camelot'] = str(t.tags.get('TKEY', [''])[0]) if 'TKEY' in t.tags else ""
            except: pass
            
    except Exception as e:
        print(f"Read Error: {e}")
        
            # AM ENDE DER FUNKTION (vor dem return info):
    if info['camelot'] and not info['key']:
        # Falls wir Camelot haben, aber keinen Key, suchen wir ihn aus der Liste
        # Wir säubern den String (falls Leerzeichen drin sind)
        clean_camelot = info['camelot'].strip().upper()
        if clean_camelot in REVERSE_CAMELOT:
            info['key'] = REVERSE_CAMELOT[clean_camelot]
        
    return info

def extract_cover_data(path):
    try:
        ext = os.path.splitext(path)[1].lower()
        data = None
        if ext == '.mp3':
            try:
                tags = ID3(path)
                apic = tags.getall("APIC")
                if apic: data = apic[0].data
            except: pass
        elif ext == '.flac':
            try:
                f = FLAC(path)
                if f.pictures: data = f.pictures[0].data
            except: pass
        elif ext == '.m4a':
            try:
                m = MP4(path)
                if 'covr' in m and m['covr']: data = m['covr'][0]
            except: pass
        elif ext in ['.wav', '.aiff', '.aif']:
            try:
                if ext == '.wav': t = WAVE(path)
                else: t = AIFF(path)
                if t.tags:
                    apic = t.tags.getall("APIC")
                    if apic: data = apic[0].data
            except: pass
        return data
    except: return None

def perform_export(track_list, export_folder, formats, playlist_name):
    created = []
    safe_name = "".join([c for c in playlist_name if c.isalnum() or c in " _-"]).strip()
    if not safe_name: safe_name = "Playlist"
    try:
        if "Rekordbox" in formats:
            root = ET.Element("DJ_PLAYLISTS", Version="1.0.0", Creator="@bagueDev")
            col = ET.SubElement(root, "COLLECTION", Entries=str(len(track_list)))
            for i, r in enumerate(track_list):
                loc = "file://localhost" + urllib.parse.quote(os.path.abspath(r['Pfad']).replace("\\","/"))
                t = ET.SubElement(col, "TRACK", TrackID=str(i+1), Name=str(r['Dateiname']), Artist="DJ Import", Kind="Audio File", Size=str(r['Größe']), TotalTime="300", Location=loc, AverageBpm=str(r['BPM']))
                if str(r['Camelot']) != "-": t.set("Tonality", str(r['Camelot']))
            pl = ET.SubElement(root, "PLAYLISTS")
            node = ET.SubElement(pl, "NODE", Type="FOLDER", Name="Imports", Count="1")
            pl_n = ET.SubElement(node, "NODE", Name=playlist_name, Type="PLAYLIST", Entries=str(len(track_list)))
            for i in range(len(track_list)): ET.SubElement(pl_n, "TRACK", Key=str(i+1))
            with open(os.path.join(export_folder, f"{safe_name}.xml"), "w", encoding="utf-8") as f: f.write(minidom.parseString(ET.tostring(root)).toprettyxml(indent="  "))
            created.append(f"{safe_name}.xml")
        if "M3U" in formats:
            with open(os.path.join(export_folder, f"{safe_name}.m3u"), "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for r in track_list: f.write(f"#EXTINF:-1,{r['Dateiname']}\n{r['Pfad']}\n")
            created.append(f"{safe_name}.m3u")
        if "JSON" in formats:
            data = {"name": playlist_name, "dev": "@bagueDev", "tracks": track_list}
            with open(os.path.join(export_folder, f"{safe_name}.json"), "w", encoding="utf-8") as f: json.dump(data, f, indent=4)
            created.append(f"{safe_name}.json")
        return f"✅ Export OK: {', '.join(created)}"
    except Exception as e: return f"❌ Fehler: {e}"

def export_chat_html(history, target_path):
    try:
        html = """<html><head><style>body { font-family: sans-serif; background: #1a1a1a; color: white; padding: 20px;} .msg { padding: 10px; margin-bottom: 10px; border-radius: 5px; } .user { background: #005580; text-align: right; margin-left: 20%; } .bot { background: #333; text-align: left; margin-right: 20%; } h1 { color: #00AAFF; }</style></head><body><h1>Chat Export - DJ Gadget AI Suite Pro</h1>"""
        for msg in history:
            cls = "user" if msg['role'] == "User" else "bot"
            html += f"<div class='msg {cls}'><strong>{msg['role']}:</strong><br>{msg['content'].replace(chr(10), '<br>')}</div>"
        html += "<br><small>Generated by @bagueDev - DJ Gadget AI Suite Pro</small></body></html>"
        
        # HIER GEÄNDERT: Wir speichern direkt unter dem Wunschnamen
        with open(target_path, "w", encoding="utf-8") as f: 
            f.write(html)
            
        return target_path
    except Exception as e: return str(e)

# --- UI HELPER (RECHTSKLICK FIX) ---
class RightClickMenu:
    def __init__(self, widget):
        # 1. Das innere Widget finden (für CTk)
        self.target = widget
        if hasattr(widget, "_textbox"): self.target = widget._textbox
        elif hasattr(widget, "_entry"): self.target = widget._entry
        
        # 2. Referenz sichern! (Damit Python es nicht löscht)
        # Wir kleben das Menü-Objekt einfach an das Widget dran.
        self.target.rc_menu = self 

        self.menu = tk.Menu(self.target, tearoff=0)
        self.menu.add_command(label=" 📄 Copy", command=lambda: self.target.event_generate("<<Copy>>"))
        self.menu.add_command(label=" 📋 Paste", command=lambda: self.target.event_generate("<<Paste>>"))
        self.menu.add_separator()
        self.menu.add_command(label="✂️ Cut", command=lambda: self.target.event_generate("<<Cut>>"))
        self.menu.add_command(label="🔘 Select All", command=self.select_all)

        # 3. Alle Mac/Windows Bindings
        self.target.bind("<Button-3>", self.show_menu) # Windows / Mac Maus
        self.target.bind("<Button-2>", self.show_menu) # Mac Trackpad (oft)
        self.target.bind("<Control-Button-1>", self.show_menu) # Mac Ctrl+Click

    def show_menu(self, event):
        try:
            self.target.focus_set()
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()
            
    def select_all(self):
        self.target.event_generate("<<SelectAll>>")
        
        
    # --- IMPORT LOGIC ---
def import_playlist_file(playlist_path):
    """Liest M3U, XML oder JSON und gibt eine Liste von Tracks zurück."""
    tracks = []
    if not os.path.exists(playlist_path): return []
    
    ext = os.path.splitext(playlist_path)[1].lower()
    base_dir = os.path.dirname(playlist_path) # Für relative Pfade in M3U
    
    try:
        # 1. JSON (Unser eigenes Format - Volle Daten)
        if ext == '.json':
            with open(playlist_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Prüfen ob es unser Format ist
                if "tracks" in data:
                    for t in data["tracks"]:
                        if os.path.exists(t['Pfad']):
                            tracks.append(t)

        # 2. Rekordbox XML (Volle Daten)
        elif ext == '.xml':
            tree = ET.parse(playlist_path)
            root = tree.getroot()
            # Suche in COLLECTION -> TRACK
            collection = root.find("COLLECTION")
            if collection is not None:
                for tr in collection.findall("TRACK"):
                    # Pfad decodieren (file://localhost/...)
                    raw_loc = tr.get("Location", "")
                    path = urllib.parse.unquote(raw_loc.replace("file://localhost", ""))
                    
                    # Windows Fix (falls nötig)
                    if os.name == 'nt' and path.startswith("/"): path = path[1:]
                    
                    if os.path.exists(path):
                        # Metadaten auslesen
                        bpm = tr.get("AverageBpm", "0")
                        key = tr.get("Tonality", "-")
                        name = tr.get("Name", os.path.basename(path))
                        
                        tracks.append({
                            "Dateiname": name,
                            "Pfad": path,
                            "BPM": float(bpm) if bpm else 0,
                            "Camelot": key,
                            "Key": key, # Rekordbox nutzt oft Camelot als Key
                            "Tags": "Imported",
                            "Time": "--:--" # XML hat TotalTime in Sekunden, könnte man umrechnen
                        })

        # 3. M3U / M3U8 (Nur Pfade)
        elif ext == '.m3u' or ext == '.m3u8':
            with open(playlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    
                    # Pfad prüfen (Absolut oder Relativ?)
                    check_path = line
                    if not os.path.isabs(check_path):
                        check_path = os.path.join(base_dir, line)
                    
                    if os.path.exists(check_path):
                        tracks.append({
                            "Dateiname": os.path.basename(check_path),
                            "Pfad": check_path,
                            "BPM": 0,       # Unbekannt
                            "Camelot": "-", # Unbekannt
                            "Key": "-",
                            "Tags": "Pending",
                            "Time": "--:--"
                        })
                        
    except Exception as e:
        print(f"Import Error: {e}")
        
    return tracks    

# --- METADATA INFO POPUP ---
def get_raw_metadata_string(path):
    """Liest ALLE technischen und Tag-Daten aus"""
    if not os.path.exists(path): return "Datei nicht gefunden."
    
    lines = []
    lines.append(f"FILE: {os.path.basename(path)}")
    lines.append(f"PATH: {path}")
    lines.append("-" * 40)
    
    try:
        f = mutagen.File(path)
        if not f: return "Format nicht unterstützt oder Datei defekt."
        
        # 1. Technische Daten
        if f.info:
            lines.append("--- TECH INFO ---")
            lines.append(f"Duration: {int(f.info.length)} sec")
            if hasattr(f.info, 'bitrate'): lines.append(f"Bitrate: {int(f.info.bitrate / 1000)} kbps")
            if hasattr(f.info, 'sample_rate'): lines.append(f"Sample Rate: {f.info.sample_rate} Hz")
            if hasattr(f.info, 'channels'): lines.append(f"Channels: {f.info.channels}")
            lines.append("")

        # 2. Alle Tags
        lines.append("--- TAGS (RAW) ---")
        # Mutagen Tags sind Dictionary-ähnlich
        for key, value in f.tags.items():
            # Werte schön formatieren
            val_str = str(value)
            # Bei Listen (oft bei MP3/M4A) nur den Inhalt zeigen
            if isinstance(value, list):
                val_str = ", ".join([str(v) for v in value])
            
            # Lange Base64 Strings (Cover Art) kürzen
            if len(val_str) > 100: 
                val_str = val_str[:100] + "... [DATA]"
                
            lines.append(f"{key}: {val_str}")
            
    except Exception as e:
        lines.append(f"Error reading tags: {e}")
        
    return "\n".join(lines)

def show_details_popup(parent, file_path):
    """Öffnet ein Fenster mit den Rohdaten"""
    if not file_path: return
    
    info_text = get_raw_metadata_string(file_path)
    
    # Popup Fenster
    top = ctk.CTkToplevel(parent)
    top.title("File Details")
    top.geometry("275x375")
    top.attributes("-topmost", True) # Immer im Vordergrund
    
    # Textbox
    textbox = ctk.CTkTextbox(top, font=("Consolas", 12))
    textbox.pack(fill="both", expand=True, padx=10, pady=10)
    textbox.insert("0.0", info_text)
    
    # Rechtsklick Menü auch hier aktivieren!
    RightClickMenu(textbox) 
    
    textbox.configure(state="disabled") # Read-only
        # --- NEU: WIR GEBEN DIE OBJEKTE ZURÜCK ---
    return top, textbox

def get_open_key(camelot_code):
    """Wandelt Camelot (8A/8B) in Traktor Open Key (8m/8d) um"""
    if not camelot_code or len(camelot_code) < 2:
        return ""
    
    code = camelot_code.strip().upper()
    # A wird zu m (moll), B wird zu d (dur)
    return code.replace('A', 'm').replace('B', 'd')

def reveal_in_finder(path):
    """Öffnet den Finder (Mac) oder Explorer (Win) und markiert die Datei."""
    if not path or not os.path.exists(path): return

    try:
        system_name = platform.system()

        if system_name == "Darwin": # macOS
            # 'open -R' öffnet den Ordner und markiert die Datei (Reveal)
            subprocess.run(["open", "-R", path])

        elif system_name == "Windows": # Windows
            # 'explorer /select' macht das Gleiche unter Windows
            subprocess.run(f'explorer /select,"{path}"')

        else: # Linux (Fallback)
            subprocess.run(["xdg-open", os.path.dirname(path)])

    except Exception as e:
        print(f"Reveal-Fehler: {e}")

class ShortcutOverviewWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Keyboard Shortcuts & Commands")
        self.geometry("550x650")

        # Fenster-Einstellungen
        self.lift()
        self.focus_force()
        self.grab_set()

        # Titel
        ctk.CTkLabel(self, text="⌨️ Shortcut Cheat-Sheet", font=("Arial", 24, "bold")).pack(pady=(20, 10))
        ctk.CTkLabel(self, text="Handle the AI Suite like an instrument.", text_color="gray").pack(pady=(0, 15))

        # Scroll-Container
        scroll = ctk.CTkScrollableFrame(self, width=450, height=450)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # --- FIX: Cmd+W abfangen ---
        def close_help(event=None):
            self.destroy()
            return "break"

        self.bind("<Command-w>", close_help)
        self.bind("<Control-w>", close_help)
        # --------

        # --- DIE DATEN (Exakt nach deiner Liste) ---
        shortcuts = [
    ("🌍 GLOBAL NAVIGATION", [
        ("Cmd + ⬅️ / ➡️", "Switch Tab (Previous/Next)"),
        ("Cmd + 9 / 0", "Volume 🔉/🔊 (Softer/Louder)"),
        ("F1", "Show Help")
    ]),
    ("🔍 ANALYZER (Playlist & DJ)", [
        ("Space", "Play/Pause ▶️/⏸️"),
        ("S", "Stop ⏹️ (Reset)"),
        ("⬅️ / ➡️", "Rewind ⏪/ Fast Forward ⏩ (10s)"),
        ("I / O", "Set Loop IN/OUT 📥/📤"),
        ("P", "Preview Loop 🔁"),
        ("K", "Exit Loop (Seamless Transition) ➡️"),
        ("L", "Save Cut as WAV 💾"),
        ("M", "Meta Details ℹ️"),
        ("1 - 6", "Smart Loop ⚡ (1, 2, 4, 8, 16, 32 Bars)"),

        ("Enter", "Start Scan 🚀"),
        ("Esc", "Cancel Scan 🛑"),
        ("#", "Choose Folder 📂"),
        ("+", "Add Files 📄"),
        ("R", "Remove Track 🚫"),
        ("Z", "Undo ↩️"),
        ("J / H", "Import Playlist 📥/Export Playlist 📤")
    ]),
    ("✂️ STEMS AI (Remixing)", [
        ("Enter", "Start Separation ✂️"),
        ("Esc", "Cancel Batch 🛑"),
        ("#", "Add Files ➕"),
        ("T", "Sync from Analyzer 📥"),
        ("R / C", "Remove/ Clear List 🚫🗑️"),
        ("Z", "Undo ↩️")
    ]),
    ("🤖 AI CHAT", [
        ("Cmd + Enter", "Send Message 💬"),
        ("Esc", "Stop Answer ⏹️"),
        ("Cmd + #", "Choose Model Folder 📂"),
        ("Cmd + +", "Start Engine 🚀"),
        ("Cmd + S", "Save History 💾"),
        ("Cmd + E", "Export to HTML 🌐"),
        ("Cmd + D", "Clear Context 🗑️")
    ]),
    ("📝 TRANSCRIBER (Lyrics/Subs)", [
        ("Enter", "Start Transcription 📝"),
        ("Esc", "Cancel 🛑"),
        ("#", "Add Vocal/Video ➕"),
        ("T", "Sync from Analyzer 📥"),
        ("R / C", "Remove/Clear ❌🗑️"),
        ("Z", "Undo ↩️")
    ]),
    ("🎹 MELODY LAB (Creative)", [
        ("Enter", "Generate Melody 🎲"),
        ("Space", "Play/Pause ▶️/⏸️"),
        ("Cmd + S", "Save Midi 💾"),
        ("+", "Generate Full Midi Loop 🔁📄"),

    ]),
    ("✏️ META EDITOR (Tagging)", [
        ("Cmd + S", "Save 💾"),
        ("#", "Load File 📄"),
        ("T", "Sync from Analyzer 📥"),
        ("M", "Meta Details ℹ️"),
        ("R / C", "Remove/Clear ❌🗑️"),
        ("Z", "Undo ↩️")
    ])
]

        # --- TABELLE GENERIEREN ---
        for category, items in shortcuts:
            # Kategorie-Header
            header_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            header_frame.pack(fill="x", pady=(20, 5))
            ctk.CTkLabel(header_frame, text=category, font=("Arial", 16, "bold"), text_color="#007aff", anchor="w").pack(side="left")
            ctk.CTkFrame(header_frame, height=2, fg_color="#333").pack(side="bottom", fill="x", pady=2)

            # Einträge
            for key, desc in items:
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", pady=2)

                # Taste (Links)
                k_lbl = ctk.CTkLabel(row, text=key, font=("Consolas", 13, "bold"), width=140, anchor="e", text_color="#FFA500")
                k_lbl.pack(side="left", padx=(0, 15))

                # Beschreibung (Rechts)
                d_lbl = ctk.CTkLabel(row, text=desc, font=("Arial", 13), anchor="w", text_color=("black", "white"))
                d_lbl.pack(side="left", fill="x", expand=True)