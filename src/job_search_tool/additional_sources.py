"""Optional Adzuna and USAJOBS searches; independent of the existing sweep."""
import argparse
import csv
import os
from pathlib import Path

import requests

FIELDS = ['source', 'source_id', 'company', 'title', 'location', 'url',
          'description', 'salary_min', 'salary_max', 'created']


def _positive(name, value, maximum):
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= maximum:
        raise ValueError(f'{name} must be an integer between 1 and {maximum}')


def _text(value):
    return '' if value is None else str(value)


def adzuna_search(query, location='Denver', pages=1, per_page=50, session=None):
    """Search Adzuna US listings; preserve salary fields as supplied by provider."""
    _positive('pages', pages, 20)
    _positive('per_page', per_page, 50)
    app_id, app_key = os.getenv('ADZUNA_APP_ID'), os.getenv('ADZUNA_APP_KEY')
    if not app_id or not app_key:
        raise ValueError('Set ADZUNA_APP_ID and ADZUNA_APP_KEY')
    session = session or requests.Session()
    jobs, seen = [], set()
    for page in range(1, pages + 1):
        response = session.get(
            f'https://api.adzuna.com/v1/api/jobs/us/search/{page}',
            params={'app_id': app_id, 'app_key': app_key, 'what': query,
                    'where': location, 'results_per_page': per_page,
                    'content-type': 'application/json'}, timeout=30)
        response.raise_for_status()
        results = response.json().get('results') or []
        for item in results:
            ident = _text(item.get('id'))
            url = _text(item.get('redirect_url'))
            dedup = ident or url
            if dedup and dedup in seen:
                continue
            if dedup:
                seen.add(dedup)
            jobs.append({'source': 'adzuna', 'source_id': ident,
                         'company': (item.get('company') or {}).get('display_name') or '',
                         'title': item.get('title') or '',
                         'location': (item.get('location') or {}).get('display_name') or '',
                         'url': url, 'description': item.get('description') or '',
                         'salary_min': item.get('salary_min') or '',
                         'salary_max': item.get('salary_max') or '',
                         'created': item.get('created') or ''})
        if len(results) < per_page:
            break
    return jobs


def usajobs_search(query, location='Denver, Colorado', pages=1, per_page=100, session=None):
    """Search USAJOBS; exclude non-annual salary amounts from annual salary fields."""
    _positive('pages', pages, 20)
    _positive('per_page', per_page, 500)
    key, email = os.getenv('USAJOBS_API_KEY'), os.getenv('USAJOBS_EMAIL')
    if not key or not email:
        raise ValueError('Set USAJOBS_API_KEY and USAJOBS_EMAIL')
    session = session or requests.Session()
    jobs, seen = [], set()
    for page in range(1, pages + 1):
        response = session.get(
            'https://data.usajobs.gov/api/Search',
            headers={'Host': 'data.usajobs.gov', 'User-Agent': email,
                     'Authorization-Key': key},
            params={'Keyword': query, 'LocationName': location,
                    'Page': page, 'ResultsPerPage': per_page}, timeout=30)
        response.raise_for_status()
        results = (response.json().get('SearchResult') or {}).get('SearchResultItems') or []
        for wrapper in results:
            item = wrapper.get('MatchedObjectDescriptor') or {}
            ident = _text(item.get('PositionID'))
            url = _text(item.get('PositionURI'))
            dedup = ident or url
            if dedup and dedup in seen:
                continue
            if dedup:
                seen.add(dedup)
            details = (item.get('UserArea') or {}).get('Details') or {}
            salary = item.get('PositionRemuneration') or {}
            if isinstance(salary, list):
                salary = salary[0] if salary else {}
            salary = salary or {}
            rate = _text(salary.get('RateIntervalCode')).lower()
            annual = rate in ('pa', 'per year', 'year', 'annual', 'annually')
            jobs.append({'source': 'usajobs', 'source_id': ident,
                         'company': item.get('OrganizationName') or '',
                         'title': item.get('PositionTitle') or '',
                         'location': item.get('PositionLocationDisplay') or '',
                         'url': url,
                         'description': details.get('JobSummary') or '',
                         'salary_min': (salary.get('MinimumRange') or '') if annual else '',
                         'salary_max': (salary.get('MaximumRange') or '') if annual else '',
                         'created': item.get('PublicationStartDate') or ''})
        if len(results) < per_page:
            break
    return jobs


def write_jobs(jobs, filename):
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(jobs)


def main():
    parser = argparse.ArgumentParser(description='Search additional job APIs')
    parser.add_argument('--source', choices=['adzuna', 'usajobs'], required=True)
    parser.add_argument('--query', default='healthcare analytics')
    parser.add_argument('--location', default=None)
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--output', default='output/additional_jobs.csv')
    args = parser.parse_args()
    fn = adzuna_search if args.source == 'adzuna' else usajobs_search
    default_location = 'Denver' if args.source == 'adzuna' else 'Denver, Colorado'
    try:
        jobs = fn(args.query, location=args.location or default_location, pages=args.pages)
    except ValueError as exc:
        parser.error(str(exc))
    write_jobs(jobs, args.output)
    print(f'Wrote {len(jobs)} {args.source} jobs to {args.output}')


if __name__ == '__main__':
    main()
