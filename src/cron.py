import sys

from status import error, success, info
from cache import get_accounts
from config import get_llm_provider, get_openai_model, get_ollama_model, get_verbose
from classes.Tts import TTS
from classes.YouTube import YouTube
from llm_provider import select_model


def main():
    account_id = str(sys.argv[1])
    model = str(sys.argv[2]) if len(sys.argv) > 2 else None
    provider = get_llm_provider()

    if provider not in {"openai", "local_ollama"}:
        error(f"Unsupported llm_provider configured: {provider}")
        sys.exit(1)

    if model:
        select_model(model)
    else:
        fallback_model = (
            get_openai_model().strip()
            if provider == "openai"
            else get_ollama_model().strip()
        )
        if not fallback_model:
            error(
                "No LLM model specified. Pass model name as second argument or configure a default model."
            )
            sys.exit(1)
        select_model(fallback_model)

    verbose = get_verbose()

    tts = TTS()
    accounts = get_accounts()

    if not account_id:
        error("Account UUID cannot be empty.")

    for acc in accounts:
        if acc["id"] == account_id:
            if verbose:
                info("Initializing YouTube...")
            youtube = YouTube(
                acc["id"],
                acc["nickname"],
                acc["firefox_profile"],
                acc["niche"],
                acc["language"],
            )
            video_path = youtube.generate_video(tts)
            if verbose:
                success(f"Generated local short: {video_path}")
            break


if __name__ == "__main__":
    main()
