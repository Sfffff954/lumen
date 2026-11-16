"""
Lumen – Agenten. Ein Agent bekommt eine große Aufgabe, plant selbst, arbeitet viele Schritte im Hintergrund ab,
prüft sein Ergebnis und berichtet. Im Team-Modus verteilt ein Leiter Teilaufgaben an Spezialisten, die parallel
arbeiten; ein Prüfer kontrolliert am Ende. Sicherheitsabfragen gelten weiter (Karte in der App bzw. Telegram-Knöpfe).

Neu: Rückfragen an den Nutzer (agent_ask, App + Telegram), Selbstprüfung mit Nacharbeit, Zeit- und Kostenlimit,
Verlauf bleibt nach Neustart erhalten (unterbrochene Agenten lassen sich neu starten), erzeugte Dateien werden erkannt
(und in Telegram mitgeschickt), Live-Fortschritt in Telegram (eine Nachricht, die sich laufend aktualisiert).
"""
import json
import re
import secrets
import threading
import time
from pathlib import Path

L = None  # lumen-Modul (setzt lumen.py)
AGENTS = {}
LOCK = threading.Lock()
SAVE_LOCK = threading.Lock()
MAX_PARALLEL = 4
DATA = Path.home() / ".lumen" / "agents.json"

ROLES = {
    "leiter": ("🧭", "Team-Leiter", "Du leitest ein Team aus Spezialisten. Zerlege die Aufgabe, verteile parallelisierbare Teilaufgaben mit "
                                   "spawn_agents an passende Rollen, führe die Ergebnisse zusammen und lass am Ende einen Prüfer kontrollieren. "
                                   "Kleine Dinge erledigst du selbst.", None),
    "allrounder": ("🤖", "Agent", "Du erledigst die Aufgabe selbstständig von Anfang bis Ende.", None),
    "recherche": ("🔎", "Rechercheur", "Du recherchierst gründlich im Internet und in der Wissens-Bibliothek und lieferst belegte Fakten mit Quellen.",
                  {"web_search", "meta_search", "read_webpage", "read_webpages", "knowledge_search", "knowledge_list", "read_file", "list_folder",
                   "search_files", "write_file", "create_document", "calendar_events", "weather", "browser_open", "browser_read",
                   "browser_scroll", "browser_back", "skill_read"}),
    "coder": ("🧑‍💻", "Coder", "Du schreibst, startest und testest Code und Skripte. Teste immer, was du baust.",
              {"list_folder", "search_files", "read_file", "write_file", "create_folder", "move_path", "delete_path", "run_command",
               "web_search", "read_webpage", "read_webpages", "create_plugin", "read_plugin", "list_plugins", "ssh_command",
               "ssh_upload", "ssh_download", "docker_list", "docker_logs", "system_info", "skill_read", "secrets_scan",
               "meta_search", "github_tool_search", "github_tool_info", "github_tool_list", "github_tool_run",
               "code_project", "code_search", "code_outline", "code_review", "git_status", "git_log", "git_diff", "git_stage",
               "git_commit_message", "git_commit", "git_branch", "git_conflicts"}),
    "admin": ("🛠️", "Admin", "Du kümmerst dich um Server, Docker, Dienste und Systemeinstellungen – vorsichtig und mit Backups.",
              {"list_servers", "test_server", "server_overview", "ssh_command", "ssh_upload", "ssh_download", "docker_list", "docker_logs",
               "docker_action", "run_command", "system_info", "read_file", "write_file", "list_folder", "create_folder", "web_search",
               "read_webpage", "read_webpages", "port_scan", "net_diag", "ssl_check", "dns_lookup", "pc_doctor", "server_health",
               "nmap_scan", "pc_security_check", "cve_check", "lynis_audit", "skill_read"}),
    "schreiber": ("✍️", "Schreiber", "Du schreibst klare, gut gegliederte Texte und Dokumente.",
                  {"create_document", "write_file", "read_file", "list_folder", "knowledge_search", "web_search", "read_webpage",
                   "read_webpages", "write_book", "skill_read"}),
    "pruefer": ("✅", "Prüfer", "Du prüfst kritisch, ob die Aufgabe wirklich erledigt ist: Dateien öffnen, Befehle/Tests ausführen, Fakten "
                               "gegenchecken. Melde klar: was passt, was fehlt, was falsch ist. Ändere nichts, außer es ist ausdrücklich verlangt.",
                {"read_file", "list_folder", "search_files", "run_command", "web_search", "read_webpage", "read_webpages", "ssh_command",
                 "docker_list", "docker_logs", "knowledge_search", "calendar_events", "server_overview"}),
}

