"""
Integrated Debate Engine - Combines Phase 1 + Phase 2.

Phase 1 (Structured Output):
- PriorityScorer - Objective scoring (0-100)
- DecisionPackFormatter - Structured format (≤300 lines)
- TodoWriter - Auto-extract todos

Phase 2 (Performance):
- PromptOptimizer - Context extraction (200 lines vs 2000+)
- DebateCache - File-based caching (5-min TTL)
- FastModerator - Rule-based consensus (5 sec vs 20 sec)
- ParallelDebateOrchestrator - Async execution

Result: Fast (30-45 sec) + Concise (≤300 lines) + Actionable (auto todos)
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

# Phase 1 components
from .priority_scorer import PriorityScorer
from .decision_pack_formatter import DecisionPackFormatter
from .todo_writer import TodoWriter

# Phase 2 components
from .parallel_debate_orchestrator import ParallelDebateOrchestrator


class IntegratedDebateEngine:
    """Complete debate engine with Phase 1 + Phase 2 improvements."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        cache_ttl_minutes: int = 5,
        enable_cache: bool = True
    ):
        """
        Initialize integrated engine.

        Args:
            cache_dir: Directory for debate cache
            cache_ttl_minutes: Cache TTL (default 5 minutes)
            enable_cache: Enable caching (default True)
        """
        self.orchestrator = ParallelDebateOrchestrator(
            cache_dir=cache_dir,
            cache_ttl_minutes=cache_ttl_minutes,
            enable_cache=enable_cache
        )

    async def run_complete_debate(
        self,
        topic: str,
        file_path: str,
        focus_areas: Optional[List[str]] = None,
        issues: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Run complete debate with all Phase 1 + Phase 2 improvements.

        Args:
            topic: Debate topic (e.g., "v0.7.3 Refactoring Plan")
            file_path: Path to file/plan to debate
            focus_areas: Optional focus areas (auto-inferred if None)
            issues: Optional pre-identified issues to score

        Returns:
            {
                'decision_pack': str (structured markdown ≤300 lines),
                'todos': list[dict] (auto-extracted high-priority),
                'scored_issues': list[dict] (with priority scores),
                'consensus_score': int (0-100),
                'recommendation': str,
                'performance_stats': dict,
                'total_time': float (seconds)
            }
        """
        # Step 1: Run Phase 2 parallel debate (fast)
        debate_result = await self.orchestrator.run_debate(
            topic,
            file_path,
            focus_areas,
            use_phase1_format=False  # Get raw results for Phase 1 processing
        )

        raw_result = debate_result['debate_result']
        performance_stats = debate_result['performance_stats']

        # Step 2: Extract issues from debate (if not provided)
        if issues is None:
            issues = self._extract_issues_from_debate(raw_result)

        # Step 3: Apply Phase 1 - Score issues (objective priority)
        scored_issues = PriorityScorer.score_issues(issues)

        # Step 4: Apply Phase 1 - Format decision pack (≤300 lines)
        decision_pack = DecisionPackFormatter.format_structured(
            topic=topic,
            consensus_score=raw_result['consensus']['consensus_score'],
            claude_score=raw_result['claude']['score'],
            codex_score=raw_result['codex']['score'],
            debate_time_seconds=performance_stats['total_time'],
            scored_issues=scored_issues,
            disagreements=self._format_disagreements(raw_result),
            approved_aspects=[],  # Can be enhanced later
            alternatives=[]  # Can be enhanced later
        )

        # Step 5: Apply Phase 1 - Extract todos (high-priority only)
        todos = TodoWriter.extract_todos(scored_issues)

        return {
            'decision_pack': decision_pack,
            'todos': todos,
            'scored_issues': scored_issues,
            'consensus_score': raw_result['consensus']['consensus_score'],
            'recommendation': raw_result['consensus']['recommendation'],
            'performance_stats': performance_stats,
            'total_time': debate_result['total_time'],
            'cache_hit': debate_result['cache_hit']
        }

    def _extract_issues_from_debate(self, debate_result: Dict) -> List[Dict]:
        """
        Extract issues from debate disagreements.

        Args:
            debate_result: Raw debate result

        Returns:
            List of issues with severity/impact/effort
        """
        issues = []

        # Extract from disagreements
        for disagreement in debate_result['consensus']['disagreements']:
            # Infer severity from keywords
            text = disagreement['text'].lower()

            if any(kw in text for kw in ['critical', 'security', 'data loss', 'production']):
                severity = 'critical'
                impact = 'high'
            elif any(kw in text for kw in ['risk', 'concern', 'issue', 'problem']):
                severity = 'high'
                impact = 'high'
            elif any(kw in text for kw in ['missing', 'incomplete', 'unclear']):
                severity = 'medium'
                impact = 'medium'
            else:
                severity = 'low'
                impact = 'low'

            # Infer effort from keywords
            if any(kw in text for kw in ['add', 'create', 'implement', 'build']):
                effort = 'medium'
            elif any(kw in text for kw in ['update', 'clarify', 'specify', 'define']):
                effort = 'low'
            else:
                effort = 'low'

            issues.append({
                'title': disagreement['text'][:100],  # Truncate for title
                'description': disagreement['text'],
                'severity': severity,
                'impact': impact,
                'effort': effort,
                'source': disagreement['source'],
                'fix': f"Address {disagreement['source']}'s concern"
            })

        return issues

    def _format_disagreements(self, debate_result: Dict) -> List[Dict]:
        """
        Format disagreements for DecisionPackFormatter.

        Args:
            debate_result: Raw debate result

        Returns:
            List of formatted disagreements
        """
        disagreements = []

        for disagreement in debate_result['consensus']['disagreements']:
            disagreements.append({
                'topic': disagreement['text'][:50],  # Short topic
                'claude_view': debate_result['claude']['summary'] if disagreement['source'] == 'Claude' else 'See Codex view',
                'codex_view': debate_result['codex']['summary'] if disagreement['source'] == 'Codex' else 'See Claude view',
                'impact': 'HIGH',  # Can be refined
                'recommendation': 'Discuss and resolve before proceeding'
            })

        return disagreements[:5]  # Limit to top 5

    def get_complete_report(self, result: Dict) -> str:
        """
        Generate complete report with decision pack + performance stats.

        Args:
            result: Result from run_complete_debate()

        Returns:
            Formatted report string
        """
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("INTEGRATED DEBATE RESULT (Phase 1 + Phase 2)")
        lines.append("=" * 80)
        lines.append("")

        # Performance summary
        lines.append(f"Consensus Score: {result['consensus_score']}/100")
        lines.append(f"Recommendation: {result['recommendation']}")
        lines.append(f"Total Time: {result['total_time']:.2f} seconds")
        lines.append(f"Cache Hit: {'Yes (instant)' if result['cache_hit'] else 'No (full debate)'}")
        lines.append("")

        # Issues summary
        lines.append(f"Issues Identified: {len(result['scored_issues'])}")
        high_priority = [i for i in result['scored_issues'] if i.get('priority_score', 0) >= 65]
        lines.append(f"High-Priority Todos: {len(high_priority)}")
        lines.append("")

        # Decision pack
        lines.append("=" * 80)
        lines.append("DECISION PACK")
        lines.append("=" * 80)
        lines.append("")
        lines.append(result['decision_pack'])
        lines.append("")

        # Todos
        if result['todos']:
            lines.append("=" * 80)
            lines.append("AUTO-EXTRACTED TODOS (Ready for TodoWrite)")
            lines.append("=" * 80)
            lines.append("")
            lines.append(TodoWriter.format_todos_as_markdown(result['todos']))
            lines.append("")

        # Performance stats
        lines.append("=" * 80)
        lines.append("PERFORMANCE BREAKDOWN")
        lines.append("=" * 80)
        lines.append("")
        lines.append(self.orchestrator.get_performance_report(result['performance_stats']))

        return "\n".join(lines)


# Convenience function for synchronous usage
def run_integrated_debate_sync(
    topic: str,
    file_path: str,
    focus_areas: Optional[List[str]] = None,
    issues: Optional[List[Dict]] = None,
    enable_cache: bool = True
) -> Dict:
    """
    Run integrated debate synchronously (convenience wrapper).

    Args:
        topic: Debate topic
        file_path: Path to file/plan to debate
        focus_areas: Optional focus areas
        issues: Optional pre-identified issues
        enable_cache: Enable caching (default True)

    Returns:
        Complete debate result dict
    """
    engine = IntegratedDebateEngine(enable_cache=enable_cache)
    return asyncio.run(engine.run_complete_debate(topic, file_path, focus_areas, issues))
