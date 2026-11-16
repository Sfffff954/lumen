"""Lumen – Lern-Trainer.

1) Karteikarten mit täglicher Wiederholung (Spaced Repetition, an SM-2 angelehnt): Stapel, fällige Karten, Bewertung.
2) Hacking-Lernpfad: Cybersecurity Schritt für Schritt – Lumen ist der Lehrer, geübt wird nur am eigenen PC / in legalen
   Übungsumgebungen. Fortschritt wird hier gespeichert.
"""
import json
import secrets
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path

DATA = Path.home() / ".lumen" / "trainer.json"
LOCK = threading.RLock()


def _load():
    try:
        d = json.loads(DATA.read_text("utf-8"))
    except Exception:
        d = {}
    d.setdefault("decks", {})      # id -> {"name", "cards": [..], "seit"}
    d.setdefault("path", {})       # lesson_id -> {"punkte", "am"}
    d.setdefault("log", {})        # "YYYY-MM-DD" -> Anzahl gelernter Karten
    return d


def _save(d):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(DATA)


def _today():
    return date.today().isoformat()


# ================================================================ Karteikarten
def _find_deck(d, deck, create=False):
    name = str(deck or "").strip()[:60]
    if name in d["decks"]:
        return name, d["decks"][name]
    for k, v in d["decks"].items():
        if v["name"].lower() == name.lower():
            return k, v
    if not create:
        raise RuntimeError(f"Stapel „{name}“ gibt es nicht. Vorhanden: " + (", ".join(v["name"] for v in d["decks"].values()) or "keine"))
    if not name:
        raise RuntimeError("Der Stapel braucht einen Namen.")
    if len(d["decks"]) >= 100:
        raise RuntimeError("Maximal 100 Stapel.")
    k = secrets.token_hex(4)
    d["decks"][k] = {"name": name, "cards": [], "seit": _today()}
    return k, d["decks"][k]


def add_cards(deck, cards):
    """cards: [{"vorne": …, "hinten": …}] – legt den Stapel bei Bedarf an, Doppelte werden übersprungen."""
    if not isinstance(cards, list) or not cards:
        raise RuntimeError("Keine Karten übergeben.")
    with LOCK:
        d = _load()
        k, dk = _find_deck(d, deck, create=True)
        have = {c["vorne"].strip().lower() for c in dk["cards"]}
        n = 0
        for c in cards[:300]:
            v, h = str(c.get("vorne") or c.get("front") or "").strip()[:500], str(c.get("hinten") or c.get("back") or "").strip()[:1500]
            if not v or not h or v.lower() in have:
                continue
            have.add(v.lower())
            dk["cards"].append({"id": secrets.token_hex(4), "vorne": v, "hinten": h, "due": _today(), "iv": 0, "ease": 2.5, "reps": 0, "lapses": 0})
            n += 1
        if len(dk["cards"]) > 3000:
            raise RuntimeError("Ein Stapel fasst höchstens 3000 Karten.")
        _save(d)
    return {"stapel": dk["name"], "id": k, "neu": n, "gesamt": len(dk["cards"]),
            "text": f"{n} neue Karten im Stapel „{dk['name']}“ ({len(dk['cards'])} gesamt). Lernen: Karte 🎓 Lernen oder /lernen in Telegram."}


def delete_deck(deck):
    with LOCK:
        d = _load()
        k, dk = _find_deck(d, deck)
        d["decks"].pop(k)
        _save(d)
    return f"Stapel „{dk['name']}“ gelöscht."


def delete_card(card_id):
    with LOCK:
        d = _load()
        for dk in d["decks"].values():
            n = len(dk["cards"])
            dk["cards"] = [c for c in dk["cards"] if c["id"] != card_id]
            if len(dk["cards"]) < n:
                _save(d)
                return "Karte gelöscht."
    return "Karte nicht gefunden."


def _due(dk, today=None):
    today = today or _today()
    return [c for c in dk["cards"] if c["due"] <= today]


