import os
import re
import json

from typing import List, Optional
from uuid import uuid4
from termcolor import colored

from genres import register_genre
from genres.base import BaseGenre
from config import (
    ROOT_DIR,
    get_verbose,
    get_script_sentence_length,
    get_threads,
    equalize_subtitles,
)
from status import error, success, info, warning
from moviepy import (
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    CompositeAudioClip,
)


@register_genre
class NarrationGenre(BaseGenre):
    name = "narration"
    display_name = "내레이션 + 이미지"
    default_effect = "slideshow"
    default_subtitle_style = "classic"
    needs_images = True

    def generate_content(self) -> dict:
        topic = self.generate_response(
            f"Please generate a specific video idea that takes about the following topic: {self.niche}. Make it exactly one sentence. Only return the topic, nothing else."
        )
        if not topic:
            error("Failed to generate Topic.")

        sentence_length = get_script_sentence_length()
        script = self.generate_response(f"""
        Generate a script for a video in {sentence_length} sentences, depending on the subject of the video.

        The script is to be returned as a string with the specified number of paragraphs.

        Here is an example of a string:
        "This is an example string."

        Do not under any circumstance reference this prompt in your response.

        Get straight to the point, don't start with unnecessary things like, "welcome to this video".

        Obviously, the script should be related to the subject of the video.

        YOU MUST NOT EXCEED THE {sentence_length} SENTENCES LIMIT. MAKE SURE THE {sentence_length} SENTENCES ARE SHORT.
        YOU MUST NOT INCLUDE ANY TYPE OF MARKDOWN OR FORMATTING IN THE SCRIPT, NEVER USE A TITLE.
        YOU MUST WRITE THE SCRIPT IN THE LANGUAGE SPECIFIED IN [LANGUAGE].
        ONLY RETURN THE RAW CONTENT OF THE SCRIPT. DO NOT INCLUDE "VOICEOVER", "NARRATOR" OR SIMILAR INDICATORS OF WHAT SHOULD BE SPOKEN AT THE BEGINNING OF EACH PARAGRAPH OR LINE. YOU MUST NOT MENTION THE PROMPT, OR ANYTHING ABOUT THE SCRIPT ITSELF. ALSO, NEVER TALK ABOUT THE AMOUNT OF PARAGRAPHS OR LINES. JUST WRITE THE SCRIPT

        Subject: {topic}
        Language: {self.language}
        """)

        script = re.sub(r"\*", "", script)
        if not script:
            error("The generated script is empty.")
        if len(script) > 5000:
            if get_verbose():
                warning("Generated Script is too long. Retrying...")
            return self.generate_content()

        title = self.generate_response(
            f"Please generate a YouTube Video Title for the following subject, including hashtags: {topic}. Only return the title, nothing else. Limit the title under 100 characters."
        )
        if len(title) > 100:
            title = title[:97] + "..."

        description = self.generate_response(
            f"Please generate a YouTube Video Description for the following script: {script}. Only return the description, nothing else."
        )

        sentence_count = len(
            [s for s in re.split(r"[.!?]+", script) if s.strip()]
        )
        n_prompts = max(3, min(8, sentence_count or sentence_length))

        prompts_raw = self.generate_response(f"""
        Generate {n_prompts} Image Prompts for AI Image Generation,
        depending on the subject of a video.
        Subject: {topic}

        The image prompts are to be returned as a JSON-Array of strings.

        Each search term should consist of a full sentence,
        always add the main subject of the video.

        Be emotional and use interesting adjectives to make the
        Image Prompt as detailed as possible.

        YOU MUST ONLY RETURN THE JSON-ARRAY OF STRINGS.
        YOU MUST NOT RETURN ANYTHING ELSE.

        The search terms must be related to the subject of the video.
        Here is an example of a JSON-Array of strings:
        ["image prompt 1", "image prompt 2", "image prompt 3"]

        For context, here is the full text:
        {script}
        """)

        prompts_raw = prompts_raw.replace("```json", "").replace("```", "")
        try:
            parsed = json.loads(prompts_raw)
            if isinstance(parsed, dict) and "image_prompts" in parsed:
                image_prompts = parsed["image_prompts"]
            else:
                image_prompts = parsed
        except Exception:
            r = re.compile(r"\[.*\]", re.DOTALL)
            matches = r.findall(prompts_raw)
            if matches:
                image_prompts = json.loads(matches[0])
            else:
                if get_verbose():
                    warning("Failed to parse image prompts. Retrying...")
                return self.generate_content()

        if len(image_prompts) > n_prompts:
            image_prompts = image_prompts[:n_prompts]

        success(f"Generated {len(image_prompts)} Image Prompts.")

        return {
            "topic": topic,
            "script": script,
            "title": title,
            "description": description,
            "image_prompts": image_prompts,
        }

    def compose_video(self, tts_path: str, content: dict,
                      images: Optional[List[str]] = None) -> str:
        combined_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")
        threads = get_threads()

        tts_clip = AudioFileClip(tts_path)
        max_duration = tts_clip.duration

        effect = self._get_effect()
        if effect and images:
            video_clip = effect.apply(images, max_duration)
        else:
            video_clip = ImageClip(images[0]).with_duration(max_duration).with_fps(30)

        video_clip = video_clip.with_fps(30)

        subtitle_style = self._get_subtitle_style()
        subtitles = None
        try:
            srt_path = self.generate_subtitles(tts_path)
            equalize_subtitles(srt_path, 10)
            subtitles = subtitle_style.render_subtitles(srt_path, (1080, 1920))
        except Exception as e:
            warning(f"Failed to generate subtitles, continuing without: {e}")

        comp_audio = self.mix_audio(tts_path)

        video_clip = video_clip.with_audio(comp_audio)
        video_clip = video_clip.with_duration(tts_clip.duration)

        if subtitles is not None:
            video_clip = CompositeVideoClip([video_clip, subtitles])

        video_clip.write_videofile(combined_path, threads=threads)
        success(f'Wrote Video to "{combined_path}"')

        return combined_path
