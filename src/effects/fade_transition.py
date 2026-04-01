from typing import List

from moviepy import ImageClip, VideoClip, CompositeVideoClip
from moviepy.video.fx.Crop import Crop
from moviepy.video.fx.CrossFadeIn import CrossFadeIn
from moviepy.video.fx.CrossFadeOut import CrossFadeOut

from effects import register_effect
from effects.base import BaseEffect
from config import get_verbose
from status import info


@register_effect
class FadeTransitionEffect(BaseEffect):
    name = "fade_transition"
    display_name = "Fade Transition"

    FADE_DURATION = 0.5

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

    def apply(self, image_paths: List[str], duration: float,
              video_size: tuple = (1080, 1920)) -> VideoClip:
        overlap = self.FADE_DURATION
        n_images = len(image_paths)

        # 클립 간 오버랩을 감안한 개별 클립 재생 시간 계산
        # 전체: n * clip_dur - (n-1) * overlap = duration
        clip_dur = (duration + (n_images - 1) * overlap) / n_images
        clip_dur = max(clip_dur, overlap * 2)

        raw_clips = []
        tot_dur = 0.0
        idx = 0

        while tot_dur < duration:
            for image_path in image_paths:
                if get_verbose():
                    info(f" => Fade Transition: {image_path}")

                clip = ImageClip(image_path)
                clip = clip.with_duration(clip_dur)
                clip = clip.with_fps(30)
                clip = self._crop_and_resize(clip, video_size)

                raw_clips.append(clip)
                tot_dur += clip_dur - overlap
                idx += 1

                if tot_dur >= duration:
                    break

        # 각 클립에 CrossFadeIn/CrossFadeOut 적용 및 시간 오프셋 배치
        positioned_clips = []
        for i, clip in enumerate(raw_clips):
            effects_list = []
            if i > 0:
                effects_list.append(CrossFadeIn(overlap))
            if i < len(raw_clips) - 1:
                effects_list.append(CrossFadeOut(overlap))

            if effects_list:
                clip = clip.with_effects(effects_list)

            start_time = i * (clip_dur - overlap)
            clip = clip.with_start(start_time)
            positioned_clips.append(clip)

        final_clip = CompositeVideoClip(positioned_clips, size=video_size)
        final_clip = final_clip.with_duration(duration)
        final_clip = final_clip.with_fps(30)

        return final_clip