def due_count():
    d = _load()
    return sum(len(_due(dk)) for dk in d["decks"].values())


def next_card(deck=None):
    """Nächste fällige Karte (optional aus einem Stapel). None, wenn nichts fällig."""
    d = _load()
    best = None
    for k, dk in d["decks"].items():
        if deck and deck not in (k, dk["name"]):
            continue
        for c in _due(dk):
            key = (c["due"], c["reps"])
            if best is None or key < best[0]:
                best = (key, k, dk, c)
    if not best:
        return None
    _, k, dk, c = best
    return {"id": c["id"], "stapel": dk["name"], "stapel_id": k, "vorne": c["vorne"], "hinten": c["hinten"],
            "noch_fällig": sum(len(_due(x)) for kk, x in d["decks"].items() if not deck or deck in (kk, x["name"]))}


GRADES = {0: "nochmal", 1: "schwer", 2: "gut", 3: "leicht"}


def grade(card_id, g):
    """Bewertung 0 = nochmal, 1 = schwer, 2 = gut, 3 = leicht → nächster Termin."""
    g = int(g)
    if g not in GRADES:
        raise RuntimeError("Bewertung 0–3.")
    with LOCK:
        d = _load()
        for dk in d["decks"].values():
            for c in dk["cards"]:
                if c["id"] != card_id:
                    continue
                if g == 0:
                    c["lapses"] += 1
                    c["reps"] = 0
                    c["iv"] = 0
                    c["ease"] = max(1.3, c["ease"] - 0.2)
                else:
                    c["reps"] += 1
                    if c["iv"] == 0:
                        c["iv"] = {1: 1, 2: 1, 3: 3}[g]
                    elif c["reps"] == 2 and c["iv"] <= 1:
                        c["iv"] = {1: 2, 2: 3, 3: 6}[g]
                    else:
                        c["iv"] = max(c["iv"] + 1, round(c["iv"] * {1: 1.2, 2: c["ease"], 3: c["ease"] * 1.3}[g]))
                    c["ease"] = min(3.0, max(1.3, c["ease"] + {1: -0.15, 2: 0.0, 3: 0.15}[g]))
                    c["iv"] = min(c["iv"], 365)
                c["due"] = (date.today() + timedelta(days=c["iv"])).isoformat()
                d["log"][_today()] = d["log"].get(_today(), 0) + 1
                for k in sorted(d["log"])[:-60]:
                    d["log"].pop(k)
                _save(d)
                return {"nächste_in_tagen": c["iv"], "text": "Kommt gleich nochmal." if g == 0 else f"Wieder in {c['iv']} Tag{'en' if c['iv'] != 1 else ''}."}
    raise RuntimeError("Karte nicht gefunden.")


def streak(d=None):
    d = d or _load()
    n, day = 0, date.today()
    if _today() not in d["log"]:
        day -= timedelta(days=1)
    while day.isoformat() in d["log"]:
        n += 1
        day -= timedelta(days=1)
    return n


def overview():
    d = _load()
    decks = []
    for k, dk in d["decks"].items():
        cards = dk["cards"]
        decks.append({"id": k, "name": dk["name"], "karten": len(cards), "fällig": len(_due(dk)),
                      "neu": sum(1 for c in cards if c["reps"] == 0 and c["lapses"] == 0),
                      "sicher": sum(1 for c in cards if c["iv"] >= 21)})
    decks.sort(key=lambda x: (-x["fällig"], x["name"].lower()))
    return {"stapel": decks, "fällig": sum(x["fällig"] for x in decks), "heute_gelernt": d["log"].get(_today(), 0), "serie_tage": streak(d),
            "pfad": path_view(d)}


def deck_cards(deck):
    d = _load()
    k, dk = _find_deck(d, deck)
    return {"id": k, "name": dk["name"], "karten": [{"id": c["id"], "vorne": c["vorne"], "hinten": c["hinten"], "due": c["due"], "iv": c["iv"]} for c in dk["cards"]]}


