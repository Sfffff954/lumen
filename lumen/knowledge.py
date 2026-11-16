"""
Lumen – Wissens-Bibliothek. PDFs, Word, EPUB, Texte und Webseiten aufnehmen, durchsuchen (BM25, offline, ohne
Zusatzpakete) und daraus lernen: Zusammenfassung, Karteikarten, Quiz – und auf Wunsch Trainingsbeispiele für Lumens KI.
Alles liegt lokal in ~/.lumen/wissen/.
"""
import html
import io
import json
import math
import re
import secrets
import shutil
import threading
import time
import zipfile
from collections import Counter
from pathlib import Path

import files

DIR = Path.home() / ".lumen" / "wissen"
INDEX = DIR / "index.json"
LOCK = threading.Lock()
CHUNK = 1400
_cache = {"stamp": None, "docs": None, "chunks": None, "df": None, "avg": 1}

STOP = set("""der die das und oder aber ein eine einer eines einem einen ist sind war waren wird werden wurde nicht kein keine
mit von zu zum zur im in an am auf aus bei für über unter vor nach als wie wo was wer wem wen ich du er sie es wir ihr
mich dich sich uns euch mein dein sein ihr unser euer dass daß so auch noch nur schon sehr mehr man hat haben habe hatte
the a an and or of to in on for is are was were be by with as at from this that it its""".split())


# ---------------------------------------------------------------- Text holen
def _epub(path):
    z = zipfile.ZipFile(path)
    names = [n for n in z.namelist() if n.lower().endswith((".xhtml", ".html", ".htm"))]
    try:  # Lesereihenfolge aus content.opf
        opf = next(n for n in z.namelist() if n.endswith(".opf"))
        o = z.read(opf).decode("utf-8", "replace")
        base = opf.rsplit("/", 1)[0] + "/" if "/" in opf else ""
        hrefs = dict(re.findall(r'<item[^>]*id="([^"]+)"[^>]*href="([^"]+)"', o))
        hrefs.update({k: v for v, k in re.findall(r'<item[^>]*href="([^"]+)"[^>]*id="([^"]+)"', o)})
        order = [base + hrefs[i] for i in re.findall(r'<itemref[^>]*idref="([^"]+)"', o) if i in hrefs]
        names = [n for n in order if n in z.namelist()] or names
    except StopIteration:
        pass
    parts = []
    for i, n in enumerate(names):
        raw = z.read(n).decode("utf-8", "replace")
        raw = re.sub(r"(?is)<(script|style|head).*?</\1>", " ", raw)
        raw = re.sub(r"(?i)<h[1-3][^>]*>", "\n## ", raw)
        raw = re.sub(r"(?i)</(p|div|h\d|li)>|<br\s*/?>", "\n", raw)
        t = html.unescape(re.sub(r"<[^>]+>", "", raw))
        t = re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", t)).strip()
        if t:
            parts.append(f"--- Abschnitt {i + 1} ---\n{t}")
    return "\n\n".join(parts)


def extract(path):
    """→ (text, hinweis). PDF-Seiten als '--- Seite N ---'."""
    path = Path(path)
    if path.suffix.lower() == ".epub":
        try:
            return _epub(path), ""
        except Exception as e:
            return "", f"EPUB konnte nicht gelesen werden: {e}"
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return "", "pypdf fehlt (pip install pypdf)."
        try:
            reader = PdfReader(io.BytesIO(path.read_bytes()))
            parts = []
            for i, page in enumerate(reader.pages[:2000]):
                t = (page.extract_text() or "").strip()
                if t:
                    parts.append(f"--- Seite {i + 1} ---\n{t}")
            text = "\n\n".join(parts)
            return text, "" if text.strip() else "PDF enthält keinen Text (eingescannt? Dann bitte erst per OCR umwandeln)."
        except Exception as e:
            return "", f"PDF konnte nicht gelesen werden: {e}"
    if path.suffix.lower() in (".html", ".htm"):
        try:
            import web
            return web.html_to_text(path.read_text("utf-8", "replace"))[0], ""
        except Exception:
            pass
    return files.extract_text(path)


