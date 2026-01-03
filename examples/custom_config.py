"""Custom Configuration Example

This example shows how to customize the debate tool configuration.
"""

import asyncio
from pathlib import Path

from ai_debate_tool import check_debate_required, DebateConfig


def example_check_complexity():
    """Example: Check if a change needs debate."""
    print("=== Complexity Check Examples ===\n")

    # Simple change - likely won't need debate
    result = check_debate_required(
        request="Fix typo in README",
        file_paths=["README.md"]
    )
    print(f"Request: 'Fix typo in README'")
    print(f"  Complexity: {result.get('complexity_score', 0)}/100")
    print(f"  Debate required: {result.get('required', False)}")

    # Complex change - likely needs debate
    result = check_debate_required(
        request="Refactor authentication to use OAuth2 with multiple providers",
        file_paths=["auth/views.py", "auth/models.py", "auth/oauth.py", "settings.py"]
    )
    print(f"\nRequest: 'Refactor authentication to use OAuth2'")
    print(f"  Complexity: {result.get('complexity_score', 0)}/100")
    print(f"  Debate required: {result.get('required', False)}")
    if result.get("reasons"):
        print(f"  Reasons:")
        for reason in result["reasons"][:3]:
            print(f"    - {reason}")


async def example_custom_orchestrator():
    """Example: Create orchestrator with custom settings."""
    from ai_debate_tool import get_orchestrator

    print("\n=== Custom Orchestrator Example ===\n")

    # Create orchestrator with custom settings
    Orchestrator = get_orchestrator()
    orchestrator = Orchestrator(
        enable_cache=True,       # Use caching for repeated debates
        enable_intelligence=True  # Enable pattern detection and learning
    )

    # Create a sample file
    sample_file = Path("sample.md")
    sample_file.write_text("# Sample Plan\nAdd new feature X")

    try:
        result = await orchestrator.run_debate(
            request="Quick review of this simple change",
            file_path=str(sample_file.absolute()),
            focus_areas=["simplicity"]
        )

        print(f"Consensus: {result['debate_result'].get('consensus_score', 0)}/100")
        print(f"Time: {result['performance_stats'].get('total_time', 0):.1f}s")
        print(f"Cached: {result['performance_stats'].get('cache_hit', False)}")

    finally:
        if sample_file.exists():
            sample_file.unlink()


def example_config_object():
    """Example: Using DebateConfig directly."""
    print("\n=== DebateConfig Example ===\n")

    # Create custom config
    config = DebateConfig(
        enabled=True,
        complexity_threshold=50,   # Higher threshold = fewer debates
        target_consensus=80,       # Require higher agreement
        max_rounds=3,              # Limit iteration rounds
        log_level="DEBUG"
    )

    print("Custom configuration:")
    print(f"  Enabled: {config.enabled}")
    print(f"  Complexity threshold: {config.complexity_threshold}")
    print(f"  Target consensus: {config.target_consensus}")
    print(f"  Max rounds: {config.max_rounds}")
    print(f"  Log level: {config.log_level}")


def example_environment_variables():
    """Example: Configuration via environment variables."""
    import os

    print("\n=== Environment Variables ===\n")

    # These environment variables are supported
    env_vars = {
        "ENABLE_AI_DEBATE": "true",
        "DEBATE_COMPLEXITY_THRESHOLD": "40",
        "DEBATE_TARGET_CONSENSUS": "75",
        "DEBATE_MAX_ROUNDS": "5",
        "DEBATE_LOG_LEVEL": "INFO"
    }

    print("Supported environment variables:")
    for var, default in env_vars.items():
        current = os.environ.get(var, f"(default: {default})")
        print(f"  {var}: {current}")


def main():
    """Run all examples."""
    example_check_complexity()
    asyncio.run(example_custom_orchestrator())
    example_config_object()
    example_environment_variables()


if __name__ == "__main__":
    main()
