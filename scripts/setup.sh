#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[setup] Root: $ROOT_DIR"

if [[ ! -f "config.json" ]]; then
  cp config.example.json config.json
  echo "[setup] Created config.json from config.example.json"
fi

PYTHON_CMD="$(command -v python3.12 || command -v python3)"
PYTHON_BIN="${ROOT_DIR}/venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  "$PYTHON_CMD" -m venv venv
  echo "[setup] Created virtual environment at venv/"
fi

"$PYTHON_BIN" -m ensurepip --upgrade >/dev/null 2>&1 || true
"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
"$PYTHON_BIN" -m pip install -r requirements.txt

MAGICK_PATH="$(command -v magick || true)"
if [[ -z "$MAGICK_PATH" ]]; then
  MAGICK_PATH="$(command -v convert || true)"
fi

FIREFOX_PROFILE=""
if [[ -d "$HOME/Library/Application Support/Firefox/Profiles" ]]; then
  FIREFOX_PROFILE="$(find "$HOME/Library/Application Support/Firefox/Profiles" -maxdepth 1 -type d -name "*default-release*" | head -n 1 || true)"
  if [[ -z "$FIREFOX_PROFILE" ]]; then
    FIREFOX_PROFILE="$(find "$HOME/Library/Application Support/Firefox/Profiles" -maxdepth 1 -type d | tail -n +2 | head -n 1 || true)"
  fi
fi

MAGICK_PATH="$MAGICK_PATH" FIREFOX_PROFILE="$FIREFOX_PROFILE" "$PYTHON_BIN" - <<'PY'
import json
import os

cfg_path = os.path.join(os.getcwd(), "config.json")

with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)

cfg.setdefault("llm_provider", "openai")
cfg.setdefault("stt_provider", "local_whisper")
cfg.setdefault("openai_base_url", "https://api.openai.com/v1")
cfg.setdefault("openai_api_key", "")
cfg.setdefault("openai_model", "gpt-4.1-mini")
cfg.setdefault("ollama_base_url", "http://127.0.0.1:11434")
cfg.setdefault("ollama_model", "")
cfg.setdefault("whisper_model", "base")
cfg.setdefault("whisper_device", "auto")
cfg.setdefault("whisper_compute_type", "int8")

magick_path = os.environ.get("MAGICK_PATH", "")
if magick_path:
    cfg["imagemagick_path"] = magick_path

firefox_profile = os.environ.get("FIREFOX_PROFILE", "")
if firefox_profile and not cfg.get("firefox_profile"):
    cfg["firefox_profile"] = firefox_profile

with open(cfg_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")

print(f"[setup] Updated {cfg_path}")
print(f"[setup] llm_provider={cfg.get('llm_provider')} model={cfg.get('openai_model')}")
print(f"[setup] stt_provider={cfg.get('stt_provider')}")
PY

echo "[setup] Running preflight..."
"$PYTHON_BIN" scripts/preflight.py

echo ""
echo "[setup] Done."
echo "[setup] Start app with: source venv/bin/activate && python src/main.py"
