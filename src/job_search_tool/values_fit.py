"""Score manually reviewed, URL-cited company values evidence (no web scraping)."""
import argparse
import csv
import json
import math
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
FIELDS = ['company', 'values_fit_100', 'coverage_pct', 'dimensions_evaluated',
          'evidence_items', 'status']


def validate(record):
    """Check structure, provenance fields and numeric score; not factual source content."""
    if not isinstance(record, dict):
        raise ValueError('Evidence must be a JSON object')
    required = ('company', 'dimension', 'score', 'source_url', 'observed_at', 'note')
    missing = [name for name in required
               if name not in record or not str(record[name] or '').strip()]
    if missing:
        raise ValueError(f'Missing or blank evidence fields: {missing}')
    if record['dimension'] not in WEIGHTS:
        raise ValueError(f'Unknown dimension: {record["dimension"]}')
    try:
        score = float(record['score'])
    except (ValueError, TypeError) as exc:
        raise ValueError('Evidence score must be a number between 0 and 5') from exc
    if not math.isfinite(score) or not 0 <= score <= 5:
        raise ValueError('Evidence score must be finite and between 0 and 5')
    url = record['source_url']
    if not isinstance(url, str):
        raise ValueError('Source URL must be a string')
    parsed = urlparse(url)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or
            any(char.isspace() for char in url)):
        raise ValueError('Must supply an absolute http(s) source URL')
    try:
        observed = date.fromisoformat(str(record['observed_at']))
    except ValueError as exc:
        raise ValueError('observed_at must be YYYY-MM-DD') from exc
    if observed.isoformat() != record['observed_at']:
        raise ValueError('observed_at must be YYYY-MM-DD')
    if observed > date.today():
        raise ValueError('observed_at cannot be in the future')
    return score


def summarize(evidence, min_dimensions=3):
    """Average independent observations within dimensions, then apply weights.

    Coverage describes dimensions assessed, NOT source quality or completeness.
    """
    if not isinstance(min_dimensions, int) or not 1 <= min_dimensions <= len(WEIGHTS):
        raise ValueError('min_dimensions must be between 1 and 5')
    groups = defaultdict(lambda: defaultdict(list))
    display_names = {}
    seen = set()
    for record in evidence:
        score = validate(record)
        name = record['company'].strip()
        canonical = name.casefold()
        display_names.setdefault(canonical, name)
        # Avoid duplicate source observations artificially overpowering other sources.
        fingerprint = (canonical, record['dimension'], record['source_url'].strip(),
                       record['observed_at'], record['note'].strip(), score)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        groups[canonical][record['dimension']].append(score)
    results = []
    for canonical in sorted(groups):
        dimensions = groups[canonical]
        coverage = sum(WEIGHTS[d] for d in dimensions)
        numerator = sum(WEIGHTS[d] * sum(scores) / len(scores)
                        for d, scores in dimensions.items())
        sufficient = len(dimensions) >= min_dimensions and coverage >= .60 - 1e-9
        results.append({'company': display_names[canonical],
                        'values_fit_100': round(20 * numerator / coverage, 1) if sufficient else '',
                        'coverage_pct': round(coverage * 100, 1),
                        'dimensions_evaluated': len(dimensions),
                        'evidence_items': sum(len(scores) for scores in dimensions.values()),
                        'status': 'scored' if sufficient else 'insufficient evidence'})
    return results


def read_evidence(path):
    records = []
    with open(path, encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                validate(item)
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                raise ValueError(f'{path}:{lineno}: {exc}') from exc
            records.append(item)
    return records


def main():
    parser = argparse.ArgumentParser(description='Score employer values using cited evidence')
    parser.add_argument('--evidence', required=True, help='JSONL of manually assessed observations')
    parser.add_argument('--output', default='output/company_values.csv')
    args = parser.parse_args()
    try:
        results = summarize(read_evidence(args.evidence))
    except ValueError as exc:
        parser.error(str(exc))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    print(f'Wrote {len(results)} companies to {path}')


if __name__ == '__main__':
    main()
