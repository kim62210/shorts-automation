import json
import time
import os

from typing import List, Optional
from datetime import datetime

from utils import build_url
from cache import get_youtube_cache_path
from .Tts import TTS
from config import ROOT_DIR, get_verbose, get_headless, get_is_for_kids
from status import error, success, info, warning
from constants import (
    YOUTUBE_TEXTBOX_ID,
    YOUTUBE_MADE_FOR_KIDS_NAME,
    YOUTUBE_NOT_MADE_FOR_KIDS_NAME,
    YOUTUBE_NEXT_BUTTON_ID,
    YOUTUBE_RADIO_BUTTON_XPATH,
    YOUTUBE_DONE_BUTTON_ID,
)
from genres import get_genre


class YouTube:
    """
    YouTube Shorts Automation.
    장르 디스패치 + 계정 관리 + 업로드.
    """

    def __init__(
        self,
        account_uuid: str,
        account_nickname: str,
        fp_profile_path: str,
        niche: str,
        language: str,
    ) -> None:
        self._account_uuid: str = account_uuid
        self._account_nickname: str = account_nickname
        self._fp_profile_path: str = fp_profile_path
        self._niche: str = niche
        self._language: str = language

        self.browser = None

    @property
    def niche(self) -> str:
        return self._niche

    @property
    def language(self) -> str:
        return self._language

    def generate_video(self, tts_instance: TTS,
                       genre_name: str = "narration",
                       effect_override: Optional[str] = None,
                       subtitle_override: Optional[str] = None) -> str:
        genre_cls = get_genre(genre_name)
        genre = genre_cls(
            niche=self._niche,
            language=self._language,
            effect_override=effect_override,
            subtitle_override=subtitle_override,
        )
        path = genre.generate_video(tts_instance)
        self.video_path = os.path.abspath(path)
        return path

    # ── Browser Automation ───────────────────────────

    def _initialize_browser(self) -> None:
        if self.browser is not None:
            return

        if not self._fp_profile_path:
            raise RuntimeError(
                "Firefox profile path is empty. Upload automation requires a logged-in Firefox profile."
            )

        if not os.path.isdir(self._fp_profile_path):
            raise RuntimeError(
                f"Firefox profile path does not exist or is not a directory: {self._fp_profile_path}"
            )

        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        from webdriver_manager.firefox import GeckoDriverManager

        options = Options()
        if get_headless():
            options.add_argument("--headless")

        options.add_argument("-profile")
        options.add_argument(self._fp_profile_path)

        service = Service(GeckoDriverManager().install())
        self.browser = webdriver.Firefox(service=service, options=options)

    def get_channel_id(self) -> str:
        self._initialize_browser()
        driver = self.browser
        if driver is None:
            raise RuntimeError(
                "Firefox browser could not be initialized for upload automation."
            )

        driver.get("https://studio.youtube.com")
        time.sleep(2)
        channel_id = driver.current_url.split("/")[-1]
        self.channel_id = channel_id

        return channel_id

    def upload_video(self) -> bool:
        try:
            from selenium.webdriver.common.by import By

            self.get_channel_id()

            driver = self.browser
            if driver is None:
                raise RuntimeError(
                    "Firefox browser could not be initialized for upload automation."
                )
            verbose = get_verbose()

            driver.get("https://www.youtube.com/upload")

            file_picker = driver.find_element(By.TAG_NAME, "ytcp-uploads-file-picker")
            file_input = file_picker.find_element(By.TAG_NAME, "input")
            file_input.send_keys(self.video_path)

            time.sleep(5)

            textboxes = driver.find_elements(By.ID, YOUTUBE_TEXTBOX_ID)
            title_el = textboxes[0]
            description_el = textboxes[-1]

            if verbose:
                info("\t=> Setting title...")
            title_el.click()
            time.sleep(1)
            title_el.clear()
            title_el.send_keys(self.metadata["title"])

            if verbose:
                info("\t=> Setting description...")
            time.sleep(10)
            description_el.click()
            time.sleep(0.5)
            description_el.clear()
            description_el.send_keys(self.metadata["description"])

            time.sleep(0.5)

            if verbose:
                info("\t=> Setting `made for kids` option...")

            is_for_kids_checkbox = driver.find_element(
                By.NAME, YOUTUBE_MADE_FOR_KIDS_NAME
            )
            is_not_for_kids_checkbox = driver.find_element(
                By.NAME, YOUTUBE_NOT_MADE_FOR_KIDS_NAME
            )

            if not get_is_for_kids():
                is_not_for_kids_checkbox.click()
            else:
                is_for_kids_checkbox.click()

            time.sleep(0.5)

            if verbose:
                info("\t=> Clicking next...")
            next_button = driver.find_element(By.ID, YOUTUBE_NEXT_BUTTON_ID)
            next_button.click()

            if verbose:
                info("\t=> Clicking next again...")
            next_button = driver.find_element(By.ID, YOUTUBE_NEXT_BUTTON_ID)
            next_button.click()

            time.sleep(2)

            if verbose:
                info("\t=> Clicking next again...")
            next_button = driver.find_element(By.ID, YOUTUBE_NEXT_BUTTON_ID)
            next_button.click()

            if verbose:
                info("\t=> Setting as unlisted...")
            radio_button = driver.find_elements(By.XPATH, YOUTUBE_RADIO_BUTTON_XPATH)
            radio_button[2].click()

            if verbose:
                info("\t=> Clicking done button...")
            done_button = driver.find_element(By.ID, YOUTUBE_DONE_BUTTON_ID)
            done_button.click()

            time.sleep(2)

            if verbose:
                info("\t=> Getting video URL...")

            driver.get(
                f"https://studio.youtube.com/channel/{self.channel_id}/videos/short"
            )
            time.sleep(2)
            videos = driver.find_elements(By.TAG_NAME, "ytcp-video-row")
            first_video = videos[0]
            anchor_tag = first_video.find_element(By.TAG_NAME, "a")
            href = anchor_tag.get_attribute("href")
            if verbose:
                info(f"\t=> Extracting video ID from URL: {href}")
            video_id = href.split("/")[-2]

            url = build_url(video_id)
            self.uploaded_video_url = url

            if verbose:
                success(f" => Uploaded Video: {url}")

            self.add_video(
                {
                    "title": self.metadata["title"],
                    "description": self.metadata["description"],
                    "url": url,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

            driver.quit()
            self.browser = None
            return True
        except Exception as e:
            if self.browser is not None:
                self.browser.quit()
                self.browser = None
            warning(f"Upload failed: {e}")
            return False

    # ── Cache ────────────────────────────────────────

    def add_video(self, video: dict) -> None:
        videos = self.get_videos()
        videos.append(video)

        cache = get_youtube_cache_path()

        with open(cache, "r") as file:
            previous_json = json.loads(file.read())
            accounts = previous_json["accounts"]
            for account in accounts:
                if account["id"] == self._account_uuid:
                    account["videos"].append(video)

            with open(cache, "w") as f:
                f.write(json.dumps(previous_json))

    def get_videos(self) -> List[dict]:
        if not os.path.exists(get_youtube_cache_path()):
            with open(get_youtube_cache_path(), "w") as file:
                json.dump({"videos": []}, file, indent=4)
            return []

        videos = []
        with open(get_youtube_cache_path(), "r") as file:
            previous_json = json.loads(file.read())
            accounts = previous_json["accounts"]
            for account in accounts:
                if account["id"] == self._account_uuid:
                    videos = account["videos"]

        return videos
