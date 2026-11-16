"""Lumen – Sicherheits-Zentrale.

• PC-Sicherheits-Check (Firewall, offene Dienste, SSH, Updates, Verschlüsselung …)
• Heimnetz-Scan (welche Geräte sind in MEINEM Netz? neue/unbekannte erkennen)
• USB-Kontrolle (angeschlossene Geräte, Sicherheits-/Funk-Hardware erkennen, USB-Wächter gegen „BadUSB“)
• Funk mit HackRF/RTL-SDR – NUR EMPFANGEN: Geräte-Info, Spektrum-Scan, Signal-Test für eigene Fernbedienungen
• Domain-Report (OSINT für Webseiten/Firmen-Domains: DNS, Mail-Schutz, TLS, Sicherheits-Header, Subdomains)

Grundsätze: nur eigene Geräte/Netze; keine Personensuche; Funk wird nie gesendet (kein Stören, kein Replay).
"""
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import osint

DATA = Path.home() / ".lumen" / "security.json"
LOCK = threading.RLock()
ENV_C = {**os.environ, "LC_ALL": "C", "LANG": "C"}


def _run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=ENV_C, stdin=subprocess.DEVNULL)
        return (r.stdout or "") + (("\n" + r.stderr) if r.returncode and r.stderr else ""), r.returncode
    except FileNotFoundError:
        return "", 127
    except Exception as e:
        return str(e), 1


def _load():
    try:
        d = json.loads(DATA.read_text("utf-8"))
    except Exception:
        d = {}
    d.setdefault("lan_known", {})     # mac -> {"name", "seit"}
    d.setdefault("usb_known", {})     # key -> {"name", "seit"}
    return d


def _save(d):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(DATA)


def _f(stufe, titel, text="", tipp=""):
    return {"stufe": stufe, "titel": titel, "text": text, "tipp": tipp}


def _score(findings):
    p = 100
    for f in findings:
        p -= {"kritisch": 25, "warn": 10}.get(f["stufe"], 0)
    return max(0, p)


def _read(path, limit=20000):
    try:
        return Path(path).read_text("utf-8", "replace")[:limit]
    except Exception:
        return ""


