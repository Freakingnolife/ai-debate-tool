"""
Smart Recommender - Intelligent pre-debate analysis and recommendations.

Integrates all Phase 3 components to provide:
1. Pre-debate intelligence analysis
2. Auto-suggested focus areas
3. Risk predictions with confidence
4. Learned recommendation adjustments
5. Proactive warnings

This is the main entry point for Phase 3 intelligence features.
"""

from pathlib import Path
from typing import Dict, List, Optional


class SmartRecommender:
    """Intelligent recommender combining all Phase 3 components."""

    def __init__(
        self,
        history_manager,
        pattern_detector,
        risk_predictor,
        decision_learner
    ):
        """
        Initialize smart recommender.

        Args:
            history_manager: DebateHistoryManager instance
            pattern_detector: PatternDetector instance
            risk_predictor: RiskPredictor instance
            decision_learner: DecisionLearner instance
        """
        self.history = history_manager
        self.pattern_detector = pattern_detector
        self.risk_predictor = risk_predictor
        self.decision_learner = decision_learner

    def analyze_pre_debate(
        self,
        request: str,
        file_path: Optional[str] = None,
        focus_areas: Optional[List[str]] = None
    ) -> Dict:
        """
        Perform complete pre-debate intelligence analysis.

        Args:
            request: User's debate request
            file_path: Optional file path
            focus_areas: Optional user-specified focus areas

        Returns:
            {
                'should_proceed': bool,
                'confidence': float,
                'risk_prediction': dict,
                'pattern_analysis': dict,
                'suggested_focus_areas': list[str],
                'expected_consensus': int,
                'estimated_time': float,
                'warnings': list[str],
                'learning_adjustments': dict
            }
        """
        # Step 1: Risk prediction
        risk_prediction = self.risk_predictor.predict_risks(
            request,
            file_path,
            focus_areas
        )

        # Step 2: Pattern analysis
        relevant_patterns = self.pattern_detector.get_patterns_for_request(
            request,
            file_path,
            top_k=5
        )

        # Step 3: Auto-suggestions
        auto_suggestions = self.risk_predictor.get_auto_suggestions(request, file_path)

        # Step 4: Merge focus areas (user + suggested)
        merged_focus_areas = self._merge_focus_areas(
            focus_areas,
            risk_prediction['suggested_focus_areas']
        )

        # Step 5: Learning adjustments (prepare for post-debate)
        learning_prep = {
            'patterns_to_detect': [p['name'] for p in relevant_patterns],
            'baseline_consensus': auto_suggestions['expected_consensus']
        }

        # Step 6: Overall assessment
        overall_confidence = self._calculate_overall_confidence(
            risk_prediction,
            relevant_patterns
        )

        should_proceed = risk_prediction['should_proceed'] and len(auto_suggestions['warnings']) < 2

        return {
            'should_proceed': should_proceed,
            'confidence': overall_confidence,
            'risk_prediction': risk_prediction,
            'pattern_analysis': {
                'relevant_patterns': relevant_patterns,
                'pattern_count': len(relevant_patterns)
            },
            'suggested_focus_areas': merged_focus_areas,
            'expected_consensus': auto_suggestions['expected_consensus'],
            'estimated_time': auto_suggestions['estimated_time'],
            'warnings': auto_suggestions['warnings'],
            'learning_prep': learning_prep
        }

    def enhance_debate_result(
        self,
        debate_result: Dict,
        pre_debate_analysis: Dict
    ) -> Dict:
        """
        Enhance debate result with learning-based adjustments.

        Args:
            debate_result: Original debate result
            pre_debate_analysis: Result from analyze_pre_debate()

        Returns:
            Enhanced debate result with adjustments
        """
        # Get learning adjustments
        learning_adj = self.decision_learner.get_recommendation_adjustment(
            consensus_score=debate_result.get('consensus_score', 70),
            patterns_detected=pre_debate_analysis['learning_prep']['patterns_to_detect'],
            focus_areas=pre_debate_analysis['suggested_focus_areas'],
            score_difference=debate_result.get('score_difference', 0)
        )

        # Enhance result
        enhanced = debate_result.copy()
        enhanced['learning_adjustments'] = learning_adj

        # Adjust recommendation if learning suggests
        if learning_adj['severity_change'] > 0:
            original_rec = debate_result.get('recommendation', '')
            enhanced['original_recommendation'] = original_rec
            enhanced['recommendation'] = self._adjust_recommendation_severity(
                original_rec,
                learning_adj['severity_change']
            )
            enhanced['adjustment_reason'] = learning_adj['adjustment']

        return enhanced

    def get_pre_debate_summary(self, analysis: Dict) -> str:
        """
        Generate human-readable pre-debate summary.

        Args:
            analysis: Result from analyze_pre_debate()

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("SMART PRE-DEBATE ANALYSIS")
        lines.append("=" * 70)
        lines.append("")

        # Overall assessment
        confidence_pct = analysis['confidence'] * 100
        lines.append(f"Overall Confidence: {confidence_pct:.0f}%")
        lines.append(f"Expected Consensus: {analysis['expected_consensus']}/100")
        lines.append(f"Estimated Time: {analysis['estimated_time']:.1f} seconds")
        lines.append("")

        # Pattern matches
        if analysis['pattern_analysis']['pattern_count'] > 0:
            lines.append(f"Pattern Matches: {analysis['pattern_analysis']['pattern_count']} found")
            for i, pattern in enumerate(analysis['pattern_analysis']['relevant_patterns'][:3], 1):
                lines.append(f"  {i}. {pattern['name']} " +
                           f"(relevance: {pattern.get('relevance_score', 0):.0f}%, " +
                           f"frequency: {pattern['frequency']})")
            lines.append("")

        # Predicted risks
        risks = analysis['risk_prediction']['predicted_risks']
        if risks:
            lines.append("Predicted Risks:")
            for i, risk in enumerate(risks[:3], 1):
                prob_pct = risk['probability'] * 100
                lines.append(f"  {i}. [{risk['severity'].upper()}] {risk['name']} " +
                           f"({prob_pct:.0f}% probability)")
            lines.append("")

        # Suggested focus areas
        if analysis['suggested_focus_areas']:
            lines.append("Suggested Focus Areas:")
            for area in analysis['suggested_focus_areas']:
                lines.append(f"  - {area}")
            lines.append("")

        # Warnings
        if analysis['warnings']:
            lines.append("WARNINGS:")
            for warning in analysis['warnings']:
                lines.append(f"  [!] {warning}")
            lines.append("")

        # Recommendation
        if analysis['should_proceed']:
            lines.append("[OK] Proceeding with debate (risks identified, confidence adequate)")
        else:
            lines.append("[CAUTION] Review analysis carefully before proceeding")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    def _merge_focus_areas(
        self,
        user_focus_areas: Optional[List[str]],
        suggested_focus_areas: List[str]
    ) -> List[str]:
        """
        Merge user-specified and auto-suggested focus areas.

        Args:
            user_focus_areas: User's focus areas (priority)
            suggested_focus_areas: Auto-suggested focus areas

        Returns:
            Merged list (user areas first, then suggestions)
        """
        merged = list(user_focus_areas or [])

        # Add suggestions not already in user list
        for area in suggested_focus_areas:
            if area not in merged:
                merged.append(area)

        return merged

    def _calculate_overall_confidence(
        self,
        risk_prediction: Dict,
        patterns: List[Dict]
    ) -> float:
        """
        Calculate overall confidence score.

        Args:
            risk_prediction: Risk prediction dict
            patterns: Relevant patterns

        Returns:
            Overall confidence (0-1)
        """
        # Base confidence from risk prediction
        base_confidence = risk_prediction['confidence']

        # Boost confidence if we have good pattern matches
        pattern_boost = min(len(patterns) * 0.1, 0.3)

        # Reduce confidence if high-severity risks detected
        high_risks = [
            r for r in risk_prediction['predicted_risks']
            if r['severity'] == 'high' and r['probability'] > 0.7
        ]
        risk_penalty = len(high_risks) * 0.15

        overall = base_confidence + pattern_boost - risk_penalty

        return min(max(overall, 0.0), 1.0)

    def _adjust_recommendation_severity(
        self,
        original_recommendation: str,
        severity_change: int
    ) -> str:
        """
        Adjust recommendation severity based on learning.

        Args:
            original_recommendation: Original recommendation
            severity_change: Change amount (-2 to +2)

        Returns:
            Adjusted recommendation
        """
        # Severity levels (low to high)
        severity_levels = [
            '[PROCEED CONFIDENTLY]',
            '[PROCEED]',
            '[CAUTION]',
            '[DISCUSS FIRST]',
            '[RECONSIDER]',
            '[STOP-SHIP]'
        ]

        # Find current level
        current_level = 2  # Default to CAUTION
        for i, level in enumerate(severity_levels):
            if level in original_recommendation:
                current_level = i
                break

        # Adjust level
        new_level = current_level + severity_change
        new_level = max(0, min(new_level, len(severity_levels) - 1))

        # Extract message part
        message = original_recommendation
        for level in severity_levels:
            message = message.replace(level, '').strip()

        # Construct new recommendation
        return f"{severity_levels[new_level]} {message}".strip()

    def get_intelligence_stats(self) -> Dict:
        """
        Get statistics on Phase 3 intelligence system.

        Returns:
            Statistics dictionary
        """
        # Get history stats
        history_stats = self.history.get_statistics()

        # Get pattern stats
        patterns = self.pattern_detector.detect_patterns()

        # Get learning stats
        learning_data = self.decision_learner.learn_from_outcomes()

        return {
            'total_debates': history_stats['total_debates'],
            'avg_consensus': history_stats['avg_consensus'],
            'patterns_detected': len(patterns),
            'learned_rules': len(learning_data.get('rules', [])),
            'outcome_breakdown': history_stats['outcome_breakdown'],
            'intelligence_active': len(patterns) > 0 or len(learning_data.get('rules', [])) > 0
        }

    def get_complete_intelligence_report(self) -> str:
        """
        Get comprehensive intelligence system report.

        Returns:
            Formatted report string
        """
        stats = self.get_intelligence_stats()

        lines = []
        lines.append("=" * 70)
        lines.append("AI DEBATE TOOL - INTELLIGENCE SYSTEM REPORT")
        lines.append("=" * 70)
        lines.append("")

        lines.append("SYSTEM STATUS:")
        lines.append(f"  Intelligence Active: {'YES' if stats['intelligence_active'] else 'NO'}")
        lines.append(f"  Total Debates: {stats['total_debates']}")
        lines.append(f"  Average Consensus: {stats['avg_consensus']}/100")
        lines.append("")

        lines.append("LEARNING CAPABILITIES:")
        lines.append(f"  Patterns Detected: {stats['patterns_detected']}")
        lines.append(f"  Learned Rules: {stats['learned_rules']}")
        lines.append("")

        lines.append("OUTCOME TRACKING:")
        for outcome, count in stats['outcome_breakdown'].items():
            lines.append(f"  {outcome.title()}: {count}")
        lines.append("")

        if stats['intelligence_active']:
            lines.append("INTELLIGENCE FEATURES:")
            lines.append("  [OK] Pre-debate risk prediction")
            lines.append("  [OK] Pattern-based suggestions")
            lines.append("  [OK] Auto focus area detection")
            lines.append("  [OK] Learning from outcomes")
        else:
            lines.append("NOTE: Intelligence features will activate after 3+ debates")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)
