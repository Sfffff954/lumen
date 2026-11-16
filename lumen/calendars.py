"""
Lumen – Kalender schreiben: Termine anlegen, verschieben, löschen.

Ziele (beliebig kombinierbar):
  • Lumen-Kalender (lokal, immer da) – auch als .ics zum Importieren/Abonnieren
  • CalDAV: Nextcloud, iCloud, mailbox.org, Posteo, Fastmail, Radicale … (Benutzer + App-Passwort)
  • Google Kalender (OAuth – eigene Client-ID, wie bei Spotify)
Lesen: alle Ziele + die bisherigen iCal-Links (nur lesen).
"""
import base64
import hashlib
import json
import re
import secrets
import time
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import integrations as I

LOCAL = Path.home() / ".lumen" / "calendar.json"
ICS_OUT = Path.home() / ".lumen" / "lumen-kalender.ics"
RRULES = {"täglich": "FREQ=DAILY", "wöchentlich": "FREQ=WEEKLY", "zweiwöchentlich": "FREQ=WEEKLY;INTERVAL=2",
          "monatlich": "FREQ=MONTHLY", "jährlich": "FREQ=YEARLY", "werktags": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"}
NS = {"d": "DAV:", "c": "urn:ietf:params:xml:ns:caldav", "cs": "http://calendarserver.org/ns/", "a": "http://apple.com/ns/ical/"}


def conf():
    return I.conf("calendar")


# ================================================================ Zeit-Helfer
def parse_dt(s):
    s = str(s or "").strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            d = datetime.strptime(s, fmt)
            return d, fmt in ("%Y-%m-%d", "%d.%m.%Y")
        except ValueError:
            pass
    raise RuntimeError(f"Zeit „{s}“ nicht verstanden – bitte als JJJJ-MM-TT HH:MM.")


def ics_escape(t):
    return str(t or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_fold(line):
    out, b = [], line.encode()
    while len(b) > 74:
        cut = 74
        while cut > 0 and (b[cut] & 0xC0) == 0x80:
            cut -= 1
        out.append(b[:cut].decode())
        b = b" " + b[cut:]
    out.append(b.decode())
    return "\r\n".join(out)


def to_ics(ev):
    start, allday = parse_dt(ev["start"])
    end = parse_dt(ev["end"])[0] if ev.get("end") else (start + timedelta(days=1) if allday else start + timedelta(hours=1))
    utc = lambda d: d.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: E731
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Lumen//Kalender//DE", "CALSCALE:GREGORIAN", "BEGIN:VEVENT",
             f"UID:{ev['uid']}", f"DTSTAMP:{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}", f"SUMMARY:{ics_escape(ev['title'])}"]
    if allday:
        lines += [f"DTSTART;VALUE=DATE:{start:%Y%m%d}", f"DTEND;VALUE=DATE:{(end if end > start else start + timedelta(days=1)):%Y%m%d}"]
    else:
        lines += [f"DTSTART:{utc(start)}", f"DTEND:{utc(end)}"]
    if ev.get("location"):
        lines.append(f"LOCATION:{ics_escape(ev['location'])}")
    if ev.get("description"):
        lines.append(f"DESCRIPTION:{ics_escape(ev['description'])}")
    if ev.get("rrule"):
        lines.append("RRULE:" + ev["rrule"])
    if ev.get("remind_min"):
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{ics_escape(ev['title'])}", f"TRIGGER:-PT{int(ev['remind_min'])}M", "END:VALARM"]
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(ics_fold(l) for l in lines) + "\r\n"


# ================================================================ Lumen-Kalender (lokal)
def local_load():
    try:
        return json.loads(LOCAL.read_text("utf-8"))
    except Exception:
        return []


def local_save(evs):
    LOCAL.parent.mkdir(parents=True, exist_ok=True)
    LOCAL.write_text(json.dumps(evs, ensure_ascii=False, indent=1), "utf-8")
    body = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Lumen//Kalender//DE\r\nX-WR-CALNAME:Lumen\r\n"
    for e in evs:
        one = to_ics(e)
        body += one[one.index("BEGIN:VEVENT"):one.index("END:VCALENDAR")]
    ICS_OUT.write_text(body + "END:VCALENDAR\r\n", "utf-8")


# ================================================================ CalDAV
def _dav(method, url, body=None, depth=None, ctype="application/xml; charset=utf-8", extra=None):
    c = conf()
    auth = base64.b64encode(f"{c.get('caldav_user')}:{c.get('caldav_password')}".encode()).decode()
    h = {"Authorization": "Basic " + auth, "Content-Type": ctype, **(extra or {})}
    if depth is not None:
        h["Depth"] = str(depth)
    import urllib.request
    req = urllib.request.Request(url, data=body.encode() if isinstance(body, str) else body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace"), r.headers
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError("CalDAV: Anmeldung fehlgeschlagen – Benutzer/App-Passwort prüfen.")
        return e.code, e.read().decode("utf-8", "replace"), e.headers


def _abs(base, href):
    return urllib.parse.urljoin(base, href)


def caldav_ok():
    c = conf()
    return all(str(c.get(k) or "").strip() for k in ("caldav_url", "caldav_user", "caldav_password"))


def caldav_calendars():
    """Findet die Kalender des Kontos (PROPFIND-Kette)."""
    url = conf()["caldav_url"].strip()
    if "icloud.com" in url and not url.rstrip("/").endswith(".com"):
        pass
    prop = ('<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop>'
            '<d:current-user-principal/><c:calendar-home-set/><d:resourcetype/><d:displayname/></d:prop></d:propfind>')
    st, body, _ = _dav("PROPFIND", url, prop, depth=0)
    if st >= 400:
        raise RuntimeError(f"CalDAV-Adresse antwortet mit {st}. Beispiele: https://cloud.example.de/remote.php/dav, https://caldav.icloud.com")
    root = ET.fromstring(body)
    home = root.find(".//c:calendar-home-set/d:href", NS)
    if home is None:
        pr = root.find(".//d:current-user-principal/d:href", NS)
        if pr is not None:
            url = _abs(url, pr.text)
            st, body, _ = _dav("PROPFIND", url, prop, depth=0)
            root = ET.fromstring(body)
            home = root.find(".//c:calendar-home-set/d:href", NS)
    home_url = _abs(url, home.text) if home is not None else url
    q = ('<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop><d:resourcetype/>'
         '<d:displayname/><c:supported-calendar-component-set/></d:prop></d:propfind>')
    st, body, _ = _dav("PROPFIND", home_url, q, depth=1)
    cals = []
    for r in ET.fromstring(body).findall("d:response", NS):
        if r.find(".//d:resourcetype/c:calendar", NS) is None:
            continue
        comps = [x.get("name") for x in r.findall(".//c:supported-calendar-component-set/c:comp", NS)]
        if comps and "VEVENT" not in comps:
            continue
        href = r.find("d:href", NS).text
        name = (r.find(".//d:displayname", NS).text if r.find(".//d:displayname", NS) is not None else None) or href.rstrip("/").rsplit("/", 1)[-1]
        cals.append({"name": name, "url": _abs(home_url, href)})
    if not cals:
        raise RuntimeError("Keine Kalender im Konto gefunden.")
    return cals


def _caldav_target():
    cals = caldav_calendars()
    want = (conf().get("caldav_calendar") or "").strip().lower().strip("/")
    if not want:
        return cals[0]
    return next((c for c in cals if c["name"].lower() == want or c["name"].lower().rsplit("/", 1)[-1] == want
                 or c["url"].rstrip("/").rsplit("/", 1)[-1].lower() == want), cals[0])


def caldav_put(ev, cal_url=None):
    url = (cal_url or _caldav_target()["url"]).rstrip("/") + f"/{ev['uid']}.ics"
    st, body, _ = _dav("PUT", url, to_ics(ev), ctype="text/calendar; charset=utf-8")
    if st >= 300:
        raise RuntimeError(f"CalDAV: Termin nicht gespeichert ({st}).")
    return url


def caldav_events(start, end):
    out = []
    q = (f'<?xml version="1.0"?><c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop><d:getetag/>'
         f'<c:calendar-data/></d:prop><c:filter><c:comp-filter name="VCALENDAR"><c:comp-filter name="VEVENT">'
         f'<c:time-range start="{start.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}" end="{end.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}"/>'
         f'</c:comp-filter></c:comp-filter></c:filter></c:calendar-query>')
    for cal in caldav_calendars():
        st, body, _ = _dav("REPORT", cal["url"], q, depth=1)
        if st >= 400:
            continue
        for r in ET.fromstring(body).findall("d:response", NS):
            data = r.find(".//c:calendar-data", NS)
            if data is None or not data.text:
                continue
            href = _abs(cal["url"], r.find("d:href", NS).text)
            for ev in I._parse_ics(data.text):
                if "DTSTART" in ev:
                    out.append(("caldav", cal["name"], href, ev))
    return out


def caldav_delete(href):
    st, _, _ = _dav("DELETE", href)
    if st >= 300 and st != 404:
        raise RuntimeError(f"CalDAV: Löschen fehlgeschlagen ({st}).")


# ================================================================ Google Kalender (OAuth)
G_SCOPES = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/calendar.readonly"
_pending = {}


def google_redirect():
    return I.base_url().rstrip("/") + "/callback/google"


def google_ok():
    return bool(conf().get("google_refresh"))


def google_auth_url():
    c = conf()
    if not c.get("google_client_id") or not c.get("google_client_secret"):
        raise RuntimeError("Zuerst Google Client-ID und Client-Secret eintragen und speichern.")
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(16)
    _pending.clear()
    _pending[state] = (verifier, time.time())
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": c["google_client_id"], "redirect_uri": google_redirect(), "response_type": "code", "scope": G_SCOPES,
        "code_challenge": challenge, "code_challenge_method": "S256", "state": state, "access_type": "offline", "prompt": "consent"})


