from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field


ConfidenceScore = Annotated[float, Field(ge=0, le=1)]


class ConfidencePayload(BaseModel):
    overall: float | None = None
    fields: dict[str, float] = Field(default_factory=dict)


class StructuredExtraction(BaseModel):
    model_config = {"extra": "forbid"}


class ExtractionConfidence(StructuredExtraction):
    overall: float = Field(ge=0, le=1)
    fields: dict[str, ConfidenceScore]


class ExtractionAgentMetadata(StructuredExtraction):
    migrated_from_legacy_schema: bool


class OddsTeam(StructuredExtraction):
    name: str
    pitcher: str | None


class OddsRunLine(StructuredExtraction):
    line: float | None
    odds: float | None


class AwayTotal(StructuredExtraction):
    line: float | None
    over_odds: float | None


class HomeTotal(StructuredExtraction):
    line: float | None
    under_odds: float | None


class AwayOdds(StructuredExtraction):
    run_line: OddsRunLine
    total: AwayTotal
    moneyline: float | None


class HomeOdds(StructuredExtraction):
    run_line: OddsRunLine
    total: HomeTotal
    moneyline: float | None


class GameOdds(StructuredExtraction):
    away: AwayOdds
    home: HomeOdds


class OddsGame(StructuredExtraction):
    away_team: OddsTeam
    home_team: OddsTeam
    date: date | None
    odds: GameOdds
    series_id: str | None = Field(
        description=(
            "Format as SERIES_{away_abbreviation}_{home_abbreviation} using abbreviations shown in the screenshot. "
            "Use null if either abbreviation cannot be determined reliably."
        )
    )
    game_number: int | None
    league: str | None


class OddsData(StructuredExtraction):
    games: list[OddsGame]


class OddsExtraction(StructuredExtraction):
    games: OddsData
    warnings: list[str]
    confidence: ExtractionConfidence


class ScoreTeam(StructuredExtraction):
    name: str
    runs: int | None


class ScoreSeries(StructuredExtraction):
    league: str | None
    game: int | None
    summary: str | None


class ScoreGame(StructuredExtraction):
    date: date | None
    status: str | None
    away_team: ScoreTeam
    home_team: ScoreTeam
    series: ScoreSeries | None
    series_id: str | None = Field(
        description=(
            "Format as SERIES_{away_abbreviation}_{home_abbreviation} using abbreviations shown in the screenshot. "
            "Use null if either abbreviation cannot be determined reliably."
        )
    )


class ScoresExtraction(StructuredExtraction):
    games: list[ScoreGame]
    warnings: list[str]
    confidence: ExtractionConfidence


class ScheduleTeam(StructuredExtraction):
    name: str


class ScheduleSeries(StructuredExtraction):
    league: str | None
    game: int | None
    summary: str | None


class ScheduleGame(StructuredExtraction):
    date: date | None
    status: str | None
    away_team: ScheduleTeam
    home_team: ScheduleTeam
    game_number: int | None
    series_id: str | None = Field(
        description=(
            "Format as SERIES_{away_abbreviation}_{home_abbreviation} using abbreviations shown in the screenshot. "
            "Use null if either abbreviation cannot be determined reliably."
        )
    )
    league: str | None
    series: ScheduleSeries | None


class SchedulesExtraction(StructuredExtraction):
    games: list[ScheduleGame]
    warnings: list[str]
    confidence: ExtractionConfidence


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
    saved_file_paths: list[str] = Field(default_factory=list)
    extraction_type: str
    series_type: str


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
