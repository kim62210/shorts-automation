# Shorts Automation

YouTube Shorts 자동 생성 CLI 도구. 13개 콘텐츠 장르 + 4개 영상 효과 + 5개 자막 스타일을 지원.

## 기능

LLM 콘텐츠 생성 → (선택적) AI 이미지 → TTS 음성 합성 → 자막 → MoviePy 비디오 합성을 자동으로 수행.

### 13개 콘텐츠 장르

| 장르 | 설명 | 이미지 |
|------|------|--------|
| 🎙️ 내레이션 + 이미지 | 스크립트 + AI 이미지 슬라이드쇼 | 필요 |
| 🧠 퀴즈 / 트리비아 | 질문 → 카운트다운 → 정답 공개 | 불필요 |
| 🏆 카운트다운 / 랭킹 | Top N 역순 카운트다운 | 필요 |
| 💬 명언 / 동기부여 | 감성 배경 + 큰 텍스트 | 불필요 |
| ⚡ 이것 vs 저것 | 분할 화면 비교 | 필요 |
| 📖 텍스트 스토리 | Reddit 스타일 텍스트 카드 | 불필요 |
| 🔄 Before / After | 전후 비교 | 필요 |
| 🔍 틀린그림찾기 | 좌우 이미지 비교 + 정답 | 필요 |
| ⏳ Wait For It | 힌트 → 카운트다운 → 반전 | 필요 |
| 🤥 두 진실 하나 거짓 | 3문장 → 거짓 공개 | 불필요 |
| 📋 스텝 튜토리얼 | 단계별 이미지 + 진행 바 | 필요 |
| 🔮 운세 / 타로 / MBTI | 카드 공개 연출 | 불필요 |
| 🌍 What If | 가상 시나리오 + 시각 설명 | 필요 |

### 4개 영상 효과

| 효과 | 설명 |
|------|------|
| Slideshow | 이미지 순차 배치 (기본) |
| Ken Burns | 느린 줌인/줌아웃 + 팬 |
| Fade Transition | 이미지 간 CrossFade 전환 |
| B-Roll | Pexels 스톡 비디오 배경 |

### 5개 자막 스타일

| 스타일 | 설명 |
|--------|------|
| Classic | 노란색 + 검정 테두리 |
| Modern Box | 반투명 박스 + 흰색 텍스트 |
| Bold Center | 큰 볼드 중앙 배치 |
| Highlight Word | 현재 단어 강조 (MrBeast 스타일) |
| Minimal Bottom | 하단 미니멀 |

## 사전 요구사항

- Python 3.12+
- ImageMagick (자막 렌더링용)

## 설치

```bash
bash scripts/setup.sh
```

## 설정

`config.json`의 주요 설정:

| 키 | 설명 | 기본값 |
|---|---|---|
| `llm_provider` | LLM 공급자 (`openai` / `local_ollama`) | `openai` |
| `openai_api_key` | OpenAI API 키 (env: `OPENAI_API_KEY`) | — |
| `nanobanana2_api_key` | Gemini 이미지 API 키 (env: `GEMINI_API_KEY`) | — |
| `pexels_api_key` | Pexels Video API 키 (B-Roll용, env: `PEXELS_API_KEY`) | — |
| `imagemagick_path` | ImageMagick 실행 경로 | — |
| `stt_provider` | 자막 (`local_whisper` / `third_party_assemblyai`) | `local_whisper` |
| `tts_voice` | KittenTTS 음성 | `Jasper` |

## 실행

```bash
source venv/bin/activate
python src/main.py
```

실행 흐름: 계정 선택 → 장르 선택 → (선택적) 효과/자막 커스터마이즈 → 영상 생성.

```bash
# CRON 스케줄러
python src/cron.py <account_uuid> [model] [genre]

# Preflight 체크
python scripts/preflight.py
```

## 프로젝트 구조

```
shorts-automation/
├── config.example.json
├── requirements.txt
├── fonts/bold_font.ttf
├── Songs/
├── scripts/
│   ├── setup.sh
│   └── preflight.py
├── src/
│   ├── main.py
│   ├── cron.py
│   ├── config.py
│   ├── llm_provider.py
│   ├── cache.py
│   ├── status.py
│   ├── constants.py
│   ├── utils.py
│   ├── video_provider.py       # Pexels API 래퍼
│   ├── classes/
│   │   ├── YouTube.py          # 장르 디스패치 + 업로드
│   │   └── Tts.py
│   ├── genres/                  # 13개 콘텐츠 장르
│   │   ├── base.py
│   │   ├── narration.py
│   │   ├── quiz.py
│   │   ├── countdown.py
│   │   ├── quote.py
│   │   ├── would_you_rather.py
│   │   ├── story_text.py
│   │   ├── before_after.py
│   │   ├── spot_difference.py
│   │   ├── wait_for_it.py
│   │   ├── two_truths.py
│   │   ├── step_tutorial.py
│   │   ├── fortune.py
│   │   └── what_if.py
│   ├── effects/                 # 4개 영상 효과
│   │   ├── base.py
│   │   ├── slideshow.py
│   │   ├── ken_burns.py
│   │   ├── fade_transition.py
│   │   └── broll.py
│   └── subtitles/               # 5개 자막 스타일
│       ├── base.py
│       ├── classic.py
│       ├── modern_box.py
│       ├── bold_center.py
│       ├── highlight_word.py
│       └── minimal_bottom.py
└── .mp/
```

## 원본 프로젝트

[MoneyPrinterV2](https://github.com/kim62210/MoneyPrinterV2)에서 YouTube Shorts 파이프라인을 추출하여 13개 장르 시스템으로 확장.
