"""Lumen – Standort & Orte (über Telegram geteilt).

• Letzter geteilter Standort (nur der letzte, kein Verlauf; nach 24 h vergessen)
• Ortsname, Wetter vor Ort, Fahr-/Geh-Zeit (OpenStreetMap: Nominatim + OSRM)
• Orts-Erinnerungen: „wenn ich beim Supermarkt bin“, „wenn ich zuhause ankomme“, „wenn ich die Arbeit verlasse“
• „Zeit loszufahren“ zum nächsten Termin (bei Live-Standort)
• Was ist in der Nähe? (Apotheke, Supermarkt … über Overpass/OpenStreetMap)

Datenschutz: Es wird nur DEIN selbst geteilter Standort verwendet, lokal gespeichert, ohne Verlauf.
"""
import json
import math
import re
import secrets
import threading
import time
import urllib.parse
from pathlib import Path

import integrations as ig

DATA = Path.home() / ".lumen" / "orte.json"
LOCK = threading.RLock()
STALE_S = 24 * 3600          # danach wird der letzte Standort vergessen
FRESH_S = 20 * 60            # so lange gilt ein Standort als „aktuell“
get_events = lambda: []      # wird von lumen.py gesetzt: kommende Termine (mit "ort")

CATS = {  # Wort → (Anzeige, OSM-Filter)
    "supermarkt": ("Supermarkt", ['["shop"="supermarket"]', '["shop"="convenience"]']),
    "apotheke": ("Apotheke", ['["amenity"="pharmacy"]']),
    "bäckerei": ("Bäckerei", ['["shop"="bakery"]']),
    "drogerie": ("Drogerie", ['["shop"="chemist"]']),
    "tankstelle": ("Tankstelle", ['["amenity"="fuel"]']),
    "baumarkt": ("Baumarkt", ['["shop"="doityourself"]', '["shop"="hardware"]']),
    "post": ("Post/Paketshop", ['["amenity"="post_office"]', '["shop"="post"]']),
    "bank": ("Bank/Geldautomat", ['["amenity"="bank"]', '["amenity"="atm"]']),
    "geldautomat": ("Geldautomat", ['["amenity"="atm"]']),
    "arzt": ("Arzt", ['["amenity"="doctors"]']),
    "krankenhaus": ("Krankenhaus", ['["amenity"="hospital"]']),
    "café": ("Café", ['["amenity"="cafe"]']),
    "restaurant": ("Restaurant", ['["amenity"="restaurant"]']),
    "bahnhof": ("Bahnhof", ['["railway"="station"]']),
    "haltestelle": ("Haltestelle", ['["highway"="bus_stop"]', '["railway"="tram_stop"]', '["railway"="halt"]']),
    "parkplatz": ("Parkplatz", ['["amenity"="parking"]']),
    "ladestation": ("E-Ladestation", ['["amenity"="charging_station"]']),
    "toilette": ("Toilette", ['["amenity"="toilets"]']),
    "spielplatz": ("Spielplatz", ['["leisure"="playground"]']),
    "fitness": ("Fitnessstudio", ['["leisure"="fitness_centre"]']),
}
ALIAS = {"supermärkte": "supermarkt", "einkaufen": "supermarkt", "laden": "supermarkt", "lidl": "supermarkt", "aldi": "supermarkt",
         "rewe": "supermarkt", "edeka": "supermarkt", "carrefour": "supermarkt", "baecker": "bäckerei", "bäcker": "bäckerei",
         "dm": "drogerie", "rossmann": "drogerie", "tanke": "tankstelle", "atm": "geldautomat", "cafe": "café", "kaffee": "café",
         "doktor": "arzt", "hausarzt": "arzt", "bus": "haltestelle", "bushaltestelle": "haltestelle", "gym": "fitness",
         "fitnessstudio": "fitness", "post office": "post", "pharmacy": "apotheke", "supermarket": "supermarkt", "bakery": "bäckerei"}
MODES = {"auto": ("routed-car", 50, "🚗", "mit dem Auto"), "fahrrad": ("routed-bike", 15, "🚲", "mit dem Rad"), "fuß": ("routed-foot", 4.8, "🚶", "zu Fuß")}