# ================================================================ PC-Sicherheits-Check
def pc_security():
    F = []
    # Firewall
    fw = None
    out, rc = _run(["ufw", "status"])
    if rc == 0 and "Status:" in out:
        fw = "ufw aktiv" if "Status: active" in out else "ufw installiert, aber AUS"
    elif rc != 127 and "root" in out.lower():
        fw = "ufw aktiv" if "ENABLED=yes" in _read("/etc/ufw/ufw.conf") else "ufw installiert, aber AUS"
    if not fw:
        out, rc = _run(["firewall-cmd", "--state"])
        if rc == 0 and "running" in out:
            fw = "firewalld aktiv"
    if not fw:
        out, rc = _run(["systemctl", "is-active", "nftables"])
        if out.strip() == "active":
            fw = "nftables aktiv"
    if fw and "AUS" not in fw:
        F.append(_f("ok", "Firewall", fw))
    else:
        F.append(_f("warn", "Firewall", fw or "Keine aktive Firewall gefunden.",
                    "Einschalten: sudo ufw enable (vorher ggf. installieren: sudo apt install ufw). Im Heimnetz hinter dem Router ist das Risiko kleiner, in fremden WLANs wichtig."))
    # Lauschende Dienste
    out, rc = _run(["ss", "-tlnH"])
    public = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        addr = parts[3]
        host, _, port = addr.rpartition(":")
        host = host.strip("[]")
        if host in ("127.0.0.1", "::1") or host.startswith("127.") or "%lo" in host:
            continue
        if port.isdigit():
            public[int(port)] = host
    names = {22: "SSH", 80: "Webserver", 443: "Webserver (HTTPS)", 445: "Windows-Freigabe (Samba)", 139: "Samba", 3389: "Remote-Desktop", 5900: "VNC",
             631: "Drucker (CUPS)", 3306: "MySQL", 5432: "PostgreSQL", 6379: "Redis", 27017: "MongoDB", 11434: "Ollama", 8765: "Lumen", 53: "DNS",
             5353: "mDNS", 1716: "KDE Connect", 2049: "NFS", 21: "FTP", 23: "Telnet", 25: "Mail"}
    risky = {23, 21, 5900, 3389, 6379, 27017, 3306, 5432, 445, 139, 2049}
    if rc == 127:
        F.append(_f("info", "Offene Dienste", "Konnte nicht prüfen (ss fehlt)."))
    elif not public:
        F.append(_f("ok", "Offene Dienste", "Kein Dienst ist aus dem Netz erreichbar."))
    else:
        lst = ", ".join(f"{p} ({names.get(p, '?')})" for p in sorted(public))
        bad = sorted(set(public) & risky)
        if bad:
            F.append(_f("warn", "Offene Dienste", f"Aus dem Netz erreichbar: {lst}.",
                        f"Heikel: {', '.join(names.get(p, str(p)) for p in bad)} – nur offen lassen, wenn du es brauchst; sonst Dienst stoppen oder per Firewall sperren."))
        else:
            F.append(_f("info", "Offene Dienste", f"Aus dem Netz erreichbar: {lst}. Unbekanntes prüfen: sudo ss -tlnp"))
    # SSH-Server
    if 22 in public or Path("/etc/ssh/sshd_config").exists() and _run(["systemctl", "is-active", "ssh"])[0].strip() == "active":
        conf = _read("/etc/ssh/sshd_config") + "".join(_read(p) for p in sorted(Path("/etc/ssh/sshd_config.d").glob("*.conf"))) if Path("/etc/ssh").exists() else ""
        opt = lambda k, default: (re.findall(rf"(?im)^\s*{k}\s+(\S+)", conf) or [default])[0].lower()
        issues = []
        if opt("PasswordAuthentication", "yes") != "no":
            issues.append("Passwort-Login erlaubt (besser nur Schlüssel: PasswordAuthentication no)")
        if opt("PermitRootLogin", "prohibit-password") == "yes":
            issues.append("Root-Login mit Passwort erlaubt (PermitRootLogin no)")
        F.append(_f("warn" if issues else "ok", "SSH-Server", "; ".join(issues) or "Läuft mit sicheren Einstellungen.",
                    "Datei /etc/ssh/sshd_config anpassen, dann: sudo systemctl restart ssh" if issues else ""))
    # Updates
    if shutil.which("apt-get"):
        out, rc = _run(["apt-get", "-s", "-o", "Debug::NoLocking=true", "upgrade"], 40)
        n = len(re.findall(r"(?m)^Inst ", out))
        sec = len(re.findall(r"(?m)^Inst .*security", out, re.I))
        auto = "1" in "".join(re.findall(r'Unattended-Upgrade\s+"(\d)"', _read("/etc/apt/apt.conf.d/20auto-upgrades")))
        if sec:
            F.append(_f("warn", "Updates", f"{sec} Sicherheits-Updates offen ({n} Updates gesamt).", "Installieren: sudo apt update && sudo apt upgrade"))
        else:
            F.append(_f("ok" if n < 30 else "info", "Updates", f"{n} Updates offen, keine davon als Sicherheits-Update markiert."))
        F.append(_f("ok" if auto else "info", "Automatische Sicherheits-Updates", "Eingeschaltet." if auto else "Nicht eingeschaltet.",
                    "" if auto else "sudo apt install unattended-upgrades && sudo dpkg-reconfigure unattended-upgrades"))
    elif shutil.which("dnf"):
        out, rc = _run(["dnf", "-q", "updateinfo", "list", "--security"], 60)
        n = len([l for l in out.splitlines() if l.strip()])
        F.append(_f("warn" if n else "ok", "Updates", f"{n} Sicherheits-Updates offen." if n else "Keine Sicherheits-Updates offen.", "sudo dnf upgrade" if n else ""))
    elif shutil.which("checkupdates"):
        out, rc = _run(["checkupdates"], 60)
        n = len(out.splitlines())
        F.append(_f("info" if n else "ok", "Updates", f"{n} Updates offen." if n else "System ist aktuell.", "sudo pacman -Syu" if n else ""))
    # Festplatten-Verschlüsselung
    out, rc = _run(["lsblk", "-rno", "TYPE,MOUNTPOINT"])
    if rc == 0:
        crypt = "crypt" in out
        F.append(_f("ok" if crypt else "info", "Festplatten-Verschlüsselung", "Aktiv (LUKS)." if crypt else "Nicht verschlüsselt.",
                    "" if crypt else "Wichtig bei Laptops: Bei Diebstahl sind sonst alle Dateien lesbar. Lässt sich am einfachsten bei einer Neuinstallation einschalten."))
    # sudo ohne Passwort
    nop = [p.name for p in list(Path("/etc/sudoers.d").glob("*")) if "NOPASSWD" in _read(p)] if Path("/etc/sudoers.d").exists() else []
    if nop:
        F.append(_f("info", "sudo ohne Passwort", f"Regeln in /etc/sudoers.d: {', '.join(nop)[:120]}", "Nur behalten, wenn du sie selbst angelegt hast."))
    # Bildschirmsperre
    out, rc = _run(["gsettings", "get", "org.gnome.desktop.screensaver", "lock-enabled"])
    if rc == 0 and out.strip() in ("true", "false"):
        on = out.strip() == "true"
        F.append(_f("ok" if on else "warn", "Bildschirmsperre", "Sperrt automatisch." if on else "Automatische Sperre ist aus.",
                    "" if on else "Einstellungen → Datenschutz → Bildschirmsperre einschalten."))
    # SSH-Schlüssel ohne Passphrase / Rechte
    ssh_dir = Path.home() / ".ssh"
    if ssh_dir.exists():
        loose = [p.name for p in ssh_dir.glob("id_*") if not p.name.endswith(".pub") and p.stat().st_mode & 0o077]
        if loose:
            F.append(_f("warn", "SSH-Schlüssel", f"Zu offene Dateirechte: {', '.join(loose)}", "chmod 600 ~/.ssh/id_*"))
    # Fehlgeschlagene Logins
    out, rc = _run(["journalctl", "-q", "--since", "-24h", "-g", "Failed password|authentication failure", "--no-pager", "-o", "cat"], 15)
    if rc == 0:
        n = len([l for l in out.splitlines() if l.strip()])
        if n > 20:
            F.append(_f("warn", "Fehlgeschlagene Anmeldungen", f"{n} in den letzten 24 Stunden – jemand probiert evtl. Passwörter durch.",
                        "Wenn SSH aus dem Internet erreichbar ist: fail2ban installieren und Passwort-Login abschalten."))
        elif n:
            F.append(_f("info", "Fehlgeschlagene Anmeldungen", f"{n} in den letzten 24 Stunden (meist eigene Vertipper)."))
    # USBGuard
    if shutil.which("usbguard"):
        F.append(_f("ok", "USBGuard", "Installiert – unbekannte USB-Geräte können blockiert werden."))
    return {"titel": "PC-Sicherheits-Check", "punkte": _score(F), "befunde": F, "zeit": time.strftime("%d.%m. %H:%M")}


