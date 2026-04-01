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
    display_name = "텍스트 스토리"
    default_subtitle_style = "minimal_bottom"
    needs_images = False

    def generate_content(self) -> dict:
        prompt = f"""Generate a short, gripping story related to the topic: {self.niche}.
The story should be in the style of a Reddit nosleep or creepy story post.
Return your answer as JSON with exactly this structure:
{{
  "title": "Story title",
  "paragraphs": ["First paragraph...", "Second paragraph...", "Third paragraph..."],
  "script": "The complete story text as one continuous narration"
}}

Requirements:
- Write 3-5 short paragraphs that build tension and have a satisfying conclusion
- Write everything in {self.language}
- The title should be catchy and intriguing
- The script field contains all paragraphs joined as continuous narration text
- Each paragraph should be short enough to fit on a mobile screen (2-4 sentences)
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

        # 제목 프레임 (Reddit 스타일 헤더)
        title_frame = self.generate_text_frame(
            texts=["r/nosleep", "", title],
            colors=["#FF4500", "#FFFFFF", "#FFFFFF"],
            bg_color="#1a1a2e",
            font_sizes=[36, 20, 52],
        )

        # 각 문단 프레임
        paragraph_frames = []
        for para in paragraphs:
            frame = self.generate_text_frame(
                texts=[para],
                colors=["#E0E0E0"],
                bg_color="#1a1a2e",
                font_sizes=[40],
            )
            paragraph_frames.append(frame)

        # 타이밍 배분
        total_frames = 1 + len(paragraph_frames)
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

        video = concatenate_videoclips(clips)

        return self._finalize_video(video, tts_path, combined_path)
