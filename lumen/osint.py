"""
Lumen – Sicherheits- & OSINT-Werkzeuge.

Domains:  Whois (RDAP), DNS (DNS-over-HTTPS), Subdomains (crt.sh), SSL-Zertifikat, Technik-Erkennung, Wayback Machine
Netz:     IP-Infos, Shodan/InternetDB, Port-Scan (nur eigene Server/Geräte), Ping/Traceroute
Links:    Kurzlinks aufklappen, Phishing-Check, VirusTotal, Mail-Header-Analyse
Dateien:  Metadaten lesen/entfernen (Fotos, PDF, Office), Bild-Prüfung (Hashes, ELA), Bild-Rückwärtssuche
Selbst:   Datenleck-Check & Benutzernamen-Check (nur eigene, in den Einstellungen hinterlegt), Passwort-Check (anonym)

Bewusst NICHT enthalten: Personensuche, Profile über Privatpersonen.
"""
import base64
import email
import email.policy
import email.utils
import hashlib
import io
import ipaddress
import json
import platform
import re
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import web

OS = platform.system()
OUT_DIR = Path.home() / ".lumen" / "osint"
UA = "Lumen-Assistant/1.0 (+lokaler persoenlicher Assistent)"


# ================================================================ HTTP helpers
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_PLAIN = urllib.request.build_opener(_NoRedirect)


def _req(url, method="GET", headers=None, data=None, timeout=20, allow_private=False, follow=True, max_bytes=3_000_000):
    """Wie http_get, aber gibt (status, headers, body) auch bei 4xx/5xx zurück."""
    host = urllib.parse.urlparse(url).hostname or ""
    if not allow_private and web._private(host):
        raise RuntimeError("Lokale/private Adressen werden hier nicht abgefragt.")
    h = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.5"}
    h.update(headers or {})
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    req.allow_private = allow_private
    opener = web._OPENER if follow else _PLAIN
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.headers, r.read(max_bytes)
    except urllib.error.HTTPError as e:
        try:
            body = e.read(max_bytes)
        except Exception:
            body = b""
        return e.code, e.headers, body
    except urllib.error.URLError as e:
        raise RuntimeError(f"Nicht erreichbar: {e.reason}")
    except socket.timeout:
        raise RuntimeError("Zeitüberschreitung.")


def _json(url, **kw):
    status, headers, body = _req(url, **kw)
    try:
        return status, json.loads(body or b"null")
    except json.JSONDecodeError:
        return status, None


def _host_of(target):
    t = str(target).strip()
    if "://" not in t:
        t = "http://" + t
    host = urllib.parse.urlparse(t).hostname or ""
    if not host:
        raise RuntimeError("Keine gültige Domain/Adresse.")
    return host.lower().rstrip(".")


SECOND_LEVEL = {"co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.at", "or.at", "co.jp",
                "com.br", "com.tr", "co.nz", "co.za", "com.mx", "com.cn", "com.pl", "co.in", "com.ar"}


def registrable(host):
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _is_ip(s):
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


# ================================================================ Domains
def _rdap_events(d):
    ev = {}
    for e in d.get("events", []) or []:
        ev[e.get("eventAction")] = (e.get("eventDate") or "")[:10]
    return ev


def _vcard_name(entity):
    try:
        for item in entity.get("vcardArray", [None, []])[1]:
            if item[0] in ("fn", "org") and item[3]:
                return item[3] if isinstance(item[3], str) else " ".join(item[3])
    except Exception:
        pass
    return entity.get("handle", "")


def whois(domain):
    host = _host_of(domain)
    dom = registrable(host) if not _is_ip(host) else host
    kind = "ip" if _is_ip(dom) else "domain"
    status, d = _json(f"https://rdap.org/{kind}/{dom}", timeout=20)
    if status == 200 and isinstance(d, dict):
        ev = _rdap_events(d)
        res = {"domain": dom, "quelle": "RDAP"}
        if kind == "domain":
            res.update({"registriert": ev.get("registration"), "läuft_ab": ev.get("expiration"),
                        "zuletzt_geändert": ev.get("last changed"), "status": d.get("status"),
                        "nameserver": [n.get("ldhName") for n in d.get("nameservers", []) or []][:8]})
        else:
            res.update({"netz": d.get("name"), "bereich": f"{d.get('startAddress')} – {d.get('endAddress')}",
                        "land": d.get("country")})
        roles = {}
        for ent in d.get("entities", []) or []:
            for role in ent.get("roles", []) or []:
                name = _vcard_name(ent)
                if name and role in ("registrar", "registrant", "abuse", "administrative", "technical"):
                    roles.setdefault(role, name)
            for sub in ent.get("entities", []) or []:
                if "abuse" in (sub.get("roles") or []):
                    for item in (sub.get("vcardArray") or [None, []])[1]:
                        if item[0] == "email":
                            roles.setdefault("abuse_email", item[3])
        res.update(roles)
        if ev.get("registration"):
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(ev["registration"] + "T00:00:00+00:00")).days
                res["alter_tage"] = age
            except Exception:
                pass
        return res
    if shutil.which("whois"):
        r = subprocess.run(["whois", dom], capture_output=True, text=True, timeout=25, errors="replace")
        keep = [l.strip() for l in r.stdout.splitlines()
                if re.match(r"\s*(Domain|Registrar|Creation|Created|Changed|Updated|Expir|Registry Expiry|Status|"
                            r"Name Server|Nserver|Registrant Organization|Registrant Country|org|country|netname)",
                            l, re.I)]
        return {"domain": dom, "quelle": "whois", "auszug": keep[:40] or r.stdout[:3000]}
    raise RuntimeError(f"Keine Whois-Daten gefunden (RDAP-Status {status}).")


def domain_age_days(host):
    try:
        return whois(registrable(host)).get("alter_tage")
    except Exception:
        return None


DNS_TYPES = {"A": 1, "AAAA": 28, "CNAME": 5, "MX": 15, "NS": 2, "TXT": 16, "SOA": 6, "CAA": 257}


def _doh(name, rtype):
    status, d = _json("https://cloudflare-dns.com/dns-query?" + urllib.parse.urlencode({"name": name, "type": rtype}),
                      headers={"Accept": "application/dns-json"}, timeout=10)
    if status != 200 or not isinstance(d, dict):
        raise RuntimeError("DNS-Abfrage fehlgeschlagen")
    return [a.get("data", "").strip('"') if rtype == "TXT" else a.get("data", "")
            for a in d.get("Answer", []) or [] if a.get("type") == DNS_TYPES.get(rtype)]


def _dig(name, rtype):
    r = subprocess.run(["dig", "+short", rtype, name], capture_output=True, text=True, timeout=10)
    return [l.strip().strip('"') for l in r.stdout.splitlines() if l.strip()]


def dns_lookup(domain, types=None):
    host = _host_of(domain)
    types = [t.upper() for t in (types or ["A", "AAAA", "CNAME", "MX", "NS", "TXT", "CAA"]) if t.upper() in DNS_TYPES]
    res, method = {"domain": host}, None
    for t in types:
        try:
            res[t] = _doh(host, t)
            method = "DNS-over-HTTPS"
        except Exception:
            if shutil.which("dig"):
                res[t] = _dig(host, t)
                method = "dig"
            elif t in ("A", "AAAA"):
                fam = socket.AF_INET if t == "A" else socket.AF_INET6
                try:
                    res[t] = sorted({i[4][0] for i in socket.getaddrinfo(host, None, fam)})
                except socket.gaierror:
                    res[t] = []
                method = "System"
    res["methode"] = method
    # Mail-Sicherheit
    base = registrable(host)
    try:
        txt = res.get("TXT") if host == base else (_doh(base, "TXT") if method == "DNS-over-HTTPS" else [])
        spf = [t for t in txt or [] if t.lower().startswith("v=spf1")]
        dmarc = [t for t in (_doh("_dmarc." + base, "TXT") if method == "DNS-over-HTTPS"
                             else (_dig("_dmarc." + base, "TXT") if shutil.which("dig") else []))
                 if t.lower().startswith("v=dmarc1")]
        m = re.search(r"p=(\w+)", dmarc[0]) if dmarc else None
        res["mail_schutz"] = {
            "spf": spf[0] if spf else "FEHLT – jeder kann Mails in diesem Namen fälschen",
            "dmarc": dmarc[0] if dmarc else "FEHLT",
            "bewertung": ("gut" if spf and m and m.group(1) in ("reject", "quarantine") else
                          "schwach (DMARC nur 'none')" if spf and dmarc else "unsicher")}
    except Exception:
        pass
    return res


