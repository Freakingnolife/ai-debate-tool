"""Iterative Debate Engine - Automatic plan revision until target consensus.

Orchestrates iterative debates with AI-powered plan revision:
1. Run initial full debate (Claude vs Codex)
2. If consensus < target, AI revises plan based on feedback
3. Re-debate with revised plan using fast delta mode
4. Repeat until consensus >= target or max iterations
5. Return best result across all iterations

Features:
- Automatic plan revision using Codex CLI
- Fast re-checks using delta debate (5-10s vs 30-60s)
- Best result tracking (even if later iterations regress)
- Comprehensive iteration history
- Configurable stopping criteria

Usage:
    from ai_debate_tool.services.iterative_debate_engine import IterativeDebateEngine
    from ai_debate_tool.services.integrated_debate_engine import IntegratedDebateEngine
    from ai_debate_tool.services.plan_reviser import PlanReviser
    from ai_debate_tool.services.delta_debate import DeltaDebate
    from ai_debate_tool.services.codex_cli_invoker import CodexCLIInvoker
    from ai_debate_tool.config import DebateConfig

    config = DebateConfig(target_consensus=90, max_rounds=5)
    engine = IterativeDebateEngine(
        integrated_engine=IntegratedDebateEngine(),
        plan_reviser=PlanReviser(CodexCLIInvoker()),
        delta_debate=DeltaDebate(),
        config=config
    )

    result = await engine.run_iterative_debate(
        topic="v0.9.9 Payment Refactoring",
        file_path="plans/payment_refactoring.md",
        target_consensus=90
    )

    print(f"Best consensus: {result['best_consensus']}/100")
    print(f"Iterations: {result['total_iterations']}")
"""

