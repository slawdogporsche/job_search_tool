"""Human-labeled filter audit; avoids declaring precision without ground truth."""
import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path


def key(row):
    """Stable identifier for a job across independent CSV exports."""
    return (row.get('url') or row.get('job_url') or row.get('source_id') or
            f"{row.get('company','')}|{row.get('title','')}|{row.get('location','')}").strip().lower()


def load(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def build_review_sample(all_jobs, selected, n=30, seed=7):
    """Stratify positives and negatives so exclusion errors can be measured."""
    selected_keys = {key(r) for r in selected}
    groups = {'included': [], 'excluded': []}
    for row in all_jobs:
        group = 'included' if key(row) in selected_keys else 'excluded'
        groups[group].append(row)
    rng = random.Random(seed)
    sample = []
    for group, rows in groups.items():
        pool = rng.sample(rows, min(len(rows), n))
        for row in pool:
            sample.append({'job_key': key(row), 'filter_result': group,
                           'company': row.get('company', ''), 'title': row.get('title', ''),
                           'location': row.get('location', ''),
                           'url': row.get('url') or row.get('job_url', ''),
                           'human_relevant': '', 'reason': ''})
    return sample


def metrics(review_rows):
    counts = Counter()
    for r in review_rows:
        label = str(r.get('human_relevant', '')).strip().lower()
        if label not in ('yes', 'no'):
            continue
        included = r['filter_result'] == 'included'
        relevant = label == 'yes'
        counts['tp' if included and relevant else
               'fp' if included else 'fn' if relevant else 'tn'] += 1
    precision_denom = counts['tp'] + counts['fp']
    recall_denom = counts['tp'] + counts['fn']
    return {'labeled': sum(counts.values()), 'confusion_matrix': dict(counts),
            'sample_precision': counts['tp'] / precision_denom if precision_denom else None,
            'sample_recall': counts['tp'] / recall_denom if recall_denom else None,
            'warning': 'Case-control stratified sampling: recall is not population recall. '
                       'For population metrics, weight by actual included/excluded counts.'}


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('sample')
    p.add_argument('--all', required=True, dest='all_csv')
    p.add_argument('--selected', required=True)
    p.add_argument('--per-group', type=int, default=30)
    p.add_argument('--output', default='output/filter_review.csv')
    p = subs.add_parser('report')
    p.add_argument('--review', required=True)
    args = parser.parse_args()
    if args.command == 'sample':
        samples = build_review_sample(load(args.all_csv), load(args.selected), args.per_group)
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['job_key', 'filter_result', 'company',
                 'title', 'location', 'url', 'human_relevant', 'reason'])
            writer.writeheader()
            writer.writerows(samples)
        print(f'Wrote {len(samples)} jobs for manual review to {path}')
    else:
        print(json.dumps(metrics(load(args.review)), indent=2))


if __name__ == '__main__':
    main()