def google_callback(code, state):
    item = _pending.pop(state or "", None)
    if not item or time.time() - item[1] > 900:
        raise RuntimeError("Anmeldung abgelaufen – in Lumen nochmal auf 'Mit Google anmelden' klicken.")
    c = conf()
    st, js, _ = I._http("POST", "https://oauth2.googleapis.com/token", form={
        "code": code, "client_id": c["google_client_id"], "client_secret": c["google_client_secret"], "redirect_uri": google_redirect(),
        "grant_type": "authorization_code", "code_verifier": item[0]})
    if st != 200 or not js or not js.get("refresh_token"):
        raise RuntimeError(f"Google-Anmeldung fehlgeschlagen: {(js or {}).get('error_description', st)}")
    I.save_app("calendar", {"google_refresh": js["refresh_token"], "google_token": js["access_token"],
                            "google_expires": time.time() + js.get("expires_in", 3600) - 60})
    try:
        cal = _g("GET", "/calendars/primary")
        I.save_app("calendar", {"google_account": cal.get("id")})
    except Exception:
        pass
    return True


def _g_token():
    c = conf()
    if time.time() < float(c.get("google_expires") or 0) and c.get("google_token"):
        return c["google_token"]
    st, js, _ = I._http("POST", "https://oauth2.googleapis.com/token", form={
        "client_id": c.get("google_client_id"), "client_secret": c.get("google_client_secret"),
        "refresh_token": c.get("google_refresh"), "grant_type": "refresh_token"})
    if st != 200 or not js:
        raise RuntimeError("Google-Anmeldung abgelaufen – in den Apps unter Kalender neu anmelden.")
    I.save_app("calendar", {"google_token": js["access_token"], "google_expires": time.time() + js.get("expires_in", 3600) - 60})
    return js["access_token"]


