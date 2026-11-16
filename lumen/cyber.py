"""Lumen – Cybersecurity-Werkzeuge (nur für eigene Geräte, Netze und Webseiten).

A) Schutz-Scanner: Datei-/Download-Scan (ClamAV, VirusTotal-Hash, Heuristik), Geheimnis-Scanner (geleakte Keys/Passwörter in
   eigenen Ordnern), Integritäts-Wächter (veränderte System-/Autostart-Dateien, Rootkit-Hinweise), rkhunter/chkrootkit
B) Lücken finden: CVE-Check installierter Pakete (OSV.dev), TLS-Check, Härtungs-Aktionen (Firewall, SSH, fail2ban, Auto-Updates)
C) Werkzeugkasten: Kodieren/Dekodieren, Hashes, Hash-Erkennung, JWT lesen, Passwort-Generator, IP-Rechner
D) Programme auf dem PC: nmap, tshark/tcpdump (Wireshark), Lynis, ClamAV, testssl.sh/sslscan, Nikto, WhatWeb, Nuclei
   – Lumen ruft sie mit sicheren Voreinstellungen auf, nur gegen eigene Ziele, und erklärt die Ergebnisse.

Bewusst NICHT eingebunden: Passwort-Knacker/Brute-Force (hydra, john, hashcat), Exploit-Frameworks (metasploit),
WLAN-Angriffe (aircrack-ng) – die gehören in ein eigenes Übungslabor, nicht in einen Assistenten mit Werkzeugzugriff.
"""
import base64
import binascii
import hashlib
import ipaddress
import json
import math
import os
import re
import secrets
import shutil
import socket
import ssl
import string
import subprocess
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import integrations as ig

HOME = Path.home()
DATA = HOME / ".lumen" / "cyber.json"
OUT_DIR = HOME / "Lumen" / "Sicherheit"
LOCK = threading.RLock()
ENV_C = {**os.environ, "LC_ALL": "C", "LANG": "C"}
own_check = None          # von lumen.py gesetzt: (ziel) → (host, ip) oder RuntimeError
own_domains = lambda: []  # von lumen.py gesetzt: eigene Domains aus den Einstellungen
vt_key = lambda: ""


def _run(cmd, timeout=120, input_=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=ENV_C,
                           stdin=subprocess.DEVNULL if input_ is None else None, input=input_)
        return r.stdout or "", r.stderr or "", r.returncode
    except FileNotFoundError:
        return "", "nicht installiert", 127
    except subprocess.TimeoutExpired:
        return "", "Zeitüberschreitung", 124


def _load():
    try:
        d = json.loads(DATA.read_text("utf-8"))
    except Exception:
        d = {}
    d.setdefault("baseline", {})
    d.setdefault("baseline_zeit", None)
    d.setdefault("downloads_seen", {})
    return d


def _save(d):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    tmp.replace(DATA)


def _f(stufe, titel, text="", tipp=""):
    return {"stufe": stufe, "titel": titel, "text": text, "tipp": tipp}


# ================================================================ D) Programme auf dem PC
TOOLS = {  # name: (Befehl(e), Zweck, Paket, Art)
    "nmap": (["nmap"], "Netzwerk- und Port-Scanner", "nmap", "eingebunden"),
    "tshark": (["tshark"], "Wireshark im Terminal – Netzwerkverkehr mitschneiden", "tshark", "eingebunden"),
    "wireshark": (["wireshark"], "Netzwerkverkehr grafisch ansehen", "wireshark", "öffnen"),
    "tcpdump": (["tcpdump"], "Netzwerkverkehr mitschneiden", "tcpdump", "eingebunden"),
    "lynis": (["lynis"], "System-Sicherheitsaudit", "lynis", "eingebunden"),
    "clamav": (["clamscan", "clamdscan"], "Virenscanner", "clamav", "eingebunden"),
    "rkhunter": (["rkhunter"], "Rootkit-Suche", "rkhunter", "eingebunden"),
    "chkrootkit": (["chkrootkit"], "Rootkit-Suche", "chkrootkit", "eingebunden"),
    "testssl": (["testssl", "testssl.sh"], "TLS/SSL-Konfiguration gründlich prüfen", "testssl.sh", "eingebunden"),
    "sslscan": (["sslscan"], "TLS/SSL-Protokolle und Verschlüsselungen", "sslscan", "eingebunden"),
    "nikto": (["nikto"], "Webserver-Schwachstellen-Scanner", "nikto", "eingebunden"),
    "whatweb": (["whatweb"], "Web-Technik erkennen", "whatweb", "eingebunden"),
    "nuclei": (["nuclei"], "Vorlagen-basierter Schwachstellen-Scanner", "(github.com/projectdiscovery/nuclei)", "eingebunden"),
    "ufw": (["ufw"], "Einfache Firewall", "ufw", "eingebunden"),
    "fail2ban": (["fail2ban-client"], "Sperrt IPs nach vielen Fehlversuchen", "fail2ban", "eingebunden"),
    "usbguard": (["usbguard"], "Unbekannte USB-Geräte blockieren", "usbguard", "info"),
    "aide": (["aide"], "Datei-Integrität (professionell)", "aide", "info"),
    "gobuster": (["gobuster"], "Verzeichnisse auf Webservern finden", "gobuster", "info"),
    "ffuf": (["ffuf"], "Web-Fuzzer", "ffuf", "info"),
    "sqlmap": (["sqlmap"], "SQL-Injection-Tester", "sqlmap", "labor"),
    "hydra": (["hydra"], "Login-Brute-Force", "hydra", "labor"),
    "john": (["john"], "Passwort-Knacker", "john", "labor"),
    "hashcat": (["hashcat"], "Passwort-Knacker (GPU)", "hashcat", "labor"),
    "aircrack-ng": (["aircrack-ng"], "WLAN-Angriffe", "aircrack-ng", "labor"),
    "metasploit": (["msfconsole"], "Exploit-Framework", "metasploit-framework", "labor"),
    "burpsuite": (["burpsuite"], "Web-Proxy für Tests", "burpsuite", "labor"),
    "zaproxy": (["zaproxy", "owasp-zap"], "Web-Sicherheits-Scanner (OWASP ZAP)", "zaproxy", "labor"),
}


def _which(cmds):
    for c in cmds:
        p = shutil.which(c)
        if p:
            return p
    return None


def inventory():
    out = []
    for name, (cmds, what, pkg, kind) in TOOLS.items():
        path = _which(cmds)
        out.append({"name": name, "zweck": what, "installiert": bool(path), "pfad": path or "", "paket": pkg, "art": kind,
                    "hinweis": {"eingebunden": "Lumen kann es für dich bedienen (nur eigene Ziele).",
                                "öffnen": "Lumen öffnet es oder einen Mitschnitt darin.",
                                "info": "Erkannt – bedienen musst du es selbst.",
                                "labor": "Angriffswerkzeug: Lumen bedient es nicht. Üben im eigenen Labor (z. B. Juice Shop, TryHackMe) – "
                                         "der Hacking-Lernpfad erklärt es."}[kind]})
    pm = "apt" if shutil.which("apt-get") else "dnf" if shutil.which("dnf") else "pacman" if shutil.which("pacman") else None
    missing = [t["paket"] for t in out if not t["installiert"] and t["art"] == "eingebunden" and not t["paket"].startswith("(")]
    inst = {"apt": "sudo apt install ", "dnf": "sudo dnf install ", "pacman": "sudo pacman -S "}.get(pm, "")
    return {"werkzeuge": out, "installieren": (inst + " ".join(dict.fromkeys(missing))) if inst and missing else ""}


def _own(target):
    if not own_check:
        raise RuntimeError("Zielprüfung nicht verfügbar.")
    return own_check(target)


def _own_web(target):
    """Webseiten-Scans nur für eigene Domains (Einstellungen), eigene Server, Heimnetz und localhost."""
    t = str(target or "").strip()
    host = urllib.parse.urlparse(t if "://" in t else "http://" + t).hostname or ""
    doms = [d.lower().strip().lstrip("*.") for d in own_domains() if d.strip()]
    if any(host == d or host.endswith("." + d) for d in doms):
        return host
    try:
        h, ip = _own(host)
        return host
    except RuntimeError:
        raise RuntimeError(f"„{host}“ ist nicht als deine eigene Seite eingetragen. Webseiten-Scanner (Nikto, Nuclei, testssl …) "
                           f"laufen nur gegen eigene Domains – trag sie unter Sicherheit → Werkzeuge → „Meine Domains“ ein. "
                           f"Fremde Seiten nur mit schriftlicher Erlaubnis des Betreibers.")


# ---------------------------------------------------------------- nmap
NMAP_PROFILES = {
    "schnell": (["-T4", "-F"], "Top-100-Ports, schnell"),
    "standard": (["-T4", "-sV", "--version-light"], "Top-1000-Ports mit Dienst-Erkennung"),
    "gründlich": (["-T4", "-sV", "-sC", "-p-"], "alle 65535 Ports, Dienste + sichere Standard-Skripte (dauert)"),
    "sicher_skripte": (["-T4", "-sV", "--script", "default and safe"], "Dienste + nur als „safe“ markierte NSE-Skripte"),
    "schwachstellen": (["-T4", "-sV", "--script", "vulners"], "Dienst-Versionen gegen bekannte CVEs (Skript vulners, falls vorhanden)"),
    "netz_finden": (["-sn"], "Welche Geräte sind im Netz? (nur Ping, keine Ports)"),
}


