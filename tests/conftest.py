"""Pytest configuration and fixtures for AI Debate Tool tests."""

import os
import sys
from pathlib import Path

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_plan_file(tmp_path):
    """Create a sample plan file for testing."""
    plan_content = """# Test Plan

## Overview
This is a test plan for unit testing.

## Changes
- Add feature X
- Refactor module Y
- Update tests

## Testing
- Unit tests
- Integration tests
"""
    plan_file = tmp_path / "test_plan.md"
    plan_file.write_text(plan_content)
    return plan_file


@pytest.fixture
def sample_code_file(tmp_path):
    """Create a sample code file for testing."""
    code_content = '''"""Sample module for testing."""

def calculate_total(items):
    """Calculate total price of items."""
    return sum(item.price for item in items)

class Order:
    """Order class for testing."""

    def __init__(self, items):
        self.items = items

    def total(self):
        return calculate_total(self.items)
'''
    code_file = tmp_path / "sample.py"
    code_file.write_text(code_content)
    return code_file


@pytest.fixture
def mock_debate_result():
    """Return a mock debate result for testing."""
    return {
        "debate_result": {
            "consensus_score": 85,
            "interpretation": "Good Agreement",
            "recommendation": "[PROCEED]",
            "claude": {
                "score": 88,
                "summary": "The plan looks solid with good structure."
            },
            "codex": {
                "score": 82,
                "summary": "Generally good approach with minor concerns."
            },
            "agreements": [
                "Code structure is appropriate",
                "Testing strategy is comprehensive"
            ],
            "disagreements": []
        },
        "performance_stats": {
            "total_time": 12.5,
            "cache_hit": False,
            "context_extraction_time": 0.5,
            "moderation_time": 2.0
        }
    }


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / ".cache" / "debate_history"
    cache_dir.mkdir(parents=True)
    return cache_dir