def subdomains(domain):
    base = registrable(_host_of(domain))
    status, d = _json("https://crt.sh/?" + urllib.parse.urlencode({"q": f"%.{base}", "output": "json"}), timeout=45)
    if status != 200 or not isinstance(d, list):
        raise RuntimeError(f"crt.sh antwortet nicht (Status {status}). Später nochmal versuchen.")
    names = set()
    for row in d:
        for n in str(row.get("name_value", "")).splitlines():
            n = n.strip().lower().lstrip("*.")
            if n.endswith(base):
                names.add(n)
    names = sorted(names)
    return {"domain": base, "anzahl": len(names), "subdomains": names[:300],
            "hinweis": "Aus öffentlichen Zertifikats-Logs. Nicht jede Subdomain ist noch aktiv."}


def ssl_check(target, port=443):
    host = _host_of(target)
    port = int(port or 443)
    res = {"host": host, "port": port}
    pem = None
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=10) as sock, ctx.wrap_socket(sock, server_hostname=host) as s:
            cert = s.getpeercert()
            res.update(gültig=True, tls=s.version(), cipher=s.cipher()[0])
    except ssl.SSLCertVerificationError as e:
        res.update(gültig=False, fehler=e.verify_message or str(e))
        cert = None
    except (OSError, ssl.SSLError) as e:
        raise RuntimeError(f"Keine TLS-Verbindung zu {host}:{port} ({e}).")
    if cert is None:  # Details trotzdem anzeigen
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=10) as sock, ctx.wrap_socket(sock, server_hostname=host) as s:
            der = s.getpeercert(binary_form=True)
            res.update(tls=s.version())
        pem = ssl.DER_cert_to_PEM_cert(der)
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
            f.write(pem)
        try:
            cert = ssl._ssl._test_decode_cert(f.name)  # CPython-intern, aber stabil
        except Exception:
            cert = {}
        finally:
            Path(f.name).unlink(missing_ok=True)

    def flat(seq):
        return {k: v for part in seq or [] for k, v in part}
    subj, iss = flat(cert.get("subject")), flat(cert.get("issuer"))
    res["für"] = subj.get("commonName")
    res["aussteller"] = " · ".join(x for x in (iss.get("organizationName"), iss.get("commonName")) if x)
    res["namen"] = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"][:25]
    nb, na = cert.get("notBefore"), cert.get("notAfter")
    if na:
        exp = datetime.strptime(na, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        res["gültig_von"] = datetime.strptime(nb, "%b %d %H:%M:%S %Y %Z").strftime("%d.%m.%Y") if nb else None
        res["gültig_bis"] = exp.strftime("%d.%m.%Y")
        res["tage_übrig"] = (exp - datetime.now(timezone.utc)).days
        if res["tage_übrig"] < 0:
            res["warnung"] = "Zertifikat ist abgelaufen!"
        elif res["tage_übrig"] < 14:
            res["warnung"] = "Läuft bald ab – erneuern (z. B. certbot renew)."
    if subj.get("commonName") == iss.get("commonName"):
        res["selbst_signiert"] = True
    return res


TECH = [
    ("WordPress", r"wp-content|wp-includes|wp-json"), ("Joomla", r"/media/jui/|Joomla!"), ("Drupal", r"Drupal|/sites/default/files"),
    ("Shopify", r"cdn\.shopify\.com|Shopify\.theme"), ("Wix", r"static\.wixstatic\.com|wix\.com"), ("Squarespace", r"squarespace"),
    ("Jimdo", r"jimdo"), ("Webflow", r"webflow"), ("Ghost", r"ghost-(?:url|portal)|content=\"Ghost"),
    ("Next.js", r"__NEXT_DATA__|/_next/static"), ("Nuxt", r"__NUXT__|/_nuxt/"), ("Gatsby", r"___gatsby"),
    ("Astro", r"astro-island|/_astro/"), ("SvelteKit", r"__sveltekit|/_app/immutable"), ("React", r"data-reactroot|react-dom"),
    ("Vue", r"data-v-[0-9a-f]{8}|vue(?:\.min)?\.js"), ("Angular", r"ng-version="), ("jQuery", r"jquery(?:\.min)?\.js"),
    ("Bootstrap", r"bootstrap(?:\.min)?\.(?:css|js)"), ("Tailwind", r"tailwind"), ("Google Analytics", r"googletagmanager|google-analytics"),
    ("Matomo", r"matomo|piwik"), ("Cloudflare Turnstile", r"challenges\.cloudflare\.com"), ("reCAPTCHA", r"recaptcha"),
    ("Hugo", r"content=\"Hugo"), ("Typo3", r"typo3"), ("Magento", r"Magento|mage/"), ("WooCommerce", r"woocommerce"),
]
SEC_HEADERS = {"strict-transport-security": "HSTS", "content-security-policy": "CSP", "x-frame-options": "Clickjacking-Schutz",
               "x-content-type-options": "MIME-Sniffing-Schutz", "referrer-policy": "Referrer-Policy",
               "permissions-policy": "Permissions-Policy"}


def site_tech(url):
    if not re.match(r"^https?://", url.strip()):
        url = "https://" + url.strip()
    status, headers, raw = _req(url, headers={"User-Agent": web.UA, "Accept": "text/html"}, timeout=20)
    html_txt = raw[:600000].decode("utf-8", errors="replace")
    h = {k.lower(): v for k, v in headers.items()}
    found = [name for name, pat in TECH if re.search(pat, html_txt, re.I)]
    gen = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', html_txt, re.I)
    cdn = []
    if "cf-ray" in h or "cloudflare" in h.get("server", "").lower():
        cdn.append("Cloudflare")
    if "x-amz-cf-id" in h:
        cdn.append("Amazon CloudFront")
    if "x-served-by" in h and "cache" in h.get("x-served-by", ""):
        cdn.append("Fastly")
    if "akamai" in json.dumps(h).lower():
        cdn.append("Akamai")
    if h.get("x-vercel-id"):
        cdn.append("Vercel")
    if "netlify" in h.get("server", "").lower():
        cdn.append("Netlify")
    present = {v: ("✓" if k in h else "fehlt") for k, v in SEC_HEADERS.items()}
    cookies = headers.get_all("Set-Cookie") or []
    insecure = [c.split("=")[0] for c in cookies if "secure" not in c.lower() or "httponly" not in c.lower()]
    return {"url": url, "status": status, "server": h.get("server"), "powered_by": h.get("x-powered-by"),
            "generator": gen.group(1) if gen else None, "technik": found, "cdn": cdn,
            "sicherheits_header": present,
            "cookies_ohne_secure_oder_httponly": insecure[:10]}


def wayback(url):
    u = url.strip()
    status, d = _json("https://archive.org/wayback/available?" + urllib.parse.urlencode({"url": u}), timeout=20)
    closest = ((d or {}).get("archived_snapshots") or {}).get("closest") if isinstance(d, dict) else None
    status2, rows = _json("https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(
        {"url": u, "output": "json", "fl": "timestamp,statuscode", "collapse": "timestamp:6", "limit": "2000"}), timeout=40)
    years = {}
    first = last = None
    if isinstance(rows, list) and len(rows) > 1:
        for ts, code in rows[1:]:
            years[ts[:4]] = years.get(ts[:4], 0) + 1
        first, last = rows[1][0], rows[-1][0]
    fmt = lambda ts: f"{ts[6:8]}.{ts[4:6]}.{ts[:4]}" if ts else None
    return {"url": u, "erster_snapshot": fmt(first), "letzter_snapshot": fmt(last),
            "monate_mit_snapshots_pro_jahr": years,
            "nächster_snapshot": closest.get("url") if closest else None,
            "alle_snapshots": f"https://web.archive.org/web/*/{u}",
            "hinweis": None if first else "Keine archivierten Versionen gefunden."}


