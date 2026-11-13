import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

from job_search_tool.additional_sources import adzuna_search, usajobs_search, write_jobs, FIELDS


class Response:
    def __init__(self, data, fail=False):
        self.data, self.fail = data, fail

    def raise_for_status(self):
        if self.fail:
            raise RuntimeError('API HTTP error')

    def json(self):
        return self.data


class Session:
    def __init__(self, *pages, fail=False):
        self.pages, self.calls, self.fail = list(pages), [], fail

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return Response(self.pages.pop(0), self.fail)


def credentials(monkeypatch):
    monkeypatch.setenv('ADZUNA_APP_ID', 'a')
    monkeypatch.setenv('ADZUNA_APP_KEY', 'b')
    monkeypatch.setenv('USAJOBS_API_KEY', 'k')
    monkeypatch.setenv('USAJOBS_EMAIL', 'test@example.com')


def test_adzuna_parsing_and_query(monkeypatch):
    credentials(monkeypatch)
    s = Session({'results': [{'id': 1, 'title': 'Analyst', 'company': {'display_name': 'HealthCo'},
                              'location': {'display_name': 'Denver'}, 'salary_min': 120000}]})
    jobs = adzuna_search('analytics', session=s)
    assert jobs[0]['source_id'] == '1' and jobs[0]['company'] == 'HealthCo'
    assert s.calls[0][1]['params']['what'] == 'analytics'
    assert s.calls[0][1]['timeout'] == 30


def test_usajobs_annual_and_hourly_salaries(monkeypatch):
    credentials(monkeypatch)
    items = [{'MatchedObjectDescriptor': {'PositionID': str(i), 'PositionTitle': 'Analyst',
               'PositionRemuneration': [{'RateIntervalCode': rate, 'MinimumRange': str(lo),
                                        'MaximumRange': str(hi)}]}}
             for i, rate, lo, hi in [(1, 'PA', 100000, 140000), (2, 'PH', 45, 70)]]
    s = Session({'SearchResult': {'SearchResultItems': items}})
    jobs = usajobs_search('analytics', session=s)
    assert jobs[0]['salary_max'] == '140000'
    assert jobs[1]['salary_min'] == '' and jobs[1]['salary_max'] == ''
    assert s.calls[0][1]['headers']['Authorization-Key'] == 'k'


def test_pagination_and_deduplication(monkeypatch):
    credentials(monkeypatch)
    s = Session({'results': [{'id': 1}, {'id': 2}]},
                {'results': [{'id': 2}, {'id': 3}]}, {'results': []})
    jobs = adzuna_search('analytics', pages=3, per_page=2, session=s)
    assert [j['source_id'] for j in jobs] == ['1', '2', '3']
    assert len(s.calls) == 3


def test_invalid_pagination_and_missing_credentials(monkeypatch):
    with pytest.raises(ValueError, match='pages'):
        adzuna_search('x', pages=0)
    with pytest.raises(ValueError, match='per_page'):
        usajobs_search('x', per_page=0)
    monkeypatch.delenv('ADZUNA_APP_ID', raising=False)
    monkeypatch.delenv('ADZUNA_APP_KEY', raising=False)
    with pytest.raises(ValueError, match='ADZUNA_APP_ID'):
        adzuna_search('x')


def test_empty_response_and_http_failure(monkeypatch):
    credentials(monkeypatch)
    assert usajobs_search('x', session=Session({'SearchResult': {}})) == []
    with pytest.raises(RuntimeError, match='HTTP'):
        adzuna_search('x', session=Session({'results': []}, fail=True))


def test_export_schema(tmp_path):
    p = tmp_path / 'export.csv'
    write_jobs([{'source': 'adzuna', 'title': 'Analyst', 'unused': 1}], p)
    with p.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDS
        assert list(reader)[0]['title'] == 'Analyst'


def test_cli_rejects_bad_page_and_no_credentials(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
    env.update(ADZUNA_APP_ID='a', ADZUNA_APP_KEY='b')
    result = subprocess.run([sys.executable, '-m', 'job_search_tool.additional_sources',
                             '--source', 'adzuna', '--pages', '0', '--output', str(tmp_path / 'bad.csv')],
                            capture_output=True, text=True, env=env)
    assert result.returncode != 0 and 'pages' in result.stderr
    assert not (tmp_path / 'bad.csv').exists()
