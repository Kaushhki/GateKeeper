import redis
import time

class RedisTokenBucket:
    

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
