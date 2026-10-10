"""Source ingestion worker; shares validation, auth and persistence with the API."""

from propadmin_runtime import create_app

app = create_app("ingestion")