# ================================================================ Heimnetz
OUI = {  # kleine Auswahl häufiger Hersteller (erste 3 Bytes der MAC)
    "b827eb": "Raspberry Pi", "dca632": "Raspberry Pi", "e45f01": "Raspberry Pi", "d83add": "Raspberry Pi", "2ccf67": "Raspberry Pi",
    "3c5ab4": "Google", "f4f5d8": "Google", "54600a": "Google", "001a11": "Google", "a47733": "Google", "1c53f9": "Google",
    "f0272d": "Amazon", "44650d": "Amazon", "fc65de": "Amazon", "68543a": "Amazon", "0c47c9": "Amazon", "74c246": "Amazon",
    "001132": "Synology", "0011d8": "ASUS", "ac220b": "ASUS", "2c56dc": "ASUS", "0c9d92": "ASUS",
    "3810d5": "AVM (FRITZ!Box)", "2c3afd": "AVM (FRITZ!Box)", "e0286d": "AVM (FRITZ!Box)", "c80e14": "AVM (FRITZ!Box)", "7cff4d": "AVM (FRITZ!Box)",
    "5c4979": "AVM (FRITZ!Box)", "dc396f": "AVM (FRITZ!Box)", "989bcb": "AVM (FRITZ!Box)", "444e6d": "AVM (FRITZ!Box)",
    "b0be76": "TP-Link", "50c7bf": "TP-Link", "ec086b": "TP-Link", "f4f26d": "TP-Link", "98dac4": "TP-Link", "1c61b4": "TP-Link",
    "001788": "Philips Hue", "ecb5fa": "Philips Hue", "000e58": "Sonos", "5caafd": "Sonos", "b8e937": "Sonos", "347e5c": "Sonos",
    "00e04c": "Realtek", "525400": "Virtuelle Maschine (QEMU)", "080027": "VirtualBox", "000c29": "VMware", "0242ac": "Docker",
    "a4c138": "Espressif (ESP/IoT)", "240ac4": "Espressif (ESP/IoT)", "30aea4": "Espressif (ESP/IoT)", "84f3eb": "Espressif (ESP/IoT)",
    "ecfabc": "Espressif (ESP/IoT)", "bcddc2": "Espressif (ESP/IoT)", "7c9ebd": "Espressif (ESP/IoT)", "d8bfc0": "Espressif (ESP/IoT)",
    "7c2ebd": "Google", "001e06": "Wibrain", "0017c8": "Kyocera", "3c2af4": "Brother", "001ba9": "Brother", "30055c": "Brother",
    "00804f": "Daikin", "7483c2": "Ubiquiti", "fcecda": "Ubiquiti", "245a4c": "Ubiquiti", "18e829": "Ubiquiti",
    "a85e45": "ASUS", "04d9f5": "ASUS", "7085c2": "ASRock", "d85ed3": "Gigabyte", "1c697a": "EliteGroup", "00d861": "MSI", "2cf05d": "MSI",
    "001422": "Dell", "f8bc12": "Dell", "3c2c30": "Dell", "9c7bef": "HP", "3024a9": "HP", "001b63": "Apple",
    "a4831c": "Apple", "f01898": "Apple", "3c0754": "Apple", "8866a5": "Apple", "d0817a": "Apple", "acbc32": "Apple", "f4f15a": "Apple",
    "8c8590": "Apple", "5855ca": "Apple", "0c4de9": "Apple", "38f9d3": "Apple", "001a2b": "Ayecom", "9c5c8e": "ASUS",
    "0024e4": "Withings", "64166d": "Xiaomi", "7811dc": "Xiaomi", "286c07": "Xiaomi", "50ec50": "Xiaomi", "f8a45f": "Xiaomi",
    "8cf5a3": "Samsung", "f025b7": "Samsung", "5c497d": "Samsung", "bc7e8b": "Samsung", "cc6ea4": "Samsung", "7c6456": "Samsung",
    "0009bf": "Nintendo", "98b6e9": "Nintendo", "7cbb8a": "Nintendo", "00d9d1": "Sony (PlayStation)", "fc0fe6": "Sony (PlayStation)",
    "bc60a7": "Sony (PlayStation)", "7c1e52": "Microsoft (Xbox/Surface)", "985fd3": "Microsoft (Xbox/Surface)", "001dd8": "Microsoft",
    "e8de27": "TP-Link", "a842a1": "TP-Link", "00226b": "Linksys", "c0c1c0": "Linksys", "a021b7": "Netgear", "9c3dcf": "Netgear",
}


def _local_net():
    """(iface, eigene IP, Netz) des Standard-Netzwerks – nur private Netze."""
    out, rc = _run(["ip", "-j", "route", "get", "1.1.1.1"])
    try:
        r = json.loads(out)[0]
        dev, src = r["dev"], r["prefsrc"]
        a, _ = _run(["ip", "-j", "-4", "addr", "show", "dev", dev])
        for info in json.loads(a)[0]["addr_info"]:
            if info["local"] == src:
                net = ipaddress.ip_network(f"{src}/{info['prefixlen']}", strict=False)
                if not net.is_private:
                    raise RuntimeError("Dieses Gerät hängt direkt an einem öffentlichen Netz – Heimnetz-Scan nur in privaten Netzen.")
                if net.num_addresses > 1024:
                    net = ipaddress.ip_network(f"{src}/24", strict=False)
                return dev, src, net, r.get("gateway")
    except RuntimeError:
        raise
    except Exception:
        pass
    raise RuntimeError("Kein lokales Netzwerk gefunden (nicht verbunden?).")


def _vendor(mac):
    m = mac.lower().replace(":", "")
    if len(m) >= 2 and int(m[1], 16) & 2:
        return "zufällige MAC (Handy/Tablet mit Privatsphäre-Schutz)"
    return OUI.get(m[:6], "")


def lan_scan():
    dev, me, net, gw = _local_net()
    hosts = [str(h) for h in net.hosts()]

    def ping(ip):
        subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True, env=ENV_C, stdin=subprocess.DEVNULL, timeout=4)

    if shutil.which("ping"):
        with ThreadPoolExecutor(64) as ex:
            list(ex.map(lambda ip: _try(ping, ip), hosts))
    out, _ = _run(["ip", "-j", "neigh", "show", "dev", dev])
    try:
        neigh = json.loads(out)
    except Exception:
        neigh = []
    d = _load()
    known = d["lan_known"]
    first = not known
    devices = []
    for n in neigh:
        ip, mac = n.get("dst"), (n.get("lladdr") or "").lower()
        if not mac or ":" in (ip or "") or "FAILED" in (n.get("state") or []) or ip not in hosts:
            continue
        try:
            name = socket.gethostbyaddr(ip)[0]
        except Exception:
            name = ""
        k = known.get(mac)
        if first:  # erster Scan: alles Vorhandene gilt als bekannt
            k = known[mac] = {"name": "", "seit": time.strftime("%d.%m.%Y")}
        devices.append({"ip": ip, "mac": mac, "hersteller": _vendor(mac), "hostname": name, "name": (k or {}).get("name", ""),
                        "bekannt": bool(k), "router": ip == gw})
    devices.sort(key=lambda x: tuple(int(p) for p in x["ip"].split(".")))
    if first:
        _save(d)
    new = [x for x in devices if not x["bekannt"]]
    F = [_f("ok", "Geräte im Netz", f"{len(devices)} Geräte in {net} gefunden (plus dieser PC, {me}).")]
    if first:
        F.append(_f("info", "Erster Scan", "Alle jetzt gefundenen Geräte gelten als bekannt. Ab jetzt meldet Lumen neue Geräte. Gib ihnen Namen, dann erkennst du sie wieder."))
    elif new:
        F.append(_f("warn", f"{len(new)} neue(s) Gerät(e)", ", ".join(f"{x['ip']} ({x['hersteller'] or x['hostname'] or x['mac']})" for x in new)[:300],
                    "Kennst du es? → „Bekannt“ klicken. Wenn nicht: WLAN-Passwort ändern und im Router nachsehen."))
    else:
        F.append(_f("ok", "Keine unbekannten Geräte", "Alles, was online ist, kennst du schon."))
    return {"titel": "Heimnetz", "netz": str(net), "ich": me, "router": gw, "geraete": devices, "befunde": F, "zeit": time.strftime("%d.%m. %H:%M")}


