from typing import List

from moviepy import ImageClip, VideoClip, concatenate_videoclips
from moviepy.video.fx.Crop import Crop

from effects import register_effect
from effects.base import BaseEffect
from config import get_verbose
from status import info


@register_effect
class SlideshowEffect(BaseEffect):
    name = "slideshow"
    display_name = "Slideshow"

    def apply(self, image_paths: List[str], duration: float,
              video_size: tuple = (1080, 1920)) -> VideoClip:
        req_dur = duration / len(image_paths)
        aspect_ratio = video_size[0] / video_size[1]

        clips = []
        tot_dur = 0.0

        while tot_dur < duration:
            for image_path in image_paths:
                clip = ImageClip(image_path)
                clip = clip.with_duration(req_dur)
                clip = clip.with_fps(30)

                if round((clip.w / clip.h), 4) < aspect_ratio:
                    if get_verbose():
                        info(f" => Resizing Image: {image_path} to {video_size[0]}x{video_size[1]}")
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
                    if get_verbose():
                        info(f" => Resizing Image: {image_path} to {video_size[1]}x{video_size[0]}")
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
                clips.append(clip)
                tot_dur += clip.duration

                if tot_dur >= duration:
                    break

        final_clip = concatenate_videoclips(clips)
        final_clip = final_clip.with_duration(duration)
        final_clip = final_clip.with_fps(30)

        return final_clip
