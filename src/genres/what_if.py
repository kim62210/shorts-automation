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
    concatenate_videoclips,
)


@register_genre
class WhatIfGenre(BaseGenre):
    name = "what_if"
    display_name = "Animal What If"
    default_effect = "ken_burns"
    default_subtitle_style = "classic"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate an animal-themed "What If" hypothetical scenario video script about the topic: {self.niche}.

IMPORTANT: The content MUST be about animals. This is for a cute animal YouTube channel called "PawPick".
Examples of good scenarios:
- "What if cats were smarter than humans?"
- "What if animals could talk?"
- "What if dinosaurs were still alive?"
- "What if dogs ruled the world?"
- "What if animals went to school?"

Return ONLY valid JSON in this exact format:
{{
  "scenario": "What if ... ? (a fun hypothetical question about animals)",
  "explanations": [
    {{"point": "First consequence or explanation about the animal scenario", "image_prompt": "Detailed AI image generation prompt featuring animals in an imaginative scene"}},
    {{"point": "Second consequence or explanation about the animal scenario", "image_prompt": "Detailed AI image generation prompt featuring animals in an imaginative scene"}},
    {{"point": "Third consequence or explanation about the animal scenario", "image_prompt": "Detailed AI image generation prompt featuring animals in an imaginative scene"}}
  ],
  "script": "Full narration script exploring the animal scenario and its fun consequences",
  "image_prompts": ["animal scene prompt 1", "animal scene prompt 2", "animal scene prompt 3"]
}}

The script must be narrated in {self.language}.
Make the scenario fun, imaginative, and always centered around animals.
Provide 3-5 explanation points.
Make image prompts detailed and vivid, always featuring cute or imaginative animal scenes.
"""
        content = self.generate_response_json(prompt)
        success(f"Generated what-if content: {content.get('scenario', '')[:60]}...")
        return content

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")

        tts_clip = AudioFileClip(tts_path)
        max_duration = tts_clip.duration

        video_size = (1080, 1920)
        scenario = content.get("scenario", "WHAT IF...?")
        explanations = content.get("explanations", [])

        # Intro: "WHAT IF...?" + scenario question frame
        intro_frame = self.generate_text_frame(
            texts=["WHAT IF...?", scenario[:80]],
            colors=["#FF6B35", "#FFFFFF"],
            bg_color="#0a0a1a",
            font_sizes=[80, 36],
        )
        intro_clip = ImageClip(intro_frame).with_duration(3).with_fps(30)

        # Generate clips for each explanation point
        point_clips = []
        remaining_duration = max_duration - 3
        per_point_duration = remaining_duration / max(len(explanations), 1)

        effect = self._get_effect()

        for idx, explanation in enumerate(explanations):
            if images and idx < len(images):
                if effect:
                    bg_clip = effect.apply([images[idx]], per_point_duration)
                else:
                    bg_clip = (
                        ImageClip(images[idx])
                        .with_duration(per_point_duration)
                        .with_fps(30)
                        .resized(new_size=video_size)
                    )
            else:
                point_text = explanation.get("point", "")[:60]
                fallback = self.generate_text_frame(
                    texts=[point_text],
                    colors=["#FFFFFF"],
                    bg_color="#0a0a1a",
                    font_sizes=[44],
                )
                bg_clip = ImageClip(fallback).with_duration(per_point_duration).with_fps(30)

            bg_clip = bg_clip.with_duration(per_point_duration).with_fps(30)
            point_clips.append(bg_clip)

        all_clips = [intro_clip] + point_clips

        # Add CTA (Call-To-Action) frame
        cta_img = images[-1] if images else None
        cta_frame = self.generate_cta_frame(cta_img)
        all_clips.append(ImageClip(cta_frame).with_duration(3.0).with_fps(30))

        video_clip = concatenate_videoclips(all_clips)
        video_clip = video_clip.with_duration(max_duration).with_fps(30)

        return self._finalize_video(video_clip, tts_path, combined_path)
