"""
Decision Pack Formatter - Structured, concise debate output.

Formats debate results into clear, actionable format:
- Quick Action Summary (top 5 must-fix items)
- Issues by Severity (tables)
- Disagreements requiring decision
- Approved aspects
- Alternative approaches
- Final recommendation

Target: ≤300 lines total
"""

from typing import List, Dict, Optional
from .priority_scorer import PriorityScorer


class DecisionPackFormatter:
    """Format debate results in structured, concise format."""

    MAX_LINES = 300  # Target line count (soft limit)
    QUICK_ACTION_COUNT = 5  # Number of issues in Quick Action Summary

    @classmethod
    def format_structured(
        cls,
        topic: str,
        consensus_score: int,
        claude_score: int,
        codex_score: int,
        debate_time_seconds: int,
        scored_issues: List[Dict],
        disagreements: List[Dict] = None,
        approved_aspects: List[str] = None,
        alternatives: List[Dict] = None
    ) -> str:
        """
        Generate structured decision pack (≤300 lines).

        Args:
            topic: Debate topic (e.g., "v0.7.3 Refactoring Plan")
            consensus_score: Overall consensus (0-100)
            claude_score: Claude's score (0-100)
            codex_score: Codex's score (0-100)
            debate_time_seconds: Time taken for debate
            scored_issues: List of issues (must have priority_score, priority_label)
            disagreements: List of points requiring user decision
            approved_aspects: List of aspects that are good to proceed
            alternatives: List of alternative approaches considered

        Returns:
            Markdown-formatted decision pack string
        """
        disagreements = disagreements or []
        approved_aspects = approved_aspects or []
        alternatives = alternatives or []

        # Group issues by severity
        grouped = PriorityScorer.get_issues_by_severity(scored_issues)

        # Calculate fix times
        fix_times = PriorityScorer.calculate_fix_time(scored_issues)

        # Determine execution recommendation
        exec_rec = cls._get_execution_recommendation(
            consensus_score,
            len(grouped['stop_ship'])
        )

        # Build decision pack
        sections = []

        # Header
        sections.append(cls._format_header(
            topic,
            consensus_score,
            claude_score,
            codex_score,
            debate_time_seconds,
            exec_rec
        ))

        # Quick Action Summary
        sections.append(cls._format_quick_action_summary(
            scored_issues,
            fix_times
        ))

        # Issues by Severity
        sections.append(cls._format_issues_by_severity(grouped))

        # Disagreements (if any)
        if disagreements:
            sections.append(cls._format_disagreements(disagreements))

        # Approved Aspects (if any)
        if approved_aspects:
            sections.append(cls._format_approved_aspects(approved_aspects))

        # Alternatives (if any)
        if alternatives:
            sections.append(cls._format_alternatives(alternatives))

        # Final Recommendation
        sections.append(cls._format_final_recommendation(
            consensus_score,
            len(grouped['stop_ship']),
            len(grouped['high']),
            fix_times
        ))

        return '\n\n'.join(sections)

    @classmethod
    def _get_execution_recommendation(
        cls,
        consensus_score: int,
        stop_ship_count: int
    ) -> str:
        """Determine execution recommendation based on consensus and issues."""
        if stop_ship_count > 0:
            return f"⚠️ CONDITIONAL GO - Fix {stop_ship_count} stop-ship issues first"
        elif consensus_score >= 85:
            return "✅ GO - Proceed with confidence"
        elif consensus_score >= 70:
            return "⚠️ PROCEED WITH CAUTION - Address key concerns"
        elif consensus_score >= 50:
            return "🔶 REVIEW NEEDED - Significant issues to resolve"
        else:
            return "🔴 NO-GO - Fundamental disagreements, reconsider approach"

    @classmethod
    def _format_header(
        cls,
        topic: str,
        consensus_score: int,
        claude_score: int,
        codex_score: int,
        debate_time_seconds: int,
        exec_rec: str
    ) -> str:
        """Format decision pack header."""
        consensus_interpretation = cls._interpret_consensus(consensus_score)

        return f"""# AI DEBATE DECISION PACK: {topic}

**Consensus:** {consensus_score}/100 ({consensus_interpretation})
**Execution Recommendation:** {exec_rec}
**Debate Time:** {debate_time_seconds} seconds
**Participants:** Claude ({claude_score}/100) + Codex ({codex_score}/100)

---"""

    @classmethod
    def _interpret_consensus(cls, score: int) -> str:
        """Interpret consensus score as text."""
        if score >= 85:
            return "Strong Agreement"
        elif score >= 70:
            return "Moderate Agreement"
        elif score >= 50:
            return "Significant Disagreements"
        else:
            return "Fundamental Disagreements"

    @classmethod
    def _format_quick_action_summary(
        cls,
        scored_issues: List[Dict],
        fix_times: Dict[str, str]
    ) -> str:
        """Format Quick Action Summary section."""
        # Get top N issues (highest priority)
        top_issues = scored_issues[:cls.QUICK_ACTION_COUNT]

        if not top_issues:
            return """## ⚡ QUICK ACTION SUMMARY

✅ **No critical issues found** - Plan approved as-is

---"""

        lines = [
            "## ⚡ QUICK ACTION SUMMARY (Top 5 Must-Fix)",
            ""
        ]

        for i, issue in enumerate(top_issues, 1):
            label = issue['priority_label']
            title = issue['title']
            impact = issue.get('impact', 'unknown').title()

            # Truncate title if too long
            if len(title) > 60:
                title = title[:57] + "..."

            lines.append(f"{i}. {label}: {title} ({impact} impact)")

        # Add summary stats
        lines.append("")
        lines.append(f"**Estimated Fix Time:** {fix_times.get('stop_ship', '0 hours')} (stop-ship) + {fix_times.get('high', '0 hours')} (high)")
        lines.append(f"**Total Effort:** {fix_times['total']}")

        # Risk reduction
        risk_level = "HIGH" if len([i for i in scored_issues if i['priority_score'] >= 85]) >= 3 else "MEDIUM"
        lines.append(f"**Risk Reduction:** {risk_level}")

        lines.append("")
        lines.append("---")

        return '\n'.join(lines)

    @classmethod
    def _format_issues_by_severity(cls, grouped: Dict[str, List[Dict]]) -> str:
        """Format issues grouped by severity level."""
        sections = ["## 📊 ISSUES BY SEVERITY", ""]

        # Stop-ship issues
        if grouped['stop_ship']:
            sections.append("### 🔴 STOP-SHIP ISSUES (Must Fix Before Release)")
            sections.append("")
            sections.append("| # | Issue | Impact | Effort | Fix |")
            sections.append("|---|-------|--------|--------|-----|")

            for i, issue in enumerate(grouped['stop_ship'], 1):
                title = cls._truncate(issue['title'], 40)
                impact = issue.get('impact', 'unknown').title()
                effort = cls._format_effort(issue.get('effort', 'medium'))
                fix = cls._truncate(issue.get('fix', 'See details'), 30)

                sections.append(f"| {i} | {title} | {impact} | {effort} | {fix} |")

            sections.append("")

        # High priority issues
        if grouped['high']:
            sections.append("### 🟠 HIGH PRIORITY (Strongly Recommended)")
            sections.append("")
            sections.append("| # | Issue | Impact | Effort | Fix |")
            sections.append("|---|-------|--------|--------|-----|")

            for i, issue in enumerate(grouped['high'], 1):
                title = cls._truncate(issue['title'], 40)
                impact = issue.get('impact', 'unknown').title()
                effort = cls._format_effort(issue.get('effort', 'medium'))
                fix = cls._truncate(issue.get('fix', 'See details'), 30)

                sections.append(f"| {i} | {title} | {impact} | {effort} | {fix} |")

            sections.append("")

        # Medium priority issues (compact format)
        if grouped['medium']:
            sections.append("### 🟡 MEDIUM PRIORITY (Nice to Have)")
            sections.append("")

            for issue in grouped['medium']:
                title = issue['title']
                effort = cls._format_effort(issue.get('effort', 'medium'))
                sections.append(f"- {title} ({effort})")

            sections.append("")

        # Low priority (just count)
        if grouped['low']:
            sections.append(f"### ⚪ LOW PRIORITY")
            sections.append(f"*{len(grouped['low'])} optional improvements (see full analysis)*")
            sections.append("")

        sections.append("---")

        return '\n'.join(sections)

    @classmethod
    def _format_disagreements(cls, disagreements: List[Dict]) -> str:
        """Format disagreements requiring user decision."""
        sections = ["## 🤔 DISAGREEMENTS REQUIRING USER DECISION", ""]

        for i, disagreement in enumerate(disagreements, 1):
            sections.append(f"### Disagreement #{i}: {disagreement.get('topic', 'Unknown')}")
            sections.append("")
            sections.append(f"- **Claude:** {disagreement.get('claude_view', 'N/A')}")
            sections.append(f"- **Codex:** {disagreement.get('codex_view', 'N/A')}")
            sections.append(f"- **Impact:** {disagreement.get('impact', 'Unknown')}")
            sections.append(f"- **Recommendation:** {disagreement.get('recommendation', 'User decision required')}")
            sections.append("")

        sections.append("---")

        return '\n'.join(sections)

    @classmethod
    def _format_approved_aspects(cls, approved_aspects: List[str]) -> str:
        """Format approved aspects (proceed as-is)."""
        sections = ["## ✅ APPROVED ASPECTS (Proceed As-Is)", ""]

        for aspect in approved_aspects:
            sections.append(f"- {aspect}")

        sections.append("")
        sections.append("---")

        return '\n'.join(sections)

    @classmethod
    def _format_alternatives(cls, alternatives: List[Dict]) -> str:
        """Format alternative approaches considered."""
        sections = ["## 💡 ALTERNATIVE APPROACHES", ""]

        for i, alt in enumerate(alternatives, 1):
            sections.append(f"### Alternative {i}: {alt.get('title', 'Unknown')}")
            sections.append("")
            sections.append(f"**Pros:** {alt.get('pros', 'N/A')}")
            sections.append(f"**Cons:** {alt.get('cons', 'N/A')}")
            sections.append(f"**Consensus:** {alt.get('consensus', 'N/A')}")
            sections.append("")

        sections.append("---")

        return '\n'.join(sections)

    @classmethod
    def _format_final_recommendation(
        cls,
        consensus_score: int,
        stop_ship_count: int,
        high_count: int,
        fix_times: Dict[str, str]
    ) -> str:
        """Format final recommendation section."""
        sections = ["## 🏁 FINAL RECOMMENDATION", ""]

        if stop_ship_count > 0:
            sections.append(f"**Decision:** ⚠️ **CONDITIONAL GO**")
            sections.append("")
            sections.append(f"**Conditions:**")
            sections.append(f"1. ✅ Fix {stop_ship_count} stop-ship issues ({fix_times.get('stop_ship', 'N/A')}) BEFORE starting")

            if high_count > 0:
                sections.append(f"2. ✅ Address {high_count} high-priority items during implementation")

            sections.append("")
            sections.append(f"**If conditions met:** 95% confidence of success")
            sections.append(f"**If conditions ignored:** High risk of critical issues")

        elif consensus_score >= 85:
            sections.append(f"**Decision:** ✅ **GO - Proceed with Confidence**")
            sections.append("")
            sections.append(f"**Consensus:** {consensus_score}/100 (Strong agreement)")
            sections.append(f"**High-priority items:** {high_count} (address during implementation)")
            sections.append(f"**Estimated additional effort:** {fix_times.get('high', '0 hours')}")

        elif consensus_score >= 70:
            sections.append(f"**Decision:** ⚠️ **PROCEED WITH CAUTION**")
            sections.append("")
            sections.append(f"**Consensus:** {consensus_score}/100 (Moderate agreement)")
            sections.append(f"**Action:** Address key concerns before proceeding")

        else:
            sections.append(f"**Decision:** 🔴 **REVIEW NEEDED**")
            sections.append("")
            sections.append(f"**Consensus:** {consensus_score}/100 (Significant disagreements)")
            sections.append(f"**Action:** Resolve fundamental issues before implementation")

        sections.append("")
        sections.append("---")

        return '\n'.join(sections)

    @staticmethod
    def _truncate(text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    @staticmethod
    def _format_effort(effort: str) -> str:
        """Format effort as human-readable string."""
        effort_map = {
            'low': '<30 min',
            'medium': '1-4 hours',
            'high': '>4 hours'
        }
        return effort_map.get(effort.lower(), effort)
