"""Lumen – GitHub-Werkstatt: Werkzeuge von GitHub finden, prüfen, isoliert installieren, selbst lernen und benutzen.

Ablauf: suchen → prüfen (Sterne, Alter, Lizenz, letzte Änderung, Warnzeichen) → installieren (immer mit deiner Bestätigung,
jedes Werkzeug in einem eigenen Ordner unter ~/.lumen/gh-tools, Python-Werkzeuge in einer eigenen virtuellen Umgebung,
keine Admin-Rechte, keine „curl | sh“-Installer) → lernen (README + --help lesen, daraus schreibt Lumen sich eine
Fähigkeit) → benutzen (github_tool_run; fragt nach, außer du hast das Werkzeug als vertraut markiert).

Gesperrt: Schadsoftware/Angriffs-Werkzeuge (Stealer, RATs, Ransomware, DDoS, Brute-Force/Passwort-Knacker, Exploit-/C2-
Frameworks) und Personensuche-Werkzeuge (Sherlock, Maigret, Holehe …) – passend zu Lumens Regeln.
"""
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import tarfile
import threading
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import integrations as ig

DIR = Path.home() / ".lumen" / "gh-tools"
BIN = DIR / "bin"
DATA = DIR / "tools.json"
OUT = Path.home() / "Lumen" / "Werkzeuge"
LOCK = threading.RLock()
API = "https://api.github.com"
learn_fn = None   # von lumen.py gesetzt: (name, readme, help_text, meta) → SKILL-Text

BLOCK = [
    (r"\b(keylogger|stealer|grabber|token[- ]?grabber|cookie[- ]?stealer|infostealer|rat\b|remote access trojan|ransomware|crypter|"
     r"fud\b|botnet|ddos|dos[- ]?attack|booter|stresser|sms[- ]?bomb|call[- ]?bomb|discord[- ]?nuke|spyware|stalkerware|rootkit\b(?![- ]?(hunter|detect|check|scan))|"
     r"phishing[- ]?(kit|page|tool)|credential[- ]?harvest|av[- ]?bypass|antivirus[- ]?bypass|evasion|payload[- ]?generator|c2\b|"
     r"command[- ]and[- ]control|reverse[- ]?shell|exploit[- ]?(kit|framework)|brute[- ]?forc|password[- ]?crack|hash[- ]?crack|"
     r"wifi[- ]?(crack|hack)|wpa[- ]?crack|deauth|carding|bank[- ]?fraud)", "Angriffs- oder Schadsoftware"),
    (r"\b(sherlock|maigret|holehe|social[- ]?analyzer|blackbird|phoneinfoga|ghunt|people[- ]?search|doxx?|dox(ing)?|"
     r"find (social|accounts) (by|of) (username|person)|username[- ]?(osint|search|hunt))", "Personensuche (Privatsphäre Dritter)"),
]
BLOCK_REPOS = {"sherlock-project/sherlock", "soxoj/maigret", "megadose/holehe", "sundowndev/phoneinfoga", "mxrch/ghunt"}


