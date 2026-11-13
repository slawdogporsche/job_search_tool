import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from job_search_tool.filter_audit import build_review_sample, metrics


def job(i):
    return {'url': f'https://example.org/{i}', 'company': 'Example',
            'title': f'Analyst {i}', 'location': 'Denver'}


def test_inclusion_and_exclusion_classification():
    rows = [job(i) for i in range(5)]
    out = build_review_sample(rows, rows[:2], n=10)
    assert {r['job_key'] for r in out if r['filter_result'] == 'included'} == {job(i)['url'] for i in range(2)}
    assert {r['job_key'] for r in out if r['filter_result'] == 'excluded'} == {job(i)['url'] for i in range(2, 5)}


def test_seed_is_deterministic():
    rows = [job(i) for i in range(30)]
    assert build_review_sample(rows, rows[:10], 4, seed=42) == build_review_sample(rows, rows[:10], 4, seed=42)


def test_confusion_matrix_precision_recall():
    rows = [
        {'filter_result': 'included', 'human_relevant': 'yes'},
        {'filter_result': 'included', 'human_relevant': 'yes'},
        {'filter_result': 'included', 'human_relevant': 'no'},
        {'filter_result': 'excluded', 'human_relevant': 'yes'},
        {'filter_result': 'excluded', 'human_relevant': 'no'},
    ]
    m = metrics(rows)
    assert m['confusion_matrix'] == {'tp': 2, 'fp': 1, 'fn': 1, 'tn': 1}
    assert m['sample_precision'] == pytest.approx(2 / 3)
    assert m['sample_recall'] == pytest.approx(2 / 3)


def test_blank_labels_ignored():
    m = metrics([{'filter_result': 'included', 'human_relevant': ''},
                 {'filter_result': 'excluded', 'human_relevant': 'yes'}])
    assert m['labeled'] == 1
    assert m['confusion_matrix']['fn'] == 1


def test_invalid_labels_rejected():
    with pytest.raises(ValueError, match='human_relevant'):
        metrics([{'filter_result': 'included', 'human_relevant': 'maybe'}])
    with pytest.raises(ValueError, match='filter_result'):
        metrics([{'filter_result': 'includedd', 'human_relevant': 'yes'}])


def test_empty_inputs_and_zero_denominators():
    assert build_review_sample([], [], 5) == []
    m = metrics([])
    assert m['sample_precision'] is None and m['sample_recall'] is None
    m = metrics([{'filter_result': 'excluded', 'human_relevant': 'no'}])
    assert m['sample_precision'] is None and m['sample_recall'] is None
    with pytest.raises(ValueError, match='Sample size'):
        build_review_sample([], [], 0)


def test_deduplicates_and_checks_missing_shortlist_jobs():
    rows = [job(0), job(0), job(1)]
    out = build_review_sample(rows, [job(0)], 10)
    assert len(out) == 2
    assert len({r['job_key'] for r in out}) == 2
    with pytest.raises(ValueError, match='absent'):
        build_review_sample(rows, [job(99)], 10)


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['url', 'company', 'title', 'location'])
        writer.writeheader()
        writer.writerows(rows)


def test_cli_end_to_end(tmp_path):
    all_csv, selected_csv, review_csv = [tmp_path / n for n in ('all.csv', 'selected.csv', 'review.csv')]
    write_csv(all_csv, [job(0), job(1)])
    write_csv(selected_csv, [job(0)])
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
    command = [sys.executable, '-m', 'job_search_tool.filter_audit']
    subprocess.run(command + ['sample', '--all', str(all_csv), '--selected', str(selected_csv),
                              '--output', str(review_csv)], env=env, check=True, capture_output=True, text=True)
    with review_csv.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    for row in rows:
        row['human_relevant'] = 'yes' if row['filter_result'] == 'included' else 'no'
    with review_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = subprocess.run(command + ['report', '--review', str(review_csv)],
                            env=env, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)['sample_precision'] == 1
