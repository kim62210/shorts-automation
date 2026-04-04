from abc import ABC, abstractmethod
from moviepy import TextClip, VideoClip

# YouTube Shorts safe zone (1080x1920)
SAFE_LEFT = 60
SAFE_RIGHT = 190
SAFE_TOP = 270
SAFE_BOTTOM = 400
# 자막용 세이프 가로폭: 1080 - 60 - 190 = 830
SUBTITLE_SAFE_WIDTH = 1080 - SAFE_LEFT - SAFE_RIGHT
# 자막 Y 위치: 세이프존 하단 근처 (상대값 0.66 = 약 1267px, 세이프존 내)
SUBTITLE_Y_RELATIVE = 0.66


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
        return clip.with_position(("center", SUBTITLE_Y_RELATIVE), relative=True)
