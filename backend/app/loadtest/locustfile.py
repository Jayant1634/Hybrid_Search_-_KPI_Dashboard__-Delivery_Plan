"""Locust user class for concurrent ``POST /search`` load.

Run from a second process (not inside the API worker):

    locust -f app/loadtest/locustfile.py --host http://127.0.0.1:8000
    locust -f app/loadtest/locustfile.py --host http://127.0.0.1:8000 \\
        --headless -u 20 -r 20 --iterations 20
"""

from __future__ import annotations

from locust import HttpUser, constant, task

from app.loadtest.burst import DEFAULT_QUERY

SEARCH_BODY = {"query": DEFAULT_QUERY, "top_k": 10}


class SearchUser(HttpUser):
    """One virtual user that posts the default KPI probe query."""

    wait_time = constant(0)

    @task
    def search(self) -> None:
        with self.client.post(
            "/search",
            json=SEARCH_BODY,
            name="/search",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"status {response.status_code}")
                return
            response.success()
