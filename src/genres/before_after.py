import os

from typing import List, Optional
from uuid import uuid4

from genres import register_genre
from genres.base import BaseGenre
from config import ROOT_DIR, get_verbose, get_threads, equalize_subtitles
from status import success, warning
from moviepy import (
    AudioFileClip,
    ImageClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
from moviepy.video.fx.CrossFadeIn import CrossFadeIn


@register_genre
class BeforeAfterGenre(BaseGenre):
    name = "before_after"
    display_name = "Before / After"
    default_effect = "fade_transition"
    default_subtitle_style = "classic"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate a "Before and After" comparison video script about the topic: {self.niche}.

Return ONLY valid JSON in this exact format:
{{
  "subject": "The subject of the comparison",
  "before_description": "Description of the before state",
  "after_description": "Description of the after state",
  "before_prompt": "Detailed AI image generation prompt for the before state",
  "after_prompt": "Detailed AI image generation prompt for the after state",
  "script": "Full narration script comparing before and after states",
  "image_prompts": ["before image prompt", "after image prompt"]
}}

The script must be narrated in {self.language}.
Make image prompts detailed and vivid for AI image generation.
The before and after should show a dramatic transformation.
"""
        content = self.generate_response_json(prompt)
        success(f"Generated before/after content: {content.get('subject', '')}")
        return content

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")
        threads = get_threads()

        tts_clip = AudioFileClip(tts_path)
        max_duration = tts_clip.duration
        half_duration = max_duration / 2
        transition_duration = 0.5

        video_size = (1080, 1920)

        # BEFORE 클립
        if images and len(images) >= 1:
            before_clip = (
                ImageClip(images[0])
                .with_duration(half_duration)
                .with_fps(30)
                .resized(new_size=video_size)
            )
        else:
            before_frame = self.generate_text_frame(
                texts=["BEFORE", content.get("before_description", "")[:40]],
                colors=["#FF6B6B", "#FFFFFF"],
                bg_color="#1a0a0a",
                font_sizes=[80, 40],
            )
            before_clip = ImageClip(before_frame).with_duration(half_duration).with_fps(30)

        before_label = (
            TextClip(
                text="BEFORE",
                font_size=64,
                color="#FF6B6B",
                font="Arial-Bold",
                stroke_color="#000000",
                stroke_width=3,
            )
            .with_duration(half_duration)
            .with_fps(30)
            .with_position(("center", 100))
        )

        before_comp = CompositeVideoClip(
            [before_clip, before_label], size=video_size
        ).with_duration(half_duration)

        # AFTER 클립
        if images and len(images) >= 2:
            after_clip = (
                ImageClip(images[1])
                .with_duration(half_duration)
                .with_fps(30)
                .resized(new_size=video_size)
            )
        else:
            after_frame = self.generate_text_frame(
                texts=["AFTER", content.get("after_description", "")[:40]],
                colors=["#4ECDC4", "#FFFFFF"],
                bg_color="#0a1a1a",
                font_sizes=[80, 40],
            )
            after_clip = ImageClip(after_frame).with_duration(half_duration).with_fps(30)

        after_label = (
            TextClip(
                text="AFTER",
                font_size=64,
                color="#4ECDC4",
                font="Arial-Bold",
                stroke_color="#000000",
                stroke_width=3,
            )
            .with_duration(half_duration)
            .with_fps(30)
            .with_position(("center", 100))
        )

        after_comp = CompositeVideoClip(
            [after_clip, after_label], size=video_size
        ).with_duration(half_duration)

        # CrossFadeIn 전환 효과 적용
        after_comp = after_comp.with_effects([CrossFadeIn(transition_duration)])

        # BEFORE → 전환 → AFTER
        after_comp = after_comp.with_start(half_duration - transition_duration)
        video_clip = CompositeVideoClip(
            [before_comp, after_comp], size=video_size
        ).with_duration(max_duration).with_fps(30)

        # 자막
        subtitle_style = self._get_subtitle_style()
        subtitles = None
        try:
            srt_path = self.generate_subtitles(tts_path)
            equalize_subtitles(srt_path, 10)
            subtitles = subtitle_style.render_subtitles(srt_path, video_size)
        except Exception as e:
            warning(f"Failed to generate subtitles, continuing without: {e}")

        comp_audio = self.mix_audio(tts_path)
        video_clip = video_clip.with_audio(comp_audio)

        if subtitles is not None:
            video_clip = CompositeVideoClip([video_clip, subtitles])

        video_clip.write_videofile(combined_path, threads=threads)
        success(f'Wrote Video to "{combined_path}"')

        return combined_path
