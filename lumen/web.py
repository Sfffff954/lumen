"""
Lumen – Internet: suchen und Webseiten lesen.

Suche ohne Key: DuckDuckGo (HTML) → DuckDuckGo Lite → Bing.
Optional zuverlässiger: Brave Search API (kostenloser Key) oder eigene SearXNG-Instanz.
Webseiten werden zu lesbarem Text (ohne Menüs, Werbung, Skripte); PDFs mit pypdf.
"""
import gzip
import html
import io
import ipaddress
import json
import re
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
import zlib
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
MAX_BYTES = 4_000_000
PAGE_CHARS = 12000


# ================================================================ HTTP
def _private(host):
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise RuntimeError(f"Adresse '{host}' nicht gefunden.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
    return False


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = urllib.parse.urlparse(newurl).hostname or ""
        if not getattr(req, "allow_private", False) and _private(host):
            raise RuntimeError("Weiterleitung auf eine lokale Adresse blockiert.")
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            new.allow_private = getattr(req, "allow_private", False)
        return new


_OPENER = urllib.request.build_opener(_SafeRedirect)


def http_get(url, data=None, headers=None, timeout=15, allow_private=False):
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https"):
        raise RuntimeError("Nur http/https-Adressen.")
    if not allow_private and _private(u.hostname or ""):
        raise RuntimeError("Lokale/private Adressen werden aus Sicherheitsgründen nicht geladen.")
    h = {"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
         "Accept": "text/html,application/xhtml+xml,application/pdf,text/plain;q=0.9,*/*;q=0.5",
         "Accept-Encoding": "gzip, deflate"}
    h.update(headers or {})
    body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data
    req = urllib.request.Request(url, data=body, headers=h, method="POST" if body else "GET")
    req.allow_private = allow_private
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            raw = r.read(MAX_BYTES + 1)
            enc = (r.headers.get("Content-Encoding") or "").lower()
            if enc == "gzip":
                raw = gzip.decompress(raw)
            elif enc == "deflate":
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            return r.status, r.headers, raw[:MAX_BYTES], r.geturl()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Seite antwortet mit Fehler {e.code}.")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Seite nicht erreichbar: {e.reason}")
    except socket.timeout:
        raise RuntimeError("Zeitüberschreitung beim Laden.")


def _decode(raw, headers):
    m = re.search(r"charset=([\w\-]+)", headers.get("Content-Type", "") or "", re.I)
    cs = m.group(1) if m else None
    if not cs:
        m = re.search(rb'<meta[^>]+charset=["\']?([\w\-]+)', raw[:4000], re.I)
        cs = m.group(1).decode() if m else "utf-8"
    try:
        return raw.decode(cs, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


# ================================================================ text extraction
SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form", "iframe",
        "button", "select", "template", "canvas", "figure"}
BLOCK = {"p", "div", "section", "article", "main", "li", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6",
         "pre", "blockquote", "table", "ul", "ol", "dd", "dt", "hr"}
JUNK_CLASS = re.compile(r"(^|[\s_-])(cookie|consent|banner|newsletter|share|social|related|advert|ads|promo|sidebar|"
                        r"comments?|breadcrumbs?|menu|popup|modal|subscribe|footer|navbar)([\s_-]|$)", re.I)
NEVER_JUNK = {"html", "body", "main", "article"}


class _Extractor(HTMLParser):
    def __init__(self, strict=True):
        super().__init__(convert_charrefs=True)
        self.strict = strict
        self.out, self.skip, self.title, self.meta = [], [], "", {}
        self._in_title = False
        self._stack = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            k = (a.get("property") or a.get("name") or "").lower()
            if k in ("description", "og:description", "article:published_time", "og:site_name", "date",
                     "article:modified_time", "author"):
                self.meta.setdefault(k, a.get("content", ""))
            return
        if tag in ("br", "hr", "img", "input", "link", "source", "wbr"):
            if tag in ("br", "hr"):
                self.out.append("\n")
            return
        junk = tag in SKIP or (self.strict and tag not in NEVER_JUNK and (
            JUNK_CLASS.search((a.get("class") or "") + " " + (a.get("id") or ""))
            or a.get("aria-hidden") == "true" or a.get("hidden") is not None
            or a.get("role") in ("navigation", "banner", "dialog")))
        self._stack.append((tag, bool(junk)))
        if junk:
            self.skip.append(tag)
        if tag == "title":
            self._in_title = True
        if not self.skip:
            if tag in ("h1", "h2", "h3"):
                self.out.append("\n\n## ")
            elif tag in ("h4", "h5", "h6"):
                self.out.append("\n\n### ")
            elif tag == "li":
                self.out.append("\n- ")
            elif tag in ("td", "th"):
                self.out.append(" | ")
            elif tag in BLOCK:
                self.out.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        # Stapel bis zum passenden Tag abbauen (kaputtes HTML tolerieren)
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                for t, junk in self._stack[i:]:
                    if junk and self.skip:
                        self.skip.pop()
                del self._stack[i:]
                break
        if not self.skip and tag in BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip:
            self.out.append(data)


