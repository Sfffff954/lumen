"""
Lumen – Verbindung PC ↔ Lumen-Server (alles über SSH, kein offener Port nötig).

Der PC installiert den Lumen-Server per SSH, schickt Einstellungen/Aufgaben/Notizen/Gedächtnis/Erinnerungen hin,
holt Änderungen zurück und führt Aufträge aus, die du dem Server per Telegram gibst („öffne Discord auf meinem PC“).
"""
import hashlib
import io
import json
import subprocess
import tarfile
import threading
import time
from pathlib import Path

L = None  # lumen-Modul (setzt lumen.py)
STATUS = {"letzter_sync": None, "fehler": None, "heartbeat": None, "aufträge": [], "cfg_hash": None, "pull_ok": None}
SEP = "===LUMEN-SEP==="
REMOTE_DIR = "~/lumen-server"
_busy = threading.Lock()


def _name():
    return (L.load_config().get("lumen_server") or "").strip()


def ssh(cmd, input=None, timeout=60, name=None):
    target, port, key = L._server(name or _name())
    r = subprocess.run(L._ssh_base(port, key) + [target, cmd], input=input, capture_output=True, timeout=timeout)
    out, err = r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")
    if r.returncode == 255:
        raise RuntimeError(L._ssh_error(err, target)[1])
    return r.returncode, out, err


def _bundle():
    """Lumen-Dateien als tar.gz (ohne venvs, Caches)."""
    app = L.APP_DIR
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for p in sorted(app.rglob("*")):
            rel = p.relative_to(app)
            if any(part.startswith(".venv") or part in ("__pycache__", ".git") for part in rel.parts) or p.is_dir():
                continue
            if p.suffix in (".pyc",) or p.stat().st_size > 5_000_000:
                continue
            tar.add(p, arcname=str(rel))
    return buf.getvalue()


SERVICE = """[Unit]
Description=Lumen-Server (persönlicher KI-Assistent, Telegram, Briefing)
After=network-online.target
Wants=network-online.target

[Service]
ExecStart={py} {dir}/lumen.py --server
WorkingDirectory={dir}
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
{user}
[Install]
WantedBy={wanted}
"""


