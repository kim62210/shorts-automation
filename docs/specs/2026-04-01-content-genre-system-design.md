# Content Genre System Design

## 개요

Shorts Automation의 단일 포맷 파이프라인을 **13개 콘텐츠 장르**를 지원하는 확장 가능한 구조로 리팩토링한다.

## 결정 사항

| 항목 | 결정 |
|------|------|
| 장르 수 | 13개 (기존 1개 + 신규 12개) |
| 구조 | 장르별 클래스 분리 (각 장르 = 독립 파일) |
| 장르 선택 | 실행 시 메뉴에서 선택 |
| 영상 효과 | 장르 기본값 + 오버라이드 가능 |
| 자막 스타일 | 5개 프리셋, 장르 기본값 + 오버라이드 가능 |

## 13개 콘텐츠 장르

### 이미지 기반 (AI 이미지 필요)

| # | 장르 | ID | LLM 출력 | 이미지 수 |
|---|------|----|----------|----------|
| 1 | 내레이션 + 이미지 | `narration` | script (문단) | 3-8장 |
| 2 | 카운트다운 / 랭킹 | `countdown` | ranked_items[] | 항목당 1장 |
| 3 | Before / After | `before_after` | description + before/after prompts | 2장 |
| 4 | 이것 vs 저것 | `would_you_rather` | option_a + option_b | 2장 |
| 5 | 스텝 튜토리얼 | `step_tutorial` | steps[] | 단계당 1장 |
| 6 | What If | `what_if` | scenario + explanations[] | 3-5장 |
| 7 | Wait For It | `wait_for_it` | hint + reveal | 2장 (힌트+정답) |

### 텍스트/템플릿 기반 (이미지 불필요)

| # | 장르 | ID | LLM 출력 | 이미지 |
|---|------|----|----------|--------|
| 8 | 퀴즈 / 트리비아 | `quiz` | question + options + answer | 없음 |
| 9 | 명언 / 동기부여 | `quote` | quote + author | 없음 |
| 10 | 텍스트 스토리 | `story_text` | paragraphs[] | 없음 |
| 11 | 두 개의 진실, 하나의 거짓 | `two_truths` | statements[] + lie_index | 없음 |
| 12 | 운세 / 타로 / MBTI | `fortune` | cards[] + reading | 없음 |

### 특수 (이미지 정밀 제어)

| # | 장르 | ID | LLM 출력 | 이미지 |
|---|------|----|----------|--------|
| 13 | 틀린그림찾기 | `spot_difference` | differences[] | 2장 (유사) |

## 영상 효과 (Visual Effects)

4개 효과. 장르마다 기본값이 있고, 실행 시 오버라이드 가능.

| 효과 | ID | 설명 | MoviePy API |
|------|----|------|-------------|
| 슬라이드쇼 | `slideshow` | 이미지 순차 배치 (하드컷) | `concatenate_videoclips` |
| Ken Burns | `ken_burns` | 이미지에 느린 줌/팬 | `Resize(lambda t)` + `Crop` |
| 페이드 전환 | `fade_transition` | 이미지 간 CrossFade | `CrossFadeIn` + `CompositeVideoClip` |
| B-Roll | `broll` | Pexels 스톡 비디오 배경 | `VideoFileClip` + `Crop` |

### 장르별 기본 효과

| 장르 | 기본 효과 | 사용 가능 효과 |
|------|----------|---------------|
| narration | slideshow | 전부 |
| countdown | ken_burns | slideshow, fade_transition |
| before_after | fade_transition | slideshow |
| would_you_rather | — (자체 레이아웃) | — |
| step_tutorial | slideshow | ken_burns, fade_transition |
| what_if | ken_burns | slideshow, fade_transition, broll |
| wait_for_it | fade_transition | slideshow |
| quiz | — (텍스트 렌더링) | — |
| quote | — (텍스트 렌더링) | — |
| story_text | — (텍스트 렌더링) | — |
| two_truths | — (텍스트 렌더링) | — |
| fortune | — (텍스트 렌더링) | — |
| spot_difference | — (자체 레이아웃) | — |

## 자막 스타일

5개 프리셋. 장르마다 기본값이 있고, 오버라이드 가능.

| 스타일 | ID | 설명 | 특이사항 |
|--------|----|------|----------|
| Classic | `classic` | 노란색 + 검정 테두리 | 현재 구현됨 |
| Modern Box | `modern_box` | 하단 반투명 박스 + 흰색 | — |
| Bold Center | `bold_center` | 큰 볼드 중앙 배치 | — |
| Highlight Word | `highlight_word` | 현재 단어 색상 강조 | Whisper word-level timestamp 필요 |
| Minimal Bottom | `minimal_bottom` | 하단 그라데이션 + 작은 텍스트 | — |

### 장르별 기본 자막 스타일

| 장르 | 기본 자막 |
|------|----------|
| narration | classic |
| countdown | modern_box |
| before_after | classic |
| would_you_rather | bold_center |
| step_tutorial | modern_box |
| what_if | classic |
| wait_for_it | bold_center |
| quiz | bold_center |
| quote | minimal_bottom |
| story_text | minimal_bottom |
| two_truths | bold_center |
| fortune | classic |
| spot_difference | bold_center |

## 아키텍처