# ================================================================ Hacking-Lernpfad
PATH = [
    ("grundlagen", "🧭 Grundlagen & Denkweise", [
        ("g1", "Was ist Hacking wirklich?", "White-, Grey- und Black-Hat, Berufe (Pentester, Blue Team, Bug Bounty), wie ein Angriff grob abläuft.", "Finde drei echte Sicherheitsvorfälle aus den Nachrichten und ordne sie ein: Was war die Ursache?"),
        ("g2", "Recht & Ethik", "Was erlaubt ist (eigene Geräte, schriftliche Erlaubnis, Übungsplattformen) und was strafbar ist (§202a–c StGB u. ä.). Responsible Disclosure.", "Schreib in eigenen Worten auf: Was darf ich testen? Lumen prüft deine Liste."),
        ("g3", "Deine Übungsumgebung", "Legal üben: eigene VM, Docker-Labor (Juice Shop, DVWA), Plattformen wie TryHackMe, Hack The Box, OverTheWire, picoCTF.", "Starte OWASP Juice Shop lokal in Docker (nur auf 127.0.0.1) – Lumen hilft dir Schritt für Schritt."),
        ("g4", "Das CIA-Dreieck & Bedrohungsmodelle", "Vertraulichkeit, Integrität, Verfügbarkeit; wer greift wen warum an; Angriffsfläche erkennen.", "Erstelle ein kleines Bedrohungsmodell für deinen eigenen PC und dein Heimnetz."),
    ]),
    ("linux", "🐧 Linux & Terminal", [
        ("l1", "Terminal-Grundlagen", "Dateisystem, Navigation, Pipes, grep/find/less, Hilfe mit man und --help.", "Finde mit find und grep alle Dateien in ~/Downloads, die größer als 50 MB sind, und zähle sie."),
        ("l2", "Rechte, Benutzer & sudo", "rwx, chmod/chown, Gruppen, SUID, warum Root gefährlich ist.", "Suche auf deinem PC nach SUID-Programmen und lass dir von Lumen erklären, wofür zwei davon da sind."),
        ("l3", "Prozesse, Dienste & Logs", "ps, top, systemctl, journalctl – erkennen, was auf dem System läuft und was passiert ist.", "Finde heraus, welche Dienste beim Start laufen und wer sich zuletzt angemeldet hat."),
        ("l4", "Bash-Skripte", "Variablen, Schleifen, Bedingungen – kleine Werkzeuge selbst bauen.", "Schreib ein Skript, das dir täglich die 5 größten Ordner in deinem Home zeigt."),
    ]),
    ("netz", "🌐 Netzwerke", [
        ("n1", "IP, Ports & Protokolle", "IPv4/IPv6, Subnetze, TCP vs. UDP, die wichtigsten Ports, DNS, DHCP.", "Finde deine IP, dein Gateway und deinen DNS-Server heraus und erklär, was jeder davon tut."),
        ("n2", "Mitlesen mit Wireshark", "Pakete aufzeichnen und verstehen: Handshake, DNS-Anfrage, HTTP vs. HTTPS – nur im eigenen Netz.", "Zeichne den Aufruf einer Webseite auf deinem eigenen PC auf und finde DNS-Anfrage und TLS-Handshake."),
        ("n3", "Scannen mit nmap", "Host-Erkennung, Port-Scan, Dienst-Erkennung – und warum man nur eigene Geräte scannt.", "Scanne deinen eigenen PC und deinen Router (Lumen: „Wer ist in meinem WLAN?“) und deute das Ergebnis."),
        ("n4", "Firewall & Absicherung", "ufw/nftables, unnötige Dienste abschalten, SSH härten, VPN-Grundlagen.", "Mach den PC-Check in der Sicherheits-Zentrale und behebe mindestens eine Warnung."),
    ]),
    ("web", "🕸 Web-Sicherheit", [
        ("w1", "Wie das Web funktioniert", "HTTP-Anfragen, Header, Cookies, Sessions, Same-Origin-Policy, Entwicklerwerkzeuge im Browser.", "Sieh dir im Browser (F12 → Netzwerk) an, welche Anfragen eine Seite stellt und welche Cookies sie setzt."),
        ("w2", "OWASP Top 10 im Überblick", "Die häufigsten Schwachstellen-Klassen und wie man sie verhindert.", "Ordne fünf Aufgaben aus deinem lokalen Juice Shop den OWASP-Kategorien zu."),
        ("w3", "Injection & XSS verstehen", "Warum ungeprüfte Eingaben gefährlich sind – ausprobieren nur im eigenen Juice-Shop-Labor – und wie Entwickler sich schützen.", "Löse im lokalen Juice Shop eine 1-Sterne-Aufgabe und erklär danach, wie man die Lücke schließt."),
        ("w4", "Anmeldung & Zugriffskontrolle", "Passwort-Hashing, Sessions, 2FA, typische Fehler (IDOR, schwache Reset-Links) und Gegenmaßnahmen.", "Prüfe mit dem Domain-Report deine eigene Seite oder eine Seite, die du betreust, und deute die Sicherheits-Header."),
    ]),
    ("krypto", "🔐 Passwörter & Kryptografie", [
        ("k1", "Hashes, Salz & Passwörter", "Hash vs. Verschlüsselung, Salt, warum lange Passphrasen gewinnen, Passwort-Manager, 2FA/Passkeys.", "Prüfe eines deiner alten Passwörter in Lumen („Passwort prüfen“) und richte irgendwo 2FA ein."),
        ("k2", "Symmetrisch & asymmetrisch", "AES, RSA/ECC, Schlüsselaustausch, Signaturen – was TLS damit macht.", "Erzeuge ein SSH-Schlüsselpaar mit Passphrase und erklär, was der öffentliche Teil darf."),
        ("k3", "Zertifikate & TLS", "Zertifikatskette, Let's Encrypt, was das Schloss im Browser bedeutet – und was nicht.", "Sieh dir mit Lumen (SSL-Check) das Zertifikat einer bekannten Seite an und erklär die Kette."),
    ]),
    ("funk", "📡 Funk & Hardware", [
        ("f1", "Funk-Grundlagen", "Frequenz, Bandbreite, Modulation (AM/FM/digital), Antennen, was ein SDR ist. Rechtliches: nur empfangen, was für alle bestimmt ist.", "Mach mit dem HackRF einen Spektrum-Scan im UKW-Band und finde den stärksten Sender."),
        ("f2", "Das Spektrum lesen", "Wer funkt wo: Rundfunk, Mobilfunk, WLAN, ISM-Bänder – und wie man Signale im Wasserfall erkennt.", "Scanne 433 und 868 MHz und teste, ob deine eigene Funkfernbedienung sendet (Signal-Test)."),
        ("f3", "ADS-B & Rundfunk empfangen", "Wie Flugzeuge ihre Position senden und wie FM-Radio demoduliert wird.", "Hör mit Lumen einen UKW-Sender und sieh dir die Flugzeuge über dir an."),
        ("f4", "USB & Hardware-Sicherheit", "BadUSB, warum fremde Sticks gefährlich sind, USB-Wächter, Firmware, physischer Zugriff.", "Sieh dir in der Sicherheits-Zentrale deine USB-Geräte an und erklär, woran man eine falsche Tastatur erkennt."),
    ]),
    ("verteidigung", "🛡 Verteidigen & Weiterlernen", [
        ("v1", "Phishing & Social Engineering erkennen", "Typische Tricks, Absender prüfen, Links aufklappen, was im Ernstfall zu tun ist.", "Lass Lumen eine verdächtige Mail aus deinem Spam-Ordner prüfen und nenne drei Warnzeichen."),
        ("v2", "Malware & Vorfälle", "Arten von Schadsoftware, Backups (3-2-1), was tun, wenn es passiert ist.", "Prüfe, ob du ein funktionierendes Backup deiner wichtigsten Dateien hast – und stell eine Datei daraus wieder her."),
        ("v3", "CTFs & nächste Schritte", "Wie Capture-the-Flag-Wettbewerbe funktionieren, Lernplattformen, Zertifikate (z. B. eJPT, Security+), Bug-Bounty-Regeln.", "Löse Level 0–3 von OverTheWire Bandit und erzähl Lumen, was du gelernt hast."),
    ]),
]
LESSONS = {lid: (mod, title, goal, task) for mod, _, ls in PATH for lid, title, goal, task in ls}


