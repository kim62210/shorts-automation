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
    display_name = "Animal Facts Guide"
    default_effect = "slideshow"
    default_subtitle_style = "modern_box"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate an animal-themed step-by-step knowledge/tips video script about the topic: {self.niche}.

IMPORTANT: The content MUST be about animals. This is for a cute animal YouTube channel called "PawPick".
Instead of generic tutorials, generate fun animal knowledge or tips in step format.
Examples of good titles:
- "3 Steps to Read Your Dog's Mood from Their Expression"
- "3 Steps to Befriend a Cat"
- "3 Steps to Take Great Animal Photos at the Zoo"
- "3 Steps to Tell If Your Hamster Is Happy"
- "3 Steps to Safely Bond with a Stray Cat"

Return ONLY valid JSON in this exact format:
{{
  "title": "Animal topic in N steps",
  "steps": [
    {{"number": 1, "title": "Step title about animals", "description": "Step description about animals", "image_prompt": "Detailed AI image generation prompt featuring cute animals"}},
    {{"number": 2, "title": "Step title about animals", "description": "Step description about animals", "image_prompt": "Detailed AI image generation prompt featuring cute animals"}},
    {{"number": 3, "title": "Step title about animals", "description": "Step description about animals", "image_prompt": "Detailed AI image generation prompt featuring cute animals"}}
  ],
  "script": "Full narration script covering all steps about animal knowledge",
  "image_prompts": ["animal scene prompt for step 1", "animal scene prompt for step 2", "animal scene prompt for step 3"]
}}

The script must be narrated in {self.language}.
Keep to 3-5 steps maximum.
Make image prompts detailed and vivid, always featuring cute or interesting animal scenes.
"""
        content = self.generate_response_json(prompt)
        success(f"Generated step tutorial content: {content.get('title', '')}")
        return content

    def _generate_progress_bar(self, current_step: int, total_steps: int,
                               size: tuple = (1080, 60)) -> str:
        """Generate a progress bar image showing current step / total steps."""
        img = Image.new("RGBA", size, (0, 0, 0, 160))
        draw = ImageDraw.Draw(img)

        padding = 40
        bar_height = 12
        bar_y = (size[1] - bar_height) // 2
        bar_width = size[0] - padding * 2

        # Background bar
        draw.rounded_rectangle(
            [padding, bar_y, padding + bar_width, bar_y + bar_height],
            radius=6,
            fill=(80, 80, 80, 200),
        )

        # Progress bar
        fill_width = int(bar_width * (current_step / total_steps))
        if fill_width > 0:
            draw.rounded_rectangle(
                [padding, bar_y, padding + fill_width, bar_y + bar_height],
                radius=6,
                fill=(78, 205, 196, 255),
            )

        # Step dot indicators
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
        title = content.get("title", "Guide")
        total_steps = len(steps)

        # Intro frame
        intro_frame = self.generate_text_frame(
            texts=[title],
            colors=["#4ECDC4"],
            bg_color="#0a0a1a",
            font_sizes=[64],
        )
        intro_clip = ImageClip(intro_frame).with_duration(3).with_fps(30)

        # Generate clips for each step
        step_clips = []
        remaining_duration = max_duration - 3
        per_step_duration = remaining_duration / max(total_steps, 1)

        effect = self._get_effect()

        for idx, step in enumerate(steps):
            step_number = step.get("number", idx + 1)
            step_title = step.get("title", f"Step {step_number}")

            # Background image
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
                    texts=[f"STEP {step_number}", step_title],
                    colors=["#4ECDC4", "#FFFFFF"],
                    bg_color="#0a0a1a",
                    font_sizes=[80, 40],
                )
                bg_clip = ImageClip(fallback).with_duration(per_step_duration).with_fps(30)

            bg_clip = bg_clip.with_duration(per_step_duration).with_fps(30)

            # Step number badge overlay
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

            # Step title overlay
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

            # Bottom progress bar
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

        # Add CTA (Call-To-Action) frame
        cta_img = images[-1] if images else None
        cta_frame = self.generate_cta_frame(cta_img)
        all_clips.append(ImageClip(cta_frame).with_duration(3.0).with_fps(30))

        video_clip = concatenate_videoclips(all_clips)
        video_clip = video_clip.with_duration(max_duration).with_fps(30)

        return self._finalize_video(video_clip, tts_path, combined_path)
