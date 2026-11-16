"""
Lumen – verbundene Apps.

Krypto-Wallets (Phantom & Co.) – NUR LESEN über öffentliche Adressen, Zahlungen nur als QR-Code zum Bestätigen in Phantom.
Spotify (OAuth/PKCE), Discord (Webhooks), Telegram (Bot), GitHub (Token), Home Assistant (Token),
Steam (Preise ohne Key, Profil mit Key), Wetter (Open-Meteo, ohne Key), Kalender (iCal-Links).

lumen.py setzt: get_apps() -> dict, save_app(app_id, patch_dict), base_url() -> "http://127.0.0.1:PORT"
"""
import base64
import hashlib
import io
import json
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

get_apps = lambda: {}
save_app = lambda app_id, patch: None
base_url = lambda: "http://127.0.0.1:8765"
UA = "Lumen-Assistant/1.0"


def S(props=None, req=None):
    return {"type": "object", "properties": props or {}, "required": req or []}


STR = {"type": "string"}


def conf(app_id):
    return (get_apps() or {}).get(app_id, {}) or {}


def _http(method, url, headers=None, json_body=None, form=None, data=None, timeout=20):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body).encode()
        h["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded"
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read()
    except urllib.error.URLError as e:
        raise RuntimeError(f"Nicht erreichbar: {e.reason}")
    except TimeoutError:
        raise RuntimeError("Zeitüberschreitung.")
    try:
        js = json.loads(body) if body else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        js = None
    return status, js, body


def _lines(text):
    out = {}
    for line in str(text or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            if k.strip() and v.strip():
                out[k.strip()] = v.strip()
    return out


# ================================================================ Seed-Phrasen-Schutz
def looks_like_secret(text):
    t = str(text or "")
    if re.search(r"(?<![a-zäöüß])((?:[a-z]{3,8}[ \t\n]+){11,23}[a-z]{3,8})(?![a-zäöüß])", t):
        run = re.search(r"((?:[a-z]{3,8}[ \t\n]+){11,23}[a-z]{3,8})", t).group(1).split()
        common = {"ich", "und", "die", "der", "das", "ist", "nicht", "mit", "auf", "für", "ein", "eine", "den", "dem", "wir",
                  "sie", "mal", "noch", "nur", "habe", "bin", "kann", "will", "was", "wie", "mir", "mich", "dir", "dich",
                  "aber", "oder", "wenn", "dann", "auch", "schon", "hab", "the", "and", "you", "with", "for", "this", "that",
                  "have", "are", "was", "but", "not", "what", "how", "mein", "meine", "bitte", "jetzt", "heute"}
        if len(run) in (12, 15, 18, 21, 24) and len(set(run)) >= len(run) // 2 and len(common & set(run)) < 2:
            return "Das sieht aus wie eine Seed-Phrase (Wiederherstellungs-Wörter)."
    ctx = re.search(r"(?i)key|schlüssel|schluessel|private|privat|secret|geheim|seed|phantom|export", t)
    for m in re.finditer(r"(?<![1-9A-HJ-NP-Za-km-z/])[1-9A-HJ-NP-Za-km-z]{80,100}(?![1-9A-HJ-NP-Za-km-z])", t):
        before = t[max(0, m.start() - 4):m.start()]
        if "tx/" in before:
            continue
        if ctx or t.strip() == m.group(0):
            return "Das sieht aus wie ein privater Wallet-Schlüssel."
    if re.search(r"\[\s*(\d{1,3}\s*,\s*){63}\d{1,3}\s*\]", t):
        return "Das sieht aus wie eine Solana-Schlüsseldatei."
    if ctx and re.search(r"(?<![0-9a-fA-F])(0x)?[0-9a-fA-F]{64}(?![0-9a-fA-F])", t):
        return "Das sieht aus wie ein privater Schlüssel."
    return None


# ================================================================ Wetter
WMO = {0: ("klar", "☀️"), 1: ("überwiegend klar", "🌤️"), 2: ("teils bewölkt", "⛅"), 3: ("bedeckt", "☁️"),
       45: ("Nebel", "🌫️"), 48: ("Reifnebel", "🌫️"), 51: ("leichter Niesel", "🌦️"), 53: ("Niesel", "🌦️"),
       55: ("starker Niesel", "🌧️"), 56: ("gefrierender Niesel", "🌧️"), 57: ("gefrierender Niesel", "🌧️"),
       61: ("leichter Regen", "🌦️"), 63: ("Regen", "🌧️"), 65: ("starker Regen", "🌧️"), 66: ("gefrierender Regen", "🌧️"),
       67: ("gefrierender Regen", "🌧️"), 71: ("leichter Schnee", "🌨️"), 73: ("Schnee", "🌨️"), 75: ("starker Schnee", "❄️"),
       77: ("Schneegriesel", "🌨️"), 80: ("Regenschauer", "🌦️"), 81: ("Regenschauer", "🌧️"), 82: ("heftige Schauer", "⛈️"),
       85: ("Schneeschauer", "🌨️"), 86: ("Schneeschauer", "❄️"), 95: ("Gewitter", "⛈️"), 96: ("Gewitter mit Hagel", "⛈️"),
       99: ("Gewitter mit Hagel", "⛈️")}
_geo = {}


def _geocode(city):
    key = city.strip().lower()
    if key in _geo:
        return _geo[key]
    st, js, _ = _http("GET", "https://geocoding-api.open-meteo.com/v1/search?" +
                      urllib.parse.urlencode({"name": city, "count": 1, "language": "de"}))
    res = (js or {}).get("results") or []
    if not res:
        raise RuntimeError(f"Ort '{city}' nicht gefunden.")
    r = res[0]
    _geo[key] = (r["latitude"], r["longitude"], f"{r['name']}{', ' + r['admin1'] if r.get('admin1') else ''}")
    return _geo[key]


def weather(city=None, days=3):
    city = (city or conf("weather").get("city") or "").strip()
    if not city:
        raise RuntimeError("Kein Ort angegeben. In den Apps unter Wetter deinen Ort eintragen.")
    lat, lon, name = _geocode(city)
    return weather_at(lat, lon, name, days)


def weather_at(lat, lon, name="", days=3):
    """Wetter für Koordinaten (z. B. geteilter Standort)."""
    days = max(1, min(int(days or 3), 7))
    st, js, _ = _http("GET", "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
        "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": days,
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation,relative_humidity_2m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,sunrise,sunset"}))
    if st != 200 or not js:
        raise RuntimeError("Wetterdienst nicht erreichbar.")
    c = js["current"]
    desc, icon = WMO.get(c["weather_code"], ("?", "🌡️"))
    d = js["daily"]
    days_out = []
    for i, day in enumerate(d["time"]):
        dd, di = WMO.get(d["weather_code"][i], ("?", ""))
        dt = datetime.fromisoformat(day)
        days_out.append({"tag": f"{('Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So')[dt.weekday()]} {dt:%d.%m.}", "wetter": dd, "icon": di,
                         "max": d["temperature_2m_max"][i], "min": d["temperature_2m_min"][i],
                         "regen_wahrscheinlichkeit": d["precipitation_probability_max"][i], "regen_mm": d["precipitation_sum"][i],
                         "sonnenaufgang": d["sunrise"][i][-5:], "sonnenuntergang": d["sunset"][i][-5:]})
    return {"ort": name, "jetzt": {"temperatur": c["temperature_2m"], "gefühlt": c["apparent_temperature"], "wetter": desc,
                                    "icon": icon, "wind_kmh": c["wind_speed_10m"], "luftfeuchte": c["relative_humidity_2m"]},
            "tage": days_out}


# ================================================================ Kalender (iCal)
def _ics_dt(value, params):
    v = value.strip()
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", v):
        return datetime.strptime(v[:8], "%Y%m%d"), True
    if v.endswith("Z"):
        return datetime.strptime(v, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None), False
    dt = datetime.strptime(v[:15], "%Y%m%dT%H%M%S")
    tz = params.get("TZID")
    if tz and ZoneInfo:
        try:
            dt = dt.replace(tzinfo=ZoneInfo(tz)).astimezone().replace(tzinfo=None)
        except Exception:
            pass
    return dt, False


def _parse_ics(text):
    text = re.sub(r"\r?\n[ \t]", "", text)
    events, cur = [], None
    for line in text.splitlines():
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT" and cur is not None:
            events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            head, val = line.split(":", 1)
            name, *ps = head.split(";")
            params = dict(p.split("=", 1) for p in ps if "=" in p)
            if name == "EXDATE":
                cur.setdefault("EXDATE", []).extend((v, params) for v in val.split(","))
            else:
                cur[name] = (val, params)
    return events


WD = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def _expand(ev, start, end):
    dtstart, allday = _ics_dt(*ev["DTSTART"])
    dur = timedelta(days=1) if allday else timedelta(hours=1)
    if "DTEND" in ev:
        dtend, _ = _ics_dt(*ev["DTEND"])
        dur = dtend - dtstart
    rr = ev.get("RRULE")
    if not rr:
        return [(dtstart, dur, allday)] if dtstart + dur >= start and dtstart <= end else []
    rule = dict(p.split("=", 1) for p in rr[0].split(";") if "=" in p)
    freq, interval = rule.get("FREQ"), int(rule.get("INTERVAL", 1))
    count = int(rule["COUNT"]) if "COUNT" in rule else None
    until = _ics_dt(rule["UNTIL"], {})[0] if "UNTIL" in rule else None
    ex = {_ics_dt(v, p)[0] for v, p in ev.get("EXDATE", [])}
    byday = [WD[d[-2:]] for d in rule.get("BYDAY", "").split(",") if d[-2:] in WD]
    out, n, cur, guard = [], 0, dtstart, 0
    while guard < 3000:
        guard += 1
        cands = [cur]
        if freq == "WEEKLY" and byday:
            monday = cur - timedelta(days=cur.weekday())
            cands = sorted(monday + timedelta(days=d) for d in byday)
            cands = [c.replace(hour=dtstart.hour, minute=dtstart.minute) for c in cands if c >= dtstart.replace(hour=0, minute=0)]
        for c in cands:
            if until and c > until or count and n >= count:
                return out
            if c < dtstart:
                continue
            n += 1
            if c not in ex and c + dur >= start and c <= end:
                out.append((c, dur, allday))
        if cur > end:
            return out
        if freq == "DAILY":
            cur += timedelta(days=interval)
        elif freq == "WEEKLY":
            cur += timedelta(weeks=interval)
        elif freq == "MONTHLY":
            m = cur.month - 1 + interval
            y = cur.year + m // 12
            try:
                cur = cur.replace(year=y, month=m % 12 + 1)
            except ValueError:
                cur = cur.replace(year=y, month=m % 12 + 1, day=28)
        elif freq == "YEARLY":
            try:
                cur = cur.replace(year=cur.year + interval)
            except ValueError:
                cur = cur.replace(year=cur.year + interval, day=28)
        else:
            return out
    return out


def calendar_events_raw(start, end, text_override=None):
    """Termine aus den iCal-Links (nur lesen)."""
    cals = _lines(conf("calendar").get("calendars"))
    events, errors = [], []
    sources = {"Test": text_override} if text_override is not None else cals
    for name, src in sources.items():
        try:
            if text_override is None:
                url = re.sub(r"^webcal://", "https://", src)
                st, _, body = _http("GET", url, headers={"Accept": "text/calendar"}, timeout=25)
                if st != 200:
                    raise RuntimeError(f"Status {st}")
                text = body.decode("utf-8", errors="replace")
            else:
                text = src
            for ev in _parse_ics(text):
                if "DTSTART" not in ev:
                    continue
                for s, dur, allday in _expand(ev, start, end):
                    events.append({"start": s, "allday": allday, "ende": s + dur, "titel": ev.get("SUMMARY", ("(ohne Titel)",))[0]
                                   .replace("\\,", ",").replace("\\n", " "), "ort": ev.get("LOCATION", ("",))[0].replace("\\,", ","),
                                   "kalender": name, "id": None})
        except Exception as e:
            errors.append(f"{name}: {e}")
    if text_override is None:
        return events, errors
    return events, errors


def calendar_events(days=7, text_override=None):
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=max(1, min(int(days or 7), 60)))
    events, errors = calendar_events_raw(start, end, text_override)
    if text_override is None:
        try:
            import calendars
            more, err2 = calendars.collect(start, end)
            events += more
            errors += err2
        except Exception as e:
            errors.append(f"Kalender: {e}")
    events.sort(key=lambda e: e["start"])
    out = [{"wann": e["start"].strftime("%a %d.%m.") + ("" if e["allday"] else e["start"].strftime(" %H:%M") +
            "–" + e["ende"].strftime("%H:%M")) + (" (ganztägig)" if e["allday"] else ""),
            "titel": e["titel"], "ort": e["ort"] or None, "kalender": e["kalender"], "id": e.get("id")} for e in events[:80]]
    return {"zeitraum_tage": (end - start).days, "termine": out, "fehler": errors or None}


# ================================================================ Discord
def discord_send(channel, message):
    hooks = _lines(conf("discord").get("webhooks"))
    if not hooks:
        raise RuntimeError("Kein Discord-Webhook verbunden.")
    key = next((k for k in hooks if k.lower() == str(channel or "").lower()), None) or (list(hooks)[0] if len(hooks) == 1 else None)
    if not key:
        raise RuntimeError(f"Unbekannter Kanal. Verfügbar: {', '.join(hooks)}")
    st, js, body = _http("POST", hooks[key], json_body={"content": str(message)[:2000], "allowed_mentions": {"parse": []}})
    if st not in (200, 204):
        raise RuntimeError(f"Discord-Fehler {st}: {(js or {}).get('message', '')}")
    return f"In #{key} gesendet."


def _discord_test(c):
    hooks = _lines(c.get("webhooks"))
    if not hooks:
        raise RuntimeError("Mindestens einen Webhook eintragen: name = https://discord.com/api/webhooks/…")
    names = []
    for k, url in hooks.items():
        if not re.match(r"^https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[\w-]+$", url):
            raise RuntimeError(f"'{k}' ist keine Discord-Webhook-Adresse.")
        st, js, _ = _http("GET", url)
        if st != 200:
            raise RuntimeError(f"Webhook '{k}' ungültig ({st}).")
        names.append(f"{k} → {js.get('name')}")
    return "Verbunden: " + ", ".join(names)


# ================================================================ Telegram
def _tg(method, token=None, **params):
    token = token or conf("telegram").get("bot_token")
    if not token:
        raise RuntimeError("Telegram-Bot nicht verbunden.")
    st, js, _ = _http("POST", f"https://api.telegram.org/bot{token}/{method}", json_body=params)
    if not js or not js.get("ok"):
        raise RuntimeError(f"Telegram: {(js or {}).get('description', st)}")
    return js["result"]


def telegram_send(text):
    cid = conf("telegram").get("chat_id")
    if not cid:
        raise RuntimeError("Keine Chat-ID. In den Apps unter Telegram 'Chat-ID finden' klicken.")
    _tg("sendMessage", chat_id=cid, text=str(text)[:4000])
    return "Nachricht an dein Telegram gesendet."


def telegram_send_file(path, caption=""):
    from pathlib import Path
    c = conf("telegram")
    p = Path(path)
    if not p.is_file():
        raise RuntimeError(f"{p} existiert nicht.")
    if p.stat().st_size > 49 * 1024 * 1024:
        raise RuntimeError("Telegram-Bots dürfen max. 50 MB senden.")
    boundary = "lumen" + secrets.token_hex(8)
    parts = []
    for k, v in (("chat_id", c.get("chat_id", "")), ("caption", caption[:1000])):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{p.name}\"\r\n"
                 f"Content-Type: application/octet-stream\r\n\r\n".encode() + p.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    st, js, _ = _http("POST", f"https://api.telegram.org/bot{c.get('bot_token')}/sendDocument", data=b"".join(parts),
                      headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, timeout=120)
    if not js or not js.get("ok"):
        raise RuntimeError(f"Telegram: {(js or {}).get('description', st)}")
    return f"{p.name} an dein Telegram gesendet."


def telegram_detect(token):
    me = _tg("getMe", token=token)
    upd = _tg("getUpdates", token=token, limit=20)
    chats = [u["message"]["chat"] for u in upd if u.get("message", {}).get("chat", {}).get("type") == "private"]
    if not chats:
        raise RuntimeError(f"Schreib zuerst deinem Bot @{me['username']} in Telegram eine Nachricht (z. B. /start) und klick dann nochmal.")
    return str(chats[-1]["id"]), me["username"]


def _telegram_test(c):
    me = _tg("getMe", token=c.get("bot_token"))
    if c.get("chat_id"):
        _tg("sendMessage", token=c["bot_token"], chat_id=c["chat_id"], text="✅ Lumen ist verbunden.")
        return f"Verbunden mit @{me['username']} – Testnachricht gesendet."
    return f"Bot @{me['username']} erkannt. Jetzt noch die Chat-ID finden."


# ================================================================ GitHub
def _gh(method, path, body=None, token=None):
    token = token or conf("github").get("token")
    if not token:
        raise RuntimeError("GitHub nicht verbunden.")
    st, js, _ = _http(method, "https://api.github.com" + path, json_body=body, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    if st == 401:
        raise RuntimeError("GitHub-Token ungültig oder abgelaufen.")
    if st == 404:
        raise RuntimeError("Nicht gefunden (Repo-Name richtig? Token hat Zugriff?).")
    if st >= 400:
        raise RuntimeError(f"GitHub-Fehler {st}: {(js or {}).get('message', '')}")
    return js


_gh_user = {}


def _repo(repo):
    r = str(repo or "").strip().strip("/")
    if not r:
        raise RuntimeError("Welches Repository? (z. B. meinname/projekt)")
    if "/" not in r:
        tok = conf("github").get("token")
        if tok not in _gh_user:
            _gh_user[tok] = _gh("GET", "/user")["login"]
        r = f"{_gh_user[tok]}/{r}"
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", r):
        raise RuntimeError("Ungültiger Repo-Name.")
    return r


def github(action, repo=None, title=None, body=None):
    if action == "repos":
        js = _gh("GET", "/user/repos?sort=updated&per_page=25")
        return [{"repo": r["full_name"], "privat": r["private"], "sterne": r["stargazers_count"],
                 "offene_issues": r["open_issues_count"], "aktualisiert": r["updated_at"][:10]} for r in js]
    if action == "notifications":
        js = _gh("GET", "/notifications?per_page=25")
        return [{"repo": n["repository"]["full_name"], "titel": n["subject"]["title"], "art": n["subject"]["type"],
                 "grund": n["reason"], "zeit": n["updated_at"][:16]} for n in js] or "Keine ungelesenen Benachrichtigungen."
    if action == "issues":
        js = _gh("GET", f"/repos/{_repo(repo)}/issues?state=open&per_page=25")
        return [{"nr": i["number"], "titel": i["title"], "von": i["user"]["login"], "labels": [l["name"] for l in i["labels"]],
                 "kommentare": i["comments"]} for i in js if "pull_request" not in i] or "Keine offenen Issues."
    if action == "prs":
        js = _gh("GET", f"/repos/{_repo(repo)}/pulls?state=open&per_page=25")
        return [{"nr": p["number"], "titel": p["title"], "von": p["user"]["login"], "branch": p["head"]["ref"],
                 "entwurf": p["draft"]} for p in js] or "Keine offenen Pull Requests."
    if action == "actions":
        js = _gh("GET", f"/repos/{_repo(repo)}/actions/runs?per_page=10")
        return [{"workflow": r["name"], "status": r["status"], "ergebnis": r["conclusion"], "branch": r["head_branch"],
                 "zeit": r["created_at"][:16], "link": r["html_url"]} for r in js.get("workflow_runs", [])] or "Keine Workflow-Läufe."
    if action == "create_issue":
        if not title:
            raise RuntimeError("Titel fehlt.")
        js = _gh("POST", f"/repos/{_repo(repo)}/issues", {"title": str(title)[:250], "body": str(body or "")[:20000]})
        return {"erstellt": js["number"], "link": js["html_url"]}
    raise RuntimeError("Unbekannte Aktion.")


def _github_test(c):
    u = _gh("GET", "/user", token=c.get("token"))
    return f"Verbunden als {u['login']}."


# ================================================================ Home Assistant
HA_RISKY = {"lock", "alarm_control_panel", "cover", "siren", "valve", "water_heater", "garage_door"}


def _ha(method, path, body=None, c=None):
    c = c or conf("homeassistant")
    url, tok = (c.get("url") or "").rstrip("/"), c.get("token")
    if not url or not tok:
        raise RuntimeError("Home Assistant nicht verbunden.")
    st, js, raw = _http(method, url + path, json_body=body, headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    if st == 401:
        raise RuntimeError("Home-Assistant-Token ungültig.")
    if st >= 400:
        raise RuntimeError(f"Home Assistant Fehler {st}: {raw[:200].decode(errors='replace')}")
    return js


def ha_states(search=None, domain=None):
    js = _ha("GET", "/api/states")
    q = (search or "").lower()
    out = []
    for e in js:
        eid = e["entity_id"]
        d = eid.split(".", 1)[0]
        if domain and d != domain:
            continue
        name = e.get("attributes", {}).get("friendly_name", eid)
        if q and q not in eid.lower() and q not in name.lower():
            continue
        if d in ("update", "persistent_notification", "zone", "sun", "conversation", "tts", "event", "image") and not domain:
            continue
        item = {"id": eid, "name": name, "zustand": e["state"]}
        unit = e.get("attributes", {}).get("unit_of_measurement")
        if unit:
            item["einheit"] = unit
        if d == "light" and e["state"] == "on" and e["attributes"].get("brightness") is not None:
            item["helligkeit_%"] = round(e["attributes"]["brightness"] / 2.55)
        out.append(item)
    return {"anzahl": len(out), "geräte": out[:80]}


def ha_call(domain, service, entity_id=None, data=None):
    if not re.fullmatch(r"[a-z_]+", str(domain)) or not re.fullmatch(r"[a-z_]+", str(service)):
        raise RuntimeError("Ungültiger Dienst.")
    body = dict(data or {})
    if entity_id:
        body["entity_id"] = entity_id
    js = _ha("POST", f"/api/services/{domain}/{service}", body)
    changed = [f"{s['entity_id']} → {s['state']}" for s in (js or [])][:10]
    return {"ausgeführt": f"{domain}.{service}", "geändert": changed or "ok"}


def _ha_test(c):
    js = _ha("GET", "/api/config", c=c)
    return f"Verbunden mit „{js.get('location_name', 'Home Assistant')}“ (Version {js.get('version', '?')})."


# ================================================================ Steam
def steam_price(game):
    st, js, _ = _http("GET", "https://store.steampowered.com/api/storesearch/?" + urllib.parse.urlencode(
        {"term": game, "cc": "DE", "l": "german"}))
    items = (js or {}).get("items") or []
    if not items:
        return f"Kein Spiel '{game}' im Steam-Shop gefunden."
    ids = ",".join(str(i["id"]) for i in items[:3])
    st, det, _ = _http("GET", "https://store.steampowered.com/api/appdetails?" + urllib.parse.urlencode(
        {"appids": ids, "cc": "de", "filters": "price_overview"}))
    out = []
    for i in items[:3]:
        po = (((det or {}).get(str(i["id"])) or {}).get("data") or {}) if isinstance((det or {}).get(str(i["id"])), dict) else {}
        po = po.get("price_overview") if isinstance(po, dict) else None
        out.append({"spiel": i["name"], "preis": po["final_formatted"] if po else ("kostenlos" if not i.get("price") else "?"),
                    "normalpreis": po["initial_formatted"] if po and po.get("discount_percent") else None,
                    "rabatt_%": po["discount_percent"] if po else 0, "link": f"https://store.steampowered.com/app/{i['id']}"})
    return out


def _steam_id(c):
    sid = str(c.get("steam_id") or "").strip()
    sid = re.sub(r"^https?://steamcommunity\.com/(id|profiles)/", "", sid).strip("/")
    if re.fullmatch(r"\d{17}", sid):
        return sid
    st, js, _ = _http("GET", "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?" + urllib.parse.urlencode(
        {"key": c.get("api_key"), "vanityurl": sid}))
    r = (js or {}).get("response", {})
    if r.get("success") != 1:
        raise RuntimeError("Steam-Profil nicht gefunden (Profilname oder SteamID64 prüfen).")
    return r["steamid"]


def steam_me():
    c = conf("steam")
    if not c.get("api_key") or not c.get("steam_id"):
        raise RuntimeError("Für dein Profil brauche ich Steam-API-Key und Profil (Apps → Steam). Preise gehen auch ohne.")
    sid, key = _steam_id(c), c["api_key"]
    base = "https://api.steampowered.com"
    _, summ, _ = _http("GET", f"{base}/ISteamUser/GetPlayerSummaries/v2/?key={key}&steamids={sid}")
    _, rec, _ = _http("GET", f"{base}/IPlayerService/GetRecentlyPlayedGames/v1/?key={key}&steamid={sid}&count=8")
    _, own, _ = _http("GET", f"{base}/IPlayerService/GetOwnedGames/v1/?key={key}&steamid={sid}&include_appinfo=1")
    p = ((summ or {}).get("response", {}).get("players") or [{}])[0]
    games = (own or {}).get("response", {}).get("games", [])
    top = sorted(games, key=lambda g: -g.get("playtime_forever", 0))[:10]
    return {"name": p.get("personaname"), "spielt_gerade": p.get("gameextrainfo"),
            "spiele_gesamt": len(games), "stunden_gesamt": round(sum(g.get("playtime_forever", 0) for g in games) / 60),
            "zuletzt_gespielt": [{"spiel": g["name"], "stunden_2_wochen": round(g.get("playtime_2weeks", 0) / 60, 1),
                                  "stunden_gesamt": round(g.get("playtime_forever", 0) / 60)}
                                 for g in (rec or {}).get("response", {}).get("games", [])],
            "meistgespielt": [{"spiel": g["name"], "stunden": round(g.get("playtime_forever", 0) / 60)} for g in top],
            "hinweis": None if games else "Spieleliste leer – evtl. ist dein Steam-Profil/Spieldetails auf privat gestellt."}


def _steam_test(c):
    if not c.get("api_key"):
        return "Preise gehen ohne Key. Für Profil/Spielzeit API-Key eintragen."
    sid = _steam_id(c)
    _, summ, _ = _http("GET", f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={c['api_key']}&steamids={sid}")
    p = ((summ or {}).get("response", {}).get("players") or [None])[0]
    if not p:
        raise RuntimeError("API-Key oder Profil ungültig.")
    return f"Verbunden als {p['personaname']}."


# ================================================================ Spotify (OAuth PKCE)
SP_SCOPES = ("user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-recently-played "
             "user-top-read playlist-read-private user-library-read user-library-modify")
_pending = {}


def spotify_redirect():
    return base_url().rstrip("/") + "/callback/spotify"


def spotify_auth_url():
    cid = conf("spotify").get("client_id")
    if not cid:
        raise RuntimeError("Zuerst die Client-ID eintragen und speichern.")
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(16)
    _pending.clear()
    _pending[state] = (verifier, time.time())
    return "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": cid, "response_type": "code", "redirect_uri": spotify_redirect(), "code_challenge_method": "S256",
        "code_challenge": challenge, "scope": SP_SCOPES, "state": state})


def spotify_callback(code, state):
    item = _pending.pop(state or "", None)
    if not item or time.time() - item[1] > 900:
        raise RuntimeError("Anmeldung abgelaufen oder ungültig. Bitte in Lumen nochmal auf 'Mit Spotify anmelden' klicken.")
    st, js, _ = _http("POST", "https://accounts.spotify.com/api/token", form={
        "grant_type": "authorization_code", "code": code, "redirect_uri": spotify_redirect(),
        "client_id": conf("spotify").get("client_id"), "code_verifier": item[0]})
    if st != 200 or not js:
        raise RuntimeError(f"Spotify-Anmeldung fehlgeschlagen: {(js or {}).get('error_description', st)}")
    save_app("spotify", {"access_token": js["access_token"], "refresh_token": js.get("refresh_token"),
                         "expires_at": time.time() + js.get("expires_in", 3600) - 60})
    try:
        me = _sp("GET", "/me")
        save_app("spotify", {"user": me.get("display_name") or me.get("id"), "premium": me.get("product") == "premium"})
    except Exception:
        pass
    return True


def _sp_token():
    c = conf("spotify")
    if not c.get("refresh_token"):
        raise RuntimeError("Spotify nicht verbunden (Apps → Spotify → Mit Spotify anmelden).")
    if time.time() < float(c.get("expires_at") or 0) and c.get("access_token"):
        return c["access_token"]
    st, js, _ = _http("POST", "https://accounts.spotify.com/api/token", form={
        "grant_type": "refresh_token", "refresh_token": c["refresh_token"], "client_id": c.get("client_id")})
    if st != 200 or not js:
        raise RuntimeError("Spotify-Anmeldung abgelaufen. Bitte in den Apps neu anmelden.")
    patch = {"access_token": js["access_token"], "expires_at": time.time() + js.get("expires_in", 3600) - 60}
    if js.get("refresh_token"):
        patch["refresh_token"] = js["refresh_token"]
    save_app("spotify", patch)
    return js["access_token"]


def _sp(method, path, params=None, body=None):
    url = "https://api.spotify.com/v1" + path + ("?" + urllib.parse.urlencode(params) if params else "")
    st, js, _ = _http(method, url, json_body=body, headers={"Authorization": f"Bearer {_sp_token()}"},
                      data=b"" if method in ("PUT", "POST") and body is None else None)
    if st == 204 or (st in (200, 202) and js is None):
        return None
    if st == 404 and "device" in json.dumps(js or {}).lower() or st == 404 and path.startswith("/me/player"):
        raise RuntimeError("Kein aktives Spotify-Gerät. Öffne Spotify auf PC oder Handy und spiel kurz etwas ab.")
    if st == 403:
        reason = ((js or {}).get("error") or {}).get("reason", "")
        if reason == "PREMIUM_REQUIRED" or "premium" in json.dumps(js or {}).lower():
            raise RuntimeError("Für die Steuerung braucht Spotify ein Premium-Konto.")
        raise RuntimeError(f"Spotify verweigert: {((js or {}).get('error') or {}).get('message', '')}")
    if st == 401:
        save_app("spotify", {"expires_at": 0})
        raise RuntimeError("Spotify-Anmeldung abgelaufen – nochmal versuchen.")
    if st >= 400:
        raise RuntimeError(f"Spotify-Fehler {st}: {((js or {}).get('error') or {}).get('message', '')}")
    return js


def _fmt_track(t):
    return f"{t['name']} – {', '.join(a['name'] for a in t.get('artists', []))}"


def spotify_now():
    js = _sp("GET", "/me/player")
    if not js or not js.get("item"):
        return {"läuft": False, "hinweis": "Gerade läuft nichts."}
    it = js["item"]
    imgs = (it.get("album") or {}).get("images") or []
    return {"läuft": js.get("is_playing"), "titel": it["name"], "künstler": ", ".join(a["name"] for a in it.get("artists", [])),
            "album": (it.get("album") or {}).get("name"), "cover": imgs[-2]["url"] if len(imgs) > 1 else (imgs[0]["url"] if imgs else None),
            "position_s": round((js.get("progress_ms") or 0) / 1000), "länge_s": round((it.get("duration_ms") or 0) / 1000),
            "gerät": (js.get("device") or {}).get("name"), "lautstärke": (js.get("device") or {}).get("volume_percent"),
            "shuffle": js.get("shuffle_state"), "id": it.get("id")}


def spotify(action, query=None, kind="track", volume=None):
    a = action
    if a == "now":
        return spotify_now()
    if a in ("play", "pause"):
        _sp("PUT", f"/me/player/{a}")
        return "Wiedergabe fortgesetzt." if a == "play" else "Pausiert."
    if a in ("next", "previous"):
        _sp("POST", f"/me/player/{a}")
        time.sleep(0.4)
        n = spotify_now()
        return f"Jetzt: {n.get('titel')} – {n.get('künstler')}" if n.get("titel") else "Gewechselt."
    if a == "volume":
        v = max(0, min(int(volume if volume is not None else 50), 100))
        _sp("PUT", "/me/player/volume", {"volume_percent": v})
        return f"Lautstärke {v} %."
    if a == "shuffle":
        cur = (_sp("GET", "/me/player") or {}).get("shuffle_state")
        _sp("PUT", "/me/player/shuffle", {"state": "false" if cur else "true"})
        return "Shuffle " + ("aus." if cur else "an.")
    if a == "like":
        n = spotify_now()
        if not n.get("id"):
            return "Gerade läuft nichts."
        _sp("PUT", "/me/tracks", {"ids": n["id"]})
        return f"„{n['titel']}“ zu deinen Lieblingssongs hinzugefügt."
    if a in ("search_play", "queue"):
        if not query:
            raise RuntimeError("Was soll ich suchen?")
        kind = kind if kind in ("track", "playlist", "album", "artist") else "track"
        if a == "queue":
            kind = "track"
        res = _sp("GET", "/search", {"q": query, "type": kind, "limit": 1, "market": "from_token"})
        items = ((res or {}).get(kind + "s") or {}).get("items") or []
        items = [i for i in items if i]
        if not items:
            return f"Nichts gefunden für '{query}'."
        it = items[0]
        if a == "queue":
            _sp("POST", "/me/player/queue", {"uri": it["uri"]})
            return f"In die Warteschlange: {_fmt_track(it)}"
        body = {"uris": [it["uri"]]} if kind == "track" else {"context_uri": it["uri"]}
        try:
            _sp("PUT", "/me/player/play", body=body)
        except RuntimeError as e:
            if "Kein aktives" not in str(e):
                raise
            devs = (_sp("GET", "/me/player/devices") or {}).get("devices") or []
            if not devs:
                raise
            _sp("PUT", "/me/player/play", {"device_id": devs[0]["id"]}, body=body)
        label = _fmt_track(it) if kind == "track" else f"{it['name']} ({ {'playlist': 'Playlist', 'album': 'Album', 'artist': 'Künstler'}[kind]})"
        return f"Spielt: {label}"
    if a == "devices":
        devs = (_sp("GET", "/me/player/devices") or {}).get("devices") or []
        return [{"gerät": d["name"], "typ": d["type"], "aktiv": d["is_active"], "lautstärke": d.get("volume_percent")} for d in devs] \
            or "Kein Gerät online – öffne Spotify irgendwo."
    if a == "recent":
        js = _sp("GET", "/me/player/recently-played", {"limit": 15})
        return [_fmt_track(i["track"]) for i in (js or {}).get("items", [])]
    if a == "top":
        tr = _sp("GET", "/me/top/tracks", {"limit": 10, "time_range": "short_term"})
        ar = _sp("GET", "/me/top/artists", {"limit": 10, "time_range": "short_term"})
        return {"top_songs_4_wochen": [_fmt_track(t) for t in (tr or {}).get("items", [])],
                "top_künstler_4_wochen": [x["name"] for x in (ar or {}).get("items", [])]}
    if a == "playlists":
        js = _sp("GET", "/me/playlists", {"limit": 40})
        return [{"name": p["name"], "songs": (p.get("tracks") or {}).get("total")} for p in (js or {}).get("items", []) if p]
    raise RuntimeError("Unbekannte Aktion.")


def _spotify_test(c):
    if not c.get("refresh_token"):
        return "Client-ID gespeichert. Jetzt auf 'Mit Spotify anmelden' klicken."
    me = _sp("GET", "/me")
    save_app("spotify", {"user": me.get("display_name") or me.get("id"), "premium": me.get("product") == "premium"})
    return f"Verbunden als {me.get('display_name') or me.get('id')}" + ("" if me.get("product") == "premium" else
                                                                         " (ohne Premium: nur Infos, keine Steuerung)")


# ================================================================ Krypto (nur lesen)
SOL_RPC = "https://api.mainnet-beta.solana.com"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_SOL = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_SOL = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
EVM = {
    "Ethereum": {"rpc": "https://ethereum-rpc.publicnode.com", "native": "ETH", "cg": "ethereum", "scan": "https://etherscan.io/address/",
                 "tokens": {"USDC": ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6), "USDT": ("0xdAC17F958D2ee523a2206206994597C13D831ec7", 6)}},
    "Base": {"rpc": "https://base-rpc.publicnode.com", "native": "ETH", "cg": "ethereum", "scan": "https://basescan.org/address/",
             "tokens": {"USDC": ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6)}},
    "Polygon": {"rpc": "https://polygon-bor-rpc.publicnode.com", "native": "POL", "cg": "polygon-ecosystem-token",
                "scan": "https://polygonscan.com/address/",
                "tokens": {"USDC": ("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", 6)}},
}
CG_IDS = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana", "pol": "polygon-ecosystem-token", "matic": "polygon-ecosystem-token",
          "usdc": "usd-coin", "usdt": "tether", "bonk": "bonk", "jup": "jupiter-exchange-solana", "doge": "dogecoin",
          "xrp": "ripple", "ada": "cardano", "bnb": "binancecoin", "sui": "sui", "avax": "avalanche-2", "link": "chainlink",
          "dot": "polkadot", "ltc": "litecoin", "trx": "tron", "ton": "the-open-network", "pepe": "pepe", "shib": "shiba-inu",
          "wif": "dogwifcoin", "ray": "raydium", "pyth": "pyth-network", "render": "render-token", "hnt": "helium"}
