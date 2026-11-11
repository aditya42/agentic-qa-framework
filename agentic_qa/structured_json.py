"""Validate JSON text returned by a model without relying on tool calling.

Intentionally strict: malformed JSON is rejected rather than guessing or
modifying expected results. The model may wrap the object in a JSON code fence.
"""
import json
from pydantic import BaseModel, ValidationError

def parse_model_json(content: str, schema: type[BaseModel]) -> BaseModel:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Model returned an empty JSON response")
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) < 3 or lines[0].strip().lower() not in ("```json", "```") or lines[-1].strip() != "```":
            raise ValueError("Malformed JSON code fence")
        text = "\n".join(lines[1:-1]).strip()
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Model returned invalid JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("Model JSON must be an object")
    if set(document) == {"name", "arguments"} and isinstance(document.get("arguments"), dict):
        document = document["arguments"]
    try:
        return schema.model_validate(document)
    except ValidationError as exc:
        raise ValueError("Model JSON did not match the required schema") from exc
