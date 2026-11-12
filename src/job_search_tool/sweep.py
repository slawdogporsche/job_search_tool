#!/usr/bin/env python3
"""
job_sweep.py - sweep public ATS job boards (Greenhouse, Lever, Ashby) for
analytics-type roles that are remote or Denver/Colorado, extract pay, score
against your skills, and write everything to a CSV.

Usage:
    pip install requests
    python job_sweep.py --discover "Oscar Health" "Devoted Health" "Evolent"
    python job_sweep.py                  # sweep everything in BOARDS
    python job_sweep.py --min-pay 100000 # drop postings whose max pay is below this

Output: jobs_YYYY-MM-DD.csv, plus descriptions/ folder with one .txt per job
(so you can hand a description straight to Claude for resume tailoring).
"""
import argparse, csv, html, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import requests

# ---------------------------------------------------------------- CONFIG ----
# (platform, board_token, display name). Tokens are the slug in the careers URL:
#   greenhouse: boards.greenhouse.io/<token>  or job-boards.greenhouse.io/<token>
#   lever:      jobs.lever.co/<token>
#   ashby:      jobs.ashbyhq.com/<token>
# Only includedhealth was confirmed. Use --discover to verify/find the rest.
BOARDS = [
    ("lever", "includedhealth", "Included Health"),
    ("greenhouse", "oscar", "Oscar Health"),
    ("lever", "lyrahealth", "Lyra Health"),
    ("greenhouse", "mavenclinic", "Maven Clinic"),
    ("greenhouse", "swordhealth", "Sword Health"),
    ("lever", "aledade", "Aledade"),
    ("greenhouse", "zocdoc", "Zocdoc"),
    ("greenhouse", "doximity", "Doximity"),
    ("greenhouse", "flatironhealth", "Flatiron Health"),
    # ("greenhouse", "oscar", "Oscar Health"),        # unverified
    # ("greenhouse", "evolent", "Evolent"),           # unverified
]

TITLE_INCLUDE = re.compile(
    r"analy(st|tics)|insights|data scien|business intelligence|\bbi\b|"
    r"strateg|bizops|business operations|decision science|forward.deployed|"
    r"ai (enablement|automation)|automation", re.I)
TITLE_EXCLUDE = re.compile(
    r"intern\b|junior|\bjr\b|entry|associate analyst|actuar|security analyst|"
    r"software engineer|data engineer|machine learning engineer|recruit", re.I)

# Skills from your resume -> used for a rough relevance score.
SKILLS = ["snowflake", "dbt", "tableau", "python", "sql", "salesforce", "streamlit",
          "agentic", "ai", "llm", "stakeholder", "executive", "okr", "gtm",
          "segmentation", "dashboard", "forecast", "automation", "insights",
          "machine learning", "statistics", "aws", "git"]

LOCATION_OK = re.compile(r"remote|anywhere|denver|colorado|\bco\b|united states|\bus\b|usa", re.I)
UA = {"User-Agent": "job-sweep/1.0 (personal job search)"}

