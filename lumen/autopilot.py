"""Lumen – Autopilot: Automationen (geplante KI-Aufgaben) und Heartbeat (regelmäßiger stiller Check mit eigener Checkliste).

Die eigentliche Ausführung (KI-Job, Zustellung) liefert lumen.py über run_fn / deliver_fn.
"""
import json
import re
import secrets
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path.home() / ".lumen" / "autopilot.json"
LOCK = threading.RLock()
WD = ["mo", "di", "mi", "do", "fr", "sa", "so"]
WD_NAMES = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
KINDS = ("einmal", "täglich", "wochentags", "wöchentlich", "monatlich", "stündlich", "alle_x_minuten")
DEFAULT_CHECKLIST = """- Ist eine wichtige ungelesene E-Mail da (nicht Newsletter/Werbung)? Dann kurz Absender + Betreff.
- Beginnt in der nächsten Stunde ein Termin, auf den ich mich vorbereiten sollte?
- Ist etwas mit meinen Servern nicht in Ordnung?
"""
RUNNING = set()


def _load():
    try:
        d = json.loads(DATA.read_text("utf-8"))
    except Exception:
        d = {}
    d.setdefault("automations", [])
    d.setdefault("heartbeat", {})
    hb = d["heartbeat"]
    hb.setdefault("an", False)
    hb.setdefault("minuten", 30)
    hb.setdefault("checkliste", DEFAULT_CHECKLIST)
    hb.setdefault("ruhe_von", "22:00")
    hb.setdefault("ruhe_bis", "07:00")
    hb.setdefault("letzter", 0)
    hb.setdefault("meldungen", [])      # letzte Meldungen (gegen Wiederholung)
    hb.setdefault("protokoll", [])      # letzte Durchläufe
    return d


def _save(d):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(DATA)


def _hm(s):
    m = re.fullmatch(r"\s*(\d{1,2})(?::|\.|h)?(\d{2})?\s*(uhr)?\s*", str(s or ""), re.I)
    if not m:
        raise RuntimeError(f"Uhrzeit „{s}“ verstehe ich nicht (z. B. 07:30).")
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if h > 23 or mi > 59:
        raise RuntimeError("Ungültige Uhrzeit.")
    return h, mi


def next_run(a, after=None):
    """Nächster Zeitpunkt (Unix-Zeit) für eine Automation – oder None (einmalig und vorbei)."""
    now = datetime.fromtimestamp(after or time.time())
    k = a["art"]
    if k == "alle_x_minuten":
        base = datetime.fromtimestamp(a.get("zuletzt") or 0) if a.get("zuletzt") else now
        n = max(15, int(a.get("minuten") or 60))
        t = base + timedelta(minutes=n) if a.get("zuletzt") else now + timedelta(minutes=1)
        return max(t, now + timedelta(seconds=30)).timestamp()
    if k == "stündlich":
        mi = int(a.get("minute") or 0)
        t = now.replace(minute=mi, second=0, microsecond=0)
        if t <= now:
            t += timedelta(hours=1)
        return t.timestamp()
    h, mi = _hm(a.get("uhrzeit") or "08:00")
    if k == "einmal":
        d = datetime.strptime(a["datum"], "%Y-%m-%d").replace(hour=h, minute=mi)
        return d.timestamp() if d > now - timedelta(minutes=1) and not a.get("zuletzt") else None
    t = now.replace(hour=h, minute=mi, second=0, microsecond=0)
    for _ in range(400):
        if t > now:
            if k == "täglich":
                return t.timestamp()
            if k == "wochentags" and t.weekday() < 5:
                return t.timestamp()
            if k == "wöchentlich" and WD[t.weekday()] in (a.get("tage") or ["mo"]):
                return t.timestamp()
            if k == "monatlich" and t.day == int(a.get("tag_im_monat") or 1):
                return t.timestamp()
        t += timedelta(days=1)
    return None