# ================================================================ IPs & network
def _resolve(target):
    host = _host_of(target)
    if _is_ip(host):
        return host, host
    try:
        return host, socket.gethostbyname(host)
    except socket.gaierror:
        raise RuntimeError(f"'{host}' konnte nicht aufgelöst werden.")


def ip_info(target):
    host, ip = _resolve(target)
    ipo = ipaddress.ip_address(ip)
    if ipo.is_private or ipo.is_loopback:
        return {"ziel": host, "ip": ip, "hinweis": "Private/lokale Adresse (dein Heimnetz) – keine öffentlichen Infos."}
    status, d = _json(f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,org,as,asname,"
                      f"reverse,proxy,hosting,mobile,query&lang=de", timeout=15)
    res = {"ziel": host, "ip": ip}
    if isinstance(d, dict) and d.get("status") == "success":
        res.update({"land": d.get("country"), "region": d.get("regionName"), "ungefährer_ort": d.get("city"),
                    "anbieter": d.get("isp"), "organisation": d.get("org"), "asn": d.get("as"),
                    "reverse_dns": d.get("reverse"), "vpn_oder_proxy": d.get("proxy"),
                    "rechenzentrum": d.get("hosting"), "mobilfunk": d.get("mobile"),
                    "hinweis": "IP-Standorte sind nur grob (Ort des Anbieters, nicht einer Person)."})
    try:
        res["shodan_internetdb"] = internetdb(ip)
    except Exception:
        pass
    return res


def internetdb(ip):
    status, d = _json(f"https://internetdb.shodan.io/{ip}", timeout=15)
    if status == 404:
        return {"ports": [], "hinweis": "Shodan kennt keine offenen Dienste für diese IP."}
    if not isinstance(d, dict):
        raise RuntimeError("InternetDB nicht erreichbar.")
    return {"offene_ports": d.get("ports"), "hostnamen": d.get("hostnames"), "cpes": d.get("cpes", [])[:15],
            "bekannte_schwachstellen": d.get("vulns", [])[:20], "tags": d.get("tags")}


def shodan_lookup(target, key=""):
    host, ip = _resolve(target)
    if not key:
        return {"ip": ip, "quelle": "Shodan InternetDB (kostenlos)", **internetdb(ip)}
    status, d = _json(f"https://api.shodan.io/shodan/host/{ip}?key={urllib.parse.quote(key)}", timeout=25)
    if status == 401:
        raise RuntimeError("Shodan-Key ungültig.")
    if status == 404:
        return {"ip": ip, "hinweis": "Shodan hat diese IP nicht gescannt."}
    if not isinstance(d, dict):
        raise RuntimeError(f"Shodan-Fehler {status}.")
    services = [{"port": s.get("port"), "dienst": s.get("product") or s.get("_shodan", {}).get("module"),
                 "version": s.get("version"), "zuletzt": (s.get("timestamp") or "")[:10]} for s in d.get("data", [])][:30]
    return {"ip": ip, "quelle": "Shodan", "organisation": d.get("org"), "os": d.get("os"), "dienste": services,
            "schwachstellen": list((d.get("vulns") or {}))[:25], "zuletzt_gescannt": d.get("last_update", "")[:10]}


_own_ip_cache = {"t": 0, "ip": None}


def own_public_ip():
    if time.time() - _own_ip_cache["t"] < 600 and _own_ip_cache["ip"]:
        return _own_ip_cache["ip"]
    for url in ("https://api.ipify.org?format=json", "https://ifconfig.co/json"):
        try:
            status, d = _json(url, timeout=10)
            ip = (d or {}).get("ip")
            if ip:
                _own_ip_cache.update(t=time.time(), ip=ip)
                return ip
        except Exception:
            continue
    return None


COMMON_PORTS = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
                443: "HTTPS", 445: "SMB", 465: "SMTPS", 587: "SMTP-Submission", 853: "DNS-over-TLS", 993: "IMAPS",
                995: "POP3S", 1194: "OpenVPN", 1433: "MSSQL", 1883: "MQTT", 2049: "NFS", 2375: "Docker (ungeschützt!)",
                2376: "Docker TLS", 3000: "Web-App/Grafana", 3306: "MySQL", 3389: "Remote Desktop", 5000: "Web-App",
                5432: "PostgreSQL", 5900: "VNC", 6379: "Redis", 8000: "Web-App", 8080: "HTTP-Alt", 8081: "HTTP-Alt",
                8123: "Home Assistant", 8443: "HTTPS-Alt", 8888: "Web-App", 9000: "Portainer/Web", 9090: "Prometheus/Cockpit",
                9100: "Node-Exporter", 9200: "Elasticsearch", 11211: "Memcached", 19999: "Netdata", 25565: "Minecraft",
                27017: "MongoDB", 32400: "Plex", 51820: "WireGuard (UDP)", 8096: "Jellyfin", 9443: "Portainer"}
RISKY = {23: "Telnet ist unverschlüsselt – abschalten.", 2375: "Docker-API ohne TLS = volle Kontrolle für jeden!",
         6379: "Redis sollte nie öffentlich sein.", 27017: "MongoDB sollte nie öffentlich sein.",
         9200: "Elasticsearch sollte nie öffentlich sein.", 11211: "Memcached sollte nie öffentlich sein.",
         3389: "Remote Desktop öffentlich = häufiges Angriffsziel.", 445: "SMB öffentlich = sehr gefährlich.",
         5900: "VNC öffentlich nur mit starkem Passwort/VPN.", 3306: "Datenbank besser nur intern.",
         5432: "Datenbank besser nur intern.", 21: "FTP ist unverschlüsselt – besser SFTP."}


def port_scan(host, ip, ports=None, timeout=1.0):
    ports = sorted({int(p) for p in (ports or COMMON_PORTS) if 0 < int(p) < 65536})[:1024]
    open_ports = []

    def probe(p):
        try:
            with socket.create_connection((ip, p), timeout=timeout) as s:
                banner = ""
                if p in (21, 22, 25, 110, 143, 587):
                    s.settimeout(1.5)
                    try:
                        banner = s.recv(160).decode("utf-8", errors="replace").strip()
                    except Exception:
                        pass
                return p, banner
        except Exception:
            return None
    with ThreadPoolExecutor(64) as ex:
        for r in ex.map(probe, ports):
            if r:
                p, banner = r
                item = {"port": p, "dienst": COMMON_PORTS.get(p, "?")}
                if banner:
                    item["banner"] = banner[:120]
                if p in RISKY:
                    item["warnung"] = RISKY[p]
                open_ports.append(item)
    return {"ziel": host, "ip": ip, "geprüfte_ports": len(ports), "offen": open_ports,
            "hinweis": "Scan von deinem PC aus. Was das Internet sieht, zeigt shodan_lookup."}


_SAFE_HOST = re.compile(r"^[A-Za-z0-9.\-:]+$")


def net_diag(target, kind="ping"):
    host = _host_of(target)
    if not _SAFE_HOST.match(host):
        raise RuntimeError("Ungültiger Host.")
    win = OS == "Windows"
    if kind == "ping":
        cmd = ["ping", "-n" if win else "-c", "4", host]
    else:
        for tool, args in (("mtr", ["mtr", "-r", "-c", "3", "-n", host]), ("traceroute", ["traceroute", "-n", "-w", "2", "-q", "1", host]),
                           ("tracepath", ["tracepath", "-n", host]), ("tracert", ["tracert", "-d", "-w", "1500", host])):
            if shutil.which(tool):
                cmd = args
                break
        else:
            raise RuntimeError("Kein traceroute/tracepath/mtr installiert.")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90, errors="replace")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Zeitüberschreitung.")
    return {"befehl": " ".join(cmd), "ausgabe": (r.stdout or r.stderr)[-5000:]}


