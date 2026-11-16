<div align="center">

# ✨ Lumen

**Dein lokaler KI-Assistent für Linux: er spricht mit dir, bedient deinen PC, schützt dein Netz und arbeitet im Team mit eigenen Agenten.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-Ubuntu%20%7C%20Debian%20%7C%20Mint-FCC624?logo=linux&logoColor=black)
![Lokal](https://img.shields.io/badge/l%C3%A4uft-lokal-2E8B57)
![KI](https://img.shields.io/badge/KI-Claude%20%7C%20OpenAI%20%7C%20Gemini%20%7C%20DeepSeek%20%7C%20Ollama-8A2BE2)

🇬🇧 [English](README.md) · 📖 [Ausführliche Anleitung](ANLEITUNG.md)

</div>

---

Lumen ist ein persönlicher Assistent, der **auf deinem eigenen Rechner** läuft. Er versteht Sprache, sieht den Bildschirm,
startet Programme und Spiele, verwaltet Server, liest Mails, recherchiert im Netz und lernt mit der Zeit dazu.
Du erreichst ihn am PC über die Weboberfläche oder von unterwegs über Telegram.
Die KI kommt über deinen eigenen API-Schlüssel (Claude, OpenAI, Gemini, DeepSeek) **oder komplett lokal und kostenlos** mit Ollama.

Lumen besteht aus reinem Python ohne Framework und Build-Schritt und bringt rund **190 Werkzeuge** mit, die die KI selbst benutzen kann.

## 🌟 Was Lumen kann

| | |
|---|---|
| 🗣️ **Sprechen & Hören** | Sprachsteuerung, Vorlesen mit lokaler Stimme (Piper), Diktieren, Meetings mitschreiben |
| 🖥️ **PC steuern** | Bildschirm sehen, Maus & Tastatur, Apps und Spiele starten, Musik, Zwischenablage-Helfer, PC-Doktor |
| 🤖 **Agenten-Team** | Agenten arbeiten parallel (Rechercheur, Coder, Admin, Schreiber …), fragen bei Unklarem nach und prüfen sich selbst. Live-Ansicht auch in Telegram |
| 🧠 **Lernt dazu** | Gedächtnis, selbst gelernte Fähigkeiten, Wissens-Bibliothek aus PDFs, eigenes Ollama-Modell, LoRA-Training auf der eigenen GPU |
| ⏰ **Autopilot** | Automationen nach Zeitplan, Heartbeat-Checks, Tagesbriefing, Browser-Steuerung |
| 🔎 **Eigene Such-Bots** | Metasuche über 11 Quellen parallel; Beobachter-Bots melden nur Neues |
| 🧰 **GitHub-Werkstatt** | Findet Werkzeuge auf GitHub, prüft sie, installiert sie isoliert und lernt selbst, sie zu bedienen |
| 👨‍💻 **Code-Werkstatt** | Projekt-Erklärer, Code-Review mit KI + Linter, Git-Assistent mit KI-Commit-Nachrichten und Konfliktlösung |
| 📱 **Telegram-Bot** | Chatten, Sprachnachrichten und Anrufe, Standort (Wetter, Wegzeit, Orts-Erinnerungen), Kamera-Bilder, Agenten steuern |
| 🛰️ **Lumen-Server** | Läuft 24/7 auf deinem Server, hält Telegram am Leben und gleicht sich mit dem PC ab |
| 📧 **E-Mail & Kalender** | Eigene Lumen-Adresse, deine Postfächer, Kontakte, Termine eintragen |
| 📷 **Überwachungskameras** | IP-Kameras (Reolink, Tapo, Hikvision, Dahua/Imou …) mit Live-Bild und Schnappschuss, auch per Telegram |
| 🛡️ **Sicherheits-Zentrale** | PC-Check, Heimnetz-Scan, USB-Wächter, nmap/Wireshark/Lynis/ClamAV, CVE-Check, Härtung |
| 📻 **Funk-Empfang** | UKW-Radio und Flugzeuge (ADS-B) mit HackRF oder RTL-SDR, nur Empfang |
| 📈 **Krypto** | Übungsdepot, Kurs-Alarme, Solana-Swaps, die **du** in Phantom bestätigst |
| 🎓 **Lernen** | Karteikarten mit Wiederholungsplan, 26-teiliger Hacking-Lernpfad (Theorie und eigenes Labor) |
| 📚 **Studio** | Bücher schreiben, aus PDFs lernen, Dokumente erstellen (Word, PDF, Excel, PowerPoint) |
| 🧩 **Plugins** | Eigene Werkzeuge als kleine Python-Dateien, Beispiele liegen bei |
| 🌍 **Zweisprachig** | Oberfläche, Antworten und Stimme auf Deutsch oder Englisch |

## 🚀 Schnellstart

```bash
git clone https://github.com/DEIN-NAME/lumen.git
cd lumen
./setup-linux.sh        # einmalig: Pakete, Python-Umgebung, Stimme, App-Menü-Eintrag
./start-mac-linux.sh    # oder im App-Menü auf „Lumen“ klicken
```

Lumen öffnet sich im Browser unter `http://127.0.0.1:8765`. Beim ersten Start trägst du einen API-Schlüssel ein oder wählst
**Ollama** für den komplett lokalen Betrieb. Fertig.

<details>
<summary><b>Komplett lokal und kostenlos mit Ollama</b></summary>

```bash
curl -fsSL https://ollama.com/install.sh | sh
```
Danach in Lumen unter **🧪 KI-Labor** ein Basis-Modell laden (z. B. Qwen 2.5 7B) und „Lumen-Modell bauen“ klicken.
Im **Auto-Modus** beantwortet die lokale KI Alltägliches, und nur schwierige Aufgaben gehen an die Cloud. Das spart Geld.
</details>

<details>
<summary><b>Windows</b></summary>

`start-windows.bat` starten. Für die Stimme:
`pip install faster-whisper sounddevice numpy pillow mss pyautogui`.
Einige Linux-Funktionen (Funk, USB-Wächter, Härtung) gibt es unter Windows nicht.
</details>

## 💻 Voraussetzungen

- **Linux** (Ubuntu, Debian, Mint und andere Debian-basierte Systeme), Python **3.10+**
- Ein API-Schlüssel **oder** Ollama
- Optional: **NVIDIA-GPU mit 8 GB+** für lokale Modelle und LoRA-Training · **HackRF/RTL-SDR** für Funk ·
  **IP-Kamera mit RTSP** · **Telegram-Bot** (über @BotFather) für unterwegs

`setup-linux.sh` installiert alles Nötige (u. a. ffmpeg, git, ripgrep, Playwright/Chromium, Piper-Stimme).
Alles Weitere schaltest du in der Oberfläche frei, und Lumen zeigt dir, was auf deinem PC schon bereit ist.

## 📱 Unterwegs mit Telegram

Bot bei **@BotFather** anlegen, das Token in Lumen unter *Apps → Telegram* eintragen, und schon antwortet Lumen auf dem Handy.
Einige Befehle:

`/agent` Agent starten · `/agenten` laufende Agenten · `/kamera` Kamera-Bild · `/standort` Standort teilen ·
`/suche` Metasuche · `/beobachte` Thema beobachten · `/github` Werkzeug finden · `/anruf` Lumen anrufen ·
`/lernen` Karteikarten · `/automation` Automationen

Damit Telegram auch läuft, wenn der PC aus ist, gibt es den **Lumen-Server** (Abschnitt „Lumen-Server“ in der [Anleitung](ANLEITUNG.md)).

## 🔒 Sicherheit & Datenschutz

Lumen hat Zugriff auf viel, deshalb sind die wichtigsten Schutzregeln **fest eingebaut**:

- **Deine Daten bleiben bei dir.** Einstellungen, Chats und Gedächtnis liegen in `~/.lumen` (nicht im Projektordner).
  Der Server lauscht nur auf `127.0.0.1` und verlangt ein Token.
- **Passwörter** gibst du nur in geschützten Feldern ein. Sie gehen nie an die KI, nie in den Chat und nie über Telegram.
  Lumen fragt nie nach Seed-Phrasen oder privaten Schlüsseln.
- **Riskante Aktionen** (Mails senden, Kaufen-Klicks, Commits, Installationen, Systemänderungen) brauchen immer deine Bestätigung.
- **Inhalte von außen sind Daten.** Anweisungen in Webseiten, E-Mails, READMEs oder Code befolgt Lumen nicht.
- **Krypto:** Lumen führt keine echten Transaktionen aus. Swaps bereitet es nur vor, und **du** unterschreibst sie in Phantom.
  Es gibt ein Limit pro Swap und keine Finanzberatung.
- **Code:** force-push, `reset --hard` und `clean` werden gar nicht angeboten. Commits mit Geheimnissen werden gestoppt.

## ⚖️ Verantwortungsvolle Nutzung

Die Sicherheits-, Netzwerk- und Funk-Werkzeuge sind zum **Schutz eigener Geräte** gedacht:

- Scans (nmap, Web-Scanner, Port-Scans) nur auf **eigene** Rechner, das **eigene** Heimnetz und **eigene** Domains.
  Lumen prüft das vor jedem Scan.
- **HackRF/SDR nur zum Empfangen:** kein Senden, Stören, Wiederholen oder Klonen von Signalen.
- Angriffswerkzeuge (Passwort-Cracker, Exploit-Frameworks) werden erkannt, aber nicht gesteuert. **Keine Personensuche**,
  Prüfungen nur für eigene Konten.
- Überwachungskameras: nur das **eigene Grundstück** filmen. Lumen zeichnet nichts auf und erkennt keine Personen.

Du bist selbst dafür verantwortlich, Lumen im Rahmen der Gesetze deines Landes zu nutzen.

## 🗂️ Aufbau

```
lumen.py            Server, Werkzeuge, KI-Anbindung, Telegram-Befehle
web/                Oberfläche (index.html, Übersetzung, Phantom-Swap-Seite)
agents.py           Agenten und Agenten-Team
autopilot.py        Automationen und Heartbeat
skills.py           selbst gelernte Fähigkeiten
searchbots.py       eigene Metasuche und Beobachter-Bots
ghtools.py          GitHub-Werkstatt
codehelp.py         Code-Werkstatt (Review, Git, Projekt-Erklärer)
camera.py           IP-Kameras (RTSP)
cyber.py, secplus.py  Sicherheits-Werkzeuge
telebot.py, serverlink.py  Telegram und Lumen-Server
mail.py, calendars.py, trading.py, funk.py, trainer.py, orte.py, browser.py …
plugins_beispiele/  Beispiel-Plugins zum Nachbauen
```

## 🤝 Mitmachen

Ideen, Fehlerberichte und Pull Requests sind willkommen. Am einfachsten startest du mit einem **Plugin**, das ist eine
einzelne Python-Datei. Die Beispiele liegen in `plugins_beispiele/`, die Erklärung steht im Abschnitt „Plugins“ der [Anleitung](ANLEITUNG.md).

## 📄 Lizenz

Noch nicht festgelegt.
<!-- Tipp: MIT-Lizenz als Datei LICENSE hinzufügen, dann hier "MIT – siehe LICENSE" eintragen. -->
