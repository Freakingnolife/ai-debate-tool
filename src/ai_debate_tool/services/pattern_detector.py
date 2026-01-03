"""
Pattern Detector - Extract recurring patterns from debate history.

Analyzes debate history to identify:
1. Common issues and concerns
2. Recurring keywords and phrases
3. Pattern clusters (similar debates)
4. Pattern frequency and severity rankings

Uses zero-cost text analysis (TF-IDF, keyword extraction) instead of LLMs.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
import hashlib


class PatternDetector:
    """Detect recurring patterns in debate history."""

    # Pattern categories
    PATTERN_CATEGORIES = [
        'refactoring',
        'database',
        'testing',
        'architecture',
        'performance',
        'security',
        'migration',
        'deployment'
    ]

    # Common risk keywords
    RISK_KEYWORDS = {
        'circular_imports': ['circular', 'import', 'dependency', 'cycle'],
        'transaction_boundaries': ['transaction', 'atomic', 'rollback', 'commit'],
        'missing_migration': ['migration', 'schema', 'database', 'alter'],
        'tight_coupling': ['coupling', 'dependency', 'tightly', 'coupled'],
        'unclear_interfaces': ['interface', 'contract', 'api', 'boundary'],
        'insufficient_testing': ['test', 'coverage', 'untested', 'missing test'],
        'performance_regression': ['performance', 'slow', 'optimization', 'regression'],
        'backward_compatibility': ['backward', 'compatibility', 'breaking', 'deprecated']
    }

    def __init__(self, history_manager):
        """
        Initialize pattern detector.

        Args:
            history_manager: DebateHistoryManager instance
        """
        self.history = history_manager
        self.pattern_cache_file = history_manager.patterns_dir / 'pattern_index.json'

    def detect_patterns(
        self,
        min_debates: int = 3,
        min_frequency: int = 2,
        force_refresh: bool = False
    ) -> List[Dict]:
        """
        Detect patterns across all debates.

        Args:
            min_debates: Minimum debates required for pattern detection
            min_frequency: Minimum occurrences to be considered a pattern
            force_refresh: Force re-analysis (ignore cache)

        Returns:
            List of detected patterns with metadata
        """
        # Load from cache if available
        if not force_refresh and self.pattern_cache_file.exists():
            with open(self.pattern_cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                # Check if cache is still valid (has enough debates)
                if cached.get('total_debates', 0) >= min_debates:
                    return cached.get('patterns', [])

        # Get all debates
        all_debates = self.history.query_debates(limit=1000)

        if len(all_debates) < min_debates:
            # Not enough data for pattern detection
            return []

        # Extract patterns
        patterns = []

        # Pattern 1: Risk keyword patterns
        risk_patterns = self._detect_risk_patterns(all_debates, min_frequency)
        patterns.extend(risk_patterns)

        # Pattern 2: File-based patterns (e.g., "large file refactoring")
        file_patterns = self._detect_file_patterns(all_debates, min_frequency)
        patterns.extend(file_patterns)

        # Pattern 3: Focus area patterns
        focus_patterns = self._detect_focus_patterns(all_debates, min_frequency)
        patterns.extend(focus_patterns)

        # Pattern 4: Consensus score patterns
        consensus_patterns = self._detect_consensus_patterns(all_debates)
        patterns.extend(consensus_patterns)

        # Rank patterns by importance
        patterns = self._rank_patterns(patterns, all_debates)

        # Cache results
        cache_data = {
            'total_debates': len(all_debates),
            'last_updated': self.history._generate_debate_id(),  # Use timestamp
            'patterns': patterns
        }

        with open(self.pattern_cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

        return patterns

    def _detect_risk_patterns(
        self,
        debates: List[Dict],
        min_frequency: int
    ) -> List[Dict]:
        """
        Detect risk keyword patterns.

        Args:
            debates: List of debate records
            min_frequency: Minimum occurrences

        Returns:
            List of risk patterns
        """
        patterns = []
        risk_counters = defaultdict(list)

        for debate in debates:
            # Combine disagreements into single text
            text = ' '.join([
                d.get('text', '') for d in debate.get('disagreements', [])
            ]).lower()

            # Check for risk keywords
            for risk_name, keywords in self.RISK_KEYWORDS.items():
                if any(keyword in text for keyword in keywords):
                    risk_counters[risk_name].append({
                        'debate_id': debate['debate_id'],
                        'consensus': debate['consensus_score'],
                        'outcome': debate.get('outcome', 'pending')
                    })

        # Create patterns for frequent risks
        for risk_name, occurrences in risk_counters.items():
            if len(occurrences) >= min_frequency:
                # Calculate metrics
                avg_consensus = sum(o['consensus'] for o in occurrences) / len(occurrences)
                success_rate = len([o for o in occurrences if o['outcome'] == 'succeeded']) / len([o for o in occurrences if o['outcome'] != 'pending']) if any(o['outcome'] != 'pending' for o in occurrences) else 0

                patterns.append({
                    'type': 'risk',
                    'name': risk_name,
                    'frequency': len(occurrences),
                    'avg_consensus': round(avg_consensus, 1),
                    'success_rate': round(success_rate, 2),
                    'occurrences': occurrences,
                    'keywords': self.RISK_KEYWORDS[risk_name]
                })

        return patterns

    def _detect_file_patterns(
        self,
        debates: List[Dict],
        min_frequency: int
    ) -> List[Dict]:
        """
        Detect file-based patterns (e.g., large file refactoring).

        Args:
            debates: List of debate records
            min_frequency: Minimum occurrences

        Returns:
            List of file patterns
        """
        patterns = []

        # Group by file size ranges
        size_groups = {
            'small': [],  # < 500 lines
            'medium': [],  # 500-1500 lines
            'large': []  # > 1500 lines
        }

        for debate in debates:
            file_size = debate.get('file_size', 0)
            lines = file_size // 50  # Rough estimate (50 chars per line avg)

            if lines < 500:
                size_groups['small'].append(debate)
            elif lines < 1500:
                size_groups['medium'].append(debate)
            else:
                size_groups['large'].append(debate)

        # Create patterns for each size group
        for size_name, group_debates in size_groups.items():
            if len(group_debates) >= min_frequency:
                # Check if refactoring-related
                refactor_count = sum(
                    1 for d in group_debates
                    if any(kw in d.get('request', '').lower() for kw in ['refactor', 'split', 'extract', 'reorganize'])
                )

                if refactor_count >= min_frequency:
                    avg_consensus = sum(d['consensus_score'] for d in group_debates) / len(group_debates)

                    patterns.append({
                        'type': 'file_pattern',
                        'name': f'{size_name}_file_refactoring',
                        'frequency': refactor_count,
                        'avg_consensus': round(avg_consensus, 1),
                        'file_size_range': size_name,
                        'sample_debates': [d['debate_id'] for d in group_debates[:3]]
                    })

        return patterns

    def _detect_focus_patterns(
        self,
        debates: List[Dict],
        min_frequency: int
    ) -> List[Dict]:
        """
        Detect focus area patterns.

        Args:
            debates: List of debate records
            min_frequency: Minimum occurrences

        Returns:
            List of focus patterns
        """
        patterns = []
        focus_combinations = Counter()

        for debate in debates:
            focus_areas = tuple(sorted(debate.get('focus_areas', [])))
            if focus_areas:
                focus_combinations[focus_areas] += 1

        # Create patterns for frequent combinations
        for focus_combo, frequency in focus_combinations.items():
            if frequency >= min_frequency:
                # Get debates with this focus combination
                matching_debates = [
                    d for d in debates
                    if tuple(sorted(d.get('focus_areas', []))) == focus_combo
                ]

                avg_consensus = sum(d['consensus_score'] for d in matching_debates) / len(matching_debates)

                patterns.append({
                    'type': 'focus_pattern',
                    'name': '_'.join(focus_combo),
                    'frequency': frequency,
                    'focus_areas': list(focus_combo),
                    'avg_consensus': round(avg_consensus, 1),
                    'sample_debates': [d['debate_id'] for d in matching_debates[:3]]
                })

        return patterns

    def _detect_consensus_patterns(self, debates: List[Dict]) -> List[Dict]:
        """
        Detect consensus score patterns.

        Args:
            debates: List of debate records

        Returns:
            List of consensus patterns
        """
        patterns = []

        # Group by consensus ranges
        ranges = {
            'low': [d for d in debates if d['consensus_score'] < 50],
            'medium': [d for d in debates if 50 <= d['consensus_score'] < 70],
            'high': [d for d in debates if 70 <= d['consensus_score'] < 85],
            'very_high': [d for d in debates if d['consensus_score'] >= 85]
        }

        for range_name, group_debates in ranges.items():
            if len(group_debates) >= 2:
                # Check outcome success rates
                outcomes_known = [d for d in group_debates if d.get('outcome') != 'pending']
                if outcomes_known:
                    success_rate = len([d for d in outcomes_known if d['outcome'] == 'succeeded']) / len(outcomes_known)

                    patterns.append({
                        'type': 'consensus_pattern',
                        'name': f'{range_name}_consensus',
                        'frequency': len(group_debates),
                        'consensus_range': range_name,
                        'success_rate': round(success_rate, 2),
                        'avg_consensus': round(sum(d['consensus_score'] for d in group_debates) / len(group_debates), 1)
                    })

        return patterns

    def _rank_patterns(self, patterns: List[Dict], all_debates: List[Dict]) -> List[Dict]:
        """
        Rank patterns by importance/relevance.

        Args:
            patterns: List of patterns
            all_debates: All debates

        Returns:
            Ranked patterns (sorted by priority score)
        """
        for pattern in patterns:
            # Calculate priority score (0-100)
            # Factors: frequency, consensus impact, success rate

            frequency_score = min(pattern.get('frequency', 0) / len(all_debates) * 100, 50)
            consensus_impact = 100 - pattern.get('avg_consensus', 70)  # Lower consensus = higher priority
            success_penalty = (1 - pattern.get('success_rate', 0.5)) * 30 if pattern.get('success_rate') is not None else 0

            priority_score = frequency_score + (consensus_impact * 0.3) + success_penalty

            pattern['priority_score'] = round(min(priority_score, 100), 1)

        # Sort by priority (highest first)
        patterns.sort(key=lambda p: p.get('priority_score', 0), reverse=True)

        return patterns

    def get_patterns_for_request(
        self,
        request: str,
        file_path: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Get relevant patterns for a specific request.

        Args:
            request: User's debate request
            file_path: Optional file path
            top_k: Maximum patterns to return

        Returns:
            List of relevant patterns
        """
        all_patterns = self.detect_patterns()

        if not all_patterns:
            return []

        request_lower = request.lower()

        # Score patterns by relevance to request
        scored_patterns = []

        for pattern in all_patterns:
            relevance_score = 0

            # Keyword matching
            if pattern['type'] == 'risk':
                if any(kw in request_lower for kw in pattern.get('keywords', [])):
                    relevance_score += 50

            # Focus area matching
            elif pattern['type'] == 'focus_pattern':
                focus_areas = pattern.get('focus_areas', [])
                if any(area in request_lower for area in focus_areas):
                    relevance_score += 40

            # File pattern matching
            elif pattern['type'] == 'file_pattern':
                if file_path:
                    # Check file size
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_size = len(f.read())
                            lines = file_size // 50

                            if pattern.get('file_size_range') == 'large' and lines > 1500:
                                relevance_score += 60
                            elif pattern.get('file_size_range') == 'medium' and 500 <= lines < 1500:
                                relevance_score += 60
                            elif pattern.get('file_size_range') == 'small' and lines < 500:
                                relevance_score += 60
                    except:
                        pass

            # Add base priority score
            relevance_score += pattern.get('priority_score', 0) * 0.3

            if relevance_score > 0:
                pattern_copy = pattern.copy()
                pattern_copy['relevance_score'] = round(relevance_score, 1)
                scored_patterns.append(pattern_copy)

        # Sort by relevance
        scored_patterns.sort(key=lambda p: p.get('relevance_score', 0), reverse=True)

        return scored_patterns[:top_k]

    def get_pattern_summary(self) -> str:
        """
        Get human-readable summary of all patterns.

        Returns:
            Formatted summary string
        """
        patterns = self.detect_patterns()

        if not patterns:
            return "No patterns detected yet. Run more debates to build pattern history."

        lines = []
        lines.append("=" * 60)
        lines.append("PATTERN DETECTION SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        # Group by type
        by_type = defaultdict(list)
        for pattern in patterns:
            by_type[pattern['type']].append(pattern)

        # Risk patterns
        if 'risk' in by_type:
            lines.append("RISK PATTERNS:")
            for pattern in by_type['risk'][:5]:
                lines.append(f"  - {pattern['name']}: {pattern['frequency']} occurrences, " +
                           f"avg consensus {pattern['avg_consensus']}/100")
            lines.append("")

        # File patterns
        if 'file_pattern' in by_type:
            lines.append("FILE PATTERNS:")
            for pattern in by_type['file_pattern']:
                lines.append(f"  - {pattern['name']}: {pattern['frequency']} occurrences, " +
                           f"avg consensus {pattern['avg_consensus']}/100")
            lines.append("")

        # Focus patterns
        if 'focus_pattern' in by_type:
            lines.append("FOCUS AREA PATTERNS:")
            for pattern in by_type['focus_pattern'][:5]:
                lines.append(f"  - {pattern['name']}: {pattern['frequency']} occurrences, " +
                           f"avg consensus {pattern['avg_consensus']}/100")
            lines.append("")

        # Consensus patterns
        if 'consensus_pattern' in by_type:
            lines.append("CONSENSUS PATTERNS:")
            for pattern in by_type['consensus_pattern']:
                lines.append(f"  - {pattern['name']}: success rate {pattern.get('success_rate', 0)*100:.0f}%")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)
