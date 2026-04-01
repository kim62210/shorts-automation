import os

from moviepy import TextClip

from config import get_font, get_fonts_dir
from subtitles import register_style
from subtitles.base import BaseSubtitleStyle


@register_style
class BoldCenterStyle(BaseSubtitleStyle):
    name = "bold_center"
    display_name = "Bold Center"

    def make_textclip(self, text: str, video_size: tuple) -> TextClip:
        font_path = os.path.join(get_fonts_dir(), get_font())
        return TextClip(
            text=text,
            font=font_path,
            font_size=120,
            color="#FFFFFF",
            stroke_color="black",
            stroke_width=8,
            size=video_size,
            method="caption",
        )
