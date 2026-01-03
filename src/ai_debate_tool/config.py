"""Configuration management for AI Debate Tool.

Handles loading and validation of configuration from environment variables.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class DebateConfig:
    """Configuration for AI Debate Tool."""

    # Enforcement Gate
    enabled: bool = True
    complexity_threshold: int = 40
    max_rounds: int = 5
    consensus_min: int = 75

    # Iterative Debate (v0.3.0)
    target_consensus: int = 90
    enable_iterative_mode: bool = False
    min_improvement_threshold: int = 5
    max_regression_tolerance: int = 10

    # File Protocol
    temp_dir: Optional[Path] = None
    cleanup_days: int = 7
    persist_history: bool = True
    scrub_secrets: bool = True

    # Locking & Concurrency
    lock_timeout: int = 10
    retry_attempts: int = 3
    retry_delay: float = 0.5

    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    debug: bool = False

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Validate ranges
        if not 0 <= self.complexity_threshold <= 100:
            raise ValueError("complexity_threshold must be 0-100")
        if not 1 <= self.max_rounds <= 10:
            raise ValueError("max_rounds must be 1-10")
        if not 0 <= self.consensus_min <= 100:
            raise ValueError("consensus_min must be 0-100")
        if not 50 <= self.target_consensus <= 100:
            raise ValueError("target_consensus must be 50-100")
        if self.min_improvement_threshold < 0:
            raise ValueError("min_improvement_threshold must be >= 0")
        if self.max_regression_tolerance < 0:
            raise ValueError("max_regression_tolerance must be >= 0")
        if self.lock_timeout <= 0:
            raise ValueError("lock_timeout must be > 0")
        if self.cleanup_days <= 0:
            raise ValueError("cleanup_days must be > 0")

        # Auto-detect temp directory if not provided
        if self.temp_dir is None:
            import tempfile

            self.temp_dir = Path(tempfile.gettempdir())

        # Ensure temp_dir is Path object
        if isinstance(self.temp_dir, str):
            self.temp_dir = Path(self.temp_dir)


def load_config(env_file: Optional[Path] = None) -> DebateConfig:
    """Load configuration from environment variables.

    Args:
        env_file: Optional path to .env file to load

    Returns:
        DebateConfig instance with loaded configuration

    Example:
        >>> config = load_config()
        >>> print(config.complexity_threshold)
        40
    """
    # Load .env file if provided
    if env_file and env_file.exists():
        _load_env_file(env_file)

    # Parse environment variables
    config = DebateConfig(
        # Enforcement Gate
        enabled=_get_bool("ENABLE_AI_DEBATE", True),
        complexity_threshold=_get_int("DEBATE_COMPLEXITY_THRESHOLD", 40),
        max_rounds=_get_int("DEBATE_MAX_ROUNDS", 5),
        consensus_min=_get_int("DEBATE_CONSENSUS_MIN", 75),
        # Iterative Debate
        target_consensus=_get_int("DEBATE_TARGET_CONSENSUS", 90),
        enable_iterative_mode=_get_bool("DEBATE_ENABLE_ITERATIVE", False),
        min_improvement_threshold=_get_int("DEBATE_MIN_IMPROVEMENT", 5),
        max_regression_tolerance=_get_int("DEBATE_MAX_REGRESSION", 10),
        # File Protocol
        temp_dir=_get_path("DEBATE_TEMP_DIR", None),
        cleanup_days=_get_int("DEBATE_CLEANUP_DAYS", 7),
        persist_history=_get_bool("DEBATE_PERSIST_HISTORY", True),
        scrub_secrets=_get_bool("DEBATE_SCRUB_SECRETS", True),
        # Locking
        lock_timeout=_get_int("DEBATE_LOCK_TIMEOUT", 10),
        retry_attempts=_get_int("DEBATE_RETRY_ATTEMPTS", 3),
        retry_delay=_get_float("DEBATE_RETRY_DELAY", 0.5),
        # Logging
        log_level=_get_str("DEBATE_LOG_LEVEL", "INFO"),
        log_file=_get_path("DEBATE_LOG_FILE", None),
        debug=_get_bool("DEBATE_DEBUG", False),
    )

    return config


def _load_env_file(env_file: Path) -> None:
    """Load environment variables from .env file.

    Args:
        env_file: Path to .env file
    """
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Parse KEY=VALUE
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value


def _get_str(key: str, default: str) -> str:
    """Get string value from environment."""
    return os.environ.get(key, default)


def _get_int(key: str, default: int) -> int:
    """Get integer value from environment."""
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(key: str, default: float) -> float:
    """Get float value from environment."""
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_bool(key: str, default: bool) -> bool:
    """Get boolean value from environment."""
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def _get_path(key: str, default: Optional[Path]) -> Optional[Path]:
    """Get Path value from environment."""
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return Path(value)
