"""Basic Debate Example

This example shows how to run a simple debate using the AI Debate Tool.
"""

import asyncio
from pathlib import Path

# Create a sample plan file for the example
SAMPLE_PLAN = """# Refactoring Plan

## Overview
Refactor the authentication module to improve security and maintainability.

## Proposed Changes
1. Split auth.py into separate modules:
   - auth/login.py - Login logic
   - auth/logout.py - Logout logic
   - auth/tokens.py - Token management

2. Add rate limiting to prevent brute force attacks

3. Implement proper password hashing with bcrypt

4. Add comprehensive logging

## Testing Strategy
- Unit tests for each module
- Integration tests for auth flow
- Security penetration testing
"""


async def main():
    from ai_debate_tool import get_orchestrator

    # Create a temporary plan file
    plan_file = Path("example_plan.md")
    plan_file.write_text(SAMPLE_PLAN)

    try:
        # Create orchestrator
        Orchestrator = get_orchestrator()
        orchestrator = Orchestrator(
            enable_cache=True,
            enable_intelligence=True
        )

        print("Running debate on refactoring plan...")
        print("=" * 60)

        # Run the debate
        result = await orchestrator.run_debate(
            request="Review this authentication refactoring plan for security and maintainability",
            file_path=str(plan_file.absolute()),
            focus_areas=["security", "architecture", "testing"]
        )

        # Display results
        debate = result.get("debate_result", {})
        stats = result.get("performance_stats", {})

        print(f"\nConsensus Score: {debate.get('consensus_score', 0)}/100")
        print(f"Interpretation: {debate.get('interpretation', 'N/A')}")
        print(f"Recommendation: {debate.get('recommendation', 'N/A')}")

        # Claude perspective
        claude = debate.get("claude", {})
        print(f"\n--- Claude Perspective ({claude.get('score', 'N/A')}/100) ---")
        if claude.get("summary"):
            print(claude["summary"][:300] + "...")

        # Codex perspective
        codex = debate.get("codex", {})
        print(f"\n--- Codex Perspective ({codex.get('score', 'N/A')}/100) ---")
        if codex.get("summary"):
            print(codex["summary"][:300] + "...")

        # Agreements
        if debate.get("agreements"):
            print("\n--- Key Agreements ---")
            for agreement in debate["agreements"][:3]:
                print(f"  - {agreement[:100]}")

        # Disagreements
        if debate.get("disagreements"):
            print("\n--- Key Disagreements ---")
            for disagreement in debate["disagreements"][:3]:
                print(f"  - [{disagreement.get('source', 'N/A')}]: {disagreement.get('text', '')[:100]}")

        print(f"\n--- Performance ---")
        print(f"Total time: {stats.get('total_time', 0):.1f}s")
        print(f"Cache hit: {stats.get('cache_hit', False)}")

    finally:
        # Cleanup
        if plan_file.exists():
            plan_file.unlink()


if __name__ == "__main__":
    asyncio.run(main())
