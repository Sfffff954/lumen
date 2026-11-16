# Lumen – your local smart assistant

🏠 [Overview](README.md) · 🇩🇪 [Deutsch](README.de.md) · 📖 [Full guide (German)](ANLEITUNG.md)

Lumen runs on your PC, understands speech, sees your screen, uses mouse and keyboard, launches games and programs and
manages your servers via SSH. The AI comes from your own API key (Claude, OpenAI, Gemini or DeepSeek) – or fully local
and free with Ollama.

## Switch to English
Settings (⚙) → **Language · Sprache** → **🇬🇧 English** → Save. The page reloads in English. This switches:
- the whole interface (menus, buttons, lab, studio, dialogs),
- Lumen's answers, reports, documents and books,
- speech recognition (Whisper) and the voice – download an English voice under Settings → Voice
  (e.g. *Lessac*, *Ryan*, *Alan (UK)*). Without one, Lumen uses espeak-ng in English.

## Setup (Linux)
```bash
unzip Lumen.zip && cd lumen
./setup-linux.sh        # once: installs packages, Python environment, voice, app menu entry
./start-mac-linux.sh    # or click "Lumen" in the app menu
```
On first start the settings open: enter an API key, save, done.

## Highlights
- **Chat & voice:** "Hey Lumen", push-to-talk (Ctrl+M), spoken answers.
- **PC control:** folders and files, programs, games, screen, mouse/keyboard, terminal – risky actions ask first.
- **Documents:** "Make me a shopping list as a Word file", "Write a cover letter as PDF" → Word, PDF, e-book, HTML.
- **📚 Studio:** drop in PDFs/books/notes → ask questions with page references, summaries, flashcards (Anki export),
  quizzes. **Writing:** whole books chapter by chapter as Word/PDF/EPUB.
- **🧪 AI Lab:** your own local model "lumen", auto mode (local for easy things, cloud for hard ones), one-click
  training on your NVIDIA GPU, Teacher AI, quick rating, before/after comparison.
- **Servers & Docker** via SSH, **Deep Research** with sources, **security tools** (phishing check, breach check for
  your own accounts, port scan of your own servers), **apps** (Spotify, Discord, Telegram, GitHub, Home Assistant,
  Steam, weather, calendar, read-only crypto wallets), **Discord call & meeting notes** (with consent).

- **🛰️ Lumen server:** card “Lumen Server” → install on your own Linux server over SSH. It runs 24/7, sends a
  **daily briefing** (weather, events, tasks, server health, news) and **reminders** via Telegram, lets you **chat with
  Lumen from your phone** (confirm risky actions with buttons), alerts you about server problems and syncs tasks/notes/
  memory with your PC – “open Discord on my PC” via Telegram is picked up by the PC.
- **🧩 Plugins:** “build yourself a tool that …” – Lumen writes a small Python plugin, shows you the code and only installs
  it after you approve. Manage them under Apps → Custom tools.

Lumen never asks for seed phrases or private keys, doesn't search for private persons, and stores passwords nowhere.
The full (German) documentation is in [ANLEITUNG.md](ANLEITUNG.md); the German overview is [README.de.md](README.de.md).


## 👨‍💻 Code workshop
Card **👨‍💻 Code workshop** (or `/code`, `/review`, `/git`): **project explainer** (languages, structure, entry points, dependencies,
outline, code search, "explain project", write ARCHITECTURE.md), **code reviewer** (open changes, staged, last commit, branch vs main,
a commit or a file – with ruff/shellcheck linters and secret detection, findings by severity with fixes and "let Lumen fix it") and
**Git assistant** (status with per-file diffs, staging, AI commit messages in your style, commit, branches, fetch/pull --ff-only/push,
undo last unpushed commit, merge conflicts side by side with AI merge). No force-push, reset --hard or clean; commits containing
secrets are blocked; every write action asks first.

## 📷 Security cameras
Card **📷 Cameras** (or `/kamera`): connect IP cameras on your LAN (Reolink, Tapo, Hikvision, Dahua/Imou, eufy, Foscam, Axis,
ONVIF/RTSP). "Search network" finds them, Lumen detects the right stream address itself. Live view (~5 fps), snapshots,
fullscreen, save picture; ask in chat "Who is at the front door?"; Telegram `/kamera` sends a current photo. Camera passwords
are entered only in the Lumen window, stored locally (`~/.lumen/cameras.json`, mode 600), never sent to the AI; nothing is
recorded, no face recognition, own network only. Ring/Arlo/Blink/Nest have no RTSP access.

## 🔎 Own search bots & 🧰 GitHub workshop
**Metasearch:** up to 11 small bots ask DuckDuckGo, Bing, Mojeek, Wikipedia, GitHub, Stack Overflow, Hacker News, Reddit and
arXiv in parallel (plus Brave API / your own SearXNG if configured) and merge the results – what several sources find ranks
first. Lumen uses it for its own research too. **Watcher bots** (`/beobachte <topic>`) search on a schedule and report only
**new** hits via Telegram/PC. **GitHub workshop** (`/github <what you need>`): Lumen finds a tool, checks the repo (stars,
age, license, warnings), installs it isolated in `~/.lumen/gh-tools` after your OK (release binary, Python venv, source, Go, npm –
no admin rights) and then **learns to use it** from README + `--help` as a skill. Tools run without a shell in
`~/Lumen/Werkzeuge` and ask before each run unless marked trusted. Malware/attack tools and people-search tools are blocked.

