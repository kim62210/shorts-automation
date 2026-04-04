import os
import re
import json

from typing import List, Optional
from uuid import uuid4

from genres import register_genre
from genres.base import BaseGenre
from config import (
    ROOT_DIR,
    get_verbose,
    get_script_sentence_length,
)
from status import error, success, info, warning
from moviepy import (
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
)


@register_genre
class NarrationGenre(BaseGenre):
    name = "narration"
    display_name = "Animal Stories"
    default_effect = "slideshow"
    default_subtitle_style = "classic"
    needs_images = True

    def generate_content(self, _retry_count: int = 0) -> dict:
        topic = self.generate_response(
            f"Please generate a specific and interesting animal-related video topic. The niche is: {self.niche}, but the topic MUST be about animals (e.g., surprising animal facts, cute animal behaviors, amazing animal abilities, animal world records, etc.). Write the topic in {self.language}. Make it exactly one sentence. Only return the topic, nothing else."
        )
        if not topic:
            error("Failed to generate Topic.")

        sentence_length = get_script_sentence_length()
        script = self.generate_response(f"""
        Generate a script for a cute and fun animal video in {sentence_length} sentences.

        The script is to be returned as a string with the specified number of paragraphs.

        Here is an example of a string:
        "This is an example string."

        Do not under any circumstance reference this prompt in your response.

        Get straight to the point, don't start with unnecessary things like, "welcome to this video".

        The script MUST be about animals. Write in an engaging, warm, and fun tone as if talking to animal lovers.
        Include surprising or heartwarming animal facts. Make readers feel amazed or say "aww" about animals.

        YOU MUST NOT EXCEED THE {sentence_length} SENTENCES LIMIT. MAKE SURE THE {sentence_length} SENTENCES ARE SHORT.
        YOU MUST NOT INCLUDE ANY TYPE OF MARKDOWN OR FORMATTING IN THE SCRIPT, NEVER USE A TITLE.
        YOU MUST WRITE THE SCRIPT IN {self.language}.
        ONLY RETURN THE RAW CONTENT OF THE SCRIPT. DO NOT INCLUDE "VOICEOVER", "NARRATOR" OR SIMILAR INDICATORS OF WHAT SHOULD BE SPOKEN AT THE BEGINNING OF EACH PARAGRAPH OR LINE. YOU MUST NOT MENTION THE PROMPT, OR ANYTHING ABOUT THE SCRIPT ITSELF. ALSO, NEVER TALK ABOUT THE AMOUNT OF PARAGRAPHS OR LINES. JUST WRITE THE SCRIPT

        Subject: {topic}
        Language: {self.language}
        """)

        script = re.sub(r"\*", "", script)
        if not script:
            error("The generated script is empty.")
        if len(script) > 5000:
            if _retry_count >= 3:
                raise RuntimeError("Max retries exceeded for content generation")
            if get_verbose():
                warning("Generated Script is too long. Retrying...")
            return self.generate_content(_retry_count=_retry_count + 1)

        title = self.generate_response(
            f"Please generate a cute and catchy YouTube Shorts title about animals for the following subject, including animal-related hashtags (e.g., #animals #cuteanimals #animalfacts). Write the title in {self.language}. Subject: {topic}. Only return the title, nothing else. Limit the title under 100 characters."
        )
        if len(title) > 100:
            title = title[:97] + "..."

        description = self.generate_response(
            f"Please generate a YouTube Video Description about animals for the following script. Write in {self.language}. Script: {script}. Only return the description, nothing else."
        )

        sentence_count = len(
            [s for s in re.split(r"[.!?]+", script) if s.strip()]
        )
        n_prompts = max(3, min(8, sentence_count or sentence_length))

        prompts_raw = self.generate_response(f"""
        Generate {n_prompts} Image Prompts for AI Image Generation.
        The images MUST depict cute, adorable, or majestic animals related to the video subject.
        Subject: {topic}

        The image prompts are to be returned as a JSON-Array of strings.

        Each prompt should describe a vivid, cute, or stunning animal scene.
        Use descriptive adjectives like "adorable", "fluffy", "majestic", "playful".
        Always specify the animal species clearly. Use photorealistic or high-quality illustration style.
        Make images look warm, bright, and appealing for an animal-loving audience.

        YOU MUST ONLY RETURN THE JSON-ARRAY OF STRINGS.
        YOU MUST NOT RETURN ANYTHING ELSE.

        Here is an example of a JSON-Array of strings:
        ["A fluffy orange tabby cat curled up sleeping in warm sunlight, photorealistic, soft lighting", "An adorable baby otter floating on its back in crystal clear water, 4K wildlife photography"]

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
        except json.JSONDecodeError as e:
            r = re.compile(r"\[.*\]", re.DOTALL)
            matches = r.findall(prompts_raw)
            if matches:
                image_prompts = json.loads(matches[0])
            else:
                if _retry_count >= 3:
                    raise RuntimeError("Max retries exceeded for content generation") from e
                if get_verbose():
                    warning("Failed to parse image prompts. Retrying...")
                return self.generate_content(_retry_count=_retry_count + 1)

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

        tts_clip = AudioFileClip(tts_path)
        max_duration = tts_clip.duration

        effect = self._get_effect()
        if effect and images:
            video_clip = effect.apply(images, max_duration)
        else:
            video_clip = ImageClip(images[0]).with_duration(max_duration).with_fps(30)

        video_clip = video_clip.with_fps(30)

        cta_img = images[-1] if images else None
        cta_frame = self.generate_cta_frame(cta_img)
        cta_clip = ImageClip(cta_frame).with_duration(3.0).with_fps(30)
        video_clip = concatenate_videoclips([video_clip, cta_clip])

        return self._finalize_video(video_clip, tts_path, combined_path)
