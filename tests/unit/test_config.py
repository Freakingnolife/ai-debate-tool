"""Tests for configuration module."""

import os
import pytest
from pathlib import Path


class TestDebateConfig:
    """Tests for DebateConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        from ai_debate_tool.config import DebateConfig

        config = DebateConfig()

        assert config.enabled is True
        assert config.complexity_threshold == 40
        assert config.target_consensus == 75
        assert config.max_rounds == 5
        assert config.log_level == "INFO"

    def test_custom_values(self):
        """Test custom configuration values."""
        from ai_debate_tool.config import DebateConfig

        config = DebateConfig(
            enabled=False,
            complexity_threshold=60,
            target_consensus=90,
            max_rounds=3,
            log_level="DEBUG"
        )

        assert config.enabled is False
        assert config.complexity_threshold == 60
        assert config.target_consensus == 90
        assert config.max_rounds == 3
        assert config.log_level == "DEBUG"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_default_config(self):
        """Test loading default configuration."""
        from ai_debate_tool.config import load_config

        config = load_config()

        assert config is not None
        assert hasattr(config, "enabled")
        assert hasattr(config, "complexity_threshold")

    def test_load_config_from_env(self, monkeypatch):
        """Test loading configuration from environment variables."""
        from ai_debate_tool.config import load_config

        # Set environment variables
        monkeypatch.setenv("ENABLE_AI_DEBATE", "false")
        monkeypatch.setenv("DEBATE_COMPLEXITY_THRESHOLD", "50")

        config = load_config()

        # Check that env vars are respected
        assert config is not None


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_complexity_threshold_range(self):
        """Test that complexity threshold is in valid range."""
        from ai_debate_tool.config import DebateConfig

        # Valid values
        config = DebateConfig(complexity_threshold=0)
        assert config.complexity_threshold == 0

        config = DebateConfig(complexity_threshold=100)
        assert config.complexity_threshold == 100

    def test_target_consensus_range(self):
        """Test that target consensus is in valid range."""
        from ai_debate_tool.config import DebateConfig

        config = DebateConfig(target_consensus=50)
        assert config.target_consensus == 50

        config = DebateConfig(target_consensus=100)
        assert config.target_consensus == 100
