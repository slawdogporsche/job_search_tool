"""Build a ranked shortlist from a sweep CSV.

    python -m job_search_tool.shortlist            # uses newest output/jobs_*.csv
    python -m job_search_tool.shortlist --min-pay-ceiling 140000 --top 25
"""
import argparse
import glob
import os

import pandas as pd

FOREIGN = ("india|dubai|london|united kingdom|poland|spain|portugal|china|bulgaria|cyprus|canada|"
           "ireland|germany|france|singapore|japan|australia|israel|mexico|brazil|hyderabad|pune|"
           "bangalore|toronto")
INCLUDE = "analy|insight|data scien|strateg|business intell|operations|bizops|revenue|planning"
EXCLUDE = "sales|marketing|talent|recruit|legal|accounting|engineer|events|audit|risk|compliance|associate|intern"
LEVELS = ["3 Senior", "4 Staff/Lead", "5 Manager"]


def build_shortlist(df, min_pay_ceiling=130_000, include=INCLUDE, exclude=EXCLUDE,
                    foreign=FOREIGN, levels=LEVELS):
    """Filter to plausible roles; keep jobs with no posted pay (parser may have missed it)."""
    d = df[~df["location"].fillna("").str.contains(foreign, case=False)]
    d = d[d["title"].str.contains(include, case=False, na=False)
          & ~d["title"].str.contains(exclude, case=False, na=False)]
    d = d[d["seniority"].isin(levels)]
    d = d[d["pay_max"].isna() | (d["pay_max"] >= min_pay_ceiling)]
    d = d.drop_duplicates(["company", "title"]).assign(pay_listed=lambda x: x["pay_max"].notna())
    return d.sort_values(["pay_listed", "score"], ascending=False)


def latest_csv(outdir):
    files = sorted(glob.glob(os.path.join(outdir, "jobs_*.csv")))
    if not files:
        raise SystemExit(f"no jobs_*.csv in {outdir}/ - run the sweep first")
    return files[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output")
    ap.add_argument("--csv")
    ap.add_argument("--min-pay-ceiling", type=int, default=130_000)
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    d = build_shortlist(pd.read_csv(a.csv or latest_csv(a.out)), a.min_pay_ceiling)
    path = os.path.join(a.out, "shortlist.csv")
    d.to_csv(path, index=False)
    print(f"{len(d)} jobs -> {path}")
    print(d[["company", "title", "pay_min", "pay_max", "location", "url"]].head(a.top).to_string(index=False))


if __name__ == "__main__":
    main()
