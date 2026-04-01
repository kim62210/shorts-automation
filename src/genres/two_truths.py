import os

from typing import List, Optional
from uuid import uuid4

from genres import register_genre
from genres.base import BaseGenre
from config import ROOT_DIR, get_threads, get_verbose, equalize_subtitles
from status import warning
from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
)


@register_genre
class TwoTruthsGenre(BaseGenre):
    name = "two_truths"
    display_name = "두 개의 진실, 하나의 거짓"
    default_subtitle_style = "bold_center"
    needs_images = False

    def generate_content(self) -> dict:
        prompt = f"""Generate a "Two Truths and a Lie" challenge about the topic: {self.niche}.
Return your answer as JSON with exactly this structure:
{{
  "statements": ["Statement 1 (true or false)", "Statement 2 (true or false)", "Statement 3 (true or false)"],
  "lie_index": 1,
  "explanation": "Why the lie is false and what the truth actually is",
  "script": "Full narration: present the three statements, ask which is the lie, reveal the answer, and explain"
}}

Requirements:
- Two statements must be true and one must be a believable lie
- Write everything in {self.language}
- lie_index is 0-based (0, 1, or 2)
- The statements should be surprising and interesting facts
- The lie should be plausible enough to fool people
- Return ONLY valid JSON, no markdown"""

        return self.generate_response_json(prompt)

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")
        threads = get_threads()

        tts_clip = AudioFileClip(tts_path)
        total_duration = tts_clip.duration

        statements = content.get("statements", [])
        lie_index = content.get("lie_index", 0)
        explanation = content.get("explanation", "")

        # 1) 3개 문장 제시 프레임 (모두 흰색)
        statement_texts = []
        statement_colors = []
        statement_font_sizes = []
        for idx, stmt in enumerate(statements):
            statement_texts.append(f"{idx + 1}. {stmt}")
            statement_colors.append("#FFFFFF")
            statement_font_sizes.append(44)

        statements_frame = self.generate_text_frame(
            texts=["Two Truths, One Lie", ""] + statement_texts,
            colors=["#FFD700", "#FFFFFF"] + statement_colors,
            bg_color="#0a0a2e",
            font_sizes=[52, 20] + statement_font_sizes,
        )

        # 2) 카운트다운 프레임
        thinking_frame = self.generate_text_frame(
            texts=["Which one is the LIE?", "..."],
            colors=["#FFD700", "#AAAAAA"],
            bg_color="#0a0a2e",
            font_sizes=[48, 60],
        )

        # 3) 거짓 공개 프레임 (거짓 문장만 빨간색)
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

        reveal_frame = self.generate_text_frame(
            texts=["The Lie Is...", ""] + reveal_texts + ["", explanation],
            colors=["#FFD700", "#FFFFFF"] + reveal_colors + ["#FFFFFF", "#CCCCCC"],
            bg_color="#0a0a2e",
            font_sizes=[52, 20] + reveal_font_sizes + [20, 36],
        )

        # 타이밍 배분
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

        video = concatenate_videoclips(clips)

        # 자막
        subtitle_style = self._get_subtitle_style()
        subtitles = None
        try:
            srt_path = self.generate_subtitles(tts_path)
            equalize_subtitles(srt_path, 10)
            subtitles = subtitle_style.render_subtitles(srt_path, (1080, 1920))
        except Exception as e:
            warning(f"Failed to generate subtitles, continuing without: {e}")

        # 오디오 합성
        comp_audio = self.mix_audio(tts_path)
        video = video.with_audio(comp_audio)
        video = video.with_duration(total_duration)

        if subtitles is not None:
            video = CompositeVideoClip([video, subtitles])

        video.write_videofile(combined_path, threads=threads)
        return combined_path
