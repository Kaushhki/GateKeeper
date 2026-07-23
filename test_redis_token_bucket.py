import time
import redis
import pytest
from redis_token_bucket import RedisTokenBucket


@pytest.fixture
def redis_client():
    client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    client.flushdb() 
    yield client
    client.flushdb() 


def test_allows_requests_within_capacity(redis_client):
    bucket = RedisTokenBucket(redis_client, capacity=3, refill_rate=0)
    assert bucket.allow_request("client1") is True
    assert bucket.allow_request("client1") is True
    assert bucket.allow_request("client1") is True


def test_blocks_requests_over_capacity(redis_client):
    bucket = RedisTokenBucket(redis_client, capacity=2, refill_rate=0)
    assert bucket.allow_request("client1") is True
    assert bucket.allow_request("client1") is True
    assert bucket.allow_request("client1") is False  


def test_separate_clients_have_independent_buckets(redis_client):
    bucket = RedisTokenBucket(redis_client, capacity=1, refill_rate=0)
    assert bucket.allow_request("clientA") is True
    assert bucket.allow_request("clientB") is True  


def test_tokens_refill_over_time(redis_client):
    bucket = RedisTokenBucket(redis_client, capacity=1, refill_rate=10)  
    assert bucket.allow_request("client1") is True
    assert bucket.allow_request("client1") is False  # no tokens left
    time.sleep(0.2)  # wait for refill (10 tokens/sec * 0.2s = 2 tokens)
    assert bucket.allow_request("client1") is True  # should have refilled