def nmap_scan(target, profil="standard", ports=None):
    exe = shutil.which("nmap")
    if not exe:
        raise RuntimeError("nmap ist nicht installiert: sudo apt install nmap")
    if profil not in NMAP_PROFILES:
        raise RuntimeError("Profile: " + ", ".join(NMAP_PROFILES))
    t = str(target or "").strip()
    if profil == "netz_finden":
        net = ipaddress.ip_network(t, strict=False) if "/" in t else None
        if not net or not net.is_private or net.num_addresses > 4096:
            raise RuntimeError("Netz-Suche nur für dein privates Netz, z. B. 192.168.1.0/24.")
        scan_t = str(net)
    else:
        host, ip = _own(t)
        scan_t = ip
    args = list(NMAP_PROFILES[profil][0])
    if ports and profil != "netz_finden":
        ps = ",".join(str(int(p)) for p in ports if 0 < int(p) < 65536)[:400]
        args = [a for a in args if a not in ("-F", "-p-")] + ["-p", ps]
    out, err, rc = _run([exe, *args, "-oX", "-", "--host-timeout", "15m", scan_t], timeout=1800 if profil == "gründlich" else 600)
    if not out.strip().startswith("<?xml"):
        raise RuntimeError("nmap-Fehler: " + (err.strip()[:300] or "keine Ausgabe"))
    root = ET.fromstring(out)
    hosts = []
    for h in root.findall("host"):
        se = h.find("status")
        st = se.get("state", "?") if se is not None else "?"
        addr = next((a.get("addr") for a in h.findall("address") if a.get("addrtype") in ("ipv4", "ipv6")), "")
        mac = next(((a.get("addr"), a.get("vendor", "")) for a in h.findall("address") if a.get("addrtype") == "mac"), None)
        name = next((n.get("name") for n in h.findall("hostnames/hostname")), "")
        ports_ = []
        for p in h.findall("ports/port"):
            s = p.find("state")
            if s is None or s.get("state") not in ("open", "open|filtered"):
                continue
            sv = p.find("service")
            svc = {k: sv.get(k) for k in ("name", "product", "version", "extrainfo") if sv is not None and sv.get(k)}
            scripts = [{"id": sc.get("id"), "ausgabe": (sc.get("output") or "").strip()[:600]} for sc in p.findall("script")]
            ports_.append({"port": int(p.get("portid")), "proto": p.get("protocol"), "zustand": s.get("state"),
                           "dienst": " ".join(x for x in (svc.get("name"), svc.get("product"), svc.get("version"), svc.get("extrainfo")) if x),
                           **({"skripte": scripts} if scripts else {})})
        osm = [o.get("name") for o in h.findall("os/osmatch")][:2]
        hosts.append({"ip": addr, "name": name, "status": st, **({"mac": mac[0], "hersteller": mac[1]} if mac else {}),
                      "offene_ports": ports_, **({"system": osm} if osm else {})})
    fin = root.find("runstats/finished")
    return {"werkzeug": "nmap", "profil": profil, "beschreibung": NMAP_PROFILES[profil][1], "ziel": t, "hosts": hosts,
            "dauer_s": float(fin.get("elapsed", 0)) if fin is not None else None,
            "hinweis": "Nur eigene Geräte scannen. Ports, die du nicht kennst: Dienst stoppen oder per Firewall sperren."}


# ---------------------------------------------------------------- tshark / tcpdump (Wireshark)
def interfaces():
    exe = shutil.which("tshark")
    if exe:
        out, err, rc = _run([exe, "-D"], 20)
        if rc == 0:
            return [re.sub(r"^\d+\.\s*", "", l).split(" ")[0] for l in out.splitlines() if l.strip()]
    return sorted(p.name for p in Path("/sys/class/net").iterdir()) if Path("/sys/class/net").exists() else []


def capture(seconds=20, interface=None, filter_=""):
    """Mitschnitt auf DEINER Netzwerkkarte (kein Monitor-Modus): Protokolle, Gesprächspartner, DNS-Namen. Speichert .pcapng."""
    seconds = max(5, min(int(seconds or 20), 300))
    exe = shutil.which("tshark")
    if not exe:
        raise RuntimeError("tshark (Wireshark im Terminal) fehlt: sudo apt install tshark – bei der Frage „Dürfen Nicht-Admins "
                           "mitschneiden?“ Ja wählen und dich der Gruppe wireshark hinzufügen (sudo usermod -aG wireshark $USER, neu anmelden).")
    if filter_ and not re.fullmatch(r"[\w\s.:/()!=<>&|\-]{1,200}", filter_):
        raise RuntimeError("Ungültiger Filter.")
    iface = interface or _default_iface()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    f = OUT_DIR / f"mitschnitt-{datetime.now():%Y%m%d-%H%M%S}.pcapng"
    cmd = [exe, "-i", iface, "-a", f"duration:{seconds}", "-w", str(f), "-q"] + (["-f", filter_] if filter_ else [])
    out, err, rc = _run(cmd, seconds + 30)
    if not f.exists() or f.stat().st_size < 100:
        msg = err.strip()
        if "ermission" in msg or "don't have permission" in msg.lower():
            msg = "Keine Berechtigung zum Mitschneiden. Einmal: sudo usermod -aG wireshark $USER (dann ab- und anmelden)."
        raise RuntimeError("Mitschnitt fehlgeschlagen: " + msg[:300])
    return {**analyze_pcap(f), "datei": str(f), "sekunden": seconds, "schnittstelle": iface}


def _default_iface():
    out, err, rc = _run(["ip", "-j", "route", "get", "1.1.1.1"], 10)
    try:
        return json.loads(out)[0]["dev"]
    except Exception:
        return "any"