def install(name):
    import brain

    def fn(t):
        steps = ["Verbindung prüfen", "Dateien kopieren", "Python-Umgebung", "Dienst einrichten", "Einstellungen übertragen", "Test-Nachricht"]
        t.steps = [{"name": s, "status": "offen"} for s in steps]

        def step(i, status, detail=""):
            t.steps[i]["status"] = status
            if detail:
                t.steps[i]["detail"] = detail
            t.detail = steps[i] + (f" – {detail}" if detail else "")
            t.progress = (i + (1 if status in ("fertig", "übersprungen") else 0.3)) / len(steps)

        step(0, "läuft")
        rc, out, err = ssh("python3 -c 'import sys;print(\"%d.%d\" % sys.version_info[:2])'; id -u; whoami; "
                           "command -v systemctl >/dev/null && echo systemd || echo nosystemd; echo $HOME", name=name, timeout=30)
        lines = out.split()
        if rc != 0 or len(lines) < 5 or not lines[0][0].isdigit():
            step(0, "fehler", "kein python3")
            raise RuntimeError("Auf dem Server fehlt python3 (ab 3.9). Installieren: sudo apt install python3 python3-venv")
        ver, uid, user, init, home = lines[0], lines[1], lines[2], lines[3], lines[4]
        if tuple(map(int, ver.split("."))) < (3, 9):
            step(0, "fehler", f"Python {ver}")
            raise RuntimeError(f"Python {ver} ist zu alt – mindestens 3.9 nötig.")
        step(0, "fertig", f"{user}@{name} · Python {ver}")

        step(1, "läuft")
        data = _bundle()
        rc, out, err = ssh(f"mkdir -p {REMOTE_DIR} ~/.lumen && chmod 700 ~/.lumen && tar -xzf - -C {REMOTE_DIR} && echo ok",
                           input=data, name=name, timeout=300)
        if rc != 0:
            step(1, "fehler", err[-200:])
            raise RuntimeError("Kopieren fehlgeschlagen: " + err[-300:])
        step(1, "fertig", f"{len(data) // 1024} KB")

        step(2, "läuft", "venv + pypdf, python-docx, reportlab (1–3 Min.)")
        rc, out, err = ssh(f"cd {REMOTE_DIR} && ( [ -x .venv/bin/python ] || python3 -m venv .venv ) && "
                           ".venv/bin/pip install -q --disable-pip-version-check pypdf python-docx reportlab qrcode 2>&1 | tail -3; "
                           "[ -x .venv/bin/python ] && echo VENV_OK", name=name, timeout=900)
        py = f"{home}/lumen-server/.venv/bin/python" if "VENV_OK" in out else "/usr/bin/python3"
        step(2, "fertig" if "VENV_OK" in out else "übersprungen",
             "fertig" if "VENV_OK" in out else "ohne venv (python3-venv fehlt) – PDF/Word-Funktionen evtl. eingeschränkt")

        step(3, "läuft")
        d = f"{home}/lumen-server"
        if init == "systemd" and uid == "0":
            unit = SERVICE.format(py=py, dir=d, user="User=root\n", wanted="multi-user.target")
            cmd = ("cat > /etc/systemd/system/lumen-server.service && systemctl daemon-reload && "
                   "systemctl enable lumen-server >/dev/null 2>&1; systemctl restart lumen-server && echo SVC_OK")
            mode = "system"
        elif init == "systemd":
            unit = SERVICE.format(py=py, dir=d, user="", wanted="default.target")
            cmd = ("mkdir -p ~/.config/systemd/user && cat > ~/.config/systemd/user/lumen-server.service && "
                   "(loginctl enable-linger $(whoami) 2>/dev/null || echo NO_LINGER) && systemctl --user daemon-reload && "
                   "systemctl --user enable lumen-server >/dev/null 2>&1; systemctl --user restart lumen-server && echo SVC_OK")
            mode = "user"
        nohup_cmd = (f"[ -f ~/.lumen/server.pid ] && kill $(cat ~/.lumen/server.pid) 2>/dev/null; sleep 1; cd {d} || exit 1; PYTHONUNBUFFERED=1 setsid nohup {py} lumen.py --server > ~/.lumen/server.log 2>&1 < /dev/null & echo $! > ~/.lumen/server.pid ; "
                     f"(crontab -l 2>/dev/null | grep -v 'lumen.py --server'; echo '@reboot cd {d} && {py} lumen.py --server > "
                     "~/.lumen/server.log 2>&1') | crontab - 2>/dev/null; echo SVC_OK")
        if init != "systemd":
            unit, cmd, mode = "", nohup_cmd, "nohup"
        rc, out, err = ssh(cmd, input=unit.encode(), name=name, timeout=60)
        if "SVC_OK" not in out and mode != "nohup":  # systemd da, aber nicht nutzbar (Container, kein Benutzer-Bus)
            mode = "nohup"
            rc, out, err = ssh(nohup_cmd, name=name, timeout=60)
        if "SVC_OK" not in out:
            step(3, "fehler", (err or out)[-200:])
            raise RuntimeError("Dienst nicht gestartet: " + (err or out)[-400:])
        step(3, "fertig", {"system": "systemd (startet automatisch)", "user": "systemd-Benutzerdienst", "nohup": "Hintergrund + @reboot"}[mode]
             + (" ⚠ ohne linger: läuft nur, solange du eingeloggt bist – Admin: sudo loginctl enable-linger " + user if "NO_LINGER" in out else ""))
        with L.LOCK:
            c = L._load(L.CONFIG_FILE, L.DEFAULT_CONFIG)
            c["lumen_server"], c["lumen_server_mode"] = name, mode
            L._save(L.CONFIG_FILE, c)

        step(4, "läuft")
        push(full=True)
        step(4, "fertig")
        step(5, "läuft")
        if L.integrations.connected("telegram"):
            push(commands=["test_message"], full=False)
            step(5, "fertig", "Schau auf dein Handy 📱")
        else:
            step(5, "übersprungen", "Telegram noch nicht verbunden (Apps → Telegram)")
        t.detail = f"Lumen-Server läuft auf {name}"
        return name

    return brain.run_py_task("lumenserver", "Lumen-Server einrichten", fn)


def _lists():
    st = L.load_state()
    out = {k: st.get(k, []) for k in ("tasks", "notes", "memory", "reminders")}
    out["calendar"] = L.calendars.local_load()
    out["place_reminders"] = L.orte.sync_payload()
    out["automations"] = L.autopilot.sync_payload()
    out["heartbeat"] = {k: v for k, v in L.autopilot.hb_get().items() if k in ("an", "minuten", "checkliste", "ruhe_von", "ruhe_bis")}
    return out