AGENT_PROMPT = """

AGENTEN-MODUS – du bist „{name}“ ({role}). {role_text}
Aufgabe: {task}
Regeln:
1. Plane zuerst: rufe agent_plan mit 3–10 konkreten Schritten auf. Passt eine deiner gelernten Fähigkeiten, lies sie vorher (skill_read).
2. Arbeite die Schritte selbstständig ab und melde jeden Fortschritt mit agent_step (index ab 0, status läuft/fertig/übersprungen/fehler, kurze Notiz).
3. Fehlt dir eine Information, die nur der Nutzer kennt und ohne die das Ergebnis wertlos wäre (z. B. welcher Server, welches Budget,
   welche von zwei Varianten), frag mit agent_ask – kurz, am besten mit 2–4 Antwort-Optionen. Höchstens 2 Rückfragen pro Auftrag.
   Kommt keine Antwort, triff eine vernünftige Annahme und schreib sie in den Bericht. Für Kleinigkeiten nicht fragen.
4. Riskante Aktionen werden vom Nutzer bestätigt; wird etwas abgelehnt, mach ohne weiter oder such einen anderen Weg.
5. Prüfe dein Ergebnis wirklich (Datei öffnen, Befehl testen, Seite abrufen), bevor du fertig bist.
6. Zum Schluss: ein kurzer Bericht in Markdown – **Ergebnis**, was du gemacht hast (Stichpunkte), erzeugte Dateien mit VOLLEM Pfad,
   getroffene Annahmen, offene Punkte.
7. Erfinde nichts. Behaupte nur, was du wirklich getan/gesehen hast."""

TEAM_HINT = """
TEAM: Du kannst mit spawn_agents bis zu 4 Spezialisten gleichzeitig starten. Rollen: recherche (Internet/Fakten), coder (Code/
Skripte/Dateien), admin (Server/Docker/System), schreiber (Texte/Dokumente), pruefer (kontrolliert Ergebnisse). Gib jedem eine
klare, eigenständige Teilaufgabe mit allem Kontext (sie sehen deinen Verlauf nicht). spawn_agents wartet, bis alle fertig sind,
und gibt dir ihre Berichte. Rückfragen an den Nutzer stellst nur du (agent_ask), nicht deine Spezialisten."""

REVIEW_SYS = ("Du bist ein strenger Prüfer für Lumens Agenten. Du bekommst Auftrag, Plan (mit Status), die ausgeführten Schritte und den "
              "Abschlussbericht. Entscheide NUR anhand dieser Belege, ob der Auftrag wirklich erledigt ist. Nicht erledigt ist er, wenn Teile "
              "des Auftrags fehlen, Schritte fehlgeschlagen sind und nicht ersetzt wurden, nichts geprüft wurde oder der Bericht etwas behauptet, "
              "das in den Schritten nicht vorkommt. Antworte NUR mit JSON: {\"fertig\": true} oder {\"fertig\": false, \"fehlt\": \"konkret, was noch "
              "zu tun ist (1–3 Sätze)\"}")

ACTIVE = ("startet", "plant", "arbeitet", "wartet", "fragt", "prüft")


