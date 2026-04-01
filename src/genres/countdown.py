import os

from typing import List, Optional
from uuid import uuid4

from genres import register_genre
from genres.base import BaseGenre
from config import ROOT_DIR
from status import success
from moviepy import (
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
)


@register_genre
class CountdownGenre(BaseGenre):
    name = "countdown"
    display_name = "카운트다운 / 랭킹"
    default_effect = "ken_burns"
    default_subtitle_style = "modern_box"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate a "Top 5" countdown video script about the topic: {self.niche}.

Return ONLY valid JSON in this exact format:
{{
  "title": "Top 5 ...",
  "items": [
    {{"rank": 5, "name": "...", "description": "Short description", "image_prompt": "Detailed image generation prompt"}},
    {{"rank": 4, "name": "...", "description": "Short description", "image_prompt": "Detailed image generation prompt"}},
    {{"rank": 3, "name": "...", "description": "Short description", "image_prompt": "Detailed image generation prompt"}},
    {{"rank": 2, "name": "...", "description": "Short description", "image_prompt": "Detailed image generation prompt"}},
    {{"rank": 1, "name": "...", "description": "Short description", "image_prompt": "Detailed image generation prompt"}}
  ],
  "script": "Full narration script covering all 5 items from rank 5 to 1",
  "image_prompts": ["prompt for rank 5", "prompt for rank 4", "prompt for rank 3", "prompt for rank 2", "prompt for rank 1"]
}}

Items must be ordered from rank 5 (lowest) to rank 1 (highest).
The script must be narrated in {self.language}.
image_prompts array must match the items' image_prompt fields in order.
Make image prompts detailed and vivid for AI image generation.
"""
        content = self.generate_response_json(prompt)
        success(f"Generated countdown content: {content.get('title', '')}")
        return content

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")

        tts_clip = AudioFileClip(tts_path)
        max_duration = tts_clip.duration

        items = content.get("items", [])
        title = content.get("title", "Top 5")

        # 인트로 프레임 (title 텍스트, 다크 배경)
        intro_frame = self.generate_text_frame(
            texts=[title],
            colors=["#FFD700"],
            bg_color="#0a0a1a",
            font_sizes=[72],
        )
        intro_clip = ImageClip(intro_frame).with_duration(3).with_fps(30)

        # 각 항목 클립 생성
        item_clips = []
        remaining_duration = max_duration - 3
        per_item_duration = remaining_duration / max(len(items), 1)

        effect = self._get_effect()

        for idx, item in enumerate(items):
            rank = item.get("rank", len(items) - idx)

            # 순위 배지 오버레이 프레임
            badge_frame = self.generate_text_frame(
                texts=[f"#{rank}"],
                colors=["#FFD700"],
                bg_color="#000000",
                font_sizes=[120],
            )

            if images and idx < len(images):
                if effect:
                    bg_clip = effect.apply([images[idx]], per_item_duration)
                else:
                    bg_clip = ImageClip(images[idx]).with_duration(per_item_duration).with_fps(30)
                    bg_clip = bg_clip.resized(new_size=(1080, 1920))
            else:
                desc_text = item.get("name", f"#{rank}")
                fallback = self.generate_text_frame(
                    texts=[f"#{rank}", desc_text],
                    colors=["#FFD700", "#FFFFFF"],
                    bg_color="#0a0a1a",
                    font_sizes=[120, 48],
                )
                bg_clip = ImageClip(fallback).with_duration(per_item_duration).with_fps(30)

            bg_clip = bg_clip.with_duration(per_item_duration).with_fps(30)

            badge_clip = (
                ImageClip(badge_frame)
                .with_duration(per_item_duration)
                .with_fps(30)
                .with_position(("center", 80))
            )

            item_comp = CompositeVideoClip(
                [bg_clip, badge_clip], size=(1080, 1920)
            ).with_duration(per_item_duration)

            item_clips.append(item_comp)

        all_clips = [intro_clip] + item_clips
        video_clip = concatenate_videoclips(all_clips)
        video_clip = video_clip.with_duration(max_duration).with_fps(30)

        return self._finalize_video(video_clip, tts_path, combined_path)