def describe(a):
    k = a["art"]
    if k == "alle_x_minuten":
        return f"alle {a.get('minuten')} Minuten"
    if k == "stündlich":
        return f"stündlich zur Minute {int(a.get('minute') or 0):02d}"
    if k == "einmal":
        return f"einmal am {datetime.strptime(a['datum'], '%Y-%m-%d'):%d.%m.%Y} um {a['uhrzeit']}"
    if k == "wöchentlich":
        return "jeden " + ", ".join(WD_NAMES[WD.index(x)] for x in a.get("tage") or ["mo"]) + f" um {a['uhrzeit']}"
    if k == "monatlich":
        return f"jeden {a.get('tag_im_monat', 1)}. des Monats um {a['uhrzeit']}"
    return {"täglich": "täglich", "wochentags": "Mo–Fr"}[k] + f" um {a['uhrzeit']}"


def _clean(spec):
    k = str(spec.get("art") or spec.get("when") or "täglich").lower().replace("woechentlich", "wöchentlich").replace("taeglich", "täglich")
    k = {"daily": "täglich", "weekdays": "wochentags", "weekly": "wöchentlich", "hourly": "stündlich", "once": "einmal", "monthly": "monatlich",
         "every": "alle_x_minuten", "intervall": "alle_x_minuten"}.get(k, k)
    if k not in KINDS:
        raise RuntimeError("Zeitplan: " + ", ".join(KINDS))
    out = {"art": k}
    if k in ("einmal", "täglich", "wochentags", "wöchentlich", "monatlich"):
        h, mi = _hm(spec.get("uhrzeit") or spec.get("time") or "08:00")
        out["uhrzeit"] = f"{h:02d}:{mi:02d}"
    if k == "einmal":
        dt = str(spec.get("datum") or spec.get("date") or "").strip()
        if re.fullmatch(r"\d{1,2}\.\d{1,2}\.(\d{4})?", dt):
            p = dt.split(".")
            dt = f"{p[2] or datetime.now().year}-{int(p[1]):02d}-{int(p[0]):02d}"
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dt):
            dt = (datetime.now() + timedelta(days=0 if datetime.now().strftime("%H:%M") < out["uhrzeit"] else 1)).strftime("%Y-%m-%d")
        out["datum"] = dt
    if k == "wöchentlich":
        days = spec.get("tage") or spec.get("weekdays") or [spec.get("weekday") or "mo"]
        if isinstance(days, str):
            days = re.split(r"[,\s]+", days)
        days = [str(x).strip().lower()[:2] for x in days if str(x).strip()]
        days = [{"we": "mi", "th": "do", "su": "so", "tu": "di"}.get(x, x) for x in days]
        if not days or any(x not in WD for x in days):
            raise RuntimeError("Wochentage als mo, di, mi, do, fr, sa, so.")
        out["tage"] = sorted(set(days), key=WD.index)
    if k == "monatlich":
        out["tag_im_monat"] = max(1, min(28, int(spec.get("tag_im_monat") or spec.get("day") or 1)))
    if k == "stündlich":
        out["minute"] = max(0, min(59, int(spec.get("minute") or 0)))
    if k == "alle_x_minuten":
        out["minuten"] = max(15, min(1440, int(spec.get("minuten") or spec.get("every_min") or 60)))
    return out


def add(name, prompt, spec, deliver="telegram", origin="pc"):
    prompt = str(prompt or "").strip()
    if len(prompt) < 8:
        raise RuntimeError("Was soll Lumen jeweils tun? (Auftrag fehlt)")
    if deliver not in ("telegram", "pc", "beide", "still"):
        deliver = "telegram"
    a = {"id": secrets.token_hex(4), "name": str(name or prompt[:40]).strip()[:60], "auftrag": prompt[:2000], **_clean(spec),
         "zustellen": deliver, "an": True, "erstellt": time.time(), "zuletzt": 0, "ergebnis": "", "fehler": "", "herkunft": origin}
    a["nächste"] = next_run(a)
    if a["nächste"] is None:
        raise RuntimeError("Dieser Zeitpunkt liegt in der Vergangenheit.")
    with LOCK:
        d = _load()
        if len(d["automations"]) >= 50:
            raise RuntimeError("Maximal 50 Automationen.")
        d["automations"].append(a)
        _save(d)
    return {"id": a["id"], "text": f"⏱ Automation „{a['name']}“: {describe(a)} – zuerst {datetime.fromtimestamp(a['nächste']):%a %d.%m. %H:%M}"
                                   .replace("Mon", "Mo").replace("Tue", "Di").replace("Wed", "Mi").replace("Thu", "Do").replace("Fri", "Fr")
                                   .replace("Sat", "Sa").replace("Sun", "So") + "."}


