import random
from locust import HttpUser, task, between


class RateLimiterUser(HttpUser):
    wait_time = between(0.01, 0.05)  # small pause between requests, like real users

    @task
    def hit_data_endpoint(self):
        # Simulate many different clients, not just one, so we measure
        # real throughput instead of just triggering rate-limit blocks.
        client_id = f"loadtest-client-{random.randint(1, 500)}"
        self.client.get("/data", headers={"X-Client-Id": client_id})
