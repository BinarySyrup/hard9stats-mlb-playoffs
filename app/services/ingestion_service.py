from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.models.contracts import ConfidencePayload, IngestionEnvelope
from app.services.agent_client import OllamaAgentClient
from app.services.storage import build_ingestion_filename, save_json_payload


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
            parsed_output["request_id"] = str(request_id)
            parsed_output["created_at"] = created_at.isoformat()
            parsed_output["source_image_name"] = source_image_name
            parsed_output["agent_metadata"]["migrated_from_legacy_schema"] = True
            data = parsed_output["data"]
            output_categories = ["odds"]
        else:
            parsed_output["agent_metadata"]["migrated_from_legacy_schema"] = True
            data = {"date": parsed_output["date"], "games": parsed_output["games"]}
            output_categories = ["scores", "schedules"]
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
