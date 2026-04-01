import os

from typing import List, Optional
from uuid import uuid4

from genres import register_genre
from genres.base import BaseGenre
from config import ROOT_DIR, get_verbose, get_threads, equalize_subtitles
from status import success, warning
from moviepy import (
    AudioFileClip,
    ImageClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
)


@register_genre
class WaitForItGenre(BaseGenre):
    name = "wait_for_it"
    display_name = "Wait For It (반전 공개)"
    default_effect = "fade_transition"
    default_subtitle_style = "bold_center"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate a "Wait For It" reveal-style video script about the topic: {self.niche}.

Return ONLY valid JSON in this exact format:
{{
  "hint_text": "A teasing hint about what will be revealed",
  "reveal_text": "The surprising reveal or answer",
  "hint_prompt": "Detailed AI image generation prompt for the hint/mystery phase",
  "reveal_prompt": "Detailed AI image generation prompt for the reveal moment",
  "script": "Full narration script that builds suspense then reveals the answer",
  "image_prompts": ["hint image prompt", "reveal image prompt"]
}}

The script must be narrated in {self.language}.
Build genuine suspense in the hint phase.
The reveal should be surprising and satisfying.
Make image prompts detailed and vivid for AI image generation.
"""
        content = self.generate_response_json(prompt)
        success("Generated 'wait for it' content.")
        return content

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")
        threads = get_threads()

        tts_clip = AudioFileClip(tts_path)
        max_duration = tts_clip.duration

        video_size = (1080, 1920)
        countdown_duration = 3.0

        # 시간 배분: 힌트(60%) - 카운트다운(3초) - 정답(나머지)
        hint_duration = (max_duration - countdown_duration) * 0.6
        reveal_duration = max_duration - hint_duration - countdown_duration

        # 힌트 이미지 + "WAIT FOR IT..." 오버레이 (전반 60%)
        if images and len(images) >= 1:
            hint_clip = (
                ImageClip(images[0])
                .with_duration(hint_duration)
                .with_fps(30)
                .resized(new_size=video_size)
            )
        else:
            hint_frame = self.generate_text_frame(
                texts=[content.get("hint_text", "...")[:60]],
                colors=["#FFFFFF"],
                bg_color="#0a0a1a",
                font_sizes=[48],
            )
            hint_clip = ImageClip(hint_frame).with_duration(hint_duration).with_fps(30)

        wait_label = (
            TextClip(
                text="WAIT FOR IT...",
                font_size=56,
                color="#FFD700",
                font="Arial-Bold",
                stroke_color="#000000",
                stroke_width=3,
            )
            .with_duration(hint_duration)
            .with_fps(30)
            .with_position(("center", 150))
        )

        hint_comp = CompositeVideoClip(
            [hint_clip, wait_label], size=video_size
        ).with_duration(hint_duration)

        # 카운트다운 프레임 3 → 2 → 1
        countdown_clips = []
        for num in [3, 2, 1]:
            cd_frame = self.generate_text_frame(
                texts=[str(num)],
                colors=["#FF4444"],
                bg_color="#000000",
                font_sizes=[200],
            )
            cd_clip = ImageClip(cd_frame).with_duration(1.0).with_fps(30)
            countdown_clips.append(cd_clip)

        countdown_comp = concatenate_videoclips(countdown_clips)

        # 정답 이미지 (나머지 시간)
        if images and len(images) >= 2:
            reveal_clip = (
                ImageClip(images[1])
                .with_duration(reveal_duration)
                .with_fps(30)
                .resized(new_size=video_size)
            )
        else:
            reveal_frame = self.generate_text_frame(
                texts=[content.get("reveal_text", "Reveal!")[:60]],
                colors=["#4ECDC4"],
                bg_color="#0a0a1a",
                font_sizes=[56],
            )
            reveal_clip = ImageClip(reveal_frame).with_duration(reveal_duration).with_fps(30)

        # 합성
        all_clips = [hint_comp, countdown_comp, reveal_clip]
        video_clip = concatenate_videoclips(all_clips)
        video_clip = video_clip.with_duration(max_duration).with_fps(30)

        # 자막
        subtitle_style = self._get_subtitle_style()
        subtitles = None
        try:
            srt_path = self.generate_subtitles(tts_path)
            equalize_subtitles(srt_path, 10)
            subtitles = subtitle_style.render_subtitles(srt_path, video_size)
        except Exception as e:
            warning(f"Failed to generate subtitles, continuing without: {e}")

        comp_audio = self.mix_audio(tts_path)
        video_clip = video_clip.with_audio(comp_audio)

        if subtitles is not None:
            video_clip = CompositeVideoClip([video_clip, subtitles])

        video_clip.write_videofile(combined_path, threads=threads)
        success(f'Wrote Video to "{combined_path}"')

        return combined_path
