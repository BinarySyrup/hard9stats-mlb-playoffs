import base64
import json
from collections.abc import Mapping
from typing import Any

import httpx

from app.core.config import get_llm_prompt_path, settings


class AgentClientError(Exception):
    pass


class OllamaAgentClient:
    _structured_extractions = {
        "odds": "mlb-data-ingestion-odds.txt",
        "scores": "mlb-data-ingestion-scores.txt",
        "schedules": "mlb-data-ingestion-schedules.txt",
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
        filename = self._structured_extractions.get(extraction_type)
        if filename is None:
            raise AgentClientError(f"Unsupported screenshot extraction type: {extraction_type}.")

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
        )

    async def merge_json_files(self, combined_json: dict[str, Any]) -> str:
        prompt_path = get_llm_prompt_path("mlb-data-merge.txt")
        try:
            prompt = prompt_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise AgentClientError(f"Unable to read Ollama prompt file: {prompt_path}.") from exc

        prompt = f"{prompt.rstrip()}\n{json.dumps(combined_json, indent=2, ensure_ascii=False)}"
        return await self._request_chat(prompt=prompt)

    async def _parse_image(
        self,
        image_bytes: bytes,
        prompt: str,
    ) -> dict[str, Any]:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        content = await self._request_chat(prompt=prompt, images=[image_b64])

        try:
            extraction = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AgentClientError("Ollama response message content was not valid JSON.") from exc

        if not isinstance(extraction, dict):
            raise AgentClientError("Ollama JSON response must be an object.")

        return extraction

    async def _request_chat(
        self,
        prompt: str,
        images: list[str] | None = None,
    ) -> str:
        message: dict[str, Any] = {
            "role": "user",
            "content": prompt,
        }
        if images:
            message["images"] = images

        request_payload: dict[str, Any] = {
            "model": settings.ollama_model,
            "messages": [message],
            "format": "json",
            "think": False,
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
            diagnostics = []
            done_reason = payload.get("done_reason")
            if done_reason:
                diagnostics.append(f"done_reason={done_reason}")
            thinking = message.get("thinking")
            diagnostics.append(
                f"thinking_present={isinstance(thinking, str) and bool(thinking.strip())}"
            )
            eval_count = payload.get("eval_count")
            if isinstance(eval_count, int):
                diagnostics.append(f"eval_count={eval_count}")
            detail = f" ({', '.join(diagnostics)})" if diagnostics else ""
            raise AgentClientError(f"Ollama response did not contain message content{detail}.")
        return content
