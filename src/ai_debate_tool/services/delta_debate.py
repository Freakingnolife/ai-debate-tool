"""
Delta Debate - Incremental debate mode for quick refinements.

Instead of re-debating entire plan (30-60 seconds), debate only changes (5-10 seconds):
1. Detect what changed since last debate
2. Re-debate only changed sections
3. Verify resolved issues are actually fixed
4. Merge with previous debate results

Use case: User makes changes based on debate feedback, wants quick re-check.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class DeltaDebate:
    """Incremental debate mode for quick refinements."""

    def __init__(self, history_dir: Optional[Path] = None):
        """
        Initialize delta debate tracker.

        Args:
            history_dir: Directory for debate history (default: .cache/debate_history)
        """
        if history_dir is None:
            history_dir = Path(__file__).parent.parent / '.cache' / 'debate_history'

        self.history_dir = history_dir
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def detect_changes(
        self,
        file_path: str,
        previous_debate_id: Optional[str] = None
    ) -> Dict:
        """
        Detect what changed since last debate.

        Args:
            file_path: Path to file
            previous_debate_id: Optional ID of previous debate
                               (if None, finds latest debate for this file)

        Returns:
            {
                'has_changes': bool,
                'change_summary': str,
                'changed_sections': list[dict],
                'previous_content_hash': str,
                'current_content_hash': str,
                'previous_debate': dict (or None if not found)
            }
        """
        # Read current content
        with open(file_path, 'r', encoding='utf-8') as f:
            current_content = f.read()

        current_hash = self._hash_content(current_content)

        # Find previous debate
        previous_debate = self._load_previous_debate(file_path, previous_debate_id)

        if not previous_debate:
            return {
                'has_changes': True,  # No previous debate = treat as new
                'change_summary': 'No previous debate found - treat as initial debate',
                'changed_sections': [],
                'previous_content_hash': None,
                'current_content_hash': current_hash,
                'previous_debate': None
            }

        previous_hash = previous_debate.get('content_hash')

        # Check if content changed
        if current_hash == previous_hash:
            return {
                'has_changes': False,
                'change_summary': 'No changes since last debate',
                'changed_sections': [],
                'previous_content_hash': previous_hash,
                'current_content_hash': current_hash,
                'previous_debate': previous_debate
            }

        # Detect specific changes (line-level diff)
        previous_content = previous_debate.get('content', '')
        changed_sections = self._detect_changed_sections(
            previous_content,
            current_content
        )

        change_summary = self._summarize_changes(changed_sections)

        return {
            'has_changes': True,
            'change_summary': change_summary,
            'changed_sections': changed_sections,
            'previous_content_hash': previous_hash,
            'current_content_hash': current_hash,
            'previous_debate': previous_debate
        }

    def should_use_delta_mode(self, change_info: Dict) -> bool:
        """
        Determine if delta debate mode should be used.

        Args:
            change_info: Result from detect_changes()

        Returns:
            True if delta mode is appropriate, False for full debate
        """
        if not change_info['has_changes']:
            return False  # No changes, no need to debate

        if not change_info['previous_debate']:
            return False  # No previous debate, must do full debate

        # Delta mode appropriate if changes are small (< 30% of file)
        if change_info['changed_sections']:
            total_lines_changed = sum(
                section['end_line'] - section['start_line'] + 1
                for section in change_info['changed_sections']
            )

            # Get file size
            previous_lines = len(change_info['previous_debate'].get('content', '').split('\n'))

            if previous_lines == 0:
                return False

            change_percentage = (total_lines_changed / previous_lines) * 100

            return change_percentage < 30  # Use delta if < 30% changed

        return True  # Default to delta if we have previous debate

    def create_delta_prompt(
        self,
        change_info: Dict,
        original_request: str
    ) -> str:
        """
        Create focused prompt for delta debate (changed sections only).

        Args:
            change_info: Result from detect_changes()
            original_request: Original debate request

        Returns:
            Delta-focused prompt
        """
        changed_sections_text = "\n\n".join([
            f"[Lines {section['start_line']}-{section['end_line']}]\n{section['content']}"
            for section in change_info['changed_sections']
        ])

        previous_issues = change_info['previous_debate'].get('issues', [])
        previous_issues_text = "\n".join([
            f"- {issue.get('title', 'Unknown issue')}"
            for issue in previous_issues[:5]
        ])

        prompt = f"""This is a DELTA DEBATE (incremental review of changes only).

ORIGINAL REQUEST:
{original_request}

CHANGE SUMMARY:
{change_info['change_summary']}

CHANGED SECTIONS:
{changed_sections_text}

PREVIOUS ISSUES IDENTIFIED:
{previous_issues_text}