class Agent:
    def __init__(self, task, role="allrounder", parent=None, origin="app", title=None):
        self.id = secrets.token_hex(5)
        self.task = task.strip()
        self.role = role if role in ROLES else "allrounder"
        self.parent = parent
        self.children = []
        self.origin = origin
        self.title = (title or self.task.split("\n")[0])[:90]
        self.status = "startet"     # startet | plant | arbeitet | wartet | fragt | prüft | fertig | fehler | gestoppt | unterbrochen
        self.plan = []              # [{"text":…, "status":…, "notiz":…}]
        self.result = ""
        self.error = None
        self.created = time.time()
        self.finished = None
        self.job = None
        self.chat_id = None
        self.question = None        # {"text", "optionen", "seit", "antwort"}
        self.questions_asked = 0
        self.answers = []           # [(frage, antwort)]
        self.files = []
        self.review = None          # {"runde", "fehlt"}
        self.cost_saved = 0.0
        self.actions_saved = []
        self.tg_msg = None
        self._answer_ev = threading.Event()

    def emoji(self):
        return ROLES[self.role][0]

    def name(self):
        return ROLES[self.role][1]

    def cost(self):
        return round((self.job.usage.get("cost") or 0) if self.job else self.cost_saved, 4)

    def view(self, full=False):
        j = self.job
        st = self.status
        if j is not None and st in ("plant", "arbeitet", "wartet"):
            st = "wartet" if j.status == "confirm" else ("plant" if not self.plan else "arbeitet")
            self.status = st
        done = sum(1 for p in self.plan if p["status"] in ("fertig", "übersprungen"))
        acts = (j.actions if j else self.actions_saved)
        v = {"id": self.id, "titel": self.title, "aufgabe": self.task if full else self.task[:400], "rolle": self.role,
             "emoji": self.emoji(), "rollenname": self.name(), "status": st, "plan": self.plan,
             "fortschritt": round(done / len(self.plan), 2) if self.plan else None, "eltern": self.parent, "kinder": self.children,
             "aktion": (acts[-1]["text"] if acts else None), "aktionen_anzahl": len(acts),
             "kosten": self.cost(), "start": self.created, "ende": self.finished,
             "minuten": round(((self.finished or time.time()) - self.created) / 60, 1), "fehler": self.error,
             "bestaetigen": (j.pending if j and j.status == "confirm" else None), "job": j.id if j else None,
             "herkunft": self.origin, "chat": self.chat_id, "frage": self.question if st == "fragt" else None,
             "dateien": self.files, "prüfung": self.review}
        if full:
            v["aktionen"] = acts
            v["ergebnis"] = self.result
            v["antworten"] = self.answers
        elif st in ("fertig", "fehler", "gestoppt", "unterbrochen"):
            v["ergebnis_kurz"] = (self.result or "")[:300]
        return v

    def active(self):
        return self.status in ACTIVE

    def to_dict(self):
        return {"id": self.id, "task": self.task, "role": self.role, "parent": self.parent, "children": self.children, "origin": self.origin,
                "title": self.title, "status": self.status if not self.active() else "unterbrochen", "plan": self.plan, "result": self.result,
                "error": self.error if not self.active() else "Lumen wurde beendet, während der Agent lief.", "created": self.created,
                "finished": self.finished or (time.time() if self.active() else None), "chat_id": self.chat_id, "answers": self.answers,
                "files": self.files, "review": self.review, "cost": self.cost(),
                "actions": [{"ok": x.get("ok"), "text": str(x.get("text", ""))[:200]} for x in ((self.job.actions if self.job else self.actions_saved) or [])][-80:]}


# ---------------------------------------------------------------- Speichern / Laden
def save():
    try:
        with LOCK:
            data = [a.to_dict() for a in sorted(AGENTS.values(), key=lambda a: a.created)][-60:]
        with SAVE_LOCK:
            DATA.parent.mkdir(parents=True, exist_ok=True)
            tmp = DATA.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
            tmp.replace(DATA)
    except Exception as e:
        print("Agenten speichern:", e)


