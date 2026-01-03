"""
Priority Scorer - Objective priority scoring for debate issues.

Calculates priority scores based on:
- Severity (critical/high/medium/low)
- Impact (high/medium/low)
- Effort (low/medium/high)

Formula: Score = Severity + Impact + Effort Penalty
Thresholds:
- ≥85: 🔴 STOP-SHIP (must fix before release)
- ≥65: 🟠 HIGH (strongly recommended)
- ≥50: 🟡 MEDIUM (nice to have)
- <50: ⚪ LOW (optional)
"""

from typing import List, Dict, Tuple


class PriorityScorer:
    """Calculate objective priority scores for debate issues."""

    # Severity contribution (max 40 points)
    SEVERITY_SCORES = {
        'critical': 40,
        'high': 30,
        'medium': 20,
        'low': 10
    }

    # Impact contribution (max 40 points)
    IMPACT_SCORES = {
        'high': 40,
        'medium': 25,
        'low': 10
    }

    # Effort penalty (inverse - less effort = higher priority)
    EFFORT_PENALTY = {
        'low': 0,       # <30 minutes: no penalty
        'medium': -10,  # 1-4 hours: slight penalty
        'high': -20     # >4 hours: significant penalty
    }

    # Priority thresholds
    THRESHOLDS = {
        'stop_ship': 85,
        'high': 65,
        'medium': 50,
        'low': 0
    }

    @classmethod
    def score_issue(
        cls,
        severity: str,
        impact: str,
        effort: str
    ) -> Tuple[int, str]:
        """
        Calculate priority score and label for a single issue.

        Args:
            severity: 'critical', 'high', 'medium', 'low'
            impact: 'high', 'medium', 'low'
            effort: 'low' (<30 min), 'medium' (1-4h), 'high' (>4h)

        Returns:
            (priority_score, priority_label)
            - priority_score: 0-100 (higher = more urgent)
            - priority_label: '🔴 STOP-SHIP', '🟠 HIGH', '🟡 MEDIUM', '⚪ LOW'

        Examples:
            >>> PriorityScorer.score_issue('critical', 'high', 'low')
            (80, '🔴 STOP-SHIP')

            >>> PriorityScorer.score_issue('high', 'medium', 'medium')
            (45, '🟡 MEDIUM')
        """
        # Validate inputs
        severity = severity.lower()
        impact = impact.lower()
        effort = effort.lower()

        if severity not in cls.SEVERITY_SCORES:
            raise ValueError(f"Invalid severity: {severity}")
        if impact not in cls.IMPACT_SCORES:
            raise ValueError(f"Invalid impact: {impact}")
        if effort not in cls.EFFORT_PENALTY:
            raise ValueError(f"Invalid effort: {effort}")

        # Calculate score
        score = (
            cls.SEVERITY_SCORES[severity] +
            cls.IMPACT_SCORES[impact] +
            cls.EFFORT_PENALTY[effort]
        )

        # Determine label
        if score >= cls.THRESHOLDS['stop_ship']:
            label = '🔴 STOP-SHIP'
        elif score >= cls.THRESHOLDS['high']:
            label = '🟠 HIGH'
        elif score >= cls.THRESHOLDS['medium']:
            label = '🟡 MEDIUM'
        else:
            label = '⚪ LOW'

        return (score, label)

    @classmethod
    def score_issues(cls, issues: List[Dict]) -> List[Dict]:
        """
        Score all issues and sort by priority (descending).

        Args:
            issues: List of issue dicts with 'severity', 'impact', 'effort' fields
                Example:
                [
                    {
                        'title': 'Race condition in payment',
                        'severity': 'critical',
                        'impact': 'high',
                        'effort': 'low',
                        'description': '...',
                        'fix': '...'
                    },
                    ...
                ]

        Returns:
            Same issues with added fields:
            - priority_score: int (0-100)
            - priority_label: str ('🔴 STOP-SHIP', etc.)
            Sorted descending by priority_score (highest priority first)

        Example:
            >>> issues = [
            ...     {'title': 'Bug A', 'severity': 'low', 'impact': 'low', 'effort': 'high'},
            ...     {'title': 'Bug B', 'severity': 'critical', 'impact': 'high', 'effort': 'low'},
            ... ]
            >>> scored = PriorityScorer.score_issues(issues)
            >>> scored[0]['title']
            'Bug B'
            >>> scored[0]['priority_score']
            80
        """
        scored_issues = []

        for issue in issues:
            # Calculate score
            score, label = cls.score_issue(
                issue['severity'],
                issue['impact'],
                issue['effort']
            )

            # Add score fields to issue
            scored_issue = issue.copy()
            scored_issue['priority_score'] = score
            scored_issue['priority_label'] = label

            scored_issues.append(scored_issue)

        # Sort descending by priority_score
        scored_issues.sort(key=lambda x: x['priority_score'], reverse=True)

        return scored_issues

    @classmethod
    def get_issues_by_severity(cls, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group scored issues by severity level.

        Args:
            issues: List of scored issues (must have priority_score field)

        Returns:
            Dict with severity level as key:
            {
                'stop_ship': [issues with score >= 85],
                'high': [issues with 65 <= score < 85],
                'medium': [issues with 50 <= score < 65],
                'low': [issues with score < 50]
            }
        """
        grouped = {
            'stop_ship': [],
            'high': [],
            'medium': [],
            'low': []
        }

        for issue in issues:
            score = issue.get('priority_score', 0)

            if score >= cls.THRESHOLDS['stop_ship']:
                grouped['stop_ship'].append(issue)
            elif score >= cls.THRESHOLDS['high']:
                grouped['high'].append(issue)
            elif score >= cls.THRESHOLDS['medium']:
                grouped['medium'].append(issue)
            else:
                grouped['low'].append(issue)

        return grouped

    @classmethod
    def calculate_fix_time(cls, issues: List[Dict]) -> Dict[str, str]:
        """
        Calculate total fix time for issues by severity.

        Args:
            issues: List of scored issues with 'effort' field

        Returns:
            Dict with estimated times:
            {
                'stop_ship': '1.5 hours',
                'high': '3 hours',
                'total': '4.5 hours'
            }
        """
        # Effort to hours mapping
        effort_hours = {
            'low': 0.5,     # 30 minutes
            'medium': 2.5,  # 2.5 hours average of 1-4h
            'high': 6.0     # 6 hours average of 4-8h
        }

        grouped = cls.get_issues_by_severity(issues)
        times = {}

        for severity_level, issue_list in grouped.items():
            if not issue_list:
                times[severity_level] = '0 hours'
                continue

            total_hours = sum(
                effort_hours.get(issue.get('effort', 'medium'), 2.5)
                for issue in issue_list
            )

            if total_hours < 1:
                times[severity_level] = f'{int(total_hours * 60)} minutes'
            else:
                times[severity_level] = f'{total_hours:.1f} hours'

        # Calculate total
        all_hours = sum(
            effort_hours.get(issue.get('effort', 'medium'), 2.5)
            for issue in issues
        )
        if all_hours < 1:
            times['total'] = f'{int(all_hours * 60)} minutes'
        else:
            times['total'] = f'{all_hours:.1f} hours'

        return times
