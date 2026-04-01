import os

from typing import List, Optional
from uuid import uuid4

from genres import register_genre
from genres.base import BaseGenre
from config import ROOT_DIR
from moviepy import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips,
)


@register_genre
class FortuneGenre(BaseGenre):
    name = "fortune"
    display_name = "운세 / 타로 / MBTI"
    default_subtitle_style = "classic"
    needs_images = False

    def generate_content(self) -> dict:
        prompt = f"""Generate a mystical tarot or fortune reading related to the topic: {self.niche}.
Return your answer as JSON with exactly this structure:
{{
  "theme": "Today's Tarot Reading",
  "cards": [
    {{"name": "The Star", "meaning": "Hope and inspiration are guiding you..."}},
    {{"name": "The Moon", "meaning": "Trust your intuition..."}}
  ],
  "reading": "Overall reading that ties all the cards together into a cohesive message",
  "script": "Full narration: introduce the theme, reveal each card with its meaning, then deliver the overall reading"
}}

Requirements:
- Generate 2-4 tarot cards with meaningful interpretations
- Write everything in {self.language}
- The theme can be tarot, horoscope, fortune cookie, or MBTI-style reading
- Make it feel mystical and personal
- The reading should be encouraging and insightful
- Return ONLY valid JSON, no markdown"""

        return self.generate_response_json(prompt)

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")

        tts_clip = AudioFileClip(tts_path)
        total_duration = tts_clip.duration

        theme = content.get("theme", "Today's Reading")
        cards = content.get("cards", [])
        reading = content.get("reading", "")

        # 인트로 프레임
        intro_frame = self.generate_text_frame(
            texts=[theme],
            colors=["#E8D5F5"],
            bg_color="#1a0a2e",
            font_sizes=[56],
        )

        # 카드 프레임들
        card_frames = []
        for card in cards:
            card_name = card.get("name", "")
            card_meaning = card.get("meaning", "")
            frame = self.generate_text_frame(
                texts=[card_name, "", card_meaning],
                colors=["#FFD700", "#FFFFFF", "#D4B8E8"],
                bg_color="#1a0a2e",
                font_sizes=[52, 20, 38],
            )
            card_frames.append(frame)

        # 종합 리딩 프레임
        reading_frame = self.generate_text_frame(
            texts=["Overall Reading", "", reading],
            colors=["#FFD700", "#FFFFFF", "#E8D5F5"],
            bg_color="#1a0a2e",
            font_sizes=[48, 20, 40],
        )

        # 타이밍 배분
        intro_dur = 3.0
        card_dur = 4.0
        fixed_total = intro_dur + (card_dur * len(card_frames))
        if fixed_total >= total_duration:
            ratio = total_duration * 0.85 / fixed_total
            intro_dur *= ratio
            card_dur *= ratio
        reading_dur = total_duration - intro_dur - (card_dur * len(card_frames))

        clips = []
        clips.append(
            ImageClip(intro_frame).with_duration(intro_dur).with_fps(30)
        )
        for cf in card_frames:
            clips.append(
                ImageClip(cf).with_duration(card_dur).with_fps(30)
            )
        clips.append(
            ImageClip(reading_frame).with_duration(reading_dur).with_fps(30)
        )

        video = concatenate_videoclips(clips)

        return self._finalize_video(video, tts_path, combined_path)
