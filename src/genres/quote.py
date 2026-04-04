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
class QuoteGenre(BaseGenre):
    name = "quote"
    display_name = "Animal Wisdom"
    default_subtitle_style = "minimal_bottom"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate a cute, funny, or heartwarming animal-themed quote related to the topic: {self.niche}.
The content MUST be about animals. Examples: wisdom we can learn from cats, funny dog philosophy, animal life lessons, etc.
Return your answer as JSON with exactly this structure:
{{
  "quote": "The full animal-themed quote text",
  "author": "Author name (a famous person who said something about animals, or a fictional animal character name)",
  "script": "Full narration that reads the quote with feeling and attributes it to the author",
  "image_prompts": ["A cute, heartwarming animal portrait or scene that matches the quote mood. Adorable animal, soft lighting, warm colors, 9:16 portrait orientation."]
}}

Requirements:
- The quote MUST be about animals — animal wisdom, funny animal observations, or heartwarming animal-human bonds
- Examples of good quotes: "What cats teach us about life", "Why living like a dog makes you happier", funny animal philosophy
- The author can be a real person known for loving animals, or a cute fictional animal character name
- Write everything in {self.language}
- The script should read the quote naturally, then mention the author
- image_prompts: exactly 1 prompt for a cute/wise animal image as background
- Return ONLY valid JSON, no markdown"""

        return self.generate_response_json(prompt)

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")

        tts_clip = AudioFileClip(tts_path)
        total_duration = tts_clip.duration

        quote = content.get("quote", "")
        author = content.get("author", "")

        texts = ['"', "", quote, "", f"- {author}"]
        colors = ["#FFFF00", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#AAAAAA"]
        font_sizes = [80, 20, 44, 20, 36]

        if images:
            frame = self.generate_text_on_image_frame(
                images[0], texts=texts, colors=colors, font_sizes=font_sizes,
            )
        else:
            frame = self.generate_text_frame(
                texts=texts, colors=colors, bg_color="#0f0a2e", font_sizes=font_sizes,
            )

        main_clip = ImageClip(frame).with_duration(total_duration).with_fps(30)

        # CTA frame (3 seconds)
        bg_img = images[0] if images else None
        cta_frame = self.generate_cta_frame(bg_img)
        cta_clip = ImageClip(cta_frame).with_duration(3.0).with_fps(30)

        video = concatenate_videoclips([main_clip, cta_clip])

        return self._finalize_video(video, tts_path, combined_path)
