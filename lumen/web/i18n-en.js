/* Lumen – English interface. Translates the German UI on the fly (text, placeholders, tooltips, dialogs).
   Format: German ⟶ English. {} = dynamic part (in order); {1} {2} … to reorder. AI answers are never touched. */
(() => {
const RAW = String.raw`
Lumen Assistent ⟶ Lumen Assistant
Assistent ⟶ Assistant
Heute ⟶ Today
Bereit ⟶ Ready
Apps ⟶ Apps
Chats ⟶ Chats
Studio ⟶ Studio
Neu ⟶ New
＋ Neu ⟶ ＋ New
+ Neu ⟶ + New
Neuer Chat ⟶ New chat
KI-Labor ⟶ AI Lab
🧪 KI-Labor ⟶ 🧪 AI Lab
Einstellungen ⟶ Settings
Studio: Wissen, Lernen & Schreiben ⟶ Studio: knowledge, learning & writing
Sag „Hey Lumen“ und dann deinen Befehl ⟶ Say “Hey Lumen” and then your command
Guten Abend. ⟶ Good evening.
Was steht ⟶ What's
an? ⟶ on?
Was gibt es heute Neues in der Tech-Welt? ⟶ What's new in tech today?
Recherchiere: beste Linux-Distro fürs Gaming 2026 ⟶ Research: best Linux distro for gaming 2026
Welche Spiele habe ich? ⟶ Which games do I have?
Erinnere mich: Mama anrufen um 18 Uhr ⟶ Remind me: call mom at 6 pm
Öffne Discord ⟶ Open Discord
Was liegt in meinem Downloads-Ordner? ⟶ What's in my Downloads folder?
Was ist gerade auf meinem Bildschirm? ⟶ What's on my screen right now?
Wie geht es meinem Server? ⟶ How is my server doing?
Mach die Musik lauter ⟶ Turn the music up
Dateien hier ablegen ⟶ Drop files here
Research ⟶ Research
Enter senden · Dateien reinziehen oder einfügen · Strg+M sprechen · „Hey Lumen“ freihändig ⟶ Enter to send · drag in or paste files · Ctrl+M to talk · “Hey Lumen” hands-free
Chats durchsuchen ⟶ Search chats
Datei anhängen ⟶ Attach file
Datei anhängen (oder reinziehen / einfügen) ⟶ Attach file (or drag in / paste)
Frag Lumen etwas oder gib eine Aufgabe … ⟶ Ask Lumen something or give it a task …
Frag {} etwas oder gib eine Aufgabe … ⟶ Ask {} something or give it a task …
Was soll {} gründlich recherchieren? ⟶ What should {} research in depth?
Deep Research: gründliche Recherche mit vielen Quellen und Bericht ⟶ Deep Research: thorough research with many sources and a report
Sprechen (Strg+M) ⟶ Talk (Ctrl+M)
Senden ⟶ Send
Stoppen ⟶ Stop
Zurück ⟶ Back
Abspielen/Pause ⟶ Play/Pause
Weiter ⟶ Next
Zu Lieblingssongs ⟶ Add to liked songs
Letzte 30 Tage ⟶ Last 30 days
Gerät ⟶ Device
Neue Aufgabe ⟶ New task
Kurze Notiz ⟶ Quick note
Call & Meeting ⟶ Call & Meeting
Aus ⟶ Off
Call-Modus starten ⟶ Start call mode
– Lumen sagt im Call kurz Hallo. ⟶ – Lumen briefly says hello in the call.
In Discord: Einstellungen → Sprache & Video → Eingabegerät: ⟶ In Discord: Settings → Voice & Video → Input device:
Lumen-Mikrofon ⟶ Lumen microphone
(nur einmal). ⟶ (only once).
Alle können fragen: ⟶ Everyone can ask:
„Hey Lumen, …“ ⟶ “Hey Lumen, …”
🎧 Call-Modus starten ⟶ 🎧 Start call mode
🎙 Meeting im Raum ⟶ 🎙 In-room meeting
Alle Teilnehmer wissen Bescheid und sind einverstanden, dass mitgeschrieben wird. ⟶ All participants know and agree that notes are being taken.
📝 Protokoll starten ⟶ 📝 Start notes
Lumen-Mikrofon entfernen ⟶ Remove Lumen microphone
Wallet ⟶ Wallet
Aktualisieren ⟶ Refresh
Nur lesen · Lumen kann nichts senden ⟶ Read-only · Lumen can't send anything
Verbrauch ⟶ Usage
Diesen Monat ⟶ This month
Schnellstart ⟶ Quick launch
Dateien ⟶ Files
Server ⟶ Servers
Noch keine Server. Sag z. B. „Verbinde dich mit meinem Server 192.168.1.50, Benutzer root“. ⟶ No servers yet. Say e.g. “Connect to my server 192.168.1.50, user root”.
+ Server hinzufügen ⟶ + Add server
Sicherheit ⟶ Security
Link prüfen ⟶ Check link
Mail prüfen ⟶ Check email
Server-Check ⟶ Server check
Datenlecks ⟶ Data breaches
Passwort prüfen ⟶ Check password
Metadaten ⟶ Metadata
Bild prüfen ⟶ Check image
Spiele ⟶ Games
Suche nach Steam- und Epic-Spielen … ⟶ Looking for Steam and Epic games …
Aufgaben ⟶ Tasks
Notizen ⟶ Notes
Lumen weiß über dich ⟶ What Lumen knows about you
Schließen ⟶ Close
Lumens eigene KI: läuft auf deinem PC, kostenlos und offline. Braucht ⟶ Lumen's own AI: runs on your PC, free and offline. Requires
📚 Studio ⟶ 📚 Studio
📖 Wissen & Lernen ⟶ 📖 Knowledge & Learning
✍️ Schreiben ⟶ ✍️ Writing
⚡ Schnell bewerten ⟶ ⚡ Quick rating
Fertig ⟶ Done
Apps verbinden ⟶ Connect apps
Deine Keys bleiben auf diesem PC (Ordner ⟶ Your keys stay on this PC (folder
in deinem Benutzerordner) und gehen nur an den gewählten Anbieter. ⟶ in your home folder) and are only sent to the provider you choose.
Sprache · Language ⟶ Language · Sprache
Anbieter ⟶ Provider
Ollama (lokal) ⟶ Ollama (local)
Auto (lokal + Cloud) ⟶ Auto (local + cloud)
Einfaches beantwortet dein lokales Modell kostenlos, Schweres (Recherche, Code, Dateien, Server …) die Cloud. Ist die lokale Antwort zu schwach, fragt Lumen automatisch die Cloud. Einstellen im ⟶ Your local model answers simple things for free, the cloud handles hard things (research, code, files, servers …). If the local answer is too weak, Lumen automatically asks the cloud. Configure in the
Anthropic API-Key ⟶ Anthropic API key
Claude-Modell ⟶ Claude model
OpenAI API-Key ⟶ OpenAI API key
OpenAI-Modell ⟶ OpenAI model
DeepSeek API-Key ⟶ DeepSeek API key
DeepSeek-Modell ⟶ DeepSeek model
Gemini API-Key ⟶ Gemini API key
Gemini-Modell ⟶ Gemini model
Key kostenlos unter aistudio.google.com → „Get API key“. Gemini kann auch Bilder und deinen Bildschirm sehen. ⟶ Free key at aistudio.google.com → “Get API key”. Gemini can also see images and your screen.
Ollama-Adresse ⟶ Ollama address
Lokales Modell ⟶ Local model
Neu laden ⟶ Reload
Installierte Modelle ⟶ Installed models
Installierte Modelle … ⟶ Installed models …
PC-Werkzeuge für die lokale KI ⟶ PC tools for the local AI
Wichtige (empfohlen für kleine Modelle) ⟶ Essential (recommended for small models)
Alle (für große Modelle) ⟶ All (for large models)
Keine (nur Chat) ⟶ None (chat only)
Kontextlänge in Tokens (mehr = besseres Gedächtnis, braucht mehr RAM) ⟶ Context length in tokens (more = better memory, needs more RAM)
Kostenlos, offline, ohne Key. Installieren: ⟶ Free, offline, no key. Install:
, dann z. B. ⟶ , then e.g.
(sieht auch Bilder) oder ⟶ (can also see images) or
. Mit 8 GB Grafikspeicher laufen 7–8B-Modelle flüssig. ⟶ . With 8 GB of VRAM, 7–8B models run smoothly.
z. B. qwen2.5vl:7b ⟶ e.g. qwen2.5vl:7b
Dein Name (optional) ⟶ Your name (optional)
Persönlichkeit ⟶ Personality
Name des Assistenten ⟶ Assistant name
Charakter ⟶ Character
Kraftausdrücke erlaubt ⟶ Swearing allowed
Lumen darf fluchen und derb reden („Scheiße“, „verdammt“ …) – aber keine Hetze und niemanden ernsthaft beleidigen. ⟶ Lumen may swear and talk rough (“shit”, “damn” …) – but no hate speech and no seriously insulting anyone.
Eigene Wünsche an den Charakter (optional) ⟶ Your own wishes for the character (optional)
z. B. Nenn mich Chef. Mach ab und zu Gaming-Vergleiche. ⟶ e.g. Call me boss. Make gaming comparisons now and then.
Akzentfarbe ⟶ Accent color
Standard ⟶ Default
Eigene Farbe ⟶ Custom color
Stimme ⟶ Voice
Laden ⟶ Download
Probehören ⟶ Preview
Kosten ⟶ Costs
Monatsbudget in US-Dollar (0 = kein Budget) ⟶ Monthly budget in US dollars (0 = no budget)
Bei erreichtem Budget anhalten ⟶ Stop when the budget is reached
Sonst nur Warnung. Lokale Modelle (Ollama) laufen immer weiter. ⟶ Otherwise just a warning. Local models (Ollama) always keep running.
Eigene Preise · eine Zeile pro Modell: name = Eingabe, Ausgabe (US-Dollar pro 1 Mio. Tokens) ⟶ Custom prices · one line per model: name = input, output (US dollars per 1M tokens)
Kosten sind Schätzungen aus der Token-Anzahl und einer Preisliste. Den genauen Betrag zeigt dein Anbieter. ⟶ Costs are estimates from token counts and a price list. Your provider shows the exact amount.
Eigene Programme · eine Zeile pro Programm: name = Pfad ⟶ Custom programs · one line per program: name = path
SSH-Server · eine Zeile pro Server: name = user@host:port ⟶ SSH servers · one line per server: name = user@host:port
Lumen nutzt deine SSH-Keys (ohne Passwortabfrage). Einmalig einrichten mit ⟶ Lumen uses your SSH keys (no password prompt). One-time setup with
Websuche ⟶ Web search
Lumen sucht ohne Key über DuckDuckGo/Bing. Zuverlässiger mit einem kostenlosen ⟶ Without a key Lumen searches via DuckDuckGo/Bing. More reliable with a free
-Key (api-dashboard.search.brave.com) oder deiner eigenen SearXNG-Instanz. ⟶ key (api-dashboard.search.brave.com) or your own SearXNG instance.
Brave Search API-Key (optional) ⟶ Brave Search API key (optional)
SearXNG-Adresse (optional) ⟶ SearXNG address (optional)
Sicherheit & eigene Konten ⟶ Security & your own accounts
VirusTotal API-Key (kostenlos, für Link-/Datei-Scans) ⟶ VirusTotal API key (free, for link/file scans)
Shodan API-Key (optional – ohne Key: kostenlose InternetDB) ⟶ Shodan API key (optional – without key: free InternetDB)
Have I Been Pwned Key (optional – ohne Key: XposedOrNot) ⟶ Have I Been Pwned key (optional – without key: XposedOrNot)
Meine E-Mail-Adressen (für den Datenleck-Check, durch Komma getrennt) ⟶ My email addresses (for the breach check, comma-separated)
Meine Benutzernamen (für den Konten-Check, durch Komma getrennt) ⟶ My usernames (for the account check, comma-separated)
Datenleck- und Konten-Check funktionieren nur mit den Adressen und Namen, die du hier als deine eigenen einträgst. ⟶ The breach and account checks only work with the addresses and names you enter here as your own.
ich@gmx.de, gaming@gmail.com ⟶ me@example.com, gaming@gmail.com
Weckwort ⟶ Wake word
Spracherkennung ⟶ Speech recognition
Schnell (tiny) ⟶ Fast (tiny)
Ausgewogen (base) ⟶ Balanced (base)
Genau (small, braucht mehr CPU) ⟶ Accurate (small, needs more CPU)
Antworten vorlesen ⟶ Read answers aloud
Wenn du per Stimme fragst, antwortet Lumen auch mit Stimme. ⟶ When you ask by voice, Lumen also answers by voice.
Prüfe, was auf diesem PC verfügbar ist … ⟶ Checking what's available on this PC …
Ohne Nachfrage ausführen ⟶ Run without asking
Lumen führt dann auch Befehle, Löschen, Beenden und Herunterfahren aus, ohne dich zu fragen. Nur einschalten, wenn du dir sicher bist. ⟶ Lumen will then run commands, delete, close and shut down without asking you. Only turn on if you're sure.
Key löschen: einfach ⟶ Delete a key: just enter
eintragen und speichern. ⟶ and save.
Abbrechen ⟶ Cancel
Speichern ⟶ Save
Gespeichert ⟶ Saved
Server antwortet nicht ( ⟶ Server not responding (
Speichern fehlgeschlagen ⟶ Saving failed
Gute Antwort – davon soll Lumen lernen ⟶ Good answer – Lumen should learn from this
Schlechte Antwort – nicht lernen ⟶ Bad answer – don't learn
Verbessern – so hätte die Antwort sein sollen ⟶ Improve – this is what the answer should have been
Zu dieser Antwort gibt es keine Frage. ⟶ There's no question for this answer.
Bessere Antwort ⟶ Better answer
So hätte {} antworten sollen – Lumen lernt das beim nächsten Training: ⟶ This is how {} should have answered – Lumen learns it at the next training:
Merken ⟶ Remember
Keine Aufgaben. Sag Lumen, was ansteht. ⟶ No tasks. Tell Lumen what's coming up.
Als offen markieren ⟶ Mark as open
Erledigt ⟶ Done
Löschen ⟶ Delete
Noch nichts geplant. ⟶ Nothing planned yet.
Alles erledigt. Stark! ⟶ All done. Nice!
{} offen · {} erledigt ⟶ {} open · {} done
Noch keine Notizen. ⟶ No notes yet.
Notiz löschen ⟶ Delete note
Erzähl Lumen etwas über dich, z. B. „Ich spiele am liebsten Minecraft“. Lumen merkt es sich. ⟶ Tell Lumen something about yourself, e.g. “My favorite game is Minecraft”. Lumen will remember it.
Vergessen ⟶ Forget
{} wird geöffnet ⟶ Opening {}
Keine Steam- oder Epic-Spiele gefunden. Frag Lumen nach anderen Spielen. ⟶ No Steam or Epic games found. Ask Lumen about other games.
Spielen ⟶ Play
{} starten ⟶ Launch {}
{} startet ⟶ {} is starting
Spiele konnten nicht geladen werden. ⟶ Couldn't load games.
Denkt nach … ⟶ Thinking …
Verbinde … ⟶ Connecting …
Bereit · Auto (lokal + Cloud) ⟶ Ready · Auto (local + cloud)
Bereit · lokal · {} ⟶ Ready · local · {}
Bereit · {} ⟶ Ready · {}
Kein API-Key ⟶ No API key
{} entfernen ⟶ Remove {}
{} ist größer als 50 MB. ⟶ {} is larger than 50 MB.
Upload fehlgeschlagen ⟶ Upload failed
Warte, bis die Dateien hochgeladen sind. ⟶ Wait until the files are uploaded.
Plant die Recherche … ⟶ Planning the research …
Gelesen: {} ⟶ Read: {}
Recherchiert … {} Quellen gelesen ⟶ Researching … {} sources read
Sucht Quellen … ⟶ Looking for sources …
Wartet auf dich ⟶ Waiting for you
Erlauben? · {} ⟶ Allow? · {}
Passwort ⟶ Password
Key einrichten ⟶ Set up key
Erlauben ⟶ Allow
Ablehnen ⟶ Deny
Passwort gesendet · {} ⟶ Password sent · {}
Erlaubt · {} ⟶ Allowed · {}
Abgelehnt · {} ⟶ Denied · {}
Arbeitet … ⟶ Working …
Recherchiert · {} Quellen ⟶ Researched · {} sources
Deep Research · {} Quellen ⟶ Deep Research · {} sources
Bericht öffnen ⟶ Open report
Ordner zeigen ⟶ Show folder
Text kopieren ⟶ Copy text
Kopiert ⟶ Copied
Kopieren nicht möglich ⟶ Copying not possible
Protokoll gespeichert in Dokumente/Lumen-Protokolle ⟶ Notes saved in Documents/Lumen-Protokolle
Bericht gespeichert in Dokumente/Lumen-Recherchen ⟶ Report saved in Documents/Lumen-Recherchen
Lumen-Server nicht erreichbar. Läuft lumen.py noch? ⟶ Can't reach the Lumen server. Is lumen.py still running?
•••• (aus Sicherheitsgründen entfernt) ⟶ •••• (removed for security reasons)
🔒 Gestoppt. ⟶ 🔒 Stopped.
Suche Modelle … ⟶ Looking for models …
Noch keine Modelle installiert ⟶ No models installed yet
Ollama nicht erreichbar ⟶ Ollama not reachable
{} (lädt …) ⟶ {} (downloading …)
{} – nicht geladen ⟶ {} – not downloaded
Stimme wird geladen (ca. 20–100 MB) … ⟶ Downloading voice (about 20–100 MB) …
bereit ⟶ ready
Sprachausgabe ⟶ Speech output
Maus/Tastatur ⟶ Mouse/keyboard
Hinweis ⟶ Note
Konnte Fähigkeiten nicht prüfen. ⟶ Couldn't check capabilities.
Hört zu ⟶ Listening
Ich höre … ⟶ I'm listening …
Versteht … ⟶ Understanding …
Spricht … ⟶ Speaking …
Mikro-Fehler ⟶ Mic error
Lumen arbeitet noch … ⟶ Lumen is still working …
Gehört (ohne Weckwort): {} ⟶ Heard (no wake word): {}
Sag „Hey {}“ und dann deinen Befehl ⟶ Say “Hey {}” and then your command
Weckwort aus ⟶ Wake word off
Sprich jetzt … ⟶ Speak now …
Key fehlt ⟶ Key missing
nicht erreichbar ⟶ not reachable
Fingerabdruck geändert ⟶ Fingerprint changed
Fehler ⟶ Error
Fehler. ⟶ Error.
Einrichten ⟶ Set up
Richte den SSH-Key für {} ein. ⟶ Set up the SSH key for {}.
Verbinde dich mit meinem Server: IP oder Domain , Benutzer ⟶ Connect to my server: IP or domain , user
IP oder Domain ⟶ IP or domain
{} Min. ⟶ {} min
{} Std. ⟶ {} h
gerade ⟶ just now
Nichts gefunden. ⟶ Nothing found.
Noch keine gespeicherten Chats. ⟶ No saved chats yet.
{} · {} Nachrichten ⟶ {} · {} messages
Lösen ⟶ Unpin
Anheften ⟶ Pin
Umbenennen ⟶ Rename
Sicher? ⟶ Sure?
{} % von {} Monatsbudget ⟶ {} % of {} monthly budget
Monatsbudget erreicht! ⟶ Monthly budget reached!
Preis unbekannt für: {} ⟶ Price unknown for: {}
Lade Container … ⟶ Loading containers …
Keine Container. ⟶ No containers.
Neustart ⟶ Restart
Stopp ⟶ Stop
Fortsetzen ⟶ Resume
Lumen fragen ⟶ Ask Lumen
Lade … ⟶ Loading …
Logs · {} ⟶ Logs · {}
(keine Logs) ⟶ (no logs)
Schau dir die Logs von Container {} ({}) an: Gibt es Fehler und wie behebe ich sie? ⟶ Look at the logs of container {} ({}): are there errors and how do I fix them?
Zugangsdaten bleiben nur auf deinem PC. Lumen bekommt nur die Werkzeuge der Apps, die du verbindest. ⟶ Credentials stay on your PC only. Lumen only gets the tools of the apps you connect.
verbunden ⟶ connected
nicht verbunden ⟶ not connected
← Alle Apps ⟶ ← All apps
verbunden · {} ⟶ connected · {}
🔒 Niemals Seed-Phrase oder privaten Schlüssel eingeben ⟶ 🔒 Never enter a seed phrase or private key
– nicht hier, nicht im Chat, nirgendwo. Kein echter Support fragt danach. Lumen braucht nur deine ⟶ – not here, not in the chat, nowhere. No real support will ever ask for it. Lumen only needs your
öffentliche Adresse ⟶ public address
Einen Moment … ⟶ One moment …
Erledigt. ⟶ Done.
Speichern & testen ⟶ Save & test
Neu anmelden ⟶ Sign in again
Mit Spotify anmelden ⟶ Sign in with Spotify
Browser geöffnet – dort anmelden, dann hier 'Testen' klicken. ⟶ Browser opened – sign in there, then click 'Test' here.
Testen ⟶ Test
Chat-ID finden ⟶ Find chat ID
Trennen ⟶ Disconnect
Wirklich trennen? ⟶ Really disconnect?
Gerade läuft nichts ⟶ Nothing playing right now
Im Call ⟶ In call
Meeting läuft ⟶ Meeting running
· Protokoll läuft ⟶ · taking notes
· spricht ⟶ · speaking
· denkt nach ⟶ · thinking
■ Call-Modus beenden ⟶ ■ End call mode
■ Meeting beenden & zusammenfassen ⟶ ■ End meeting & summarize
■ Protokoll beenden & zusammenfassen ({}) ⟶ ■ Stop notes & summarize ({})
📝 Protokoll zusammenfassen ({} Beiträge) ⟶ 📝 Summarize notes ({} entries)
{} Beiträge ⟶ {} entries
Bitte erst bestätigen, dass alle Bescheid wissen. ⟶ Please confirm first that everyone knows.
Fehler (Loss): {} → {} · je kleiner, desto besser ⟶ Error (loss): {} → {} · lower is better
Lernkurve ⟶ Learning curve
Jetzt nutzen ⟶ Use now
läuft ⟶ running
läuft · {} Min. ⟶ running · {} min
fertig ⟶ done
fehler ⟶ error
abgebrochen ⟶ cancelled
keine NVIDIA-GPU erkannt ⟶ no NVIDIA GPU detected
3 · {} trainieren ⟶ 3 · Train {}
{} lernt aus Beispiel-Gesprächen deinen Stil, deine Vorlieben und seine Persönlichkeit – fest im eigenen Modell. Sammle Beispiele (unten, geht auch nebenbei) und drück dann einmal auf „Trainieren“. Den Rest macht {} allein. ⟶ {} learns your style, your preferences and its personality from example conversations – baked into its own model. Collect examples (below, works on the side too) and then press “Train” once. {2} does the rest on its own.
Noch {} bis zum ersten Training – am schnellsten mit der Lehrer-KI 🎓. ⟶ {} more until the first training – fastest with the Teacher AI 🎓.
Training möglich. Ab 100 wird's spürbar besser (noch {}). ⟶ Training possible. From 100 it gets noticeably better ({} to go).
Gut! Ab 500 Beispielen wird {} richtig sicher. ⟶ Good! From 500 examples {} gets really solid.
Top – genug für ein richtig gutes Modell. ⟶ Top – enough for a really good model.
💬 Chats: {} ⟶ 💬 Chats: {}
✏️ verbessert: {} ⟶ ✏️ improved: {}
☁️ von der Cloud: {} ⟶ ☁️ from the cloud: {}
🎓 Lehrer-KI: {} ⟶ 🎓 Teacher AI: {}
wissen: {} ⟶ 📚 from documents: {}
+{} neu seit Training ⟶ +{} new since training
Beispiele ⟶ Examples
Stufe: {} ⟶ Level: {}
Zu wenig ⟶ Too few
Anfänger 🌱 ⟶ Beginner 🌱
Gut 👍 ⟶ Good 👍
Profi 🏆 ⟶ Pro 🏆
Kosten je nach Modell ⟶ cost depends on model
🎓 Lehrer-KI ⟶ 🎓 Teacher AI
{} schreibt einmalig 200 Übungsgespräche in {}s Stil – über Smalltalk, Gaming, Linux, Alltag, Witze … Dauert ein paar Minuten. ⟶ {} writes 200 practice conversations in {}'s style, once – small talk, gaming, Linux, everyday life, jokes … Takes a few minutes.
Braucht einen Cloud-Key (z. B. Claude) in den Einstellungen. ⟶ Needs a cloud key (e.g. Claude) in Settings.
Schreibt gerade … ⟶ Writing …
200 Gespräche erzeugen · {} ⟶ Create 200 conversations · {}
Die Lehrer-KI ({}) schreibt 200 Übungsgespräche. Geschätzte Kosten: {}. Starten? ⟶ The Teacher AI ({}) writes 200 practice conversations. Estimated cost: {}. Start?
Alte Antworten nacheinander durchgehen: 👍 gut, 👎 schlecht, ✏️ besser schreiben. Mit Tasten 1 2 3 und Leertaste – 50 Stück in 3 Minuten. ⟶ Go through old answers one by one: 👍 good, 👎 bad, ✏️ write a better one. Keys 1 2 3 and space – 50 in 3 minutes.
Bewerten starten ⟶ Start rating
☁️ Von der Cloud lernen ⟶ ☁️ Learn from the cloud
Im Auto-Modus: Immer wenn {} die Cloud fragen muss, merkt es sich die gute Antwort als Beispiel. Kostet nichts extra. (Nur deine eigenen Fragen, keine mit Dateien oder PC-Aktionen.) ⟶ In auto mode: whenever {} has to ask the cloud, it keeps the good answer as an example. Costs nothing extra. (Only your own questions, none with files or PC actions.)
Automatisch lernen ⟶ Learn automatically
An (wirkt im Auto-Modus) ⟶ On (works in auto mode)
Ollama läuft nicht ⟶ Ollama isn't running
Ollama läuft nicht. ⟶ Ollama isn't running.
Keine NVIDIA-Grafikkarte erkannt ⟶ No NVIDIA graphics card detected
Keine NVIDIA-Grafikkarte gefunden. ⟶ No NVIDIA graphics card found.
Noch {} Beispiele nötig ⟶ {} more examples needed
⚠ Noch {} Beispiele nötig ⟶ ⚠ {} more examples needed
🚀 {} jetzt trainieren ⟶ 🚀 Train {} now
🚀 {} nachtrainieren ⟶ 🚀 Retrain {}
{} jetzt trainieren? ⟶ Train {} now?
Alles läuft automatisch (Datensatz → ggf. Installation → Training → umstellen → Test). Dauert je nach Grafikkarte 15–90 Minuten, beim ersten Mal plus Download (5–8 GB). Du kannst {} solange normal nutzen. ⟶ Everything runs automatically (dataset → install if needed → training → switch → test). Takes 15–90 minutes depending on your GPU, plus a 5–8 GB download the first time. You can keep using {} normally meanwhile.
Ein Klick – prüft alles, wählt das passende Modell für deine Grafikkarte, trainiert und stellt um. ⟶ One click – checks everything, picks the right model for your GPU, trains and switches over.
✓ Trainiert am {} – {} nutzt „{}“ ⟶ ✓ Trained on {} – {} uses “{}”
Testfrage, z. B. „Was soll ich heute zocken?“ ⟶ Test question, e.g. “What should I play today?”
Testfrage ⟶ Test question
Vorher · {} ⟶ Before · {}
Nachher · {} ⟶ After · {}
Vorher / Nachher vergleichen ⟶ Compare before / after
Beide antworten … ⟶ Both are answering …
↩ Zurück zu „{}“ ⟶ ↩ Back to “{}”
Wieder das alte Modell nutzen? Das trainierte bleibt gespeichert. ⟶ Use the old model again? The trained one stays saved.
✓ Training fertig ⟶ ✓ Training done
🌙 Nachts automatisch nachtrainieren (wenn 50+ neue Beispiele da sind, 3–5 Uhr, PC muss an sein) ⟶ 🌙 Retrain automatically at night (when there are 50+ new examples, 3–5 am, PC must be on)
Profi-Einstellungen (alles von Hand) ⟶ Pro settings (everything by hand)
{} Chats ⟶ {} chats
Datensatz: {} ⟶ Dataset: {}
Datensatz erstellen ⟶ Create dataset
Trainings-Umgebung installieren (einmalig, ca. 5–8 GB) ⟶ Install training environment (once, about 5–8 GB)
Trainings-Basis ⟶ Training base
Durchgänge ⟶ Epochs
1 Durchgang ⟶ 1 epoch
{} Durchgänge ⟶ {} epochs
Name des neuen Modells ⟶ Name of the new model
Training starten ⟶ Start training
Welche KI ⟶ Which AI
KI: {} (lokal, kostenlos) ⟶ AI: {} (local, free)
KI: {} (Cloud – beste Qualität) ⟶ AI: {} (cloud – best quality)
KI: {} (lokal, kostenlos, langsamer) ⟶ AI: {} (local, free, slower)
kostenlos (lokal mit {}) ⟶ free (local with {})
ca. \x24{} mit {} ⟶ about \x24{} with {}
mit {} ⟶ with {}
Zusammenfassung ⟶ Summary
Quiz (10 Fragen) ⟶ Quiz (10 questions)
20 Karteikarten ⟶ 20 flashcards
Lumen lernt aus dem Dokument (Übungsgespräche fürs Training) ⟶ Lumen learns from the document (practice conversations for training)
{} für „{}“ erstellen? ⟶ Create {} for “{}”?
Kosten: {} ⟶ Cost: {}
Lade {} … ⟶ Loading {} …
{} liest {} Datei(en) … ⟶ {} is reading {} file(s) …
{} aufgenommen. ⟶ {} added.
…oder Webseite (https://…) / Pfad (~/Dokumente/skript.pdf) ⟶ …or website (https://…) / path (~/Documents/notes.pdf)
Webseite oder Pfad ⟶ Website or path
📥 PDFs, Bücher & Skripte hier reinziehen ⟶ 📥 Drag PDFs, books & lecture notes here
PDF, Word, EPUB, PowerPoint, Text – {} liest alles, merkt sich den Inhalt und kann daraus Fragen beantworten, zusammenfassen, abfragen und lernen. ⟶ PDF, Word, EPUB, PowerPoint, text – {} reads it all, remembers the content and can answer questions, summarize, quiz you and learn from it.
Dateien wählen ⟶ Choose files
Aufnehmen ⟶ Add
Deine Bibliothek ⟶ Your library
{} Dokumente ⟶ {} documents
Noch leer. Zieh dein erstes Skript, Buch oder PDF rein – dann kannst du z. B. fragen: „Was steht in meinem Bio-Skript über Photosynthese?“ ⟶ Still empty. Drag in your first notes, book or PDF – then you can ask e.g. “What do my biology notes say about photosynthesis?”
{} Seiten · {} Wörter · {} ⟶ {} pages · {} words · {}
{} Wörter · {} ⟶ {} words · {}
Aus der Bibliothek entfernen ⟶ Remove from library
Entfernen ⟶ Remove
„{}“ aus der Bibliothek entfernen? (Die Originaldatei bleibt.) ⟶ Remove “{}” from the library? (The original file stays.)
💬 Fragen stellen ⟶ 💬 Ask questions
📝 Zusammenfassen ⟶ 📝 Summarize
Die wichtigsten Punkte als Lernzettel ⟶ The key points as a study sheet
🃏 Karteikarten ⟶ 🃏 Flashcards
20 Karteikarten zum Lernen ⟶ 20 flashcards for studying
❓ Quiz ⟶ ❓ Quiz
10 Fragen zum Selbsttesten ⟶ 10 questions to test yourself
🧠 {} lernt daraus ⟶ 🧠 {} learns from it
Erstellt Übungsgespräche für das Training im KI-Labor ⟶ Creates practice conversations for training in the AI Lab
Karteikarten ⟶ Flashcards
Gespeichert in Dokumente/Lumen/Lernen ✓ ⟶ Saved in Documents/Lumen/Lernen ✓
Als Word speichern ⟶ Save as Word
Als PDF ⟶ As PDF
Als Word ⟶ As Word
Quiz dazu ⟶ Quiz on it
❓ Quiz · {} ⟶ ❓ Quiz · {}
Stark! Das sitzt. 🏆 ⟶ Excellent! You've got it. 🏆
Gut! Ein paar Sachen nochmal anschauen. 👍 ⟶ Good! Review a few things again. 👍
Da geht noch was – schau dir die Zusammenfassung an und probier's nochmal. 💪 ⟶ Room to improve – look at the summary and try again. 💪
Nochmal ⟶ Again
Neue Fragen ⟶ New questions
✓ Richtig! {} ⟶ ✓ Correct! {}
✗ Leider falsch. {} ⟶ ✗ Sorry, wrong. {}
Weiter → ⟶ Next →
Ergebnis ⟶ Result
🃏 Karteikarten · {} ⟶ 🃏 Flashcards · {}
{} gewusst · {} übrig ⟶ {} known · {} left
Alle {} Karten gewusst! ⟶ All {} cards known!
Von vorn ⟶ Start over
Karte umdrehen ⟶ Flip card
✗ Nochmal ⟶ ✗ Again
✓ Gewusst ⟶ ✓ Knew it
Karte antippen zum Umdrehen ⟶ Tap the card to flip
Für Anki (CSV) ⟶ For Anki (CSV)
🧠 Gelernt aus „{}“ ⟶ 🧠 Learned from “{}”
{} Übungsgespräche erstellt. Beim nächsten Training im KI-Labor lernt die eigene KI diesen Stoff fest. ⟶ {} practice conversations created. At the next training in the AI Lab, your own AI will learn this material for good.
🧪 Zum KI-Labor ⟶ 🧪 To the AI Lab
fertig ⟶ done
≈ {} Wörter · ca. {} Seiten · {} ⟶ ≈ {} words · about {} pages · {}
≈ {} Wörter · ca. {} Seiten · ⟶ ≈ {} words · about {} pages ·
{} – dauert länger ⟶ {} – takes longer
Kurz (~1.000 Wörter) ⟶ Short (~1,000 words)
Mittel (~2.500 Wörter) ⟶ Medium (~2,500 words)
Lang (~4.000 Wörter) ⟶ Long (~4,000 words)
Sehr lang (~6.000) ⟶ Very long (~6,000)
E-Book (EPUB) ⟶ E-book (EPUB)
📖 Buch schreiben ⟶ 📖 Write a book
Plan → Kapitel für Kapitel → Word/PDF/E-Book ⟶ Plan → chapter by chapter → Word/PDF/e-book
Beschreib deine Idee – Lumen plant Handlung und Figuren und schreibt dann jedes Kapitel im Hintergrund. Kurze Texte (Brief, Gedicht, Bewerbung, Referat) geht schneller direkt im Chat: „Schreib mir … als PDF“. ⟶ Describe your idea – Lumen plans plot and characters and then writes each chapter in the background. Short texts (letter, poem, application, essay) are quicker right in the chat: “Write me … as a PDF”.
Worum geht's? ⟶ What's it about?
z. B. Ein Gamer wird in sein Lieblingsspiel gesaugt und muss mit seinen Discord-Freunden das letzte Level schaffen, bevor der Server abgeschaltet wird … ⟶ e.g. A gamer gets sucked into their favorite game and has to beat the final level with their Discord friends before the server shuts down …
Genre ⟶ Genre
Titel (optional) ⟶ Title (optional)
Lumen denkt sich einen aus ⟶ Lumen will come up with one
Kapitel ⟶ Chapters
Länge pro Kapitel ⟶ Length per chapter
Stil / Ton ⟶ Style / tone
spannend, witzig, düster, wie ein Manga … ⟶ thrilling, funny, dark, like a manga …
Für wen? ⟶ For whom?
Jugendliche, Kinder ab 8, Erwachsene … ⟶ teens, kids 8+, adults …
Autor ⟶ Author
Dein Name ⟶ Your name
KI ⟶ AI
Formate ⟶ Formats
✍️ Buch schreiben ⟶ ✍️ Write book
Erst die Idee eintragen. ⟶ Enter the idea first.
Buch schreiben? {} ⟶ Write the book? {}
Buch schreiben ⟶ Write book
Deine Bücher ⟶ Your books
Noch keine Bücher. ⟶ No books yet.
Was soll anders sein? (z. B. mehr Dialoge, spannenderes Ende) ⟶ What should change? (e.g. more dialogue, a more exciting ending)
Wunsch ⟶ Wish
📂 Ordner ⟶ 📂 Folder
📝 Text ⟶ 📝 Text
📗 E-Book ⟶ 📗 E-book
Dateien aus fertigen Kapiteln erstellen ⟶ Create files from finished chapters
✏️ Kapitel überarbeiten ⟶ ✏️ Revise a chapter
Neu schreiben ⟶ Rewrite
Kap. {}: {} ⟶ Ch. {}: {}
{} · {}/{} Kapitel · {} Wörter · {} ⟶ {} · {}/{} chapters · {} words · {}
Fertig – {} Antworten bewertet. Danke! 🎉 ⟶ Done – {} answers rated. Thanks! 🎉
Keine unbewerteten Antworten. Chatte mehr oder nutze die Lehrer-KI 🎓. ⟶ No unrated answers. Chat more or use the Teacher AI 🎓.
Zurück zum Labor ⟶ Back to the lab
Du: {} ⟶ You: {}
So hätte die Antwort sein sollen (Strg+Enter speichert): ⟶ This is what the answer should have been (Ctrl+Enter saves):
gut · 1 ⟶ good · 1
schlecht · 2 ⟶ bad · 2
verbessern · 3 ⟶ improve · 3
überspringen · Leertaste ⟶ skip · Space
{} / {} · {} bewertet ⟶ {} / {} · {} rated
Installieren mit ⟶ Install with
1 · Dein Lumen-Modell ⟶ 1 · Your Lumen model
✓ gebaut ⟶ ✓ built
noch nicht gebaut ⟶ not built yet
Ein eigenes Modell namens „lumen“ auf Basis einer freien KI – mit Lumens Name, Persönlichkeit (inkl. Fluchen, falls an) und allem, was Lumen über dich weiß. Nach Änderungen einfach neu bauen. ⟶ Your own model called “lumen” based on a free AI – with Lumen's name, personality (incl. swearing, if on) and everything Lumen knows about you. After changes, just rebuild.
Basismodell ⟶ Base model
Herunterladen ⟶ Download
Lumen-Modell bauen ⟶ Build Lumen model
✓ Lumen nutzt „lumen“ ⟶ ✓ Lumen uses “lumen”
„lumen“ als Haupt-KI nutzen ⟶ Use “lumen” as main AI
Cloud-Anbieter ⟶ Cloud provider
2 · Schlaues Zusammenspiel ⟶ 2 · Smart teamwork
Einfache Sachen (Smalltalk, Musik, Apps öffnen, Wetter) beantwortet die lokale KI kostenlos. Schweres (Recherche, Code, Dateien, Bilder, Server) geht an die Cloud. Ist die lokale Antwort zu schwach, fragt Lumen automatisch nach. Unter jeder Antwort steht 🧠 lokal oder ☁️ Cloud. ⟶ The local AI answers simple things (small talk, music, opening apps, weather) for free. Hard things (research, code, files, images, servers) go to the cloud. If the local answer is too weak, Lumen automatically asks the cloud. Every answer shows 🧠 local or ☁️ cloud.
Auto-Modus ⟶ Auto mode
Lokal ⟶ Local
lokal ⟶ local
4 · Mini-KI von null ⟶ 4 · Mini AI from scratch
{} Mio. Parameter · Loss {} ⟶ {}M parameters · loss {}
noch nicht trainiert ⟶ not trained yet
Eine winzige KI (ein echter Transformer wie GPT – nur tausendmal kleiner), die Buchstabe für Buchstabe aus euren Chats lernt. Sie wird nicht schlau, aber du siehst live, wie KI lernt: erst Buchstabensalat, dann Wörter, dann Sätze in eurem Stil. Mehr Text? Lege .txt-Dateien in ~/.lumen/lab/mini_texte/. ⟶ A tiny AI (a real transformer like GPT – just a thousand times smaller) that learns letter by letter from your chats. It won't get smart, but you can watch live how AI learns: first letter soup, then words, then sentences in your style. More text? Put .txt files in ~/.lumen/lab/mini_texte/.
Größe ⟶ Size
Klein (≈ 2 Mio. Parameter, 3 Min.) ⟶ Small (≈ 2M parameters, 3 min)
Mittel (≈ 11 Mio., 10 Min.) ⟶ Medium (≈ 11M, 10 min)
Groß (≈ 25 Mio., 25 Min.) ⟶ Large (≈ 25M, 25 min)
Schritte ⟶ Steps
Mini-KI trainieren ⟶ Train mini AI
Anfang ⟶ Start
Die Mini-KI schreibt hier weiter … ⟶ The mini AI continues writing here …
Schreiben lassen ⟶ Let it write
🧠 lokal · {} ⟶ 🧠 local · {}
☁️ Cloud · {} ⟶ ☁️ cloud · {}
Alles prüfen ⟶ Check everything
Datensatz bauen ⟶ Build dataset
Trainings-Umgebung ⟶ Training environment
Lumen umstellen ⟶ Switch Lumen over
Kurztest ⟶ Quick test
Lumen trainieren ⟶ Train Lumen
Lehrer-KI schreibt Übungsgespräche ⟶ Teacher AI is writing practice conversations
schon installiert ⟶ already installed
installiert ⟶ installed
{} Beispiele ⟶ {} examples
nur {} Beispiele ⟶ only {} examples
das dauert 15–90 Minuten – du kannst Lumen solange normal nutzen ⟶ this takes 15–90 minutes – you can keep using Lumen normally
lädt PyTorch & Unsloth (5–8 GB, einmalig) ⟶ downloading PyTorch & Unsloth (5–8 GB, once)
Lumen nutzt jetzt „{}“ ⟶ Lumen now uses “{}”
Training – {} ⟶ Training – {}
{} Übungsgespräche erstellt ⟶ {} practice conversations created
{} Gespräche erstellt ⟶ {} conversations created
Plan & Figuren ⟶ Plan & characters
Kapitel {} ⟶ Chapter {}
Kapitel {}: {} ⟶ Chapter {}: {}
Dateien erstellen ⟶ Create files
Plane Handlung, Figuren und Kapitel … ⟶ Planning plot, characters and chapters …
Schreibe Kapitel {} von {} … ⟶ Writing chapter {} of {} …
Erstelle Word/PDF/E-Book … ⟶ Creating Word/PDF/e-book …
{} Wörter ⟶ {} words
zu kurz – nochmal ⟶ too short – retrying
Fertig: „{}“ – {} Wörter, {} Kapitel ⟶ Done: “{}” – {} words, {} chapters
Kapitel {} neu schreiben ⟶ Rewrite chapter {}
Schreibe Kapitel {} neu … ⟶ Rewriting chapter {} …
Kapitel {} neu geschrieben ({} Wörter) ⟶ Chapter {} rewritten ({} words)
Teil {} ⟶ Part {}
Zusammenfassen ⟶ Summarize
Zusammenführen ⟶ Merging
Lese Teil {} von {} … ⟶ Reading part {} of {} …
Führe zusammen … ⟶ Merging …
Lese den Stoff und denke mir Fragen aus … ⟶ Reading the material and coming up with questions …
Teil {} von {} – {} Gespräche ⟶ Part {} of {} – {} conversations
Lumen lernt aus dem Dokument ⟶ Lumen is learning from the document
Quiz ⟶ Quiz
Roman ⟶ Novel
Fantasy ⟶ Fantasy
Science-Fiction ⟶ Science fiction
Krimi/Thriller ⟶ Crime/thriller
Liebesroman ⟶ Romance
Horror ⟶ Horror
Kinderbuch ⟶ Children's book
Jugendbuch ⟶ Young adult
Sachbuch ⟶ Non-fiction
Ratgeber ⟶ Self-help / guide
Biografie (fiktiv) ⟶ Biography (fictional)
Kurzgeschichten ⟶ Short stories
Fanfiction (eigene Figuren) ⟶ Fan fiction (own characters)
Lehrbuch/Skript ⟶ Textbook/course notes
Freundlich ⟶ Friendly
Butler mit Humor ⟶ Butler with humor
Kumpel ⟶ Buddy
Frech ⟶ Cheeky
Kurz & knapp ⟶ Short & sweet
Ruhig & geduldig ⟶ Calm & patient
Ungefiltert ⟶ Unfiltered
Eigene ⟶ Custom
Ordner angesehen: {} ⟶ Viewed folder: {}
Gesucht: {} ⟶ Searched: {}
Geöffnet: {} ⟶ Opened: {}
Ordner angelegt: {} ⟶ Created folder: {}
Datei geschrieben: {} ⟶ Wrote file: {}
Verschoben: {} → {} ⟶ Moved: {} → {}
Gelöscht: {} ⟶ Deleted: {}
Dokument erstellt: {} ⟶ Created document: {}
Buch gestartet: {} ⟶ Book started: {}
In der Bibliothek gesucht: {} ⟶ Searched the library: {}
In die Bibliothek aufgenommen: {} ⟶ Added to the library: {}
Bibliothek angesehen ⟶ Viewed library
Spiele gesucht ⟶ Looked for games
Spiel gestartet: {} ⟶ Launched game: {}
Programme gelistet ⟶ Listed programs
Laufende Programme angesehen ⟶ Viewed running programs
Beendet: {} ⟶ Closed: {}
Medien: {} ⟶ Media: {}
Befehl: {} ⟶ Command: {}
Server gelistet ⟶ Listed servers
Server gespeichert: {} ⟶ Saved server: {}
Server entfernt: {} ⟶ Removed server: {}
Verbindung getestet: {} ⟶ Tested connection: {}
SSH-Key eingerichtet: {} ⟶ Set up SSH key: {}
Server-Übersicht: {} ⟶ Server overview: {}
Hochgeladen → {} ⟶ Uploaded → {}
Heruntergeladen ← {} ⟶ Downloaded ← {}
Bildschirm angesehen ⟶ Looked at the screen
Maus: {} ⟶ Mouse: {}
Getippt: {} ⟶ Typed: {}
Tasten: {} ⟶ Keys: {}
Fenster gelistet ⟶ Listed windows
Fenster: {} ⟶ Window: {}
Systeminfo gelesen ⟶ Read system info
Websuche: {} ⟶ Web search: {}
{} Seiten gelesen: {} ⟶ Read {} pages: {}
Im Browser gesucht: {} ⟶ Searched in browser: {}
Aufgabe: {} ⟶ Task: {}
Aufgabe erledigt ⟶ Task done
Notiz gespeichert ⟶ Note saved
Technik: {} ⟶ Tech: {}
Link aufgeklappt: {} ⟶ Expanded link: {}
Mail analysiert ⟶ Analyzed email
Metadaten: {} ⟶ Metadata: {}
Metadaten entfernt: {} ⟶ Removed metadata: {}
Bild geprüft: {} ⟶ Checked image: {}
Bild-Rückwärtssuche geöffnet ⟶ Opened reverse image search
Datenleck-Check (eigene E-Mails) ⟶ Breach check (own emails)
Passwort anonym geprüft ⟶ Checked password anonymously
Benutzernamen-Check (eigene) ⟶ Username check (own)
Abgehört: {} ⟶ Transcribed: {}
Verbrauch abgefragt ⟶ Checked usage
Gemerkt: {} ⟶ Remembered: {}
Vergessen: {} ⟶ Forgot: {}
Verschieben / umbenennen ⟶ Move / rename
Löschen (in den Papierkorb) ⟶ Delete (to trash)
Programm beenden ⟶ Close program
Server entfernen ⟶ Remove server
Auf {} hochladen ⟶ Upload to {}
Maus und Tastatur steuern ⟶ Control mouse and keyboard
Datei zu VirusTotal hochladen ⟶ Upload file to VirusTotal
Skript oder Installer öffnen ⟶ Open script or installer
Dokument überschreiben ⟶ Overwrite document
Datei überschreiben ⟶ Overwrite file
Befehl ausführen ⟶ Run command
Herunterfahren ⟶ Shut down
Neu starten ⟶ Restart
Lokal zu schwer ({}) → frage die Cloud ⟶ Too hard locally ({}) → asking the cloud
Nicht erlaubt im Call: {} ⟶ Not allowed in call: {}
Abgelehnt: {} ⟶ Denied: {}
{} kann keine Werkzeuge nutzen – antworte ohne PC-Steuerung ⟶ {} can't use tools – answering without PC control
Datei nicht gefunden. ⟶ File not found.
Getrennt. ⟶ Disconnected.
Spotify-Anmeldung im Browser geöffnet. ⟶ Spotify sign-in opened in the browser.
Unbekannte Aktion ⟶ Unknown action
Für die Lehrer-KI brauchst du einen Cloud-Key (z. B. Anthropic) in den Einstellungen. ⟶ The Teacher AI needs a cloud key (e.g. Anthropic) in Settings.
Bitte die bessere Antwort eintragen. ⟶ Please enter the better answer.
Das sieht nach einem geheimen Schlüssel/einer Seed-Phrase aus – wird nicht gespeichert. ⟶ That looks like a secret key/seed phrase – it won't be saved.
Gemerkt ✏️ – Lumen lernt das beim nächsten Training. ⟶ Saved ✏️ – Lumen learns it at the next training.
Kein vorheriges Modell gespeichert. ⟶ No previous model saved.
Zurück zum alten Modell ({}). Das trainierte Modell bleibt in Ollama erhalten. ⟶ Back to the old model ({}). The trained model stays in Ollama.
Lumen nutzt jetzt „{}“ (lokal, kostenlos). ⟶ Lumen now uses “{}” (local, free).
Auto-Modus an: Einfaches lokal, Schweres in der Cloud. ⟶ Auto mode on: simple things local, hard things in the cloud.
Nichts mitgeschrieben. ⟶ Nothing was recorded.
Zu wenig Text gefunden. ⟶ Too little text found.
Wetter ⟶ Weather
Kalender ⟶ Calendar
Krypto-Wallets ⟶ Crypto wallets
Dein Ort ⟶ Your location
Adresse ⟶ Address
Deine Chat-ID ⟶ Your chat ID
Profilname oder SteamID64 ⟶ Profile name or SteamID64
Langlebiges Zugangstoken ⟶ Long-lived access token
Aktuelles Wetter und Vorhersage – ohne Key (Open-Meteo). ⟶ Current weather and forecast – no key needed (Open-Meteo).
Einfach deinen Ort eintragen. Lumen zeigt das Wetter dann auch oben rechts an. ⟶ Just enter your location. Lumen will then also show the weather at the top right.
Termine aus Google, Outlook, iCloud oder Nextcloud (nur lesen). ⟶ Events from Google, Outlook, iCloud or Nextcloud (read-only).
Licht, Steckdosen, Heizung, Sensoren, Szenen steuern. ⟶ Control lights, plugs, heating, sensors, scenes.
Lumen schickt dir Nachrichten und Dateien aufs Handy. ⟶ Lumen sends messages and files to your phone.
Nachrichten in deine Discord-Kanäle senden (z. B. Server-Updates, Ankündigungen). ⟶ Send messages to your Discord channels (e.g. server updates, announcements).
Phantom, Solflare, MetaMask, Bitcoin – Kontostand, Tokens, Wert, Transaktionen. Nur lesen. ⟶ Phantom, Solflare, MetaMask, Bitcoin – balance, tokens, value, transactions. Read-only.
Repos, Issues, Pull Requests, Actions-Status, Benachrichtigungen, Issues erstellen. ⟶ Repos, issues, pull requests, Actions status, notifications, create issues.
Spielpreise und Rabatte (ohne Key), dein Profil und deine Spielzeit (mit Key). ⟶ Game prices and discounts (no key), your profile and playtime (with key).
Was läuft, Songs/Playlists abspielen, Lautstärke, Warteschlange, Lieblingssongs. ⟶ What's playing, play songs/playlists, volume, queue, liked songs.
Steam Web-API-Key (optional) ⟶ Steam Web API key (optional)
Eigener Solana-RPC (optional, z. B. Helius – schneller) ⟶ Own Solana RPC (optional, e.g. Helius – faster)
Öffentliche Adressen (name = adresse) ⟶ Public addresses (name = address)
iCal-Links (name = link) ⟶ iCal links (name = link)
Webhooks (kanal = url) ⟶ Webhooks (channel = url)
Discord → Server-Einstellungen → Integrationen → Webhooks → Neuer Webhook → Kanal wählen → URL kopieren. ⟶ Discord → Server settings → Integrations → Webhooks → New webhook → pick channel → copy URL.
In Home Assistant: Profil (unten links) → Sicherheit → Langlebige Zugangstoken → Token erstellen. ⟶ In Home Assistant: Profile (bottom left) → Security → Long-lived access tokens → Create token.
In Telegram @BotFather öffnen → /newbot → Namen wählen → Token kopieren und hier einfügen. Dann deinem neuen Bot /start schreiben und 'Chat-ID finden' klicken. ⟶ In Telegram open @BotFather → /newbot → pick a name → copy the token and paste it here. Then send /start to your new bot and click 'Find chat ID'.
In Phantom oben auf deinen Account → Adresse kopieren (Solana, Ethereum oder Bitcoin). NUR die öffentliche Adresse – niemals Seed-Phrase oder privaten Schlüssel! Zahlungen erstellt Lumen als QR-Code, du bestätigst in Phantom. ⟶ In Phantom tap your account at the top → copy address (Solana, Ethereum or Bitcoin). ONLY the public address – never a seed phrase or private key! Lumen creates payments as a QR code, you confirm in Phantom.
API-Key: steamcommunity.com/dev/apikey (Domain egal, z. B. localhost). Profil: dein Profilname aus der URL oder SteamID64. Spieldetails im Profil auf 'öffentlich' stellen. ⟶ API key: steamcommunity.com/dev/apikey (any domain, e.g. localhost). Profile: your profile name from the URL or SteamID64. Set game details in your profile to 'public'.
Google Kalender: Einstellungen → dein Kalender → 'Privatadresse im iCal-Format' kopieren. Outlook: Kalender freigeben → ICS-Link. iCloud: Kalender teilen → öffentlich. Der Link ist geheim – nicht weitergeben. ⟶ Google Calendar: Settings → your calendar → copy 'Secret address in iCal format'. Outlook: share calendar → ICS link. iCloud: share calendar → public. The link is secret – don't share it.
github.com → Settings → Developer settings → Personal access tokens → Fine-grained → Repos wählen, Rechte: Issues, Pull requests, Actions (lesen; Issues schreiben für 'erstellen'). ⟶ github.com → Settings → Developer settings → Personal access tokens → Fine-grained → pick repos, permissions: Issues, Pull requests, Actions (read; Issues write for 'create').
1. developer.spotify.com/dashboard → Create app. 2. Redirect URI genau so eintragen: http://127.0.0.1:8765/callback/spotify 3. 'Web API' anhaken, speichern. 4. Client ID hier einfügen, speichern, dann 'Mit Spotify anmelden'. Steuerung braucht Premium. ⟶ 1. developer.spotify.com/dashboard → Create app. 2. Enter the redirect URI exactly like this: http://127.0.0.1:8765/callback/spotify 3. Tick 'Web API', save. 4. Paste the Client ID here, save, then 'Sign in with Spotify'. Playback control needs Premium.
Qwen 2.5 7B – Allrounder, sehr gut auf Deutsch, Werkzeuge (≈ 5 GB) ⟶ Qwen 2.5 7B – all-rounder, very good at German, tools (≈ 5 GB)
Qwen 2.5 3B – klein & schnell, für schwächere PCs (≈ 2 GB) ⟶ Qwen 2.5 3B – small & fast, for weaker PCs (≈ 2 GB)
Qwen 2.5 VL 7B – kann zusätzlich Bilder/Bildschirm sehen (≈ 6 GB) ⟶ Qwen 2.5 VL 7B – can also see images/screen (≈ 6 GB)
Qwen 3 8B – neuer, denkt mit, Werkzeuge (≈ 5 GB) ⟶ Qwen 3 8B – newer, reasons, tools (≈ 5 GB)
Llama 3.1 8B – Meta, solide, Werkzeuge (≈ 5 GB) ⟶ Llama 3.1 8B – Meta, solid, tools (≈ 5 GB)
klar ⟶ clear
überwiegend klar ⟶ mostly clear
teils bewölkt ⟶ partly cloudy
bedeckt ⟶ overcast
Nebel ⟶ fog
Nieselregen ⟶ drizzle
leichter Regen ⟶ light rain
Regen ⟶ rain
starker Regen ⟶ heavy rain
gefrierender Regen ⟶ freezing rain
leichter Schnee ⟶ light snow
Schnee ⟶ snow
starker Schnee ⟶ heavy snow
Schneegriesel ⟶ snow grains
Regenschauer ⟶ rain showers
heftige Schauer ⟶ heavy showers
Gewitter ⟶ thunderstorm
Agenten ⟶ Agents
🤖 Agenten ⟶ 🤖 Agents
{} online ⟶ {} online
Gib Lumen eine große Aufgabe – ein Agent (oder ein ganzes Team) plant und erledigt sie im Hintergrund, während du weitermachst. ⟶ Give Lumen a big task – an agent (or a whole team) plans and does it in the background while you carry on.
＋ Neuer Agent ⟶ ＋ New agent
Agenten · {} online · {} wartet auf dich ⟶ Agents · {} online · {} waiting for you
Agenten · {} online ⟶ Agents · {} online
Neue Aufgabe ⟶ New task
läuft im Hintergrund – du kannst normal weiterchatten ⟶ runs in the background – you can keep chatting
Was soll erledigt werden? z. B. „Richte auf meinem Server einen Minecraft-Server mit Paper ein, mit Backup jede Nacht“ oder „Vergleiche die 5 besten Gaming-Mäuse unter 80 € und schreib mir einen Bericht als PDF“ ⟶ What should be done? e.g. “Set up a Paper Minecraft server on my server with a nightly backup” or “Compare the 5 best gaming mice under €80 and write me a PDF report”
🧭 Als Team: Leiter verteilt an Spezialisten (🔎 Recherche, 🧑‍💻 Coder, 🛠️ Admin, ✍️ Schreiber, ✅ Prüfer), die parallel arbeiten ⟶ 🧭 As a team: a lead hands work to specialists (🔎 research, 🧑‍💻 coder, 🛠️ admin, ✍️ writer, ✅ reviewer) working in parallel
🤖 Agent starten ⟶ 🤖 Start agent
Strg+Enter · Riskante Schritte fragen trotzdem nach. ⟶ Ctrl+Enter · Risky steps still ask first.
⏳ {} wartet auf dich ⟶ ⏳ {} waiting for you
✅ {} fertig ⟶ ✅ {} done
Gerade aktiv: {} ⟶ Active now: {}
Fertige ausblenden ⟶ Hide finished
Noch keine Agenten. Tipp: Auch im Chat geht's – „Mach das als Agent im Hintergrund: …“ – oder per Telegram mit /agent bzw. /team. ⟶ No agents yet. Tip: works in the chat too – “Do this as an agent in the background: …” – or via Telegram with /agent or /team.
🚀 startet ⟶ 🚀 starting
🧠 plant ⟶ 🧠 planning
⚙️ arbeitet ⟶ ⚙️ working
⏳ wartet auf dich ⟶ ⏳ waiting for you
✅ fertig ⟶ ✅ done
⚠️ Fehler ⟶ ⚠️ error
🛑 gestoppt ⟶ 🛑 stopped
{} · {} Min. · \x24{} ⟶ {} · {} min · \x24{}
{} · {} Min. ⟶ {} · {} min
Team-Leiter ⟶ Team lead
Agent ⟶ Agent
Rechercheur ⟶ Researcher
Coder ⟶ Coder
Admin ⟶ Admin
Schreiber ⟶ Writer
Prüfer ⟶ Reviewer
Plan ▴ ⟶ Plan ▴
Plan ▾ ⟶ Plan ▾
Verlauf ▴ ⟶ Log ▴
Verlauf ▾ ⟶ Log ▾
Ergebnis ▴ ⟶ Result ▴
Ergebnis ▾ ⟶ Result ▾
💬 Im Chat öffnen ⟶ 💬 Open in chat
Agent stoppen? ⟶ Stop agent?
Agent stoppen? (Sein Team stoppt mit.) ⟶ Stop agent? (Its team stops too.)
Was soll der Agent erledigen? ⟶ What should the agent do?
🧭 Team gestartet ⟶ 🧭 Team started
🤖 Agent gestartet ⟶ 🤖 Agent started
{} Agent {}: {} ⟶ {} Agent {}: {}
Agent erledigt eine große Aufgabe im Hintergrund ⟶ An agent does a big task in the background
Agenten-Team: Leiter + Spezialisten parallel ⟶ Agent team: lead + specialists in parallel
Welche Agenten laufen (online) ⟶ Which agents are running (online)
<Aufgabe> ⟶ <task>
Plan: {} Schritte ⟶ Plan: {} steps
Schritt {}: {} ⟶ Step {}: {}
Team gestartet: {} ⟶ Team started: {}
Agent gestartet: {} ⟶ Agent started: {}
→ {} ⟶ → {}
Termine lesen UND eintragen: Lumen-Kalender, Google, Nextcloud, iCloud, Outlook (Lesen per iCal-Link). ⟶ Read AND add events: Lumen calendar, Google, Nextcloud, iCloud, Outlook (reading via iCal link).
CalDAV-Adresse (optional) ⟶ CalDAV address (optional)
CalDAV-Benutzer ⟶ CalDAV user
CalDAV-App-Passwort ⟶ CalDAV app password
In welchen Kalender eintragen (Name, leer = erster) ⟶ Which calendar to add to (name, empty = first)
Google Client-ID (optional) ⟶ Google client ID (optional)
Google Client-Secret ⟶ Google client secret
Neue Termine eintragen in: lumen / caldav / google (leer = automatisch) ⟶ Add new events to: lumen / caldav / google (empty = automatic)
Nur lesen: iCal-Links (name = link) ⟶ Read-only: iCal links (name = link)
Mit Google anmelden ⟶ Sign in with Google
Google neu anmelden ⟶ Sign in to Google again
Browser geöffnet – dort anmelden, dann hier 'Speichern & testen' klicken. ⟶ Browser opened – sign in there, then click 'Save & test' here.
Google-Anmeldung im Browser geöffnet. ⟶ Google sign-in opened in the browser.
Termin eintragen, z. B. /termin Freitag 18 Uhr Kino ⟶ Add an event, e.g. /termin Friday 6pm cinema
<wann & was> ⟶ <when & what>
z. B. /termin Freitag 18 Uhr Kino ⟶ e.g. /termin Friday 6pm cinema
Termin eingetragen: {} ⟶ Added event: {}
Termin geändert: {} ⟶ Changed event: {}
Termin gelöscht: {} ⟶ Deleted event: {}
Freie Zeiten gesucht: {} ⟶ Looked for free time: {}
Termin löschen ⟶ Delete event
🩺 PC-Doktor ⟶ 🩺 PC Doctor
Findet, was deinen PC langsam oder voll macht – und räumt auf, wenn du willst. ⟶ Finds what makes your PC slow or full – and cleans up if you want.
Untersuchen ⟶ Check
Bericht ⟶ Report
{} · {} Hinweise · {} frei machbar · {} ⟶ {} · {} warnings · {} can be freed · {}
📋 Zwischenablage ⟶ 📋 Clipboard
Text markieren → ⟶ Select text →
→ übersetzen, verbessern, erklären … ⟶ → translate, improve, explain …
Mit dem Text aus der Zwischenablage ⟶ With the text from the clipboard
Mehr & Einstellungen ⟶ More & settings
Mehr ⟶ More
Wayland: Kürzel unter ⋯ → „Kürzel einrichten“. Oder die Knöpfe hier nutzen. ⟶ Wayland: shortcuts under ⋯ → “Set up shortcuts”. Or use the buttons here.
Kürzel aus – Knöpfe nutzen oder unter ⋯ einschalten. ⟶ Shortcuts off – use the buttons or turn them on under ⋯.
Untersuche deinen PC … ⟶ Checking your PC …
Speicher, Caches, Programme, Temperaturen, Autostart, Updates – dauert 5–30 Sekunden. ⟶ Storage, caches, programs, temperatures, autostart, updates – takes 5–30 seconds.
Der PC-Doktor schaut nach vollen Laufwerken, Caches und Papierkorb, Speicher- und CPU-Fressern, Temperaturen, Autostart-Programmen, Startzeit und Updates. Beim Untersuchen wird nichts verändert – aufgeräumt wird nur, wenn du es bestätigst. ⟶ The PC Doctor checks for full drives, caches and trash, memory and CPU hogs, temperatures, autostart programs, boot time and updates. Nothing is changed during the check – it only cleans up when you confirm.
🩺 Jetzt untersuchen ⟶ 🩺 Check now
{} dringend · {} Hinweise · {} lassen sich frei machen · untersucht {} ({} s) ⟶ {} urgent · {} warnings · {} can be freed · checked {} ({} s)
🧹 Empfohlenes aufräumen (~{}) ⟶ 🧹 Clean up recommended (~{})
↻ Neu untersuchen ⟶ ↻ Check again
Speicher ⟶ Storage
Leistung ⟶ Performance
Autostart ⟶ Autostart
System ⟶ System
Überblick ⟶ Overview
Beenden ⟶ Close
Ausschalten ⟶ Turn off
Aufräumen ⟶ Clean up
Aufräumen 🔑 ⟶ Clean up 🔑
{} · {} ⟶ {} · {}
RAM-Fresser ⟶ RAM hogs
CPU-Fresser ⟶ CPU hogs
Startzeit ⟶ Boot time
Grafikkarte ⟶ Graphics card
Größte Ordner ⟶ Largest folders
Laufwerk {} ⟶ Drive {}
Temperatur {} ⟶ Temperature {}
{} % belegt · {} frei ⟶ {} % used · {} free
{} % · {} frei von {} ⟶ {} % · {} free of {}
Top 💚 ⟶ Great 💚
Okay 💛 ⟶ Okay 💛
Braucht Pflege 🧡 ⟶ Needs care 🧡
Kritisch ❤️ ⟶ Critical ❤️
Papierkorb leeren ⟶ Empty trash
Vorschaubilder-Cache leeren ⟶ Clear thumbnail cache
pip-Cache leeren ⟶ Clear pip cache
npm-Cache leeren ⟶ Clear npm cache
Browser-Caches leeren ⟶ Clear browser caches
Docker aufräumen ⟶ Clean up Docker
Ungenutzte Flatpak-Laufzeiten entfernen ⟶ Remove unused Flatpak runtimes
Paket-Cache leeren (apt) ⟶ Clear package cache (apt)
Paket-Cache leeren (pacman) ⟶ Clear package cache (pacman)
Paket-Cache leeren (dnf) ⟶ Clear package cache (dnf)
System-Logs verkleinern ⟶ Shrink system logs
Alte Snap-Versionen entfernen ⟶ Remove old Snap versions
Autostart-Eintrag ausschalten ⟶ Turn off autostart entry
Programm beenden ⟶ Close program
Startet automatisch: {} ({}) ⟶ Starts automatically: {} ({})
Laufwerk {} ist zu {} % voll (nur noch {} frei). ⟶ Drive {} is {} % full (only {} free).
Laufwerk {} ist zu {} % voll. ⟶ Drive {} is {} % full.
{} System-Updates verfügbar. ⟶ {} system updates available.
{} Flatpak-Updates verfügbar (flatpak update). ⟶ {} Flatpak updates available (flatpak update).
Ein Neustart ist nötig, damit Updates aktiv werden. ⟶ A restart is needed for updates to take effect.
Dienst fehlgeschlagen: {} ⟶ Service failed: {}
Der Arbeitsspeicher ist zu {} % voll – das macht den PC langsam. ⟶ RAM is {} % full – that slows the PC down.
Der Arbeitsspeicher ist zu {} % belegt. ⟶ RAM is {} % used.
„{}“ braucht {} RAM ({} %). ⟶ “{}” uses {} RAM ({} %).
„{}“ lastet die CPU mit {} % aus. ⟶ “{}” uses {} % CPU.
Der Downloads-Ordner ist {} groß – vielleicht mal ausmisten? ⟶ The Downloads folder is {} – time for a clean-out?
🧹 {} frei gemacht ⟶ 🧹 {} freed
{}: {} frei ⟶ {}: {} freed
📋 Zwischenablage-Helfer ⟶ 📋 Clipboard helper
So geht's ⟶ How it works
Text irgendwo markieren (oder kopieren) und ein Kürzel drücken – das Ergebnis liegt danach in der Zwischenablage (Strg+V) und kommt als Benachrichtigung. ⟶ Select (or copy) text anywhere and press a shortcut – the result ends up in the clipboard (Ctrl+V) and shows as a notification.
Menü mit allen Aktionen ⟶ Menu with all actions
Übersetzen ⟶ Translate
Verbessern ⟶ Improve
Erklären ⟶ Explain
Zusammenfassen ⟶ Summarize
Antwort schreiben ⟶ Write reply
Formeller ⟶ More formal
Lockerer ⟶ More casual
Kürzer ⟶ Shorter
Code verbessern ⟶ Improve code
Tastenkürzel an ⟶ Shortcuts on
Tastenkürzel an ✓ ⟶ Shortcuts on ✓
Ergebnis direkt einfügen (ersetzt den markierten Text) ⟶ Paste result directly (replaces the selected text)
⌨ Kürzel in GNOME einrichten (auch Wayland) ⟶ ⌨ Set up shortcuts in GNOME (also Wayland)
Andere Desktops: Eigenes Tastenkürzel anlegen mit dem Befehl {} ⟶ Other desktops: create a custom shortcut with the command {}
Ausprobieren ⟶ Try it
Leer lassen = Text aus der Zwischenablage nehmen ⟶ Leave empty = use the clipboard text
Kopieren ⟶ Copy
Zuletzt ⟶ Recent
Nochmal kopieren ⟶ Copy again
✓ In der Zwischenablage – Strg+V ⟶ ✓ In the clipboard – Ctrl+V
PC-Doktor: untersuchen & aufräumen ⟶ PC Doctor: check & clean up
Zwischenablage bearbeiten ⟶ Process clipboard
[übersetzen|verbessern|erklären …] ⟶ [translate|improve|explain …]
PC untersucht ⟶ Checked PC
Aufgeräumt: {} ⟶ Cleaned up: {}
Zwischenablage gelesen ⟶ Read clipboard
In die Zwischenablage gelegt ⟶ Put in clipboard
Schreib deinem Bot einfach wie im Chat – der Server antwortet, rund um die Uhr. ⟶ Just message your bot like in the chat – the server answers, around the clock.
Schreib deinem Bot einfach wie im Chat – ohne Lumen-Server antwortet der PC, solange Lumen hier läuft. Mit Lumen-Server (Abschnitt 1) klappt es auch, wenn der PC aus ist. ⟶ Just message your bot like in the chat – without a Lumen server the PC answers while Lumen is running here. With a Lumen server (section 1) it also works when the PC is off.
Riskante Aktionen bestätigst du mit Knöpfen ✅/❌. Sprachnachrichten, Fotos und PDFs gehen auch. Im Telegram-Menü (/) stehen alle Befehle: /ki und /modelle (KI per Knopf wählen), /deepseek, /claude, /gpt, /gemini, /ollama, /lumen, /auto (mit Frage dahinter nur für diese Antwort), /modell, /research, /wetter, /termine, /erinnerung, /erinnerungen, /aufgaben, /aufgabe, /notiz, /briefing, /status, /kosten, /neu, /stopp, /befehl name = Text (eigener Befehl), /befehle, /hilfe. ⟶ You confirm risky actions with ✅/❌ buttons. Voice messages, photos and PDFs work too. The Telegram menu (/) lists all commands: /ki and /modelle (choose AI with buttons), /deepseek, /claude, /gpt, /gemini, /ollama, /lumen, /auto (with a question after it: only for that answer), /modell, /research, /wetter, /termine, /erinnerung, /erinnerungen, /aufgaben, /aufgabe, /notiz, /briefing, /status, /kosten, /neu, /stopp, /befehl name = text (own command), /befehle, /hilfe.
Telegram-Chat über diesen PC ⟶ Telegram chat via this PC
Bot am PC: {} ⟶ Bot on PC: {}
läuft ✓ ⟶ running ✓
Enter senden · / für Befehle · Dateien reinziehen · Strg+M sprechen · „Hey Lumen“ freihändig ⟶ Enter to send · / for commands · drag in files · Ctrl+M to talk · “Hey Lumen” hands-free
Befehle ⟶ Commands
**/Befehle** – tippe \x60/\x60 im Eingabefeld. ⟶ **/Commands** – type \x60/\x60 in the input field.
Eigene Befehle löschen: in den Einstellungen unter „Eigene Befehle“. ⟶ Delete custom commands: in Settings under “Custom /commands”.
Eigene /Befehle · eine Zeile pro Befehl: name = was Lumen tun soll ⟶ Custom /commands · one line per command: name = what Lumen should do
KI ⟶ AI
Chat ⟶ Chat
Schnell ⟶ Quick
Öffnen ⟶ Open
Eigene ⟶ Custom
[Frage] ⟶ [question]
[Modell | Frage] ⟶ [model | question]
[Name] ⟶ [name]
<Frage> ⟶ <question>
[Ort] ⟶ [place]
<was & wann> ⟶ <what & when>
<Beschreibung> ⟶ <description>
[Idee] ⟶ [idea]
[an|aus] ⟶ [on|off]
<Name> ⟶ <name>
<name> = <Text> ⟶ <name> = <text>
[+ Text] ⟶ [+ text]
Claude nutzen – mit Frage: nur für diese Antwort ⟶ Use Claude – with a question: only for this answer
OpenAI (ChatGPT) nutzen ⟶ Use OpenAI (ChatGPT)
DeepSeek nutzen ⟶ Use DeepSeek
Gemini nutzen ⟶ Use Gemini
Lokale KI (Ollama) – z. B. /ollama qwen2.5:7b ⟶ Local AI (Ollama) – e.g. /ollama qwen2.5:7b
Dein eigenes Lumen-Modell (lokal) ⟶ Your own Lumen model (local)
Auto: Einfaches lokal, Schweres in der Cloud ⟶ Auto: simple things local, hard things in the cloud
Modell anzeigen oder ändern ⟶ Show or change model
Deep Research mit Quellen und Bericht ⟶ Deep Research with sources and report
Alle Chats anzeigen ⟶ Show all chats
Letzte Antwort kopieren ⟶ Copy last answer
Chat als Word/PDF speichern ⟶ Save chat as Word/PDF
Laufende Antwort abbrechen ⟶ Cancel the current answer
Wetter heute und morgen ⟶ Weather today and tomorrow
Was steht heute und morgen an? ⟶ What's on today and tomorrow?
Erinnerung setzen, z. B. /erinnerung morgen 9 Uhr Zahnarzt ⟶ Set a reminder, e.g. /erinnerung tomorrow 9am dentist
Wie geht es meinem Server? ⟶ How is my server doing?
Lumen baut sich ein neues Werkzeug ⟶ Lumen builds itself a new tool
Buch schreiben im Studio ⟶ Write a book in the Studio
Tages-Briefing jetzt schicken ⟶ Send the daily briefing now
Wissen, Lernen & Schreiben ⟶ Knowledge, learning & writing
KI-Labor (eigene KI, Training) ⟶ AI Lab (own AI, training)
Apps & Plugins ⟶ Apps & plugins
Lumen-Server & Briefing ⟶ Lumen server & briefing
Schnell bewerten (fürs Training) ⟶ Quick rating (for training)
Antworten vorlesen an/aus ⟶ Read answers aloud on/off
„Hey Lumen“ an/aus ⟶ “Hey Lumen” on/off
Kraftausdrücke an/aus ⟶ Swearing on/off
Charakter wechseln (freundlich, kumpel, frech, butler …) ⟶ Change character (friendly, buddy, cheeky, butler …)
Sprache / language ⟶ Language / Sprache
Verbrauch & Kosten ⟶ Usage & costs
Eigenen Befehl anlegen, z. B. /befehl zocken = Öffne Discord und Steam ⟶ Create your own command, e.g. /befehl gaming = Open Discord and Steam
Alle Befehle anzeigen ⟶ Show all commands
Unbekannter Befehl /{} – /hilfe zeigt alle. ⟶ Unknown command /{} – /hilfe shows all.
✓ /{} angelegt ⟶ ✓ /{} created
/{} gibt es schon. ⟶ /{} already exists.
So: /befehl zocken = Öffne Discord und Steam ⟶ Like this: /befehl gaming = Open Discord and Steam
z. B. /erinnerung morgen 9 Uhr Zahnarzt ⟶ e.g. /erinnerung tomorrow 9am dentist
Der Chat ist noch leer. ⟶ The chat is still empty.
Noch keine Antwort. ⟶ No answer yet.
🔊 Vorlesen an ⟶ 🔊 Read aloud on
🔇 Vorlesen aus ⟶ 🔇 Read aloud off
🤬 Fluchen erlaubt ⟶ 🤬 Swearing allowed
😇 Fluchen aus ⟶ 😇 Swearing off
🛰️ Lumen-Server ⟶ 🛰️ Lumen Server
Lumen rund um die Uhr auf deinem Server: Tages-Briefing, Erinnerungen und Chat per Telegram – auch wenn der PC aus ist. ⟶ Lumen around the clock on your server: daily briefing, reminders and chat via Telegram – even when your PC is off.
↻ Abgleichen ⟶ ↻ Sync
⚙ Verwalten ⟶ ⚙ Manage
● online ⟶ ● online
● offline ⟶ ● offline
Briefing vom PC ⟶ Briefing from PC
Läuft auf {} · Telegram-Bot aktiv · Briefing {} ⟶ Running on {} · Telegram bot active · briefing {}
Läuft auf {} · Telegram-Bot aktiv ⟶ Running on {} · Telegram bot active
Läuft auf {} · Telegram: {} ⟶ Running on {} · Telegram: {}
Läuft auf {} · Briefing {} ⟶ Running on {} · briefing {}
Läuft auf {} ⟶ Running on {}
Nicht erreichbar: {} ⟶ Not reachable: {}
Keine Meldung von {} – läuft der Server? ⟶ No signal from {} – is the server running?
Abgeglichen ✓ ⟶ Synced ✓
🛰️ Lumen-Server & Briefing ⟶ 🛰️ Lumen Server & Briefing
1 · Lumen auf deinem Server ⟶ 1 · Lumen on your server
nicht eingerichtet ⟶ not set up
Ein zweites Lumen läuft 24/7 auf deinem Linux-Server (ohne Bildschirm). Es schickt dir das Tages-Briefing und Erinnerungen per Telegram, du kannst ihm vom Handy schreiben – und es arbeitet mit Lumen auf dem PC zusammen: Aufgaben, Notizen, Gedächtnis und Erinnerungen bleiben abgeglichen, und „Öffne Discord auf meinem PC“ per Telegram landet hier. Alles über deine SSH-Verbindung, kein offener Port nötig. ⟶ A second Lumen runs 24/7 on your Linux server (no screen). It sends you the daily briefing and reminders via Telegram, you can message it from your phone – and it works together with Lumen on your PC: tasks, notes, memory and reminders stay in sync, and “Open Discord on my PC” via Telegram lands here. All over your SSH connection, no open port needed.
⚠ Erst einen Server speichern (Karte „Server“ → + Server hinzufügen) und den SSH-Key einrichten. ⟶ ⚠ First save a server (card “Servers” → + Add server) and set up the SSH key.
↻ Aktualisieren / neu installieren ⟶ ↻ Update / reinstall
🚀 Auf diesem Server installieren ⟶ 🚀 Install on this server
online · {} ⟶ online · {}
offline ⟶ offline
Telegram-Bot: {} ⟶ Telegram bot: {}
abgeglichen {} ⟶ synced {}
↻ Jetzt abgleichen ⟶ ↻ Sync now
📱 Test-Nachricht ⟶ 📱 Test message
📜 Logs ⟶ 📜 Logs
⟳ Neu starten ⟶ ⟳ Restart
■ Stoppen ⟶ ■ Stop
🗑 Entfernen ⟶ 🗑 Remove
Neu gestartet ⟶ Restarted
(leer) ⟶ (empty)
API-Keys mit auf den Server nehmen (nötig, damit er antworten und Briefings schreiben kann) ⟶ Take API keys to the server (needed so it can answer and write briefings)
2 · Tages-Briefing ⟶ 2 · Daily briefing
kommt vom Server (auch wenn der PC aus ist) ⟶ comes from the server (even when the PC is off)
kommt vom PC, wenn er an ist ⟶ comes from the PC when it's on
Jeden Morgen eine Nachricht aufs Handy: Wetter, Termine, Aufgaben und Erinnerungen, Server-Zustand und News zu deinen Themen – von Lumen in seiner Persönlichkeit geschrieben. ⟶ A message to your phone every morning: weather, events, tasks and reminders, server health and news on your topics – written by Lumen in its own personality.
Tipp: In den Apps noch verbinden: {} ⟶ Tip: still connect in Apps: {}
Briefing jeden Tag schicken ⟶ Send the briefing every day
Um ⟶ At
Mo ⟶ Mon
Di ⟶ Tue
Mi ⟶ Wed
Do ⟶ Thu
Fr ⟶ Fri
Sa ⟶ Sat
So ⟶ Sun
🌤 Wetter ⟶ 🌤 Weather
📅 Termine ⟶ 📅 Events
✅ Aufgaben & Erinnerungen ⟶ ✅ Tasks & reminders
🖥️ Server-Zustand ⟶ 🖥️ Server health
News zu (optional): z. B. Gaming, Linux, KI ⟶ News about (optional): e.g. gaming, Linux, AI
News-Themen ⟶ News topics
Server-Warnungen sofort per Telegram (Festplatte voll, RAM, Container abgestürzt, Dienst ausgefallen) ⟶ Server alerts instantly via Telegram (disk full, RAM, container crashed, service down)
☀️ Briefing jetzt testen ⟶ ☀️ Test briefing now
Gespeichert – an den Server übertragen ⟶ Saved – sent to the server
3 · Mit Lumen per Telegram schreiben ⟶ 3 · Chat with Lumen via Telegram
Telegram verbunden ⟶ Telegram connected
Telegram nicht verbunden ⟶ Telegram not connected
Schreib deinem Bot einfach wie im Chat – der Server antwortet. Riskante Aktionen bestätigst du mit Knöpfen ✅/❌. Sprachnachrichten, Fotos und PDFs gehen auch. Befehle: /briefing, /status, /erinnerungen, /neu, /stopp. ⟶ Just message your bot like in the chat – the server answers. You confirm risky actions with ✅/❌ buttons. Voice messages, photos and PDFs work too. Commands: /briefing, /status, /erinnerungen, /neu, /stopp.
Damit du Lumen vom Handy schreiben kannst, braucht es den Lumen-Server (Abschnitt 1) – er ist immer online. Ohne Server kann Lumen dir nur Nachrichten schicken. ⟶ To message Lumen from your phone you need the Lumen server (section 1) – it's always online. Without a server Lumen can only send you messages.
Nur deine Chat-ID darf mit dem Bot reden. Passwörter und Seed-Phrasen gehen nie über Telegram. ⟶ Only your chat ID may talk to the bot. Passwords and seed phrases never go over Telegram.
Telegram-Einstellungen ⟶ Telegram settings
Telegram verbinden ⟶ Connect Telegram
Lumen-Server einrichten ⟶ Set up Lumen server
Verbindung prüfen ⟶ Check connection
Dateien kopieren ⟶ Copy files
Python-Umgebung ⟶ Python environment
Dienst einrichten ⟶ Set up service
Einstellungen übertragen ⟶ Transfer settings
Test-Nachricht ⟶ Test message
Schau auf dein Handy 📱 ⟶ Check your phone 📱
Hintergrund + @reboot ⟶ background + @reboot
systemd (startet automatisch) ⟶ systemd (starts automatically)
systemd-Benutzerdienst ⟶ systemd user service
Lumen-Server läuft auf {} ⟶ Lumen server running on {}
Telegram noch nicht verbunden (Apps → Telegram) ⟶ Telegram not connected yet (Apps → Telegram)
📱 Letzte Aufträge per Telegram an den PC: {} ⟶ 📱 Recent tasks sent to the PC via Telegram: {}
Telegram nicht erreichbar (Internet/DNS auf dem Server?) ⟶ Telegram not reachable (internet/DNS on the server?)
Telegram nicht verbunden ⟶ Telegram not connected
Der Server schickt das Briefing gleich per Telegram 📱 ⟶ The server will send the briefing via Telegram shortly 📱
Test-Nachricht angefordert – schau auf dein Handy. ⟶ Test message requested – check your phone.
🧩 Eigene Werkzeuge (Plugins) ⟶ 🧩 Custom tools (plugins)
Plugins sind kleine Python-Dateien, die Lumen neue Fähigkeiten geben. Am einfachsten: Sag Lumen im Chat z. B. „Bau dir ein Werkzeug, das mir den Bitcoin-Kurs in Euro sagt“ – Lumen schreibt den Code, du siehst ihn und bestätigst. ⟶ Plugins are small Python files that give Lumen new abilities. Easiest way: tell Lumen in the chat e.g. “Build yourself a tool that tells me the Bitcoin price in euros” – Lumen writes the code, you see it and confirm.
📂 Ordner ⟶ 📂 Folder
Noch keine Plugins. ⟶ No plugins yet.
an ⟶ on
aus ⟶ off
Code ⟶ Code
An/Aus ⟶ On/Off
Plugin „{}“ löschen? (Landet im Papierkorb-Ordner der Plugins.) ⟶ Delete plugin “{}”? (It goes to the plugins' trash folder.)
⚠ {} ⟶ ⚠ {}
greift aufs Internet/Netzwerk zu ⟶ accesses the internet/network
führt Programme/Befehle aus ⟶ runs programs/commands
kann Dateien löschen ⟶ can delete files
schreibt Dateien ⟶ writes files
führt dynamischen Code aus ⟶ runs dynamic code
berührt Schlüssel/Zugangsdaten ⟶ touches keys/credentials
greift tief ins System ein ⟶ reaches deep into the system
Neues Plugin: {} ⟶ New plugin: {}
Plugin ändern: {} ⟶ Change plugin: {}
Plugin gebaut: {} ⟶ Built plugin: {}
Plugins angesehen ⟶ Viewed plugins
Plugin gelesen: {} ⟶ Read plugin: {}
Erinnerung: {} ⟶ Reminder: {}
Erinnerungen angesehen ⟶ Viewed reminders
Erinnerung gelöscht ⟶ Reminder deleted
An den PC geschickt: {} ⟶ Sent to PC: {}
Server-Zustand geprüft ⟶ Checked server health
Briefing gesendet ⟶ Briefing sent
⏰ Erinnerung: {} ⟶ ⏰ Reminder: {}
📱 Auftrag per Telegram: {} ⟶ 📱 Task via Telegram: {}
Plugin-Werkzeug {} ausführen ⟶ Run plugin tool {}
Kein PulseAudio/PipeWire-Soundserver erreichbar. ⟶ No PulseAudio/PipeWire sound server reachable.
Kein Mikrofon gefunden. ⟶ No microphone found.
Keine Lautsprecher/Kopfhörer gefunden. ⟶ No speakers/headphones found.
Spracherkennung fehlt ({} ⟶ Speech recognition missing ({}
Call-Modus gestartet. ⟶ Call mode started.
Raum-Modus gestartet (nur dein Mikrofon). ⟶ Room mode started (your microphone only).
Beendet. Die Mitschrift wurde gelöscht. ⟶ Ended. The transcript was deleted.
Audioquelle beendet. ⟶ Audio source ended.
Spracherkennung: {} ⟶ Speech recognition: {}
Fehler: {} ⟶ Error: {}
Sprachausgabe: {} ⟶ Speech output: {}
Wiedergabe: {} ⟶ Playback: {}
Protokoll läuft. ⟶ Taking notes.
Dauer: ca. {} Min. · {} Beiträge ⟶ Duration: about {} min · {} entries
📚 aus Dokumenten: {} ⟶ 📚 from documents: {}
Schreiben lassen ⟶ Let it write
Sprachausgabe fehlgeschlagen: {} ⟶ Speech output failed: {}
Stimme {} ist installiert. ⟶ Voice {} is installed.
E-Mail ⟶ Email
📧 E-Mail ⟶ 📧 Email
📧 E-Mail & Kontakte ⟶ 📧 Email & contacts
{} ungelesen ⟶ {} unread
{} neu ⟶ {} new
Einrichten ⟶ Set up
⚙ Verwalten ⟶ ⚙ Manage
Gib Lumen eine eigene E-Mail-Adresse (z. B. bei GMX oder Gmail) und/oder verbinde dein Postfach – dann liest, sortiert und schreibt Lumen Mails für dich. ⟶ Give Lumen its own email address (e.g. at GMX or Gmail) and/or connect your mailbox – Lumen then reads, sorts and writes mail for you.
Konto bearbeiten ⟶ Edit account
Konto hinzufügen ⟶ Add account
E-Mail-Adresse ⟶ Email address
Passwort (leer lassen = unverändert) ⟶ Password (leave empty = unchanged)
Passwort / App-Passwort ⟶ Password / app password
Server-Einstellungen (werden automatisch erkannt) ⟶ Server settings (detected automatically)
IMAP-Server ⟶ IMAP server
IMAP-Port ⟶ IMAP port
SMTP-Server ⟶ SMTP server
SMTP-Port ⟶ SMTP port
Benutzername ⟶ Username
Benutzername (falls nicht die Adresse) ⟶ Username (if not the address)
🤖 Lumens eigene Adresse ⟶ 🤖 Lumen's own address
📬 Mein Postfach ⟶ 📬 My mailbox
Anzeigename ⟶ Display name
Dein Name ⟶ Your name
Neue Mails melden (Benachrichtigung) ⟶ Report new mail (notification)
Neue Mails melden (Benachrichtigung + Telegram) ⟶ Report new mail (notification + Telegram)
Eine Adresse nur für Lumen (z. B. lumen.max@gmx.de – kostenlos bei GMX, WEB.DE oder Gmail anlegen). Lumen schickt dir darüber Berichte und Dateien, kann Newsletter/Bestätigungen empfangen und – wenn du willst – Aufträge per Mail annehmen. ⟶ An address just for Lumen (e.g. lumen.max@gmx.de – free at GMX, WEB.DE or Gmail). Lumen sends you reports and files from it, can receive newsletters/confirmations and – if you like – accept tasks by mail.
Dein eigenes Postfach: Lumen kann Mails lesen, zusammenfassen, sortieren, Antworten vorschlagen und (nach deinem OK) senden. ⟶ Your own mailbox: Lumen can read, summarize and sort mail, suggest replies and (after your OK) send them.
Aufträge per Mail annehmen (Lumen erledigt sie und antwortet per Mail) ⟶ Accept tasks by mail (Lumen does them and replies by mail)
Nur von diesen Absendern (leer = deine Postfächer) ⟶ Only from these senders (empty = your mailboxes)
Code-Wort im Betreff (optional, mehr Schutz) ⟶ Code word in the subject (optional, more protection)
z. B. Banane42 ⟶ e.g. Banana42
Schutz: nur erlaubte Absender, deren Absender der Mail-Server bestätigt (DKIM/DMARC); riskante Aktionen sind bei Mail-Aufträgen immer gesperrt. ⟶ Protection: only allowed senders whose identity the mail server confirms (DKIM/DMARC); risky actions are always blocked for mail tasks.
Speichern & testen ⟶ Save & test
Konten ⟶ Accounts
Noch keine Konten. Tipp: Leg Lumen eine eigene Adresse an (z. B. bei GMX: kostenlos, IMAP in den Einstellungen erlauben) – dann kann Lumen dir Berichte schicken und Aufträge per Mail annehmen. Dein eigenes Postfach kannst du zusätzlich verbinden. ⟶ No accounts yet. Tip: create an address for Lumen (e.g. at GMX: free, allow IMAP in the settings) – then Lumen can send you reports and accept tasks by mail. You can connect your own mailbox as well.
Lumens Adresse ⟶ Lumen's address
dein Postfach ⟶ your mailbox
{} ungelesen ⟶ {} unread
meldet neue ⟶ reports new
nimmt Aufträge an ⟶ accepts tasks
Testen ⟶ Test
Bearbeiten ⟶ Edit
Entfernen ⟶ Remove
Konto {} aus Lumen entfernen? ⟶ Remove account {} from Lumen?
＋ Lumens eigene Adresse ⟶ ＋ Lumen's own address
＋ Mein Postfach verbinden ⟶ ＋ Connect my mailbox
↻ Ungelesene zählen ⟶ ↻ Count unread
Kontakte & Signatur ⟶ Contacts & signature
Kontakte ⟶ Contacts
Signatur ⟶ Signature
Kontakte – damit „Schreib Mama eine Mail …“ klappt (eine Zeile pro Kontakt: Name = Adresse): ⟶ Contacts – so “Email mom …” works (one line per contact: name = address):
Signatur unter deinen Mails: ⟶ Signature under your mails:
Neue Mails melden (gilt für Konten mit „melden“) ⟶ Report new mail (for accounts with “report”)
Was Lumen damit kann ⟶ What Lumen can do with it
„Was ist neu in meinem Postfach?“ · „Fass die Mail von Amazon zusammen“ · „Antworte dem Vermieter, dass Dienstag passt“ · „Schick mir den Bericht als PDF an meine Adresse“ · „Schreib Mama eine Mail, dass ich später komme“ · „Lösch alle Newsletter von heute“ – Senden und Löschen fragt immer nach. Per Telegram: /mails und /mail. Im Briefing: „📧 Ungelesene Mails“ anhaken. ⟶ “What's new in my mailbox?” · “Summarize the mail from Amazon” · “Tell the landlord Tuesday works” · “Send me the report as PDF to my address” · “Email mom that I'll be late” · “Delete all newsletters from today” – sending and deleting always ask first. Via Telegram: /mails and /mail. In the briefing: tick “📧 Unread mail”.
📧 Ungelesene Mails ⟶ 📧 Unread mail
Ungelesene E-Mails zusammenfassen ⟶ Summarize unread emails
E-Mail schreiben, z. B. /mail Mama: komme später ⟶ Write an email, e.g. /mail Mom: I'll be late
<an wen: was> ⟶ <to whom: what>
Gespeichert ⟶ Saved
Schritt {}/{}: {} ⟶ Step {}/{}: {}
📈 Krypto-Trading ⟶ 📈 Crypto trading
Krypto-Trading ⟶ Crypto trading
Üben mit Spielgeld oder echt tauschen mit Phantom. ⟶ Practice with play money or swap for real with Phantom.
Öffnen ⟶ Open
Übung {} € ⟶ Practice {} €
🎮 Übungsdepot ⟶ 🎮 Practice portfolio
👻 Echt tauschen (Phantom) ⟶ 👻 Real swap (Phantom)
🔔 Alarme & Orders ⟶ 🔔 Alerts & orders
Keine Anlageberatung. Krypto schwankt stark – bis zum Totalverlust. Lumen kennt nie deine Seed-Phrase oder deinen privaten Schlüssel; echte Tausche führst nur du in Phantom aus. ⟶ Not financial advice. Crypto is highly volatile – up to total loss. Lumen never knows your seed phrase or private key; only you execute real swaps in Phantom.
Depotwert ⟶ Portfolio value
Gewinn/Verlust ⟶ Profit/loss
Freies Spielgeld ⟶ Free play money
Gestartet ⟶ Started
seit {} ⟶ since {}
Kurs ⟶ Price
24 h ⟶ 24 h
7 Tage ⟶ 7 days
30 Tage ⟶ 30 days
1 Jahr ⟶ 1 year
Lade Chart … ⟶ Loading chart …
Handeln (Übung) ⟶ Trade (practice)
Aktion ⟶ Action
Kaufen ⟶ Buy
Verkaufen ⟶ Sell
Coin ⟶ Coin
Betrag € ⟶ Amount €
oder Anteil ⟶ or share
Betrag in € ⟶ Amount in €
🎮 Ausführen (Spielgeld) ⟶ 🎮 Execute (play money)
Echte Kurse, simulierte Gebühr 0,3 %. Probier Strategien ohne Risiko aus – oder frag Lumen: „Kauf im Übungsdepot für 100 € SOL und setz einen Stop-Loss bei −10 %“. ⟶ Real prices, simulated 0.3% fee. Try strategies risk-free – or ask Lumen: “Buy €100 of SOL in the practice portfolio and set a stop-loss at −10%”.
Positionen ⟶ Positions
Noch nichts gekauft. ⟶ Nothing bought yet.
Menge ⟶ Amount
Wert ⟶ Value
Gewinn ⟶ Profit
Letzte Trades ⟶ Recent trades
Neu anfangen ⟶ Start over
Startbetrag € ⟶ Starting amount €
↺ Depot zurücksetzen ⟶ ↺ Reset portfolio
Übungsdepot wirklich zurücksetzen? ⟶ Really reset the practice portfolio?
Echter Tausch auf Solana ⟶ Real swap on Solana
Deine Wallet: {} (aus Apps → Krypto). ⟶ Your wallet: {} (from Apps → Crypto).
Tipp: Trag unter Apps → Krypto deine öffentliche Phantom-Adresse ein – dann sieht Lumen deinen Kontostand (nur lesen). ⟶ Tip: add your public Phantom address under Apps → Crypto – Lumen then sees your balance (read-only).
So funktioniert's: Lumen holt den besten Kurs bei Jupiter und zeigt dir alles an. Erst wenn du in Phantom „Bestätigen“ drückst, wird getauscht. Lumen selbst kann nichts ausführen. ⟶ How it works: Lumen gets the best price from Jupiter and shows you everything. Only when you press “Confirm” in Phantom is the swap made. Lumen itself can't execute anything.
Von ⟶ From
Nach ⟶ To
in ⟶ in
Kurs holen & vorbereiten ⟶ Get price & prepare
Hole Kurs … ⟶ Getting price …
Mindestens {} ⟶ At least {}
👻 In Phantom bestätigen ⟶ 👻 Confirm in Phantom
In Phantom bestätigen ⟶ Confirm in Phantom
Bei Jupiter öffnen ⟶ Open on Jupiter
Öffnet eine Seite in deinem Browser (dort, wo Phantom installiert ist). Phantom zeigt den Tausch noch einmal – erst dein „Bestätigen“ führt ihn aus. ⟶ Opens a page in your browser (where Phantom is installed). Phantom shows the swap again – only your “Confirm” executes it.
Sicherheits-Limits ⟶ Safety limits
Max. € pro Tausch ⟶ Max € per swap
Max. Slippage % ⟶ Max slippage %
Deine echten Tausche ⟶ Your real swaps
Noch keine. ⟶ None yet.
Neuer Alarm / Order ⟶ New alert / order
Art ⟶ Type
🔔 Alarm: Kurs über ⟶ 🔔 Alert: price above
🔔 Alarm: Kurs unter ⟶ 🔔 Alert: price below
🎮 Limit-Kauf (Übung) ⟶ 🎮 Limit buy (practice)
🎮 Stop-Loss (Übung) ⟶ 🎮 Stop-loss (practice)
🎮 Gewinnmitnahme (Übung) ⟶ 🎮 Take profit (practice)
Kurs € ⟶ Price €
€ (Kauf) / % (Verkauf) ⟶ € (buy) / % (sell)
Anlegen ⟶ Create
Alarme melden sich am PC und per Telegram (Lumen prüft jede Minute, solange Lumen läuft). Orders laufen nur im Übungsdepot – echte Tausche bestätigst du immer selbst. ⟶ Alerts notify you on the PC and via Telegram (checked every minute while Lumen runs). Orders only run in the practice portfolio – you always confirm real swaps yourself.
Offen ⟶ Open
Keine offenen Alarme oder Orders. ⟶ No open alerts or orders.
Krypto-Trading öffnen (Übung & Phantom) ⟶ Open crypto trading (practice & Phantom)
Krypto-Kurse, z. B. /kurs sol btc ⟶ Crypto prices, e.g. /kurs sol btc
Üben: /trade kauf 50 € SOL · echt: /trade echt 0.1 SOL zu USDC ⟶ Practice: /trade buy €50 SOL · real: /trade real 0.1 SOL to USDC
Kurs-Alarm, z. B. /alarm SOL über 200 ⟶ Price alert, e.g. /alarm SOL above 200
<Coins> ⟶ <coins>
<Auftrag> ⟶ <order>
<Coin über/unter Kurs> ⟶ <coin above/below price>
Betrag eingeben ⟶ Enter amount
Menge eingeben ⟶ Enter amount
Limits gespeichert ⟶ Limits saved
Nächste Schritte vorschlagen ⟶ Suggest next steps
Unter jeder Antwort 2–3 Knöpfe mit passenden Folgefragen. ⟶ 2–3 buttons with fitting follow-up questions under each answer.
Von selbst Hinweise geben ⟶ Give hints on its own
Lumen meldet sich, wenn gleich ein Termin beginnt, und schlägt auf der Startseite Passendes vor. ⟶ Lumen notifies you when an event is about to start and suggests fitting things on the start page.
Einklappen: {} ⟶ Collapse: {}
Aufklappen: {} ⟶ Expand: {}
🛡️ Sicherheits-Zentrale ⟶ 🛡️ Security center
💻 PC-Check ⟶ 💻 PC check
📶 Heimnetz ⟶ 📶 Home network
📡 Funk ⟶ 📡 Radio
Nur für deine eigenen Geräte, Netze und Webseiten. Funk wird ausschließlich empfangen – Lumen sendet nie. ⟶ Only for your own devices, networks and websites. Radio is receive-only – Lumen never transmits.
Wie sicher ist dieser PC? ⟶ How secure is this PC?
Prüft Firewall, offene Dienste, SSH, Updates, Verschlüsselung, Bildschirmsperre und fehlgeschlagene Anmeldungen. Ändert nichts. ⟶ Checks firewall, open services, SSH, updates, encryption, screen lock and failed logins. Changes nothing.
Jetzt prüfen ⟶ Check now
↻ Nochmal prüfen ⟶ ↻ Check again
💬 Lumen fragen, was ich tun soll ⟶ 💬 Ask Lumen what to do
💬 Lumen erklären lassen ⟶ 💬 Let Lumen explain
Wer ist in meinem Netz? ⟶ Who is on my network?
Zeigt alle Geräte in deinem WLAN/LAN und merkt sich, welche du kennst. Neue Geräte fallen so sofort auf. ⟶ Shows all devices on your Wi-Fi/LAN and remembers which you know. New devices stand out immediately.
Netz scannen ⟶ Scan network
↻ Neu scannen ⟶ ↻ Rescan
Kenne ich ⟶ I know it
Name geben … ⟶ Give a name …
Heimnetz-Wächter: neue Geräte von selbst melden (prüft alle 10 Minuten) ⟶ Network watch: report new devices automatically (checks every 10 minutes)
Angeschlossene USB-Geräte ⟶ Connected USB devices
↻ Aktualisieren ⟶ ↻ Refresh
Vergessen ⟶ Forget
Vertrauen ⟶ Trust
USB-Wächter ⟶ USB watch
Meldet sich, sobald etwas Neues angesteckt wird. Ein fremder „USB-Stick“, der sich als Tastatur ausgibt (BadUSB), kann in Sekunden Befehle eintippen – Lumen warnt dich sofort, auch per Telegram. ⟶ Notifies you as soon as something new is plugged in. A foreign “USB stick” posing as a keyboard (BadUSB) can type commands within seconds – Lumen warns you at once, also via Telegram.
Aus ⟶ Off
Wichtiges melden (unbekannte Tastaturen, Netzwerk-Adapter, Funk-Hardware) ⟶ Report important things (unknown keyboards, network adapters, radio hardware)
Alles melden, was angesteckt wird ⟶ Report everything that is plugged in
Funk-Hardware (HackRF / RTL-SDR) ⟶ Radio hardware (HackRF / RTL-SDR)
↻ Neu suchen ⟶ ↻ Search again
Spektrum-Scan ⟶ Spectrum scan
Zeigt, auf welchen Frequenzen um dich herum gerade gesendet wird – und welcher Funkdienst das ist. Gemessen wird nur die Stärke, kein Inhalt. ⟶ Shows which frequencies around you are in use – and which radio service it is. Only strength is measured, never content.
Eigenen Bereich scannen ⟶ Scan custom range
Keine deutlichen Signale in diesem Bereich. ⟶ No clear signals in this range.
Signal-Test: Sendet meine Fernbedienung? ⟶ Signal test: is my remote transmitting?
Für deine eigenen Geräte: 1. Ruhe messen. 2. Taste gedrückt halten und nochmal messen. Lumen sagt dir, ob und auf welcher Frequenz sie sendet (z. B. um eine leere Batterie zu finden). Es wird nichts aufgezeichnet. ⟶ For your own devices: 1. Measure idle. 2. Hold the button and measure again. Lumen tells you whether and on which frequency it transmits (e.g. to spot a dead battery). Nothing is recorded.
1. Ruhe messen ⟶ 1. Measure idle
2. Mit gedrückter Taste messen ⟶ 2. Measure with button held
Domain-Report ⟶ Domain report
Rundum-Blick auf eine Website aus öffentlichen Quellen: Registrierung, Mail-Schutz gegen Fälschungen (SPF/DMARC), HTTPS-Zertifikat, Sicherheits-Header, bekannte Subdomains. Ideal für deine eigene Seite – oder um einen Shop vor dem Bestellen zu prüfen. ⟶ All-round view of a website from public sources: registration, mail spoofing protection (SPF/DMARC), HTTPS certificate, security headers, known subdomains. Ideal for your own site – or to check a shop before ordering.
Bericht erstellen ⟶ Create report
Sicherheits-Zentrale: PC-Check, Heimnetz, USB, Funk, Domain ⟶ Security center: PC check, home network, USB, radio, domain
USB-Geräte & USB-Wächter ⟶ USB devices & USB watch
HackRF/RTL-SDR: Spektrum-Scan & Signal-Test ⟶ HackRF/RTL-SDR: spectrum scan & signal test
Wer ist in meinem WLAN? ⟶ Who is on my Wi-Fi?
Domain-Report, z. B. /domain meine-seite.de ⟶ Domain report, e.g. /domain my-site.com
🎓 Lernen ⟶ 🎓 Learn
Karteikarten ⟶ Flashcards
🃏 Karteikarten ⟶ 🃏 Flashcards
🧑‍💻 Hacking-Lernpfad ⟶ 🧑‍💻 Hacking course
Karteikarten mit täglicher Wiederholung und ein Hacking-Lernpfad mit Lumen als Lehrer. ⟶ Flashcards with daily review and a hacking course with Lumen as your teacher.
{} fällig ⟶ {} due
Heute fällig ⟶ Due today
Heute gelernt ⟶ Studied today
Serie ⟶ Streak
Tage am Stück ⟶ days in a row
▶ Jetzt lernen ({} Karten) ⟶ ▶ Study now ({} cards)
Stapel ⟶ Decks
Noch keine Karten. Sag Lumen ein Thema – oder lass dir im Studio aus einem PDF Karteikarten machen und übernimm sie hierher. ⟶ No cards yet. Give Lumen a topic – or create flashcards from a PDF in the Studio and import them here.
Nichts fällig ⟶ Nothing due
Lernen ({}) ⟶ Study ({})
Neue Karten von Lumen ⟶ New cards from Lumen
Erstellen lassen ⟶ Create
Eigene Karte ⟶ Own card
Vorderseite (Frage) ⟶ Front (question)
Rückseite (Antwort) ⟶ Back (answer)
＋ Hinzufügen ⟶ ＋ Add
Abends erinnern, wenn Karten fällig sind (PC + Telegram – dort lernst du mit /lernen) ⟶ Remind me in the evening when cards are due (PC + Telegram – study there with /lernen)
Antwort zeigen (Leertaste) ⟶ Show answer (space)
🔁 Nochmal ⟶ 🔁 Again
😬 Schwer ⟶ 😬 Hard
🙂 Gut ⟶ 🙂 Good
😎 Leicht ⟶ 😎 Easy
← Übersicht ⟶ ← Overview
🗑 Karte löschen ⟶ 🗑 Delete card
Zurück zur Übersicht ⟶ Back to overview
🎉 Für heute alles gelernt! ⟶ 🎉 All done for today!
🎓 In den Lern-Trainer übernehmen (tägliche Wiederholung) ⟶ 🎓 Import into the trainer (daily review)
Dein Weg in die Cybersecurity ⟶ Your path into cybersecurity
Lumen ist dein Lehrer: erklärt jede Lektion einfach, macht eine Praxis-Übung mit dir (nur am eigenen PC oder in legalen Übungsumgebungen), stellt 5 Quizfragen und legt Karteikarten für dich an. ⟶ Lumen is your teacher: explains each lesson simply, does a hands-on exercise with you (only on your own PC or in legal practice labs), asks 5 quiz questions and creates flashcards for you.
{} von {} Lektionen geschafft ⟶ {} of {} lessons done
Starten ⟶ Start
Wiederholen ⟶ Repeat
📻 Funk-Empfang ⟶ 📻 Radio reception
UKW-Radio hören und Flugzeuge über dir sehen – mit HackRF oder RTL-SDR. ⟶ Listen to FM radio and see planes above you – with HackRF or RTL-SDR.
📻 Radio ⟶ 📻 Radio
✈️ Flugzeuge ⟶ ✈️ Planes
⏹ Aus ⟶ ⏹ Off
📻 UKW-Radio ⟶ 📻 FM radio
Nur Empfang von Rundfunk und öffentlich ausgestrahlten Flugzeug-Positionen. Der Empfänger kann immer nur eines gleichzeitig: Radio, Flugzeuge oder Spektrum-Scan. ⟶ Receive-only: broadcast radio and publicly transmitted aircraft positions. The receiver can do only one thing at a time: radio, planes or spectrum scan.
Radio ist aus ⟶ Radio is off
Meine Sender ⟶ My stations
Frequenz einstellen ⟶ Tune frequency
▶ Abspielen ⟶ ▶ Play
Sendersuche ⟶ Station scan
Sucht das UKW-Band (87,5–108 MHz) nach starken Sendern ab. Gib gefundenen Sendern einen Namen, dann erscheinen sie oben als Knopf – und du kannst sagen: „Mach Radio Eins an“. ⟶ Scans the FM band (87.5–108 MHz) for strong stations. Name the ones found and they appear as buttons above – and you can say: “Turn on Radio One”.
🔎 Sender suchen ⟶ 🔎 Scan stations
Braucht einen HackRF (oder RTL-SDR) mit Antenne. DAB+ kann Lumen noch nicht abspielen – dafür gibt es das Programm welle.io. ⟶ Needs a HackRF (or RTL-SDR) with antenna. Lumen can't play DAB+ yet – use the welle.io app for that.
Flugzeuge über dir ⟶ Planes above you
Flugzeuge senden ihre Position selbst aus (ADS-B, 1090 MHz). Lumen empfängt das direkt mit deinem HackRF – ohne Internet. ⟶ Aircraft broadcast their own position (ADS-B, 1090 MHz). Lumen receives it directly with your HackRF – no internet needed.
▶ Empfang starten ⟶ ▶ Start receiving
⏹ Empfang stoppen ⟶ ⏹ Stop receiving
💬 Lumen fragen ⟶ 💬 Ask Lumen
Noch nichts empfangen – das dauert bis zu einer Minute. Antenne ans Fenster, möglichst hoch. ⟶ Nothing received yet – this can take up to a minute. Put the antenna by the window, as high as possible.
Mein Standort ⟶ My location
Für Entfernung, Richtung und das Radar braucht Lumen deinen ungefähren Standort (wird nur lokal gespeichert). ⟶ For distance, direction and the radar Lumen needs your approximate location (stored locally only).
Einmalig einrichten: im Lumen-Ordner „bash setup-adsb.sh“ ausführen (baut das Empfangsprogramm dump1090 mit HackRF-Unterstützung). ⟶ One-time setup: run “bash setup-adsb.sh” in the Lumen folder (builds the dump1090 receiver with HackRF support).
Telegram: mit Stimme antworten ⟶ Telegram: answer by voice
Wenn ich eine Sprachnachricht schicke (und bei /anruf) ⟶ When I send a voice message (and during /anruf)
Immer zusätzlich als Sprachnachricht ⟶ Always also as a voice message
Nie – nur Text ⟶ Never – text only
Karteikarten lernen (tägliche Wiederholung) ⟶ Study flashcards (daily review)
Hacking-Lernpfad: Cybersecurity Schritt für Schritt ⟶ Hacking course: cybersecurity step by step
UKW-Radio über den HackRF, z. B. /radio 100.3 ⟶ FM radio via HackRF, e.g. /radio 100.3
Flugzeuge über dir (ADS-B) ⟶ Planes above you (ADS-B)
Unterwegs meistens (für Fahrzeiten zu Terminen) ⟶ Usually travelling (for travel times to events)
🚗 Mit dem Auto ⟶ 🚗 By car
🚲 Mit dem Fahrrad ⟶ 🚲 By bike
🚶 Zu Fuß ⟶ 🚶 On foot
🤖 Autopilot ⟶ 🤖 Autopilot
Geplante Aufgaben, Heartbeat, selbst gelernte Fähigkeiten und Browser-Steuerung. ⟶ Scheduled tasks, heartbeat, self-learned skills and browser control.
{} aktiv ⟶ {} active
⏱ Automationen ⟶ ⏱ Automations
💓 Heartbeat ⟶ 💓 Heartbeat
🧠 Fähigkeiten ⟶ 🧠 Skills
🌐 Browser ⟶ 🌐 Browser
Geplante KI-Aufgaben ⟶ Scheduled AI tasks
Lumen erledigt Aufgaben von selbst nach Zeitplan und schickt dir das Ergebnis – z. B. jeden Morgen die News, jeden Freitag einen Wochenrückblick, stündlich einen Preis-Check. ⟶ Lumen does tasks on a schedule and sends you the result – e.g. the news every morning, a weekly review every Friday, an hourly price check.
Noch keine. Leg eine an – oder sag im Chat z. B. „Schick mir jeden Morgen um 7 das Wetter und meine Termine“. ⟶ None yet. Create one – or say in chat e.g. “Send me the weather and my events every morning at 7”.
＋ Neue Automation ⟶ ＋ New automation
Neue Automation ⟶ New automation
Automation bearbeiten ⟶ Edit automation
Ideen zum Antippen ⟶ Ideas to tap
▶ Jetzt ⟶ ▶ Now
Pause ⟶ Pause
Aktivieren ⟶ Activate
Name ⟶ Name
Wie oft ⟶ How often
Täglich ⟶ Daily
Wöchentlich ⟶ Weekly
Monatlich ⟶ Monthly
Stündlich ⟶ Hourly
Alle X Minuten ⟶ Every X minutes
Einmal ⟶ Once
Uhrzeit ⟶ Time
Datum ⟶ Date
Tage ⟶ Days
Am Tag ⟶ On day
Zur Minute ⟶ At minute
Alle … Minuten (mind. 15) ⟶ Every … minutes (min. 15)
Auftrag an Lumen ⟶ Task for Lumen
Ergebnis schicken an ⟶ Send result to
💻 PC (Benachrichtigung + Chat) ⟶ 💻 PC (notification + chat)
📱 + 💻 Beides ⟶ 📱 + 💻 Both
🔕 Nur speichern ⟶ 🔕 Just save
Lumen schaut regelmäßig still deine Checkliste durch und meldet sich nur, wenn wirklich etwas ist – per Telegram und am PC. Dabei darf Lumen nur nachsehen, nichts verändern oder senden. ⟶ Lumen quietly goes through your checklist regularly and only reaches out when something really matters – via Telegram and on the PC. It may only look, never change or send anything.
Heartbeat an ⟶ Heartbeat on
Ruhe ab ⟶ Quiet from
bis ⟶ until
Checkliste – ein Punkt pro Zeile, in deinen Worten: ⟶ Checklist – one item per line, in your own words:
💓 Jetzt prüfen ⟶ 💓 Check now
Tipp: Jeder Durchlauf kostet eine KI-Anfrage. Mit einem lokalen Modell (Ollama) ist das kostenlos; mit Cloud-KI lieber alle 60 Minuten. ⟶ Tip: every run costs one AI request. With a local model (Ollama) it's free; with cloud AI better every 60 minutes.
Letzte Durchläufe ⟶ Recent runs
Was Lumen selbst gelernt hat ⟶ What Lumen has learned
Nach längeren Aufgaben schreibt Lumen sich eine Anleitung, wie es geklappt hat – und nutzt sie beim nächsten Mal (und verbessert sie). Es sind reine Text-Anleitungen, kein Code. Du kannst sie lesen, ändern und löschen. ⟶ After longer tasks Lumen writes itself a guide on how it worked – and uses (and improves) it next time. They're plain text guides, not code. You can read, edit and delete them.
Selbst lernen nach längeren Aufgaben (kostet pro gelernter Aufgabe eine kleine KI-Anfrage) ⟶ Learn after longer tasks (one small AI request per learned task)
Ansehen ⟶ View
← Zurück ⟶ ← Back
Wann passt sie? ⟶ When does it apply?
Selbst eine Fähigkeit schreiben oder einfügen ⟶ Write or paste a skill yourself
Übernehmen ⟶ Import
Lumen steuert den Browser ⟶ Lumen controls the browser
Browser ist zu ⟶ Browser is closed
Sicherheit ⟶ Security
Heartbeat: Checkliste & an/aus ⟶ Heartbeat: checklist & on/off
👨‍💻 Code-Werkstatt ⟶ 👨‍💻 Code workshop
Code-Werkstatt ⟶ Code workshop
Projekte erklären lassen, Code-Review mit KI und Linter, Git ohne Terminal: Commits, Branches, Konflikte. ⟶ Get projects explained, code review with AI and linters, Git without a terminal: commits, branches, conflicts.
👨‍💻 Öffnen ⟶ 👨‍💻 Open
🗺 Projekt ⟶ 🗺 Project
🔍 Review ⟶ 🔍 Review
🌿 Git ⟶ 🌿 Git
⚔️ Konflikte ⟶ ⚔️ Conflicts
Alles läuft lokal mit git. Riskante Befehle (force-push, reset --hard, clean) bietet Lumen absichtlich nicht an. Commits mit Passwörtern oder API-Schlüsseln werden gestoppt. ⟶ Everything runs locally with git. Risky commands (force-push, reset --hard, clean) are deliberately not offered. Commits containing passwords or API keys are stopped.
Projektordner, z. B. ~/Projekte/meine-app ⟶ Project folder, e.g. ~/Projects/my-app
🕘 Zuletzt … ⟶ 🕘 Recent …
📂 Wählen ⟶ 📂 Choose
Projekt öffnen ⟶ Open project
Gib oben den Ordner deines Projekts ein (oder wähle ihn). Lumen erklärt dir den Aufbau, prüft deinen Code und hilft bei Git – ganz ohne Terminal. ⟶ Enter your project folder above (or choose it). Lumen explains the structure, reviews your code and helps with Git – no terminal needed.
Lese Projekt … ⟶ Reading project …
🧠 Projekt erklären lassen ⟶ 🧠 Explain project
📝 ARCHITEKTUR.md schreiben ⟶ 📝 Write ARCHITECTURE.md
🚀 Wie starte ich das? ⟶ 🚀 How do I run it?
🔎 Im Code suchen ⟶ 🔎 Search code
Wo wird … benutzt? (Text oder Funktionsname) ⟶ Where is … used? (text or function name)
💬 Fragen ⟶ 💬 Ask
Sucht … ⟶ Searching …
📁 Aufbau ⟶ 📁 Structure
Ordner ⟶ Folders
Wichtige Dateien ⟶ Key files
Abhängigkeiten ⟶ Dependencies
🧩 Gliederung der wichtigsten Dateien ⟶ 🧩 Outline of the main files
💬 Diese Datei erklären ⟶ 💬 Explain this file
🔍 Code-Review ⟶ 🔍 Code review
Lumen prüft deinen Code wie ein erfahrener Kollege: Bugs, Sicherheitslücken, Randfälle, Lesbarkeit. Dazu laufen Linter (ruff, shellcheck …) und eine Suche nach versehentlich eingecheckten Passwörtern/API-Schlüsseln. ⟶ Lumen reviews your code like an experienced colleague: bugs, security holes, edge cases, readability. Linters (ruff, shellcheck …) run too, plus a search for accidentally committed passwords/API keys.
Alle offenen Änderungen ⟶ All open changes
Nur vorgemerkte (staged) ⟶ Staged only
Letzter Commit ⟶ Last commit
Ganzer Branch gegen main ⟶ Whole branch vs. main
Bestimmter Commit ⟶ Specific commit
Eine ganze Datei ⟶ A whole file
Worauf besonders achten? (optional, z. B. Sicherheit) ⟶ Anything to focus on? (optional, e.g. security)
🔍 Review starten ⟶ 🔍 Start review
Prüft … ⟶ Reviewing …
Läuft ⟶ Running
Linter laufen, KI liest den Diff … (je nach Größe 10–60 s) ⟶ Linters running, AI is reading the diff … (10–60 s depending on size)
🔧 Lumen soll das beheben ⟶ 🔧 Let Lumen fix it
👏 Gut gemacht ⟶ 👏 Well done
Kein Git-Projekt ⟶ Not a Git project
Dieser Ordner wird noch nicht mit Git versioniert. ⟶ This folder isn't versioned with Git yet.
🌱 Git hier starten (git init) ⟶ 🌱 Start Git here (git init)
📡 Abgleichen ⟶ 📡 Fetch
git fetch – nur nachsehen, ändert nichts ⟶ git fetch – only checks, changes nothing
📝 Änderungen ({}) ⟶ 📝 Changes ({})
Vorgemerkt für den Commit ⟶ Staged for commit
Noch nicht vorgemerkt ⟶ Not staged yet
＋ Alle vormerken ⟶ ＋ Stage all
✨ Alles committet. ⟶ ✨ Everything committed.
Vormerken ⟶ Stage
Vormerkung aufheben ⟶ Unstage
Verbergen ⟶ Hide
✅ Commit ⟶ ✅ Commit
Commit-Nachricht – oder ✨ von Lumen schreiben lassen ⟶ Commit message – or ✨ let Lumen write it
✨ Nachricht vorschlagen ⟶ ✨ Suggest message
schreibt … ⟶ writing …
Sprache wie bisher ⟶ Same language as before
Englisch ⟶ English
Commit-Nachricht fehlt ⟶ Commit message missing
🔍 Vorher reviewen ⟶ 🔍 Review first
neuer-branch-name ⟶ new-branch-name
＋ Neuer Branch ⟶ ＋ New branch
Wechseln ⟶ Switch
🕘 Verlauf ⟶ 🕘 History
Diesen Commit reviewen ⟶ Review this commit
Zurücknehmen (Änderungen bleiben) ⟶ Undo (changes are kept)
Zwei Versionen derselben Stelle passen nicht zusammen. Wähle pro Datei: unsere Version, ihre Version – oder lass Lumen beides sinnvoll zusammenführen. ⟶ Two versions of the same spot don't fit together. Per file choose: our version, their version – or let Lumen merge both sensibly.
Keine Konflikte. 🎉 ⟶ No conflicts. 🎉
Unsere (aktueller Branch) ⟶ Ours (current branch)
Ihre (wird eingemischt) ⟶ Theirs (being merged in)
🧠 Lumen zusammenführen lassen ⟶ 🧠 Let Lumen merge
🧠 Neuer Vorschlag ⟶ 🧠 New suggestion
✅ Lumens Lösung übernehmen ⟶ ✅ Apply Lumen's solution
Unsere nehmen ⟶ Take ours
Ihre nehmen ⟶ Take theirs
denkt … ⟶ thinking …
Code-Werkstatt: Projekt, Review, Git ⟶ Code workshop: project, review, git
Code-Review der offenen Änderungen ⟶ Code review of open changes
Git-Assistent: Status, Commit, Branches ⟶ Git assistant: status, commit, branches
📷 Kameras ⟶ 📷 Cameras
Kameras ⟶ Cameras
Deine IP-Überwachungskameras: Live-Bild und Schnappschuss – hier und per Telegram /kamera. ⟶ Your IP security cameras: live view and snapshot – here and via Telegram /kamera.
📷 Öffnen ⟶ 📷 Open
＋ Kamera ⟶ ＋ Camera
▶ Alle live ⟶ ▶ All live
＋ Kamera hinzufügen ⟶ ＋ Add camera
Bilder bleiben nur im Speicher und werden nicht aufgezeichnet. Zugangsdaten liegen nur auf diesem Gerät (nie an die KI, nie per Telegram). Bitte nur das eigene Grundstück filmen – öffentliche Wege und Nachbarn sind in Deutschland meist tabu. ⟶ Images stay in memory only and are not recorded. Credentials stay on this device only (never sent to the AI or Telegram). Please only film your own property – public paths and neighbours are usually off-limits.
lädt … ⟶ loading …
ausgeschaltet ⟶ switched off
holt Bild … ⟶ getting picture …
▶ Live ⟶ ▶ Live
⏹ Stopp ⟶ ⏹ Stop
gestoppt ⟶ stopped
🔴 live ⟶ 🔴 live
⚠️ Live-Bild abgebrochen ⟶ ⚠️ Live view interrupted
Neues Bild ⟶ New picture
Vollbild ⟶ Fullscreen
Bild speichern ⟶ Save picture
Erst ein Bild holen (📸) ⟶ Get a picture first (📸)
Bearbeiten ⟶ Edit
Ausschalten ⟶ Switch off
Einschalten ⟶ Switch on
Kamera „{}“ entfernen? Die Zugangsdaten werden gelöscht. ⟶ Remove camera “{}”? Its credentials will be deleted.
ffmpeg fehlt – installieren mit: sudo apt install ffmpeg ⟶ ffmpeg is missing – install with: sudo apt install ffmpeg
z. B. Haustür, Garten ⟶ e.g. Front door, Garden
🔍 automatisch erkennen ⟶ 🔍 detect automatically
(unverändert) ⟶ (unchanged)
Passwort der Kamera ⟶ Camera password
rtsp://192.168.1.50:554/stream1 (nur wenn die Erkennung nicht klappt) ⟶ rtsp://192.168.1.50:554/stream1 (only if detection fails)
💡 Lumen probiert die üblichen Stream-Adressen der bekannten Marken durch (mit deinem Passwort – es rät keine Passwörter). ⟶ 💡 Lumen tries the usual stream addresses of known brands (with your password – it never guesses passwords).
🔌 Verbindung testen ⟶ 🔌 Test connection
IP-Adresse fehlt ⟶ IP address missing
Verbinde … (kann bis 30 s dauern) ⟶ Connecting … (may take up to 30 s)
💾 Speichern ⟶ 💾 Save
➕ Hinzufügen ⟶ ➕ Add
Verbinde und speichere … ⟶ Connecting and saving …
📡 Im Netz suchen ⟶ 📡 Search network
sucht … (ca. 10 s) ⟶ searching … (approx. 10 s)
⚙ {} bearbeiten ⟶ ⚙ Edit {}
IP-Kameras im WLAN/LAN (Reolink, Tapo, Hikvision, Dahua/Imou, eufy, Foscam, Axis, ONVIF …) verbindet Lumen über RTSP. ⟶ Lumen connects IP cameras on your Wi-Fi/LAN (Reolink, Tapo, Hikvision, Dahua/Imou, eufy, Foscam, Axis, ONVIF …) via RTSP.
schon da ⟶ already added
Übernehmen ⟶ Use
Marke ⟶ Brand
IP-Adresse ⟶ IP address
RTSP-Port ⟶ RTSP port
Benutzer ⟶ User
Eigene RTSP-Adresse (für Profis) ⟶ Custom RTSP address (advanced)
RTSP-Adresse ⟶ RTSP address
Benutzer und Passwort trägst du oben ein – nicht in die Adresse. ⟶ Enter user and password above – not in the address.
Ring, Arlo, Blink und Google Nest haben keinen RTSP-Zugang – die gehen nur über die Hersteller-App. ⟶ Ring, Arlo, Blink and Google Nest have no RTSP access – they only work through the maker's app.
Überwachungskamera: Live-Bild & Schnappschuss ⟶ Security camera: live view & snapshot
Such-Bots & GitHub ⟶ Search bots & GitHub
Eigene Metasuche über viele Quellen, Bots, die Themen beobachten, und eine Werkstatt, die Werkzeuge von GitHub holt und lernt. ⟶ Own metasearch across many sources, bots that watch topics, and a workshop that fetches tools from GitHub and learns them.
🔎 Suchen ⟶ 🔎 Search
🧰 Werkstatt ⟶ 🧰 Workshop
🔎 Such-Bots & GitHub-Werkstatt ⟶ 🔎 Search bots & GitHub workshop
🔎 Metasuche ⟶ 🔎 Metasearch
🕵️ Beobachter ⟶ 🕵️ Watchers
🧰 GitHub finden ⟶ 🧰 Find on GitHub
📦 Meine Werkzeuge ⟶ 📦 My tools
Webseiten und READMEs sind für Lumen nur Daten – Anweisungen darin werden nicht befolgt. Installiert wird nur mit deinem OK, isoliert und ohne Admin-Rechte. ⟶ Web pages and READMEs are only data for Lumen – instructions in them are never followed. Installs only happen with your OK, isolated and without admin rights.
Beobachter-Bots: {} · gemeldete Funde: {} · GitHub-Werkzeuge: {} ⟶ Watcher bots: {} · reported finds: {} · GitHub tools: {}
🔎 Such-Bots & GitHub ⟶ 🔎 Search bots & GitHub
Lumens eigene Metasuche ⟶ Lumen's own metasearch
Statt einer Suchmaschine fragen mehrere Such-Bots gleichzeitig – Treffer, die viele Quellen finden, landen oben. Lumen nutzt das auch selbst bei Recherchen. ⟶ Instead of one search engine, several search bots ask at once – hits found by many sources rank first. Lumen uses this for its own research too.
Wonach suchen? z. B. „beste Linux-Tools für PDF“ ⟶ What to search for? e.g. “best Linux tools for PDF”
🎯 automatisch ⟶ 🎯 automatic
Sucht … ⟶ Searching …
Danach Lumen die besten Seiten lesen und zusammenfassen lassen ⟶ Then let Lumen read and summarize the best pages
Suche läuft ⟶ Searching
Die Bots schwärmen aus … ⟶ The bots are swarming out …
Hat nicht geklappt ⟶ That didn't work
{} Treffer · Profil {} · {} s ⟶ {} hits · profile {} · {} s
🕵️ Thema beobachten ⟶ 🕵️ Watch topic
💬 Lumen zusammenfassen lassen ⟶ 💬 Let Lumen summarize
Die Such-Bots ⟶ The search bots
Neuer Beobachter-Bot ⟶ New watcher bot
Ein Bot sucht regelmäßig nach deinem Thema und meldet dir nur das, was neu dazugekommen ist. ⟶ A bot searches your topic regularly and only reports what's new.
Thema, z. B. „HackRF Firmware Update“ ⟶ Topic, e.g. “HackRF firmware update”
Thema ⟶ Topic
Wie oft ⟶ How often
Melden an ⟶ Report to
Muss enthalten ⟶ Must contain
stündlich ⟶ hourly
alle 3 Std ⟶ every 3 h
alle 6 Std ⟶ every 6 h
2× täglich ⟶ twice a day
täglich ⟶ daily
wöchentlich ⟶ weekly
beides ⟶ both
Neue Funde von der KI kurz zusammenfassen lassen ⟶ Let the AI briefly summarize new finds
🕵️ Bot starten ⟶ 🕵️ Start bot
Thema fehlt ⟶ Topic missing
Deine Bots ({}) ⟶ Your bots ({})
Noch keine. Oder in Telegram: /beobachte <Thema> ⟶ None yet. Or in Telegram: /beobachte <topic>
▶ Jetzt ⟶ ▶ Now
Pause ⟶ Pause
Weiter ⟶ Resume
Such-Bot „{}“ löschen? ⟶ Delete search bot “{}”?
Letzte Funde ({}) ⟶ Latest finds ({})
Werkzeug auf GitHub finden ⟶ Find a tool on GitHub
Lumen sucht passende Programme, prüft sie (Sterne, Alter, Lizenz, Warnzeichen), installiert sie mit deinem OK isoliert in einen eigenen Ordner und liest danach README und Hilfe, um sie selbst bedienen zu können. ⟶ Lumen finds suitable programs, checks them (stars, age, license, warning signs), installs them isolated in their own folder after your OK, and then reads the README and help to learn to use them.
Was brauchst du? z. B. „Videos herunterladen“, „pdf compress“, „markdown to pdf“ ⟶ What do you need? e.g. “download videos”, “pdf compress”, “markdown to pdf”
💬 Lumen aussuchen lassen ⟶ 💬 Let Lumen choose
⚠️ git fehlt – für Python-/Quellcode-Werkzeuge: sudo apt install git ⟶ ⚠️ git is missing – for Python/source tools: sudo apt install git
Tipp: Ohne GitHub-Token sind es 60 Anfragen pro Stunde. Ein Token (nur Lesen, ohne Rechte) unter Apps → GitHub hebt das auf 5000. ⟶ Tip: without a GitHub token you get 60 requests per hour. A token (read-only, no scopes) under Apps → GitHub raises that to 5000.
📦 fertige Linux-Datei ⟶ 📦 ready-made Linux file
🐍 Python-Paket (venv) ⟶ 🐍 Python package (venv)
📂 Quellcode ⟶ 📂 Source code
🐹 Go bauen ⟶ 🐹 Build with Go
Keine Warnzeichen gefunden. ⟶ No warning signs found.
📥 Installieren & lernen ⟶ 📥 Install & learn
Installiere … (kann dauern) ⟶ Installing … (may take a while)
Auf GitHub ansehen ⟶ View on GitHub
README-Anfang ⟶ README start
← Zurück zu den Treffern ⟶ ← Back to results
Suche … ⟶ Searching …
Frage GitHub … ⟶ Asking GitHub …
{} Repos ⟶ {} repos
🔍 Prüfen ⟶ 🔍 Check
Installierte Werkzeuge ({}) ⟶ Installed tools ({})
Arbeitsordner (Ergebnisse landen hier): {} ⟶ Working folder (results go here): {}
Noch keine. Such im Tab „GitHub finden“ – oder sag Lumen einfach, was du brauchst („Ich will YouTube-Videos als MP3 speichern“). ⟶ None yet. Search in the “Find on GitHub” tab – or just tell Lumen what you need (“I want to save YouTube videos as MP3”).
🧠 Neu lernen ⟶ 🧠 Relearn
Lernt … ⟶ Learning …
Vertrauen ⟶ Trust
Nachfragen ⟶ Ask first
Vertraute Werkzeuge darf Lumen ohne Nachfrage starten ⟶ Lumen may start trusted tools without asking
Neueste Version holen ⟶ Get latest version
„{}“ samt Fähigkeit entfernen? ⟶ Remove “{}” including its skill?
▶ Starten ⟶ ▶ Run
läuft … ⟶ running …
💬 Mit Lumen ⟶ 💬 With Lumen
Eigene Such-Bots fragen viele Quellen parallel ⟶ Own search bots ask many sources in parallel
Such-Bot meldet dir nur Neues zu einem Thema ⟶ A search bot reports only new things on a topic
Werkzeug auf GitHub finden, installieren & lernen ⟶ Find, install & learn a tool from GitHub
Installierte GitHub-Werkzeuge ⟶ Installed GitHub tools
Erster Lauf: {} Treffer gemerkt – ab jetzt meldet der Bot nur Neues. ⟶ First run: {} hits remembered – from now on the bot only reports new ones.
Nichts Neues. ⟶ Nothing new.
{} neue Treffer ⟶ {} new hits
Vertraut – läuft ab jetzt ohne Nachfrage. ⟶ Trusted – runs without asking from now on.
Fragt wieder vor jedem Start. ⟶ Asks again before every run.
Was Lumen selbst gelernt hat ⟶ What Lumen has learned
Automation anlegen, z. B. /automation jeden Morgen um 7 die News ⟶ Create an automation, e.g. /automation the news every morning at 7
🦠 Scanner ⟶ 🦠 Scanner
🩹 Lücken ⟶ 🩹 Vulnerabilities
🛠 Programme ⟶ 🛠 Programs
🧰 Werkzeugkasten ⟶ 🧰 Toolbox
🦠 Dateien & Downloads prüfen ⟶ 🦠 Check files & downloads
Findet getarnte Programme (Rechnung.pdf.exe), Office-Makros, PDFs mit Skripten, Archive mit Programmen; mit ClamAV auch Viren. Verdächtiges wird per Fingerabdruck bei VirusTotal nachgeschlagen – hochgeladen wird nichts. ⟶ Finds disguised programs (invoice.pdf.exe), Office macros, PDFs with scripts, archives containing programs; viruses too with ClamAV. Suspicious files are looked up on VirusTotal by fingerprint – nothing is uploaded.
alle Dateien ⟶ all files
letzte 7 Tage ⟶ last 7 days
letzte 30 Tage ⟶ last 30 days
Prüfen ⟶ Check
🔒 Quarantäne ⟶ 🔒 Quarantine
✅ Nichts Auffälliges. ⟶ ✅ Nothing suspicious.
Download-Wächter: neue Downloads automatisch prüfen und bei Gefahr melden ⟶ Download watch: check new downloads automatically and warn about danger
🔑 Geleakte Passwörter & Schlüssel finden ⟶ 🔑 Find leaked passwords & keys
Sucht in deinen Ordnern nach API-Keys, Tokens, privaten Schlüsseln ohne Passphrase und Passwörtern in Konfig-Dateien – z. B. bevor du ein Projekt auf GitHub hochlädst. Funde werden nur gekürzt angezeigt. ⟶ Searches your folders for API keys, tokens, private keys without passphrase and passwords in config files – e.g. before you push a project to GitHub. Findings are shown masked.
Durchsuchen ⟶ Scan
✅ Nichts gefunden. ⟶ ✅ Nothing found.
🛡️ Wächter für Systemdateien & Rootkit-Check ⟶ 🛡️ System file watch & rootkit check
Lumen merkt sich einen Fingerabdruck von wichtigen Dateien (Login, sudo, SSH-Schlüssel, Autostart, Programme wie ssh/sudo/ls) und meldet, wenn sich etwas ändert – so fallen Hintertüren und Rootkits auf. ⟶ Lumen keeps a fingerprint of important files (login, sudo, SSH keys, autostart, programs like ssh/sudo/ls) and reports changes – that's how backdoors and rootkits stand out.
Als neuen Stand übernehmen ⟶ Accept as new baseline
🔍 rkhunter / chkrootkit (Admin) ⟶ 🔍 rkhunter / chkrootkit (admin)
Alle 6 Stunden automatisch prüfen und Wichtiges melden ⟶ Check automatically every 6 hours and report important changes
🩹 Bekannte Sicherheitslücken in deinen Programmen ⟶ 🩹 Known vulnerabilities in your programs
Vergleicht deine installierten Pakete (Debian/Ubuntu und Python) mit der öffentlichen Schwachstellen-Datenbank OSV.dev. Gesendet werden nur Paketnamen und Versionen. ⟶ Compares your installed packages (Debian/Ubuntu and Python) with the public OSV.dev vulnerability database. Only package names and versions are sent.
🔐 HTTPS-Verschlüsselung prüfen (TLS) ⟶ 🔐 Check HTTPS encryption (TLS)
🧱 PC absichern (ein Klick, mit Bestätigung) ⟶ 🧱 Harden the PC (one click, with confirmation)
Jede Aktion zeigt dir vorher genau, was als Admin ausgeführt wird. SSH-Härtung geht nur, wenn ein SSH-Schlüssel hinterlegt ist (sonst würdest du dich aussperren). ⟶ Each action shows exactly what will run as admin first. SSH hardening only works when an SSH key is set up (otherwise you'd lock yourself out).
Firewall einschalten (ufw) ⟶ Turn on firewall (ufw)
SSH absichern ⟶ Harden SSH
fail2ban installieren ⟶ Install fail2ban
Automatische Sicherheits-Updates ⟶ Automatic security updates
ClamAV installieren ⟶ Install ClamAV
🗺 nmap – Ports & Dienste deiner Geräte ⟶ 🗺 nmap – ports & services of your devices
Scannen ⟶ Scan
Nur eigene Ziele: eigene Server aus Lumen, Geräte im Heimnetz, deine öffentliche IP. ⟶ Own targets only: your servers in Lumen, devices on your home network, your public IP.
🦈 Wireshark – Netzwerkverkehr mitschneiden ⟶ 🦈 Wireshark – capture network traffic
Schneidet den Verkehr DEINES PCs mit (tshark) und zeigt: welche Protokolle, mit wem, welche Webseiten-Namen, ob etwas unverschlüsselt läuft. Die Datei kannst du in Wireshark öffnen. ⟶ Captures YOUR PC's traffic (tshark) and shows: which protocols, with whom, which site names, whether anything is unencrypted. You can open the file in Wireshark.
Standard-Netzwerkkarte ⟶ Default network interface
● Aufnehmen ⟶ ● Record
Wireshark öffnen ⟶ Open Wireshark
In Wireshark öffnen ⟶ Open in Wireshark
📡 Wer redet gerade mit dem Internet? ⟶ 📡 Who is talking to the internet right now?
Verbindungen anzeigen ⟶ Show connections
🔎 Lynis – Sicherheitsaudit des Systems ⟶ 🔎 Lynis – system security audit
Audit starten (1–3 Min) ⟶ Start audit (1–3 min)
🌐 Webseiten-Scanner (nur eigene Seiten) ⟶ 🌐 Website scanners (own sites only)
Meine Domains (eine pro Zeile) – nur diese, eigene Server und localhost dürfen gescannt werden: ⟶ My domains (one per line) – only these, your servers and localhost may be scanned:
Domains speichern ⟶ Save domains
📦 Sicherheits-Programme auf deinem PC ⟶ 📦 Security programs on your PC
installiert ⟶ installed
fehlt ⟶ missing
🧰 Werkzeugkasten (alles lokal, nichts verlässt den PC) ⟶ 🧰 Toolbox (all local, nothing leaves the PC)
📋 Ergebnis kopieren ⟶ 📋 Copy result
🔐 Sichere Passwörter erzeugen ⟶ 🔐 Generate secure passwords
Zufalls-Passwort ⟶ Random password
Merk-Passphrase ⟶ Memorable passphrase
Dateien auf Viren & geleakte Schlüssel prüfen ⟶ Check files for viruses & leaked keys
nmap-Scan eines eigenen Geräts, z. B. /nmap 192.168.1.1 ⟶ nmap scan of your own device, e.g. /nmap 192.168.1.1
Netzwerkverkehr mitschneiden (tshark) ⟶ Capture network traffic (tshark)
Sicherheitslücken in installierten Programmen ⟶ Vulnerabilities in installed programs
Werkzeugkasten: Base64, Hashes, JWT, Passwörter ⟶ Toolbox: Base64, hashes, JWT, passwords
❓ fragt dich ⟶ ❓ asking you
🔍 prüft sich ⟶ 🔍 self-checking
⏸ unterbrochen ⟶ ⏸ interrupted
Deine Antwort … ⟶ Your answer …
Antworten ⟶ Answer
Ohne Antwort macht der Agent in ca. {} Min mit einer eigenen Annahme weiter. ⟶ Without an answer the agent continues with its own assumption in about {} min.
Ohne Antwort macht der Agent in ca. {} Min mit einer eigenen Annahme weiter. Du kannst auch in Telegram antworten. ⟶ Without an answer the agent continues with its own assumption in about {} min. You can also answer in Telegram.
🔍 Selbstprüfung: vollständig ⟶ 🔍 Self-check: complete
📎 Dateien: ⟶ 📎 Files:
🔁 Neu starten ⟶ 🔁 Restart
⚙ Grenzen & Verhalten ⟶ ⚙ Limits & behaviour
Zeitlimit (Min, 0 = keins) ⟶ Time limit (min, 0 = none)
Kostenlimit ($, 0 = keins) ⟶ Cost limit ($, 0 = none)
Auf Antwort warten (Min) ⟶ Wait for answer (min)
🔍 Selbstprüfung: Agent kontrolliert am Ende, ob alles erledigt ist, und arbeitet bei Lücken nach ⟶ 🔍 Self-check: the agent verifies at the end that everything is done and fixes gaps
❓ Rückfragen auch per Telegram schicken (antworten per Knopf oder Nachricht) ⟶ ❓ Also send questions via Telegram (answer by button or message)
`;

const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const EXACT = new Map(), PATS = [];
for (const line of RAW.replaceAll("\\x24", "$").replaceAll("\\x60", "`").split("\n")) {
  const i = line.indexOf(" ⟶ ");
  if (i < 0) continue;
  const de = line.slice(0, i).trim(), en = line.slice(i + 3).trim();
  if (de.includes("{}")) PATS.push([new RegExp("^" + de.split("{}").map(esc).join("(.+?)") + "$", "s"), en, de.replace(/\{\}/g, "").length]);
  else EXACT.set(de, en);
}
PATS.sort((a, b) => b[2] - a[2]);   // spezifischste Muster zuerst
const cache = new Map();
function fill(en, groups) {
  let n = 0;
  return en.replace(/\{(\d*)\}/g, (_, d) => { const g = groups[d ? +d - 1 : n++]; return g === undefined ? "" : tr(g); });
}
function tr(s) {
  if (typeof s !== "string") return s;
  const t = s.trim();
  if (!t || !/[A-Za-zÄÖÜäöüß]/.test(t)) return s;
  if (cache.has(t)) { const r = cache.get(t); return r === t ? s : s.replace(t, r); }
  let r = EXACT.get(t);
  if (r === undefined) for (const [re, en] of PATS) { const m = t.match(re); if (m) { r = fill(en, m.slice(1)); break; } }
  if (r === undefined && t.includes("\n")) r = t.split("\n").map(x => tr(x)).join("\n");
  if (r === undefined) r = t;
  if (cache.size > 5000) cache.clear();
  cache.set(t, r);
  return r === t ? s : s.replace(t, r);
}
window.tr = tr;
const SKIP = "[data-noi18n],script,style,textarea,code,pre,.mdc", SKIP_EL = "[data-noi18n],script,style,.mdc";
const ATTRS = ["placeholder", "title", "aria-label"];
function doText(n) {
  const p = n.parentElement;
  if (!p || p.closest(SKIP)) return;
  const v = n.nodeValue, r = tr(v);
  if (r !== v) n.nodeValue = r;
}
function doEl(e) {
  if (e.closest(SKIP_EL)) return;
  for (const a of ATTRS) if (e.hasAttribute(a)) { const v = e.getAttribute(a), r = tr(v); if (r !== v) e.setAttribute(a, r); }
}
function walk(root) {
  if (root.nodeType === 3) return doText(root);
  if (root.nodeType !== 1) return;
  if (root.matches(SKIP_EL)) return;
  doEl(root);
  const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode: n => n.nodeType === 1 && n.matches(SKIP_EL) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
  let n; while ((n = w.nextNode())) n.nodeType === 3 ? doText(n) : doEl(n);
}
walk(document.body);
new MutationObserver(ms => {
  for (const m of ms) {
    if (m.type === "childList") m.addedNodes.forEach(walk);
    else if (m.type === "characterData") doText(m.target);
    else if (m.type === "attributes") doEl(m.target);
  }
}).observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
const oc = window.confirm.bind(window), oa = window.alert.bind(window);
window.confirm = m => oc(tr(String(m)));
window.alert = m => oa(tr(String(m)));
document.title = document.title.replace("Assistent", "Assistant");
})();
