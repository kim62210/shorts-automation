import os

from typing import List, Optional
from uuid import uuid4

from PIL import Image

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
class SpotDifferenceGenre(BaseGenre):
    name = "spot_difference"
    display_name = "틀린그림찾기"
    default_effect = None
    default_subtitle_style = "bold_center"
    needs_images = True

    def generate_content(self) -> dict:
        prompt = f"""Generate a "Spot the Difference" video script about the topic: {self.niche}.

Return ONLY valid JSON in this exact format:
{{
  "scene": "Description of the scene being compared",
  "differences": ["Difference 1", "Difference 2", "Difference 3"],
  "original_prompt": "Detailed AI image generation prompt for the original scene",
  "modified_prompt": "Detailed AI image generation prompt for the modified scene (with the differences included)",
  "script": "Full narration script that introduces the challenge and reveals the answers",
  "image_prompts": ["original scene prompt", "modified scene prompt"]
}}

The script must be narrated in {self.language}.
Include exactly 3 differences that are subtle but findable.
The modified_prompt should describe the same scene but with the 3 differences reflected.
Make image prompts detailed and vivid for AI image generation.
"""
        content = self.generate_response_json(prompt)
        success(f"Generated spot-the-difference content: {content.get('scene', '')[:60]}")
        return content

    def _create_side_by_side(self, image_a_path: str, image_b_path: str,
                             size: tuple = (1080, 1920)) -> str:
        """두 이미지를 좌우로 배치한 하나의 프레임을 생성"""
        half_w = size[0] // 2
        canvas = Image.new("RGB", size, (10, 10, 26))

        img_a = Image.open(image_a_path).convert("RGB")
        img_a = img_a.resize((half_w, size[1]), Image.Resampling.LANCZOS)
        canvas.paste(img_a, (0, 0))

        img_b = Image.open(image_b_path).convert("RGB")
        img_b = img_b.resize((half_w, size[1]), Image.Resampling.LANCZOS)
        canvas.paste(img_b, (half_w, 0))

        frame_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
        canvas.save(frame_path)
        return frame_path

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")
        threads = get_threads()

        tts_clip = AudioFileClip(tts_path)
        max_duration = tts_clip.duration

        video_size = (1080, 1920)
        differences = content.get("differences", [])

        # 시간 배분: 좌우 배치(5초) + 찾아보세요 카운트다운(5초) + 정답 텍스트(나머지)
        compare_duration = 5.0
        countdown_duration = 5.0
        answer_duration = max(max_duration - compare_duration - countdown_duration, 3.0)

        # 1. 두 이미지 좌우 배치 + 제목
        if images and len(images) >= 2:
            side_by_side_frame = self._create_side_by_side(
                images[0], images[1], size=video_size
            )
        else:
            side_by_side_frame = self.generate_text_frame(
                texts=["LEFT", "RIGHT"],
                colors=["#FF6B6B", "#4ECDC4"],
                bg_color="#0a0a1a",
                font_sizes=[60, 60],
            )

        compare_clip = (
            ImageClip(side_by_side_frame)
            .with_duration(compare_duration)
            .with_fps(30)
        )

        title_label = (
            TextClip(
                text="Spot the Difference!",
                font_size=48,
                color="#FFD700",
                font="Arial-Bold",
                stroke_color="#000000",
                stroke_width=3,
            )
            .with_duration(compare_duration)
            .with_fps(30)
            .with_position(("center", 60))
        )

        # 중앙 구분선
        divider_frame = self.generate_gradient_frame(
            color_top="#FFD700", color_bottom="#FFD700",
            size=(4, video_size[1])
        )
        divider_clip = (
            ImageClip(divider_frame)
            .with_duration(compare_duration)
            .with_fps(30)
            .with_position(("center", 0))
        )

        compare_comp = CompositeVideoClip(
            [compare_clip, title_label, divider_clip], size=video_size
        ).with_duration(compare_duration)

        # 2. "찾아보세요!" 카운트다운 (5초)
        countdown_clips = []
        for sec in range(5, 0, -1):
            cd_frame = self.generate_text_frame(
                texts=["Find them!", str(sec)],
                colors=["#FFFFFF", "#FF4444"],
                bg_color="#0a0a1a",
                font_sizes=[56, 160],
            )
            cd_clip = ImageClip(cd_frame).with_duration(1.0).with_fps(30)
            countdown_clips.append(cd_clip)

        countdown_comp = concatenate_videoclips(countdown_clips)

        # 3. 정답 텍스트 프레임 (차이점 리스트)
        answer_texts = ["ANSWERS:"]
        answer_colors = ["#FFD700"]
        answer_sizes = [56]
        for idx, diff in enumerate(differences):
            answer_texts.append(f"{idx + 1}. {diff[:50]}")
            answer_colors.append("#FFFFFF")
            answer_sizes.append(36)

        answer_frame = self.generate_text_frame(
            texts=answer_texts,
            colors=answer_colors,
            bg_color="#0a0a1a",
            font_sizes=answer_sizes,
        )
        answer_clip = ImageClip(answer_frame).with_duration(answer_duration).with_fps(30)

        # 합성
        all_clips = [compare_comp, countdown_comp, answer_clip]
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
