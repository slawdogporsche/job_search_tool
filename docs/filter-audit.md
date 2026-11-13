# Auditing job filtering

This tool audits **the combined sweep + shortlist filtering pipeline** using human labels. It does not change production filters or establish that the filters are accurate.

## Generate review samples

Run a broad sweep **without** `--min-pay`, then shortlist from that same file:

```sh
python -m job_search_tool.sweep --all --out output
python -m job_search_tool.shortlist --out output
python -m job_search_tool.filter_audit sample --all output/jobs_YYYY-MM-DD.csv --selected output/shortlist.csv --per-group 30 --seed 7
```

Replace `YYYY-MM-DD` with the actual sweep date. Keep the two inputs from the **same dataset and run**. If any selected job is absent from the all-jobs file, the tool fails instead of silently misclassifying it. Duplicate job identifiers are sampled once. The identifier prioritizes URL, then source ID, then company/title/location; URL variations or reuse can still cause mismatches.

Review `output/filter_review.csv`. Set `human_relevant` to `yes` or `no` for each job, and use `reason` to explain the judgment. Blank labels are ignored; invalid values generate errors.

```sh
python -m job_search_tool.filter_audit report --review output/filter_review.csv
pytest tests/test_filter_audit.py
```

The report displays true positives, false positives, false negatives, true negatives, and **sample-only** precision/recall. If there is no denominator, the metric is `null` rather than a fabricated 0%.

## Interpretation and limitations

- Included and excluded samples are independently sampled (up to the per-group limit); this **case-control design is not proportional to the population**. Reported precision/recall are diagnostic sample statistics, *not unbiased estimates of actual filter performance*. For population estimates, weight by group sizes and use an appropriate sampling design.
- Comparing the unfiltered sweep to the shortlist tests the **combined** rules, not each filtering stage independently.
- Human labels require a consistent relevance rubric, ideally reviewed by more than one evaluator in ambiguous cases.
- This utility will not find opportunities missing from the scraped boards in the first place; it only analyzes observed jobs.
- Check exclusions by title, seniority, geography/remote eligibility, and salary policy (the shortlist filters by **maximum** advertised pay).
- Do not change production thresholds until actual postings are labeled and reviewed.

## Verification

The targeted unit suite covers inclusion/exclusion classification, repeatable sampling, TP/FP/FN/TN math, blank/invalid labels, empty samples and zero denominators, duplicate jobs, mismatched datasets, and the CLI round-trip.
