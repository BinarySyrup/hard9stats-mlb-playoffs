from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.models.contracts import ConfidencePayload, IngestionEnvelope
from app.services.agent_client import OllamaAgentClient
from app.services.storage import build_ingestion_filename, save_json_payload


def _only_fields(value: Any, fields: tuple[str, ...]) -> Any:
    if not isinstance(value, dict):
        return value
    return {field: value[field] for field in fields if field in value}


def _normalize_scores_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _only_fields(payload, ("games", "warnings", "confidence"))
    games = normalized.get("games")
    if not isinstance(games, list):
        return normalized

    normalized_games = []
    for game in games:
        game = _only_fields(
            game,
            ("date", "status", "away_team", "home_team", "series", "series_id"),
        )
        if not isinstance(game, dict):
            normalized_games.append(game)
            continue

        for team_key in ("away_team", "home_team"):
            if team_key in game:
                game[team_key] = _only_fields(game[team_key], ("name", "runs"))

        if isinstance(game.get("series"), dict):
            game["series"] = _only_fields(game["series"], ("league", "game", "summary"))
        normalized_games.append(game)

    normalized["games"] = normalized_games
    return normalized


class IngestionService:
    def __init__(self) -> None:
        self._agent_client = OllamaAgentClient()

    async def ingest_screenshot(
        self,
        source_image_name: str,
        image_bytes: bytes,
        content_type: str,
        extraction_type: str,
        series_type: str,
    ) -> tuple[IngestionEnvelope, list[str]]:
        request_id = uuid4()
        created_at = datetime.now(timezone.utc)

        context = ""
        if extraction_type == "odds":
            context = (
                "Trusted ingestion metadata (use these values exactly):\n"
                f"request_id: {request_id}\n"
                f"created_at: {created_at.isoformat()}\n"
                f"source_image_name: {source_image_name}"
            )

        parsed_output = await self._agent_client.parse_structured_screenshot(
            image_bytes=image_bytes,
            content_type=content_type,
            extraction_type=extraction_type,
            context=context,
        )
        if extraction_type == "odds":
            data = parsed_output.get("games", parsed_output.get("data", {}))
            output_categories = ["odds"]
        elif extraction_type == "scores":
            parsed_output = _normalize_scores_payload(parsed_output)
            data = {"games": parsed_output["games"]}
            output_categories = ["scores"]
        else:
            data = {"games": parsed_output["games"]}
            output_categories = ["schedules"]
        output_dirs = [
            Path("data/ingested") / series_type / category
            for category in output_categories
        ]

        warnings = parsed_output.get("warnings", [])
        confidence_raw: Any = parsed_output.get("confidence", {})

        confidence = ConfidencePayload()
        if isinstance(confidence_raw, dict):
            confidence = ConfidencePayload.model_validate(confidence_raw)

        if not isinstance(data, dict):
            data = {"value": data}
        if not isinstance(warnings, list):
            warnings = ["Agent returned non-list warnings payload."]

        envelope = IngestionEnvelope(
            request_id=request_id,
            created_at=created_at,
            source_image_name=source_image_name,
            data=data,
            warnings=[str(item) for item in warnings],
            confidence=confidence,
            agent_metadata={
                "model": settings.ollama_model,
                "api_url": settings.ollama_base_url,
                "extraction_type": extraction_type,
                "series_type": series_type,
            },
        )

        filename = build_ingestion_filename(created_at=created_at, request_id=request_id)
        saved_paths = []
        for output_dir in output_dirs:
            save_path = save_json_payload(
                payload=parsed_output,
                output_dir=output_dir,
                filename=filename,
            )
            saved_paths.append(str(save_path).replace("\\", "/"))

        return envelope, saved_paths
