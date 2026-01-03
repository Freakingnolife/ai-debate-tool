# Architecture

This document describes the internal architecture of AI Debate Tool.

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                    AI Debate Tool                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │   CLI    │  │  Python API      │  │  MCP Server  │  │
│  │ (cli.py) │  │  (__init__.py)   │  │  (v1.1)      │  │
│  └────┬─────┘  └────────┬─────────┘  └──────────────┘  │
│       │                 │                               │
│       └────────┬────────┘                               │
│                ▼                                        │
│  ┌─────────────────────────────────────┐               │
│  │   ParallelDebateOrchestrator        │               │
│  │   - Coordinates debate flow         │               │
│  │   - Manages caching                 │               │
│  │   - Integrates intelligence         │               │
│  └───────────────┬─────────────────────┘               │
│                  │                                      │
│    ┌─────────────┼─────────────┐                       │
│    ▼             ▼             ▼                       │
│  ┌────────┐ ┌──────────┐ ┌──────────────┐             │
│  │ Codex  │ │   Fast   │ │ Intelligence │             │
│  │Invoker │ │Moderator │ │   System     │             │
│  └────────┘ └──────────┘ └──────────────┘             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Entry Points

#### CLI (`cli.py`)
- Click-based command-line interface
- Commands: `run`, `check`, `history`, `config`
- Wraps the Python API

#### Python API (`__init__.py`)
- Exports main functions and classes
- Lazy loading for heavy services

### 2. Orchestration Layer

#### ParallelDebateOrchestrator
The main orchestrator that coordinates the entire debate flow.

```python
class ParallelDebateOrchestrator:
    def __init__(
        self,
        enable_cache: bool = True,
        enable_intelligence: bool = True
    ):
        self.cache = DebateCache() if enable_cache else None
        self.history = DebateHistoryManager()
        self.pattern_detector = PatternDetector()
        self.risk_predictor = RiskPredictor()
        self.decision_learner = DecisionLearner()
        self.smart_recommender = SmartRecommender()

    async def run_debate(
        self,
        request: str,
        file_path: str,
        focus_areas: list = None
    ) -> dict:
        # 1. Pre-debate intelligence
        # 2. Check cache
        # 3. Run parallel LLM calls
        # 4. Moderate consensus
        # 5. Post-debate learning
        # 6. Return results
```

### 3. LLM Integration

#### CodexCLIInvoker
Invokes Codex CLI via subprocess for AI perspectives.

```python
class CodexCLIInvoker:
    def invoke(self, prompt: str, perspective: str) -> dict:
        # Runs: codex --prompt "..." --mode chat
        # Returns: {"score": int, "summary": str, ...}
```

**Why CLI instead of API?**
- Zero API costs (uses local Codex installation)
- Works offline after authentication
- Consistent with user's existing setup

### 4. Moderation

#### FastModerator
Rule-based consensus calculation (fast, ~5 seconds).

```python
class FastModerator:
    def calculate_consensus(
        self,
        claude_response: dict,
        codex_response: dict
    ) -> dict:
        # Compare scores
        # Identify agreements/disagreements
        # Calculate weighted consensus
        # Return interpretation
```

### 5. Intelligence System

#### Pattern Detector
Identifies recurring patterns in debate history.

```python
class PatternDetector:
    def detect_patterns(self) -> list:
        # TF-IDF analysis
        # Keyword matching
        # File pattern recognition
```

#### Risk Predictor
Predicts risks before debate based on history.

```python
class RiskPredictor:
    def predict_risks(self, request: str, file_path: str) -> dict:
        # Match against known risk patterns
        # Return predictions with confidence
```

#### Decision Learner
Learns from debate outcomes.

```python
class DecisionLearner:
    def learn_from_outcome(
        self,
        debate_id: str,
        outcome: str,  # "succeeded" | "failed"
        notes: str
    ):
        # Update learned rules
        # Adjust future predictions
```

#### Smart Recommender
Unified intelligence API.

```python
class SmartRecommender:
    def get_pre_debate_analysis(self, request: str, file_path: str) -> dict:
        # Combine all intelligence sources
        # Return unified analysis
```

### 6. Caching & Storage

#### Debate Cache
5-minute TTL cache for identical requests.

```python
class DebateCache:
    def get(self, key: str) -> Optional[dict]:
        # Check cache, validate TTL
        # Return cached result or None

    def set(self, key: str, result: dict):
        # Store with timestamp
```

#### Debate History Manager
Persistent JSON storage for debate history.

```
.cache/debate_history/
├── debates/           # Individual debate records
├── metadata/          # Index files
└── patterns/          # Pattern analysis cache
```

## Data Flow

### Run Debate Flow

```
1. Request received
   │
2. ├── Check cache ──────────────────────► Cache hit? Return cached
   │
3. ├── Pre-debate intelligence
   │   ├── Pattern detection
   │   ├── Risk prediction
   │   └── Smart recommendations
   │
4. ├── Parallel LLM calls
   │   ├── Claude perspective ─────────────┐
   │   └── Codex perspective ──────────────┤
   │                                       │
5. ├── Await both responses ◄──────────────┘
   │
6. ├── Fast moderation
   │   ├── Calculate consensus
   │   ├── Identify agreements
   │   └── Identify disagreements
   │
7. ├── Post-debate processing
   │   ├── Save to history
   │   ├── Update patterns
   │   └── Cache result
   │
8. └── Return result
```

## File Structure

```
src/ai_debate_tool/
├── __init__.py              # Package exports
├── cli.py                   # CLI entry point
├── config.py                # Configuration management
├── enforcement_gate.py      # Complexity checking
├── file_protocol.py         # File-based session management
│
└── services/
    ├── parallel_debate_orchestrator.py  # Main orchestrator
    ├── ai_orchestrator.py               # Automation controller
    │
    ├── codex_cli_invoker.py            # Codex CLI wrapper
    ├── copilot_invoker.py              # VS Code Copilot bridge
    │
    ├── fast_moderator.py               # Rule-based consensus
    ├── moderator_service.py            # LLM-based moderation
    │
    ├── debate_cache.py                 # 5-min TTL cache
    ├── debate_history_manager.py       # Persistent storage
    │
    ├── pattern_detector.py             # Pattern analysis
    ├── risk_predictor.py               # Risk prediction
    ├── decision_learner.py             # Outcome learning
    ├── smart_recommender.py            # Unified intelligence
    │
    ├── prompt_optimizer.py             # Context extraction
    ├── delta_debate.py                 # Incremental debates
    ├── iterative_debate_engine.py      # Multi-round debates
    └── ...
```

## Performance

| Metric | Value |
|--------|-------|
| Typical debate time | 10-18 seconds |
| Cache hit time | <1 second |
| Intelligence overhead | 1-2 seconds |
| Memory footprint | ~50MB |

## Extension Points

### Adding New Perspectives
Implement the invoker interface:

```python
class CustomInvoker:
    def invoke(self, prompt: str, perspective: str) -> dict:
        return {
            "score": int,
            "summary": str,
            "details": dict
        }
```

### Custom Moderators
Implement the moderator interface:

```python
class CustomModerator:
    def calculate_consensus(
        self,
        perspective_a: dict,
        perspective_b: dict
    ) -> dict:
        return {
            "consensus_score": int,
            "interpretation": str,
            "agreements": list,
            "disagreements": list
        }
```
