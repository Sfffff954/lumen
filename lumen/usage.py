"""
Lumen – Verbrauch & Kosten.

Zählt die Tokens jeder KI-Antwort und schätzt die Kosten anhand einer Preistabelle
(US-Dollar pro 1 Mio. Tokens, in den Einstellungen änderbar). Lokale Modelle (Ollama) kosten nichts.
"""
import json
import threading
from datetime import date, timedelta
from pathlib import Path

FILE = Path.home() / ".lumen" / "usage.json"
LOCK = threading.Lock()

# Schätzwerte – Anbieter ändern Preise; in den Einstellungen anpassbar. Schlüssel = Teil des Modellnamens.
DEFAULT_PRICES = {
    "opus": [5.0, 25.0], "sonnet": [3.0, 15.0], "haiku": [1.0, 5.0], "fable": [5.0, 25.0],
    "gpt-4o-mini": [0.15, 0.60], "gpt-4o": [2.50, 10.0], "gpt-4.1-nano": [0.10, 0.40], "gpt-4.1-mini": [0.40, 1.60],
    "gpt-4.1": [2.0, 8.0], "gpt-5-nano": [0.05, 0.40], "gpt-5-mini": [0.25, 2.0], "gpt-5": [1.25, 10.0],
    "o4-mini": [1.10, 4.40], "deepseek-chat": [0.28, 0.42], "deepseek-reasoner": [0.28, 0.42],
    "gemini-2.5-flash-lite": [0.10, 0.40], "gemini-2.5-flash": [0.30, 2.50], "gemini-2.5-pro": [1.25, 10.0],
    "gemini-3-pro": [2.0, 12.0], "gemini-3-flash": [0.50, 3.0], "gemini-2.0-flash": [0.10, 0.40],
}


def price_for(model, prices=None):
    m = (model or "").lower()
    table = {**DEFAULT_PRICES, **(prices or {})}
    best = None
    for key, val in table.items():
        if key.lower() in m and (best is None or len(key) > len(best[0])):
            best = (key, val)
    return best[1] if best else None


def cost(model, tin, tout, prices=None, provider=""):
    if provider == "ollama":
        return 0.0, True
    p = price_for(model, prices)
    if not p:
        return 0.0, False
    return (tin * p[0] + tout * p[1]) / 1_000_000, True


def _load():
    try:
        return json.loads(FILE.read_text("utf-8"))
    except Exception:
        return {"days": {}}


def record(provider, model, tin, tout, prices=None):
    c, known = cost(model, tin, tout, prices, provider)
    day = date.today().isoformat()
    key = f"{provider}:{model}"
    with LOCK:
        d = _load()
        e = d.setdefault("days", {}).setdefault(day, {}).setdefault(key, {"in": 0, "out": 0, "cost": 0.0, "calls": 0})
        e["in"] += int(tin)
        e["out"] += int(tout)
        e["cost"] = round(e["cost"] + c, 6)
        e["calls"] += 1
        if not known:
            e["price_unknown"] = True
        # nur 400 Tage behalten
        cutoff = (date.today() - timedelta(days=400)).isoformat()
        d["days"] = {k: v for k, v in d["days"].items() if k >= cutoff}
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(json.dumps(d, indent=1), "utf-8")
    return c


def summary(budget=0.0):
    d = _load().get("days", {})
    today = date.today()
    tkey, mkey = today.isoformat(), today.isoformat()[:7]
    sum_day = lambda k: sum(e["cost"] for e in d.get(k, {}).values())
    last30 = [{"tag": (today - timedelta(days=i)).isoformat(), "kosten": round(sum_day((today - timedelta(days=i)).isoformat()), 4)}
              for i in range(29, -1, -1)]
    per_model, month_cost, month_in, month_out, unknown = {}, 0.0, 0, 0, []
    for k, models in d.items():
        if not k.startswith(mkey):
            continue
        for m, e in models.items():
            pm = per_model.setdefault(m, {"in": 0, "out": 0, "kosten": 0.0, "aufrufe": 0})
            pm["in"] += e["in"]
            pm["out"] += e["out"]
            pm["kosten"] = round(pm["kosten"] + e["cost"], 4)
            pm["aufrufe"] += e["calls"]
            month_cost += e["cost"]
            month_in += e["in"]
            month_out += e["out"]
            if e.get("price_unknown") and m not in unknown:
                unknown.append(m)
    res = {"heute": round(sum_day(tkey), 4), "monat": round(month_cost, 4), "monat_tokens": month_in + month_out,
           "letzte_30_tage": last30, "modelle": dict(sorted(per_model.items(), key=lambda x: -x[1]["kosten"])),
           "preis_unbekannt": unknown, "budget": budget or 0}
    if budget:
        res["budget_anteil"] = round(month_cost / budget, 3)
    return res
