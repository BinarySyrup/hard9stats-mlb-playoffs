import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


def build_ingestion_filename(created_at: datetime, request_id: UUID) -> str:
    timestamp = created_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{request_id}.json"


def save_json_payload(payload: dict, output_dir: Path, filename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return output_path
