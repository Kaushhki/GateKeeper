# GateKeeper — Distributed Rate Limiter

A Redis-backed token bucket rate limiter for multi-process APIs, built as a progression from a naive single-process limiter to a race-condition-safe distributed one — with load testing and CI to prove it under real traffic.

## Why This Exists

Rate limiters that work fine in a single process silently break once you scale to multiple workers or servers — each process tracks its own counter, so limits get bypassed. This project builds the fix step by step and proves it with load testing rather than just claiming it works.

## The Progression

| File | What it shows |
| --- | --- |
| `01_naive_broken.py` | A naive rate limiter — breaks under concurrent access (the problem) |
| `02_threadsafe_single_process.py` | Thread-safe within one process — still fails across multiple processes/servers |
| `03_redis_distributed.py` | Redis-backed token bucket — race-condition-safe across processes (the fix) |
| `04_load_test_multiprocess.py` | Multi-process load test validating the fix under concurrency |
| `05_flask_api.py` | Flask middleware wrapping the limiter as a real API |

## Results

- **100% test coverage** (`pytest`, see `test_redis_token_bucket.py`)
- **CI via GitHub Actions** — tests run on every push
- **Locust load testing** showed throughput improve from **~72 req/s → ~113 req/s** after moving to the Redis-backed distributed implementation

## Tech Stack

Python, Redis (via Docker), Flask, pytest, Locust, GitHub Actions

## Setup

```bash
# start Redis
docker run -d -p 6379:6379 redis

pip install -r requirements.txt

# run the Flask API
python 05_flask_api.py
```

## Running Tests

```bash
pytest test_redis_token_bucket.py --cov
```

## Load Testing

```bash
locust -f locustfile.py
```

## License

MIT
