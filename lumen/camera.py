"""Überwachungskameras (IP-Kameras im eigenen Netz) – Live-Bild & Schnappschuss.

Verbindung über RTSP (fast jede IP-Kamera kann das) mit ffmpeg. Passwörter liegen nur in
~/.lumen/cameras.json (Rechte 600), werden nie an die KI gegeben, nie angezeigt und in
Fehlermeldungen geschwärzt. Lumen probiert keine fremden Passwörter durch.
"""
import base64
import ipaddress
import json
import os
import re
import secrets
import shutil
import socket
import struct
import subprocess
import threading
import time
import urllib.parse
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DIR = Path.home() / ".lumen"
DATA = DIR / "cameras.json"
LOCK = threading.Lock()

# Marke → Anzeigename, RTSP-Pfade (Haupt-, Unterstream), Port, Hinweis zum Einrichten
BRANDS = {
    "reolink": dict(label="Reolink", paths=[("/h264Preview_01_main", "/h264Preview_01_sub"), ("/Preview_01_main", "/Preview_01_sub")],
                    tip="In der Reolink-App/Weboberfläche: Einstellungen → Netzwerk → Erweitert → Server-Einstellungen → RTSP einschalten. Benutzer meist „admin“."),
    "tapo": dict(label="TP-Link Tapo / Vigi", paths=[("/stream1", "/stream2")],
                 tip="Tapo-App → Kamera → Einstellungen → Erweiterte Einstellungen → Kamerakonto: eigenen Benutzer + Passwort anlegen. "
                     "Das ist NICHT dein TP-Link-Konto."),
    "hikvision": dict(label="Hikvision / HiLook / Annke / Ezviz", paths=[("/Streaming/Channels/101", "/Streaming/Channels/102"),
                                                                       ("/h264/ch1/main/av_stream", "/h264/ch1/sub/av_stream")],
                      tip="Benutzer meist „admin“. Bei Ezviz ist das Passwort der Verifizierungscode auf dem Aufkleber; RTSP ggf. in der App freischalten."),
    "dahua": dict(label="Dahua / Imou / Amcrest / Lorex", paths=[("/cam/realmonitor?channel=1&subtype=0", "/cam/realmonitor?channel=1&subtype=1")],
                  tip="Benutzer „admin“. Bei Imou ist das Passwort der Sicherheitscode (Safety Code) auf dem Aufkleber der Kamera."),
    "eufy": dict(label="eufy", paths=[("/live0", "/live0")],
                 tip="eufy-App → Kamera → Einstellungen → Speicher → NAS (RTSP) einschalten und dort Benutzer/Passwort setzen (nicht alle Modelle)."),
    "foscam": dict(label="Foscam", paths=[("/videoMain", "/videoSub")], port=554, tip="RTSP-Port steht in der Foscam-Weboberfläche (oft 554 oder 88)."),
    "axis": dict(label="Axis", paths=[("/axis-media/media.amp", "/axis-media/media.amp?resolution=640x360")], tip=""),
    "wyze": dict(label="Wyze (RTSP-Firmware)", paths=[("/live", "/live")], tip="Braucht die offizielle RTSP-Firmware von Wyze. Die RTSP-Adresse aus der App kannst du auch direkt eintragen."),
    "unifi": dict(label="UniFi Protect", paths=[], tip="In UniFi Protect: Kamera → Einstellungen → Erweitert → RTSP(S) aktivieren und die angezeigte Adresse als „Eigene RTSP-Adresse“ eintragen."),
    "generic": dict(label="Andere / ONVIF", paths=[("/onvif1", "/onvif2"), ("/live/ch00_0", "/live/ch00_1"), ("/11", "/12"), ("/live", "/live"),
                                                   ("/stream1", "/stream2"), ("/h264", "/h264"), ("/media/video1", "/media/video2"), ("/", "/")],
                    tip="Steht im Handbuch meist unter „RTSP“. Oder die komplette RTSP-Adresse unten eintragen."),
}
NO_RTSP = "Ring, Arlo, Blink, Google Nest, SimpliSafe und viele Billig-Cloud-Kameras haben keinen RTSP-Zugang – die gehen nur über die Hersteller-App."
VENDOR_HINT = [("reolink", "reolink"), ("tp-link", "tapo"), ("tplink", "tapo"), ("tapo", "tapo"), ("hikvision", "hikvision"), ("hangzhou hikvision", "hikvision"),
               ("ezviz", "hikvision"), ("dahua", "dahua"), ("zhejiang dahua", "dahua"), ("imou", "dahua"), ("amcrest", "dahua"), ("lorex", "dahua"),
               ("foscam", "foscam"), ("shenzhen foscam", "foscam"), ("axis", "axis"), ("anker", "eufy"), ("eufy", "eufy"), ("wyze", "wyze"),
               ("ubiquiti", "unifi")]


