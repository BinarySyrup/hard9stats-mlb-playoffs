from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConfidencePayload(BaseModel):
    overall: float | None = None
    fields: dict[str, float] = Field(default_factory=dict)


class IngestionEnvelope(BaseModel):
    request_id: UUID
    created_at: datetime
    source_image_name: str
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    confidence: ConfidencePayload = Field(default_factory=ConfidencePayload)
    agent_metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionResponse(IngestionEnvelope):
    saved_file_path: str


class MergeReportResponse(BaseModel):
    series_type: str = Field(..., description="Normalized series type code (WCS, LDS, LCS, WS).")
    report_date: str = Field(..., description="Report date derived from merged game data (YYYY-MM-DD).")
    games_count: int = Field(..., description="Number of merged games.")
    merged_json_path: str = Field(..., description="Filesystem path to merged report JSON output.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "series_type": "WCS",
                "report_date": "2026-09-30",
                "games_count": 12,
                "merged_json_path": "data/reports/WCS/report-merged.json",
            }
        }
    }


class ReportGenerationResponse(BaseModel):
    series_type: str = Field(..., description="Normalized series type code (WCS, LDS, LCS, WS).")
    report_date: str = Field(..., description="Report date used for generated HTML filename.")
    games_count: int = Field(..., description="Number of games in merged report JSON.")
    merged_json_path: str = Field(..., description="Filesystem path to merged report JSON input.")
    html_report_path: str = Field(..., description="Filesystem path to generated HTML report.")


class ReportStatusResponse(BaseModel):
    series_type: str
    merged_json_exists: bool
    merged_json_path: str
    merged_json_modified_at: str | None = None
    latest_html_exists: bool
    latest_html_path: str | None = None
    latest_html_modified_at: str | None = None


class HealthResponse(BaseModel):
    status: str
