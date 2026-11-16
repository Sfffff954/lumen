#!/usr/bin/env python3
"""
Lumen – Mini-KI von null.

Ein winziges GPT (Transformer, wie die großen – nur tausendmal kleiner), das Buchstabe für Buchstabe
lernt, Text weiterzuschreiben. Trainingsdaten: eure Chats + eigene .txt-Dateien.
Es wird NICHT schlau – aber man sieht genau, wie KI-Sprachmodelle lernen: Am Anfang Buchstabensalat,
nach ein paar hundert Schritten Wörter, später Sätze im Stil der Trainingsdaten.

  python mini_gpt.py train --corpus text.txt --out ordner --steps 3000 --size mittel
  python mini_gpt.py sample --out ordner --prompt "Du: Hallo" --length 400
"""
import argparse
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

SIZES = {"klein": dict(n_layer=4, n_head=4, n_embd=192, block=128),
         "mittel": dict(n_layer=6, n_head=6, n_embd=384, block=256),
         "groß": dict(n_layer=8, n_head=8, n_embd=512, block=256)}


class Block(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(c["n_embd"]), nn.LayerNorm(c["n_embd"])
        self.attn = nn.MultiheadAttention(c["n_embd"], c["n_head"], dropout=0.1, batch_first=True)
        self.mlp = nn.Sequential(nn.Linear(c["n_embd"], 4 * c["n_embd"]), nn.GELU(),
                                 nn.Linear(4 * c["n_embd"], c["n_embd"]), nn.Dropout(0.1))

    def forward(self, x, mask):
        h = self.ln1(x)
        x = x + self.attn(h, h, h, attn_mask=mask, need_weights=False)[0]
        return x + self.mlp(self.ln2(x))


class MiniGPT(nn.Module):
    def __init__(self, vocab, c):
        super().__init__()
        self.c = c
        self.tok = nn.Embedding(vocab, c["n_embd"])
        self.pos = nn.Embedding(c["block"], c["n_embd"])
        self.blocks = nn.ModuleList(Block(c) for _ in range(c["n_layer"]))
        self.ln = nn.LayerNorm(c["n_embd"])
        self.head = nn.Linear(c["n_embd"], vocab, bias=False)
        self.head.weight = self.tok.weight  # Gewichte teilen (wie bei GPT-2)

    def forward(self, idx, targets=None):
        T = idx.shape[1]
        x = self.tok(idx) + self.pos(torch.arange(T, device=idx.device))
        mask = torch.triu(torch.ones(T, T, device=idx.device, dtype=torch.bool), 1)  # nicht in die Zukunft schauen
        for b in self.blocks:
            x = b(x, mask)
        logits = self.head(self.ln(x))
        loss = None if targets is None else F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1))
        return logits, loss

    @torch.no_grad()
    def generate(self, idx, n, temp=0.8, top_k=40):
        for _ in range(n):
            logits, _ = self(idx[:, -self.c["block"]:])
            logits = logits[:, -1, :] / max(temp, 0.05)
            v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
            logits[logits < v[:, [-1]]] = -float("inf")
            idx = torch.cat([idx, torch.multinomial(F.softmax(logits, -1), 1)], 1)
        return idx


def train(a):
    text = Path(a.corpus).read_text("utf-8", errors="replace")
    if len(text) < 20000:
        print(f"FEHLER: Zu wenig Text ({len(text)} Zeichen). Mindestens 20.000 – chatte mehr mit Lumen oder lege "
              f".txt-Dateien in ~/.lumen/lab/mini_texte/ (z. B. Bücher, Songtexte, eigene Texte).", flush=True)
        sys.exit(2)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    c = dict(SIZES.get(a.size, SIZES["mittel"]))
    chars = sorted(set(text))
    stoi = {ch: i for i, ch in enumerate(chars)}
    data = torch.tensor([stoi[ch] for ch in text], dtype=torch.long)
    n = int(0.9 * len(data))
    tr, va = data[:n], data[n:]
    model = MiniGPT(len(chars), c).to(dev)
    params = sum(p.numel() for p in model.parameters())
    print(f"STATUS Mini-KI: {params / 1e6:.1f} Mio. Parameter · {len(text):,} Zeichen · {len(chars)} verschiedene Zeichen · {dev}", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.1)
    bs = 64 if dev == "cuda" else 16
    steps = max(50, a.steps)

    def batch(src):
        ix = torch.randint(len(src) - c["block"] - 1, (bs,))
        x = torch.stack([src[i:i + c["block"]] for i in ix]).to(dev)
        y = torch.stack([src[i + 1:i + 1 + c["block"]] for i in ix]).to(dev)
        return x, y

    @torch.no_grad()
    def evaluate():
        model.eval()
        losses = [model(*batch(va if len(va) > c["block"] + 2 else tr))[1].item() for _ in range(20)]
        model.train()
        return sum(losses) / len(losses)

    t0 = time.time()
    for step in range(1, steps + 1):
        lr = 1e-3 * min(1, step / 100) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * step / steps)))
        for g in opt.param_groups:
            g["lr"] = lr
        _, loss = model(*batch(tr))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if step % 10 == 0 or step == 1:
            print(f"PROGRESS {step}/{steps}", flush=True)
        if step % 100 == 0 or step == steps:
            vl = evaluate()
            print(f"LOSS {vl:.4f}", flush=True)
            if step % 500 == 0 or step == steps:
                start = torch.tensor([[stoi.get("D", 0)]], device=dev)
                s = "".join(chars[i] for i in model.generate(start, 120)[0].tolist())
                print(f"Beispiel nach {step} Schritten: {s!r}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "config": c, "chars": chars}, out / "ckpt.pt")
    meta = {"parameter_mio": round(params / 1e6, 1), "schritte": steps, "loss": round(vl, 3), "zeichen": len(text),
            "größe": a.size, "gerät": dev, "minuten": round((time.time() - t0) / 60, 1),
            "trainiert": datetime.now().strftime("%d.%m.%Y %H:%M")}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    print(f"STATUS Fertig! Loss {vl:.2f} nach {meta['minuten']} Min.", flush=True)


def sample(a):
    ck = torch.load(Path(a.out) / "ckpt.pt", map_location="cpu")
    chars, c = ck["chars"], ck["config"]
    stoi = {ch: i for i, ch in enumerate(chars)}
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = MiniGPT(len(chars), c).to(dev)
    model.load_state_dict(ck["model"])
    model.eval()
    ids = [stoi[ch] for ch in a.prompt if ch in stoi] or [0]
    out = model.generate(torch.tensor([ids], device=dev), a.length, a.temp)
    print("<<<TEXT>>>" + "".join(chars[i] for i in out[0].tolist()), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["train", "sample"])
    ap.add_argument("--corpus")
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--size", default="mittel")
    ap.add_argument("--prompt", default="Du: ")
    ap.add_argument("--length", type=int, default=400)
    ap.add_argument("--temp", type=float, default=0.8)
    args = ap.parse_args()
    train(args) if args.cmd == "train" else sample(args)
