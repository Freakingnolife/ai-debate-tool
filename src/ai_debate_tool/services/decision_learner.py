"""
Decision Learner - Learn from past debate outcomes to improve recommendations.

Tracks debate outcomes and adjusts future recommendations:
1. Analyze outcome success rates by pattern
2. Identify which consensus scores predict success
3. Adjust recommendation thresholds dynamically
4. Build decision rules from history

Uses simple statistical learning (no ML models).
"""

import ast
import json
import logging
import operator
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# v0.9.6: Safe condition evaluation using AST whitelist (Issue #3 - Code Review Findings)
# Replaces dangerous eval() with secure AST-based parsing

SAFE_COMPARE_OPS = {
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}

SAFE_BOOL_OPS = {
    ast.And: all,
    ast.Or: any,
}


def safe_evaluate_condition(condition: str, consensus: int) -> bool:
    """
    Safely evaluate consensus threshold conditions using AST whitelist.

    Supports:
    - Simple: "consensus >= 70"
    - Compound: "70 <= consensus < 85"
    - Boolean: "consensus >= 70 and consensus < 85"

    Rejects: floats, function calls, imports, unknown variables

    Args:
        condition: String condition to evaluate
        consensus: Integer consensus score to check against

    Returns:
        True if condition is met, False otherwise (including on errors)
    """
    try:
        tree = ast.parse(condition, mode='eval')
        return _eval_node(tree.body, consensus)
    except (SyntaxError, ValueError, KeyError, TypeError) as e:
        logger.debug(f"Safe evaluation failed for condition '{condition}': {e}")
        return False


def _eval_node(node, consensus: int) -> bool:
    """Recursively evaluate AST nodes with strict whitelist."""
    if isinstance(node, ast.Compare):
        # Handle comparison chains like "70 <= consensus < 85"
        left = _get_value(node.left, consensus)
        for op, comparator in zip(node.ops, node.comparators):
            if type(op) not in SAFE_COMPARE_OPS:
                raise ValueError(f"Unsupported operator: {type(op).__name__}")
            right = _get_value(comparator, consensus)
            if not SAFE_COMPARE_OPS[type(op)](left, right):
                return False
            left = right
        return True
    elif isinstance(node, ast.BoolOp):
        # Handle "and" / "or"
        if type(node.op) not in SAFE_BOOL_OPS:
            raise ValueError(f"Unsupported boolean: {type(node.op).__name__}")
        results = [_eval_node(v, consensus) for v in node.values]
        return SAFE_BOOL_OPS[type(node.op)](results)
    else:
        raise ValueError(f"Unsupported node: {type(node).__name__}")


