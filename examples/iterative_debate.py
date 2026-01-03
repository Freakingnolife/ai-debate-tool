"""Iterative Debate Example

This example shows how to run iterative debates that automatically
revise plans until reaching target consensus.
"""

import asyncio
from pathlib import Path


async def main():
    from ai_debate_tool.services.iterative_debate_engine import IterativeDebateEngine

    # Sample plan that might need revision
    initial_plan = """# API Design Plan

## Endpoints
- POST /users - Create user
- GET /users/{id} - Get user
- PUT /users/{id} - Update user
- DELETE /users/{id} - Delete user

## Authentication
- JWT tokens
- No rate limiting
- Passwords stored in plain text

## Database
- Direct SQL queries
- No connection pooling
"""

    # Create temporary file
    plan_file = Path("api_plan.md")
    plan_file.write_text(initial_plan)

    try:
        # Create iterative debate engine
        engine = IterativeDebateEngine(
            target_consensus=85,
            max_rounds=5
        )

        print("Starting iterative debate...")
        print("Target consensus: 85/100")
        print("=" * 60)

        # Run iterative debate
        final_result = await engine.run_iterative_debate(
            request="Review this API design for security best practices",
            file_path=str(plan_file.absolute()),
            focus_areas=["security", "performance", "best-practices"]
        )

        print(f"\n=== Final Results ===")
        print(f"Rounds completed: {final_result.get('rounds_completed', 0)}")
        print(f"Final consensus: {final_result.get('final_consensus', 0)}/100")
        print(f"Target reached: {final_result.get('target_reached', False)}")

        # Show revision history
        if final_result.get("revision_history"):
            print("\n--- Revision History ---")
            for i, revision in enumerate(final_result["revision_history"], 1):
                print(f"\nRound {i}:")
                print(f"  Consensus: {revision.get('consensus', 0)}/100")
                print(f"  Key changes: {revision.get('changes_made', 'N/A')[:100]}")

        # Show final plan if revised
        if final_result.get("final_plan"):
            print("\n--- Final Revised Plan ---")
            print(final_result["final_plan"][:500] + "...")

    finally:
        if plan_file.exists():
            plan_file.unlink()


if __name__ == "__main__":
    asyncio.run(main())
