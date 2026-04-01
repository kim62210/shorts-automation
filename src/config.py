import json
import os
import sys
import srt_equalizer

from pathlib import Path
from termcolor import colored

ROOT_DIR = str(Path(__file__).resolve().parent.parent)


def _read_config() -> dict:
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file)


def assert_folder_structure() -> None:
    mp_dir = os.path.join(ROOT_DIR, ".mp")
    if not os.path.exists(mp_dir):
        if get_verbose():
            print(colored(f"=> Creating .mp folder at {mp_dir}", "green"))
        os.makedirs(mp_dir)


def get_first_time_running() -> bool:
    return not os.path.exists(os.path.join(ROOT_DIR, ".mp"))


def get_verbose() -> bool:
    return _read_config()["verbose"]


def get_firefox_profile_path() -> str:
    return _read_config()["firefox_profile"]


def get_headless() -> bool:
    return _read_config()["headless"]


def get_llm_provider() -> str:
    return str(_read_config().get("llm_provider", "openai")).strip().lower()


def get_ollama_base_url() -> str:
    return _read_config().get("ollama_base_url", "http://127.0.0.1:11434")


def get_ollama_model() -> str:
    return _read_config().get("ollama_model", "")


def get_openai_base_url() -> str:
    return _read_config().get("openai_base_url", "https://api.openai.com/v1")


def get_openai_api_key() -> str:
    configured = _read_config().get("openai_api_key", "")
    return configured or os.environ.get("OPENAI_API_KEY", "")


def get_openai_model() -> str:
    return _read_config().get("openai_model", "gpt-4.1-mini")


def get_nanobanana2_api_base_url() -> str:
    return _read_config().get(
        "nanobanana2_api_base_url",
        "https://generativelanguage.googleapis.com/v1beta",
    )


def get_nanobanana2_api_key() -> str:
    configured = _read_config().get("nanobanana2_api_key", "")
    return configured or os.environ.get("GEMINI_API_KEY", "")


def get_nanobanana2_model() -> str:
    return _read_config().get("nanobanana2_model", "gemini-3.1-flash-image-preview")


def get_nanobanana2_aspect_ratio() -> str:
    return _read_config().get("nanobanana2_aspect_ratio", "9:16")


def get_threads() -> int:
    return _read_config()["threads"]


def get_zip_url() -> str:
    return _read_config()["zip_url"]


def get_is_for_kids() -> bool:
    return _read_config()["is_for_kids"]


def get_tts_voice() -> str:
    return _read_config().get("tts_voice", "Jasper")


def get_assemblyai_api_key() -> str:
    return _read_config()["assembly_ai_api_key"]


def get_stt_provider() -> str:
    return _read_config().get("stt_provider", "local_whisper")


def get_whisper_model() -> str:
    return _read_config().get("whisper_model", "base")


def get_whisper_device() -> str:
    return _read_config().get("whisper_device", "auto")


def get_whisper_compute_type() -> str:
    return _read_config().get("whisper_compute_type", "int8")


def equalize_subtitles(srt_path: str, max_chars: int = 10) -> None:
    srt_equalizer.equalize_srt_file(srt_path, srt_path, max_chars)


def get_font() -> str:
    return _read_config()["font"]


def get_fonts_dir() -> str:
    return os.path.join(ROOT_DIR, "fonts")


def get_imagemagick_path() -> str:
    return _read_config()["imagemagick_path"]


def get_script_sentence_length() -> int:
    config_json = _read_config()
    if config_json.get("script_sentence_length") is not None:
        return config_json["script_sentence_length"]
    return 4
