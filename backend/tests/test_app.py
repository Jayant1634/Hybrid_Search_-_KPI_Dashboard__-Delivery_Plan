from importlib import metadata

import pytest

import app
import app.ingest as ingest


def test_package_version() -> None:
    assert app.__version__ == "0.1.0"
    assert metadata.version("app") == "0.1.0"


def test_ingest_module_is_runnable() -> None:
    assert callable(ingest.main)
    assert ingest.main.__module__ == "app.ingest"


@pytest.mark.slow
def test_slow_marker_for_real_model() -> None:
    """Real embedding-model tests use this marker. No model load in the skeleton."""
    assert True
