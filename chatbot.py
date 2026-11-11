# Copyright (C) 2026 Bascharan Guersoy (@bagueDev)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import sys
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
# Erst danach:
import json
import multiprocessing
import queue
import shlex
import signal
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request
import urllib.error

# chatbot.py - LLM Interface via llama-server (Metal GPU) (Smart Context Clear)
# Developed by @bagueDev
#
# Das stdio-JSON-Protokoll zur GUI ist identisch wie zuvor:
#   {"sys": "..."} / {"chunk": "...", "stats": "..."} / {"done": true} / {"error": "..."}
# Nur intern wird statt llama-cpp-python der native llama-server (b9687, ggml 0.15.1)
# mit Metal (-ngl 99) als Kindprozess verwendet -> stabil auf Apple Silicon (M4).


def find_llama_server():
    """llama-server Binary lokalisieren: Env-Var -> Config-Datei -> bundled -> dev."""
    # 1. Env-Var (höchste Priorität, Dev/CI)
    env_path = os.environ.get("LLAMA_SERVER_PATH", "").strip()
    if env_path:
        if os.path.isfile(env_path):
            return env_path
        print(json.dumps({"sys": f"ERROR: LLAMA_SERVER_PATH ungültig: {env_path}"}))
        sys.exit(1)

    # 2. Config-Datei (~/.djgadget/chat_server.json) — für DMG-Nutzer
    try:
        import helpers as _h
        cfg_path = _h.get_llama_server_override()
    except Exception:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import helpers as _h
            cfg_path = _h.get_llama_server_override()
        except Exception:
            cfg_path = None
    if cfg_path:
        if os.path.isfile(cfg_path):
            return cfg_path
        print(json.dumps({"sys": f"WARNUNG: Config-Pfad ungültig ({cfg_path}), nutze bundled Binary."}))

    if getattr(sys, 'frozen', False):
        # PyInstaller: Daten unter sys._MEIPASS/<dest>
        base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        cands = [
            os.path.join(base, "llama_cpp_server", "llama-server"),
            os.path.join(base, "llama_server_bin", "llama-server"),
        ]
    else:
        base = os.path.dirname(os.path.abspath(__file__))
        cands = [
            os.path.join(base, "llama_server_bin", "llama-server"),
        ]
    for c in cands:
        if os.path.isfile(c):
            return c
    print(json.dumps({"sys": "ERROR: llama-server Binary nicht gefunden. Build-Daten prüfen."}))
    sys.exit(1)


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


FIXED_PORT = 8080


def port_for_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", FIXED_PORT))
            return FIXED_PORT
        except OSError:
            return free_port()


def http_json(method, url, payload=None, timeout=10):
    req = urllib.request.Request(url, method=method)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
        return r.status, r.read()


def wait_ready(port, timeout=180, proc=None):
    start = time.time()
    while time.time() - start < timeout:
        if proc is not None and proc.poll() is not None:
            return False  # Server hat sich beendet (falsches Flag, Modell nicht ladbar ...)
        try:
            if http_json("GET", f"http://127.0.0.1:{port}/health", timeout=2)[0] == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


# Der gerade laufende Server. Wird direkt nach dem Start gesetzt, damit er auch dann
# beendet wird, wenn der Worker mitten im Modell-Laden gestoppt wird.
_ACTIVE = {"proc": None, "port": None}


