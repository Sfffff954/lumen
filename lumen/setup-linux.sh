#!/usr/bin/env bash
# Lumen – Einrichtung für Linux (Ubuntu/Debian/Mint, Fedora, Arch/Manjaro)
cd "$(dirname "$0")"
echo "== Lumen Setup =="
SESSION="${XDG_SESSION_TYPE:-x11}"
echo "Sitzung: $SESSION"

install_pkgs() {  # erst alle zusammen, bei Fehler einzeln (fehlende Pakete überspringen)
  local mgr="$1"; shift
  if ! sudo $mgr "$@"; then
    local base=(); local pkgs=()
    for a in "$@"; do [[ "$a" == -* || "$a" == install || "$a" == -S ]] && base+=("$a") || pkgs+=("$a"); done
    for p in "${pkgs[@]}"; do sudo $mgr "${base[@]}" "$p" >/dev/null 2>&1 && echo "  ✓ $p" || echo "  – übersprungen: $p"; done
  fi
}

if command -v apt-get >/dev/null; then
  sudo apt-get update
  PKGS=(python3-venv python3-pip python3-gi gir1.2-webkit2-4.1 libportaudio2 espeak-ng openssh-client dnsutils traceroute whois
        ffmpeg pulseaudio-utils playerctl xdotool wmctrl scrot fonts-dejavu-core xclip libnotify-bin zenity git ripgrep shellcheck)
  [[ "$SESSION" == wayland ]] && PKGS+=(grim gnome-screenshot ydotool wl-clipboard)
  install_pkgs apt-get install -y "${PKGS[@]}"
elif command -v dnf >/dev/null; then
  PKGS=(python3-pip python3-gobject webkit2gtk4.1 portaudio espeak-ng openssh-clients ffmpeg-free bind-utils traceroute whois
        pulseaudio-utils playerctl xdotool wmctrl scrot xclip libnotify zenity)
  [[ "$SESSION" == wayland ]] && PKGS+=(grim gnome-screenshot ydotool wl-clipboard)
  install_pkgs dnf install -y "${PKGS[@]}"
elif command -v pacman >/dev/null; then
  PKGS=(python python-pip python-gobject webkit2gtk-4.1 portaudio espeak-ng openssh ffmpeg libpulse bind traceroute whois
        playerctl xdotool wmctrl scrot xclip libnotify zenity)
  [[ "$SESSION" == wayland ]] && PKGS+=(grim ydotool wl-clipboard)
  install_pkgs pacman -S --needed --noconfirm "${PKGS[@]}"
else
  echo "Paketmanager nicht erkannt – bitte portaudio, espeak-ng, xdotool, wmctrl, ssh selbst installieren."
fi

echo "== Python-Umgebung (.venv) =="
python3 -m venv --system-site-packages .venv || { echo "venv fehlgeschlagen (python3-venv installieren)"; exit 1; }
.venv/bin/pip install -q -U pip
.venv/bin/pip install -q pywebview faster-whisper sounddevice numpy pillow mss pypdf qrcode python-docx reportlab pynput || echo "Einige Python-Pakete fehlen – Lumen läuft trotzdem."
.venv/bin/pip install -q piper-tts || echo "Piper (schöne Stimme) nicht installiert – nutze espeak-ng."
echo "==> Browser für die Browser-Steuerung (Playwright + Chromium, ca. 150 MB)"
.venv/bin/pip install -q playwright && .venv/bin/python -m playwright install chromium || echo "Browser-Steuerung nicht eingerichtet – später: .venv/bin/pip install playwright && .venv/bin/python -m playwright install chromium"

echo "== Deutsche Stimme (Piper, ca. 60 MB) =="
V=~/.lumen/voices; mkdir -p "$V"
BASE=https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium
[[ -f "$V/de_DE-thorsten-medium.onnx" ]] || curl -fL --progress-bar -o "$V/de_DE-thorsten-medium.onnx" "$BASE/de_DE-thorsten-medium.onnx" || echo "Stimme nicht geladen."
[[ -f "$V/de_DE-thorsten-medium.onnx.json" ]] || curl -fsL -o "$V/de_DE-thorsten-medium.onnx.json" "$BASE/de_DE-thorsten-medium.onnx.json"

echo "== Spracherkennung vorladen (Whisper base, ca. 150 MB) =="
.venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8'); print('ok')" 2>/dev/null || echo "Wird beim ersten Sprechen geladen."

echo "== App-Menü-Eintrag =="
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/lumen.desktop <<DESK
[Desktop Entry]
Name=Lumen
Comment=Dein Smart Assistant
Exec=$(pwd)/start-mac-linux.sh
Icon=$(pwd)/web/icon.svg
Terminal=false
Type=Application
Categories=Utility;
DESK

if [[ "$SESSION" == wayland ]]; then
  echo
  echo "Hinweis Wayland: Für Maus/Tastatur braucht Lumen ydotool (Version 1.0+) mit laufendem Dienst:"
  echo "  sudo systemctl enable --now ydotool      (oder: sudo ydotoold &)"
  echo "Am zuverlässigsten ist die Steuerung in einer X11-Sitzung (z. B. 'Ubuntu auf Xorg' beim Login)."
fi
echo
echo "Fertig! Starten mit ./start-mac-linux.sh oder über das App-Menü (Lumen)."