def _gh(path, raw=False):
    tok = (ig.conf("github") or {}).get("token")
    h = {"Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json", "User-Agent": "Lumen-Assistant/1.0"}
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(API + path, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        if e.code in (403, 429) and (e.headers.get("X-RateLimit-Remaining") == "0" or e.code == 429):
            raise RuntimeError("GitHub-Limit erreicht (60 Anfragen/Stunde ohne Konto). Unter Apps → GitHub einen Token eintragen hebt das auf.")
        if e.code == 404:
            raise RuntimeError("Repository nicht gefunden.")
        raise RuntimeError(f"GitHub-Fehler {e.code}.")
    except urllib.error.URLError as e:
        raise RuntimeError(f"GitHub nicht erreichbar: {e.reason}")
    return data.decode("utf-8", "replace") if raw else json.loads(data)


def _load():
    try:
        d = json.loads(DATA.read_text("utf-8"))
    except Exception:
        d = {}
    d.setdefault("tools", {})
    return d


def _save(d):
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(DATA)


def _repo(r):
    r = str(r or "").strip()
    m = re.search(r"github\.com/([\w.-]+/[\w.-]+?)(?:\.git|/|$)", r)
    r = m.group(1) if m else r
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", r):
        raise RuntimeError("Repository bitte als besitzer/name oder GitHub-Link angeben.")
    return r


def _blocked(repo, desc, topics):
    if repo.lower() in BLOCK_REPOS:
        return "Personensuche (Privatsphäre Dritter)"
    text = " ".join([repo.replace("-", " ").replace("_", " "), desc or "", " ".join(topics or [])]).lower()
    for rx, why in BLOCK:
        if re.search(rx, text):
            return why
    return None


# ---------------------------------------------------------------- Suchen & Prüfen
def search(query, n=8):
    q = str(query or "").strip()
    if not q:
        raise RuntimeError("Wonach suchen?")
    js = _gh("/search/repositories?" + urllib.parse.urlencode({"q": q + " archived:false", "sort": "stars", "order": "desc", "per_page": min(int(n), 15)}))
    out = []
    for r in js.get("items", []):
        why = _blocked(r["full_name"], r.get("description"), r.get("topics"))
        out.append({"repo": r["full_name"], "sterne": r["stargazers_count"], "beschreibung": (r.get("description") or "")[:200],
                    "sprache": r.get("language"), "lizenz": (r.get("license") or {}).get("spdx_id"), "zuletzt": (r.get("pushed_at") or "")[:10],
                    "url": r["html_url"], **({"gesperrt": why} if why else {})})
    return {"suche": q, "treffer": out, "hinweis": "Mit github_tool_info prüfen, dann mit github_tool_install installieren (fragt nach)."}


def _arch_words():
    m = platform.machine().lower()
    if m in ("x86_64", "amd64"):
        return ("x86_64", "amd64", "x64", "linux64"), ("arm", "aarch64", "i386", "386", "darwin", "macos", "windows", ".exe", ".msi", ".dmg")
    if m in ("aarch64", "arm64"):
        return ("aarch64", "arm64"), ("x86", "amd64", "darwin", "macos", "windows", ".exe", "armv7")
    return (m,), ("darwin", "windows", ".exe")


def _pick_asset(assets):
    good, bad = _arch_words()
    cands = []
    for a in assets or []:
        n = a["name"].lower()
        if "linux" not in n and not n.endswith(".appimage"):
            continue
        if any(b in n for b in bad) or n.endswith((".sha256", ".sig", ".asc", ".sbom", ".deb", ".rpm", ".apk", ".txt", ".json", ".pem")):
            continue
        score = (2 if any(g in n for g in good) else 0) + (1 if n.endswith((".tar.gz", ".tgz", ".zip", ".appimage")) or "." not in n[-8:] else 0)
        if score:
            cands.append((score, a))
    cands.sort(key=lambda x: -x[0])
    return cands[0][1] if cands else None


def info(repo):
    repo = _repo(repo)
    r = _gh(f"/repos/{repo}")
    topics = r.get("topics") or []
    files = [f["name"] for f in _gh(f"/repos/{repo}/contents/")] if r.get("size") else []
    try:
        readme = _gh(f"/repos/{repo}/readme", raw=True)
    except Exception:
        readme = ""
    rel = None
    try:
        rel = _gh(f"/repos/{repo}/releases/latest")
    except Exception:
        pass
    asset = _pick_asset((rel or {}).get("assets"))
    methods = []
    if asset:
        methods.append("release")
    if "pyproject.toml" in files or "setup.py" in files:
        methods.append("pip")
    if "go.mod" in files and shutil.which("go"):
        methods.append("go")
    if "package.json" in files and shutil.which("npm"):
        methods.append("npm")
    if any(f.endswith((".py", ".sh")) for f in files) and "pip" not in methods:
        methods.append("clone")
    now = datetime.now(timezone.utc)
    age = (now - datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))).days
    idle = (now - datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))).days
    risks = []
    why = _blocked(repo, r.get("description"), topics)
    if why:
        risks.append(("gesperrt", f"Lumen installiert das nicht: {why}."))
    if r["stargazers_count"] < 50:
        risks.append(("warn", f"Nur {r['stargazers_count']} Sterne – wenig genutzt, schwer einzuschätzen."))
    if age < 60:
        risks.append(("warn", f"Erst {age} Tage alt – neue Repos werden manchmal für Schadcode missbraucht."))
    if r.get("archived"):
        risks.append(("warn", "Archiviert – wird nicht mehr gepflegt."))
    if idle > 730:
        risks.append(("info", f"Seit {idle // 365} Jahren keine Änderung."))
    if not r.get("license"):
        risks.append(("info", "Keine Lizenz angegeben."))
    if r.get("fork"):
        risks.append(("info", f"Ist ein Fork von {(r.get('parent') or {}).get('full_name', '?')} – lieber das Original nehmen?"))
    if re.search(r"curl[^\n]*\|\s*(sudo\s+)?(ba)?sh", readme):
        risks.append(("info", "README nutzt „curl … | sh“ – Lumen macht das nicht, sondern installiert selbst isoliert."))
    if not methods:
        risks.append(("warn", "Keine automatische Installationsart erkannt (kein Linux-Release, kein Python-Paket)."))
    return {"repo": repo, "beschreibung": r.get("description"), "sterne": r["stargazers_count"], "forks": r["forks_count"],
            "sprache": r.get("language"), "lizenz": (r.get("license") or {}).get("spdx_id"), "erstellt": r["created_at"][:10],
            "zuletzt": r["pushed_at"][:10], "themen": topics[:10], "release": (rel or {}).get("tag_name"),
            "release_datei": asset["name"] if asset else None, "installation": methods, "risiken": [{"stufe": s, "text": t} for s, t in risks],
            "gesperrt": bool(why), "readme_anfang": readme[:2500], "url": r["html_url"]}