import asyncio
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class IterativeDebateEngine:
    """Orchestrate iterative debates with automatic plan revision."""

    def __init__(
        self,
        integrated_engine,
        plan_reviser,
        delta_debate,
        config
    ):
        """Initialize iterative debate engine.

        Args:
            integrated_engine: IntegratedDebateEngine instance
            plan_reviser: PlanReviser instance
            delta_debate: DeltaDebate instance
            config: DebateConfig instance
        """
        self.integrated_engine = integrated_engine
        self.plan_reviser = plan_reviser
        self.delta_debate = delta_debate
        self.config = config

        # Iteration tracking
        self.iteration_history = []
        self.best_result = None
        self.best_consensus = 0
        self.best_iteration = 0
        self.previous_debate_id = None

    async def run_iterative_debate(
        self,
        topic: str,
        file_path: str,
        focus_areas: Optional[List[str]] = None,
        target_consensus: Optional[int] = None,
        max_iterations: Optional[int] = None
    ) -> Dict:
        """Run iterative debate with automatic plan revision.

        Args:
            topic: Debate topic (e.g., "v0.9.9 Payment Refactoring Plan")
            file_path: Path to plan file
            focus_areas: Optional focus areas (auto-inferred if None)
            target_consensus: Target consensus score (default: config.target_consensus)
            max_iterations: Max iterations (default: config.max_rounds)

        Returns:
            {
                'best_result': dict (best iteration's debate result),
                'best_consensus': int (highest score achieved),
                'best_iteration': int (which iteration was best),
                'final_consensus': int (last iteration's score),
                'total_iterations': int,
                'iterations': list[dict] (full history),
                'target_reached': bool,
                'total_time': float,
                'warnings': list[str],
                'plan_file_path': str,
                'final_plan_hash': str,
                'total_revisions': int
            }
        """
        start_time = time.time()

        # Use config defaults if not provided
        target_consensus = target_consensus or self.config.target_consensus
        max_iterations = max_iterations or self.config.max_rounds

        # Initialize tracking
        self.iteration_history = []
        self.best_result = None
        self.best_consensus = 0
        self.best_iteration = 0
        self.previous_debate_id = None

        warnings = []
        no_improvement_count = 0
        previous_consensus = 0
        total_revisions = 0

        # ═══════════════════════════════════════════════════════════
        # Iteration 1: Full Debate
        # ═══════════════════════════════════════════════════════════

        iteration = 1
        iteration_start = time.time()

        debate_result = await self.integrated_engine.run_complete_debate(
            topic,
            file_path,
            focus_areas,
            issues=None
        )

        iteration_time = time.time() - iteration_start
        consensus = debate_result['consensus_score']

        # Track iteration
        self._track_iteration({
            'iteration': iteration,
            'type': 'full_debate',
            'consensus_score': consensus,
            'issues_addressed': [],
            'revision_summary': None,
            'time_seconds': iteration_time,
            'is_best': True  # First iteration is initially best
        })

        # Save as best result (initial baseline)
        self.best_result = debate_result
        self.best_consensus = consensus
        self.best_iteration = iteration

        # Save debate for delta mode
        self._save_debate_for_delta(file_path, debate_result)

        # Check if target reached on first try
        if consensus >= target_consensus:
            return self._format_result(
                target_consensus,
                time.time() - start_time,
                file_path,
                total_revisions,
                warnings
            )

        previous_consensus = consensus

        # ═══════════════════════════════════════════════════════════
        # Iterations 2-N: Revision + Delta Debate
        # ═══════════════════════════════════════════════════════════

        for iteration in range(2, max_iterations + 1):
            # Check stopping criteria
            should_stop, stop_reason = self._check_stopping_criteria(
                iteration,
                consensus,
                target_consensus,
                max_iterations
            )

            if should_stop:
                if stop_reason:
                    warnings.append(stop_reason)
                break

            iteration_start = time.time()

            # ─────────────────────────────────────────────────────
            # Step 1: Revise plan based on previous debate feedback
            # ─────────────────────────────────────────────────────

            revision_result = self.plan_reviser.revise_plan(
                plan_file_path=file_path,
                debate_result=debate_result,
                target_consensus=target_consensus
            )

            if not revision_result['success']:
                warnings.append(
                    f"Iteration {iteration}: Revision failed - {revision_result['error']}"
                )
                # Skip this iteration, try next
                continue

            # ─────────────────────────────────────────────────────
            # Step 2: Write revised plan to file (overwrite)
            # ─────────────────────────────────────────────────────

            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(revision_result['revised_content'])
                total_revisions += 1
            except IOError as e:
                warnings.append(
                    f"Iteration {iteration}: File write failed - {e}"
                )
                # Skip this iteration, preserve previous plan
                continue

            # ─────────────────────────────────────────────────────
            # Step 3: Detect changes for delta debate
            # ─────────────────────────────────────────────────────

            change_info = self.delta_debate.detect_changes(
                file_path=file_path,
                previous_debate_id=self.previous_debate_id
            )

            # ─────────────────────────────────────────────────────
            # Step 4: Re-debate (delta mode if < 30% changed)
            # ─────────────────────────────────────────────────────

            if change_info['has_changes'] and self.delta_debate.should_use_delta_mode(change_info):
                # Fast delta debate (5-10s)
                debate_result = await self.integrated_engine.run_complete_debate(
                    topic,
                    file_path,
                    focus_areas,
                    issues=None
                )
                debate_type = 'delta_debate'
            else:
                # Full debate if > 30% changed or no previous debate
                debate_result = await self.integrated_engine.run_complete_debate(
                    topic,
                    file_path,
                    focus_areas,
                    issues=None
                )
                debate_type = 'full_debate'

            iteration_time = time.time() - iteration_start
            consensus = debate_result['consensus_score']

            # ─────────────────────────────────────────────────────
            # Step 5: Track results
            # ─────────────────────────────────────────────────────

            # Update best result if current is better
            is_best = self._update_best_result(debate_result, consensus, iteration)

            # Track iteration
            self._track_iteration({
                'iteration': iteration,
                'type': debate_type,
                'consensus_score': consensus,
                'issues_addressed': revision_result['issues_addressed'],
                'revision_summary': revision_result['revision_summary'],
                'time_seconds': iteration_time,
                'is_best': is_best
            })

            # Save debate for next delta
            self._save_debate_for_delta(file_path, debate_result)

            # ─────────────────────────────────────────────────────
            # Step 6: Check progress
            # ─────────────────────────────────────────────────────

            # Check if target reached
            if consensus >= target_consensus:
                break

            # Check for no improvement
            improvement = consensus - previous_consensus
            if improvement < self.config.min_improvement_threshold:
                no_improvement_count += 1
                if no_improvement_count >= 2:
                    warnings.append(
                        f"No significant improvement in 2 consecutive iterations "
                        f"(iterations {iteration-1}-{iteration})"
                    )
            else:
                no_improvement_count = 0  # Reset counter

            # Check for regression
            if consensus < previous_consensus - self.config.max_regression_tolerance:
                warnings.append(
                    f"Iteration {iteration}: Regression detected "
                    f"({previous_consensus} → {consensus}, -{previous_consensus - consensus} points)"
                )

            previous_consensus = consensus

        # ═══════════════════════════════════════════════════════════
        # Return comprehensive result
        # ═══════════════════════════════════════════════════════════

        total_time = time.time() - start_time

        # Add final warnings if target not reached
        final_consensus = self.iteration_history[-1]['consensus_score'] if self.iteration_history else 0
        if final_consensus < target_consensus:
            warnings.append(
                f"Target consensus {target_consensus} not reached after "
                f"{len(self.iteration_history)} iteration(s) (best: {self.best_consensus})"
            )

        return self._format_result(
            target_consensus,
            total_time,
            file_path,
            total_revisions,
            warnings
        )

    def _track_iteration(self, iteration_data: Dict) -> None:
        """Record iteration in history.

        Args:
            iteration_data: Iteration metadata dict
        """
        self.iteration_history.append(iteration_data)

    def _update_best_result(self, current_result: Dict, consensus: int, iteration: int) -> bool:
        """Update best result if current is better.

        Args:
            current_result: Current debate result
            consensus: Current consensus score
            iteration: Current iteration number

        Returns:
            True if this is the new best result
        """
        if consensus > self.best_consensus:
            self.best_result = current_result
            self.best_consensus = consensus
            self.best_iteration = iteration

            # Update is_best flags in history
            for iter_data in self.iteration_history:
                iter_data['is_best'] = False
            self.iteration_history[-1]['is_best'] = True  # Mark current as best

            return True

        return False

    def _check_stopping_criteria(
        self,
        iteration: int,
        consensus: int,
        target_consensus: int,
        max_iterations: int
    ) -> Tuple[bool, str]:
        """Determine if iteration should stop.

        Args:
            iteration: Current iteration number
            consensus: Current consensus score
            target_consensus: Target consensus score
            max_iterations: Maximum iterations allowed

        Returns:
            (should_stop, stop_reason)
        """
        # Target reached
        if consensus >= target_consensus:
            return True, ""

        # Max iterations reached
        if iteration > max_iterations:
            return True, f"Max iterations ({max_iterations}) reached"

        # Continue iterating
        return False, ""

    def _save_debate_for_delta(self, file_path: str, debate_result: Dict) -> None:
        """Save debate result for delta mode in next iteration.

        Args:
            file_path: Path to plan file
            debate_result: Debate result to save
        """
        try:
            # Generate debate ID based on file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
            debate_id = f"{Path(file_path).stem}_{content_hash}"

            # Save debate result via delta_debate
            self.delta_debate.save_debate_result(
                file_path=file_path,
                debate_result=debate_result,
                content=content,
                debate_id=debate_id
            )

            self.previous_debate_id = debate_id

        except Exception:
            # If save fails, just continue without delta mode
            pass

    def _calculate_plan_hash(self, file_path: str) -> str:
        """Calculate hash of plan file content.

        Args:
            file_path: Path to plan file

        Returns:
            MD5 hash (first 8 chars)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
        except Exception:
            return "unknown"

    def _format_result(
        self,
        target_consensus: int,
        total_time: float,
        file_path: str,
        total_revisions: int,
        warnings: List[str]
    ) -> Dict:
        """Format final result dictionary.

        Args:
            target_consensus: Target consensus score
            total_time: Total elapsed time
            file_path: Path to plan file
            total_revisions: Number of revisions made
            warnings: List of warning messages

        Returns:
            Complete result dictionary
        """
        final_consensus = self.iteration_history[-1]['consensus_score'] if self.iteration_history else 0
        target_reached = final_consensus >= target_consensus

        return {
            # Best result
            'best_result': self.best_result,
            'best_consensus': self.best_consensus,
            'best_iteration': self.best_iteration,

            # Final state
            'final_consensus': final_consensus,
            'total_iterations': len(self.iteration_history),

            # Iteration history
            'iterations': self.iteration_history,

            # Meta
            'target_consensus': target_consensus,
            'target_reached': target_reached,
            'total_time': total_time,

            # Warnings
            'warnings': warnings,

            # File tracking
            'plan_file_path': file_path,
            'final_plan_hash': self._calculate_plan_hash(file_path),
            'total_revisions': total_revisions
        }


# Convenience function for synchronous usage
def run_iterative_debate_sync(
    topic: str,
    file_path: str,
    focus_areas: Optional[List[str]] = None,
    target_consensus: int = 90,
    max_iterations: int = 5
) -> Dict:
    """Run iterative debate synchronously (convenience wrapper).

    Args:
        topic: Debate topic
        file_path: Path to plan file
        focus_areas: Optional focus areas
        target_consensus: Target consensus score (default: 90)
        max_iterations: Max iterations (default: 5)

    Returns:
        Complete iterative debate result dict
    """
    from .integrated_debate_engine import IntegratedDebateEngine
    from .plan_reviser import PlanReviser
    from .delta_debate import DeltaDebate
    from .codex_cli_invoker import CodexCLIInvoker
    from ..config import DebateConfig

    config = DebateConfig(target_consensus=target_consensus, max_rounds=max_iterations)

    engine = IterativeDebateEngine(
        integrated_engine=IntegratedDebateEngine(),
        plan_reviser=PlanReviser(CodexCLIInvoker()),
        delta_debate=DeltaDebate(),
        config=config
    )

    return asyncio.run(engine.run_iterative_debate(
        topic, file_path, focus_areas, target_consensus, max_iterations
    ))