# ---------------------------------------------------------------- Bibliothek
def _load():
    try:
        return json.loads(INDEX.read_text("utf-8"))
    except Exception:
        return {"docs": []}


def _save(d):
    DIR.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    _cache["stamp"] = None


def _chunks(text):
    """Text → Stücke (~1400 Zeichen) mit Seitenangabe."""
    out, page = [], None
    sections = re.split(r"(--- (?:Seite|Abschnitt) \d+ ---)", text)
    cur_label = None
    for sec in sections:
        m = re.match(r"--- (Seite|Abschnitt) (\d+) ---", sec)
        if m:
            cur_label = f"{'S.' if m.group(1) == 'Seite' else 'Abschn.'} {m.group(2)}"
            continue
        paras = [p.strip() for p in re.split(r"\n\s*\n", sec) if p.strip()]
        buf = ""
        for p in paras:
            while len(p) > CHUNK * 1.5:  # sehr lange Absätze teilen
                cut = p.rfind(". ", 0, CHUNK) + 1 or CHUNK
                if buf:
                    out.append((cur_label, buf))
                    buf = ""
                out.append((cur_label, p[:cut].strip()))
                p = p[cut:].strip()
            if len(buf) + len(p) > CHUNK and buf:
                out.append((cur_label, buf))
                buf = ""
            buf = (buf + "\n\n" + p).strip()
        if buf:
            out.append((cur_label, buf))
    return [{"ort": lbl, "text": t} for lbl, t in out if len(t) > 30]


def add_text(title, text, source, kind="text"):
    text = text.replace("\x00", "")
    if len(text.strip()) < 50:
        raise RuntimeError("Zu wenig Text gefunden.")
    did = secrets.token_hex(4)
    chunks = _chunks(text)
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / f"{did}.json").write_text(json.dumps({"text": text, "chunks": chunks}, ensure_ascii=False), "utf-8")
    pages = len(re.findall(r"--- Seite \d+ ---", text))
    doc = {"id": did, "titel": title[:120], "quelle": str(source)[:500], "art": kind, "zeichen": len(text),
           "seiten": pages or None, "stücke": len(chunks), "hinzugefügt": time.time(), "wörter": len(text.split())}
    with LOCK:
        d = _load()
        old = [x for x in d["docs"] if x.get("quelle") == doc["quelle"] or (x["titel"] == doc["titel"] and x["zeichen"] == doc["zeichen"])]
        for x in old:
            (DIR / f"{x['id']}.json").unlink(missing_ok=True)
        d["docs"] = [x for x in d["docs"] if x not in old] + [doc]
        _save(d)
    return doc


def add_file(path, title=None):
    path = Path(path).expanduser()
    if not path.is_file():
        raise RuntimeError(f"{path} ist keine Datei.")
    text, hint = extract(path)
    if not text.strip():
        raise RuntimeError(hint or "Kein Text in der Datei gefunden.")
    name = title or re.sub(r"-[0-9a-f]{4}$", "", re.sub(r"^[0-9a-f]{8,12}_", "", path.stem))
    return add_text(name.replace("_", " "), text, str(path), path.suffix.lstrip(".").lower() or "text")


def add_url(url):
    import web
    res = web.read_webpage(url, max_chars=2_000_000)
    return add_text(res.get("titel") or url, res["text"], res.get("url") or url, "web")


def add(source):
    s = str(source or "").strip()
    if re.match(r"^https?://", s):
        return add_url(s)
    return add_file(s)


def docs():
    return sorted(_load()["docs"], key=lambda x: -x.get("hinzugefügt", 0))


def get(did):
    doc = next((x for x in _load()["docs"] if x["id"] == did), None)
    if not doc:
        raise RuntimeError("Dokument nicht gefunden.")
    data = json.loads((DIR / f"{did}.json").read_text("utf-8"))
    return doc, data


def remove(did):
    with LOCK:
        d = _load()
        d["docs"] = [x for x in d["docs"] if x["id"] != did]
        _save(d)
    (DIR / f"{did}.json").unlink(missing_ok=True)
    return True