# ------------------------------------------------------------------ Speicher
def _load():
    try:
        return json.loads(DATA.read_text())
    except Exception:
        return {"kameras": []}


def _save(d):
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    os.chmod(tmp, 0o600)
    tmp.replace(DATA)


def _public(c):
    """Ohne Passwort – für Oberfläche und KI."""
    return {"id": c["id"], "name": c["name"], "host": c["host"], "port": c.get("port", 554), "marke": c.get("marke", "generic"),
            "marke_name": BRANDS.get(c.get("marke"), BRANDS["generic"])["label"], "benutzer": c.get("user", ""),
            "passwort_gesetzt": bool(c.get("password")), "eigene_url": bool(c.get("url")), "aufloesung": c.get("aufloesung", ""),
            "codec": c.get("codec", ""), "an": c.get("an", True), "zuletzt_ok": c.get("zuletzt_ok", "")}


def listing():
    return [_public(c) for c in _load()["kameras"]]


def get(ref):
    ref = str(ref or "").strip().lower()
    cams = _load()["kameras"]
    if not cams:
        raise RuntimeError("Noch keine Kamera eingerichtet – Karte „📷 Kameras“ in Lumen öffnen.")
    if not ref:
        return cams[0]
    for c in cams:
        if c["id"] == ref or c["name"].lower() == ref:
            return c
    for c in cams:
        if ref in c["name"].lower():
            return c
    raise RuntimeError(f"Keine Kamera „{ref}“. Vorhanden: " + ", ".join(c["name"] for c in cams))


# ------------------------------------------------------------------ Adressen
def _check_host(host):
    host = (host or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9.\-:\[\]]{1,253}", host):
        raise RuntimeError("Bitte nur die IP-Adresse oder den Namen der Kamera eintragen (z. B. 192.168.1.50).")
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host.strip("[]")))
    except Exception:
        raise RuntimeError(f"„{host}“ ist im Netz nicht erreichbar (Name unbekannt).")
    if not (ip.is_private or ip.is_loopback or ip.is_link_local):
        # Kameras gehören ins eigene Netz – Zugriff übers Internet nur, wenn ausdrücklich eine eigene RTSP-Adresse eingetragen wird.
        raise RuntimeError("Das ist keine Adresse im Heimnetz. Lumen verbindet nur Kameras im eigenen Netz "
                           "(oder trag eine eigene RTSP-Adresse deiner Kamera ein, z. B. über VPN).")
    return host


def _url(c, path=None, sub=False):
    if c.get("url") and not path:
        u = c["sub_url"] if sub and c.get("sub_url") else c["url"]
        if c.get("user") and "@" not in u.split("//", 1)[-1].split("/", 1)[0]:
            scheme, rest = u.split("://", 1)
            u = f"{scheme}://{urllib.parse.quote(c['user'], safe='')}:{urllib.parse.quote(c.get('password', ''), safe='')}@{rest}"
        return u
    p = path if path is not None else (c.get("sub_path") if sub and c.get("sub_path") else c.get("path", "/"))
    auth = ""
    if c.get("user"):
        auth = urllib.parse.quote(c["user"], safe="") + ":" + urllib.parse.quote(c.get("password", ""), safe="") + "@"
    h = c["host"]
    if ":" in h and not h.startswith("["):
        h = f"[{h}]"
    return f"rtsp://{auth}{h}:{int(c.get('port') or 554)}{p}"


def _mask(text, c):
    text = str(text)
    for s in (c.get("password"), urllib.parse.quote(c.get("password", "") or "", safe="")):
        if s and len(s) >= 2:
            text = text.replace(s, "***")
    return re.sub(r"(rtsps?://[^:/@\s]+:)[^@\s]+@", r"\1***@", text)


