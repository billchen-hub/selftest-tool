"""AI response cache — avoid repeated calls for unchanged files."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


class AICache:
    """File-content-hash based cache for AI responses.

    Cache key = hash(source_file_content + prompt_rules_hash).
    Cache is stored in .selftest/cache/ as JSON files.
    """

    def __init__(self, cache_dir: Path, ttl_days: int = 30):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_days * 86400
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, source_content: str, prompt_hash: str) -> str:
        """Generate cache key from source content and prompt config hash."""
        combined = source_content + "|" + prompt_hash
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, source_content: str, prompt_hash: str) -> str | None:
        """Retrieve cached AI response. Returns None if miss or expired."""
        key = self._make_key(source_content, prompt_hash)
        path = self._cache_path(key)

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            path.unlink(missing_ok=True)
            return None

        # Check expiry
        cached_time = data.get("timestamp", 0)
        if time.time() - cached_time > self.ttl_seconds:
            path.unlink(missing_ok=True)
            return None

        return data.get("response")

    def put(self, source_content: str, prompt_hash: str, response: str) -> None:
        """Store AI response in cache."""
        key = self._make_key(source_content, prompt_hash)
        path = self._cache_path(key)

        data = {
            "timestamp": time.time(),
            "key": key,
            "response": response,
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def invalidate(self, source_content: str, prompt_hash: str) -> None:
        """Remove a specific cache entry."""
        key = self._make_key(source_content, prompt_hash)
        self._cache_path(key).unlink(missing_ok=True)

    def clear_expired(self) -> int:
        """Remove all expired cache entries. Returns count removed."""
        removed = 0
        for path in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if time.time() - data.get("timestamp", 0) > self.ttl_seconds:
                    path.unlink()
                    removed += 1
            except Exception:
                path.unlink(missing_ok=True)
                removed += 1
        return removed


def hash_prompt_config(prompts_dir: Path | None) -> str:
    """Hash all prompt rule files to detect config changes."""
    h = hashlib.sha256()
    if prompts_dir and prompts_dir.exists():
        for md_file in sorted(prompts_dir.glob("*.md")):
            h.update(md_file.read_bytes())
    return h.hexdigest()[:16]
