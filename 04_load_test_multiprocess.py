

import multiprocessing
import redis
from redis_token_bucket import RedisTokenBucket  


def worker(process_id, num_requests, result_queue):
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    bucket = RedisTokenBucket(r, capacity=CAPACITY, refill_rate=0, key_prefix="loadtest")

    allowed_count = 0
    for _ in range(num_requests):
        if bucket.allow_request("shared-client"):
            allowed_count += 1

    result_queue.put((process_id, allowed_count))


CAPACITY = 100  

if __name__ == "__main__":
    NUM_PROCESSES = 10
    REQUESTS_PER_PROCESS = 30  

    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    try:
        r.ping()
    except redis.exceptions.ConnectionError:
        print("Could not connect to Redis. Start it first (redis-server or Docker).")
        raise SystemExit(1)

    r.delete("loadtest:shared-client")  

    result_queue = multiprocessing.Queue()
    processes = []

    for i in range(NUM_PROCESSES):
        p = multiprocessing.Process(target=worker, args=(i, REQUESTS_PER_PROCESS, result_queue))
        processes.append(p)

    for p in processes:
        p.start()
    for p in processes:
        p.join()

    results = {}
    while not result_queue.empty():
        pid, count = result_queue.get()
        results[pid] = count

    total_allowed = sum(results.values())
    total_attempted = NUM_PROCESSES * REQUESTS_PER_PROCESS

    print(f"Capacity (the limit we want enforced): {CAPACITY}")
    print(f"Total requests attempted across {NUM_PROCESSES} separate processes: {total_attempted}")
    print(f"Total requests ALLOWED: {total_allowed}")
    print(f"Per-process breakdown: {results}")

    if total_allowed == CAPACITY:
        print(f"\nCorrect: exactly {CAPACITY} requests allowed across {NUM_PROCESSES} "
              f"independent processes racing concurrently against shared Redis state.")
    else:
        print(f"\nMismatch: expected exactly {CAPACITY}, got {total_allowed}.")