def _friendly(err, c):
    e = _mask(err, c)
    low = e.lower()
    if "401" in e or "unauthorized" in low:
        return "Benutzername oder Passwort falsch (die Kamera lehnt die Anmeldung ab)."
    if "404" in e or "not found" in low or "454" in e:
        return "Die Kamera kennt diese Stream-Adresse nicht."
    if "connection refused" in low:
        return "Die Kamera lehnt die Verbindung ab – ist RTSP in der Kamera-App eingeschaltet und der Port richtig?"
    if "timed out" in low or "timeout" in low or "no route" in low or "unreachable" in low:
        return "Kamera antwortet nicht (aus, anderes Netz oder falsche Adresse?)."
    if "invalid data" in low:
        return "Die Kamera liefert kein lesbares Bild auf dieser Adresse."
    return e.strip().splitlines()[-1][:200] if e.strip() else "Unbekannter Fehler."


def _need_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg fehlt – installieren mit: sudo apt install ffmpeg")


def _jpeg_size(b):
    i = 2
    try:
        while i < len(b) - 9:
            if b[i] != 0xFF:
                i += 1
                continue
            m = b[i + 1]
            if m in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", b[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    except Exception:
        pass
    return None


def grab(url, timeout=10, width=None):
    """Ein Einzelbild als JPEG-Bytes. Wirft RuntimeError mit ffmpeg-Fehler."""
    _need_ffmpeg()
    vf = ["-vf", f"scale='min({width},iw)':-2"] if width else []
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error"]
    if url.startswith("rtsp"):
        cmd += ["-rtsp_transport", "tcp", "-timeout", str(int(timeout * 1_000_000))]
    cmd += ["-i", url, "-an", "-frames:v", "1", *vf, "-q:v", "3", "-f", "image2", "-c:v", "mjpeg", "-"]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout + 6, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Connection timed out")
    if p.returncode != 0 or not p.stdout.startswith(b"\xff\xd8"):
        raise RuntimeError(p.stderr.decode(errors="replace") or "invalid data")
    return p.stdout


def _probe(url, timeout=8):
    if not shutil.which("ffprobe"):
        return ""
    try:
        p = subprocess.run(["ffprobe", "-v", "error", "-rtsp_transport", "tcp", "-timeout", str(timeout * 1_000_000), "-select_streams", "v:0",
                            "-show_entries", "stream=codec_name", "-of", "csv=p=0", url], capture_output=True, timeout=timeout + 4, stdin=subprocess.DEVNULL)
        return p.stdout.decode().strip().splitlines()[0] if p.returncode == 0 and p.stdout.strip() else ""
    except Exception:
        return ""


# ------------------------------------------------------------------ Einrichten
def detect(host, port=554, user="", password="", brand="auto", url="", sub_url=""):
    """Findet die passende Stream-Adresse. Probiert nur Pfade – nie Passwörter."""
    c = {"host": host, "port": int(port or 554), "user": (user or "").strip(), "password": password or "", "url": (url or "").strip(), "sub_url": (sub_url or "").strip()}
    if c["url"]:
        if not re.match(r"^rtsps?://", c["url"], re.I) and not re.match(r"^https?://", c["url"], re.I):
            raise RuntimeError("Eigene Adresse muss mit rtsp:// (oder http:// für MJPEG) beginnen.")
        h = urllib.parse.urlparse(c["url"]).hostname or ""
        c["host"] = h
        try:
            img = grab(_url(c), 12)
        except RuntimeError as e:
            raise RuntimeError(_friendly(e, c))
        return {**c, "path": "", "sub_path": "", "marke": brand if brand in BRANDS else "generic", "jpg": img, "codec": _probe(_url(c))}
    c["host"] = _check_host(host)
    try:
        socket.create_connection((c["host"], c["port"]), 3).close()
    except Exception:
        raise RuntimeError(f"Auf {c['host']}:{c['port']} antwortet nichts. RTSP in der Kamera-App eingeschaltet? Richtige IP? "
                           "(Tipp: „Im Netz suchen“.)")
    order = [brand] if brand in BRANDS and brand != "generic" else []
    order += [b for b in BRANDS if b not in order]
    tried, last = set(), ""
    for b in order:
        for main, sub in BRANDS[b]["paths"]:
            if main in tried:
                continue
            tried.add(main)
            try:
                img = grab(_url(c, main), 7)
            except RuntimeError as e:
                last = _friendly(e, c)
                if "Passwort falsch" in last:
                    raise RuntimeError(last + (f" Tipp {BRANDS[brand]['label']}: {BRANDS[brand]['tip']}" if brand in BRANDS and BRANDS[brand]["tip"] else ""))
                continue
            sub_ok = sub
            if sub != main:
                try:
                    grab(_url(c, sub), 6)
                except RuntimeError:
                    sub_ok = main
            return {**c, "path": main, "sub_path": sub_ok, "marke": b, "jpg": img, "codec": _probe(_url(c, main))}
        if len(tried) >= 14:
            break
    raise RuntimeError("Keine passende Stream-Adresse gefunden. " + (last + " " if last else "") +
                       "Trag die RTSP-Adresse aus dem Handbuch/der App als „Eigene RTSP-Adresse“ ein. " + NO_RTSP)


