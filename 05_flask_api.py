"""
A small Flask API protected by the distributed rate limiter.

The idea: any real endpoint (here, a fake "/data" endpoint standing in
for something expensive — a DB query, a third-party API call, etc.)
gets a per-client rate limit enforced BEFORE the request is allowed to
do any real work. Run multiple instances of this app (different ports)
and they all correctly share ONE limit per client, because the state
lives in Redis, not in any single Flask process.

Run with:
    python3 05_flask_api.py
Then in another terminal try multiple instances on different ports:
    python3 05_flask_api.py 5001
    python3 05_flask_api.py 5002
(Both instances will enforce the SAME shared limit per client_id.)
"""

import sys
import time
import redis
from flask import Flask, request, jsonify
from redis_token_bucket import RedisTokenBucket

app = Flask(__name__)

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
import os

def _reset_redis_connection_after_fork():
    """
    When gunicorn forks into multiple worker processes, each worker
    inherits a copy of the same Redis connection, which causes them
    to contend with each other. This forces each worker to drop the
    inherited connection and open a fresh one on first use.
    """
    r.connection_pool.disconnect()

os.register_at_fork(after_in_child=_reset_redis_connection_after_fork)
# Capacity: 5 requests per client. Refill rate: 1 token every 2 seconds.
limiter = RedisTokenBucket(r, capacity=5, refill_rate=0.5, key_prefix="api_limiter")


def get_client_id():
    """
    In a real system this would be an API key, user ID, or authenticated
    identity. For this demo we use a header so it's easy to test different
    "clients" with curl/Postman without building auth.
    """
    return request.headers.get("X-Client-Id", request.remote_addr)


@app.before_request
def enforce_rate_limit():
    if request.path == "/health":
        return  # don't rate-limit the health check itself

    client_id = get_client_id()
    allowed = limiter.allow_request(client_id)

    if not allowed:
        return jsonify({
            "error": "Too Many Requests",
            "message": f"Rate limit exceeded for client '{client_id}'. Try again shortly.",
        }), 429


@app.route("/data", methods=["GET"])
def get_data():
    """Stand-in for some real, expensive operation worth protecting."""
    return jsonify({
        "message": "Here is your expensive data.",
        "served_by_port": request.host,
        "timestamp": time.time(),
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"Starting rate-limited API on port {port}")
    print(f"Try: curl http://localhost:{port}/data -H \"X-Client-Id: alice\"")
    print(f"Run it repeatedly (6+ times fast) to see the 429 kick in.")
    app.run(port=port, debug=False)
