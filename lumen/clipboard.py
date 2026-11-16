"""
Lumen – Zwischenablage-Helfer. Text markieren/kopieren → Tastenkürzel → übersetzt, verbessert, erklärt …
Das Ergebnis landet wieder in der Zwischenablage (Strg+V) und als Benachrichtigung.

Tastenkürzel:
  • X11: Lumen lauscht selbst (pynput), Standard Strg+Alt+L = Menü, Strg+Alt+Ü = übersetzen, Strg+Alt+K = verbessern
  • Wayland/alle: Lumen trägt Kürzel in GNOME/KDE ein, die lumen-clip.sh aufrufen (Knopf in der App)
"""
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

ACTIONS = {
    # id: (Bezeichnung, Emoji, Auftrag)
    "uebersetzen": ("Übersetzen", "🌍", "Übersetze den Text. Ist er Deutsch → ins Englische, sonst → ins {lang}. Nur die Übersetzung ausgeben, "
                                          "Ton und Formatierung beibehalten."),
    "verbessern": ("Verbessern", "✨", "Korrigiere Rechtschreibung, Grammatik und Zeichensetzung und mach den Text flüssiger – Sprache, Bedeutung "
                                      "und Ton beibehalten. Nur den verbesserten Text ausgeben."),
    "erklaeren": ("Erklären", "💡", "Erkläre kurz und verständlich, was das bedeutet bzw. was gemeint ist (bei Code: was er tut; bei Fehlermeldungen: "
                                   "Ursache und Lösung). Auf {lang}, max. 8 Sätze."),
    "zusammenfassen": ("Zusammenfassen", "📝", "Fasse den Text in 3–6 Stichpunkten auf {lang} zusammen. Nur die Stichpunkte."),
    "antworten": ("Antwort schreiben", "💬", "Das ist eine Nachricht/Mail an mich. Schreibe eine passende, freundliche Antwort in derselben "
                                            "Sprache und im passenden Ton (du/Sie wie im Original). Nur die Antwort."),
    "formell": ("Formeller", "👔", "Schreibe den Text höflich und formell (Sie-Form, wenn Deutsch). Gleiche Sprache. Nur den Text."),
    "lockerer": ("Lockerer", "😎", "Schreibe den Text locker und freundlich. Gleiche Sprache. Nur den Text."),
    "kuerzer": ("Kürzer", "✂️", "Kürze den Text auf das Wesentliche (etwa halb so lang). Gleiche Sprache. Nur den Text."),
    "code": ("Code verbessern", "🧑‍💻", "Verbessere bzw. repariere diesen Code. Nur den Code ausgeben, ohne Markdown-Zäune."),
}
DEFAULT_KEYS = {"menu": "<ctrl>+<alt>+l", "uebersetzen": "<ctrl>+<alt>+ü", "verbessern": "<ctrl>+<alt>+k"}
HISTORY = []
STATE = {"hotkeys": "aus", "fehler": None, "busy": False}
_listener = None


def wayland():
    return bool(os.environ.get("WAYLAND_DISPLAY")) or os.environ.get("XDG_SESSION_TYPE") == "wayland"


def get_text(primary=False):
    cmds = []
    if wayland() and shutil.which("wl-paste"):
        cmds.append(["wl-paste", "-n"] + (["-p"] if primary else []))
    if shutil.which("xclip"):
        cmds.append(["xclip", "-o", "-selection", "primary" if primary else "clipboard"])
    if shutil.which("xsel"):
        cmds.append(["xsel", "-o", "-p" if primary else "-b"])
    for c in cmds:
        try:
            r = subprocess.run(c, capture_output=True, timeout=3)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.decode("utf-8", "replace")
        except Exception:
            pass
    return ""