def _g(method, path, params=None, body=None):
    url = "https://www.googleapis.com/calendar/v3" + path + ("?" + urllib.parse.urlencode(params) if params else "")
    st, js, _ = I._http(method, url, json_body=body, headers={"Authorization": f"Bearer {_g_token()}"})
    if st >= 300:
        raise RuntimeError(f"Google Kalender: {((js or {}).get('error') or {}).get('message', st)}")
    return js or {}


def _g_body(ev):
    start, allday = parse_dt(ev["start"])
    end = parse_dt(ev["end"])[0] if ev.get("end") else (start + timedelta(days=1) if allday else start + timedelta(hours=1))
    tz = time.tzname[0] if False else None
    b = {"summary": ev["title"], "location": ev.get("location") or None, "description": ev.get("description") or None}
    if allday:
        b["start"], b["end"] = {"date": f"{start:%Y-%m-%d}"}, {"date": f"{(end if end > start else start + timedelta(days=1)):%Y-%m-%d}"}
    else:
        b["start"], b["end"] = {"dateTime": start.astimezone().isoformat()}, {"dateTime": end.astimezone().isoformat()}
    if ev.get("rrule"):
        b["recurrence"] = ["RRULE:" + ev["rrule"]]
    if ev.get("remind_min"):
        b["reminders"] = {"useDefault": False, "overrides": [{"method": "popup", "minutes": int(ev["remind_min"])}]}
    return {k: v for k, v in b.items() if v is not None}


