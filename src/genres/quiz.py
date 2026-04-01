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
    display_name = "퀴즈 / 트리비아"
    default_subtitle_style = "bold_center"
    needs_images = False

    def generate_content(self) -> dict:
        prompt = f"""Generate a fun trivia quiz question about the topic: {self.niche}.
Return your answer as JSON with exactly this structure:
{{
  "question": "The trivia question",
  "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
  "answer_index": 1,
  "explanation": "Why this is the correct answer",
  "script": "Full narration script that reads the question, pauses for thinking, reveals the answer, and explains why. Format: The question is... The options are... Think about it... The correct answer is... Because..."
}}

Requirements:
- The question should be interesting and engaging for a {self.niche} audience
- Write everything in {self.language}
- The script field must contain the complete narration covering question, options, answer reveal, and explanation
- answer_index is 0-based (0=A, 1=B, 2=C, 3=D)
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

        # 1) 질문 + 선택지 프레임
        question_texts = [question, ""] + options
        question_colors = ["#FFD700"] + ["#FFFFFF"] * (len(options) + 1)
        question_font_sizes = [52] + [40] * (len(options) + 1)
        question_frame = self.generate_text_frame(
            texts=question_texts,
            colors=question_colors,
            bg_color="#0a0a2e",
            font_sizes=question_font_sizes,
        )

        # 2) 카운트다운 프레임 (3, 2, 1)
        countdown_frames = []
        for n in [3, 2, 1]:
            frame = self.generate_text_frame(
                texts=["Think...", str(n)],
                colors=["#AAAAAA", "#FFD700"],
                bg_color="#0a0a2e",
                font_sizes=[48, 120],
            )
            countdown_frames.append(frame)

        # 3) 정답 공개 프레임
        answer_texts = []
        answer_colors = []
        for idx, opt in enumerate(options):
            answer_texts.append(opt)
            if idx == answer_index:
                answer_colors.append("#00FF88")
            else:
                answer_colors.append("#555555")
        answer_frame = self.generate_text_frame(
            texts=["Answer:"] + answer_texts,
            colors=["#FFD700"] + answer_colors,
            bg_color="#0a0a2e",
            font_sizes=[52] + [48] * len(options),
        )

        # 4) 해설 프레임
        explanation_frame = self.generate_text_frame(
            texts=["Why?", "", explanation],
            colors=["#FFD700", "#FFFFFF", "#CCCCCC"],
            bg_color="#0a0a2e",
            font_sizes=[52, 40, 40],
        )

        # 프레임 타이밍 배분
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

        video = concatenate_videoclips(clips)

        return self._finalize_video(video, tts_path, combined_path)
