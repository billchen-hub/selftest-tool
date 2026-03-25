import time
from selftest.generator.cache import AICache, hash_prompt_config


def test_cache_miss(tmp_path):
    cache = AICache(tmp_path / "cache")
    result = cache.get("source code", "hash123")
    assert result is None


def test_cache_put_and_get(tmp_path):
    cache = AICache(tmp_path / "cache")
    cache.put("source code", "hash123", "ai response")
    result = cache.get("source code", "hash123")
    assert result == "ai response"


def test_cache_different_source(tmp_path):
    cache = AICache(tmp_path / "cache")
    cache.put("source v1", "hash123", "response v1")
    result = cache.get("source v2", "hash123")
    assert result is None


def test_cache_different_prompt_hash(tmp_path):
    cache = AICache(tmp_path / "cache")
    cache.put("source", "hash_a", "response a")
    result = cache.get("source", "hash_b")
    assert result is None


def test_cache_expired(tmp_path):
    cache = AICache(tmp_path / "cache", ttl_days=0)  # 0 days = immediate expire
    cache.put("source", "hash", "response")
    time.sleep(0.1)
    result = cache.get("source", "hash")
    assert result is None


def test_cache_invalidate(tmp_path):
    cache = AICache(tmp_path / "cache")
    cache.put("source", "hash", "response")
    assert cache.get("source", "hash") == "response"
    cache.invalidate("source", "hash")
    assert cache.get("source", "hash") is None


def test_cache_clear_expired(tmp_path):
    cache = AICache(tmp_path / "cache", ttl_days=0)
    cache.put("s1", "h1", "r1")
    cache.put("s2", "h2", "r2")
    time.sleep(0.1)
    removed = cache.clear_expired()
    assert removed == 2


def test_hash_prompt_config(tmp_path):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "rule1.md").write_text("rule 1")
    (prompts / "rule2.md").write_text("rule 2")

    h1 = hash_prompt_config(prompts)
    assert len(h1) == 16

    # Same content = same hash
    h2 = hash_prompt_config(prompts)
    assert h1 == h2

    # Changed content = different hash
    (prompts / "rule1.md").write_text("rule 1 modified")
    h3 = hash_prompt_config(prompts)
    assert h3 != h1


def test_hash_prompt_config_none():
    h = hash_prompt_config(None)
    assert len(h) == 16
