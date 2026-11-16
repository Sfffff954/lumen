#!/usr/bin/env bash
cd "$(dirname "$0")"
if [[ -x .venv/bin/python ]]; then exec .venv/bin/python lumen.py "$@"; fi
echo "Tipp: Einmal ./setup-linux.sh ausführen für Stimme, Bildschirm-Steuerung und App-Fenster."
exec python3 lumen.py "$@"
