"""
Lumen – Telegram-Bot (Long-Polling, keine offenen Ports nötig).
Nur die eingetragene Chat-ID (du) darf mit Lumen reden. Bestätigungen kommen als Knöpfe.
"""
import html
import json
import re
import threading
import time
import urllib.error
import urllib.request

API = "https://api.telegram.org"


def md_to_html(text):
    """Markdown (wie es die KI schreibt) → Telegram-HTML."""
    text = text or ""
    blocks = []

    def keep_code(m):
        blocks.append("<pre>" + html.escape(m.group(2).strip("\n")) + "</pre>")
        return f"\x00{len(blocks) - 1}\x00"

    text = re.sub(r"```(\w*)\n?(.*?)```", keep_code, text, flags=re.S)
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"^#{1,6}\s*(.+)$", r"<b>\1</b>", text, flags=re.M)
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.M)
    text = re.sub(r"^\|?[-:| ]{3,}\|?$", "", text, flags=re.M)  # Tabellen-Trennzeilen
    return re.sub(r"\x00(\d+)\x00", lambda m: blocks[int(m.group(1))], text)


def split(text, size=3900):
    parts, cur = [], ""
    for para in text.split("\n"):
        while len(para) > size:
            parts.append(para[:size])
            para = para[size:]
        if len(cur) + len(para) + 1 > size:
            parts.append(cur)
            cur = ""
        cur += ("\n" if cur else "") + para
    if cur.strip():
        parts.append(cur)
    return parts or [""]