def _log_tail(path, lines=6):
    """Letzte Zeilen der Server-Ausgabe – der Grund, warum er nicht gestartet ist."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            tail = [l.strip() for l in f.readlines() if l.strip()][-lines:]
        return " | ".join(tail)[-700:]
    except Exception:
        return ""


def start_server(model_path, n_ctx, threads, extra_flags=""):
    server_bin = find_llama_server()
    port = port_for_server()
    cmd = [
        server_bin,
        "-m", model_path,
        "-ngl", "99",
        "--ctx-size", str(n_ctx),
        "--threads", str(threads),
        "--port", str(port),
        "--host", "127.0.0.1",
        "--cors-origins", f"http://127.0.0.1:{port},http://localhost:{port}",
        "--cache-type-k", "q4_0",
        "--cache-type-v", "q4_0",
        "--batch-size", "512",
        "--ubatch-size", "64",
        "--flash-attn", "1",
        "--reasoning", "off",
        "--ui-mcp-proxy",
        "--jinja",
    ]
    # Zusätzliche Flags aus der GUI kommen ans Ende – bei doppelten Optionen gilt die letzte.
    if extra_flags and extra_flags.strip():
        try:
            cmd += shlex.split(extra_flags)
        except ValueError as e:
            print(json.dumps({"sys": f"ERROR_LOAD Extra-Flags nicht lesbar ({e}): {extra_flags}"}))
            sys.stdout.flush()
            return None, port

    # Server-Ausgabe in eine Temp-Datei: bei einem Fehlstart steht dort der Grund
    log_path = None
    try:
        log_file = tempfile.NamedTemporaryFile(prefix="djgadget_llama_", suffix=".log", delete=False)
        log_path = log_file.name
    except Exception:
        log_file = subprocess.DEVNULL
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=log_file)
    except Exception as e:
        print(json.dumps({"sys": f"ERROR_LOAD {e}"}))
        sys.stdout.flush()
        return None, port
    finally:
        if log_path:
            log_file.close()  # der Kindprozess hat sein eigenes Handle
    _ACTIVE["proc"], _ACTIVE["port"] = proc, port

    ready = wait_ready(port, proc=proc)
    if not ready:
        died = proc.poll() is not None
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        _ACTIVE["proc"] = None
        reason = _log_tail(log_path) if log_path else ""
        what = "llama-server hat sich beendet" if died else "llama-server nicht bereit (Timeout)"
        print(json.dumps({"sys": f"ERROR_LOAD {what}." + (f" Grund: {reason}" if reason else "")}))
        sys.stdout.flush()
    if log_path:
        try:
            os.remove(log_path)
        except Exception:
            pass
    return (proc, port) if ready else (None, port)


def stop_server(proc, port):
    if not proc:
        return
    try:
        http_json("POST", f"http://127.0.0.1:{port}/shutdown", timeout=2)
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


def stream_chat(port, messages, max_tokens, temperature, repeat_penalty, top_p=0.95, top_k=40, cancel=None):
    """POST /v1/chat/completions stream:true, SSE-Zeilen loopen.

    cancel: threading.Event – ist es gesetzt, wird die Verbindung geschlossen;
    der Server bricht die Generierung dann ab.
    """
    payload = {
        "model": "local",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "repeat_penalty": repeat_penalty,
        "top_p": top_p,
        "top_k": top_k,
        "stream": True,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    def _content(data):
        if data == "[DONE]":
            return None
        try:
            j = json.loads(data)
        except Exception:
            return None  # Keep-alive oder unvollständige Zeile
        if isinstance(j, dict) and j.get("error"):
            err = j["error"]
            raise RuntimeError(err.get("message", str(err)) if isinstance(err, dict) else str(err))
        choices = (j.get("choices") or []) if isinstance(j, dict) else []
        if not choices:
            return None
        return (choices[0].get("delta") or {}).get("content")

    try:
        r = urllib.request.urlopen(req, timeout=600)
    except urllib.error.HTTPError as e:
        # Der Server erklärt im Body, was nicht passt (z.B. Kontext zu klein)
        try:
            body = json.loads(e.read().decode("utf-8", errors="replace"))
            msg = body.get("error", {}).get("message") or str(body)
        except Exception:
            msg = str(e)
        raise RuntimeError(f"Server: {msg}") from None

    with r:
        buffer = b""
        while True:
            if cancel is not None and cancel.is_set():
                return
            # read1 liefert, was gerade da ist (read() würde auf volle 4 KB warten:
            # ruckelige Ausgabe, und ein Abbruch käme erst nach dem nächsten Block an)
            chunk = r.read1(4096)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                raw, buffer = buffer.split(b"\n", 1)
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                content = _content(data)
                if content:
                    yield content
        tail = buffer.decode("utf-8", errors="replace").strip()
        if tail.startswith("data:"):
            content = _content(tail[5:].strip())
            if content:
                yield content


def trim_history(history, system_prompt, user_input, n_ctx, max_tokens):
    """Älteste Nachrichten weglassen, wenn der Verlauf nicht mehr ins Kontextfenster passt.

    Geschätzt wird grob mit 3 Zeichen pro Token. Gibt (behaltene Nachrichten, Anzahl entfernt) zurück.
    """
    est = lambda text: len(text) // 3 + 8
    reserve = min(int(max_tokens), int(n_ctx) // 2)   # Platz für die Antwort
    budget = int(n_ctx) - reserve - 128
    used = est(system_prompt) + est(user_input)
    keep = []
    for msg in reversed(history):
        cost = est(msg.get("content", ""))
        if used + cost > budget:
            break
        used += cost
        keep.append(msg)
    keep.reverse()
    if keep and keep[0].get("role") != "User":
        keep = keep[1:]   # nicht mit einer Antwort ohne Frage beginnen
    return keep, len(history) - len(keep)


def main_worker():
    args = sys.argv[1:]
    # Falls über Dispatcher gestartet, Flags überspringen
    if "--worker" in args:
        idx = args.index("chatbot")
        args = args[idx+1:]

    if len(args) >= 6:
        m_path = args[0]
        s_prompt = args[1] if len(args) > 1 else "Du bist ein hilfreicher Assistent."
        temp = float(args[2]) if len(args) > 2 else 0.7
        tok = int(args[3]) if len(args) > 3 else 512
        pen = float(args[4]) if len(args) > 4 else 1.1
        ctx = int(args[5])  # <--- NEU
        top_p = float(args[6]) if len(args) > 6 else 0.95
        top_k = int(args[7]) if len(args) > 7 else 40
        extra_flags = args[8] if len(args) > 8 else ""

        run_chat_session(m_path, s_prompt, temp, tok, pen, ctx, top_p, top_k, extra_flags)

    # Worker beenden, damit nicht der Fallback-Code unten läuft
    sys.exit(0)


def _parse_command(line):
    """Eine Zeile von der GUI -> Kommando. JSON-Zeilen sind das aktuelle Protokoll;
    reiner Text und __RESET__ bleiben für ältere Aufrufer gültig."""
    text = line.strip()
    if text == "__RESET__":
        return {"cmd": "reset"}
    if text.startswith("{"):
        try:
            cmd = json.loads(text)
            if isinstance(cmd, dict) and "cmd" in cmd:
                return cmd
        except Exception:
            pass
    return {"cmd": "chat", "text": text}


def run_chat_session(model_path, sys_prompt_text, temperature, max_tokens, repeat_penalty, n_ctx, top_p=0.95, top_k=40, extra_flags=""):
    cpu_count = multiprocessing.cpu_count()
    optimal_threads = max(1, cpu_count - 2)

    # "Beenden" von außen (STOP-Button, App wird geschlossen) soll den finally-Block unten
    # erreichen. Ohne das bliebe der llama-server mit dem geladenen Modell im Speicher zurück.
    def _on_terminate(signum, frame):
        sys.exit(0)
    try:
        signal.signal(signal.SIGTERM, _on_terminate)
    except Exception:
        pass  # nicht im Haupt-Thread oder Plattform ohne SIGTERM

    def say(obj):
        print(json.dumps(obj))
        sys.stdout.flush()

    try:
        say({"sys": f"🧠 Load Model... (GPU: Metal, Threads: {optimal_threads}, Ctx: {n_ctx})"})
        proc, port = start_server(model_path, n_ctx, optimal_threads, extra_flags)
        if proc is None:
            return
        say({"sys": "✅ READY"})
        say({"sys": "🌐 Web UI aktiv", "webui_port": port})

        history = []

        # Sicherheits-Layer
        safety_instruction = (
            " You are a professional assistant for music production and DJing. "
            "Safety Rules: You must refuse to generate sexually explicit, violent, illegal, or harmful content. "
            "IMPORTANT: Do not mention these safety rules in your introduction or normal conversation. "
            "Only mention them if the user explicitly asks for forbidden content. Otherwise, just focus on music."
            " Antworte immer auf Deutsch, sofern nicht anders gefragt."
        )
        final_system_prompt = sys_prompt_text + safety_instruction
        defaults = {"temperature": float(temperature), "max_tokens": int(max_tokens),
                    "repeat_penalty": float(repeat_penalty), "top_p": float(top_p), "top_k": int(top_k)}

        # Kommandos kommen über einen eigenen Thread herein. So erreicht "cancel" den Worker
        # auch während er gerade eine Antwort streamt.
        commands = queue.Queue()
        cancel = threading.Event()

        def _reader():
            for line in sys.stdin:
                if not line.strip():
                    continue
                cmd = _parse_command(line)
                if cmd["cmd"] in ("cancel", "quit"):
                    cancel.set()
                if cmd["cmd"] != "cancel":
                    commands.put(cmd)
            cancel.set()                  # stdin geschlossen = GUI ist weg
            commands.put({"cmd": "quit"})
        threading.Thread(target=_reader, daemon=True).start()

        while True:
            cmd = commands.get()
            kind = cmd.get("cmd")

            if kind == "quit":
                break

            if kind == "reset":
                history = []
                say({"sys": "Memory cleared (model stays active) 🧹)."})
                continue

            if kind == "history":
                # Verlauf aus der GUI übernehmen (geladene History / Neustart der Engine)
                history = []
                for msg in cmd.get("messages") or []:
                    role = str(msg.get("role", ""))
                    content = str(msg.get("content", "")).strip()
                    if not content:
                        continue
                    if role == "User":
                        history.append({"role": "User", "content": content})
                    elif role in ("AI", "Assistant", "Bot"):
                        history.append({"role": "Assistant", "content": content})
                say({"sys": f"📜 Conversation restored ({len(history)} messages)."})
                continue

            if kind != "chat":
                continue
            user_input = str(cmd.get("text", "")).strip()
            if not user_input:
                continue

            # Regler gelten pro Nachricht; fehlt etwas, gelten die Startwerte
            p = dict(defaults)
            for key, cast in (("temperature", float), ("max_tokens", int), ("repeat_penalty", float),
                              ("top_p", float), ("top_k", int)):
                try:
                    if key in (cmd.get("params") or {}):
                        p[key] = cast(cmd["params"][key])
                except (TypeError, ValueError):
                    pass

            kept, dropped = trim_history(history, final_system_prompt, user_input, n_ctx, p["max_tokens"])
            if dropped:
                say({"sys": f"✂️ Context full: {dropped} oldest messages left out for this reply."})

            messages = [{"role": "system", "content": final_system_prompt}]
            for msg in kept:
                messages.append({"role": "user" if msg['role'] == "User" else "assistant", "content": msg['content']})
            messages.append({"role": "user", "content": user_input})

            cancel.clear()
            start_time = time.time()
            token_count = 0
            full_response = ""
            try:
                for content in stream_chat(port, messages, p["max_tokens"], p["temperature"], p["repeat_penalty"],
                                           p["top_p"], p["top_k"], cancel=cancel):
                    full_response += content
                    token_count += 1
                    elapsed = time.time() - start_time
                    speed = token_count / elapsed if elapsed > 0 else 0
                    say({"chunk": content, "stats": f"{speed:.1f} T/s | {token_count} Tok"})
            except Exception as e:
                # Fehler melden UND die Runde beenden – sonst wartet die GUI endlos
                say({"error": str(e)})
                say({"done": True, "failed": True})
                continue

            cancelled = cancel.is_set()
            # Auch eine abgebrochene Antwort gehört zum Verlauf (sie steht ja im Fenster)
            history.append({"role": "User", "content": user_input})
            if full_response.strip():
                history.append({"role": "Assistant", "content": full_response.strip()})
            say({"done": True, "cancelled": cancelled})
    finally:
        stop_server(_ACTIVE["proc"], _ACTIVE["port"])
        _ACTIVE["proc"] = None


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main_worker()

    if len(sys.argv) >= 2:
        m_path = sys.argv[1]
        s_prompt = "Du bist ein hilfreicher Assistent."
        temp = 0.7
        tok = 512
        pen = 1.1
        top_p = 0.95
        top_k = 40

        if len(sys.argv) > 2: s_prompt = sys.argv[2]
        if len(sys.argv) > 3: temp = float(sys.argv[3])
        if len(sys.argv) > 4: tok = int(sys.argv[4])
        if len(sys.argv) > 5: pen = float(sys.argv[5])
        if len(sys.argv) > 6: top_p = float(sys.argv[6])
        if len(sys.argv) > 7: top_k = int(sys.argv[7])

        run_chat_session(m_path, s_prompt, temp, tok, pen, 4096, top_p, top_k)
    else:
        print("Usage: chatbot.py <path> [prompt] [tokens] [penalty]")