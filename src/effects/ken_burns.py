from typing import List

from moviepy import ImageClip, VideoClip, concatenate_videoclips
from moviepy.video.fx.Crop import Crop

from effects import register_effect
from effects.base import BaseEffect
from config import get_verbose
from status import info


@register_effect
class KenBurnsEffect(BaseEffect):
    name = "ken_burns"
    display_name = "Ken Burns"

    ZOOM_FACTOR = 1.2

    def _crop_to_aspect(self, clip: VideoClip, aspect_ratio: float) -> VideoClip:
        """9:16 등 목표 종횡비에 맞게 중앙 크롭"""
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
        return clip

    def _make_ken_burns_clip(self, image_path: str, clip_duration: float,
                             video_size: tuple, zoom_in: bool) -> VideoClip:
        """단일 이미지에 줌인/줌아웃 효과를 적용하여 클립 생성"""
        target_w, target_h = video_size
        aspect_ratio = target_w / target_h
        scaled_w = int(target_w * self.ZOOM_FACTOR)
        scaled_h = int(target_h * self.ZOOM_FACTOR)

        clip = ImageClip(image_path)
        clip = self._crop_to_aspect(clip, aspect_ratio)
        clip = clip.resized(new_size=(scaled_w, scaled_h))
        clip = clip.with_duration(clip_duration)
        clip = clip.with_fps(30)

        if zoom_in:
            start_w, start_h = scaled_w, scaled_h
            end_w, end_h = target_w, target_h
        else:
            start_w, start_h = target_w, target_h
            end_w, end_h = scaled_w, scaled_h

        def make_frame_crop(get_frame, t):
            progress = t / clip_duration if clip_duration > 0 else 0
            crop_w = int(start_w + (end_w - start_w) * progress)
            crop_h = int(start_h + (end_h - start_h) * progress)
            crop_w = max(target_w, min(scaled_w, crop_w))
            crop_h = max(target_h, min(scaled_h, crop_h))

            x_offset = (scaled_w - crop_w) // 2
            y_offset = (scaled_h - crop_h) // 2

            frame = get_frame(t)
            cropped = frame[y_offset:y_offset + crop_h, x_offset:x_offset + crop_w]
            return cropped

        original_get_frame = clip.get_frame
        ken_clip = clip.transform(lambda get_frame, t: make_frame_crop(get_frame, t))
        ken_clip = ken_clip.resized(new_size=video_size)

        return ken_clip

    def apply(self, image_paths: List[str], duration: float,
              video_size: tuple = (1080, 1920)) -> VideoClip:
        req_dur = duration / len(image_paths)

        clips = []
        tot_dur = 0.0
        idx = 0

        while tot_dur < duration:
            for image_path in image_paths:
                zoom_in = (idx % 2 == 0)

                if get_verbose():
                    direction = "zoom-in" if zoom_in else "zoom-out"
                    info(f" => Ken Burns ({direction}): {image_path}")

                clip = self._make_ken_burns_clip(
                    image_path, req_dur, video_size, zoom_in
                )
                clips.append(clip)
                tot_dur += clip.duration
                idx += 1

                if tot_dur >= duration:
                    break

        final_clip = concatenate_videoclips(clips)
        final_clip = final_clip.with_duration(duration)
        final_clip = final_clip.with_fps(30)

        return final_clip