def load():
    try:
        data = json.loads(DATA.read_text("utf-8"))
    except Exception:
        return
    for d in data:
        a = Agent(d["task"], d.get("role", "allrounder"), d.get("parent"), d.get("origin", "app"), d.get("title"))
        a.id = d["id"]
        a.children = d.get("children") or []
        a.status = d.get("status", "fertig")
        if a.status in ACTIVE:
            a.status, a.error = "unterbrochen", "Lumen wurde beendet, während der Agent lief."
        a.plan, a.result, a.error = d.get("plan") or [], d.get("result") or "", d.get("error") or a.error
        a.created, a.finished, a.chat_id = d.get("created", time.time()), d.get("finished"), d.get("chat_id")
        a.answers, a.files, a.review = d.get("answers") or [], d.get("files") or [], d.get("review")
        a.cost_saved, a.actions_saved = d.get("cost") or 0, d.get("actions") or []
        AGENTS[a.id] = a


def online():
    return [a for a in AGENTS.values() if a.active()]


def listing():
    with LOCK:
        items = sorted(AGENTS.values(), key=lambda a: -a.created)
    return [a.view() for a in items]


def stats():
    act = online()
    return {"online": len(act), "wartet": sum(1 for a in act if a.status in ("wartet", "fragt") or (a.job and a.job.status == "confirm")),
            "fertig": sum(1 for a in AGENTS.values() if a.status == "fertig"), "gesamt": len(AGENTS),
            "rollen": [a.emoji() for a in act]}


def _cleanup():
    done = sorted((a for a in AGENTS.values() if not a.active()), key=lambda a: a.created)
    for a in done[:-40]:
        AGENTS.pop(a.id, None)


def find(prefix):
    """Agent über ID oder ID-Anfang (für Telegram-Knöpfe)."""
    if prefix in AGENTS:
        return AGENTS[prefix]
    hits = [a for k, a in AGENTS.items() if k.startswith(str(prefix))]
    return hits[0] if len(hits) == 1 else None


def start(task, team=False, role=None, parent=None, origin="app"):
    if not str(task or "").strip():
        raise RuntimeError("Was soll der Agent erledigen?")
    if len(online()) >= 12:
        raise RuntimeError("Schon 12 Agenten aktiv – warte, bis welche fertig sind, oder stoppe einen.")
    a = Agent(task, role or ("leiter" if team else "allrounder"), parent, origin)
    with LOCK:
        _cleanup()
        AGENTS[a.id] = a
    if parent and parent in AGENTS:
        AGENTS[parent].children.append(a.id)
    threading.Thread(target=_run, args=(a,), daemon=True).start()
    if origin == "telegram" and not parent:
        threading.Thread(target=_telegram_live, args=(a,), daemon=True).start()
    save()
    return a


def restart(aid):
    a = AGENTS.get(aid)
    if not a:
        raise RuntimeError("Agent nicht gefunden.")
    if a.active():
        raise RuntimeError("Läuft noch.")
    task = a.task
    if a.answers:
        task += "\n\nAntworten des Nutzers auf frühere Rückfragen:\n" + "\n".join(f"- {q} → {ans}" for q, ans in a.answers)
    return start(task, team=a.role == "leiter", role=None if a.role in ("leiter", "allrounder") else a.role, origin=a.origin)


def _limits():
    cfg = L.load_config()
    return float(cfg.get("agent_max_minutes") or 60), float(cfg.get("agent_max_cost") or 0), bool(cfg.get("agent_selfcheck", True))


