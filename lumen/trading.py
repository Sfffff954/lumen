"""Lumen – Krypto-Trading.

1) Übungsdepot (Paper-Trading): echte Kurse (CoinGecko), Spielgeld, Gebühren simuliert, Limit-/Stop-Orders.
2) Echte Swaps auf Solana über Jupiter – Lumen bereitet nur vor, UNTERSCHRIEBEN wird ausschließlich in Phantom.
   Lumen sieht/speichert nie Seed-Phrase oder privaten Schlüssel.
3) Kurs-Alarme (Benachrichtigung + Telegram).
"""
import json
import re
import secrets
import threading
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import integrations as ig

DATA = Path.home() / ".lumen" / "trading.json"
LOCK = threading.RLock()
FEE = 0.003            # simulierte Gebühr 0,3 % (wie typische DEX-/Börsengebühr)
JUP = "https://lite-api.jup.ag"
SWAPS = {}             # id -> vorbereiteter Swap (nur im Speicher)

SOL_TOKENS = {  # bekannte, verifizierte Solana-Tokens: Symbol -> (Mint, Dezimalstellen, CoinGecko-ID)
    "SOL": (ig.SOL_MINT, 9, "solana"), "USDC": (ig.USDC_SOL, 6, "usd-coin"), "USDT": (ig.USDT_SOL, 6, "tether"),
    "JUP": ("JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN", 6, "jupiter-exchange-solana"),
    "BONK": ("DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", 5, "bonk"),
    "WIF": ("EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm", 6, "dogwifcoin"),
    "RAY": ("4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R", 6, "raydium"),
    "PYTH": ("HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3", 6, "pyth-network"),
    "JTO": ("jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL", 9, "jito-governance-token"),
    "RENDER": ("rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof", 8, "render-token"),
    "HNT": ("hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux", 8, "helium"),
}


def _de(v, dec=None):
    """Zahl deutsch formatiert: 1.234,56 (dec=None → 6 signifikante Stellen)."""
    try:
        t = f"{float(v):,.{dec}f}" if dec is not None else f"{float(v):,.6g}"
    except (TypeError, ValueError):
        return str(v)
    return t.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _now():
    return datetime.now().strftime("%d.%m. %H:%M")


def _load():
    try:
        d = json.loads(DATA.read_text("utf-8"))
    except Exception:
        d = {}
    d.setdefault("depot", None)
    d.setdefault("orders", [])
    d.setdefault("alerts", [])
    d.setdefault("swaps", [])
    d.setdefault("limits", {"max_swap_eur": 250, "max_slippage_pct": 1.0})
    return d


def _save(d):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(DATA)


def _num(v, what="Betrag"):
    try:
        x = float(str(v).replace("€", "").replace(",", ".").strip())
    except (TypeError, ValueError):
        raise RuntimeError(f"Ungültiger {what}.")
    if x <= 0 or x > 1e12:
        raise RuntimeError(f"Ungültiger {what}.")
    return x


# ---------------------------------------------------------------- Kurse
def coin_id(sym):
    s = str(sym or "").strip().lower()
    if not s:
        raise RuntimeError("Welcher Coin?")
    if s in ig.CG_IDS:
        return ig.CG_IDS[s]
    if s in ig.CG_IDS.values() or s in {v[2] for v in SOL_TOKENS.values()} or s in _pc:
        return s
    if s.upper() in SOL_TOKENS:
        return SOL_TOKENS[s.upper()][2]
    st, js, _ = ig._http("GET", "https://api.coingecko.com/api/v3/search?query=" + urllib.parse.quote(s))
    hit = ((js or {}).get("coins") or [None])[0]
    if not hit:
        raise RuntimeError(f"Coin „{sym}“ nicht gefunden.")
    return hit["id"]


_pc = {}


def prices(ids):
    """{id: {"eur":…, "usd":…, "ch":…}} – 60 s Cache, gegen CoinGecko-Limits."""
    ids = [i for i in dict.fromkeys(ids) if i]
    need = [i for i in ids if time.time() - _pc.get(i, (0, None))[0] > 60]
    if need:
        for k, v in ig._cg_prices(need).items():
            _pc[k] = (time.time(), {"eur": v.get("eur"), "usd": v.get("usd"), "ch": round(v.get("eur_24h_change") or 0, 2)})
    return {i: _pc[i][1] for i in ids if i in _pc}


