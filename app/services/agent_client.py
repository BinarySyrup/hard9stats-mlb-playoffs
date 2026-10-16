import base64
import json
from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_llm_prompt_path, settings
from app.models.contracts import OddsExtraction, ScoresExtraction, SchedulesExtraction


class AgentClientError(Exception):
    pass


class OllamaAgentClient:
    _structured_extractions = {
        "odds": ("mlb-data-ingestion-odds.txt", OddsExtraction),
        "scores": ("mlb-data-ingestion-scores.txt", ScoresExtraction),
        "schedules": ("mlb-data-ingestion-schedules.txt", SchedulesExtraction),
    }

    def __init__(self) -> None:
        self._base_url = settings.ollama_base_url.strip().rstrip("/")
        if not self._base_url:
            raise AgentClientError("Missing OLLAMA_BASE_URL in environment configuration.")
        if not settings.ollama_model.strip():
            raise AgentClientError("Missing OLLAMA_MODEL in environment configuration.")

    async def parse_structured_screenshot(
        self,
        image_bytes: bytes,
        content_type: str,
        extraction_type: str,
        context: str = "",
    ) -> dict[str, Any]:
        extraction = self._structured_extractions.get(extraction_type)
        if extraction is None:
            raise AgentClientError(f"Unsupported screenshot extraction type: {extraction_type}.")

        filename, response_model = extraction
        prompt_path = get_llm_prompt_path(filename)
        try:
            prompt = prompt_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise AgentClientError(f"Unable to read Ollama prompt file: {prompt_path}.") from exc

        if context:
            prompt = f"{prompt}\n\n{context}"

        return await self._parse_image(
            image_bytes=image_bytes,
            prompt=prompt,
            response_model=response_model,
        )

    async def _parse_image(
        self,
        image_bytes: bytes,
        prompt: str,
        response_model: type[BaseModel],
    ) -> dict[str, Any]:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        schema = response_model.model_json_schema()
        prompt = f"{prompt}\n\nReturn JSON matching this schema:\n{json.dumps(schema, ensure_ascii=False)}"
        request_payload: dict[str, Any] = {
            "model": settings.ollama_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64],
                }
            ],
            "format": schema,
            "stream": False,
            "options": {"temperature": 0},
        }

        async with httpx.AsyncClient(timeout=settings.agent_timeout_seconds) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json=request_payload,
                )
                response.raise_for_status()
            except httpx.TimeoutException as exc:
                raise AgentClientError("Ollama inference request timed out.") from exc
            except httpx.HTTPStatusError as exc:
                raise AgentClientError(
                    f"Ollama request failed with status {exc.response.status_code}."
                ) from exc
            except httpx.HTTPError as exc:
                raise AgentClientError("Unable to connect to the Ollama server.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise AgentClientError("Ollama returned an invalid JSON response.") from exc

        if not isinstance(payload, Mapping):
            raise AgentClientError("Ollama returned an invalid response format.")

        message = payload.get("message")
        if not isinstance(message, Mapping):
            raise AgentClientError("Ollama response did not contain a message.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise AgentClientError("Ollama response did not contain message content.")

        try:
            extraction = response_model.model_validate_json(content)
        except ValidationError as exc:
            raise AgentClientError("Ollama output did not match the requested extraction schema.") from exc

        return extraction.model_dump(mode="json")
