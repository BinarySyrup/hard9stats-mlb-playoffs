import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, Path as ApiPath, UploadFile, status
from pydantic import ValidationError

from app.models.contracts import (
    HealthResponse,
    IngestionResponse,
    MergeReportResponse,
    ReportGenerationResponse,
    ReportStatusResponse,
)
from app.scripts.generate_report_html import render_report_html
from app.services.agent_client import AgentClientError, OllamaAgentClient
from app.services.ingestion_service import IngestionService

router = APIRouter()


def _series_key(series_type: str) -> str:
    raw = (series_type or "WCS").strip()
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", raw).strip("-").upper()

    mappings = {
        "WCS": "WCS",
        "WILD-CARD": "WCS",
        "WILDCARD": "WCS",
        "LDS": "LDS",
        "DIVISION-SERIES": "LDS",
        "DIVISIONSERIES": "LDS",
        "LCS": "LCS",
        "LEAGUE-CHAMPIONSHIP-SERIES": "LCS",
        "LEAGUECHAMPIONSHIPSERIES": "LCS",
        "WS": "WS",
        "WORLD-SERIES": "WS",
        "WORLDSERIES": "WS",
    }
    return mappings.get(normalized, normalized or "WCS")


def _iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/ingest/screenshot", response_model=IngestionResponse)
async def ingest_screenshot(
    image: UploadFile = File(...),
    data_type: Literal["odds", "scores", "schedules"] = Form(...),
    series_type: str = Form(...),
) -> IngestionResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an image.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty.",
        )

    series_key = _series_key(series_type)
    if series_key not in {"WCS", "LDS", "LCS", "WS"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="series_type must be WCS, LDS, LCS, or WS.",
        )

    try:
        service = IngestionService()
        envelope, saved_file_paths = await service.ingest_screenshot(
            source_image_name=image.filename or "uploaded_image",
            image_bytes=image_bytes,
            content_type=image.content_type,
            extraction_type=data_type,
            series_type=series_key,
        )
    except AgentClientError as exc:
        message = str(exc)
        status_code = status.HTTP_502_BAD_GATEWAY
        if "timed out" in message.lower():
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
        if "missing ollama" in message.lower() or "prompt file" in message.lower():
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(status_code=status_code, detail=message) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Model output schema validation failed: {exc}",
        ) from exc

    return IngestionResponse(
        **envelope.model_dump(),
        saved_file_path=saved_file_paths[0],
        saved_file_paths=saved_file_paths,
        extraction_type=data_type,
        series_type=series_key,
    )