## 🤖 Better agents & Telegram agent
Agents now ask you short questions when they really need info (app + Telegram buttons), self-check their result and fix
gaps, respect time/cost limits, survive restarts (interrupted ones can be restarted) and send created files. In Telegram,
`/agent <task>` shows live progress in one updating message with stop/log buttons; `/agenten` lists all with buttons.

## 🤖 Autopilot
**Automations** (scheduled AI tasks with results via Telegram/PC, `/automation`), a **heartbeat** that quietly checks your
own checklist and only pings you when something matters (`/heartbeat`), **self-learned skills** – after longer tasks Lumen
writes itself a SKILL.md guide and reuses/improves it (`/faehigkeiten`) – and **browser control** (own profile; never types
passwords or payment data; buying/sending/deleting always asks first).

## 📍 Share your location (Telegram)
Send your location to the bot (or `/standort`): place name, weather right there, your next event with travel time and
when to leave, nearby places. Place reminders: “remind me about milk when I'm at a supermarket / get home / leave work”.
Share your **live location** so reminders and “time to leave” alerts work on the go. Only your last location is kept
(no history, forgotten after 24 h). Maps and routes from OpenStreetMap.

## 📞 Call Lumen · 🎓 Learn · 📻 Radio & planes
- **Call Lumen via Telegram:** send voice messages, Lumen answers by text and voice; `/anruf` starts a phone-style
  conversation, `/auflegen` ends it.
- **Learn:** flashcards with spaced repetition (also in Telegram via `/lernen`) and a 26-lesson hacking course with Lumen
  as teacher – exercises only on your own PC or legal practice labs (`/pfad`).
- **Radio reception (HackRF / RTL-SDR, receive-only):** FM radio with station scan, and aircraft above you via ADS-B with
  a radar view (run `bash setup-adsb.sh` once).

## 🧰 Cybersecurity tools
File/download scanner (disguised executables, macros, risky PDFs, ClamAV, VirusTotal hash lookup, quarantine, download
watch), leaked-secrets finder, system-file integrity watch + rootkit hints (rkhunter/chkrootkit), CVE check via OSV.dev,
TLS check, one-click hardening (ufw, SSH keys-only, fail2ban, auto-updates), and Lumen drives your installed tools:
nmap, tshark/Wireshark, Lynis, testssl/sslscan, Nikto, WhatWeb, Nuclei – own targets only. Plus a local CyberChef-like
toolbox. Attack tools (hydra, john, hashcat, aircrack-ng, sqlmap, Metasploit) are detected but not driven.

## 🛡️ Security center
PC security check (firewall, exposed services, SSH, updates, encryption) with a score; home-network scan that flags new
devices (optional watcher); USB overview that recognises HackRF, RTL-SDR, Flipper Zero, YubiKey etc. and a USB watch that
warns about unknown keyboard devices (BadUSB); radio with HackRF One / RTL-SDR – **receive only**: device check, spectrum
scan with chart and band names, signal test for your own remotes; domain report (DNS, SPF/DMARC, TLS, security headers,
subdomains). Lumen never transmits, jams or replays signals. Commands: `/sicherheit`, `/netz`, `/usb`, `/funk`, `/domain`.

## ✨ Start page, suggestions & memory
Overview tiles (weather, next event, tasks, unread mail, practice portfolio, servers), suggestions that fit your day,
2–3 next-step buttons under every answer, a heads-up 20 minutes before events, and a better memory that also learns
your corrections and preferences (never passwords). Click a card title on the right to collapse it.

## 📈 Crypto trading
Card **📈 Crypto trading**: a **practice portfolio** with play money at real prices (charts, P&L, limit/stop-loss orders),
**real Solana swaps** prepared via Jupiter that only execute when you sign in **Phantom** (safety limits per swap and
slippage, warnings for unverified tokens), and **price alerts** (desktop + Telegram). Commands: `/kurs`, `/depot`,
`/trade`, `/alarm`. Lumen never asks for your seed phrase or private key and never trades real money on its own.
Not financial advice.

## 📧 Email
Card **📧 Email → Set up**. Give Lumen **its own address** (e.g. free at GMX or Gmail) – it sends you reports and files,
and can optionally accept tasks by mail (only from your allowed senders, verified by DKIM/DMARC or a code word; risky
actions always blocked). Connect **your mailbox** too: Lumen reads, summarizes, sorts and drafts replies; sending and
deleting always ask first. Most providers need an **app password** and IMAP enabled; Outlook.com often blocks IMAP
passwords (OAuth only) – use GMX/Gmail for Lumen instead. Contacts (`name = address`), signature, new-mail alerts
(desktop + Telegram), briefing part “📧 Unread mail”, commands `/mails` and `/mail Mom: I'll be late`.
Text inside emails is treated as data – Lumen never follows instructions found in mails.
