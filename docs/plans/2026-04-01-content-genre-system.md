# Content Genre System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 단일 포맷 파이프라인을 13개 콘텐츠 장르 + 4개 영상 효과 + 5개 자막 스타일을 지원하는 확장 가능한 구조로 리팩토링한다.

**Architecture:** 장르별 독립 클래스 (BaseGenre 상속) + Effect/SubtitleStyle 프리셋 조합. GenreRegistry로 장르 동적 등록. 기존 YouTube.py의 combine() 로직을 narration 장르로 이전하고, YouTube.py는 장르 디스패치 역할로 전환.

**Tech Stack:** Python 3.12, MoviePy 2.2.1 (Resize/CrossFadeIn/SlideIn/Crop), faster-whisper (word-level timestamps), Pexels Video API (B-Roll), KittenTTS

---

## Chunk 1: Foundation — Base Classes & Registries

### Task 1: SubtitleStyle 베이스 + Registry

**Files:**
- Create: `src/subtitles/__init__.py`
- Create: `src/subtitles/base.py`

- [ ] **Step 1: `src/subtitles/base.py` 작성**

```python
from abc import ABC, abstractmethod
from moviepy import TextClip, VideoClip


class BaseSubtitleStyle(ABC):
    name: str
    display_name: str

    @abstractmethod
    def make_textclip(self, text: str, video_size: tuple) -> TextClip:
        """SRT 한 줄에 대한 TextClip 생성."""
        raise NotImplementedError

    def render_subtitles(self, srt_path: str, video_size: tuple) -> VideoClip:
        """SRT 파일 → SubtitlesClip 변환. 기본 구현은 대부분 스타일에서 재사용."""
        from moviepy.video.tools.subtitles import SubtitlesClip
        generator = lambda txt: self.make_textclip(txt, video_size)
        clip = SubtitlesClip(srt_path, make_textclip=generator)
        return clip.with_position(("center", "center"))
```

- [ ] **Step 2: `src/subtitles/__init__.py` Registry 작성**

```python
SUBTITLE_STYLES = {}

def register_style(cls):
    SUBTITLE_STYLES[cls.name] = cls
    return cls

def get_style(name):
    return SUBTITLE_STYLES[name]

def list_styles():
    return list(SUBTITLE_STYLES.values())
```

- [ ] **Step 3: 커밋**

---

### Task 2: Effect 베이스 + Registry

**Files:**
- Create: `src/effects/__init__.py`
- Create: `src/effects/base.py`

- [ ] **Step 1: `src/effects/base.py` 작성**

```python
from abc import ABC, abstractmethod
from typing import List
from moviepy import VideoClip


class BaseEffect(ABC):
    name: str
    display_name: str

    @abstractmethod
    def apply(self, image_paths: List[str], duration: float, video_size: tuple) -> VideoClip:
        """이미지 리스트 → 효과 적용된 비디오 클립 반환.

        Args:
            image_paths: 이미지 파일 경로 리스트
            duration: 전체 영상 길이 (초)
            video_size: (width, height) 튜플
        """
        raise NotImplementedError
```

- [ ] **Step 2: `src/effects/__init__.py` Registry 작성**

```python
EFFECTS = {}

def register_effect(cls):
    EFFECTS[cls.name] = cls
    return cls

def get_effect(name):
    return EFFECTS[name]

def list_effects():
    return list(EFFECTS.values())
```

- [ ] **Step 3: 커밋**

---

### Task 3: Genre 베이스 + Registry

**Files:**
- Create: `src/genres/__init__.py`
- Create: `src/genres/base.py`

- [ ] **Step 1: `src/genres/base.py` 작성**

BaseGenre는 공통 메서드를 제공하고 장르별 `generate_content()`와 `compose_video()`만 구현하도록 한다.

핵심 공통 메서드:
- `generate_tts(text, tts_instance)` → WAV 경로
- `generate_subtitles(audio_path)` → SRT 경로
- `apply_subtitle_style(video_clip, srt_path)` → 자막 합성된 VideoClip
- `mix_audio(tts_clip, bgm_path)` → CompositeAudioClip
- `generate_image(prompt)` → PNG 경로
- `generate_text_frame(texts, colors, bg, size)` → ImageClip (텍스트 장르용)
- `generate_video(tts_instance)` → 마스터 오케스트레이터, MP4 경로

