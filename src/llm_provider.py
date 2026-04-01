import requests

from config import (
    get_llm_provider,
    get_ollama_base_url,
    get_ollama_model,
    get_openai_api_key,
    get_openai_base_url,
    get_openai_model,
)

_selected_model: str | None = None


def list_models() -> list[str]:
    provider = get_llm_provider()
    if provider == "openai":
        configured_model = get_openai_model().strip()
        return [configured_model] if configured_model else []
    if provider != "local_ollama":
        raise RuntimeError(f"Unsupported llm_provider: {provider}")

    response = requests.get(f"{get_ollama_base_url().rstrip('/')}/api/tags", timeout=10)
    response.raise_for_status()
    payload = response.json()
    return sorted(m.get("name", "") for m in payload.get("models", []) if m.get("name"))


def select_model(model: str) -> None:
    global _selected_model
    _selected_model = model


def get_active_model() -> str | None:
    return _selected_model


def _get_model_name(model_name: str | None) -> str:
    if model_name:
        return model_name
    if _selected_model:
        return _selected_model

    provider = get_llm_provider()
    if provider == "openai":
        configured_model = get_openai_model().strip()
        if configured_model:
            return configured_model
        raise RuntimeError(
            "No OpenAI model configured. Set openai_model or call select_model() first."
        )

    configured_model = get_ollama_model().strip()
    if configured_model:
        return configured_model
    raise RuntimeError(
        "No LLM model selected. Call select_model() first or configure a default model."
    )


def _generate_text_openai(prompt: str, model: str) -> str:
    api_key = get_openai_api_key().strip()
    if not api_key:
        raise RuntimeError(
            "OpenAI API key is missing. Set openai_api_key or OPENAI_API_KEY."
        )

    response = requests.post(
        f"{get_openai_base_url().rstrip('/')}/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": prompt,
            "store": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()

    output_text = str(payload.get("output_text", "")).strip()
    if output_text:
        return output_text

    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                return str(text).strip()

    raise RuntimeError("OpenAI response did not include output text.")


def _generate_text_ollama(prompt: str, model: str) -> str:
    response = requests.post(
        f"{get_ollama_base_url().rstrip('/')}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload["message"]["content"]).strip()


def generate_text(prompt: str, model_name: str = None) -> str:
    model = _get_model_name(model_name)
    provider = get_llm_provider()

    if provider == "openai":
        return _generate_text_openai(prompt, model)
    if provider == "local_ollama":
        return _generate_text_ollama(prompt, model)

    raise RuntimeError(f"Unsupported llm_provider: {provider}")
