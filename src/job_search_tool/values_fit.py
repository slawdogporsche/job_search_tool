"""Evidence-backed company values fit, not a fabricated reputation rating.

Input is JSON Lines with company, dimension, score (0..5), source_url,
observed_at (YYYY-MM-DD), note, and source_type.
"""
import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

WEIGHTS = {
    'patient_outcomes': .30,
    'business_model_alignment': .25,
    'employee_experience': .20,
    'transparency_ethics': .15,
    'work_life_balance': .10,
}


def validate(record):
    required = ['company', 'dimension', 'score', 'source_url', 'observed_at', 'note']
    missing = [field for field in required if record.get(field) in (None, '')]
    if missing:
        raise ValueError(f'Missing evidence fields: {missing}')
    if record['dimension'] not in WEIGHTS:
        raise ValueError(f'Unknown dimension: {record["dimension"]}')
    score = float(record['score'])
    if not 0 <= score <= 5:
        raise ValueError('Evidence score must be between 0 and 5')
    url = urlparse(record['source_url'])
    if url.scheme not in ('http', 'https') or not url.netloc:
        raise ValueError('Must supply a verifiable source URL')
    date.fromisoformat(record['observed_at'])
    return score


def summarize(evidence, min_dimensions=3):
    """Weighted score over available dimensions; insufficient coverage -> None."""
    grouped = defaultdict(lambda: defaultdict(list))
    for item in evidence:
        value = validate(item)
        grouped[item['company'].strip()][item['dimension']].append(value)
    results = []
    for company, dimensions in sorted(grouped.items()):
        present = set(dimensions)
        coverage = sum(WEIGHTS[d] for d in present)
        numerator = sum((sum(dimensions[d]) / len(dimensions[d])) * WEIGHTS[d]
                        for d in present)
        sufficient = len(present) >= min_dimensions and coverage >= .60
        results.append({'company': company,
                        'values_fit_100': round(20 * numerator / coverage, 1) if sufficient else '',
                        'coverage_pct': round(100 * coverage, 1),
                        'dimensions_evaluated': len(present),
                        'evidence_items': sum(map(len, dimensions.values())),
                        'status': 'scored' if sufficient else 'insufficient evidence'})
    return results


def main():
    parser = argparse.ArgumentParser(description='Score employer values using URL-cited evidence')
    parser.add_argument('--evidence', required=True, help='JSONL file of sourced claims')
    parser.add_argument('--output', default='output/company_values.csv')
    args = parser.parse_args()
    with open(args.evidence, encoding='utf-8') as f:
        records = [json.loads(line) for line in f if line.strip()]
    results = summarize(records)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        columns = ['company', 'values_fit_100', 'coverage_pct', 'dimensions_evaluated',
                   'evidence_items', 'status']
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)
    print(f'Wrote {len(results)} companies to {path}')


if __name__ == '__main__':
    main()
