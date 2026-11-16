"""
Lumen – Stimme: Weckwort, Push-to-Talk, Spracherkennung (lokal) und Sprachausgabe.

Spracherkennung: faster-whisper (läuft lokal, kein Key nötig).
Mikrofon:        sounddevice (braucht PortAudio: libportaudio2).
Sprachausgabe:   Piper (natürliche Stimme, lokal) → sonst espeak-ng → sonst stumm.

Alle Abhängigkeiten sind optional: fehlt etwas, meldet Lumen das in der App,
der Rest funktioniert weiter.
"""
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path

RATE = 16000
BLOCK = 480  # 30 ms
VOICES_DIR = Path.home() / ".lumen" / "voices"
PIPER_VOICE = "de_DE-thorsten-medium"
VOICES = {  # Deutsche Piper-Stimmen (rhasspy/piper-voices)
    "de_DE-thorsten-medium": "Thorsten (männlich, klar)",
    "de_DE-thorsten-high": "Thorsten HD (männlich, beste Qualität)",
    "de_DE-thorsten_emotional-medium": "Thorsten emotional (männlich)",
    "de_DE-kerstin-low": "Kerstin (weiblich)",
    "de_DE-eva_k-x_low": "Eva (weiblich, sehr schnell)",
    "de_DE-ramona-low": "Ramona (weiblich)",
    "de_DE-mls-medium": "MLS (weiblich)",
    "de_DE-karlsson-low": "Karlsson (männlich, tief)",
    "de_DE-pavoque-low": "Pavoque (männlich)",
    # English voices
    "en_US-lessac-medium": "Lessac (US, female, clear)",
    "en_US-lessac-high": "Lessac HD (US, female, best quality)",
    "en_US-ryan-high": "Ryan (US, male)",
    "en_US-amy-medium": "Amy (US, female)",
    "en_US-joe-medium": "Joe (US, male)",
    "en_GB-alan-medium": "Alan (UK, male)",
    "en_GB-jenny_dioco-medium": "Jenny (UK, female)",
}
EN_VOICE = "en_US-lessac-medium"
_DL = {}


def voice_list():
    return [{"id": v, "name": n, "installiert": (VOICES_DIR / f"{v}.onnx").exists() and (VOICES_DIR / f"{v}.onnx.json").exists(),
             "lädt": _DL.get(v) == "läuft"} for v, n in VOICES.items()]


def download_voice(vid, voice_obj=None):
    if vid not in VOICES:
        raise RuntimeError("Unbekannte Stimme.")
    if _DL.get(vid) == "läuft":
        return
    lang, rest = vid.split("-", 1)
    speaker, quality = rest.rsplit("-", 1)
    base = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang.split('_')[0]}/{lang}/{speaker}/{quality}/{vid}"

    def work():
        import urllib.request
        _DL[vid] = "läuft"
        try:
            VOICES_DIR.mkdir(parents=True, exist_ok=True)
            for ext in (".onnx.json", ".onnx"):
                tmp = VOICES_DIR / f"{vid}{ext}.part"
                urllib.request.urlretrieve(base + ext, tmp)
                tmp.replace(VOICES_DIR / f"{vid}{ext}")
            _DL[vid] = "fertig"
            if voice_obj:
                voice_obj.emit(type="info", text=f"Stimme {VOICES[vid]} ist installiert.")
        except Exception as e:
            _DL[vid] = "fehler"
            if voice_obj:
                voice_obj.emit(type="error", text=f"Stimme konnte nicht geladen werden: {e}")
    threading.Thread(target=work, daemon=True).start()

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None
try:
    import sounddevice as sd
except Exception:  # pragma: no cover  (fehlt Modul oder PortAudio)
    sd = None


def clean_for_speech(text, limit=700):
    t = re.sub(r"```.*?```", " Code siehe Bildschirm. ", text, flags=re.S)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"[*_#>]+", "", t)
    t = re.sub(r"https?://\S+", "Link", t)
    t = re.sub(r"^\s*[-•]\s*", "", t, flags=re.M)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > limit:
        cut = t[:limit]
        t = cut[: max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), 200) + 1] + " Den Rest siehst du in der App."
    return t


def _norm(s):
    s = s.lower()
    for a, b in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9 ]+", " ", s)


def wake_variants(word):
    w = _norm(word).strip() or "lumen"
    v = {w}
    if w == "lumen":  # typische Verhörer von Whisper
        v |= {"lumen", "lumin", "lumen", "luhmen", "lumens", "luman", "lummen", "loomen", "lumine", "rumen", "lumena"}
    return v


