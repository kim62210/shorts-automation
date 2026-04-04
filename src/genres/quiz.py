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
class QuizGenre(BaseGenre):
    name = "quiz"
    display_name = "Animal Trivia Quiz"
    default_subtitle_style = "bold_center"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate a fun and surprising animal trivia quiz question. The niche is: {self.niche}, but the question MUST be about animals.
The question should be about fascinating, surprising, or little-known animal facts that make people go "wow!"
Examples of good topics: animal superpowers, weird animal behaviors, animal body facts, animal records, etc.

Return your answer as JSON with exactly this structure:
{{
  "question": "The animal trivia question",
  "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
  "answer_index": 1,
  "explanation": "Why this is the correct answer - include a fun animal fact",
  "script": "Full narration script that reads the question, pauses for thinking, reveals the answer, and explains why with an interesting animal fact.",
  "image_prompts": ["A cute, vivid image of the animal featured in the quiz. Photorealistic style, 9:16 portrait orientation, warm lighting, adorable pose."]
}}

Requirements:
- The question MUST be about animals - surprising or fun animal facts
- Write everything in {self.language}
- The script field must contain the complete narration covering question, options, answer reveal, and explanation
- answer_index is 0-based (0=A, 1=B, 2=C, 3=D)
- image_prompts: exactly 1 prompt for a cute animal background image related to the quiz topic
- Return ONLY valid JSON, no markdown"""

        return self.generate_response_json(prompt)

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")

        tts_clip = AudioFileClip(tts_path)
        total_duration = tts_clip.duration

        question = content.get("question", "")
        options = content.get("options", [])
        answer_index = content.get("answer_index", 0)
        explanation = content.get("explanation", "")

        bg_img = images[0] if images else None
        _frame = self.generate_text_on_image_frame if bg_img else self.generate_text_frame

        def make_frame(texts, colors, font_sizes):
            if bg_img:
                return _frame(bg_img, texts=texts, colors=colors, font_sizes=font_sizes)
            return _frame(texts=texts, colors=colors, bg_color="#0a0a2e", font_sizes=font_sizes)

        # 1) Question + options frame
        question_texts = [question, ""] + options
        question_colors = ["#FFFF00"] + ["#FFFFFF"] * (len(options) + 1)
        question_font_sizes = [52] + [40] * (len(options) + 1)
        question_frame = make_frame(question_texts, question_colors, question_font_sizes)

        # 2) Countdown frames (3, 2, 1)
        countdown_frames = []
        for n in [3, 2, 1]:
            frame = make_frame(["Think...", str(n)], ["#AAAAAA", "#FFFF00"], [48, 120])
            countdown_frames.append(frame)

        # 3) Answer reveal frame
        answer_texts = []
        answer_colors = []
        for idx, opt in enumerate(options):
            answer_texts.append(opt)
            if idx == answer_index:
                answer_colors.append("#00FF88")
            else:
                answer_colors.append("#555555")
        answer_frame = make_frame(
            ["Answer:"] + answer_texts,
            ["#FFFF00"] + answer_colors,
            [52] + [48] * len(options),
        )

        # 4) Explanation frame
        explanation_frame = make_frame(
            ["Why?", "", explanation],
            ["#FFFF00", "#FFFFFF", "#CCCCCC"],
            [52, 40, 40],
        )

        # Frame timing distribution
        countdown_total = 3.0
        remaining = total_duration - countdown_total
        question_dur = remaining * 0.35
        answer_dur = remaining * 0.30
        explanation_dur = remaining * 0.35

        clips = []
        clips.append(
            ImageClip(question_frame).with_duration(question_dur).with_fps(30)
        )
        for cd_frame in countdown_frames:
            clips.append(
                ImageClip(cd_frame).with_duration(1.0).with_fps(30)
            )
        clips.append(
            ImageClip(answer_frame).with_duration(answer_dur).with_fps(30)
        )
        clips.append(
            ImageClip(explanation_frame).with_duration(explanation_dur).with_fps(30)
        )

        # CTA frame (3 seconds)
        cta_frame = self.generate_cta_frame(bg_img)
        clips.append(ImageClip(cta_frame).with_duration(3.0).with_fps(30))

        video = concatenate_videoclips(clips)

        return self._finalize_video(video, tts_path, combined_path)
