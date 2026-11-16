"""
Lumen – Bildschirm sehen und Maus/Tastatur steuern.

Linux X11:     Screenshot mit mss/scrot/ImageMagick, Steuerung mit xdotool, Fenster mit wmctrl.
Linux Wayland: Screenshot mit grim (Sway/Hyprland), gnome-screenshot oder spectacle (KDE),
               Steuerung mit ydotool (braucht laufenden ydotoold).
Windows/macOS: Screenshot mit mss, Steuerung mit pyautogui (optional).

Screenshots werden auf max. 1280 px Breite verkleinert. Die KI klickt in diesem Raster,
Lumen rechnet die Koordinaten auf die echte Bildschirmgröße um.
"""
import base64
import io
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

OS = platform.system()
MAX_W = 1280
_last = {"scale": 1.0, "offset": (0, 0), "size": None}


def session_type():
    if OS != "Linux":
        return OS.lower()
    t = (os.environ.get("XDG_SESSION_TYPE") or "").lower()
    if t:
        return t
    return "wayland" if os.environ.get("WAYLAND_DISPLAY") else "x11"


def _run(cmd, timeout=15, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kw)


def capabilities():
    st = session_type()
    caps = {"sitzung": st, "screenshot": None, "steuerung": None}
    if OS == "Linux":
        if st == "wayland":
            for tool in ("grim", "gnome-screenshot", "spectacle"):
                if shutil.which(tool):
                    caps["screenshot"] = tool
                    break
            if shutil.which("ydotool"):
                caps["steuerung"] = "ydotool"
        else:
            try:
                import mss  # noqa: F401
                caps["screenshot"] = "mss"
            except Exception:
                for tool in ("scrot", "import", "gnome-screenshot"):
                    if shutil.which(tool):
                        caps["screenshot"] = tool
                        break
            if shutil.which("xdotool"):
                caps["steuerung"] = "xdotool"
    else:
        try:
            import mss  # noqa: F401
            caps["screenshot"] = "mss"
        except Exception:
            pass
        try:
            import pyautogui  # noqa: F401
            caps["steuerung"] = "pyautogui"
        except Exception:
            pass
    try:
        import PIL  # noqa: F401
    except Exception:
        caps["hinweis"] = "Pillow fehlt (pip install pillow)"
    return caps


# ================================================================ screenshot
def _grab_png():
    st = session_type()
    caps = capabilities()
    tool = caps["screenshot"]
    if not tool:
        hint = ("grim, gnome-screenshot oder spectacle" if st == "wayland" else "python3-mss oder scrot")
        raise RuntimeError(f"Kein Screenshot-Werkzeug gefunden ({st}). Installiere {hint} – siehe setup-linux.sh.")
    if tool == "mss":
        import mss
        import mss.tools
        with mss.mss() as s:
            mon = s.monitors[0]  # alle Bildschirme zusammen
            img = s.grab(mon)
            _last["offset"] = (mon["left"], mon["top"])
            return mss.tools.to_png(img.rgb, img.size)
    out = Path(tempfile.gettempdir()) / f"lumen-shot-{os.getpid()}.png"
    out.unlink(missing_ok=True)
    cmd = {"grim": ["grim", str(out)], "gnome-screenshot": ["gnome-screenshot", "-f", str(out)],
           "spectacle": ["spectacle", "-b", "-n", "-f", "-o", str(out)], "scrot": ["scrot", "-o", str(out)],
           "import": ["import", "-window", "root", str(out)]}[tool]
    r = _run(cmd, timeout=20)
    if not out.exists():
        raise RuntimeError(f"Screenshot fehlgeschlagen ({tool}): {r.stderr.strip()[-300:]}")
    _last["offset"] = (0, 0)
    data = out.read_bytes()
    out.unlink(missing_ok=True)
    return data


def screenshot():
    """Gibt (jpeg_base64, breite, höhe, thumb_base64) zurück und merkt sich den Maßstab."""
    png = _grab_png()
    from PIL import Image
    img = Image.open(io.BytesIO(png)).convert("RGB")
    real_w, real_h = img.size
    scale = min(1.0, MAX_W / real_w)
    if scale < 1:
        img = img.resize((round(real_w * scale), round(real_h * scale)), Image.LANCZOS)
    _last["scale"] = scale
    _last["size"] = img.size
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=72)
    thumb = img.copy()
    thumb.thumbnail((420, 420))
    tb = io.BytesIO()
    thumb.save(tb, "JPEG", quality=60)
    return (base64.b64encode(buf.getvalue()).decode(), img.size[0], img.size[1],
            base64.b64encode(tb.getvalue()).decode(), (real_w, real_h))


def _real(x, y):
    s = _last["scale"] or 1.0
    ox, oy = _last["offset"]
    return int(round(float(x) / s)) + ox, int(round(float(y) / s)) + oy


