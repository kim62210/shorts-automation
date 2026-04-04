import os
import re
import json

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from config import (
    ROOT_DIR,
    get_verbose,
    get_fonts_dir,
    get_font,
    get_stt_provider,
    get_assemblyai_api_key,
    get_whisper_model,
    get_whisper_device,
    get_whisper_compute_type,
    get_nanobanana2_api_key,
    get_nanobanana2_api_base_url,
    get_nanobanana2_model,
    get_nanobanana2_aspect_ratio,
    get_threads,
    equalize_subtitles,
)
from status import error, success, info, warning
from llm_provider import generate_text
from utils import choose_random_song

import requests
import base64
from moviepy import (
    AudioFileClip,
    ImageClip,
    CompositeAudioClip,
    CompositeVideoClip,
    afx,
)


class BaseGenre(ABC):
    name: str = ""
    display_name: str = ""
    default_effect: Optional[str] = None
    default_subtitle_style: str = "classic"
    needs_images: bool = True

    # YouTube Shorts safe zone (based on 1080x1920)
    SAFE_TOP = 270
    SAFE_BOTTOM = 400     # bottom margin (buttons/channel info)
    SAFE_LEFT = 60
    SAFE_RIGHT = 190      # right margin (like/comment buttons)

    # PawPick cute animal image style suffix
    IMAGE_STYLE_SUFFIX = (
        ", adorable cute animal character, photorealistic 3D render, "
        "oversized sparkling eyes, Pixar-quality kawaii expression, "
        "soft pastel colors, cinematic lighting, hyperrealistic fur texture, "
        "9:16 vertical composition, 4K quality"
    )

    # CTA texts (PawPick)
    CTA_TEXTS = [
        "Like if accurate! 👍",
        "Comment your answer! 💬",
        "Follow for more! 🐾",
    ]
    CTA_COLORS = ["#FFFF00", "#FFFFFF", "#C4B5FD"]
    CTA_FONT_SIZES = [48, 40, 36]

    def __init__(self, niche: str, language: str,
                 effect_override: Optional[str] = None,
                 subtitle_override: Optional[str] = None):
        self._niche = niche
        self._language = language
        self._effect_name = effect_override or self.default_effect
        self._subtitle_name = subtitle_override or self.default_subtitle_style

    @property
    def niche(self) -> str:
        return self._niche

    @property
    def language(self) -> str:
        return self._language

    def _get_effect(self):
        if self._effect_name is None:
            return None
        from effects import get_effect
        return get_effect(self._effect_name)()

    def _get_subtitle_style(self):
        from subtitles import get_style
        return get_style(self._subtitle_name)()

    # ── LLM ──────────────────────────────────────────

    def generate_response(self, prompt: str) -> str:
        return generate_text(prompt)

    def generate_response_json(self, prompt: str, _retry_count: int = 0) -> dict:
        raw = self.generate_response(prompt)
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            if _retry_count >= 2:
                raise RuntimeError(
                    f"LLM returned invalid JSON after {_retry_count + 1} attempts"
                ) from exc
            if get_verbose():
                warning(f"JSON parse failed (attempt {_retry_count + 1}), retrying...")
            return self.generate_response_json(prompt, _retry_count=_retry_count + 1)

    # ── Image Generation ─────────────────────────────

    def generate_image(self, prompt: str) -> Optional[str]:
        api_key = get_nanobanana2_api_key()
        if not api_key:
            error("nanobanana2_api_key is not configured.")
            return None

        # PawPick cute animal style auto-applied
        styled_prompt = prompt + self.IMAGE_STYLE_SUFFIX

        base_url = get_nanobanana2_api_base_url().rstrip("/")
        model = get_nanobanana2_model()
        aspect_ratio = get_nanobanana2_aspect_ratio()

        endpoint = f"{base_url}/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": styled_prompt}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": aspect_ratio},
            },
        }

        try:
            response = requests.post(
                endpoint,
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
            body = response.json()

            for candidate in body.get("candidates", []):
                content = candidate.get("content", {})
                for part in content.get("parts", []):
                    inline_data = part.get("inlineData") or part.get("inline_data")
                    if not inline_data:
                        continue
                    data = inline_data.get("data")
                    mime_type = inline_data.get("mimeType") or inline_data.get("mime_type", "")
                    if data and str(mime_type).startswith("image/"):
                        image_bytes = base64.b64decode(data)
                        image_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)
                        if get_verbose():
                            info(f' => Wrote image to "{image_path}"')
                        return image_path

            if get_verbose():
                warning(f"Image generation did not return an image payload.")
            return None
        except Exception as e:
            if get_verbose():
                warning(f"Failed to generate image: {str(e)}")
            return None

    # ── TTS ──────────────────────────────────────────

    def generate_tts(self, text: str, tts_instance) -> str:
        path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".wav")
        cleaned = re.sub(r"[^\w\s.?!]", "", text)
        tts_instance.synthesize(cleaned, path)
        if get_verbose():
            info(f' => Wrote TTS to "{path}"')
        return path

    # ── Subtitles ────────────────────────────────────

    def generate_subtitles(self, audio_path: str) -> str:
        provider = str(get_stt_provider() or "local_whisper").lower()

        if provider == "local_whisper":
            return self._generate_subtitles_whisper(audio_path)
        if provider == "third_party_assemblyai":
            return self._generate_subtitles_assemblyai(audio_path)

        warning(f"Unknown stt_provider '{provider}'. Falling back to local_whisper.")
        return self._generate_subtitles_whisper(audio_path)

    def _generate_subtitles_whisper(self, audio_path: str) -> str:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            get_whisper_model(),
            device=get_whisper_device(),
            compute_type=get_whisper_compute_type(),
        )
        segments, _ = model.transcribe(audio_path, vad_filter=True)

        lines = []
        for idx, segment in enumerate(segments, start=1):
            start = self._format_srt_timestamp(segment.start)
            end = self._format_srt_timestamp(segment.end)
            text = str(segment.text).strip()
            if not text:
                continue
            lines.append(str(idx))
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")

        srt_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return srt_path

    def generate_word_level_subtitles(self, audio_path: str) -> list:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            get_whisper_model(),
            device=get_whisper_device(),
            compute_type=get_whisper_compute_type(),
        )
        segments, _ = model.transcribe(audio_path, vad_filter=True, word_timestamps=True)

        words = []
        for segment in segments:
            for word in segment.words:
                words.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end,
                })
        return words

    def _generate_subtitles_assemblyai(self, audio_path: str) -> str:
        import assemblyai as aai

        aai.settings.api_key = get_assemblyai_api_key()
        config = aai.TranscriptionConfig()
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_path)
        subtitles = transcript.export_subtitles_srt()

        srt_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".srt")
        with open(srt_path, "w") as f:
            f.write(subtitles)
        return srt_path

    @staticmethod
    def _format_srt_timestamp(seconds: float) -> str:
        total_millis = max(0, int(round(seconds * 1000)))
        hours = total_millis // 3600000
        minutes = (total_millis % 3600000) // 60000
        secs = (total_millis % 60000) // 1000
        millis = total_millis % 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    # ── Text Wrapping Helper ─────────────────────────

    @staticmethod
    def _wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list:
        """Wrap text to fit within max_width."""
        if not text.strip():
            return [text]
        words = text.split()
        if not words:
            return [text]
        lines = []
        current_line = words[0]
        for word in words[1:]:
            test = f"{current_line} {word}"
            bbox = draw.textbbox((0, 0), test, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                current_line = test
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return lines

    def _draw_texts_in_safe_zone(self, draw: ImageDraw.ImageDraw, texts: list,
                                  colors: list, font_sizes: list,
                                  size: tuple = (1080, 1920)) -> None:
        """Center-align text within the safe zone with auto line wrapping."""
        font_path = os.path.join(get_fonts_dir(), get_font())
        safe_x1 = self.SAFE_LEFT
        safe_x2 = size[0] - self.SAFE_RIGHT
        safe_y1 = self.SAFE_TOP
        safe_y2 = size[1] - self.SAFE_BOTTOM
        safe_w = safe_x2 - safe_x1
        safe_h = safe_y2 - safe_y1
        safe_cx = (safe_x1 + safe_x2) // 2
        line_spacing = 16

        # Step 1: Wrap all texts and calculate total height
        all_rendered = []  # [(wrapped_lines, font, color, fsize)]
        total_height = 0
        for text, color, fsize in zip(texts, colors, font_sizes):
            try:
                font = ImageFont.truetype(font_path, fsize)
            except (OSError, IOError):
                font = ImageFont.load_default()
            wrapped = self._wrap_text(text, font, safe_w, draw)
            block_h = len(wrapped) * (fsize + line_spacing)
            all_rendered.append((wrapped, font, color, fsize))
            total_height += block_h

        # Step 2: Start from vertical center of the safe zone
        y = safe_y1 + max(0, (safe_h - total_height) // 2)

        # Step 3: Draw
        for wrapped, font, color, fsize in all_rendered:
            for line in wrapped:
                bbox = draw.textbbox((0, 0), line, font=font)
                tw = bbox[2] - bbox[0]
                x = safe_cx - tw // 2
                # Clamp to stay within the safe zone
                x = max(safe_x1, min(x, safe_x2 - tw))
                if y + fsize <= safe_y2:
                    draw.text((x, y), line, fill=color, font=font)
                y += fsize + line_spacing

    # ── Text Frame Generation (Pillow) ───────────────

    def generate_text_frame(self, texts: list, colors: list = None,
                            bg_color: str = "#0a0a1a",
                            size: tuple = (1080, 1920),
                            font_sizes: list = None) -> str:
        img = Image.new("RGB", size, bg_color)
        draw = ImageDraw.Draw(img)

        if colors is None:
            colors = ["#FFFFFF"] * len(texts)
        if font_sizes is None:
            font_sizes = [60] * len(texts)

        self._draw_texts_in_safe_zone(draw, texts, colors, font_sizes, size)

        frame_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
        img.save(frame_path)
        return frame_path

    def generate_text_on_image_frame(self, image_path: str, texts: list,
                                        colors: list = None,
                                        size: tuple = (1080, 1920),
                                        font_sizes: list = None,
                                        darken: float = 0.45) -> str:
        """Darken AI image with semi-transparent overlay, then add text."""
        bg = Image.open(image_path).convert("RGB")
        bg = bg.resize(size, Image.LANCZOS)

        overlay = Image.new("RGBA", size, (0, 0, 0, int(255 * darken)))
        bg = bg.convert("RGBA")
        bg = Image.alpha_composite(bg, overlay)
        bg = bg.convert("RGB")

        draw = ImageDraw.Draw(bg)
        if colors is None:
            colors = ["#FFFFFF"] * len(texts)
        if font_sizes is None:
            font_sizes = [60] * len(texts)

        self._draw_texts_in_safe_zone(draw, texts, colors, font_sizes, size)

        frame_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
        bg.save(frame_path)
        return frame_path

    def generate_3tier_image_frame(self, image_path: str,
                                    top_texts: list = None, top_colors: list = None,
                                    top_font_sizes: list = None,
                                    bottom_texts: list = None, bottom_colors: list = None,
                                    bottom_font_sizes: list = None,
                                    size: tuple = (1080, 1920),
                                    darken: float = 0.35) -> str:
        """PawPick 3-tier layout: top 20% question, center 60% image, bottom 20% CTA/info."""
        bg = Image.open(image_path).convert("RGB")
        bg = bg.resize(size, Image.LANCZOS)

        # Darken only top/bottom zones (keep center image area bright)
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        top_zone = int(size[1] * 0.25)
        bottom_zone = int(size[1] * 0.75)
        # Top gradient
        for y in range(top_zone):
            alpha = int(180 * (1 - y / top_zone))
            overlay_draw.line([(0, y), (size[0], y)], fill=(0, 0, 0, alpha))
        # Bottom gradient
        for y in range(bottom_zone, size[1]):
            alpha = int(180 * ((y - bottom_zone) / (size[1] - bottom_zone)))
            overlay_draw.line([(0, y), (size[0], y)], fill=(0, 0, 0, alpha))

        bg = bg.convert("RGBA")
        bg = Image.alpha_composite(bg, overlay)
        bg = bg.convert("RGB")

        draw = ImageDraw.Draw(bg)
        font_path = os.path.join(get_fonts_dir(), get_font())
        safe_x1 = self.SAFE_LEFT
        safe_x2 = size[0] - self.SAFE_RIGHT
        safe_w = safe_x2 - safe_x1
        safe_cx = (safe_x1 + safe_x2) // 2
        line_sp = 14

        def _draw_block(texts, colors, font_sizes, y_start, y_end, valign="center"):
            if not texts:
                return
            rendered = []
            total_h = 0
            for t, c, fs in zip(texts, colors, font_sizes):
                try:
                    f = ImageFont.truetype(font_path, fs)
                except (OSError, IOError):
                    f = ImageFont.load_default()
                wrapped = self._wrap_text(t, f, safe_w, draw)
                block_h = len(wrapped) * (fs + line_sp)
                rendered.append((wrapped, f, c, fs))
                total_h += block_h

            if valign == "top":
                y = y_start + 10
            elif valign == "bottom":
                y = max(y_start, y_end - total_h - 10)
            else:
                y = y_start + max(0, (y_end - y_start - total_h) // 2)

            for wrapped, f, c, fs in rendered:
                for line in wrapped:
                    bbox = draw.textbbox((0, 0), line, font=f)
                    tw = bbox[2] - bbox[0]
                    x = safe_cx - tw // 2
                    x = max(safe_x1, min(x, safe_x2 - tw))
                    if y + fs <= size[1]:
                        draw.text((x, y), line, fill=c, font=f)
                    y += fs + line_sp

        # Top zone (safe zone top ~ 25%)
        if top_texts:
            _draw_block(top_texts, top_colors or ["#FFFFFF"] * len(top_texts),
                       top_font_sizes or [52] * len(top_texts),
                       self.SAFE_TOP, int(size[1] * 0.25), valign="center")

        # Bottom zone (75% ~ safe zone bottom)
        if bottom_texts:
            _draw_block(bottom_texts, bottom_colors or ["#FFFFFF"] * len(bottom_texts),
                       bottom_font_sizes or [40] * len(bottom_texts),
                       int(size[1] * 0.75), size[1] - self.SAFE_BOTTOM, valign="center")

        frame_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
        bg.save(frame_path)
        return frame_path

    def generate_cta_frame(self, bg_image_path: str = None,
                           size: tuple = (1080, 1920)) -> str:
        """Generate CTA (call-to-action) frame."""
        if bg_image_path:
            return self.generate_text_on_image_frame(
                bg_image_path, texts=self.CTA_TEXTS,
                colors=self.CTA_COLORS, font_sizes=self.CTA_FONT_SIZES,
                darken=0.55,
            )
        return self.generate_text_frame(
            texts=self.CTA_TEXTS, colors=self.CTA_COLORS,
            bg_color="#0a0a2e", font_sizes=self.CTA_FONT_SIZES,
        )

    def generate_gradient_frame(self, color_top: str = "#0a0a1a",
                                color_bottom: str = "#1a1a3e",
                                size: tuple = (1080, 1920)) -> str:
        img = Image.new("RGB", size)
        draw = ImageDraw.Draw(img)

        r1, g1, b1 = Image.new("RGB", (1, 1), color_top).getpixel((0, 0))
        r2, g2, b2 = Image.new("RGB", (1, 1), color_bottom).getpixel((0, 0))

        for y in range(size[1]):
            ratio = y / size[1]
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            draw.line([(0, y), (size[0], y)], fill=(r, g, b))

        frame_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
        img.save(frame_path)
        return frame_path

    # ── Finalize Video ────────────────────────────────

    def _finalize_video(self, video_clip, tts_path: str, combined_path: str,
                        video_size: tuple = (1080, 1920)) -> str:
        """Common logic for subtitle compositing + audio mixing + file writing."""
        tts_clip = AudioFileClip(tts_path)

        # Subtitles
        subtitle_style = self._get_subtitle_style()
        subtitles = None
        try:
            if self._subtitle_name == "highlight_word" and hasattr(subtitle_style, "render_word_level"):
                words = self.generate_word_level_subtitles(tts_path)
                if words:
                    subtitles = subtitle_style.render_word_level(words, video_size, tts_clip.duration)
            if subtitles is None:
                srt_path = self.generate_subtitles(tts_path)
                equalize_subtitles(srt_path, 10)
                subtitles = subtitle_style.render_subtitles(srt_path, video_size)
        except Exception as e:
            warning(f"Failed to generate subtitles, continuing without: {e}")

        # Audio
        comp_audio = self.mix_audio(tts_path)
        video_clip = video_clip.with_audio(comp_audio)
        video_clip = video_clip.with_duration(tts_clip.duration)

        # Subtitle compositing
        if subtitles is not None:
            video_clip = CompositeVideoClip([video_clip, subtitles])

        # Write file
        video_clip.write_videofile(combined_path, threads=get_threads())
        success(f'Wrote Video to "{combined_path}"')

        return combined_path

    # ── Audio Mixing ─────────────────────────────────

    def mix_audio(self, tts_path: str) -> CompositeAudioClip:
        tts_clip = AudioFileClip(tts_path).with_fps(44100)
        audio_clips = [tts_clip]

        try:
            random_song = choose_random_song()
            bgm_clip = AudioFileClip(random_song).with_fps(44100)
            bgm_clip = bgm_clip.with_effects([afx.MultiplyVolume(0.1)])
            audio_clips.append(bgm_clip)
        except Exception as e:
            warning(f"Failed to attach background music, continuing with TTS only: {e}")

        return CompositeAudioClip(audio_clips)

    # ── Abstract Methods ─────────────────────────────

    @abstractmethod
    def generate_content(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        raise NotImplementedError

    # ── Master Orchestrator ──────────────────────────

    def generate_video(self, tts_instance) -> str:
        content = self.generate_content()

        script = content.get("script", "")
        tts_path = self.generate_tts(script, tts_instance)

        images = []
        if self.needs_images:
            for prompt in content.get("image_prompts", []):
                img = self.generate_image(prompt)
                if img:
                    images.append(img)
            if not images and content.get("image_prompts"):
                raise RuntimeError("Image generation failed for all prompts.")

        path = self.compose_video(tts_path, content, images)

        if get_verbose():
            info(f" => Generated Video: {path}")

        return path
