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
class TwoTruthsGenre(BaseGenre):
    name = "two_truths"
    display_name = "Animal Facts: True or False"
    default_subtitle_style = "bold_center"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate a "Two Truths and a Lie" challenge about animals, related to the topic: {self.niche}.
The content MUST be about animals — surprising and fun animal facts where one is false.
Return your answer as JSON with exactly this structure:
{{
  "statements": ["Animal fact 1 (true or false)", "Animal fact 2 (true or false)", "Animal fact 3 (true or false)"],
  "lie_index": 1,
  "explanation": "Why the lie is false and what the truth actually is",
  "script": "Full narration: present the three animal facts, ask which is false, reveal the answer, and explain",
  "image_prompts": ["A vivid, eye-catching image of cute animals related to the facts. Photorealistic, adorable, 9:16 portrait orientation."]
}}

Requirements:
- All three statements MUST be about animals (animal abilities, behaviors, biology, fun facts)
- Two statements must be true and one must be a believable lie
- Write everything in {self.language}
- lie_index is 0-based (0, 1, or 2)
- The statements should be surprising and fascinating animal facts that make viewers go "really?!"
- The lie should be plausible enough to fool people
- image_prompts: exactly 1 prompt for a cute/interesting animal background image
- Return ONLY valid JSON, no markdown"""

        return self.generate_response_json(prompt)

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")

        tts_clip = AudioFileClip(tts_path)
        total_duration = tts_clip.duration

        statements = content.get("statements", [])
        lie_index = content.get("lie_index", 0)
        explanation = content.get("explanation", "")

        bg_img = images[0] if images else None
        _frame = self.generate_text_on_image_frame if bg_img else self.generate_text_frame

        def make_frame(texts, colors, font_sizes):
            if bg_img:
                return _frame(bg_img, texts=texts, colors=colors, font_sizes=font_sizes)
            return _frame(texts=texts, colors=colors, bg_color="#0a0a2e", font_sizes=font_sizes)

        # 1) Statements presentation frame
        statement_texts = []
        statement_colors = []
        statement_font_sizes = []
        for idx, stmt in enumerate(statements):
            statement_texts.append(f"{idx + 1}. {stmt}")
            statement_colors.append("#FFFFFF")
            statement_font_sizes.append(44)

        statements_frame = make_frame(
            ["True or False? Animal Facts", ""] + statement_texts,
            ["#FFFF00", "#FFFFFF"] + statement_colors,
            [52, 20] + statement_font_sizes,
        )

        # 2) Thinking / countdown frame
        thinking_frame = make_frame(
            ["Which one is the LIE?", "..."],
            ["#FFFF00", "#AAAAAA"],
            [48, 60],
        )

        # 3) Lie reveal frame
        reveal_texts = []
        reveal_colors = []
        reveal_font_sizes = []
        for idx, stmt in enumerate(statements):
            label = f"{idx + 1}. {stmt}"
            if idx == lie_index:
                label = f"{idx + 1}. [LIE] {stmt}"
                reveal_colors.append("#FF4444")
            else:
                reveal_colors.append("#00FF88")
            reveal_texts.append(label)
            reveal_font_sizes.append(44)

        reveal_frame = make_frame(
            ["The Lie Is...", ""] + reveal_texts + ["", explanation],
            ["#FFFF00", "#FFFFFF"] + reveal_colors + ["#FFFFFF", "#CCCCCC"],
            [52, 20] + reveal_font_sizes + [20, 36],
        )

        # Timing allocation
        statements_dur = 5.0
        thinking_dur = 3.0
        fixed_total = statements_dur + thinking_dur
        if fixed_total > total_duration:
            ratio = total_duration / fixed_total
            statements_dur *= ratio
            thinking_dur *= ratio
        reveal_dur = total_duration - statements_dur - thinking_dur

        clips = [
            ImageClip(statements_frame).with_duration(statements_dur).with_fps(30),
            ImageClip(thinking_frame).with_duration(thinking_dur).with_fps(30),
            ImageClip(reveal_frame).with_duration(reveal_dur).with_fps(30),
        ]

        # CTA frame (3 seconds)
        cta_frame = self.generate_cta_frame(bg_img)
        clips.append(ImageClip(cta_frame).with_duration(3.0).with_fps(30))

        video = concatenate_videoclips(clips)

        return self._finalize_video(video, tts_path, combined_path)
