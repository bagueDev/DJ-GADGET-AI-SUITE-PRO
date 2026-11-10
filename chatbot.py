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
import socket
import subprocess
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


def wait_ready(port, timeout=180):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if http_json("GET", f"http://127.0.0.1:{port}/health", timeout=2)[0] == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def start_server(model_path, n_ctx, threads):
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
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(json.dumps({"sys": f"ERROR_LOAD {e}"}))
        sys.stdout.flush()
        return None, port
    if not wait_ready(port):
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        print(json.dumps({"sys": "ERROR_LOAD llama-server nicht bereit (Timeout)."}))
        sys.stdout.flush()
        return None, port
    return proc, port


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


def stream_chat(port, messages, max_tokens, temperature, repeat_penalty, top_p=0.95, top_k=40):
    """POST /v1/chat/completions stream:true, SSE-Zeilen loopen."""
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
    with urllib.request.urlopen(req, timeout=600) as r:
        buffer = ""
        while True:
            chunk = r.read(4096).decode("utf-8", errors="replace")
            if not chunk:
                break
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    j = json.loads(data)
                except Exception:
                    continue
                choices = j.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content")
                if content:
                    yield content
        if buffer.strip().startswith("data:"):
            data = buffer[5:].strip()
            if data != "[DONE]":
                try:
                    j = json.loads(data)
                    choices = j.get("choices") or []
                    if choices:
                        delta = choices[0].get("delta") or {}
                        content = delta.get("content")
                        if content:
                            yield content
                except Exception:
                    pass


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

        run_chat_session(m_path, s_prompt, temp, tok, pen, ctx, top_p, top_k)

    # Worker beenden, damit nicht der Fallback-Code unten läuft
    sys.exit(0)


def run_chat_session(model_path, sys_prompt_text, temperature, max_tokens, repeat_penalty, n_ctx, top_p=0.95, top_k=40):
    cpu_count = multiprocessing.cpu_count()
    optimal_threads = max(1, cpu_count - 2)

    print(json.dumps({"sys": f"🧠 Load Model... (GPU: Metal, Threads: {optimal_threads}, Ctx: {n_ctx})"}))
    sys.stdout.flush()

    proc, port = start_server(model_path, n_ctx, optimal_threads)
    if proc is None:
        return
    print(json.dumps({"sys": "✅ READY"}))
    sys.stdout.flush()
    print(json.dumps({"sys": "🌐 Web UI aktiv", "webui_port": port}))
    sys.stdout.flush()

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

    try:
        while True:
            try:
                user_input = sys.stdin.readline()
                if not user_input:
                    break
                user_input = user_input.strip()
                if not user_input:
                    continue

                # --- NEU: SMART RESET LOGIK ---
                if user_input == "__RESET__":
                    history = []  # Gedächtnis löschen
                    print(json.dumps({"sys": "Memory cleared (model stays active) 🧹)."}))
                    sys.stdout.flush()
                    continue  # Nächste Runde warten
                # ------------------------------

                messages = [{"role": "system", "content": final_system_prompt}]

                for msg in history:
                    role = "user" if msg['role'] == "User" else "assistant"
                    messages.append({"role": role, "content": msg['content']})

                messages.append({"role": "user", "content": user_input})

                start_time = time.time()
                token_count = 0
                full_response = ""

                for content in stream_chat(port, messages, int(max_tokens), float(temperature), float(repeat_penalty), float(top_p), int(top_k)):
                    full_response += content
                    token_count += 1

                    elapsed = time.time() - start_time
                    speed = token_count / elapsed if elapsed > 0 else 0
                    stats_text = f"{speed:.1f} T/s | {token_count} Tok"

                    print(json.dumps({"chunk": content, "stats": stats_text}))
                    sys.stdout.flush()

                history.append({"role": "User", "content": user_input})
                history.append({"role": "Assistant", "content": full_response.strip()})

                print(json.dumps({"done": True}))
                sys.stdout.flush()

            except Exception as e:
                print(json.dumps({"error": str(e)}))
                sys.stdout.flush()
    finally:
        stop_server(proc, port)


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