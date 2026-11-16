"""
Lumen – Plugins: eigene Werkzeuge als kleine Python-Dateien in ~/.lumen/plugins/.

Eine Plugin-Datei sieht so aus:

    \"\"\"Würfeln – ein Beispiel-Plugin.\"\"\"
    import random

    def wuerfeln(args):
        n = int(args.get("seiten", 6))
        return {"ergebnis": random.randint(1, n)}

    TOOLS = [{
        "name": "wuerfeln",
        "description": "Würfelt eine Zahl zwischen 1 und seiten.",
        "parameters": {"seiten": {"type": "integer", "description": "Anzahl Seiten (Standard 6)"}},
        "required": [],
        "run": wuerfeln,
        "risky": False,          # True = Lumen fragt vor jeder Ausführung nach
    }]

Lumen kann sich auch selbst Plugins schreiben (create_plugin) – das geht nur, wenn du den Code bestätigst.
"""
import ast
import importlib.util
import re
import shutil
import sys
import threading
import time
import traceback
from pathlib import Path

DIR = Path.home() / ".lumen" / "plugins"
EXAMPLES = Path(__file__).resolve().parent / "plugins_beispiele"
LOCK = threading.Lock()
_state = {"stamp": None, "plugins": [], "tools": []}
RESERVED = set()          # Namen der eingebauten Werkzeuge (setzt lumen.py)
get_disabled = lambda: set()  # noqa: E731  (setzt lumen.py: deaktivierte Plugins)

DANGER = [(r"\bsubprocess\b|os\.system|os\.popen|pty\.", "führt Programme/Befehle aus"),
          (r"shutil\.rmtree|os\.remove|os\.unlink|\.unlink\(|os\.rmdir", "kann Dateien löschen"),
          (r"\bopen\([^)]*['\"][wa]", "schreibt Dateien"),
          (r"urllib|requests|http\.client|socket", "greift aufs Internet/Netzwerk zu"),
          (r"\beval\(|\bexec\(|__import__|compile\(", "führt dynamischen Code aus"),
          (r"\.ssh|\.lumen|config\.json|id_ed25519|id_rsa|keyring|wallet|seed", "berührt Schlüssel/Zugangsdaten"),
          (r"ctypes|sys\.modules", "greift tief ins System ein")]


def ensure_examples():
    """Beim ersten Start die Beispiel-Plugins kopieren."""
    if DIR.exists():
        return
    DIR.mkdir(parents=True, exist_ok=True)
    if EXAMPLES.is_dir():
        for f in EXAMPLES.glob("*.py"):
            shutil.copy2(f, DIR / f.name)


def warnings_for(code):
    return [msg for pat, msg in DANGER if re.search(pat, code)]


def _stamp():
    if not DIR.exists():
        return ()
    return tuple(sorted((f.name, f.stat().st_mtime) for f in DIR.glob("*.py"))) + (tuple(sorted(get_disabled())),)


def _load_file(f):
    name = f"lumen_plugin_{f.stem}"
    spec = importlib.util.spec_from_file_location(name, f)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.pop(name, None)
    spec.loader.exec_module(mod)
    tools = getattr(mod, "TOOLS", None)
    if not isinstance(tools, list) or not tools:
        raise RuntimeError("Die Datei definiert keine TOOLS-Liste.")
    return mod, tools


def _wrap(t, plugin):
    name = str(t.get("name", "")).strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", name):
        raise RuntimeError(f"Ungültiger Werkzeug-Name „{name}“ (nur a–z, 0–9, _).")
    if name in RESERVED:
        raise RuntimeError(f"„{name}“ gibt es schon als eingebautes Werkzeug.")
    run = t.get("run")
    if not callable(run):
        raise RuntimeError(f"Werkzeug „{name}“ hat keine run-Funktion.")
    props = t.get("parameters") or {}
    if props.get("type") == "object":  # auch ein komplettes Schema erlauben
        schema = props
    else:
        schema = {"type": "object", "properties": props, "required": list(t.get("required") or [])}

    def fn(a, run=run, name=name):
        try:
            return run(a or {})
        except Exception as e:
            raise RuntimeError(f"Plugin {plugin}/{name}: {e}")

    out = dict(name=name, fn=fn, label=lambda a, n=name: f"🧩 {n}", description=f"[Plugin {plugin}] " + str(t.get("description", ""))[:900],
               schema=schema, plugin=plugin)
    if t.get("risky"):
        out["confirm"] = lambda a, n=name: (f"Plugin-Werkzeug {n} ausführen", str(a)[:600])
    return out


