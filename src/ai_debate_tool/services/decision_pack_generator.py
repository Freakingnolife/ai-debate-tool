"""Decision Pack Generator

Generates enhanced decision packs from consensus analysis.
Provides clear, actionable recommendations for users.

Phase 4 Implementation - Enhanced decision reporting.
"""

from typing import Dict, List, Optional
from datetime import datetime


class DecisionPackGenerator:
    """Generates enhanced decision packs.

    Creates clear, formatted decision packs that:
    1. Show consensus score prominently
    2. List key agreements
    3. Highlight conflicts
    4. Provide clear recommendation
    5. Include next steps
    6. Show metadata

    Makes it easy for users to understand consensus.
    """

    # Consensus thresholds
    THRESHOLD_HIGH = 70  # >= 70 = high consensus
    THRESHOLD_MEDIUM = 40  # 40-69 = medium consensus
    # < 40 = low consensus

    def generate(
        self,
        session_id: str,
        claude_proposal: str,
        codex_proposal: str,
        analysis: Dict,
        analysis_method: str
    ) -> str:
        """Generate decision pack from analysis.

        Args:
            session_id: Debate session ID
            claude_proposal: Claude's proposal text
            codex_proposal: Codex's proposal text
            analysis: Analysis results (from RuleBasedAnalyzer or LLMAnalyzer)
            analysis_method: 'rule-based' or 'llm'

        Returns:
            Formatted decision pack as string
        """
        consensus_score = analysis['consensus_score']
        consensus_level = self._get_consensus_level(consensus_score)

        # Build sections
        header = self._build_header(session_id, consensus_score, consensus_level, analysis_method)
        summary = self._build_summary(analysis, analysis_method, consensus_level)
        agreements = self._build_agreements_section(analysis, analysis_method)
        conflicts = self._build_conflicts_section(analysis, analysis_method)
        recommendation = self._build_recommendation(consensus_level, analysis, analysis_method)
        proposals = self._build_proposals_section(claude_proposal, codex_proposal)
        metadata = self._build_metadata(analysis, analysis_method)

        # Assemble decision pack
        decision_pack = f"""{header}

{summary}

{agreements}

{conflicts}

{recommendation}

{proposals}

{metadata}
"""
        return decision_pack

    def _get_consensus_level(self, score: int) -> str:
        """Get consensus level from score.

        Args:
            score: Consensus score 0-100

        Returns:
            'high', 'medium', or 'low'
        """
        if score >= self.THRESHOLD_HIGH:
            return 'high'
        elif score >= self.THRESHOLD_MEDIUM:
            return 'medium'
        else:
            return 'low'

    def _build_header(
        self,
        session_id: str,
        score: int,
        level: str,
        method: str
    ) -> str:
        """Build decision pack header."""
        level_emoji = {
            'high': '[OK]',
            'medium': '[WARN]',
            'low': '[FAIL]'
        }

        return f"""{'=' * 70}
AI DEBATE DECISION PACK
{'=' * 70}

Session ID: {session_id}
Analysis Method: {method.upper()}
Consensus Score: {score}/100 {level_emoji[level]} ({level.upper()})
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

    def _build_summary(self, analysis: Dict, method: str, level: str) -> str:
        """Build summary section."""
        if method == 'llm':
            reasoning = analysis.get('reasoning', 'No reasoning provided')
            return f"""
{'=' * 70}
SUMMARY
{'=' * 70}

Consensus Level: {level.upper()}

Analysis: {reasoning}
"""
        else:  # rule-based
            term_overlap = analysis.get('key_term_overlap', 0)
            structure_sim = analysis.get('structure_similarity', 0)

            return f"""
{'=' * 70}
SUMMARY
{'=' * 70}

Consensus Level: {level.upper()}

Key Metrics:
- Term Overlap: {term_overlap:.1%}
- Structure Similarity: {structure_sim:.1%}
- Conflicts Found: {len(analysis.get('conflicts_found', []))}
"""

    def _build_agreements_section(self, analysis: Dict, method: str) -> str:
        """Build agreements section."""
        if method == 'llm':
            agreements = analysis.get('key_agreements', [])
        else:  # rule-based
            # Extract common terms as agreements
            claude_terms = set(analysis.get('claude_key_terms', []))
            codex_terms = set(analysis.get('codex_key_terms', []))
            common_terms = claude_terms & codex_terms

            if common_terms:
                agreements = [f"Both proposals mention: {', '.join(sorted(list(common_terms)[:5]))}"]
            else:
                agreements = []

        if not agreements:
            return f"""
{'=' * 70}
KEY AGREEMENTS
{'=' * 70}

