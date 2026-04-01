import os
import sys
import schedule
import subprocess

from uuid import uuid4
from termcolor import colored
from prettytable import PrettyTable

from cache import get_accounts, add_account, remove_account
from utils import rem_temp_files, fetch_songs
from config import ROOT_DIR, get_verbose, assert_folder_structure, get_first_time_running
from config import get_llm_provider, get_openai_model, get_ollama_model
from status import error, success, info, warning, question
from constants import YOUTUBE_OPTIONS, YOUTUBE_CRON_OPTIONS
from classes.Tts import TTS
from classes.YouTube import YouTube
from llm_provider import list_models, select_model, get_active_model
from genres import list_genres
from effects import list_effects
from subtitles import list_styles

# 장르/효과/자막 모듈 자동 등록
import genres.narration
import genres.quiz
import genres.quote
import genres.story_text
import genres.two_truths
import genres.fortune
import genres.countdown
import genres.before_after
import genres.would_you_rather
import genres.step_tutorial
import genres.what_if
import genres.wait_for_it
import genres.spot_difference
import effects.slideshow
import effects.ken_burns
import effects.fade_transition
import effects.broll
import subtitles.classic
import subtitles.modern_box
import subtitles.bold_center
import subtitles.highlight_word
import subtitles.minimal_bottom


def select_genre() -> tuple:
    """장르 선택 메뉴. (genre_name, effect_override, subtitle_override) 반환."""
    genres = list_genres()

    info("\n========== CONTENT GENRES =========", False)
    for idx, genre_cls in enumerate(genres):
        label = genre_cls.display_name
        print(colored(f" {idx + 1}. {label}", "cyan"))
    info("===================================\n", False)

    genre_input = int(question("Select a genre: ")) - 1
    if genre_input < 0 or genre_input >= len(genres):
        warning("Invalid selection. Using default (narration).")
        return "narration", None, None

    selected = genres[genre_input]
    genre_name = selected.name

    effect_override = None
    subtitle_override = None

    customize = question("Customize effect/subtitle? (y/N): ").strip().lower()
    if customize == "y":
        effects_list = list_effects()
        if effects_list and selected.default_effect:
            info(f"\n  Current effect: {selected.default_effect}", False)
            info("  Available effects:", False)
            for idx, eff_cls in enumerate(effects_list):
                print(colored(f"   {idx + 1}. {eff_cls.display_name}", "cyan"))
            print(colored(f"   0. Keep default", "cyan"))
            eff_input = question("  Select effect (0=default): ").strip()
            if eff_input and eff_input != "0":
                eff_idx = int(eff_input) - 1
                if 0 <= eff_idx < len(effects_list):
                    effect_override = effects_list[eff_idx].name

        styles_list = list_styles()
        if styles_list:
            info(f"\n  Current subtitle: {selected.default_subtitle_style}", False)
            info("  Available styles:", False)
            for idx, sty_cls in enumerate(styles_list):
                print(colored(f"   {idx + 1}. {sty_cls.display_name}", "cyan"))
            print(colored(f"   0. Keep default", "cyan"))
            sty_input = question("  Select style (0=default): ").strip()
            if sty_input and sty_input != "0":
                sty_idx = int(sty_input) - 1
                if 0 <= sty_idx < len(styles_list):
                    subtitle_override = styles_list[sty_idx].name

    return genre_name, effect_override, subtitle_override