# ------------------------------------------------------------- FETCHERS -----
def strip_html(s):
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def get(url, params=None):
    r = requests.get(url, params=params, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_greenhouse(token):
    data = get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs", {"content": "true"})
    for j in data.get("jobs", []):
        pay = None
        for rng in j.get("pay_input_ranges") or []:
            if rng.get("min_cents") and rng.get("max_cents"):
                pay = (rng["min_cents"] // 100, rng["max_cents"] // 100)
                break
        yield dict(title=j.get("title", ""), location=(j.get("location") or {}).get("name", ""),
                   url=j.get("absolute_url", ""), desc=strip_html(j.get("content")),
                   pay=pay, posted=(j.get("updated_at") or "")[:10])

def fetch_lever(token):
    data = get(f"https://api.lever.co/v0/postings/{token}", {"mode": "json"})
    for j in data:
        cats = j.get("categories") or {}
        loc = " / ".join([cats.get("location") or ""] + (cats.get("allLocations") or []))
        sr = j.get("salaryRange") or {}
        pay = (int(sr["min"]), int(sr["max"])) if sr.get("min") and sr.get("max") \
            and sr.get("interval", "").endswith("year") else None
        desc = j.get("descriptionPlain", "") + " " + " ".join(
            (l.get("text", "") + " " + strip_html(l.get("content"))) for l in j.get("lists", []))
        desc += " " + (j.get("additionalPlain") or "")
        if j.get("workplaceType"):
            loc += " " + j["workplaceType"]
        ts = j.get("createdAt")
        yield dict(title=j.get("text", ""), location=loc, url=j.get("hostedUrl", ""),
                   desc=desc, pay=pay,
                   posted=date.fromtimestamp(ts / 1000).isoformat() if ts else "")

def fetch_ashby(token):
    data = get(f"https://api.ashbyhq.com/posting-api/job-board/{token}",
               {"includeCompensation": "true"})
    for j in data.get("jobs", []):
        loc = j.get("location", "") + (" Remote" if j.get("isRemote") else "")
        comp = (j.get("compensation") or {}).get("compensationTierSummary", "")
        yield dict(title=j.get("title", ""), location=loc, url=j.get("jobUrl", ""),
                   desc=(j.get("descriptionPlain") or "") + " " + comp,
                   pay=None, posted=(j.get("publishedAt") or "")[:10])

FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby}

# --------------------------------------------------------------- PARSING ----
_NUM = r"\$\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d)?\s?[kK])"
PAY_RE = re.compile(_NUM + r"\s*(?:-|–|—|to|and)\s*" + r"\$?\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d)?\s?[kK])")

def _to_int(s):
    s = s.replace(",", "").replace(" ", "").lower()
    return int(float(s[:-1]) * 1000) if s.endswith("k") else int(float(s))

def extract_pay(text):
    """Return (min, max) annual pay from free text, or None. Ignores hourly-looking values."""
    for m in PAY_RE.finditer(text):
        try:
            lo, hi = _to_int(m.group(1)), _to_int(m.group(2))
        except ValueError:
            continue
        if 40_000 <= lo <= hi <= 600_000:
            return lo, hi
    return None

def work_mode(location, desc):
    blob = f"{location} {desc[:1500]}".lower()
    if "hybrid" in blob:
        return "hybrid"
    if "remote" in blob or "anywhere" in blob:
        return "remote"
    return "onsite/unknown"

def colorado_ok(location, desc, mode):
    """Keep: remote roles not restricted to other states, or hybrid/onsite in Denver area."""
    loc = location.lower()
    if re.search(r"denver|colorado|boulder|\bco\b", loc):
        return True
    return mode == "remote" and bool(LOCATION_OK.search(loc) or not loc.strip())

def score(title, desc):
    blob = f"{title} {desc}".lower()
    hits = [s for s in SKILLS if re.search(rf"\b{re.escape(s)}\b", blob)]
    pts = len(hits)
    if re.search(r"senior|staff|lead|principal|manager", title, re.I):
        pts += 3
    if re.search(r"analytics engineer|data engineer", title, re.I):
        pts -= 3  # you said sewer work isn't the goal
    return pts, hits

def seniority(title):
    t = title.lower()
    if re.search(r"intern\b|junior|\bjr\b|entry", t): return "1 Entry"
    if re.search(r"vice president|\bvp\b|director|head of|chief", t): return "6 Director+"
    if re.search(r"manager|\bmgr\b", t): return "5 Manager"
    if re.search(r"principal|staff|lead\b", t): return "4 Staff/Lead"
    if re.search(r"senior|\bsr\b", t): return "3 Senior"
    return "2 Mid"

# ----------------------------------------------------------------- MAIN -----
def slug_variants(name):
    base = re.sub(r"[^a-z0-9 ]", "", name.lower())
    return list(dict.fromkeys([base.replace(" ", ""), base.replace(" ", "-"), base.split()[0]]))

def _probe(name):
    """Try every slug variant on every platform; return the first hit per platform."""
    variants = slug_variants(name)
    short = variants[-1] if " " in name.strip() else None
    hits = []
    for plat, fn in FETCHERS.items():
        for slug in variants:
            try:
                jobs = list(fn(slug))
            except Exception:
                continue
            if jobs:
                hits.append(dict(platform=plat, token=slug, name=name, n=len(jobs),
                                 sample=[j["title"] for j in jobs[:3]],
                                 short=(slug == short)))
                break
    return name, hits

def load_names(path):
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]

