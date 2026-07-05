import threading
import time

class ThreadSafeTokenBucket:
    """
    A correct, thread-safe Token Bucket for a SINGLE process.

    Fix: wrap the check-then-act sequence (_refill -> check -> decrement)
    in a Lock, so only one thread can execute that critical section at a time.
    This makes the whole "check, then take a token" operation atomic
    from the perspective of any other thread in this process.

    Limitation this does NOT solve: if you run this same code in TWO
    separate processes (e.g. two instances of your API server), each
    process gets its OWN bucket and its OWN lock. The lock only protects
    against other threads in the SAME process — it knows nothing about
    the other process. That's the problem Redis solves later.
    """
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        refill_amount = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + refill_amount)
        self.last_refill = now

    def allow_request(self):
        with self.lock:
            self._refill()
            if self.tokens >= 1:
                time.sleep(0.0001)  # same artificial delay as before, on purpose
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
    CAPACITY = 50

    bucket = ThreadSafeTokenBucket(capacity=CAPACITY, refill_rate=0)
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
        print(f"\n*** Unexpected: {total_allowed - CAPACITY} extra requests allowed. ***")
    else:
        print(f"\nCorrect: exactly {total_allowed} requests allowed, capacity respected "
              f"even under concurrent load from {NUM_THREADS} threads.")
