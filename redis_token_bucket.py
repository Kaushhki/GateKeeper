import redis
import time

class RedisTokenBucket:
    """
    A distributed Token Bucket. State lives in Redis, NOT in this process's
    memory — so any number of separate processes/servers, all talking to the
    same Redis instance, share and correctly enforce ONE limit.

    Why a Python threading.Lock can't help here:
    A Lock only synchronizes threads inside the SAME process. It has no way
    to coordinate with a different process on a different machine. We need
    something both processes can talk to and agree on — that's Redis.

    Why we can't just do "GET tokens, check, SET tokens-1" from Python:
    That's the exact same check-then-act race condition as before, just
    moved to Redis calls instead of in-memory variables. Two processes could
    both GET the same token count, both decide to allow the request, and
    both SET an updated value, again over-allowing requests.

    The fix: a Lua script. Redis guarantees that an entire Lua script runs
    atomically — no other client's command (from any process) can run in
    the middle of it. So we do the ENTIRE check-and-decrement operation as
    a single atomic unit on the Redis server itself.
    """

    LUA_SCRIPT = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local refill_rate = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])

    local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
    local tokens = tonumber(bucket[1])
    local last_refill = tonumber(bucket[2])

    if tokens == nil then
        tokens = capacity
        last_refill = now
    end

    local elapsed = math.max(0, now - last_refill)
    local refill_amount = elapsed * refill_rate
    tokens = math.min(capacity, tokens + refill_amount)

    local allowed = 0
    if tokens >= 1 then
        tokens = tokens - 1
        allowed = 1
    end

    redis.call('HMSET', key, 'tokens', tostring(tokens), 'last_refill', tostring(now))
    redis.call('EXPIRE', key, 3600)

    return allowed
    """

    def __init__(self, redis_client, capacity, refill_rate, key_prefix="rate_limiter"):
        self.redis = redis_client
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.key_prefix = key_prefix
        self.script = self.redis.register_script(self.LUA_SCRIPT)

    def allow_request(self, client_id):
        """
        client_id identifies WHO is being rate-limited (e.g. a user ID or
        API key) — each client_id gets its own independent bucket in Redis,
        all sharing the same Redis instance regardless of which process
        or server handled the request.
        """
        key = f"{self.key_prefix}:{client_id}"
        now = time.time()
        result = self.script(
            keys=[key],
            args=[self.capacity, self.refill_rate, now]
        )
        return bool(result)
