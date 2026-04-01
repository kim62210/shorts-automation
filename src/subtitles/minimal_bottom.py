import os

from moviepy import TextClip, VideoClip

from config import get_font, get_fonts_dir
from subtitles import register_style
from subtitles.base import BaseSubtitleStyle


@register_style
class MinimalBottomStyle(BaseSubtitleStyle):
    name = "minimal_bottom"
    display_name = "Minimal Bottom"

    def make_textclip(self, text: str, video_size: tuple) -> TextClip:
        return TextClip(
            text=text,
            font=os.path.join(get_fonts_dir(), get_font()),
            font_size=55,
            color="#FFFFFF",
            size=(video_size[0], None),
            method="caption",
        )

    def render_subtitles(self, srt_path: str, video_size: tuple) -> VideoClip:
        from moviepy.video.tools.subtitles import SubtitlesClip

        generator = lambda txt: self.make_textclip(txt, video_size)
        clip = SubtitlesClip(srt_path, make_textclip=generator)
        return clip.with_position(("center", 0.88), relative=True)