def google_events(start, end):
    js = _g("GET", "/calendars/primary/events", {"timeMin": start.astimezone().isoformat(), "timeMax": end.astimezone().isoformat(),
                                                  "singleEvents": "true", "orderBy": "startTime", "maxResults": 250})
    out = []
    for e in js.get("items", []):
        s, en = e.get("start", {}), e.get("end", {})
        allday = "date" in s
        st = datetime.fromisoformat(s.get("dateTime") or s.get("date")).astimezone().replace(tzinfo=None) if not allday else datetime.fromisoformat(s["date"])
        et = datetime.fromisoformat(en.get("dateTime") or en.get("date")).astimezone().replace(tzinfo=None) if not allday else datetime.fromisoformat(en["date"])
        out.append({"start": st, "ende": et, "allday": allday, "titel": e.get("summary") or "(ohne Titel)", "ort": e.get("location") or "",
                    "kalender": "Google", "id": "google:" + e["id"].split("_")[0] if e.get("recurringEventId") is None else "google:" + e["recurringEventId"]})
    return out


# ================================================================ Gemeinsame Schnittstelle
def targets():
    t = [{"id": "lumen", "name": "Lumen-Kalender (lokal)"}]
    if caldav_ok():
        t.append({"id": "caldav", "name": "CalDAV" + (f" · {conf().get('caldav_calendar')}" if conf().get("caldav_calendar") else "")})
    if google_ok():
        t.append({"id": "google", "name": "Google" + (f" · {conf().get('google_account')}" if conf().get("google_account") else "")})
    return t


def default_target():
    want = conf().get("write_to") or ""
    ids = [t["id"] for t in targets()]
    if want in ids:
        return want
    return "google" if "google" in ids else "caldav" if "caldav" in ids else "lumen"


def add(title, start, end=None, duration_min=None, location="", description="", repeat="", remind_min=None, target=None):
    s, allday = parse_dt(start)
    if end:
        e, _ = parse_dt(end)
    elif duration_min:
        e = s + timedelta(minutes=int(duration_min))
    else:
        e = s + (timedelta(days=1) if allday else timedelta(hours=1))
    if e <= s:
        raise RuntimeError("Das Ende liegt vor dem Anfang.")
    rr = RRULES.get(str(repeat or "").lower(), "") if repeat else ""
    if repeat and not rr and str(repeat).upper().startswith("FREQ="):
        rr = str(repeat).upper()
    ev = {"uid": f"{uuid.uuid4()}@lumen", "title": str(title)[:200], "start": f"{s:%Y-%m-%d}" if allday else f"{s:%Y-%m-%d %H:%M}",
          "end": f"{e:%Y-%m-%d}" if allday else f"{e:%Y-%m-%d %H:%M}", "location": location or "", "description": description or "",
          "rrule": rr, "remind_min": int(remind_min) if remind_min else None, "created": time.time()}
    tgt = target or default_target()
    where = "Lumen-Kalender"
    if tgt == "google":
        js = _g("POST", "/calendars/primary/events", body=_g_body(ev))
        ev["google_id"], where = js.get("id"), "Google Kalender"
    elif tgt == "caldav":
        cal = _caldav_target()
        ev["caldav_href"], where = caldav_put(ev, cal["url"]), f"Kalender „{cal['name']}“"
    else:
        evs = local_load()
        evs.append(ev)
        local_save(evs)
    wd = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][s.weekday()]
    when = (f"{wd} {s:%d.%m.%Y}" + ("" if allday else f", {s:%H:%M}–{e:%H:%M}"))
    return {"ok": True, "text": f"📅 „{ev['title']}“ am {when} eingetragen ({where})" + (f", {repeat}" if rr else "") + ".",
            "termin": ev, "ziel": tgt, "google_link": google_template_link(ev) if tgt == "lumen" else None}


