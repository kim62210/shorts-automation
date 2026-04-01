from abc import ABC, abstractmethod
from moviepy import TextClip, VideoClip


class BaseSubtitleStyle(ABC):
    name: str
    display_name: str

    @abstractmethod
    def make_textclip(self, text: str, video_size: tuple) -> TextClip:
        raise NotImplementedError

    def render_subtitles(self, srt_path: str, video_size: tuple) -> VideoClip:
        from moviepy.video.tools.subtitles import SubtitlesClip

        generator = lambda txt: self.make_textclip(txt, video_size)
        clip = SubtitlesClip(srt_path, make_textclip=generator)
        return clip.with_position(("center", "center"))