def add(name, host, port=554, user="", password="", brand="auto", url="", sub_url=""):
    r = detect(host, port, user, password, brand, url, sub_url)
    size = _jpeg_size(r["jpg"])
    with LOCK:
        d = _load()
        name = (name or "").strip()[:40] or f"Kamera {len(d['kameras']) + 1}"
        if any(x["name"].lower() == name.lower() for x in d["kameras"]):
            name += f" {len(d['kameras']) + 1}"
        c = {"id": uuid.uuid4().hex[:8], "name": name, "host": r["host"], "port": r["port"], "user": r["user"], "password": r["password"],
             "marke": r["marke"], "path": r["path"], "sub_path": r["sub_path"], "url": r["url"], "sub_url": r["sub_url"],
             "aufloesung": f"{size[0]}×{size[1]}" if size else "", "codec": r.get("codec", ""), "an": True,
             "zuletzt_ok": time.strftime("%d.%m. %H:%M")}
        d["kameras"].append(c)
        _save(d)
    LAST[c["id"]] = (r["jpg"], time.time())
    return {"text": f"📷 „{c['name']}“ verbunden ({BRANDS[c['marke']]['label']}, {c['aufloesung'] or 'Bild ok'}).", "kamera": _public(c),
            "bild": base64.b64encode(r["jpg"]).decode()}


def test(host, port=554, user="", password="", brand="auto", url="", sub_url="", cam_id=None):
    if cam_id and not password:
        old = get(cam_id)
        password = old.get("password", "")
        user = user or old.get("user", "")
    r = detect(host, port, user, password, brand, url, sub_url)
    size = _jpeg_size(r["jpg"])
    return {"text": f"✅ Verbindung klappt – {BRANDS[r['marke']]['label']}, {size[0]}×{size[1]}" if size else "✅ Verbindung klappt.",
            "marke": r["marke"], "bild": base64.b64encode(r["jpg"]).decode()}


def update(cid, **kw):
    with LOCK:
        d = _load()
        c = next((x for x in d["kameras"] if x["id"] == cid), None)
        if not c:
            raise RuntimeError("Kamera nicht gefunden.")
        if "name" in kw and kw["name"]:
            c["name"] = str(kw["name"]).strip()[:40]
        if "an" in kw:
            c["an"] = bool(kw["an"])
        conn = {k: kw[k] for k in ("host", "port", "user", "password", "marke", "url", "sub_url") if k in kw and kw[k] is not None}
        conn = {k: v for k, v in conn.items() if not (k == "password" and v == "")}   # leer = altes Passwort behalten
        if conn and any(str(conn[k]) != str(c.get(k if k != "marke" else "marke", "")) for k in conn):
            m = {**c, **conn}
            r = detect(m["host"], m.get("port", 554), m.get("user", ""), m.get("password", ""), m.get("marke", "auto"), m.get("url", ""), m.get("sub_url", ""))
            size = _jpeg_size(r["jpg"])
            c.update(host=r["host"], port=r["port"], user=r["user"], password=r["password"], marke=r["marke"], path=r["path"], sub_path=r["sub_path"],
                     url=r["url"], sub_url=r["sub_url"], aufloesung=f"{size[0]}×{size[1]}" if size else "", codec=r.get("codec", ""))
        _save(d)
    LIVE_STOP(cid)
    return {"text": "Gespeichert.", "kamera": _public(c)}


def delete(cid):
    with LOCK:
        d = _load()
        n = len(d["kameras"])
        d["kameras"] = [x for x in d["kameras"] if x["id"] != cid]
        if len(d["kameras"]) == n:
            raise RuntimeError("Kamera nicht gefunden.")
        _save(d)
    LIVE_STOP(cid)
    LAST.pop(cid, None)
    return "Kamera entfernt (Zugangsdaten gelöscht)."


# ------------------------------------------------------------------ Schnappschuss & Live
LAST = {}   # id → (jpeg, zeit) – nur im Speicher, nie auf der Platte


