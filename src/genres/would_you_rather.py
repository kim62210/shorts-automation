import os

from typing import List, Optional
from uuid import uuid4

from PIL import Image

from genres import register_genre
from genres.base import BaseGenre
from config import ROOT_DIR
from status import success
from moviepy import (
    AudioFileClip,
    ImageClip,
    TextClip,
    CompositeVideoClip,
)


@register_genre
class WouldYouRatherGenre(BaseGenre):
    name = "would_you_rather"
    display_name = "이것 vs 저것"
    default_effect = None
    default_subtitle_style = "bold_center"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate a "Would You Rather" / "This vs That" video script about the topic: {self.niche}.

Return ONLY valid JSON in this exact format:
{{
  "option_a": {{
    "text": "Option A description (short, punchy)",
    "image_prompt": "Detailed AI image generation prompt for option A"
  }},
  "option_b": {{
    "text": "Option B description (short, punchy)",
    "image_prompt": "Detailed AI image generation prompt for option B"
  }},
  "explanation": "Brief explanation or fun fact about both options",
  "script": "Full narration script presenting both options and the explanation",
  "image_prompts": ["prompt for option A", "prompt for option B"]
}}

The script must be narrated in {self.language}.
Make the two options genuinely interesting and thought-provoking.
Make image prompts detailed and vivid for AI image generation.
"""
        content = self.generate_response_json(prompt)
        success("Generated 'would you rather' content.")
        return content

    def _apply_color_tint(self, image_path: str, tint_rgb: tuple) -> str:
        """이미지에 색상 틴트를 적용한 새 파일을 반환"""
        img = Image.open(image_path).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (*tint_rgb, 80))
        tinted = Image.alpha_composite(img, overlay).convert("RGB")

        tinted_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
        tinted.save(tinted_path)
        return tinted_path

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")

        tts_clip = AudioFileClip(tts_path)
        max_duration = tts_clip.duration

        video_size = (1080, 1920)
        half_height = video_size[1] // 2

        # Option A 이미지 (상단, 빨간 틴트)
        if images and len(images) >= 1:
            tinted_a = self._apply_color_tint(images[0], (200, 50, 50))
            clip_a = (
                ImageClip(tinted_a)
                .with_duration(max_duration)
                .with_fps(30)
                .resized(new_size=(video_size[0], half_height))
                .with_position((0, 0))
            )
        else:
            frame_a = self.generate_text_frame(
                texts=[content.get("option_a", {}).get("text", "Option A")],
                colors=["#FF4444"],
                bg_color="#2a0a0a",
                size=(video_size[0], half_height),
                font_sizes=[48],
            )
            clip_a = (
                ImageClip(frame_a)
                .with_duration(max_duration)
                .with_fps(30)
                .with_position((0, 0))
            )

        # Option B 이미지 (하단, 파란 틴트)
        if images and len(images) >= 2:
            tinted_b = self._apply_color_tint(images[1], (50, 50, 200))
            clip_b = (
                ImageClip(tinted_b)
                .with_duration(max_duration)
                .with_fps(30)
                .resized(new_size=(video_size[0], half_height))
                .with_position((0, half_height))
            )
        else:
            frame_b = self.generate_text_frame(
                texts=[content.get("option_b", {}).get("text", "Option B")],
                colors=["#4444FF"],
                bg_color="#0a0a2a",
                size=(video_size[0], half_height),
                font_sizes=[48],
            )
            clip_b = (
                ImageClip(frame_b)
                .with_duration(max_duration)
                .with_fps(30)
                .with_position((0, half_height))
            )

        # Option A 텍스트 라벨
        text_a = content.get("option_a", {}).get("text", "Option A")
        label_a = (
            TextClip(
                text=text_a,
                font_size=42,
                color="#FFFFFF",
                font="Arial-Bold",
                stroke_color="#000000",
                stroke_width=2,
                size=(video_size[0] - 80, None),
                method="caption",
            )
            .with_duration(max_duration)
            .with_fps(30)
            .with_position(("center", half_height // 2 + 200))
        )

        # Option B 텍스트 라벨
        text_b = content.get("option_b", {}).get("text", "Option B")
        label_b = (
            TextClip(
                text=text_b,
                font_size=42,
                color="#FFFFFF",
                font="Arial-Bold",
                stroke_color="#000000",
                stroke_width=2,
                size=(video_size[0] - 80, None),
                method="caption",
            )
            .with_duration(max_duration)
            .with_fps(30)
            .with_position(("center", half_height + half_height // 2 + 200))
        )

        # 중앙 VS 배지
        vs_clip = (
            TextClip(
                text="VS",
                font_size=80,
                color="#FFD700",
                font="Arial-Bold",
                stroke_color="#000000",
                stroke_width=4,
            )
            .with_duration(max_duration)
            .with_fps(30)
            .with_position(("center", "center"))
        )

        video_clip = CompositeVideoClip(
            [clip_a, clip_b, label_a, label_b, vs_clip],
            size=video_size,
        ).with_duration(max_duration).with_fps(30)

        return self._finalize_video(video_clip, tts_path, combined_path)