B58 = r"[1-9A-HJ-NP-Za-km-z]"


def chain_of(addr):
    a = addr.strip()
    m = re.match(r"^(sol|solana|btc|bitcoin|eth|evm):(.+)$", a, re.I)
    if m:
        k = m.group(1).lower()
        return {"sol": "solana", "solana": "solana", "btc": "bitcoin", "bitcoin": "bitcoin"}.get(k, "evm"), m.group(2).strip()
    if re.fullmatch(r"0x[0-9a-fA-F]{40}", a):
        return "evm", a
    if re.fullmatch(r"bc1[0-9a-z]{25,90}", a):
        return "bitcoin", a
    if re.fullmatch(B58 + r"{40,44}", a):
        return "solana", a
    if re.fullmatch(r"[13]" + B58 + r"{25,34}", a):
        return "bitcoin", a
    if re.fullmatch(B58 + r"{32,39}", a):
        return "solana", a
    raise RuntimeError(f"Adresse '{a[:12]}…' nicht erkannt (Solana, Ethereum/Base/Polygon oder Bitcoin).")


def _cg_prices(ids, cur="eur"):
    if not ids:
        return {}
    st, js, _ = _http("GET", "https://api.coingecko.com/api/v3/simple/price?" + urllib.parse.urlencode(
        {"ids": ",".join(sorted(set(ids))), "vs_currencies": f"{cur},usd", "include_24hr_change": "true"}))
    if st == 429:
        raise RuntimeError("Kursdienst kurz überlastet – gleich nochmal versuchen.")
    return js or {}


