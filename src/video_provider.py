import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from config import get_pexels_api_key
from status import info, warning

logger = logging.getLogger(__name__)

PEXELS_API_BASE = "https://api.pexels.com"


def search_videos(
    query: str,
    orientation: str = "portrait",
    min_duration: int = 5,
    max_duration: int = 15,
    per_page: int = 5,
) -> List[Dict[str, Any]]:
    """Pexels Video API로 영상 검색

    Args:
        query: 검색 키워드
        orientation: 영상 방향 (portrait, landscape, square)
        min_duration: 최소 길이(초)
        max_duration: 최대 길이(초)
        per_page: 결과 수

    Returns:
        비디오 정보 딕셔너리 리스트
    """
    api_key = get_pexels_api_key()
    if not api_key:
        warning("Pexels API 키가 설정되지 않았습니다 (config.json 또는 환경변수 확인)")
        return []

    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "orientation": orientation,
        "per_page": per_page,
    }

    try:
        response = requests.get(
            f"{PEXELS_API_BASE}/videos/search",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.exception("Pexels API 요청 실패")
        warning(f"Pexels API 요청 실패: {e}")
        return []

    data = response.json()
    videos = data.get("videos", [])

    # 길이 필터링
    filtered = []
    for video in videos:
        dur = video.get("duration", 0)
        if min_duration <= dur <= max_duration:
            filtered.append({
                "id": video["id"],
                "url": video["url"],
                "duration": dur,
                "width": video.get("width", 0),
                "height": video.get("height", 0),
                "video_files": video.get("video_files", []),
            })

    info(f"Pexels 검색 결과: {len(filtered)}개 (query={query})")
    return filtered


def download_video(
    video_url: str,
    output_path: str,
    timeout: int = 60,
) -> Optional[str]:
    """비디오 파일을 다운로드하여 로컬에 저장

    Args:
        video_url: 다운로드할 비디오 URL
        output_path: 저장할 로컬 경로
        timeout: 다운로드 타임아웃(초)

    Returns:
        저장된 로컬 파일 경로, 실패 시 None
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(video_url, stream=True, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.exception("비디오 다운로드 실패")
        warning(f"비디오 다운로드 실패: {e}")
        return None

    with open(output, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    info(f"비디오 다운로드 완료: {output_path}")
    return str(output)
