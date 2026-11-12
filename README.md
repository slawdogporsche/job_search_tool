# job_search_tool

Sweeps public Greenhouse / Lever / Ashby job boards for health-aligned roles, extracts posted pay,
scores postings against a skills list, and builds a ranked shortlist and pay histogram.

## Setup
    ./setup.sh                      # macOS/Linux/WSL  (Windows: .\setup.ps1)
    source .venv/bin/activate

## Workflow
    python3 -m job_search_tool.sweep --discover-file data/companies.txt   # find board tokens -> data/boards.json
    python3 -m job_search_tool.sweep --all                                # pull every job -> output/jobs_<date>.csv
    python3 -m job_search_tool.plot_pay output/jobs_<date>.csv --titles "analy|insight|strateg"
    python3 -m job_search_tool.shortlist                                  # -> output/shortlist.csv
    pytest

## Layout
    src/job_search_tool/   sweep.py (fetch/parse/score), plot_pay.py, shortlist.py
    data/                  companies.txt (seed names), boards.json (confirmed boards)
    tests/                 parser and shortlist tests
    output/                generated CSVs and descriptions (gitignored)

## Known limits
- Covers Greenhouse/Lever/Ashby only. Workday/iCIMS employers are not covered.
- Seniority is inferred from titles. Pay is parsed from structured fields or description text and can miss formats.
- The `remote` flag is noisy; always read the posting for in-office requirements and the Colorado pay band.

## Roadmap
- Mission vetting: score companies on business model (does revenue depend on outcomes, or on keeping people enrolled?).
- Workday pull for large payers and health systems.
- Per-job resume tailoring from `output/descriptions/`.
- Private notes/tracking per application.
