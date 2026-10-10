"""Apply schema migrations to an explicitly configured SurrealDB HTTP endpoint."""

import argparse
import os
import re
from pathlib import Path

import httpx


def execute(client, source):
    response = client.post('/sql', content=source)
    response.raise_for_status()
    results = response.json()
    failures = [item['result'] for item in results if item.get('status') != 'OK']
    if failures:
        raise RuntimeError('\n'.join(str(item) for item in failures))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--create-database', action='store_true', help='Local root-only namespace/database setup')
    parser.add_argument('--url', default=os.getenv('SURREAL_URL', 'http://localhost:8008'))
    args = parser.parse_args()
    password = os.getenv('SURREAL_PASSWORD')
    if not password:
        parser.error('SURREAL_PASSWORD is required; credentials never default outside compose')
    namespace = os.getenv('SURREAL_NAMESPACE', 'propadmin')
    database = os.getenv('SURREAL_DATABASE', 'propadmin')
    if not all(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', value) for value in [namespace, database]):
        parser.error('Namespace and database must be simple identifiers')
    with httpx.Client(
        base_url=args.url,
        auth=(os.getenv('SURREAL_USER', 'root'), password),
        headers={'Surreal-NS': os.getenv('SURREAL_NAMESPACE', 'propadmin'),
                 'Surreal-DB': os.getenv('SURREAL_DATABASE', 'propadmin'),
                 'Accept': 'application/json'},
        timeout=120,
    ) as client:
        if args.create_database:
            execute(client, f'DEFINE NAMESPACE IF NOT EXISTS {namespace}; USE NS {namespace}; '
                    f'DEFINE DATABASE IF NOT EXISTS {database}; USE DB {database};')
        for file in sorted(Path(__file__).parent.glob('*.surql')):
            execute(client, file.read_text())
            print(f'Applied {file.name}')


if __name__ == '__main__':
    main()