# ================================================================ links & threats
def expand_url(url, max_hops=15):
    u = url.strip()
    if not re.match(r"^https?://", u):
        u = "http://" + u
    chain = []
    for _ in range(max_hops):
        try:
            status, headers, body = _req(u, method="GET", follow=False, timeout=15, max_bytes=200_000,
                                         headers={"User-Agent": web.UA, "Accept": "text/html,*/*"})
        except RuntimeError as e:
            chain.append({"url": u, "fehler": str(e)})
            break
        step = {"url": u, "status": status}
        chain.append(step)
        nxt = None
        if status in (301, 302, 303, 307, 308) and headers.get("Location"):
            nxt = urllib.parse.urljoin(u, headers["Location"])
        elif status == 200 and b"<" in body[:2000]:
            txt = body.decode("utf-8", errors="replace")
            m = re.search(r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\']?\d+\s*;\s*url=([^"\'>]+)', txt, re.I)
            if m:
                nxt = urllib.parse.urljoin(u, m.group(1).strip())
                step["art"] = "Meta-Refresh"
            else:
                m = re.search(r'(?:window\.)?location(?:\.href)?\s*=\s*["\'](https?://[^"\']+)', txt[:20000])
                if m and len(txt) < 20000:
                    nxt = m.group(1)
                    step["art"] = "JavaScript-Weiterleitung"
        if not nxt or nxt == u:
            break
        u = nxt
    final = chain[-1]["url"]
    return {"start": url, "ziel": final, "ziel_domain": _host_of(final), "weiterleitungen": len(chain) - 1, "kette": chain}


BRANDS = {
    "paypal": ["paypal.com", "paypal.de", "paypal.me", "paypalobjects.com"], "amazon": ["amazon.de", "amazon.com", "amazon.co.uk", "amazon.at", "amazonaws.com", "amzn.to"],
    "google": ["google.com", "google.de", "gmail.com", "youtube.com", "goo.gl", "googleusercontent.com"],
    "apple": ["apple.com", "icloud.com", "apple.de"], "microsoft": ["microsoft.com", "live.com", "outlook.com", "office.com", "microsoftonline.com", "office365.com"],
    "netflix": ["netflix.com"], "steam": ["steampowered.com", "steamcommunity.com", "steamstatic.com"],
    "steamcommunity": ["steamcommunity.com"], "discord": ["discord.com", "discord.gg", "discordapp.com", "discord.gift", "discordapp.net", "discord.media", "discord.new"],
    "epicgames": ["epicgames.com"], "instagram": ["instagram.com"], "facebook": ["facebook.com", "fb.com", "fb.me"],
    "whatsapp": ["whatsapp.com", "whatsapp.net"], "ebay": ["ebay.de", "ebay.com"], "dhl": ["dhl.de", "dhl.com"],
    "sparkasse": ["sparkasse.de"], "volksbank": ["volksbank.de", "vr.de"], "commerzbank": ["commerzbank.de"],
    "deutsche-bank": ["deutsche-bank.de", "db.com"], "postbank": ["postbank.de"], "ing": ["ing.de", "ing.com"],
    "n26": ["n26.com"], "telekom": ["telekom.de", "t-online.de"], "vodafone": ["vodafone.de", "vodafone.com"],
    "gmx": ["gmx.de", "gmx.net"], "webde": ["web.de"], "dropbox": ["dropbox.com"], "binance": ["binance.com"],
    "coinbase": ["coinbase.com"], "roblox": ["roblox.com"], "tiktok": ["tiktok.com"], "twitch": ["twitch.tv"],
    "spotify": ["spotify.com"], "klarna": ["klarna.com", "klarna.de"], "zalando": ["zalando.de"], "otto": ["otto.de"],
    "elster": ["elster.de"], "hermes": ["myhermes.de", "hermesworld.com"], "dpd": ["dpd.de", "dpd.com"],
}
SUS_TLDS = {"zip", "mov", "top", "xyz", "tk", "ml", "ga", "cf", "gq", "click", "country", "work", "support", "rest",
            "fit", "cam", "icu", "buzz", "monster", "cyou", "sbs", "lol", "quest", "live", "shop", "online", "site", "info"}
LURE = re.compile(r"login|log-in|signin|sign-in|verify|verif|secure|account|konto|update|bestaetig|bestätig|sicherheit|"
                  r"unlock|wallet|support|billing|rechnung|paket|delivery|gift|nitro|free|bonus|claim", re.I)
HOMO = str.maketrans({"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j",
                      "ԁ": "d", "ɡ": "g", "ӏ": "l", "ѕ": "s", "ԛ": "q", "ԝ": "w", "ο": "o", "α": "a", "ν": "v", "ρ": "p",
                      "τ": "t", "κ": "k", "ı": "i", "ɩ": "l", "ꞵ": "b"})
CONFUSE = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "@": "a", "$": "s", "|": "l"})


def _lev(a, b):
    if abs(len(a) - len(b)) > 3:
        return 9
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def phishing_check(target, vt_key="", deep=True):
    raw = str(target).strip()
    host = _host_of(raw)
    reasons, score = [], 0
    reg = registrable(host) if not _is_ip(host) else host
    label = reg.split(".")[0]
    tld = host.rsplit(".", 1)[-1]
    shown = host
    if _is_ip(host):
        score += 3
        reasons.append("Link zeigt direkt auf eine IP-Adresse statt auf eine Domain.")
    if "xn--" in host:
        try:
            shown = host.encode().decode("idna")
        except Exception:
            pass
        score += 4
        reasons.append(f"Internationalisierte Domain (Punycode): sieht aus wie '{shown}' – klassischer Trick für Doppelgänger-Domains.")
    if "@" in raw.split("//", 1)[-1].split("/", 1)[0]:
        score += 4
        reasons.append("'@' in der Adresse – alles davor ist Tarnung, das echte Ziel steht dahinter.")
    official = None
    for brand, doms in BRANDS.items():
        if reg in doms:
            official = brand
            break
    regional = re.match(r"^(sparkasse|ksk|sk|volksbank|vr|vb|raiffeisenbank|psd|sparda)-[a-z\-]+\.de$", reg)
    if official:
        reasons.append(f"Offizielle Domain von {official}.")
    elif regional and not LURE.search(host):
        score += 1
        reasons.append("Sieht aus wie die Domain einer regionalen Bank (z. B. Sparkasse/Volksbank vor Ort). "
                       "Vergleiche sie mit der Adresse auf deiner Bankkarte oder in deinen Unterlagen.")
    else:
        skel_host = shown.translate(HOMO)  # kyrillische/griechische Doppelgänger → lateinisch
        skel_label = registrable(skel_host).split(".")[0] if not _is_ip(host) else label

        def norm(x):
            return x.translate(CONFUSE).replace("rn", "m").replace("vv", "w").replace("-", "")
        parts = [x for x in re.split(r"[-.]", skel_host) if x]
        hit = None
        # 1. Durchgang: Fälschungen/Tippfehler (spezifischste Marke zuerst)
        for brand in sorted(BRANDS, key=len, reverse=True):
            b = brand.replace("-", "")
            if len(b) < 4:
                continue
            cands = [skel_label] + parts
            if any(norm(c) == b and c.replace("-", "") != b for c in cands) or (skel_label != label and norm(skel_label) == b):
                hit = (7, f"Fälschung von '{brand}': ähnlich aussehende Zeichen ({shown}). Echt wäre {BRANDS[brand][0]}.")
                break
            if any(0 < _lev(norm(c), b) <= (2 if len(b) >= 7 else 1) for c in cands if len(c) >= 4):
                hit = (5, f"Tippfehler-Domain: ähnelt '{brand}' (echt wäre {BRANDS[brand][0]}).")
                break
        # 2. Durchgang: Markenname eingebaut
        if not hit:
            for brand in sorted(BRANDS, key=len, reverse=True):
                b = brand.replace("-", "")
                if len(b) >= 4 and (b in [norm(x) for x in parts] or b in norm(skel_label)):
                    hit = (5, f"Enthält den Markennamen '{brand}', gehört aber nicht {brand} (echt wäre {BRANDS[brand][0]}).")
                    break
        if hit:
            score += hit[0]
            reasons.append(hit[1])
    if tld in SUS_TLDS and not official:
        score += 2
        reasons.append(f"Endung .{tld} wird oft für Betrugsseiten genutzt.")
    if LURE.search(host) and not official:
        score += 2
        reasons.append("Lockwörter in der Adresse (login, verify, konto, …).")
    if host.count(".") >= 4:
        score += 1
        reasons.append("Ungewöhnlich viele Subdomains.")
    if len(host) > 45:
        score += 1
        reasons.append("Sehr lange Adresse.")
    if raw.lower().startswith("http://"):
        score += 1
        reasons.append("Unverschlüsselt (http).")
    res = {"geprüft": raw, "domain": shown, "registrierbare_domain": reg}
    if deep and not _is_ip(host) and not official:
        age = domain_age_days(host)
        if age is not None:
            res["domain_alter_tage"] = age
            if age < 30:
                score += 4
                reasons.append(f"Domain ist erst {age} Tage alt – sehr typisch für Phishing.")
            elif age < 180:
                score += 2
                reasons.append(f"Domain ist recht neu ({age} Tage).")
        try:
            ssl_check(host)
        except Exception:
            if not raw.lower().startswith("http://"):
                score += 1
                reasons.append("Kein gültiges HTTPS.")
    if vt_key and deep:
        try:
            vt = virustotal_url(raw if "://" in raw else "http://" + raw, vt_key)
            res["virustotal"] = vt
            mal = (vt.get("ergebnis") or {}).get("malicious", 0)
            if mal >= 2:
                score += 6
                reasons.append(f"VirusTotal: {mal} Scanner melden diese Adresse als gefährlich.")
            elif mal == 1:
                score += 2
                reasons.append("VirusTotal: 1 Scanner meldet die Adresse.")
        except Exception as e:
            res["virustotal_fehler"] = str(e)
    res["punkte"] = score
    res["urteil"] = ("sehr wahrscheinlich Phishing / Betrug" if score >= 7 else "verdächtig – Vorsicht" if score >= 3
                     else "keine typischen Warnzeichen")
    res["gründe"] = reasons
    return res


