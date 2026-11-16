"""Lumen – Funk-Empfang zum Anhören und Ansehen (NUR EMPFANG):

• UKW-Radio über HackRF (eigener Demodulator radio_fm.py) oder RTL-SDR (rtl_fm)
• Flugzeuge über dir (ADS-B, 1090 MHz) über dump1090 / dump1090-fa / readsb

Der Empfänger kann immer nur eine Sache gleichzeitig: Radio, Flugzeuge oder Spektrum-Scan.
"""
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import secplus

HERE = Path(__file__).resolve().parent
DATA = Path.home() / ".lumen" / "funk.json"
TOOLS = Path.home() / ".lumen" / "tools"
LOCK = threading.RLock()
RADIO = {"proc": None, "mhz": None, "name": "", "seit": 0, "fehler": ""}
ADSB = {"proc": None, "dir": None, "seit": 0, "fehler": "", "prog": ""}


def _load():
    try:
        d = json.loads(DATA.read_text("utf-8"))
    except Exception:
        d = {}
    d.setdefault("sender", [])          # [{"mhz": 100.3, "name": "…"}]
    d.setdefault("home", None)          # {"lat":…, "lon":…, "ort":…}
    d.setdefault("volume", 1.0)
    return d


def _save(d):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(DATA)


def _kill(st):
    p = st.get("proc")
    if p and p.poll() is None:
        try:
            os.killpg(p.pid, signal.SIGTERM)
        except Exception:
            try:
                p.terminate()
            except Exception:
                pass
        try:
            p.wait(timeout=3)
        except Exception:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except Exception:
                pass
    st["proc"] = None


def _device():
    usb = {x["id"] for x in secplus._safe(secplus.usb_devices, [])}
    if shutil.which("hackrf_transfer") and (not usb or any(i.startswith("1d50:6089") or i.startswith("1d50:604b") or i.startswith("1d50:cc15") for i in usb)):
        out, rc = secplus._run(["hackrf_info"], 8)
        if "Serial number" in out:
            return "hackrf"
    if any(i in ("0bda:2838", "0bda:2832") for i in usb):
        return "rtlsdr"
    return None


def free_device():
    """Vor Spektrum-Scans aufrufen: Radio/Flugzeug-Empfang anhalten."""
    stopped = []
    with LOCK:
        if radio_status()["läuft"]:
            radio_stop()
            stopped.append("Radio")
        if adsb_running():
            adsb_stop()
            stopped.append("Flugzeug-Empfang")
    return stopped


# ================================================================ UKW-Radio
def radio_status():
    p = RADIO["proc"]
    running = bool(p and p.poll() is None)
    if p and not running and not RADIO["fehler"] and time.time() - RADIO["seit"] < 15:
        RADIO["fehler"] = "Der Empfang ist sofort abgebrochen – ist der HackRF frei (kein GQRX/SDR++ offen) und ein Lautsprecher da?"
    d = _load()
    return {"läuft": running, "mhz": RADIO["mhz"] if running else None, "name": RADIO["name"] if running else "", "fehler": RADIO["fehler"],
            "sender": sorted(d["sender"], key=lambda s: s["mhz"]), "lautstärke": d["volume"]}


def radio_stop():
    with LOCK:
        _kill(RADIO)
        RADIO.update(mhz=None, name="")
    return "📻 Radio aus."


def radio_play(mhz=None, name=None):
    d = _load()
    if mhz is None and name:
        hit = [s for s in d["sender"] if name.lower() in s["name"].lower()]
        if not hit:
            raise RuntimeError(f"Sender „{name}“ ist nicht gespeichert. Gespeichert: " + (", ".join(f"{s['name']} ({s['mhz']})" for s in d["sender"]) or "keine – erst Sendersuche machen."))
        mhz, name = hit[0]["mhz"], hit[0]["name"]
    try:
        mhz = round(float(str(mhz).replace(",", ".")), 2)
    except (TypeError, ValueError):
        raise RuntimeError("Welche Frequenz? z. B. 100.3")
    if not 87.5 <= mhz <= 108.0:
        raise RuntimeError("UKW-Radio liegt zwischen 87,5 und 108 MHz.")
    dev = _device()
    if not dev:
        raise RuntimeError("Kein Empfänger bereit. HackRF anstecken und „sudo apt install hackrf“ (Details: Sicherheits-Zentrale → Funk).")
    with LOCK:
        _kill(RADIO)
        if adsb_running():
            adsb_stop()
        if dev == "hackrf":
            cmd = [sys.executable, str(HERE / "radio_fm.py"), "--freq", str(mhz), "--volume", str(d["volume"])]
        else:
            player = next((c for c in (["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-r", "48000", "-c", "1", "-"],
                                       ["pw-cat", "-p", "--format", "s16", "--rate", "48000", "--channels", "1", "-"]) if shutil.which(c[0])), None)
            if not shutil.which("rtl_fm") or not player:
                raise RuntimeError("Für den RTL-SDR fehlt rtl_fm oder ein Audio-Player: sudo apt install rtl-sdr alsa-utils")
            cmd = ["sh", "-c", f"rtl_fm -M wbfm -f {mhz}M -r 48000 - 2>/dev/null | " + " ".join(player)]
        RADIO["fehler"] = ""
        RADIO["proc"] = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        nm = name or next((s["name"] for s in d["sender"] if abs(s["mhz"] - mhz) < 0.06), "")
        RADIO.update(mhz=mhz, name=nm, seit=time.time())
    return f"📻 Spiele {nm + ' · ' if nm else ''}{mhz:g} MHz."