def _load():
    try:
        d = json.loads(DATA.read_text("utf-8"))
    except Exception:
        d = {}
    d.setdefault("last", None)
    d.setdefault("places", {})        # name → {lat, lon, name}
    d.setdefault("reminders", [])
    d.setdefault("done_ids", [])
    d.setdefault("told", {})          # Termin-Schlüssel → Zeit (Losfahr-Hinweis schon gesendet)
    d.setdefault("fired", [])         # ausgelöste einmalige Erinnerungen (für „Nächstes Mal wieder“)
    return d


def _save(d):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(DATA)


def dist_m(a_lat, a_lon, b_lat, b_lon):
    R = 6371000.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def fmt_dist(m):
    return f"{round(m / 10) * 10:.0f} m" if m < 1000 else f"{m / 1000:.1f} km".replace(".", ",")


def fmt_min(s):
    m = max(1, round(s / 60))
    return f"{m} Min" if m < 60 else f"{m // 60} Std {m % 60:02d} Min"


# ---------------------------------------------------------------- OpenStreetMap-Dienste
_nom_lock, _nom_last = threading.Lock(), [0.0]
_cache = {}


def _nominatim(path, params):
    """Nominatim erlaubt höchstens 1 Anfrage pro Sekunde."""
    with _nom_lock:
        wait = 1.05 - (time.time() - _nom_last[0])
        if wait > 0:
            time.sleep(wait)
        st, js, _ = ig._http("GET", f"https://nominatim.openstreetmap.org/{path}?" + urllib.parse.urlencode({**params, "format": "jsonv2"}),
                             headers={"Accept-Language": "de"}, timeout=15)
        _nom_last[0] = time.time()
    if st != 200:
        raise RuntimeError("Kartendienst (OpenStreetMap) gerade nicht erreichbar.")
    return js


def place_name(lat, lon):
    key = ("rev", round(lat, 4), round(lon, 4))
    if key in _cache:
        return _cache[key]
    try:
        js = _nominatim("reverse", {"lat": lat, "lon": lon, "zoom": 18, "addressdetails": 1}) or {}
        a = js.get("address") or {}
        poi = js.get("name") if js.get("name") and js.get("name") not in (a.get("road"), a.get("house_number")) else ""
        street = " ".join(x for x in (a.get("road") or a.get("pedestrian") or a.get("footway") or "", a.get("house_number") or "") if x)
        city = a.get("city") or a.get("town") or a.get("village") or a.get("municipality") or a.get("suburb") or ""
        name = ", ".join(x for x in (poi, street, city) if x) or js.get("display_name", "")[:80] or f"{lat:.4f}, {lon:.4f}"
    except Exception:
        name = f"{lat:.4f}, {lon:.4f}"
    _cache[key] = name
    return name


def geocode(q, near=None):
    q = str(q or "").strip()
    if not q:
        raise RuntimeError("Welcher Ort?")
    key = ("geo", q.lower(), round(near[0], 1) if near else None, round(near[1], 1) if near else None)
    if key in _cache:
        return _cache[key]
    params = {"q": q, "limit": 1}
    if near:  # in der Umgebung bevorzugen (ca. ±50 km)
        params.update(viewbox=f"{near[1] - 0.6},{near[0] + 0.45},{near[1] + 0.6},{near[0] - 0.45}")
    js = _nominatim("search", params) or []
    if not js and near:
        js = _nominatim("search", {"q": q, "limit": 1}) or []
    if not js:
        raise RuntimeError(f"„{q}“ nicht auf der Karte gefunden – genauer schreiben (Straße, Ort)?")
    r = (float(js[0]["lat"]), float(js[0]["lon"]), js[0].get("display_name", q)[:100])
    _cache[key] = r
    return r