# ---------------------------------------------------------------- Installieren
def _run(cmd, cwd=None, timeout=900, env=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL,
                       env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "GIT_TERMINAL_PROMPT": "0", **(env or {})})
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])} fehlgeschlagen: " + (r.stderr or r.stdout).strip()[-500:])
    return r.stdout


def _execs(folder):
    out = []
    for p in Path(folder).rglob("*"):
        try:
            if p.is_file() and os.access(p, os.X_OK) and not p.name.startswith(".") and p.suffix not in (".so", ".dylib", ".txt", ".md", ".json"):
                with open(p, "rb") as f:
                    head = f.read(4)
                if head.startswith((b"\x7fELF", b"#!")) or p.suffix.lower() == ".appimage":
                    out.append(p)
        except Exception:
            pass
    return out


def plan(repo, method=None):
    """Was beim Installieren passiert (für die Bestätigung)."""
    i = info(repo)
    if i["gesperrt"]:
        raise RuntimeError(i["risiken"][0]["text"])
    m = method or (i["installation"][0] if i["installation"] else None)
    if not m or m not in i["installation"]:
        raise RuntimeError("Keine passende Installationsart. Möglich: " + (", ".join(i["installation"]) or "keine"))
    target = DIR / i["repo"].replace("/", "__")
    what = {"release": f"Lädt die fertige Linux-Datei „{i['release_datei']}“ aus Release {i['release']} herunter und entpackt sie.",
            "pip": "Lädt den Quellcode (git clone) und installiert ihn in eine eigene Python-Umgebung (venv) – dabei läuft der Installationscode des Projekts.",
            "go": "Baut das Werkzeug mit „go install“ in einen eigenen Ordner.",
            "npm": "Lädt den Quellcode und installiert die Node-Abhängigkeiten (npm install) – dabei können Install-Skripte laufen.",
            "clone": "Lädt den Quellcode (git clone); Python-Abhängigkeiten aus requirements.txt kommen in eine eigene venv."}[m]
    risk = "\n".join(("⚠️ " if r["stufe"] == "warn" else "ℹ️ ") + r["text"] for r in i["risiken"]) or "✅ Keine Warnzeichen gefunden."
    return i, m, target, (f"{i['repo']} (★{i['sterne']}, {i['lizenz'] or 'ohne Lizenz'}, zuletzt {i['zuletzt']})\n{i['beschreibung'] or ''}\n\n"
                          f"Art: {m} – {what}\nOrdner: {target}\nOhne Admin-Rechte, nichts außerhalb dieses Ordners (+ Verknüpfung in {BIN}).\n\n{risk}")


