# Shorts Automation

YouTube Shorts 자동 생성 CLI 도구. [MoneyPrinterV2](https://github.com/kim62210/MoneyPrinterV2)에서 YouTube Shorts 파이프라인만 추출한 독립 프로젝트.

## 기능

LLM 스크립트 생성 → AI 이미지 생성 → TTS 음성 합성 → 자막 생성 → MoviePy 비디오 합성을 자동으로 수행하여 YouTube Shorts 영상을 로컬에 생성한다.

### 파이프라인 7단계

1. **Topic** — 니치 기반 영상 아이디어 생성 (LLM)
2. **Script** — 아이디어 기반 스크립트 작성 (LLM)
3. **Metadata** — 제목/설명 생성 (LLM)
4. **Image Prompts** — 이미지 생성 프롬프트 추출 (LLM)
5. **Images** — AI 이미지 생성 (Gemini API)
6. **TTS** — 스크립트 음성 변환 (KittenTTS)
7. **Combine** — 이미지 + TTS + 자막 + BGM → MP4 합성 (MoviePy)

## 사전 요구사항

- Python 3.12+
- ImageMagick (자막 렌더링용)
- Firefox + 프로필 (업로드 자동화 시에만 필요)

## 설치

```bash
# 자동 셋업 (venv 생성 + 의존성 설치 + ImageMagick 감지)
bash scripts/setup.sh

# 또는 수동 설치
cp config.example.json config.json   # 설정값 채우기
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 설정

`config.json`의 주요 설정:

| 키 | 설명 | 기본값 |
|---|---|---|
| `llm_provider` | LLM 공급자 (`openai` / `local_ollama`) | `openai` |
| `openai_api_key` | OpenAI API 키 (env: `OPENAI_API_KEY`) | — |
| `nanobanana2_api_key` | Gemini 이미지 API 키 (env: `GEMINI_API_KEY`) | — |
| `imagemagick_path` | ImageMagick 실행 경로 | — |
| `stt_provider` | 자막 생성 (`local_whisper` / `third_party_assemblyai`) | `local_whisper` |
| `tts_voice` | KittenTTS 음성 | `Jasper` |
| `script_sentence_length` | 스크립트 문장 수 | `4` |

## 실행

```bash
source venv/bin/activate

# 대화형 메뉴
python src/main.py

# CRON 스케줄러 (headless)
python src/cron.py <account_uuid> [model_name]

# Preflight 체크
python scripts/preflight.py
```

## 프로젝트 구조

```
shorts-automation/
├── config.example.json       # 설정 템플릿
├── requirements.txt          # Python 의존성
├── fonts/bold_font.ttf       # 자막 폰트
├── Songs/                    # 배경음악 (자동 다운로드 또는 수동 배치)
├── scripts/
│   ├── setup.sh              # 자동 셋업
│   └── preflight.py          # 서비스 가용성 검증
├── src/
│   ├── main.py               # 대화형 진입점
│   ├── cron.py               # 스케줄러 진입점
│   ├── config.py             # 설정 관리
│   ├── llm_provider.py       # LLM 추상화 (OpenAI/Ollama)
│   ├── cache.py              # YouTube 계정/영상 캐시
│   ├── status.py             # CLI 출력 유틸리티
│   ├── constants.py          # YouTube Studio 셀렉터
│   ├── utils.py              # 유틸리티 (BGM, 임시파일 관리)
│   └── classes/
│       ├── YouTube.py        # 핵심 파이프라인
│       └── Tts.py            # KittenTTS 래퍼
└── .mp/                      # 캐시 + 임시 파일 (자동 생성)
```

## 데이터 저장

- `.mp/youtube.json` — 계정 정보 및 영상 메타데이터 캐시
- `.mp/*.png|wav|srt|mp4` — 파이프라인 중간 산출물 (실행 시작 시 자동 정리)

## 원본 프로젝트

MoneyPrinterV2에서 YouTube Shorts 파이프라인만 추출. Twitter Bot, Affiliate Marketing, Outreach 기능은 제외.
