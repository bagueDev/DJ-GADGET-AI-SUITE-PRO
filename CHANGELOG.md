# Changelog

All notable changes to **DJ Gadget AI-Suite Pro** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.3.1] - 2026-11-11

### 🎲 Melody Lab – Seed & reproduzierbare Ergebnisse (🎹)
- **Seed-Feld + 🔒 Lock** – ohne Lock würfelt jedes Generate / Full Loop einen neuen Seed (0–999999) und schreibt ihn ins Feld; mit Lock ergibt gleicher Seed + gleiche Einstellungen exakt dieselbe MIDI- und WAV-Datei (auch über Programmstarts hinweg).
- **Seed sichtbar** – im Status (`✅ Ready! (Seed 521392)`), im Log und als Vorschlag im Dateinamen beim MIDI-Speichern.
- **Gleiche Noten, neuer Sound** – gleicher Seed mit anderer Waveform liefert dieselbe Melodie; die 2-Takt-Vorschau entspricht dem Anfang der vollen Sequenz; die Melodie allein entspricht der Melodie im Full Loop.
- **Backend** – `@_seeded`-Decorator in `melody_generator.py` (Kwarg `seed=`, abwärtskompatibel): pro Funktion abgeleiteter Startwert, innere Aufrufe im Full Loop erben den Seed. Ein Lock lässt immer nur eine Generierung gleichzeitig würfeln.

### 🎵 Melody Lab – Motive statt Zufallsfolge (🎹)
- **Motiv-Engine** – statt jede Note einzeln zu würfeln, erfindet der Generator ein eintaktiges Motiv A und ein Kontrast-Motiv B und baut daraus 4-Takt-Phrasen: `A | A' (Ende variiert) | B | A (Schluss auf dem Akkord-Grundton, gehalten)`.
- **Motiv folgt der Progression** – der Anker wandert mit dem Akkord-Grundton, das Motiv wird also diatonisch mitverschoben (Sequenz) und bleibt erkennbar.
- **Messbar mehr Wiederholung** – Rhythmus Takt 1 ↔ Takt 5: 100 % statt ~20 % (Zufallsniveau); Takt 1 ↔ Takt 3 bleibt als Kontrast bei ~25–30 %. Tonbereich bleibt in der gewählten Oktavlage (kein Rand-Kleben).
- **Verse/Chorus** – je Energie-Stufe des Arrangements ein eigenes Motiv-Paar (Verse: kürzere Töne, reduzierter Tonvorrat; Chorus: längere Töne, volle Skala). Atempause und Mute-Regeln der Arrangements unverändert.
- Density, Swing, Humanize, Triads-Mode und Seed wirken wie bisher; der alte Zufalls-Modus bleibt im Backend über `motif=False` erreichbar.

### 🥁 Drums – Fixes & DnB-Groove (🎹)
- **Letzter Takt fehlte im Audio** – ein Schlag wurde komplett weggelassen, wenn sein Sample über das Dateiende ragte (Snare 1,37 s = ein ganzer Takt bei 174 BPM). Jetzt wird nur der Ausklang abgeschnitten, mit 10 ms Fade am Dateiende. Betraf WAV, Vorschau und Full-Loop-Mix aller Genres; MIDI war korrekt.
- **Techno / House / Synthpop spielten zwei Schlagzeuge** – nach dem eigenen Muster lief zusätzlich der „Standard 4/4"-Zweig (doppelte Kicks, ungewollte Snare auf 2+4, Synthpop-Kickmuster überdeckt). Kette repariert; Techno bekommt stattdessen einen dezenten Clap auf 2 und 4.
- **Reggaeton war identisch mit Reggae** (`"Reggae" in "Reggaeton"`) – das Dembow-Muster wird jetzt erreicht. Reggae hat erstmals Hi-Hats (8tel, Offbeat betont).
- **Kein Dauer-Ride mehr** – Techno, House, Oriental und Ambient spielten im Infinite-Loop durchgehend 16tel auf dem Ride. Jetzt feste Hat-Muster je Genre (House/Techno: offene Hat auf den Offbeats); Ride nur noch im Refrain eines Arrangements.
- **DnB: 8-Takt-Sektionen** – der 2-Takt-Groove bleibt stehen (`A B A B'`), Takt 4 ist der Turnaround (Extra-Kick auf der 4-und + Ghost), Takt 8 der Fill; erst danach wird neu gewürfelt.
- **DnB: Hats als Muster** – drei Varianten (Rolling 16ths, Shuffle, Straight 8ths) plus feste Open-Hat-Positionen pro Sektion; Density dünnt das Muster aus, statt in jedem Takt andere Löcher zu würfeln.
- **DnB/Rolling: Ghost-Snares** um die Hauptschläge (ab Density 40) und **Snare-Wirbel statt Tom-Fill** für beide DnB-Varianten.
- **Bass rastet auf die Kick ein (Full Loop)** – bei DnB, Trap und HipHop spielt der Bass mit den Stilen „Steady" und „Busy" genau auf den Kick-Positionen der Drums (eine Note pro Kick, gehalten bis zur nächsten; Trap als lange 808, DnB als kurze Sub-Stöße). Vorher lagen nur 50–86 % der Bass-Einsätze auf einer Kick und 28–50 % der Kicks hatten eine Bassnote, jetzt jeweils 100 %. Feste Bass-Patterns (Neuro Roller, Dembow …) und House/Techno/Reggae/Jazz bleiben unverändert.
- **Keine Doppeltreffer mehr** – House spielte gelegentlich zwei offene Hats bzw. zwei Claps auf demselben Schritt, DnB/Breakbeat zwei Ghost-Snares.
- Jazz-Comping wird pro Takt statt pro Schritt gewürfelt; Humanize-Jitter gilt pro Schlag und summiert sich nicht mehr auf.

