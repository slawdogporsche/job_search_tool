"""Opt-in searches of Adzuna and USAJOBS. Run with --help for usage."""
import argparse
import csv
import os
from pathlib import Path

import requests


FIELDS = ['source', 'source_id', 'company', 'title', 'location', 'url',
          'description', 'salary_min', 'salary_max', 'created']


def adzuna_search(query, location='Denver', pages=1, per_page=50, session=None):
    """Search Adzuna US job listings using credentials from the environment."""
    app_id, app_key = os.getenv('ADZUNA_APP_ID'), os.getenv('ADZUNA_APP_KEY')
    if not app_id or not app_key:
        raise ValueError('Set ADZUNA_APP_ID and ADZUNA_APP_KEY')
    session = session or requests.Session()
    jobs = []
    for page in range(1, pages + 1):
        response = session.get(
            f'https://api.adzuna.com/v1/api/jobs/us/search/{page}',
            params={'app_id': app_id, 'app_key': app_key, 'what': query,
                    'where': location, 'results_per_page': per_page,
                    'content-type': 'application/json'}, timeout=30)
        response.raise_for_status()
        results = response.json().get('results', [])
        for item in results:
            jobs.append({'source': 'adzuna', 'source_id': str(item.get('id', '')),
                         'company': (item.get('company') or {}).get('display_name', ''),
                         'title': item.get('title', ''),
                         'location': (item.get('location') or {}).get('display_name', ''),
                         'url': item.get('redirect_url', ''),
                         'description': item.get('description', ''),
                         'salary_min': item.get('salary_min', ''),
                         'salary_max': item.get('salary_max', ''),
                         'created': item.get('created', '')})
        if len(results) < per_page:
            break
    return jobs


def usajobs_search(query, location='Denver, Colorado', pages=1, per_page=100, session=None):
    """Search USAJOBS API using API key and email from the environment."""
    key, email = os.getenv('USAJOBS_API_KEY'), os.getenv('USAJOBS_EMAIL')
    if not key or not email:
        raise ValueError('Set USAJOBS_API_KEY and USAJOBS_EMAIL')
    session = session or requests.Session()
    jobs = []
    for page in range(1, pages + 1):
        response = session.get(
            'https://data.usajobs.gov/api/Search',
            headers={'Host': 'data.usajobs.gov', 'User-Agent': email,
                     'Authorization-Key': key},
            params={'Keyword': query, 'LocationName': location,
                    'Page': page, 'ResultsPerPage': per_page}, timeout=30)
        response.raise_for_status()
        results = response.json().get('SearchResult', {}).get('SearchResultItems', [])
        for wrapper in results:
            item = wrapper.get('MatchedObjectDescriptor', {})
            details = item.get('UserArea', {}).get('Details', {})
            pay = item.get('PositionRemuneration') or [{}]
            pay = pay[0] if isinstance(pay, list) else pay
            jobs.append({'source': 'usajobs', 'source_id': str(item.get('PositionID', '')),
                         'company': item.get('OrganizationName', ''),
                         'title': item.get('PositionTitle', ''),
                         'location': item.get('PositionLocationDisplay', ''),
                         'url': item.get('PositionURI', ''),
                         'description': details.get('JobSummary', ''),
                         'salary_min': pay.get('MinimumRange', ''),
                         'salary_max': pay.get('MaximumRange', ''),
                         'created': item.get('PublicationStartDate', '')})
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
    parser.add_argument('--location', default='Denver')
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--output', default='output/additional_jobs.csv')
    args = parser.parse_args()
    if args.pages < 1:
        parser.error('--pages must be positive')
    fn = adzuna_search if args.source == 'adzuna' else usajobs_search
    jobs = fn(args.query, location=args.location, pages=args.pages)
    write_jobs(jobs, args.output)
    print(f'Wrote {len(jobs)} {args.source} jobs to {args.output}')


if __name__ == '__main__':
    main()
