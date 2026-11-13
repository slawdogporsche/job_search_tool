# Auditing job filtering

Create a diagnostic sample of kept and rejected postings. It is important to include rejected jobs to identify false negatives. Start with your all-roles sweep, then compare against the shortlist:

```sh
python -m job_search_tool.sweep --all --out output
python -m job_search_tool.shortlist --out output
python -m job_search_tool.filter_audit sample --all output/jobs_YYYY-MM-DD.csv --selected output/shortlist.csv --per-group 30
```

Replace YYYY-MM-DD with your actual sweep date. Review output/filter_review.csv, label human_relevant as yes/no, and describe the reasoning in the reason column. Then run:

```sh
python -m job_search_tool.filter_audit report --review output/filter_review.csv
pytest tests/test_filter_audit.py
```

Evaluate title exclusions, geographic/remote eligibility, salary policy (maximum versus minimum), and seniority. Note that --all still applies the sweep's minimum-pay filter if specified: omit --min-pay for this baseline.

**Important:** These are diagnostic sample metrics, not unbiased population estimates. The stratified sample intentionally oversamples the relatively rare accepted/rejected group. Also, comparing the broad all-jobs sweep to shortlist captures the combination of upstream and shortlist rules, not the accuracy of each stage independently. Don't change production screening thresholds until real postings have been reviewed.