def split_wake(text, word):
    """Gibt (gefunden, befehl) zurück. 'Hey Lumen, starte Steam' -> (True, 'starte Steam')."""
    words = text.split()
    variants = wake_variants(word)
    for i, raw in enumerate(words[:6]):  # Weckwort am Satzanfang (mit 'hey', 'ok', 'hallo' davor)
        if _norm(raw).strip() in variants:
            rest = " ".join(words[i + 1:]).lstrip(",.!?:;- ").strip()
            return True, rest
    return False, ""


class Voice:
    def __init__(self, get_config):
        self.get_config = get_config
        self.events = []          # [(id, dict)]
        self._eid = 0
        self._elock = threading.Lock()
        self.state = "off"        # off | idle | wake | listening | thinking | speaking | error
        self.wake_on = False
        self._ptt = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self._model = None
        self._model_name = None
        self._speaking = threading.Event()
        self._tlock = threading.Lock()
        self._tts_proc = None

    # ------------------------------------------------------------ status
    def capabilities(self):
        stt = "ok"
        if np is None:
            stt = "numpy fehlt"
        elif sd is None:
            stt = "sounddevice/PortAudio fehlt"
        else:
            try:
                import faster_whisper  # noqa: F401
            except Exception:
                stt = "faster-whisper fehlt"
        return {"stt": stt, "tts": self.tts_engine() or "keine Sprachausgabe installiert"}

    def emit(self, **ev):
        with self._elock:
            self._eid += 1
            self.events.append((self._eid, ev))
            self.events = self.events[-200:]

    def events_since(self, since):
        with self._elock:
            return [dict(id=i, **e) for i, e in self.events if i > since], self._eid

    def set_state(self, s):
        if s != self.state:
            self.state = s
            self.emit(type="state", state=s)

    # ------------------------------------------------------------ control
    def ensure_thread(self):
        if self._thread and self._thread.is_alive():
            return
        caps = self.capabilities()
        if caps["stt"] != "ok":
            raise RuntimeError("Spracherkennung nicht verfügbar: " + caps["stt"] + ". Führe setup-linux.sh aus.")
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def set_wake(self, on):
        self.wake_on = bool(on)
        if on:
            self.ensure_thread()
            self.set_state("idle")
        elif not self._ptt.is_set():
            self._stop.set()
            self.set_state("off")

    def push_to_talk(self):
        self.stop_speaking()
        self.ensure_thread()
        self._ptt.set()

    # ------------------------------------------------------------ STT
    def _get_model(self):
        cfg = self.get_config()
        name = cfg.get("whisper_model") or "base"
        if self._model is None or self._model_name != name:
            from faster_whisper import WhisperModel
            self.emit(type="info", text=f"Lade Spracherkennung ({name}) … beim ersten Mal wird sie heruntergeladen.")
            self._model = WhisperModel(name, device="cpu", compute_type="int8")
            self._model_name = name
        return self._model

    def transcribe(self, audio):
        with self._tlock:
            model = self._get_model()
            lang = (self.get_config().get("voice_language") or self.lang()).strip() or None
            segs, _ = model.transcribe(audio, language=lang, beam_size=1, vad_filter=False,
                                       condition_on_previous_text=False)
            return " ".join(s.text.strip() for s in segs).strip()

    def transcribe_file(self, path, max_minutes=180):
        """Audiodatei (ogg/opus/m4a/mp3/wav/…) → Text mit Zeitmarken. Läuft komplett lokal."""
        caps = self.capabilities()
        if caps["stt"] not in ("ok", "sounddevice/PortAudio fehlt"):
            raise RuntimeError("Spracherkennung nicht verfügbar: " + caps["stt"] + ". Führe setup-linux.sh aus.")
        with self._tlock:
            model = self._get_model()
            lang = (self.get_config().get("voice_language") or self.lang()).strip() or None
            segs, info = model.transcribe(str(path), language=lang, beam_size=1, vad_filter=True,
                                          condition_on_previous_text=True)
            lines = []
            for sgm in segs:
                if sgm.start > max_minutes * 60:
                    lines.append("[… abgeschnitten]")
                    break
                m, sec = divmod(int(sgm.start), 60)
                lines.append(f"[{m:02d}:{sec:02d}] {sgm.text.strip()}")
            return {"dauer_min": round(getattr(info, "duration", 0) / 60, 1), "sprache": getattr(info, "language", lang),
                    "text": "\n".join(lines)}

    def synth_wav(self, text):
        """Text → WAV-Datei (für Ausgabe in Calls). Gibt Pfad zurück."""
        engine = self.tts_engine()
        wav = Path(tempfile.gettempdir()) / f"lumen-say-{os.getpid()}-{int(time.time() * 1000)}.wav"
        if engine == "piper":
            r = subprocess.run(self.piper_cmd() + ["--model", str(self.piper_model()), "--output_file", str(wav)],
                               input=text, text=True, capture_output=True, timeout=60)
            if r.returncode != 0 or not wav.exists():
                raise RuntimeError(r.stderr.strip()[-300:] or "Piper fehlgeschlagen")
        elif engine == "espeak-ng":
            speed = str(self.get_config().get("voice_speed") or 165)
            r = subprocess.run(["espeak-ng", "-v", self.lang(), "-s", speed, "-w", str(wav), text], capture_output=True, timeout=60)
            if r.returncode != 0:
                raise RuntimeError("espeak-ng fehlgeschlagen")
        else:
            raise RuntimeError("Keine Sprachausgabe installiert (Piper oder espeak-ng).")
        return wav

    def _utterances(self, stream_q):
        """Zerlegt den Mikrofonstrom per Lautstärke in einzelne Sätze (Generator)."""
        floor, speech, silence, buf = 0.004, False, 0, []
        pre = []
        while not self._stop.is_set():
            try:
                block = stream_q.get(timeout=0.3)
            except queue.Empty:
                yield None
                continue
            if self._speaking.is_set():  # nicht sich selbst zuhören
                speech, buf, pre = False, [], []
                continue
            rms = float(np.sqrt(np.mean(block ** 2)))
            thresh = max(floor * 3.2, 0.012)
            if not speech:
                floor = 0.97 * floor + 0.03 * min(rms, 0.05)
                pre = (pre + [block])[-10:]  # 300 ms Vorlauf
                if rms > thresh:
                    speech, silence, buf = True, 0, pre[:]
                    self.emit(type="level", speaking=True)
            else:
                buf.append(block)
                silence = silence + 1 if rms < thresh * 0.7 else 0
                if silence > 27 or len(buf) > 15 * 1000 // 30:  # 0,8 s Stille oder 15 s
                    speech = False
                    self.emit(type="level", speaking=False)
                    audio = np.concatenate(buf).astype(np.float32)
                    if len(audio) > RATE * 0.35:
                        yield audio
                    buf, pre = [], []
            yield None

    def _loop(self):
        q = queue.Queue(maxsize=400)

        def cb(indata, frames, t, status):
            try:
                q.put_nowait(indata[:, 0].copy())
            except queue.Full:
                pass

        try:
            stream = sd.InputStream(samplerate=RATE, channels=1, dtype="float32", blocksize=BLOCK, callback=cb)
            stream.start()
        except Exception as e:
            self.set_state("error")
            self.emit(type="error", text=f"Mikrofon konnte nicht geöffnet werden: {e}")
            return
        try:
            self._get_model()
        except Exception as e:
            stream.close()
            self.set_state("error")
            self.emit(type="error", text=f"Spracherkennung konnte nicht geladen werden: {e}")
            return

        awaiting_cmd_until = 0.0
        ptt_started = 0.0
        self.set_state("idle" if self.wake_on else "off")
        try:
            for audio in self._utterances(q):
                now = time.time()
                if self._ptt.is_set() and not ptt_started:
                    ptt_started = now
                    self.set_state("listening")
                    self.beep(880)
                if ptt_started and now - ptt_started > 10 and audio is None:
                    self._ptt.clear()
                    ptt_started = 0
                    self.emit(type="info", text="Nichts gehört.")
                    self.set_state("idle" if self.wake_on else "off")
                if awaiting_cmd_until and now > awaiting_cmd_until:
                    awaiting_cmd_until = 0
                    self.set_state("idle")
                if not self.wake_on and not self._ptt.is_set():
                    if audio is None:
                        break  # nichts mehr zu tun → Mikrofon freigeben
                if audio is None:
                    continue

                prev = self.state
                self.set_state("thinking")
                try:
                    text = self.transcribe(audio)
                except Exception as e:
                    self.emit(type="error", text=f"Spracherkennung fehlgeschlagen: {e}")
                    text = ""
                if not text or re.fullmatch(r"[\W_]*(untertitel.*|vielen dank\.?|\.\.\.)?", text.lower()):
                    self.set_state(prev if prev != "thinking" else "idle")
                    continue

                if self._ptt.is_set():
                    self._ptt.clear()
                    ptt_started = 0
                    self.emit(type="command", text=text)
                    self.set_state("idle" if self.wake_on else "off")
                    continue
                if awaiting_cmd_until:
                    awaiting_cmd_until = 0
                    self.emit(type="command", text=text)
                    self.set_state("idle")
                    continue
                if self.wake_on:
                    found, rest = split_wake(text, self.get_config().get("wake_word") or "lumen")
                    if found and rest and len(rest) > 2:
                        self.beep(880)
                        self.emit(type="command", text=rest)
                        self.set_state("idle")
                    elif found:
                        self.beep(880)
                        awaiting_cmd_until = time.time() + 8
                        self.set_state("listening")
                    else:
                        self.emit(type="heard", text=text)
                        self.set_state("idle")
        finally:
            stream.close()
            if not self.wake_on:
                self.set_state("off")

    # ------------------------------------------------------------ TTS
    def lang(self):
        return "en" if self.get_config().get("ui_lang") == "en" else "de"

    def piper_model(self):
        cfg = self.get_config()
        pre = "en_" if self.lang() == "en" else "de_"
        want = cfg.get("piper_voice") or (EN_VOICE if pre == "en_" else PIPER_VOICE)
        order = [v for v in (want, EN_VOICE if pre == "en_" else PIPER_VOICE, *VOICES) if v.startswith(pre)]
        for v in order:
            p = VOICES_DIR / f"{v}.onnx"
            if p.exists() and (VOICES_DIR / f"{v}.onnx.json").exists():
                return p
        return None

    def piper_cmd(self):
        exe = shutil.which("piper")
        if exe:
            return [exe]
        venv_exe = Path(os.sys.executable).parent / "piper"
        return [str(venv_exe)] if venv_exe.exists() else None

    def tts_engine(self):
        if self.piper_model() and self.piper_cmd():
            return "piper"
        if shutil.which("espeak-ng"):
            return "espeak-ng"
        if shutil.which("spd-say"):
            return "spd-say"
        return None

    def _player(self):
        for p in (["pw-play"], ["paplay"], ["aplay", "-q"], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]):
            if shutil.which(p[0]):
                return p
        return None

    def speak(self, text):
        text = clean_for_speech(text)
        if not text:
            return
        self.stop_speaking()
        threading.Thread(target=self._speak, args=(text,), daemon=True).start()

    def _speak(self, text):
        engine = self.tts_engine()
        if not engine:
            self.emit(type="error", text="Keine Sprachausgabe installiert (Piper oder espeak-ng).")
            return
        self._speaking.set()
        prev = self.state
        self.set_state("speaking")
        try:
            if engine == "piper":
                wav = Path(tempfile.gettempdir()) / f"lumen-{os.getpid()}.wav"
                r = subprocess.run(self.piper_cmd() + ["--model", str(self.piper_model()), "--output_file", str(wav)],
                                   input=text, text=True, capture_output=True, timeout=60)
                if r.returncode != 0 or not wav.exists():
                    raise RuntimeError(r.stderr.strip()[-300:] or "Piper fehlgeschlagen")
                player = self._player()
                if player:
                    self._tts_proc = subprocess.Popen(player + [str(wav)])
                    self._tts_proc.wait()
                elif sd is not None:
                    with wave.open(str(wav)) as w:
                        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
                        sd.play(data, w.getframerate())
                        sd.wait()
            elif engine == "espeak-ng":
                speed = str(self.get_config().get("voice_speed") or 165)
                self._tts_proc = subprocess.Popen(["espeak-ng", "-v", self.lang(), "-s", speed, text])
                self._tts_proc.wait()
            else:
                self._tts_proc = subprocess.Popen(["spd-say", "-w", "-l", self.lang(), text])
                self._tts_proc.wait()
        except Exception as e:
            self.emit(type="error", text=f"Sprachausgabe fehlgeschlagen: {e}")
        finally:
            self._tts_proc = None
            time.sleep(0.25)
            self._speaking.clear()
            self.set_state(prev if prev not in ("speaking", "thinking") else ("idle" if self.wake_on else "off"))

    def stop_speaking(self):
        p = self._tts_proc
        if p and p.poll() is None:
            p.terminate()
        if sd is not None:
            try:
                sd.stop()
            except Exception:
                pass

    def beep(self, freq=880, ms=90):
        if sd is None or np is None:
            return
        try:
            t = np.linspace(0, ms / 1000, int(22050 * ms / 1000), False)
            tone = (np.sin(2 * np.pi * freq * t) * 0.18 * np.hanning(len(t))).astype(np.float32)
            sd.play(tone, 22050)
        except Exception:
            pass