def update(aid, **kw):
    with LOCK:
        d = _load()
        a = next((x for x in d["automations"] if x["id"] == aid), None)
        if not a:
            raise RuntimeError("Automation nicht gefunden.")
        if "an" in kw:
            a["an"] = bool(kw["an"])
        if kw.get("name"):
            a["name"] = str(kw["name"])[:60]
        if kw.get("auftrag"):
            a["auftrag"] = str(kw["auftrag"])[:2000]
        if kw.get("zustellen") in ("telegram", "pc", "beide", "still"):
            a["zustellen"] = kw["zustellen"]
        if kw.get("zeitplan"):
            for k in ("uhrzeit", "datum", "tage", "minute", "minuten", "tag_im_monat"):
                a.pop(k, None)
            a.update(_clean(kw["zeitplan"]))
        a["nächste"] = next_run(a)
        _save(d)
        return a


def delete(aid):
    with LOCK:
        d = _load()
        n = len(d["automations"])
        d["automations"] = [a for a in d["automations"] if a["id"] != aid and aid != "alle"]
        _save(d)
    return "Gelöscht." if len(d["automations"]) < n else "Nicht gefunden."


def listing():
    d = _load()
    out = []
    for a in d["automations"]:
        out.append({**a, "wann": describe(a), "läuft": a["id"] in RUNNING,
                    "nächste_text": datetime.fromtimestamp(a["nächste"]).strftime("%d.%m. %H:%M") if a.get("nächste") and a["an"] else "—"})
    return out


def due(now=None):
    now = now or time.time()
    d = _load()
    return [a for a in d["automations"] if a["an"] and a.get("nächste") and a["nächste"] <= now and a["id"] not in RUNNING]


def run(a, run_fn, deliver_fn):
    """Eine Automation ausführen (im eigenen Thread)."""
    if a["id"] in RUNNING:
        return
    RUNNING.add(a["id"])
    with LOCK:  # sofort weiterschalten, damit sie nicht doppelt startet
        d = _load()
        x = next((y for y in d["automations"] if y["id"] == a["id"]), None)
        if x:
            x["zuletzt"] = time.time()
            x["nächste"] = next_run(x)
            if x["nächste"] is None:
                x["an"] = False
            _save(d)
    try:
        text, err = run_fn(a), ""
    except Exception as e:
        text, err = "", str(e)[:300]
    finally:
        RUNNING.discard(a["id"])
    with LOCK:
        d = _load()
        x = next((y for y in d["automations"] if y["id"] == a["id"]), None)
        if x:
            x["ergebnis"], x["fehler"] = (text or "")[:4000], err
            _save(d)
    try:
        deliver_fn(a, text, err)
    except Exception:
        pass
    return text


def merge_from_desktop(lst):
    """Lumen-Server: Automationen vom PC übernehmen. Eigene (per Telegram angelegte) bleiben, Laufzeit-Daten bleiben erhalten."""
    if not isinstance(lst, list):
        return
    with LOCK:
        d = _load()
        old = {a["id"]: a for a in d["automations"]}
        keep = [a for a in d["automations"] if a.get("herkunft") == "server"]
        new = []
        for a in lst:
            if not isinstance(a, dict) or not a.get("id") or a.get("herkunft") == "server":
                continue
            o = old.get(a["id"], {})
            b = {**a, "zuletzt": max(a.get("zuletzt") or 0, o.get("zuletzt") or 0), "ergebnis": o.get("ergebnis", a.get("ergebnis", ""))}
            b["nächste"] = next_run(b) if b.get("an") else None
            new.append(b)
        d["automations"] = keep + new
        _save(d)