def _sol_rpc(method, params):
    rpc = conf("crypto").get("solana_rpc") or SOL_RPC
    st, js, _ = _http("POST", rpc, json_body={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    if not js or "error" in js:
        raise RuntimeError(f"Solana: {((js or {}).get('error') or {}).get('message', st)}")
    return js["result"]


def _jup_prices(mints):
    out = {}
    mints = list(dict.fromkeys(mints))
    for i in range(0, len(mints), 50):
        try:
            st, js, _ = _http("GET", "https://lite-api.jup.ag/price/v3?ids=" + ",".join(mints[i:i + 50]))
            for k, v in (js or {}).items():
                if isinstance(v, dict) and v.get("usdPrice") is not None:
                    out[k] = float(v["usdPrice"])
        except Exception:
            pass
    return out


def _jup_meta(mints):
    meta = {}
    try:
        st, js, _ = _http("GET", "https://lite-api.jup.ag/tokens/v2/search?query=" + ",".join(mints[:100]))
        for t in js or []:
            meta[t.get("id")] = {"symbol": t.get("symbol"), "name": t.get("name"), "verified": t.get("isVerified")}
    except Exception:
        pass
    return meta


def _solana(addr, eur_rate):
    lamports = _sol_rpc("getBalance", [addr])["value"]
    holdings = [{"token": "SOL", "menge": lamports / 1e9, "mint": SOL_MINT}]
    for prog in ("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"):
        try:
            res = _sol_rpc("getTokenAccountsByOwner", [addr, {"programId": prog}, {"encoding": "jsonParsed"}])
            for acc in res["value"]:
                info = acc["account"]["data"]["parsed"]["info"]
                amt = info["tokenAmount"].get("uiAmount") or 0
                if amt > 0:
                    holdings.append({"token": None, "menge": amt, "mint": info["mint"]})
        except Exception:
            pass
    prices = _jup_prices([h["mint"] for h in holdings])
    meta = _jup_meta([h["mint"] for h in holdings if h["token"] is None])
    out, hidden = [], 0
    for h in holdings:
        m = meta.get(h["mint"], {})
        sym = h["token"] or m.get("symbol") or (h["mint"][:4] + "…" + h["mint"][-4:])
        usd = prices.get(h["mint"])
        val = h["menge"] * usd * eur_rate if usd is not None else None
        if h["token"] is None and (val is None or val < 0.01):
            hidden += 1
            continue
        out.append({"token": sym, "menge": round(h["menge"], 6), "wert_eur": round(val, 2) if val is not None else None,
                    "verifiziert": m.get("verified")})
    return out, hidden


def _evm(addr, prices, eur_key):
    out = []
    for chain, c in EVM.items():
        try:
            st, js, _ = _http("POST", c["rpc"], json_body={"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [addr, "latest"]})
            bal = int((js or {}).get("result") or "0x0", 16) / 1e18
            if bal > 0:
                p = prices.get(c["cg"], {}).get(eur_key)
                out.append({"chain": chain, "token": c["native"], "menge": round(bal, 6), "wert_eur": round(bal * p, 2) if p else None})
            for sym, (contract, dec) in c["tokens"].items():
                data = "0x70a08231" + addr[2:].lower().rjust(64, "0")
                st, js, _ = _http("POST", c["rpc"], json_body={"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                                                               "params": [{"to": contract, "data": data}, "latest"]})
                amt = int((js or {}).get("result") or "0x0", 16) / 10 ** dec
                if amt > 0:
                    p = prices.get("usd-coin" if sym == "USDC" else "tether", {}).get(eur_key)
                    out.append({"chain": chain, "token": sym, "menge": round(amt, 2), "wert_eur": round(amt * p, 2) if p else None})
        except Exception as e:
            out.append({"chain": chain, "fehler": str(e)[:80]})
    return out


def _btc(addr, prices, eur_key):
    st, js, _ = _http("GET", f"https://mempool.space/api/address/{addr}")
    if st != 200 or not js:
        raise RuntimeError("Bitcoin-Adresse nicht abrufbar.")
    sats = (js["chain_stats"]["funded_txo_sum"] - js["chain_stats"]["spent_txo_sum"] +
            js["mempool_stats"]["funded_txo_sum"] - js["mempool_stats"]["spent_txo_sum"])
    p = prices.get("bitcoin", {}).get(eur_key)
    return [{"token": "BTC", "menge": sats / 1e8, "wert_eur": round(sats / 1e8 * p, 2) if p else None}]


def crypto_portfolio():
    wallets = _lines(conf("crypto").get("wallets"))
    if not wallets:
        raise RuntimeError("Keine Wallet-Adressen hinterlegt (Apps → Krypto). Nur die ÖFFENTLICHE Adresse, nie die Seed-Phrase!")
    prices = _cg_prices(["solana", "ethereum", "bitcoin", "polygon-ecosystem-token", "usd-coin", "tether"])
    eur_rate = (prices.get("solana", {}).get("eur") or 0) / (prices.get("solana", {}).get("usd") or 1) or 0.92
    result, total = [], 0.0
    for name, raw in wallets.items():
        try:
            kind, addr = chain_of(raw)
            if kind == "solana":
                holdings, hidden = _solana(addr, eur_rate)
                w = {"wallet": name, "netz": "Solana", "adresse": addr[:4] + "…" + addr[-4:], "bestände": holdings,
                     "explorer": f"https://solscan.io/account/{addr}"}
                if hidden:
                    w["ausgeblendet"] = f"{hidden} Token ohne Wert (oft Spam-Airdrops – nicht anklicken/handeln!)"
            elif kind == "evm":
                w = {"wallet": name, "netz": "Ethereum/Base/Polygon", "adresse": addr[:6] + "…" + addr[-4:],
                     "bestände": _evm(addr, prices, "eur"), "explorer": EVM["Ethereum"]["scan"] + addr,
                     "hinweis": "Nur Haupt-Coins und USDC/USDT; weitere Tokens im Explorer."}
            else:
                w = {"wallet": name, "netz": "Bitcoin", "adresse": addr[:6] + "…" + addr[-4:], "bestände": _btc(addr, prices, "eur"),
                     "explorer": f"https://mempool.space/address/{addr}"}
            w["summe_eur"] = round(sum(h.get("wert_eur") or 0 for h in w["bestände"]), 2)
            total += w["summe_eur"]
            result.append(w)
        except Exception as e:
            result.append({"wallet": name, "fehler": str(e)})
    ch = {k: round(v.get("eur_24h_change") or 0, 1) for k, v in prices.items() if k in ("solana", "ethereum", "bitcoin")}
    return {"gesamt_eur": round(total, 2), "wallets": result, "24h_änderung_%": ch,
            "hinweis": "Nur Lesezugriff über öffentliche Adressen. Lumen kann nichts senden."}


def crypto_price(coins):
    ids = []
    for c in (coins if isinstance(coins, list) else re.split(r"[,\s]+", str(coins or ""))):
        c = c.strip().lower()
        if not c:
            continue
        if c in CG_IDS:
            ids.append(CG_IDS[c])
        else:
            st, js, _ = _http("GET", "https://api.coingecko.com/api/v3/search?query=" + urllib.parse.quote(c))
            hit = ((js or {}).get("coins") or [None])[0]
            if hit:
                ids.append(hit["id"])
    if not ids:
        raise RuntimeError("Welche Coins? (z. B. BTC, ETH, SOL)")
    pr = _cg_prices(ids[:20])
    return [{"coin": i, "eur": v.get("eur"), "usd": v.get("usd"), "24h_%": round(v.get("eur_24h_change") or 0, 2)}
            for i, v in pr.items()]


def crypto_transactions(wallet=None):
    wallets = _lines(conf("crypto").get("wallets"))
    if not wallets:
        raise RuntimeError("Keine Wallets hinterlegt.")
    name = next((k for k in wallets if k.lower() == str(wallet or "").lower()), None) or list(wallets)[0]
    kind, addr = chain_of(wallets[name])
    if kind == "solana":
        sigs = _sol_rpc("getSignaturesForAddress", [addr, {"limit": 12}])
        return {"wallet": name, "transaktionen": [{"zeit": datetime.fromtimestamp(s["blockTime"]).strftime("%d.%m. %H:%M") if s.get("blockTime") else "?",
                                                   "ok": s.get("err") is None, "link": f"https://solscan.io/tx/{s['signature']}"} for s in sigs],
                "hinweis": "Details (Beträge, Gegenseite) im Link."}
    if kind == "bitcoin":
        st, js, _ = _http("GET", f"https://mempool.space/api/address/{addr}/txs")
        out = []
        for tx in (js or [])[:12]:
            recv = sum(v["value"] for v in tx["vout"] if v.get("scriptpubkey_address") == addr)
            sent = sum(v["prevout"]["value"] for v in tx["vin"] if (v.get("prevout") or {}).get("scriptpubkey_address") == addr)
            t = tx.get("status", {}).get("block_time")
            out.append({"zeit": datetime.fromtimestamp(t).strftime("%d.%m. %H:%M") if t else "unbestätigt",
                        "btc": round((recv - sent) / 1e8, 8), "link": f"https://mempool.space/tx/{tx['txid']}"})
        return {"wallet": name, "transaktionen": out}
    return {"wallet": name, "hinweis": "Für Ethereum/Base/Polygon den Explorer nutzen.",
            "links": {k: c["scan"] + addr for k, c in EVM.items()}}


def payment_request(recipient, amount, token="SOL", label="", message=""):
    """Erstellt einen Zahlungs-QR (Solana Pay / Bitcoin). Lumen sendet NICHTS – bestätigt wird in Phantom."""
    kind, addr = chain_of(recipient)
    try:
        amt = float(str(amount).replace(",", "."))
    except ValueError:
        raise RuntimeError("Ungültiger Betrag.")
    if amt <= 0 or amt > 1e9:
        raise RuntimeError("Ungültiger Betrag.")
    tok = str(token or "SOL").upper()
    if kind == "solana":
        params = {"amount": f"{amt:.9f}".rstrip("0").rstrip(".")}
        if tok in ("USDC", "USDT"):
            params["spl-token"] = USDC_SOL if tok == "USDC" else USDT_SOL
        elif tok != "SOL":
            raise RuntimeError("Für Solana gehen SOL, USDC und USDT.")
        if label:
            params["label"] = str(label)[:60]
        if message:
            params["message"] = str(message)[:120]
        uri = f"solana:{addr}?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        app = "Phantom (oder jede Solana-Wallet)"
    elif kind == "bitcoin":
        uri = f"bitcoin:{addr}?amount={amt:.8f}".rstrip("0").rstrip(".")
        tok, app = "BTC", "Phantom oder jede Bitcoin-Wallet"
    else:
        raise RuntimeError("Zahlungs-QR gibt es für Solana und Bitcoin. Für Ethereum die Adresse in Phantom einfügen.")
    res = {"empfänger": addr, "betrag": f"{amt:g} {tok}", "zahlungslink": uri,
           "so_gehts": f"QR-Code mit {app} am Handy scannen, Empfänger und Betrag PRÜFEN und in der Wallet bestätigen. "
                       "Lumen selbst kann nichts senden."}
    try:
        import qrcode
        qr = qrcode.QRCode(border=2, box_size=8)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        buf = io.BytesIO()
        img.save(buf, "PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"__image__": b64, "__thumb__": b64, "__image_type__": "image/png",
                "text": json.dumps(res, ensure_ascii=False)}
    except ImportError:
        res["hinweis"] = "QR-Code braucht 'pip install qrcode' – der Link funktioniert trotzdem in Phantom."
        return res


def _crypto_test(c):
    w = _lines(c.get("wallets"))
    if not w:
        raise RuntimeError("Mindestens eine öffentliche Adresse eintragen: name = adresse")
    for k, v in w.items():
        if looks_like_secret(v) or len(v.split()) > 1:
            raise RuntimeError(f"'{k}' sieht nicht wie eine öffentliche Adresse aus. NIE Seed-Phrase oder privaten Schlüssel eintragen!")
        chain_of(v)
    p = crypto_portfolio()
    return f"{len(w)} Wallet(s) gelesen – Gesamtwert ca. {p['gesamt_eur']:.2f} €."


# ================================================================ Registry
APPS = [
    {"id": "crypto", "name": "Krypto-Wallets", "color": "#AB9FF2", "desc": "Phantom, Solflare, MetaMask, Bitcoin – Kontostand, Tokens, Wert, Transaktionen. Nur lesen.",
     "help": "In Phantom oben auf deinen Account → Adresse kopieren (Solana, Ethereum oder Bitcoin). NUR die öffentliche Adresse – "
             "niemals Seed-Phrase oder privaten Schlüssel! Zahlungen erstellt Lumen als QR-Code, du bestätigst in Phantom.",
     "fields": [{"key": "wallets", "label": "Öffentliche Adressen (name = adresse)", "type": "textarea",
                 "placeholder": "phantom-sol = 7xKX…AsU\nphantom-eth = 0x12…ab"},
                {"key": "solana_rpc", "label": "Eigener Solana-RPC (optional, z. B. Helius – schneller)", "type": "secret"}],
     "required": ["wallets"], "test": _crypto_test},
    {"id": "spotify", "name": "Spotify", "color": "#1DB954", "desc": "Was läuft, Songs/Playlists abspielen, Lautstärke, Warteschlange, Lieblingssongs.",
     "help": "1. developer.spotify.com/dashboard → Create app. 2. Redirect URI genau so eintragen: {redirect} 3. 'Web API' anhaken, "
             "speichern. 4. Client ID hier einfügen, speichern, dann 'Mit Spotify anmelden'. Steuerung braucht Premium.",
     "fields": [{"key": "client_id", "label": "Client ID", "type": "text"}],
     "required": ["client_id", "refresh_token"], "oauth": True, "test": _spotify_test},
    {"id": "discord", "name": "Discord", "color": "#5865F2", "desc": "Nachrichten in deine Discord-Kanäle senden (z. B. Server-Updates, Ankündigungen).",
     "help": "Discord → Server-Einstellungen → Integrationen → Webhooks → Neuer Webhook → Kanal wählen → URL kopieren.",
     "fields": [{"key": "webhooks", "label": "Webhooks (kanal = url)", "type": "textarea",
                 "placeholder": "allgemein = https://discord.com/api/webhooks/…"}],
     "required": ["webhooks"], "test": _discord_test},
    {"id": "telegram", "name": "Telegram", "color": "#26A5E4", "desc": "Lumen schickt dir Nachrichten und Dateien aufs Handy.",
     "help": "In Telegram @BotFather öffnen → /newbot → Namen wählen → Token kopieren und hier einfügen. Dann deinem neuen Bot "
             "/start schreiben und 'Chat-ID finden' klicken.",
     "fields": [{"key": "bot_token", "label": "Bot-Token", "type": "secret"}, {"key": "chat_id", "label": "Deine Chat-ID", "type": "text"}],
     "required": ["bot_token", "chat_id"], "test": _telegram_test},
    {"id": "github", "name": "GitHub", "color": "#8B949E", "desc": "Repos, Issues, Pull Requests, Actions-Status, Benachrichtigungen, Issues erstellen.",
     "help": "github.com → Settings → Developer settings → Personal access tokens → Fine-grained → Repos wählen, Rechte: "
             "Issues, Pull requests, Actions (lesen; Issues schreiben für 'erstellen').",
     "fields": [{"key": "token", "label": "Personal Access Token", "type": "secret"}], "required": ["token"], "test": _github_test},
    {"id": "homeassistant", "name": "Home Assistant", "color": "#41BDF5", "desc": "Licht, Steckdosen, Heizung, Sensoren, Szenen steuern.",
     "help": "In Home Assistant: Profil (unten links) → Sicherheit → Langlebige Zugangstoken → Token erstellen.",
     "fields": [{"key": "url", "label": "Adresse", "type": "text", "placeholder": "http://homeassistant.local:8123"},
                {"key": "token", "label": "Langlebiges Zugangstoken", "type": "secret"}],
     "required": ["url", "token"], "test": _ha_test},
    {"id": "steam", "name": "Steam", "color": "#66C0F4", "desc": "Spielpreise und Rabatte (ohne Key), dein Profil und deine Spielzeit (mit Key).",
     "help": "API-Key: steamcommunity.com/dev/apikey (Domain egal, z. B. localhost). Profil: dein Profilname aus der URL oder SteamID64. "
             "Spieldetails im Profil auf 'öffentlich' stellen.",
     "fields": [{"key": "api_key", "label": "Steam Web-API-Key (optional)", "type": "secret"},
                {"key": "steam_id", "label": "Profilname oder SteamID64", "type": "text"}],
     "required": [], "always": True, "test": _steam_test},
    {"id": "weather", "name": "Wetter", "color": "#F5B83D", "desc": "Aktuelles Wetter und Vorhersage – ohne Key (Open-Meteo).",
     "help": "Einfach deinen Ort eintragen. Lumen zeigt das Wetter dann auch oben rechts an.",
     "fields": [{"key": "city", "label": "Dein Ort", "type": "text", "placeholder": "Berlin"}], "required": ["city"],
     "always": True, "test": lambda c: (lambda w: f"{w['ort']}: {w['jetzt']['temperatur']} °C, {w['jetzt']['wetter']}")(weather(c.get("city"), 1))},
    {"id": "calendar", "name": "Kalender", "color": "#E5484D",
     "desc": "Termine lesen UND eintragen: Lumen-Kalender, Google, Nextcloud, iCloud, Outlook (Lesen per iCal-Link).",
     "help": "Ohne Einrichtung trägt Lumen Termine in den Lumen-Kalender ein (lokal, als .ics importierbar). Zum Eintragen in deinen "
             "echten Kalender: ① Nextcloud/iCloud/mailbox.org/Posteo/Fastmail: CalDAV-Adresse, Benutzer und App-Passwort (iCloud: "
             "appleid.apple.com → App-Passwort, Adresse https://caldav.icloud.com; Nextcloud: https://deine-cloud/remote.php/dav). "
             "② Google: console.cloud.google.com → Projekt → 'Google Calendar API' aktivieren → OAuth-Zustimmung (extern, dich als "
             "Testnutzer) → Anmeldedaten → OAuth-Client-ID 'Desktop-App' → ID und Secret hier eintragen → 'Mit Google anmelden'. "
             "③ Nur lesen (z. B. Outlook): iCal-Link eintragen – der Link ist geheim.",
     "fields": [{"key": "caldav_url", "label": "CalDAV-Adresse (optional)", "type": "text", "placeholder": "https://caldav.icloud.com"},
                {"key": "caldav_user", "label": "CalDAV-Benutzer", "type": "text"},
                {"key": "caldav_password", "label": "CalDAV-App-Passwort", "type": "secret"},
                {"key": "caldav_calendar", "label": "In welchen Kalender eintragen (Name, leer = erster)", "type": "text"},
                {"key": "google_client_id", "label": "Google Client-ID (optional)", "type": "text"},
                {"key": "google_client_secret", "label": "Google Client-Secret", "type": "secret"},
                {"key": "write_to", "label": "Neue Termine eintragen in: lumen / caldav / google (leer = automatisch)", "type": "text"},
                {"key": "calendars", "label": "Nur lesen: iCal-Links (name = link)", "type": "textarea",
                 "placeholder": "arbeit = https://outlook.office365.com/owa/calendar/…/calendar.ics"}],
     "required": [], "test": lambda c: _cal_test(c)},
]
APP_BY_ID = {a["id"]: a for a in APPS}


def _cal_test(c):
    import calendars
    parts = []
    if c.get("caldav_url"):
        cals = calendars.caldav_calendars()
        parts.append("CalDAV: " + ", ".join(x["name"] for x in cals))
    if c.get("google_refresh"):
        parts.append("Google verbunden" + (f" ({c.get('google_account')})" if c.get("google_account") else ""))
    elif c.get("google_client_id"):
        parts.append("Google: jetzt auf 'Mit Google anmelden' klicken")
    res = calendar_events(14)
    if res.get("fehler"):
        raise RuntimeError("; ".join(res["fehler"]))
    links = _lines(c.get("calendars"))
    if links:
        parts.append(f"{len(links)} iCal-Link(s)")
    return (" · ".join(parts) or "Lumen-Kalender (lokal)") + f" – {len(res['termine'])} Termine in den nächsten 14 Tagen. " + \
        f"Neue Termine landen in: {calendars.default_target()}."


def connected(app_id, c=None):
    a = APP_BY_ID[app_id]
    c = c if c is not None else conf(app_id)
    if app_id == "calendar":
        from pathlib import Path as _P
        return bool(_lines(c.get("calendars")) or (c.get("caldav_url") and c.get("caldav_user") and c.get("caldav_password"))
                    or c.get("google_refresh") or (_P.home() / ".lumen" / "calendar.json").exists())
    return all(str(c.get(k) or "").strip() for k in a["required"]) and (bool(a["required"]) or any(str(v).strip() for v in c.values()))


def public_view():
    out = []
    for a in APPS:
        c = conf(a["id"])
        fields = []
        for f in a["fields"]:
            v = str(c.get(f["key"]) or "")
            if f["type"] == "secret" and v:
                v = (v[:4] + "…" + v[-3:]) if len(v) > 10 else "gesetzt"
            fields.append({**f, "value": v})
        item = {k: a[k] for k in ("id", "name", "color", "desc")}
        item.update(help=a["help"].replace("{redirect}", spotify_redirect()), fields=fields, connected=connected(a["id"]),
                    oauth=bool(a.get("oauth")))
        if a["id"] == "calendar":
            item["account"] = c.get("google_account")
            item["google_ready"] = bool(c.get("google_client_id") and c.get("google_client_secret"))
            item["google_connected"] = bool(c.get("google_refresh"))
            item["help"] = item["help"] + " Weiterleitungs-URI (falls gefragt): " + base_url().rstrip("/") + "/callback/google"
        if a["id"] == "spotify":
            item["account"] = c.get("user")
            item["premium"] = c.get("premium")
            item["redirect"] = spotify_redirect()
        out.append(item)
    return out


def tools():
    """Werkzeuge nur für verbundene Apps (hält die Liste für die KI kurz)."""
    t = []
    if connected("crypto"):
        t += [
            dict(name="crypto_portfolio", fn=lambda a: crypto_portfolio(), label=lambda a: "Wallets gelesen",
                 description="Kontostände, Tokens und Wert (EUR) der eigenen Krypto-Wallets (Phantom & Co.). Nur lesen.", schema=S()),
            dict(name="crypto_transactions", fn=lambda a: crypto_transactions(a.get("wallet")), label=lambda a: "Transaktionen gelesen",
                 description="Letzte Transaktionen einer eigenen Wallet.", schema=S({"wallet": STR})),
            dict(name="crypto_payment_request", fn=lambda a: payment_request(a["recipient"], a["amount"], a.get("token", "SOL"),
                                                                              a.get("label", ""), a.get("message", "")),
                 label=lambda a: f"Zahlungs-QR: {a.get('amount')} {a.get('token', 'SOL')}",
                 description="Erstellt einen Zahlungs-QR-Code/Link (Solana Pay: SOL/USDC/USDT, oder Bitcoin) an einen Empfänger. "
                             "Lumen sendet NICHTS – der Nutzer scannt und bestätigt in Phantom.",
                 schema=S({"recipient": STR, "amount": {"type": "number"}, "token": STR, "label": STR, "message": STR},
                          ["recipient", "amount"])),
        ]
    t.append(dict(name="crypto_price", fn=lambda a: crypto_price(a["coins"]), label=lambda a: f"Kurse: {a.get('coins')}",
                  description="Aktuelle Kurse (EUR/USD, 24h-Änderung) für Coins, z. B. 'BTC, ETH, SOL, BONK'.",
                  schema=S({"coins": STR}, ["coins"])))
    if connected("spotify"):
        t.append(dict(name="spotify", fn=lambda a: spotify(a["action"], a.get("query"), a.get("kind", "track"), a.get("volume")),
                      label=lambda a: f"Spotify: {a.get('action')}" + (f" {a.get('query')}" if a.get("query") else ""),
                      description="Spotify steuern: now (was läuft), play, pause, next, previous, volume (0-100), shuffle, like "
                                  "(aktuellen Song speichern), search_play (query + kind: track|playlist|album|artist), queue (query), "
                                  "devices, recent, top, playlists.",
                      schema=S({"action": {"type": "string", "enum": ["now", "play", "pause", "next", "previous", "volume", "shuffle",
                                                                     "like", "search_play", "queue", "devices", "recent", "top", "playlists"]},
                                "query": STR, "kind": {"type": "string", "enum": ["track", "playlist", "album", "artist"]},
                                "volume": {"type": "integer"}}, ["action"])))
    if connected("discord"):
        t.append(dict(name="discord_send", fn=lambda a: discord_send(a.get("channel"), a["message"]),
                      label=lambda a: f"Discord #{a.get('channel') or ''}",
                      description="Sendet eine Nachricht per Webhook in einen Discord-Kanal des Nutzers. Kanäle: " +
                                  ", ".join(_lines(conf("discord").get("webhooks"))),
                      schema=S({"channel": STR, "message": STR}, ["message"]),
                      confirm=lambda a: (f"In Discord #{a.get('channel') or ''} posten", str(a.get("message", ""))[:600])))
    if connected("telegram"):
        t += [dict(name="telegram_send", fn=lambda a: telegram_send(a["text"]), label=lambda a: "An Telegram gesendet",
                   description="Schickt dem Nutzer eine Nachricht auf sein Handy (Telegram).", schema=S({"text": STR}, ["text"])),
              dict(name="telegram_send_file", fn=lambda a: telegram_send_file(a["path"], a.get("caption", "")),
                   label=lambda a: "Datei an Telegram gesendet",
                   description="Schickt dem Nutzer eine Datei vom PC aufs Handy (Telegram, max. 50 MB).",
                   schema=S({"path": STR, "caption": STR}, ["path"]),
                   confirm=lambda a: ("Datei an dein Telegram senden", str(a.get("path"))))]
    if connected("github"):
        t.append(dict(name="github", fn=lambda a: github(a["action"], a.get("repo"), a.get("title"), a.get("body")),
                      label=lambda a: f"GitHub: {a.get('action')} {a.get('repo') or ''}",
                      description="GitHub: repos, notifications, issues (repo), prs (repo), actions (repo), create_issue (repo, title, body).",
                      schema=S({"action": {"type": "string", "enum": ["repos", "notifications", "issues", "prs", "actions", "create_issue"]},
                                "repo": STR, "title": STR, "body": STR}, ["action"]),
                      confirm=lambda a: (f"GitHub-Issue in {a.get('repo')} erstellen", str(a.get("title"))) if a.get("action") == "create_issue" else None))
    if connected("homeassistant"):
        t += [dict(name="ha_states", fn=lambda a: ha_states(a.get("search"), a.get("domain")), label=lambda a: "Smart Home gelesen",
                   description="Listet Smart-Home-Geräte/Sensoren aus Home Assistant (search = Name, domain = light, switch, sensor, climate …).",
                   schema=S({"search": STR, "domain": STR})),
              dict(name="ha_call", fn=lambda a: ha_call(a["domain"], a["service"], a.get("entity_id"), a.get("data")),
                   label=lambda a: f"Smart Home: {a.get('domain')}.{a.get('service')} {a.get('entity_id') or ''}",
                   description="Steuert Home Assistant, z. B. light.turn_on (data: brightness_pct, rgb_color [r,g,b], color_temp_kelvin), "
                               "light.turn_off, switch.toggle, climate.set_temperature (data: temperature), scene.turn_on, script.turn_on. "
                               "Vorher mit ha_states die entity_id suchen.",
                   schema=S({"domain": STR, "service": STR, "entity_id": STR, "data": {"type": "object"}}, ["domain", "service"]),
                   confirm=lambda a: (f"Smart Home: {a.get('domain')}.{a.get('service')}", str(a.get("entity_id")))
                   if a.get("domain") in HA_RISKY else None)]
    t.append(dict(name="steam_price", fn=lambda a: steam_price(a["game"]), label=lambda a: f"Steam-Preis: {a.get('game')}",
                  description="Aktueller Steam-Preis und Rabatt eines Spiels (Deutschland).", schema=S({"game": STR}, ["game"])))
    if conf("steam").get("api_key"):
        t.append(dict(name="steam_me", fn=lambda a: steam_me(), label=lambda a: "Steam-Profil gelesen",
                      description="Eigenes Steam-Profil: was gerade gespielt wird, zuletzt gespielt, meistgespielt, Spielzeit.", schema=S()))
    t.append(dict(name="weather", fn=lambda a: weather(a.get("city"), a.get("days", 3)), label=lambda a: f"Wetter {a.get('city') or ''}",
                  description="Wetter jetzt und Vorhersage (bis 7 Tage). Ohne city: Ort des Nutzers.",
                  schema=S({"city": STR, "days": {"type": "integer"}})))
    if connected("calendar"):
        t.append(dict(name="calendar_events", fn=lambda a: calendar_events(a.get("days", 7)), label=lambda a: "Kalender gelesen",
                      description="Termine des Nutzers in den nächsten Tagen (days, Standard 7).", schema=S({"days": {"type": "integer"}})))
    return t


def test(app_id, values):
    a = APP_BY_ID.get(app_id)
    if not a:
        raise RuntimeError("Unbekannte App.")
    return a["test"](values)