def reload(force=False):
    with LOCK:
        st = _stamp()
        if not force and st == _state["stamp"]:
            return _state
        plugins, tools, seen = [], [], set()
        off = get_disabled()
        for f in sorted(DIR.glob("*.py")) if DIR.exists() else []:
            info = {"datei": f.name, "name": f.stem, "an": f.stem not in off, "werkzeuge": [], "fehler": None,
                    "beschreibung": "", "geändert": f.stat().st_mtime}
            try:
                src = f.read_text("utf-8")
                info["warnungen"] = warnings_for(src)
                doc = ast.get_docstring(ast.parse(src)) or ""
                info["beschreibung"] = doc.strip().splitlines()[0][:200] if doc.strip() else ""
                if info["an"]:
                    _, raw = _load_file(f)
                    for t in raw:
                        w = _wrap(t, f.stem)
                        if w["name"] in seen:
                            raise RuntimeError(f"Werkzeug „{w['name']}“ gibt es in einem anderen Plugin schon.")
                        seen.add(w["name"])
                        tools.append(w)
                        info["werkzeuge"].append(w["name"])
            except Exception as e:
                info["fehler"] = f"{type(e).__name__}: {e}"
                info["trace"] = traceback.format_exc()[-1500:]
            plugins.append(info)
        _state.update(stamp=st, plugins=plugins, tools=tools)
        return _state


def tools():
    try:
        return reload()["tools"]
    except Exception:
        return []


def listing():
    return reload()["plugins"]


def validate(name, code):
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", name or ""):
        raise RuntimeError("Plugin-Name: nur Kleinbuchstaben, Zahlen und _ (z. B. wetter_alarm).")
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise RuntimeError(f"Syntaxfehler in Zeile {e.lineno}: {e.msg}")
    if not any(isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "TOOLS" for t in n.targets) for n in tree.body):
        raise RuntimeError("Der Code muss eine Liste TOOLS = [...] definieren (siehe Plugin-Format).")
    return True


def write(name, code):
    validate(name, code)
    DIR.mkdir(parents=True, exist_ok=True)
    path = DIR / f"{name}.py"
    backup = path.read_text("utf-8") if path.exists() else None
    path.write_text(code, "utf-8")
    st = reload(force=True)
    info = next((p for p in st["plugins"] if p["name"] == name), None)
    if info and info["fehler"]:
        if backup is not None:  # kaputte neue Version → alte zurück, Fehler melden
            path.write_text(backup, "utf-8")
        else:
            path.rename(path.with_suffix(".py.kaputt"))
        reload(force=True)
        raise RuntimeError(f"Plugin lädt nicht: {info['fehler']}\n{info.get('trace', '')[-600:]}")
    return info


def delete(name):
    p = DIR / f"{Path(name).stem}.py"
    if p.exists():
        trash = DIR / ".papierkorb"
        trash.mkdir(exist_ok=True)
        p.rename(trash / f"{p.stem}-{int(time.time())}.py")
    reload(force=True)
    return True


FORMAT_HELP = '''Plugin-Format (Python, nur Standardbibliothek oder bereits installierte Pakete):

"""Kurze Beschreibung in einer Zeile."""
import json

def mein_werkzeug(args):            # args = dict mit den Parametern
    stadt = args.get("stadt", "Berlin")
    return {"ergebnis": "..."}       # dict, Liste oder Text – geht an dich (die KI) zurück

TOOLS = [{
    "name": "mein_werkzeug",         # a–z, 0–9, _
    "description": "Was es tut und wann man es benutzt.",
    "parameters": {"stadt": {"type": "string", "description": "…"}},
    "required": ["stadt"],
    "run": mein_werkzeug,
    "risky": False,                  # True, wenn es etwas verändert/löscht/sendet → Lumen fragt jedes Mal
}]
Regeln: keine Zugangsdaten, Keys oder Seed-Phrasen auslesen; Netzwerk nur wenn nötig (urllib.request);
Fehler mit raise RuntimeError("verständliche Meldung"); Zeitlimits bei Netzwerkzugriffen (timeout=15).'''