def _get_value(node, consensus: int):
    """Extract value from AST node - integers only."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int):
            return node.value
        raise ValueError("Only integer constants allowed")
    elif isinstance(node, ast.Num):  # Python 3.7 compatibility
        if isinstance(node.n, int):
            return node.n
        raise ValueError("Only integer constants allowed")
    elif isinstance(node, ast.Name):
        if node.id == 'consensus':
            return consensus
        raise ValueError(f"Unknown variable: {node.id}")
    else:
        raise ValueError(f"Unsupported value: {type(node).__name__}")


class DecisionLearner:
    """Learn from debate outcomes to improve future decisions."""

    def __init__(self, history_manager, pattern_detector):
        """
        Initialize decision learner.

        Args:
            history_manager: DebateHistoryManager instance
            pattern_detector: PatternDetector instance
        """
        self.history = history_manager
        self.pattern_detector = pattern_detector
        self.rules_file = history_manager.patterns_dir / 'learned_rules.json'

    def learn_from_outcomes(self, force_refresh: bool = False) -> Dict:
        """
        Analyze outcomes and generate learned rules.

        Args:
            force_refresh: Force re-learning (ignore cache)

        Returns:
            Learned rules dictionary
        """
        # Load cached rules
        if not force_refresh and self.rules_file.exists():
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # Get all debates with known outcomes
        all_debates = self.history.query_debates(limit=1000)
        outcome_debates = [d for d in all_debates if d.get('outcome') != 'pending']

        if len(outcome_debates) < 3:
            # Not enough outcome data
            return {
                'total_debates': len(all_debates),
                'outcome_debates': len(outcome_debates),
                'rules': [],
                'note': 'Insufficient outcome data for learning (need 3+ debates with outcomes)'
            }

        # Learn rules
        rules = []

        # Rule 1: Consensus threshold rules
        consensus_rules = self._learn_consensus_thresholds(outcome_debates)
        rules.extend(consensus_rules)

        # Rule 2: Pattern-specific success rates
        pattern_rules = self._learn_pattern_success_rates(outcome_debates)
        rules.extend(pattern_rules)

        # Rule 3: Focus area combinations
        focus_rules = self._learn_focus_area_rules(outcome_debates)
        rules.extend(focus_rules)

        # Rule 4: Score difference impact
        score_diff_rules = self._learn_score_difference_rules(outcome_debates)
        rules.extend(score_diff_rules)

        # Save rules
        learned_data = {
            'total_debates': len(all_debates),
            'outcome_debates': len(outcome_debates),
            'last_updated': self.history._generate_debate_id(),
            'rules': rules
        }

        with open(self.rules_file, 'w', encoding='utf-8') as f:
            json.dump(learned_data, f, indent=2, ensure_ascii=False)

        return learned_data

    def _learn_consensus_thresholds(self, debates: List[Dict]) -> List[Dict]:
        """
        Learn optimal consensus thresholds for success.

        Args:
            debates: Debates with known outcomes

        Returns:
            List of consensus threshold rules
        """
        rules = []

        # Group by consensus ranges
        ranges = [
            (0, 50, 'very_low'),
            (50, 70, 'low'),
            (70, 85, 'medium'),
            (85, 100, 'high')
        ]

        for min_score, max_score, range_name in ranges:
            range_debates = [
                d for d in debates
                if min_score <= d['consensus_score'] < max_score
            ]

            if len(range_debates) >= 2:
                success_count = len([d for d in range_debates if d['outcome'] == 'succeeded'])
                success_rate = success_count / len(range_debates)

                # Generate rule
                if success_rate < 0.4:
                    recommendation = '[RECONSIDER]'
                    adjustment = 'Increase severity - low success rate observed'
                elif success_rate < 0.7:
                    recommendation = '[DISCUSS FIRST]'
                    adjustment = 'Moderate caution - mixed results observed'
                else:
                    recommendation = '[PROCEED]'
                    adjustment = 'Confidence boost - high success rate observed'

                rules.append({
                    'type': 'consensus_threshold',
                    'condition': f'{min_score} <= consensus < {max_score}',
                    'success_rate': round(success_rate, 2),
                    'sample_size': len(range_debates),
                    'learned_recommendation': recommendation,
                    'adjustment': adjustment,
                    'confidence': min(len(range_debates) / 10, 1.0)  # More data = more confidence
                })

        return rules

    def _learn_pattern_success_rates(self, debates: List[Dict]) -> List[Dict]:
        """
        Learn success rates for specific patterns.

        Args:
            debates: Debates with known outcomes

        Returns:
            List of pattern-specific rules
        """
        rules = []

        # Get all patterns
        all_patterns = self.pattern_detector.detect_patterns()

        for pattern in all_patterns:
            if pattern['type'] != 'risk':
                continue

            # Find debates with this pattern
            pattern_debates = [
                d for d in debates
                if pattern['name'] in [p.get('name', '') for p in d.get('patterns_detected', [])]
            ]

            if len(pattern_debates) >= 2:
                success_count = len([d for d in pattern_debates if d['outcome'] == 'succeeded'])
                success_rate = success_count / len(pattern_debates)

                # Generate pattern-specific rule
                if success_rate < 0.5:
                    severity_adjustment = 'Increase severity'
                else:
                    severity_adjustment = 'Standard severity'

                rules.append({
                    'type': 'pattern_success',
                    'pattern_name': pattern['name'],
                    'success_rate': round(success_rate, 2),
                    'sample_size': len(pattern_debates),
                    'severity_adjustment': severity_adjustment,
                    'confidence': min(len(pattern_debates) / 5, 1.0)
                })

        return rules

    def _learn_focus_area_rules(self, debates: List[Dict]) -> List[Dict]:
        """
        Learn which focus area combinations predict success.

        Args:
            debates: Debates with known outcomes

        Returns:
            List of focus area rules
        """
        rules = []

        # Group by focus area combinations
        focus_groups = defaultdict(list)

        for debate in debates:
            focus_combo = tuple(sorted(debate.get('focus_areas', [])))
            if focus_combo:
                focus_groups[focus_combo].append(debate)

        # Analyze each combination
        for focus_combo, combo_debates in focus_groups.items():
            if len(combo_debates) >= 2:
                success_count = len([d for d in combo_debates if d['outcome'] == 'succeeded'])
                success_rate = success_count / len(combo_debates)

                avg_consensus = sum(d['consensus_score'] for d in combo_debates) / len(combo_debates)

                rules.append({
                    'type': 'focus_combination',
                    'focus_areas': list(focus_combo),
                    'success_rate': round(success_rate, 2),
                    'avg_consensus': round(avg_consensus, 1),
                    'sample_size': len(combo_debates),
                    'recommendation': 'Recommended' if success_rate > 0.6 else 'Caution advised',
                    'confidence': min(len(combo_debates) / 5, 1.0)
                })

        return rules

    def _learn_score_difference_rules(self, debates: List[Dict]) -> List[Dict]:
        """
        Learn how score difference between AIs affects outcomes.

        Args:
            debates: Debates with known outcomes

        Returns:
            List of score difference rules
        """
        rules = []

        # Group by score difference ranges
        ranges = [
            (0, 10, 'minimal'),
            (10, 20, 'moderate'),
            (20, 100, 'significant')
        ]

        for min_diff, max_diff, range_name in ranges:
            range_debates = [
                d for d in debates
                if min_diff <= d.get('score_difference', 0) < max_diff
            ]

            if len(range_debates) >= 2:
                success_count = len([d for d in range_debates if d['outcome'] == 'succeeded'])
                success_rate = success_count / len(range_debates)

                rules.append({
                    'type': 'score_difference',
                    'difference_range': range_name,
                    'success_rate': round(success_rate, 2),
                    'sample_size': len(range_debates),
                    'insight': f'{range_name.title()} disagreement between AIs',
                    'confidence': min(len(range_debates) / 5, 1.0)
                })

        return rules

    def get_recommendation_adjustment(
        self,
        consensus_score: int,
        patterns_detected: List[str],
        focus_areas: List[str],
        score_difference: int
    ) -> Dict:
        """
        Get recommendation adjustment based on learned rules.

        Args:
            consensus_score: Current consensus score
            patterns_detected: Patterns detected in current debate
            focus_areas: Focus areas used
            score_difference: Difference between AI scores

        Returns:
            {
                'adjustment': str (description),
                'severity_change': int (-1, 0, +1),
                'confidence': float (0-1),
                'applied_rules': list[str]
            }
        """
        learned_data = self.learn_from_outcomes()
        rules = learned_data.get('rules', [])

        if not rules:
            return {
                'adjustment': 'No learned rules available',
                'severity_change': 0,
                'confidence': 0.0,
                'applied_rules': []
            }

        severity_change = 0
        applied_rules = []
        confidences = []

        # Check consensus threshold rules
        for rule in rules:
            if rule['type'] == 'consensus_threshold':
                # Parse condition (e.g., "70 <= consensus < 85")
                # v0.9.6: Use safe_evaluate_condition instead of eval() (Issue #3)
                condition = rule.get('condition', '')
                if 'consensus' in condition:
                    try:
                        # Use AST-based safe evaluation
                        if safe_evaluate_condition(condition, consensus_score):
                            if rule.get('success_rate', 0.5) < 0.5:
                                severity_change += 1
                            applied_rules.append(rule['adjustment'])
                            confidences.append(rule.get('confidence', 0.5))
                    except Exception as e:
                        # v0.9.6: Log errors instead of silently passing (Issue #15)
                        logger.warning(f"Failed to evaluate rule condition '{condition}': {e}")

            # Check pattern rules
            elif rule['type'] == 'pattern_success':
                if rule['pattern_name'] in patterns_detected:
                    if rule.get('success_rate', 0.5) < 0.5:
                        severity_change += 1
                        applied_rules.append(f"Pattern {rule['pattern_name']} has low success rate")
                        confidences.append(rule.get('confidence', 0.5))

            # Check focus area rules
            elif rule['type'] == 'focus_combination':
                if set(rule['focus_areas']) == set(focus_areas):
                    if rule.get('success_rate', 0.5) < 0.5:
                        applied_rules.append(f"Focus combination has low success rate")
                        confidences.append(rule.get('confidence', 0.5))

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Generate adjustment description
        if severity_change > 0:
            adjustment = f"Increase severity by {severity_change} level(s) based on learned patterns"
        elif severity_change < 0:
            adjustment = f"Decrease severity by {abs(severity_change)} level(s) based on learned patterns"
        else:
            adjustment = "No severity adjustment needed"

        return {
            'adjustment': adjustment,
            'severity_change': min(severity_change, 2),  # Cap at +2
            'confidence': round(avg_confidence, 2),
            'applied_rules': applied_rules
        }

    def get_learning_summary(self) -> str:
        """
        Get human-readable summary of learned rules.

        Returns:
            Formatted summary string
        """
        learned_data = self.learn_from_outcomes()

        lines = []
        lines.append("=" * 60)
        lines.append("DECISION LEARNING SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        lines.append(f"Total Debates: {learned_data['total_debates']}")
        lines.append(f"Debates with Outcomes: {learned_data['outcome_debates']}")
        lines.append(f"Learned Rules: {len(learned_data.get('rules', []))}")
        lines.append("")

        if learned_data.get('note'):
            lines.append(f"Note: {learned_data['note']}")
            lines.append("")
            lines.append("=" * 60)
            return "\n".join(lines)

        # Group rules by type
        rules = learned_data.get('rules', [])
        by_type = defaultdict(list)
        for rule in rules:
            by_type[rule['type']].append(rule)

        # Consensus threshold rules
        if 'consensus_threshold' in by_type:
            lines.append("CONSENSUS THRESHOLD RULES:")
            for rule in by_type['consensus_threshold']:
                lines.append(f"  - {rule['condition']}: " +
                           f"success rate {rule['success_rate']*100:.0f}% " +
                           f"(n={rule['sample_size']})")
                lines.append(f"    → {rule['learned_recommendation']}")
            lines.append("")

        # Pattern success rules
        if 'pattern_success' in by_type:
            lines.append("PATTERN SUCCESS RULES:")
            for rule in by_type['pattern_success'][:5]:
                lines.append(f"  - {rule['pattern_name']}: " +
                           f"success rate {rule['success_rate']*100:.0f}% " +
                           f"(n={rule['sample_size']})")
            lines.append("")

        # Focus combination rules
        if 'focus_combination' in by_type:
            lines.append("FOCUS COMBINATION RULES:")
            for rule in by_type['focus_combination'][:5]:
                areas = ', '.join(rule['focus_areas'])
                lines.append(f"  - {areas}: " +
                           f"success rate {rule['success_rate']*100:.0f}% " +
                           f"(n={rule['sample_size']})")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)