[WARN] No clear agreements identified.
"""

        agreements_text = '\n'.join(f"  {i+1}. {agreement}" for i, agreement in enumerate(agreements))

        return f"""
{'=' * 70}
KEY AGREEMENTS
{'=' * 70}

{agreements_text}
"""

    def _build_conflicts_section(self, analysis: Dict, method: str) -> str:
        """Build conflicts section."""
        if method == 'llm':
            conflicts = analysis.get('conflicts', [])
        else:  # rule-based
            conflicts = analysis.get('conflicts_found', [])

        if not conflicts:
            return f"""
{'=' * 70}
CONFLICTS & CONCERNS
{'=' * 70}

[OK] No conflicts detected.
"""

        conflicts_text = '\n'.join(f"  {i+1}. {conflict}" for i, conflict in enumerate(conflicts))

        return f"""
{'=' * 70}
CONFLICTS & CONCERNS
{'=' * 70}

[WARN] {len(conflicts)} conflict(s) found:

{conflicts_text}
"""

    def _build_recommendation(
        self,
        consensus_level: str,
        analysis: Dict,
        method: str
    ) -> str:
        """Build recommendation section."""
        if method == 'llm':
            llm_recommendation = analysis.get('recommendation', 'review')

            if llm_recommendation == 'execute':
                action = '[OK] PROCEED WITH EXECUTION'
                explanation = 'Strong consensus detected. Safe to proceed with implementation.'
            elif llm_recommendation == 'review':
                action = '[WARN] REVIEW REQUIRED'
                explanation = 'Moderate consensus. Review conflicts before proceeding.'
            else:  # reject
                action = '[FAIL] DO NOT EXECUTE'
                explanation = 'Low consensus. Significant disagreement detected.'

        else:  # rule-based
            if consensus_level == 'high':
                action = '[OK] PROCEED WITH EXECUTION'
                explanation = 'High consensus detected. Safe to proceed with implementation.'
            elif consensus_level == 'medium':
                action = '[WARN] REVIEW REQUIRED'
                explanation = 'Medium consensus. Review analysis before proceeding.'
            else:  # low
                action = '[FAIL] DO NOT EXECUTE'
                explanation = 'Low consensus. Further discussion recommended.'

        return f"""
{'=' * 70}
RECOMMENDATION
{'=' * 70}

{action}

{explanation}

Next Steps:
"""

    def _build_proposals_section(self, claude: str, codex: str) -> str:
        """Build proposals section."""
        return f"""
{'=' * 70}
FULL PROPOSALS
{'=' * 70}

CLAUDE'S PROPOSAL:
{'-' * 70}
{claude.strip()}

{'=' * 70}

CODEX'S PROPOSAL:
{'-' * 70}
{codex.strip()}
"""

    def _build_metadata(self, analysis: Dict, method: str) -> str:
        """Build metadata section."""
        if method == 'llm':
            metadata_items = [
                f"Semantic Similarity: {analysis.get('semantic_similarity', 0):.1%}",
                f"Approach Agreement: {analysis.get('approach_agreement', 0):.1%}"
            ]
        else:  # rule-based
            metadata_items = [
                f"Key Term Overlap: {analysis.get('key_term_overlap', 0):.1%}",
                f"Structure Similarity: {analysis.get('structure_similarity', 0):.1%}",
                f"Length Ratio: {analysis.get('length_ratio', 1.0):.2f}",
                f"Claude Terms: {len(analysis.get('claude_key_terms', []))}",
                f"Codex Terms: {len(analysis.get('codex_key_terms', []))}"
            ]

        metadata_text = '\n'.join(f"  - {item}" for item in metadata_items)

        return f"""
{'=' * 70}
ANALYSIS METADATA
{'=' * 70}

{metadata_text}

{'=' * 70}
END OF DECISION PACK
{'=' * 70}
"""

    def generate_simple(self, consensus_score: int, can_execute: bool) -> str:
        """Generate simple decision pack (backward compatibility).

        Args:
            consensus_score: Consensus score 0-100
            can_execute: Whether execution is allowed

        Returns:
            Simple formatted decision pack
        """
        level = self._get_consensus_level(consensus_score)
        status = '[OK]' if can_execute else '[FAIL]'

        return f"""
{'=' * 70}
DECISION PACK (SIMPLE)
{'=' * 70}

Consensus Score: {consensus_score}/100 {status}
Can Execute: {'Yes' if can_execute else 'No'}
Level: {level.upper()}

{'=' * 70}
"""
