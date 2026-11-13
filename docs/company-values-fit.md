# Evidence-backed company values scoring — PR #3

This is a **manual evidence scoring engine**, not an automated company researcher. It assigns a weighted 0–100 score only when enough dimensions have human-reviewed evidence. It does not browse the web or scrape Glassdoor/LinkedIn.

Default weights:
- Patient outcomes / impact: 30%
- Business model alignment: 25%
- Employee experience: 20%
- Transparency / ethics: 15%
- Work-life balance: 10%

Supply one JSON object per line in `data/company_evidence.jsonl`:

```json
{"company":"Example Health","dimension":"patient_outcomes","score":4,"source_url":"https://example.org/research","observed_at":"2026-11-01","source_type":"company-report","note":"Explain what this source shows, including limitations"}
```

```sh
python -m job_search_tool.values_fit --evidence data/company_evidence.jsonl --output output/company_values.csv
pytest tests/test_values_fit.py
```

## Scoring and validation

The tool requires nonblank company, dimension, source URL, evidence date and notes; a finite numeric 0–5 score; http(s) URL shape; and a non-future ISO date. Identical source observations are deduplicated. Company-name casing is normalized for grouping, and repeated independent scores are averaged *within their dimension* before dimension weights are applied.

At least 3 dimensions totaling >=60% nominal weight are required. Missing dimensions are excluded from the weighted denominator, so **coverage_pct must be interpreted alongside values_fit_100**. Evidence quantity and nominal coverage are not measures of evidence credibility. For insufficient coverage, no score is emitted.

## Review findings and remaining limitations

Tests cover threshold behavior, weighting, multi-company isolation, multi-evidence averaging, duplicates, invalid scores/URLs/dates, empty files, and the JSONL-to-CSV CLI. The engine checks URL *format*, not whether a source is online, accurate, trustworthy, independent, or recent enough for decisions. The score is subjective and depends on human judgments and currently hardcoded weights. Different company names/aliases beyond casing are not unified.

Still needed to achieve an automated values-fit score: publicly permitted search/research integrations, evidence retrieval and attribution, contradiction handling, review of scoring rubric/weights, and joining scores to the job shortlist. Avoid scraping LinkedIn/Glassdoor without authorization.