def route(a, b, mode="auto"):
    """(Sekunden, Meter) von a nach b. Fällt bei Ausfall auf Luftlinie × 1,3 zurück."""
    prof, kmh, _, _ = MODES.get(mode, MODES["auto"])
    key = ("route", mode, round(a[0], 3), round(a[1], 3), round(b[0], 4), round(b[1], 4))
    hit = _cache.get(key)
    if hit and time.time() - hit[2] < 600:
        return hit[0], hit[1], hit[3]
    try:
        st, js, _ = ig._http("GET", f"https://routing.openstreetmap.de/{prof}/route/v1/driving/{a[1]},{a[0]};{b[1]},{b[0]}?overview=false", timeout=15)
        r = (js or {}).get("routes") or []
        if st != 200 or not r:
            raise RuntimeError
        sec, m, exact = float(r[0]["duration"]), float(r[0]["distance"]), True
    except Exception:
        m = dist_m(*a, *b) * 1.3
        sec, exact = m / (kmh / 3.6), False
    _cache[key] = (sec, m, time.time(), exact)
    return sec, m, exact


def _overpass(lat, lon, cat, radius):
    filters = CATS[cat][1]
    parts = "".join(f"node(around:{radius},{lat},{lon}){f};way(around:{radius},{lat},{lon}){f};" for f in filters)
    q = f"[out:json][timeout:20];({parts});out center 60;"
    st, js, _ = ig._http("POST", "https://overpass-api.de/api/interpreter", form={"data": q}, timeout=30)
    if st != 200 or not js:
        raise RuntimeError("Ortssuche (OpenStreetMap) gerade überlastet – gleich nochmal.")
    out = []
    for e in js.get("elements", []):
        la, lo = e.get("lat") or (e.get("center") or {}).get("lat"), e.get("lon") or (e.get("center") or {}).get("lon")
        if la is None:
            continue
        t = e.get("tags") or {}
        name = t.get("name") or t.get("brand") or CATS[cat][0]
        addr = " ".join(x for x in (t.get("addr:street", ""), t.get("addr:housenumber", "")) if x)
        out.append({"name": name, "adresse": addr, "lat": la, "lon": lo, "öffnungszeiten": t.get("opening_hours")})
    return out


_poi = {}


def pois(cat, lat, lon, radius=1500):
    """POIs einer Kategorie im Umkreis – gecacht, neu geladen erst nach 700 m Bewegung oder 30 Minuten."""
    c = _poi.get(cat)
    if not c or dist_m(lat, lon, c["lat"], c["lon"]) > 700 or time.time() - c["t"] > 1800 or c["r"] < radius:
        c = {"lat": lat, "lon": lon, "t": time.time(), "r": radius, "items": _overpass(lat, lon, cat, radius)}
        _poi[cat] = c
    return c["items"]


def category_of(word):
    w = re.sub(r"^(dem|der|den|die|das|einem|einer|einen|ein|eine|zum|zur|beim|bei|im|in|am|an)\s+", "", str(word or "").strip().lower())
    w = re.sub(r"\s+(laden|geschäft|markt)$", lambda m: "" if w.startswith(("super", "bau")) else m.group(0), w)
    w = ALIAS.get(w, w)
    if w in CATS:
        return w
    for k in CATS:
        if w.rstrip("n").rstrip("e") == k.rstrip("e") or (len(w) > 4 and k.startswith(w)):
            return k
    return None


# ---------------------------------------------------------------- Standort
def last(fresh_only=False):
    d = _load()
    l = d["last"]
    if not l or time.time() - l["t"] > STALE_S:
        return None
    if fresh_only and time.time() - l["t"] > FRESH_S and not (l.get("live_until", 0) > time.time()):
        return None
    return l


def need_last():
    l = last()
    if not l:
        raise RuntimeError("Ich kenne deinen Standort nicht. Teile ihn in Telegram (📎 → Standort; am besten „Live-Standort“) – "
                           "dann geht das. Am PC gibt es keinen Standort.")
    return l


def forget():
    with LOCK:
        d = _load()
        d["last"] = None
        _save(d)
    return "Standort vergessen."