def path_view(d=None):
    d = d or _load()
    mods, done_total, total = [], 0, 0
    nxt = None
    for mid, mtitle, ls in PATH:
        lessons = []
        for lid, title, goal, task in ls:
            p = d["path"].get(lid)
            total += 1
            done_total += bool(p)
            if not p and not nxt:
                nxt = lid
            lessons.append({"id": lid, "titel": title, "ziel": goal, "übung": task, "fertig": bool(p), "punkte": (p or {}).get("punkte"), "am": (p or {}).get("am")})
        mods.append({"id": mid, "titel": mtitle, "lektionen": lessons, "fertig": sum(1 for x in lessons if x["fertig"])})
    return {"module": mods, "fertig": done_total, "gesamt": total, "nächste": nxt}


def lesson_prompt(lid):
    if lid not in LESSONS:
        raise RuntimeError("Lektion unbekannt.")
    mod, title, goal, task = LESSONS[lid]
    return (f"Hacking-Lernpfad, Lektion {lid}: „{title}“. Sei mein geduldiger Lehrer. Inhalt: {goal}\n"
            f"Ablauf: 1) Erklär es mir einfach, mit Beispielen aus dem Alltag, in kleinen Häppchen – frag zwischendurch, ob ich mitkomme. "
            f"2) Praxis-Übung nur an meinem eigenen PC/Netz oder einer legalen Übungsumgebung: {task} Hilf mir dabei Schritt für Schritt. "
            f"3) Stell mir danach 5 Quizfragen, eine nach der anderen, und sag mir jeweils, ob es stimmt. "
            f"4) Am Ende: ruf lesson_done mit lesson_id=\"{lid}\" und meiner Punktzahl (0–5) auf und leg für alles, was ich falsch hatte oder "
            f"was wichtig ist, 3–6 Karteikarten mit flashcards_add im Stapel „Hacking“ an. Fang jetzt mit Schritt 1 an.")


def lesson_done(lid, score=None):
    lid = str(lid).strip().lower()
    if lid not in LESSONS:
        raise RuntimeError("Lektion unbekannt. Gültig: " + ", ".join(LESSONS))
    try:
        score = max(0, min(5, int(score))) if score is not None else None
    except (TypeError, ValueError):
        score = None
    with LOCK:
        d = _load()
        d["path"][lid] = {"punkte": score, "am": datetime.now().strftime("%d.%m.%Y")}
        _save(d)
    v = path_view(d)
    nxt = LESSONS.get(v["nächste"] or "", (None, None))[1]
    return {"text": f"Lektion „{LESSONS[lid][1]}“ abgeschlossen" + (f" ({score}/5)" if score is not None else "") + f". Fortschritt: {v['fertig']}/{v['gesamt']}."
                    + (f" Als Nächstes: „{nxt}“." if nxt else " 🎉 Lernpfad komplett!"), "fortschritt": f"{v['fertig']}/{v['gesamt']}", "nächste": v["nächste"]}


def lesson_reset(lid=None):
    with LOCK:
        d = _load()
        if lid:
            d["path"].pop(lid, None)
        else:
            d["path"] = {}
        _save(d)
    return "Zurückgesetzt."