def analyze_pcap(path):
    exe = shutil.which("tshark")
    if not exe:
        raise RuntimeError("tshark fehlt.")
    p = str(Path(path).expanduser())
    if not Path(p).exists():
        raise RuntimeError("Datei nicht gefunden.")
    out, err, rc = _run([exe, "-r", p, "-q", "-z", "io,phs", "-z", "conv,ip"], 120)
    protos, convs = [], []
    sec = None
    for line in out.splitlines():
        if "Protocol Hierarchy Statistics" in line:
            sec = "phs"
            continue
        if "IPv4 Conversations" in line:
            sec = "conv"
            continue
        if sec == "phs":
            m = re.match(r"^(\s*)([\w.-]+)\s+frames:(\d+)\s+bytes:(\d+)", line)
            if m and len(m.group(1)) <= 8:
                protos.append({"protokoll": m.group(2), "pakete": int(m.group(3)), "bytes": int(m.group(4)), "ebene": len(m.group(1)) // 2})
        if sec == "conv":
            m = re.match(r"^([\d.]+)\s+<->\s+([\d.]+)\s+(\d+)\s+(\d+)\s*\S*\s+(\d+)\s+(\d+)\s*\S*\s+(\d+)\s+(\d+)", line)
            if m:
                convs.append({"a": m.group(1), "b": m.group(2), "pakete": int(m.group(7)), "bytes": int(m.group(8))})
    dns_out, _, _ = _run([exe, "-r", p, "-Y", "dns.flags.response == 0", "-T", "fields", "-e", "dns.qry.name"], 120)
    names = {}
    for n in dns_out.split():
        names[n] = names.get(n, 0) + 1
    sni_out, _, _ = _run([exe, "-r", p, "-Y", "tls.handshake.extensions_server_name", "-T", "fields", "-e", "tls.handshake.extensions_server_name"], 120)
    sni = {}
    for n in sni_out.split():
        sni[n] = sni.get(n, 0) + 1
    plain = [x for x in protos if x["protokoll"] in ("http", "ftp", "telnet", "pop", "imap", "smtp") and x["pakete"]]
    convs.sort(key=lambda c: -c["bytes"])
    total = next((x["pakete"] for x in protos if x["ebene"] == 0), sum(x["pakete"] for x in protos if x["ebene"] == 0))
    return {"pakete": total, "protokolle": protos[:25], "gesprächspartner": convs[:15],
            "dns_namen": sorted(names.items(), key=lambda kv: -kv[1])[:30], "https_ziele": sorted(sni.items(), key=lambda kv: -kv[1])[:30],
            "unverschlüsselt": [x["protokoll"] for x in plain],
            "hinweis": "Zusammenfassung ohne Inhalte. Die Datei kannst du in Wireshark öffnen." +
                       (" ⚠️ Unverschlüsselter Verkehr gefunden – Passwörter könnten im Klartext übertragen werden." if plain else "")}


def open_wireshark(path=None):
    exe = shutil.which("wireshark")
    if not exe:
        raise RuntimeError("Wireshark ist nicht installiert: sudo apt install wireshark")
    args = [exe] + ([str(Path(path).expanduser())] if path else [])
    subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return "Wireshark geöffnet."


def connections():
    """Welche Programme reden gerade mit wem im Internet? (ss -tunap)"""
    out, err, rc = _run(["ss", "-tunapH"], 20)
    rows, by_prog = [], {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        proto, state, local, peer = parts[0], parts[1], parts[4], parts[5]
        if state not in ("ESTAB", "SYN-SENT", "UNCONN") or peer.startswith(("*", "0.0.0.0", "[::]")):
            continue
        host = peer.rsplit(":", 1)[0].strip("[]")
        try:
            ipo = ipaddress.ip_address(host.split("%")[0])
        except ValueError:
            continue
        if ipo.is_loopback:
            continue
        prog = (re.search(r'users:\(\("([^"]+)",pid=(\d+)', line) or [None, "?", ""])
        name = prog[1] if prog[1] else "?"
        rows.append({"programm": name, "pid": prog[2] if prog[2] else "", "proto": proto, "ziel": peer, "privat": ipo.is_private})
        by_prog.setdefault(name, set()).add(host)
    public = [r for r in rows if not r["privat"]]
    names = {}
    for r in public[:60]:
        ip = r["ziel"].rsplit(":", 1)[0].strip("[]")
        if ip not in names:
            try:
                names[ip] = socket.gethostbyaddr(ip)[0]
            except Exception:
                names[ip] = ""
        r["name"] = names[ip]
    return {"verbindungen": rows[:150], "ins_internet": len(public),
            "programme": sorted(({"programm": k, "ziele": len(v)} for k, v in by_prog.items()), key=lambda x: -x["ziele"]),
            "hinweis": "„?“ = Programm eines anderen Benutzers (für Details: sudo ss -tunap). Unbekanntes Programm mit vielen Zielen → nachfragen."}


# ---------------------------------------------------------------- Lynis
def lynis_audit():
    exe = shutil.which("lynis")
    if not exe:
        raise RuntimeError("Lynis ist nicht installiert: sudo apt install lynis")
    rep = Path(os.environ.get("TMPDIR", "/tmp")) / f"lumen-lynis-{os.getpid()}.dat"
    out, err, rc = _run([exe, "audit", "system", "--quick", "--no-colors", "--report-file", str(rep)], 900)
    data = rep.read_text("utf-8", "replace") if rep.exists() else ""
    rep.unlink(missing_ok=True)
    idx = re.search(r"hardening_index=(\d+)", data)
    warn = [w.split("|") for w in re.findall(r"^warning\[\]=(.+)$", data, re.M)]
    sugg = [s.split("|") for s in re.findall(r"^suggestion\[\]=(.+)$", data, re.M)]
    if not data:
        m = re.search(r"Hardening index\s*:\s*(\d+)", out)
        idx = m
    return {"werkzeug": "lynis", "härtungs_index": int(idx.group(1)) if idx else None,
            "warnungen": [{"id": w[0], "text": w[1] if len(w) > 1 else ""} for w in warn][:30],
            "vorschläge": [{"id": s[0], "text": s[1] if len(s) > 1 else ""} for s in sugg][:40],
            "hinweis": "Ohne Admin-Rechte prüft Lynis nicht alles. Vollständig: sudo lynis audit system"}


# ================================================================ A) Schutz-Scanner
DANGER_EXT = {".exe", ".scr", ".bat", ".cmd", ".com", ".pif", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".hta", ".msi", ".ps1", ".lnk",
              ".jar", ".apk", ".appimage", ".deb", ".rpm", ".sh", ".run", ".bin", ".desktop", ".iso", ".img"}
OFFICE_MACRO = {".docm", ".xlsm", ".pptm", ".dotm", ".xltm"}
OFFICE = {".doc", ".xls", ".ppt", ".docx", ".xlsx", ".pptx"} | OFFICE_MACRO
DOC_LIKE = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png", ".txt", ".mp3", ".mp4", ".zip", ".rar"}
MAGIC = {b"MZ": "Windows-Programm", b"\x7fELF": "Linux-Programm", b"#!": "Skript", b"PK\x03\x04": "ZIP/Office", b"%PDF": "PDF",
         b"\xd0\xcf\x11\xe0": "altes Office (OLE)", b"Rar!": "RAR", b"7z\xbc\xaf": "7-Zip", b"\x1f\x8b": "gzip"}


def _magic(p):
    try:
        head = p.read_bytes()[:8] if p.stat().st_size < 64 else open(p, "rb").read(8)
    except Exception:
        return ""
    return next((v for k, v in MAGIC.items() if head.startswith(k)), "")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_file(p):
    """Heuristik ohne Virenscanner: Tarnung, Makros, PDF-Aktionen, ausführbar."""
    p = Path(p)
    flags = []
    name = p.name.lower()
    suf = p.suffix.lower()
    parts = name.split(".")
    if len(parts) >= 3 and "." + parts[-2] in DOC_LIKE and suf in DANGER_EXT:
        flags.append(("kritisch", f"Doppelte Endung „.{parts[-2]}{suf}“ – typische Tarnung von Schadprogrammen."))
    if re.search(r"[‮‏‎]", p.name):
        flags.append(("kritisch", "Unsichtbare Richtungszeichen im Namen – Dateiname wird gefälscht angezeigt."))
    kind = _magic(p)
    if kind in ("Windows-Programm", "Linux-Programm") and suf in DOC_LIKE:
        flags.append(("kritisch", f"Endung {suf}, aber eigentlich ein {kind}."))
    if suf in DANGER_EXT:
        flags.append(("warn" if suf in (".exe", ".scr", ".vbs", ".js", ".hta", ".ps1", ".lnk", ".bat", ".cmd", ".jar", ".desktop") else "info",
                      f"Ausführbare Art ({suf}) – nur öffnen, wenn du die Quelle kennst."))
    try:
        if os.access(p, os.X_OK) and p.is_file() and suf not in (".sh", ".appimage", ".run", ".bin") and kind not in ("Linux-Programm", "Skript"):
            flags.append(("info", "Datei ist als ausführbar markiert."))
    except Exception:
        pass
    try:
        size = p.stat().st_size
        if suf in OFFICE_MACRO:
            flags.append(("warn", "Office-Datei mit Makros (.…m) – Makros nur aktivieren, wenn du sie erwartest."))
        elif suf in OFFICE and kind == "ZIP/Office" and size < 80 * 1024 * 1024:
            with zipfile.ZipFile(p) as z:
                n = z.namelist()
                if any("vbaProject.bin" in x for x in n):
                    flags.append(("warn", "Enthält Makros (vbaProject.bin) – nicht aktivieren, wenn unerwartet."))
                if any(x.endswith(".rels") and b"oleObject" in z.read(x)[:200000] and b"TargetMode=\"External\"" in z.read(x)[:200000] for x in n if x.endswith(".rels")):
                    flags.append(("warn", "Lädt externe Inhalte nach (Remote-Template/OLE) – häufige Angriffsart."))
        elif kind == "altes Office (OLE)" and size < 50 * 1024 * 1024:
            data = p.read_bytes()
            if b"VBA" in data and (b"Auto_Open" in data or b"AutoOpen" in data or b"Document_Open" in data or b"Workbook_Open" in data):
                flags.append(("kritisch", "Makro, das beim Öffnen automatisch startet."))
            elif b"_VBA_PROJECT" in data:
                flags.append(("warn", "Enthält Makros."))
        elif kind == "PDF" and size < 50 * 1024 * 1024:
            data = p.read_bytes()
            for k, why in ((b"/JavaScript", "JavaScript"), (b"/Launch", "startet Programme (/Launch)"), (b"/EmbeddedFile", "eingebettete Dateien"),
                           (b"/OpenAction", "Aktion beim Öffnen"), (b"/AA", "automatische Aktionen")):
                if k in data:
                    flags.append(("warn" if k in (b"/JavaScript", b"/Launch") else "info", f"PDF enthält {why}."))
        elif kind == "ZIP/Office" and suf in (".zip", ".jar", ".apk") and size < 200 * 1024 * 1024:
            with zipfile.ZipFile(p) as z:
                inner = [x for x in z.namelist() if Path(x).suffix.lower() in (".exe", ".scr", ".vbs", ".js", ".lnk", ".hta", ".bat", ".ps1", ".iso")]
                if inner:
                    flags.append(("warn", f"Archiv enthält ausführbare Dateien: {', '.join(inner[:4])}"))
                if any(zi.flag_bits & 0x1 for zi in z.infolist()):
                    flags.append(("info", "Passwortgeschütztes Archiv – Virenscanner sehen nicht hinein (Trick von Angreifern)."))
    except Exception:
        pass
    return kind, flags


def clam_scan(paths, recursive=True):
    exe = _which(["clamdscan", "clamscan"])
    if not exe:
        return None
    args = [exe, "--no-summary", "--infected"] + (["-r"] if recursive and "clamscan" in exe and "clamd" not in exe else []) + \
           (["--fdpass"] if "clamdscan" in exe else []) + [str(p) for p in paths]
    out, err, rc = _run(args, 3600)
    hits = []
    for line in out.splitlines():
        m = re.match(r"^(.+): (.+) FOUND$", line.strip())
        if m:
            hits.append({"datei": m.group(1), "fund": m.group(2)})
    if rc == 2 and not hits:
        msg = (err or out)
        if "No supported database" in msg or "cli_loaddbdir" in msg or "Can't connect to clamd" in msg and "clamdscan" in exe:
            if "clamdscan" in exe and shutil.which("clamscan"):
                return clam_scan.__wrapped__(paths, recursive) if hasattr(clam_scan, "__wrapped__") else {"fehler": "clamd läuft nicht – sudo systemctl enable --now clamav-daemon"}
            return {"fehler": "ClamAV hat noch keine Virensignaturen – einmal: sudo freshclam (oder Sicherheits-Zentrale → Lücken → „ClamAV installieren“)"}
        return {"fehler": msg.strip()[:200]}
    return {"funde": hits, "programm": Path(exe).name}


def file_scan(path="~/Downloads", recent_days=None, use_vt=True, limit=400):
    """Prüft eine Datei oder einen Ordner: ClamAV (falls da), Heuristik, VirusTotal-Hash (falls Key; nichts wird hochgeladen)."""
    base = Path(str(path or "~/Downloads")).expanduser()
    if not base.exists():
        raise RuntimeError(f"{base} gibt es nicht.")
    files = [base] if base.is_file() else []
    if base.is_dir():
        cutoff = time.time() - recent_days * 86400 if recent_days else 0
        for p in base.rglob("*"):
            try:
                if p.is_file() and not p.is_symlink() and p.stat().st_mtime >= cutoff and ".git" not in p.parts:
                    files.append(p)
            except Exception:
                continue
            if len(files) >= limit:
                break
    clam = clam_scan([base]) if files else None
    rows, crit = [], 0
    vt = vt_key() if use_vt else ""
    vt_left = 4  # kostenloser Key: 4 Anfragen/Minute
    clam_hits = {h["datei"]: h["fund"] for h in (clam or {}).get("funde", [])}
    for p in files:
        kind, flags = inspect_file(p)
        if str(p) in clam_hits:
            flags.insert(0, ("kritisch", f"Virenscanner: {clam_hits[str(p)]}"))
        risky = any(s in ("kritisch", "warn") for s, _ in flags) or Path(p).suffix.lower() in DANGER_EXT
        vt_res = None
        if vt and risky and vt_left > 0 and p.stat().st_size < 650 * 1024 * 1024:
            vt_left -= 1
            try:
                from osint import virustotal_file
                r = virustotal_file(path=str(p), key=vt)
                if r.get("bekannt") is False:
                    vt_res = "VirusTotal kennt die Datei nicht"
                else:
                    mal = r.get("bösartig", r.get("malicious", 0)) or 0
                    vt_res = f"VirusTotal: {mal} Scanner melden Schadcode" if mal else "VirusTotal: sauber"
                    if mal and int(mal) >= 3:
                        flags.insert(0, ("kritisch", vt_res))
            except Exception as e:
                vt_res = f"VirusTotal: {str(e)[:60]}"
        if flags or vt_res:
            worst = "kritisch" if any(s == "kritisch" for s, _ in flags) else "warn" if any(s == "warn" for s, _ in flags) else "info"
            crit += worst == "kritisch"
            rows.append({"datei": str(p).replace(str(HOME), "~"), "art": kind, "stufe": worst, "gründe": [t for _, t in flags],
                         **({"virustotal": vt_res} if vt_res else {})})
    rows.sort(key=lambda r: {"kritisch": 0, "warn": 1, "info": 2}[r["stufe"]])
    return {"geprüft": len(files), "auffällig": rows[:80], "kritisch": crit,
            "virenscanner": (clam or {}).get("programm") or (clam["fehler"] if clam and clam.get("fehler") else "nicht installiert (sudo apt install clamav)"),
            "virustotal": "nur Hash-Abfrage, nichts hochgeladen" if vt else "kein Key (optional, in den Einstellungen)",
            "hinweis": "Kritisch = nicht öffnen und löschen (oder in Quarantäne). Warn = nur öffnen, wenn du die Quelle kennst."}


def quarantine(path):
    p = Path(str(path)).expanduser()
    if not p.is_file():
        raise RuntimeError("Datei nicht gefunden.")
    q = HOME / ".lumen" / "quarantaene"
    q.mkdir(parents=True, exist_ok=True)
    dst = q / f"{int(time.time())}-{p.name}.quarantaene"
    shutil.move(str(p), dst)
    os.chmod(dst, 0o400)
    (q / (dst.name + ".info")).write_text(json.dumps({"von": str(p), "zeit": datetime.now().isoformat(timespec="seconds")}), "utf-8")
    return f"In Quarantäne verschoben (nicht mehr ausführbar): {dst}"


def downloads_watch(notify):
    """Hintergrund: neue Dateien in ~/Downloads prüfen und bei Gefahr melden."""
    dl = HOME / "Downloads"
    if not dl.exists():
        return
    with LOCK:
        d = _load()
        seen = d["downloads_seen"]
        first = not seen
        new = []
        for p in dl.iterdir():
            try:
                if not p.is_file() or p.name.endswith((".part", ".crdownload", ".download", ".tmp")):
                    continue
                key = f"{p.name}|{p.stat().st_size}|{int(p.stat().st_mtime)}"
            except Exception:
                continue
            if key not in seen:
                seen[key] = int(time.time())
                if not first and time.time() - p.stat().st_mtime > 3:
                    new.append(p)
        if len(seen) > 3000:
            for k in sorted(seen, key=seen.get)[:1000]:
                seen.pop(k)
        _save(d)
    for p in new[:10]:
        kind, flags = inspect_file(p)
        clam = clam_scan([p]) if _which(["clamdscan", "clamscan"]) and p.stat().st_size < 200 * 1024 * 1024 else None
        if clam and clam.get("funde"):
            flags.insert(0, ("kritisch", "Virenscanner: " + clam["funde"][0]["fund"]))
        bad = [t for s, t in flags if s in ("kritisch", "warn")]
        if bad:
            notify(("⛔ " if any(s == "kritisch" for s, _ in flags) else "⚠️ ") + f"Download prüfen: {p.name}", "; ".join(bad)[:300], str(p))


# ---------------------------------------------------------------- Geheimnis-Scanner
SECRET_RX = [
    ("AWS-Zugangsschlüssel", r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("GitHub-Token", r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{50,}\b"),
    ("Anthropic-API-Key", r"\bsk-ant-[A-Za-z0-9_\-]{30,}"),
    ("OpenAI-API-Key", r"\bsk-(proj-)?[A-Za-z0-9_\-]{32,}"),
    ("Google-API-Key", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("Slack-Token", r"\bxox[abpors]-[A-Za-z0-9-]{10,}"),
    ("Stripe-Live-Key", r"\b(sk|rk)_live_[A-Za-z0-9]{20,}"),
    ("Telegram-Bot-Token", r"\b\d{8,10}:AA[A-Za-z0-9_\-]{30,40}\b"),
    ("Discord-Token", r"\b[MN][A-Za-z\d]{23,25}\.[\w-]{6}\.[\w-]{27,38}\b"),
    ("Privater Schlüssel", r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY( BLOCK)?-----"),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("Passwort im Klartext", r"(?i)\b(password|passwort|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*['\"]?(?!\$\{|<|\*{3}|xxx|changeme|example|your)[^\s'\"#]{6,}"),
    ("Datenbank-URL mit Passwort", r"\b(postgres|postgresql|mysql|mongodb(\+srv)?|redis|amqp)://[^:\s/]+:[^@\s]{3,}@"),
]
SECRET_SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "__pycache__", ".cache", "site-packages", "dist", "build", ".npm", ".cargo", ".rustup",
                    ".mozilla", ".thunderbird", ".local", "snap", ".steam", ".lumen"}
SECRET_EXT = {".env", ".py", ".js", ".ts", ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".txt", ".md", ".sh", ".bash", ".zsh",
              ".php", ".rb", ".go", ".java", ".kt", ".cs", ".tf", ".tfvars", ".properties", ".xml", ".pem", ".key", ".netrc", ".npmrc", ".pypirc", ""}


def _mask(s):
    s = s.strip()
    return s[:4] + "…" + s[-2:] if len(s) > 10 else s[:2] + "…"


def secrets_scan(path="~", limit_files=20000):
    base = Path(str(path or "~")).expanduser()
    if not base.exists():
        raise RuntimeError("Ordner nicht gefunden.")
    rp = str(base.resolve())
    if rp == "/" or rp.startswith(("/proc", "/sys", "/dev", "/run")):
        raise RuntimeError("Bitte einen konkreten Ordner wählen (z. B. ~/Projekte), nicht das ganze System.")
    hits, n = [], 0
    rx = [(name, re.compile(p)) for name, p in SECRET_RX]
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SECRET_SKIP_DIRS and not (d.startswith(".") and d not in (".ssh", ".aws", ".config", ".docker", ".kube"))]
        for fn in files:
            p = Path(root) / fn
            if p.suffix.lower() not in SECRET_EXT and not fn.startswith(".env"):
                continue
            n += 1
            if n > limit_files:
                break
            try:
                if p.stat().st_size > 2 * 1024 * 1024 or p.is_symlink():
                    continue
                text = p.read_text("utf-8", "ignore")
            except Exception:
                continue
            for name, r in rx:
                for m in r.finditer(text):
                    if name == "Privater Schlüssel" and p.parent.name == ".ssh":
                        if b"ENCRYPTED" in p.read_bytes()[:400] or "bcrypt" in text[:600] or "aes256" in text[:600]:
                            continue
                        name2 = "SSH-Schlüssel ohne Passphrase"
                    else:
                        name2 = name
                    line = text.count("\n", 0, m.start()) + 1
                    hits.append({"datei": str(p).replace(str(HOME), "~"), "zeile": line, "art": name2, "ausschnitt": _mask(m.group(0)),
                                 "git": (p.parent / ".git").exists() or any((q / ".git").exists() for q in p.parents if str(q).startswith(str(base)))})
                    break
            if len(hits) >= 200:
                break
        if n > limit_files or len(hits) >= 200:
            break
    perms = []
    for f in (HOME / ".ssh").glob("id_*") if (HOME / ".ssh").exists() else []:
        if not f.name.endswith(".pub") and f.stat().st_mode & 0o077:
            perms.append(str(f).replace(str(HOME), "~"))
    return {"geprüfte_dateien": min(n, limit_files), "funde": hits, "zu_offene_schlüssel": perms,
            "hinweis": "Funde sind maskiert. Geleakte Schlüssel beim Anbieter SOFORT neu erzeugen (widerrufen) – Löschen allein reicht nicht, "
                       "vor allem wenn die Datei in Git/GitHub war. Passwörter in Dateien → Passwort-Manager oder Umgebungsvariablen."}


# ---------------------------------------------------------------- Integritäts-Wächter
def _watch_list():
    files = [Path(p) for p in ("/etc/passwd", "/etc/group", "/etc/hosts", "/etc/crontab", "/etc/ld.so.preload", "/etc/environment",
                               "/etc/profile", "/etc/bash.bashrc", "/etc/rc.local", "/etc/ssh/sshd_config", "/etc/pam.d/common-auth",
                               "/etc/pam.d/sshd", "/etc/apt/sources.list", "/etc/resolv.conf")]
    for d in ("/etc/cron.d", "/etc/cron.daily", "/etc/cron.hourly", "/etc/systemd/system", "/etc/sudoers.d", "/etc/profile.d",
              "/etc/xdg/autostart", "/etc/apt/sources.list.d", "/etc/ssh/sshd_config.d", "/etc/udev/rules.d"):
        p = Path(d)
        if p.is_dir():
            files += [x for x in p.rglob("*") if x.is_file()][:300]
    for f in (".bashrc", ".profile", ".bash_profile", ".zshrc", ".bash_logout", ".ssh/authorized_keys", ".ssh/config", ".ssh/rc",
              ".config/environment.d", ".pam_environment", ".xprofile", ".xsessionrc"):
        files.append(HOME / f)
    for d in (".config/autostart", ".config/systemd/user", ".local/share/applications"):
        p = HOME / d
        if p.is_dir():
            files += [x for x in p.rglob("*") if x.is_file()][:300]
    for b in ("sudo", "su", "ssh", "sshd", "login", "passwd", "ls", "ps", "netstat", "ss", "top", "find", "bash", "sh", "cron", "systemctl"):
        x = shutil.which(b) or (f"/usr/sbin/{b}" if Path(f"/usr/sbin/{b}").exists() else None)
        if x:
            files.append(Path(x).resolve())
    return sorted(set(files))


def _fingerprint():
    out = {}
    for p in _watch_list():
        try:
            if p.is_file():
                st = p.stat()
                out[str(p)] = {"sha": sha256_file(p) if st.st_size < 50 * 1024 * 1024 else f"size:{st.st_size}", "mode": oct(st.st_mode & 0o7777),
                               "uid": st.st_uid}
        except PermissionError:
            out[str(p)] = {"sha": "kein-zugriff"}
        except Exception:
            pass
    cr, _, rc = _run(["crontab", "-l"], 10)
    out["crontab (dein Benutzer)"] = {"sha": hashlib.sha256(cr.encode()).hexdigest() if rc == 0 else "leer"}
    return out


def integrity_baseline():
    fp = _fingerprint()
    with LOCK:
        d = _load()
        d["baseline"], d["baseline_zeit"] = fp, datetime.now().strftime("%d.%m.%Y %H:%M")
        _save(d)
    return {"text": f"Fingerabdruck von {len(fp)} wichtigen Dateien gespeichert. Ab jetzt meldet Lumen Veränderungen.", "dateien": len(fp)}


def integrity_check(update=False):
    d = _load()
    if not d["baseline"]:
        r = integrity_baseline()
        return {"erstmals": True, **r, "änderungen": [], "rootkit_hinweise": rootkit_hints()}
    now = _fingerprint()
    base = d["baseline"]
    changes = []
    for k, v in now.items():
        if k not in base:
            changes.append({"datei": k.replace(str(HOME), "~"), "art": "neu"})
        elif base[k].get("sha") != v.get("sha"):
            changes.append({"datei": k.replace(str(HOME), "~"), "art": "geändert"})
        elif base[k].get("mode") != v.get("mode") or base[k].get("uid") != v.get("uid"):
            changes.append({"datei": k.replace(str(HOME), "~"), "art": f"Rechte {base[k].get('mode')}→{v.get('mode')}"})
    for k in base:
        if k not in now:
            changes.append({"datei": k.replace(str(HOME), "~"), "art": "gelöscht"})
    crit_words = ("ld.so.preload", "authorized_keys", "sudoers", "/usr/bin/", "/usr/sbin/", "/bin/", "pam.d", "passwd")
    for c in changes:
        c["wichtig"] = any(w in c["datei"] for w in crit_words)
    res = {"seit": d["baseline_zeit"], "geprüft": len(now), "änderungen": changes, "rootkit_hinweise": rootkit_hints(),
           "hinweis": "Änderungen nach Updates (apt upgrade) oder eigenen Einstellungen sind normal → „Als neuen Stand übernehmen“. "
                      "Unerklärliche Änderungen an Programmen (/usr/bin), authorized_keys, sudoers oder ld.so.preload ernst nehmen."}
    if update:
        integrity_baseline()
        res["übernommen"] = True
    return res


def rootkit_hints():
    hints = []
    if Path("/etc/ld.so.preload").exists() and Path("/etc/ld.so.preload").read_text("utf-8", "ignore").strip():
        hints.append(_f("kritisch", "/etc/ld.so.preload ist gesetzt", "Wird von vielen Linux-Rootkits benutzt, um sich zu verstecken.",
                        "Inhalt prüfen: cat /etc/ld.so.preload – ohne bekannten Grund ernst nehmen."))
    if os.environ.get("LD_PRELOAD"):
        hints.append(_f("warn", "LD_PRELOAD ist gesetzt", os.environ["LD_PRELOAD"][:120]))
    try:
        proc = {int(p.name) for p in Path("/proc").iterdir() if p.name.isdigit()}
        out, _, rc = _run(["ps", "-e", "-o", "pid="], 15)
        ps = {int(x) for x in out.split() if x.isdigit()}
        proc2 = {int(p.name) for p in Path("/proc").iterdir() if p.name.isdigit()}
        hidden = (proc & proc2) - ps
        hidden = {p for p in hidden if Path(f"/proc/{p}").exists() and not Path(f"/proc/{p}/task").exists() is False}
        hidden = {p for p in hidden if p > 2 and Path(f"/proc/{p}/status").exists()}
        if len(hidden) > 3:
            hints.append(_f("warn", f"{len(hidden)} Prozesse, die „ps“ nicht zeigt", ", ".join(map(str, sorted(hidden)[:10])),
                            "Kann harmlos sein (kurzlebige Prozesse). Wenn es bleibt: rkhunter/chkrootkit laufen lassen."))
    except Exception:
        pass
    for mod_dir in ("/dev/shm", "/tmp", "/var/tmp"):
        try:
            ex = [p.name for p in Path(mod_dir).iterdir() if p.is_file() and os.access(p, os.X_OK) and _magic(p) == "Linux-Programm"][:5]
            if ex:
                hints.append(_f("warn", f"Programme in {mod_dir}", ", ".join(ex), "Schadsoftware legt sich gern dort ab. Herkunft prüfen."))
        except Exception:
            pass
    if not hints:
        hints.append(_f("ok", "Keine typischen Rootkit-Spuren", "ld.so.preload leer, keine versteckten Prozesse, keine Programme in /tmp."))
    return hints


def rootkit_tools():
    """rkhunter/chkrootkit brauchen Admin-Rechte → pkexec (Passwort-Fenster)."""
    res = []
    pk = ["pkexec"] if shutil.which("pkexec") and os.geteuid() != 0 else []
    for name, cmd in (("rkhunter", ["rkhunter", "--check", "--sk", "--nocolors", "--rwo"]), ("chkrootkit", ["chkrootkit", "-q"])):
        if not shutil.which(cmd[0]):
            continue
        out, err, rc = _run(pk + cmd, 1800)
        if rc in (126, 127) and pk:
            raise RuntimeError("Abgebrochen (Passwort-Fenster geschlossen).")
        lines = [l.strip() for l in (out + "\n" + err).splitlines() if l.strip() and not l.startswith(("Invalid", "grep"))][:40]
        res.append({"werkzeug": name, "meldungen": lines or ["Keine Warnungen."]})
    if not res:
        raise RuntimeError("Weder rkhunter noch chkrootkit installiert: sudo apt install rkhunter chkrootkit")
    return {"ergebnisse": res, "hinweis": "rkhunter meldet manchmal Fehlalarme nach Updates (dann: sudo rkhunter --propupd)."}


# ================================================================ B) Lücken finden
def _os_release():
    d = {}
    try:
        for l in Path("/etc/os-release").read_text().splitlines():
            k, _, v = l.partition("=")
            d[k] = v.strip('"')
    except Exception:
        pass
    return d


def cve_check(max_details=25):
    """Installierte Pakete gegen bekannte Sicherheitslücken (OSV.dev). Debian/Ubuntu: Systempakete; überall: pip-Pakete von Lumen."""
    osr = _os_release()
    eco, pkgs = None, []
    if shutil.which("dpkg-query") and osr.get("ID") in ("debian", "ubuntu") or "debian" in osr.get("ID_LIKE", "") or "ubuntu" in osr.get("ID_LIKE", ""):
        if osr.get("ID") == "ubuntu" or "ubuntu" in osr.get("ID_LIKE", ""):
            ver = osr.get("VERSION_ID", "")
            eco = f"Ubuntu:{ver}:LTS" if ver.split(".")[-1] == "04" and int(ver.split(".")[0]) % 2 == 0 else f"Ubuntu:{ver}"
        else:
            eco = f"Debian:{osr.get('VERSION_ID', '12').split('.')[0]}"
        out, _, _ = _run(["dpkg-query", "-W", "-f", "${source:Package}\t${source:Version}\t${Package}\n"], 60)
        seen = set()
        for l in out.splitlines():
            p = l.split("\t")
            if len(p) >= 2 and (p[0], p[1]) not in seen:
                seen.add((p[0], p[1]))
                pkgs.append({"ecosystem": eco, "name": p[0], "version": p[1]})
    try:
        import importlib.metadata as md
        for dist in md.distributions():
            n, v = dist.metadata.get("Name"), dist.version
            if n and v:
                pkgs.append({"ecosystem": "PyPI", "name": n, "version": v})
    except Exception:
        pass
    if not pkgs:
        raise RuntimeError("Keine Pakete gefunden (unterstützt: Debian/Ubuntu-Systempakete und Python-Pakete).")
    hits = {}
    for i in range(0, len(pkgs), 900):
        chunk = pkgs[i:i + 900]
        st, js, _ = ig._http("POST", "https://api.osv.dev/v1/querybatch", json_body={"queries": [
            {"package": {"ecosystem": p["ecosystem"], "name": p["name"]}, "version": p["version"]} for p in chunk]}, timeout=90)
        if st != 200 or not js:
            raise RuntimeError("OSV.dev (Schwachstellen-Datenbank) nicht erreichbar.")
        for p, r in zip(chunk, js.get("results", [])):
            ids = [v["id"] for v in r.get("vulns") or []]
            if ids:
                hits[(p["ecosystem"], p["name"], p["version"])] = ids
    details = []
    for (e, n, v), ids in sorted(hits.items(), key=lambda kv: -len(kv[1]))[:max_details]:
        sev, fixed, summary = None, None, ""
        for vid in ids[:3]:
            st, js, _ = ig._http("GET", f"https://api.osv.dev/v1/vulns/{vid}", timeout=30)
            if st != 200 or not js:
                continue
            summary = summary or (js.get("summary") or js.get("details", "")[:140])
            for s in js.get("severity", []) + [x for a in js.get("affected", []) for x in a.get("severity", [])]:
                m = re.search(r"CVSS:\d\.\d/.*", s.get("score", ""))
                if s.get("type", "").startswith("CVSS") and m:
                    sc = _cvss_score(s["score"])
                    sev = max(sev or 0, sc or 0)
            for a in js.get("affected", []):
                if a.get("package", {}).get("name") == n:
                    for rg in a.get("ranges", []):
                        for ev in rg.get("events", []):
                            if ev.get("fixed"):
                                fixed = ev["fixed"]
            if (js.get("database_specific") or {}).get("severity"):
                sev = sev or {"low": 3, "medium": 5, "moderate": 5, "high": 8, "critical": 9.5}.get(str(js["database_specific"]["severity"]).lower())
        details.append({"paket": n, "version": v, "quelle": "System" if e != "PyPI" else "Python", "lücken": len(ids), "ids": ids[:6],
                        "schwere": round(sev, 1) if sev else None, "behoben_in": fixed, "kurz": summary[:160]})
    details.sort(key=lambda x: (-(x["schwere"] or 0), -x["lücken"]))
    fixable = [x for x in details if x["behoben_in"]]
    return {"system": f"{osr.get('PRETTY_NAME', '?')} ({eco or 'nur Python'})", "geprüfte_pakete": len(pkgs), "betroffene_pakete": len(hits),
            "details": details, "mit_update_behebbar": len(fixable),
            "hinweis": "Debian/Ubuntu führen auch Lücken, für die es (noch) keinen Fix gibt oder die nur unter Sonderbedingungen gelten – "
                       "Panik unnötig. Wichtig: alles mit „behoben in“ → sudo apt update && sudo apt upgrade."}


def _cvss_score(vec):
    """CVSS-3-Basiswert aus dem Vektor berechnen (vereinfacht, Scope beachtet)."""
    try:
        m = dict(x.split(":") for x in vec.split("/")[1:])
        av = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}[m["AV"]]
        ac = {"L": 0.77, "H": 0.44}[m["AC"]]
        sc = m["S"] == "C"
        pr = {"N": 0.85, "L": 0.68 if sc else 0.62, "H": 0.5 if sc else 0.27}[m["PR"]]
        ui = {"N": 0.85, "R": 0.62}[m["UI"]]
        c, i, a = ({"H": 0.56, "L": 0.22, "N": 0}[m[k]] for k in ("C", "I", "A"))
        iss = 1 - (1 - c) * (1 - i) * (1 - a)
        imp = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15 if sc else 6.42 * iss
        if imp <= 0:
            return 0.0
        ex = 8.22 * av * ac * pr * ui
        base = min(1.08 * (imp + ex), 10) if sc else min(imp + ex, 10)
        return math.ceil(base * 10) / 10
    except Exception:
        return None


def tls_check(host, port=443):
    """TLS-Check (eine Handvoll normaler Verbindungen – wie ein Browser): Protokolle, Verschlüsselung, Zertifikat."""
    host = (urllib.parse.urlparse(host if "://" in host else "https://" + host).hostname or "").strip()
    if not host:
        raise RuntimeError("Welche Domain?")
    res, F = {"host": host, "port": port, "protokolle": {}}, []
    for name, ver in (("TLS 1.3", ssl.TLSVersion.TLSv1_3), ("TLS 1.2", ssl.TLSVersion.TLSv1_2), ("TLS 1.1", ssl.TLSVersion.TLSv1_1),
                      ("TLS 1.0", ssl.TLSVersion.TLSv1)):
        ctx = ssl.create_default_context()
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        try:
            ctx.set_ciphers("ALL:@SECLEVEL=0")
        except ssl.SSLError:
            pass
        try:
            ctx.minimum_version = ctx.maximum_version = ver
        except (ValueError, ssl.SSLError):
            res["protokolle"][name] = "nicht prüfbar"
            continue
        try:
            with socket.create_connection((host, port), timeout=8) as s, ctx.wrap_socket(s, server_hostname=host) as t:
                res["protokolle"][name] = "ja"
                if name in ("TLS 1.3", "TLS 1.2") and "cipher" not in res:
                    res["cipher"] = t.cipher()[0]
        except ssl.SSLError as e:
            res["protokolle"][name] = "nein" if "unsupported protocol" in str(e).lower() or "version" in str(e).lower() or "handshake" in str(e).lower() \
                else "nicht prüfbar"
        except Exception:
            res["protokolle"][name] = "nein"
    pr = res["protokolle"]
    if pr.get("TLS 1.3") == "ja":
        F.append(_f("ok", "TLS 1.3", "Modernstes Protokoll wird unterstützt."))
    elif pr.get("TLS 1.2") == "ja":
        F.append(_f("info", "Kein TLS 1.3", "TLS 1.2 geht, TLS 1.3 wäre schneller und sicherer."))
    else:
        F.append(_f("kritisch", "Kein TLS 1.2/1.3", "Moderne Browser verbinden sich nicht mehr sicher."))
    for old in ("TLS 1.0", "TLS 1.1"):
        if pr.get(old) == "ja":
            F.append(_f("warn", f"{old} noch an", "Veraltet und unsicher – im Webserver abschalten."))
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=8) as s, ctx.wrap_socket(s, server_hostname=host) as t:
            c = t.getpeercert()
            exp = datetime.strptime(c["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days = (exp - datetime.now(timezone.utc)).days
            issuer = dict(x[0] for x in c.get("issuer", []))
            res.update(gültig_bis=exp.strftime("%d.%m.%Y"), tage=days, aussteller=issuer.get("organizationName", issuer.get("commonName", "?")),
                       namen=[v for k, v in c.get("subjectAltName", [])][:10])
            F.append(_f("ok" if days > 20 else "warn" if days > 0 else "kritisch", "Zertifikat",
                        f"Gültig bis {res['gültig_bis']} ({days} Tage) · {res['aussteller']}", "Automatische Erneuerung prüfen (certbot renew --dry-run)." if days <= 20 else ""))
    except ssl.SSLCertVerificationError as e:
        F.append(_f("kritisch", "Zertifikat ungültig", str(e.verify_message or e)[:160]))
    except Exception as e:
        F.append(_f("warn", "Zertifikat", f"Nicht prüfbar: {str(e)[:120]}"))
    res["befunde"] = F
    res["tiefer"] = "Gründlicher (eigene Domain): testssl oder sslscan über Lumen laufen lassen." if _which(["testssl", "testssl.sh", "sslscan"]) else \
        "Für eine gründliche Prüfung: testssl.sh installieren oder ssllabs.com/ssltest nutzen."
    return res


def web_tool(tool, target):
    """Webserver-Scanner für EIGENE Seiten: testssl, sslscan, nikto, whatweb, nuclei."""
    host = _own_web(target)
    url = target if "://" in str(target) else "https://" + host
    if tool == "testssl":
        exe = _which(["testssl", "testssl.sh"])
        cmd = [exe, "--quiet", "--color", "0", "--warnings", "batch", "-S", "-P", "-p", "-U", host] if exe else None
        to = 900
    elif tool == "sslscan":
        exe = shutil.which("sslscan")
        cmd = [exe, "--no-colour", host] if exe else None
        to = 300
    elif tool == "nikto":
        exe = shutil.which("nikto")
        cmd = [exe, "-h", url, "-ask", "no", "-nointeractive", "-maxtime", "600s", "-Tuning", "x6"] if exe else None   # ohne DoS-Tests
        to = 700
    elif tool == "whatweb":
        exe = shutil.which("whatweb")
        cmd = [exe, "--color=never", "-a", "1", url] if exe else None
        to = 120
    elif tool == "nuclei":
        exe = shutil.which("nuclei")
        cmd = [exe, "-u", url, "-silent", "-nc", "-severity", "low,medium,high,critical", "-etags", "dos,intrusive,fuzz,bruteforce",
               "-rate-limit", "30"] if exe else None
        to = 1200
    else:
        raise RuntimeError("Werkzeuge: testssl, sslscan, nikto, whatweb, nuclei")
    if not cmd:
        raise RuntimeError(f"{tool} ist nicht installiert ({TOOLS.get(tool, ('', '', tool))[2]}).")
    out, err, rc = _run(cmd, to)
    text = re.sub(r"\x1b\[[0-9;]*m", "", out or err)
    lines = [l.rstrip() for l in text.splitlines() if l.strip()]
    if tool == "nikto":
        lines = [l for l in lines if l.startswith("+") and "Target" not in l and "Start Time" not in l]
    keep = lines[:120]
    return {"werkzeug": tool, "ziel": host, "ausgabe": "\n".join(keep)[:9000], "zeilen": len(lines),
            "hinweis": "Rohausgabe gekürzt. Lumen erklärt sie dir gern Punkt für Punkt."}


# ---------------------------------------------------------------- Härtung (mit Bestätigung, über pkexec)
HARDEN = {
    "firewall": ("Firewall einschalten (ufw)", "Eingehend alles sperren, ausgehend erlauben; SSH bleibt aus dem Heimnetz erreichbar, falls es läuft.",
                 None),
    "ssh_haerten": ("SSH absichern", "Passwort-Login und Root-Login abschalten (nur Schlüssel). Nur möglich, wenn bei dir schon ein SSH-Schlüssel "
                                     "hinterlegt ist – sonst sperrst du dich aus.", None),
    "fail2ban": ("fail2ban installieren", "Sperrt IPs für 10 Minuten nach 5 falschen Anmeldungen (SSH).", None),
    "auto_updates": ("Automatische Sicherheits-Updates", "Installiert unattended-upgrades und schaltet es ein.", None),
    "clamav": ("ClamAV installieren", "Virenscanner + Signatur-Updates.", None),
}


def harden_plan(fid):
    if fid not in HARDEN:
        raise RuntimeError("Aktionen: " + ", ".join(HARDEN))
    apt = shutil.which("apt-get")
    if fid == "firewall":
        if not shutil.which("ufw") and not apt:
            raise RuntimeError("ufw fehlt und kann hier nicht automatisch installiert werden.")
        lan = ""
        try:
            out, _, _ = _run(["ip", "-j", "-4", "route"], 10)
            nets = [r["dst"] for r in json.loads(out) if "/" in r.get("dst", "") and ipaddress.ip_network(r["dst"]).is_private]
            lan = nets[0] if nets else ""
        except Exception:
            pass
        ssh_on = _run(["systemctl", "is-active", "ssh"], 10)[0].strip() == "active" or _run(["systemctl", "is-active", "sshd"], 10)[0].strip() == "active"
        script = ("command -v ufw >/dev/null || apt-get install -y ufw; ufw default deny incoming; ufw default allow outgoing; "
                  + (f"ufw allow from {lan} to any port 22 proto tcp; " if ssh_on and lan else "ufw allow 22/tcp; " if ssh_on else "")
                  + "ufw --force enable; ufw status verbose")
    elif fid == "ssh_haerten":
        ak = Path("/root/.ssh/authorized_keys"), HOME / ".ssh" / "authorized_keys"
        if not any(p.exists() and p.stat().st_size > 50 for p in ak if os.access(p.parent, os.R_OK)):
            raise RuntimeError("Für dich ist noch kein SSH-Schlüssel hinterlegt (~/.ssh/authorized_keys). Ohne Schlüssel würdest du dich "
                               "aussperren – erst Schlüssel einrichten (Lumen: „Richte SSH-Schlüssel ein“).")
        script = ("mkdir -p /etc/ssh/sshd_config.d; printf 'PasswordAuthentication no\\nKbdInteractiveAuthentication no\\nPermitRootLogin no\\n' "
                  "> /etc/ssh/sshd_config.d/99-lumen-haertung.conf; sshd -t && (systemctl reload ssh 2>/dev/null || systemctl reload sshd) "
                  "&& echo OK || (rm -f /etc/ssh/sshd_config.d/99-lumen-haertung.conf; echo 'Test fehlgeschlagen – nichts geändert'; exit 1)")
    elif fid == "fail2ban":
        if not apt:
            raise RuntimeError("Automatisch nur unter Debian/Ubuntu.")
        script = ("apt-get install -y fail2ban && printf '[sshd]\\nenabled = true\\nmaxretry = 5\\nbantime = 10m\\n' > /etc/fail2ban/jail.d/lumen.local "
                  "&& systemctl enable --now fail2ban && systemctl restart fail2ban && fail2ban-client status sshd")
    elif fid == "auto_updates":
        if not apt:
            raise RuntimeError("Automatisch nur unter Debian/Ubuntu.")
        script = ("apt-get install -y unattended-upgrades && printf 'APT::Periodic::Update-Package-Lists \"1\";\\nAPT::Periodic::Unattended-Upgrade \"1\";\\n' "
                  "> /etc/apt/apt.conf.d/20auto-upgrades && echo OK")
    else:
        if not apt:
            raise RuntimeError("Automatisch nur unter Debian/Ubuntu: sonst clamav über die Paketverwaltung installieren.")
        script = "apt-get install -y clamav clamav-daemon && systemctl stop clamav-freshclam; freshclam; systemctl enable --now clamav-freshclam clamav-daemon; echo OK"
    return HARDEN[fid][0], HARDEN[fid][1], script


def harden(fid):
    title, why, script = harden_plan(fid)
    pk = ["pkexec"] if shutil.which("pkexec") and os.geteuid() != 0 else [] if os.geteuid() == 0 else None
    if pk is None:
        raise RuntimeError("Admin-Rechte nötig, pkexec fehlt. Im Terminal: sudo sh -c '" + script + "'")
    out, err, rc = _run(pk + ["sh", "-c", script], 1800)
    if rc in (126, 127) and pk:
        raise RuntimeError("Abgebrochen (Passwort-Fenster geschlossen).")
    if rc != 0:
        raise RuntimeError(f"{title} fehlgeschlagen: " + (err or out).strip()[-300:])
    return {"text": f"✅ {title} – erledigt.", "ausgabe": out.strip()[-1200:]}


# ================================================================ C) Werkzeugkasten
HASH_IDS = [
    (r"^\$2[abxy]\$\d\d\$[./A-Za-z0-9]{53}$", "bcrypt"), (r"^\$argon2(id|i|d)\$", "Argon2"), (r"^\$6\$", "SHA-512-crypt (Linux /etc/shadow)"),
    (r"^\$5\$", "SHA-256-crypt"), (r"^\$1\$", "MD5-crypt (veraltet)"), (r"^\$y\$", "yescrypt (Linux /etc/shadow)"), (r"^\$P\$|^\$H\$", "phpass (WordPress)"),
    (r"^pbkdf2_sha256\$", "Django PBKDF2"), (r"^\{SSHA\}", "LDAP SSHA"), (r"^[a-f0-9]{32}$", "MD5 oder NTLM (32 Hex)"),
    (r"^[a-f0-9]{40}$", "SHA-1 (40 Hex)"), (r"^[a-f0-9]{56}$", "SHA-224"), (r"^[a-f0-9]{64}$", "SHA-256 (64 Hex)"), (r"^[a-f0-9]{96}$", "SHA-384"),
    (r"^[a-f0-9]{128}$", "SHA-512 (128 Hex)"), (r"^[a-f0-9]{8}$", "CRC32"),
]


def _b64d(s):
    s = re.sub(r"\s", "", s)
    s += "=" * (-len(s) % 4)
    try:
        return base64.b64decode(s, validate=False)
    except Exception:
        return base64.urlsafe_b64decode(s)


def _txt(b):
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return "(Binärdaten) " + b.hex()[:400]


def toolbox(op, text="", extra=None):
    text = str(text if text is not None else "")
    extra = extra or {}
    if len(text) > 200000:
        raise RuntimeError("Eingabe zu groß (max. 200 000 Zeichen).")
    if op == "base64_kodieren":
        return base64.b64encode(text.encode()).decode()
    if op == "base64_dekodieren":
        return _txt(_b64d(text))
    if op == "hex_kodieren":
        return text.encode().hex()
    if op == "hex_dekodieren":
        return _txt(binascii.unhexlify(re.sub(r"[^0-9a-fA-F]", "", text)))
    if op == "url_kodieren":
        return urllib.parse.quote(text, safe="")
    if op == "url_dekodieren":
        return urllib.parse.unquote_plus(text)
    if op == "rot13":
        return text.translate(str.maketrans(string.ascii_letters, string.ascii_lowercase[13:] + string.ascii_lowercase[:13] +
                                            string.ascii_uppercase[13:] + string.ascii_uppercase[:13]))
    if op == "binär":
        return " ".join(f"{b:08b}" for b in text.encode())
    if op == "binär_dekodieren":
        return _txt(bytes(int(x, 2) for x in text.split()))
    if op == "html_entities_dekodieren":
        import html
        return html.unescape(text)
    if op == "hashes":
        b = text.encode()
        return {k: getattr(hashlib, k)(b).hexdigest() for k in ("md5", "sha1", "sha256", "sha512")} | {"crc32": f"{binascii.crc32(b) & 0xffffffff:08x}"}
    if op == "datei_hash":
        p = Path(text.strip()).expanduser()
        if not p.is_file():
            raise RuntimeError("Datei nicht gefunden.")
        hs = {k: hashlib.new(k) for k in ("md5", "sha1", "sha256")}
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                for h in hs.values():
                    h.update(chunk)
        return {"datei": str(p), **{k: h.hexdigest() for k, h in hs.items()}}
    if op == "hash_erkennen":
        t = text.strip()
        hits = [n for rx, n in HASH_IDS if re.search(rx, t if t.startswith(("$", "{", "pbkdf2")) else t.lower())]
        return {"eingabe": t[:80], "vermutlich": hits or ["unbekannt"], "hinweis": "Nur anhand der Form geraten – sicher ist das nicht."}
    if op == "jwt_lesen":
        parts = text.strip().split(".")
        if len(parts) < 2:
            raise RuntimeError("Kein JWT (Form: xxx.yyy.zzz).")
        head, body = json.loads(_b64d(parts[0])), json.loads(_b64d(parts[1]))
        info = {}
        for k in ("exp", "iat", "nbf"):
            if isinstance(body.get(k), (int, float)):
                info[k] = datetime.fromtimestamp(body[k]).strftime("%d.%m.%Y %H:%M:%S")
        warn = []
        if str(head.get("alg", "")).lower() == "none":
            warn.append("alg=none – Token ist NICHT signiert (gefährlich, wenn ein Server das akzeptiert).")
        if body.get("exp") and body["exp"] < time.time():
            warn.append("Abgelaufen.")
        return {"kopf": head, "inhalt": body, "zeiten": info, "warnungen": warn, "hinweis": "Signatur nicht geprüft (dafür bräuchte es den Schlüssel)."}
    if op == "passwort":
        n = max(8, min(int(extra.get("länge") or 20), 128))
        alphabet = string.ascii_letters + string.digits + ("!#$%&*+-=?@^_~" if extra.get("sonderzeichen", True) else "")
        while True:
            pw = "".join(secrets.choice(alphabet) for _ in range(n))
            if any(c.islower() for c in pw) and any(c.isupper() for c in pw) and any(c.isdigit() for c in pw):
                break
        return {"passwort": pw, "stärke_bits": round(n * math.log2(len(alphabet)))}
    if op == "passphrase":
        words = PASS_WORDS
        n = max(4, min(int(extra.get("wörter") or 5), 10))
        ph = "-".join(secrets.choice(words) for _ in range(n)) + "-" + str(secrets.randbelow(90) + 10)
        return {"passphrase": ph, "stärke_bits": round(n * math.log2(len(words)) + math.log2(90)),
                "hinweis": "Gut zu merken, schwer zu knacken. Für wichtige Konten zusätzlich 2FA einschalten."}
    if op == "ip_rechner":
        net = ipaddress.ip_network(text.strip(), strict=False)
        hosts = net.num_addresses - (2 if net.version == 4 and net.prefixlen < 31 else 0)
        return {"netz": str(net), "netzmaske": str(net.netmask), "erste": str(next(net.hosts(), net.network_address)),
                "letzte": str(list(net.hosts())[-1]) if net.num_addresses <= 65536 and hosts > 0 else str(net.broadcast_address - 1),
                "broadcast": str(net.broadcast_address) if net.version == 4 else "–", "adressen": hosts, "privat": net.is_private}
    if op == "zeitstempel":
        t = text.strip()
        if re.fullmatch(r"\d{9,13}", t):
            v = int(t) / (1000 if len(t) == 13 else 1)
            return {"datum": datetime.fromtimestamp(v).strftime("%d.%m.%Y %H:%M:%S"), "utc": datetime.fromtimestamp(v, timezone.utc).isoformat()}
        return {"unix": int(time.time())}
    if op == "entropie":
        if not text:
            return 0
        counts = {c: text.count(c) for c in set(text)}
        e = -sum(v / len(text) * math.log2(v / len(text)) for v in counts.values())
        return {"bits_pro_zeichen": round(e, 2), "gesamt_bits": round(e * len(text)), "hinweis": "Hohe Entropie (>4,5) bei langen Zeichenketten = vermutlich Schlüssel/zufällig."}
    raise RuntimeError("Unbekannte Funktion. Möglich: " + ", ".join(TOOLBOX_OPS))


TOOLBOX_OPS = ["base64_kodieren", "base64_dekodieren", "hex_kodieren", "hex_dekodieren", "url_kodieren", "url_dekodieren", "rot13", "binär",
               "binär_dekodieren", "html_entities_dekodieren", "hashes", "datei_hash", "hash_erkennen", "jwt_lesen", "passwort", "passphrase",
               "ip_rechner", "zeitstempel", "entropie"]

PASS_WORDS = """apfel birne kirsche pflaume traube melone zitrone orange banane mango tomate gurke karotte kartoffel zwiebel knoblauch
paprika kohl salat spinat erbse bohne linse mais reis nudel brot kuchen keks honig zucker salz pfeffer butter milch sahne kaese
quark joghurt wasser saft kaffee tee kakao suppe wurst schinken fisch lachs hering muschel krabbe tisch stuhl bett schrank regal
lampe spiegel teppich vorhang fenster tuer treppe dach keller garten zaun brunnen teich bach fluss see meer insel strand welle
sonne mond stern wolke regen schnee nebel wind sturm blitz donner himmel erde stein felsen sand kiesel berg tal wald baum ast
blatt wurzel blume rose tulpe lilie veilchen gras moos pilz farn eiche buche birke tanne fichte kiefer ahorn linde weide hund
katze maus ratte hase igel fuchs wolf baer reh hirsch elch pferd esel kuh ziege schaf schwein huhn ente gans taube rabe eule adler
falke spatz meise amsel storch kranich biene wespe ameise kaefer spinne schnecke frosch kroete eidechse schlange schildkroete
delfin wal hai robbe pinguin loewe tiger panther zebra giraffe elefant nashorn affe kamel lama papagei koala kaenguru buch heft
stift papier brief karte bild foto film lied musik geige gitarre klavier trommel floete harfe glocke uhr wecker kalender schluessel
schloss kette ring krone muenze schatz kiste korb tasche koffer rucksack schirm mantel jacke hose hemd rock kleid schuh stiefel
socke muetze schal handschuh guertel knopf nadel faden schere hammer zange saege bohrer schraube nagel leiter eimer besen
schaufel harke giesskanne zug bus auto fahrrad roller boot schiff segel anker hafen bruecke tunnel strasse weg pfad gleis
bahnhof flughafen rakete planet komet galaxie atom welle funke flamme feuer asche rauch dampf eis kristall perle diamant gold
silber kupfer eisen zinn blei glas holz wolle seide leder pappe farbe pinsel leinwand tinte kreide radiergummi lineal zirkel
globus atlas kompass karte fernrohr lupe mikroskop magnet batterie kabel stecker lampe kerze laterne fackel signal sirene pfeife
""".split()
