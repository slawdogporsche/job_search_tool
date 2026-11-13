# Additional job search APIs — PR #1

This is an **opt-in** module for searching Adzuna and USAJOBS by keyword and location. It exports normalized source-specific CSVs but **does not connect to the existing Greenhouse/Lever/Ashby sweep or production shortlist**.

## Setup and usage

Get API credentials from the providers. Export `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, or `USAJOBS_API_KEY` and `USAJOBS_EMAIL`. Do not commit credentials.

```sh
python -m job_search_tool.additional_sources --source adzuna --query "healthcare analytics" --location Denver --output output/adzuna.csv
python -m job_search_tool.additional_sources --source usajobs --query "health analytics" --location "Denver, Colorado" --output output/usajobs.csv
pytest tests/test_additional_sources.py
```

The CSV columns are `source, source_id, company, title, location, url, description, salary_min, salary_max, created`.

Adzuna salary estimates are **not necessarily employer-confirmed**. USAJOBS exports salary min/max only for responses explicitly reporting an annual rate; hourly and unknown rate codes produce blank salary fields rather than misleading annual numbers. Rates are not converted and currencies are not normalized.

## Verification and limitations

Mocked-unit tests cover source parsing and request parameters, annual versus hourly salary rates, pagination and duplicate provider IDs, invalid page limits, missing credentials, empty replies, HTTP failures, CSV schema and CLI validation. Run tests with `pytest tests/test_additional_sources.py`. No live provider credentials were available for smoke testing.

Additional work before operational use: map the new CSV schema to existing `sweep.py` output, standardize annual salary/currency and provider confidence, cross-source deduplication, retry/backoff for rate limits, and live API schema verification. Job availability, API quotas, and provider terms should be confirmed during integration.

Provider references: https://developer.adzuna.com/docs/search and https://developer.usajobs.gov/api-reference/get-api-search
