import os

from moviepy import TextClip, VideoClip

from config import get_font, get_fonts_dir
from subtitles import register_style
from subtitles.base import BaseSubtitleStyle


@register_style
class ModernBoxStyle(BaseSubtitleStyle):
    name = "modern_box"
    display_name = "Modern Box"

    def make_textclip(self, text: str, video_size: tuple) -> TextClip:
        from subtitles.base import SUBTITLE_SAFE_WIDTH
        return TextClip(
            text=text,
            font=os.path.join(get_fonts_dir(), get_font()),
            font_size=60,
            color="#FFFFFF",
            bg_color="#000000",
            size=(SUBTITLE_SAFE_WIDTH, None),
            method="caption",
        )

    def render_subtitles(self, srt_path: str, video_size: tuple) -> VideoClip:
        from moviepy.video.tools.subtitles import SubtitlesClip
        from subtitles.base import SUBTITLE_Y_RELATIVE

        generator = lambda txt: self.make_textclip(txt, video_size)
        clip = SubtitlesClip(srt_path, make_textclip=generator)
        return clip.with_position(("center", SUBTITLE_Y_RELATIVE), relative=True)
