#!/usr/bin/env python3
"""UKW-Radio mit dem HackRF – NUR EMPFANG. Liest IQ-Daten von hackrf_transfer, demoduliert FM und gibt Audio (48 kHz, mono, s16le) aus.

    python3 radio_fm.py --freq 100.3                # spielt über den Lautsprecher
    python3 radio_fm.py --freq 100.3 --out datei.raw --seconds 5   # Test: in Datei schreiben
"""
import argparse
import shutil
import signal
import subprocess
import sys

import numpy as np

FS = 2_400_000          # Abtastrate HackRF
OFFSET = 300_000        # neben dem Sender abstimmen (vermeidet den Gleichanteil in der Mitte)
D1, D2 = 10, 5          # 2,4 MHz → 240 kHz → 48 kHz
CHUNK = FS // 10        # 0,1 s


def player_cmd():
    for cmd in (["pw-cat", "-p", "--format", "s16", "--rate", "48000", "--channels", "1", "-"],
                ["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-r", "48000", "-c", "1", "-"],
                ["paplay", "--raw", "--format=s16le", "--rate=48000", "--channels=1"],
                ["ffplay", "-loglevel", "quiet", "-nodisp", "-f", "s16le", "-ar", "48000", "-ac", "1", "-"]):
        if shutil.which(cmd[0]):
            return cmd
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freq", type=float, required=True, help="Frequenz in MHz (87.5–108)")
    ap.add_argument("--gain", type=int, default=28)
    ap.add_argument("--lna", type=int, default=24)
    ap.add_argument("--volume", type=float, default=1.0)
    ap.add_argument("--out", help="statt Lautsprecher in Datei schreiben (Test)")
    ap.add_argument("--seconds", type=float, default=0)
    a = ap.parse_args()
    if not 60 <= a.freq <= 110:
        sys.exit("Nur Rundfunk: 60–110 MHz.")
    src = subprocess.Popen(["hackrf_transfer", "-r", "-", "-f", str(int(a.freq * 1e6) - OFFSET), "-s", str(FS), "-l", str(a.lna), "-g", str(a.gain), "-a", "0"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if a.out:
        sink, play = open(a.out, "wb"), None
    else:
        cmd = player_cmd()
        if not cmd:
            src.kill()
            sys.exit("Kein Audio-Player gefunden (pw-cat, aplay, paplay oder ffplay).")
        play = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        sink = play.stdin

    def stop(*_):
        for p in (src, play):
            try:
                p and p.kill()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    n0, prev, de = 0, 0j, 0.0
    alpha = 1.0 / (1.0 + 48000 * 50e-6)      # De-Emphasis 50 µs (Europa)
    total = 0
    try:
        while True:
            raw = src.stdout.read(CHUNK * 2)
            if len(raw) < CHUNK * 2:
                break
            iq = np.frombuffer(raw, dtype=np.int8).astype(np.float32).reshape(-1, 2)
            x = (iq[:, 0] + 1j * iq[:, 1]) / 128.0
            n = np.arange(n0, n0 + len(x))
            x = x * np.exp(-2j * np.pi * OFFSET * n / FS).astype(np.complex64)   # Sender in die Mitte schieben
            n0 = (n0 + len(x)) % FS
            x = x.reshape(-1, D1).mean(axis=1)                                   # Kanalfilter + auf 240 kHz
            y = np.concatenate(([prev], x))
            prev = x[-1]
            fm = np.angle(y[1:] * np.conj(y[:-1]))                               # FM-Demodulation
            au = fm.reshape(-1, D2).mean(axis=1)                                 # auf 48 kHz
            out = np.empty_like(au)
            for i, v in enumerate(au):                                           # De-Emphasis (Höhen absenken)
                de += alpha * (v - de)
                out[i] = de
            pcm = np.clip(out * 9000 * a.volume, -32000, 32000).astype("<i2")
            sink.write(pcm.tobytes())
            total += len(pcm)
            if a.seconds and total >= a.seconds * 48000:
                break
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    finally:
        try:
            sink.close()
        except Exception:
            pass
        stop()


if __name__ == "__main__":
    main()