### 디렉토리 구조

```
src/
├── genres/
│   ├── __init__.py          # GenreRegistry
│   ├── base.py              # BaseGenre 추상 클래스
│   ├── narration.py
│   ├── quiz.py
│   ├── countdown.py
│   ├── quote.py
│   ├── would_you_rather.py
│   ├── story_text.py
│   ├── before_after.py
│   ├── spot_difference.py
│   ├── wait_for_it.py
│   ├── two_truths.py
│   ├── step_tutorial.py
│   ├── fortune.py
│   └── what_if.py
│
├── effects/
│   ├── __init__.py          # EffectRegistry
│   ├── base.py              # BaseEffect
│   ├── slideshow.py
│   ├── ken_burns.py
│   ├── fade_transition.py
│   └── broll.py
│
├── subtitles/
│   ├── __init__.py          # SubtitleStyleRegistry
│   ├── base.py              # BaseSubtitleStyle
│   ├── classic.py
│   ├── modern_box.py
│   ├── bold_center.py
│   ├── highlight_word.py
│   └── minimal_bottom.py
│
├── classes/
│   ├── YouTube.py           # 장르 디스패치 + 업로드
│   └── Tts.py
│
├── main.py                  # 장르 선택 메뉴 추가
├── cron.py
├── config.py
├── llm_provider.py
├── cache.py
├── status.py
├── constants.py
└── utils.py
```

### BaseGenre 인터페이스

```python
class BaseGenre:
    name: str                      # "quiz"
    display_name: str              # "퀴즈 / 트리비아"
    default_effect: str | None     # "slideshow" or None (텍스트 장르)
    default_subtitle_style: str    # "bold_center"
    needs_images: bool             # False

    def __init__(self, niche, language, effect_override=None, subtitle_override=None):
        ...

    # 장르가 반드시 구현
    def generate_content(self) -> dict:
        """LLM으로 콘텐츠 생성. 장르별 구조화된 dict 반환."""
        raise NotImplementedError

    def compose_video(self, tts_path, content, images=None) -> str:
        """영상 합성 → MP4 경로 반환."""
        raise NotImplementedError

    # 공통 메서드 (base 제공)
    def generate_tts(self, text) -> str: ...
    def generate_subtitles(self, audio_path) -> str: ...
    def apply_subtitle_style(self, video_clip, srt_path) -> VideoClip: ...
    def mix_audio(self, tts_clip, bgm_path=None) -> AudioClip: ...
    def generate_image(self, prompt) -> str: ...
    def generate_text_frame(self, text, style_config) -> ImageClip: ...

    # 마스터 오케스트레이터
    def generate_video(self, tts_instance) -> str:
        content = self.generate_content()
        tts_path = self.generate_tts(content["script"])
        images = [self.generate_image(p) for p in content.get("image_prompts", [])]
        return self.compose_video(tts_path, content, images)
```

### GenreRegistry

```python
# src/genres/__init__.py
GENRES = {}

def register(genre_cls):
    GENRES[genre_cls.name] = genre_cls
    return genre_cls

def get_genre(name): return GENRES[name]
def list_genres(): return list(GENRES.values())
```

### 데이터 흐름

```
main.py
  ├─ 계정 선택
  ├─ 장르 선택 (메뉴)
  ├─ (선택적) 효과/자막 오버라이드
  └─ YouTube.generate_video(genre, tts)
       └─ genre.generate_video(tts)
            ├─ genre.generate_content()     # LLM
            ├─ genre.generate_tts()         # TTS
            ├─ genre.generate_image() × N   # 이미지 (필요 시)
            └─ genre.compose_video()        # 영상 합성
                 ├─ effect.apply()          # 효과 적용
                 ├─ subtitle_style.render()  # 자막 렌더링
                 └─ mix_audio()             # 오디오 믹싱
```

## B-Roll 효과 외부 의존성

B-Roll 효과만 외부 API가 필요하다.

| API | 용도 | 무료 한도 | config 키 |
|-----|------|----------|-----------|
| Pexels Video API | 스톡 비디오 검색/다운로드 | 20,000 req/월 | `pexels_api_key` |

## Highlight Word 자막 의존성

faster-whisper의 word-level timestamp 기능 활용.

```python
segments, _ = model.transcribe(audio, word_timestamps=True)
for segment in segments:
    for word in segment.words:
        word.start, word.end, word.word  # 단어별 타이밍
```

기존 `faster-whisper` 패키지로 가능. 추가 의존성 없음.

## 변경 범위

### 수정 파일
- `src/main.py` — 장르 선택 메뉴 추가
- `src/classes/YouTube.py` — combine() 로직 제거, 장르 디스패치로 교체
- `src/cron.py` — 장르 파라미터 추가
- `src/config.py` — pexels_api_key getter 추가
- `config.example.json` — pexels_api_key 키 추가

### 신규 파일
- `src/genres/` — 15개 파일 (base + __init__ + 13 장르)
- `src/effects/` — 6개 파일 (base + __init__ + 4 효과)
- `src/subtitles/` — 7개 파일 (base + __init__ + 5 스타일)

### 미변경
- `src/llm_provider.py`
- `src/cache.py`
- `src/status.py`
- `src/utils.py`
- `src/classes/Tts.py`
