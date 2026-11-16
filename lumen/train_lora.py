#!/usr/bin/env python3
"""
Lumen – LoRA-Feintuning auf deiner NVIDIA-Grafikkarte (Unsloth).

Läuft in der eigenen Umgebung .venv-train (wird im KI-Labor installiert).
Ablauf: Datensatz (eure Chats) → 4-Bit-Basismodell + LoRA trainieren → als GGUF speichern → Ollama-Modell anlegen.
Ausgaben für Lumen: "STATUS …", "PROGRESS x/y", "LOSS z".
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True)
ap.add_argument("--base", required=True)
ap.add_argument("--template", default="qwen-2.5")
ap.add_argument("--epochs", type=int, default=2)
ap.add_argument("--out", required=True)
ap.add_argument("--name", default="lumen-trained")
ap.add_argument("--ollama-base", default="qwen2.5:7b")
ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
ap.add_argument("--max-len", type=int, default=2048)
a = ap.parse_args()
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)


QWEN_TOOLS_TEMPLATE = """{{- if or .System .Tools }}<|im_start|>system
{{- if .System }}
{{ .System }}
{{- end }}
{{- if .Tools }}

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{{- range .Tools }}
{"type": "function", "function": {{ .Function }}}
{{- end }}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
{{- end }}<|im_end|>
{{ end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{ if .Content }}{{ .Content }}
{{- else if .ToolCalls }}<tool_call>
{{ range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ .Function.Arguments }}}
{{ end }}</tool_call>
{{- end }}{{ if not $last }}<|im_end|>
{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>user
<tool_response>
{{ .Content }}
</tool_response><|im_end|>
{{ end }}
{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant
{{ end }}
{{- end }}"""


def status(msg):
    print("STATUS", msg, flush=True)


status("Lade Bibliotheken …")
import torch  # noqa: E402

if not torch.cuda.is_available():
    print("FEHLER: Keine CUDA-Grafikkarte verfügbar. Treiber/CUDA prüfen.", flush=True)
    sys.exit(2)
print(f"GPU: {torch.cuda.get_device_name(0)} · {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB", flush=True)

from unsloth import FastLanguageModel  # noqa: E402  (muss vor transformers/trl importiert werden)
from unsloth.chat_templates import get_chat_template  # noqa: E402
from datasets import load_dataset  # noqa: E402
from transformers import TrainerCallback  # noqa: E402
from trl import SFTConfig, SFTTrainer  # noqa: E402

status(f"Lade Basismodell {a.base} (4-Bit) …")
model, tok = FastLanguageModel.from_pretrained(model_name=a.base, max_seq_length=a.max_len, load_in_4bit=True)
model = FastLanguageModel.get_peft_model(
    model, r=16, lora_alpha=16, lora_dropout=0, bias="none", random_state=3407,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    use_gradient_checkpointing="unsloth")
tok = get_chat_template(tok, chat_template=a.template)

status("Bereite Datensatz vor …")
ds = load_dataset("json", data_files=a.data, split="train")
ds = ds.map(lambda ex: {"text": tok.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False)},
            remove_columns=ds.column_names)
print(f"{len(ds)} Trainingsbeispiele", flush=True)
system_text = json.loads(open(a.data, encoding="utf-8").readline())["messages"][0]["content"]


class Progress(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kw):
        if logs and "loss" in logs:
            print(f"LOSS {logs['loss']:.4f}", flush=True)

    def on_step_end(self, args, state, control, **kw):
        print(f"PROGRESS {state.global_step}/{state.max_steps}", flush=True)


bf16 = torch.cuda.is_bf16_supported()
cfg = dict(dataset_text_field="text", per_device_train_batch_size=2, gradient_accumulation_steps=4, warmup_steps=5,
           num_train_epochs=a.epochs, learning_rate=2e-4, logging_steps=1, optim="adamw_8bit", weight_decay=0.01,
           lr_scheduler_type="linear", seed=3407, output_dir=str(out / "checkpoints"), report_to="none",
           save_strategy="no", bf16=bf16, fp16=not bf16)
try:
    args = SFTConfig(max_seq_length=a.max_len, **cfg)
except TypeError:  # neuere TRL-Versionen
    args = SFTConfig(max_length=a.max_len, **cfg)
try:
    trainer = SFTTrainer(model=model, processing_class=tok, train_dataset=ds, args=args, callbacks=[Progress()])
except TypeError:  # ältere TRL-Versionen
    trainer = SFTTrainer(model=model, tokenizer=tok, train_dataset=ds, args=args, callbacks=[Progress()])

try:  # nur auf Lumens Antworten lernen, nicht auf deine Fragen
    from unsloth.chat_templates import train_on_responses_only
    if a.template.startswith("qwen"):
        trainer = train_on_responses_only(trainer, instruction_part="<|im_start|>user\n", response_part="<|im_start|>assistant\n")
    elif a.template.startswith("llama"):
        trainer = train_on_responses_only(trainer, instruction_part="<|start_header_id|>user<|end_header_id|>\n\n",
                                          response_part="<|start_header_id|>assistant<|end_header_id|>\n\n")
except Exception as e:
    print(f"Hinweis: train_on_responses_only nicht genutzt ({e})", flush=True)

status("Training läuft …")
stats = trainer.train()
print(f"Training fertig: Loss {stats.training_loss:.4f}", flush=True)

status("Speichere LoRA-Adapter …")
model.save_pretrained(str(out / "lora"))
tok.save_pretrained(str(out / "lora"))

status("Wandle in GGUF um (q4_k_m) – das dauert ein paar Minuten …")
model.save_pretrained_gguf(str(out / "gguf"), tok, quantization_method="q4_k_m")
ggufs = sorted(glob.glob(str(out / "**" / "*.gguf"), recursive=True), key=os.path.getsize)
ggufs = [g for g in ggufs if "mmproj" not in g]
if not ggufs:
    print("FEHLER: Keine GGUF-Datei erzeugt.", flush=True)
    sys.exit(3)
gguf = ggufs[-1]
print(f"GGUF: {gguf} ({os.path.getsize(gguf) / 1e9:.1f} GB)", flush=True)

status("Lege Ollama-Modell an …")
template, params = None, []
try:
    req = urllib.request.Request(a.ollama_url.rstrip("/") + "/api/show", data=json.dumps({"model": a.ollama_base, "name": a.ollama_base}).encode(),
                                 headers={"Content-Type": "application/json"})
    info = json.loads(urllib.request.urlopen(req, timeout=20).read())
    template = info.get("template")
    params = [l.strip() for l in (info.get("parameters") or "").splitlines() if l.strip().startswith("stop")]
except Exception as e:
    print(f"Hinweis: Vorlage von {a.ollama_base} nicht gefunden ({e}) – nutze Standard-Vorlage.", flush=True)
if template and ".Tools" not in template and a.template.startswith("qwen"):
    print("Hinweis: Vorlage ohne Werkzeug-Unterstützung – nutze Qwen-Vorlage mit Werkzeugen.", flush=True)
    template = None
if not template:
    if a.template.startswith("qwen"):
        template = QWEN_TOOLS_TEMPLATE  # mit Werkzeug-Unterstützung, sonst kann Lumen keine Dateien/Programme steuern
        params = ['stop "<|im_start|>"', 'stop "<|im_end|>"']
    else:
        template = ("{{- if .System }}<|start_header_id|>system<|end_header_id|>\n\n{{ .System }}<|eot_id|>{{ end }}"
                    "{{- range .Messages }}<|start_header_id|>{{ .Role }}<|end_header_id|>\n\n{{ .Content }}<|eot_id|>{{ end }}"
                    "<|start_header_id|>assistant<|end_header_id|>\n\n")
        params = ['stop "<|eot_id|>"', 'stop "<|start_header_id|>"']
mf = out / "Modelfile"
mf.write_text(f'FROM {gguf}\nTEMPLATE """{template}"""\n' + "".join(f"PARAMETER {p.split(None, 1)[0]} {p.split(None, 1)[1]}\n" for p in params)
              + 'PARAMETER temperature 0.7\nPARAMETER num_ctx 16384\n'
              + f'SYSTEM """{system_text.replace(chr(34) * 3, "")}"""\n', "utf-8")
if not shutil.which("ollama"):
    print(f"FEHLER: 'ollama' nicht gefunden. Manuell: ollama create {a.name} -f {mf}", flush=True)
    sys.exit(4)
r = subprocess.run(["ollama", "create", a.name, "-f", str(mf)], capture_output=True, text=True)
print(r.stdout[-500:], r.stderr[-500:], flush=True)
if r.returncode != 0:
    sys.exit(5)
print(f"DONE {a.name}", flush=True)
status(f"Fertig! Neues Modell: {a.name}")