def radio_volume(v):
    v = max(0.1, min(3.0, float(v)))
    with LOCK:
        d = _load()
        d["volume"] = v
        _save(d)
    if radio_status()["läuft"]:
        radio_play(RADIO["mhz"], RADIO["name"])
    return v


def radio_scan():
    """Sendersuche: Spektrum 87,5–108 MHz, starke Träger = Sender (auf 0,1 MHz gerundet)."""
    free_device()
    r = secplus.sdr_sweep(87, 108)
    found, d = [], _load()
    names = {round(s["mhz"], 1): s["name"] for s in d["sender"]}
    pts = {p[0]: p[1] for p in r["punkte"]}
    fs = sorted(pts)
    for s in secplus._peaks(pts, top=30)[0]:
        i = fs.index(s["mhz"])
        near = fs[max(0, i - 1):i + 2]
        w = [10 ** (pts[f] / 10) for f in near]                    # Schwerpunkt aus Nachbar-Bins → genauere Frequenz
        f = round(sum(f * x for f, x in zip(near, w)) / sum(w) * 10 + 1e-6) / 10
        if 87.5 <= f <= 108 and s["über_rauschen_db"] >= 12 and all(abs(f - x["mhz"]) >= 0.2 for x in found):
            found.append({"mhz": f, "stärke_db": s["über_rauschen_db"], "name": names.get(f, "")})
    found.sort(key=lambda x: x["mhz"])
    return {"gefunden": found, "text": f"{len(found)} Sender gefunden." if found else "Keine Sender gefunden – Antenne angeschlossen? Näher ans Fenster."}


def station_save(mhz, name):
    mhz = round(float(mhz), 1)
    name = str(name or "").strip()[:40]
    with LOCK:
        d = _load()
        d["sender"] = [s for s in d["sender"] if abs(s["mhz"] - mhz) > 0.06]
        if name:
            d["sender"].append({"mhz": mhz, "name": name})
        _save(d)
    return "Gespeichert." if name else "Entfernt."


# ================================================================ Flugzeuge (ADS-B)
def _adsb_binary(dev):
    """(Pfad, Art) – Art bestimmt die Parameter."""
    own = TOOLS / "dump1090" / "dump1090"
    cands = [(str(own), "fa")] if own.exists() else []
    cands += [(shutil.which(n), k) for n, k in (("dump1090-fa", "fa"), ("readsb", "readsb"), ("dump1090", "fa"), ("dump1090-mutability", "mut")) if shutil.which(n)]
    for path, kind in cands:
        if dev == "hackrf":
            if kind == "fa":
                out, _ = secplus._run([path, "--help"], 8)
                if "hackrf" in out.lower():
                    return path, kind
        elif kind in ("fa", "readsb", "mut"):
            return path, kind
    return None, None


def adsb_running():
    p = ADSB["proc"]
    return bool(p and p.poll() is None)


def adsb_stop():
    with LOCK:
        _kill(ADSB)
        if ADSB["dir"]:
            shutil.rmtree(ADSB["dir"], ignore_errors=True)
            ADSB["dir"] = None
    return "✈️ Flugzeug-Empfang aus."


