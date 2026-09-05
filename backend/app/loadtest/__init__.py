"""Concurrent search bursts for KPI latency checks.

Locust (``app/loadtest/locustfile.py``) is the CLI multi-user driver.
The dashboard button uses ``run_search_burst`` so uvicorn is not mixed
with gevent, and so the hits still go through ``POST /search``.
"""

from app.loadtest.burst import BurstHit, BurstResult, run_search_burst

__all__ = ["BurstHit", "BurstResult", "run_search_burst"]