def _run(a):
    cfg = L.load_config()
    try:
        cfg = L.agent_config(cfg)
    except Exception as e:
        a.status, a.error, a.finished = "fehler", str(e), time.time()
        save()
        return
    job = L.Job(cfg)
    job.mode = "agent"
    job.agent = a
    job.allowed = None if ROLES[a.role][3] is None else set(ROLES[a.role][3]) | {"agent_plan", "agent_step"}
    if a.role != "leiter":
        job.allowed = (job.allowed or {t["name"] for t in L.all_tools()}) - {"spawn_agents", "start_agent"}
    if a.parent:   # Spezialisten fragen nicht selbst nach – das macht der Leiter
        job.allowed = (job.allowed or {t["name"] for t in L.all_tools()}) - {"agent_ask"}
    if a.origin == "telegram":
        job.via = "telegram"
    L.JOBS[job.id] = job
    a.job = job
    a.status = "plant"
    threading.Thread(target=_watch, args=(a,), daemon=True).start()
    history = [{"role": "user", "content": a.task}]
    try:
        a.result = L.run_chat(job, history)
        _, _, selfcheck = _limits()
        if selfcheck and a.role not in ("pruefer",) and len(job.actions) >= 3 and not job.cancelled:
            for rnd in (1,):
                missing = _self_review(a, cfg)
                if not missing:
                    a.review = {"runde": rnd, "ok": True}
                    break
                a.review = {"runde": rnd, "ok": False, "fehlt": missing}
                a.status = "arbeitet"
                a.plan.append({"text": "Nacharbeit nach Selbstprüfung", "status": "läuft", "notiz": missing[:200]})
                history = history + [{"role": "assistant", "content": a.result},
                                     {"role": "user", "content": f"SELBSTPRÜFUNG: Der Auftrag ist noch nicht ganz erledigt. Es fehlt: {missing}\n"
                                                                 f"Erledige das jetzt (prüfe es auch) und gib danach den VOLLSTÄNDIGEN Abschlussbericht."}]
                a.result = L.run_chat(job, history)
                a.plan[-1]["status"] = "fertig"
        a.status = "fertig"
        for p in a.plan:
            if p["status"] in ("offen", "läuft"):
                p["status"] = "übersprungen" if p["status"] == "offen" else "fertig"
    except L.Cancelled:
        a.status, a.result = "gestoppt", a.result or ("Gestoppt: " + (a.error or "vom Nutzer."))
    except Exception as e:
        a.status, a.error = "fehler", str(e)
        a.result = a.result or f"Fehler: {e}"
    a.finished = time.time()
    a.question = None
    a.files = _find_files(a.result)
    save()
    if not a.parent:
        _deliver(a)
        if a.status == "fertig":
            try:
                L.maybe_learn(job, history, a.result, notify=(lambda t: L.BOT.send(t)) if a.origin == "telegram" and L.BOT else None)
            except Exception:
                pass


def _self_review(a, cfg):
    acts = "\n".join(("✓ " if x.get("ok") else "✗ ") + str(x.get("text", ""))[:160] for x in a.job.actions[-50:])
    plan = "\n".join(f"[{p['status']}] {p['text']}" + (f" – {p['notiz']}" if p.get("notiz") else "") for p in a.plan)
    prompt = f"AUFTRAG:\n{a.task[:3000]}\n\nPLAN:\n{plan or '(kein Plan)'}\n\nSCHRITTE:\n{acts}\n\nBERICHT:\n{a.result[:4000]}\n\nErledigt? Nur JSON."
    a.status = "prüft"
    try:
        out = L.plain_complete(cfg, L.studio_route(cfg, "auto"), REVIEW_SYS, prompt, 400)
        m = re.search(r"\{.*\}", out or "", re.S)
        js = json.loads(m.group(0)) if m else {}
        if js.get("fertig") is False and str(js.get("fehlt", "")).strip():
            return str(js["fehlt"]).strip()[:600]
    except Exception:
        pass
    return None


def _find_files(text):
    """Pfade im Bericht, die es wirklich gibt (für „Dateien“ und Telegram-Versand)."""
    out = []
    for m in re.finditer(r"(?:(?<=\s)|(?<=^)|(?<=`)|(?<=\()|(?<=:))((?:~|/)[^\s`'\")\]]*\.[A-Za-z0-9]{1,6})", text or "", re.M):
        p = Path(m.group(1).rstrip(".,;:")).expanduser()
        try:
            if p.is_file() and str(p) not in out and not str(p).startswith(("/proc", "/sys", "/dev", "/etc/shadow")):
                out.append(str(p))
        except Exception:
            pass
    return out[:10]


