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

        base_url = get_nanobanana2_api_base_url().rstrip("/")
        model = get_nanobanana2_model()
        aspect_ratio = get_nanobanana2_aspect_ratio()

        endpoint = f"{base_url}/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
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

    # ── Text Frame Generation (Pillow) ───────────────

    def generate_text_frame(self, texts: list, colors: list = None,
                            bg_color: str = "#0a0a1a",
                            size: tuple = (1080, 1920),
                            font_sizes: list = None) -> str:
        img = Image.new("RGB", size, bg_color)
        draw = ImageDraw.Draw(img)

        font_path = os.path.join(get_fonts_dir(), get_font())
        if colors is None:
            colors = ["#FFFFFF"] * len(texts)
        if font_sizes is None:
            font_sizes = [60] * len(texts)

        y_offset = size[1] // 2 - (len(texts) * 80) // 2
        for text, color, fsize in zip(texts, colors, font_sizes):
            try:
                font = ImageFont.truetype(font_path, fsize)
            except (OSError, IOError):
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x = (size[0] - text_width) // 2
            draw.text((x, y_offset), text, fill=color, font=font)
            y_offset += fsize + 20

        frame_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
        img.save(frame_path)
        return frame_path

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
        """자막 합성 + 오디오 믹싱 + 파일 쓰기 공통 로직."""
        tts_clip = AudioFileClip(tts_path)

        # 자막
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

        # 오디오
        comp_audio = self.mix_audio(tts_path)
        video_clip = video_clip.with_audio(comp_audio)
        video_clip = video_clip.with_duration(tts_clip.duration)

        # 자막 합성
        if subtitles is not None:
            video_clip = CompositeVideoClip([video_clip, subtitles])

        # 파일 쓰기
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
