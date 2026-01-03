"""
Parallel Debate Orchestrator - Async execution with intelligence.

Coordinates Phase 2 + Phase 3 components:
PHASE 2 (Performance):
1. PromptOptimizer - Extract relevant context (parallel)
2. DebateCache - Check cache before invoking LLMs
3. Parallel LLM calls - Claude + Codex simultaneously
4. FastModerator - Quick consensus analysis

PHASE 3 (Intelligence):
5. DebateHistoryManager - Save all debates for learning
6. PatternDetector - Identify recurring issues
7. RiskPredictor - Predict risks before debate
8. DecisionLearner - Learn from outcomes
9. SmartRecommender - Pre-debate intelligence

Target: 18-30 second debates with proactive intelligence
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .prompt_optimizer import PromptOptimizer
from .debate_cache import DebateCache
from .fast_moderator import FastModerator
from .codex_cli_invoker import CodexCLIInvoker
from .debate_history_manager import DebateHistoryManager
from .pattern_detector import PatternDetector
from .risk_predictor import RiskPredictor
from .decision_learner import DecisionLearner
from .smart_recommender import SmartRecommender


class ParallelDebateOrchestrator:
    """Orchestrate debates with parallel execution for maximum speed."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        cache_ttl_minutes: int = 5,
        enable_cache: bool = True,
        enable_history: bool = True,
        enable_intelligence: bool = True
    ):
        """
        Initialize orchestrator.

        Args:
            cache_dir: Directory for debate cache
            cache_ttl_minutes: Cache TTL (default 5 minutes)
            enable_cache: Enable caching (default True)
            enable_history: Enable debate history (default True, Phase 3.0)
            enable_intelligence: Enable intelligence features (default True, Phase 3.1-3.4)
        """
        self.cache = DebateCache(cache_dir, cache_ttl_minutes) if enable_cache else None
        self.enable_cache = enable_cache
        self.codex_invoker = CodexCLIInvoker()  # Single Codex CLI for both perspectives

        # Phase 3: Intelligence system
        self.history = DebateHistoryManager() if enable_history else None
        self.enable_history = enable_history
        self.enable_intelligence = enable_intelligence

        # Initialize intelligence components (Phase 3.1-3.4)
        if enable_intelligence and enable_history and self.history:
            self.pattern_detector = PatternDetector(self.history)
            self.risk_predictor = RiskPredictor(self.pattern_detector)
            self.decision_learner = DecisionLearner(self.history, self.pattern_detector)
            self.smart_recommender = SmartRecommender(
                self.history,
                self.pattern_detector,
                self.risk_predictor,
                self.decision_learner
            )
        else:
            self.pattern_detector = None
            self.risk_predictor = None
            self.decision_learner = None
            self.smart_recommender = None

    async def run_debate(
        self,
        request: str,
        file_path: str,
        focus_areas: Optional[List[str]] = None,
        use_phase1_format: bool = True
    ) -> Dict:
        """
        Run complete debate with parallel execution.

        Args:
            request: User's debate request
            file_path: Path to file to debate
            focus_areas: Optional focus areas (auto-inferred if None)
            use_phase1_format: Use Phase 1 structured format (default True)

        Returns:
            {
                'debate_result': dict (Phase 1 decision pack),
                'performance_stats': dict,
                'cache_hit': bool,
                'total_time': float (seconds)
            }
        """
        start_time = time.time()
        stats = {
            'context_extraction_time': 0,
            'claude_time': 0,
            'codex_time': 0,
            'moderation_time': 0,
            'intelligence_time': 0,  # Phase 3
            'cache_hit_claude': False,
            'cache_hit_codex': False,
        }

        # Phase 3: Pre-debate intelligence analysis (optional, fast ~1-2 seconds)
        pre_debate_analysis = None
        if self.enable_intelligence and self.smart_recommender:
            intel_start = time.time()
            pre_debate_analysis = self.smart_recommender.analyze_pre_debate(
                request,
                file_path,
                focus_areas
            )
            stats['intelligence_time'] = time.time() - intel_start

            # Use intelligence-suggested focus areas if available
            if not focus_areas:
                focus_areas = pre_debate_analysis['suggested_focus_areas']
        elif not focus_areas:
            # Fallback: Infer focus areas (Phase 2 behavior)
            focus_areas = PromptOptimizer.infer_focus_areas(request)

        # Step 2: Extract relevant context (fast - ~2 seconds)
        context_start = time.time()
        context = PromptOptimizer.extract_relevant_context(
            file_path,
            focus_areas,
            max_lines=200
        )
        stats['context_extraction_time'] = time.time() - context_start

        # Step 3: Create focused prompts for both AIs
        file_hash = DebateCache.hash_file_content(file_path) if self.enable_cache else None

        # Create Claude perspective prompt (primary analysis)
        claude_base_prompt = PromptOptimizer.create_focused_prompt(
            request,
            context,
            focus_areas
        )
        claude_prompt = claude_base_prompt + "\n\n**IMPORTANT: End your response with a numerical score (0-100) like 'Score: 85/100'**"

        codex_prompt = self._create_codex_prompt(request, context, focus_areas)

        # Step 4: Check cache for both (parallel check)
        claude_cached = None
        codex_cached = None

        if self.enable_cache:
            claude_cached = self.cache.get(claude_prompt, file_hash)
            codex_cached = self.cache.get(codex_prompt, file_hash)

            stats['cache_hit_claude'] = claude_cached is not None
            stats['cache_hit_codex'] = codex_cached is not None

        # Step 5: Run LLM calls in parallel (only for cache misses)
        claude_result, codex_result = await self._run_parallel_llm_calls(
            claude_prompt,
            codex_prompt,
            claude_cached,
            codex_cached,
            file_hash,
            stats
        )

        # Step 6: Fast moderation (rule-based - ~5 seconds)
        moderation_start = time.time()
        consensus = FastModerator.analyze(claude_result, codex_result)
        stats['moderation_time'] = time.time() - moderation_start

        # Step 7: Format results (Phase 1 format if requested)
        if use_phase1_format:
            debate_result = self._format_phase1_result(
                request,
                claude_result,
                codex_result,
                consensus
            )
        else:
            debate_result = {
                'claude': claude_result,
                'codex': codex_result,
                'consensus': consensus
            }

        total_time = time.time() - start_time
        stats['total_time'] = total_time

        # Phase 3: Enhance result with learning-based adjustments
        if self.enable_intelligence and self.smart_recommender and pre_debate_analysis:
            debate_result = self.smart_recommender.enhance_debate_result(
                debate_result,
                pre_debate_analysis
            )

        # Save to history (Phase 3)
        debate_id = None
        if self.enable_history and self.history:
            debate_id = self.history.save_debate(
                request=request,
                file_path=file_path,
                debate_result=debate_result,
                performance_stats=stats,
                focus_areas=focus_areas or []
            )

            # Update patterns detected in history (Phase 3)
            if self.enable_intelligence and pre_debate_analysis:
                # Store patterns in debate record for future learning
                debate_record = self.history.get_debate(debate_id)
                if debate_record and pre_debate_analysis.get('learning_prep'):
                    debate_record['patterns_detected'] = pre_debate_analysis['learning_prep']['patterns_to_detect']
                    # Save updated record
                    import json
                    debate_file = self.history.debates_dir / f'{debate_id}.json'
                    with open(debate_file, 'w', encoding='utf-8') as f:
                        json.dump(debate_record, f, indent=2, ensure_ascii=False)

        return {
            'debate_result': debate_result,
            'performance_stats': stats,
            'cache_hit': stats['cache_hit_claude'] and stats['cache_hit_codex'],
            'total_time': total_time,
            'debate_id': debate_id,  # Phase 3: for outcome tracking
            'pre_debate_analysis': pre_debate_analysis  # Phase 3: intelligence insights
        }

    async def _run_parallel_llm_calls(
        self,
        claude_prompt: str,
        codex_prompt: str,
        claude_cached: Optional[Dict],
        codex_cached: Optional[Dict],
        file_hash: Optional[str],
        stats: Dict
    ) -> Tuple[Dict, Dict]:
        """
        Run Claude and Codex calls in parallel (only for cache misses).

        Args:
            claude_prompt: Prompt for Claude
            codex_prompt: Prompt for Codex
            claude_cached: Cached Claude result (or None)
            codex_cached: Cached Codex result (or None)
            file_hash: File hash for caching
            stats: Performance stats dict (updated in-place)

        Returns:
            (claude_result, codex_result) tuple
        """
        tasks = []

        # Claude task (if not cached)
        if claude_cached is None:
            tasks.append(self._call_claude(claude_prompt, file_hash, stats))
        else:
            # Use cached result (instant)
            tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Dummy task

        # Codex task (if not cached)
        if codex_cached is None:
            tasks.append(self._call_codex(codex_prompt, file_hash, stats))
        else:
            # Use cached result (instant)
            tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Dummy task

        # Run in parallel
        await asyncio.gather(*tasks)

        # Return results (cached or fresh)
        claude_result = claude_cached if claude_cached else self._last_claude_result
        codex_result = codex_cached if codex_cached else self._last_codex_result

        return claude_result, codex_result

    async def _call_claude(
        self,
        prompt: str,
        file_hash: Optional[str],
        stats: Dict
    ) -> Dict:
        """
        Call Codex CLI with "Claude perspective" prompt (primary analysis).

        Args:
            prompt: Prompt for Claude perspective
            file_hash: File hash for caching
            stats: Performance stats dict

        Returns:
            Analysis result from Codex CLI (Claude perspective)
        """
        start = time.time()

        # Use Codex CLI for primary analysis (Claude perspective)
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        codex_result = await loop.run_in_executor(
            None,
            self.codex_invoker.invoke,
            prompt
        )

        if not codex_result['success']:
            # Fallback to placeholder on error
            result = {
                'score': 75,
                'response': f"Codex CLI error: {codex_result.get('error', 'Unknown error')}",
                'analysis': 'Error occurred during analysis'
            }
        else:
            # Parse Codex response (extract score if provided)
            response_text = codex_result['response']
            result = {
                'score': self._extract_score(response_text, default=80),
                'response': response_text,
                'analysis': response_text
            }

        stats['claude_time'] = time.time() - start

        # Cache result
        if self.enable_cache and self.cache:
            self.cache.set(prompt, result, file_hash)

        self._last_claude_result = result
        return result

    async def _call_codex(
        self,
        prompt: str,
        file_hash: Optional[str],
        stats: Dict
    ) -> Dict:
        """
        Call Codex CLI with "Codex perspective" prompt (counter-proposal).

        Args:
            prompt: Prompt for Codex perspective
            file_hash: File hash for caching
            stats: Performance stats dict

        Returns:
            Analysis result from Codex CLI (Codex perspective)
        """
        start = time.time()

        # Use Codex CLI for counter-proposal (Codex perspective)
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        codex_result = await loop.run_in_executor(
            None,
            self.codex_invoker.invoke,
            prompt
        )

        if not codex_result['success']:
            # Fallback to placeholder on error
            result = {
                'score': 70,
                'response': f"Codex CLI error: {codex_result.get('error', 'Unknown error')}",
                'analysis': 'Error occurred during counter-analysis'
            }
        else:
            # Parse Codex response (extract score if provided)
            response_text = codex_result['response']
            result = {
                'score': self._extract_score(response_text, default=75),
                'response': response_text,
                'analysis': response_text
            }

        stats['codex_time'] = time.time() - start

        # Cache result
        if self.enable_cache and self.cache:
            self.cache.set(prompt, result, file_hash)

        self._last_codex_result = result
        return result

    def _create_codex_prompt(
        self,
        request: str,
        context: str,
        focus_areas: List[str]
    ) -> str:
        """
        Create Codex-specific prompt (counter-proposal perspective).

        Args:
            request: User's debate request
            context: Extracted context
            focus_areas: Focus areas

        Returns:
            Codex prompt string
        """
        prompt = f"""You are a senior software architect providing a COUNTER-PERSPECTIVE on this plan.

USER REQUEST:
{request}

RELEVANT CONTEXT:
{context}

FOCUS AREAS:
{chr(10).join(f'- {area.replace("_", " ").title()}' for area in focus_areas)}

Your task as a CRITICAL REVIEWER:
1. Provide YOUR independent analysis (be skeptical and critical)
2. Identify risks and concerns that others might miss
3. Suggest alternative approaches if the current plan has flaws
4. End with recommendation and numerical score (0-100)

Be specific, actionable, and CRITICAL. Focus on {', '.join(focus_areas)}.

**IMPORTANT: End your response with a score like 'Score: 75/100'**
"""
        return prompt

    def _extract_score(self, response_text: str, default: int = 75) -> int:
        """
        Extract numerical score from Codex response.

        Args:
            response_text: Response text from Codex
            default: Default score if not found

        Returns:
            Extracted score (0-100)
        """
        import re

        # Look for patterns like "Score: 85", "85/100", "Rating: 85"
        patterns = [
            r'(?:score|rating):\s*(\d{1,3})',
            r'(\d{1,3})\s*/\s*100',
            r'(?:give|assign)\s+(?:it\s+)?(?:a\s+)?(\d{1,3})'
        ]

        for pattern in patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                # Validate range
                if 0 <= score <= 100:
                    return score

        return default

    def _format_phase1_result(
        self,
        request: str,
        claude_result: Dict,
        codex_result: Dict,
        consensus: Dict
    ) -> Dict:
        """
        Format result in Phase 1 structured format.

        Args:
            request: Original request
            claude_result: Claude's analysis
            codex_result: Codex's analysis
            consensus: FastModerator consensus

        Returns:
            Structured debate result
        """
        return {
            'request': request,
            'consensus_score': consensus['consensus_score'],
            'interpretation': consensus['interpretation'],
            'recommendation': consensus['recommendation'],
            'claude': {
                'score': claude_result.get('score', 0),
                'summary': claude_result.get('response', '')[:200]
            },
            'codex': {
                'score': codex_result.get('score', 0),
                'summary': codex_result.get('response', '')[:200]
            },
            'disagreements': consensus['disagreements'],
            'agreements': consensus['agreements'],
            'score_difference': consensus['score_difference']
        }

    def get_performance_report(self, stats: Dict) -> str:
        """
        Generate human-readable performance report.

        Args:
            stats: Performance stats from run_debate()

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("PARALLEL DEBATE PERFORMANCE REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Total time
        lines.append(f"Total Time: {stats['total_time']:.2f} seconds")
        lines.append("")

        # Breakdown
        lines.append("Breakdown:")
        lines.append(f"  Context Extraction: {stats['context_extraction_time']:.2f}s")
        lines.append(f"  Claude API Call:    {stats['claude_time']:.2f}s" +
                    (" (cached)" if stats['cache_hit_claude'] else ""))
        lines.append(f"  Codex CLI Call:     {stats['codex_time']:.2f}s" +
                    (" (cached)" if stats['cache_hit_codex'] else ""))
        lines.append(f"  Moderation:         {stats['moderation_time']:.2f}s")
        lines.append("")

        # Cache efficiency
        cache_hits = sum([stats['cache_hit_claude'], stats['cache_hit_codex']])
        lines.append(f"Cache Hits: {cache_hits}/2")
        if cache_hits == 2:
            lines.append("  Status: FULL CACHE HIT (instant result)")
        elif cache_hits == 1:
            lines.append("  Status: PARTIAL CACHE HIT (50% faster)")
        else:
            lines.append("  Status: CACHE MISS (full LLM calls)")
        lines.append("")

        # Speedup
        baseline_time = 60  # Baseline: 60 seconds average
        if stats['total_time'] < baseline_time:
            speedup = ((baseline_time - stats['total_time']) / baseline_time) * 100
            lines.append(f"Speedup: {speedup:.0f}% faster than baseline ({baseline_time}s)")
        else:
            lines.append(f"Note: Slower than baseline (network latency or large file)")
        lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)


# Convenience function for synchronous usage
def run_debate_sync(
    request: str,
    file_path: str,
    focus_areas: Optional[List[str]] = None,
    enable_cache: bool = True
) -> Dict:
    """
    Run debate synchronously (convenience wrapper).

    Args:
        request: User's debate request
        file_path: Path to file to debate
        focus_areas: Optional focus areas
        enable_cache: Enable caching (default True)

    Returns:
        Debate result dict
    """
    orchestrator = ParallelDebateOrchestrator(enable_cache=enable_cache)
    return asyncio.run(orchestrator.run_debate(request, file_path, focus_areas))