def set_text(text):
    cmds = []
    if wayland() and shutil.which("wl-copy"):
        cmds.append(["wl-copy"])
    if shutil.which("xclip"):
        cmds.append(["xclip", "-selection", "clipboard"])
    if shutil.which("xsel"):
        cmds.append(["xsel", "-b", "-i"])
    for c in cmds:
        try:
            p = subprocess.Popen(c, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            p.stdin.write(text.encode())
            p.stdin.close()
            return True
        except Exception:
            pass
    return False


def available():
    tools = [t for t in ("wl-paste", "wl-copy", "xclip", "xsel") if shutil.which(t)]
    return {"werkzeuge": tools, "ok": bool(tools), "wayland": wayland(),
            "hinweis": None if tools else ("Für die Zwischenablage fehlt ein Werkzeug: sudo apt install " + ("wl-clipboard" if wayland() else "xclip"))}


def notify(title, body):
    if shutil.which("notify-send"):
        try:
            subprocess.Popen(["notify-send", "-a", "Lumen", "-t", "9000", title, body[:400]])
        except Exception:
            pass


def choose_action():
    """Kleines Auswahlmenü (rofi/wofi/zenity/kdialog)."""
    items = [f"{e} {l}" for l, e, _ in ACTIONS.values()]
    keys = list(ACTIONS)
    for cmd in (["rofi", "-dmenu", "-i", "-p", "Lumen"], ["wofi", "--dmenu", "-p", "Lumen"], ["fuzzel", "--dmenu"],
                ["zenity", "--list", "--title=Lumen", "--column=Was soll Lumen tun?", "--hide-header", "--width=320", "--height=420"] + items,
                ["kdialog", "--menu", "Was soll Lumen tun?"] + sum([[str(i), it] for i, it in enumerate(items)], [])):
        if not shutil.which(cmd[0]):
            continue
        try:
            stdin = "\n".join(items).encode() if cmd[0] in ("rofi", "wofi", "fuzzel") else None
            r = subprocess.run(cmd, input=stdin, capture_output=True, timeout=60)
            out = r.stdout.decode().strip()
            if not out:
                return None
            if cmd[0] == "kdialog":
                return keys[int(out)]
            return keys[items.index(out)] if out in items else None
        except Exception:
            continue
    return "uebersetzen"


def run(action, text, complete, lang="Deutsche", paste=False):
    """complete(system, prompt) → Text. Gibt das Ergebnis zurück und legt es in die Zwischenablage."""
    if action not in ACTIONS:
        raise RuntimeError("Unbekannte Aktion.")
    text = (text or "").strip()
    if not text:
        raise RuntimeError("Die Zwischenablage ist leer – erst Text markieren oder kopieren.")
    if len(text) > 30000:
        text = text[:30000]
    label, emoji, task = ACTIONS[action]
    STATE["busy"] = True
    try:
        out = complete("Du bist ein präziser Text-Assistent. Gib ausschließlich das Ergebnis aus – keine Einleitung, keine Anführungszeichen.",
                       task.format(lang=lang) + "\n\nTEXT:\n" + text).strip()
    finally:
        STATE["busy"] = False
    if out.startswith("```") and out.endswith("```"):
        out = out.strip("`").split("\n", 1)[-1]
    set_text(out)
    HISTORY.insert(0, {"aktion": action, "label": f"{emoji} {label}", "vorher": text[:4000], "nachher": out, "zeit": time.time()})
    del HISTORY[20:]
    notify(f"Lumen · {emoji} {label}", out + "\n\n(In der Zwischenablage – Strg+V)")
    if paste:
        time.sleep(0.15)
        if shutil.which("xdotool") and not wayland():
            subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"], timeout=5)
        elif shutil.which("ydotool"):
            subprocess.run(["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], timeout=5)
    return out


def trigger(action, complete, lang, paste=False):
    """Vom Tastenkürzel: markierter Text (PRIMARY) bevorzugt, sonst Zwischenablage."""
    def work():
        try:
            if STATE["busy"]:
                return notify("Lumen", "Bin noch beschäftigt …")
            a = action
            if a == "menu":
                a = choose_action()
                if not a:
                    return
            text = get_text(primary=True) or get_text()
            notify("Lumen", f"{ACTIONS[a][1]} {ACTIONS[a][0]} …")
            run(a, text, complete, lang, paste)
        except Exception as e:
            STATE["fehler"] = str(e)
            notify("Lumen – Fehler", str(e))
    threading.Thread(target=work, daemon=True).start()


def start_hotkeys(keys, handler):
    """X11: globale Tastenkürzel über pynput. handler(action)."""
    global _listener
    stop_hotkeys()
    if wayland():
        STATE["hotkeys"], STATE["fehler"] = "wayland", "Unter Wayland: Kürzel über GNOME/KDE eintragen (Knopf „Kürzel einrichten“)."
        return False
    try:
        from pynput import keyboard
    except ImportError:
        STATE["hotkeys"], STATE["fehler"] = "fehlt", "pynput fehlt (pip install pynput) – oder Kürzel über die Desktop-Einstellungen."
        return False
    try:
        mapping = {}
        for action, combo in keys.items():
            if combo:
                mapping[combo] = (lambda a=action: handler(a))
        _listener = keyboard.GlobalHotKeys(mapping)
        _listener.daemon = True
        _listener.start()
        STATE["hotkeys"], STATE["fehler"] = "an", None
        return True
    except Exception as e:
        STATE["hotkeys"], STATE["fehler"] = "fehler", f"Tastenkürzel nicht möglich: {e}"
        return False


def stop_hotkeys():
    global _listener
    if _listener:
        try:
            _listener.stop()
        except Exception:
            pass
    _listener = None
    STATE["hotkeys"] = "aus"


def write_cli(app_dir, data_dir):
    """lumen-clip.sh: für Desktop-Tastenkürzel (auch Wayland)."""
    p = Path(data_dir) / "lumen-clip.sh"
    p.write_text(f'''#!/bin/sh
# Lumen-Zwischenablage: lumen-clip.sh [menu|uebersetzen|verbessern|erklaeren|zusammenfassen|antworten|formell|lockerer|kuerzer|code]
A="${{1:-menu}}"
T=$(cat "{data_dir}/token" 2>/dev/null); P=$(cat "{data_dir}/port" 2>/dev/null || echo 8765)
curl -s -m 5 -H "x-lumen-token: $T" -H "content-type: application/json" -d "{{\\"action\\":\\"$A\\",\\"trigger\\":true}}" "http://127.0.0.1:$P/api/clip" >/dev/null \\
  || notify-send "Lumen" "Lumen läuft nicht – bitte starten."
''', "utf-8")
    p.chmod(0o755)
    return p


def register_desktop_shortcuts(script, keys_human):
    """Trägt Kürzel in GNOME (gsettings) bzw. KDE (kglobalaccel über khotkeys ist komplex → Hinweis) ein."""
    done = []
    if shutil.which("gsettings") and "gnome" in (os.environ.get("XDG_CURRENT_DESKTOP", "").lower() + os.environ.get("DESKTOP_SESSION", "").lower()):
        base = "org.gnome.settings-daemon.plugins.media-keys"
        cur = subprocess.run(["gsettings", "get", base, "custom-keybindings"], capture_output=True, text=True).stdout.strip()
        paths = [x.strip(" '") for x in cur.strip("@as []").split(",") if x.strip(" '")]
        for action, accel in keys_human.items():
            path = f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/lumen-{action}/"
            if path not in paths:
                paths.append(path)
            schema = f"{base}.custom-keybinding:{path}"
            subprocess.run(["gsettings", "set", schema, "name", f"Lumen {action}"])
            subprocess.run(["gsettings", "set", schema, "command", f"{script} {action}"])
            subprocess.run(["gsettings", "set", schema, "binding", accel])
            done.append(f"{accel} → {action}")
        subprocess.run(["gsettings", "set", base, "custom-keybindings", str(paths)])
        return {"ok": True, "desktop": "GNOME", "kürzel": done}
    return {"ok": False, "hinweis": f"Bitte in den System-Einstellungen → Tastatur → Eigene Kürzel anlegen: Befehl „{script} menu“ "
                                    f"(und z. B. „{script} uebersetzen“)."}
