from job_search_tool.filter_audit import build_review_sample, metrics


def test_sample_covers_exclusions():
    rows = [{'url': str(i), 'title': 'Analyst'} for i in range(10)]
    sample = build_review_sample(rows, rows[:3], n=2)
    assert len(sample) == 4
    assert {r['filter_result'] for r in sample} == {'included', 'excluded'}


def test_metrics():
    rows = [
        {'filter_result': 'included', 'human_relevant': 'yes'},
        {'filter_result': 'included', 'human_relevant': 'no'},
        {'filter_result': 'excluded', 'human_relevant': 'yes'},
        {'filter_result': 'excluded', 'human_relevant': 'no'},
    ]
    result = metrics(rows)
    assert result['sample_precision'] == .5
    assert result['sample_recall'] == .5