def desktop_changed(key, value):
    """True, wenn sich dieser Stand vom PC seit dem letzten Abgleich geändert hat (sonst gelten Änderungen am Server, z. B. per Telegram)."""
    import hashlib
    h = hashlib.sha1(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    with LOCK:
        d = _load()
        seen = d.setdefault("sync_seen", {})
        if seen.get(key) == h:
            return False
        seen[key] = h
        _save(d)
    return True


def sync_payload():
    return [a for a in _load()["automations"] if a.get("herkunft") != "server"]


# ---------------------------------------------------------------- Heartbeat
def hb_get():
    return _load()["heartbeat"]


def hb_set(**kw):
    with LOCK:
        d = _load()
        hb = d["heartbeat"]
        if "an" in kw:
            hb["an"] = bool(kw["an"])
        if kw.get("minuten"):
            hb["minuten"] = max(10, min(240, int(kw["minuten"])))
        if "checkliste" in kw and kw["checkliste"] is not None:
            hb["checkliste"] = str(kw["checkliste"])[:3000]
        for k in ("ruhe_von", "ruhe_bis"):
            if kw.get(k):
                h, mi = _hm(kw[k])
                hb[k] = f"{h:02d}:{mi:02d}"
        _save(d)
        return hb


def in_quiet(hb, now=None):
    now = (now or datetime.now()).strftime("%H:%M")
    a, b = hb.get("ruhe_von", "22:00"), hb.get("ruhe_bis", "07:00")
    if a == b:
        return False
    return (a <= now or now < b) if a > b else (a <= now < b)


def hb_due(now=None):
    hb = hb_get()
    now = now or time.time()
    return hb["an"] and hb["checkliste"].strip() and now - hb["letzter"] >= hb["minuten"] * 60 - 20 and not in_quiet(hb) \
        and "heartbeat" not in RUNNING


HB_PROMPT = ("HEARTBEAT – stiller Routine-Check (der Nutzer hat nichts gefragt). Geh diese Checkliste des Nutzers durch und prüfe sie mit "
             "deinen Werkzeugen (nur nachsehen, nichts verändern, nichts senden):\n\n{checkliste}\n\n"
             "Bereits gemeldet (NICHT nochmal melden, außer es hat sich deutlich verändert):\n{gemeldet}\n\n"
             "Jetzt ist {jetzt}. Wenn etwas dabei ist, das der Nutzer JETZT wissen sollte, schreib ihm eine kurze Nachricht (1–4 Sätze, "
             "das Wichtigste zuerst). Wenn nichts Neues oder Wichtiges ist, antworte exakt: HEARTBEAT_OK")


def hb_prompt():
    hb = hb_get()
    told = "\n".join(f"- {m['zeit']}: {m['text'][:200]}" for m in hb["meldungen"][-8:]) or "(nichts)"
    return HB_PROMPT.format(checkliste=hb["checkliste"].strip(), gemeldet=told, jetzt=datetime.now().strftime("%A %d.%m. %H:%M"))


def hb_record(text, err=""):
    quiet = bool(re.fullmatch(r"\s*\**HEARTBEAT_OK\**[.!]?\s*", text or "")) or (text or "").strip().endswith("HEARTBEAT_OK")
    with LOCK:
        d = _load()
        hb = d["heartbeat"]
        hb["letzter"] = time.time()
        entry = {"zeit": datetime.now().strftime("%d.%m. %H:%M"), "ergebnis": "fehler" if err else "ruhig" if quiet else "gemeldet",
                 "text": (err or ("" if quiet else text))[:500]}
        hb["protokoll"] = (hb["protokoll"] + [entry])[-30:]
        if not quiet and not err:
            hb["meldungen"] = (hb["meldungen"] + [{"zeit": entry["zeit"], "text": text[:500]}])[-20:]
        _save(d)
    return not quiet and not err
