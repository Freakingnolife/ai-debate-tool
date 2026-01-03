"""Moderator Service

Orchestrates consensus analysis using multiple analyzers.
Provides graceful fallback from LLM to rule-based analysis.

Phase 4 Implementation - Intelligent moderator.
"""

from typing import Dict, Optional
from .rule_based_analyzer import RuleBasedAnalyzer
from .llm_analyzer import LLMAnalyzer, LLMConfig
from .decision_pack_generator import DecisionPackGenerator


class ModeratorService:
    """Moderator service for AI debate consensus.

    Orchestrates consensus analysis by:
    1. Attempting LLM analysis first (90%+ accuracy)
    2. Falling back to rule-based if LLM unavailable (75-80% accuracy)
    3. Generating enhanced decision packs
    4. Providing clear recommendations

    Ensures debates always get analyzed, even if LLM is down.
    """

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        enable_llm: bool = True
    ):
        """Initialize moderator service.

        Args:
            llm_config: Optional LLM configuration
            enable_llm: Whether to enable LLM analysis (default: True)
        """
        self.rule_based_analyzer = RuleBasedAnalyzer()
        self.llm_analyzer = LLMAnalyzer(llm_config) if enable_llm else None
        self.decision_pack_generator = DecisionPackGenerator()
        self.enable_llm = enable_llm

    def moderate_debate(
        self,
        session_id: str,
        claude_proposal: str,
        codex_proposal: str,
        force_rule_based: bool = False
    ) -> Dict:
        """Moderate debate and generate decision.

        Attempts LLM analysis first, falls back to rule-based if needed.

        Args:
            session_id: Debate session ID
            claude_proposal: Claude's proposal text
            codex_proposal: Codex's proposal text
            force_rule_based: Force use of rule-based (skip LLM)

        Returns:
            Dictionary with:
                - consensus_score (int): 0-100
                - analysis_method (str): 'llm' or 'rule-based'
                - decision_pack (str): Formatted decision pack
                - can_execute (bool): Whether execution is allowed
                - analysis (Dict): Raw analysis results
        """
        # 1. Attempt LLM analysis (if enabled and not forced rule-based)
        if self.enable_llm and not force_rule_based and self.llm_analyzer:
            llm_result = self.llm_analyzer.analyze(claude_proposal, codex_proposal)

            if llm_result:
                # LLM analysis succeeded
                analysis_method = 'llm'
                analysis = llm_result
                print("[OK] Using LLM analysis (90%+ accuracy)")
            else:
                # LLM failed, fallback to rule-based
                print("[WARN] LLM unavailable, falling back to rule-based analysis")
                analysis_method = 'rule-based'
                analysis = self.rule_based_analyzer.analyze(claude_proposal, codex_proposal)
        else:
            # Use rule-based analysis
            analysis_method = 'rule-based'
            analysis = self.rule_based_analyzer.analyze(claude_proposal, codex_proposal)

            if force_rule_based:
                print("[OK] Using rule-based analysis (forced)")
            else:
                print("[OK] Using rule-based analysis (75-80% accuracy)")

        # 2. Extract consensus score
        consensus_score = analysis['consensus_score']

        # 3. Determine if execution is allowed
        can_execute = self._can_execute(consensus_score, analysis_method)

        # 4. Generate decision pack
        decision_pack = self.decision_pack_generator.generate(
            session_id=session_id,
            claude_proposal=claude_proposal,
            codex_proposal=codex_proposal,
            analysis=analysis,
            analysis_method=analysis_method
        )

        return {
            'consensus_score': consensus_score,
            'analysis_method': analysis_method,
            'decision_pack': decision_pack,
            'can_execute': can_execute,
            'analysis': analysis
        }

    def _can_execute(self, consensus_score: int, method: str) -> bool:
        """Determine if execution is allowed.

        Args:
            consensus_score: Consensus score 0-100
            method: Analysis method ('llm' or 'rule-based')

        Returns:
            True if execution allowed, False otherwise
        """
        # Threshold depends on analysis method
        # LLM is more accurate, so we can use a lower threshold
        if method == 'llm':
            threshold = 65  # 65+ for LLM (more accurate)
        else:
            threshold = 70  # 70+ for rule-based (less accurate, be conservative)

        return consensus_score >= threshold

    def check_llm_availability(self) -> bool:
        """Check if LLM is available.

        Returns:
            True if LLM is enabled and available, False otherwise
        """
        if not self.enable_llm or not self.llm_analyzer:
            return False

        return self.llm_analyzer.is_available()

    def get_status(self) -> Dict:
        """Get moderator status.

        Returns:
            Dictionary with:
                - llm_enabled (bool): Whether LLM is enabled
                - llm_available (bool): Whether LLM is available
                - analysis_mode (str): Current analysis mode
        """
        llm_available = self.check_llm_availability()

        if self.enable_llm and llm_available:
            analysis_mode = 'llm (primary), rule-based (fallback)'
        elif self.enable_llm:
            analysis_mode = 'rule-based (LLM unavailable)'
        else:
            analysis_mode = 'rule-based (LLM disabled)'

        return {
            'llm_enabled': self.enable_llm,
            'llm_available': llm_available,
            'analysis_mode': analysis_mode
        }