def html_to_text(src, strict=True):
    p = _Extractor(strict)
    try:
        p.feed(src)
        p.close()
    except Exception:
        pass
    text = "".join(p.out)
    lines, seen = [], set()
    for line in text.splitlines():
        line = re.sub(r"[ \t ]+", " ", line).strip(" |")
        if not line or line in ("##", "###", "-"):
            continue
        key = line.lower()
        if len(line) < 40 and key in seen:
            continue
        seen.add(key)
        lines.append(line)
    # sehr kurze Fragmente am Stück (Menüreste) entfernen
    cleaned = []
    for ln in lines:
        if len(ln) < 3 and not ln.startswith("#"):
            continue
        cleaned.append(ln)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned)).strip()
    if strict and len(text) < 400:  # zu viel weggefiltert? → nur Skripte/Menüs entfernen
        loose = html_to_text(src, strict=False)
        if len(loose[0]) > len(text) * 2:
            return loose
    return text, html.unescape(p.title.strip()), p.meta


def pdf_to_text(raw):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("PDF erkannt, aber pypdf fehlt (pip install pypdf).")
    reader = PdfReader(io.BytesIO(raw))
    parts = []
    for i, page in enumerate(reader.pages[:80]):
        t = (page.extract_text() or "").strip()
        if t:
            parts.append(f"--- Seite {i + 1} ---\n{t}")
    return "\n\n".join(parts), len(reader.pages)


def read_webpage(url, start=0, max_chars=PAGE_CHARS):
    url = url.strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    status, headers, raw, final = http_get(url, timeout=20)
    ctype = (headers.get("Content-Type") or "").lower()
    meta, title = {}, ""
    if "pdf" in ctype or raw[:5] == b"%PDF-":
        text, pages = pdf_to_text(raw)
        title = f"PDF ({pages} Seiten)"
    elif "html" in ctype or b"<html" in raw[:2000].lower() or b"<!doctype" in raw[:200].lower():
        text, title, meta = html_to_text(_decode(raw, headers))
    elif ctype.startswith("text/") or "json" in ctype or "xml" in ctype:
        text = _decode(raw, headers)
    else:
        raise RuntimeError(f"Dateityp {ctype or 'unbekannt'} kann nicht gelesen werden.")
    if len(text) < 200 and "html" in ctype:
        text += "\n\n(Hinweis: Wenig Text gefunden – die Seite lädt Inhalte evtl. per JavaScript.)"
    start = max(0, int(start or 0))
    chunk = text[start:start + max_chars]
    res = {"url": final, "titel": title, "text": chunk, "länge": len(text)}
    if meta.get("article:published_time") or meta.get("date"):
        res["datum"] = meta.get("article:published_time") or meta.get("date")
    if meta.get("og:site_name"):
        res["seite"] = meta["og:site_name"]
    if start + max_chars < len(text):
        res["weiter"] = f"Gekürzt. Für mehr: read_webpage mit start={start + max_chars}"
    return res


