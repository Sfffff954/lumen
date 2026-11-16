"""
Lumen – mehrere Chats mit Verlauf und Suche. Jeder Chat liegt als JSON in ~/.lumen/chats/.
"""
import json
import re
import secrets
import threading
import time
from pathlib import Path

DIR = Path.home() / ".lumen" / "chats"
LOCK = threading.Lock()


def _path(cid):
    if not re.fullmatch(r"[0-9a-f]{10}", str(cid or "")):
        raise RuntimeError("Ungültige Chat-ID.")
    return DIR / f"{cid}.json"


def _read(p):
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return None


def _title_from(messages):
    for m in messages:
        if m.get("role") == "user" and str(m.get("content", "")).strip():
            t = re.sub(r"^\[per Sprache\] ", "", str(m["content"])).strip().splitlines()[0]
            return (t[:60] + "…") if len(t) > 60 else t
        if m.get("role") == "user" and m.get("attachments"):
            return "Datei: " + str(m["attachments"][0].get("name", ""))[:50]
    return "Neuer Chat"


def clean_messages(messages):
    out = []
    for m in (messages or [])[-200:]:
        if not isinstance(m, dict) or m.get("role") not in ("user", "assistant"):
            continue
        item = {"role": m["role"], "content": str(m.get("content", ""))[:40000]}
        atts = [{k: a.get(k) for k in ("id", "name", "kind")} for a in (m.get("attachments") or []) if isinstance(a, dict)][:10]
        if atts:
            item["attachments"] = atts
        for k in ("cost", "mode", "report", "rating"):
            if m.get(k) is not None:
                item[k] = m[k]
        out.append(item)
    return out


def save(cid, messages, title=None):
    DIR.mkdir(parents=True, exist_ok=True)
    msgs = clean_messages(messages)
    with LOCK:
        if cid:
            p = _path(cid)
            old = _read(p) or {}
        else:
            cid = secrets.token_hex(5)
            p, old = _path(cid), {}
        data = {"id": cid, "title": (title or "").strip()[:80] or old.get("title_custom") and old.get("title") or _title_from(msgs),
                "title_custom": bool((title or "").strip()) or old.get("title_custom", False),
                "created": old.get("created", time.time()), "updated": time.time(), "messages": msgs,
                "pinned": old.get("pinned", False)}
        p.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
    return {"id": cid, "title": data["title"]}


def rename(cid, title):
    with LOCK:
        p = _path(cid)
        d = _read(p)
        if not d:
            raise RuntimeError("Chat nicht gefunden.")
        d["title"], d["title_custom"] = str(title).strip()[:80] or d["title"], True
        p.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    return {"id": cid, "title": d["title"]}


def pin(cid, on):
    with LOCK:
        p = _path(cid)
        d = _read(p)
        if not d:
            raise RuntimeError("Chat nicht gefunden.")
        d["pinned"] = bool(on)
        p.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    return {"id": cid, "pinned": d["pinned"]}


def get(cid):
    d = _read(_path(cid))
    if not d:
        raise RuntimeError("Chat nicht gefunden.")
    return d


def delete(cid):
    _path(cid).unlink(missing_ok=True)
    return {"ok": True}


def listing(q="", limit=200):
    DIR.mkdir(parents=True, exist_ok=True)
    q = (q or "").strip().lower()
    items = []
    for p in DIR.glob("*.json"):
        d = _read(p)
        if not d:
            continue
        item = {"id": d["id"], "title": d.get("title") or "Chat", "updated": d.get("updated", 0),
                "count": len(d.get("messages", [])), "pinned": d.get("pinned", False)}
        if q:
            hit = None
            if q in item["title"].lower():
                hit = item["title"]
            else:
                for m in d.get("messages", []):
                    c = str(m.get("content", ""))
                    i = c.lower().find(q)
                    if i >= 0:
                        s = max(0, i - 40)
                        hit = ("…" if s else "") + c[s:i + len(q) + 60].replace("\n", " ") + "…"
                        break
            if not hit:
                continue
            item["treffer"] = hit
        items.append(item)
    items.sort(key=lambda x: (not x["pinned"], -x["updated"]))
    return items[:limit]


def migrate(old_chat):
    """Einmalig: alten Einzel-Chat übernehmen."""
    if old_chat and not any(DIR.glob("*.json")):
        return save(None, old_chat)
    return None


def set_rating(cid, idx, rating):
    with LOCK:
        p = _path(cid)
        d = _read(p)
        if not d or not (0 <= int(idx) < len(d["messages"])) or d["messages"][int(idx)].get("role") != "assistant":
            raise RuntimeError("Nachricht nicht gefunden.")
        if rating in ("up", "down"):
            d["messages"][int(idx)]["rating"] = rating
        else:
            d["messages"][int(idx)].pop("rating", None)
        p.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    return True


def unrated(limit=40):
    items = []
    for p in DIR.glob("*.json") if DIR.exists() else []:
        d = _read(p)
        if not d:
            continue
        msgs = d.get("messages", [])
        for i, m in enumerate(msgs):
            if m.get("role") == "assistant" and not m.get("rating") and i > 0 and msgs[i - 1].get("role") == "user" \
                    and m.get("mode") not in ("research", "protocol") and len(str(m.get("content", ""))) < 4000:
                items.append({"chat": d["id"], "idx": i, "frage": re.sub(r"^\[per Sprache\] ", "", str(msgs[i - 1]["content"]))[:1500],
                              "antwort": str(m["content"]), "zeit": d.get("updated", 0)})
    items.sort(key=lambda x: -x["zeit"])
    return items[:limit]
