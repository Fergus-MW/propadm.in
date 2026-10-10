"""Shared Propadmin domain services; all service results are JSON-compatible."""

from .gcs_store import GcsStore, open_store
from .graph import GraphService
from .ingestion import IngestionService
from .providers import ProviderNotConfigured, SurrealRepository
from .rules import RuleService
from .search import SearchService
from .store import ConflictError, Store, publish


def seed_demo(store):
    from .seed import seed_demo as seed

    return seed(store)


__all__ = [
    "ConflictError",
    "GcsStore",
    "GraphService",
    "IngestionService",
    "ProviderNotConfigured",
    "RuleService",
    "SearchService",
    "Store",
    "SurrealRepository",
    "open_store",
    "publish",
    "seed_demo",
]
