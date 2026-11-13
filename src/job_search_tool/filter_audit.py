"""Human-labeled diagnostic audit of job filters (not population-level metrics)."""
import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

FIELDS = ['job_key', 'filter_result', 'company', 'title', 'location', 'url',
          'human_relevant', 'reason']


def key(row):
    """Identify a posting by URL, source ID, or company/title/location fallback."""
    return str(row.get('url') or row.get('job_url') or row.get('source_id') or
               f"{row.get('company', '')}|{row.get('title', '')}|{row.get('location', '')}").strip().lower()


def load(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def build_review_sample(all_jobs, selected, n=30, seed=7):
    """Sample unique included/excluded postings for manual relevance labeling."""
    if n < 1:
        raise ValueError('Sample size per group must be at least 1')
    selected_keys = {key(row) for row in selected}
    distinct = {key(row): row for row in reversed(all_jobs)}
    missing = selected_keys - distinct.keys()
    if missing:
        raise ValueError(f'{len(missing)} shortlisted postings absent from the all-jobs input')
    groups = {'included': [], 'excluded': []}
    for job_key, row in distinct.items():
        groups['included' if job_key in selected_keys else 'excluded'].append(row)
    rng = random.Random(seed)
    sample = []
    for group, rows in groups.items():
        for row in rng.sample(rows, min(len(rows), n)):
            sample.append({'job_key': key(row), 'filter_result': group,
                           'company': row.get('company', ''), 'title': row.get('title', ''),
                           'location': row.get('location', ''),
                           'url': row.get('url') or row.get('job_url', ''),
                           'human_relevant': '', 'reason': ''})
    return sample


def metrics(review_rows):
    counts = Counter({'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0})
    for index, row in enumerate(review_rows, start=1):
        classification = str(row.get('filter_result', '')).strip().lower()
        if classification not in ('included', 'excluded'):
            raise ValueError(f'Row {index}: invalid filter_result {classification!r}')
        label = str(row.get('human_relevant') or '').strip().lower()
        if not label:
            continue
        if label not in ('yes', 'no'):
            raise ValueError(f'Row {index}: invalid human_relevant {label!r}; use yes/no or leave blank')
        included = classification == 'included'
        relevant = label == 'yes'
        counts['tp' if included and relevant else
               'fp' if included else 'fn' if relevant else 'tn'] += 1
    precision_denom = counts['tp'] + counts['fp']
    recall_denom = counts['tp'] + counts['fn']
    return {'labeled': sum(counts.values()), 'confusion_matrix': dict(counts),
            'sample_precision': counts['tp'] / precision_denom if precision_denom else None,
            'sample_recall': counts['tp'] / recall_denom if recall_denom else None,
            'warning': 'This stratified case-control sample is diagnostic; sample recall/precision '
                       'do not necessarily represent population-level filter performance.'}


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('sample')
    p.add_argument('--all', required=True, dest='all_csv')
    p.add_argument('--selected', required=True)
    p.add_argument('--per-group', type=int, default=30)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--output', default='output/filter_review.csv')
    p = subs.add_parser('report')
    p.add_argument('--review', required=True)
    args = parser.parse_args()
    if args.command == 'sample':
        samples = build_review_sample(load(args.all_csv), load(args.selected), args.per_group, args.seed)
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(samples)
        print(f'Wrote {len(samples)} jobs for manual review to {path}')
    else:
        print(json.dumps(metrics(load(args.review)), indent=2))


if __name__ == '__main__':
    main()
