#!/usr/bin/env python3
import json
import os
import sys
from typing import Tuple

import requests


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, "config.json")


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def check_url(url: str, timeout: int = 3) -> Tuple[bool, str]:
    try:
        response = requests.get(url, timeout=timeout)
        return True, f"HTTP {response.status_code}"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    if not os.path.exists(CONFIG_PATH):
        fail(f"Missing config file: {CONFIG_PATH}")
        return 1

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    failures = 0

    llm_provider = str(cfg.get("llm_provider", "openai")).lower()
    stt_provider = str(cfg.get("stt_provider", "local_whisper")).lower()

    ok(f"llm_provider={llm_provider}")
    ok(f"stt_provider={stt_provider}")

    if llm_provider not in {"openai", "local_ollama"}:
        fail(f"Unsupported llm_provider configured: {llm_provider}")
        failures += 1

    imagemagick_path = cfg.get("imagemagick_path", "")
    if imagemagick_path and os.path.exists(imagemagick_path):
        ok(f"imagemagick_path exists: {imagemagick_path}")
    else:
        warn(
            "imagemagick_path is not set to a valid executable path. "
            "MoviePy subtitle rendering may fail."
        )

    firefox_profile = cfg.get("firefox_profile", "")
    if firefox_profile:
        if os.path.isdir(firefox_profile):
            ok(f"firefox_profile exists: {firefox_profile}")
        else:
            warn(f"firefox_profile does not exist: {firefox_profile}")
    else:
        warn(
            "firefox_profile is empty. This is fine for local-only generation, but browser automation requires it."
        )

    if llm_provider == "openai":
        openai_api_key = cfg.get("openai_api_key", "") or os.environ.get(
            "OPENAI_API_KEY", ""
        )
        openai_base = str(
            cfg.get("openai_base_url", "https://api.openai.com/v1")
        ).rstrip("/")
        openai_model = str(cfg.get("openai_model", "gpt-4.1-mini")).strip()

        if openai_api_key:
            ok("openai_api_key is set")
        else:
            fail("openai_api_key is empty (and OPENAI_API_KEY is not set)")
            failures += 1

        if openai_model:
            ok(f"openai_model configured: {openai_model}")
        else:
            fail("openai_model is empty")
            failures += 1

        reachable, detail = check_url(openai_base, timeout=8)
        if not reachable:
            warn(f"OpenAI base URL could not be reached: {detail}")
        else:
            ok(f"OpenAI base URL reachable: {openai_base}")
    else:
        base = str(cfg.get("ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
        reachable, detail = check_url(f"{base}/api/tags")
        if not reachable:
            fail(f"Ollama is not reachable at {base}: {detail}")
            failures += 1
        else:
            ok(f"Ollama reachable at {base}")
            try:
                tags = requests.get(f"{base}/api/tags", timeout=5).json()
                models = [m.get("name") for m in tags.get("models", [])]
                if models:
                    ok(f"Ollama models available: {', '.join(models[:10])}")
                else:
                    warn(
                        "No models found on Ollama. Pull a model first (e.g. 'ollama pull llama3.2:3b')."
                    )
            except Exception as exc:
                warn(f"Could not validate Ollama model list: {exc}")

    api_key = cfg.get("nanobanana2_api_key", "") or os.environ.get("GEMINI_API_KEY", "")
    nb2_base = str(
        cfg.get(
            "nanobanana2_api_base_url",
            "https://generativelanguage.googleapis.com/v1beta",
        )
    ).rstrip("/")
    if api_key:
        ok("nanobanana2_api_key is set")
    else:
        fail("nanobanana2_api_key is empty (and GEMINI_API_KEY is not set)")
        failures += 1

    reachable, detail = check_url(nb2_base, timeout=8)
    if not reachable:
        warn(f"Nano Banana 2 base URL could not be reached: {detail}")
    else:
        ok(f"Nano Banana 2 base URL reachable: {nb2_base}")

    if stt_provider == "local_whisper":
        try:
            import faster_whisper  # noqa: F401

            ok("faster-whisper is installed")
        except Exception as exc:
            fail(f"faster-whisper is not importable: {exc}")
            failures += 1

    if failures:
        print("")
        print(f"Preflight completed with {failures} blocking issue(s).")
        return 1

    print("")
    print("Preflight passed. Setup looks ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