### 🎼 Melody Lab – Generator-Fixes (🎹)
- **Full Loop: „Mode" gilt nur noch für die Akkorde, die Melodie bleibt einstimmig.** Bisher steuerte die Einstellung beide Spuren zugleich: Mit „Melody (Mono)" bestand die Akkordspur nur aus Grundtönen, mit „Triads" spielte die Melodie durchgehend dreistimmige Blöcke. Eine einstimmige Melodie über vollen Akkorden war im Full Loop nicht möglich. „Melody (Mono)" ergibt für die Akkordspur jetzt Dreiklänge (auch im einzelnen Chords-Modus).
- **Gehaltene Melodietöne reiben sich nicht mehr mit dem Akkord** – Viertel oder länger sowie Töne auf Schlag 1 und 3 rücken einen Skalenschritt auf einen Akkordton, wenn sie einen Halbton neben einem Akkordton liegen. Spannungstöne mit Ganzton-Abstand und kurze Durchgangstöne bleiben. Messung über 35 Full Loops in Dur/Moll: Reibung auf langen Tönen 16 % → 0 %, Akkordtöne auf langen Tönen 60 % → 75 %; der Anteil an Sekundschritten sinkt dabei von 46 % auf 38 %.
- **Presets funktionieren jetzt mit allen Skalen** – bei Skalen mit 5, 6 oder 12 Tönen (Pentatonik Dur/Moll, Blues, Hirajoshi, Ganzton, Chromatik) zeigten die Stufen der Progression auf falsche Töne und es entstanden keine Dreiklänge (0 % statt 100 %). Akkorde, Bass, Pads und Strings werden dort jetzt aus der passenden Dur- oder Moll-Leiter gebaut (`harmony_intervals()`); die Melodie bleibt in der gewählten Skala. Sieben-Ton-Skalen sind unverändert.
- **Sus2 / Sus4 mit reinen Intervallen** – die Töne kamen aus der Skala, sodass auf manchen Stufen ein Tritonus statt der Quarte bzw. eine kleine Sekunde entstand. Jetzt immer große Sekunde bzw. reine Quarte mit reiner Quinte.
- **Melodie klebte am oberen Rand** – die „Magnet"-Logik wählte fast immer den Ton darüber; ab Takt 3 lagen 87–97 % der Noten ganz oben. Jetzt hat der gewürfelte Ton Vorrang, Nachbartöne sind Ausweichtöne in zufälliger Reihenfolge (7–12 % am Rand, mehr verschiedene Töne, voller Tonbereich).
- **7 Progression-Presets ohne Rezept** – „Pop Anthem" und „Classic House" scheiterten an einem Leerzeichen, die fünf Reggae-Presets fehlten im Backend ganz und liefen still als „Random". Neuer toleranter Lookup `resolve_progression()` (ignoriert Emojis/Leerzeichen), Reggae-Rezepte ergänzt – 43/43 Presets greifen.
- **Full Loop mit „Random"** – Chords würfelten pro Takt eine Stufe, Bass und Melodie blieben auf dem Grundton. Jetzt wird einmal ein Preset gewürfelt, das alle Spuren gemeinsam nutzen (steht im Log: `🎲 Random progression used: …`).

### 🎹 Melody Lab – Tab-Fixes (🎹)
- **Vorschau ersetzt das Ergebnis nicht mehr** – die 2-Takt-Vorschau wird direkt abgespielt; ▶ Play und 💾 MIDI behalten die generierte Sequenz (vorher speicherte MIDI nach einem Dropdown-Wechsel nur die 2 Takte).
- **Keine Vorschau während einer Generierung.**
- **⏹ Stop beim Full Loop** zeigt jetzt „⏹ Stopped" statt „❌ Error" und greift auch während des Abmischens.
- **Fehlerpfad sperrte die Buttons** – `lambda: self._fail(..., e)` lief nach dem `except`-Block in einen `NameError`; Exception wird jetzt fest gebunden.
- **Echte Fehlerursache im Log-Tab** – der Generator merkt sich den letzten Fehler pro Thread (`get_last_error()`), statt ihn nur ins Terminal zu drucken.