Your task:
1. Review ONLY the changed sections (don't re-review unchanged parts)
2. Check if previous issues were addressed in changes
3. Identify any NEW issues introduced by changes
4. Give quick recommendation (approve changes / needs more work)

Focus on incremental analysis, not full re-review.
"""
        return prompt

    def verify_resolved_issues(
        self,
        change_info: Dict,
        current_content: str
    ) -> List[Dict]:
        """
        Check which previous issues were resolved by changes.

        Args:
            change_info: Result from detect_changes()
            current_content: Current file content

        Returns:
            List of issues with resolution status:
            [
                {
                    'issue': dict (original issue),
                    'resolved': bool,
                    'evidence': str (why we think it's resolved/not)
                },
                ...
            ]
        """
        previous_issues = change_info['previous_debate'].get('issues', [])
        verification = []

        current_lower = current_content.lower()

        for issue in previous_issues:
            title = issue.get('title', '').lower()
            fix = issue.get('fix', '').lower()

            # Simple heuristic: check if fix keywords appear in changed content
            changed_content = " ".join([
                section['content']
                for section in change_info['changed_sections']
            ]).lower()

            # Extract keywords from fix description
            fix_keywords = self._extract_keywords(fix)

            resolved = any(keyword in changed_content for keyword in fix_keywords)

            evidence = (
                f"Found fix keywords ({', '.join(fix_keywords)}) in changed sections"
                if resolved
                else f"Fix keywords not found in changes"
            )

            verification.append({
                'issue': issue,
                'resolved': resolved,
                'evidence': evidence
            })

        return verification

    def save_debate_result(
        self,
        file_path: str,
        debate_result: Dict,
        content: str,
        is_delta: bool = False
    ) -> str:
        """
        Save debate result to history.

        Args:
            file_path: Path to debated file
            debate_result: Debate results
            content: File content at time of debate
            is_delta: Whether this was delta debate

        Returns:
            Debate ID (for future delta debates)
        """
        debate_id = self._generate_debate_id(file_path)

        history_entry = {
            'debate_id': debate_id,
            'file_path': file_path,
            'timestamp': datetime.now().isoformat(),
            'content': content,
            'content_hash': self._hash_content(content),
            'debate_result': debate_result,
            'is_delta': is_delta
        }

        history_file = self.history_dir / f"{debate_id}.json"

        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_entry, f, indent=2, ensure_ascii=False)

        return debate_id

    def _load_previous_debate(
        self,
        file_path: str,
        debate_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Load previous debate for file.

        Args:
            file_path: Path to file
            debate_id: Optional specific debate ID (else finds latest)

        Returns:
            Previous debate dict or None
        """
        if debate_id:
            # Load specific debate
            history_file = self.history_dir / f"{debate_id}.json"
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None

        # Find latest debate for this file
        file_debates = []

        for history_file in self.history_dir.glob("*.json"):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    debate = json.load(f)
                    if debate.get('file_path') == file_path:
                        file_debates.append(debate)
            except Exception:
                continue

        if not file_debates:
            return None

        # Return most recent
        file_debates.sort(key=lambda d: d.get('timestamp', ''), reverse=True)
        return file_debates[0]

    def _detect_changed_sections(
        self,
        previous_content: str,
        current_content: str
    ) -> List[Dict]:
        """
        Detect which sections changed (simple line-level diff).

        Args:
            previous_content: Previous file content
            current_content: Current file content

        Returns:
            List of changed sections
        """
        prev_lines = previous_content.split('\n')
        curr_lines = current_content.split('\n')

        changed_sections = []
        i = 0

        while i < len(curr_lines):
            # Check if this line exists in previous content at same position
            if i >= len(prev_lines) or curr_lines[i] != prev_lines[i]:
                # Found change - collect consecutive changed lines
                start_line = i + 1  # 1-indexed
                changed_lines = []

                while i < len(curr_lines) and (
                    i >= len(prev_lines) or curr_lines[i] != prev_lines[i]
                ):
                    changed_lines.append(curr_lines[i])
                    i += 1

                end_line = i  # 1-indexed

                changed_sections.append({
                    'start_line': start_line,
                    'end_line': end_line,
                    'content': '\n'.join(changed_lines)
                })
            else:
                i += 1

        return changed_sections

    def _summarize_changes(self, changed_sections: List[Dict]) -> str:
        """
        Summarize changes in human-readable format.

        Args:
            changed_sections: List of changed sections

        Returns:
            Summary string
        """
        if not changed_sections:
            return "No changes detected"

        total_lines = sum(
            section['end_line'] - section['start_line'] + 1
            for section in changed_sections
        )

        return f"{len(changed_sections)} section(s) changed ({total_lines} lines total)"

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text for issue matching.

        Args:
            text: Text to extract keywords from

        Returns:
            List of keywords
        """
        # Simple keyword extraction (words > 4 chars, excluding common words)
        common_words = {'the', 'this', 'that', 'with', 'from', 'have', 'need', 'should', 'would', 'could'}

        words = text.lower().split()
        keywords = [
            word.strip('.,!?;:')
            for word in words
            if len(word) > 4 and word.lower() not in common_words
        ]

        return keywords[:5]  # Top 5 keywords

    def _hash_content(self, content: str) -> str:
        """
        Hash file content for change detection.

        Args:
            content: File content

        Returns:
            MD5 hash (16 chars)
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]

    def _generate_debate_id(self, file_path: str) -> str:
        """
        Generate unique debate ID.

        Args:
            file_path: Path to file

        Returns:
            Debate ID (timestamp + file hash)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(file_path.encode('utf-8')).hexdigest()[:8]
        return f"{timestamp}_{file_hash}"