def _try(fn, *a):
    try:
        fn(*a)
    except Exception:
        pass


def lan_trust(mac, name="", trust=True):
    mac = str(mac).lower()
    if not re.fullmatch(r"([0-9a-f]{2}:){5}[0-9a-f]{2}", mac):
        raise RuntimeError("Ungültige MAC-Adresse.")
    with LOCK:
        d = _load()
        if trust:
            d["lan_known"][mac] = {"name": str(name)[:40], "seit": d["lan_known"].get(mac, {}).get("seit") or time.strftime("%d.%m.%Y")}
        else:
            d["lan_known"].pop(mac, None)
        _save(d)
    return "Gespeichert."


# ================================================================ USB
USB_KNOWN = {  # (vid, pid|None) -> (Name, Art, Hinweis)
    ("1d50", "6089"): ("HackRF One", "funk", "Software Defined Radio 1 MHz–6 GHz. Lumen nutzt es nur zum Empfangen (Spektrum-Scan, Signal-Test)."),
    ("1d50", "604b"): ("HackRF Jawbreaker", "funk", "Software Defined Radio."),
    ("1d50", "cc15"): ("rad1o (HackRF-kompatibel)", "funk", "Software Defined Radio."),
    ("0bda", "2838"): ("RTL-SDR (RTL2832U)", "funk", "Empfänger ca. 24 MHz–1,7 GHz (nur Empfang)."),
    ("0bda", "2832"): ("RTL-SDR (RTL2832U)", "funk", "Empfänger (nur Empfang)."),
    ("1d50", "6002"): ("Ubertooth One", "funk", "Bluetooth-Analyse-Werkzeug."),
    ("1d50", "60a1"): ("Airspy", "funk", "SDR-Empfänger."),
    ("0483", "5740"): ("Flipper Zero / STM32 (serielle Schnittstelle)", "werkzeug", "Multi-Tool für Funk/NFC/Infrarot – kann auch als Tastatur auftreten (BadUSB)."),
    ("9ac4", "4b8f"): ("Proxmark3", "werkzeug", "RFID/NFC-Analyse-Werkzeug."),
    ("2d2d", "504d"): ("Proxmark3", "werkzeug", "RFID/NFC-Analyse-Werkzeug."),
    ("1050", None): ("YubiKey", "schluessel", "Sicherheitsschlüssel für Zwei-Faktor-Anmeldung."),
    ("096e", None): ("FEITIAN Sicherheitsschlüssel", "schluessel", "Sicherheitsschlüssel (FIDO)."),
    ("20a0", "42b1"): ("Nitrokey", "schluessel", "Sicherheitsschlüssel."),
    ("2341", "8036"): ("Arduino Leonardo", "badusb", "Mikrocontroller, der sich als Tastatur ausgeben kann."),
    ("2341", "8037"): ("Arduino Micro", "badusb", "Mikrocontroller, der sich als Tastatur ausgeben kann."),
    ("16c0", "0486"): ("Teensy (HID)", "badusb", "Mikrocontroller, der sich als Tastatur ausgeben kann."),
    ("16c0", "27db"): ("Digispark (Tastatur)", "badusb", "Mini-Mikrocontroller, typisch für BadUSB-Basteleien."),
    ("16c0", "27dd"): ("Digispark/CDC", "badusb", "Mini-Mikrocontroller."),
    ("03eb", "2401"): ("USB Rubber Ducky (ältere Firmware)", "badusb", "Tastatur-Angriffswerkzeug."),
    ("f000", "ff01"): ("O.MG / Rubber-Ducky-artiges Gerät", "badusb", "Tastatur-Angriffswerkzeug."),
    ("0bda", "8812"): ("WLAN-Adapter RTL8812AU (z. B. Alfa)", "wlan", "WLAN-Adapter mit Monitor-Modus."),
    ("148f", "3070"): ("WLAN-Adapter Ralink RT3070 (z. B. Alfa)", "wlan", "WLAN-Adapter mit Monitor-Modus."),
    ("0cf3", "9271"): ("WLAN-Adapter Atheros AR9271", "wlan", "WLAN-Adapter mit Monitor-Modus."),
    ("0e8d", "7612"): ("WLAN-Adapter MediaTek MT7612U", "wlan", "WLAN-Adapter mit Monitor-Modus."),
}
USB_CLASS = {"01": "Audio", "02": "Kommunikation/Modem", "03": "Eingabegerät (HID)", "06": "Kamera/Bilder", "07": "Drucker", "08": "Speicher",
             "09": "USB-Hub", "0a": "Daten (CDC)", "0b": "Chipkarte", "0e": "Video/Webcam", "e0": "Funk (Bluetooth/WLAN)", "ef": "Verschiedenes",
             "fe": "Anwendungs-spezifisch", "ff": "Hersteller-spezifisch"}
SYS_USB = Path("/sys/bus/usb/devices")


def _sys(p, name):
    try:
        return (p / name).read_text("utf-8", "replace").strip()
    except Exception:
        return ""


