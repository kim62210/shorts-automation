import os

from moviepy import TextClip

from config import get_font, get_fonts_dir
from subtitles import register_style
from subtitles.base import BaseSubtitleStyle


@register_style
class ClassicStyle(BaseSubtitleStyle):
    name = "classic"
    display_name = "Classic"

    def make_textclip(self, text: str, video_size: tuple) -> TextClip:
        from subtitles.base import SUBTITLE_SAFE_WIDTH
        return TextClip(
            text=text,
            font=os.path.join(get_fonts_dir(), get_font()),
            font_size=80,
            color="#FFFF00",
            stroke_color="black",
            stroke_width=5,
            size=(SUBTITLE_SAFE_WIDTH, None),
            method="caption",
        )
