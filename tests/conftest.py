from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

# Ensure project root settings before imports that cache settings
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("UKZ16_DATABASE_URL", f"sqlite:///{ROOT / 'test_ukz16.db'}")
os.environ.setdefault("UKZ16_MODEL_VERSION", "research-v0.2")

from ukz16.config import get_settings
from ukz16.db.session import get_engine, init_db, reset_engine


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("UKZ16_DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    reset_engine()
    init_db()
    yield
    reset_engine()
    get_settings.cache_clear()
    if db_path.exists():
        db_path.unlink(missing_ok=True)


@pytest.fixture
def session() -> Session:
    engine = get_engine()
    with Session(engine) as s:
        yield s
        s.commit()