def update(lat, lon, acc=None, live_period=None, edited=False):
    """Neuer Standort von Telegram. Gibt (Ereignisse) zurück: Liste von dicts {art, text, id?}."""
    lat, lon = float(lat), float(lon)
    now = time.time()
    with LOCK:
        d = _load()
        prev = d["last"] or {}
        live_until = prev.get("live_until", 0)
        if live_period:
            live_until = now + int(live_period) if not edited or not prev.get("live_until") else prev["live_until"]
            if int(live_period) >= 0x7FFFFFFF:      # „bis ich es beende“
                live_until = now + 30 * 86400
        elif not edited:
            live_until = 0
        d["last"] = {"lat": round(lat, 6), "lon": round(lon, 6), "acc": acc, "t": now, "live_until": live_until}
        _save(d)
    events = check_reminders(lat, lon, acc)
    events += check_leave(lat, lon)
    return events


def summary(lat=None, lon=None, mode="auto"):
    """Für die Telegram-Antwort auf einen geteilten Standort: Ort, Wetter, nächster Termin mit Fahrzeit."""
    if lat is None:
        l = need_last()
        lat, lon = l["lat"], l["lon"]
    out = {"ort": place_name(lat, lon)}
    try:
        w = ig.weather_at(lat, lon, out["ort"], 1)
        j, t = w["jetzt"], (w.get("tage") or [{}])[0]
        out["wetter"] = f"{j['icon']} {round(j['temperatur'])}° (gefühlt {round(j['gefühlt'])}°), {j['wetter']}" + \
                        (f" · heute {round(t['min'])}–{round(t['max'])}°, Regen {t['regen_wahrscheinlichkeit']} %" if "min" in t else "")
    except Exception:
        pass
    ev = next_event_with_place()
    if ev:
        try:
            out["termin"] = travel_to_event(ev, lat, lon, mode)
        except Exception as e:
            out["termin"] = {"titel": ev["titel"], "fehler": str(e)[:120]}
    d = _load()
    near = [(n, dist_m(lat, lon, p["lat"], p["lon"])) for n, p in d["places"].items()]
    near = [x for x in near if x[1] < 300]
    if near:
        out["bei"] = min(near, key=lambda x: x[1])[0]
    out["orts_erinnerungen"] = len([r for r in d["reminders"] if r["id"] not in d["done_ids"]])
    return out


# ---------------------------------------------------------------- Termine & Losfahren
def next_event_with_place(hours=12):
    try:
        evs = get_events() or []
    except Exception:
        return None
    from datetime import datetime
    now = datetime.now()
    for e in evs:
        if e.get("allday") or not (e.get("ort") or "").strip():
            continue
        if e["start"] >= now and (e["start"] - now).total_seconds() <= hours * 3600:
            return e
    return None


def travel_to_event(ev, lat, lon, mode="auto"):
    from datetime import datetime
    tl = geocode(ev["ort"], (lat, lon))
    sec, m, exact = route((lat, lon), tl[:2], mode)
    mins_left = (ev["start"] - datetime.now()).total_seconds()
    res = {"titel": ev["titel"], "um": ev["start"].strftime("%H:%M"), "ort": ev["ort"], "dauer": fmt_min(sec), "strecke": fmt_dist(m),
           "art": MODES[mode][3], "dauer_s": round(sec), "genau": exact, "losfahren_bis": None}
    leave = mins_left - sec - 10 * 60
    res["losfahren_in_min"] = round(leave / 60)
    res["losfahren_bis"] = datetime.fromtimestamp(time.time() + leave).strftime("%H:%M")
    if mode == "auto":
        fs, fm, _ = route((lat, lon), tl[:2], "fuß")
        if fs < 35 * 60:
            res["zu_fuß"] = fmt_min(fs)
    return res


def check_leave(lat, lon, mode=None):
    """Live-Standort + Termin mit Ort: einmal melden, wenn man losmuss (Fahrzeit + 10 Min Puffer)."""
    mode = mode or _mode()
    ev = next_event_with_place(3)
    if not ev:
        return []
    key = f"{ev['titel']}|{ev['start']:%Y%m%d%H%M}"
    d = _load()
    if key in d["told"]:
        return []
    try:
        t = travel_to_event(ev, lat, lon, mode)
    except Exception:
        return []
    if t["losfahren_in_min"] > 3 or t["dauer_s"] < 4 * 60:
        return []
    with LOCK:
        d = _load()
        d["told"] = {k: v for k, v in d["told"].items() if time.time() - v < 86400}
        d["told"][key] = time.time()
        _save(d)
    late = t["losfahren_in_min"] < -5
    return [{"art": "losfahren", "text": f"{'⏰ Du bist knapp dran' if late else MODES[mode][2] + ' Zeit loszufahren'}: **{t['titel']}** um {t['um']} "
                                         f"({t['ort']}) – ca. {t['dauer']} {t['art']} ({t['strecke']})."
                                         + (f" Zu Fuß: {t['zu_fuß']}." if t.get("zu_fuß") else "")
                                         + ("" if t["genau"] else " (geschätzt)"), "ziel": t["ort"]}]


