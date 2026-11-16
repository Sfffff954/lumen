"""Lumen – Fähigkeiten, die Lumen selbst lernt (angelehnt an das SKILL.md-Format).

Jede Fähigkeit ist eine Markdown-Anleitung in ~/.lumen/skills/<name>/SKILL.md – reiner Text, kein Code, der von selbst läuft.
Lumen schreibt sie nach erfolgreichen, mehrschrittigen Aufgaben, liest sie, wenn eine ähnliche Aufgabe kommt, und
verbessert sie, wenn es einen besseren Weg findet. Alte Fassungen bleiben als Verlauf erhalten.
"""
import json
import re
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

DIR = Path.home() / ".lumen" / "skills"
LOCK = threading.RLock()
MAX_SKILLS = 200
MAX_CHARS = 8000


def slug(name):
    s = str(name or "").strip().lower()
    s = s.translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]
    if not s:
        raise RuntimeError("Die Fähigkeit braucht einen Namen.")
    return s


def _parse(text):
    meta, body = {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            if k.strip():
                meta[k.strip()] = v.strip().strip('"')
        body = m.group(2)
    return meta, body.strip()


def _render(meta, body):
    head = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False) if k == 'description' else v}" for k, v in meta.items())
    return f"---\n{head}\n---\n\n{body.strip()}\n"


def _path(s):
    return DIR / s / "SKILL.md"


def listing():
    out = []
    if not DIR.exists():
        return out
    for p in sorted(DIR.glob("*/SKILL.md")):
        try:
            meta, body = _parse(p.read_text("utf-8"))
        except Exception:
            continue
        out.append({"id": p.parent.name, "name": meta.get("name") or p.parent.name, "beschreibung": meta.get("description", ""),
                    "genutzt": int(meta.get("uses") or 0), "version": int(meta.get("version") or 1), "von": meta.get("source", "lumen"),
                    "geändert": meta.get("updated", ""), "aus": meta.get("disabled") == "true", "zeichen": len(body)})
    out.sort(key=lambda x: (-x["genutzt"], x["name"].lower()))
    return out


def index_for_prompt(limit=40):
    """Kurze Liste für den System-Prompt (nur Name + Beschreibung)."""
    items = [s for s in listing() if not s["aus"]][:limit]
    if not items:
        return ""
    return "\n".join(f"- {s['id']}: {s['beschreibung'][:140]}" for s in items)


def read(name, count_use=True):
    s = slug(name)
    p = _path(s)
    if not p.exists():
        raise RuntimeError(f"Fähigkeit „{name}“ gibt es nicht. Vorhanden: " + (", ".join(x["id"] for x in listing()) or "keine"))
    with LOCK:
        meta, body = _parse(p.read_text("utf-8"))
        if count_use:
            meta["uses"] = str(int(meta.get("uses") or 0) + 1)
            meta["last_used"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            p.write_text(_render(meta, body), "utf-8")
    return {"id": s, "name": meta.get("name", s), "beschreibung": meta.get("description", ""), "anleitung": body,
            "version": int(meta.get("version") or 1)}


def save(name, description, content, source="lumen"):
    """Neue Fähigkeit anlegen oder bestehende verbessern (alte Fassung wird aufgehoben)."""
    s = slug(name)
    content = str(content or "").strip()
    description = re.sub(r"\s+", " ", str(description or "")).strip()[:300]
    if len(content) < 40:
        raise RuntimeError("Die Anleitung ist zu kurz – beschreibe die Schritte genauer.")
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS]
    if not description:
        raise RuntimeError("Bitte eine kurze Beschreibung, wann die Fähigkeit passt.")
    if re.search(r"(?i)\b(passwort|password|api[-_ ]?key|seed|private[-_ ]?key|token)\b\s*[:=]\s*\S{6,}", content):
        raise RuntimeError("Fähigkeiten dürfen keine Passwörter oder Schlüssel enthalten.")
    with LOCK:
        p = _path(s)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        if p.exists():
            meta, old = _parse(p.read_text("utf-8"))
            v = int(meta.get("version") or 1)
            hist = p.parent / "verlauf"
            hist.mkdir(exist_ok=True)
            (hist / f"v{v}.md").write_text(p.read_text("utf-8"), "utf-8")
            for f in sorted(hist.glob("v*.md"), key=lambda f: int(f.stem[1:]))[:-10]:
                f.unlink()
            meta.update(name=str(name).strip()[:80] or meta.get("name", s), description=description, version=str(v + 1), updated=now)
            new = False
        else:
            if len(listing()) >= MAX_SKILLS:
                raise RuntimeError(f"Maximal {MAX_SKILLS} Fähigkeiten – lösch erst alte.")
            p.parent.mkdir(parents=True, exist_ok=True)
            meta = {"name": str(name).strip()[:80], "description": description, "version": "1", "uses": "0", "created": now,
                    "updated": now, "source": source}
            new = True
        p.write_text(_render(meta, content), "utf-8")
    return {"id": s, "neu": new, "version": int(meta["version"]),
            "text": f"🧠 Fähigkeit „{meta['name']}“ {'gelernt' if new else 'verbessert (Version ' + meta['version'] + ')'}."}


