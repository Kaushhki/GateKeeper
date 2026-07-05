# Requirements: Distributed Rate Limiter

## Problem
A single API server can protect itself from abuse using an in-memory rate
limiter, but this breaks down the moment traffic is spread across multiple
server processes or machines — each process would enforce its own separate
limit, allowing a client to exceed the intended global limit by simply
hitting different servers.

## Goals
- Enforce a single, correct rate limit per client, regardless of which
  server process handles the request.
- No double-counting or race conditions when multiple processes check
  and update the limit at the same time.
- Simple integration into an existing Flask API via middleware.

## Non-goals
- Per-endpoint custom limits (every endpoint shares one limiter config
  in this version).
- Authentication/identity management (client ID is passed via header
  for demo purposes, not tied to a real auth system).

## Requirements
**Must-have:**
- Shared state lives outside any single process (Redis).
- Atomic check-and-decrement operation (no read-then-write race window).
- Returns a clear 429 response when a client is over their limit.

**Nice-to-have:**
- Configurable capacity and refill rate per client type.
- Observability into current token counts (for debugging).

## Success metrics
- Correctness: a multi-process load test enforces the exact configured
  limit with zero over-allowance (verified: 300 concurrent requests
  against a 100-request limit; only 100 were allowed).
- Performance: sustain 100+ requests/sec with p95 latency under 1 second
  under a production WSGI server (verified: ~113 req/s, 610ms p95).

## Tradeoffs considered
- **Redis Lua script vs. distributed lock (e.g. Redlock):** chose a Lua
  script because it runs atomically on the Redis server itself in a
  single round trip, avoiding the added complexity and failure modes of
  acquiring/releasing a separate distributed lock for every request.
- **Token Bucket vs. Fixed Window counter:** chose Token Bucket because
  it allows short bursts up to capacity while still enforcing a smooth
  average rate, rather than the harsh cliff-edge resets a fixed window
  produces at window boundaries.
