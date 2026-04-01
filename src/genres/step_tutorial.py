import os

from typing import List, Optional
from uuid import uuid4

from PIL import Image, ImageDraw

from genres import register_genre
from genres.base import BaseGenre
from config import ROOT_DIR
from status import success
from moviepy import (
    AudioFileClip,
    ImageClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
)


@register_genre
class StepTutorialGenre(BaseGenre):
    name = "step_tutorial"
    display_name = "스텝 튜토리얼"
    default_effect = "slideshow"
    default_subtitle_style = "modern_box"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate a step-by-step tutorial video script about the topic: {self.niche}.

Return ONLY valid JSON in this exact format:
{{
  "title": "3 Steps to ...",
  "steps": [
    {{"number": 1, "title": "Step title", "description": "Step description", "image_prompt": "Detailed AI image generation prompt"}},
    {{"number": 2, "title": "Step title", "description": "Step description", "image_prompt": "Detailed AI image generation prompt"}},
    {{"number": 3, "title": "Step title", "description": "Step description", "image_prompt": "Detailed AI image generation prompt"}}
  ],
  "script": "Full narration script covering all steps",
  "image_prompts": ["prompt for step 1", "prompt for step 2", "prompt for step 3"]
}}

The script must be narrated in {self.language}.
Keep to 3-5 steps maximum.
Make image prompts detailed and vivid for AI image generation.
"""
        content = self.generate_response_json(prompt)
        success(f"Generated step tutorial content: {content.get('title', '')}")
        return content

    def _generate_progress_bar(self, current_step: int, total_steps: int,
                               size: tuple = (1080, 60)) -> str:
        """현재 단계 / 전체 단계를 나타내는 진행 바 이미지 생성"""
        img = Image.new("RGBA", size, (0, 0, 0, 160))
        draw = ImageDraw.Draw(img)

        padding = 40
        bar_height = 12
        bar_y = (size[1] - bar_height) // 2
        bar_width = size[0] - padding * 2

        # 배경 바
        draw.rounded_rectangle(
            [padding, bar_y, padding + bar_width, bar_y + bar_height],
            radius=6,
            fill=(80, 80, 80, 200),
        )

        # 진행 바
        fill_width = int(bar_width * (current_step / total_steps))
        if fill_width > 0:
            draw.rounded_rectangle(
                [padding, bar_y, padding + fill_width, bar_y + bar_height],
                radius=6,
                fill=(78, 205, 196, 255),
            )

        # 단계 점(dot) 표시
        for i in range(total_steps):
            dot_x = padding + int(bar_width * ((i + 0.5) / total_steps))
            dot_radius = 8
            if i < current_step:
                dot_color = (78, 205, 196, 255)
            else:
                dot_color = (120, 120, 120, 255)
            draw.ellipse(
                [dot_x - dot_radius, bar_y + bar_height // 2 - dot_radius,
                 dot_x + dot_radius, bar_y + bar_height // 2 + dot_radius],
                fill=dot_color,
            )

        bar_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
        img.save(bar_path)
        return bar_path

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")

        tts_clip = AudioFileClip(tts_path)
        max_duration = tts_clip.duration

        video_size = (1080, 1920)
        steps = content.get("steps", [])
        title = content.get("title", "Tutorial")
        total_steps = len(steps)

        # 인트로 프레임
        intro_frame = self.generate_text_frame(
            texts=[title],
            colors=["#4ECDC4"],
            bg_color="#0a0a1a",
            font_sizes=[64],
        )
        intro_clip = ImageClip(intro_frame).with_duration(3).with_fps(30)

        # 각 단계 클립 생성
        step_clips = []
        remaining_duration = max_duration - 3
        per_step_duration = remaining_duration / max(total_steps, 1)

        effect = self._get_effect()

        for idx, step in enumerate(steps):
            step_number = step.get("number", idx + 1)
            step_title = step.get("title", f"Step {step_number}")

            # 배경 이미지
            if images and idx < len(images):
                if effect:
                    bg_clip = effect.apply([images[idx]], per_step_duration)
                else:
                    bg_clip = (
                        ImageClip(images[idx])
                        .with_duration(per_step_duration)
                        .with_fps(30)
                        .resized(new_size=video_size)
                    )
            else:
                fallback = self.generate_text_frame(
                    texts=[f"Step {step_number}", step_title],
                    colors=["#4ECDC4", "#FFFFFF"],
                    bg_color="#0a0a1a",
                    font_sizes=[80, 40],
                )
                bg_clip = ImageClip(fallback).with_duration(per_step_duration).with_fps(30)

            bg_clip = bg_clip.with_duration(per_step_duration).with_fps(30)

            # 순위 번호 배지 오버레이
            badge_frame = self.generate_text_frame(
                texts=[f"STEP {step_number}"],
                colors=["#4ECDC4"],
                bg_color="#000000",
                font_sizes=[56],
            )
            badge_clip = (
                ImageClip(badge_frame)
                .with_duration(per_step_duration)
                .with_fps(30)
                .with_position(("center", 80))
            )

            # 단계 제목 오버레이
            title_clip = (
                TextClip(
                    text=step_title,
                    font_size=40,
                    color="#FFFFFF",
                    font="Arial-Bold",
                    stroke_color="#000000",
                    stroke_width=2,
                    size=(video_size[0] - 80, None),
                    method="caption",
                )
                .with_duration(per_step_duration)
                .with_fps(30)
                .with_position(("center", 200))
            )

            # 하단 진행 바
            progress_path = self._generate_progress_bar(
                idx + 1, total_steps, size=(video_size[0], 60)
            )
            progress_clip = (
                ImageClip(progress_path)
                .with_duration(per_step_duration)
                .with_fps(30)
                .with_position(("center", video_size[1] - 120))
            )

            step_comp = CompositeVideoClip(
                [bg_clip, badge_clip, title_clip, progress_clip],
                size=video_size,
            ).with_duration(per_step_duration)

            step_clips.append(step_comp)

        all_clips = [intro_clip] + step_clips
        video_clip = concatenate_videoclips(all_clips)
        video_clip = video_clip.with_duration(max_duration).with_fps(30)

        return self._finalize_video(video_clip, tts_path, combined_path)
