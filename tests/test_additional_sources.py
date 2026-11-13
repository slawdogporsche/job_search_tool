from job_search_tool.additional_sources import adzuna_search, usajobs_search


class Response:
    def __init__(self, data):
        self.data = data
    def raise_for_status(self):
        pass
    def json(self):
        return self.data


class Session:
    def __init__(self, data):
        self.data = data
    def get(self, *args, **kwargs):
        return Response(self.data)


def test_adzuna(monkeypatch):
    monkeypatch.setenv('ADZUNA_APP_ID', 'a')
    monkeypatch.setenv('ADZUNA_APP_KEY', 'b')
    out = adzuna_search('analytics', per_page=50, session=Session({'results': [
        {'id': 1, 'title': 'Analyst', 'company': {'display_name': 'Example'},
         'location': {'display_name': 'Denver'}, 'salary_min': 120000}]}))
    assert out[0]['source'] == 'adzuna'
    assert out[0]['company'] == 'Example'


def test_usajobs(monkeypatch):
    monkeypatch.setenv('USAJOBS_API_KEY', 'a')
    monkeypatch.setenv('USAJOBS_EMAIL', 'test@example.com')
    data = {'SearchResult': {'SearchResultItems': [{'MatchedObjectDescriptor': {
        'PositionID': '123', 'PositionTitle': 'Data Analyst',
        'PositionRemuneration': [{'MinimumRange': '100000', 'MaximumRange': '140000'}]
    }}]}}
    out = usajobs_search('analytics', session=Session(data))
    assert out[0]['salary_max'] == '140000'