def _h(v):
    return hashlib.sha1(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def config_payload():
    cfg = L.load_config()
    conf = {k: cfg.get(k) for k in L.SYNC_CONFIG_KEYS if k in cfg}
    if conf.get("provider") in ("ollama",):
        conf["provider"] = "auto" if any(cfg.get(k + "_key") for k in ("anthropic", "openai", "gemini", "deepseek")) else "ollama"
    if cfg.get("sync_keys", True):
        conf.update({k: cfg.get(k) for k in L.SYNC_KEY_KEYS if cfg.get(k)})
    apps = {k: v for k, v in (cfg.get("apps") or {}).items() if k in L.SYNC_APPS and v}
    plugs = {}
    for p in L.plugins.listing():
        if p["an"] and not p["fehler"]:
            try:
                plugs[p["name"]] = (L.plugins.DIR / p["datei"]).read_text("utf-8")
            except Exception:
                pass
    return {"config": conf, "apps": apps, "plugins": plugs}


def push(commands=None, full=True, lists=None):
    payload = {"commands": commands or []}
    if full:
        payload.update(config_payload())
        payload["lists"] = lists if lists is not None else _lists()
    elif lists is not None:
        payload["lists"] = lists
    data = json.dumps(payload, ensure_ascii=False).encode()
    rc, out, err = ssh("mkdir -p ~/.lumen && umask 077 && cat > ~/.lumen/sync_in.json.tmp && mv ~/.lumen/sync_in.json.tmp ~/.lumen/sync_in.json && echo OK",
                       input=data, timeout=40)
    if "OK" not in out:
        raise RuntimeError("Übertragen fehlgeschlagen: " + err[-300:])
    if full:
        STATUS["cfg_hash"] = _h(config_payload())
        _remember_base(payload.get("lists") or _lists())
    STATUS["letzter_sync"] = time.time()
    return True


def _remember_base(lists):
    with L.LOCK:
        st = L.load_state()
        st["_sync_base"] = {k: _h(v) for k, v in lists.items()}
        L._save(L.STATE_FILE, st)


def _merge(k, a, b):
    """Vereinigung nach id; Flags (erledigt/gesendet) gewinnen."""
    kf = lambda x: x.get("id") or x.get("uid") or json.dumps(x, sort_keys=True)  # noqa: E731
    out = {kf(x): dict(x) for x in a}
    for x in b:
        key = kf(x)
        if key in out:
            for f in ("done", "sent_tg", "sent_local"):
                if x.get(f):
                    out[key][f] = True
        else:
            out[key] = dict(x)
    return list(out.values())


def pull():
    cmd = (f"cat ~/.lumen/data.json 2>/dev/null; echo; echo {SEP}; cat ~/.lumen/heartbeat.json 2>/dev/null; echo; echo {SEP}; "
           f"cat ~/.lumen/calendar.json 2>/dev/null; echo; echo {SEP}; "
           "touch ~/.lumen/pc_seen; f=~/.lumen/pc_queue.jsonl; if [ -f $f ]; then mv $f $f.taken && cat $f.taken && rm -f $f.taken; fi")
    rc, out, err = ssh(cmd, timeout=40)
    parts = out.split(SEP)
    if len(parts) < 4:
        raise RuntimeError("Unerwartete Antwort vom Server.")

    def js(t, default):
        try:
            return json.loads(t.strip() or "null") or default
        except json.JSONDecodeError:
            return default
    remote = js(parts[0], {})
    if isinstance(remote, dict):
        remote["calendar"] = js(parts[2], [])
    return remote, js(parts[1], {}), [js(line, None) for line in parts[3].splitlines() if line.strip()]


def tick():
    """Jede Minute: Heartbeat holen, Listen abgleichen, PC-Aufträge ausführen, geänderte Einstellungen schicken."""
    if not _name() or not _busy.acquire(blocking=False):
        return
    try:
        remote, hb, queue = pull()
        STATUS["heartbeat"], STATUS["pull_ok"], STATUS["fehler"] = hb, time.time(), None
        local = _lists()
        base = L.load_state().get("_sync_base") or {}
        new_local, new_remote, changed_l, changed_r = {}, {}, False, False
        for k in local:
            lv, rv = local[k], remote.get(k, []) if isinstance(remote, dict) else []
            hl, hr, hb_ = _h(lv), _h(rv), base.get(k)
            if hl == hr:
                v = lv
            elif hr == hb_:
                v, changed_r = lv, True          # nur hier geändert → hinschicken
            elif hl == hb_:
                v, changed_l = rv, True          # nur dort geändert (z. B. per Telegram) → übernehmen
            else:
                v, changed_l, changed_r = _merge(k, lv, rv), True, True
            new_local[k] = new_remote[k] = v
        if changed_l:
            with L.LOCK:
                st = L.load_state()
                for k, v in new_local.items():
                    if k != "calendar":
                        st[k] = v
                L._save(L.STATE_FILE, st)
            if _h(new_local["calendar"]) != _h(local["calendar"]):
                L.calendars.local_save(new_local["calendar"])
        cfg_changed = _h(config_payload()) != STATUS.get("cfg_hash")
        if changed_r or cfg_changed:
            push(full=True, lists=new_remote)
        else:
            _remember_base(new_local)
            STATUS["letzter_sync"] = time.time()
        for task in [q for q in queue if q and q.get("task")]:
            threading.Thread(target=run_pc_task, args=(task,), daemon=True).start()
    except Exception as e:
        STATUS["fehler"] = str(e)[:300]
    finally:
        _busy.release()


def run_pc_task(task):
    STATUS["aufträge"] = (STATUS["aufträge"] + [{"task": task["task"], "zeit": time.time(), "status": "läuft"}])[-10:]
    entry = STATUS["aufträge"][-1]
    L.desktop_notify("📱 Auftrag per Telegram", task["task"])
    job = L.Job(L.load_config())
    job.no_confirm = True   # aus der Ferne: nichts Riskantes ohne Bestätigung am PC
    L.JOBS[job.id] = job
    try:
        text = L.run_chat(job, [{"role": "user", "content": "(Auftrag vom Nutzer per Telegram über den Lumen-Server – er sitzt "
                                                            "gerade NICHT am PC. Riskante Aktionen sind gesperrt; sag dann, dass er "
                                                            "das am PC bestätigen muss.)\n" + task["task"]}])
        entry["status"] = "fertig"
    except Exception as e:
        text = f"⚠️ Fehler am PC: {e}"
        entry["status"] = "fehler"
    acts = [("✓ " if a.get("ok") else "✗ ") + a["text"] for a in job.actions][:8]
    result = {"id": task.get("id"), "task": task["task"], "text": text + ("\n\n" + "\n".join(acts) if acts else "")}
    try:
        ssh("cat >> ~/.lumen/pc_results.jsonl", input=(json.dumps(result, ensure_ascii=False) + "\n").encode(), timeout=30)
    except Exception as e:
        STATUS["fehler"] = f"Ergebnis nicht zurückgeschickt: {e}"


def control(action):
    mode = L.load_config().get("lumen_server_mode") or "user"
    sc = {"system": "systemctl", "user": "systemctl --user"}.get(mode)
    jc = {"system": "journalctl -u lumen-server", "user": "journalctl --user -u lumen-server"}.get(mode)
    if action == "logs":
        cmd = f"{jc} -n 80 --no-pager 2>&1 | tail -80" if jc else "tail -80 ~/.lumen/server.log"
    elif action in ("start", "stop", "restart"):
        cmd = f"{sc} {action} lumen-server && echo OK" if sc else (
            "[ -f ~/.lumen/server.pid ] && kill $(cat ~/.lumen/server.pid) 2>/dev/null; sleep 1; echo OK" if action == "stop" else
            f"[ -f ~/.lumen/server.pid ] && kill $(cat ~/.lumen/server.pid) 2>/dev/null; sleep 1; cd {REMOTE_DIR} || exit 1; PYTHONUNBUFFERED=1 setsid nohup .venv/bin/python lumen.py --server > ~/.lumen/server.log 2>&1 < /dev/null & echo $! > ~/.lumen/server.pid ; echo OK")
    elif action == "uninstall":
        cmd = ((f"{sc} disable --now lumen-server; rm -f /etc/systemd/system/lumen-server.service ~/.config/systemd/user/lumen-server.service; "
                f"{sc} daemon-reload; ") if sc else "[ -f ~/.lumen/server.pid ] && kill $(cat ~/.lumen/server.pid) 2>/dev/null; sleep 1; (crontab -l | grep -v 'lumen.py --server') | crontab -; ") + \
            f"rm -rf {REMOTE_DIR}; echo OK"
    else:
        raise RuntimeError("Unbekannte Aktion.")
    rc, out, err = ssh(cmd, timeout=60)
    if action == "uninstall":
        with L.LOCK:
            c = L._load(L.CONFIG_FILE, L.DEFAULT_CONFIG)
            c["lumen_server"] = ""
            L._save(L.CONFIG_FILE, c)
    return (out + err).strip()[-6000:]


def view():
    name = _name()
    hb = STATUS.get("heartbeat") or {}
    age = time.time() - hb["zeit"] if hb.get("zeit") else None
    return {"name": name, "online": age is not None and age < 150, "heartbeat_alter": age, "heartbeat": hb,
            "letzter_sync": STATUS.get("letzter_sync"), "fehler": STATUS.get("fehler"), "aufträge": STATUS.get("aufträge")}