def usb_devices():
    """Angeschlossene USB-Geräte aus /sys (ohne Root, ohne Zusatzprogramme)."""
    devs = []
    if not SYS_USB.exists():
        raise RuntimeError("USB-Übersicht gibt es nur unter Linux.")
    known = _load()["usb_known"]
    for p in sorted(SYS_USB.iterdir()):
        vid, pid = _sys(p, "idVendor"), _sys(p, "idProduct")
        if not vid or ":" in p.name:
            continue
        classes, keyboard, storage, net = set(), False, False, False
        dc = _sys(p, "bDeviceClass")
        if dc and dc != "00":
            classes.add(dc)
        for i in p.glob(p.name + ":*"):
            c, sc, pr = _sys(i, "bInterfaceClass"), _sys(i, "bInterfaceSubClass"), _sys(i, "bInterfaceProtocol")
            if c:
                classes.add(c)
            keyboard |= c == "03" and pr == "01"
            storage |= c == "08"
            net |= (c == "02" and sc == "06") or (c == "e0" and sc == "01" and pr == "03") or (c == "ef" and sc == "04")
        hub = "09" in classes
        if hub and vid == "1d6b":
            continue  # interne Root-Hubs
        serial = _sys(p, "serial")
        key = f"{vid}:{pid}:{serial or '-'}"
        info = USB_KNOWN.get((vid, pid)) or USB_KNOWN.get((vid, None))
        name = (info[0] if info else "") or " ".join(x for x in (_sys(p, "manufacturer"), _sys(p, "product")) if x) or f"Gerät {vid}:{pid}"
        art = info[1] if info else ("tastatur" if keyboard else "speicher" if storage else "netz" if net else "hub" if hub else "sonst")
        devs.append({"key": key, "id": f"{vid}:{pid}", "name": name[:80], "art": art, "hinweis": info[2] if info else "",
                     "klassen": sorted(USB_CLASS.get(c, c) for c in classes), "tastatur": keyboard, "speicher": storage, "netz": net,
                     "port": p.name, "tempo": _sys(p, "speed"), "bekannt": key in known, "eigener_name": known.get(key, {}).get("name", "")})
    return devs


def usb_overview():
    devs = usb_devices()
    d = _load()
    if not d["usb_known"] and devs:  # erstes Mal: alles Angeschlossene gilt als vertraut
        with LOCK:
            d = _load()
            for x in devs:
                d["usb_known"][x["key"]] = {"name": "", "seit": time.strftime("%d.%m.%Y")}
                x["bekannt"] = True
            _save(d)
    F = []
    for x in devs:
        if x["art"] == "badusb" or (x["art"] in ("werkzeug",) and x["tastatur"]):
            F.append(_f("warn", x["name"], x["hinweis"] + (" Gibt sich gerade als Tastatur aus." if x["tastatur"] else ""),
                        "Nur angesteckt lassen, wenn es dein eigenes Gerät ist."))
        elif x["art"] in ("funk", "werkzeug", "wlan", "schluessel"):
            F.append(_f("info", x["name"], x["hinweis"]))
        elif not x["bekannt"] and (x["tastatur"] or x["netz"]):
            F.append(_f("warn", f"Neu: {x['name']}", "Unbekannte Tastatur – so tarnen sich BadUSB-Sticks." if x["tastatur"] else "Unbekannter Netzwerk-Adapter – kann Datenverkehr umleiten.",
                        "Wenn du das Gerät nicht selbst angesteckt hast: abziehen."))
    if not F:
        F.append(_f("ok", "Nichts Auffälliges", f"{len(devs)} USB-Geräte angeschlossen, alle unauffällig."))
    guard = None
    if shutil.which("usbguard"):
        out, rc = _run(["systemctl", "is-active", "usbguard"])
        guard = out.strip() == "active"
    return {"titel": "USB-Geräte", "geraete": devs, "befunde": F, "usbguard": guard, "zeit": time.strftime("%d.%m. %H:%M")}


def usb_trust(key, name="", trust=True):
    if not re.fullmatch(r"[0-9a-f]{4}:[0-9a-f]{4}:.{1,80}", str(key)):
        raise RuntimeError("Unbekanntes Gerät.")
    with LOCK:
        d = _load()
        if trust:
            d["usb_known"][key] = {"name": str(name)[:40], "seit": d["usb_known"].get(key, {}).get("seit") or time.strftime("%d.%m.%Y")}
        else:
            d["usb_known"].pop(key, None)
        _save(d)
    return "Gespeichert."


_usb_last = None


def usb_watch(mode="wichtig"):
    """Für den Hintergrund: meldet neu angesteckte Geräte. mode: aus | wichtig (Tastatur/Netz/Werkzeuge) | alle.
    Gibt Liste von (titel, text, dringend) zurück."""
    global _usb_last
    if mode == "aus" or not SYS_USB.exists():
        return []
    try:
        devs = usb_devices()
    except Exception:
        return []
    now = {x["key"]: x for x in devs}
    if _usb_last is None:
        _usb_last = set(now)
        if not _load()["usb_known"]:
            _try(usb_overview)
        return []
    out = []
    for k in set(now) - _usb_last:
        x = now[k]
        if x["bekannt"] and mode != "alle":
            continue
        if x["art"] == "badusb" or (not x["bekannt"] and x["tastatur"]):
            out.append(("⚠️ Neue USB-Tastatur", f"{x['name']} wurde angesteckt und verhält sich wie eine Tastatur. Nicht von dir? Sofort abziehen – "
                                               f"so funktionieren BadUSB-Angriffe.", True))
        elif not x["bekannt"] and x["netz"]:
            out.append(("⚠️ Neuer USB-Netzwerkadapter", f"{x['name']} wurde angesteckt. Nicht von dir? Abziehen.", True))
        elif x["art"] in ("funk", "werkzeug", "wlan", "schluessel"):
            out.append(("🔌 " + x["name"], x["hinweis"] or "Angeschlossen.", False))
        elif mode == "alle" or (not x["bekannt"] and x["speicher"]):
            out.append(("🔌 USB-Gerät angesteckt", x["name"] + (" (Speicher – Dateien vor dem Öffnen prüfen, wenn der Stick nicht deiner ist)" if x["speicher"] else ""), False))
    _usb_last = set(now)
    return out


