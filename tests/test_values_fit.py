import pytest
from job_search_tool.values_fit import summarize


def record(dim, score):
    return {'company': 'Example', 'dimension': dim, 'score': score,
            'source_url': 'https://example.org/report', 'observed_at': '2026-11-01',
            'note': 'Human-verified source excerpt'}


def test_coverage_prevents_unfounded_score():
    assert summarize([record('patient_outcomes', 5)])[0]['status'] == 'insufficient evidence'


def test_weighted_score():
    items = [record(d, 4) for d in ('patient_outcomes', 'business_model_alignment',
                                    'employee_experience', 'transparency_ethics')]
    result = summarize(items)[0]
    assert result['values_fit_100'] == 80
    assert result['status'] == 'scored'


def test_missing_provenance_rejected():
    with pytest.raises(ValueError):
        summarize([{**record('patient_outcomes', 5), 'source_url': ''}])
