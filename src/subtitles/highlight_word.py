import os
from typing import TypedDict

from moviepy import CompositeVideoClip, TextClip, VideoClip

from config import get_font, get_fonts_dir
from subtitles import register_style
from subtitles.base import BaseSubtitleStyle


class WordData(TypedDict):
    word: str
    start: float
    end: float


@register_style
class HighlightWordStyle(BaseSubtitleStyle):
    name = "highlight_word"
    display_name = "Highlight Word"

    def make_textclip(self, text: str, video_size: tuple) -> TextClip:
        """SRT 기반 폴백 -- bold_center와 동일하게 동작"""
        from subtitles.base import SUBTITLE_SAFE_WIDTH
        font_path = os.path.join(get_fonts_dir(), get_font())
        return TextClip(
            text=text,
            font=font_path,
            font_size=100,
            color="#FFFFFF",
            stroke_color="black",
            stroke_width=7,
            size=(SUBTITLE_SAFE_WIDTH, None),
            method="caption",
        )

    def render_word_level(
        self,
        words_data: list[WordData],
        video_size: tuple,
        duration: float,
    ) -> VideoClip:
        """단어별 하이라이트 렌더링 (세이프존 내 배치)"""
        from subtitles.base import SUBTITLE_SAFE_WIDTH, SUBTITLE_Y_RELATIVE
        font_path = os.path.join(get_fonts_dir(), get_font())
        all_words = [w["word"] for w in words_data]
        full_text = " ".join(all_words)
        clip_size = (SUBTITLE_SAFE_WIDTH, None)

        clips: list[VideoClip] = []
        for i, current in enumerate(words_data):
            base_clip = TextClip(
                text=full_text,
                font=font_path,
                font_size=80,
                color="#FFFFFF",
                stroke_color="black",
                stroke_width=5,
                size=clip_size,
                method="caption",
            )
            base_clip = (
                base_clip.with_start(current["start"])
                .with_end(current["end"])
                .with_position(("center", SUBTITLE_Y_RELATIVE), relative=True)
            )
            clips.append(base_clip)

            highlight_text = " ".join(
                w.upper() if j == i else w for j, w in enumerate(all_words)
            )
            hl_clip = TextClip(
                text=highlight_text,
                font=font_path,
                font_size=80,
                color="#FFFF00",
                stroke_color="black",
                stroke_width=5,
                size=clip_size,
                method="caption",
            )
            hl_clip = (
                hl_clip.with_start(current["start"])
                .with_end(current["end"])
                .with_position(("center", SUBTITLE_Y_RELATIVE), relative=True)
            )
            clips.append(hl_clip)

        return CompositeVideoClip(clips, size=video_size).with_duration(duration)
