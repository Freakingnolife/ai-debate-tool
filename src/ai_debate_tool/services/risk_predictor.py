"""
Risk Predictor - Predict likely risks based on historical patterns.

Analyzes current request + file context and predicts risks before debate starts:
1. Match request to known patterns
2. Calculate risk probabilities
3. Suggest proactive focus areas
4. Provide confidence scores

Uses zero-cost rule-based matching (no LLM calls).
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple


class RiskPredictor:
    """Predict risks based on historical patterns."""

    def __init__(self, pattern_detector):
        """
        Initialize risk predictor.

        Args:
            pattern_detector: PatternDetector instance
        """
        self.pattern_detector = pattern_detector

    def predict_risks(
        self,
        request: str,
        file_path: Optional[str] = None,
        focus_areas: Optional[List[str]] = None
    ) -> Dict:
        """
        Predict risks for a debate request.

        Args:
            request: User's debate request
            file_path: Optional file path
            focus_areas: Optional focus areas (if already specified)

        Returns:
            {
                'predicted_risks': list[dict],
                'pattern_matches': list[dict],
                'suggested_focus_areas': list[str],
                'confidence': float (0-1),
                'should_proceed': bool
            }
        """
        # Get relevant patterns
        relevant_patterns = self.pattern_detector.get_patterns_for_request(
            request,
            file_path,
            top_k=10
        )

        if not relevant_patterns:
            # No historical data - return generic prediction
            return {
                'predicted_risks': [],
                'pattern_matches': [],
                'suggested_focus_areas': focus_areas or [],
                'confidence': 0.0,
                'should_proceed': True,
                'note': 'No historical patterns found. Proceeding with standard debate.'
            }

        # Extract predicted risks from patterns
        predicted_risks = self._extract_risks_from_patterns(relevant_patterns)

        # Calculate overall confidence
        confidence = self._calculate_confidence(relevant_patterns)

        # Suggest focus areas
        suggested_focus_areas = self._suggest_focus_areas(
            relevant_patterns,
            predicted_risks,
            focus_areas
        )

        # Determine if should proceed
        should_proceed = self._should_proceed(predicted_risks, confidence)

        return {
            'predicted_risks': predicted_risks,
            'pattern_matches': relevant_patterns[:5],  # Top 5 for display
            'suggested_focus_areas': suggested_focus_areas,
            'confidence': round(confidence, 2),
            'should_proceed': should_proceed
        }

    def _extract_risks_from_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """
        Extract predicted risks from matched patterns.

        Args:
            patterns: List of matched patterns

        Returns:
            List of predicted risks with probabilities
        """
        risks = {}

        for pattern in patterns:
            if pattern['type'] == 'risk':
                risk_name = pattern['name']
                probability = self._calculate_risk_probability(pattern)

                if risk_name not in risks or risks[risk_name]['probability'] < probability:
                    risks[risk_name] = {
                        'name': risk_name,
                        'probability': probability,
                        'severity': self._determine_severity(pattern),
                        'evidence': f"Detected in {pattern['frequency']} previous debates " +
                                  f"(avg consensus: {pattern['avg_consensus']}/100)",
                        'pattern': pattern
                    }

        # Sort by probability * severity
        risk_list = list(risks.values())
        risk_list.sort(
            key=lambda r: r['probability'] * {'high': 1.0, 'medium': 0.7, 'low': 0.4}[r['severity']],
            reverse=True
        )

        return risk_list

    def _calculate_risk_probability(self, pattern: Dict) -> float:
        """
        Calculate risk probability based on pattern data.

        Args:
            pattern: Pattern dict

        Returns:
            Probability (0-1)
        """
        # Factors:
        # 1. Frequency (how often this risk occurs)
        # 2. Success rate (lower success = higher risk)
        # 3. Relevance score

        frequency_weight = min(pattern.get('frequency', 0) / 10, 1.0) * 0.4
        success_penalty = (1 - pattern.get('success_rate', 0.5)) * 0.3
        relevance_weight = min(pattern.get('relevance_score', 0) / 100, 1.0) * 0.3

        probability = frequency_weight + success_penalty + relevance_weight

        return min(probability, 1.0)

    def _determine_severity(self, pattern: Dict) -> str:
        """
        Determine risk severity based on consensus impact.

        Args:
            pattern: Pattern dict

        Returns:
            Severity level: 'high', 'medium', or 'low'
        """
        avg_consensus = pattern.get('avg_consensus', 70)

        if avg_consensus < 50:
            return 'high'
        elif avg_consensus < 70:
            return 'medium'
        else:
            return 'low'

    def _calculate_confidence(self, patterns: List[Dict]) -> float:
        """
        Calculate confidence in risk prediction based on pattern quality.

        Args:
            patterns: Matched patterns

        Returns:
            Confidence level (0-1)
        """
        if not patterns:
            return 0.0

        # Factors:
        # 1. Number of patterns matched (more = higher confidence)
        # 2. Pattern frequency (more occurrences = higher confidence)
        # 3. Pattern relevance scores

        pattern_count_score = min(len(patterns) / 5, 1.0) * 0.4

        avg_frequency = sum(p.get('frequency', 0) for p in patterns) / len(patterns)
        frequency_score = min(avg_frequency / 10, 1.0) * 0.3

        avg_relevance = sum(p.get('relevance_score', 0) for p in patterns) / len(patterns)
        relevance_score = min(avg_relevance / 100, 1.0) * 0.3

        confidence = pattern_count_score + frequency_score + relevance_score

        return min(confidence, 1.0)

    def _suggest_focus_areas(
        self,
        patterns: List[Dict],
        risks: List[Dict],
        existing_focus_areas: Optional[List[str]]
    ) -> List[str]:
        """
        Suggest focus areas based on patterns and risks.

        Args:
            patterns: Matched patterns
            risks: Predicted risks
            existing_focus_areas: User-specified focus areas

        Returns:
            List of suggested focus areas
        """
        suggested = set(existing_focus_areas or [])

        # Add focus areas from patterns
        for pattern in patterns[:5]:
            if pattern['type'] == 'focus_pattern':
                suggested.update(pattern.get('focus_areas', []))

        # Add focus areas based on risks
        risk_to_focus = {
            'circular_imports': 'architecture',
            'transaction_boundaries': 'database',
            'missing_migration': 'database',
            'tight_coupling': 'architecture',
            'unclear_interfaces': 'architecture',
            'insufficient_testing': 'testing',
            'performance_regression': 'performance',
            'backward_compatibility': 'architecture'
        }

        for risk in risks[:3]:  # Top 3 risks
            risk_name = risk['name']
            if risk_name in risk_to_focus:
                suggested.add(risk_to_focus[risk_name])

        return sorted(list(suggested))

    def _should_proceed(self, risks: List[Dict], confidence: float) -> bool:
        """
        Determine if debate should proceed or warn user first.

        Args:
            risks: Predicted risks
            confidence: Prediction confidence

        Returns:
            True if should proceed, False if should warn user first
        """
        # Check for high-severity, high-probability risks
        critical_risks = [
            r for r in risks
            if r['severity'] == 'high' and r['probability'] > 0.7
        ]

        if critical_risks and confidence > 0.6:
            # High-confidence critical risk prediction - warn user
            return False

        return True

    def get_prediction_summary(self, prediction: Dict) -> str:
        """
        Generate human-readable summary of risk prediction.

        Args:
            prediction: Result from predict_risks()

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("RISK PREDICTION ANALYSIS")
        lines.append("=" * 60)
        lines.append("")

        # Confidence
        confidence_pct = prediction['confidence'] * 100
        lines.append(f"Prediction Confidence: {confidence_pct:.0f}%")
        lines.append("")

        # Pattern matches
        if prediction['pattern_matches']:
            lines.append("Pattern Matches:")
            for i, pattern in enumerate(prediction['pattern_matches'][:3], 1):
                lines.append(f"  {i}. {pattern['name']} " +
                           f"(frequency: {pattern['frequency']}, " +
                           f"relevance: {pattern.get('relevance_score', 0):.0f}%)")
            lines.append("")

        # Predicted risks
        if prediction['predicted_risks']:
            lines.append("Predicted Risks:")
            for i, risk in enumerate(prediction['predicted_risks'], 1):
                prob_pct = risk['probability'] * 100
                lines.append(f"  {i}. [{risk['severity'].upper()}] {risk['name']} " +
                           f"(probability: {prob_pct:.0f}%)")
                lines.append(f"     {risk['evidence']}")
            lines.append("")

        # Suggested focus areas
        if prediction['suggested_focus_areas']:
            lines.append("Suggested Focus Areas:")
            for area in prediction['suggested_focus_areas']:
                lines.append(f"  - {area}")
            lines.append("")

        # Recommendation
        if not prediction['should_proceed']:
            lines.append("[WARNING] High-confidence critical risks detected!")
            lines.append("Review risks carefully before proceeding with debate.")
        else:
            lines.append("[OK] Proceeding with debate (risks identified, manageable)")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def get_auto_suggestions(
        self,
        request: str,
        file_path: Optional[str] = None
    ) -> Dict:
        """
        Get automatic suggestions for debate setup.

        Args:
            request: User's debate request
            file_path: Optional file path

        Returns:
            {
                'focus_areas': list[str],
                'expected_consensus': int,
                'estimated_time': float,
                'warnings': list[str]
            }
        """
        prediction = self.predict_risks(request, file_path)

        # Estimate consensus based on patterns
        expected_consensus = 70  # Default

        if prediction['pattern_matches']:
            avg_consensus = sum(
                p.get('avg_consensus', 70) for p in prediction['pattern_matches'][:3]
            ) / min(len(prediction['pattern_matches']), 3)
            expected_consensus = int(avg_consensus)

        # Estimate time (base: 20 seconds)
        estimated_time = 20.0

        # Add time for complex patterns
        if len(prediction['suggested_focus_areas']) > 3:
            estimated_time += 5.0

        # Generate warnings
        warnings = []

        for risk in prediction['predicted_risks']:
            if risk['severity'] == 'high' and risk['probability'] > 0.7:
                warnings.append(f"High risk: {risk['name']} ({risk['probability']*100:.0f}% probability)")

        if not prediction['should_proceed']:
            warnings.insert(0, "CRITICAL: Multiple high-severity risks detected")

        return {
            'focus_areas': prediction['suggested_focus_areas'],
            'expected_consensus': expected_consensus,
            'estimated_time': round(estimated_time, 1),
            'warnings': warnings,
            'confidence': prediction['confidence']
        }
