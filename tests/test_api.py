import json
import mimetypes
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import create_app
from app.models.contracts import IngestionEnvelope
from app.services.agent_client import AgentClientError


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "lds"
INGESTION_TYPES = ("odds", "schedules", "scores")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    temp_root = Path(__file__).resolve().parent / ".tmp"
    temp_root.mkdir(exist_ok=True)
    original_cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="api-", dir=temp_root) as working_dir:
        try:
            monkeypatch.chdir(working_dir)
            with TestClient(create_app()) as test_client:
                yield test_client
        finally:
            os.chdir(original_cwd)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_rejects_non_image_upload(client: TestClient) -> None:
    response = client.post(
        "/ingest/LDS/odds/",
        files={"image": ("notes.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file must be an image."


def test_ingest_rejects_empty_image(client: TestClient) -> None:
    response = client.post(
        "/ingest/LDS/odds/",
        files={"image": ("empty.png", b"", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded image file is empty."


def test_ingest_rejects_unsupported_data_type(client: TestClient) -> None:
    response = client.post(
        "/ingest/LDS/unknown/",
        files={"image": ("screen.png", b"image-bytes", "image/png")},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("data_type", INGESTION_TYPES)
def test_ingest_uses_lds_screenshot_fixtures(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, data_type: str
) -> None:
    fixture_directory = FIXTURE_ROOT / data_type
    screenshots = sorted(
        path
        for path in fixture_directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not screenshots:
        pytest.skip(f"Add an LDS {data_type} screenshot under {fixture_directory}.")

    for screenshot_path in screenshots:
        content_type = mimetypes.guess_type(screenshot_path.name)[0]
        assert content_type is not None and content_type.startswith("image/")
        image_bytes = screenshot_path.read_bytes()
        saved_path = f"data/ingested/LDS/{data_type}/example.json"

        class FakeIngestionService:
            async def ingest_screenshot(
                self,
                source_image_name: str,
                image_bytes: bytes,
                content_type: str,
                extraction_type: str,
                series_type: str,
            ):
                assert source_image_name == screenshot_path.name
                assert image_bytes == screenshot_path.read_bytes()
                assert content_type == mimetypes.guess_type(screenshot_path.name)[0]
                assert extraction_type == data_type
                assert series_type == "LDS"
                envelope = IngestionEnvelope(
                    request_id=UUID("00000000-0000-0000-0000-000000000001"),
                    created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                    source_image_name=source_image_name,
                    data={"games": []},
                )
                return envelope, [saved_path]

        monkeypatch.setattr(routes, "IngestionService", FakeIngestionService)
        response = client.post(
            f"/ingest/LDS/{data_type}/",
            files={"image": (screenshot_path.name, image_bytes, content_type)},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["series_type"] == "LDS"
        assert payload["extraction_type"] == data_type
        assert payload["data"] == {"games": []}
        assert payload["saved_file_path"] == saved_path
        assert payload["saved_file_paths"] == [saved_path]


def test_ingest_maps_agent_timeout_to_gateway_timeout(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailingIngestionService:
        async def ingest_screenshot(self, **kwargs):
            raise AgentClientError("Ollama inference request timed out.")

    monkeypatch.setattr(routes, "IngestionService", FailingIngestionService)

    response = client.post(
        "/ingest/LDS/odds/",
        files={"image": ("odds.png", b"image-bytes", "image/png")},
    )

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"]


def test_merge_returns_not_found_when_series_has_no_inputs(client: TestClient) -> None:
    response = client.post("/reports/division-series/merge-json")

    assert response.status_code == 404
    detail = response.json()["detail"].replace("\\", "/")
    assert "data/ingested/LDS" in detail


def test_merge_rejects_invalid_input_json(client: TestClient) -> None:
    input_path = Path("data/ingested/LDS/odds/broken.json")
    input_path.parent.mkdir(parents=True)
    input_path.write_text("{invalid", encoding="utf-8")

    response = client.post("/reports/LDS/merge-json")

    assert response.status_code == 422
    assert "not valid JSON" in response.json()["detail"]


def test_merge_saves_agent_result_and_reports_game_count(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = Path("data/ingested/LDS/schedules/game.json")
    input_path.parent.mkdir(parents=True)
    input_path.write_text(json.dumps({"games": [{"game_number": 1}]}), encoding="utf-8")
    merged_json = json.dumps(
        {"report_date": "2026-10-01", "games": [{"game_number": 1}, {"game_number": 2}]}
    )

    class FakeAgentClient:
        async def merge_json_files(self, combined_json: dict[str, object]) -> str:
            assert combined_json["series_type"] == "LDS"
            files = combined_json["files"]
            assert files["schedules"][0]["filename"] == "schedules/game.json"
            assert files["schedules"][0]["contents"] == {"games": [{"game_number": 1}]}
            return merged_json

    monkeypatch.setattr(routes, "OllamaAgentClient", FakeAgentClient)

    response = client.post("/reports/LDS/merge-json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["series_type"] == "LDS"
    assert payload["report_date"] == "2026-10-01"
    assert payload["games_count"] == 2
    output_path = Path(payload["merged_json_path"])
    assert output_path == Path("data/reports/LDS/report-merged.json")
    assert json.loads(output_path.read_text(encoding="utf-8")) == json.loads(merged_json)


def test_generate_html_returns_not_found_without_merged_json(client: TestClient) -> None:
    response = client.post("/reports/LDS/generate-html")

    assert response.status_code == 404
    assert "Merged JSON file not found" in response.json()["detail"]


def test_generate_html_writes_rendered_report(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    merged_path = Path("data/reports/LDS/report-merged.json")
    merged_path.parent.mkdir(parents=True)
    merged_path.write_text(json.dumps({"games": []}), encoding="utf-8")

    def fake_render(payload: dict[str, object]) -> str:
        assert payload["series_type"] == "LDS"
        assert payload["generated_report_date"]
        return "<html>report</html>"

    monkeypatch.setattr(routes, "render_report_html", fake_render)

    response = client.post("/reports/division-series/generate-html")

    assert response.status_code == 200
    payload = response.json()
    assert payload["series_type"] == "LDS"
    assert payload["games_count"] == 0
    html_path = Path(payload["html_report_path"])
    assert html_path.exists()
    assert html_path.read_text(encoding="utf-8") == "<html>report</html>"


def test_status_reports_missing_artifacts(client: TestClient) -> None:
    response = client.get("/reports/division-series/status")

    assert response.status_code == 200
    assert response.json() == {
        "series_type": "LDS",
        "merged_json_exists": False,
        "merged_json_path": "data/reports/LDS/report-merged.json",
        "merged_json_modified_at": None,
        "latest_html_exists": False,
        "latest_html_path": None,
        "latest_html_modified_at": None,
    }


def test_status_reports_existing_artifacts_and_latest_html(client: TestClient) -> None:
    reports_dir = Path("data/reports/LDS")
    reports_dir.mkdir(parents=True)
    merged_path = reports_dir / "report-merged.json"
    older_html_path = reports_dir / "report-2026-09-30.html"
    latest_html_path = reports_dir / "report-2026-10-01.html"
    merged_path.write_text("{}", encoding="utf-8")
    older_html_path.write_text("old report", encoding="utf-8")
    latest_html_path.write_text("latest report", encoding="utf-8")
    os.utime(older_html_path, (1_800_000_000, 1_800_000_000))
    os.utime(latest_html_path, (1_800_000_100, 1_800_000_100))

    response = client.get("/reports/LDS/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["merged_json_exists"] is True
    assert payload["merged_json_path"] == "data/reports/LDS/report-merged.json"
    assert payload["merged_json_modified_at"] is not None
    assert payload["latest_html_exists"] is True
    assert payload["latest_html_path"] == "data/reports/LDS/report-2026-10-01.html"
    assert payload["latest_html_modified_at"] is not None
