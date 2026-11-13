import csv
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from job_search_tool.values_fit import summarize, validate


def record(dim, score, company='Example'):
    return {'company': company, 'dimension': dim, 'score': score,
            'source_url': 'https://example.org/report', 'observed_at': '2026-11-01',
            'note': 'Human-reviewed evidence summary'}


def evidence(score=4):
    return [record(dim, score) for dim in ('patient_outcomes', 'business_model_alignment',
                                          'employee_experience', 'transparency_ethics')]


def test_insufficient_evidence_withholds_score():
    out = summarize([record('patient_outcomes', 5)])[0]
    assert out['status'] == 'insufficient evidence'
    assert out['values_fit_100'] == ''
    assert out['coverage_pct'] == 30


def test_weighted_score_and_multi_company_grouping():
    items = evidence(4) + evidence(2)
    for row in items[4:]:
        row['company'] = 'Different'
    rows = summarize(items)
    assert len(rows) == 2
    assert {r['company']: r['values_fit_100'] for r in rows} == {'Example': 80, 'Different': 40}
    assert all(r['coverage_pct'] == 90 for r in rows)


def test_multiple_observations_are_averaged_within_dimension():
    items = evidence(4)
    other = record('patient_outcomes', 2)
    other['source_url'] = 'https://another.example.org/report'
    items.append(other)
    assert summarize(items)[0]['values_fit_100'] == pytest.approx(73.3, abs=.05)


def test_duplicate_evidence_and_company_case_are_normalized():
    items = evidence(4)
    duplicate = dict(items[0], company='example')
    result = summarize(items + [duplicate])[0]
    assert result['company'] == 'Example'
    assert result['evidence_items'] == 4
    assert result['values_fit_100'] == 80


@pytest.mark.parametrize('field,value', [
    ('source_url', ''), ('source_url', 'ftp://example.com'),
    ('source_url', 'https://'), ('source_url', 'https://bad url.com'),
    ('note', ' '), ('company', ''), ('dimension', 'invented'),
    ('score', -1), ('score', 6), ('score', 'nan'), ('score', 'inf'),
    ('score', 'not a number'), ('observed_at', 'not-a-date'),
    ('observed_at', (date.today() + timedelta(days=1)).isoformat()),
])
def test_invalid_evidence_rejected(field, value):
    with pytest.raises(ValueError):
        validate({**record('patient_outcomes', 3), field: value})


def test_empty_input_and_min_dimensions():
    assert summarize([]) == []
    with pytest.raises(ValueError, match='min_dimensions'):
        summarize([], min_dimensions=0)


def test_cli_round_trip(tmp_path):
    source = tmp_path / 'evidence.jsonl'
    output = tmp_path / 'values.csv'
    source.write_text('\n'.join(json.dumps(r) for r in evidence()) + '\n', encoding='utf-8')
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
    cmd = [sys.executable, '-m', 'job_search_tool.values_fit', '--evidence', str(source),
           '--output', str(output)]
    result = subprocess.run(cmd, env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    with output.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1 and rows[0]['values_fit_100'] == '80.0'
    source.write_text(json.dumps({**record('patient_outcomes', 3), 'score': 'nan'}) + '\n')
    failure = subprocess.run(cmd, env=env, text=True, capture_output=True)
    assert failure.returncode != 0 and 'evidence.jsonl:1' in failure.stderr