_mode = lambda: "auto"


# ---------------------------------------------------------------- Orts-Erinnerungen
def resolve_place(place):
    """'hier' | gespeicherter Name | Kategorie (Supermarkt …) | Adresse → Ziel-dict."""
    p = str(place or "").strip()
    pl = p.lower()
    d = _load()
    if pl in ("hier", "here", "da", "dort", "aktueller standort", "mein standort"):
        l = need_last()
        return {"typ": "punkt", "lat": l["lat"], "lon": l["lon"], "name": place_name(l["lat"], l["lon"]), "radius": 150}
    name = re.sub(r"^(zu|bei|nach|im|in|am|an der|an dem|auf der|bei der)\s+", "", pl).replace("zuhause", "zuhause").replace("zu hause", "zuhause")
    name = {"daheim": "zuhause", "home": "zuhause", "zuhaus": "zuhause", "haus": "zuhause", "büro": "arbeit", "work": "arbeit", "job": "arbeit"}.get(name, name)
    if name in d["places"]:
        x = d["places"][name]
        return {"typ": "punkt", "lat": x["lat"], "lon": x["lon"], "name": name.capitalize(), "ort_name": name, "radius": 150}
    cat = category_of(p)
    if cat:
        return {"typ": "kategorie", "kategorie": cat, "name": CATS[cat][0], "radius": 80}
    if name in ("zuhause", "arbeit"):
        raise RuntimeError(f"Ich weiß noch nicht, wo „{name}“ ist. Teile in Telegram deinen Standort, wenn du dort bist, und tipp auf "
                           f"„{'🏠 Als Zuhause' if name == 'zuhause' else '🏢 Als Arbeit'} speichern“ – oder nenn mir die Adresse.")
    l = last()
    lat, lon, full = geocode(p, (l["lat"], l["lon"]) if l else None)
    return {"typ": "punkt", "lat": lat, "lon": lon, "name": full.split(",")[0] if len(full) > 40 else full, "adresse": full, "radius": 150}


def reminder_add(text, place, when="ankommen", repeat=False):
    text = str(text or "").strip()[:200]
    if not text:
        raise RuntimeError("Woran soll ich dich erinnern?")
    if when not in ("ankommen", "verlassen"):
        when = "ankommen"
    target = resolve_place(place)
    if target["typ"] == "kategorie" and when == "verlassen":
        when = "ankommen"
    r = {"id": secrets.token_hex(4), "text": text, "ziel": target, "wann": when, "wiederholen": bool(repeat), "seit": time.time(), "drin": None}
    with LOCK:
        d = _load()
        if len([x for x in d["reminders"] if x["id"] not in d["done_ids"]]) >= 50:
            raise RuntimeError("Maximal 50 Orts-Erinnerungen.")
        d["reminders"].append(r)
        _save(d)
    live = (last() or {}).get("live_until", 0) > time.time()
    where = target["name"] if target["typ"] == "punkt" else f"einem {target['name']}" if target["name"] not in ("Apotheke", "Bäckerei", "Drogerie", "Tankstelle", "Post/Paketshop", "Bank/Geldautomat", "Haltestelle", "E-Ladestation", "Toilette") else f"einer {target['name']}"
    return {"id": r["id"], "text": f"📍 Ich erinnere dich an „{text}“, wenn du {'bei' if when == 'ankommen' else 'von'} {where} "
                                   f"{'bist' if when == 'ankommen' else 'weggehst'}" + (" (jedes Mal)" if repeat else "") + ".",
            "hinweis": "" if live else "Dafür muss Lumen deinen Standort kennen: in Telegram „Live-Standort teilen“ (📎 → Standort → Live-Standort, "
                                       "z. B. 8 Stunden). Ohne Live-Standort prüfe ich nur, wenn du den Standort von Hand schickst."}


