# Evidence-based company values fit

This module offers a **human-reviewed** values rubric rather than inventing company reputation scores. Company research is not automated; reviewers supply dated observations, citations and a 0–5 assessment per observation.

Default weights (customize for your priorities):
- Patient outcomes / clinical impact: 30%
- Business-model alignment: 25%
- Employee experience: 20%
- Transparency / ethics: 15%
- Work-life balance: 10%

Create a JSONL file such as data/company_evidence.jsonl with one line per observation:

```json
{"company":"Example Health","dimension":"patient_outcomes","score":4,"source_url":"https://example.org/research","observed_at":"2026-11-01","source_type":"company-report","note":"Summarize exactly what the source demonstrates and its limitations"}
```

Then run:

```sh
python -m job_search_tool.values_fit --evidence data/company_evidence.jsonl --output output/company_values.csv
pytest tests/test_values_fit.py
```

A company is only scored when there are observations for at least 3 dimensions totaling at least 60% of the predefined weight. Otherwise it is marked `insufficient evidence`. Scores are 0–100 weighted averages **over available dimensions only**, and reported coverage prevents overconfidence.

Potential research sources: company reports, public policies, regulatory records, reputable journalism, and publicly accessible review aggregations. The score engine verifies URL shape, not the factual accuracy of the link or the evidence. Reviewers must check sources, recency, representativeness, and contradictions. Do not scrape Glassdoor or LinkedIn without permission; use licensed sources or human-observed public material. Integrating research/search APIs and attaching scores to job shortlists are separate future tasks.