# ================================================================ input backends
# Linux-Eingabecodes für ydotool (Wayland)
KEYCODES = {
    "esc": 1, "escape": 1, "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
    "minus": 12, "equal": 13, "backspace": 14, "tab": 15, "q": 16, "w": 17, "e": 18, "r": 19, "t": 20, "y": 21,
    "u": 22, "i": 23, "o": 24, "p": 25, "enter": 28, "return": 28, "ctrl": 29, "control": 29, "a": 30, "s": 31,
    "d": 32, "f": 33, "g": 34, "h": 35, "j": 36, "k": 37, "l": 38, "shift": 42, "z": 44, "x": 45, "c": 46,
    "v": 47, "b": 48, "n": 49, "m": 50, "comma": 51, "period": 52, "slash": 53, "alt": 56, "space": 57,
    "capslock": 58, "f1": 59, "f2": 60, "f3": 61, "f4": 62, "f5": 63, "f6": 64, "f7": 65, "f8": 66, "f9": 67,
    "f10": 68, "f11": 87, "f12": 88, "home": 102, "up": 103, "pageup": 104, "page_up": 104, "left": 105,
    "right": 106, "end": 107, "down": 108, "pagedown": 109, "page_down": 109, "insert": 110, "delete": 111,
    "super": 125, "meta": 125, "win": 125, "altgr": 100,
}
# xdotool-Schlüsselnamen
XKEYS = {"enter": "Return", "return": "Return", "esc": "Escape", "escape": "Escape", "ctrl": "ctrl",
         "control": "ctrl", "alt": "alt", "shift": "shift", "super": "super", "win": "super", "meta": "super",
         "tab": "Tab", "space": "space", "backspace": "BackSpace", "delete": "Delete", "up": "Up", "down": "Down",
         "left": "Left", "right": "Right", "home": "Home", "end": "End", "pageup": "Prior", "page_up": "Prior",
         "pagedown": "Next", "page_down": "Next", "insert": "Insert", "capslock": "Caps_Lock"}


def _backend():
    b = capabilities()["steuerung"]
    if not b:
        st = session_type()
        need = "ydotool (und ydotoold)" if st == "wayland" else "xdotool"
        raise RuntimeError(f"Maus/Tastatur-Steuerung nicht verfügbar ({st}). Installiere {need} – siehe setup-linux.sh.")
    return b


def _check(r, what):
    if r.returncode != 0:
        msg = (r.stderr or r.stdout).strip()[-300:]
        if "ydotoold" in msg or "socket" in msg.lower():
            msg += " – läuft ydotoold? (sudo systemctl enable --now ydotool  oder  ydotoold &)"
        raise RuntimeError(f"{what} fehlgeschlagen: {msg}")


def mouse(action, x=None, y=None, x2=None, y2=None, amount=3):
    b = _backend()
    if action in ("move", "click", "double_click", "right_click", "middle_click", "drag") and (x is None or y is None):
        raise RuntimeError("x und y fehlen (Koordinaten aus dem letzten Screenshot).")
    if _last["size"] is None and x is not None:
        raise RuntimeError("Mach zuerst einen Screenshot, damit die Koordinaten stimmen.")
    rx, ry = _real(x, y) if x is not None else (None, None)
    amount = max(1, min(int(amount or 3), 30))
    btn = {"click": 1, "double_click": 1, "right_click": 3, "middle_click": 2}

    if b == "xdotool":
        if action in btn:
            cmd = ["xdotool", "mousemove", "--sync", str(rx), str(ry), "click"]
            cmd += ["--repeat", "2", "--delay", "80"] if action == "double_click" else []
            _check(_run(cmd + [str(btn[action])]), "Klick")
        elif action == "move":
            _check(_run(["xdotool", "mousemove", "--sync", str(rx), str(ry)]), "Mausbewegung")
        elif action == "drag":
            ex, ey = _real(x2, y2)
            _check(_run(["xdotool", "mousemove", "--sync", str(rx), str(ry), "mousedown", "1",
                         "mousemove", "--sync", str(ex), str(ey), "mouseup", "1"]), "Ziehen")
        elif action in ("scroll_up", "scroll_down"):
            if rx is not None:
                _run(["xdotool", "mousemove", str(rx), str(ry)])
            _check(_run(["xdotool", "click", "--repeat", str(amount), "4" if action == "scroll_up" else "5"]), "Scrollen")
        else:
            raise RuntimeError("Unbekannte Mausaktion.")
    elif b == "ydotool":
        codes = {"click": "0xC0", "right_click": "0xC1", "middle_click": "0xC2"}

        def move(px, py):
            # erst in die Ecke, dann relativ – robust auch mit Mausbeschleunigung
            _check(_run(["ydotool", "mousemove", "--absolute", "-x", str(px), "-y", str(py)]), "Mausbewegung")
        if action in ("click", "right_click", "middle_click", "double_click"):
            move(rx, ry)
            for _ in range(2 if action == "double_click" else 1):
                _check(_run(["ydotool", "click", codes.get(action, "0xC0")]), "Klick")
                time.sleep(0.08)
        elif action == "move":
            move(rx, ry)
        elif action == "drag":
            ex, ey = _real(x2, y2)
            move(rx, ry)
            _run(["ydotool", "click", "0x40"])
            move(ex, ey)
            _run(["ydotool", "click", "0x80"])
        elif action in ("scroll_up", "scroll_down"):
            if rx is not None:
                move(rx, ry)
            _check(_run(["ydotool", "mousemove", "--wheel", "-x", "0", "-y",
                         str(amount if action == "scroll_up" else -amount)]), "Scrollen")
        else:
            raise RuntimeError("Unbekannte Mausaktion.")
    else:  # pyautogui
        import pyautogui
        if action == "click":
            pyautogui.click(rx, ry)
        elif action == "double_click":
            pyautogui.doubleClick(rx, ry)
        elif action == "right_click":
            pyautogui.rightClick(rx, ry)
        elif action == "middle_click":
            pyautogui.middleClick(rx, ry)
        elif action == "move":
            pyautogui.moveTo(rx, ry)
        elif action == "drag":
            ex, ey = _real(x2, y2)
            pyautogui.moveTo(rx, ry)
            pyautogui.dragTo(ex, ey, duration=0.4)
        elif action in ("scroll_up", "scroll_down"):
            pyautogui.scroll(amount * (120 if action == "scroll_up" else -120), rx, ry)
        else:
            raise RuntimeError("Unbekannte Mausaktion.")
    time.sleep(0.35)
    return f"Maus: {action}" + (f" bei ({round(float(x))}, {round(float(y))})" if x is not None else "")