def read_webpages(urls, max_chars=7000):
    """Mehrere Seiten parallel lesen (für Recherche)."""
    urls = [u for u in dict.fromkeys(urls or []) if isinstance(u, str) and u.strip()][:10]
    results = [None] * len(urls)

    def work(i, u):
        try:
            results[i] = read_webpage(u, 0, max_chars)
        except Exception as e:
            results[i] = {"url": u, "fehler": str(e)}
    threads = [threading.Thread(target=work, args=(i, u), daemon=True) for i, u in enumerate(urls)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    return [r or {"url": u, "fehler": "Zeitüberschreitung"} for r, u in zip(results, urls)]


# ================================================================ search
class _DDG(HTMLParser):
    """Parst html.duckduckgo.com und lite.duckduckgo.com."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results, self._cur, self._field = [], None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag == "a" and ("result__a" in cls or "result-link" in cls):
            self._cur = {"title": "", "url": a.get("href", ""), "snippet": ""}
            self.results.append(self._cur)
            self._field = "title"
        elif ("result__snippet" in cls or "result-snippet" in cls) and self._cur is not None:
            self._field = "snippet"

    def handle_endtag(self, tag):
        if tag in ("a", "td") and self._field:
            self._field = None

    def handle_data(self, data):
        if self._cur is not None and self._field:
            self._cur[self._field] += data


def _clean_ddg_url(u):
    if u.startswith("//"):
        u = "https:" + u
    q = urllib.parse.urlparse(u)
    if "duckduckgo.com" in q.netloc and q.path.startswith("/l/"):
        uddg = urllib.parse.parse_qs(q.query).get("uddg")
        if uddg:
            return uddg[0]
    return u


def _ddg(query, n):
    for url, data in (("https://html.duckduckgo.com/html/", {"q": query, "kl": "de-de"}),
                      ("https://lite.duckduckgo.com/lite/", {"q": query, "kl": "de-de"})):
        try:
            status, headers, raw, _ = http_get(url, data=data)
        except Exception:
            continue
        p = _DDG()
        p.feed(_decode(raw, headers))
        out = []
        for r in p.results:
            u = _clean_ddg_url(r["url"])
            if not u.startswith("http") or "duckduckgo.com/y.js" in u or "ad_domain" in u:
                continue
            out.append({"titel": " ".join(r["title"].split()), "url": u, "auszug": " ".join(r["snippet"].split())})
        if out:
            return out[:n]
    return []


class _Bing(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results, self._in, self._depth, self._cur, self._field = [], False, 0, None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "li" and "b_algo" in (a.get("class") or ""):
            self._cur = {"title": "", "url": "", "snippet": ""}
            self.results.append(self._cur)
            self._in = True
        elif self._in and tag == "h2":
            self._field = "h2"
        elif self._in and tag == "a" and self._field == "h2" and not self._cur["url"]:
            self._cur["url"] = a.get("href", "")
            self._field = "title"
        elif self._in and tag == "p" and not self._cur["snippet"]:
            self._field = "snippet"

    def handle_endtag(self, tag):
        if tag in ("a", "h2", "p") and self._field:
            self._field = None
        if tag == "li" and self._in:
            self._in = False

    def handle_data(self, data):
        if self._cur is not None and self._field in ("title", "snippet"):
            self._cur[self._field] += data


def _bing_url(u):
    q = urllib.parse.urlparse(u)
    if "bing.com" in q.netloc and q.path.startswith("/ck/"):
        enc = urllib.parse.parse_qs(q.query).get("u", [""])[0]
        if enc.startswith("a1"):
            import base64
            try:
                return base64.urlsafe_b64decode(enc[2:] + "==").decode()
            except Exception:
                pass
    return u


def _bing(query, n):
    status, headers, raw, _ = http_get("https://www.bing.com/search?" + urllib.parse.urlencode(
        {"q": query, "setlang": "de", "cc": "DE", "count": n}))
    p = _Bing()
    p.feed(_decode(raw, headers))
    return [{"titel": " ".join(r["title"].split()), "url": _bing_url(r["url"]), "auszug": " ".join(r["snippet"].split())}
            for r in p.results if r["url"].startswith("http")][:n]


def _brave(query, n, key):
    status, headers, raw, _ = http_get("https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
        {"q": query, "count": n, "search_lang": "de", "country": "DE"}),
        headers={"Accept": "application/json", "X-Subscription-Token": key})
    data = json.loads(raw)
    return [{"titel": r.get("title", ""), "url": r.get("url", ""),
             "auszug": re.sub(r"<[^>]+>", "", r.get("description", "")), "datum": r.get("age", "")}
            for r in data.get("web", {}).get("results", [])][:n]


def _searx(query, n, base):
    status, headers, raw, _ = http_get(base.rstrip("/") + "/search?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "language": "de"}), allow_private=True)
    data = json.loads(raw)
    return [{"titel": r.get("title", ""), "url": r.get("url", ""), "auszug": r.get("content", ""),
             "datum": r.get("publishedDate") or ""} for r in data.get("results", [])][:n]


def web_search(query, n=8, cfg=None):
    cfg = cfg or {}
    n = max(1, min(int(n or 8), 15))
    errors = []
    order = []
    if cfg.get("brave_key"):
        order.append(("Brave", lambda: _brave(query, n, cfg["brave_key"])))
    if cfg.get("searxng_url"):
        order.append(("SearXNG", lambda: _searx(query, n, cfg["searxng_url"])))
    order += [("DuckDuckGo", lambda: _ddg(query, n)), ("Bing", lambda: _bing(query, n))]
    for name, fn in order:
        try:
            res = fn()
            if res:
                return {"suche": query, "quelle": name, "ergebnisse": res}
            errors.append(f"{name}: keine Treffer")
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise RuntimeError("Websuche fehlgeschlagen (" + "; ".join(errors) + "). Tipp: In den Einstellungen einen "
                       "kostenlosen Brave-Search-Key eintragen.")
