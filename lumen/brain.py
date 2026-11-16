"""
Lumen – eigene KI ("KI-Labor").

1. Eigenes Lumen-Modell: Ollama-Modell "lumen" auf Basis einer freien KI, mit Persönlichkeit & Wissen.
2. Training: Datensatz aus euren Chats (👍/👎) → LoRA-Feintuning mit Unsloth (train_lora.py) → "lumen-trained".
3. Auto-Modus: Einfaches lokal (kostenlos), Schweres in der Cloud.
4. Mini-KI: winziges GPT von null (mini_gpt.py) – zum Verstehen, wie KI funktioniert.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
LAB = Path.home() / ".lumen" / "lab"
TRAIN_VENV = APP_DIR / ".venv-train"

BASES = {  # Ollama-Basismodelle für "lumen"
    "qwen2.5:7b": "Qwen 2.5 7B – Allrounder, sehr gut auf Deutsch, Werkzeuge (≈ 5 GB)",
    "qwen3:8b": "Qwen 3 8B – neuer, denkt mit, Werkzeuge (≈ 5 GB)",
    "llama3.1:8b": "Llama 3.1 8B – Meta, solide, Werkzeuge (≈ 5 GB)",
    "qwen2.5vl:7b": "Qwen 2.5 VL 7B – kann zusätzlich Bilder/Bildschirm sehen (≈ 6 GB)",
    "qwen2.5:3b": "Qwen 2.5 3B – klein & schnell, für schwächere PCs (≈ 2 GB)",
}
TRAIN_BASES = {  # Unsloth-4bit-Modelle → passendes Ollama-Basismodell (für Chat-Vorlage)
    "unsloth/Qwen2.5-3B-Instruct-bnb-4bit": ("qwen2.5:3b", "qwen-2.5", "3B – schnell, ab 6 GB Grafikspeicher"),
    "unsloth/Qwen2.5-7B-Instruct-bnb-4bit": ("qwen2.5:7b", "qwen-2.5", "7B – beste Qualität für 8–12 GB"),
    "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit": ("llama3.1:8b", "llama-3.1", "Llama 8B – ab 10 GB"),
}


# ================================================================ helpers
def _ollama(url, path, body=None, timeout=30, stream=False):
    req = urllib.request.Request(url.rstrip("/") + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")
        try:
            msg = json.loads(msg).get("error", msg)
        except Exception:
            pass
        raise RuntimeError(f"Ollama: {msg}")
    except urllib.error.URLError:
        raise RuntimeError("Ollama läuft nicht. Installieren: curl -fsSL https://ollama.com/install.sh | sh  – dann 'ollama serve'.")
    if stream:
        return r
    with r:
        data = r.read()
    return json.loads(data) if data else {}


def ollama_models(url):
    try:
        return [m["name"] for m in _ollama(url, "/api/tags", timeout=5).get("models", [])]
    except Exception:
        return None


def gpu_info():
    if not shutil.which("nvidia-smi"):
        return {"ok": False, "hinweis": "Keine NVIDIA-Grafikkarte gefunden (nvidia-smi fehlt). Treiber installiert?"}
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=10)
        name, total, used, drv = [x.strip() for x in r.stdout.splitlines()[0].split(",")]
        gb = round(int(total) / 1024, 1)
        return {"ok": True, "name": name, "vram_gb": gb, "belegt_gb": round(int(used) / 1024, 1), "treiber": drv,
                "empfehlung": "unsloth/Qwen2.5-7B-Instruct-bnb-4bit" if gb >= 8 else "unsloth/Qwen2.5-3B-Instruct-bnb-4bit"}
    except Exception as e:
        return {"ok": False, "hinweis": f"nvidia-smi: {e}"}


# ================================================================ background tasks
class Task:
    def __init__(self, name, title):
        self.name, self.title = name, title
        self.status = "läuft"      # läuft | fertig | fehler | abgebrochen
        self.progress = None       # 0..1
        self.detail = ""
        self.log = []
        self.started = time.time()
        self.proc = None
        self.result = None
        self.loss = []
        self.steps = None          # [{"name":…, "status": "offen|läuft|fertig|fehler|übersprungen"}]

    def add(self, line):
        line = line.rstrip()
        if not line:
            return
        m = re.search(r"PROGRESS (\d+)/(\d+)", line)
        if m:
            self.progress = int(m.group(1)) / max(1, int(m.group(2)))
            self.detail = f"Schritt {m.group(1)} von {m.group(2)}"
        m = re.search(r"LOSS ([\d.]+)", line)
        if m:
            self.loss.append(round(float(m.group(1)), 4))
            self.loss = self.loss[-300:]
        m = re.search(r"STATUS (.+)", line)
        if m:
            self.detail = m.group(1)
        self.log.append(line[:400])
        self.log = self.log[-300:]

    def view(self):
        return {"name": self.name, "titel": self.title, "status": self.status, "fortschritt": self.progress,
                "detail": self.detail, "log": self.log[-40:], "loss": self.loss[-120:], "result": self.result,
                "minuten": round((time.time() - self.started) / 60, 1), "schritte": self.steps}


TASKS = {}


def run_task(name, title, cmd, env=None, cwd=None, on_done=None):
    if name in TASKS and TASKS[name].status == "läuft":
        raise RuntimeError(f"„{TASKS[name].title}“ läuft schon.")
    t = Task(name, title)
    TASKS[name] = t

    def work():
        try:
            t.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                                      env={**os.environ, "PYTHONUNBUFFERED": "1", **(env or {})}, cwd=cwd)
            for line in t.proc.stdout:
                for part in line.replace("\r", "\n").split("\n"):
                    t.add(part)
            rc = t.proc.wait()
            if t.status == "abgebrochen":
                return
            if rc == 0:
                t.status, t.progress = "fertig", 1.0
                if on_done:
                    t.result = on_done(t)
            else:
                t.status = "fehler"
                t.detail = next((l for l in reversed(t.log) if re.search(r"error|fehler|Error|Exception", l)), f"Exit-Code {rc}")
        except Exception as e:
            t.status, t.detail = "fehler", str(e)
    threading.Thread(target=work, daemon=True).start()
    return t


def run_py_task(name, title, fn):
    """Python-Funktion im Hintergrund, fn(task) darf task.add('PROGRESS …') nutzen."""
    if name in TASKS and TASKS[name].status == "läuft":
        raise RuntimeError(f"„{TASKS[name].title}“ läuft schon.")
    t = Task(name, title)
    TASKS[name] = t

    def work():
        try:
            t.result = fn(t)
            if t.status != "abgebrochen":
                t.status, t.progress = "fertig", 1.0
        except Exception as e:
            if t.status != "abgebrochen":
                t.status, t.detail = "fehler", str(e)
        for st in t.steps or []:
            if st["status"] == "läuft":
                st["status"] = "abgebrochen" if t.status == "abgebrochen" else "fehler"
    threading.Thread(target=work, daemon=True).start()
    return t


def cancel(name):
    t = TASKS.get(name)
    if t and t.status == "läuft":
        t.status = "abgebrochen"
        if t.proc and t.proc.poll() is None:
            t.proc.terminate()
    return True


# ================================================================ 1. eigenes Lumen-Modell
def pull_model(url, model):
    def fn(t):
        t.add(f"STATUS Lade {model} herunter …")
        r = _ollama(url, "/api/pull", {"model": model, "name": model, "stream": True}, timeout=3600, stream=True)
        with r:
            for raw in r:
                try:
                    ev = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if ev.get("error"):
                    raise RuntimeError(ev["error"])
                if ev.get("total") and ev.get("completed") is not None:
                    t.progress = ev["completed"] / ev["total"]
                    t.detail = f"{ev.get('status', '')} · {ev['completed'] / 1e9:.1f} / {ev['total'] / 1e9:.1f} GB"
                elif ev.get("status"):
                    t.detail = ev["status"]
                    t.add(ev["status"])
        return model
    return run_py_task("pull", f"{model} herunterladen", fn)


def build_lumen_model(url, base, system, name="lumen", temperature=0.7, ctx=16384):
    if not re.fullmatch(r"[\w.\-:/]+", base or "") or not re.fullmatch(r"[\w.\-]+", name):
        raise RuntimeError("Ungültiger Modellname.")
    models = ollama_models(url)
    if models is None:
        raise RuntimeError("Ollama läuft nicht.")
    if base not in models and base + ":latest" not in models:
        raise RuntimeError(f"Basismodell {base} ist noch nicht geladen – zuerst herunterladen.")
    LAB.mkdir(parents=True, exist_ok=True)
    modelfile = f'FROM {base}\nPARAMETER temperature {temperature}\nPARAMETER num_ctx {int(ctx)}\nSYSTEM """{system.replace(chr(34) * 3, "")}"""\n'
    (LAB / f"Modelfile.{name}").write_text(modelfile, "utf-8")
    try:  # neue Ollama-API
        _ollama(url, "/api/create", {"model": name, "from": base, "system": system,
                                    "parameters": {"temperature": temperature, "num_ctx": int(ctx)}, "stream": False}, timeout=600)
    except RuntimeError as e:
        if not shutil.which("ollama"):
            raise RuntimeError(f"Modell konnte nicht erstellt werden: {e}")
        r = subprocess.run(["ollama", "create", name, "-f", str(LAB / f"Modelfile.{name}")], capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip()[-300:] or "ollama create fehlgeschlagen")
    return {"modell": name, "basis": base, "erstellt": datetime.now().strftime("%d.%m.%Y %H:%M")}


# ================================================================ 3. Auto-Modus (Router)
HARD = re.compile(r"recherch|analysier|vergleich|ausführlich|detailliert|programmier|\bcode\b|skript|script|python|javascript|"
                  r"debug|fehler im|log|stacktrace|bildschirm|screenshot|klick|maus|ssh|server|docker|container|phishing|"
                  r"mail prüfen|ist diese mail|vertrag|rechtlich|steuer|bewerbung|übersetz.*(text|dokument)|zusammenfass|"
                  r"plan(e|ung)|strategie|warum genau|beweis|mathe|rechne.*(aus|genau)|excel|tabelle|ssl|dns|port|nmap|"
                  r"wallet|krypto|transaktion|github|issue|pull request|home assistant", re.I)
EASY = re.compile(r"^(hi|hallo|hey|moin|servus|danke|ok|okay|super|gut|cool|guten (morgen|abend|tag)|wie geht'?s)\b|"
                  r"öffne|starte|spiel |play|pause|nächste[rs]? (song|lied)|lauter|leiser|wetter|wie spät|uhrzeit|"
                  r"timer|erinner|notiz|aufgabe|witz|wer bist du", re.I)


def route(history, mode=None):
    """→ ('lokal'|'cloud', Grund)"""
    if mode in ("research", "protocol"):
        return "cloud", "Recherche/Protokoll"
    last = next((m for m in reversed(history) if m.get("role") == "user"), {})
    text = str(last.get("content", ""))
    atts = last.get("attachments") or []
    if any((a or {}).get("kind") in ("image", "pdf", "office") for a in atts):
        return "cloud", "Datei/Bild"
    if len(text) > 700:
        return "cloud", "lange Nachricht"
    if HARD.search(text):
        return "cloud", "anspruchsvolle Aufgabe"
    if EASY.search(text) or len(text) < 160:
        return "lokal", "einfach"
    return "lokal", "Standard"


def is_weak_answer(text):
    t = (text or "").strip().lower()
    return len(t) < 2 or bool(re.search(r"ich (weiß|kann) (das )?(leider )?nicht|i (don't|cannot|can't) |als ki(-sprachmodell)? kann ich", t))


# ================================================================ 2. Datensatz & Training
def export_dataset(chats_dir, system_text, memory=None, min_len=2, write=True):
    LAB.mkdir(parents=True, exist_ok=True)
    out, stats = [], {"chats": 0, "beispiele": 0, "gute": 0, "schlechte_entfernt": 0, "zeichen": 0}
    for p in sorted(Path(chats_dir).glob("*.json")):
        try:
            chat = json.loads(p.read_text("utf-8"))
        except Exception:
            continue
        msgs = []
        for m in chat.get("messages", []):
            if m.get("role") not in ("user", "assistant") or m.get("mode") in ("protocol",):
                continue
            c = re.sub(r"^\[per Sprache\] ", "", str(m.get("content", ""))).strip()
            if not c or "DATEIINHALT" in c:
                continue
            if m["role"] == "assistant" and m.get("rating") == "down":
                stats["schlechte_entfernt"] += 1
                if msgs and msgs[-1]["role"] == "user":
                    msgs.pop()
                continue
            if m["role"] == "assistant" and m.get("rating") == "up":
                stats["gute"] += 1
            if msgs and msgs[-1]["role"] == m["role"]:
                msgs[-1]["content"] += "\n\n" + c
            else:
                msgs.append({"role": m["role"], "content": c[:6000]})
        if len(msgs) < min_len:
            continue
        stats["chats"] += 1
        # in Fenster von max. 6 Nachrichten schneiden
        i = 0
        while i < len(msgs):
            win = msgs[i:i + 6]
            while win and win[0]["role"] != "user":
                win = win[1:]
            while win and win[-1]["role"] != "assistant":
                win = win[:-1]
            if len(win) >= 2:
                good = any(m.get("content") for m in win)
                if good:
                    out.append({"messages": [{"role": "system", "content": system_text}] + win})
                    stats["zeichen"] += sum(len(m["content"]) for m in win)
            i += 4
    if memory:
        facts = "\n".join(f"- {m}" for m in memory[:60])
        out.append({"messages": [{"role": "system", "content": system_text},
                                 {"role": "user", "content": "Was weißt du alles über mich?"},
                                 {"role": "assistant", "content": f"Das hab ich mir über dich gemerkt:\n{facts}"}]})
    if not write:
        stats["beispiele"] = len(out)
        return stats
    extra = load_examples()
    stats["extra"] = {}
    for ex in extra:
        out.append({"messages": [{"role": "system", "content": system_text}] + ex["messages"]})
        stats["extra"][ex.get("quelle", "?")] = stats["extra"].get(ex.get("quelle", "?"), 0) + 1
    path = LAB / "dataset.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for ex in out:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    stats["beispiele"] = len(out)
    stats["datei"] = str(path)
    stats["bewertung"] = ("zu wenig – Lumen lernt dabei kaum etwas (ab ca. 100 Beispielen sinnvoll, ab 500 richtig gut)"
                          if len(out) < 100 else "okay" if len(out) < 500 else "gut")
    return stats


def mini_corpus(chats_dir):
    """Text für die Mini-KI: eure Chats + eigene .txt-Dateien in ~/.lumen/lab/mini_texte/."""
    parts = []
    for p in sorted(Path(chats_dir).glob("*.json")):
        try:
            for m in json.loads(p.read_text("utf-8")).get("messages", []):
                c = re.sub(r"^\[per Sprache\] ", "", str(m.get("content", ""))).strip()
                if c and "DATEIINHALT" not in c:
                    parts.append(("Du: " if m.get("role") == "user" else "Lumen: ") + c)
        except Exception:
            continue
    extra = LAB / "mini_texte"
    extra.mkdir(parents=True, exist_ok=True)
    for p in sorted(extra.glob("*.txt")):
        parts.append(p.read_text("utf-8", errors="replace"))
    text = "\n\n".join(parts)
    path = LAB / "mini_corpus.txt"
    path.write_text(text, "utf-8")
    return path, len(text)


def train_python():
    py = TRAIN_VENV / "bin" / "python"
    return str(py) if py.exists() else None


def install_training_env():
    if not shutil.which("nvidia-smi"):
        raise RuntimeError("Für das Training wird eine NVIDIA-Grafikkarte mit Treiber gebraucht.")
    script = (f'set -e; python3 -m venv "{TRAIN_VENV}"; "{TRAIN_VENV}/bin/pip" install -U pip; '
              f'"{TRAIN_VENV}/bin/pip" install unsloth; "{TRAIN_VENV}/bin/python" -c "import torch;'
              f'print(\'STATUS GPU bereit:\', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else \'\')"')
    return run_task("install", "Trainings-Umgebung installieren (ca. 5–8 GB)", ["bash", "-c", script])


def start_training(base, epochs, name, ollama_url, on_done=None):
    py = train_python()
    if not py:
        raise RuntimeError("Zuerst die Trainings-Umgebung installieren.")
    if base not in TRAIN_BASES:
        raise RuntimeError("Unbekanntes Basismodell.")
    data = LAB / "dataset.jsonl"
    if not data.exists() or data.stat().st_size < 200:
        raise RuntimeError("Zuerst den Datensatz erstellen.")
    ollama_base, template, _ = TRAIN_BASES[base]
    out = LAB / "training" / datetime.now().strftime("%Y%m%d-%H%M")
    cmd = [py, str(APP_DIR / "train_lora.py"), "--data", str(data), "--base", base, "--template", template,
           "--epochs", str(max(1, min(int(epochs), 5))), "--out", str(out), "--name", name,
           "--ollama-base", ollama_base, "--ollama-url", ollama_url]
    return run_task("train", f"Training von „{name}“", cmd, on_done=on_done)


def start_mini(steps, size):
    py = train_python()
    if not py:
        raise RuntimeError("Zuerst die Trainings-Umgebung installieren (bringt PyTorch mit).")
    return run_task("mini", "Mini-KI trainieren", [py, str(APP_DIR / "mini_gpt.py"), "train", "--corpus", str(LAB / "mini_corpus.txt"),
                                                   "--out", str(LAB / "mini"), "--steps", str(int(steps)), "--size", size])


def mini_sample(prompt, length=400, temp=0.8):
    py = train_python()
    if not py or not (LAB / "mini" / "ckpt.pt").exists():
        raise RuntimeError("Die Mini-KI ist noch nicht trainiert.")
    r = subprocess.run([py, str(APP_DIR / "mini_gpt.py"), "sample", "--out", str(LAB / "mini"), "--prompt", prompt[:300],
                        "--length", str(int(length)), "--temp", str(float(temp))], capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[-300:] or "Mini-KI-Fehler")
    return r.stdout.split("<<<TEXT>>>", 1)[-1].strip()


def lab_state(url, chats_dir):
    models = ollama_models(url)
    n_chats = len(list(Path(chats_dir).glob("*.json"))) if Path(chats_dir).exists() else 0
    rated = {"up": 0, "down": 0}
    for p in Path(chats_dir).glob("*.json") if Path(chats_dir).exists() else []:
        try:
            for m in json.loads(p.read_text("utf-8")).get("messages", []):
                if m.get("rating") in rated:
                    rated[m["rating"]] += 1
        except Exception:
            pass
    ds = LAB / "dataset.jsonl"
    mini = LAB / "mini" / "meta.json"
    return {"ollama": models is not None, "modelle": models or [], "basen": BASES, "train_basen": {k: v[2] for k, v in TRAIN_BASES.items()},
            "gpu": gpu_info(), "train_env": bool(train_python()), "chats": n_chats, "bewertungen": rated,
            "datensatz": {"beispiele": sum(1 for _ in open(ds, encoding="utf-8")) if ds.exists() else 0,
                          "stand": datetime.fromtimestamp(ds.stat().st_mtime).strftime("%d.%m. %H:%M") if ds.exists() else None},
            "mini": json.loads(mini.read_text()) if mini.exists() else None,
            "tasks": {k: v.view() for k, v in TASKS.items()}}


# ================================================================ Beispiele (Korrekturen, Lehrer-KI, von der Cloud gelernt)
EXAMPLES = LAB / "examples.jsonl"
STATE = LAB / "state.json"
SOURCES = {"chat": "Chats (👍 & normale)", "korrektur": "Von dir verbessert ✏️", "cloud": "Von der Cloud gelernt ☁️",
           "lehrer": "Lehrer-KI 🎓", "wissen": "Aus deinen Dokumenten 📚"}


def add_example(messages, source):
    msgs = [{"role": m["role"], "content": str(m["content"]).strip()[:6000]} for m in messages
            if m.get("role") in ("user", "assistant") and str(m.get("content", "")).strip()]
    if len(msgs) < 2 or msgs[0]["role"] != "user" or msgs[-1]["role"] != "assistant":
        return False
    LAB.mkdir(parents=True, exist_ok=True)
    with open(EXAMPLES, "a", encoding="utf-8") as f:
        f.write(json.dumps({"messages": msgs, "quelle": source, "zeit": time.time()}, ensure_ascii=False) + "\n")
    return True


def load_examples():
    out = []
    if EXAMPLES.exists():
        for line in open(EXAMPLES, encoding="utf-8"):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def lab_memory():
    try:
        return json.loads(STATE.read_text("utf-8"))
    except Exception:
        return {}


def lab_remember(**kw):
    st = lab_memory()
    st.update(kw)
    LAB.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), "utf-8")
    return st


def readiness(chats_dir, system_text):
    st = export_dataset(chats_dir, system_text, write=False)
    counts = {k: 0 for k in SOURCES}
    counts["chat"] = st["beispiele"]
    for ex in load_examples():
        counts[ex.get("quelle", "chat")] = counts.get(ex.get("quelle", "chat"), 0) + 1
    total = sum(counts.values())
    mem = lab_memory()
    new = total - int(mem.get("trained_examples") or 0)
    level = ("Profi 🏆" if total >= 500 else "Gut 👍" if total >= 100 else "Anfänger 🌱" if total >= 30 else "Zu wenig")
    return {"gesamt": total, "quellen": counts, "stufe": level, "neu_seit_training": max(0, new),
            "lohnt_sich": total >= 50, "ziel": 100 if total < 100 else 500,
            "letztes_training": mem.get("trained_at"), "modell": mem.get("model"), "vorher": mem.get("prev_model")}


def pick_base(gpu):
    gb = gpu.get("vram_gb") or 0
    if gb >= 7.5:
        return "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
    return "unsloth/Qwen2.5-3B-Instruct-bnb-4bit"


def _stream(cmd, t, env=None):
    t.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                              env={**os.environ, "PYTHONUNBUFFERED": "1", **(env or {})})
    for line in t.proc.stdout:
        for part in line.replace("\r", "\n").split("\n"):
            t.add(part)
        if t.status == "abgebrochen":
            t.proc.terminate()
            raise RuntimeError("Abgebrochen.")
    rc = t.proc.wait()
    if rc != 0:
        bad = next((l for l in reversed(t.log) if re.search(r"error|fehler|Error|Exception", l)), f"Exit-Code {rc}")
        raise RuntimeError(bad)


PIPE_STEPS = ["Alles prüfen", "Datensatz bauen", "Trainings-Umgebung", "Training", "Lumen umstellen", "Kurztest"]


def one_click(ollama_url, chats_dir, system_text, memory, set_model, name="lumen-trained", epochs=2):
    """Der Ein-Knopf-Weg: alles automatisch, mit Schritt-Anzeige."""
    def fn(t):
        t.steps = [{"name": n, "status": "offen"} for n in PIPE_STEPS]

        def step(i, status, detail=""):
            t.steps[i]["status"] = status
            if detail:
                t.steps[i]["detail"] = detail
            t.detail = f"{PIPE_STEPS[i]} – {detail}" if detail else PIPE_STEPS[i]
            t.progress = None if status == "läuft" else t.progress

        # 1 prüfen
        step(0, "läuft")
        if ollama_models(ollama_url) is None:
            step(0, "fehler", "Ollama läuft nicht")
            raise RuntimeError("Ollama läuft nicht. Installieren: curl -fsSL https://ollama.com/install.sh | sh")
        if not shutil.which("ollama"):
            step(0, "fehler", "ollama-Befehl fehlt")
            raise RuntimeError("Der Befehl 'ollama' wurde nicht gefunden – Ollama neu installieren.")
        gpu = gpu_info()
        if not gpu.get("ok"):
            step(0, "fehler", gpu.get("hinweis", "keine GPU"))
            raise RuntimeError(gpu.get("hinweis", "Keine NVIDIA-Grafikkarte gefunden."))
        base = pick_base(gpu)
        step(0, "fertig", f"{gpu['name']} · {gpu['vram_gb']} GB → {TRAIN_BASES[base][2].split(' –')[0]}")
        # 2 Datensatz
        step(1, "läuft")
        st = export_dataset(chats_dir, system_text, memory)
        if st["beispiele"] < 30:
            step(1, "fehler", f"nur {st['beispiele']} Beispiele")
            raise RuntimeError(f"Nur {st['beispiele']} Beispiele – mindestens 30 nötig. Tipp: „🎓 Lehrer-KI“ erzeugt in 5 Minuten 200 Beispiele.")
        step(1, "fertig", f"{st['beispiele']} Beispiele")
        # 3 Umgebung
        if train_python():
            step(2, "übersprungen", "schon installiert")
        else:
            step(2, "läuft", "lädt PyTorch & Unsloth (5–8 GB, einmalig)")
            _stream(["bash", "-c", f'set -e; python3 -m venv "{TRAIN_VENV}"; "{TRAIN_VENV}/bin/pip" install -U pip; '
                                   f'"{TRAIN_VENV}/bin/pip" install unsloth'], t)
            step(2, "fertig", "installiert")
        # 4 Training
        step(3, "läuft", "das dauert 15–90 Minuten – du kannst Lumen solange normal nutzen")
        ollama_base, template, _ = TRAIN_BASES[base]
        if ollama_base not in (ollama_models(ollama_url) or []):
            t.add(f"STATUS Lade Vorlage {ollama_base} …")
            try:
                r = _ollama(ollama_url, "/api/pull", {"model": ollama_base, "name": ollama_base, "stream": False}, timeout=3600)
            except Exception as e:
                t.add(f"Hinweis: {ollama_base} nicht geladen ({e}) – nutze Standard-Vorlage")
        out = LAB / "training" / datetime.now().strftime("%Y%m%d-%H%M")
        t.loss = []
        _stream([train_python(), str(APP_DIR / "train_lora.py"), "--data", str(LAB / "dataset.jsonl"), "--base", base,
                 "--template", template, "--epochs", str(epochs), "--out", str(out), "--name", name,
                 "--ollama-base", ollama_base, "--ollama-url", ollama_url], t)
        step(3, "fertig", f"Loss {t.loss[-1] if t.loss else '?'}")
        # 5 umstellen
        step(4, "läuft")
        prev = set_model(name)
        lab_remember(trained_at=datetime.now().strftime("%d.%m.%Y %H:%M"), trained_examples=readiness(chats_dir, system_text)["gesamt"],
                     model=name, prev_model=prev)
        step(4, "fertig", f"Lumen nutzt jetzt „{name}“")
        # 6 Kurztest
        step(5, "läuft")
        try:
            ans = _ollama(ollama_url, "/api/chat", {"model": name, "stream": False, "messages": [
                {"role": "system", "content": system_text}, {"role": "user", "content": "Wer bist du und was kannst du? Antworte in 2 Sätzen."}]},
                timeout=300).get("message", {}).get("content", "")
            ans = re.sub(r"<think>.*?</think>", "", ans, flags=re.S).strip()
            lab_remember(last_test=ans)
            step(5, "fertig", ans[:160])
        except Exception as e:
            step(5, "fehler", str(e)[:120])
        t.progress = 1.0
        return name
    return run_py_task("auto", "Lumen trainieren", fn)


def compare(ollama_url, system_text, question, before, after):
    out = {}
    for key, model in (("vorher", before), ("nachher", after)):
        try:
            ans = _ollama(ollama_url, "/api/chat", {"model": model, "stream": False, "messages": [
                {"role": "system", "content": system_text}, {"role": "user", "content": question}]}, timeout=300)
            out[key] = re.sub(r"<think>.*?</think>", "", ans.get("message", {}).get("content", ""), flags=re.S).strip()
        except Exception as e:
            out[key] = f"(Fehler: {e})"
        out[key + "_modell"] = model
    return out


LANG = {"name": "Deutsch"}  # wird von lumen.py auf "Englisch" gesetzt
TEACHER_TOPICS = ["Smalltalk, Laune und Begrüßungen", "Gaming: Tipps, Spiele-Empfehlungen, Hardware", "Linux- und PC-Probleme lösen",
                  "Programmieren für Einsteiger", "Alltag: Kochen, Einkaufen, Tagesplanung", "Wissen verständlich erklärt",
                  "Musik, Filme und Serien", "Motivation, Lernen und Schule/Arbeit", "Server, Docker und Heimnetz (Grundlagen)",
                  "Witze, Spaß und Sprüche", "Fragen an den Assistenten selbst (wer bist du, was kannst du, wie funktionierst du)",
                  "Krypto-Grundlagen und Sicherheit (ohne Anlageberatung)", "Discord, Freunde, Freizeit und Hobbys"]


def teacher_prompt(user, aname, persona, facts, topic, k):
    return (f"Erzeuge {k} realistische, abwechslungsreiche Übungsgespräche auf {LANG['name']} zwischen {user} (Nutzer) und "
            f"{aname} (persönlicher KI-Assistent auf seinem PC). Themenbereich: {topic}.\n"
            f"So ist {aname}: {persona}\n"
            + (f"Was {aname} über {user} weiß (darf natürlich einfließen, nichts dazuerfinden): {facts}\n" if facts else "")
            + "Regeln: Die Nutzer-Nachrichten klingen echt (umgangssprachlich, mal kurz, mal mit Tippfehlern). "
              f"{aname} antwortet hilfreich, korrekt, eher kurz und genau in der beschriebenen Persönlichkeit. Keine erfundenen "
              "Fakten über den Nutzer. WICHTIG: Keine Gespräche, in denen etwas am PC getan wird (Dateien anlegen, Programme "
              f"öffnen, Musik steuern …) – das macht {aname} über Werkzeuge, nicht per Text. Nur Gespräche, Wissen, Erklären, "
              "Ratschläge, Spaß. Jedes Gespräch hat 1–3 Wechsel.\n"
              'Gib NUR gültiges JSON zurück, ohne Text davor/danach: {"gespraeche": [[{"role":"user","content":"…"},'
              '{"role":"assistant","content":"…"}], …]}')


def parse_teacher(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    good = []
    for conv in data.get("gespraeche", []):
        if not isinstance(conv, list) or len(conv) < 2:
            continue
        msgs = [{"role": x.get("role"), "content": str(x.get("content", "")).strip()} for x in conv if isinstance(x, dict)]
        if any(m["role"] not in ("user", "assistant") or not m["content"] for m in msgs):
            continue
        said = " ".join(m["content"] for m in msgs if m["role"] == "assistant")
        if re.search(r"als (eine )?ki(-sprachmodell)? kann ich|as an ai", said, re.I):
            continue
        if re.search(r"\b(habe|hab)\b.{0,60}\b(geöffnet|gestartet|erstellt|angelegt|gespeichert|gelöscht|verschoben)", said, re.I):
            continue  # vorgetäuschte PC-Aktionen nicht lernen
        good.append(msgs)
    return good


def teacher_run(n, ask_fn, user, aname, persona, facts):
    """ask_fn(prompt) -> Text der Cloud-KI."""
    def fn(t):
        batches = max(1, -(-int(n) // 5))
        made = 0
        for i in range(batches):
            if t.status == "abgebrochen":
                break
            topic = TEACHER_TOPICS[i % len(TEACHER_TOPICS)]
            t.add(f"STATUS {topic} …")
            try:
                convs = parse_teacher(ask_fn(teacher_prompt(user, aname, persona, facts, topic, 5)))
            except Exception as e:
                t.add(f"Fehler bei {topic}: {e}")
                if "Key" in str(e) or "Guthaben" in str(e):
                    raise
                continue
            for c in convs:
                if add_example(c, "lehrer"):
                    made += 1
            t.add(f"PROGRESS {i + 1}/{batches}")
            t.add(f"{made} Gespräche erstellt")
        t.detail = f"{made} Übungsgespräche erstellt"
        return made
    return run_py_task("teacher", "Lehrer-KI schreibt Übungsgespräche", fn)
