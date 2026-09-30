from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.config import get_ingested_output_path, settings
from app.models.contracts import ConfidencePayload, IngestionEnvelope
from app.services.agent_client import AzureFoundryAgentClient
from app.services.storage import build_ingestion_filename, save_json_payload


class IngestionService:
    def __init__(self) -> None:
        self._agent_client = AzureFoundryAgentClient()

    async def ingest_screenshot(self, source_image_name: str, image_bytes: bytes, content_type: str) -> tuple[IngestionEnvelope, str]:
        request_id = uuid4()
        created_at = datetime.now(timezone.utc)

        parsed_output = await self._agent_client.parse_screenshot(
            image_bytes=image_bytes,
            content_type=content_type,
        )

        data = parsed_output.get("data", {})
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
                "model": settings.azure_agent_model,
                "api_url": settings.azure_agent_api_url,
            },
        )

        output_dir = get_ingested_output_path()
        filename = build_ingestion_filename(created_at=created_at, request_id=request_id)
        save_path = save_json_payload(
            payload=envelope.model_dump(mode="json"),
            output_dir=output_dir,
            filename=filename,
        )

        return envelope, str(save_path)