### 🔊 Audio → MIDI (🎹)
- **Tempo nicht mehr fest 120 BPM** – neues BPM-Feld im Converter: eigener Wert → BPM aus dem Analyzer (wenn der Track dort gescannt ist) → automatische Erkennung. Die Noten liegen damit im DAW auf dem Raster des Tracks; das verwendete Tempo steht in Status, Log und Dialog.
- **🧽 Smooth funktioniert jetzt** – die Checkbox hatte bisher keine Wirkung. Melody: Medianfilter (~115 ms), gleiche Noten mit < 60 ms Pause werden verbunden, Noten < 90 ms verworfen. Drums: Doppelschläge < 60 ms werden zusammengefasst.
- **Drums-Modus neu: Erkennung pro Frequenzbereich** – bisher entschied eine einzige Helligkeits-Schwelle (1800 Hz) über den ganzen Mix, sodass fast alles auf einer Note landete (dunkles Material: nur Kicks, helles: nur Snares; Hi-Hats gab es gar nicht). Jetzt wird in Tiefen (Kick), Mitten (Snare/Clap) und Höhen (Hi-Hat) getrennt nach Schlägen gesucht, gleichzeitige Schläge sind möglich. Auf 8 Test-Loops mit bekannter Lösung: Kicks 9 % → 90 % gefunden bei 0 Fehltreffern, falsche Snare-Noten 104 → 17, Hi-Hats 0 % → 56 %.
- **Drums-Modus: Timing und Dynamik** – Schläge wurden ~1 Frame vor dem Schlag gemessen und bei dichten Folgen nach hinten geschoben; jetzt absolute Zeiten (mittlere Abweichung ~5 ms), Velocity nach Schlagstärke, Ausgabe auf MIDI-Kanal 10, Schlag am Dateianfang wird erkannt.
- **Neuer Modus 🎹 Chords** – erkennt die Akkordfolge (Dur/Moll-Dreiklänge) pro halbem Takt und schreibt sie als MIDI: Dreiklang ab C3 plus Grundton im Bass, exakt auf dem Beat-Raster, mit den Akkordnamen als Marker. Gleiche Nachbarn werden zu einem gehaltenen Akkord verbunden. Dazu eine Tonart-Schätzung als Paar aus Dur und paralleler Moll-Tonart (z. B. „C minor / D# major") in Dialog, Log und als MIDI-Tonart. Damit hat der Converter dieselben drei Modi wie der Generator. Test gegen Akkordfolgen aus dem eigenen Generator: 86 % der Halbtakte exakt richtig bei Akkorden allein (24 Dateien), 79 % im kompletten Mix mit Drums, Bass und Melodie (6 Dateien).
- **Als „experimental" gekennzeichnet** – regelbasierte Erkennung ohne trainiertes Modell; Hinweis im Tab, dass ein trockener Loop oder ein Stem aus Stems AI die beste Quelle ist.
- **🧲 Snap to 1/16 grid** – zieht die Noten aufs Raster und legt den Clip-Anfang auf einen Beat (unter 100 BPM 32tel, damit Halftime-Erkennung die echten 16tel nicht verliert). Mit bekanntem BPM lagen in 6 von 8 Test-Loops alle erkannten Kicks exakt auf der richtigen Position.
- **🎚 Full mix (whole song)** – trennt vor der Erkennung Schlag- und Ton-Anteil (HPSS). Bei kompletten Mixen deutlich besser (House: 17/31 Kicks mit 21 falschen → 31/31 mit 2 falschen), bei trockenen Loops schlechter (0 → 40 falsche Kicks), deshalb als Schalter und standardmäßig aus.
- **Automatisches BPM nachgeschärft** – das grob erkannte Tempo wird an den gefundenen Einsätzen ausgerichtet (Klicktrack 174: 172,27 → 174,07) und gegen typische Verwechslungen (×1,5, ×4/3) geprüft. Halbes/doppeltes Tempo bleibt mehrdeutig.
- **Melody: wiederholte gleiche Töne** werden an deutlichen neuen Anschlägen getrennt (Test: 37 → 40 von 40 Tönen), solange Smooth aus ist.
- **Rückfrage, wenn `<name>_extracted.mid` schon existiert** – Yes überschreibt, No öffnet einen Speichern-Dialog mit dem nächsten freien Namen (`…_extracted_2.mid`) als Vorschlag, Cancel bricht ab.
- **Letzter Ton ging verloren**, wenn das Audio mitten im Ton endet – behoben.
- „No notes detected" und andere Converter-Fehler erscheinen jetzt im Log-Tab.

### 🔍 Playlist & BPM – genaueres Tempo (🔍)
- **BPM rastete auf grobe Stufen ein** – die Erkennung lieferte nur Rasterwerte (117.45, 123.05, 129.20, 172.27 …): Tracks mit 122 bis 126 BPM zeigten alle 123.05, und Auto-Tag schrieb diesen Wert in die Datei. Das Tempo wird jetzt um den Rohwert herum fein nachgemessen (Klick-Tracks mit 120/124/125/126/128 BPM: exakt). Bei Material ohne klaren Puls bleibt der bisherige Wert. Halbes Tempo (z. B. 87 statt 174) kann weiterhin vorkommen – dafür Min-BPM oder „BPM (2x)".

### ✏️ Metadata Editor & Auto-Tag – ehrliche Rückmeldung, fehlende Felder (✏️)
- **Open Key stimmte nicht** – die Statuszeile zeigte die Camelot-Zahl mit anderem Buchstaben (9B → „9d"). Open Key zählt ab C-Dur: 8B ist 1d, 9B ist 2d.
- **MP3 mit neuem Cover wurde nie gespeichert** – ein Import mitten in der Funktion ließ den MP3-Zweig abstürzen, sobald ein Cover dabei war; der Fehler wurde verschluckt und der Editor zeigte trotzdem „Saved". Es wurde dann gar nichts geschrieben, auch nicht Artist oder Titel. Behoben.
- **Tracknummer (Trk) ging verloren** – sie wurde zwar geschrieben, aber nie wieder eingelesen: Das Feld im Editor blieb nach dem Neuladen leer, und das nächste Speichern überschrieb sie mit 0. Sie wird jetzt in allen Formaten gelesen; ein leeres Feld lässt die vorhandene Nummer stehen. M4A versteht auch „3/12".
- **Auto-Tag setzte die Tracknummer auf 0** – beim Scan mit Auto-Tag wurde neben BPM und Key auch der Standardwert „0" als Tracknummer geschrieben und überschrieb vorhandene Nummern. Auto-Tag fasst jetzt wirklich nur noch BPM und Key an.
- **FLAC:** Titel, Album und Cover werden jetzt geschrieben (bisher nur Artist, BPM, Key, Track).
- **M4A: Kommentar bleibt erhalten** – Auto-Tag und der Editor schrieben den Camelot-Code ins Kommentarfeld und überschrieben damit einen vorhandenen Kommentar. Der Code steht jetzt im üblichen Tonart-Feld (`initialkey`); ein bereits überschriebener Kommentar lässt sich nicht wiederherstellen. Dateien aus älteren Versionen werden weiter gelesen.
- **M4A:** Artist, Titel, Album und Cover werden jetzt geschrieben (bisher nur BPM, Key, Track). Leere Felder überschreiben bei diesen neu geschriebenen Feldern nichts.
- **„❌ Save failed (see Log)" statt immer „✅ Saved!"** – der Editor wertet das Ergebnis des Tag-Prozesses aus; der Grund (schreibgeschützt, beschädigt, nicht unterstütztes Format, Datei fehlt) steht im Log-Tab.
- **Auto-Tag beim Scan** trägt „Failed" statt „Saved" ein, wenn BPM/Key nicht geschrieben werden konnten; die Meldungen des Analyzer-Prozesses erscheinen im Log-Tab. Dessen Fehlerausgabe wird jetzt mitgelesen (vorher konnte der Scan an einer vollen Pipe hängen bleiben).
- Nicht unterstützte Dateitypen und fehlende Dateien gelten als Fehler statt als stiller Erfolg; eine fehlende MP3 wird nicht mehr als leere Datei angelegt.
- Chat: „Override entfernt" erscheint nur noch, wenn die Server-Einstellung wirklich entfernt wurde.

### 🤖 AI Chat – Grundfunktionen repariert (🤖)
- **✋ Stop reply** – bricht nur die laufende Antwort ab; das Modell bleibt geladen. Bisher gab es nur ⏹ STOP, das die ganze Engine beendet.
- **Fehler des Modells erscheinen im Chat** – die Fehlermeldung des Workers wurde nie ausgewertet, die Anzeige blieb endlos bei „Thinking". Jetzt steht der Grund im Fenster (z. B. Kontext zu klein).
- **Geladene History kennt jetzt auch das Modell** – ein über „📜 History" geladener Chat erschien nur im Fenster. Er wird jetzt an das Modell übergeben, sofort oder beim nächsten 🚀 Start; ebenso das bisherige Gespräch nach einem Neustart der Engine.
- **Regler gelten pro Nachricht** – Temp, MaxT, Rep, TopP und TopK wirkten nur beim Start der Engine. Nur Ctx braucht weiterhin einen Neustart.
- **Zeilenumbrüche bleiben erhalten** – mehrzeilige Eingaben (Songtexte, Listen) wurden zu einer Zeile zusammengezogen.
- **⏹ STOP entlädt das Modell wirklich** – der Worker wurde hart beendet, sein Aufräum-Code lief nicht und der llama-server blieb mit dem Modell im Speicher zurück (nachgestellt: 1 übrig gebliebener Server vorher, 0 jetzt; auch beim Schließen der App und mitten im Laden).
- **Voller Kontext** – passt der Verlauf nicht mehr ins Kontextfenster, werden die ältesten Nachrichten für die Antwort weggelassen und das im Chat gemeldet, statt mit einem Fehler abzubrechen.
- **Zwischenspeicher passend zum Kontext komprimiert** – bisher immer `q4_0` für K und V, die stärkste Stufe. Jetzt: bis 16.384 Tokens K q8 / V q8, bis 65.536 K q8 / V q4, darüber K q4 / V q4. Die K-Werte (worauf das Modell achtet) vertragen Kompression schlechter als die V-Werte, deshalb wird zuerst bei V gespart. Gemessen mit einem 3B-Modell bei 32.768 Tokens: 936 MB (q4/q4), 1.352 MB (q8/q4), 1.768 MB (q8/q8). Die gewählte Stufe steht beim Laden im Chat; das Extra-Flags-Feld überschreibt sie.
- **⚙️ Extra server flags** – optionales Feld für zusätzliche llama-server-Optionen (z. B. `--cache-type-k q8_0 --cache-type-v q8_0`), gespeichert in `chat_server.json`. Bei doppelten Optionen gilt die letzte.
- **🔌 MCP proxy nur noch auf Wunsch** – der MCP-Proxy des llama-servers lief bisher bei jedem Chat-Start mit. Jetzt gibt es dafür einen Haken im Chat-Tab (Standard: aus, gespeichert in `chat_server.json`). Wer MCP in der Web UI nutzt, schaltet ihn vor 🚀 Start ein.
- **Fehlstart mit Grund** – beendet sich der Server beim Start (falsches Flag, Modell nicht ladbar), erscheint die Ursache nach etwa einer Sekunde statt eines Timeouts nach 3 Minuten; die Oberfläche setzt sich danach selbst zurück.
- Flüssigere Ausgabe (Antwort wurde in 4-KB-Blöcken gelesen); neues Kommando-Protokoll zwischen Tab und Worker (JSON-Zeilen, alte Klartext-Zeilen bleiben gültig).

### 🔎 Verschluckte Fehler sichtbar gemacht (📝)
- **Zentrale Warnungen im Log-Tab** – neuer Logger `djgadget` mit Handler in `main.py`; Module ohne Zugriff auf die Oberfläche (`helpers.py`, `melody_generator.py`) und Worker-Threads können damit Meldungen in den Log-Tab schreiben.
- **18 von 50 stillen `except`-Stellen melden sich jetzt**, ohne dass sich das Verhalten ändert: Ordner konnte nicht angelegt werden (AI_Models, Offline_Models, Whisper_Models, Chat_History, Config), `chat_server.json` nicht les-/schreibbar, Drum-Sample defekt (Synthese als Ersatz), Player (nächster Track, Spulen, Loop-Anzeige), BPM ×2 / ÷2, unlesbarer LRC-Zeitstempel beim SRT-Export, Tag-Schreibfehler im Analyzer-Unterprozess (stderr).
- Die übrigen 31 sind bewusst still (fehlende Tags oder Cover, Abfragen beim Start, Aufräumen, Schutz von GUI-Aufrufen).

### 🔄 Playlist-Update – Fixes (🔍)
- **Update nach Export fand nie eine Datei** – undefinierte Variable wurde von `except: pass` verschluckt; Export und Update nutzen jetzt denselben `safe_playlist_name()`.
- **Rückfrage + Backup** – vor dem Überschreiben erscheint eine Ja/Nein-Abfrage mit Dateien und Track-Anzahl (inkl. Warnung bei aktivem Filter); die alte Version wird als `<datei>.bak` gesichert.
- **Atomares Schreiben** – Inhalt wird im Speicher erzeugt und über eine Temp-Datei ersetzt; ein Fehler hinterlässt keine leere oder halbe Playlist mehr (gilt auch für den Export).
- „Filter zurücksetzen" vergisst die Playlist nicht mehr; wörtliches `\n` in drei Dialogen korrigiert.
- Rekordbox-/M3U-/JSON-Erzeugung für Export und Update zusammengelegt.

---

## [3.3.0] - 2026-11-01

### ⚡ Stems – MLX-Backend für Apple Silicon (🎧)
- **Demucs `4.0.1 → 4.1.0`** – inkl. neuem `--other-method` (`add`/`minus`/`none` steuert, wie `no_vocals` gebaut wird: Stems summieren, Original-minus-Stem oder verwerfen).
- **Neuer MLX-Fast-Path (`demucs-mlx`, fp32)** – native Apple-Silicon-Inferenz via Metal, ca. 2–3× schneller als Torch-MPS bei gleichem Output-Layout (`Stems/<Modell>/<Song>/*.wav`).
- **Backend-Auto (`separator.py`)** – ARM + MLX verfügbar → MLX, sonst Torch (Fallback für Intel-Macs/Linux bleibt erhalten, inkl. automatischem Fallback bei MLX-Fehler).
- **Stems-Tab UI** – neues Backend-Dropdown (Auto / MLX / Torch) + `no_*`-Dropdown (`add`/`minus`/`none`); „Offline Load" lädt den MLX-Modell-Cache jetzt wirklich nach `Offline_Models/demucs-mlx` vorab.
- **Schlankes ARM-Bundle** – `app_build_arm_single.sh` packt `demucs_mlx`/`mlx`/`safetensors` ein und schließt `torch`/`torchaudio` aus (~1 GB kleiner).

### 🥁 Drums – mehr Abwechslung, weniger Looping (🎹)
- **Phrasen-Wechsel** – alle 2 Takte werden mit 60 % Chance frische Pattern gewürfelt (statt 8 Takte `ABABABAB`); `pick_pair()` garantiert A≠B.
- **Pools verdoppelt** – HipHop- und Trap-Kick-Pools von 4 auf je 8 Pattern erweitert.
- **Hats & Ghosts** – HipHop (8tel-Hats mit Akzenten + Open-Hat), Trap (dichte Hats + Offbeat-Öffnung), Ghost-Snare (HipHop), Ghost-Clap + offene Hat (House), Offbeat-Hats (Synthpop).
- **Sound-Round-Robin** – jeder Drumsound rotiert durch 3 leicht verstimmte Varianten (0/+35/−40 Cent) gegen den Maschinengewehr-Effekt.
- **Timing-Jitter** – Humanize streut jetzt auch Timing (±5 ms Audio, ±6 Ticks MIDI), nicht nur Velocity.

### 🎹 Melody Lab – Robustheit & UX (🎹)
- **Zentrales Input-Sanitizing** – BPM (20–300) + Bars (1–**128** statt 512, echter RAM-Schutz) in allen Pfaden (Generate, Preview, Full Loop); stürzt nie mehr ab.
- **Gehärtete Worker-Wrapper** – alle `_run_*`-Threads + Converter mit try/except; Status bleibt nie hängen, Fehler landen im Log.
- **Preview-Debounce (400 ms)** – schnelles Durchklicken rendert nur 1× statt 5 Threads.
- **Generations-Counter** – veraltete Ergebnisse werden verworfen (kein Last-Writer-Wins mehr).
- **Full Loop mit Fortschritt + Stop** – `Creating Loop (2/6): 🎹 Chords...` via `progress_cb`-Hook, ⏹ Stop-Button bricht zwischen den Stems ab (Backend-Kwargs abwärtskompatibel).
- **Künstliche Delays (800/1200 ms) entfernt**, Generate-Buttons während Läufen gesperrt, Temp-Ordner werden beim Start aufgeräumt.
- **Progression-Header** im Melody-Pfad abgefangen (→ Random), Toggle-Logik tabellarisch, Genre-Dropdown-Regression gefixt.

### 🐛 Fixed
- About-Fenster zeigte `Version 3.0` – jetzt `3.3` (passend zu Titel + Build); Kontakt-E-Mail aktualisiert.
- Genre-Dropdown im Melody-Tab war nach Refactoring unsichtbar (fehlende `.grid()`-Zeile) – wiederhergestellt.
- Tippfehler „ore folder" → „or folder" im Analyzer-Pfad-Eingabefeld.
- JSON-Export-Fehler `Object of type ndarray is not JSON serializable` behoben (numpy-Typen werden jetzt konvertiert).
- „Que" → „Queue" Tippfehler im Transcriber (2 Stellen).

### ✨ Features
- **Playlist Update-Button** (🔄 UPDATE) – aktualisiert bestehende Playlist-Dateien in place (XML/M3U/JSON) ohne neue Datei zu erstellen.
- **CORS-Hardening** – llama-server nur für localhost-Origins (`--cors-origins`), verhindert Prompt-Injection über bösartige Websites.

### 🔐 Lizenz & Open Source
- **GPLv3** als Projekt-Lizenz: `LICENSE`-Datei (vollständiger GPLv3-Text), `THIRD_PARTY_LICENSES.md` (Lizenzen aller Dependencies).
- **Copyright-Header** in allen `.py`-Dateien (`Copyright (C) 2026 Bascharan Guersoy (@bagueDev)`).
- **Produktkey-System entfernt** (`license_guard.py` gelöscht, Lizenz-Check in `main.py` entfernt).
- About-Fenster: Copyright + „Licensed under GPLv3" + Button „View Full License".
- „All rights reserved" → GPLv3-Hinweis.

### 🔧 Infrastruktur
- **llama-server aktualisiert** auf 0.8.0-dev (build 12032, commit dde879bc4) — ersetzt 9687 (b4024af6c).
- **Config-Datei Override** (`~/.djgadget/chat_server.json`) — eigene llama-server-Binary nutzen ohne Rebuild (Env-Var → Config → bundled → dev).
- **Chat-Tab UI** — neue Zeile „🔧 Server-Binary (optional)" mit Datei-Picker (📂) und Löschen (🗑️).
- **Chat-Tab Regler** — TopP (🎯) und TopK (🔝) Slider hinzugefügt (2-reihiges Layout: Temp/MaxT/Rep + TopP/TopK/Ctx).
- **`.gitignore`** erstellt — venv, build, dist, Modelle, Binaries, Backups ausgeschlossen.
- **Samples umbenannt** mit `bagueDEV_`-Prefix (24 Dateien), `sample_map` aktualisiert.
- **Build-Skript bereinigt** — `--collect-all "llama_cpp"` entfernt (verhindert dylib-Konflikt mit neuer Binary), `license_guard` entfernt.

---

## [3.1.2] - 2026-08-11

### 🥁 DnB/Breakbeat – Amen-Break-Engine (🎹)
- **Neues Genre „DnB/Rolling"** – trennt den bisherigen 2-Step-Stil (Rolling Hats, SampleFocus-Logik) vom neuen Breakbeat-Sound.
- **„DnB/Breakbeat" spielt jetzt echte Amen-Patterns** – neuer `amen_pool` (Classic Amen, Jungle Roller, Techstep) mit den Signature-Merkmalen: „phat" 4 (Kick+Snare zusammen), Ghost-Snares (Velocity 35–55, Dichte-gesteuert), Flam vor der 4 (Schritt 11), 16tel-Hats mit Akzentmuster + Open Hats auf Offbeats.
- **Amen-„Break"-Fill** – im 8-Takt-Fill spielt Breakbeat statt Toms eine Snare-Rat-a-tat-Roll mit Crescendo (echtes Break-Taktende).
- Beide Varianten: 2 Muster pro Klick, wechseln pro Takt; Zwei-Takt-Zyklus beibehalten. Rolling-Logik komplett unverändert.

### ⚠️ Notes
- Build-Ergebnis: `dist/DJ Gadget AI-Suite Pro v3.1.2 @bagueDEV ARM.app` + `.dmg`.

---

## [3.1.1] - 2026-08-11

### 🎛️ Melody Lab – Musiklogik-Härtung (🎹)
- **Synthpop/Trap/HipHop spielten DnB-Beats** – nach der Genre-Auswahl überschrieb eine pauschale Zeile `p_a/p_b` immer mit dem DnB-Pool. Jetzt saubere if/elif-Kette: jedes Genre (Synthpop, Trap, HipHop, DnB) bekommt seine eigenen Kick-Patterns.
- **Power-Chords (2 Noten) + Inversion = Absturz** – `apply_voicing()` griff bei „1st/2nd Inversion" auf `notes[2]` zu (IndexError) → Chords stürzten still ab. Inversion wird bei <3 Noten jetzt übersprungen.
- **Genre „Random" (und „Ambient") hatten fast keine Drums** – fielen nur auf die globalen Fallback-Hats zurück. Neuer `else`-Zweig: solider Basic 4/4 (Kick auf jedem Viertel, Snare auf 2+4).
- **Reggaeton hatte keine Drums** – neuer Dembow-Branch bindet die vorher toten Latin-Patterns `samba_kick` (Kick-Puls) und `bossa_rim` (Rimshots) ein + Offbeat-Hats.
- **Bass ignorierte die Taktart** – `create_bass_files()` rechnete immer mit 16 Steps. Jetzt 12 Steps bei 3/4 & 6/8 (Muster-Positionen werden skaliert), passend zu Drums/Chords.

### ⚠️ Notes
- Build-Ergebnis: `dist/DJ Gadget AI-Suite Pro v3.1.1 @bagueDEV ARM.app` + `.dmg`.

---

## [3.1.0] - 2026-08-11

### 🐛 Melody Lab Fixes (🎹)
- **Chords-Preview repariert** – die Vorschau übergab die Argumente in falscher Reihenfolge und ohne `sound`/`genre`/`human` → Thread stürzte still ab (TypeError). Jetzt mit korrekten 15 Args (inkl. `sound`, `genre`, `time_sig`, `human`).
- **Humanize-Schalter wirkt jetzt wirklich** – Chords-Generierung übergab das Checkbox-**Objekt** statt des Bool-Werts → Humanize lief immer. Jetzt `bool(self.mel_human.get())`.
- **Drums-Ausgabe-Ort korrigiert** – `output_dir`/`time_sig` waren im Drum-Wrapper vertauscht → Dateien landeten im Ordner `"4/4"` statt im Temp-Verzeichnis.
- **Arrangement Structure wirkt jetzt überall** – `get_arrangement_energy()` (Intro/Verse/Chorus/Drop-Logik) wurde nur beim Full Loop durchgereicht; jetzt auch bei Melody/Chords/Drums Einzelgenerierung **und** Preview.
- **Genre „Random"** hat jetzt ein Profil in `GENRE_PROFILES` (setzt Defaults statt stille No-op).

### 🧠 Chat-Tab (🧠)
- **`🤖 Tools`-Dropdown entfernt** – die eingebauten llama-server-Agent-Tools (inkl. `exec_shell_command`) werden nicht mehr angeboten; Tools laufen ausschließlich über **MCP** (`--ui-mcp-proxy` + WebUI). `--tools`-Flag und Parameter-Kette (UI → Worker → Server) komplett entfernt.
- **Stabiler WebUI-Port 8080** – llama-server startet jetzt auf einem festen Port (`FIXED_PORT = 8080`, Fallback auf freien Port falls belegt). Dadurch bleibt die Browser-Origin stabil: **MCP-Server-Konfiguration (LocalStorage) und Chatverläufe (IndexedDB) der WebUI überleben App-Neustarts**. (Hinweis: MCP-Server einmalig unter `127.0.0.1:8080` neu eintragen.)

### ⚠️ Notes
- Chat engine (llama-server GPU/Metal) ansonsten unverändert.
- Alte Ordnerkopien (`gadget arm/`, `Archiv_basis_golden/`) bleiben unberührt – nur Root-Dateien werden gebaut.

---

## [3.0.0] - 2026-08-10

### ⭐ Highlights
- **🎹 Melody Lab complete overhaul** – full 6-track loop generation engine
- **⌨️ Shortcut Cheat-Sheet** – new built-in help window with all keyboard commands
- **🔊 Global Volume Control** – master mute + volume slider in the header
- **✏️ Metadata Editor upgrade** – track number support, scrollbar, Send-to-Analyzer, Show-in-Finder
- **🔐 Product Activation** – license key check on first launch

### ✨ Melody Lab (🎹)
- Integrated the advanced `melody_generator` engine:
  - **19 scales** (Major, Minor, Pentatonic, Blues, Phrygian, ...)
  - **45+ chord progressions** across 6 categories
  - **10 genre profiles** with smart BPM/parameter defaults
  - **Hybrid drum sounds** – 12 real percussion samples with synthesized fallbacks
  - **3 generator modes**: Melody, Chords, Drums (+ dedicated preview)
  - **🎼 Full Loop**: 6-track stereo loop (Melody + Chords + Drums + Bass + Pads/Keys + Arp) with **MIDI merge** via `mido`
  - **Voicing styles**, bass complexity, arrangement modes, humanize & swing controls
  - **Audio → MIDI converter** with sensitivity / smoothing / duration options
- Added `samples/` folder (drum one-shots) bundled into the app.
- Fixed a converter crash where the duration dropdown widget was never created (`midi_conv_len`).

### ✏️ Metadata Editor (✏️)
- **Track number field** – edit/save `tracknumber` (`TRCK`/`tracknumber`/`trkn` tags) for MP3, FLAC, M4A, WAV, AIFF
- **File list scrollbar** (clean container with `CTkScrollbar`)
- Context menu: **"🔍 Send to Analyzer"** – push selected files straight into Playlist & BPM analysis
- Context menu: **"📂 Show in Finder"** – reveal the file in Finder/Explorer
- **Better cover cropping** via `ImageOps.fit` (exact 200×200, no ratio offset)
- UI polish: "🔄 Sync Playlist" label, larger placeholder

### 🔍 Playlist & BPM (🔍)
- **`load_external_files()`** – receive files from the Metadata Editor (log entry, loading animation, batch analysis)
- **Numeric table sorting** – BPM and # columns now sort numerically (`9 → 10 → 100`) instead of as strings; the internal track list is hard-synced so the order survives tab switches
- Context menu: **"📂 Show in Finder"** – reveal the selected file in Finder/Explorer
- **Single-instance details window** – "📄 Details" lifts the already-open window instead of opening duplicates; it auto-refreshes when a new track starts playing

### 🛠️ Under the Hood
- **`analyzer.py`**: `write_metadata()` accepts a new `track` argument with per-format tag support; `--tag` worker reads the 10th argument (backwards compatible).
- **`helpers.py`**: new `ShortcutOverviewWindow` (shortcut cheat-sheet) and `reveal_in_finder()`.

### ✂️ Stems AI (✂️)
- Context menu: **"🔍 Send to Analyzer"** – push selected files straight into Playlist & BPM analysis
- Context menu: **"📂 Show in Finder"** – reveal the file in Finder/Explorer
- File list **scrollbar** (cleaner list navigation)

### 🎙️ Vocal Transcriber (🎙️)
- **Auto-SRT**: after every transcription a `.srt` subtitle file is automatically generated from the fresh `.lrc` (Karaoke) in the source folder
- Context menu: **"🔍 Send to Analyzer"** + **"📂 Show in Finder"**
- Console context menu: **"📋 Copy"** (selection or all) / **"🗑️ Clear Log"**
- File list **scrollbar**
- **Video support**: file dialog now accepts `.mp4`, `.mov`, `.mkv` (besides audio)
- Status hint now mentions `.srt` export + auto-reset to default text after batch
- **`transcriber.py`**: transcription uses `word_timestamps=True`, `vad_filter=False`, `condition_on_previous_text=True` for more precise timings

### ⌨️ Shortcuts & UI (⌨️)
- Chat-Tab: **"🌐 Web UI"** button (enabled once the model is loaded) opens the native llama.cpp web interface in your browser at the live server port
- Chat-Tab: **"🤖 Tools"** dropdown enables llama-server built-in agent tools (`all`, or `read_file`, `write_file`, `edit_file`, `grep_search`, …) — passed to the server via `--tools`
- Chat-Tab: **MCP proxy** is now enabled on the llama-server (`--ui-mcp-proxy 1`) so the WebUI can reach MCP servers
- Chat-Tab: **Max-Token slider** reworked — 512-token steps up to 32768, default **4096**, 20 % narrower
- **`F1`** – open Shortcut Cheat-Sheet, **`F2`** / `ℹ️` – About window
- **`Cmd + 9` / `Cmd + 0`** – volume down / up in **every** tab
- **Melody Lab**: `Space` = play/pause, `Return` = generate, `+` = full loop, `Cmd + S` = save MIDI
- **Playlist**: `0`/`9` volume, `M` = track details
- **Improved About window**: single-instance guard, `Cmd+W` handling, resizable

### 🐛 Fixed
- Melody Lab shortcuts referenced non-existent methods (`play_generated_melody` / `generate_melody`) – now correctly wired to `play()` / `generate()`.

### ⚠️ Notes
- **`license_guard.py`** added: the app asks for a product key on first launch. Workers (analysis/separation/transcription/chat) are **not** blocked by the activation check.
- Chat engine (llama-server GPU/Metal) untouched in this release.

---

## [2.5.0] - 2026-06-17

### ✨ Initial ARM/Metal release
- App fully rebuilt as a single binary for **Apple Silicon (ARM)**.
- **Chat engine on GPU (Metal)** via native `llama-server` subprocess (replaces unstable in-process `llama-cpp-python`).
  - Flash attention enabled, Metal offload `-ngl 99`.
- Workers (analyzer / separator / transcriber / chatbot) run as separate subprocesses from one bundle.

---

[3.3.0]: https://github.com/baguedev/DJ-GADGET-AI-SUITE-PRO/releases/tag/v3.3.0
[3.1.0]: https://github.com/baguedev/DJ-GADGET-AI-SUITE-PRO/releases/tag/v3.1.0
[3.0.0]: https://github.com/baguedev/DJ-GADGET-AI-SUITE-PRO/releases/tag/v3.0.0
[2.5.0]: https://github.com/baguedev/DJ-GADGET-AI-SUITE-PRO/releases/tag/v2.5.0