# ================================================================ Funk (HackRF / RTL-SDR) – NUR EMPFANG
BANDS = [  # (von MHz, bis MHz, Name) – Europa
    (0.15, 0.285, "Langwelle-Rundfunk"), (0.5265, 1.6065, "Mittelwelle-Rundfunk"), (3.5, 3.8, "Amateurfunk 80 m"), (7.0, 7.2, "Amateurfunk 40 m"),
    (14.0, 14.35, "Amateurfunk 20 m"), (26.965, 27.405, "CB-Funk"), (28.0, 29.7, "Amateurfunk 10 m"), (87.5, 108.0, "UKW-Radio (FM)"),
    (108.0, 137.0, "Flugfunk"), (137.0, 138.0, "Wettersatelliten"), (144.0, 146.0, "Amateurfunk 2 m"), (148.0, 174.0, "Betriebsfunk/BOS/Seefunk"),
    (174.0, 240.0, "DAB+ Digitalradio"), (380.0, 400.0, "TETRA (Behördenfunk, verschlüsselt)"), (430.0, 440.0, "Amateurfunk 70 cm / ISM 433"),
    (433.05, 434.79, "ISM 433 MHz (Funksteckdosen, Wetterstationen, Autoschlüssel)"), (446.0, 446.2, "PMR446 (Walkie-Talkies)"),
    (470.0, 694.0, "DVB-T2 Fernsehen"), (703.0, 788.0, "Mobilfunk 700 (LTE/5G)"), (791.0, 862.0, "Mobilfunk 800 (LTE)"),
    (863.0, 870.0, "ISM 868 MHz (Smart Home, Zigbee-ähnlich, LoRa, Alarmanlagen)"), (880.0, 960.0, "Mobilfunk 900 (GSM/LTE)"),
    (1090.0, 1090.0, "ADS-B (Flugzeug-Transponder)"), (1164.0, 1300.0, "Satellitennavigation (GPS L2/L5, Galileo)"),
    (1452.0, 1492.0, "Mobilfunk 1500"), (1559.0, 1610.0, "Satellitennavigation (GPS L1, Galileo, GLONASS)"), (1710.0, 1880.0, "Mobilfunk 1800 (LTE)"),
    (1880.0, 1900.0, "DECT (Schnurlostelefone)"), (1920.0, 2170.0, "Mobilfunk 2100 (LTE/5G)"), (2400.0, 2483.5, "WLAN 2,4 GHz / Bluetooth / Zigbee"),
    (2500.0, 2690.0, "Mobilfunk 2600 (LTE)"), (3400.0, 3800.0, "5G (3,6 GHz)"), (5150.0, 5725.0, "WLAN 5 GHz"), (5725.0, 5875.0, "WLAN 5 GHz / ISM 5,8 GHz"),
]
SWEEP_PRESETS = {"ukw": (87, 108), "433": (432, 436), "868": (862, 871), "wlan": (2400, 2484), "mobilfunk": (700, 960), "alles": (50, 2700),
                 "dab": (174, 240), "flugfunk": (108, 137), "5ghz": (5150, 5875)}


def band_of(mhz):
    hits = [(b - a, n) for a, b, n in BANDS if a - 0.3 <= mhz <= b + 0.3]
    return min(hits)[1] if hits else ""