def reminders():
    d = _load()
    out = []
    for r in d["reminders"]:
        if r["id"] in d["done_ids"]:
            continue
        z = r["ziel"]
        out.append({"id": r["id"], "text": r["text"], "ort": z["name"] + (" (jede Filiale)" if z["typ"] == "kategorie" else ""), "wann": r["wann"],
                    "jedes_mal": r["wiederholen"]})
    return out


def reminder_done(rid, keep=False):
    with LOCK:
        d = _load()
        r = next((x for x in d["reminders"] if x["id"] == rid), None)
        if keep:
            old = r or next((x for x in d["fired"] if x["id"] == rid), None)
            if not old:
                return "Nicht mehr gefunden."
            if not r:   # einmalige, schon ausgelöste Erinnerung wieder scharf schalten
                d["fired"] = [x for x in d["fired"] if x["id"] != rid]
                d["done_ids"] = [x for x in d["done_ids"] if x != rid]
                d["reminders"].append({**old, "seit": time.time()})
            _save(d)
            return "🔁 Ich erinnere dich nächstes Mal wieder."
        if not r:
            return "✅ Erledigt."
        d["reminders"] = [x for x in d["reminders"] if x["id"] != rid]
        d["done_ids"] = (d["done_ids"] + [rid])[-300:]
        _save(d)
    return "✅ Erledigt."


def reminder_delete(rid):
    if rid == "alle":
        with LOCK:
            d = _load()
            d["done_ids"] = (d["done_ids"] + [r["id"] for r in d["reminders"]])[-300:]
            d["reminders"] = []
            _save(d)
        return "Alle Orts-Erinnerungen gelöscht."
    return reminder_done(rid).replace("✅ Erledigt.", "Gelöscht.")


def check_reminders(lat, lon, acc=None):
    """Prüft alle Orts-Erinnerungen gegen den neuen Standort. Gibt ausgelöste zurück."""
    acc = float(acc or 0)
    fired = []
    with LOCK:
        d = _load()
        changed = False
        for r in d["reminders"]:
            if r["id"] in d["done_ids"]:
                continue
            z, hit_name = r["ziel"], None
            if z["typ"] == "punkt":
                dist = dist_m(lat, lon, z["lat"], z["lon"])
                inside = dist <= max(z.get("radius", 150), min(acc, 250))
                outside = dist > max(z.get("radius", 150), min(acc, 250)) + 100      # Puffer gegen Flackern
                hit_name = z["name"]
            else:
                try:
                    items = pois(z["kategorie"], lat, lon)
                except Exception:
                    continue
                best = min(((dist_m(lat, lon, p["lat"], p["lon"]), p) for p in items), key=lambda x: x[0], default=(1e9, None))
                inside = best[0] <= max(z.get("radius", 80), min(acc, 120))
                outside = best[0] > max(z.get("radius", 80), min(acc, 120)) + 100
                if best[1]:
                    hit_name = best[1]["name"] + (f", {best[1]['adresse']}" if best[1]["adresse"] else "")
            was = r.get("drin")
            fresh = time.time() - r.get("seit", 0) < 120          # gerade erst angelegt (steht vermutlich schon dort)
            fire = False
            if r["wann"] == "ankommen" and inside and was is not True and not (was is None and fresh):
                fire = True
            if r["wann"] == "verlassen" and outside and was is True:
                fire = True
            new_state = True if inside else False if outside else was
            if new_state != was:
                r["drin"] = new_state
                changed = True
            if fire:
                if not r["wiederholen"]:   # einmalig → gleich erledigt; „Nächstes Mal wieder“ holt sie zurück
                    d["done_ids"] = (d["done_ids"] + [r["id"]])[-300:]
                    d["fired"] = (d["fired"] + [r])[-50:]
                    changed = True
                fired.append({"art": "erinnerung", "id": r["id"], "wiederholen": r["wiederholen"],
                              "text": f"📍 **Erinnerung:** {r['text']}\n*{'Du bist bei' if r['wann'] == 'ankommen' else 'Du gehst gerade von'} {hit_name or z['name']}*"})
        if changed:
            d["reminders"] = [x for x in d["reminders"] if x["id"] not in d["done_ids"]]
            _save(d)
    return fired


