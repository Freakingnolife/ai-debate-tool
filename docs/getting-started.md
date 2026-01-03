# Getting Started with AI Debate Tool

This guide will help you set up and run your first AI debate.

## Prerequisites

1. **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
2. **Codex CLI** - Install and authenticate with OpenAI Codex

## Installation

```bash
pip install ai-debate-tool
```

Verify installation:
```bash
ai-debate --version
```

## Your First Debate

### Option 1: CLI

```bash
# Create a sample plan file
echo "# Refactoring Plan
## Changes
- Split views.py into modules
- Add caching layer
- Update tests" > my_plan.md

# Run a debate
ai-debate run "Review this refactoring plan" --file my_plan.md -v
```

### Option 2: Python API

```python
import asyncio
from ai_debate_tool import get_orchestrator

async def main():
    Orchestrator = get_orchestrator()
    orchestrator = Orchestrator()

    result = await orchestrator.run_debate(
        request="Should we proceed with this refactoring?",
        file_path="my_plan.md"
    )

    print(f"Consensus: {result['debate_result']['consensus_score']}/100")
    print(f"Recommendation: {result['debate_result']['recommendation']}")

asyncio.run(main())
```

## Understanding Results

### Consensus Score

| Score | Meaning | Action |
|-------|---------|--------|
| 90+ | Strong agreement | Proceed confidently |
| 75-89 | Good agreement | Minor review needed |
| 60-74 | Moderate agreement | Discuss key points |
| <60 | Disagreement | Address concerns first |

### Output Structure

```python
{
    "debate_result": {
        "consensus_score": 85,
        "interpretation": "Good Agreement",
        "recommendation": "[PROCEED]",
        "claude": {"score": 88, "summary": "..."},
        "codex": {"score": 82, "summary": "..."},
        "agreements": ["...", "..."],
        "disagreements": [{"source": "...", "text": "..."}]
    },
    "performance_stats": {
        "total_time": 12.5,
        "cache_hit": false
    }
}
```

## Configuration

Initialize a config file:
```bash
ai-debate config --init
```

This creates `~/.config/ai-debate-tool/config.json`:
```json
{
    "enabled": true,
    "complexity_threshold": 40,
    "target_consensus": 75,
    "enable_cache": true,
    "enable_intelligence": true
}
```

## Next Steps

- [CLI Reference](cli-reference.md) - Full CLI documentation
- [Architecture](architecture.md) - How it works under the hood
- [Examples](../examples/) - More usage examples
