"""One-shot text backfill, invoked by gated Cloud Run Jobs."""

import argparse
import os

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['backfill'])
    parser.parse_args()
    from google.auth.transport.requests import Request
    from google.oauth2.id_token import fetch_id_token

    url = os.environ['TARGET_SERVICE_URL'].rstrip('/')
    token = fetch_id_token(Request(), url)
    with httpx.Client(headers={'Authorization': f'Bearer {token}'}, timeout=600) as client:
        from google.cloud import storage

        bucket = storage.Client().bucket(os.environ['RAW_BUCKET'])
        count = 0
        for blob in bucket.list_blobs(prefix=os.getenv('SOURCE_PREFIX', '')):
            # Binary PDF/audio parsing is handled by provider pipelines when configured.
            if not (blob.content_type or '').startswith('text/'):
                continue
            payload = {'filename': blob.name, 'mime': blob.content_type,
                       'origin': f'gs://{bucket.name}/{blob.name}',
                       'text': blob.download_as_text()}
            response = client.post(f'{url}/internal/events/land', json=payload)
            response.raise_for_status()
            count += 1
        print(f'Backfilled {count} text sources')


if __name__ == '__main__':
    main()