def load_boards(path):
    boards = list(BOARDS)
    if path and os.path.exists(path):
        have = {(p, t) for p, t, _ in boards}
        for b in json.load(open(path)):
            if (b["platform"], b["token"]) not in have:
                boards.append((b["platform"], b["token"], b["name"]))
    return boards

def discover(names, outfile=None, workers=6):
    print(f"Probing {len(names)} companies on Greenhouse / Lever / Ashby...\n")
    found, missed = [], []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for name, hits in ex.map(_probe, names):
            if not hits:
                missed.append(name)
                continue
            for h in hits:
                flag = "  <-- short slug, verify it's the right company" if h["short"] else ""
                print(f"  {h['name']:28s} {h['platform']:10s} {h['token']:24s} {h['n']:4d} jobs  e.g. {h['sample'][0]}{flag}")
                found.append(h)
    print(f"\n{len(found)} boards found for {len(names) - len(missed)} companies.")
    print("No match (likely Workday/iCIMS/own site):", ", ".join(missed) or "none")
    if outfile:
        old = json.load(open(outfile)) if os.path.exists(outfile) else []
        have = {(b["platform"], b["token"]) for b in old}
        old += [dict(platform=h["platform"], token=h["token"], name=h["name"])
                for h in found if (h["platform"], h["token"]) not in have]
        json.dump(old, open(outfile, "w"), indent=1)
        print(f"Saved {len(old)} boards -> {outfile}")

def sweep(min_pay, outdir, show_all=False, boards=BOARDS):
    rows, failed = [], []
    for plat, token, name in boards:
        try:
            jobs = list(FETCHERS[plat](token))
        except Exception as e:
            failed.append(f"{name} ({plat}/{token}): {e}")
            continue
        kept = 0
        for j in jobs:
            mode = work_mode(j["location"], j["desc"])
            if not show_all:
                if not TITLE_INCLUDE.search(j["title"]) or TITLE_EXCLUDE.search(j["title"]):
                    continue
                if not colorado_ok(j["location"], j["desc"], mode):
                    continue
            pay = j["pay"] or extract_pay(j["desc"])
            if min_pay and pay and pay[1] < min_pay:
                continue
            pts, hits = score(j["title"], j["desc"])
            rows.append(dict(score=pts, company=name, title=j["title"], seniority=seniority(j["title"]), mode=mode,
                             location=j["location"].strip(), pay_min=pay[0] if pay else "",
                             pay_max=pay[1] if pay else "", posted_or_updated=j["posted"],
                             matched_skills=", ".join(hits), url=j["url"], _desc=j["desc"]))
            kept += 1
        print(f"{name:28s} {len(jobs):4d} postings, {kept:3d} kept")
        time.sleep(0.5)

    rows.sort(key=lambda r: -r["score"])
    os.makedirs(os.path.join(outdir, "descriptions"), exist_ok=True)
    path = os.path.join(outdir, f"jobs_{date.today().isoformat()}.csv")
    fields = [k for k in rows[0] if k != "_desc"] if rows else []
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, r in enumerate(rows):
            fn = f"{i:03d}_{re.sub(r'[^A-Za-z0-9]+', '_', r['company'] + '_' + r['title'])[:80]}.txt"
            with open(os.path.join(outdir, "descriptions", fn), "w", encoding="utf-8") as d:
                d.write(f"{r['company']} - {r['title']}\n{r['url']}\n\n{r['_desc']}\n")
            w.writerow({k: r[k] for k in fields})
    print(f"\nWrote {len(rows)} jobs -> {path}")
    if failed:
        print("\nBoards that failed (check the token):")
        for line in failed:
            print("  -", line)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", nargs="+", metavar="COMPANY")
    ap.add_argument("--discover-file", metavar="FILE", help="text file, one company name per line")
    ap.add_argument("--boards-file", default="data/boards.json", help="where discovered boards are saved/loaded")
    ap.add_argument("--min-pay", type=int, default=0, help="drop jobs whose max pay is below this")
    ap.add_argument("--all", action="store_true", help="skip title/location filters; keep every job")
    ap.add_argument("--out", default="output")
    a = ap.parse_args()
    if a.discover_file:
        discover(load_names(a.discover_file), a.boards_file)
    elif a.discover:
        discover(a.discover, a.boards_file)
    else:
        boards = load_boards(a.boards_file)
        print(f"Sweeping {len(boards)} boards\n")
        sweep(a.min_pay, a.out, a.all, boards)
