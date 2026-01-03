"""Integration tests for ParallelDebateOrchestrator.

Note: These tests require Codex CLI to be installed and authenticated.
They are marked as 'slow' and can be skipped in quick test runs.
"""

import pytest
from pathlib import Path


@pytest.mark.slow
@pytest.mark.integration
class TestParallelDebateOrchestrator:
    """Integration tests for the parallel debate orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        from ai_debate_tool import get_orchestrator

        Orchestrator = get_orchestrator()
        return Orchestrator(
            enable_cache=False,  # Disable cache for testing
            enable_intelligence=True
        )

    @pytest.mark.asyncio
    async def test_run_debate_basic(self, orchestrator, sample_plan_file):
        """Test running a basic debate."""
        result = await orchestrator.run_debate(
            request="Review this test plan",
            file_path=str(sample_plan_file)
        )

        assert "debate_result" in result
        assert "performance_stats" in result

        debate = result["debate_result"]
        assert "consensus_score" in debate
        assert 0 <= debate["consensus_score"] <= 100
        assert "recommendation" in debate

    @pytest.mark.asyncio
    async def test_run_debate_with_focus_areas(self, orchestrator, sample_plan_file):
        """Test debate with focus areas."""
        result = await orchestrator.run_debate(
            request="Security review",
            file_path=str(sample_plan_file),
            focus_areas=["security", "testing"]
        )

        assert "debate_result" in result
        debate = result["debate_result"]
        assert "consensus_score" in debate

    @pytest.mark.asyncio
    async def test_debate_result_structure(self, orchestrator, sample_plan_file):
        """Test that debate result has expected structure."""
        result = await orchestrator.run_debate(
            request="Review plan structure",
            file_path=str(sample_plan_file)
        )

        debate = result["debate_result"]

        # Check required fields
        assert "consensus_score" in debate
        assert "interpretation" in debate
        assert "recommendation" in debate
        assert "claude" in debate
        assert "codex" in debate

        # Check claude/codex structure
        assert "score" in debate["claude"]
        assert "summary" in debate["claude"]
        assert "score" in debate["codex"]
        assert "summary" in debate["codex"]

    @pytest.mark.asyncio
    async def test_performance_stats(self, orchestrator, sample_plan_file):
        """Test that performance stats are captured."""
        result = await orchestrator.run_debate(
            request="Quick review",
            file_path=str(sample_plan_file)
        )

        stats = result["performance_stats"]

        assert "total_time" in stats
        assert stats["total_time"] > 0
        assert "cache_hit" in stats


@pytest.mark.integration
class TestOrchestratorCaching:
    """Tests for orchestrator caching behavior."""

    @pytest.fixture
    def cached_orchestrator(self):
        """Create orchestrator with caching enabled."""
        from ai_debate_tool import get_orchestrator

        Orchestrator = get_orchestrator()
        return Orchestrator(enable_cache=True)

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cache_hit_on_repeated_request(self, cached_orchestrator, sample_plan_file):
        """Test that repeated requests hit cache."""
        # First request
        result1 = await cached_orchestrator.run_debate(
            request="Review this plan",
            file_path=str(sample_plan_file)
        )

        # Second identical request
        result2 = await cached_orchestrator.run_debate(
            request="Review this plan",
            file_path=str(sample_plan_file)
        )

        # Second should be cache hit
        assert result2["performance_stats"].get("cache_hit", False) is True
        # And should be much faster
        assert result2["performance_stats"]["total_time"] < result1["performance_stats"]["total_time"]
