"""Append-only local JSONL audit events without requirement text or credentials."""
import json
from datetime import datetime, timezone
from pathlib import Path

def record(path: Path, *, run_id: str, event: str, status: str, details: dict | None = None) -> None:
    allowed = {"run_started", "run_finished", "publish_attempt", "publish_result", "repair_validated"}
    if event not in allowed:
        raise ValueError("Unsupported audit event")
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "run_id": run_id,
             "event": event, "status": status}
    if details:
        # Only numeric metrics and known categorical fields; never log arbitrary prompts or tokens.
        entry["details"] = {key: value for key, value in details.items()
                            if key in {"case_count", "repair_attempts", "result", "category"}
                            and isinstance(value, (int, float, bool, str)) and len(str(value)) <= 80}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, sort_keys=True) + "\n")