def google_template_link(ev):
    """Klick-Link: öffnet Google Kalender mit vorausgefülltem Termin (ohne Anmeldung in Lumen)."""
    s, allday = parse_dt(ev["start"])
    e = parse_dt(ev["end"])[0]
    fmt = (lambda d: f"{d:%Y%m%d}") if allday else (lambda d: d.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode({
        "action": "TEMPLATE", "text": ev["title"], "dates": f"{fmt(s)}/{fmt(e)}", "location": ev.get("location") or "",
        "details": ev.get("description") or ""})


def collect(start, end):
    """Alle schreibbaren Kalender lesen → Liste wie integrations.calendar_events (start, ende, allday, titel, ort, kalender, id)."""
    out, errors = [], []
    for ev in local_load():
        try:
            raw = I._parse_ics(to_ics(ev))[0]
            for s, dur, allday in I._expand(raw, start, end):
                out.append({"start": s, "ende": s + dur, "allday": allday, "titel": ev["title"], "ort": ev.get("location", ""),
                            "kalender": "Lumen", "id": "lumen:" + ev["uid"]})
        except Exception:
            continue
    if caldav_ok():
        try:
            for _, cal, href, raw in caldav_events(start, end):
                for s, dur, allday in I._expand(raw, start, end):
                    out.append({"start": s, "ende": s + dur, "allday": allday, "titel": raw.get("SUMMARY", ("(ohne Titel)",))[0].replace("\\,", ","),
                                "ort": raw.get("LOCATION", ("",))[0].replace("\\,", ","), "kalender": cal, "id": "caldav:" + href})
        except Exception as e:
            errors.append(f"CalDAV: {e}")
    if google_ok():
        try:
            out += google_events(start, end)
        except Exception as e:
            errors.append(f"Google: {e}")
    return out, errors


def find(query, days=60):
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    evs, _ = collect(start, start + timedelta(days=days))
    q = str(query or "").lower().strip()
    hits = [e for e in evs if q and (q in e["titel"].lower() or q in e["id"].lower())]
    return sorted(hits, key=lambda e: e["start"])


def delete(event_id=None, query=None):
    if not event_id:
        hits = find(query)
        if not hits:
            raise RuntimeError(f"Keinen Termin „{query}“ gefunden.")
        if len({h["id"] for h in hits}) > 1:
            raise RuntimeError("Mehrere Termine passen: " + "; ".join(f"{h['titel']} {h['start']:%d.%m. %H:%M} (id {h['id']})" for h in hits[:6]) +
                               " – bitte mit id löschen.")
        event_id = hits[0]["id"]
    kind, _, ref = event_id.partition(":")
    if kind == "lumen":
        evs = local_load()
        left = [e for e in evs if e["uid"] != ref]
        if len(left) == len(evs):
            raise RuntimeError("Termin nicht gefunden.")
        local_save(left)
    elif kind == "caldav":
        caldav_delete(ref)
    elif kind == "google":
        _g("DELETE", f"/calendars/primary/events/{urllib.parse.quote(ref)}")
    else:
        raise RuntimeError("Unbekannte Termin-id (Termine aus reinen iCal-Links kann Lumen nicht ändern).")
    return {"ok": True, "text": "🗑 Termin gelöscht."}


def move(event_id=None, query=None, new_start=None, new_end=None, title=None, location=None):
    if not event_id:
        hits = find(query)
        if len({h["id"] for h in hits}) != 1:
            raise RuntimeError("Termin nicht eindeutig gefunden – bitte genauer oder mit id.")
        event_id = hits[0]["id"]
    kind, _, ref = event_id.partition(":")
    if kind == "lumen":
        evs = local_load()
        ev = next((e for e in evs if e["uid"] == ref), None)
        if not ev:
            raise RuntimeError("Termin nicht gefunden.")
        _apply_change(ev, new_start, new_end, title, location)
        local_save(evs)
    elif kind == "google":
        cur = _g("GET", f"/calendars/primary/events/{urllib.parse.quote(ref)}")
        s0 = (cur.get("start") or {})
        ev = {"title": title or cur.get("summary", ""), "location": location if location is not None else cur.get("location", ""),
              "description": cur.get("description", ""),
              "start": (s0.get("dateTime") or s0.get("date") or "")[:16], "end": ((cur.get("end") or {}).get("dateTime") or (cur.get("end") or {}).get("date") or "")[:16]}
        _apply_change(ev, new_start, new_end, None, None)
        _g("PATCH", f"/calendars/primary/events/{urllib.parse.quote(ref)}", body={k: v for k, v in _g_body(ev).items() if k in ("summary", "location", "start", "end")})
    elif kind == "caldav":
        st, body, _ = _dav("GET", ref, ctype="text/calendar")
        raw = I._parse_ics(body)[0]
        s, allday = I._ics_dt(*raw["DTSTART"])
        e = I._ics_dt(*raw["DTEND"])[0] if "DTEND" in raw else s + timedelta(hours=1)
        ev = {"uid": raw.get("UID", (ref.rsplit("/", 1)[-1][:-4],))[0], "title": title or raw.get("SUMMARY", ("",))[0].replace("\\,", ","),
              "location": location if location is not None else raw.get("LOCATION", ("",))[0], "description": raw.get("DESCRIPTION", ("",))[0],
              "start": f"{s:%Y-%m-%d}" if allday else f"{s:%Y-%m-%d %H:%M}", "end": f"{e:%Y-%m-%d}" if allday else f"{e:%Y-%m-%d %H:%M}",
              "rrule": raw.get("RRULE", ("",))[0]}
        _apply_change(ev, new_start, new_end, None, None)
        st, _, _ = _dav("PUT", ref, to_ics(ev), ctype="text/calendar; charset=utf-8")
        if st >= 300:
            raise RuntimeError(f"CalDAV: Ändern fehlgeschlagen ({st}).")
    else:
        raise RuntimeError("Diesen Termin kann Lumen nicht ändern (nur-lesen iCal-Link).")
    return {"ok": True, "text": "✏️ Termin geändert."}


def _apply_change(ev, new_start, new_end, title, location):
    if new_start:
        s_old, allday = parse_dt(ev["start"])
        e_old = parse_dt(ev["end"])[0] if ev.get("end") else s_old + timedelta(hours=1)
        s_new, allday_new = parse_dt(new_start)
        ev["start"] = f"{s_new:%Y-%m-%d}" if allday_new else f"{s_new:%Y-%m-%d %H:%M}"
        e_new = parse_dt(new_end)[0] if new_end else s_new + (e_old - s_old)
        ev["end"] = f"{e_new:%Y-%m-%d}" if allday_new else f"{e_new:%Y-%m-%d %H:%M}"
    elif new_end:
        e_new, allday = parse_dt(new_end)
        ev["end"] = f"{e_new:%Y-%m-%d}" if allday else f"{e_new:%Y-%m-%d %H:%M}"
    if title:
        ev["title"] = title
    if location is not None:
        ev["location"] = location


def free_slots(day, duration_min=60, start_h=8, end_h=20):
    d, _ = parse_dt(day)
    d0 = d.replace(hour=start_h, minute=0)
    d1 = d.replace(hour=end_h, minute=0)
    evs, _ = collect(d.replace(hour=0, minute=0), d.replace(hour=23, minute=59))
    try:
        ics, _ = I.calendar_events_raw(d.replace(hour=0, minute=0), d.replace(hour=23, minute=59))
        evs += ics
    except Exception:
        pass
    busy = sorted((max(e["start"], d0), min(e["ende"], d1)) for e in evs if not e["allday"] and e["ende"] > d0 and e["start"] < d1)
    slots, cur = [], d0
    for s, e in busy:
        if (s - cur).total_seconds() >= duration_min * 60:
            slots.append(f"{cur:%H:%M}–{s:%H:%M}")
        cur = max(cur, e)
    if (d1 - cur).total_seconds() >= duration_min * 60:
        slots.append(f"{cur:%H:%M}–{d1:%H:%M}")
    return {"tag": f"{['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][d.weekday()]} {d:%d.%m.%Y}", "frei": slots, "belegt": [f"{s:%H:%M}–{e:%H:%M}" for s, e in busy]}
