# Lumen – ausführliche Anleitung

> 🇬🇧 **English?** Settings (⚙) → *Sprache · Language* → **English** → Save. The whole interface, the answers, the
> voice (English Piper voices) and speech recognition switch to English. Quick guide: [GUIDE.md](GUIDE.md)

Lumen läuft auf deinem PC, versteht Sprache, sieht deinen Bildschirm, bedient Maus und Tastatur,
startet Spiele und Programme und verwaltet deine Server per SSH. Die KI kommt über deinen eigenen
API-Key (Claude, OpenAI, Gemini oder DeepSeek) – oder komplett lokal und kostenlos mit Ollama.

## Einrichten (Linux)
```bash
unzip Lumen.zip && cd lumen
./setup-linux.sh        # einmalig: installiert Pakete, Python-Umgebung, Stimme, App-Menü-Eintrag
./start-mac-linux.sh    # oder im App-Menü „Lumen“ anklicken
```
Beim ersten Start öffnen sich die Einstellungen: API-Key eintragen, speichern, fertig.
Unter **Einstellungen** siehst du unten, was auf deinem PC bereit ist (Stimme, Bildschirm, Maus, SSH).

Windows: `start-windows.bat` (Stimme dort mit `pip install faster-whisper sounddevice numpy pillow mss pyautogui`).

## 🧪 KI-Labor – Lumens eigene KI
Oben **🧪 KI-Labor**. Braucht Ollama (`curl -fsSL https://ollama.com/install.sh | sh`).

**1 · Eigenes Lumen-Modell** – Basis wählen (z. B. Qwen 2.5 7B), „Herunterladen“, dann „Lumen-Modell bauen“.
Es entsteht das Modell `lumen` mit Lumens Name, Persönlichkeit und allem, was Lumen über dich weiß – offline und
kostenlos. Auch im Terminal nutzbar: `ollama run lumen`. Nach Änderungen an Persönlichkeit/Gedächtnis neu bauen.

**2 · Schlaues Zusammenspiel (Auto-Modus)** – Smalltalk, Musik, Apps, Wetter beantwortet die lokale KI; Recherche,
Code, Dateien, Bilder, Server die Cloud (Claude/Gemini/…). Ist die lokale Antwort zu schwach, fragt Lumen automatisch
die Cloud. Unter jeder Antwort steht 🧠 lokal oder ☁️ Cloud. Spart viel Geld.

**3 · Lumen trainieren (NVIDIA-Grafikkarte)** – so einfach wie möglich:

1. **Beispiele sammeln** – die Anzeige zeigt, wie viele es schon sind (ab 30 möglich, ab 100 gut, ab 500 top):
   - 🎓 **Lehrer-KI:** Claude (oder deine Cloud-KI) schreibt einmalig 200 Übungsgespräche in Lumens Stil.
     Die Kosten (ca. 1–2 $) werden vorher angezeigt. Der schnellste Weg zum ersten Training.
   - ☁️ **Von der Cloud lernen:** Im Auto-Modus merkt sich Lumen automatisch jede Cloud-Antwort auf deine Fragen.
     Antworten mit Datei-Anhang oder PC-Aktionen werden nicht gemerkt.
   - ⚡ **Schnell bewerten:** Alte Antworten nacheinander: Taste `1` 👍, `2` 👎, `3` ✏️ verbessern, Leertaste überspringen.
   - ✏️ **Im Chat verbessern:** Unter jeder Antwort ✏️ → schreiben, wie es richtig gewesen wäre.
2. **🚀 „Lumen jetzt trainieren“** – ein Klick. Lumen prüft Ollama und GPU, wählt das passende Modell (8 GB → 7B,
   weniger → 3B), baut den Datensatz, installiert beim ersten Mal die Trainings-Umgebung (5–8 GB), trainiert
   (15–90 Min.), stellt auf das neue Modell um und macht einen Kurztest. Du kannst Lumen währenddessen normal nutzen.
3. **Vorher/Nachher vergleichen** mit einer eigenen Testfrage, gefällt's nicht → **↩ Zurück zum alten Modell**.
4. Optional **🌙 nachts automatisch nachtrainieren**, wenn 50+ neue Beispiele da sind (3–5 Uhr, PC muss an sein).

Alles von Hand (Basis, Durchgänge, Name) geht weiter unter „Profi-Einstellungen“.

**4 · Mini-KI von null** – Ein winziger Transformer (wie GPT, nur tausendmal kleiner) lernt Buchstabe für Buchstabe aus
euren Chats (und .txt-Dateien in `~/.lumen/lab/mini_texte/`). Zum Verstehen, wie KI lernt: erst Buchstabensalat,
dann Wörter, dann Sätze. Wird nicht schlau – macht aber Spaß.

**Fluchen:** Einstellungen → Persönlichkeit → „Kraftausdrücke erlaubt“ oder Charakter „Ungefiltert“. Lumen redet dann
derb und direkt – Hetze und ernsthafte Beleidigungen bleiben aus, Sicherheitsregeln gelten weiter.

## Lumen in Discord-Calls (Linux)
Rechts die Karte **Call & Meeting**:
1. **„Call-Modus starten“** – Lumen legt ein virtuelles Mikrofon **„Lumen-Mikrofon“** an und sagt im Call kurz Hallo.
2. **Einmalig in Discord:** Einstellungen → Sprache & Video → Eingabegerät: **Lumen-Mikrofon**.
   (Darin sind deine Stimme und Lumens Stimme – deine Freunde hören dich ganz normal.)
3. Jeder im Call kann fragen: **„Hey Lumen, wer hat 2022 die WM gewonnen?“** – Lumen antwortet hörbar für alle.

Funktioniert genauso in TeamSpeak, Mumble, Zoom, Teams, Signal-Desktop usw. Braucht PipeWire oder PulseAudio
(Standard bei Ubuntu, Fedora, Mint, Arch). Unter Windows/Mac ist der Call-Modus nicht verfügbar.

**Sicherheit:** Fragen von anderen Personen im Call bekommen einen eingeschränkten Lumen – nur Websuche, Wetter,
Preise. Sie können nichts an deinem PC tun und erfahren nichts Privates (Gedächtnis, Termine, Wallet, Server,
Dateien). Wenn **du** fragst, hat Lumen seine normalen Fähigkeiten, führt riskante Aktionen im Call aber nicht aus.
Ton wird nie gespeichert. Mit „Lumen-Mikrofon entfernen“ verschwindet das virtuelle Gerät wieder.

## Meetings & Sprachnachrichten mitschreiben
- **Protokoll im Call:** Häkchen „Alle wissen Bescheid“ → „Protokoll starten“. Lumen sagt im Call an, dass
  mitgeschrieben wird. „Protokoll beenden & zusammenfassen“ erstellt Kurzfassung, Themen, Entscheidungen und eine
  **To-do-Tabelle** (deine To-dos landen automatisch in deinen Aufgaben).
- **Meeting im Raum:** nur dein Mikrofon, z. B. am Tisch, in der Schule oder bei einer Besprechung.
- **Sprachnachrichten & Aufnahmen:** WhatsApp-/Telegram-Sprachnachricht, Podcast oder Aufnahme (ogg, opus, m4a,
  mp3, wav, mp4 …) in den Chat ziehen → „Was steht da drin?“.
