import base64
import json
from collections.abc import Mapping
from json import JSONDecodeError
from typing import Any

import httpx

from app.core.config import settings


class AgentClientError(Exception):
    pass


def _extract_json_block(candidate_text: str) -> dict[str, Any]:
    try:
        return json.loads(candidate_text)
    except JSONDecodeError:
        pass

    fenced_prefix = "```json"
    if fenced_prefix in candidate_text:
        start = candidate_text.find(fenced_prefix)
        end = candidate_text.find("```", start + len(fenced_prefix))
        if start >= 0 and end > start:
            raw_json = candidate_text[start + len(fenced_prefix) : end].strip()
            return json.loads(raw_json)

    first_brace = candidate_text.find("{")
    last_brace = candidate_text.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        raw_json = candidate_text[first_brace : last_brace + 1]
        return json.loads(raw_json)

    raise AgentClientError("Agent response did not contain valid JSON.")


def _extract_text_output(payload: Mapping[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = payload.get("output")
    if isinstance(output, list):
        text_parts: list[str] = []
        for item in output:
            if not isinstance(item, Mapping):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for segment in content:
                if not isinstance(segment, Mapping):
                    continue
                maybe_text = segment.get("text")
                if isinstance(maybe_text, str):
                    text_parts.append(maybe_text)
        if text_parts:
            return "\n".join(text_parts)

    raise AgentClientError("Unable to read text output from agent response.")


class AzureFoundryAgentClient:
    def __init__(self) -> None:
        if not settings.azure_agent_api_url:
            raise AgentClientError("Missing AZURE_AGENT_API_URL in environment configuration.")
        if not settings.azure_agent_model:
            raise AgentClientError("Missing AZURE_AGENT_MODEL in environment configuration.")

    async def parse_screenshot(self, image_bytes: bytes, content_type: str) -> dict[str, Any]:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:{content_type};base64,{image_b64}"

        request_payload: dict[str, Any] = {
            "model": settings.azure_agent_model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": settings.agent_extraction_prompt},
                        {"type": "input_image", "image_url": image_url},
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
        }

        params: dict[str, str] = {}
        if settings.azure_agent_api_version:
            params["api-version"] = settings.azure_agent_api_version

        headers = {"Content-Type": "application/json"}
        if settings.azure_agent_api_key:
            headers["api-key"] = settings.azure_agent_api_key

        async with httpx.AsyncClient(timeout=settings.agent_timeout_seconds) as client:
            try:
                response = await client.post(
                    settings.azure_agent_api_url,
                    params=params or None,
                    headers=headers,
                    json=request_payload,
                )
                response.raise_for_status()
            except httpx.TimeoutException as exc:
                raise AgentClientError("Agent request timed out.") from exc
            except httpx.HTTPStatusError as exc:
                raise AgentClientError(
                    f"Agent request failed with status {exc.response.status_code}."
                ) from exc
            except httpx.HTTPError as exc:
                raise AgentClientError("Agent request failed due to network error.") from exc

        payload = response.json()
        if not isinstance(payload, Mapping):
            raise AgentClientError("Invalid agent response format.")

        text_output = _extract_text_output(payload)
        try:
            parsed = _extract_json_block(text_output)
        except (JSONDecodeError, AgentClientError) as exc:
            raise AgentClientError("Agent output was not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise AgentClientError("Agent output JSON root must be an object.")

        return parsed
