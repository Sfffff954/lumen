"""
Lumen – Docker-Zentrale: Container auf dem eigenen PC und auf SSH-Servern ansehen und steuern.

Der eigentliche Befehl läuft über einen Runner, den lumen.py setzt:
runner(target, argv, timeout, cwd=None) -> (returncode, stdout, stderr)
target = "local" oder ein gespeicherter Servername.
"""
import json
import re

runner = None
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,127}$")
ACTIONS = ("start", "stop", "restart", "pause", "unpause", "update")


def _run(target, argv, timeout=40, cwd=None):
    rc, out, err = runner(target, argv, timeout, cwd)
    if rc != 0:
        e = (err or out or "").strip()
        if "permission denied" in e.lower() and "docker" in e.lower():
            raise RuntimeError("Keine Berechtigung für Docker. Einmalig auf dem Gerät: sudo usermod -aG docker $USER "
                               "(danach neu anmelden).")
        if "command not found" in e or "not recognized" in e or "No such file" in e and argv[0] == "docker":
            raise RuntimeError("Docker ist dort nicht installiert.")
        if "Cannot connect to the Docker daemon" in e:
            raise RuntimeError("Docker läuft nicht (sudo systemctl start docker).")
        raise RuntimeError(e[-500:] or f"Fehler (Code {rc}).")
    return out


def _check_name(name):
    if not NAME_RE.match(str(name or "")):
        raise RuntimeError("Ungültiger Containername.")
    return name


def list_containers(target="local", stats=True):
    out = _run(target, ["docker", "ps", "-a", "--no-trunc", "--format", "{{json .}}"])
    items = []
    for line in out.splitlines():
        try:
            c = json.loads(line)
        except json.JSONDecodeError:
            continue
        labels = dict(kv.split("=", 1) for kv in (c.get("Labels") or "").split(",") if "=" in kv)
        items.append({"name": c.get("Names"), "image": c.get("Image"), "state": c.get("State"),
                      "status": c.get("Status"), "ports": c.get("Ports"), "created": c.get("CreatedAt", "")[:16],
                      "compose": labels.get("com.docker.compose.project"),
                      "health": "unhealthy" if "unhealthy" in (c.get("Status") or "") else
                                "healthy" if "(healthy)" in (c.get("Status") or "") else None})
    if stats and any(i["state"] == "running" for i in items):
        try:
            s_out = _run(target, ["docker", "stats", "--no-stream", "--format", "{{json .}}"], timeout=30)
            st = {}
            for line in s_out.splitlines():
                try:
                    s = json.loads(line)
                    st[s.get("Name")] = s
                except json.JSONDecodeError:
                    pass
            for i in items:
                s = st.get(i["name"])
                if s:
                    i["cpu"] = s.get("CPUPerc")
                    i["ram"] = (s.get("MemUsage") or "").split("/")[0].strip()
                    i["ram_prozent"] = s.get("MemPerc")
        except Exception:
            pass
    items.sort(key=lambda x: (x["state"] != "running", (x["compose"] or "~"), x["name"] or ""))
    return {"ziel": target, "anzahl": len(items), "laufen": sum(1 for i in items if i["state"] == "running"),
            "container": items}


def logs(target, name, lines=200):
    _check_name(name)
    lines = max(10, min(int(lines or 200), 2000))
    rc, out, err = runner(target, ["docker", "logs", "--tail", str(lines), "--timestamps", name], 40, None)
    if rc != 0:
        raise RuntimeError((err or out).strip()[-400:] or "Logs nicht verfügbar.")
    text = "\n".join(x.strip("\n") for x in (out, err) if x and x.strip())  # docker schreibt viele Logs nach stderr
    return {"container": name, "zeilen": lines, "logs": text[-30000:]}


def action(target, name, act):
    _check_name(name)
    if act not in ACTIONS:
        raise RuntimeError("Unbekannte Aktion.")
    if act != "update":
        _run(target, ["docker", act, name], timeout=90)
        return f"{name}: {act} ausgeführt."
    info = _run(target, ["docker", "inspect", "--format", "{{json .Config.Labels}}|{{.Config.Image}}", name])
    labels_json, _, image = info.strip().partition("|")
    try:
        labels = json.loads(labels_json) or {}
    except json.JSONDecodeError:
        labels = {}
    wd = labels.get("com.docker.compose.project.working_dir")
    svc = labels.get("com.docker.compose.service")
    proj = labels.get("com.docker.compose.project")
    if wd and svc and proj:
        for part in (wd, svc, proj):
            if not re.match(r"^[\w./\- ]+$", part):
                raise RuntimeError("Unerwartete Compose-Angaben.")
        _run(target, ["docker", "compose", "-p", proj, "pull", svc], timeout=600, cwd=wd)
        _run(target, ["docker", "compose", "-p", proj, "up", "-d", svc], timeout=600, cwd=wd)
        return f"{name}: neues Image geladen und per Compose neu gestartet ({proj}/{svc})."
    if not re.match(r"^[\w./:@\-]+$", image or ""):
        raise RuntimeError("Image-Name nicht erkannt.")
    out = _run(target, ["docker", "pull", image], timeout=600)
    fresh = "Image is up to date" in out
    return (f"{name}: Image {image} ist schon aktuell." if fresh else
            f"{name}: neues Image {image} geladen. Der Container ist nicht per Compose verwaltet – "
            f"er muss mit seinen bisherigen Einstellungen neu erstellt werden, damit es greift.")