`generate_text_frame()`은 Pillow로 텍스트를 이미지로 렌더링하는 메서드. 퀴즈/명언/스토리 등 텍스트 기반 장르에서 핵심.

- [ ] **Step 2: `src/genres/__init__.py` Registry 작성**

```python
GENRES = {}

def register_genre(cls):
    GENRES[cls.name] = cls
    return cls

def get_genre(name):
    return GENRES[name]

def list_genres():
    return list(GENRES.values())
```

- [ ] **Step 3: 커밋**

---

## Chunk 2: Subtitle Styles (5개)

### Task 4: Classic 자막 스타일

**Files:**
- Create: `src/subtitles/classic.py`

- [ ] **Step 1: 구현** — 현재 YouTube.py의 TextClip 설정을 그대로 이전. 노란색 100px, 검정 테두리 5px.

- [ ] **Step 2: 커밋**

---

### Task 5: Modern Box 자막 스타일

**Files:**
- Create: `src/subtitles/modern_box.py`

- [ ] **Step 1: 구현** — 반투명 검정 박스 배경(rgba), 흰색 텍스트, 하단 배치. `make_textclip()`에서 `bg_color="rgba(0,0,0,200)"` + `color="#FFFFFF"` 사용. `render_subtitles()` 오버라이드하여 `with_position(("center", 0.85), relative=True)`.

- [ ] **Step 2: 커밋**

---

### Task 6: Bold Center 자막 스타일

**Files:**
- Create: `src/subtitles/bold_center.py`

- [ ] **Step 1: 구현** — 큰 흰색 볼드(font_size=120), 중앙 배치, 텍스트 그림자 효과(stroke_color="black", stroke_width=8).

- [ ] **Step 2: 커밋**

---

### Task 7: Highlight Word 자막 스타일

**Files:**
- Create: `src/subtitles/highlight_word.py`