def install(repo, method=None):
    i, m, target, _ = plan(repo, method)
    if not shutil.which("git") and m in ("pip", "clone", "npm"):
        raise RuntimeError("git fehlt: sudo apt install git")
    with LOCK:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        BIN.mkdir(parents=True, exist_ok=True)
        commit, cmds = "", []
        try:
            if m == "release":
                rel = _gh(f"/repos/{i['repo']}/releases/latest")
                asset = _pick_asset(rel.get("assets"))
                dl = target / asset["name"]
                req = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "Lumen-Assistant/1.0"})
                with urllib.request.urlopen(req, timeout=300) as r, open(dl, "wb") as f:
                    shutil.copyfileobj(r, f)
                if dl.stat().st_size > 400 * 1024 * 1024:
                    raise RuntimeError("Datei größer als 400 MB – abgebrochen.")
                n = dl.name.lower()
                if n.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar")):
                    with tarfile.open(dl) as t:
                        try:
                            t.extractall(target / "pkg", filter="data")
                        except TypeError:   # Python < 3.12: selbst prüfen
                            for mem in t.getmembers():
                                if mem.name.startswith("/") or ".." in Path(mem.name).parts or mem.issym() and (".." in mem.linkname or mem.linkname.startswith("/")):
                                    raise RuntimeError("Unsicheres Archiv.")
                            t.extractall(target / "pkg")
                    dl.unlink()
                elif n.endswith(".zip"):
                    with zipfile.ZipFile(dl) as z:
                        for zi in z.infolist():
                            if ".." in zi.filename or zi.filename.startswith("/"):
                                raise RuntimeError("Unsicheres Archiv.")
                        z.extractall(target / "pkg")
                        for zi in z.infolist():   # Ausführbar-Bits aus dem ZIP übernehmen
                            mode = zi.external_attr >> 16
                            if mode & 0o111:
                                (target / "pkg" / zi.filename).chmod(mode & 0o755)
                    dl.unlink()
                else:
                    dl.chmod(0o755)
                cmds = _execs(target)
                if not cmds:   # Binärdateien ohne Ausführbar-Bit
                    for p in (target / "pkg").rglob("*") if (target / "pkg").exists() else []:
                        if p.is_file() and open(p, "rb").read(4) == b"\x7fELF":
                            p.chmod(0o755)
                            cmds.append(p)
                commit = rel.get("tag_name", "")
            elif m in ("pip", "clone", "npm"):
                _run(["git", "clone", "--depth", "1", f"https://github.com/{i['repo']}.git", str(target / "src")], timeout=600)
                commit = _run(["git", "rev-parse", "--short", "HEAD"], cwd=target / "src").strip()
                if m == "npm":
                    _run(["npm", "install", "--omit=dev", "--no-audit", "--no-fund"], cwd=target / "src", timeout=1200)
                    pkg = json.loads((target / "src" / "package.json").read_text())
                    b = pkg.get("bin") or {}
                    b = {pkg.get("name", "tool").split("/")[-1]: b} if isinstance(b, str) else b
                    for name, rel_path in b.items():
                        p = target / "src" / rel_path
                        p.chmod(p.stat().st_mode | 0o111)
                        cmds.append(p)
                else:
                    _run([shutil.which("python3") or "python3", "-m", "venv", str(target / "venv")], timeout=300)
                    pip = str(target / "venv" / "bin" / "pip")
                    before = {p.name for p in (target / "venv" / "bin").iterdir()}
                    if m == "pip":
                        _run([pip, "install", "-q", str(target / "src")], timeout=1800)
                        cmds = [p for p in (target / "venv" / "bin").iterdir() if p.name not in before and os.access(p, os.X_OK)
                                and not re.fullmatch(r"(python|pip)[\d.]*|activate.*|Activate\.ps1|normalizer|f2py|wheel|distro|dotenv", p.name)]
                    else:
                        req = target / "src" / "requirements.txt"
                        if req.exists():
                            _run([pip, "install", "-q", "-r", str(req)], timeout=1800)
                        src = target / "src"
                        name = i["repo"].split("/")[1].lower()
                        guess = [src / f"{name}.py", src / "main.py", src / "cli.py", src / f"{name.replace('-', '_')}.py", src / "run.py"]
                        guess += sorted(p for p in src.glob("*.sh"))
                        guess += sorted(p for p in src.glob("*.py") if p.read_text("utf-8", "ignore").startswith("#!"))
                        main = next((p for p in guess if p.exists()), None)
                        if main:
                            w = target / "run"
                            interp = str(target / "venv" / "bin" / "python") if main.suffix == ".py" else "/bin/sh"
                            w.write_text(f'#!/bin/sh\ncd "{src}" 2>/dev/null\nexec "{interp}" "{main}" "$@"\n')
                            w.chmod(0o755)
                            cmds = [w]
            elif m == "go":
                gobin = target / "bin"
                _run(["go", "install", f"github.com/{i['repo']}@latest"], env={"GOBIN": str(gobin), "CGO_ENABLED": "0"}, timeout=1800)
                cmds = list(gobin.iterdir()) if gobin.exists() else []
                commit = "latest"
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise
        if not cmds:
            shutil.rmtree(target, ignore_errors=True)
            raise RuntimeError("Installiert, aber kein startbares Programm gefunden – dieses Repo ist eher eine Bibliothek als ein Werkzeug.")
        cmds = sorted(cmds, key=lambda p: (0 if i["repo"].split("/")[1].lower().replace("-", "") in p.name.lower().replace("-", "") else 1, len(p.name)))[:5]
        names = []
        for p in cmds:
            nm = re.sub(r"[^\w.-]", "", p.stem if p.suffix.lower() in (".appimage", ".py", ".sh") else p.name).lower()
            if p.name == "run":
                nm = i["repo"].split("/")[1].lower()
            nm = re.sub(r"[-_.]?(linux|amd64|x86_64|arm64|aarch64)[-_.]?", "", nm).strip("-_.") or nm
            link = BIN / nm
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(p)
            names.append(nm)
        d = _load()
        d["tools"][names[0]] = {"repo": i["repo"], "methode": m, "version": commit, "ordner": str(target), "befehle": names,
                                "pfad": str(BIN / names[0]), "installiert": datetime.now().strftime("%d.%m.%Y %H:%M"), "vertraut": False,
                                "beschreibung": i["beschreibung"], "sterne": i["sterne"], "fähigkeit": None, "läufe": 0}
        _save(d)
    return {"name": names[0], "befehle": names, "methode": m, "version": commit,
            "text": f"🧰 {i['repo']} installiert als „{names[0]}“ ({m}, {commit}). Lumen lernt jetzt, es zu benutzen …"}