def _vt(path, key, method="GET", data=None, headers=None):
    h = {"x-apikey": key, "Accept": "application/json"}
    h.update(headers or {})
    status, d = _json("https://www.virustotal.com/api/v3" + path, method=method, headers=h, data=data, timeout=60)
    if status == 401:
        raise RuntimeError("VirusTotal-Key ungültig.")
    if status == 429:
        raise RuntimeError("VirusTotal-Limit erreicht (kostenlos: 4 Anfragen/Minute). Kurz warten.")
    return status, d


def _vt_summary(attr):
    stats = attr.get("last_analysis_stats") or attr.get("stats") or {}
    results = attr.get("last_analysis_results") or attr.get("results") or {}
    flagged = [f"{k}: {v.get('result')}" for k, v in results.items() if v.get("category") in ("malicious", "suspicious")][:12]
    out = {"ergebnis": {k: stats.get(k, 0) for k in ("malicious", "suspicious", "harmless", "undetected")},
           "meldungen": flagged}
    if attr.get("reputation") is not None:
        out["reputation"] = attr.get("reputation")
    if attr.get("categories"):
        out["kategorien"] = list(set(attr["categories"].values()))[:6]
    if attr.get("meaningful_name") or attr.get("type_description"):
        out["datei"] = {"name": attr.get("meaningful_name"), "typ": attr.get("type_description"),
                        "erstmals_gesehen": datetime.fromtimestamp(attr["first_submission_date"]).strftime("%d.%m.%Y")
                        if attr.get("first_submission_date") else None}
    return out


