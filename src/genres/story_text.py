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
class StoryTextGenre(BaseGenre):
    name = "story_text"
    display_name = "Animal Stories"
    default_subtitle_style = "minimal_bottom"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate a short, heartwarming or funny animal story related to the topic: {self.niche}.
The story MUST be about animals — cute, touching, or humorous animal tales.
Return your answer as JSON with exactly this structure:
{{
  "title": "Story title",
  "paragraphs": ["First paragraph...", "Second paragraph...", "Third paragraph..."],
  "script": "The complete story text as one continuous narration",
  "image_prompts": ["Image prompt for paragraph 1...", "Image prompt for paragraph 2...", "Image prompt for paragraph 3..."]
}}

Requirements:
- The story MUST be about animals — a cat's adventure, a dog's heartwarming daily life, an unexpected animal friendship, a rescued animal's journey, etc.
- Write 3-5 short paragraphs that build emotion and have a heartwarming or funny conclusion
- Write everything in {self.language}
- The title should be catchy and make viewers want to watch (e.g., "How a Stray Kitten Became the Boss of Our House")
- The script field contains all paragraphs joined as continuous narration text
- Each paragraph should be short enough to fit on a mobile screen (2-4 sentences)
- image_prompts: one prompt per paragraph, each describing a warm, adorable animal scene matching the paragraph. Cute animals, soft warm lighting, photorealistic, 9:16 portrait.
- Return ONLY valid JSON, no markdown"""

        return self.generate_response_json(prompt)

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")

        tts_clip = AudioFileClip(tts_path)
        total_duration = tts_clip.duration

        title = content.get("title", "")
        paragraphs = content.get("paragraphs", [])

        if not paragraphs:
            paragraphs = [content.get("script", "")]

        # Title frame
        if images:
            title_frame = self.generate_text_on_image_frame(
                images[0], texts=["🐾 PawPick", "", title],
                colors=["#FF4500", "#FFFFFF", "#FFFFFF"],
                font_sizes=[36, 20, 52],
            )
        else:
            title_frame = self.generate_text_frame(
                texts=["🐾 PawPick", "", title],
                colors=["#FF4500", "#FFFFFF", "#FFFFFF"],
                bg_color="#1a1a2e",
                font_sizes=[36, 20, 52],
            )

        # Paragraph frames
        paragraph_frames = []
        for idx, para in enumerate(paragraphs):
            img = images[idx] if images and idx < len(images) else None
            if img:
                frame = self.generate_text_on_image_frame(
                    img, texts=[para], colors=["#E0E0E0"], font_sizes=[40],
                )
            else:
                frame = self.generate_text_frame(
                    texts=[para], colors=["#E0E0E0"], bg_color="#1a1a2e", font_sizes=[40],
                )
            paragraph_frames.append(frame)

        # Timing allocation
        title_dur = min(3.0, total_duration * 0.15)
        remaining = total_duration - title_dur
        para_dur = remaining / max(1, len(paragraph_frames))

        clips = []
        clips.append(
            ImageClip(title_frame).with_duration(title_dur).with_fps(30)
        )
        for pf in paragraph_frames:
            clips.append(
                ImageClip(pf).with_duration(para_dur).with_fps(30)
            )

        cta_img = images[-1] if images else None
        cta_frame = self.generate_cta_frame(cta_img)
        clips.append(ImageClip(cta_frame).with_duration(3.0).with_fps(30))

        video = concatenate_videoclips(clips)

        return self._finalize_video(video, tts_path, combined_path)
