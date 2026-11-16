"""
Lumen – Call-Modus (Discord, TeamSpeak, Zoom … unter Linux mit PipeWire/PulseAudio).

So funktioniert's:
  • Lumen legt ein virtuelles Mikrofon „Lumen-Mikrofon“ an. Darin landen deine echte Stimme UND Lumens Stimme.
    In Discord wählst du einmal „Lumen-Mikrofon“ als Eingabegerät.
  • Lumen hört mit, was du im Call hörst (Monitor deiner Lautsprecher), und dein echtes Mikrofon – getrennt.
  • Sagt jemand „Hey Lumen, …“, antwortet Lumen hörbar für alle.
  • Personen im Call bekommen nur harmlose Werkzeuge (Websuche, Wetter, Preise) und keine privaten Infos.
  • Optional „Protokoll“: schreibt (nach Ansage) alles mit und erstellt am Ende eine Zusammenfassung.

Raum-Modus: nur dein Mikrofon (Meeting am Tisch mitschreiben), keine virtuellen Geräte.
Ton wird nie gespeichert – nur Text, und nur bei aktivem Protokoll.
"""
import os
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

import voice as voice_mod

RATE = 16000
BLOCK = 480
SINK = "lumen_voice"
VMIC = "lumen_mic"


def _pactl(*args, check=True):
    r = subprocess.run(["pactl", *args], capture_output=True, text=True, timeout=10)
    if check and r.returncode != 0:
        raise RuntimeError(f"pactl {' '.join(args[:2])}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def audio_ready():
    if not shutil.which("pactl") or not shutil.which("parec") or not shutil.which("paplay"):
        return "pactl/parec/paplay fehlen (Paket pulseaudio-utils bzw. pipewire-pulse)."
    try:
        _pactl("info")
    except Exception:
        return "Kein PulseAudio/PipeWire-Soundserver erreichbar."
    if np is None:
        return "numpy fehlt."
    return None


def _short(kind):
    out = []
    for line in _pactl("list", "short", kind).splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            out.append(parts)
    return out


def devices_present():
    sinks = [p[1] for p in _short("sinks")]
    srcs = [p[1] for p in _short("sources")]
    return SINK in sinks and VMIC in srcs


def real_mic():
    """Echtes Mikrofon (nicht Lumens virtuelles, kein Monitor)."""
    default = _pactl("get-default-source", check=False)
    if default and default != VMIC and not default.endswith(".monitor"):
        return default
    for p in _short("sources"):
        name = p[1]
        if name != VMIC and not name.endswith(".monitor") and "lumen" not in name:
            return name
    raise RuntimeError("Kein Mikrofon gefunden.")


def call_monitor():
    sink = _pactl("get-default-sink", check=False)
    if not sink or sink == SINK:
        sinks = [p[1] for p in _short("sinks") if p[1] != SINK]
        if not sinks:
            raise RuntimeError("Keine Lautsprecher/Kopfhörer gefunden.")
        sink = sinks[0]
    return sink, sink + ".monitor"


def setup_devices():
    err = audio_ready()
    if err:
        raise RuntimeError(err)
    mods = []
    if SINK not in [p[1] for p in _short("sinks")]:
        mods.append(_pactl("load-module", "module-null-sink", f"sink_name={SINK}",
                           "sink_properties=device.description=Lumen-Stimme"))
    if VMIC not in [p[1] for p in _short("sources")]:
        mods.append(_pactl("load-module", "module-remap-source", f"master={SINK}.monitor", f"source_name={VMIC}",
                           "source_properties=device.description=Lumen-Mikrofon"))
    # deine echte Stimme ins virtuelle Mikrofon
    loops = [l for l in _pactl("list", "short", "modules").splitlines() if "module-loopback" in l and f"sink={SINK}" in l]
    if not loops:
        mods.append(_pactl("load-module", "module-loopback", f"source={real_mic()}", f"sink={SINK}", "latency_msec=30",
                           "source_dont_move=true", "sink_dont_move=true"))
    return mods


def remove_devices():
    removed = 0
    for line in _pactl("list", "short", "modules").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and (SINK in parts[2] or VMIC in parts[2]):
            _pactl("unload-module", parts[0], check=False)
            removed += 1
    return removed


class Segmenter:
    """Teilt einen Audiostrom anhand der Lautstärke in Sätze."""

    def __init__(self):
        self.floor, self.speech, self.silence, self.buf, self.pre = 0.004, False, 0, [], []

    def reset(self):
        self.speech, self.buf, self.pre = False, [], []

    def feed(self, block):
        rms = float(np.sqrt(np.mean(block ** 2)))
        thresh = max(self.floor * 3.2, 0.012)
        if not self.speech:
            self.floor = 0.97 * self.floor + 0.03 * min(rms, 0.05)
            self.pre = (self.pre + [block])[-10:]
            if rms > thresh:
                self.speech, self.silence, self.buf = True, 0, self.pre[:]
            return None
        self.buf.append(block)
        self.silence = self.silence + 1 if rms < thresh * 0.7 else 0
        if self.silence > 27 or len(self.buf) > 20 * 1000 // 30:
            audio = np.concatenate(self.buf).astype(np.float32)
            self.reset()
            return audio if len(audio) > RATE * 0.35 else None
        return None


class CallMode:
    def __init__(self, voice, get_config, ask_fn):
        """ask_fn(text, source, history, context) -> Antworttext (blockierend)."""
        self.voice = voice
        self.get_config = get_config
        self.ask_fn = ask_fn
        self.active = False
        self.mode = None            # "call" | "room"
        self.protocol = False
        self.protocol_lines = []
        self.protocol_started = None
        self.lines = []             # rollierende Mitschrift (nur RAM)
        self._lid = 0
        self.speaking = threading.Event()
        self._procs = []
        self._stop = threading.Event()
        self._q = None
        self.history = []
        self.error = None
        self.busy = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------ state
    def _add(self, who, text, kind="speech"):
        with self._lock:
            self._lid += 1
            item = {"id": self._lid, "zeit": datetime.now().strftime("%H:%M:%S"), "wer": who, "text": text, "art": kind}
            self.lines.append(item)
            self.lines = self.lines[-200:]
            if self.protocol and kind in ("speech", "lumen"):
                self.protocol_lines.append(item)

    def state(self, since=0):
        return {"aktiv": self.active, "modus": self.mode, "protokoll": self.protocol, "spricht": self.speaking.is_set(),
                "denkt": self.busy, "fehler": self.error, "geräte": self._devices_ok(),
                "zeilen": [l for l in self.lines if l["id"] > since][-60:], "protokoll_zeilen": len(self.protocol_lines)}

    def _devices_ok(self):
        try:
            return devices_present()
        except Exception:
            return False

    def _name(self):
        return (self.get_config().get("assistant_name") or "Lumen").strip() or "Lumen"

    def _t(self, de, en):
        return en if self.get_config().get("ui_lang") == "en" else de

    # ------------------------------------------------------------ start/stop
    def start(self, mode="call"):
        if self.active:
            return self.state()
        err = audio_ready()
        if err:
            raise RuntimeError(err)
        caps = self.voice.capabilities()
        if caps["stt"] not in ("ok", "sounddevice/PortAudio fehlt"):
            raise RuntimeError("Spracherkennung fehlt (" + caps["stt"] + "). Führe setup-linux.sh aus.")
        self.mode, self.error = mode, None
        sources = [("du", real_mic())]
        if mode == "call":
            setup_devices()
            sources.append(("call", call_monitor()[1]))
        self._stop.clear()
        self.active = True
        self.history = []
        import queue
        self._q = queue.Queue(maxsize=2000)
        for who, src in sources:
            p = subprocess.Popen(["parec", f"--device={src}", "--format=float32le", f"--rate={RATE}", "--channels=1",
                                  "--raw", "--latency-msec=30"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self._procs.append(p)
            threading.Thread(target=self._reader, args=(who, p), daemon=True).start()
        threading.Thread(target=self._worker, daemon=True).start()
        self._add("system", "Call-Modus gestartet." if mode == "call" else "Raum-Modus gestartet (nur dein Mikrofon).", "info")
        if mode == "call":
            nm = self._name()
            self.say(self._t(f"Hallo zusammen, hier ist {nm}, ein KI-Assistent. Ich höre nur auf Fragen, die mit „Hey {nm}“ "
                             f"beginnen. Ton wird nicht gespeichert.",
                             f"Hi everyone, this is {nm}, an AI assistant. I only respond to questions that start with "
                             f"'Hey {nm}'. No audio is stored."))
        return self.state()

    def stop(self):
        self._stop.set()
        for p in self._procs:
            try:
                p.terminate()
            except Exception:
                pass
        self._procs = []
        self.active = False
        self.speaking.clear()
        self.lines = [l for l in self.lines if l["art"] != "speech"][-5:]  # Mitschrift ohne Protokoll verwerfen
        self._add("system", "Beendet. Die Mitschrift wurde gelöscht." if not self.protocol else "Beendet.", "info")
        return self.state()

    # ------------------------------------------------------------ audio
    def _reader(self, who, proc):
        size = BLOCK * 4
        while not self._stop.is_set():
            data = proc.stdout.read(size)
            if not data or len(data) < size:
                if not self._stop.is_set():
                    self.error = "Audioquelle beendet."
                break
            try:
                self._q.put_nowait((who, np.frombuffer(data, dtype=np.float32)))
            except Exception:
                pass

    def _worker(self):
        segs = {"du": Segmenter(), "call": Segmenter()}
        while not self._stop.is_set():
            try:
                who, block = self._q.get(timeout=0.3)
            except Exception:
                continue
            if self.speaking.is_set():
                segs[who].reset()
                continue
            audio = segs[who].feed(block)
            if audio is None:
                continue
            threading.Thread(target=self._handle, args=(who, audio), daemon=True).start()

    def _handle(self, who, audio):
        try:
            text = self.voice.transcribe(audio)
        except Exception as e:
            self.error = f"Spracherkennung: {e}"
            return
        if not text or re.fullmatch(r"[\W_]*(untertitel.*|vielen dank\.?|\.\.\.|amara.*)?", text.lower()):
            return
        label = "Du" if who == "du" else "Call"
        self._add(label, text)
        cfg = self.get_config()
        wake = cfg.get("wake_word") or "lumen"
        found, rest = voice_mod.split_wake(text, wake)
        if not found:
            return
        if not rest or len(rest) < 3:
            self.say(self._t("Ja?", "Yes?"))
            return
        if self.busy:
            return
        self.busy = True
        try:
            context = [f"{l['wer']}: {l['text']}" for l in self.lines if l["art"] == "speech"][-25:]
            answer = self.ask_fn(rest, who, self.history[-12:], context)
            self.history += [{"role": "user", "content": f"[{label}] {rest}"}, {"role": "assistant", "content": answer}]
            self.say(answer)
        except Exception as e:
            self.say(self._t("Das hat leider nicht geklappt.", "Sorry, that didn't work."))
            self._add("system", f"Fehler: {e}", "info")
        finally:
            self.busy = False

    # ------------------------------------------------------------ speaking
    def say(self, text):
        text = voice_mod.clean_for_speech(text, limit=500)
        if not text:
            return
        self._add(self._name(), text, "lumen")

        def run():
            try:
                wav = self.voice.synth_wav(text)
            except Exception as e:
                self._add("system", f"Sprachausgabe: {e}", "info")
                return
            self.speaking.set()
            try:
                procs = [subprocess.Popen(["paplay", str(wav)])]  # du hörst es
                if self.mode == "call":
                    procs.append(subprocess.Popen(["paplay", f"--device={SINK}", str(wav)]))  # der Call hört es
                for p in procs:
                    p.wait(timeout=120)
            except Exception as e:
                self._add("system", f"Wiedergabe: {e}", "info")
            finally:
                time.sleep(0.35)
                self.speaking.clear()
                try:
                    os.unlink(wav)
                except OSError:
                    pass
        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------ protocol
    def set_protocol(self, on):
        if on and not self.protocol:
            self.protocol, self.protocol_lines, self.protocol_started = True, [], datetime.now()
            if self.active and self.mode == "call":
                self.say(self._t("Hinweis: Ab jetzt schreibe ich das Gespräch als Text mit, um eine Zusammenfassung zu erstellen. "
                                 "Wer das nicht möchte, sagt bitte jetzt Bescheid.",
                                 "Heads up: from now on I'm taking notes of this conversation as text to create a summary. "
                                 "If anyone doesn't want that, please say so now."))
            self._add("system", "Protokoll läuft.", "info")
            return None
        if not on and self.protocol:
            self.protocol = False
            if self.active and self.mode == "call":
                self.say(self._t("Das Protokoll ist beendet.", "Note-taking has ended."))
            return self.export()
        return None

    def export(self):
        lines = self.protocol_lines
        start = self.protocol_started or datetime.now()
        text = "\n".join(f"[{l['zeit']}] {l['wer']}: {l['text']}" for l in lines)
        return {"start": start, "ende": datetime.now(), "zeilen": len(lines), "text": text, "modus": self.mode}


def save_protocol(base_dir, export, summary=None):
    d = Path(base_dir)
    d.mkdir(parents=True, exist_ok=True)
    kind = "Call" if export.get("modus") == "call" else "Meeting"
    path = d / f"{export['start']:%Y-%m-%d %H%M} {kind}.md"
    dauer = max(1, round((export["ende"] - export["start"]).total_seconds() / 60))
    body = [f"# {kind} vom {export['start']:%d.%m.%Y, %H:%M} Uhr", "", f"Dauer: ca. {dauer} Min. · {export['zeilen']} Beiträge", ""]
    if summary:
        body += [summary.strip(), "", "---", ""]
    body += ["## Mitschrift", "", "```", export["text"] or "(leer)", "```", ""]
    path.write_text("\n".join(body), "utf-8")
    return str(path)
