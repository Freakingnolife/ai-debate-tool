"""
Debate Cache - File-based caching for faster repeat debates.

Caches Codex responses with 5-minute TTL to dramatically speed up
iterative development workflows.

Cache hit: Instant response (vs 30-40 seconds Codex API call)
Cache miss: Normal speed, but result cached for next time
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict


class DebateCache:
    """Simple file-based cache for debate responses."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_minutes: int = 5
    ):
        """
        Initialize debate cache.

        Args:
            cache_dir: Directory for cache files (default: .cache/debates)
            ttl_minutes: Time-to-live for cache entries (default: 5 minutes)
        """
        if cache_dir is None:
            # Default to .cache/debates in ai_debate_tool directory
            cache_dir = Path(__file__).parent.parent / '.cache' / 'debates'

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(minutes=ttl_minutes)

    def get(self, prompt: str, file_hash: Optional[str] = None) -> Optional[Dict]:
        """
        Get cached response for prompt.

        Args:
            prompt: Prompt text to look up
            file_hash: Optional file content hash (for cache invalidation)

        Returns:
            Cached response dict or None if not found/expired

        Cache Key:
            MD5(prompt + file_hash) - ensures cache invalidates on file changes
        """
        cache_key = self._generate_cache_key(prompt, file_hash)
        cache_file = self.cache_dir / f"{cache_key}.json"

        # Check if cache file exists
        if not cache_file.exists():
            return None

        # Check TTL (time-to-live)
        try:
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime > self.ttl:
                # Expired - delete and return None
                cache_file.unlink()
                return None
        except Exception:
            # If any error checking TTL, treat as miss
            return None

        # Load cached response
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            # Verify file_hash if provided (extra safety)
            if file_hash and cached_data.get('file_hash') != file_hash:
                # File changed since cache - invalidate
                cache_file.unlink()
                return None

            return cached_data.get('response')

        except Exception as e:
            # Corrupted cache file - delete and return None
            try:
                cache_file.unlink()
            except Exception:
                pass
            return None

    def set(
        self,
        prompt: str,
        response: Dict,
        file_hash: Optional[str] = None
    ) -> bool:
        """
        Cache response for prompt.

        Args:
            prompt: Prompt text (cache key)
            response: Response data to cache
            file_hash: Optional file content hash

        Returns:
            True if cached successfully, False on error
        """
        cache_key = self._generate_cache_key(prompt, file_hash)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'file_hash': file_hash,
                'response': response
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            # Failed to cache (not critical, just slower next time)
            return False

    def clear_expired(self) -> int:
        """
        Clear all expired cache entries.

        Returns:
            Number of entries cleared
        """
        cleared = 0
        now = datetime.now()

        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if now - mtime > self.ttl:
                        cache_file.unlink()
                        cleared += 1
                except Exception:
                    # Error processing this file, skip
                    continue
        except Exception:
            # Error scanning directory
            pass

        return cleared

    def clear_all(self) -> int:
        """
        Clear all cache entries (regardless of expiration).

        Returns:
            Number of entries cleared
        """
        cleared = 0

        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                    cleared += 1
                except Exception:
                    continue
        except Exception:
            pass

        return cleared

    def get_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            {
                'total_entries': int,
                'valid_entries': int,  # Not expired
                'expired_entries': int,
                'cache_dir': str,
                'ttl_minutes': int
            }
        """
        total = 0
        valid = 0
        expired = 0
        now = datetime.now()

        try:
            for cache_file in self.cache_dir.glob("*.json"):
                total += 1
                try:
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if now - mtime > self.ttl:
                        expired += 1
                    else:
                        valid += 1
                except Exception:
                    expired += 1  # Treat errors as expired
        except Exception:
            pass

        return {
            'total_entries': total,
            'valid_entries': valid,
            'expired_entries': expired,
            'cache_dir': str(self.cache_dir),
            'ttl_minutes': self.ttl.total_seconds() / 60
        }

    def _generate_cache_key(self, prompt: str, file_hash: Optional[str] = None) -> str:
        """
        Generate cache key from prompt and file hash.

        Args:
            prompt: Prompt text
            file_hash: Optional file content hash

        Returns:
            16-character hex string (MD5 hash)

        Why MD5:
            - Fast (10x faster than SHA256)
            - Collision risk negligible for ~1000 cache entries
            - 16-char hex is short and readable
        """
        # Combine prompt + file_hash for cache key
        key_input = prompt
        if file_hash:
            key_input += f"|{file_hash}"

        # MD5 hash (first 16 chars for short filenames)
        hash_obj = hashlib.md5(key_input.encode('utf-8'))
        return hash_obj.hexdigest()[:16]

    @staticmethod
    def hash_file_content(file_path: str) -> str:
        """
        Generate hash of file content for cache invalidation.

        Args:
            file_path: Path to file

        Returns:
            MD5 hash of file content (16 chars)

        Usage:
            file_hash = DebateCache.hash_file_content('roadmap.md')
            cached = cache.get(prompt, file_hash)
            # If file changes, file_hash changes → cache miss
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            hash_obj = hashlib.md5(content)
            return hash_obj.hexdigest()[:16]
        except Exception:
            # If can't read file, return timestamp-based hash
            return hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:16]