class Bot:
    def __init__(self, get_conf, on_text, on_callback, on_file=None, on_unknown=None, on_location=None):
        self.get_conf = get_conf          # → {"bot_token":…, "chat_id":…}
        self.on_text = on_text            # (text) → None
        self.on_callback = on_callback    # (data) → Antworttext
        self.on_file = on_file            # (kind, file_id, name, caption) → None
        self.on_unknown = on_unknown
        self.on_location = on_location    # (lat, lon, genauigkeit_m, live_period_s, bearbeitet) → None
        self.offset = None
        self.status = "aus"
        self.error = None
        self.last_ok = None
        self._stop = False

    # ------------------------------------------------ API
    def call(self, method, _timeout=30, **params):
        token = self.get_conf().get("bot_token")
        if not token:
            raise RuntimeError("Kein Bot-Token.")
        req = urllib.request.Request(f"{API}/bot{token}/{method}", data=json.dumps(params).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=_timeout) as r:
                js = json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                js = json.loads(e.read())
            except Exception:
                raise RuntimeError(f"Telegram HTTP {e.code}")
        if not js.get("ok"):
            raise RuntimeError(js.get("description", "Telegram-Fehler"))
        return js.get("result")

    def chat_id(self):
        return str(self.get_conf().get("chat_id") or "").strip()

    def send(self, text, buttons=None, html_mode=True):
        cid = self.chat_id()
        if not cid:
            return None
        last = None
        parts = split(md_to_html(text) if html_mode else text)
        for i, part in enumerate(parts):
            params = {"chat_id": cid, "text": part or "…", "disable_web_page_preview": True}
            if html_mode:
                params["parse_mode"] = "HTML"
            if buttons and i == len(parts) - 1:
                params["reply_markup"] = {"inline_keyboard": buttons}
            try:
                last = self.call("sendMessage", **params)
            except RuntimeError as e:
                if html_mode and "parse" in str(e).lower():  # kaputtes HTML → als reiner Text
                    params.pop("parse_mode", None)
                    params["text"] = re.sub(r"<[^>]+>", "", html.unescape(part))
                    last = self.call("sendMessage", **params)
                else:
                    raise
        return last

    def edit(self, message_id, text):
        try:
            self.call("editMessageText", chat_id=self.chat_id(), message_id=message_id, text=text[:4000])
        except Exception:
            pass

    def edit_rich(self, message_id, text, buttons=None):
        """Nachricht ändern (mit Formatierung und Knöpfen). „Nicht verändert“ wird ignoriert."""
        params = {"chat_id": self.chat_id(), "message_id": message_id, "text": md_to_html(text)[:4000] or "…", "parse_mode": "HTML",
                  "disable_web_page_preview": True}
        if buttons:
            params["reply_markup"] = {"inline_keyboard": buttons}
        try:
            self.call("editMessageText", **params)
        except RuntimeError as e:
            if "not modified" not in str(e):
                raise

    def typing(self):
        try:
            self.call("sendChatAction", chat_id=self.chat_id(), action="typing", _timeout=10)
        except Exception:
            pass

    def send_file(self, path, caption=""):
        token, cid = self.get_conf().get("bot_token"), self.chat_id()
        import secrets
        from pathlib import Path
        p = Path(path)
        b = "----lumen" + secrets.token_hex(8)
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{cid}\r\n"
                f"--{b}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption[:1000]}\r\n"
                f"--{b}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{p.name}\"\r\n"
                "Content-Type: application/octet-stream\r\n\r\n").encode() + p.read_bytes() + f"\r\n--{b}--\r\n".encode()
        req = urllib.request.Request(f"{API}/bot{token}/sendDocument", data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())

    def send_photo(self, data, caption="", buttons=None, filename="kamera.jpg"):
        """Foto (JPEG-Bytes) mit Vorschau senden."""
        token, cid = self.get_conf().get("bot_token"), self.chat_id()
        if not cid:
            return None
        import secrets
        b = "----lumen" + secrets.token_hex(8)
        parts = [f"--{b}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{cid}\r\n",
                 f"--{b}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{md_to_html(caption)[:1000]}\r\n",
                 f"--{b}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n"]
        if buttons:
            parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"reply_markup\"\r\n\r\n{json.dumps({'inline_keyboard': buttons})}\r\n")
        body = "".join(parts).encode() + (f"--{b}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{filename}\"\r\n"
                                          "Content-Type: image/jpeg\r\n\r\n").encode() + data + f"\r\n--{b}--\r\n".encode()
        req = urllib.request.Request(f"{API}/bot{token}/sendPhoto", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())

    def ask_location(self, text):
        """Nachricht mit Knopf „📍 Standort senden“ (Antwort-Tastatur, nur am Handy)."""
        return self.call("sendMessage", chat_id=self.chat_id(), text=text, reply_markup={
            "keyboard": [[{"text": "📍 Standort senden", "request_location": True}]], "resize_keyboard": True, "one_time_keyboard": True})

    def send_voice(self, ogg_path, caption=""):
        """Sprachnachricht (OGG/Opus) senden."""
        token, cid = self.get_conf().get("bot_token"), self.chat_id()
        import secrets
        from pathlib import Path
        b = "----lumen" + secrets.token_hex(8)
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{cid}\r\n"
                f"--{b}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption[:1000]}\r\n"
                f"--{b}\r\nContent-Disposition: form-data; name=\"voice\"; filename=\"lumen.ogg\"\r\n"
                "Content-Type: audio/ogg\r\n\r\n").encode() + Path(ogg_path).read_bytes() + f"\r\n--{b}--\r\n".encode()
        req = urllib.request.Request(f"{API}/bot{token}/sendVoice", data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())

    def download(self, file_id):
        info = self.call("getFile", file_id=file_id)
        token = self.get_conf().get("bot_token")
        with urllib.request.urlopen(f"{API}/file/bot{token}/{info['file_path']}", timeout=120) as r:
            return r.read(), info["file_path"].rsplit("/", 1)[-1]

    def delete_message(self, message_id):
        try:
            self.call("deleteMessage", chat_id=self.chat_id(), message_id=message_id, _timeout=10)
        except Exception:
            pass

    # ------------------------------------------------ Schleife
    def _handle(self, u):
        if "callback_query" in u:
            q = u["callback_query"]
            if str(q.get("message", {}).get("chat", {}).get("id")) != self.chat_id():
                return
            try:
                txt = self.on_callback(q.get("data", "")) or "OK"
            except Exception as e:
                txt = f"Fehler: {e}"
            try:
                self.call("answerCallbackQuery", callback_query_id=q["id"], text=txt[:180])
                self.edit(q["message"]["message_id"], (q["message"].get("text") or "") + f"\n\n→ {txt}")
            except Exception:
                pass
            return
        if "edited_message" in u:   # Live-Standort: Telegram schickt Positions-Updates als bearbeitete Nachricht
            m = u["edited_message"]
            if str(m.get("chat", {}).get("id")) == self.chat_id() and m.get("location") and self.on_location:
                loc = m["location"]
                self.on_location(loc["latitude"], loc["longitude"], loc.get("horizontal_accuracy"), loc.get("live_period"), True)
            return
        m = u.get("message") or {}
        cid = str(m.get("chat", {}).get("id", ""))
        if not cid:
            return
        if cid != self.chat_id():
            if self.on_unknown:
                self.on_unknown(cid, m.get("from", {}).get("username"))
            try:
                token = self.get_conf().get("bot_token")
                req = urllib.request.Request(f"{API}/bot{token}/sendMessage", data=json.dumps({
                    "chat_id": cid, "text": f"🔒 Dieser Bot ist privat. (Deine Chat-ID: {cid} – nur wenn das dein Bot ist, "
                                            "trag sie in Lumen unter Apps → Telegram ein.)"}).encode(),
                    headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=15).read()
            except Exception:
                pass
            return
        if (m.get("location") or (m.get("venue") or {}).get("location")) and self.on_location:
            loc = m.get("location") or m["venue"]["location"]
            self.on_location(loc["latitude"], loc["longitude"], loc.get("horizontal_accuracy"), loc.get("live_period"), False)
        elif m.get("text"):
            self.on_text(m["text"], m.get("message_id"))
        elif self.on_file:
            for kind in ("voice", "audio", "document", "photo", "video_note"):
                if kind in m:
                    f = m[kind][-1] if kind == "photo" else m[kind]
                    self.on_file(kind, f["file_id"], f.get("file_name") or f"{kind}", m.get("caption") or "")
                    break

    def run(self):
        backoff = 2
        while not self._stop:
            c = self.get_conf()
            if not c.get("bot_token"):
                self.status, self.error = "aus", "Telegram nicht verbunden"
                time.sleep(15)
                continue
            try:
                params = {"timeout": 45, "allowed_updates": ["message", "edited_message", "callback_query"]}
                if self.offset:
                    params["offset"] = self.offset
                ups = self.call("getUpdates", _timeout=60, **params)
                self.status, self.error, self.last_ok, backoff = "läuft", None, time.time(), 2
                for u in ups or []:
                    self.offset = u["update_id"] + 1
                    threading.Thread(target=self._handle, args=(u,), daemon=True).start()
            except Exception as e:
                msg = str(e)
                if "urlopen error" in msg or "timed out" in msg:
                    msg = "Telegram nicht erreichbar (Internet/DNS auf dem Server?)"
                self.status, self.error = "fehler", msg
                if "Conflict" in msg:
                    self.error = ("Ein anderes Programm liest denselben Bot (z. B. ein zweiter Lumen-Server). "
                                  "Nur ein Lumen-Server pro Bot.")
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()
        return self