def _watch(a):
    """Bestätigungen per Telegram-Knopf, Zeit-/Kostenlimit überwachen."""
    asked = None
    max_min, max_cost, _ = _limits()
    while a.active():
        j = a.job
        if j and a.origin == "telegram" and j.status == "confirm" and j.pending and j.pending is not asked and L.BOT:
            asked = j.pending
            if j.pending.get("secret"):
                j.answer(False)
            else:
                try:
                    L.BOT.send(f"🤖 **{a.title[:60]}**\n❓ **{j.pending['title']}**\n```\n{str(j.pending['detail'])[:1200]}\n```",
                               buttons=[[{"text": "✅ Erlauben", "callback_data": f"ok:{j.id}"}, {"text": "❌ Ablehnen", "callback_data": f"no:{j.id}"}]])
                except Exception:
                    pass
        if j and not a.parent:
            over = None
            if max_min and time.time() - a.created > max_min * 60 and a.status != "fragt":
                over = f"Zeitlimit von {int(max_min)} Minuten erreicht"
            elif max_cost and a.cost() + sum(AGENTS[k].cost() for k in a.children if k in AGENTS) > max_cost:
                over = f"Kostenlimit von ${max_cost:.2f} erreicht"
            if over:
                a.error = over
                stop(a.id)
                break
        time.sleep(0.8)


# ---------------------------------------------------------------- Rückfragen
def tool_ask(job, question, options=None, wait_min=None):
    a = job.agent
    if a.parent:
        return "Rückfragen stellt nur der Team-Leiter. Triff eine vernünftige Annahme."
    if a.questions_asked >= 2:
        return "Keine weiteren Rückfragen – triff eine vernünftige Annahme und nenne sie im Bericht."
    q = str(question or "").strip()[:500]
    if not q:
        return "Leere Frage."
    opts = [str(o).strip()[:60] for o in (options or []) if str(o).strip()][:4]
    wait = float(wait_min or L.load_config().get("agent_ask_wait") or 20)
    a.questions_asked += 1
    a._answer_ev.clear()
    a.question = {"text": q, "optionen": opts, "seit": time.time(), "warten_min": wait, "antwort": None}
    prev, a.status = a.status, "fragt"
    save()
    _notify_question(a)
    deadline = time.time() + wait * 60
    while not a._answer_ev.wait(1.0):
        if job.cancelled:
            raise L.Cancelled()
        if time.time() > deadline:
            break
    ans = a.question.get("antwort") if a.question else None
    a.question = None
    a.status = "arbeitet" if prev not in ("plant",) else prev
    if ans is None:
        a.answers.append((q, "(keine Antwort – Annahme getroffen)"))
        return f"Keine Antwort nach {int(wait)} Minuten. Triff eine vernünftige Annahme, mach weiter und nenne die Annahme im Bericht."
    a.answers.append((q, ans))
    save()
    return f"Antwort des Nutzers: {ans}"


def answer(aid, text):
    a = AGENTS.get(aid) or find(aid)
    if not a or not a.question:
        raise RuntimeError("Dieser Agent wartet gerade auf keine Antwort.")
    t = str(text or "").strip()[:1000]
    if not t:
        raise RuntimeError("Antwort fehlt.")
    a.question["antwort"] = t
    a._answer_ev.set()
    return f"Antwort an „{a.title[:50]}“ übergeben."


def waiting_question():
    """Telegram: der Agent, der gerade auf eine Antwort wartet (für Freitext-Antworten)."""
    q = [a for a in AGENTS.values() if a.status == "fragt" and a.question and not a.parent]
    return sorted(q, key=lambda a: a.question["seit"])[0] if q else None


def _notify_question(a):
    q = a.question
    try:
        L.desktop_notify(f"❓ {a.emoji()} Agent fragt", q["text"][:200])
    except Exception:
        pass
    if L.BOT and (a.origin == "telegram" or L.load_config().get("agent_tg_questions", True)):
        btns = [[{"text": o[:40], "callback_data": f"aq:{a.id}:{i}"}] for i, o in enumerate(q["optionen"])]
        try:
            L.BOT.send(f"❓ **{a.emoji()} {a.title[:60]}** fragt:\n\n{q['text']}\n\n"
                       + ("Tipp auf eine Antwort oder schreib sie einfach." if q["optionen"] else "Schreib mir einfach die Antwort.")
                       + f"\n*(Ohne Antwort mache ich nach {int(q['warten_min'])} Min mit einer Annahme weiter.)*", buttons=btns or None)
        except Exception:
            pass