def main():
    cached_accounts = get_accounts()

    if len(cached_accounts) == 0:
        warning("No accounts found in cache. Create one now?")
        user_input = question("Yes/No: ")

        if user_input.lower() == "yes":
            generated_uuid = str(uuid4())

            success(f" => Generated ID: {generated_uuid}")
            nickname = question(" => Enter a nickname for this account: ")
            fp_profile = question(
                " => Enter the path to the Firefox profile (optional for local-only generation): "
            )
            niche = question(" => Enter the account niche: ")
            language = question(" => Enter the account language: ")

            account_data = {
                "id": generated_uuid,
                "nickname": nickname,
                "firefox_profile": fp_profile,
                "niche": niche,
                "language": language,
                "videos": [],
            }

            add_account(account_data)

            success("Account configured successfully!")
    else:
        table = PrettyTable()
        table.field_names = ["ID", "UUID", "Nickname", "Niche"]

        for account in cached_accounts:
            table.add_row(
                [
                    cached_accounts.index(account) + 1,
                    colored(account["id"], "cyan"),
                    colored(account["nickname"], "blue"),
                    colored(account["niche"], "green"),
                ]
            )

        print(table)
        info("Type 'd' to delete an account.", False)

        user_input = question(
            "Select an account to start (or 'd' to delete): "
        ).strip()

        if user_input.lower() == "d":
            delete_input = question("Enter account number to delete: ").strip()
            account_to_delete = None

            for account in cached_accounts:
                if str(cached_accounts.index(account) + 1) == delete_input:
                    account_to_delete = account
                    break

            if account_to_delete is None:
                error("Invalid account selected. Please try again.")
            else:
                confirm = (
                    question(
                        f"Are you sure you want to delete '{account_to_delete['nickname']}'? (Yes/No): "
                    )
                    .strip()
                    .lower()
                )

                if confirm == "yes":
                    remove_account(account_to_delete["id"])
                    success("Account removed successfully!")
                else:
                    warning("Account deletion canceled.", False)

            return

        selected_account = None

        for account in cached_accounts:
            if str(cached_accounts.index(account) + 1) == user_input:
                selected_account = account

        if selected_account is None:
            error("Invalid account selected. Please try again.")
            main()
        else:
            youtube = YouTube(
                selected_account["id"],
                selected_account["nickname"],
                selected_account["firefox_profile"],
                selected_account["niche"],
                selected_account["language"],
            )

            while True:
                rem_temp_files()
                info("\n============ OPTIONS ============", False)

                for idx, youtube_option in enumerate(YOUTUBE_OPTIONS):
                    print(colored(f" {idx + 1}. {youtube_option}", "cyan"))

                info("=================================\n", False)

                user_input = int(question("Select an option: "))
                tts = TTS()

                if user_input == 1:
                    genre_name, eff_override, sub_override = select_genre()
                    video_path = youtube.generate_video(
                        tts,
                        genre_name=genre_name,
                        effect_override=eff_override,
                        subtitle_override=sub_override,
                    )
                    success(f"Local video generated: {os.path.abspath(video_path)}")
                elif user_input == 2:
                    videos = youtube.get_videos()

                    if len(videos) > 0:
                        videos_table = PrettyTable()
                        videos_table.field_names = ["ID", "Date", "Title"]

                        for video in videos:
                            videos_table.add_row(
                                [
                                    videos.index(video) + 1,
                                    colored(video["date"], "blue"),
                                    colored(video["title"][:60] + "...", "green"),
                                ]
                            )

                        print(videos_table)
                    else:
                        warning(" No videos found.")
                elif user_input == 3:
                    info("How often do you want to generate a local video?")

                    info("\n============ OPTIONS ============", False)
                    for idx, cron_option in enumerate(YOUTUBE_CRON_OPTIONS):
                        print(colored(f" {idx + 1}. {cron_option}", "cyan"))

                    info("=================================\n", False)

                    user_input = int(question("Select an Option: "))

                    cron_script_path = os.path.join(ROOT_DIR, "src", "cron.py")
                    command = [
                        "python",
                        cron_script_path,
                        selected_account["id"],
                        get_active_model(),
                    ]

                    def job():
                        subprocess.run(command)

                    if user_input == 1:
                        schedule.every(1).day.do(job)
                        success("Set up CRON Job.")
                    elif user_input == 2:
                        schedule.every().day.at("10:00").do(job)
                        schedule.every().day.at("16:00").do(job)
                        success("Set up CRON Job.")
                    elif user_input == 3:
                        schedule.every().day.at("08:00").do(job)
                        schedule.every().day.at("12:00").do(job)
                        schedule.every().day.at("18:00").do(job)
                        success("Set up CRON Job.")
                    else:
                        break
                elif user_input == 4:
                    if get_verbose():
                        info(" => Exiting...", False)
                    break


if __name__ == "__main__":
    print(colored("\n=== Shorts Automation ===\n", "cyan", attrs=["bold"]))

    first_time = get_first_time_running()

    if first_time:
        print(
            colored(
                "First time running! Setting up folder structure...",
                "yellow",
            )
        )

    assert_folder_structure()
    rem_temp_files()
    fetch_songs()

    provider = get_llm_provider()
    if provider not in {"openai", "local_ollama"}:
        error(f"Unsupported llm_provider configured: {provider}")
        sys.exit(1)

    if provider == "openai":
        configured_model = get_openai_model().strip()
        if not configured_model:
            error("No OpenAI model configured. Set openai_model in config.json.")
            sys.exit(1)

        select_model(configured_model)
        success(f"Using OpenAI model: {configured_model}")
    else:
        configured_model = get_ollama_model()
        if configured_model:
            select_model(configured_model)
            success(f"Using configured model: {configured_model}")
        else:
            try:
                models = list_models()
            except Exception as e:
                error(f"Could not connect to Ollama: {e}")
                sys.exit(1)

            if not models:
                error(
                    "No models found on Ollama. Pull a model first (e.g. 'ollama pull llama3.2:3b')."
                )
                sys.exit(1)

            info("\n========== OLLAMA MODELS =========", False)
            for idx, model_name in enumerate(models):
                print(colored(f" {idx + 1}. {model_name}", "cyan"))
            info("==================================\n", False)

            model_choice = None
            while model_choice is None:
                raw = input(colored("Select a model: ", "magenta")).strip()
                try:
                    choice_idx = int(raw) - 1
                    if 0 <= choice_idx < len(models):
                        model_choice = models[choice_idx]
                    else:
                        warning("Invalid selection. Try again.")
                except ValueError:
                    warning("Please enter a number.")

            select_model(model_choice)
            success(f"Using model: {model_choice}")

    while True:
        main()