def find_doc(name_or_id):
    q = str(name_or_id or "").strip().lower()
    ds = docs()
    for x in ds:
        if x["id"] == q or x["titel"].lower() == q:
            return x
    return next((x for x in ds if q and q in x["titel"].lower()), None)


def summary_line():
    ds = docs()
    if not ds:
        return "noch leer"
    names = ", ".join(f"„{x['titel'][:40]}“" for x in ds[:12])
    return f"{len(ds)} Dokumente: {names}" + (" …" if len(ds) > 12 else "")


# ---------------------------------------------------------------- Suche (BM25)
def _words(t):
    return [w for w in re.findall(r"[a-zäöüß0-9]{2,}", t.lower()) if w not in STOP]


def _stem(w):
    for suf in ("ungen", "heiten", "keiten", "ungen", "ern", "en", "er", "es", "e", "s", "n"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _index():
    stamp = INDEX.stat().st_mtime if INDEX.exists() else 0
    if _cache["stamp"] == stamp:
        return _cache
    chunks, df = [], Counter()
    for doc in docs():
        try:
            data = json.loads((DIR / f"{doc['id']}.json").read_text("utf-8"))
        except Exception:
            continue
        for i, c in enumerate(data["chunks"]):
            tf = Counter(_stem(w) for w in _words(c["text"]))
            chunks.append({"doc": doc, "i": i, "ort": c["ort"], "text": c["text"], "tf": tf, "len": sum(tf.values()) or 1})
            df.update(tf.keys())
    _cache.update(stamp=stamp, chunks=chunks, df=df, avg=(sum(c["len"] for c in chunks) / len(chunks)) if chunks else 1)
    return _cache


def search(query, k=6, doc=None):
    idx = _index()
    if not idx["chunks"]:
        return []
    qs = [_stem(w) for w in _words(query)]
    N = len(idx["chunks"])
    target = find_doc(doc) if doc else None
    scored = []
    for c in idx["chunks"]:
        if target and c["doc"]["id"] != target["id"]:
            continue
        s = 0.0
        for q in qs:
            f = c["tf"].get(q, 0)
            if f:
                idf = math.log(1 + (N - idx["df"][q] + 0.5) / (idx["df"][q] + 0.5))
                s += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * c["len"] / idx["avg"]))
        if s > 0:
            scored.append((s, c))
    scored.sort(key=lambda x: -x[0])
    return [{"dokument": c["doc"]["titel"], "stelle": c["ort"] or f"Teil {c['i'] + 1}", "text": c["text"],
             "punkte": round(s, 2)} for s, c in scored[:k]]