def adsb_start():
    dev = _device()
    if not dev:
        raise RuntimeError("Kein Empfänger bereit. HackRF oder RTL-SDR anstecken (Details: Sicherheits-Zentrale → Funk).")
    path, kind = _adsb_binary(dev)
    if not path:
        raise RuntimeError("Das Empfangsprogramm für Flugzeuge fehlt" + (" (für den HackRF braucht es dump1090 mit HackRF-Unterstützung)" if dev == "hackrf" else "")
                           + ". Einmal im Lumen-Ordner ausführen: bash setup-adsb.sh")
    with LOCK:
        if adsb_running():
            return "Läuft schon."
        _kill(RADIO)
        RADIO.update(mhz=None, name="")
        d = tempfile.mkdtemp(prefix="lumen-adsb-")
        cmd = [path, "--quiet", "--write-json", d]
        if kind in ("fa", "readsb"):
            cmd += ["--device-type", dev, "--write-json-every", "1"]
        if kind == "fa" and dev == "hackrf":
            cmd += ["--lna-gain", "32", "--vga-gain", "40"]
        home = _load()["home"]
        if home and kind in ("fa", "readsb"):
            cmd += ["--lat", str(home["lat"]), "--lon", str(home["lon"])]
        ADSB.update(dir=d, seit=time.time(), fehler="", prog=Path(path).name)
        ADSB["proc"] = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True)
    time.sleep(1.5)
    if not adsb_running():
        err = ""
        try:
            err = ADSB["proc"].stderr.read().decode("utf-8", "replace")[-300:] if ADSB["proc"] else ""
        except Exception:
            pass
        ADSB["fehler"] = "Start fehlgeschlagen: " + (err.strip() or "Empfänger belegt?")
        raise RuntimeError(ADSB["fehler"])
    return "✈️ Empfange Flugzeuge auf 1090 MHz – die ersten erscheinen nach ein paar Sekunden."


def _dist_bearing(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    dist = 2 * R * math.asin(math.sqrt(a))
    brg = (math.degrees(math.atan2(math.sin(dl) * math.cos(p2), math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl))) + 360) % 360
    return dist, brg


COMPASS = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]


def aircraft():
    """Aktuelle Flugzeuge. Höhe in m, Tempo in km/h, Entfernung/Richtung vom eigenen Standort (falls gesetzt)."""
    home = _load()["home"]
    out = {"läuft": adsb_running(), "fehler": ADSB["fehler"], "home": home, "flugzeuge": [], "programm": ADSB["prog"],
           "seit_s": int(time.time() - ADSB["seit"]) if adsb_running() else 0}
    if not out["läuft"] or not ADSB["dir"]:
        return out
    try:
        js = json.loads((Path(ADSB["dir"]) / "aircraft.json").read_text("utf-8"))
    except Exception:
        return out
    for a in js.get("aircraft", []):
        if (a.get("seen") or 0) > 60:
            continue
        alt = a.get("alt_baro", a.get("altitude", a.get("alt_geom")))
        gs = a.get("gs", a.get("speed"))
        p = {"hex": str(a.get("hex", ""))[:8], "flug": (a.get("flight") or "").strip(), "squawk": a.get("squawk"),
             "höhe_m": round(alt * 0.3048 / 10) * 10 if isinstance(alt, (int, float)) else (0 if alt == "ground" else None),
             "tempo_kmh": round(gs * 1.852) if isinstance(gs, (int, float)) else None,
             "kurs": round(a["track"]) if isinstance(a.get("track"), (int, float)) else None,
             "lat": a.get("lat"), "lon": a.get("lon"), "gesehen_s": round(a.get("seen") or 0), "signal": a.get("rssi")}
        if home and isinstance(p["lat"], (int, float)) and isinstance(p["lon"], (int, float)):
            dist, brg = _dist_bearing(home["lat"], home["lon"], p["lat"], p["lon"])
            p["entfernung_km"], p["richtung"], p["peilung"] = round(dist, 1), COMPASS[int((brg + 22.5) // 45) % 8], round(brg)
        if p["squawk"] in ("7500", "7600", "7700"):
            p["notfall"] = {"7500": "Entführung gemeldet", "7600": "Funkausfall", "7700": "Luftnotfall"}[p["squawk"]]
        out["flugzeuge"].append(p)
    out["flugzeuge"].sort(key=lambda p: (p.get("entfernung_km") is None, p.get("entfernung_km") or 0, p["hex"]))
    out["anzahl"] = len(out["flugzeuge"])
    out["mit_position"] = sum(1 for p in out["flugzeuge"] if p["lat"] is not None)
    return out


def set_home(lat, lon, ort=""):
    lat, lon = float(lat), float(lon)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise RuntimeError("Ungültige Koordinaten.")
    with LOCK:
        d = _load()
        d["home"] = {"lat": round(lat, 4), "lon": round(lon, 4), "ort": str(ort)[:60]}
        _save(d)
    return d["home"]


def planes_summary(wait=8):
    """Für den Chat: startet den Empfang bei Bedarf, wartet kurz und fasst zusammen."""
    started = False
    if not adsb_running():
        adsb_start()
        started = True
        time.sleep(wait)
    r = aircraft()
    r["hinweis"] = ("Empfang gerade erst gestartet – nach 1–2 Minuten sind es meist mehr. " if started else "") + \
                   "Positionen kommen direkt von den Flugzeugen (ADS-B, öffentlich ausgestrahlt)."
    r["flugzeuge"] = r["flugzeuge"][:25]
    return r


def stop_all():
    radio_stop()
    adsb_stop()
