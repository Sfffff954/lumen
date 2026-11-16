"""Prüft, ob Webseiten erreichbar sind und wie schnell sie antworten."""
import time
import urllib.request


def webseiten_check(args):
    out = []
    for url in [u.strip() for u in str(args.get("urls", "")).split(",") if u.strip()][:10]:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        t = time.time()
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Lumen-Plugin"})
            with urllib.request.urlopen(req, timeout=15) as r:
                out.append({"url": url, "status": r.status, "ms": int((time.time() - t) * 1000), "ok": 200 <= r.status < 400})
        except Exception as e:
            out.append({"url": url, "ok": False, "fehler": str(e)[:200]})
    return out


TOOLS = [{"name": "webseiten_check", "description": "Prüft, ob Webseiten online sind (Status-Code, Antwortzeit).",
          "parameters": {"urls": {"type": "string", "description": "Eine oder mehrere Adressen, durch Komma getrennt"}},
          "required": ["urls"], "run": webseiten_check}]