# ---------------------------------------------------------------- Ergebnis zustellen
def _deliver(a):
    """Ergebnis als Chat speichern, Benachrichtigung, ggf. Telegram (mit Dateien)."""
    try:
        msgs = [{"role": "user", "content": f"🤖 Agent-Auftrag: {a.task}"},
                {"role": "assistant", "content": a.result or a.error or "–"}]
        a.chat_id = L.chats.save(None, msgs, f"🤖 {a.title[:60]}")["id"]
        save()
    except Exception:
        pass
    icon = {"fertig": "✅", "fehler": "⚠️", "gestoppt": "🛑"}.get(a.status, "🤖")
    try:
        L.desktop_notify(f"{icon} Agent {a.status}", a.title)
    except Exception:
        pass
    if a.origin == "telegram" and L.BOT:
        try:
            btns = [[{"text": "🔁 Nochmal", "callback_data": f"ag:retry:{a.id}"}]] if a.status != "fertig" else None
            L.BOT.send(f"{icon} **Agent {a.status}:** {a.title}" + (f"\n_{a.error}_" if a.error and a.status != "fertig" else "") + "\n\n"
                       + (a.result or a.error or "")[:3500], buttons=btns)
            for f in a.files[:5]:
                if Path(f).stat().st_size < 45 * 1024 * 1024:
                    L.BOT.send_file(f, caption=Path(f).name)
        except Exception:
            pass


def stop(aid):
    a = AGENTS.get(aid)
    if not a:
        raise RuntimeError("Agent nicht gefunden.")
    for cid in a.children:
        try:
            stop(cid)
        except Exception:
            pass
    if a.question:
        a._answer_ev.set()
    if a.job and a.active():
        a.job.cancelled = True
        a.job._event.set()
    a.status = "gestoppt" if a.active() else a.status
    save()
    return True


def clear_finished():
    with LOCK:
        for k in [k for k, a in AGENTS.items() if not a.active() and not a.parent]:
            for c in AGENTS[k].children:
                AGENTS.pop(c, None)
            AGENTS.pop(k, None)
    save()


# ---------------------------------------------------------------- Telegram: Live-Fortschritt
ST_ICON = {"plant": "🧠", "arbeitet": "⚙️", "wartet": "⏳", "fragt": "❓", "prüft": "🔍", "fertig": "✅", "fehler": "⚠️",
           "gestoppt": "🛑", "startet": "🚀", "unterbrochen": "⏸"}
STEP_ICON = {"offen": "▫️", "läuft": "▶️", "fertig": "✅", "übersprungen": "⏭", "fehler": "❌"}
ST_TEXT = {"plant": "plant", "arbeitet": "arbeitet", "wartet": "wartet auf deine Bestätigung", "fragt": "wartet auf deine Antwort",
           "prüft": "prüft sein Ergebnis", "fertig": "fertig", "fehler": "Fehler", "gestoppt": "gestoppt", "startet": "startet",
           "unterbrochen": "unterbrochen"}


def tg_render(a):
    v = a.view()
    bar = ""
    if v["fortschritt"] is not None:
        n = round(v["fortschritt"] * 10)
        bar = "▓" * n + "░" * (10 - n) + f" {int(v['fortschritt'] * 100)} %\n"
    lines = [f"{v['emoji']} **{a.title[:80]}**", f"{ST_ICON.get(v['status'], '•')} {ST_TEXT.get(v['status'], v['status'])} · {v['minuten']} Min"
             + (f" · ${v['kosten']:.3f}" if v["kosten"] else ""), bar.rstrip("\n")]
    for p in a.plan[:12]:
        lines.append(f"{STEP_ICON.get(p['status'], '▫️')} {p['text'][:70]}")
    kids = [AGENTS[k] for k in a.children if k in AGENTS]
    if kids:
        lines.append("\n**Team:** " + "  ".join(f"{k.emoji()}{ST_ICON.get(k.status, '')}" for k in kids))
    if a.active() and v["aktion"]:
        lines.append(f"\n→ {str(v['aktion'])[:90]}")
    return "\n".join(x for x in lines if x is not None and x != "")


