# LDS screenshot fixtures

Place the screenshots used by the ingestion API cases in the folder matching their data type:

- `odds/` for odds screenshots
- `schedules/` for schedule screenshots
- `scores/` for score screenshots

Supported extensions are `.jpg`, `.jpeg`, `.png`, and `.webp`. The tests upload every supported image in each folder to the corresponding LDS ingestion route. A category is skipped until it contains at least one screenshot. The ingestion service is mocked, so these cases check request handling without calling Ollama.