def set_disabled(name, off=True):
    s = slug(name)
    p = _path(s)
    if not p.exists():
        raise RuntimeError("Nicht gefunden.")
    with LOCK:
        meta, body = _parse(p.read_text("utf-8"))
        if off:
            meta["disabled"] = "true"
        else:
            meta.pop("disabled", None)
        p.write_text(_render(meta, body), "utf-8")
    return "Pausiert." if off else "Wieder aktiv."


def delete(name):
    s = slug(name)
    if not (DIR / s).exists():
        raise RuntimeError("Nicht gefunden.")
    shutil.rmtree(DIR / s)
    return f"Fähigkeit „{s}“ gelöscht."


def history(name):
    s = slug(name)
    hist = DIR / s / "verlauf"
    return [{"version": int(f.stem[1:]), "text": _parse(f.read_text("utf-8"))[1]} for f in sorted(hist.glob("v*.md"), key=lambda f: -int(f.stem[1:]))] \
        if hist.exists() else []


def import_text(text):
    """SKILL.md-Text importieren (z. B. selbst geschrieben oder geteilt). Nur Text – wird nie ausgeführt."""
    meta, body = _parse(str(text or ""))
    name = meta.get("name") or (re.search(r"^#\s+(.+)$", body, re.M) or [None, ""])[1]
    if not name:
        raise RuntimeError("Kein Name gefunden (Kopfzeile „name:“ oder Überschrift „# …“).")
    return save(name, meta.get("description") or body.splitlines()[0][:200], body, source="importiert")


# ---------------------------------------------------------------- Selbst lernen
REFLECT_SYS = ("Du bist Lumens Lern-Modul. Du bekommst den Verlauf einer gerade erledigten Aufgabe (Auftrag, benutzte Werkzeuge, Ergebnis). "
               "Entscheide, ob sich daraus eine wiederverwendbare Anleitung (Fähigkeit) lohnt. Lohnt sich NUR, wenn: die Aufgabe mehrere "
               "Schritte hatte, ähnlich wiederkommen kann und es einen nicht offensichtlichen Weg/Trick gab (Reihenfolge, richtige Befehle, "
               "Stolperfallen). Nicht lohnend: Smalltalk, einmalige Fakten-Fragen, persönliche Daten. Gibt es schon eine passende Fähigkeit, "
               "verbessere sie statt eine neue anzulegen. Schreibe keine Passwörter, Schlüssel, privaten Adressen oder Namen Dritter hinein. "
               "Antworte NUR mit JSON: {\"lernen\": false} oder {\"lernen\": true, \"name\": \"kurzer-name\", \"beschreibung\": \"Wann passt das "
               "(1 Satz)\", \"anleitung\": \"Markdown: ## Wann\\n…\\n## Schritte\\n1. …\\n## Stolperfallen\\n- …\"}")


def reflect_prompt(task, actions, result, existing):
    acts = "\n".join(("✓ " if a.get("ok") else "✗ ") + str(a.get("text", ""))[:160] for a in actions[:40])
    ex = "\n".join(f"- {s['id']}: {s['beschreibung'][:120]}" for s in existing[:60]) or "(noch keine)"
    return (f"AUFTRAG:\n{str(task)[:1500]}\n\nSCHRITTE ({len(actions)}):\n{acts}\n\nERGEBNIS:\n{str(result)[:1500]}\n\n"
            f"VORHANDENE FÄHIGKEITEN:\n{ex}\n\nLohnt sich eine Fähigkeit? Nur JSON.")


def parse_reflection(text):
    m = re.search(r"\{.*\}", str(text or ""), re.S)
    if not m:
        return None
    try:
        js = json.loads(m.group(0))
    except Exception:
        return None
    if not js.get("lernen") or not js.get("name") or not js.get("anleitung"):
        return None
    return js