- Alles wird **lokal** mit Whisper erkannt, gespeichert unter **Dokumente/Lumen-Protokolle/** (nur Text).
- Wichtig: Gespräche nur mitschreiben, wenn alle Bescheid wissen – heimliches Aufnehmen ist in Deutschland strafbar.

## 🤖 Agenten & Agenten-Team
Für große Aufgaben, die viele Schritte brauchen: Oben **🤖 Agenten** (die Zahl zeigt, wie viele gerade **online** sind,
gelb blinkend = einer wartet auf deine Bestätigung). Aufgabe eintippen → **Agent starten**. Der Agent plant selbst
(3–10 Schritte), arbeitet alles im Hintergrund ab, prüft sein Ergebnis und schreibt einen Bericht – du chattest
währenddessen normal weiter. Der Bericht landet auch als Chat im Verlauf.

**🧭 Als Team:** Ein Leiter zerlegt die Aufgabe und startet bis zu 4 Spezialisten gleichzeitig – 🔎 Rechercheur,
🧑‍💻 Coder, 🛠️ Admin, ✍️ Schreiber – und lässt am Ende einen ✅ Prüfer kontrollieren. Jeder Spezialist hat nur die
Werkzeuge, die er braucht. Im Fenster siehst du alle Agenten mit Rolle, Status (plant / arbeitet / wartet auf dich /
fertig), Fortschrittsbalken, Plan, aktuellem Schritt, Laufzeit und Kosten; das Team erscheint eingerückt unter dem Leiter.

Starten geht auch mit `/agent <Aufgabe>`, `/team <Aufgabe>`, im Chat („Mach das als Agent im Hintergrund: …“) und per
**Telegram** (`/agent`, `/team`, `/agenten` = wer ist online). Vom Handy gestartete Agenten fragen per ✅/❌-Knopf
nach und schicken das Ergebnis aufs Handy. Riskante Aktionen werden immer bestätigt; Agenten nutzen im Auto-Modus die
Cloud-KI (stärker), sonst dein lokales Modell. Maximal 12 Agenten gleichzeitig.


**Neu – bessere Agenten:**
- **Rückfragen:** Fehlt eine Info, die nur du kennst (welcher Server, welches Budget …), fragt der Agent kurz nach – in der
  App und per Telegram, mit Antwort-Knöpfen. Antwortest du nicht (Standard 20 Min), macht er mit einer Annahme weiter.
- **Selbstprüfung:** Am Ende kontrolliert ein Prüfer, ob der Auftrag wirklich erledigt ist; fehlt etwas, arbeitet der Agent nach.
- **Grenzen:** Zeitlimit (Standard 60 Min) und Kostenlimit (Standard 1 $) pro Auftrag – einstellbar unter „⚙ Grenzen & Verhalten“.
- **Bleibt erhalten:** Agenten und Ergebnisse überstehen einen Neustart; unterbrochene lassen sich mit „🔁 Neu starten“ fortsetzen.
- **Dateien:** Erzeugte Dateien werden erkannt, in der Karte angezeigt und in Telegram mitgeschickt.
- **Lernt mit:** Nach erfolgreichen Aufträgen hält Lumen den Weg als Fähigkeit fest.

**Telegram-Agent:** `/agent <Aufgabe>` bzw. `/team <Aufgabe>` – eine Nachricht zeigt **live** den Fortschritt (Plan mit Häkchen,
Balken, aktueller Schritt, Kosten) mit „🛑 Stoppen“ und „📋 Verlauf“. Rückfragen beantwortest du per Knopf oder einfach
mit einer Nachricht; Bestätigungen per Knopf. Am Ende: Bericht + Dateien, „📄 Ganzer Bericht“, „🔁 Nochmal“. `/agenten` listet
alle mit Knöpfen (live ansehen, stoppen, neu starten). Auch im normalen Telegram-Chat: „Mach das als Agent: …“.

## 📅 Kalender – Termine eintragen
Einfach sagen: „Trag mir Freitag 18 Uhr Kino mit Lisa ein, erinner mich 30 Minuten vorher“, „Verschieb den Zahnarzt auf
Dienstag 10 Uhr“, „Lösch das Training am Montag“, „Wann hab ich morgen Zeit?“ – oder `/termin Freitag 18 Uhr Kino`
(auch per Telegram). Wiederkehrend geht auch (täglich, wöchentlich, zweiwöchentlich, monatlich, jährlich, werktags).

Wohin? (Apps → Kalender)
- **Ohne Einrichtung:** Lumen-Kalender (lokal). Erscheint in der Uhr-Karte, im Briefing, wird mit dem Lumen-Server
  abgeglichen und liegt als `~/.lumen/lumen-kalender.ics` zum Importieren bereit. Lumen gibt dir zusätzlich einen
  Klick-Link, der den Termin in Google Kalender öffnet.
- **Nextcloud, iCloud, mailbox.org, Posteo, Fastmail, Radicale (CalDAV):** Adresse, Benutzer und App-Passwort eintragen
  (iCloud: `https://caldav.icloud.com` + App-Passwort von appleid.apple.com; Nextcloud: `https://deine-cloud/remote.php/dav`).
- **Google Kalender:** eigene OAuth-Client-ID (Desktop-App) in der Google Cloud Console anlegen, „Google Calendar API“
  aktivieren, ID + Secret eintragen → „Mit Google anmelden“.
- **Outlook/Exchange:** nur lesen per iCal-Link.

Löschen fragt immer nach. Termine aus reinen iCal-Links kann Lumen nur lesen.

## 👨‍💻 Code-Werkstatt – Projekt-Erklärer, Code-Reviewer, Git-Assistent
Karte **👨‍💻 Code-Werkstatt** (oder `/code`, `/review`, `/git`) – Projektordner eintippen oder „📂 Wählen“:

- **🗺 Projekt-Erklärer:** Sprachen, Ordner, Einstiegspunkte, Abhängigkeiten (npm, pip, Go, Cargo …), Skripte, Git-Stand und eine
  Gliederung (Klassen/Funktionen) der wichtigsten Dateien. „🧠 Projekt erklären lassen“, „Wie starte ich das?“, „Diese Datei erklären“
  oder eine `ARCHITEKTUR.md` schreiben lassen. Code-Suche („Wo wird `load` benutzt?“) mit ripgrep.
- **🔍 Code-Reviewer:** prüft offene Änderungen, nur Vorgemerktes, den letzten Commit, einen ganzen Branch gegen main, einen bestimmten
  Commit oder eine ganze Datei. Linter laufen mit (ruff für Python, shellcheck, Syntax-Check für JS/JSON), dazu eine Suche nach
  eingecheckten Passwörtern/API-Schlüsseln. Ergebnis: Gesamtnote, Funde nach Schwere (🔴 kritisch … 💡 Tipp) mit Erklärung und
  Lösungsvorschlag – „🔧 Lumen soll das beheben“ übergibt den Fund an den Chat.
- **🌿 Git-Assistent:** Status mit Diff pro Datei, vormerken per Klick, **Commit-Nachricht von Lumen** (im Stil deiner bisherigen Commits,
  Deutsch/Englisch), committen, Branches anlegen/wechseln/löschen, abgleichen/holen (nur fast-forward)/hochladen, letzten Commit
  zurücknehmen (nur wenn noch nicht hochgeladen, Änderungen bleiben). Commits mit Geheimnissen werden gestoppt.
- **⚔️ Konflikte:** bei Merge/Rebase beide Seiten nebeneinander; „unsere“, „ihre“ oder **Lumen führt beide zusammen** (mit Erklärung
  und Vorschau), danach Merge abschließen oder abbrechen.
- **Im Chat & im Agenten-Team:** „Review meine Änderungen in ~/Projekte/app“, „Mach einen Commit“, „Erklär mir das Projekt“ – der
  Coder-Agent hat die Werkzeuge auch.
- **Sicherheit:** force-push, `reset --hard` und `clean` bietet Lumen absichtlich nicht an. Commit, Push, Pull, Branch-Wechsel und
  Konfliktlösung fragen immer nach. Code, Kommentare und READMEs sind für die KI nur Daten.
- Optional: `pipx install ruff` und `sudo apt install shellcheck ripgrep zenity` für Linter, schnelle Suche und Ordner-Auswahl.

## 📷 Überwachungskameras
Karte **📷 Kameras** (oder `/kamera`): IP-Kameras im WLAN/LAN verbinden – Reolink, TP-Link Tapo/Vigi, Hikvision/Ezviz,
Dahua/Imou/Amcrest, eufy, Foscam, Axis, Wyze, UniFi und alles mit ONVIF/RTSP.

- **Einrichten:** „📡 Im Netz suchen“ findet Kameras im Heimnetz (ONVIF-Rundruf + RTSP-Port), „Übernehmen“, Benutzer und
  Kamera-Passwort eintragen, „Verbindung testen“. Lumen erkennt die richtige Stream-Adresse selbst; zu jeder Marke steht ein
  Tipp (z. B. Tapo: in der App ein *Kamerakonto* anlegen; Reolink: RTSP einschalten; Imou: Passwort = Sicherheitscode).
  Notfalls die RTSP-Adresse aus dem Handbuch unter „Eigene RTSP-Adresse“ eintragen.
- **Live-Bild & Schnappschuss:** Alle Kameras als Kacheln, ▶ Live (ca. 5 Bilder/s über den Unterstream), 📸 neues Bild,
  Vollbild, Bild speichern. Mini-Vorschau direkt in der Karte.
- **Im Chat:** „Wer steht vor der Haustür?“ – Lumen holt ein Bild und beschreibt es (braucht ein Modell, das Bilder sehen kann).
- **Telegram:** `/kamera` schickt ein aktuelles Foto (bei mehreren Kameras mit Auswahl, `/kamera alle` für alle) mit „🔄 Neu“-Knopf.
- **Datenschutz:** Kamera-Passwörter nur im Lumen-Fenster eingeben (nie im Chat/Telegram); sie liegen nur in
  `~/.lumen/cameras.json` (Rechte 600) und gehen nie an die KI. Bilder werden nicht aufgezeichnet. Lumen verbindet nur Kameras
  im eigenen Netz, rät keine Passwörter und erkennt keine Personen. Bitte nur das eigene Grundstück filmen.
- **Geht nicht:** Ring, Arlo, Blink, Google Nest und viele Billig-Cloud-Kameras haben keinen RTSP-Zugang.
- Braucht `ffmpeg` (installiert `setup-linux.sh` mit). Läuft Telegram über deinen Lumen-Server, muss der Server im selben
  Heimnetz stehen und die Kamera dort eingerichtet sein.

## 🔎 Eigene Such-Bots & 🧰 GitHub-Werkstatt
Karte **🔎 Such-Bots & GitHub** (oder `/suche`, `/beobachte`, `/github`, `/werkstatt`):

- **Metasuche mit eigenen Such-Bots:** Statt einer Suchmaschine fragen bis zu 11 kleine Bots parallel DuckDuckGo, Bing,
  Mojeek, Wikipedia, GitHub, Stack Overflow, Hacker News, Reddit, arXiv – plus Brave-Such-API und eine eigene SearXNG-Instanz,
  wenn du `brave_key` bzw. `searxng_url` einträgst. Die Treffer werden zusammengeführt (doppelte Links raus); was mehrere
  Quellen finden, steht oben. Profile: allgemein, technik, code, wissen, news, meinungen, alles – oder automatisch.
  Lumen nutzt die Metasuche auch selbst bei Recherchen und im Agenten-Team (Rechercheur, Coder).
- **Beobachter-Bots:** „/beobachte HackRF Firmware Update“ – ein Bot sucht regelmäßig (stündlich bis wöchentlich) und meldet
  **nur neue** Treffer per Telegram oder am PC, auf Wunsch mit kurzer KI-Zusammenfassung und Pflichtwörtern („muss enthalten“).
- **GitHub-Werkstatt:** Fehlt Lumen ein Werkzeug („Ich will YouTube-Videos als MP3 speichern“), sucht es auf GitHub, **prüft**
  das Repo (Sterne, Alter, Lizenz, Pflege, Fork, Warnzeichen) und schlägt es vor. Mit deinem OK installiert es **isoliert**
  unter `~/.lumen/gh-tools` – fertige Linux-Release-Datei, Python-Paket in eigener venv, Quellcode, Go oder npm, ohne Admin-Rechte –
  und **lernt danach selbst, es zu benutzen**: liest README und `--help` und schreibt sich eine Fähigkeit `gh-<name>`.
  Gestartet wird ohne Shell im Ordner `~/Lumen/Werkzeuge`; vor jedem Start fragt Lumen, außer du markierst das Werkzeug als
  „vertraut“. Aktualisieren, neu lernen und entfernen (samt Fähigkeit) im Fenster „📦 Meine Werkzeuge“.
- **Grenzen:** Angriffs-/Schadsoftware (Keylogger, Stealer, RATs, Cracker, DDoS …) und Personensuche-Tools (Sherlock, Maigret,
  Holehe …) installiert Lumen nicht. README- und Webseiten-Inhalte sind nur Daten – Anweisungen darin befolgt Lumen nicht.
  Ohne GitHub-Token sind 60 Anfragen/Stunde möglich; ein Token ohne Rechte (Apps → GitHub) hebt das auf 5000.
- **Telegram:** `/suche <Frage>` (mit Knöpfen „Zusammenfassen“ und „Beobachten“), `/beobachte <Thema>`, `/bots`,
  `/github <was du brauchst>` → Treffer prüfen → „Installieren & lernen“.

## 🤖 Autopilot – Automationen, Heartbeat, Fähigkeiten, Browser
Karte **🤖 Autopilot** (oder `/automation`, `/heartbeat`, `/faehigkeiten`):

- **⏱ Automationen (geplante KI-Aufgaben):** Lumen erledigt Aufträge selbstständig nach Zeitplan – einmal, täglich,
  Mo–Fr, wöchentlich, monatlich, stündlich oder alle X Minuten – und schickt das Ergebnis per Telegram, an den PC oder
  speichert es nur. Beispiele: „Jeden Morgen um 7 die 5 wichtigsten News“, „Jeden Freitag um 18 Uhr ein Wochenrückblick“.
  Anlegen im Fenster, im Chat („Schick mir jeden Morgen …“) oder in Telegram mit `/automation <Auftrag>`;
  `/automation` zeigt alle mit „▶ Jetzt“-Knöpfen. Riskante Aktionen sind bei Automationen gesperrt (niemand kann bestätigen).
- **💓 Heartbeat (wie bei OpenClaw):** Alle 15 Min–4 Std geht Lumen still deine **eigene Checkliste** durch („Wichtige
  ungelesene Mail?“, „Termin in der nächsten Stunde?“, „SOL unter 120 €?“) und meldet sich **nur, wenn etwas ist** – nichts
  doppelt, mit Ruhezeit (Standard 22–7 Uhr). Lumen darf dabei nur nachsehen, nichts ändern oder senden. Standardmäßig aus;
  Telegram: `/heartbeat an|aus|jetzt|<neuer Punkt>`. Mit Cloud-KI kostet jeder Durchlauf eine Anfrage – lokal ist er gratis.
- **🧠 Selbst gelernte Fähigkeiten (wie bei Hermes):** Nach längeren, erfolgreichen Aufgaben schreibt Lumen sich eine
  Anleitung (SKILL.md: Wann · Schritte · Stolperfallen) und nutzt sie beim nächsten ähnlichen Auftrag – und verbessert sie.
  Alte Fassungen bleiben erhalten. Du kannst sie ansehen, ändern, pausieren, löschen oder selbst welche einfügen.
  Fähigkeiten sind reine Text-Anleitungen, nie Code, und enthalten keine Passwörter. Abschaltbar.
- **🌐 Browser-Steuerung:** „Such mir auf der Bahn-Seite eine Verbindung nach Lyon für Samstag früh“ – Lumen öffnet einen
  eigenen Browser (eigenes Profil, Anmeldungen bleiben), liest Seiten, klickt, tippt, scrollt. **Passwörter, PINs und
  Zahlungsdaten tippt Lumen nie**; **Kaufen, Bezahlen, Senden, Löschen, Bestätigen und Formulare abschicken fragen immer
  nach**; Texte auf Webseiten sind nur Daten (Anweisungen dort werden ignoriert). Nach 20 Minuten ohne Nutzung schließt
  er sich. Einrichtung macht `setup-linux.sh` (Playwright + Chromium).

Mit Lumen-Server laufen Automationen und Heartbeat dort rund um die Uhr; Änderungen am PC werden übertragen,
Änderungen per Telegram bleiben am Server erhalten.

## 📍 Standort teilen (Telegram) – Wetter, Weg zum Termin, Orts-Erinnerungen
Schick dem Lumen-Bot deinen **Standort** (📎 → Standort, oder `/standort` → Knopf „📍 Standort senden“). Lumen antwortet mit:
- **Wo du bist** (Straße, Ort) und dem **Wetter genau dort**,
- dem **nächsten Termin mit Ort**: wie lange du brauchst (Auto, Rad oder zu Fuß – Einstellung „Unterwegs meistens“) und
  **bis wann du losmusst**,
- Knöpfen: 🔔 Erinnerung hier · 🔎 In der Nähe (Apotheke, Supermarkt, Bäckerei, Café, Geldautomat, Tankstelle) ·
  🏠 Als Zuhause / 🏢 Als Arbeit speichern · 🌤 Wetter 3 Tage.

**Orts-Erinnerungen** – einfach sagen oder schreiben:
„Erinnere mich an Milch, wenn ich beim Supermarkt bin“ (jede Filiale) · „… wenn ich zuhause ankomme“ ·
„… wenn ich die Arbeit verlasse“ · „Erinnere mich hier an …“ · auch an Adressen. Einmalige Erinnerungen sind nach dem
Auslösen erledigt („🔁 Nächstes Mal wieder erinnern“ holt sie zurück); „jedes Mal“ geht auch.

Damit das **unterwegs automatisch** klappt, teile in Telegram deinen **Live-Standort** (📎 → Standort → „Live-Standort
teilen“, z. B. 8 Stunden). Dann meldet Lumen sich auch mit **„🚗 Zeit loszufahren“**, wenn ein Termin mit Ort ansteht.
Ohne Live-Standort prüft Lumen nur, wenn du den Standort von Hand schickst – Telegram gibt Bots keinen Standort im Hintergrund.

Im Chat: „Wo ist die nächste Apotheke?“, „Wie lange brauche ich nach Hause?“, „Wann muss ich zum Zahnarzt los?“.
**Datenschutz:** Lumen speichert nur deinen letzten geteilten Standort (kein Verlauf, nach 24 Stunden vergessen; `/standort
vergessen` löscht ihn sofort). Karten, Wege und Orte kommen von OpenStreetMap. Mit Lumen-Server liegt der Standort auf
dem Server (dort läuft der Bot); Orts-Erinnerungen, die du am PC anlegst, werden dorthin übertragen.

## 📞 Lumen anrufen (Telegram-Sprachnachrichten)
Schick dem Lumen-Bot eine **Sprachnachricht** – Lumen versteht sie (lokal mit Whisper) und antwortet als Text **und als
Sprachnachricht** (lokal erzeugt mit Piper/espeak, braucht `ffmpeg`). Mit **`/anruf`** startest du ein Gespräch: Lumen begrüßt
dich mit Stimme und antwortet ab dann kurz und natürlich wie am Telefon; **`/auflegen`** beendet es. Einstellung
„Telegram: mit Stimme antworten“: bei Sprachnachrichten (Standard) / immer / nie. Echte Telegram-Anrufe können Bots nicht annehmen.

## 🎓 Lernen – Karteikarten & Hacking-Lernpfad
Karte **🎓 Lernen** (oder `/lernen`, `/pfad`):
- **Karteikarten mit täglicher Wiederholung:** Karten, die du kannst, kommen immer seltener (1, 3, 8, 20 … Tage), schwierige
  öfter. Bewerten mit Nochmal / Schwer / Gut / Leicht (Tasten 1–4, Leertaste zeigt die Antwort). Karten entstehen per Satz
  („Mach mir 15 Karteikarten zu Linux-Befehlen“), aus einem PDF im Studio („In den Lern-Trainer übernehmen“) oder von Hand.
  Serie in Tagen 🔥, Erinnerung am Abend, und **in Telegram mit `/lernen`** – Karte, Antwort zeigen, bewerten.
- **🧑‍💻 Hacking-Lernpfad:** 26 Lektionen in 7 Modulen (Grundlagen & Recht, Linux, Netzwerke, Web-Sicherheit, Passwörter &
  Kryptografie, Funk & Hardware, Verteidigen & CTFs). Lumen erklärt, macht mit dir eine Praxis-Übung – **nur am eigenen PC
  oder in legalen Übungsumgebungen** (Juice Shop lokal, TryHackMe, OverTheWire …) –, stellt 5 Quizfragen, hakt die Lektion
  ab und legt Karteikarten für das an, was noch nicht sitzt. In Telegram: `/pfad`.

## 📻 Funk-Empfang – UKW-Radio & Flugzeuge (HackRF / RTL-SDR)
Karte **📻 Funk-Empfang** (oder `/radio 100.3`, `/radio aus`, `/flugzeuge`):
- **UKW-Radio:** Sendersuche, Sendern Namen geben, abspielen über den PC-Lautsprecher, Lautstärke. Auch per Satz:
  „Mach Radio Eins an“, „Radio aus“. Der HackRF wird von Lumens eigenem FM-Demodulator (`radio_fm.py`) gelesen;
  RTL-SDR-Sticks laufen über `rtl_fm`. DAB+ kann Lumen noch nicht (dafür: welle.io).
- **Flugzeuge über dir (ADS-B, 1090 MHz):** Radar-Ansicht mit Entfernung und Richtung, Liste mit Kennung, Höhe, Tempo,
  Kurs; Notfall-Codes (7500/7600/7700) werden markiert. Alles direkt aus der Luft, ohne Internet. „Welche Flugzeuge sind
  über mir?“ geht auch im Chat. **Einmalig:** `bash setup-adsb.sh` (baut dump1090 mit HackRF-Unterstützung nach
  `~/.lumen/tools`). Standort für das Radar: Ort eintragen (nur lokal gespeichert).

Der Empfänger kann nur eines gleichzeitig (Radio, Flugzeuge oder Spektrum-Scan) – Lumen schaltet automatisch um.
Weiterhin gilt: nur Empfang, nie senden.

## 🛡️ Sicherheits-Zentrale – PC, Heimnetz, USB, Funk (HackRF), Domain
Karte **Sicherheit → 🛡️ Sicherheits-Zentrale** (oder `/sicherheit`, `/netz`, `/usb`, `/funk`, `/domain seite.de`):
- **💻 PC-Check:** Firewall, aus dem Netz erreichbare Dienste, SSH-Einstellungen, (Sicherheits-)Updates, Festplatten-Verschlüsselung,
  Bildschirmsperre, fehlgeschlagene Anmeldungen – mit Punkten (0–100) und konkreten Tipps. Ändert nichts am System.
- **📶 Heimnetz:** alle Geräte im eigenen WLAN/LAN (IP, Hersteller, Name). Beim ersten Scan gilt alles als bekannt; danach
  fallen **neue Geräte** auf. Optional: **Heimnetz-Wächter** (prüft alle 10 Minuten, meldet am PC + Telegram).
- **🔌 USB:** angeschlossene Geräte, erkennt u. a. HackRF, RTL-SDR, Flipper Zero, Proxmark, YubiKey, Alfa-WLAN-Adapter.
  **USB-Wächter:** warnt sofort, wenn ein unbekanntes Gerät sich als **Tastatur** ausgibt (BadUSB, z. B. Rubber Ducky/Digispark)
  oder ein unbekannter Netzwerk-Adapter angesteckt wird. Geräte lassen sich als „vertraut“ merken.
- **📡 Funk (HackRF One / RTL-SDR) – nur Empfang:** Geräte-Check (Firmware, Rechte), **Spektrum-Scan** mit Diagramm
  (UKW, DAB+, Flugfunk, 433/868 MHz, Mobilfunk, WLAN … oder eigener Bereich) samt Zuordnung „welcher Funkdienst ist das?“,
  und **Signal-Test**: sendet meine eigene Fernbedienung/mein Funkschlüssel – und auf welcher Frequenz?
  Braucht `sudo apt install hackrf` (bzw. `rtl-sdr`). **Lumen sendet nie:** kein Stören, kein Replay/Klonen fremder Signale,
  kein Abhören fremder Inhalte – das ist verboten und kann Notrufe oder Flugfunk stören.
- **🌐 Domain-Report (OSINT):** Registrierung, DNS, Mail-Schutz (SPF/DMARC), HTTPS-Zertifikat, Sicherheits-Header,
  öffentlich bekannte Subdomains, Technik – mit Punkten. Für die eigene Seite oder um einen Shop zu prüfen.

Im Chat: „Wie sicher ist mein PC?“, „Wer ist in meinem WLAN?“, „Was steckt an meinen USB-Ports?“, „Scan mit dem HackRF
das 433-MHz-Band“, „Mach einen Domain-Report für meine-seite.de“. Weiterhin gilt: keine Personensuche, Port-Scans nur
auf eigenen Geräten.

## 🧰 Cybersecurity-Werkzeuge
Sicherheits-Zentrale → neue Reiter **🦠 Scanner · 🩹 Lücken · 🛠 Programme · 🧰 Werkzeugkasten** (auch per Chat und
`/scanner`, `/nmap <ziel>`, `/wireshark`, `/cve`, `/kiste`):

- **Dateien & Downloads prüfen:** getarnte Programme (`Rechnung.pdf.exe`, Programm mit .jpg-Endung), Office-Makros,
  PDFs mit JavaScript/Auto-Aktionen, Archive mit Programmen; mit **ClamAV** auch Viren; Verdächtiges per Fingerabdruck bei
  **VirusTotal** (nichts wird hochgeladen). **Quarantäne** mit einem Klick. **Download-Wächter** prüft neue Downloads automatisch.
- **Geleakte Passwörter & Schlüssel finden:** API-Keys (OpenAI, Anthropic, AWS, GitHub, Google, Stripe, Slack, Telegram …),
  private Schlüssel ohne Passphrase, Passwörter in Konfig-Dateien, Datenbank-URLs – maskiert angezeigt, mit Git-Warnung.
- **Wächter für Systemdateien & Rootkits:** Fingerabdruck von Login-/sudo-/SSH-/Autostart-Dateien und Programmen wie
  ssh, sudo, ls; meldet Änderungen (alle 6 Std.), sucht typische Rootkit-Spuren (`ld.so.preload`, versteckte Prozesse,
  Programme in /tmp); startet auf Wunsch **rkhunter/chkrootkit** (Admin-Passwort-Fenster).
- **Sicherheitslücken (CVE):** installierte Debian-/Ubuntu-Pakete und Python-Pakete gegen **OSV.dev** – mit Schwere (CVSS)
  und ob ein Update hilft. **TLS-Check** für Webseiten (TLS 1.0–1.3, Zertifikat).
- **PC absichern mit einem Klick** (zeigt vorher den genauen Admin-Befehl): Firewall (ufw, SSH nur aus dem Heimnetz),
  SSH nur mit Schlüssel (nur wenn schon einer da ist – kein Aussperren), fail2ban, automatische Sicherheits-Updates, ClamAV.
- **Deine Programme:** Lumen erkennt installierte Sicherheits-Tools und bedient sie für dich – **nmap** (Profile schnell,
  standard, gründlich, sichere Skripte, vulners, Netz-Suche), **tshark/Wireshark** (Mitschnitt deines PCs mit Zusammenfassung:
  Protokolle, Gesprächspartner, DNS-/HTTPS-Ziele, unverschlüsselter Verkehr; .pcapng zum Öffnen in Wireshark), **Lynis**
  (Härtungs-Index, Warnungen, Vorschläge), **ClamAV**, **rkhunter/chkrootkit**, **testssl.sh/sslscan**, **Nikto** (ohne DoS-Tests),
  **WhatWeb**, **Nuclei** (ohne aufdringliche Vorlagen), dazu „Wer redet gerade mit dem Internet?“ (welches Programm mit
  welchem Server). Fehlende Programme zeigt Lumen mit Installations-Befehl.
- **Werkzeugkasten (lokal, wie CyberChef):** Base64/Hex/URL/Binär/ROT13/HTML kodieren und dekodieren, Hashes (MD5–SHA-512,
  auch für Dateien), Hash erkennen, JWT lesen (mit Warnung bei `alg=none`), IP-/Netz-Rechner, Zeitstempel, Entropie,
  sichere Passwörter und Merk-Passphrasen.

**Regeln:** Scans und Mitschnitte nur für eigene Geräte, Netze und Seiten (eigene Domains trägst du unter „Programme →
Meine Domains“ ein). Angriffs-Werkzeuge wie hydra, john, hashcat, aircrack-ng, sqlmap oder Metasploit erkennt Lumen,
bedient sie aber nicht – zum Üben gibt es den Hacking-Lernpfad mit legalen Laboren.
Installieren (Debian/Ubuntu): `sudo apt install nmap tshark wireshark lynis clamav rkhunter chkrootkit sslscan nikto whatweb`
– für tshark ohne Admin: `sudo usermod -aG wireshark $USER` (danach neu anmelden), für ClamAV einmal `sudo freshclam`.

## ✨ Startseite, Vorschläge & Gedächtnis
- **Übersicht auf der Startseite:** Kacheln für Wetter, nächsten Termin, Aufgaben/Erinnerungen, ungelesene Mails,
  Übungsdepot, Kurs-Alarme und Server – ein Klick fragt Lumen danach. Es erscheint nur, was du eingerichtet hast.
- **Passende Vorschläge:** Die Knöpfe unter der Begrüßung richten sich nach deinem Tag („Bereite mich auf Zahnarzt vor“,
  „Fass meine 2 ungelesenen Mails zusammen“ …) – ohne KI-Kosten, nur aus deinen Daten.
- **Nächste Schritte:** Unter jeder Antwort stehen 2–3 Knöpfe mit sinnvollen Folgefragen.
- **Von selbst melden:** 20 Minuten vor einem Termin kommt eine Benachrichtigung (PC + Telegram).
- **Besseres Gedächtnis:** Lumen merkt sich jetzt auch deine Korrekturen und Wünsche („Vorliebe: kurze Antworten“),
  aktualisiert Altes statt es doppelt zu speichern, behält bis zu 500 Dinge und holt bei jeder Frage die passenden heraus.
  Passwörter/Schlüssel werden nie gemerkt. Tipp: „Lern mich kennen: stell mir 5 Fragen über mich“.
- **Karten einklappen:** Klick auf eine Überschrift rechts klappt die Karte ein/aus; Lumen merkt sich das.

Abschalten: Einstellungen → „Nächste Schritte vorschlagen“ / „Von selbst Hinweise geben“.

## 📈 Krypto-Trading – üben & mit Phantom tauschen
Karte **📈 Krypto-Trading → Öffnen** (oder `/trading`). Drei Bereiche:
- **🎮 Übungsdepot:** traden mit Spielgeld (Start 1.000 €, frei wählbar) zu echten Kursen, simulierte Gebühr 0,3 %,
  Charts, Gewinn/Verlust, Verlauf. Automatische Orders nur hier: Limit-Kauf, Stop-Loss, Gewinnmitnahme.
- **👻 Echt tauschen (Phantom):** z. B. 0,5 SOL → USDC. Lumen holt den besten Kurs bei **Jupiter**, zeigt Menge, Mindestbetrag,
  Slippage, Preiseinfluss und Warnungen (nicht verifizierte Token, wenig Liquidität). **„In Phantom bestätigen“** öffnet eine
  Seite in deinem Browser mit der Phantom-Erweiterung – Phantom zeigt den Tausch noch einmal, **erst deine Unterschrift dort
  führt ihn aus**. Am Handy/Telegram gibt Lumen einen Link, der Jupiter direkt in der Phantom-App öffnet.
  Sicherheits-Limits: max. € pro Tausch (Standard 250 €) und max. Slippage (1 %).
- **🔔 Alarme:** „Sag mir, wenn SOL über 200 € steigt“ → Benachrichtigung am PC + Telegram (Prüfung jede Minute).

Im Chat: „Kauf im Übungsdepot für 100 € SOL und setz einen Stop-Loss bei 140 €“, „Wie läuft mein Übungsdepot?“,
„Tausch echt 0,2 SOL in USDC“. Befehle (Desktop & Telegram): `/kurs sol btc`, `/depot`, `/trade kauf 50 € SOL`,
`/alarm SOL über 200`. Damit Lumen deinen echten Kontostand sieht: Apps → Krypto → öffentliche Phantom-Adresse eintragen.

**Sicherheit:** Lumen fragt nie nach Seed-Phrase oder privatem Schlüssel und kann ohne deine Unterschrift in Phantom
nichts ausführen. Lumen tradet nie von sich aus mit echtem Geld. Keine Anlageberatung – Krypto kann bis zum
Totalverlust fallen; Memecoins und unbekannte Token sind oft Betrug. Mit Lumen-Server hat der Server ein eigenes
Übungsdepot (für Telegram), der PC seins.

## 📧 E-Mail – Lumens eigene Adresse & deine Postfächer
Karte **📧 E-Mail → Einrichten**. Zwei Arten von Konten:
- **🤖 Lumens eigene Adresse** – leg Lumen kostenlos eine Adresse an (z. B. `lumen.deinname@gmx.de`, WEB.DE oder Gmail).
  Darüber schickt Lumen dir Berichte und Dateien („Schick mir das PDF an meine Adresse“), kann Bestätigungen/Newsletter
  empfangen und – wenn du „Aufträge per Mail annehmen“ einschaltest – Aufträge erledigen und per Mail antworten
  (z. B. vom Handy: Mail an Lumen „Wie wird das Wetter morgen?“).
- **📬 Mein Postfach** – Lumen liest, fasst zusammen, sortiert (gelesen, markieren, archivieren, Spam, löschen) und
  schreibt Antworten. **Senden und Löschen fragt immer nach** – auch wenn „Automatisch erlauben“ an ist.

Server-Einstellungen werden aus der Adresse erkannt (Gmail, GMX, WEB.DE, T-Online, iCloud, Yahoo, Posteo, mailbox.org,
Outlook, Proton Bridge). Meist brauchst du ein **App-Passwort** und musst IMAP beim Anbieter erlauben:
Gmail → Google-Konto → Sicherheit → 2-Faktor an → App-Passwörter · GMX/WEB.DE → Einstellungen → POP3/IMAP erlauben ·
iCloud/Yahoo → App-spezifisches Passwort. Outlook.com/Hotmail erlaubt normale Passwörter für IMAP oft nicht mehr
(Microsoft verlangt OAuth) – dann lieber GMX/Gmail für Lumen nehmen. Passwörter werden nur in der Karte eingegeben,
lokal gespeichert und nie an die KI geschickt.

**Kontakte** (Name = Adresse) machen „Schreib Mama eine Mail, dass ich später komme“ möglich; dazu eine **Signatur**.
„Neue Mails melden“ schickt eine Desktop-Benachrichtigung und – wenn eingerichtet – eine Telegram-Nachricht.
Im Briefing „📧 Ungelesene Mails“ anhaken. Befehle: `/mails`, `/mail Mama: komme später` (Desktop und Telegram).

**Sicherheit:** Inhalte von Mails sind für Lumen nur Daten – Anweisungen in fremden Mails werden nie befolgt.
Aufträge per Mail nimmt Lumen nur von erlaubten Absendern an (leer = deine verbundenen Postfächer), deren Absender
der Mail-Server per DKIM/DMARC bestätigt (ohne Bestätigung nur mit Code-Wort im Betreff); riskante Aktionen
(löschen, Befehle, senden an andere …) sind bei Mail-Aufträgen immer gesperrt. Mit Lumen-Server prüft der Server
die Postfächer rund um die Uhr, sonst der PC alle paar Minuten.

## 🩺 PC-Doktor
Karte **🩺 PC-Doktor → Untersuchen** (oder `/doktor`, im Chat „Warum ist mein PC so langsam?“, per Telegram `/doktor`).
Er prüft volle Laufwerke, Papierkorb, Caches (Vorschaubilder, Browser, pip, npm, Paket-Cache, System-Logs, Docker,
alte Snaps), große Dateien und Ordner, RAM- und CPU-Fresser, Temperaturen (auch GPU), Autostart-Programme, Startzeit,
Updates, fehlgeschlagene Dienste und den Akku – und gibt eine Note von 0–100.
**🧹 Empfohlenes aufräumen** löscht nur Sicheres (Papierkorb, Caches, ungenutzte Docker-Images) – keine Passwörter,
Logins oder eigenen Dateien. Einzelne Punkte: Programm beenden, Autostart ausschalten (umkehrbar). Admin-Aufräumen
(apt-Cache, Logs) öffnet das Passwort-Fenster des Systems – Lumen sieht dein Passwort nie.
Während der Untersuchung zeigt ein Balken, welcher Schritt läuft. Klappt ein einzelner Schritt nicht, läuft der Rest
trotzdem weiter (Hinweis „teilweise nicht geprüft“); geht gar nichts, steht der genaue Fehler in der Karte.

## 📋 Zwischenablage-Helfer
Text irgendwo markieren → **Strg+Alt+L** → Menü: Übersetzen, Verbessern, Erklären, Zusammenfassen, Antwort schreiben,
Formeller, Lockerer, Kürzer, Code verbessern. Direkt: **Strg+Alt+Ü** übersetzen, **Strg+Alt+K** verbessern.
Das Ergebnis liegt in der Zwischenablage (Strg+V) und kommt als Benachrichtigung; optional ersetzt Lumen den markierten
Text direkt. Unter X11 lauscht Lumen selbst (pynput); unter **Wayland** trägt der Knopf „Kürzel in GNOME einrichten“
die Kürzel ins System ein (andere Desktops: eigenes Kürzel mit `~/.lumen/lumen-clip.sh menu`). Ohne Kürzel: Knöpfe auf
der Karte oder `/clip übersetzen`. Braucht `xclip` bzw. `wl-clipboard` (installiert setup-linux.sh).

## ⌨️ /Befehle
Tippe `/` im Eingabefeld – eine Liste mit allen Befehlen erscheint (Pfeiltasten + Enter/Tab).
- **KI wechseln:** `/claude`, `/gpt`, `/deepseek`, `/gemini`, `/ollama`, `/lumen`, `/auto` – allein = ab jetzt diese KI;
  mit Frage dahinter (`/deepseek erklär mir Docker`) = nur für diese eine Antwort. `/ollama qwen2.5:7b` wechselt das
  lokale Modell, `/modell <name>` das Modell des aktuellen Anbieters.
- **Chat:** `/neu`, `/research <Frage>`, `/chats`, `/kopieren`, `/export [docx|pdf|md]`, `/stopp`
- **Schnell:** `/wetter [Ort]`, `/termine`, `/erinnerung morgen 9 Uhr Zahnarzt`, `/bildschirm`, `/server`,
  `/plugin <Beschreibung>`, `/buch [Idee]`, `/briefing`, `/mails`, `/mail <an wen: was>`, `/kurs`, `/trade`, `/alarm`, `/trading`
- **Öffnen:** `/studio`, `/labor`, `/apps`, `/lumenserver`, `/einstellungen`, `/bewerten`
- **Einstellungen:** `/stimme`, `/weckwort`, `/fluchen`, `/persona kumpel`, `/sprache en`, `/kosten`
- **Eigene Befehle:** `/befehl zocken = Öffne Discord und Steam und mach Musik an` → ab dann reicht `/zocken`
  (Text dahinter wird angehängt). Verwalten in den Einstellungen unter „Eigene /Befehle“. `/hilfe` zeigt alles.

**Telegram:** Schreib deinem Bot wie im Chat. Ohne Lumen-Server antwortet der PC (solange Lumen läuft), mit Lumen-Server
rund um die Uhr. Im /-Menü von Telegram: `/ki` und `/modelle` (KI per Knopf wählen), `/deepseek`, `/claude`, `/gpt`,
`/gemini`, `/ollama [Modell]`, `/lumen`, `/auto` (mit Frage dahinter nur für diese Antwort), `/modell`, `/research`,
`/wetter`, `/termine`, `/erinnerung`, `/erinnerungen`, `/aufgaben`, `/aufgabe`, `/notiz`, `/briefing`, `/status`,
`/kosten`, `/automation`, `/heartbeat`, `/faehigkeiten`, `/standort`, `/mails`, `/mail`, `/kurs`, `/depot`, `/trade`, `/alarm`, `/neu`, `/stopp`, `/befehl name = Text`, `/befehle`, `/hilfe` – plus deine eigenen Befehle.

## 🛰️ Lumen-Server – 24/7 auf deinem Server, mit Telegram
Ein zweites Lumen läuft rund um die Uhr auf deinem Linux-Server (ohne Bildschirm) und arbeitet mit Lumen auf dem PC zusammen.

**Einrichten (2 Minuten):**
1. Server in Lumen speichern und SSH-Key einrichten (Karte „Server“ oder im Chat: „Verbinde dich mit meinem Server …“).
2. Telegram verbinden (Apps → Telegram: Bot bei @BotFather anlegen, Token eintragen, „Chat-ID finden“).
3. Karte **🛰️ Lumen-Server → Einrichten** → Server wählen → **Installieren**. Lumen kopiert sich nach `~/lumen-server`,
   richtet eine Python-Umgebung und einen Dienst ein (systemd, startet automatisch; ohne systemd: Hintergrund + `@reboot`)
   und überträgt deine Einstellungen. Auf dem Handy kommt eine Test-Nachricht.

**Was er kann:**
- **☀️ Tages-Briefing** jeden Morgen per Telegram: Wetter (mit Jacke/Schirm-Tipp), Termine, Aufgaben, Erinnerungen,
  Server-Zustand und News zu deinen Themen – in Lumens Persönlichkeit. Uhrzeit, Tage und Inhalte einstellbar.
  (Ohne Server schickt Lumen das Briefing vom PC, wenn er an ist.)
- **💬 Chatten per Telegram:** einfach dem Bot schreiben – auch Sprachnachrichten (mit `faster-whisper` auf dem Server),
  Fotos und PDFs. Riskante Aktionen bestätigst du mit ✅/❌-Knöpfen. Befehle: `/briefing`, `/status`, `/erinnerungen`,
  `/neu`, `/stopp`. Nur deine Chat-ID darf mit dem Bot reden; Passwörter und Seed-Phrasen gehen nie über Telegram.
- **⏰ Erinnerungen:** „Erinner mich morgen um 9 an den Zahnarzt“ – kommt per Telegram, auch wenn der PC aus ist
  (täglich/wöchentlich/monatlich möglich). Am PC zusätzlich als Benachrichtigung.
- **⚠️ Server-Warnungen:** Festplatte über 90 %, RAM voll, Dauerlast, abgestürzte Docker-Container, ausgefallene Dienste.
- **🤝 Zusammenarbeit mit dem PC:** Aufgaben, Notizen, Gedächtnis, Erinnerungen und Plugins werden jede Minute abgeglichen.
  „Öffne Discord auf meinem PC“ per Telegram → der PC holt den Auftrag ab und antwortet per Telegram. Aus der Ferne
  führt der PC nichts Riskantes aus (Löschen, Befehle …) – das musst du am PC bestätigen.
- Web-Oberfläche des Servers per SSH-Tunnel: `ssh -L 8765:127.0.0.1:8765 dein-server` → http://127.0.0.1:8765

Alles läuft über deine SSH-Verbindung – auf dem Server muss kein Port geöffnet werden. Verwalten (Logs, Neustart,
Stoppen, Entfernen) im Fenster „Lumen-Server“.

## 🧩 Plugins – eigene Werkzeuge
Plugins sind kleine Python-Dateien in `~/.lumen/plugins/`, die Lumen neue Fähigkeiten geben. Am einfachsten:
„**Bau dir ein Werkzeug, das mir den Bitcoin-Kurs in Euro sagt**“ – Lumen schreibt den Code, zeigt ihn dir mit Hinweisen
(z. B. „greift aufs Internet zu“, „kann Dateien löschen“) und baut ihn erst nach deinem OK ein – auch wenn „Ohne
Nachfrage ausführen“ an ist. Lädt ein Plugin nicht, repariert Lumen es selbst. Verwalten (an/aus, Code ansehen,
löschen) unter **Apps → Eigene Werkzeuge**. Zwei Beispiele sind dabei (Würfeln, Webseiten-Check). Plugins werden auch
auf den Lumen-Server übertragen. Format:

```python
"""Kurze Beschreibung."""
def mein_werkzeug(args):
    return {"ergebnis": "…"}

TOOLS = [{"name": "mein_werkzeug", "description": "Was es tut.",
          "parameters": {"stadt": {"type": "string"}}, "required": [],
          "run": mein_werkzeug, "risky": False}]   # risky=True → Lumen fragt jedes Mal
```

## Apps verbinden
Oben **⧉ Apps** öffnen, App anklicken, der Anleitung folgen. Zugangsdaten bleiben in `~/.lumen/config.json` auf deinem PC.

| App | Was Lumen damit kann | Was du brauchst |
|---|---|---|
| **Krypto-Wallets** (Phantom, Solflare, MetaMask, Bitcoin) | Kontostand, Tokens, Wert in €, Transaktionen, Kurse, Zahlungs-QR-Codes | nur die **öffentliche** Adresse |
| **Spotify** | Was läuft, Songs/Playlists abspielen, Lautstärke, Warteschlange, Lieblingssongs, Mini-Player rechts | eigene App im Spotify-Developer-Dashboard (2 Min.), Premium für Steuerung |
| **Discord** | Nachrichten in deine Kanäle posten (fragt vorher) | Webhook-URL pro Kanal |
| **Telegram** | Dir Nachrichten und Dateien aufs Handy schicken | eigener Bot über @BotFather |
| **GitHub** | Repos, Issues, PRs, Actions-Status, Benachrichtigungen, Issues erstellen | Personal Access Token |
| **Home Assistant** | Licht, Steckdosen, Heizung, Sensoren, Szenen (Schlösser/Alarm fragen vorher) | Langlebiges Zugangstoken |
| **Steam** | Preise & Rabatte (ohne Key), dein Profil und deine Spielzeit (mit Key) | optional Web-API-Key |
| **Wetter** | Wetter & Vorhersage, oben rechts angezeigt | nur deinen Ort |
| **Kalender** | Deine Termine (Google, Outlook, iCloud, Nextcloud), nächster Termin oben rechts | iCal-Link |

### Krypto – so bleibt dein Geld sicher
- Lumen bekommt **nur öffentliche Adressen** und kann damit **nur lesen**.
- **Niemals Seed-Phrase oder privaten Schlüssel** eingeben. Lumen erkennt so etwas und **blockiert die Nachricht**,
  bevor sie die KI erreicht – auch im Wallet-Feld.
- Zahlungen: „Erstell mir einen QR-Code über 0,5 SOL an …“ → QR-Code mit Phantom am Handy scannen, Empfänger und
  Betrag prüfen, **in Phantom bestätigen**. Lumen kann selbst nichts senden.
- Lumen gibt keine Kauf-/Verkaufsempfehlungen. Token ohne Wert in deiner Wallet sind oft Spam-Airdrops – nicht anklicken.

## KI-Anbieter
In den Einstellungen wählbar, jederzeit wechselbar:
- **Claude (Anthropic)** – empfohlen, kann alles inkl. Bildschirm sehen
- **OpenAI**, **Gemini** (Key kostenlos unter aistudio.google.com), **DeepSeek** (günstig, ohne Bilder)
- **Ollama (lokal)** – kostenlos, offline, kein Key. Installieren:
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ollama pull qwen2.5vl:7b     # kann auch Bilder/Bildschirm sehen
  ollama pull llama3.1:8b      # schneller Allrounder
  ```
  In den Einstellungen „Ollama (lokal)“ wählen, Modell aus der Liste nehmen. Unter „PC-Werkzeuge“ bekommen kleine
  Modelle nur die wichtigsten Werkzeuge (sonst verlieren sie den Überblick); große Modelle können „Alle“ nutzen.

## Docker-Zentrale
Rechts die Karte **Docker**: alle Container auf diesem PC und deinen SSH-Servern mit Status, CPU und RAM.
Knöpfe für Logs, Start, Stopp, Neustart und **Update** (lädt das neue Image und startet neu – bei Docker Compose
automatisch richtig). Stopp/Neustart/Update fragen mit „Sicher?“ nach. Im Log-Fenster: „Lumen fragen“ erklärt Fehler.
Im Chat: „Welche Container laufen auf dem homeserver?“, „Update Nextcloud“, „Warum stürzt minecraft ab?“

## Chats
**☰ Chats** oben öffnet alle bisherigen Unterhaltungen – mit **Suche** (auch im Text), Anheften ★, Umbenennen ✎ und
Löschen. „Neuer Chat“ startet frisch; der alte bleibt gespeichert (`~/.lumen/chats/`).

## Verbrauch & Kosten
Die Karte **Verbrauch** zeigt geschätzte Kosten heute und diesen Monat, die letzten 30 Tage und die teuersten Modelle.
Unter jeder Antwort steht, was sie gekostet hat. In den Einstellungen → Kosten: **Monatsbudget** (Warnung bei 80 %,
optional automatischer Stopp) und eigene Preise, falls sich die Preise der Anbieter ändern. Ollama ist kostenlos.

## Persönlichkeit
Einstellungen → Persönlichkeit: **Name** (z. B. „Nova“ – das Weckwort wird dann „Hey Nova“), **Charakter**
(Freundlich, Butler mit Humor, Kumpel, Frech, Kurz & knapp, Ruhig – oder ganz eigene Beschreibung),
**Akzentfarbe** und **Stimme** (9 deutsche Piper-Stimmen, per Knopf herunterladen und probehören).

## Sprechen
- **„Hey Lumen“**: Knopf oben „Hey Lumen“ einschalten. Dann einfach sagen: *„Hey Lumen, starte Steam“*
  oder *„Lumen“* … Piep … *„mach die Musik lauter“*. Bleibt nach Neustart an.
- **Push-to-Talk**: Mikrofon-Knopf neben dem Eingabefeld oder **Strg+M**, dann sprechen.
- Lumen antwortet mit Stimme (Piper „Thorsten“, sonst espeak-ng). Abschaltbar in den Einstellungen.
- Spracherkennung läuft **komplett lokal** (Whisper). Kein Ton geht ins Internet, nur der erkannte Text an deine KI.
- Weckwort und Genauigkeit (tiny / base / small) kannst du in den Einstellungen ändern.

## Bildschirm, Maus & Tastatur
Sag z. B. *„Was ist auf meinem Bildschirm?“*, *„Öffne Firefox und such nach Wetter Berlin“*,
*„Schreib in Discord an Max: bin in 5 Minuten da“*. Lumen macht Screenshots, klickt und tippt
und kontrolliert danach per Screenshot. Die Screenshots siehst du klein im Chat (anklicken = groß).

- Beim ersten Klick/Tippen in einem Auftrag fragt Lumen einmal nach Erlaubnis.
- **Braucht Claude oder OpenAI** – DeepSeek kann keine Bilder sehen.
- **X11** (z. B. „Ubuntu auf Xorg“): funktioniert am besten (xdotool).
- **Wayland**: Screenshots über grim / gnome-screenshot / spectacle, Steuerung über **ydotool ≥ 1.0**
  mit laufendem Dienst (`sudo systemctl enable --now ydotool`). Ältere ydotool-Versionen (z. B. Ubuntu 22.04)
  funktionieren nicht – dann beim Login die Xorg-Sitzung wählen.

## Server per SSH – einfach im Chat
Sag einfach: *„Verbinde dich mit meinem Server 192.168.1.50, Benutzer root“* (oder klick rechts auf „+ Server hinzufügen“).
Lumen speichert den Server, testet die Verbindung und richtet bei Bedarf **automatisch einen SSH-Key** ein:
In der App erscheint dann ein Passwortfeld. Das Passwort wird nur einmal lokal benutzt, um den Key
auf dem Server zu hinterlegen – es geht **nicht an die KI** und wird nirgends gespeichert. Danach geht alles ohne Passwort.

Dann zum Beispiel:
- *„Wie geht es meinem homeserver?“* → Uptime, Last, RAM, Speicher, Docker-Container, Fehler, Updates
- *„Welche Container laufen?“* · *„Zeig die letzten nginx-Fehler“* · *„Starte nginx neu“*
- *„Lad backup.zip aus Downloads auf den Server nach /root“* · *„Hol mir /var/log/syslog“*
- *„Öffne ein Terminal zum homeserver“* (oder Knopf „Terminal“ rechts)
- *„Benenn den Server um“* / *„Entferne den Server“*

Rechts siehst du alle Server mit Live-Status (grün = online, gelb = Key fehlt, rot = nicht erreichbar).
Lesende Befehle laufen sofort, alles Ändernde fragt vorher nach. Server lassen sich weiterhin auch in den Einstellungen eintragen.

## Gedächtnis
Erzähl Lumen etwas über dich („Ich spiele am liebsten Minecraft“, „Mein Bruder heißt Tim“) – Lumen merkt
es sich dauerhaft. Rechts unter „Lumen weiß über dich“ siehst und löschst du alles. Der letzte Chat bleibt
nach einem Neustart erhalten („Neuer Chat“ leert ihn).

## Internet & Deep Research
- Lumen **sucht selbst im Internet** und liest die Seiten (News, Preise, Versionen, Wetter, Fakten). Am Ende stehen die Quellen als Links.
  Ohne Key über DuckDuckGo/Bing. Zuverlässiger mit einem **kostenlosen Brave-Search-Key** (Einstellungen → Websuche)
  oder deiner eigenen **SearXNG**-Instanz.
- **Deep Research**: Knopf „Research“ neben dem Eingabefeld anklicken, dann Frage stellen. Lumen zerlegt die Frage,
  sucht mit vielen Suchanfragen (auch englisch), liest 8–15 Quellen, prüft Widersprüche und schreibt einen Bericht
  mit Kurzfassung, Tabellen, Quellenangaben [1] und Quellenliste. Der Bericht wird automatisch gespeichert unter
  **Dokumente/Lumen-Recherchen/** (Markdown). Dauert je nach Thema 1–5 Minuten und kostet mehr API-Guthaben als eine normale Frage.
- Lokale Netzwerkadressen (Router, 192.168.x.x …) lädt die Websuche aus Sicherheitsgründen nicht – dafür gibt es SSH und das Terminal.

## Dateien im Chat
Dateien **ins Fenster ziehen**, mit **Strg+V einfügen** (z. B. Screenshots) oder über die **Büroklammer** auswählen (max. 50 MB).
- **Bilder** sieht Lumen direkt (Claude/OpenAI) – „Was ist das für ein Fehler?“
- **PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), LibreOffice (.odt)** → Lumen liest den Text. Gescannte PDFs liest Claude als Dokument.
- **Text, Code, Logs, CSV, JSON …** → „Finde den Fehler in diesem Log“
- Alles andere: Lumen kennt den Speicherort und kann mit seinen Werkzeugen damit arbeiten.
Hochgeladene Dateien liegen in `~/.lumen/uploads` und werden nach 14 Tagen automatisch gelöscht.
DeepSeek kann keine Bilder sehen, Texte aus Dateien aber schon.

## Dateien & Dokumente erstellen
Einfach sagen: „Mach mir eine Einkaufsliste als Word-Datei“, „Schreib eine Bewerbung als PDF“, „Erstell einen Lernzettel
über den Zweiten Weltkrieg als Word und PDF“. Lumen erstellt **Word (.docx), PDF, E-Book (.epub), HTML, Markdown oder Text**
mit Überschriften, Listen und Formatierung – standardmäßig in `~/Dokumente/Lumen/`. Lesen geht auch: PDF, Word, Excel,
PowerPoint, EPUB.

**Eigenes Lumen-Modell (Ollama) konnte keine Dateien erstellen?** Behoben: Die lokale KI hat jetzt alle Datei-Werkzeuge
(erstellen, schreiben, verschieben, löschen, Dokumente). Kleine Modelle schreiben Werkzeug-Aufrufe manchmal als Text – Lumen
erkennt das und führt sie trotzdem aus. Behauptet das Modell „erledigt“, ohne etwas getan zu haben, erinnert Lumen es daran
(und fragt im Auto-Modus sonst die Cloud). Tipp: Für zuverlässige PC-Steuerung lokal mindestens ein 7B-Modell (z. B. Qwen 2.5 7B).

## 📚 Studio – Wissen, Lernen & Schreiben
Oben **📚 Studio**.

**📖 Wissen & Lernen:** PDFs, Bücher (EPUB), Skripte, Word-Dateien oder Webseiten reinziehen → Lumen liest sie und legt sie in
deiner Bibliothek ab (lokal in `~/.lumen/wissen/`). Danach:
- **💬 Fragen stellen** – „Was steht in meinem Bio-Skript über Photosynthese?“ → Antwort mit Seitenangabe.
- **📝 Zusammenfassen** – auch für dicke Bücher (wird in Teilen gelesen), als Word/PDF speicherbar.
- **🃏 Karteikarten** – zum Umdrehen, „Gewusst / Nochmal“, Export als Word, PDF oder **Anki-CSV**.
- **❓ Quiz** – 10 Fragen mit Erklärung und Fundstelle, Punktestand am Ende.
- **🧠 Lumen lernt daraus** – erzeugt Übungsgespräche zum Inhalt → beim nächsten Training im KI-Labor lernt die eigene KI den Stoff fest.

Funktioniert mit Cloud-KI (beste Qualität, Kosten werden vorher angezeigt, meist ein paar Cent) oder lokal kostenlos.

**✍️ Schreiben:** Idee, Genre, Kapitel, Länge, Stil, Zielgruppe angeben → Lumen plant Handlung und Figuren und schreibt dann
Kapitel für Kapitel im Hintergrund (mit Fortschritt). Ergebnis als **Word, PDF und E-Book** in `~/Dokumente/Lumen/Bücher/`.
Einzelne Kapitel lassen sich mit Wunsch neu schreiben („mehr Dialoge“, „spannenderes Ende“). Geht auch im Chat:
„Schreib mir ein Fantasy-Buch über …“. Ein Buch mit 10 Kapiteln à 2.500 Wörtern kostet mit Claude etwa 0,70–1 $.

## Sicherheit & OSINT
Rechts gibt es die Karte **Sicherheit** mit Schnellknöpfen – oder einfach im Chat fragen.

**„Ist diese Mail echt?“** – Mail-Quelltext einfügen (in Thunderbird: Strg+U, in Gmail: ⋮ → „Original anzeigen“)
oder die .eml-Datei reinziehen. Lumen prüft SPF/DKIM/DMARC, gefälschte Absender, täuschende Links, Domain-Alter
und gefährliche Anhänge und gibt ein klares Urteil.

**Links:** Kurzlinks aufklappen (ohne die Seite zu öffnen), Phishing-Check (Doppelgänger wie paypa1, rnicrosoft,
kyrillische Buchstaben, Tippfehler-Domains, neue Domains), VirusTotal-Scan.

**Domains & Server:** Whois, DNS mit SPF/DMARC-Bewertung, Subdomains (crt.sh), SSL-Zertifikat, Technik einer Webseite
und Sicherheits-Header, Wayback Machine, IP-Infos, Shodan, Ping/Traceroute.
**Port-Scan** nur für deine eigenen Server (in Lumen gespeichert), Geräte im Heimnetz und deine eigene öffentliche IP.
„Wie sicher ist mein homeserver?“ kombiniert alles und sagt dir, was du verbessern solltest.

**Bilder & Dateien:** Metadaten lesen (Kamera, Aufnahmezeit, **GPS-Ort**, Autor/Firma in PDF und Office) und eine
Kopie ohne Metadaten erstellen – wichtig vor dem Posten. Bild-Prüfung mit Hashes und Error Level Analysis
(Hinweise auf Bearbeitung). Bild-Rückwärtssuche öffnet Google Lens, TinEye und Bing.

**Deine eigene Sicherheit:** Datenleck-Check deiner E-Mails, anonymer Passwort-Check (das Passwort verlässt deinen
PC nie – nur ein Teil seines Hash-Werts), Benutzernamen-Check (auf welchen Seiten dein Name vergeben ist, um alte
Konten zu finden). Diese Checks funktionieren **nur mit den E-Mails und Benutzernamen, die du in den Einstellungen
als deine eigenen einträgst**.

Optionale kostenlose Keys (Einstellungen → Sicherheit): **VirusTotal** (virustotal.com → Profil → API Key),
**Shodan** (sonst kostenlose InternetDB), **Have I Been Pwned** (kostenpflichtig, sonst kostenlos über XposedOrNot).

Bewusst **nicht** enthalten: Personensuche oder Profile über andere Menschen. Lumen lehnt so etwas ab.

## Was Lumen sonst noch kann
- Ordner ansehen, Dateien suchen/lesen/schreiben/verschieben/löschen (Lumen-Papierkorb)
- Steam- und Epic-Spiele finden und starten (rechts in der App mit „Spielen“-Knopf)
- Jedes installierte Programm öffnen, laufende Programme sehen und schließen
- Musik/Lautstärke (playerctl/pactl), PC sperren, Energiesparen, Neustart, Herunterfahren
- Terminal-Befehle, Systeminfo, Aufgaben und Notizen

## API-Keys
- Anthropic (Claude): https://console.anthropic.com → API Keys – empfohlen, kann auch Bildschirm sehen
- OpenAI: https://platform.openai.com/api-keys
- DeepSeek: https://platform.deepseek.com/api_keys – günstig, aber ohne Bildschirm-Sehen

Gespeichert nur lokal in `~/.lumen/config.json`.

## Sicherheit
- Server nur auf `127.0.0.1`, jede Anfrage braucht ein Token, das bei jedem Start neu erzeugt wird.
- Riskante Aktionen fragen vorher nach („Erlauben / Ablehnen“): Befehle mit Änderungen, Löschen, Verschieben,
  Überschreiben, Programme beenden, Neustart/Herunterfahren, Maus/Tastatur, SSH-Befehle mit Änderungen.
- „Ohne Nachfrage ausführen“ in den Einstellungen schaltet das ab – nur, wenn du dir sicher bist.
- Lumen hat die Rechte deines Benutzerkontos. Nicht als root starten. `sudo` geht nur, wenn es kein Passwort verlangt.
- Screenshots gehen an deinen KI-Anbieter. Lass keine Passwörter offen auf dem Bildschirm, wenn Lumen hinschaut.
