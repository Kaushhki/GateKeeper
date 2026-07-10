import threading
import time

class NaiveTokenBucket:
    """
    A token bucket WITHOUT proper locking. This is deliberately broken
    to demonstrate the race condition that concurrency introduces.
    """
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        refill_amount = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + refill_amount)
        self.last_refill = now

    def allow_request(self):
        self._refill()
        if self.tokens >= 1:
            

            time.sleep(0.0001)  
            self.tokens -= 1
            return True
        return False


def hammer(bucket, results, thread_id, num_requests=20):
    allowed = 0
    for _ in range(num_requests):
        if bucket.allow_request():
            allowed += 1
    results[thread_id] = allowed


if __name__ == "__main__":
    NUM_THREADS = 10
    REQUESTS_PER_THREAD = 20
    CAPACITY = 50  # we only want 50 requests allowed, total, across ALL threads

    bucket = NaiveTokenBucket(capacity=CAPACITY, refill_rate=0)  # no refill, isolate the bug
    results = {}
    threads = []

    for i in range(NUM_THREADS):
        t = threading.Thread(target=hammer, args=(bucket, results, i, REQUESTS_PER_THREAD))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    total_allowed = sum(results.values())
    print(f"Bucket capacity was: {CAPACITY}")
    print(f"Total requests allowed across all threads: {total_allowed}")
    print(f"Per-thread breakdown: {results}")

    if total_allowed > CAPACITY:
        print(f"\n*** RACE CONDITION CONFIRMED: {total_allowed - CAPACITY} extra requests "
              f"were allowed beyond the capacity! ***")
    else:
        print("\nNo overshoot detected this run (race conditions are timing-dependent — try again).")
