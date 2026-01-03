"""Plan Reviser - AI-powered plan revision based on debate feedback.

Uses Codex CLI to intelligently revise plans by addressing specific issues
and disagreements identified during AI debates.

Features:
- Prioritizes top 5 critical/high issues
- Generates focused revision prompts
- Validates revisions (not empty, changed but not rewritten)
- Preserves plan structure and format

Usage:
    from ai_debate_tool.services.plan_reviser import PlanReviser
    from ai_debate_tool.services.codex_cli_invoker import CodexCLIInvoker

    plan_reviser = PlanReviser(CodexCLIInvoker())
    result = plan_reviser.revise_plan(
        plan_file_path='/path/to/plan.md',
        debate_result=debate_result,
        target_consensus=90
    )

    if result['success']:
        revised_content = result['revised_content']
        with open('/path/to/plan.md', 'w') as f:
            f.write(revised_content)
"""

from pathlib import Path
from typing import Dict, List, Optional
import difflib


class PlanReviser:
    """AI-powered plan revision based on debate feedback."""

    # Revision prompt template
    REVISION_PROMPT_TEMPLATE = """You are revising a technical plan based on AI debate feedback.

ORIGINAL PLAN:
───────────────────────────────────────────────────────────
{original_plan_content}
───────────────────────────────────────────────────────────

DEBATE CONSENSUS: {consensus_score}/100 (target: {target_consensus}+)

KEY ISSUES TO ADDRESS (Top {num_issues}):
{formatted_issues}

DISAGREEMENTS FROM DEBATE:
{formatted_disagreements}

YOUR TASK:
1. Carefully read the original plan above
2. Address ONLY the specific issues listed in "KEY ISSUES"
3. Preserve the overall structure, headings, and format
4. Make minimal, targeted changes to resolve concerns
5. Do NOT add new sections or major restructuring
6. Do NOT add explanations or meta-commentary
7. Return the COMPLETE revised plan (not just changes/diffs)

CRITICAL REQUIREMENTS:
- Output ONLY the revised plan content
- No markdown code blocks (```), no "Here is...", no explanations
- Just the raw plan text, ready to be saved to file

BEGIN REVISED PLAN:
"""

    def __init__(self, codex_invoker):
        """Initialize plan reviser.

        Args:
            codex_invoker: CodexCLIInvoker instance for LLM calls
        """
        self.codex_invoker = codex_invoker

    def revise_plan(
        self,
        plan_file_path: str,
        debate_result: Dict,
        target_consensus: int = 90
    ) -> Dict:
        """Revise plan based on debate feedback.

        Args:
            plan_file_path: Path to plan file
            debate_result: Debate result dict with scored_issues, disagreements, consensus_score
            target_consensus: Target consensus score (default: 90)

        Returns:
            {
                'success': bool,
                'revised_content': str (new plan content, or original if failed),
                'issues_addressed': list[dict] (which issues were targeted),
                'revision_summary': str (what was changed and why),
                'error': str (if failed, None if success)
            }
        """
        try:
            # Read original plan
            plan_path = Path(plan_file_path)
            if not plan_path.exists():
                return {
                    'success': False,
                    'revised_content': '',
                    'issues_addressed': [],
                    'revision_summary': '',
                    'error': f'Plan file not found: {plan_file_path}'
                }

            with open(plan_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Extract and prioritize issues
            scored_issues = debate_result.get('scored_issues', [])
            prioritized_issues = self._prioritize_issues(scored_issues)

            if not prioritized_issues:
                return {
                    'success': False,
                    'revised_content': original_content,
                    'issues_addressed': [],
                    'revision_summary': '',
                    'error': 'No issues to address'
                }

            # Format disagreements
            disagreements = debate_result.get('consensus', {}).get('disagreements', [])
            formatted_disagreements = self._format_disagreements(disagreements)

            # Generate revision prompt
            formatted_issues = self._format_issues(prioritized_issues)
            consensus_score = debate_result.get('consensus_score', 0)

            revision_prompt = self._generate_revision_prompt(
                original_content,
                formatted_issues,
                formatted_disagreements,
                consensus_score,
                target_consensus,
                len(prioritized_issues)
            )

            # Invoke Codex CLI for revision
            codex_result = self.codex_invoker.invoke(revision_prompt)

            if not codex_result['success']:
                return {
                    'success': False,
                    'revised_content': original_content,
                    'issues_addressed': prioritized_issues,
                    'revision_summary': '',
                    'error': f"Codex invocation failed: {codex_result.get('error', 'Unknown error')}"
                }

            revised_content = codex_result['response'].strip()

            # Validate revision
            is_valid, validation_error = self._validate_revision(original_content, revised_content)

            if not is_valid:
                return {
                    'success': False,
                    'revised_content': original_content,
                    'issues_addressed': prioritized_issues,
                    'revision_summary': '',
                    'error': f'Revision validation failed: {validation_error}'
                }

            # Generate revision summary
            revision_summary = self._generate_revision_summary(
                prioritized_issues,
                original_content,
                revised_content
            )

            return {
                'success': True,
                'revised_content': revised_content,
                'issues_addressed': prioritized_issues,
                'revision_summary': revision_summary,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'revised_content': '',
                'issues_addressed': [],
                'revision_summary': '',
                'error': f'Exception during revision: {str(e)}'
            }

    def _prioritize_issues(self, scored_issues: List[Dict]) -> List[Dict]:
        """Extract and prioritize top 5 critical/high issues.

        Args:
            scored_issues: List of issues with priority_score

        Returns:
            List of top 5 critical/high issues, sorted by priority
        """
        # Filter to critical (>= 85) and high (>= 65) issues
        high_priority = [
            issue for issue in scored_issues
            if issue.get('priority_score', 0) >= 65
        ]

        # Sort by priority score descending
        high_priority.sort(key=lambda x: x.get('priority_score', 0), reverse=True)

        # Return top 5
        return high_priority[:5]

    def _format_issues(self, issues: List[Dict]) -> str:
        """Format issues for prompt.

        Args:
            issues: List of prioritized issues

        Returns:
            Formatted string with numbered issues
        """
        if not issues:
            return "(No critical/high issues identified)"

        lines = []
        for i, issue in enumerate(issues, 1):
            priority_score = issue.get('priority_score', 0)
            severity = issue.get('severity', 'unknown').upper()
            title = issue.get('title', 'Unknown issue')
            description = issue.get('description', '')
            fix = issue.get('fix', '')

            lines.append(f"{i}. [{severity} - {priority_score}/100] {title}")
            if description and description != title:
                lines.append(f"   Concern: {description[:200]}")
            if fix:
                lines.append(f"   Fix Required: {fix[:200]}")
            lines.append("")  # Blank line between issues

        return "\n".join(lines)

    def _format_disagreements(self, disagreements: List[Dict]) -> str:
        """Format disagreements for prompt.

        Args:
            disagreements: List of disagreement dicts with 'source' and 'text'

        Returns:
            Formatted string with bullet points
        """
        if not disagreements:
            return "(No major disagreements identified)"

        lines = []
        for disagreement in disagreements[:5]:  # Top 5 only
            source = disagreement.get('source', 'Unknown')
            text = disagreement.get('text', '')
            if text:
                lines.append(f"- [{source}] {text[:150]}")

        return "\n".join(lines) if lines else "(No major disagreements)"

    def _generate_revision_prompt(
        self,
        original_content: str,
        formatted_issues: str,
        formatted_disagreements: str,
        consensus_score: int,
        target_consensus: int,
        num_issues: int
    ) -> str:
        """Generate revision prompt from template.

        Args:
            original_content: Full original plan content
            formatted_issues: Formatted issues string
            formatted_disagreements: Formatted disagreements string
            consensus_score: Current consensus score
            target_consensus: Target consensus score
            num_issues: Number of issues being addressed

        Returns:
            Complete revision prompt
        """
        return self.REVISION_PROMPT_TEMPLATE.format(
            original_plan_content=original_content,
            formatted_issues=formatted_issues,
            formatted_disagreements=formatted_disagreements,
            consensus_score=consensus_score,
            target_consensus=target_consensus,
            num_issues=num_issues
        )

    def _validate_revision(self, original: str, revised: str) -> tuple[bool, str]:
        """Validate revised content.

        Args:
            original: Original plan content
            revised: Revised plan content

        Returns:
            (is_valid, error_message)
        """
        # Check not empty
        if not revised or len(revised) < 100:
            return False, "Revision too short or empty"

        # Check changed from original
        if revised == original:
            return False, "No changes made by reviser"

        # Calculate change percentage
        change_pct = self._calculate_change_percentage(original, revised)

        # Check minimal change (< 1%)
        if change_pct < 1.0:
            return False, f"Changes too minimal ({change_pct:.1f}%)"

        # Check full rewrite (> 50%)
        if change_pct > 50.0:
            return False, f"Plan appears to be rewritten ({change_pct:.1f}% changed), not revised"

        # Valid revision (1% - 50% change)
        return True, ""

    def _calculate_change_percentage(self, original: str, revised: str) -> float:
        """Calculate percentage of content that changed.

        Args:
            original: Original content
            revised: Revised content

        Returns:
            Percentage changed (0-100)
        """
        # Use difflib to calculate similarity ratio
        original_lines = original.splitlines()
        revised_lines = revised.splitlines()

        # Calculate sequence matcher ratio
        matcher = difflib.SequenceMatcher(None, original_lines, revised_lines)
        similarity_ratio = matcher.ratio()

        # Convert to change percentage
        change_percentage = (1.0 - similarity_ratio) * 100

        return change_percentage

    def _generate_revision_summary(
        self,
        issues_addressed: List[Dict],
        original: str,
        revised: str
    ) -> str:
        """Generate human-readable summary of what was revised.

        Args:
            issues_addressed: List of issues that were targeted
            original: Original content
            revised: Revised content

        Returns:
            Summary string
        """
        num_issues = len(issues_addressed)
        change_pct = self._calculate_change_percentage(original, revised)

        if num_issues == 0:
            return "Minor improvements"

        # Extract issue titles
        issue_titles = [issue.get('title', 'Unknown')[:50] for issue in issues_addressed[:3]]

        if num_issues == 1:
            summary = f"Addressed: {issue_titles[0]}"
        elif num_issues == 2:
            summary = f"Addressed: {issue_titles[0]} and {issue_titles[1]}"
        else:
            summary = f"Addressed: {issue_titles[0]}, {issue_titles[1]}, and {num_issues - 2} more issue(s)"

        summary += f" ({change_pct:.1f}% of plan revised)"

        return summary
