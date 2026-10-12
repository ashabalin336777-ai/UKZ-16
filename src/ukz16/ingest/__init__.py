from ukz16.ingest.base import IngestAdapter
from ukz16.ingest.factory import build_ingest_adapter
from ukz16.ingest.fixture_adapter import FixtureEcozAdapter
from ukz16.ingest.http_adapter import HttpEcozAdapter
from ukz16.ingest.mock import MockEcozAdapter

__all__ = [
    "FixtureEcozAdapter",
    "HttpEcozAdapter",
    "IngestAdapter",
    "MockEcozAdapter",
    "build_ingest_adapter",
]
