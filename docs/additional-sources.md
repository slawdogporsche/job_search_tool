# Additional search APIs (opt-in)

This module adds keyword/location search via **Adzuna** and **USAJOBS**. It does not change the existing Greenhouse/Lever/Ashby sweep, and does not automatically merge returned jobs into the production shortlist.

Register for the applicable API credentials and set `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` or `USAJOBS_API_KEY` + `USAJOBS_EMAIL` in your local environment. Never commit credentials.

```sh
python -m job_search_tool.additional_sources --source adzuna --query "healthcare analytics" --location Denver --output output/adzuna.csv
python -m job_search_tool.additional_sources --source usajobs --query "health analytics" --location Colorado --output output/usajobs.csv
pytest tests/test_additional_sources.py
```

The normalized export columns are source, source_id, company, title, location, url, description, salary_min, salary_max, and created. Salary fields from aggregators may be estimated and should not be assumed to be employer-confirmed.

Follow-up work: map this schema into the existing sweep schema, cross-source deduplication, retry/backoff for rate limiting, and provenance tracking.

API docs: https://developer.adzuna.com/docs/search and https://developer.usajobs.gov/api-reference/get-api-search
