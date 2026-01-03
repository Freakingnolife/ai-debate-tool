"""Tests for enforcement gate module."""

import pytest


class TestCheckDebateRequired:
    """Tests for check_debate_required function."""

    def test_simple_request_no_files(self):
        """Test simple request without files."""
        from ai_debate_tool import check_debate_required

        result = check_debate_required(
            request="Fix typo",
            file_paths=[]
        )

        assert "required" in result
        assert "complexity_score" in result
        assert isinstance(result["required"], bool)
        assert isinstance(result["complexity_score"], (int, float))

    def test_complex_request_multiple_files(self):
        """Test complex request with multiple files."""
        from ai_debate_tool import check_debate_required

        result = check_debate_required(
            request="Refactor entire authentication system with OAuth2 integration",
            file_paths=["auth/views.py", "auth/models.py", "auth/oauth.py", "settings.py"]
        )

        assert "required" in result
        assert "complexity_score" in result
        # Complex request should have higher score
        assert result["complexity_score"] > 20

    def test_refactoring_keywords_increase_complexity(self):
        """Test that refactoring keywords increase complexity score."""
        from ai_debate_tool import check_debate_required

        result = check_debate_required(
            request="Refactor and restructure the database layer",
            file_paths=["db/models.py"]
        )

        assert result["complexity_score"] >= 30

    def test_security_keywords_increase_complexity(self):
        """Test that security keywords increase complexity score."""
        from ai_debate_tool import check_debate_required

        result = check_debate_required(
            request="Update authentication and security layer",
            file_paths=["security/auth.py"]
        )

        assert result["complexity_score"] >= 30

    def test_reasons_provided(self):
        """Test that reasons are provided for the decision."""
        from ai_debate_tool import check_debate_required

        result = check_debate_required(
            request="Major refactoring of core modules",
            file_paths=["core/engine.py", "core/utils.py"]
        )

        assert "reasons" in result
        assert isinstance(result["reasons"], list)


class TestBlockExecutionUntilConsensus:
    """Tests for block_execution_until_consensus function."""

    def test_returns_gate_result(self):
        """Test that function returns gate result dict."""
        from ai_debate_tool import block_execution_until_consensus

        # This would normally check a session, but for unit test
        # we test the return structure
        result = block_execution_until_consensus("test_session_123")

        assert "can_execute" in result
        assert isinstance(result["can_execute"], bool)


class TestMarkUserOverride:
    """Tests for mark_user_override function."""

    def test_marks_override(self):
        """Test marking user override."""
        from ai_debate_tool import mark_user_override

        # Should not raise
        result = mark_user_override("test_session_123", "User chose to proceed")

        assert result is None or isinstance(result, dict)
