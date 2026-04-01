from abc import ABC, abstractmethod
from typing import List
from moviepy import VideoClip


class BaseEffect(ABC):
    name: str
    display_name: str

    @abstractmethod
    def apply(self, image_paths: List[str], duration: float,
              video_size: tuple = (1080, 1920)) -> VideoClip:
        raise NotImplementedError