def price_eur(cid):
    p = prices([cid]).get(cid, {}).get("eur")
    if not p:
        raise RuntimeError(f"Kein Kurs für {cid}.")
    return float(p)


def chart(coin, days=7):
    cid = coin_id(coin)
    st, js, _ = ig._http("GET", f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart?vs_currency=eur&days={int(days)}")
    pts = (js or {}).get("prices") or []
    if not pts:
        raise RuntimeError("Keine Chart-Daten (Kursdienst evtl. überlastet).")
    step = max(1, len(pts) // 120)
    pts = pts[::step]
    vals = [p[1] for p in pts]
    return {"coin": cid, "tage": int(days), "punkte": [[int(p[0] / 1000), round(p[1], 8)] for p in pts],
            "min": min(vals), "max": max(vals), "start": vals[0], "jetzt": vals[-1],
            "änderung_%": round((vals[-1] / vals[0] - 1) * 100, 2) if vals[0] else 0}


# ---------------------------------------------------------------- Übungsdepot
def _depot(d):
    if not d["depot"]:
        d["depot"] = {"start": 1000.0, "cash": 1000.0, "pos": {}, "verlauf": [], "seit": _now()}
    return d["depot"]


def paper_reset(start=1000):
    start = _num(start, "Startbetrag")
    with LOCK:
        d = _load()
        d["depot"] = {"start": start, "cash": start, "pos": {}, "verlauf": [], "seit": _now()}
        d["orders"] = [o for o in d["orders"] if o.get("art") == "alarm"]
        _save(d)
    return f"🎮 Neues Übungsdepot mit {_de(start, 2)} € Spielgeld."


def _exec_buy(dep, cid, eur, price, note=""):
    if eur > dep["cash"] + 1e-9:
        raise RuntimeError(f"Nicht genug Spielgeld (frei: {_de(dep['cash'], 2)} €).")
    qty = eur * (1 - FEE) / price
    p = dep["pos"].setdefault(cid, {"menge": 0.0, "kosten": 0.0})
    p["menge"] += qty
    p["kosten"] += eur
    dep["cash"] -= eur
    dep["verlauf"].append({"zeit": _now(), "art": "kauf", "coin": cid, "menge": qty, "kurs": price, "eur": round(eur, 2), "notiz": note})
    dep["verlauf"] = dep["verlauf"][-300:]
    return qty


def _exec_sell(dep, cid, qty, price, note=""):
    p = dep["pos"].get(cid)
    if not p or p["menge"] <= 0:
        raise RuntimeError(f"Du hast kein {cid} im Übungsdepot.")
    qty = min(qty, p["menge"])
    eur = qty * price * (1 - FEE)
    cost = p["kosten"] * qty / p["menge"]
    p["menge"] -= qty
    p["kosten"] -= cost
    if p["menge"] < 1e-12:
        dep["pos"].pop(cid)
    dep["cash"] += eur
    dep["verlauf"].append({"zeit": _now(), "art": "verkauf", "coin": cid, "menge": qty, "kurs": price, "eur": round(eur, 2),
                           "gewinn": round(eur - cost, 2), "notiz": note})
    dep["verlauf"] = dep["verlauf"][-300:]
    return eur, eur - cost


def paper_trade(side, coin, eur=None, amount=None, percent=None):
    """Kauf mit EUR-Betrag; Verkauf mit Menge, Prozent oder allem."""
    cid = coin_id(coin)
    price = price_eur(cid)
    with LOCK:
        d = _load()
        dep = _depot(d)
        if side in ("buy", "kauf", "kaufen"):
            if eur is None and amount is not None:
                eur = _num(amount, "Menge") * price
            if eur is None and percent is not None:
                eur = dep["cash"] * min(100, _num(percent, "Prozent")) / 100
            eur = _num(eur)
            qty = _exec_buy(dep, cid, eur, price)
            _save(d)
            return {"ok": True, "text": f"🎮 Gekauft (Übung): {_de(qty)} {cid} für {_de(eur, 2)} € zu {_de(price)} €. Frei: {_de(dep['cash'], 2)} €.",
                    "depot": portfolio(d)}
        p = dep["pos"].get(cid)
        if not p:
            raise RuntimeError(f"Du hast kein {cid} im Übungsdepot.")
        if percent is not None:
            qty = p["menge"] * min(100, _num(percent, "Prozent")) / 100
        elif amount is not None:
            qty = _num(amount, "Menge")
        elif eur is not None:
            qty = _num(eur) / price
        else:
            qty = p["menge"]
        got, gain = _exec_sell(dep, cid, qty, price)
        _save(d)
        return {"ok": True, "text": f"🎮 Verkauft (Übung): {_de(qty)} {cid} für {_de(got, 2)} € ({'+' if gain >= 0 else ''}{_de(gain, 2)} €). "
                                    f"Frei: {_de(dep['cash'], 2)} €.", "depot": portfolio(d)}


def portfolio(d=None):
    d = d or _load()
    dep = _depot(d)
    pr = prices(list(dep["pos"])) if dep["pos"] else {}
    rows, val = [], dep["cash"]
    for cid, p in dep["pos"].items():
        cur = (pr.get(cid) or {}).get("eur")
        v = p["menge"] * cur if cur else None
        val += v or 0
        rows.append({"coin": cid, "menge": round(p["menge"], 8), "einstand_eur": round(p["kosten"], 2), "kurs_eur": cur,
                     "wert_eur": round(v, 2) if v is not None else None,
                     "gewinn_eur": round(v - p["kosten"], 2) if v is not None else None,
                     "gewinn_%": round((v / p["kosten"] - 1) * 100, 2) if v and p["kosten"] else None,
                     "24h_%": (pr.get(cid) or {}).get("ch")})
    rows.sort(key=lambda r: -(r["wert_eur"] or 0))
    return {"modus": "Übungsdepot (Spielgeld)", "start_eur": dep["start"], "frei_eur": round(dep["cash"], 2),
            "gesamt_eur": round(val, 2), "gewinn_eur": round(val - dep["start"], 2),
            "gewinn_%": round((val / dep["start"] - 1) * 100, 2) if dep["start"] else 0, "seit": dep["seit"],
            "positionen": rows, "letzte_trades": dep["verlauf"][-8:][::-1],
            "offene_orders": [o for o in d["orders"]]}


# ---------------------------------------------------------------- Orders & Alarme
def add_order(kind, coin, price, eur=None, percent=None, note=""):
    """kind: limit_kauf | limit_verkauf | stop_loss | take_profit (Übungsdepot) | alarm_über | alarm_unter (Kurs-Alarm)."""
    kinds = {"limit_kauf": "≤", "limit_verkauf": "≥", "stop_loss": "≤", "take_profit": "≥", "alarm_über": "≥", "alarm_unter": "≤"}
    if kind not in kinds:
        raise RuntimeError("Art: limit_kauf, limit_verkauf, stop_loss, take_profit, alarm_über oder alarm_unter.")
    cid = coin_id(coin)
    price = _num(price, "Kurs")
    o = {"id": secrets.token_hex(3), "art": kind, "coin": cid, "kurs": price, "bed": kinds[kind], "seit": _now(), "notiz": str(note)[:80]}
    if kind == "limit_kauf":
        o["eur"] = _num(eur)
    elif kind in ("limit_verkauf", "stop_loss", "take_profit"):
        o["prozent"] = min(100, _num(percent or 100, "Prozent"))
    with LOCK:
        d = _load()
        if len(d["orders"]) >= 50:
            raise RuntimeError("Maximal 50 offene Orders/Alarme.")
        d["orders"].append(o)
        _save(d)
    now = price_eur(cid)
    what = {"limit_kauf": f"Kaufe (Übung) für {_de(o.get('eur', 0), 2)} €", "limit_verkauf": f"Verkaufe (Übung) {_de(o.get('prozent', 100))} %",
            "stop_loss": f"Stop-Loss (Übung): verkaufe {_de(o.get('prozent', 100))} %", "take_profit": f"Gewinnmitnahme (Übung): verkaufe {_de(o.get('prozent', 100))} %",
            "alarm_über": "🔔 Melde mich", "alarm_unter": "🔔 Melde mich"}[kind]
    return f"{what}, wenn {cid} {o['bed']} {_de(price)} € (jetzt {_de(now)} €). ID {o['id']}."


def cancel_order(oid):
    with LOCK:
        d = _load()
        n = len(d["orders"])
        d["orders"] = [o for o in d["orders"] if o["id"] != oid and oid != "alle"]
        _save(d)
    return "Gelöscht." if len(d["orders"]) < n else "Keine solche Order."


def check_orders(notify=None):
    """Im Hintergrund: Orders/Alarme prüfen. notify(text) meldet ausgelöste."""
    d = _load()
    if not d["orders"]:
        return []
    try:
        pr = prices([o["coin"] for o in d["orders"]])
    except Exception:
        return []
    fired = []
    with LOCK:
        d = _load()
        dep = _depot(d)
        keep = []
        for o in d["orders"]:
            cur = (pr.get(o["coin"]) or {}).get("eur")
            hit = cur is not None and (cur <= o["kurs"] if o["bed"] == "≤" else cur >= o["kurs"])
            if not hit:
                keep.append(o)
                continue
            try:
                if o["art"].startswith("alarm"):
                    msg = f"🔔 **Kurs-Alarm:** {o['coin']} ist {'über' if o['bed'] == '≥' else 'unter'} {_de(o['kurs'])} € – jetzt {_de(cur)} €."
                elif o["art"] == "limit_kauf":
                    qty = _exec_buy(dep, o["coin"], min(o["eur"], dep["cash"]), cur, "Limit-Kauf")
                    msg = f"🎮 **Limit-Kauf ausgeführt (Übung):** {_de(qty)} {o['coin']} zu {_de(cur)} €."
                else:
                    p = dep["pos"].get(o["coin"])
                    if not p:
                        continue
                    got, gain = _exec_sell(dep, o["coin"], p["menge"] * o.get("prozent", 100) / 100, cur, o["art"])
                    msg = f"🎮 **{ {'stop_loss': 'Stop-Loss', 'take_profit': 'Gewinnmitnahme'}.get(o['art'], 'Limit-Verkauf')} ausgeführt (Übung):** " \
                          f"{o['coin']} zu {_de(cur)} € → {_de(got, 2)} € ({'+' if gain >= 0 else ''}{_de(gain, 2)} €)."
            except Exception as e:
                msg = f"⚠️ Order {o['id']} ({o['coin']}) nicht ausführbar: {e}"
            if o.get("notiz"):
                msg += f"\n*{o['notiz']}*"
            fired.append(msg)
        d["orders"] = keep
        _save(d)
    for m in fired:
        try:
            notify and notify(m)
        except Exception:
            pass
    return fired


# ---------------------------------------------------------------- Echte Swaps (Solana / Jupiter / Phantom)
def sol_token(sym):
    s = str(sym or "").strip()
    if s.upper() in SOL_TOKENS:
        m, dec, cg = SOL_TOKENS[s.upper()]
        return {"symbol": s.upper(), "mint": m, "dec": dec, "cg": cg, "verifiziert": True}
    q = s
    st, js, _ = ig._http("GET", f"{JUP}/tokens/v2/search?query=" + urllib.parse.quote(q))
    cands = [t for t in (js or []) if t.get("id") == s or (t.get("symbol") or "").upper() == s.upper()]
    cands.sort(key=lambda t: (not t.get("isVerified"), -(t.get("liquidity") or 0)))
    if not cands:
        raise RuntimeError(f"Token „{s}“ auf Solana nicht gefunden.")
    t = cands[0]
    return {"symbol": t.get("symbol"), "mint": t["id"], "dec": int(t.get("decimals") or 0), "cg": None,
            "verifiziert": bool(t.get("isVerified")), "name": t.get("name")}


def wallet_address():
    """Erste Solana-Adresse aus Apps → Krypto (öffentlich)."""
    for name, raw in ig._lines(ig.conf("crypto").get("wallets")).items():
        try:
            kind, addr = ig.chain_of(raw)
            if kind == "solana":
                return addr
        except Exception:
            pass
    return None


def _quote(inp, out, amount_raw, slip_bps):
    st, js, _ = ig._http("GET", f"{JUP}/swap/v1/quote?" + urllib.parse.urlencode(
        {"inputMint": inp["mint"], "outputMint": out["mint"], "amount": str(int(amount_raw)), "slippageBps": int(slip_bps),
         "restrictIntermediateTokens": "true"}))
    if st != 200 or not js or "outAmount" not in js:
        raise RuntimeError("Jupiter: kein Kurs für diesen Tausch (" + str((js or {}).get("error") or st) + ").")
    return js


def swap_prepare(from_token, to_token, amount, amount_in="token", slippage_pct=None):
    """Bereitet einen echten Tausch vor. Ausgeführt wird erst, wenn der Nutzer in Phantom unterschreibt."""
    d = _load()
    lim = d["limits"]
    inp, out = sol_token(from_token), sol_token(to_token)
    if inp["mint"] == out["mint"]:
        raise RuntimeError("Gleicher Token auf beiden Seiten.")
    amt = _num(amount)
    eur_in = None
    if inp["cg"]:
        try:
            eur_in_price = price_eur(inp["cg"])
            if amount_in == "eur":
                amt = amt / eur_in_price
            eur_in = amt * eur_in_price
        except Exception:
            if amount_in == "eur":
                raise
    elif amount_in == "eur":
        raise RuntimeError(f"Für {inp['symbol']} bitte die Menge in Token angeben.")
    slip = min(float(slippage_pct or lim.get("max_slippage_pct", 1.0)), 5.0)
    q = _quote(inp, out, round(amt * 10 ** inp["dec"]), round(slip * 100))
    out_amt = int(q["outAmount"]) / 10 ** out["dec"]
    min_out = int(q.get("otherAmountThreshold") or q["outAmount"]) / 10 ** out["dec"]
    impact = float(q.get("priceImpactPct") or 0) * 100
    warn = []
    if not inp["verifiziert"] or not out["verifiziert"]:
        warn.append("⚠️ Nicht verifizierter Token – häufig Betrug/Rug-Pull. Mint-Adresse genau prüfen!")
    if impact > 2:
        warn.append(f"⚠️ Hoher Preiseinfluss ({impact:.1f} %) – wenig Liquidität, du bekommst spürbar weniger.")
    if eur_in and eur_in > float(lim.get("max_swap_eur") or 1e12):
        warn.append(f"⚠️ Über deinem Limit von {lim['max_swap_eur']} € pro Tausch (Einstellungen im Trading-Fenster).")
    sid = secrets.token_urlsafe(9)
    route = " → ".join(dict.fromkeys(r.get("swapInfo", {}).get("label", "?") for r in q.get("routePlan") or [])) or "Jupiter"
    sw = {"id": sid, "zeit": time.time(), "von": inp, "nach": out, "menge": amt, "erwartet": out_amt, "minimum": min_out,
          "slippage_pct": slip, "preiseinfluss_pct": round(impact, 3), "route": route, "eur": round(eur_in, 2) if eur_in else None,
          "warnungen": warn, "quote": q, "status": "vorbereitet", "blockiert": bool(eur_in and eur_in > float(lim.get("max_swap_eur") or 1e12))}
    SWAPS[sid] = sw
    for k in [k for k, v in SWAPS.items() if time.time() - v["zeit"] > 3600]:
        SWAPS.pop(k, None)
    jup = f"https://jup.ag/swap/{inp['mint']}-{out['mint']}"
    return {"id": sid, "tausch": f"{_de(amt)} {inp['symbol']} → ca. {_de(out_amt)} {out['symbol']}",
            "mindestens": f"{_de(min_out)} {out['symbol']} (Slippage {_de(slip)} %)", "wert_eur": sw["eur"], "route": route,
            "preiseinfluss_%": round(impact, 3), "warnungen": warn, "blockiert": sw["blockiert"],
            "phantom_seite": f"/swap?id={sid}", "jupiter_link": jup,
            "phantom_handy": "https://phantom.app/ul/browse/" + urllib.parse.quote(jup, safe="") + "?ref=" + urllib.parse.quote("https://jup.ag", safe=""),
            "so_gehts": f"Noch NICHTS passiert. Gib dem Nutzer GENAU diesen Link: [In Phantom bestätigen](/swap?id={sid}) – am PC öffnet "
                        f"er eine Seite im Browser, Phantom zeigt den Tausch noch einmal, erst seine Unterschrift führt ihn aus. Am Handy/Telegram "
                        f"stattdessen den Link phantom_handy (öffnet Jupiter in der Phantom-App; Betrag dort eintragen). Nenne Warnungen deutlich."}


def swap_transaction(sid, pubkey):
    """Baut die unsignierte Transaktion (Jupiter) für die Phantom-Adresse des Nutzers."""
    sw = SWAPS.get(sid)
    if not sw:
        raise RuntimeError("Tausch abgelaufen – bitte neu vorbereiten.")
    if sw["blockiert"]:
        raise RuntimeError(f"Über deinem Limit pro Tausch – Limit im Trading-Fenster erhöhen oder Betrag verkleinern.")
    if not re.fullmatch(ig.B58 + r"{32,44}", str(pubkey or "")):
        raise RuntimeError("Ungültige Wallet-Adresse.")
    q = sw["quote"]
    if time.time() - sw["zeit"] > 25:  # Kurs auffrischen
        q = _quote(sw["von"], sw["nach"], int(q["inAmount"]), round(sw["slippage_pct"] * 100))
        new_out = int(q["outAmount"]) / 10 ** sw["nach"]["dec"]
        if new_out < sw["minimum"]:
            raise RuntimeError(f"Kurs hat sich verschlechtert (jetzt ca. {_de(new_out)} {sw['nach']['symbol']}) – bitte neu vorbereiten.")
        sw["quote"], sw["zeit"], sw["erwartet"] = q, time.time(), new_out
    st, js, _ = ig._http("POST", f"{JUP}/swap/v1/swap", json_body={
        "quoteResponse": q, "userPublicKey": pubkey, "wrapAndUnwrapSol": True, "dynamicComputeUnitLimit": True,
        "prioritizationFeeLamports": {"priorityLevelWithMaxLamports": {"maxLamports": 2_000_000, "priorityLevel": "high"}}}, timeout=30)
    if st != 200 or not js or not js.get("swapTransaction"):
        raise RuntimeError("Jupiter konnte die Transaktion nicht bauen (" + str((js or {}).get("error") or st) + ").")
    sw["status"] = "an Phantom übergeben"
    sw["wallet"] = pubkey
    return {"tx": js["swapTransaction"], "erwartet": sw["erwartet"], "symbol": sw["nach"]["symbol"]}


def swap_done(sid, signature, ok=True, error=""):
    sw = SWAPS.get(sid) or {}
    entry = {"zeit": _now(), "tausch": f"{_de(sw.get('menge', 0))} {sw.get('von', {}).get('symbol', '?')} → "
                                       f"{_de(sw.get('erwartet', 0))} {sw.get('nach', {}).get('symbol', '?')}",
             "eur": sw.get("eur"), "ok": bool(ok), "fehler": str(error)[:200]}
    if signature and re.fullmatch(ig.B58 + r"{64,90}", str(signature)):
        entry["link"] = f"https://solscan.io/tx/{signature}"
    if sw:
        sw["status"] = "ausgeführt" if ok else "abgebrochen"
    with LOCK:
        d = _load()
        d["swaps"] = (d["swaps"] + [entry])[-100:]
        _save(d)
    return entry


def swap_public(sid):
    sw = SWAPS.get(sid)
    if not sw:
        return None
    return {k: sw[k] for k in ("id", "menge", "erwartet", "minimum", "slippage_pct", "preiseinfluss_pct", "route", "eur", "warnungen",
                               "status", "blockiert")} | {"von": sw["von"]["symbol"], "nach": sw["nach"]["symbol"],
                                                        "von_mint": sw["von"]["mint"], "nach_mint": sw["nach"]["mint"],
                                                        "erwartete_wallet": wallet_address()}


def set_limits(max_swap_eur=None, max_slippage_pct=None):
    with LOCK:
        d = _load()
        if max_swap_eur is not None:
            d["limits"]["max_swap_eur"] = _num(max_swap_eur, "Limit")
        if max_slippage_pct is not None:
            d["limits"]["max_slippage_pct"] = min(5.0, _num(max_slippage_pct, "Slippage"))
        _save(d)
        return d["limits"]


def overview():
    d = _load()
    return {"depot": portfolio(d), "orders": d["orders"], "swaps": d["swaps"][-15:][::-1], "limits": d["limits"],
            "wallet": wallet_address(), "tokens": list(SOL_TOKENS)}
