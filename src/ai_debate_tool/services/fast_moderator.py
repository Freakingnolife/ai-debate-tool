"""
Fast Moderator - Rule-based consensus analysis for debates.

Replaces slow LLM-based moderation with fast rule-based analysis:
- Consensus score calculation (average)
- Agreement level determination (score difference)
- Disagreement extraction (keyword matching)
- Action recommendations

Performance: 5 seconds (vs 20 seconds LLM-based)
"""

from typing import Dict, List, Optional


class FastModerator:
    """Fast rule-based moderator for debate consensus analysis."""

    # Agreement thresholds based on score difference
    STRONG_AGREEMENT_THRESHOLD = 10
    MODERATE_AGREEMENT_THRESHOLD = 20

    # Consensus score thresholds for recommendations
    PROCEED_CONFIDENTLY = 85
    PROCEED_WITH_CAUTION = 70
    DISCUSS_FIRST = 50

    # Disagreement keywords for extraction
    DISAGREEMENT_KEYWORDS = [
        'disagree', 'disagrees', 'disagreement',
        'concern', 'concerns', 'concerned',
        'risk', 'risks', 'risky',
        'issue', 'issues', 'problem', 'problems',
        'wrong', 'incorrect', 'mistake',
        'missing', 'lacks', 'incomplete',
        'alternative', 'instead', 'better approach'
    ]

    @classmethod
    def analyze(
        cls,
        claude_result: Dict,
        codex_result: Dict,
        pattern_issues: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Analyze debate results and generate consensus.

        Args:
            claude_result: Claude's analysis with 'score' (0-100)
            codex_result: Codex's analysis with 'score' (0-100)
            pattern_issues: Optional list of known pattern issues

        Returns:
            {
                'consensus_score': int (0-100),
                'interpretation': str (agreement level),
                'recommendation': str (action to take),
                'score_difference': int,
                'disagreements': list[dict] (extracted from responses),
                'agreements': list[str] (common points),
                'analysis_time': float (seconds)
            }
        """
        import time
        start = time.time()

        # Extract scores
        claude_score = claude_result.get('score', 70)
        codex_score = codex_result.get('score', 70)

        # Calculate consensus
        consensus_score = (claude_score + codex_score) // 2
        score_difference = abs(claude_score - codex_score)

        # Determine agreement level
        interpretation = cls._determine_agreement_level(score_difference)

        # Generate recommendation
        recommendation = cls._generate_recommendation(
            consensus_score,
            score_difference,
            pattern_issues
        )

        # Extract disagreements from responses
        disagreements = cls._extract_disagreements(
            claude_result.get('response', ''),
            codex_result.get('response', '')
        )

        # Extract agreements (common positive statements)
        agreements = cls._extract_agreements(
            claude_result.get('response', ''),
            codex_result.get('response', '')
        )

        analysis_time = time.time() - start

        return {
            'consensus_score': consensus_score,
            'interpretation': interpretation,
            'recommendation': recommendation,
            'score_difference': score_difference,
            'disagreements': disagreements,
            'agreements': agreements,
            'analysis_time': analysis_time
        }

    @classmethod
    def _determine_agreement_level(cls, score_difference: int) -> str:
        """
        Determine agreement level from score difference.

        Args:
            score_difference: Absolute difference between scores

        Returns:
            Agreement level string
        """
        if score_difference <= cls.STRONG_AGREEMENT_THRESHOLD:
            return "Strong Agreement"
        elif score_difference <= cls.MODERATE_AGREEMENT_THRESHOLD:
            return "Moderate Agreement"
        else:
            return "Significant Disagreements"

    @classmethod
    def _generate_recommendation(
        cls,
        consensus_score: int,
        score_difference: int,
        pattern_issues: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate action recommendation based on consensus.

        Args:
            consensus_score: Average score (0-100)
            score_difference: Score difference
            pattern_issues: Optional known issues

        Returns:
            Recommendation string with emoji
        """
        # Check for stop-ship issues first
        if pattern_issues:
            stop_ship = [i for i in pattern_issues if i.get('priority_score', 0) >= 85]
            if stop_ship:
                return "[STOP-SHIP] Critical issues found"

        # Consensus-based recommendations
        if consensus_score >= cls.PROCEED_CONFIDENTLY:
            if score_difference <= cls.STRONG_AGREEMENT_THRESHOLD:
                return "[PROCEED CONFIDENTLY] Strong consensus"
            else:
                return "[PROCEED] Good consensus with minor concerns"

        elif consensus_score >= cls.PROCEED_WITH_CAUTION:
            return "[CAUTION] Address key concerns first"

        elif consensus_score >= cls.DISCUSS_FIRST:
            return "[DISCUSS FIRST] Resolve disagreements before proceeding"

        else:
            return "[RECONSIDER] Fundamental disagreements require rethinking"

    @classmethod
    def _extract_disagreements(cls, claude_text: str, codex_text: str) -> List[Dict]:
        """
        Extract disagreement points from responses.

        Uses keyword matching to find sentences expressing concerns.

        Args:
            claude_text: Claude's response text
            codex_text: Codex's response text

        Returns:
            List of disagreement dicts with 'source' and 'text'
        """
        disagreements = []

        # Split into sentences (simple approach)
        claude_sentences = cls._split_sentences(claude_text)
        codex_sentences = cls._split_sentences(codex_text)

        # Find disagreement sentences from Claude
        for sentence in claude_sentences:
            if cls._contains_disagreement_keyword(sentence):
                disagreements.append({
                    'source': 'Claude',
                    'text': sentence.strip()
                })

        # Find disagreement sentences from Codex
        for sentence in codex_sentences:
            if cls._contains_disagreement_keyword(sentence):
                disagreements.append({
                    'source': 'Codex',
                    'text': sentence.strip()
                })

        # Limit to top 5 most relevant
        return disagreements[:5]

    @classmethod
    def _extract_agreements(cls, claude_text: str, codex_text: str) -> List[str]:
        """
        Extract agreement points from responses.

        Looks for common positive statements in both responses.

        Args:
            claude_text: Claude's response text
            codex_text: Codex's response text

        Returns:
            List of agreement statements
        """
        agreements = []

        # Agreement keywords
        agreement_keywords = [
            'agree', 'agrees', 'correct', 'good', 'excellent',
            'well-designed', 'appropriate', 'smart', 'effective'
        ]

        claude_sentences = cls._split_sentences(claude_text)
        codex_sentences = cls._split_sentences(codex_text)

        # Find sentences with agreement keywords
        for sentence in claude_sentences:
            sentence_lower = sentence.lower()
            if any(kw in sentence_lower for kw in agreement_keywords):
                agreements.append(sentence.strip())

        for sentence in codex_sentences:
            sentence_lower = sentence.lower()
            if any(kw in sentence_lower for kw in agreement_keywords):
                # Only add if not duplicate
                if sentence.strip() not in agreements:
                    agreements.append(sentence.strip())

        # Limit to top 5
        return agreements[:5]

    @classmethod
    def _split_sentences(cls, text: str) -> List[str]:
        """
        Split text into sentences (simple approach).

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Simple split on period, question mark, exclamation
        import re
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    @classmethod
    def _contains_disagreement_keyword(cls, sentence: str) -> bool:
        """
        Check if sentence contains disagreement keyword.

        Args:
            sentence: Sentence to check

        Returns:
            True if contains disagreement keyword
        """
        sentence_lower = sentence.lower()
        return any(kw in sentence_lower for kw in cls.DISAGREEMENT_KEYWORDS)

    @classmethod
    def generate_summary(cls, analysis_result: Dict) -> str:
        """
        Generate human-readable summary of consensus analysis.

        Args:
            analysis_result: Result from analyze()

        Returns:
            Formatted summary string
        """
        summary_lines = []

        summary_lines.append("=" * 60)
        summary_lines.append("FAST MODERATOR CONSENSUS ANALYSIS")
        summary_lines.append("=" * 60)
        summary_lines.append("")

        # Consensus
        summary_lines.append(f"Consensus Score: {analysis_result['consensus_score']}/100")
        summary_lines.append(f"Agreement Level: {analysis_result['interpretation']}")
        summary_lines.append(f"Score Difference: {analysis_result['score_difference']} points")
        summary_lines.append("")

        # Recommendation
        summary_lines.append(f"Recommendation: {analysis_result['recommendation']}")
        summary_lines.append("")

        # Disagreements
        if analysis_result['disagreements']:
            summary_lines.append("Key Disagreements:")
            for i, disagreement in enumerate(analysis_result['disagreements'], 1):
                summary_lines.append(f"  {i}. [{disagreement['source']}] {disagreement['text'][:80]}...")
            summary_lines.append("")

        # Agreements
        if analysis_result['agreements']:
            summary_lines.append("Points of Agreement:")
            for i, agreement in enumerate(analysis_result['agreements'], 1):
                summary_lines.append(f"  {i}. {agreement[:80]}...")
            summary_lines.append("")

        # Performance
        summary_lines.append(f"Analysis Time: {analysis_result['analysis_time']:.2f} seconds")
        summary_lines.append("")
        summary_lines.append("=" * 60)

        return "\n".join(summary_lines)
