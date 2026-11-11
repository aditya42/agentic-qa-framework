"""Parse and validate model-generated JSON without Groq tool calling.

The model may include a single JSON code fence; reject surrounding prose, Python
dict literals, unknown fields, and malformed or incomplete JSON. Never execute it.
"""
import json
from pydantic import BaseModel, ValidationError

def parse_model_json(content: str, schema: type[BaseModel]) -> BaseModel:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Model returned empty JSON")
    payload = content.strip()
    if payload.startswith("```"):
        lines = payload.splitlines()
        if len(lines) < 3 or lines[0].strip().lower() not in {"```json", "```"} or lines[-1].strip() != "```":
            raise ValueError("Malformed model JSON fence")
        payload = "\n".join(lines[1:-1]).strip()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Model returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("Model JSON root must be an object")
    if set(data) != set(schema.model_fields):
        # Diagnosis.revised_code may be omitted; allow optional fields through Pydantic.
        required = {k for k, field in schema.model_fields.items() if field.is_required()}
        if not required.issubset(data) or not set(data).issubset(schema.model_fields):
            raise ValueError("Model JSON fields do not match the expected schema")
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        raise ValueError("Model JSON did not match the schema") from exc
