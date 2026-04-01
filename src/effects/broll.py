from pathlib import Path
from typing import List

from moviepy import ImageClip, VideoClip, VideoFileClip, concatenate_videoclips
from moviepy.video.fx.Crop import Crop

from effects import register_effect
from effects.base import BaseEffect
from config import get_verbose
from status import info

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


@register_effect
class BRollEffect(BaseEffect):
    name = "broll"
    display_name = "B-Roll"

    def _crop_and_resize(self, clip: VideoClip, video_size: tuple) -> VideoClip:
        """9:16 등 목표 종횡비에 맞게 크롭 후 리사이즈"""
        aspect_ratio = video_size[0] / video_size[1]

        if round((clip.w / clip.h), 4) < aspect_ratio:
            clip = clip.with_effects(
                [
                    Crop(
                        width=clip.w,
                        height=round(clip.w / aspect_ratio),
                        x_center=clip.w / 2,
                        y_center=clip.h / 2,
                    )
                ]
            )
        else:
            clip = clip.with_effects(
                [
                    Crop(
                        width=round(aspect_ratio * clip.h),
                        height=clip.h,
                        x_center=clip.w / 2,
                        y_center=clip.h / 2,
                    )
                ]
            )

        clip = clip.resized(new_size=video_size)
        return clip

    def _load_clip(self, file_path: str, clip_duration: float,
                   video_size: tuple) -> VideoClip:
        """파일 확장자에 따라 ImageClip 또는 VideoFileClip으로 로드"""
        ext = Path(file_path).suffix.lower()

        if ext in VIDEO_EXTENSIONS:
            if get_verbose():
                info(f" => Loading video: {file_path}")
            clip = VideoFileClip(file_path)
            # 원본이 요청 길이보다 길면 자르기
            if clip.duration > clip_duration:
                clip = clip.subclipped(0, clip_duration)
            clip = clip.with_duration(min(clip.duration, clip_duration))
        elif ext in IMAGE_EXTENSIONS:
            if get_verbose():
                info(f" => Loading image: {file_path}")
            clip = ImageClip(file_path)
            clip = clip.with_duration(clip_duration)
        else:
            info(f" => Unknown file type, treating as image: {file_path}")
            clip = ImageClip(file_path)
            clip = clip.with_duration(clip_duration)

        clip = clip.with_fps(30)
        clip = self._crop_and_resize(clip, video_size)

        return clip

    def apply(self, image_paths: List[str], duration: float,
              video_size: tuple = (1080, 1920)) -> VideoClip:
        req_dur = duration / len(image_paths)

        clips = []
        tot_dur = 0.0

        while tot_dur < duration:
            for file_path in image_paths:
                clip = self._load_clip(file_path, req_dur, video_size)
                clips.append(clip)
                tot_dur += clip.duration

                if tot_dur >= duration:
                    break

        final_clip = concatenate_videoclips(clips)
        final_clip = final_clip.with_duration(duration)
        final_clip = final_clip.with_fps(30)

        return final_clip
