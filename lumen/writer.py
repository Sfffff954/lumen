"""
Lumen – Schreibstudio: ganze Bücher Kapitel für Kapitel schreiben (Plan → Kapitel → Word/PDF/EPUB).
Die KI-Anfragen kommen über complete(system, prompt, max_tokens) von lumen.py – Cloud oder lokal.
Jedes Buch liegt als Projekt (projekt.json + buch.md) im Ordner Dokumente/Lumen/Bücher/<Titel>/.
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path

import brain
import docs

GENRES = ["Roman", "Fantasy", "Science-Fiction", "Krimi/Thriller", "Liebesroman", "Horror", "Kinderbuch", "Jugendbuch",
          "Sachbuch", "Ratgeber", "Biografie (fiktiv)", "Kurzgeschichten", "Fanfiction (eigene Figuren)", "Lehrbuch/Skript"]

SYSTEM = ("Du bist ein erfahrener Autor und Lektor. Du schreibst lebendig, bildhaft und abwechslungsreich, mit echten Dialogen, "
          "Spannung und klarer Sprache – ohne Floskeln, Wiederholungen oder Zusammenfassungen am Kapitelende. "
          "Halte dich strikt an Plan, Figuren und bisherige Handlung (keine Widersprüche).")


def books_dir():
    return docs.default_dir() / "Bücher"


def _json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise RuntimeError("Die KI hat keinen gültigen Plan geliefert – bitte nochmal versuchen.")
    return json.loads(m.group(0))


def plan_prompt(s):
    kind = "Sachbuch/Ratgeber" if re.search(r"sach|ratgeber|lehr|skript", s["genre"], re.I) else "Erzählung"
    return (f"Plane ein Buch.\nIdee: {s['idee']}\nGenre: {s['genre']} ({kind})\nZielgruppe: {s.get('zielgruppe') or 'Erwachsene'}\n"
            f"Stil/Ton: {s.get('stil') or 'passend zum Genre'}\nSprache: {s.get('sprache') or 'Deutsch'}\n"
            f"Kapitel: genau {s['kapitel']}, je ca. {s['woerter']} Wörter.\n"
            + (f"Titel (vorgegeben): {s['titel']}\n" if s.get("titel") else "")
            + "Gib NUR JSON zurück:\n"
              '{"titel":"…","untertitel":"…","klappentext":"3–4 Sätze","figuren":[{"name":"…","rolle":"…","beschreibung":"Aussehen, '
              'Charakter, Ziel"}],"welt":"Ort/Zeit/Regeln bzw. Aufbau des Themas","kapitel":[{"titel":"…","inhalt":"4–6 Sätze: was '
              'genau passiert bzw. welche Inhalte, Wendepunkte, wie es endet"}]}\n'
              "Bei Sachbüchern: figuren leer lassen, welt = roter Faden. Die Kapitel sollen einen klaren Bogen ergeben "
              "(Einstieg, Steigerung, Höhepunkt, Auflösung).")


def chapter_prompt(s, plan, i, prev_summaries, prev_tail, wish=""):
    ch = plan["kapitel"][i]
    figs = "\n".join(f"- {f.get('name')}: {f.get('rolle', '')} – {f.get('beschreibung', '')}" for f in plan.get("figuren") or [])
    story = "\n".join(f"Kapitel {n + 1}: {t}" for n, t in enumerate(prev_summaries)) or "(Das ist das erste Kapitel.)"
    nxt = plan["kapitel"][i + 1]["titel"] if i + 1 < len(plan["kapitel"]) else None
    return (f"BUCH: „{plan['titel']}“ – {s['genre']}, Zielgruppe {s.get('zielgruppe') or 'Erwachsene'}, Stil: {s.get('stil') or 'passend'}, "
            f"Sprache: {s.get('sprache') or 'Deutsch'}.\nWelt/roter Faden: {plan.get('welt', '')}\n"
            + (f"Figuren:\n{figs}\n" if figs else "")
            + f"\nBISHER:\n{story}\n"
            + (f"\nLetzte Zeilen des vorigen Kapitels:\n…{prev_tail}\n" if prev_tail else "")
            + f"\nSCHREIBE JETZT Kapitel {i + 1} von {len(plan['kapitel'])}: „{ch['titel']}“\nInhalt laut Plan: {ch['inhalt']}\n"
            + (f"Danach folgt: „{nxt}“ – arbeite darauf hin, nimm es aber nicht vorweg.\n" if nxt else "Das ist das letzte Kapitel – runde das Buch ab.\n")
            + (f"Besonderer Wunsch: {wish}\n" if wish else "")
            + f"Länge: ca. {s['woerter']} Wörter. Nur der Kapiteltext in Markdown (Absätze, Dialoge; KEINE Kapitelüberschrift).\n"
              "Ganz am Ende, in einer eigenen Zeile: ZUSAMMENFASSUNG: <3 Sätze, was im Kapitel passiert ist> – die wird nicht gedruckt.")


def _split_summary(text):
    m = re.search(r"\n\s*\**ZUSAMMENFASSUNG:?\**:?\s*(.+)$", text or "", re.S | re.I)
    if not m:
        body = text.strip()
        return body, " ".join(re.split(r"(?<=[.!?])\s+", body)[-3:])[:600]
    return text[:m.start()].strip(), m.group(1).strip()[:800]


def assemble(project):
    plan, s = project["plan"], project["spec"]
    parts = []
    if plan.get("klappentext"):
        parts.append(f"> {plan['klappentext']}\n\n\\pagebreak")
    for i, ch in enumerate(project["kapitel"]):
        if ch:
            parts.append(f"# Kapitel {i + 1}: {plan['kapitel'][i]['titel']}\n\n{ch['text']}")
    return "\n\n".join(parts)


def save_files(folder, project, formats):
    plan = project["plan"]
    md = assemble(project)
    title = plan["titel"]
    out = []
    (folder / "buch.md").write_text(f"# {title}\n\n" + md, "utf-8")
    for f in formats:
        if f == "md":
            out.append(str(folder / "buch.md"))
            continue
        try:
            out.append(str(docs.make(folder / docs.safe_name(title), title, md, f, project["spec"].get("autor", ""))))
        except Exception as e:
            out.append(f"{f}: Fehler – {e}")
    return out


def _store(folder, project):
    (folder / "projekt.json").write_text(json.dumps(project, ensure_ascii=False, indent=1), "utf-8")


def start(spec, complete, name="book"):
    """spec: idee, genre, kapitel, woerter, stil, zielgruppe, sprache, titel, autor, formate"""
    s = dict(spec)
    s["kapitel"] = max(1, min(int(s.get("kapitel") or 10), 40))
    s["woerter"] = max(300, min(int(s.get("woerter") or 2500), 6000))
    s["formate"] = [f for f in (s.get("formate") or ["docx", "pdf", "epub"]) if f in docs.FORMATS] or ["docx"]
    if not str(s.get("idee", "")).strip():
        raise RuntimeError("Worum soll das Buch gehen? Bitte eine Idee angeben.")

    def fn(t):
        n = s["kapitel"]
        t.steps = [{"name": "Plan & Figuren", "status": "läuft"}] + [{"name": f"Kapitel {i + 1}", "status": "offen"} for i in range(n)] \
            + [{"name": "Dateien erstellen", "status": "offen"}]
        t.detail = "Plane Handlung, Figuren und Kapitel …"
        plan = _json(complete(SYSTEM, plan_prompt(s), 6000))
        plan["kapitel"] = (plan.get("kapitel") or [])[:n]
        if len(plan["kapitel"]) < n:
            for i in range(len(plan["kapitel"]), n):
                plan["kapitel"].append({"titel": f"Kapitel {i + 1}", "inhalt": "Die Geschichte geht weiter."})
        plan["titel"] = (s.get("titel") or plan.get("titel") or "Mein Buch").strip()
        folder = books_dir() / docs.safe_name(plan["titel"])
        if folder.exists() and (folder / "projekt.json").exists():
            folder = folder.with_name(folder.name + "_" + datetime.now().strftime("%H%M%S"))
        folder.mkdir(parents=True, exist_ok=True)
        project = {"spec": s, "plan": plan, "kapitel": [None] * n, "ordner": str(folder), "start": time.time()}
        _store(folder, project)
        t.steps[0].update(status="fertig", detail=plan["titel"])
        for i, ch in enumerate(plan["kapitel"]):
            t.steps[i + 1]["name"] = f"Kapitel {i + 1}: {ch['titel']}"
        t.result = {"ordner": str(folder), "titel": plan["titel"]}
        summaries, tail = [], ""
        for i in range(n):
            if t.status == "abgebrochen":
                raise RuntimeError("Abgebrochen – bisherige Kapitel sind gespeichert.")
            t.steps[i + 1]["status"] = "läuft"
            t.detail = f"Schreibe Kapitel {i + 1} von {n} …"
            t.progress = (i + 0.3) / (n + 1)
            raw = complete(SYSTEM, chapter_prompt(s, plan, i, summaries, tail), min(16000, int(s["woerter"] * 2.4) + 800))
            raw = re.sub(r"^\s*#+\s*Kapitel[^\n]*\n", "", raw.strip())
            body, summ = _split_summary(raw)
            if len(body.split()) < 80:
                t.steps[i + 1].update(status="fehler", detail="zu kurz – nochmal")
                raw = complete(SYSTEM, chapter_prompt(s, plan, i, summaries, tail, "Schreibe das vollständige Kapitel, nicht kürzen."),
                               min(16000, int(s["woerter"] * 2.4) + 800))
                body, summ = _split_summary(re.sub(r"^\s*#+\s*Kapitel[^\n]*\n", "", raw.strip()))
            project["kapitel"][i] = {"text": body, "zusammenfassung": summ, "wörter": len(body.split())}
            summaries.append(summ)
            tail = body[-1500:]
            _store(folder, project)
            (folder / "buch.md").write_text(f"# {plan['titel']}\n\n" + assemble(project), "utf-8")  # Zwischenstand lesbar
            t.steps[i + 1].update(status="fertig", detail=f"{len(body.split())} Wörter")
            t.add(f"PROGRESS {i + 1}/{n + 1}")
        t.steps[-1]["status"] = "läuft"
        t.detail = "Erstelle Word/PDF/E-Book …"
        out = save_files(folder, project, s["formate"])
        words = sum(c["wörter"] for c in project["kapitel"] if c)
        t.steps[-1].update(status="fertig", detail=f"{words:,} Wörter".replace(",", "."))
        t.detail = f"Fertig: „{plan['titel']}“ – {words:,} Wörter, {n} Kapitel".replace(",", ".")
        t.result = {"ordner": str(folder), "titel": plan["titel"], "dateien": out, "wörter": words}
        return t.result

    return brain.run_py_task(name, "Buch schreiben", fn)


def rewrite(folder, idx, wish, complete):
    folder = Path(folder)
    project = json.loads((folder / "projekt.json").read_text("utf-8"))
    s, plan = project["spec"], project["plan"]
    i = int(idx)
    if not (0 <= i < len(plan["kapitel"])):
        raise RuntimeError("Kapitel gibt es nicht.")

    def fn(t):
        t.detail = f"Schreibe Kapitel {i + 1} neu …"
        summaries = [c["zusammenfassung"] for c in project["kapitel"][:i] if c]
        tail = project["kapitel"][i - 1]["text"][-1500:] if i > 0 and project["kapitel"][i - 1] else ""
        raw = complete(SYSTEM, chapter_prompt(s, plan, i, summaries, tail, wish), min(16000, int(s["woerter"] * 2.4) + 800))
        body, summ = _split_summary(re.sub(r"^\s*#+\s*Kapitel[^\n]*\n", "", raw.strip()))
        project["kapitel"][i] = {"text": body, "zusammenfassung": summ, "wörter": len(body.split())}
        _store(folder, project)
        out = save_files(folder, project, s["formate"])
        t.detail = f"Kapitel {i + 1} neu geschrieben ({len(body.split())} Wörter)"
        return {"ordner": str(folder), "titel": plan["titel"], "dateien": out}

    return brain.run_py_task("book", f"Kapitel {i + 1} neu schreiben", fn)


def library():
    out = []
    d = books_dir()
    if not d.exists():
        return out
    for p in d.glob("*/projekt.json"):
        try:
            pr = json.loads(p.read_text("utf-8"))
        except Exception:
            continue
        done = [c for c in pr["kapitel"] if c]
        files = [str(f) for f in p.parent.iterdir() if f.suffix in (".docx", ".pdf", ".epub", ".md", ".html", ".txt")]
        out.append({"titel": pr["plan"]["titel"], "ordner": str(p.parent), "genre": pr["spec"].get("genre"),
                    "kapitel": len(pr["kapitel"]), "fertig": len(done), "wörter": sum(c["wörter"] for c in done),
                    "klappentext": pr["plan"].get("klappentext", ""), "zeit": p.stat().st_mtime, "dateien": sorted(files),
                    "kapitel_titel": [k["titel"] for k in pr["plan"]["kapitel"]]})
    return sorted(out, key=lambda x: -x["zeit"])


def estimate_tokens(spec):
    n = max(1, min(int(spec.get("kapitel") or 10), 40))
    w = max(300, min(int(spec.get("woerter") or 2500), 6000))
    out = 2500 + n * (w * 1.7 + 120)
    inp = 1200 + n * (2200 + n * 25)
    return int(inp), int(out)
