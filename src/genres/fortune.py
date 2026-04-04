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
    display_name = "My Animal Type"
    default_subtitle_style = "classic"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate a fun "what animal type are you?" personality reading related to the topic: {self.niche}.
The content MUST be about animals. Instead of tarot cards, each "card" is an animal type with personality traits.
Return your answer as JSON with exactly this structure:
{{
  "theme": "What Your Birth Month Says About Your Past-Life Animal",
  "cards": [
    {{"name": "Golden Retriever", "meaning": "You are a warm-hearted person who is loved by everyone..."}},
    {{"name": "Cat", "meaning": "You are independent and confident..."}}
  ],
  "reading": "Overall reading that ties all the animal types together into a cohesive, fun personality message",
  "script": "Full narration: introduce the theme, reveal each animal type with its personality traits, then deliver the overall reading",
  "image_prompts": ["Adorable golden retriever portrait, warm and friendly expression, soft lighting, 9:16 portrait...", "Cute cat with confident pose, elegant atmosphere, 9:16 portrait..."]
}}

Requirements:
- Generate 2-4 animal types, each representing a personality type
- The content MUST be about animals — each card's "name" should be an animal name, "meaning" should describe personality traits of people who match that animal
- Write everything in {self.language}
- The theme should be fun animal-personality content like "What Your Birth Month Says About Your Spirit Animal", "Your Blood Type Animal Match", "Your MBTI Animal Type" etc.
- Make it feel fun, relatable and shareable
- The reading should be playful and positive
- image_prompts: one prompt per animal type, each describing an adorable, expressive animal portrait. Cute, warm colors, soft lighting, 9:16 portrait.
- Return ONLY valid JSON, no markdown"""

        return self.generate_response_json(prompt)

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")

        tts_clip = AudioFileClip(tts_path)
        total_duration = tts_clip.duration

        theme = content.get("theme", "Today's Animal Type")
        cards = content.get("cards", [])
        reading = content.get("reading", "")

        # Intro frame
        if images:
            intro_frame = self.generate_text_on_image_frame(
                images[0], texts=[theme], colors=["#E8D5F5"], font_sizes=[56],
            )
        else:
            intro_frame = self.generate_text_frame(
                texts=[theme], colors=["#E8D5F5"], bg_color="#1a0a2e", font_sizes=[56],
            )

        # Card frames
        card_frames = []
        for idx, card in enumerate(cards):
            card_name = card.get("name", "")
            card_meaning = card.get("meaning", "")
            img = images[idx] if images and idx < len(images) else None
            if img:
                frame = self.generate_text_on_image_frame(
                    img, texts=[card_name, "", card_meaning],
                    colors=["#FFD700", "#FFFFFF", "#D4B8E8"],
                    font_sizes=[52, 20, 38],
                )
            else:
                frame = self.generate_text_frame(
                    texts=[card_name, "", card_meaning],
                    colors=["#FFD700", "#FFFFFF", "#D4B8E8"],
                    bg_color="#1a0a2e",
                    font_sizes=[52, 20, 38],
                )
            card_frames.append(frame)

        # Overall reading frame
        last_img = images[-1] if images else None
        if last_img:
            reading_frame = self.generate_text_on_image_frame(
                last_img, texts=["Your Result", "", reading],
                colors=["#FFD700", "#FFFFFF", "#E8D5F5"],
                font_sizes=[48, 20, 40],
            )
        else:
            reading_frame = self.generate_text_frame(
                texts=["Your Result", "", reading],
                colors=["#FFD700", "#FFFFFF", "#E8D5F5"],
                bg_color="#1a0a2e",
                font_sizes=[48, 20, 40],
            )

        # Timing allocation
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

        cta_img = images[-1] if images else None
        cta_frame = self.generate_cta_frame(cta_img)
        clips.append(ImageClip(cta_frame).with_duration(3.0).with_fps(30))

        video = concatenate_videoclips(clips)

        return self._finalize_video(video, tts_path, combined_path)
