# job_search_tool

Sweeps public Greenhouse / Lever / Ashby job boards, writes a CSV (title, company,
seniority, mode, location, pay, matched skills, link), and plots posted pay by seniority.

## Setup
    ./setup.sh            # macOS/Linux/WSL
    .\setup.ps1           # Windows PowerShell
Then activate the venv (`source .venv/bin/activate` or `.\.venv\Scripts\Activate.ps1`).

## Use
    python job_sweep.py --discover "Oscar Health" "Devoted Health"   # find board tokens
    # paste the printed lines into BOARDS in job_sweep.py
    python job_sweep.py --all                  # every job on those boards
    python job_sweep.py --min-pay 100000       # filtered (analytics titles, remote/Colorado)
    python plot_pay.py jobs_<date>.csv         # writes pay_histogram.png

Workday/iCIMS employers are not covered yet.
