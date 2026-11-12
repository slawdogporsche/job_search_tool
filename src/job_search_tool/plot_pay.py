#!/usr/bin/env python3
"""
plot_pay.py - histogram of posted pay (midpoint of range), stacked by seniority.

Usage:
    pip install pandas matplotlib
    python plot_pay.py jobs_2026-11-12.csv          # writes pay_histogram.png
"""
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: plot_pay.py <jobs.csv>")
df = pd.read_csv(path)
pat = sys.argv[sys.argv.index("--titles") + 1] if "--titles" in sys.argv else None
if pat:
    df = df[df["title"].str.contains(pat, case=False, regex=True, na=False)]
    print(f"title filter /{pat}/ kept {len(df)} jobs")
total = len(df)
df = df.dropna(subset=["pay_min", "pay_max"]).copy()
df["pay_mid"] = (df["pay_min"] + df["pay_max"]) / 2
print(f"{len(df)} of {total} jobs have parseable pay ({total - len(df)} excluded)")
if df.empty:
    sys.exit("no pay data to plot")

levels = sorted(df["seniority"].unique())
labels = [l[2:] for l in levels]
bins = range(int(df["pay_mid"].min() // 10_000 * 10_000),
             int(df["pay_mid"].max() // 10_000 * 10_000) + 20_000, 10_000)

fig, ax = plt.subplots(figsize=(10, 5.5))
ax.hist([df.loc[df["seniority"] == l, "pay_mid"] for l in levels], bins=bins,
        stacked=True, label=[f"{lab} (n={(df['seniority'] == l).sum()})" for l, lab in zip(levels, labels)],
        edgecolor="white")
ax.axvline(100_000, ls="--", c="gray", lw=1); ax.text(100_000, ax.get_ylim()[1] * .97, " $100k floor", va="top", color="gray")
ax.axvline(145_000, ls="--", c="black", lw=1); ax.text(145_000, ax.get_ylim()[1] * .90, " current base", va="top")
ax.set_xlabel("Posted pay, midpoint of range"); ax.set_ylabel("Number of jobs")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
ax.set_title(f"Health-aligned job pay by seniority ({len(df)} jobs with posted pay)" + (f"\ntitles matching /{pat}/" if pat else ""))
ax.legend(title="Seniority")
fig.tight_layout(); out = "pay_histogram_filtered.png" if pat else "pay_histogram.png"
fig.savefig(out, dpi=150)
print("Wrote", out)
print(df.groupby("seniority")["pay_mid"].describe()[["count", "min", "50%", "max"]].round(0))
