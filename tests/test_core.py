import pandas as pd
from job_search_tool import sweep
from job_search_tool.shortlist import build_shortlist


def test_extract_pay_range():
    assert sweep.extract_pay("Pay: $114,000 - $193,000 per year") == (114000, 193000)


def test_extract_pay_k_format():
    assert sweep.extract_pay("base $140k to $165k") == (140000, 165000)


def test_extract_pay_ignores_hourly():
    assert sweep.extract_pay("$45 - $60 per hour") is None


def test_seniority_levels():
    assert sweep.seniority("Analyst Intern") == "1 Entry"
    assert sweep.seniority("Data Analyst") == "2 Mid"
    assert sweep.seniority("Senior Analyst I") == "3 Senior"
    assert sweep.seniority("Staff Analytics Engineer") == "4 Staff/Lead"
    assert sweep.seniority("Senior Manager, Insights") == "5 Manager"
    assert sweep.seniority("Director of Analytics") == "6 Director+"


def test_work_mode_and_location():
    assert sweep.work_mode("Remote - US", "x") == "remote"
    assert sweep.colorado_ok("Remote - US", "", "remote")
    assert not sweep.colorado_ok("New York, NY", "", "onsite/unknown")


def test_slug_variants():
    assert "devotedhealth" in sweep.slug_variants("Devoted Health")


def test_shortlist_drops_foreign_and_keeps_unpriced():
    df = pd.DataFrame([
        dict(company="A", title="Senior Data Analyst", seniority="3 Senior", pay_max=150000, location="Remote", score=5),
        dict(company="B", title="Senior Data Analyst", seniority="3 Senior", pay_max=150000, location="Pune, India", score=9),
        dict(company="C", title="Lead Insights Analyst", seniority="4 Staff/Lead", pay_max=None, location="Remote", score=3),
        dict(company="D", title="Senior Data Analyst", seniority="3 Senior", pay_max=90000, location="Remote", score=8),
    ])
    out = build_shortlist(df)
    assert set(out.company) == {"A", "C"}