def sample_text(did, max_chars=24000):
    """Gleichmäßig über das ganze Dokument verteilte Stücke (für Quiz/Karteikarten)."""
    doc, data = get(did)
    ch = data["chunks"]
    if sum(len(c["text"]) for c in ch) <= max_chars:
        picked = ch
    else:
        n = max(1, max_chars // CHUNK)
        step = len(ch) / n
        picked = [ch[int(i * step)] for i in range(n)]
    return doc, "\n\n".join(f"[{c['ort'] or 'Teil'}] {c['text']}" for c in picked)


def parts_for_summary(did, size=14000):
    doc, data = get(did)
    groups, buf = [], ""
    for c in data["chunks"]:
        if len(buf) + len(c["text"]) > size and buf:
            groups.append(buf)
            buf = ""
        buf += f"\n\n[{c['ort'] or 'Teil'}] {c['text']}"
    if buf:
        groups.append(buf)
    return doc, groups


# ---------------------------------------------------------------- Lernen (Prompts)
def quiz_prompt(title, text, n=10, level="mittel"):
    return (f"Erstelle aus diesem Lernstoff („{title}“) ein Quiz mit {n} Multiple-Choice-Fragen auf Deutsch, Schwierigkeit: {level}. "
            "Je Frage 4 Antworten, genau eine richtig, plausible falsche Antworten. Fragen über das ganze Material verteilt, "
            "Verständnis statt Auswendiglernen. Erklärung in 1–2 Sätzen mit Fundstelle.\n"
            'Gib NUR JSON zurück: {"fragen":[{"frage":"…","antworten":["…","…","…","…"],"richtig":0,"erklaerung":"…","stelle":"S. 3"}]}\n\n'
            f"LERNSTOFF:\n{text}")


def cards_prompt(title, text, n=20):
    return (f"Erstelle aus diesem Lernstoff („{title}“) {n} Karteikarten auf Deutsch: vorne eine klare Frage oder ein Begriff, "
            "hinten eine kurze, vollständige Antwort (1–3 Sätze). Die wichtigsten Begriffe, Fakten und Zusammenhänge.\n"
            'Gib NUR JSON zurück: {"karten":[{"vorne":"…","hinten":"…","stelle":"S. 3"}]}\n\n'
            f"LERNSTOFF:\n{text}")


def summary_prompt(title, text, part=None, total=None):
    where = f" (Teil {part} von {total})" if total and total > 1 else ""
    return (f"Fasse diesen Text aus „{title}“{where} auf Deutsch zusammen: die wichtigsten Aussagen, Begriffe und Zahlen als "
            "gut gegliederte Stichpunkte mit Zwischenüberschriften. Nichts erfinden, Seitenzahlen in Klammern wo hilfreich.\n\n"
            f"TEXT:\n{text}")


def merge_prompt(title, parts):
    return (f"Hier sind Teil-Zusammenfassungen von „{title}“. Mach daraus EINE übersichtliche Zusammenfassung in Markdown: "
            "# Titel, **Kurzfassung** (3–5 Sätze), dann ## Abschnitte mit den wichtigsten Punkten, am Ende ## Die 10 wichtigsten "
            "Begriffe (Begriff – Erklärung). Nichts erfinden.\n\n" + "\n\n---\n\n".join(parts))


def training_prompt(aname, persona, title, text, k=8):
    return (f"Erzeuge {k} realistische Übungsgespräche auf Deutsch zwischen einem Nutzer und {aname} (persönlicher KI-Assistent) "
            f"über den Inhalt von „{title}“. {aname}s Art: {persona}\n"
            f"Der Nutzer fragt so, wie man wirklich fragt (kurz, umgangssprachlich); {aname} antwortet korrekt NUR auf Basis des "
            "Textes, erklärt verständlich und nennt bei Bedarf die Quelle (Dokument/Seite). Keine PC-Aktionen.\n"
            'Gib NUR JSON zurück: {"gespraeche":[[{"role":"user","content":"…"},{"role":"assistant","content":"…"}]]}\n\n'
            f"TEXT:\n{text}")


def parse_json(text, key):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise RuntimeError("Die KI hat kein gültiges Ergebnis geliefert – bitte nochmal versuchen.")
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        # häufig: abgeschnittenes JSON – bis zum letzten vollständigen Objekt retten
        t = m.group(0)
        cut = t.rfind("},")
        try:
            d = json.loads(t[:cut + 1] + "]}") if cut > 0 else {}
        except json.JSONDecodeError:
            raise RuntimeError("Die KI hat kein gültiges Ergebnis geliefert – bitte nochmal versuchen.")
    items = d.get(key) or []
    if not items:
        raise RuntimeError("Nichts erzeugt – bitte nochmal versuchen.")
    return items


def anki_csv(cards):
    def q(s):
        return '"' + str(s).replace('"', '""') + '"'
    return "\n".join(f"{q(c.get('vorne', ''))};{q(c.get('hinten', ''))}" for c in cards)


def copy_upload(fid):
    """Upload aus dem Chat dauerhaft in die Bibliothek kopieren."""
    p = files.find(fid)
    if not p:
        raise RuntimeError("Datei nicht gefunden.")
    dest = DIR / "dateien" / p.name.split("_", 1)[-1]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest = dest.with_name(f"{dest.stem}-{secrets.token_hex(2)}{dest.suffix}")
    shutil.copy2(p, dest)
    return dest
