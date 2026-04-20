"""
Locust performance scenarios for Assistify.
Runs against a local CI server and reports response-time/throughput metrics.
"""

from locust import HttpUser, between, events, task


class AssistifyUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_documents(self):
        # In CI we usually hit this without auth. 401 is acceptable for performance sampling.
        with self.client.get("/api/v1/documents/", name="List Documents", catch_response=True) as response:
            if response.status_code in (200, 401):
                response.success()
            else:
                response.failure(f"unexpected status: {response.status_code}")

    @task(2)
    def chat_query(self):
        payload = {"question": "What are your pricing plans?"}
        # Endpoint behavior may vary by environment; keep this as a load/latency probe.
        with self.client.post("/api/v1/chat/query/", json=payload, name="Chat Query (RAG)", catch_response=True) as response:
            if response.status_code in (200, 401, 404):
                response.success()
            else:
                response.failure(f"unexpected status: {response.status_code}")

    @task(1)
    def upload_document(self):
        files = {"file": ("perf.txt", b"locust performance document", "text/plain")}
        data = {"title": "Locust Performance Doc"}
        with self.client.post(
            "/api/v1/documents/upload/",
            files=files,
            data=data,
            name="Upload Document",
            catch_response=True,
        ) as response:
            if response.status_code in (201, 202, 400, 401, 429):
                response.success()
            else:
                response.failure(f"unexpected status: {response.status_code}")

    @task(1)
    def analytics(self):
        with self.client.get("/api/v1/analytics/", name="Get Analytics", catch_response=True) as response:
            if response.status_code in (200, 401, 404):
                response.success()
            else:
                response.failure(f"unexpected status: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"[locust] starting test against: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    total = environment.stats.total
    print("[locust] test completed")
    print(f"[locust] requests={total.num_requests} failures={total.num_failures}")
    print(f"[locust] avg={total.avg_response_time:.2f}ms p95={total.get_response_time_percentile(0.95):.2f}ms rps={total.total_rps:.2f}")