- [ ] **Step 1: 구현** — `render_subtitles()` 전체 오버라이드. faster-whisper의 `word_timestamps=True`로 단어별 타이밍 추출. 각 시간대에서 현재 단어만 강조색(#FFFF00), 나머지 흰색으로 TextClip 렌더링. `generate_subtitles()`도 이 스타일 전용 버전 필요 → base에 `generate_word_level_subtitles()` 메서드 추가.

- [ ] **Step 2: 커밋**

---

### Task 8: Minimal Bottom 자막 스타일

**Files:**
- Create: `src/subtitles/minimal_bottom.py`

- [ ] **Step 1: 구현** — 작은 폰트(font_size=60), 흰색 90% 투명도, 하단 배치. 그라데이션 오버레이는 `compose_video()`에서 장르가 처리 (자막 스타일은 텍스트만 담당).

- [ ] **Step 2: 커밋**

---

## Chunk 3: Effects (4개)

### Task 9: Slideshow 효과

**Files:**
- Create: `src/effects/slideshow.py`

- [ ] **Step 1: 구현** — 현재 YouTube.py `combine()`의 이미지 루프 로직 추출. `ImageClip` → `with_duration` → `Crop` → `resized(1080, 1920)` → `concatenate_videoclips`.

- [ ] **Step 2: 커밋**

---

### Task 10: Ken Burns 효과

**Files:**
- Create: `src/effects/ken_burns.py`

- [ ] **Step 1: 구현** — 각 이미지 클립에 `Resize(new_size=lambda t: ...)` 적용. 줌인(1.0→1.15)과 줌아웃(1.15→1.0)을 이미지마다 번갈아 적용. 줌 후 중앙 Crop으로 해상도 유지.

- [ ] **Step 2: 커밋**

---

### Task 11: Fade Transition 효과

**Files:**
- Create: `src/effects/fade_transition.py`

- [ ] **Step 1: 구현** — `concatenate_videoclips` 대신 각 클립에 `CrossFadeIn(0.5)` + `CrossFadeOut(0.5)` 적용 후 `CompositeVideoClip`으로 시간 오프셋 배치. 클립 간 0.5초 오버랩.

- [ ] **Step 2: 커밋**

---

### Task 12: B-Roll 효과

**Files:**
- Create: `src/effects/broll.py`
- Create: `src/video_provider.py` (Pexels API 래퍼)
- Modify: `src/config.py` (pexels_api_key getter 추가)
- Modify: `config.example.json` (pexels_api_key 키 추가)

- [ ] **Step 1: `src/video_provider.py` 구현** — Pexels Video API 래퍼. `search_videos(query, orientation="portrait", min_duration=5, max_duration=15)` → 비디오 URL 리스트. `download_video(url, output_path)` → 로컬 경로.

- [ ] **Step 2: `src/effects/broll.py` 구현** — 이미지 프롬프트를 검색어로 변환 → Pexels 검색 → 다운로드 → `VideoFileClip` → Crop(9:16) → 클립 연결. 이미지 대신 비디오를 배경으로 사용.

- [ ] **Step 3: config 수정** — `get_pexels_api_key()` 추가, `config.example.json`에 `"pexels_api_key": ""` 추가.

- [ ] **Step 4: 커밋**

---

## Chunk 4: Narration 장르 (기존 파이프라인 이전)

### Task 13: Narration 장르 구현 + YouTube.py 리팩토링

**Files:**
- Create: `src/genres/narration.py`
- Modify: `src/classes/YouTube.py`

- [ ] **Step 1: `src/genres/narration.py` 구현** — 현재 YouTube.py의 `generate_topic()`, `generate_script()`, `generate_metadata()`, `generate_prompts()`, `generate_image()`, `generate_script_to_speech()`, `combine()` 로직을 BaseGenre 기반으로 이전. `generate_content()`는 기존 LLM 프롬프트 그대로 사용. `compose_video()`는 선택된 effect의 `apply()` 호출.

- [ ] **Step 2: YouTube.py 리팩토링** — `generate_video()`를 장르 디스패치로 교체:
```python
def generate_video(self, tts_instance, genre_name="narration",
                   effect_override=None, subtitle_override=None):
    genre_cls = get_genre(genre_name)
    genre = genre_cls(self._niche, self._language,
                      effect_override, subtitle_override)
    return genre.generate_video(tts_instance)
```
기존 `combine()`, `generate_topic()` 등 메서드 제거. `upload_video()`, `get_videos()`, `add_video()`는 유지.

- [ ] **Step 3: 기존 파이프라인이 narration 장르로 동일하게 동작하는지 검증**

Run: `python src/main.py` → 계정 선택 → Generate Short Locally (narration 장르 기본 실행)

- [ ] **Step 4: 커밋**

---

## Chunk 5: 텍스트 기반 장르 (5개, 이미지 불필요)

### Task 14: Quiz 장르

**Files:**
- Create: `src/genres/quiz.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 JSON 형식으로 퀴즈 생성 요청.
```json
{"question": "...", "options": ["A", "B", "C", "D"], "answer_index": 1, "explanation": "..."}
```

`compose_video()`: 4단계 프레임 합성.
1. 질문 화면 (3초) — `generate_text_frame()`으로 질문 + 선택지 렌더링
2. "Think..." 카운트다운 (3초) — 숫자 3→2→1 프레임
3. 정답 공개 (3초) — 정답 선택지 강조 (초록색)
4. 해설 (나머지) — 해설 텍스트 + TTS

- [ ] **Step 2: 커밋**

---

### Task 15: Quote 장르

**Files:**
- Create: `src/genres/quote.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 니치 관련 명언 + 저자 요청.

`compose_video()`: 단일 프레임.
- 배경: 그라데이션 (Pillow로 생성)
- 큰 따옴표 + 명언 텍스트 + 저자명
- TTS로 명언 낭독
- 전체 길이 = TTS 길이

- [ ] **Step 2: 커밋**

---

### Task 16: Story Text 장르

**Files:**
- Create: `src/genres/story_text.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 짧은 이야기 (paragraphs 배열) 생성 요청.

`compose_video()`: 문단별 텍스트 카드.
- Reddit 스타일 다크 배경 + 텍스트
- 각 문단 = 하나의 TextClip (TTS 타이밍에 맞춰 표시)
- 스크롤 업 효과: `with_position(lambda t: ("center", start_y - scroll_speed * t))`

- [ ] **Step 2: 커밋**

---

### Task 17: Two Truths 장르

**Files:**
- Create: `src/genres/two_truths.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 3개 문장 + `lie_index` JSON 생성 요청.

`compose_video()`: 3단계.
1. 3개 문장 제시 (5초) — 번호 + 텍스트 카드
2. "어떤 게 거짓일까?" 카운트다운 (3초)
3. 거짓 공개 (나머지) — lie_index 문장 빨간색 취소선 + 해설 TTS

- [ ] **Step 2: 커밋**

---

### Task 18: Fortune 장르

**Files:**
- Create: `src/genres/fortune.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 카드 3장(이름 + 의미) + 종합 리딩 JSON 생성 요청.

`compose_video()`: 카드 뒤집기 연출.
- 카드 뒷면 (보라색 그라데이션) 표시 → 각 카드 순서대로 앞면 공개
- 카드 전환: `CrossFadeIn` 또는 단순 하드컷
- 마지막: 종합 리딩 텍스트 + TTS

- [ ] **Step 2: 커밋**

---

## Chunk 6: 이미지 기반 장르 (7개)

### Task 19: Countdown 장르

**Files:**
- Create: `src/genres/countdown.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 "Top N" 랭킹 리스트 (항목 + 설명 + 이미지 프롬프트) JSON 생성 요청.

`compose_video()`: 역순 카운트다운.
- 각 항목: 순위 번호 오버레이 + AI 이미지 + 항목 설명 TTS
- 번호 오버레이: Pillow로 원형 배지 렌더링 → `CompositeVideoClip`으로 이미지 위에 합성
- 효과: 기본 `ken_burns`

- [ ] **Step 2: 커밋**

---

### Task 20: Before/After 장르

**Files:**
- Create: `src/genres/before_after.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 주제 + before/after 이미지 프롬프트 2개 + 설명 요청.

`compose_video()`: 3단계.
1. "BEFORE" 라벨 + before 이미지 (TTS 전반)
2. 전환 효과 (기본 `fade_transition`)
3. "AFTER" 라벨 + after 이미지 (TTS 후반)

- [ ] **Step 2: 커밋**

---

### Task 21: Would You Rather 장르

**Files:**
- Create: `src/genres/would_you_rather.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 option_a + option_b + 이미지 프롬프트 2개 + 해설 요청.

`compose_video()`: 분할 화면.
- 상단 50%: 빨간 배경 + option_a 이미지 + 텍스트
- 하단 50%: 파란 배경 + option_b 이미지 + 텍스트
- 중앙: "VS" 배지
- TTS로 각 옵션 설명 → 마지막에 해설

- [ ] **Step 2: 커밋**

---

### Task 22: Step Tutorial 장르

**Files:**
- Create: `src/genres/step_tutorial.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 steps[] (단계별 제목 + 설명 + 이미지 프롬프트) JSON 요청.

`compose_video()`: 단계별 구성.
- 각 단계: 번호 배지 오버레이 + AI 이미지 + 단계 제목/설명 TTS
- 효과: 기본 `slideshow`
- 진행 바: 하단에 현재 단계 / 전체 단계 표시

- [ ] **Step 2: 커밋**

---

### Task 23: What If 장르

**Files:**
- Create: `src/genres/what_if.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 가상 시나리오 + 단계별 설명(explanations[]) + 이미지 프롬프트 요청.

`compose_video()`: narration과 유사하지만 "WHAT IF...?" 인트로 프레임 추가.
1. 인트로: "WHAT IF...?" 텍스트 + 시나리오 질문 (3초)
2. 설명: 단계별 이미지 + TTS (narration과 동일 흐름)
- 효과: 기본 `ken_burns`

- [ ] **Step 2: 커밋**

---

### Task 24: Wait For It 장르

**Files:**
- Create: `src/genres/wait_for_it.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 hint_text + reveal_text + 힌트 이미지 프롬프트 + 정답 이미지 프롬프트 요청.

`compose_video()`: 3단계.
1. 힌트 이미지 + 힌트 TTS + "WAIT FOR IT..." 오버레이
2. 카운트다운 (3→2→1) 텍스트 프레임
3. 정답 이미지 + 정답 TTS + 효과음 대신 BGM 볼륨 업

- [ ] **Step 2: 커밋**

---

### Task 25: Spot Difference 장르

**Files:**
- Create: `src/genres/spot_difference.py`

- [ ] **Step 1: 구현**

`generate_content()`: LLM에게 장면 설명 + differences[] (차이점 목록) 요청. 이미지 프롬프트 2개 생성 — 기본 장면 + 미세 변경 장면. (AI 이미지 제어 한계로 차이가 보장되지 않을 수 있음 → LLM이 차이점을 프롬프트에 명시적으로 포함)

`compose_video()`: 3단계.
1. 두 이미지 좌우 배치 (상단 60%) + "3개 찾아보세요!" 텍스트 (5초)
2. 카운트다운 (5초)
3. 정답 공개 — 차이점 위치에 빨간 원 오버레이 + TTS 설명

- [ ] **Step 2: 커밋**

---

## Chunk 7: Integration — 진입점 수정

### Task 26: main.py 장르 선택 메뉴 추가

**Files:**
- Modify: `src/main.py`
- Modify: `src/constants.py`

- [ ] **Step 1: constants.py에 장르 메뉴 추가**

기존 `YOUTUBE_OPTIONS`에 "Generate Short Locally" 대신 장르 선택 서브메뉴 진입 옵션.

- [ ] **Step 2: main.py 수정**

"Generate Short Locally" 선택 시:
1. 장르 목록 표시 (`list_genres()`)
2. 장르 선택
3. (선택적) 효과/자막 오버라이드 — 기본값 사용 or 변경
4. `youtube.generate_video(tts, genre_name=selected_genre, effect_override=..., subtitle_override=...)`

- [ ] **Step 3: 커밋**

---

### Task 27: cron.py 장르 파라미터 추가

**Files:**
- Modify: `src/cron.py`

- [ ] **Step 1: 수정** — CLI 인자에 장르 추가: `python src/cron.py <account_uuid> [model] [genre]`. 기본값 `narration`.

- [ ] **Step 2: main.py CRON 설정에서 장르 전달**

- [ ] **Step 3: 커밋**

---

### Task 28: config 확장 + README 갱신

**Files:**
- Modify: `config.example.json`
- Modify: `src/config.py`
- Modify: `README.md`

- [ ] **Step 1: config 확장** — `pexels_api_key` 추가. `get_pexels_api_key()` getter 추가.

- [ ] **Step 2: README.md 갱신** — 13개 장르 목록, 효과/자막 스타일 설명, Pexels API 키 설정 안내 추가.

- [ ] **Step 3: 커밋**

---

## 실행 순서 요약

```
Chunk 1 (Foundation)     → Task 1-3    : base 클래스 + registry
Chunk 2 (Subtitles)      → Task 4-8    : 자막 스타일 5개
Chunk 3 (Effects)        → Task 9-12   : 영상 효과 4개
Chunk 4 (Narration)      → Task 13     : 기존 파이프라인 이전 + YouTube.py 리팩토링
Chunk 5 (Text Genres)    → Task 14-18  : 텍스트 기반 장르 5개
Chunk 6 (Image Genres)   → Task 19-25  : 이미지 기반 장르 7개
Chunk 7 (Integration)    → Task 26-28  : 진입점 + config + 문서
```

### 병렬화 가능 구간

- Chunk 2 (Subtitles)와 Chunk 3 (Effects)는 서로 독립 → **병렬 실행 가능**
- Chunk 5 (Text Genres) 내 5개 장르는 서로 독립 → **병렬 실행 가능**
- Chunk 6 (Image Genres) 내 7개 장르는 서로 독립 → **병렬 실행 가능**
- Chunk 4는 Chunk 1-3 완료 후 진행
- Chunk 7은 모든 장르 완료 후 진행

### 신규 파일 총 28개

| 디렉토리 | 파일 수 |
|----------|--------|
| `src/genres/` | 15개 (`__init__` + `base` + 13 장르) |
| `src/effects/` | 6개 (`__init__` + `base` + 4 효과) |
| `src/subtitles/` | 7개 (`__init__` + `base` + 5 스타일) |
| `src/video_provider.py` | 1개 |
| **합계** | **29개** |
