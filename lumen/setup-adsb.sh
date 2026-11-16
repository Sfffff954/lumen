#!/usr/bin/env bash
# Lumen – Flugzeug-Empfang (ADS-B) einrichten: baut dump1090 mit HackRF- und RTL-SDR-Unterstützung nach ~/.lumen/tools
set -e
echo "==> Pakete installieren (fragt nach deinem Passwort)"
if command -v apt-get >/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y build-essential pkg-config git libncurses-dev libhackrf-dev librtlsdr-dev hackrf
elif command -v dnf >/dev/null; then
  sudo dnf install -y gcc make pkgconf-pkg-config git ncurses-devel hackrf-devel rtl-sdr-devel hackrf
elif command -v pacman >/dev/null; then
  sudo pacman -S --needed --noconfirm base-devel git ncurses hackrf rtl-sdr
else
  echo "Unbekannte Distribution – bitte gcc, make, git, ncurses, libhackrf und librtlsdr (jeweils -dev) selbst installieren."; exit 1
fi
mkdir -p "$HOME/.lumen/tools" && cd "$HOME/.lumen/tools"
rm -rf dump1090-src
echo "==> dump1090 (FlightAware) laden und bauen"
git clone --depth 1 https://github.com/flightaware/dump1090 dump1090-src
cd dump1090-src
make -j"$(nproc)" HACKRF=yes RTLSDR=yes BLADERF=no LIMESDR=no SOAPYSDR=no DUMP1090_VERSION=lumen dump1090
mkdir -p ../dump1090 && cp dump1090 ../dump1090/dump1090
cd .. && rm -rf dump1090-src
echo
echo "✅ Fertig. In Lumen: Karte „📻 Funk-Empfang“ → Flugzeuge → Starten."
echo "   Tipp: Für 1090 MHz hilft eine passende Antenne am Fenster sehr."