@router.post(
    "/reports/{series_type}/merge-json",
    response_model=MergeReportResponse,
    summary="Merge schedule, score, and odds JSON with Ollama into one report JSON",
    response_description="Merged report JSON metadata and output path.",
    responses={
        404: {"description": "No input JSON files were found for this series type."},
        422: {"description": "An input JSON file is invalid."},
    },
)
async def merge_report_json(
    series_type: str = ApiPath(
        ...,
        description="Series type code. Accepted values: WCS, LDS, LCS, WS (aliases supported, e.g. wild-card).",
        examples=["WCS"],
    ),
) -> MergeReportResponse:
    series_key = _series_key(series_type)

    series_ingested_dir = Path("data/ingested") / series_key
    input_files = sorted(series_ingested_dir.glob("*/*.json"))
    if not input_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No input JSON files found under {series_ingested_dir}.",
        )

    files_by_type: dict[str, list[dict[str, object]]] = {
        "odds": [],
        "scores": [],
        "schedules": [],
    }
    for input_file in input_files:
        category = input_file.parent.name
        try:
            file_payload = json.loads(input_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Input file is not valid JSON: {input_file}.",
            ) from exc
        files_by_type.setdefault(category, []).append(
            {
                "filename": str(input_file.relative_to(series_ingested_dir)).replace("\\", "/"),
                "contents": file_payload,
            }
        )

    combined_json = {
        "series_type": series_key,
        "files": files_by_type,
    }

    try:
        agent_client = OllamaAgentClient()
        merged_json_text = await agent_client.merge_json_files(combined_json)
    except AgentClientError as exc:
        message = str(exc)
        status_code = status.HTTP_502_BAD_GATEWAY
        if "timed out" in message.lower():
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
        if "missing ollama" in message.lower() or "prompt file" in message.lower():
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(status_code=status_code, detail=message) from exc

    output_dir = Path(f"data/reports/{series_key}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for existing_json in output_dir.glob("*.json"):
        existing_json.unlink(missing_ok=True)

    output_path = output_dir / "report-merged.json"
    output_path.write_text(merged_json_text, encoding="utf-8")

    # The model response is saved without schema validation; parsing is best-effort for response metadata only.
    report_date = "latest"
    games_count = 0
    try:
        response_metadata = json.loads(merged_json_text)
    except json.JSONDecodeError:
        response_metadata = None
    if isinstance(response_metadata, dict):
        if isinstance(response_metadata.get("report_date"), str):
            report_date = response_metadata["report_date"]
        games = response_metadata.get("games")
        if isinstance(games, list):
            games_count = len(games)

    return MergeReportResponse(
        series_type=series_key,
        report_date=report_date,
        games_count=games_count,
        merged_json_path=str(output_path).replace("\\", "/"),
    )


@router.post(
    "/reports/{series_type}/generate-html",
    response_model=ReportGenerationResponse,
    summary="Generate report HTML from merged report JSON",
    response_description="Generated report HTML metadata and output path.",
    responses={
        404: {"description": "Merged report JSON was not found for series type."},
        422: {"description": "Validation error for path params."},
    },
)
async def generate_html_report(
    series_type: str = ApiPath(
        ...,
        description="Series type code. Accepted values: WCS, LDS, LCS, WS (aliases supported, e.g. wild-card).",
        examples=["WCS"],
    ),
) -> ReportGenerationResponse:
    series_key = _series_key(series_type)

    merged_path = Path(f"data/reports/{series_key}/report-merged.json")
    if not merged_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merged JSON file not found: {merged_path}",
        )

    merged_payload = json.loads(merged_path.read_text(encoding="utf-8"))
    merged_payload["series_type"] = series_key

    generated_on = datetime.now().astimezone().strftime("%Y-%m-%d")
    merged_payload["generated_report_date"] = generated_on
    html_path = Path(f"data/reports/{series_key}/report-{generated_on}.html")

    html = render_report_html(merged_payload)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")

    return ReportGenerationResponse(
        series_type=series_key,
        report_date=generated_on,
        games_count=len(merged_payload.get("games", [])),
        merged_json_path=str(merged_path).replace("\\", "/"),
        html_report_path=str(html_path).replace("\\", "/"),
    )


@router.get(
    "/reports/{series_type}/status",
    response_model=ReportStatusResponse,
    summary="Get report artifact status for a series",
    response_description="Presence and paths of merged JSON and latest generated HTML.",
)
async def report_status(
    series_type: str = ApiPath(
        ...,
        description="Series type code. Accepted values: WCS, LDS, LCS, WS (aliases supported, e.g. wild-card).",
        examples=["WCS"],
    ),
) -> ReportStatusResponse:
    series_key = _series_key(series_type)
    reports_dir = Path(f"data/reports/{series_key}")
    merged_path = reports_dir / "report-merged.json"

    html_files = sorted(reports_dir.glob("report-*.html"), key=lambda file: file.stat().st_mtime, reverse=True)
    latest_html = html_files[0] if html_files else None

    return ReportStatusResponse(
        series_type=series_key,
        merged_json_exists=merged_path.exists(),
        merged_json_path=str(merged_path).replace("\\", "/"),
        merged_json_modified_at=_iso_mtime(merged_path) if merged_path.exists() else None,
        latest_html_exists=latest_html is not None,
        latest_html_path=str(latest_html).replace("\\", "/") if latest_html else None,
        latest_html_modified_at=_iso_mtime(latest_html) if latest_html else None,
    )