def sdr_info():
    """Welche Funk-Hardware ist da und funktioniert sie?"""
    F, found = [], []
    usb = {x["id"]: x for x in _safe(usb_devices, [])}
    if shutil.which("hackrf_info"):
        out, rc = _run(["hackrf_info"], 10)
        if rc == 0 and "Serial number" in out:
            g = lambda k: (re.findall(rf"{k}:\s*(.+)", out) or ["?"])[0].strip()
            found.append({"typ": "HackRF", "board": g("Board ID Number"), "firmware": g("Firmware Version"), "seriennummer": g("Serial number")[-8:],
                          "bereich": "1 MHz – 6 GHz"})
            F.append(_f("ok", "HackRF bereit", f"{g('Board ID Number')} · Firmware {g('Firmware Version')}"))
        elif any(i.startswith("1d50:6089") or i.startswith("1d50:604b") for i in usb):
            F.append(_f("warn", "HackRF angesteckt, aber nicht ansprechbar", out.strip()[:200] or "Kein Zugriff.",
                        "Meist fehlen Rechte: sudo usermod -aG plugdev $USER, dann ab- und wieder anmelden. Oder ein anderes Programm (GQRX, SDR++) nutzt es gerade."))
        else:
            F.append(_f("info", "Kein HackRF angeschlossen", "Die Programme sind installiert, aber es steckt kein Gerät."))
    elif any(i.startswith("1d50:6089") for i in usb):
        F.append(_f("warn", "HackRF erkannt – Programme fehlen", "hackrf_info/hackrf_sweep sind nicht installiert.", "Installieren: sudo apt install hackrf"))
    if any(i in ("0bda:2838", "0bda:2832") for i in usb):
        ok = bool(shutil.which("rtl_power"))
        found.append({"typ": "RTL-SDR", "bereich": "ca. 24 MHz – 1,7 GHz"})
        F.append(_f("ok" if ok else "warn", "RTL-SDR erkannt", "Bereit für Spektrum-Scans." if ok else "rtl_power fehlt.", "" if ok else "Installieren: sudo apt install rtl-sdr"))
    if not F:
        F.append(_f("info", "Keine Funk-Hardware gefunden", "Unterstützt: HackRF One (empfohlen) und RTL-SDR-Sticks.", "HackRF anstecken und: sudo apt install hackrf"))
    F.append(_f("info", "Nur Empfang", "Lumen sendet nie Funksignale: kein Stören, kein Nachsenden (Replay) fremder Signale. Senden ist ohne Lizenz verboten und kann Notrufe, Flugfunk oder Nachbarn stören."))
    return {"titel": "Funk-Hardware", "geraete": found, "befunde": F}


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _sweep_raw(lo, hi, seconds=4):
    """Liefert {freq_mhz: dBm} (Maximum je Frequenz). Nutzt hackrf_sweep, sonst rtl_power."""
    lo, hi = int(lo), int(max(hi, lo + 1))
    if not (1 <= lo < hi <= 6000):
        raise RuntimeError("Bereich bitte zwischen 1 und 6000 MHz.")
    span = hi - lo
    if shutil.which("hackrf_sweep") and _safe(lambda: "Serial number" in _run(["hackrf_info"], 8)[0], False):
        binw = 100000 if span <= 30 else 500000 if span <= 300 else 1000000
        n = max(1, min(8, int(seconds * (20 if span < 100 else 4) / max(1, span / 20)) or 1))
        try:
            r = subprocess.run(["hackrf_sweep", "-f", f"{lo}:{hi}", "-w", str(binw), "-N", str(n), "-l", "32", "-g", "30", "-a", "0"],
                               capture_output=True, text=True, timeout=45 + span // 50, env=ENV_C, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            raise RuntimeError("Der Scan hat zu lange gedauert – kleineren Bereich wählen.")
        if not r.stdout.strip():
            raise RuntimeError("hackrf_sweep lieferte keine Daten: " + (r.stderr.strip()[:200] or "unbekannter Fehler"))
        data = {}
        for line in r.stdout.splitlines():
            p = [x.strip() for x in line.split(",")]
            if len(p) < 7:
                continue
            try:
                f0, bw = float(p[2]), float(p[4])
                for i, v in enumerate(p[6:]):
                    f = round((f0 + bw * (i + 0.5)) / 1e6, 3)
                    if lo <= f <= hi:
                        data[f] = max(data.get(f, -200.0), float(v))
            except ValueError:
                continue
        return data, "HackRF"
    if shutil.which("rtl_power"):
        if hi > 1750 or lo < 24:
            raise RuntimeError("Der RTL-SDR-Stick kann nur ca. 24–1750 MHz. Für mehr brauchst du den HackRF.")
        step = "25k" if span <= 30 else "200k" if span <= 300 else "1M"
        out, rc = _run(["rtl_power", "-f", f"{lo}M:{hi}M:{step}", "-i", "2", "-1", "-"], 60 + span // 20)
        data = {}
        for line in out.splitlines():
            p = [x.strip() for x in line.split(",")]
            if len(p) < 7:
                continue
            try:
                f0, bw = float(p[2]), float(p[4])
                for i, v in enumerate(p[6:]):
                    data[round((f0 + bw * i) / 1e6, 3)] = float(v)
            except ValueError:
                continue
        if not data:
            raise RuntimeError("rtl_power lieferte keine Daten (Stick belegt oder Treiber-Konflikt?).")
        return data, "RTL-SDR"
    raise RuntimeError("Kein Funk-Empfänger bereit. HackRF anstecken und „sudo apt install hackrf“ – Details im Reiter Funk.")


def _peaks(data, top=8):
    fs = sorted(data)
    vals = sorted(data.values())
    floor = vals[len(vals) // 2]  # Median = Rauschteppich
    cand = []
    for i, f in enumerate(fs):
        v = data[f]
        if v < floor + 8:
            continue
        if all(v >= data[fs[j]] for j in range(max(0, i - 3), min(len(fs), i + 4))):
            cand.append((v, f))
    cand.sort(reverse=True)
    out = []
    for v, f in cand:
        if all(abs(f - o["mhz"]) > max(0.15, (fs[-1] - fs[0]) / 60) for o in out):
            out.append({"mhz": round(f, 3), "dbm": round(v, 1), "über_rauschen_db": round(v - floor, 1), "band": band_of(f) or "unbekannt"})
        if len(out) >= top:
            break
    return out, round(floor, 1)


def sdr_sweep(start_mhz=None, end_mhz=None, preset=None):
    """Spektrum-Scan (nur Empfang): misst die Signalstärke je Frequenz und nennt die stärksten Signale."""
    if preset:
        if preset not in SWEEP_PRESETS:
            raise RuntimeError("Bereiche: " + ", ".join(SWEEP_PRESETS))
        start_mhz, end_mhz = SWEEP_PRESETS[preset]
    if start_mhz is None or end_mhz is None:
        start_mhz, end_mhz = SWEEP_PRESETS["433"]
    data, dev = _sweep_raw(float(start_mhz), float(end_mhz))
    peaks, floor = _peaks(data)
    fs = sorted(data)
    step = max(1, len(fs) // 400)
    pts = [[f, round(max(data[x] for x in fs[i:i + step]), 1)] for i, f in list(enumerate(fs))[::step]]
    return {"titel": f"Spektrum {start_mhz:g}–{end_mhz:g} MHz", "geraet": dev, "von": float(start_mhz), "bis": float(end_mhz), "rauschen_dbm": floor,
            "signale": peaks, "punkte": pts,
            "hinweis": "Gemessen wird nur die Stärke, kein Inhalt. Starke Signale in der Nähe (eigener Router, Handy) dominieren das Bild."}


_baseline = {}


def signal_test_step(band="433", step=1):
    """Für Chat/Knöpfe: Schritt 1 = Ruhe-Messung merken, Schritt 2 = mit gedrückter Taste vergleichen."""
    band = str(band)
    if int(step) == 1:
        r = sdr_signal_test(band)
        _baseline[band] = (time.time(), r["ruhe"])
        return {"schritt": 1, "band": band, "text": r["text"]}
    t, base = _baseline.get(band, (0, None))
    if not base or time.time() - t > 600:
        raise RuntimeError("Erst die Ruhe-Messung machen (Schritt 1).")
    return sdr_signal_test(band, before=base)


def sdr_signal_test(band="433", seconds=6, before=None):
    """Zwei Messungen vergleichen: sendet MEINE Fernbedienung/mein Funkschlüssel – und auf welcher Frequenz?
    Aufruf 1 (before=None): Ruhe-Messung. Aufruf 2 mit dem Ergebnis: während die Taste gedrückt wird."""
    if band not in ("433", "868", "315", "2400"):
        raise RuntimeError("Band: 433, 868, 315 oder 2400.")
    lo, hi = {"433": (432, 436), "868": (862, 871), "315": (313, 317), "2400": (2400, 2484)}[band]
    data, dev = _sweep_raw(lo, hi, seconds)
    if before is None:
        return {"schritt": 1, "band": band, "ruhe": {str(k): v for k, v in data.items()},
                "text": "Ruhe-Messung fertig. Jetzt die Taste der Fernbedienung gedrückt halten und die zweite Messung starten."}
    base = {float(k): v for k, v in before.items()}
    diff = {f: v - base.get(f, min(base.values())) for f, v in data.items()}
    f, d = max(diff.items(), key=lambda kv: kv[1])
    if d >= 10:
        return {"schritt": 2, "sendet": True, "mhz": round(f, 3), "stärker_db": round(d, 1), "dbm": round(data[f], 1),
                "text": f"✅ Ja, sie sendet: auf {f:.2f} MHz ({band_of(f) or 'ISM'}), {d:.0f} dB stärker als in Ruhe."}
    return {"schritt": 2, "sendet": False, "text": f"Kein neues Signal im {band}-MHz-Band erkannt. Batterie leer? Oder sie funkt in einem anderen Band "
                                                 f"(433/868/315/2400 probieren) – oder sie nutzt Infrarot."}


# ================================================================ Domain-Report (OSINT)
SEC_HEADERS = {
    "strict-transport-security": ("HSTS", "erzwingt HTTPS", "warn"),
    "content-security-policy": ("Content-Security-Policy", "bremst eingeschleuste Skripte (XSS)", "warn"),
    "x-frame-options": ("X-Frame-Options", "verhindert Einbetten in fremde Seiten (Clickjacking)", "info"),
    "x-content-type-options": ("X-Content-Type-Options", "verhindert Raten des Dateityps", "info"),
    "referrer-policy": ("Referrer-Policy", "verrät weniger über Besucher", "info"),
    "permissions-policy": ("Permissions-Policy", "sperrt Kamera/Mikro/Standort für Fremdskripte", "info"),
}


def headers_check(url):
    if not re.match(r"https?://", url):
        url = "https://" + url
    st, hd, _ = osint._req(url, timeout=15, max_bytes=20000)
    h = {k.lower(): v for k, v in dict(hd).items()}
    F = []
    for key, (name, why, lvl) in SEC_HEADERS.items():
        if key == "x-frame-options" and "frame-ancestors" in h.get("content-security-policy", ""):
            F.append(_f("ok", name, "Über CSP frame-ancestors gelöst."))
        elif key in h:
            F.append(_f("ok", name, h[key][:120]))
        else:
            F.append(_f(lvl, name + " fehlt", why[0].upper() + why[1:] + "."))
    for leak in ("server", "x-powered-by", "x-aspnet-version"):
        if leak in h and re.search(r"\d", h[leak]):
            F.append(_f("info", "Verrät Software-Version", f"{leak}: {h[leak][:80]}", "Versionsnummern ausblenden – sie helfen Angreifern, passende Lücken zu finden."))
    ck = hd.get_all("Set-Cookie") if hasattr(hd, "get_all") else []
    weak = [c.split("=")[0] for c in ck or [] if "secure" not in c.lower() or "httponly" not in c.lower()]
    if weak:
        F.append(_f("info", "Cookies ohne Secure/HttpOnly", ", ".join(weak)[:120]))
    return {"url": url, "status": st, "befunde": F}


def domain_report(domain):
    """Rundum-Bericht über eine Website/Domain (öffentliche Daten): Besitz, DNS, Mail-Schutz, TLS, Sicherheits-Header, Subdomains, Technik."""
    host = osint._host_of(domain)
    if not host or "." not in host or osint._is_ip(host):
        raise RuntimeError("Bitte eine Domain angeben, z. B. beispiel.de")
    F, parts = [], {}

    def step(name, fn):
        try:
            parts[name] = fn()
        except Exception as e:
            parts[name] = {"fehler": str(e)[:150]}
        return parts[name]

    with ThreadPoolExecutor(6) as ex:
        futs = {"whois": ex.submit(step, "whois", lambda: osint.whois(host)), "dns": ex.submit(step, "dns", lambda: osint.dns_lookup(host)),
                "ssl": ex.submit(step, "ssl", lambda: osint.ssl_check(host)), "header": ex.submit(step, "header", lambda: headers_check(host)),
                "sub": ex.submit(step, "sub", lambda: osint.subdomains(host)), "tech": ex.submit(step, "tech", lambda: osint.site_tech("https://" + host))}
        for f in futs.values():
            f.result()
    w, d, s, h, sub = parts["whois"], parts["dns"], parts["ssl"], parts["header"], parts["sub"]
    if "fehler" not in w:
        age = w.get("alter_tage")
        F.append(_f("warn" if isinstance(age, int) and age < 60 else "ok", "Domain",
                    f"Registriert: {w.get('registriert') or '?'} · Registrar: {w.get('registrar') or '?'}" + (f" · {age} Tage alt" if isinstance(age, int) else ""),
                    "Sehr junge Domains werden oft für Betrug benutzt." if isinstance(age, int) and age < 60 else ""))
    ms = d.get("mail_schutz") if isinstance(d, dict) else None
    if ms:
        lvl = {"gut": "ok", "unsicher": "kritisch"}.get(ms["bewertung"], "warn")
        F.append(_f(lvl, "Mail-Schutz (SPF/DMARC)", f"Bewertung: {ms['bewertung']}. SPF: {str(ms['spf'])[:70]} · DMARC: {str(ms['dmarc'])[:70]}",
                    "" if lvl == "ok" else "Ohne SPF + DMARC (p=quarantine/reject) kann jeder Mails im Namen dieser Domain fälschen."))
    if "fehler" in s or s.get("gültig") is False:
        F.append(_f("kritisch", "HTTPS/TLS", str(s.get("fehler") or s.get("warnung") or "Zertifikat ungültig oder kein HTTPS.")[:160], "Zertifikat einrichten (kostenlos mit Let's Encrypt)."))
    else:
        days = s.get("tage_übrig")
        probs = [x for x in (s.get("warnung"), "selbst signiert" if s.get("selbst_signiert") else None, s.get("fehler_pruefung")) if x]
        F.append(_f("warn" if probs or (isinstance(days, int) and days < 14) else "ok", "HTTPS/TLS",
                    (f"Zertifikat noch {days} Tage gültig. " if isinstance(days, int) else "") + ("; ".join(map(str, probs))[:160] if probs else "Keine Probleme.")))
    if "fehler" not in h:
        F += h["befunde"]
    subs = (sub.get("subdomains") if isinstance(sub, dict) else sub) or []
    if subs and "fehler" not in (sub if isinstance(sub, dict) else {}):
        odd = [x for x in subs if re.search(r"(^|\.)(dev|test|staging|old|backup|admin|vpn|intern|git|jenkins|db)\.", str(x))]
        F.append(_f("info" if not odd else "warn", f"{len(subs)} Subdomains öffentlich bekannt", ", ".join(map(str, subs[:12]))[:240],
                    f"Heikel wirkende Namen: {', '.join(map(str, odd[:6]))} – prüfen, ob die aus dem Internet erreichbar sein müssen." if odd else ""))
    return {"titel": f"Domain-Report: {host}", "punkte": _score(F), "befunde": F, "technik": parts.get("tech"), "dns": {k: v for k, v in (d or {}).items() if k in ("A", "AAAA", "MX", "NS")},
            "hinweis": "Nur öffentlich abrufbare Daten. Für Port-Scans gilt weiter: nur eigene Server."}