def tg_buttons(a):
    if a.active():
        return [[{"text": "🛑 Stoppen", "callback_data": f"ag:stop:{a.id}"}, {"text": "📋 Verlauf", "callback_data": f"ag:log:{a.id}"}]]
    return [[{"text": "📄 Ganzer Bericht", "callback_data": f"ag:full:{a.id}"}, {"text": "🔁 Nochmal", "callback_data": f"ag:retry:{a.id}"}]]


def _telegram_live(a):
    """Eine Nachricht, die sich während der Arbeit aktualisiert (statt vieler Einzelnachrichten)."""
    if not L.BOT:
        return
    try:
        r = L.BOT.send(tg_render(a), buttons=tg_buttons(a))
        a.tg_msg = (r or {}).get("message_id") if isinstance(r, dict) else None
    except Exception:
        a.tg_msg = None
    if not a.tg_msg:
        return
    last, last_t = "", 0
    while True:
        alive = a.active()
        txt = tg_render(a)
        if txt != last and (time.time() - last_t > 4 or not alive):
            try:
                L.BOT.edit_rich(a.tg_msg, txt, tg_buttons(a))
            except Exception:
                pass
            last, last_t = txt, time.time()
        if not alive:
            break
        time.sleep(2)


# ---------------------------------------------------------------- Werkzeuge für Agenten
def tool_plan(job, steps):
    a = job.agent
    a.plan = [{"text": str(s)[:200], "status": "offen", "notiz": ""} for s in (steps or [])][:12]
    a.status = "arbeitet"
    save()
    return f"Plan mit {len(a.plan)} Schritten gespeichert. Leg los mit Schritt 0."


def tool_step(job, index, status, note=""):
    a = job.agent
    i = int(index)
    if not (0 <= i < len(a.plan)):
        if i == len(a.plan) and len(a.plan) < 15:
            a.plan.append({"text": note or f"Schritt {i + 1}", "status": "offen", "notiz": ""})
        else:
            return "Ungültiger Schritt."
    a.plan[i]["status"] = status if status in ("läuft", "fertig", "übersprungen", "fehler") else "läuft"
    if note:
        a.plan[i]["notiz"] = str(note)[:300]
    return "ok"


def tool_spawn(job, agents, timeout_min=25):
    leader = job.agent
    specs = [x for x in (agents or []) if isinstance(x, dict) and x.get("task")][:MAX_PARALLEL]
    if not specs:
        return "Keine gültigen Teilaufgaben."
    ctx = ("\n\nAntworten des Nutzers auf Rückfragen des Leiters:\n" + "\n".join(f"- {q} → {ans}" for q, ans in leader.answers)) if leader.answers else ""
    kids = [start(f"{s['task']}\n\n(Teil des Auftrags „{leader.task[:300]}“ – dein Team-Leiter wartet auf deinen Bericht.){ctx}",
                  role=s.get("role") if s.get("role") in ROLES and s.get("role") != "leiter" else "allrounder",
                  parent=leader.id, origin=leader.origin) for s in specs]
    for k, s in zip(kids, specs):
        k.title = str(s.get("title") or s["task"])[:90]
    t0 = time.time()
    while any(k.active() for k in kids):
        if job.cancelled:
            for k in kids:
                stop(k.id)
            raise L.Cancelled()
        if time.time() - t0 > timeout_min * 60:
            for k in kids:
                if k.active():
                    stop(k.id)
            break
        time.sleep(1)
    return json.dumps([{"rolle": k.name(), "teilaufgabe": k.title, "status": k.status, "dateien": k.files,
                        "bericht": (k.result or k.error or "")[:6000]} for k in kids], ensure_ascii=False)