def virustotal_url(url, key):
    if not key:
        raise RuntimeError("Kein VirusTotal-Key. Kostenlos unter virustotal.com → Profil → API Key, dann in den Einstellungen eintragen.")
    uid = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    status, d = _vt(f"/urls/{uid}", key)
    if status == 200 and d:
        return {"url": url, **_vt_summary(d["data"]["attributes"]), "link": f"https://www.virustotal.com/gui/url/{uid}"}
    status, d = _vt("/urls", key, method="POST", data={"url": url})
    if status not in (200, 202) or not d:
        raise RuntimeError(f"VirusTotal-Fehler {status}.")
    aid = d["data"]["id"]
    for _ in range(10):
        time.sleep(3)
        status, a = _vt(f"/analyses/{aid}", key)
        if a and a["data"]["attributes"].get("status") == "completed":
            return {"url": url, **_vt_summary(a["data"]["attributes"]), "link": f"https://www.virustotal.com/gui/url/{uid}"}
    return {"url": url, "hinweis": "Analyse läuft noch – in einer Minute erneut prüfen.", "link": f"https://www.virustotal.com/gui/url/{uid}"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def virustotal_file(path=None, file_hash=None, key="", upload=False):
    if not key:
        raise RuntimeError("Kein VirusTotal-Key. Kostenlos unter virustotal.com → Profil → API Key, dann in den Einstellungen eintragen.")
    p = Path(path) if path else None
    h = (file_hash or "").strip().lower() or (sha256_file(p) if p else "")
    if not re.fullmatch(r"[0-9a-f]{32}|[0-9a-f]{40}|[0-9a-f]{64}", h):
        raise RuntimeError("Ungültiger Hash (MD5, SHA1 oder SHA256).")
    status, d = _vt(f"/files/{h}", key)
    if status == 200 and d:
        return {"hash": h, **_vt_summary(d["data"]["attributes"]), "link": f"https://www.virustotal.com/gui/file/{h}"}
    if status != 404:
        raise RuntimeError(f"VirusTotal-Fehler {status}.")
    if not upload or not p:
        return {"hash": h, "bekannt": False,
                "hinweis": "VirusTotal kennt diese Datei nicht. Mit upload=true kann sie hochgeladen werden "
                           "(Achtung: hochgeladene Dateien sehen Sicherheitsforscher – keine privaten Dokumente!)."}
    if p.stat().st_size > 32 * 1024 * 1024:
        raise RuntimeError("Datei größer als 32 MB – Upload über die Webseite nötig.")
    boundary = "lumen" + str(int(time.time() * 1000))
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{p.name}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + p.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    status, d = _vt("/files", key, method="POST", data=body,
                    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    if status not in (200, 202) or not d:
        raise RuntimeError(f"Upload fehlgeschlagen ({status}).")
    aid = d["data"]["id"]
    for _ in range(20):
        time.sleep(4)
        status, a = _vt(f"/analyses/{aid}", key)
        if a and a["data"]["attributes"].get("status") == "completed":
            return {"hash": h, **_vt_summary(a["data"]["attributes"]), "link": f"https://www.virustotal.com/gui/file/{h}"}
    return {"hash": h, "hinweis": "Hochgeladen, Analyse läuft noch.", "link": f"https://www.virustotal.com/gui/file/{h}"}


# ---------------------------------------------------------------- mail
RISKY_ATT = re.compile(r"\.(exe|scr|com|bat|cmd|js|jse|vbs|vbe|wsf|hta|ps1|msi|jar|lnk|iso|img|vhd|html?|svg|"
                       r"docm|xlsm|pptm|one|reg|cab)$", re.I)


def _addr(v):
    name, addr = email.utils.parseaddr(str(v or ""))
    return name, addr.lower(), (addr.split("@")[-1].lower() if "@" in addr else "")


def mail_analyze(raw=None, path=None, vt_key=""):
    if path:
        data = Path(path).read_bytes()
        msg = email.message_from_bytes(data, policy=email.policy.default)
    elif raw:
        msg = email.message_from_string(str(raw).replace("\r\n", "\n"), policy=email.policy.default)
    else:
        raise RuntimeError("Bitte Mail-Header/Quelltext einfügen oder eine .eml-Datei anhängen.")
    warn, ok = [], []
    fname, faddr, fdom = _addr(msg.get("From"))
    _, rto, rdom = _addr(msg.get("Reply-To"))
    _, rpath, pdom = _addr(msg.get("Return-Path"))
    res = {"betreff": str(msg.get("Subject") or ""), "datum": str(msg.get("Date") or ""),
           "absender": {"name": fname, "adresse": faddr}, "antwort_an": rto or None, "return_path": rpath or None,
           "message_id": str(msg.get("Message-ID") or ""), "mailer": str(msg.get("X-Mailer") or msg.get("User-Agent") or "") or None}
    # Authentifizierung
    auth = " ".join(str(v) for v in (msg.get_all("Authentication-Results") or []) + (msg.get_all("ARC-Authentication-Results") or []))
    spf_hdr = " ".join(str(v) for v in msg.get_all("Received-SPF") or [])
    checks = {}
    for k in ("spf", "dkim", "dmarc"):
        m = re.search(rf"\b{k}=(\w+)", auth, re.I)
        checks[k] = m.group(1).lower() if m else None
    if not checks["spf"] and spf_hdr:
        checks["spf"] = spf_hdr.split()[0].lower()
    res["prüfungen"] = checks
    for k, v in checks.items():
        if v in ("fail", "softfail", "permerror", "temperror"):
            warn.append(f"{k.upper()} = {v}: Absender ist nicht berechtigt / Mail evtl. gefälscht.")
        elif v == "pass":
            ok.append(f"{k.upper()} bestanden.")
    if not any(checks.values()):
        warn.append("Keine SPF/DKIM/DMARC-Ergebnisse im Header – Echtheit nicht prüfbar (vollständigen Header einfügen).")
    # Absender-Tricks
    if rdom and fdom and registrable(rdom) != registrable(fdom):
        warn.append(f"Antworten gehen an eine andere Domain ({rdom}) als der Absender ({fdom}).")
    if pdom and fdom and registrable(pdom) != registrable(fdom):
        res["hinweis_return_path"] = f"Return-Path-Domain ({pdom}) ≠ Absender ({fdom}) – bei Newslettern normal, sonst verdächtig."
    for brand, doms in BRANDS.items():
        if len(brand) >= 4 and brand.replace("-", "") in re.sub(r"[^a-z]", "", fname.lower()) and fdom and registrable(fdom) not in doms:
            warn.append(f"Anzeigename nennt '{brand}', die Adresse ist aber {faddr}.")
            break
    if fdom:
        pc = phishing_check(fdom, deep=False)
        if pc["punkte"] >= 3:
            warn.append(f"Absender-Domain verdächtig: {'; '.join(pc['gründe'][:2])}")
    # Weg der Mail
    hops = []
    for rcv in reversed(msg.get_all("Received") or []):
        r = " ".join(str(rcv).split())
        frm = re.search(r"from\s+(\S+)", r)
        by = re.search(r"by\s+(\S+)", r)
        ip = re.search(r"\[((?:\d{1,3}\.){3}\d{1,3}|[0-9a-f:]{6,})\]", r, re.I)
        when = r.rsplit(";", 1)[-1].strip() if ";" in r else ""
        hops.append({"von": frm.group(1) if frm else None, "an": by.group(1) if by else None,
                     "ip": ip.group(1) if ip else None, "zeit": when[:40]})
    res["weg"] = hops[:15]
    origin = next((h["ip"] for h in hops if h["ip"] and _is_ip(h["ip"]) and not ipaddress.ip_address(h["ip"]).is_private), None)
    if origin:
        res["ursprungs_ip"] = origin
    # Inhalt: Links & Anhänge
    links, mism, atts = [], [], []
    try:
        for part in msg.walk():
            ctype = part.get_content_type()
            fn = part.get_filename()
            if fn:
                size = len(part.get_payload(decode=True) or b"")
                a = {"name": fn, "typ": ctype, "größe": size}
                if RISKY_ATT.search(fn) or re.search(r"\.(pdf|docx?|xlsx?|jpg|png|txt)\.\w{2,4}$", fn, re.I):
                    a["warnung"] = "Gefährlicher Dateityp oder doppelte Endung – nicht öffnen!"
                    warn.append(f"Riskanter Anhang: {fn}")
                atts.append(a)
            elif ctype in ("text/html", "text/plain"):
                body = part.get_content() if hasattr(part, "get_content") else ""
                if ctype == "text/html":
                    for href, text in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, re.I | re.S):
                        if href.startswith("http"):
                            links.append(href)
                            shown = re.sub(r"<[^>]+>", "", text).strip()
                            m = re.search(r"([a-z0-9-]+\.)+[a-z]{2,}", shown.lower())
                            if m and registrable(m.group(0)) != registrable(_host_of(href)):
                                mism.append(f"Text zeigt '{m.group(0)}', Link führt aber zu {_host_of(href)}")
                else:
                    links += re.findall(r"https?://[^\s<>\"')]+", body)
    except Exception:
        pass
    if mism:
        warn += [f"Täuschender Link: {x}" for x in mism[:5]]
    doms = []
    for l in links:
        try:
            d = _host_of(l)
            if d not in doms:
                doms.append(d)
        except Exception:
            pass
    link_checks = []
    for d in doms[:8]:
        try:
            pc = phishing_check(d, vt_key=vt_key, deep=True)
            link_checks.append({"domain": d, "urteil": pc["urteil"], "gründe": pc["gründe"][:3]})
            if pc["punkte"] >= 3:
                warn.append(f"Verdächtiger Link: {d} ({pc['urteil']})")
        except Exception as e:
            link_checks.append({"domain": d, "fehler": str(e)})
    res.update(links=link_checks, anhänge=atts)
    subj = res["betreff"].lower()
    if re.search(r"dringend|sofort|gesperrt|eingeschränkt|letzte mahnung|verify|suspend|ungewöhnliche aktivität|"
                 r"bestätigen sie|innerhalb von 24|paket.*zustell|gewonnen|erbschaft", subj):
        warn.append("Typische Druck-/Lockformulierung im Betreff.")
    score = len(warn)
    res["warnungen"], res["positiv"] = warn, ok
    res["urteil"] = ("sehr wahrscheinlich Phishing/Betrug – nichts anklicken, nicht antworten" if score >= 3 else
                     "verdächtig – genau prüfen" if score >= 1 else "keine typischen Warnzeichen gefunden")
    return res


# ================================================================ metadata & images
def _gps_to_deg(v, ref):
    try:
        d, m, s = [float(x) for x in v]
        deg = d + m / 60 + s / 3600
        return round(-deg if ref in ("S", "W") else deg, 6)
    except Exception:
        return None


def _office_meta(z):
    out = {}
    for name in ("docProps/core.xml", "docProps/app.xml", "meta.xml"):
        if name in z.namelist():
            xml = z.read(name).decode("utf-8", errors="replace")
            for tag, label in (("dc:creator", "autor"), ("cp:lastModifiedBy", "zuletzt_bearbeitet_von"),
                               ("dcterms:created", "erstellt"), ("dcterms:modified", "geändert"), ("dc:title", "titel"),
                               ("Company", "firma"), ("Application", "programm"), ("TotalTime", "bearbeitungszeit_min"),
                               ("meta:initial-creator", "autor"), ("meta:generator", "programm"), ("meta:creation-date", "erstellt"),
                               ("dc:date", "geändert"), ("Manager", "manager"), ("cp:revision", "version")):
                m = re.search(rf"<{tag}[^>]*>([^<]+)</{tag}>", xml)
                if m and m.group(1).strip():
                    out.setdefault(label, m.group(1).strip())
    return out


def metadata_read(path):
    p = Path(path)
    if not p.is_file():
        raise RuntimeError(f"{p} ist keine Datei.")
    ext = p.suffix.lower()
    res = {"datei": str(p), "größe": p.stat().st_size, "sha256": sha256_file(p),
           "geändert_dateisystem": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d.%m.%Y %H:%M")}
    if ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".gif"):
        try:
            from PIL import Image, ExifTags
        except ImportError:
            raise RuntimeError("Pillow fehlt (pip install pillow).")
        img = Image.open(p)
        res.update(format=img.format, auflösung=f"{img.width}x{img.height}")
        exif = img.getexif()
        tags = {}
        for k, v in exif.items():
            name = ExifTags.TAGS.get(k, str(k))
            if isinstance(v, bytes) or name in ("MakerNote", "PrintImageMatching", "ExifOffset", "GPSInfo"):
                continue
            tags[name] = str(v)[:120]
        try:
            for k, v in exif.get_ifd(0x8769).items():
                name = ExifTags.TAGS.get(k, str(k))
                if not isinstance(v, bytes) and name not in ("MakerNote",):
                    tags[name] = str(v)[:120]
        except Exception:
            pass
        wanted = ["Make", "Model", "LensModel", "Software", "DateTimeOriginal", "DateTime", "Artist", "Copyright",
                  "ImageDescription", "ExposureTime", "FNumber", "ISOSpeedRatings", "FocalLength", "BodySerialNumber",
                  "CameraOwnerName", "HostComputer"]
        res["exif"] = {k: tags[k] for k in wanted if k in tags}
        try:
            gps = exif.get_ifd(0x8825)
            if gps:
                lat = _gps_to_deg(gps.get(2), gps.get(1))
                lon = _gps_to_deg(gps.get(4), gps.get(3))
                if lat is not None and lon is not None:
                    res["gps"] = {"breite": lat, "länge": lon,
                                  "karte": f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}"}
                    res["warnung"] = "Dieses Bild verrät den Aufnahmeort! Vor dem Teilen Metadaten entfernen."
        except Exception:
            pass
        if not res["exif"] and "gps" not in res:
            res["hinweis"] = "Keine EXIF-Daten (schon entfernt – z. B. von WhatsApp/Discord/Instagram – oder Screenshot)."
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
            r = PdfReader(str(p))
            meta = {k.lstrip("/"): str(v)[:200] for k, v in (r.metadata or {}).items()}
            res.update(seiten=len(r.pages), pdf_metadaten=meta, verschlüsselt=r.is_encrypted)
        except ImportError:
            raise RuntimeError("pypdf fehlt (pip install pypdf).")
    elif ext in (".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp", ".docm", ".xlsm"):
        with zipfile.ZipFile(p) as z:
            res["dokument_metadaten"] = _office_meta(z)
            if any(n.startswith(("word/vbaProject", "xl/vbaProject", "ppt/vbaProject")) for n in z.namelist()):
                res["warnung"] = "Enthält Makros (VBA) – nur öffnen, wenn du der Quelle vertraust."
    return res


def metadata_strip(path):
    p = Path(path)
    if not p.is_file():
        raise RuntimeError(f"{p} ist keine Datei.")
    ext = p.suffix.lower()
    out = p.with_name(p.stem + "_ohne_metadaten" + p.suffix)
    if ext in (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"):
        from PIL import Image, ImageOps
        img = ImageOps.exif_transpose(Image.open(p))  # Drehung übernehmen, dann alle Zusatzdaten verwerfen
        img.info = {}
        kw = {"quality": 95} if ext in (".jpg", ".jpeg", ".webp") else {}
        img.save(out, **kw)
    elif ext == ".pdf":
        from pypdf import PdfReader, PdfWriter
        r = PdfReader(str(p))
        w = PdfWriter()
        for page in r.pages:
            w.add_page(page)
        w.add_metadata({"/Producer": "", "/Creator": "", "/Author": "", "/Title": ""})
        with open(out, "wb") as f:
            w.write(f)
    elif ext in (".docx", ".xlsx", ".pptx", ".docm", ".xlsm"):
        with zipfile.ZipFile(p) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "docProps/core.xml":
                    xml = data.decode("utf-8")
                    for tag in ("dc:creator", "cp:lastModifiedBy", "dc:title", "dc:subject", "cp:keywords", "dc:description", "cp:lastPrinted"):
                        xml = re.sub(rf"<{tag}([^>]*)>[^<]*</{tag}>", rf"<{tag}\1></{tag}>", xml)
                    data = xml.encode("utf-8")
                elif item.filename == "docProps/app.xml":
                    xml = data.decode("utf-8")
                    for tag in ("Company", "Manager", "TotalTime"):
                        xml = re.sub(rf"<{tag}>[^<]*</{tag}>", f"<{tag}></{tag}>", xml)
                    data = xml.encode("utf-8")
                zout.writestr(item, data)
    else:
        raise RuntimeError("Für diesen Dateityp kann ich Metadaten nicht entfernen (Bilder, PDF, Word/Excel/PowerPoint gehen).")
    after = metadata_read(out)
    return {"neue_datei": str(out), "original_unverändert": str(p),
            "rest": {k: after.get(k) for k in ("exif", "gps", "pdf_metadaten", "dokument_metadaten") if after.get(k)}}


def _dhash(img):
    g = img.convert("L").resize((9, 8))
    px = list(g.getdata())
    bits = "".join("1" if px[r * 9 + c] > px[r * 9 + c + 1] else "0" for r in range(8) for c in range(8))
    return f"{int(bits, 2):016x}"


def image_check(path):
    from PIL import Image, ImageChops, ImageEnhance
    p = Path(path)
    img = Image.open(p)
    data = p.read_bytes()
    res = {"datei": str(p), "format": img.format, "auflösung": f"{img.width}x{img.height}", "modus": img.mode,
           "md5": hashlib.md5(data).hexdigest(), "sha256": hashlib.sha256(data).hexdigest(),
           "dhash": _dhash(img), "hinweise": []}
    meta = metadata_read(p)
    exif = meta.get("exif", {})
    sw = exif.get("Software", "")
    if re.search(r"photoshop|gimp|lightroom|affinity|pixelmator|snapseed|picsart|facetune|canva", sw, re.I):
        res["hinweise"].append(f"Mit Bildbearbeitung gespeichert: {sw}")
    if exif.get("DateTimeOriginal") and exif.get("DateTime") and exif["DateTimeOriginal"] != exif["DateTime"]:
        res["hinweise"].append(f"Aufnahme {exif['DateTimeOriginal']}, später geändert {exif['DateTime']}.")
    if not exif:
        res["hinweise"].append("Keine EXIF-Daten – typisch für Screenshots oder Bilder aus sozialen Netzwerken.")
    if "gps" in meta:
        res["hinweise"].append("Enthält GPS-Standort.")
    # Error Level Analysis
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rgb = img.convert("RGB")
    buf = io.BytesIO()
    rgb.save(buf, "JPEG", quality=90)
    re_img = Image.open(io.BytesIO(buf.getvalue()))
    diff = ImageChops.difference(rgb, re_img)
    extrema = diff.getextrema()
    maxd = max(e[1] for e in extrema) or 1
    ela = ImageEnhance.Brightness(diff).enhance(255.0 / maxd)
    ela_path = OUT_DIR / f"ela_{p.stem}.png"
    ela.save(ela_path)
    res["ela_bild"] = str(ela_path)
    if img.format not in ("JPEG", "WEBP"):
        res["hinweise"].append("ELA ist bei PNG/Screenshots wenig aussagekräftig (nur bei JPEG sinnvoll).")
    res["ela_erklärung"] = ("Error Level Analysis: Bereiche, die deutlich heller leuchten als ähnliche Flächen, wurden "
                            "eventuell nachträglich eingefügt/bearbeitet. Kanten und Text leuchten immer – nur ein Hinweis, kein Beweis.")
    small = ela.copy()
    small.thumbnail((900, 900))
    b = io.BytesIO()
    small.convert("RGB").save(b, "JPEG", quality=80)
    th = small.copy()
    th.thumbnail((420, 420))
    tb = io.BytesIO()
    th.convert("RGB").save(tb, "JPEG", quality=65)
    return {"__image__": base64.b64encode(b.getvalue()).decode(), "__thumb__": base64.b64encode(tb.getvalue()).decode(),
            "text": json.dumps(res, ensure_ascii=False)}


def reverse_image_search(url=None, path=None):
    opened = []
    if url and re.match(r"^https?://", url):
        q = urllib.parse.quote(url, safe="")
        for name, u in (("Google Lens", f"https://lens.google.com/uploadbyurl?url={q}"),
                        ("TinEye", f"https://tineye.com/search?url={q}"),
                        ("Bing", f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{q}")):
            webbrowser.open(u)
            opened.append(name)
        return {"geöffnet": opened, "hinweis": "Ergebnisse siehst du im Browser."}
    if path:
        p = Path(path)
        if not p.is_file():
            raise RuntimeError(f"{p} existiert nicht.")
        webbrowser.open("https://lens.google.com/")
        webbrowser.open("https://tineye.com/")
        try:
            if OS == "Windows":
                subprocess.Popen(["explorer", "/select,", str(p)])
            elif OS == "Darwin":
                subprocess.Popen(["open", "-R", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p.parent)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        return {"geöffnet": ["Google Lens", "TinEye", "Ordner mit dem Bild"],
                "hinweis": f"Zieh {p.name} aus dem geöffneten Ordner in Google Lens oder TinEye."}
    raise RuntimeError("Bild-URL oder Datei angeben.")


# ================================================================ own security
def breach_check(emails, hibp_key=""):
    if not emails:
        raise RuntimeError("Keine eigenen E-Mail-Adressen hinterlegt. Trag sie in den Einstellungen unter 'Eigene Konten' ein.")
    out = []
    for e in emails:
        e = e.strip().lower()
        item = {"email": e}
        try:
            if hibp_key:
                status, d = _json(f"https://haveibeenpwned.com/api/v3/breachedaccount/{urllib.parse.quote(e)}?truncateResponse=false",
                                  headers={"hibp-api-key": hibp_key}, timeout=20)
                if status == 404:
                    item["lecks"] = []
                elif status == 200 and isinstance(d, list):
                    item["lecks"] = [{"name": b.get("Title"), "datum": b.get("BreachDate"),
                                      "daten": b.get("DataClasses", [])[:8]} for b in d]
                else:
                    raise RuntimeError(f"HIBP-Fehler {status}")
                item["quelle"] = "Have I Been Pwned"
            else:
                status, d = _json("https://api.xposedornot.com/v1/breach-analytics?" + urllib.parse.urlencode({"email": e}), timeout=25)
                if status == 404 or (isinstance(d, dict) and not d.get("ExposedBreaches")):
                    item["lecks"] = []
                elif status == 200 and isinstance(d, dict):
                    det = (d.get("ExposedBreaches") or {}).get("breaches_details") or []
                    item["lecks"] = [{"name": b.get("breach"), "datum": b.get("xposed_date"),
                                      "daten": (b.get("xposed_data") or "").split(";")[:8],
                                      "passwort_risiko": b.get("password_risk")} for b in det]
                else:
                    raise RuntimeError(f"XposedOrNot-Fehler {status}")
                item["quelle"] = "XposedOrNot"
            item["anzahl"] = len(item["lecks"])
        except Exception as ex:
            item["fehler"] = str(ex)
        out.append(item)
        time.sleep(1.6 if hibp_key else 0.5)  # Rate-Limits
    return {"ergebnisse": out,
            "tipps": "Bei Treffern: Passwort dort und überall, wo du es wiederverwendet hast, ändern; 2-Faktor-Anmeldung "
                     "aktivieren; einen Passwort-Manager nutzen."}


def password_pwned(password):
    sha = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha[:5], sha[5:]
    status, headers, body = _req(f"https://api.pwnedpasswords.com/range/{prefix}", headers={"Add-Padding": "true"}, timeout=15)
    if status != 200:
        raise RuntimeError(f"Dienst nicht erreichbar ({status}).")
    count = 0
    for line in body.decode().splitlines():
        h, _, c = line.partition(":")
        if h.strip() == suffix:
            count = int(c.strip() or 0)
            break
    return count


USER_SITES = [
    ("GitHub", "https://api.github.com/users/{u}", "status", "https://github.com/{u}"),
    ("GitLab", "https://gitlab.com/api/v4/users?username={u}", "json_list", "https://gitlab.com/{u}"),
    ("Codeberg", "https://codeberg.org/api/v1/users/{u}", "status", "https://codeberg.org/{u}"),
    ("Reddit", "https://www.reddit.com/user/{u}/about.json", "status", "https://www.reddit.com/user/{u}"),
    ("Steam", "https://steamcommunity.com/id/{u}", "!The specified profile could not be found", "https://steamcommunity.com/id/{u}"),
    ("Chess.com", "https://api.chess.com/pub/player/{u}", "status", "https://www.chess.com/member/{u}"),
    ("Lichess", "https://lichess.org/api/user/{u}", "status", "https://lichess.org/@/{u}"),
    ("Minecraft", "https://api.mojang.com/users/profiles/minecraft/{u}", "status200", "https://namemc.com/profile/{u}"),
    ("Docker Hub", "https://hub.docker.com/v2/users/{u}/", "status", "https://hub.docker.com/u/{u}"),
    ("PyPI", "https://pypi.org/user/{u}/", "status", "https://pypi.org/user/{u}/"),
    ("npm", "https://registry.npmjs.org/-/user/org.couchdb.user:{u}", "status", "https://www.npmjs.com/~{u}"),
    ("Keybase", "https://keybase.io/_/api/1.0/user/lookup.json?usernames={u}", "keybase", "https://keybase.io/{u}"),
    ("dev.to", "https://dev.to/api/users/by_username?url={u}", "status", "https://dev.to/{u}"),
    ("Mastodon.social", "https://mastodon.social/api/v1/accounts/lookup?acct={u}", "status", "https://mastodon.social/@{u}"),
    ("Bluesky", "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor={u}.bsky.social", "status", "https://bsky.app/profile/{u}.bsky.social"),
    ("Itch.io", "https://{u}.itch.io", "status", "https://{u}.itch.io"),
    ("YouTube", "https://www.youtube.com/@{u}", "status", "https://www.youtube.com/@{u}"),
    ("SoundCloud", "https://soundcloud.com/{u}", "status", "https://soundcloud.com/{u}"),
    ("Linktree", "https://linktr.ee/{u}", "status", "https://linktr.ee/{u}"),
    ("Telegram", "https://t.me/{u}", "+tgme_page_title", "https://t.me/{u}"),
    ("Roblox", "https://users.roblox.com/v1/usernames/users", "roblox", "https://www.roblox.com/search/users?keyword={u}"),
]


def username_check(usernames):
    if not usernames:
        raise RuntimeError("Keine eigenen Benutzernamen hinterlegt. Trag sie in den Einstellungen unter 'Eigene Konten' ein.")
    results = {}

    def check(site, u):
        name, api, how, link = site
        try:
            if how == "roblox":
                status, d = _json(api, method="POST", data=json.dumps({"usernames": [u], "excludeBannedUsers": False}).encode(),
                                  headers={"Content-Type": "application/json"}, timeout=12)
                found = bool((d or {}).get("data"))
            else:
                status, headers, body = _req(api.format(u=urllib.parse.quote(u)), timeout=12, max_bytes=400_000,
                                             headers={"User-Agent": web.UA})
                if how == "status":
                    found = status == 200 if status in (200, 404, 410) else None
                elif how == "status200":
                    found = status == 200 if status in (200, 204, 404) else None
                elif how == "json_list":
                    found = bool(json.loads(body or b"[]")) if status == 200 else None
                elif how == "keybase":
                    found = bool((json.loads(body or b"{}").get("them") or [None])[0]) if status == 200 else None
                elif how.startswith("!"):
                    found = (how[1:].encode() not in body) if status == 200 else (False if status == 404 else None)
                elif how.startswith("+"):
                    found = how[1:].encode() in body if status == 200 else None
                else:
                    found = None
            return name, found, link.format(u=u)
        except Exception:
            return name, None, link.format(u=u)
    for u in usernames:
        u = u.strip()
        if not re.fullmatch(r"[\w.\-]{2,40}", u):
            results[u] = {"fehler": "Ungültiger Benutzername"}
            continue
        with ThreadPoolExecutor(12) as ex:
            rows = list(ex.map(lambda s: check(s, u), USER_SITES))
        results[u] = {"gefunden": [{"seite": n, "link": l} for n, f, l in rows if f],
                      "nicht_vergeben": [n for n, f, l in rows if f is False],
                      "unklar": [n for n, f, l in rows if f is None]}
    return {"ergebnisse": results,
            "hinweis": "Ein Treffer heißt nur, dass der Name dort vergeben ist – nicht unbedingt von dir. "
                       "Alte, ungenutzte Konten am besten löschen."}
