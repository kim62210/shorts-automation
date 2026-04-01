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
)


@register_genre
class QuoteGenre(BaseGenre):
    name = "quote"
    display_name = "명언 / 동기부여"
    default_subtitle_style = "minimal_bottom"
    needs_images = False

    def generate_content(self) -> dict:
        prompt = f"""Generate an inspiring and meaningful quote related to the topic: {self.niche}.
Return your answer as JSON with exactly this structure:
{{
  "quote": "The full quote text",
  "author": "Author name",
  "script": "Full narration that reads the quote with feeling and attributes it to the author"
}}

Requirements:
- The quote should be powerful, thought-provoking, and relevant to {self.niche}
- Write everything in {self.language}
- The script should read the quote naturally, then mention the author
- Return ONLY valid JSON, no markdown"""

        return self.generate_response_json(prompt)

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")
        threads = get_threads()

        tts_clip = AudioFileClip(tts_path)
        total_duration = tts_clip.duration

        quote = content.get("quote", "")
        author = content.get("author", "")

        # 감성 배경 + 명언 텍스트 프레임
        frame = self.generate_text_frame(
            texts=['"', "", quote, "", f"- {author}"],
            colors=["#FFD700", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#AAAAAA"],
            bg_color="#0f0a2e",
            font_sizes=[80, 20, 44, 20, 36],
        )

        video = ImageClip(frame).with_duration(total_duration).with_fps(30)

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