def snapshot(ref=None, width=None):
    c = get(ref)
    if not c.get("an", True):
        raise RuntimeError(f"„{c['name']}“ ist ausgeschaltet.")
    lv = LIVES.get(c["id"])
    if lv and lv.frame and time.time() - lv.ts < 2 and not width:
        img = lv.frame
    else:
        try:
            img = grab(_url(c), 12, width)
        except RuntimeError as e:
            raise RuntimeError(f"„{c['name']}“: " + _friendly(e, c))
    LAST[c["id"]] = (img, time.time())
    with LOCK:
        d = _load()
        for x in d["kameras"]:
            if x["id"] == c["id"]:
                x["zuletzt_ok"] = time.strftime("%d.%m. %H:%M")
        _save(d)
    return c, img


def snapshot_all(width=None):
    cams = [c for c in _load()["kameras"] if c.get("an", True)]
    out = []
    with ThreadPoolExecutor(max(1, min(6, len(cams)))) as ex:
        for c, r in zip(cams, ex.map(lambda c: _try_snap(c["id"], width), cams)):
            out.append((c, r))
    return out


def _try_snap(cid, width):
    try:
        return snapshot(cid, width)[1]
    except Exception as e:
        return e


class Live:
    """Ein ffmpeg pro Kamera liefert ~5 Bilder/s (Unterstream) an beliebig viele Zuschauer."""

    def __init__(self, c):
        self.c, self.frame, self.ts, self.err = c, None, 0.0, ""
        self.seen = time.time()
        self.cond = threading.Condition()
        self.proc = None
        self.alive = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        url = _url(self.c, sub=True)
        cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error"]
        if url.startswith("rtsp"):
            cmd += ["-rtsp_transport", "tcp", "-timeout", "10000000"]
        else:
            cmd += ["-use_wallclock_as_timestamps", "1"]   # MJPEG über HTTP hat keine Zeitstempel
        cmd += ["-i", url, "-an", "-vf", "scale='min(1280,iw)':-2", "-q:v", "6", "-c:v", "mjpeg", "-f", "image2pipe", "-"]
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        except Exception as e:
            self.err, self.alive = str(e), False
            return
        buf = b""
        while self.alive:
            chunk = self.proc.stdout.read1(65536)
            if not chunk:
                break
            buf += chunk
            while True:
                a = buf.find(b"\xff\xd8")
                b = buf.find(b"\xff\xd9", a + 2) if a >= 0 else -1
                if a < 0 or b < 0:
                    if len(buf) > 8_000_000:
                        buf = b""
                    break
                now = time.time()
                if now - self.ts >= 0.18:   # ~5 Bilder/s reichen
                    with self.cond:
                        self.frame, self.ts = buf[a:b + 2], now
                        self.cond.notify_all()
                buf = buf[b + 2:]
            if time.time() - self.seen > 25:   # niemand schaut mehr zu
                break
        self.alive = False
        try:
            self.proc.kill()
        except Exception:
            pass
        if not self.frame:
            try:
                self.err = _friendly(self.proc.stderr.read().decode(errors="replace"), self.c)
            except Exception:
                self.err = "Live-Bild kam nicht an."
        with self.cond:
            self.cond.notify_all()
        if LIVES.get(self.c["id"]) is self:
            LIVES.pop(self.c["id"], None)

    def stop(self):
        self.alive = False
        try:
            self.proc and self.proc.kill()
        except Exception:
            pass

    def wait_frame(self, after, timeout=6):
        self.seen = time.time()
        with self.cond:
            self.cond.wait_for(lambda: (self.frame and self.ts > after) or not self.alive, timeout)
        return self.frame if self.frame and self.ts > after else None


LIVES = {}
LIVES_LOCK = threading.Lock()


def live(cid):
    c = get(cid)
    _need_ffmpeg()
    with LIVES_LOCK:
        lv = LIVES.get(c["id"])
        if not lv or not lv.alive:
            if len(LIVES) >= 6:
                raise RuntimeError("Zu viele Live-Bilder gleichzeitig (max. 6).")
            lv = LIVES[c["id"]] = Live(c)
        lv.seen = time.time()
    return lv


def LIVE_STOP(cid):
    lv = LIVES.pop(cid, None)
    if lv:
        lv.stop()


TICKETS = {}   # Einmal-Schlüssel fürs <img>-Live-Bild (Browser kann keinen Header mitschicken)


