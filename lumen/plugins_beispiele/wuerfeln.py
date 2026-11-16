"""Würfeln, Münze werfen und Zufallsauswahl – ein einfaches Beispiel-Plugin."""
import random


def wuerfeln(args):
    seiten = max(2, int(args.get("seiten") or 6))
    anzahl = max(1, min(int(args.get("anzahl") or 1), 20))
    w = [random.randint(1, seiten) for _ in range(anzahl)]
    return {"würfe": w, "summe": sum(w)}


def zufall_auswahl(args):
    opts = [o.strip() for o in str(args.get("optionen", "")).split(",") if o.strip()]
    if len(opts) < 2:
        raise RuntimeError("Mindestens zwei Optionen, durch Komma getrennt.")
    return {"gewählt": random.choice(opts)}


TOOLS = [
    {"name": "wuerfeln", "description": "Würfelt (z. B. W6, W20) – auch mehrere Würfel auf einmal.",
     "parameters": {"seiten": {"type": "integer", "description": "Seiten pro Würfel, Standard 6"},
                    "anzahl": {"type": "integer", "description": "Anzahl Würfel, Standard 1"}},
     "required": [], "run": wuerfeln},
    {"name": "zufall_auswahl", "description": "Wählt zufällig eine Option aus (z. B. welches Spiel, welches Essen). Münzwurf: optionen='Kopf,Zahl'.",
     "parameters": {"optionen": {"type": "string", "description": "Optionen, durch Komma getrennt"}},
     "required": ["optionen"], "run": zufall_auswahl},
]
