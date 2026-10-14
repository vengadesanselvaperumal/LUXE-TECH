import importlib
from types import SimpleNamespace

import pytest

database_module = importlib.import_module("app.database")


def test_postgres_bootstrap_refuses_to_create_or_seed_missing_schema(monkeypatch):
    class EmptyInspector:
        @staticmethod
        def get_table_names():
            return []

    monkeypatch.setattr(
        database_module,
        "engine",
        SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
    )
    monkeypatch.setattr(database_module, "inspect", lambda _engine: EmptyInspector())
    monkeypatch.setattr(
        database_module.Base.metadata,
        "create_all",
        lambda **_kwargs: pytest.fail("PostgreSQL schema must not be auto-created"),
    )

    with pytest.raises(RuntimeError, match="no tables were created or changed"):
        database_module.init_db()