def help_text(name):
    t = get(name)
    exe = t["pfad"]
    for args in (["--help"], ["-h"], ["help"]):
        try:
            r = subprocess.run([exe, *args], capture_output=True, text=True, timeout=25, stdin=subprocess.DEVNULL, cwd=str(OUT_dir()))
            txt = (r.stdout or "") + ("\n" + r.stderr if r.stderr and len(r.stdout or "") < 200 else "")
            if len(txt.strip()) > 40:
                return txt[:12000]
        except Exception:
            continue
    return ""


def OUT_dir():
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT


def learn(name):
    """README + --help lesen, daraus eine Fähigkeit schreiben (über learn_fn = KI)."""
    t = get(name)
    readme = ""
    src = Path(t["ordner"]) / "src"
    for f in ("README.md", "README.rst", "README.txt", "README", "readme.md"):
        if (src / f).exists():
            readme = (src / f).read_text("utf-8", "ignore")
            break
    if not readme:
        try:
            readme = _gh(f"/repos/{t['repo']}/readme", raw=True)
        except Exception:
            readme = ""
    hlp = help_text(name)
    if not learn_fn:
        raise RuntimeError("Lernen nicht verfügbar.")
    skill_id = learn_fn(name, readme[:14000], hlp, t)
    with LOCK:
        d = _load()
        if name in d["tools"]:
            d["tools"][name]["fähigkeit"] = skill_id
            _save(d)
    return {"name": name, "fähigkeit": skill_id, "hilfe_gefunden": bool(hlp), "text": f"🧠 Gelernt: wie man „{name}“ benutzt (Fähigkeit {skill_id})."}


