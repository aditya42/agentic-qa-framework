"""Check Groq model access before running the full agent graph."""
import os
import requests

DEFAULT_MODEL = "openai/gpt-oss-120b"

def verify_model() -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Set it as a GitHub Actions environment secret.")
    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip()
    if not model:
        raise RuntimeError("GROQ_MODEL must not be empty")
    try:
        response = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        response.raise_for_status()
        supported = {item["id"] for item in response.json().get("data", [])}
    except requests.RequestException as exc:
        raise RuntimeError(
            "Could not retrieve Groq model permissions. Check GROQ_API_KEY and API connectivity."
        ) from exc
    if model not in supported:
        raise RuntimeError(
            f"Groq model {model!r} is not available to this API key. "
            "Choose an ID from your Groq models page or the GET /models API."
        )
    return model