def ticket(cid):
    c = get(cid)
    now = time.time()
    for k in [k for k, v in TICKETS.items() if v[1] < now]:
        TICKETS.pop(k, None)
    k = secrets.token_urlsafe(18)
    TICKETS[k] = (c["id"], now + 60)
    return k


def use_ticket(k):
    v = TICKETS.pop(k or "", None)
    if not v or v[1] < time.time():
        return None
    return v[0]


# ------------------------------------------------------------------ Im Netz suchen
PROBE = ('<?xml version="1.0" encoding="UTF-8"?><e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" '
         'xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery" '
         'xmlns:dn="http://www.onvif.org/ver10/network/wsdl"><e:Header><w:MessageID>uuid:{id}</w:MessageID>'
         '<w:To e:mustUnderstand="true">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>'
         '<w:Action e:mustUnderstand="true">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action></e:Header>'
         '<e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body></e:Envelope>')


def _onvif(wait=2.5):
    found = {}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        s.settimeout(0.4)
        s.sendto(PROBE.replace("{id}", str(uuid.uuid4())).encode(), ("239.255.255.250", 3702))
        end = time.time() + wait
        while time.time() < end:
            try:
                data, (ip, _) = s.recvfrom(65535)
            except socket.timeout:
                continue
            txt = data.decode(errors="replace")
            scopes = " ".join(re.findall(r"onvif://www\.onvif\.org/(?:name|hardware|mfr|manufacturer)/([^\s<]+)", txt))
            found[ip] = urllib.parse.unquote(scopes.replace("_", " "))[:120]
        s.close()
    except Exception:
        pass
    return found


def _port_open(ip, port, t=0.5):
    try:
        socket.create_connection((ip, port), t).close()
        return True
    except Exception:
        return False


def discover():
    """Sucht Kameras im eigenen Heimnetz (ONVIF-Rundruf + RTSP-Port 554/8554). Kein Anmelden, kein Passwort-Raten."""
    import secplus
    dev, me, net, gw = secplus._local_net()
    on = _onvif()
    hosts = [str(h) for h in net.hosts() if str(h) != me]
    with ThreadPoolExecutor(96) as ex:
        rtsp = dict(zip(hosts, ex.map(lambda ip: 554 if _port_open(ip, 554) else (8554 if _port_open(ip, 8554, 0.3) else 0), hosts)))
    neigh = {}
    try:
        out = subprocess.run(["ip", "-j", "neigh", "show", "dev", dev], capture_output=True, text=True, timeout=5).stdout
        neigh = {n.get("dst"): (n.get("lladdr") or "").lower() for n in json.loads(out or "[]")}
    except Exception:
        pass
    known = {c["host"] for c in _load()["kameras"]}
    res = []
    for ip in sorted(set(on) | {i for i, p in rtsp.items() if p}, key=lambda x: tuple(int(p) for p in x.split("."))):
        if ip == gw and ip not in on:
            continue
        mac = neigh.get(ip, "")
        vendor = secplus._vendor(mac) if mac else ""
        try:
            name = socket.gethostbyaddr(ip)[0]
        except Exception:
            name = ""
        hint = f"{on.get(ip, '')} {vendor} {name}".lower()
        brand = next((b for k, b in VENDOR_HINT if k in hint), "")
        res.append({"ip": ip, "port": rtsp.get(ip) or 554, "onvif": ip in on, "info": on.get(ip, ""), "hersteller": vendor, "hostname": name,
                    "marke": brand, "marke_name": BRANDS[brand]["label"] if brand else "", "schon_da": ip in known})
    return {"netz": str(net), "kameras": res,
            "text": f"{len(res)} mögliche Kamera(s) in {net} gefunden." if res else
                    f"In {net} keine Kamera mit RTSP/ONVIF gefunden. RTSP in der Kamera-App einschalten – oder die IP aus der App/dem Router eintragen. " + NO_RTSP}


def brands():
    return {k: {"label": v["label"], "tip": v["tip"]} for k, v in BRANDS.items()}


def grab_scale(jpg, width):
    """Verkleinert ein JPEG (für KI und Vorschau). Ohne Pillow: Original."""
    try:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(jpg))
        if im.width <= width:
            return jpg
        im.thumbnail((width, width * 4))
        out = io.BytesIO()
        im.convert("RGB").save(out, "JPEG", quality=75)
        return out.getvalue()
    except Exception:
        return jpg