def save_place(name, lat=None, lon=None):
    name = str(name or "").strip().lower()[:30]
    name = {"daheim": "zuhause", "zu hause": "zuhause", "home": "zuhause", "büro": "arbeit", "work": "arbeit"}.get(name, name)
    if not name:
        raise RuntimeError("Wie soll der Ort heißen?")
    if lat is None:
        l = need_last()
        lat, lon = l["lat"], l["lon"]
    with LOCK:
        d = _load()
        d["places"][name] = {"lat": round(float(lat), 6), "lon": round(float(lon), 6), "adresse": place_name(lat, lon)}
        _save(d)
    return f"📌 „{name.capitalize()}“ gespeichert: {d['places'][name]['adresse']}"


def places():
    return {n: p.get("adresse", "") for n, p in _load()["places"].items()}


def nearby(category, radius=1500, limit=5):
    l = need_last()
    cat = category_of(category)
    if not cat:
        raise RuntimeError("Das kenne ich nicht. Möglich: " + ", ".join(CATS))
    items = pois(cat, l["lat"], l["lon"], max(300, min(int(radius or 1500), 5000)))
    rows = sorted(((dist_m(l["lat"], l["lon"], p["lat"], p["lon"]), p) for p in items), key=lambda x: x[0])[:limit]
    out = []
    for dm, p in rows:
        sec, m, _ = route((l["lat"], l["lon"]), (p["lat"], p["lon"]), "fuß")
        out.append({"name": p["name"], "adresse": p["adresse"], "luftlinie": fmt_dist(dm), "zu_fuß": fmt_min(sec),
                    "öffnungszeiten": p["öffnungszeiten"], "karte": f"https://www.openstreetmap.org/?mlat={p['lat']}&mlon={p['lon']}#map=18/{p['lat']}/{p['lon']}"})
    return {"kategorie": CATS[cat][0], "von": place_name(l["lat"], l["lon"]), "treffer": out,
            "hinweis": "" if out else "Nichts im Umkreis gefunden – größeren Radius versuchen?"}


def travel_time(destination, mode=None):
    l = need_last()
    mode = mode if mode in MODES else _mode()
    dest = str(destination or "").strip()
    if dest.lower() in ("", "termin", "nächster termin", "nächsten termin", "next event"):
        ev = next_event_with_place(24)
        if not ev:
            raise RuntimeError("Kein Termin mit Ort in den nächsten 24 Stunden.")
        return travel_to_event(ev, l["lat"], l["lon"], mode)
    try:
        z = resolve_place(dest)
    except RuntimeError:
        raise
    if z["typ"] == "kategorie":
        n = nearby(dest, 3000, 1)["treffer"]
        if not n:
            raise RuntimeError(f"Kein {z['name']} in der Nähe gefunden.")
        return {"ziel": n[0]["name"], **n[0]}
    sec, m, exact = route((l["lat"], l["lon"]), (z["lat"], z["lon"]), mode)
    return {"ziel": z.get("adresse") or z["name"], "dauer": fmt_min(sec), "strecke": fmt_dist(m), "art": MODES[mode][3], "genau": exact,
            "ankunft": time.strftime("%H:%M", time.localtime(time.time() + sec))}


def merge_from_desktop(lst):
    """Lumen-Server: Orts-Erinnerungen vom PC übernehmen (nur neue; erledigte bleiben erledigt)."""
    if not isinstance(lst, list):
        return
    with LOCK:
        d = _load()
        have = {r["id"] for r in d["reminders"]} | set(d["done_ids"])
        new = [r for r in lst if isinstance(r, dict) and r.get("id") and r["id"] not in have and isinstance(r.get("ziel"), dict)]
        if new:
            d["reminders"] += new
            _save(d)


def sync_payload():
    d = _load()
    return [r for r in d["reminders"] if r["id"] not in d["done_ids"]]
