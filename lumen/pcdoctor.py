"""
Lumen – PC-Doktor: findet, was den PC langsam oder voll macht, und räumt nach Bestätigung auf.
Nur lesen beim Scan. Aufräumen nur mit Bestätigung; Admin-Aktionen über pkexec (Passwort-Fenster des Systems –
Lumen sieht das Passwort nie).
"""
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

HOME = Path.home()
LAST = {"report": None}


ENV_C = {**os.environ, "LC_ALL": "C", "LANG": "C"}


def _run(cmd, timeout=20, shell=False):
    try:
        r = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout, env=ENV_C, stdin=subprocess.DEVNULL)
        return r.stdout.strip()
    except Exception:
        return ""


def _du(path, timeout=25):
    p = Path(path).expanduser()
    if not p.exists():
        return 0
    out = _run(["du", "-sxb", str(p)], timeout=timeout)
    try:
        return int(out.split()[0])
    except Exception:
        return 0


def gb(n):
    return round(n / 1e9, 2)


def human(n):
    for unit, f in (("TB", 1e12), ("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
        if n >= f:
            return f"{n / f:.1f} {unit}".replace(".", ",")
    return f"{n} B"


# ---------------------------------------------------------------- Aufräum-Aktionen
def _trash_dir():
    return HOME / ".local/share/Trash"


FIXES = {
    # id: (Titel, Beschreibung, sicher, admin)
    "trash": ("Papierkorb leeren", "Endgültig löschen, was im Papierkorb liegt.", True, False),
    "thumbs": ("Vorschaubilder-Cache leeren", "~/.cache/thumbnails – wird bei Bedarf neu erzeugt.", True, False),
    "pip": ("pip-Cache leeren", "Heruntergeladene Python-Pakete (werden bei Bedarf neu geladen).", True, False),
    "npm": ("npm-Cache leeren", "Heruntergeladene Node-Pakete.", True, False),
    "browser_cache": ("Browser-Caches leeren", "Chrome/Chromium/Firefox/Brave-Cache (keine Passwörter, keine Verläufe, keine Logins).", True, False),
    "docker": ("Docker aufräumen", "Unbenutzte Images ohne Namen, gestoppte Build-Caches (laufende Container bleiben).", True, False),
    "flatpak": ("Ungenutzte Flatpak-Laufzeiten entfernen", "flatpak uninstall --unused", True, False),
    "apt": ("Paket-Cache leeren (apt)", "Alte heruntergeladene .deb-Pakete.", True, True),
    "pacman": ("Paket-Cache leeren (pacman)", "Behält die letzten 2 Versionen (paccache -rk2).", True, True),
    "dnf": ("Paket-Cache leeren (dnf)", "dnf clean packages", True, True),
    "journal": ("System-Logs verkleinern", "journalctl --vacuum-size=200M", True, True),
    "snap": ("Alte Snap-Versionen entfernen", "Deaktivierte Revisionen löschen.", True, True),
    "autostart": ("Autostart-Eintrag ausschalten", "Programm startet nicht mehr automatisch (umkehrbar).", False, False),
    "kill": ("Programm beenden", "Prozess mit viel Speicher/CPU beenden.", False, False),
}


def _browser_caches():
    c = HOME / ".cache"
    return [p for p in (c / "google-chrome", c / "chromium", c / "BraveSoftware", c / "mozilla/firefox", c / "microsoft-edge", c / "vivaldi")
            if p.exists()]


def _measure_fix(fid):
    if fid == "trash":
        return _du(_trash_dir())
    if fid == "thumbs":
        return _du(HOME / ".cache/thumbnails")
    if fid == "pip":
        return _du(HOME / ".cache/pip")
    if fid == "npm":
        return _du(HOME / ".npm/_cacache")
    if fid == "browser_cache":
        return sum(_du(p) for p in _browser_caches())
    if fid == "apt":
        return _du("/var/cache/apt/archives") if shutil.which("apt") else 0
    if fid == "pacman":
        return _du("/var/cache/pacman/pkg") if shutil.which("pacman") else 0
    if fid == "dnf":
        return _du("/var/cache/dnf") if shutil.which("dnf") else 0
    if fid == "journal":
        m = re.search(r"([\d.]+)\s*([KMGT])", _run(["journalctl", "--disk-usage"]) or "")
        return int(float(m.group(1)) * {"K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}[m.group(2)]) if m else 0
    if fid == "docker":
        if not shutil.which("docker"):
            return 0
        out = _run(["docker", "system", "df", "--format", "{{.Type}}|{{.Reclaimable}}"], timeout=20)
        total = 0
        for line in out.splitlines():
            t, _, rec = line.partition("|")
            m = re.match(r"([\d.]+)\s*([kKMGT]?B)", rec.strip())
            if m and t in ("Images", "Build Cache"):
                total += float(m.group(1)) * {"B": 1, "kB": 1e3, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12}.get(m.group(2), 1)
        return int(total)
    if fid == "snap":
        if not shutil.which("snap"):
            return 0
        n = len([l for l in _run(["snap", "list", "--all"]).splitlines() if "disabled" in l])
        return n * 150_000_000
    if fid == "flatpak":
        return 1 if shutil.which("flatpak") else 0
    return 0


def run_fix(fid, arg=None):
    """Führt eine Aufräum-Aktion aus. Bestätigung passiert vorher in Lumen."""
    before = _measure_fix(fid) if fid not in ("autostart", "kill") else 0
    pk = ["pkexec"] if shutil.which("pkexec") and os.geteuid() != 0 else ([] if os.geteuid() == 0 else None)
    if fid == "trash":
        for sub in ("files", "info"):
            d = _trash_dir() / sub
            if d.exists():
                for p in d.iterdir():
                    shutil.rmtree(p, ignore_errors=True) if p.is_dir() and not p.is_symlink() else p.unlink(missing_ok=True)
    elif fid == "thumbs":
        shutil.rmtree(HOME / ".cache/thumbnails", ignore_errors=True)
    elif fid == "pip":
        shutil.rmtree(HOME / ".cache/pip", ignore_errors=True)
    elif fid == "npm":
        shutil.rmtree(HOME / ".npm/_cacache", ignore_errors=True)
    elif fid == "browser_cache":
        for p in _browser_caches():
            for sub in p.rglob("Cache*"):
                if sub.is_dir() and sub.name in ("Cache", "Code Cache", "cache2", "GPUCache", "CacheStorage"):
                    shutil.rmtree(sub, ignore_errors=True)
            if p.name == "firefox":
                for c2 in p.rglob("cache2"):
                    shutil.rmtree(c2, ignore_errors=True)
    elif fid == "docker":
        _run(["docker", "image", "prune", "-f"], timeout=300)
        _run(["docker", "builder", "prune", "-f"], timeout=300)
    elif fid == "flatpak":
        _run(["flatpak", "uninstall", "--unused", "-y"], timeout=600)
    elif fid in ("apt", "pacman", "dnf", "journal", "snap"):
        if pk is None:
            raise RuntimeError("Dafür sind Admin-Rechte nötig und pkexec fehlt. Im Terminal: " + admin_cmd(fid))
        cmd = {"apt": ["apt-get", "clean"], "pacman": ["paccache", "-rk2"] if shutil.which("paccache") else ["pacman", "-Sc", "--noconfirm"],
               "dnf": ["dnf", "clean", "packages"], "journal": ["journalctl", "--vacuum-size=200M"],
               "snap": ["sh", "-c", "snap list --all | awk '/disabled/{print $1, $3}' | while read n r; do snap remove \"$n\" --revision=\"$r\"; done"]}[fid]
        r = subprocess.run(pk + cmd, capture_output=True, text=True, timeout=900)
        if r.returncode in (126, 127):
            raise RuntimeError("Abgebrochen (Passwort-Fenster geschlossen).")
    elif fid == "autostart":
        p = Path(str(arg or "")).expanduser()
        if p.parent != HOME / ".config/autostart" or p.suffix != ".desktop" or not p.exists():
            if str(arg or "").startswith("systemd-user:"):
                unit = str(arg).split(":", 1)[1]
                if not re.fullmatch(r"[\w@.\-]+", unit):
                    raise RuntimeError("Ungültiger Dienst.")
                _run(["systemctl", "--user", "disable", "--now", unit])
                return {"ok": True, "text": f"Benutzerdienst {unit} ausgeschaltet (wieder an: systemctl --user enable --now {unit})."}
            raise RuntimeError("Autostart-Eintrag nicht gefunden.")
        txt = p.read_text("utf-8", "replace")
        txt = re.sub(r"(?m)^Hidden=.*\n?", "", txt)
        txt = re.sub(r"(?m)^X-GNOME-Autostart-enabled=.*\n?", "", txt)
        txt = txt.replace("[Desktop Entry]", "[Desktop Entry]\nHidden=true\nX-GNOME-Autostart-enabled=false", 1)
        p.write_text(txt, "utf-8")
        return {"ok": True, "text": f"Autostart ausgeschaltet: {p.stem} (rückgängig: Zeile Hidden=true in {p} löschen)."}
    elif fid == "kill":
        pid = int(arg)
        if pid <= 1 or pid == os.getpid():
            raise RuntimeError("Diesen Prozess beende ich nicht.")
        os.kill(pid, 15)
        return {"ok": True, "text": f"Prozess {pid} beendet."}
    else:
        raise RuntimeError("Unbekannte Aktion.")
    after = _measure_fix(fid)
    freed = max(0, before - after)
    return {"ok": True, "frei": freed, "text": f"{FIXES[fid][0]}: {human(freed)} frei" if freed > 1000 else f"{FIXES[fid][0]}: erledigt"}


def admin_cmd(fid):
    return {"apt": "sudo apt-get clean", "pacman": "sudo paccache -rk2", "dnf": "sudo dnf clean packages",
            "journal": "sudo journalctl --vacuum-size=200M",
            "snap": "snap list --all | awk '/disabled/{print $1, $3}' | while read n r; do sudo snap remove \"$n\" --revision=\"$r\"; done"}.get(fid, "")


# ---------------------------------------------------------------- Scan
def _procs(sort):
    out = _run(["ps", "-eo", "pid,comm,%mem,%cpu,rss", f"--sort=-{sort}"], timeout=10).splitlines()[1:9]
    res = []
    for line in out:
        f = line.split()
        if len(f) >= 5:
            try:
                res.append({"pid": int(f[0]), "name": " ".join(f[1:-3]), "ram_prozent": float(f[-3].replace(",", ".")),
                            "cpu_prozent": float(f[-2].replace(",", ".")), "ram": human(int(f[-1]) * 1024)})
            except ValueError:
                continue
    return res


def _autostart():
    items = []
    d = HOME / ".config/autostart"
    for p in sorted(d.glob("*.desktop")) if d.exists() else []:
        txt = p.read_text("utf-8", "replace")
        if re.search(r"(?m)^Hidden=true", txt) or re.search(r"(?m)^X-GNOME-Autostart-enabled=false", txt):
            continue
        name = (re.search(r"(?m)^Name=(.+)$", txt) or [None, p.stem])[1]
        items.append({"name": name, "id": str(p), "art": "Programm"})
    if shutil.which("systemctl"):
        for line in _run(["systemctl", "--user", "list-unit-files", "--state=enabled", "--no-legend", "--type=service"]).splitlines():
            unit = line.split()[0] if line.split() else ""
            if unit and not unit.startswith(("pipewire", "wireplumber", "dbus", "xdg-", "gnome-", "plasma-", "pulseaudio", "gvfs", "at-spi",
                                              "evolution", "tracker", "lumen")):
                items.append({"name": unit.replace(".service", ""), "id": "systemd-user:" + unit, "art": "Benutzerdienst"})
    return items


def _temps():
    out = {}
    try:
        for z in Path("/sys/class/thermal").glob("thermal_zone*"):
            try:
                t = int((z / "temp").read_text().strip()) / 1000
                typ = (z / "type").read_text().strip()
            except Exception:
                continue
            if 0 < t < 130:
                out[typ] = max(out.get(typ, 0), round(t))
    except Exception:
        pass
    if shutil.which("nvidia-smi"):
        g = _run(["nvidia-smi", "--query-gpu=temperature.gpu,name,driver_version,memory.used,memory.total", "--format=csv,noheader,nounits"])
        if g:
            f = [x.strip() for x in g.splitlines()[0].split(",")]
            if len(f) >= 5:
                t = _safe_int(f[0], -1)
                if 0 < t < 130:
                    out["GPU"] = t
                out["_gpu"] = {"name": f[1], "treiber": f[2], "vram": f"{f[3]}/{f[4]} MB"}
    return out


def _updates():
    if shutil.which("apt"):
        n = _run("apt list --upgradable 2>/dev/null | grep -c upgradable", 40, shell=True)
    elif shutil.which("checkupdates"):
        n = str(len(_run(["checkupdates"], 60).splitlines()))
    elif shutil.which("dnf"):
        n = str(len([l for l in _run(["dnf", "-q", "check-update"], 90).splitlines() if l.strip()]))
    else:
        n = ""
    fp = len(_run(["flatpak", "remote-ls", "--updates"], 40).splitlines()) if shutil.which("flatpak") else 0
    return (int(n) if n.isdigit() else None), fp


def _big_files():
    out = _run(["find", str(HOME), "-xdev", "-type", "f", "-size", "+700M", "-not", "-path", "*/.local/share/Steam/*",
                "-not", "-path", "*/.steam/*", "-not", "-path", "*/.lumen/lab/*", "-printf", "%s\t%p\n"], timeout=40)
    files = []
    for line in out.splitlines():
        s, _, p = line.partition("\t")
        if s.isdigit():
            files.append({"pfad": p.replace(str(HOME), "~", 1), "größe": human(int(s)), "_b": int(s)})
    return sorted(files, key=lambda x: -x["_b"])[:10]


def _big_dirs():
    out = _run(f"du -xb --max-depth=1 {HOME!s} 2>/dev/null | sort -rn | head -12", 60, shell=True)
    dirs = []
    for line in out.splitlines()[1:]:
        s, _, p = line.partition("\t")
        if s.isdigit() and int(s) > 300_000_000:
            dirs.append({"pfad": p.replace(str(HOME), "~", 1), "größe": human(int(s))})
    return dirs[:8]


PROGRESS = {"schritt": None, "nr": 0, "von": 5}


def _safe_int(x, default=0):
    try:
        return int(str(x).strip().rstrip("%"))
    except Exception:
        return default


def scan(progress=None):
    """Untersucht den PC. Jeder Bereich ist abgesichert – ein Fehler in einem Teil stoppt nicht den ganzen Check."""
    t0 = time.time()
    findings, problems = [], []
    data = {"disks": [], "big_files": [], "big_dirs": [], "ram": {}, "mem_hogs": [], "cpu_hogs": [], "temps": {}, "gpu": None,
            "auto": [], "boot_time": None, "blame": []}

    def add(cat, level, text, fix=None, arg=None, size=0, detail=None):
        findings.append({"kategorie": cat, "stufe": level, "text": text, "fix": fix, "arg": arg, "größe": size,
                         "größe_text": human(size) if size > 1000 else None, "detail": detail})

    def step(nr, name):
        PROGRESS.update(schritt=name, nr=nr)
        if progress:
            progress(nr, name)

    def storage():
        for line in _run("df -P -x tmpfs -x devtmpfs -x squashfs -x overlay -x efivarfs -x fuse.portal 2>/dev/null", shell=True).splitlines()[1:]:
            f = line.split()
            if len(f) < 6:
                continue
            mount = " ".join(f[5:])
            if mount.startswith(("/snap", "/boot/efi", "/var/lib/docker", "/run", "/sys", "/proc", "/dev")):
                continue
            used, avail, pct = _safe_int(f[2], -1), _safe_int(f[3], -1), _safe_int(f[4], -1)
            if used < 0 or avail < 0 or pct < 0 or used + avail < 1_000_000:  # Pseudo-Dateisysteme / winzige Partitionen
                continue
            used, avail = used * 1024, avail * 1024
            data["disks"].append({"mount": mount, "belegt_prozent": pct, "frei": human(avail), "gesamt": human(used + avail)})
            if pct >= 90:
                add("Speicher", "rot", f"Laufwerk {mount} ist zu {pct} % voll (nur noch {human(avail)} frei).")
            elif pct >= 80:
                add("Speicher", "gelb", f"Laufwerk {mount} ist zu {pct} % voll.")

    def caches():
        for fid in ("trash", "thumbs", "browser_cache", "pip", "npm", "docker", "apt", "pacman", "dnf", "journal", "snap"):
            try:
                size = _measure_fix(fid)
            except Exception:
                continue
            threshold = {"journal": 500e6, "thumbs": 150e6, "browser_cache": 400e6}.get(fid, 200e6)
            if size >= threshold:
                add("Speicher", "gelb" if size >= 2e9 else "info", FIXES[fid][0] + f" – {FIXES[fid][1]}", fid, size=size)

    def big():
        data["big_files"] = _big_files()
        data["big_dirs"] = _big_dirs()
        if data["big_files"]:
            add("Speicher", "info", f"{len(data['big_files'])} große Dateien (über 700 MB) in deinem Home-Ordner – evtl. alte Downloads/ISOs/Videos.",
                detail=[f"{x['größe']}  {x['pfad']}" for x in data["big_files"]])
        dl = _du(HOME / "Downloads") or _du(HOME / "Download")
        if dl > 5e9:
            add("Speicher", "info", f"Der Downloads-Ordner ist {human(dl)} groß – vielleicht mal ausmisten?")

    def performance():
        mi = {}
        for l in open("/proc/meminfo"):
            if ":" in l and len(l.split()) >= 2:
                mi[l.split(":")[0]] = _safe_int(l.split()[1]) * 1024
        tot, av = mi.get("MemTotal") or 1, mi.get("MemAvailable", 0)
        swap_used = mi.get("SwapTotal", 0) - mi.get("SwapFree", 0)
        ram = {"gesamt": human(tot), "frei": human(av), "belegt_prozent": round(100 - av / tot * 100), "swap_belegt": human(max(0, swap_used))}
        data["ram"] = ram
        if ram["belegt_prozent"] >= 90:
            add("Leistung", "rot", f"Der Arbeitsspeicher ist zu {ram['belegt_prozent']} % voll – das macht den PC langsam.")
        elif ram["belegt_prozent"] >= 80:
            add("Leistung", "gelb", f"Der Arbeitsspeicher ist zu {ram['belegt_prozent']} % belegt.")
        if swap_used > 1e9 and ram["belegt_prozent"] > 70:
            add("Leistung", "gelb", f"{human(swap_used)} werden in den Auslagerungsspeicher geschoben (langsam).")
        data["mem_hogs"], data["cpu_hogs"] = _procs("%mem"), _procs("%cpu")
        me = os.getpid()
        for p in data["mem_hogs"][:3]:
            if p["ram_prozent"] >= 15 and p["pid"] != me and p["name"] not in ("Xorg", "gnome-shell", "kwin_x11", "kwin_wayland", "plasmashell", "systemd"):
                add("Leistung", "gelb" if p["ram_prozent"] >= 25 else "info", f"„{p['name']}“ braucht {p['ram']} RAM ({p['ram_prozent']} %).", "kill", p["pid"])
        for p in data["cpu_hogs"][:3]:
            if p["cpu_prozent"] >= 60 and p["pid"] != me and p["name"] not in ("ps",):
                add("Leistung", "gelb", f"„{p['name']}“ lastet die CPU mit {p['cpu_prozent']:.0f} % aus.", "kill", p["pid"])
        temps = _temps()
        data["gpu"] = temps.pop("_gpu", None)
        data["temps"] = temps
        for k, v in temps.items():
            if v >= 90:
                add("Leistung", "rot", f"Sehr heiß: {k} {v} °C – Lüfter/Staub prüfen.")
            elif v >= 80:
                add("Leistung", "gelb", f"Ziemlich warm: {k} {v} °C.")

    def autostart():
        data["auto"] = _autostart()
        for a in data["auto"]:
            add("Autostart", "info", f"Startet automatisch: {a['name']} ({a['art']})", "autostart", a["id"])
        boot = _run(["systemd-analyze"], 15)
        m = re.search(r"=\s*([\d.min ]+s)", boot.replace("\n", " "))
        data["boot_time"] = m.group(1).strip() if m else None
        data["blame"] = [l.strip() for l in _run(["systemd-analyze", "blame", "--no-pager"], 15).splitlines()[:5]] if boot else []

    def system():
        upd, fp_upd = _updates()
        if upd:
            add("System", "gelb" if upd >= 30 else "info", f"{upd} System-Updates verfügbar.")
        if fp_upd:
            add("System", "info", f"{fp_upd} Flatpak-Updates verfügbar (flatpak update).")
        if Path("/var/run/reboot-required").exists():
            add("System", "gelb", "Ein Neustart ist nötig, damit Updates aktiv werden.")
        failed = [l.split()[0] for l in _run(["systemctl", "--failed", "--no-legend", "--plain"]).splitlines() if l.split()]
        for f in failed[:5]:
            add("System", "gelb", f"Dienst fehlgeschlagen: {f}")
        try:
            bat = next(Path("/sys/class/power_supply").glob("BAT*"), None)
            if bat:
                names = ("energy_full", "energy_full_design") if (bat / "energy_full").exists() else ("charge_full", "charge_full_design")
                full, design = [_safe_int((bat / n).read_text()) for n in names]
                if design:
                    health = round(full / design * 100)
                    if health < 70:
                        add("System", "gelb", f"Der Akku hat nur noch {health} % seiner ursprünglichen Kapazität.")
        except Exception:
            pass

    steps = [("Laufwerke", storage), ("Caches & Papierkorb", caches), ("Große Dateien", big), ("Leistung & Temperaturen", performance),
             ("Autostart", autostart), ("Updates & Dienste", system)]
    PROGRESS["von"] = len(steps)
    for i, (name, fn) in enumerate(steps):
        step(i + 1, name)
        try:
            fn()
        except Exception as e:
            problems.append(f"{name}: {type(e).__name__}: {e}")
            print("PC-Doktor –", name, ":", e)
    PROGRESS.update(schritt=None, nr=0)

    pts = {"rot": 15, "gelb": 6, "info": 1}
    score = max(5, 100 - sum(pts[f["stufe"]] for f in findings if f["kategorie"] != "Autostart") - max(0, len(data["auto"]) - 6) * 2)
    freeable = sum(f["größe"] for f in findings if f["fix"] and FIXES.get(f["fix"], (0, 0, False))[2] and f["größe"])
    rep = {"punkte": score, "note": "Top 💚" if score >= 85 else "Okay 💛" if score >= 65 else "Braucht Pflege 🧡" if score >= 40 else "Kritisch ❤️",
           "befunde": findings, "laufwerke": data["disks"], "ram": data["ram"], "top_ram": data["mem_hogs"][:5], "top_cpu": data["cpu_hogs"][:5],
           "temperaturen": data["temps"], "gpu": data["gpu"], "autostart": data["auto"], "startzeit": data["boot_time"],
           "langsamste_dienste": data["blame"], "große_ordner": data["big_dirs"],
           "große_dateien": [{k: v for k, v in f.items() if k != "_b"} for f in data["big_files"]], "frei_machbar": human(freeable),
           "frei_machbar_b": freeable, "dauer_s": round(time.time() - t0, 1), "zeit": time.strftime("%d.%m.%Y %H:%M"),
           "teilfehler": problems}
    LAST["report"] = rep
    return rep


def safe_fix_ids(report):
    return [f["fix"] for f in report["befunde"] if f["fix"] and FIXES[f["fix"]][2] and not FIXES[f["fix"]][3]]


def summary_for_ai(rep):
    """Kompakt für die KI (ohne riesige Listen)."""
    return {k: rep[k] for k in ("punkte", "note", "laufwerke", "ram", "temperaturen", "gpu", "startzeit", "langsamste_dienste",
                                "große_ordner", "frei_machbar")} | {
        "befunde": [{"kategorie": f["kategorie"], "stufe": f["stufe"], "text": f["text"], "fix": f["fix"], "arg": f["arg"],
                     "größe": f["größe_text"]} for f in rep["befunde"]],
        "aufräum_aktionen": {k: v[0] + (" (Admin-Passwort-Fenster)" if v[3] else "") for k, v in FIXES.items()}}
