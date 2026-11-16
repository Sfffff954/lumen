<div align="center">

# ✨ Lumen

**A personal AI assistant that runs on your own Linux PC. It talks with you, operates your computer, guards your network and sends teams of agents to work for you.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-Ubuntu%20%7C%20Debian%20%7C%20Mint-FCC624?logo=linux&logoColor=black)
![Runs locally](https://img.shields.io/badge/runs-locally-2E8B57)
![AI](https://img.shields.io/badge/AI-Claude%20%7C%20OpenAI%20%7C%20Gemini%20%7C%20DeepSeek%20%7C%20Ollama-8A2BE2)

🇩🇪 [Deutsch](README.de.md) · 📘 [English guide](GUIDE.md) · 📖 [Full guide (German)](ANLEITUNG.md)

</div>

---

## What is Lumen?

Think of Lumen as **your own assistant like Jarvis, living on your computer** instead of in someone else's cloud.

You talk to it, by voice or by typing in a web page on your PC, or from your phone through Telegram. It doesn't just answer
questions: it **does things**. It opens programs, reads and writes files, checks your email, adds calendar events,
searches the web, looks at your security cameras, scans your home network for problems, reviews your code and commits it to Git.
When a task is big, it starts a **team of AI agents** that work in parallel and report back.

The "brain" is a large language model of your choice:
- **Cloud:** Claude, OpenAI, Gemini or DeepSeek, using **your own API key**.
- **Fully local and free:** [Ollama](https://ollama.com) on your own GPU.
- **Auto mode:** everyday questions go to the local model, and only hard tasks go to the cloud.

Everything else (your settings, chats, memory, passwords) **stays on your machine**.

### A few things you can say to Lumen

> 💬 *"What's on my calendar tomorrow, and how long will it take me to get there?"*
> 💬 *"Who is at the front door?"* → grabs a frame from your camera and describes it
> 💬 *"Research the best budget SDR antennas and write me a comparison document."* → sends an agent team
> 💬 *"Review my changes in ~/projects/app and write a commit message."*
> 💬 *"Check my PC and home network for security problems."*
> 💬 *"Every weekday at 8:00, send me the weather, my appointments and new emails on Telegram."*
> 💬 *"I need a tool that converts videos to MP3."* → finds one on GitHub, installs it safely and learns how to use it

## 🌟 Features

| | |
|---|---|
| 🗣️ **Voice** | Speech recognition (Whisper), natural local voice (Piper), dictation, meeting transcripts, "phone calls" via Telegram voice messages |
| 🖥️ **Computer control** | Sees the screen, controls mouse and keyboard, launches apps and games, music control, clipboard helper, PC doctor |
| 🤖 **Agents & agent teams** | Agents with roles (researcher, coder, admin, writer …) work in parallel, ask you questions when unsure, check their own work, and run under time and cost limits. Live view in Telegram |
| 🧠 **Learns over time** | Long-term memory, self-written skills, a knowledge library from your PDFs, your own Ollama model, LoRA fine-tuning on your GPU |
| ⏰ **Autopilot** | Scheduled automations, heartbeat checks, daily briefing, browser automation (Playwright) |
| 🔎 **Own search bots** | Metasearch across 11 sources at once (DuckDuckGo, Bing, Wikipedia, GitHub, Stack Overflow, Hacker News, Reddit, arXiv …). Watcher bots report only *new* results |
| 🧰 **GitHub workshop** | Finds command-line tools on GitHub, checks them for red flags, installs them in isolation and teaches itself how to use them |
| 👨‍💻 **Code workshop** | Project explainer, AI code review with linters and secret detection, Git assistant with AI commit messages and merge-conflict resolution |
| 📱 **Telegram bot** | Chat, voice, location features (weather, travel time, place reminders), camera snapshots, controlling agents, slash commands |
| 🛰️ **Lumen server** | Runs 24/7 on your own server so Telegram keeps working when your PC is off, and syncs with the desktop |
| 📧 **Email & calendar** | Lumen's own email address, your mailboxes and contacts, adding calendar events |
| 📷 **Security cameras** | IP cameras over RTSP (Reolink, Tapo, Hikvision, Dahua/Imou, eufy …): live view and snapshots, also on Telegram |
| 🛡️ **Security center** | PC check, home-network scan, USB watcher (BadUSB), nmap, Wireshark, Lynis, ClamAV, CVE check, TLS check, system hardening |
| 📻 **Radio reception** | FM radio and aircraft tracking (ADS-B) with HackRF or RTL-SDR, receive only |
| 📈 **Crypto** | Paper-trading account, price alerts, Solana swaps that **you** sign in Phantom |
| 🎓 **Learning** | Flashcards with spaced repetition, a 26-lesson ethical-hacking path for your own lab |
| 📚 **Studio** | Book writing, learning from PDFs, creating Word/PDF/Excel/PowerPoint files |
| 🧩 **Plugins** | Add your own tools as small Python files (examples included) |
| 🌍 **Bilingual** | Interface, answers and voice in English or German |

## ⚙️ How it works

```
   You ──voice / text──▶  Web UI (localhost:8765)  ◀──── Telegram bot (phone)
                                   │
                                   ▼
                     ┌───────────────────────────┐
                     │      lumen.py server      │   Python standard library only,
                     │  ─ builds the prompt      │   no framework, no build step
                     │  ─ calls the AI model     │◀──▶ Claude / OpenAI / Gemini /
                     │  ─ runs the tools it asks │     DeepSeek / Ollama (local)
                     │  ─ asks you before risky  │
                     │    actions                │
                     └───────────┬───────────────┘
                                 │  ~190 tools
      ┌──────────┬──────────┬────┴─────┬───────────┬────────────┬───────────┐
    files     screen &    email &    web search   cameras &   Git & code  security &
    & docs    apps        calendar   & browser    network     review      radio …
```

1. **You ask something.** Lumen sends your message to the AI model together with a list of **tools** it may use, for example
   `read_file`, `calendar_add`, `nmap_scan`, `camera_snapshot` or `git_commit`.
2. **The model decides what to do** and asks Lumen to run one or more tools. Lumen runs them on your PC and returns the results,
   and the model continues until the task is done. This loop is called *tool use*.
3. **Risky steps need your OK.** Sending an email, committing code, installing software, clicking "Buy" in the browser and similar
   actions always show a confirmation card first.
4. **A background loop** runs once a minute. It handles automations, reminders, the heartbeat, watcher bots, the USB and network
   watchers and alerts, and delivers results to your PC or to Telegram.
5. **Agents** are the same loop running in the background with a role, a limited set of tools and time and cost limits. A lead
   agent can split a big job and hand parts to specialists.
6. **Skills** are plain-text how-to notes that Lumen writes for itself after solving something new, so it is faster next time.
   Skills are never code.

Lumen is written in plain **Python with no framework**: `lumen.py` is the server and tool registry, `web/index.html` is the
whole interface, and each feature lives in its own module (see *Project layout* below).

## 🚀 Quick start

```bash
git clone git@github.com:Sfffff954/lumen.git
cd lumen
./setup-linux.sh        # one-time: system packages, Python venv, voice, app-menu entry
./start-mac-linux.sh    # or click "Lumen" in your app menu
```

Lumen opens in your browser at `http://127.0.0.1:8765`. On first start, enter an API key **or** pick **Ollama** to run
fully locally. To switch the interface to English, go to **Settings (⚙) → Sprache · Language → English**.

<details>
<summary><b>Fully local and free with Ollama</b></summary>

```bash
curl -fsSL https://ollama.com/install.sh | sh
```
In Lumen, open **🧪 AI Lab**, download a base model (e.g. Qwen 2.5 7B) and click **Build Lumen model**. In **Auto mode**
the local model handles everyday tasks and only hard ones go to the cloud.
</details>

<details>
<summary><b>Telegram (use Lumen from your phone)</b></summary>

Create a bot with **@BotFather**, paste the token into **Apps → Telegram**, and start chatting. Useful commands:
`/agent` start an agent · `/agenten` running agents · `/kamera` camera picture · `/standort` share location ·
`/suche` metasearch · `/beobachte` watch a topic · `/github` find a tool · `/anruf` voice call · `/lernen` flashcards ·
`/automation` automations. The command names are German.

To keep the bot online while your PC is off, run the **Lumen server** on a small home server or VPS (see the [guide](GUIDE.md)).
</details>

<details>
<summary><b>Windows</b></summary>

Run `start-windows.bat`. For voice: `pip install faster-whisper sounddevice numpy pillow mss pyautogui`.
Linux-specific features (radio, USB watcher, hardening) are not available on Windows.
</details>

## 💻 Requirements

- **Linux**: Ubuntu, Debian, Mint or other Debian-based distributions. **Python 3.10+**
- An API key from Anthropic, OpenAI, Google or DeepSeek, **or** Ollama
- Optional:
  - **NVIDIA GPU with 8 GB+** for local models and fine-tuning
  - **HackRF / RTL-SDR** for radio
  - **IP camera with RTSP**
  - **Telegram bot** for mobile use

`setup-linux.sh` installs what's needed, including ffmpeg, git, ripgrep, shellcheck, Playwright/Chromium and the Piper voice.
The settings page shows what is ready on your PC.

## 🔒 Privacy & safety

Lumen can do a lot, so these safety rules are **built in**:

- **Your data stays local.** Settings, chats and memory live in `~/.lumen`, outside the project folder. The server listens only
  on `127.0.0.1` and requires a token.
- **Passwords** are typed only into protected fields. They never go to the AI, into chat history or over Telegram. Lumen never
  asks for seed phrases or private keys and blocks them if pasted.
- **Confirmation for risky actions:** sending mail, purchases, commits and pushes, installs, system changes.
- **Outside content is data, not instructions.** Lumen does not follow instructions hidden in web pages, emails, READMEs or code
  (prompt-injection protection).
- **Crypto:** Lumen never moves funds itself. It prepares a swap and **you** sign it in Phantom, with a per-swap limit and
  no financial advice.
- **Git:** force-push, `reset --hard` and `clean` are not offered, and commits containing API keys or passwords are blocked.

## ⚖️ Responsible use

The security, network and radio tools are meant for **protecting your own devices**:

- Scans (nmap, web scanners, port scans) only against **your own** machines, home network, public IP and domains. Lumen checks the
  target first.
- **HackRF/SDR is receive-only:** no transmitting, jamming, replaying or cloning signals.
- Offensive tools (password crackers, exploit frameworks) are detected but not operated. No people search: account and breach
  checks are for your own accounts only.
- Cameras: film only **your own property**. Lumen records nothing and does no face recognition.

You are responsible for using Lumen in line with the laws of your country.

## 🗂️ Project layout

```
lumen.py              server, tool registry, AI providers, Telegram commands
web/                  the whole UI (index.html), English translation, Phantom swap page
agents.py             agents and agent teams
autopilot.py          automations and heartbeat
skills.py             self-written skills
searchbots.py         metasearch and watcher bots
ghtools.py            GitHub workshop
codehelp.py           code workshop (review, Git, project explainer)
camera.py             IP cameras (RTSP)
cyber.py, secplus.py  security tools
telebot.py            Telegram bot
serverlink.py         Lumen server sync
mail.py, calendars.py, trading.py, funk.py, trainer.py, orte.py, browser.py, voice.py, computer.py, …
plugins_beispiele/    example plugins
```

## 🤝 Contributing

Ideas, bug reports and pull requests are welcome. The easiest way in is a **plugin**: a single Python file that adds a new tool.
See `plugins_beispiele/` for examples. The code comments and UI texts are mostly German, and English translations live in
`web/i18n-en.js`.

## 📄 License

Not chosen yet.
<!-- Tip: add an MIT license as LICENSE and change this line to "MIT – see LICENSE". -->