def get(name):
    d = _load()
    n = str(name or "").strip().lower()
    t = d["tools"].get(n) or next((v for k, v in d["tools"].items() if n in v["befehle"] or v["repo"].lower() == n or v["repo"].split("/")[1].lower() == n), None)
    if not t:
        raise RuntimeError(f"Werkzeug „{name}“ ist nicht installiert. Installiert: " + (", ".join(d["tools"]) or "keine"))
    return t


def listing():
    return [{"name": k, **{x: v[x] for x in ("repo", "methode", "version", "befehle", "installiert", "vertraut", "beschreibung", "fähigkeit", "läufe", "sterne")}}
            for k, v in _load()["tools"].items()]


def run(name, args=None, timeout=300, stdin_text=None):
    t = get(name)
    cmd = str(args.pop(0)) if isinstance(args, list) and args and args[0] in t["befehle"] and args[0] != t["befehle"][0] else None
    exe = str(BIN / cmd) if cmd else t["pfad"]
    argv = [str(a) for a in (args or [])][:60]
    if any(len(a) > 2000 for a in argv):
        raise RuntimeError("Argument zu lang.")
    try:
        r = subprocess.run([exe, *argv], capture_output=True, text=True, timeout=max(5, min(int(timeout), 3600)), cwd=str(OUT_dir()),
                           input=stdin_text, stdin=None if stdin_text is not None else subprocess.DEVNULL,
                           env={**os.environ, "PATH": f"{BIN}:{os.environ.get('PATH', '')}"})
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Abgebrochen nach {timeout} s.")
    with LOCK:
        d = _load()
        for k, v in d["tools"].items():
            if v is t or v["pfad"] == t["pfad"]:
                v["läufe"] += 1
        _save(d)
    out = r.stdout or ""
    err = r.stderr or ""
    return {"befehl": " ".join([Path(exe).name, *argv])[:300], "rückgabe": r.returncode, "ausgabe": out[-12000:], "fehler": err[-3000:],
            "ordner": str(OUT), "hinweis": "Dateien, die das Werkzeug anlegt, liegen im Ordner oben."}


def run_confirm(name, args):
    try:
        t = get(name)
    except RuntimeError:
        return None
    if t.get("vertraut"):
        return None
    return ("GitHub-Werkzeug ausführen", f"{t['repo']} ({t['methode']} {t['version']})\n\n$ {Path(t['pfad']).name} " + " ".join(map(str, args or []))[:800]
            + f"\n\nOrdner: {OUT}\n(„Vertrauen“ im Werkstatt-Fenster spart diese Frage.)")


def set_trusted(name, on=True):
    with LOCK:
        d = _load()
        t = get(name)
        for v in d["tools"].values():
            if v["pfad"] == t["pfad"]:
                v["vertraut"] = bool(on)
        _save(d)
    return "Vertraut – läuft ab jetzt ohne Nachfrage." if on else "Fragt wieder vor jedem Start."


def remove(name, skills_delete=None):
    t = get(name)
    with LOCK:
        d = _load()
        key = next(k for k, v in d["tools"].items() if v["pfad"] == t["pfad"])
        for c in t["befehle"]:
            l = BIN / c
            if l.is_symlink() or l.exists():
                l.unlink()
        shutil.rmtree(t["ordner"], ignore_errors=True)
        d["tools"].pop(key)
        _save(d)
    if t.get("fähigkeit") and skills_delete:
        try:
            skills_delete(t["fähigkeit"])
        except Exception:
            pass
    return f"„{key}“ entfernt."


def update(name):
    t = get(name)
    r = install(t["repo"], t["methode"])
    with LOCK:
        d = _load()
        if r["name"] in d["tools"]:
            d["tools"][r["name"]]["vertraut"] = t.get("vertraut", False)
            d["tools"][r["name"]]["fähigkeit"] = t.get("fähigkeit")
            _save(d)
    return {**r, "text": f"🔄 {t['repo']} aktualisiert ({t['version']} → {r['version']})."}
