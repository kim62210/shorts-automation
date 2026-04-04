import os
import random

from typing import List, Optional
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

from genres import register_genre
from genres.base import BaseGenre
from config import ROOT_DIR, get_threads, get_fonts_dir, get_font
from status import success, warning, info
from utils import choose_random_song
from moviepy import (
    AudioFileClip,
    ImageClip,
    afx,
)


@register_genre
class SpotDifferenceGenre(BaseGenre):
    name = "spot_difference"
    display_name = "Animal Spot the Difference"
    default_effect = None
    default_subtitle_style = "bold_center"
    needs_images = True

    # Fixed duration (no TTS for this genre)
    MAIN_DURATION = 15.0

    def generate_content(self) -> dict:
        prompt = f"""Generate a single cute animal scene for a "Spot the Difference" challenge.

IMPORTANT: This is for a YouTube Shorts channel called "PawPick" — adorable animal content.

Return ONLY valid JSON:
{{
  "scene": "Description of the animal scene",
  "image_prompts": ["A single detailed AI image prompt: a cute, colorful animal scene with multiple small details and objects. Must include several cute animals (cats, dogs, rabbits, etc.) in a detailed environment with various small items, decorations, and colorful elements. The scene should have enough visual complexity for spot-the-difference. Cartoon/illustration style, vibrant colors, lots of small details, 9:16 portrait orientation."]
}}

Requirements:
- Generate ONLY ONE image prompt (we will programmatically create differences)
- The scene must have lots of small details (decorations, objects, patterns) so differences look natural
- Cartoon or illustration style works best (not photorealistic)
- Must feature cute animals
- Write in {self.language}
"""
        content = self.generate_response_json(prompt)
        success(f"Generated spot-the-difference content: {content.get('scene', '')[:60]}")
        return content

    def _create_modified_image(self, original_path: str) -> str:
        """Create a subtly modified version with 3 differences.
        Uses circular feathered masks for natural-looking blended changes."""
        img = Image.open(original_path).convert("RGB")
        w, h = img.size
        modified = img.copy()

        margin_x = w // 5
        margin_y = h // 5
        radius = min(w, h) // 14  # Circle radius

        used_centers = []

        def get_random_center():
            for _ in range(50):
                cx = random.randint(margin_x + radius, w - margin_x - radius)
                cy = random.randint(margin_y + radius, h - margin_y - radius)
                overlaps = False
                for (ux, uy) in used_centers:
                    if ((cx - ux) ** 2 + (cy - uy) ** 2) < (radius * 3) ** 2:
                        overlaps = True
                        break
                if not overlaps:
                    used_centers.append((cx, cy))
                    return cx, cy
            return margin_x + radius, margin_y + radius

        def create_feathered_circle(size, cx, cy, r):
            """Create a soft circular mask with feathered edges."""
            mask = Image.new("L", size, 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(radius=r // 3))
            return mask

        # Difference 1 (easy): Hue shift with soft circular blend
        cx1, cy1 = get_random_center()
        hue_shifted = img.convert("HSV")
        hue_pixels = np.array(hue_shifted)
        hue_pixels[:, :, 0] = (hue_pixels[:, :, 0].astype(int) + 80) % 256
        hue_shifted = Image.fromarray(hue_pixels, "HSV").convert("RGB")
        mask1 = create_feathered_circle((w, h), cx1, cy1, radius)
        modified = Image.composite(hue_shifted, modified, mask1)

        # Difference 2 (medium): Mirrored patch with soft blend
        cx2, cy2 = get_random_center()
        r2 = radius * 2 // 3
        crop_box = (cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2)
        patch = modified.crop(crop_box).transpose(Image.FLIP_LEFT_RIGHT)
        flipped_layer = modified.copy()
        flipped_layer.paste(patch, (cx2 - r2, cy2 - r2))
        mask2 = create_feathered_circle((w, h), cx2, cy2, r2)
        modified = Image.composite(flipped_layer, modified, mask2)

        # Difference 3 (hard): Subtle brightness change with soft blend
        cx3, cy3 = get_random_center()
        r3 = radius // 2
        from PIL import ImageEnhance
        bright_layer = ImageEnhance.Brightness(modified).enhance(1.3)
        mask3 = create_feathered_circle((w, h), cx3, cy3, r3)
        modified = Image.composite(bright_layer, modified, mask3)

        modified_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
        modified.save(modified_path)
        info(f" => Created modified image with 3 subtle differences (feathered circles)")
        return modified_path

    def _create_top_bottom_frame(self, image_a_path: str, image_b_path: str,
                                  size: tuple = (1080, 1920)) -> str:
        """Create a frame with two images stacked vertically with black borders on white bg."""
        canvas = Image.new("RGB", size, (255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        # Title — large bold, reference style
        font_path = os.path.join(get_fonts_dir(), get_font())
        try:
            title_font = ImageFont.truetype(font_path, 80)
            sub_font = ImageFont.truetype(font_path, 52)
            cta_font = ImageFont.truetype(font_path, 36)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            sub_font = title_font
            cta_font = title_font

        # Line 1: main title
        line1 = "Find 3 Differences"
        bbox1 = draw.textbbox((0, 0), line1, font=title_font)
        tw1 = bbox1[2] - bbox1[0]
        draw.text(((size[0] - tw1) // 2, 100), line1, fill="#222222", font=title_font)

        # Line 2: sub text
        line2 = "in 15s = GENIUS"
        bbox2 = draw.textbbox((0, 0), line2, font=sub_font)
        tw2 = bbox2[2] - bbox2[0]
        draw.text(((size[0] - tw2) // 2, 200), line2, fill="#FF4444", font=sub_font)

        # CTA text — positioned midway between bottom image and screen bottom
        # (will be drawn after images, but we pre-calculate position here)
        self._cta_font = cta_font
        self._cta_text = "Found them? Hit Like and comment!"

        # Image layout — 4:3 aspect ratio images, generous whitespace
        padding = 140
        border_w = 6
        gap = 60
        title_area = 310
        bottom_margin = 180

        img_w = size[0] - padding * 2
        img_h = int(img_w * 3 / 4)  # Force 4:3 aspect ratio

        # Helper: center-crop to 4:3 then resize to fit
        def fit_image_4x3(img_path, target_w, target_h):
            img = Image.open(img_path).convert("RGB")
            orig_w, orig_h = img.size
            # Crop to 4:3 from center
            target_ratio = 4 / 3
            orig_ratio = orig_w / orig_h
            if orig_ratio < target_ratio:
                # Too tall — crop top/bottom
                new_h = int(orig_w / target_ratio)
                top = (orig_h - new_h) // 2
                img = img.crop((0, top, orig_w, top + new_h))
            else:
                # Too wide — crop left/right
                new_w = int(orig_h * target_ratio)
                left = (orig_w - new_w) // 2
                img = img.crop((left, 0, left + new_w, orig_h))
            return img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        # Top image (original) with black border — 4:3
        y1 = title_area
        img_a = fit_image_4x3(image_a_path, img_w, img_h)
        a_x = (size[0] - img_w) // 2
        draw.rounded_rectangle(
            [a_x - border_w, y1 - border_w,
             a_x + img_w + border_w, y1 + img_h + border_w],
            radius=14, outline="#000000", width=border_w,
        )
        canvas.paste(img_a, (a_x, y1))

        # Bottom image (modified) with black border — 4:3
        y2 = y1 + img_h + gap
        img_b = fit_image_4x3(image_b_path, img_w, img_h)
        b_x = (size[0] - img_w) // 2
        draw.rounded_rectangle(
            [b_x - border_w, y2 - border_w,
             b_x + img_w + border_w, y2 + img_h + border_w],
            radius=14, outline="#000000", width=border_w,
        )
        canvas.paste(img_b, (b_x, y2))

        # CTA text — midway between bottom image and screen bottom
        cta_text = self._cta_text
        cta_font = self._cta_font
        bbox_cta = draw.textbbox((0, 0), cta_text, font=cta_font)
        tw_cta = bbox_cta[2] - bbox_cta[0]
        img_bottom = y2 + img_h
        cta_y = img_bottom + (size[1] - img_bottom) // 2 - 18
        draw.text(((size[0] - tw_cta) // 2, cta_y), cta_text,
                  fill="#555555", font=cta_font)

        frame_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
        canvas.save(frame_path)
        return frame_path

    def generate_video(self, tts_instance) -> str:
        """Override: generate 1 image, programmatically create differences, no TTS."""
        content = self.generate_content()

        # Generate only 1 original image
        image_prompts = content.get("image_prompts", [])
        if not image_prompts:
            raise RuntimeError("No image prompt generated.")

        original_path = self.generate_image(image_prompts[0])
        if not original_path:
            raise RuntimeError("Image generation failed.")

        # Programmatically create a modified version with 3 subtle differences
        modified_path = self._create_modified_image(original_path)

        path = self.compose_video(None, content, [original_path, modified_path])
        return path

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")
        video_size = (1080, 1920)

        # Single frame with everything (title + images + CTA baked in)
        if images and len(images) >= 2:
            main_frame = self._create_top_bottom_frame(
                images[0], images[1], size=video_size
            )
        else:
            main_frame = self.generate_text_frame(
                texts=["Original", "Modified"],
                colors=["#FF6B6B", "#4ECDC4"],
                bg_color="#FFFFFF",
                font_sizes=[60, 60],
            )

        video_clip = (
            ImageClip(main_frame)
            .with_duration(self.MAIN_DURATION)
            .with_fps(30)
        )

        # BGM only (no TTS)
        try:
            random_song = choose_random_song()
            bgm_clip = AudioFileClip(random_song).with_fps(44100)
            bgm_clip = bgm_clip.with_effects([afx.MultiplyVolume(0.15)])
            video_clip = video_clip.with_audio(bgm_clip)
        except Exception as e:
            warning(f"No background music available, video will be silent: {e}")

        # Write video directly (no subtitles needed)
        video_clip.write_videofile(combined_path, threads=get_threads())
        success(f'Wrote Video to "{combined_path}"')
        return combined_path
