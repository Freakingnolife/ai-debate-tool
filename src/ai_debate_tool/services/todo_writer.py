"""
Todo Writer - Auto-generate TodoWrite items from debate results.

Extracts actionable items from scored issues and formats them
for TodoWrite tool integration.

Only extracts high-priority items (score >= 65):
- Stop-ship issues (score >= 85)
- High priority issues (65 <= score < 85)

Skips medium and low priority items (user can address later if desired).
"""

from typing import List, Dict, Tuple


class TodoWriter:
    """Extract and format todos from debate results."""

    MIN_PRIORITY_SCORE = 65  # Only extract todos with score >= 65

    @classmethod
    def extract_todos(cls, scored_issues: List[Dict]) -> List[Dict]:
        """
        Extract actionable todos from scored issues.

        Only includes issues with priority_score >= 65 (stop-ship + high priority).
        Medium and low priority items are excluded (not urgent enough for immediate tracking).

        Args:
            scored_issues: List of issues with priority_score field

        Returns:
            List of todo dicts formatted for TodoWrite tool:
            [
                {
                    'content': 'Fix race condition in payment (15 min)',
                    'status': 'pending',
                    'activeForm': 'Fixing race condition in payment'
                },
                ...
            ]

        Example:
            >>> issues = [
            ...     {'title': 'Critical bug', 'priority_score': 90, 'effort': 'low'},
            ...     {'title': 'Nice to have', 'priority_score': 40, 'effort': 'low'}
            ... ]
            >>> todos = TodoWriter.extract_todos(issues)
            >>> len(todos)
            1
            >>> todos[0]['content']
            'Critical bug (<30 min)'
        """
        todos = []

        # Filter to high-priority items only
        actionable = [
            issue for issue in scored_issues
            if issue.get('priority_score', 0) >= cls.MIN_PRIORITY_SCORE
        ]

        for issue in actionable:
            title = issue.get('title', 'Unknown issue')
            effort = cls._format_effort(issue.get('effort', 'medium'))

            # Format content with effort estimate
            content = f"{title} ({effort})"

            # Create present continuous form for activeForm
            active_form = cls._create_active_form(title)

            todos.append({
                'content': content,
                'status': 'pending',
                'activeForm': active_form
            })

        return todos

    @classmethod
    def create_from_debate(
        cls,
        scored_issues: List[Dict],
        auto_write: bool = False
    ) -> Tuple[List[Dict], bool]:
        """
        Create todos from debate results and optionally write to TodoWrite.

        Args:
            scored_issues: Scored issues from debate
            auto_write: If True, would call TodoWrite tool (placeholder for now)

        Returns:
            (todos_list, success)
            - todos_list: List of todo dicts
            - success: True if todos created successfully

        Note:
            auto_write functionality requires Claude SDK integration.
            For now, this just returns the formatted todos.
            Integration happens at the MCP server level.
        """
        todos = cls.extract_todos(scored_issues)

        # TODO: Implement actual TodoWrite tool call when auto_write=True
        # This would require access to Claude SDK tools instance
        # For now, just return the formatted todos
        # The MCP server or orchestrator will handle actual TodoWrite call

        success = len(todos) > 0

        return (todos, success)

    @staticmethod
    def _format_effort(effort: str) -> str:
        """Format effort as human-readable string."""
        effort_map = {
            'low': '<30 min',
            'medium': '1-4 hours',
            'high': '>4 hours'
        }
        return effort_map.get(effort.lower(), effort)

    @staticmethod
    def _create_active_form(title: str) -> str:
        """
        Convert title to present continuous form for activeForm.

        Examples:
            'Fix race condition' -> 'Fixing race condition'
            'Add row locking' -> 'Adding row locking'
            'Remove duplicate code' -> 'Removing duplicate code'
            'Update documentation' -> 'Updating documentation'
            'Unknown action' -> 'Working on unknown action'

        Args:
            title: Issue title (usually starts with verb)

        Returns:
            Present continuous form (verb + -ing)
        """
        title_lower = title.lower().strip()

        # Common verb patterns
        verb_replacements = [
            ('fix ', 'fixing '),
            ('add ', 'adding '),
            ('remove ', 'removing '),
            ('update ', 'updating '),
            ('create ', 'creating '),
            ('delete ', 'deleting '),
            ('implement ', 'implementing '),
            ('refactor ', 'refactoring '),
            ('improve ', 'improving '),
            ('optimize ', 'optimizing '),
            ('debug ', 'debugging '),
            ('test ', 'testing '),
            ('write ', 'writing '),
            ('read ', 'reading '),
            ('check ', 'checking '),
            ('verify ', 'verifying '),
            ('validate ', 'validating '),
            ('migrate ', 'migrating '),
            ('upgrade ', 'upgrading '),
            ('downgrade ', 'downgrading '),
        ]

        # Try to replace known verb patterns
        for verb, gerund in verb_replacements:
            if title_lower.startswith(verb):
                # Preserve original case for rest of title
                return gerund.capitalize() + title[len(verb):]

        # Default: prepend "Working on"
        return f"Working on {title.lower()}"

    @classmethod
    def format_todos_as_markdown(cls, todos: List[Dict]) -> str:
        """
        Format todos as markdown checklist.

        Useful for displaying todos in decision pack or copying to tasks/todo.md.

        Args:
            todos: List of todo dicts from extract_todos()

        Returns:
            Markdown checklist string

        Example:
            >>> todos = [{'content': 'Fix bug (30 min)', 'status': 'pending', 'activeForm': 'Fixing bug'}]
            >>> print(TodoWriter.format_todos_as_markdown(todos))
            - [ ] Fix bug (30 min)
        """
        if not todos:
            return "- [ ] No high-priority action items"

        lines = []
        for todo in todos:
            content = todo['content']
            status = '✅' if todo.get('status') == 'completed' else ' '
            lines.append(f"- [{status}] {content}")

        return '\n'.join(lines)

    @classmethod
    def get_todos_summary(cls, todos: List[Dict]) -> str:
        """
        Get summary string for todos.

        Args:
            todos: List of todo dicts

        Returns:
            Summary string like "8 action items (3 critical, 5 high)"

        Example:
            >>> todos = [{'content': 'Item 1', 'status': 'pending', 'activeForm': '...'}] * 5
            >>> TodoWriter.get_todos_summary(todos)
            '5 action items'
        """
        count = len(todos)

        if count == 0:
            return "No high-priority action items"
        elif count == 1:
            return "1 action item"
        else:
            return f"{count} action items"