def type_text(text):
    b = _backend()
    text = str(text)
    if b == "xdotool":
        _check(_run(["xdotool", "type", "--delay", "12", "--", text], timeout=120), "Tippen")
    elif b == "ydotool":
        _check(_run(["ydotool", "type", "--key-delay", "12", "--", text], timeout=120), "Tippen")
    else:
        import pyautogui
        pyautogui.write(text, interval=0.01)
    time.sleep(0.2)
    return f"Getippt: {text[:60]}"


def press_keys(keys):
    """keys z. B. 'ctrl+t', 'enter', 'alt+tab', 'ctrl+shift+esc'."""
    b = _backend()
    combo = [k.strip().lower() for k in re.split(r"[+ ]", str(keys)) if k.strip()]
    if not combo:
        raise RuntimeError("Keine Taste angegeben.")
    if b == "xdotool":
        _check(_run(["xdotool", "key", "--clearmodifiers", "+".join(XKEYS.get(k, k) for k in combo)]), "Tastendruck")
    elif b == "ydotool":
        try:
            codes = [KEYCODES[k] for k in combo]
        except KeyError as e:
            raise RuntimeError(f"Taste {e} wird unter Wayland nicht unterstützt.")
        seq = [f"{c}:1" for c in codes] + [f"{c}:0" for c in reversed(codes)]
        _check(_run(["ydotool", "key"] + seq), "Tastendruck")
    else:
        import pyautogui
        pyautogui.hotkey(*[{"super": "win", "return": "enter"}.get(k, k) for k in combo])
    time.sleep(0.25)
    return f"Tasten: {keys}"


def list_windows():
    if OS == "Linux" and session_type() != "wayland" and shutil.which("wmctrl"):
        r = _run(["wmctrl", "-lx"])
        wins = []
        for line in r.stdout.splitlines():
            parts = line.split(None, 4)
            if len(parts) == 5 and parts[1] != "-1":
                wins.append({"klasse": parts[2].split(".")[-1], "titel": parts[4]})
        return {"fenster": wins}
    if OS == "Linux" and shutil.which("hyprctl"):
        import json
        r = _run(["hyprctl", "clients", "-j"])
        return {"fenster": [{"klasse": c.get("class"), "titel": c.get("title")} for c in json.loads(r.stdout or "[]")]}
    if OS == "Linux" and shutil.which("swaymsg"):
        r = _run(["swaymsg", "-t", "get_tree"])
        titles = re.findall(r'"name":\s*"([^"]+)"', r.stdout)
        return {"fenster": [{"titel": t} for t in titles if t not in ("root", "__i3")][:60]}
    raise RuntimeError("Fensterliste hier nicht verfügbar. Nutze screenshot, um zu sehen, was offen ist.")


def focus_window(name):
    if OS == "Linux" and session_type() != "wayland":
        if shutil.which("wmctrl"):
            r = _run(["wmctrl", "-a", name])
            if r.returncode == 0:
                return f"Fenster '{name}' im Vordergrund."
        if shutil.which("xdotool"):
            r = _run(["xdotool", "search", "--onlyvisible", "--name", name, "windowactivate"])
            if r.returncode == 0:
                return f"Fenster '{name}' im Vordergrund."
        raise RuntimeError(f"Kein Fenster mit '{name}' gefunden.")
    if shutil.which("hyprctl"):
        _check(_run(["hyprctl", "dispatch", "focuswindow", f"title:{name}"]), "Fokus")
        return f"Fenster '{name}' im Vordergrund."
    if shutil.which("swaymsg"):
        _check(_run(["swaymsg", f'[title="(?i){re.escape(name)}"] focus']), "Fokus")
        return f"Fenster '{name}' im Vordergrund."
    raise RuntimeError("Fenster wechseln geht hier nur per Tastenkürzel (z. B. press_keys 'alt+tab') oder Klick.")
