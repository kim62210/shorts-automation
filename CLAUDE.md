# CLAUDE.md

## Project Overview

Shorts Automation은 YouTube Shorts 자동 생성 CLI 도구로, MoneyPrinterV2에서 YouTube Shorts 파이프라인만 추출한 독립 프로젝트이다.

7단계 파이프라인: LLM 스크립트 → AI 이미지 → TTS → 자막 → MoviePy 비디오 합성.

웹 UI, REST API, 테스트 스위트, CI, 린팅 설정 없음.

## Running the Application

```bash
bash scripts/setup.sh
source venv/bin/activate
python src/main.py
```

프로젝트 루트에서 실행해야 한다. `src/` 내부 모듈은 bare import (`from config import ...`) 사용.

## Architecture

### Entry Points
- `src/main.py` — 대화형 메뉴
- `src/cron.py` — 스케줄러: `python src/cron.py <account_uuid> [model]`

### Key Modules
- **`src/classes/YouTube.py`** — 핵심 파이프라인 (generate_video + upload_video)
- **`src/classes/Tts.py`** — KittenTTS 래퍼
- **`src/config.py`** — 설정 getter (매 호출마다 config.json 재읽기)
- **`src/llm_provider.py`** — OpenAI/Ollama 텍스트 생성 추상화
- **`src/cache.py`** — YouTube 계정/영상 캐시 (`.mp/youtube.json`)
- **`src/utils.py`** — BGM 관리, 임시파일 정리

### External Dependencies
- **LLM**: OpenAI API 또는 Ollama (로컬)
- **이미지 생성**: Gemini API (Nano Banana 2)
- **TTS**: KittenTTS
- **STT**: faster-whisper (로컬) 또는 AssemblyAI
- **비디오 합성**: MoviePy + ImageMagick

## Configuration

`config.json` (프로젝트 루트). `config.example.json` 참조.

## Contributing

`main` 브랜치 대상 PR. 기능/수정 단위로 분리.
