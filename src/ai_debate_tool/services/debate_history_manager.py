"""
Debate History Manager - Storage and retrieval for debate records.

Manages persistent storage of debate results for learning and analysis:
1. Save debate results to disk
2. Index debates for fast retrieval
3. Query debates by patterns, files, dates
4. Maintain debate statistics

Storage: .cache/debate_history/ (file-based, no database required)
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class DebateHistoryManager:
    """Manage debate history storage and retrieval."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize history manager.

        Args:
            cache_dir: Directory for debate history (default: .cache/debate_history)
        """
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / '.cache' / 'debate_history'

        self.cache_dir = cache_dir
        self.debates_dir = cache_dir / 'debates'
        self.patterns_dir = cache_dir / 'patterns'
        self.metadata_dir = cache_dir / 'metadata'

        # Create directories
        self.debates_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def save_debate(
        self,
        request: str,
        file_path: str,
        debate_result: Dict,
        performance_stats: Dict,
        focus_areas: List[str]
    ) -> str:
        """
        Save debate to history.

        Args:
            request: User's debate request
            file_path: Path to debated file
            debate_result: Debate results (Phase 1 format)
            performance_stats: Performance statistics
            focus_areas: Focus areas used

        Returns:
            Debate ID (for future reference)
        """
        # Generate debate ID
        debate_id = self._generate_debate_id()

        # Read file content for hashing
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()

        file_hash = self._hash_content(file_content)

        # Create debate record
        debate_record = {
            'debate_id': debate_id,
            'timestamp': datetime.now().isoformat(),
            'file_path': file_path,
            'file_hash': file_hash,
            'file_size': len(file_content),
            'request': request,
            'focus_areas': focus_areas,
            'consensus_score': debate_result.get('consensus_score', 0),
            'interpretation': debate_result.get('interpretation', ''),
            'recommendation': debate_result.get('recommendation', ''),
            'score_difference': debate_result.get('score_difference', 0),
            'claude_score': debate_result.get('claude', {}).get('score', 0),
            'codex_score': debate_result.get('codex', {}).get('score', 0),
            'disagreements': debate_result.get('disagreements', []),
            'agreements': debate_result.get('agreements', []),
            'performance_stats': performance_stats,
            'patterns_detected': [],  # Filled by Pattern Detector (Phase 3.1)
            'outcome': 'pending',  # Updated later: succeeded, failed, abandoned
            'outcome_notes': None
        }

        # Save to file
        debate_file = self.debates_dir / f'{debate_id}.json'
        with open(debate_file, 'w', encoding='utf-8') as f:
            json.dump(debate_record, f, indent=2, ensure_ascii=False)

        # Update index
        self._update_index(debate_record)

        return debate_id

    def get_debate(self, debate_id: str) -> Optional[Dict]:
        """
        Retrieve debate by ID.

        Args:
            debate_id: Debate ID

        Returns:
            Debate record or None if not found
        """
        debate_file = self.debates_dir / f'{debate_id}.json'

        if not debate_file.exists():
            return None

        with open(debate_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def query_debates(
        self,
        file_path: Optional[str] = None,
        pattern: Optional[str] = None,
        min_consensus: Optional[int] = None,
        max_consensus: Optional[int] = None,
        since_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Query debates by criteria.

        Args:
            file_path: Filter by file path (exact match)
            pattern: Filter by pattern name
            min_consensus: Minimum consensus score
            max_consensus: Maximum consensus score
            since_date: Only debates after this date
            limit: Maximum results to return

        Returns:
            List of debate records matching criteria
        """
        results = []

        # Load index for faster filtering
        index = self._load_index()

        for debate_id in index.get('all_debates', []):
            debate = self.get_debate(debate_id)

            if debate is None:
                continue

            # Apply filters
            if file_path and debate.get('file_path') != file_path:
                continue

            if pattern and pattern not in debate.get('patterns_detected', []):
                continue

            if min_consensus and debate.get('consensus_score', 0) < min_consensus:
                continue

            if max_consensus and debate.get('consensus_score', 0) > max_consensus:
                continue

            if since_date:
                debate_date = datetime.fromisoformat(debate.get('timestamp', ''))
                if debate_date < since_date:
                    continue

            results.append(debate)

            if len(results) >= limit:
                break

        # Sort by timestamp (newest first)
        results.sort(key=lambda d: d.get('timestamp', ''), reverse=True)

        return results

    def get_recent_debates(self, days: int = 30, limit: int = 100) -> List[Dict]:
        """
        Get recent debates within specified days.

        Args:
            days: Number of days to look back
            limit: Maximum results

        Returns:
            List of recent debate records
        """
        since_date = datetime.now() - timedelta(days=days)
        return self.query_debates(since_date=since_date, limit=limit)

    def get_debates_by_file(self, file_path: str, limit: int = 10) -> List[Dict]:
        """
        Get all debates for a specific file.

        Args:
            file_path: Path to file
            limit: Maximum results

        Returns:
            List of debate records for this file
        """
        return self.query_debates(file_path=file_path, limit=limit)

    def update_debate_outcome(
        self,
        debate_id: str,
        outcome: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update debate outcome after implementation.

        Args:
            debate_id: Debate ID
            outcome: Outcome status ('succeeded', 'failed', 'abandoned')
            notes: Optional notes about outcome

        Returns:
            True if updated successfully
        """
        debate = self.get_debate(debate_id)

        if debate is None:
            return False

        # Update outcome
        debate['outcome'] = outcome
        debate['outcome_notes'] = notes
        debate['outcome_timestamp'] = datetime.now().isoformat()

        # Save updated debate
        debate_file = self.debates_dir / f'{debate_id}.json'
        with open(debate_file, 'w', encoding='utf-8') as f:
            json.dump(debate, f, indent=2, ensure_ascii=False)

        return True

    def get_statistics(self) -> Dict:
        """
        Get aggregate statistics across all debates.

        Returns:
            Statistics dictionary
        """
        index = self._load_index()

        total_debates = len(index.get('all_debates', []))

        if total_debates == 0:
            return {
                'total_debates': 0,
                'avg_consensus': 0,
                'avg_time': 0,
                'outcome_breakdown': {},
                'pattern_frequency': {}
            }

        # Calculate statistics
        all_debates = [self.get_debate(debate_id) for debate_id in index.get('all_debates', [])]
        all_debates = [d for d in all_debates if d is not None]

        total_consensus = sum(d.get('consensus_score', 0) for d in all_debates)
        avg_consensus = total_consensus / len(all_debates) if all_debates else 0

        total_time = sum(d.get('performance_stats', {}).get('total_time', 0) for d in all_debates)
        avg_time = total_time / len(all_debates) if all_debates else 0

        # Outcome breakdown
        outcome_breakdown = {}
        for debate in all_debates:
            outcome = debate.get('outcome', 'pending')
            outcome_breakdown[outcome] = outcome_breakdown.get(outcome, 0) + 1

        # Pattern frequency
        pattern_frequency = {}
        for debate in all_debates:
            for pattern in debate.get('patterns_detected', []):
                pattern_frequency[pattern] = pattern_frequency.get(pattern, 0) + 1

        return {
            'total_debates': total_debates,
            'avg_consensus': round(avg_consensus, 1),
            'avg_time': round(avg_time, 2),
            'outcome_breakdown': outcome_breakdown,
            'pattern_frequency': pattern_frequency
        }

    def _update_index(self, debate_record: Dict):
        """
        Update debate index for fast retrieval.

        Args:
            debate_record: Debate record to index
        """
        index = self._load_index()

        debate_id = debate_record['debate_id']

        # Add to all debates
        if 'all_debates' not in index:
            index['all_debates'] = []

        if debate_id not in index['all_debates']:
            index['all_debates'].append(debate_id)

        # Index by file path
        if 'by_file' not in index:
            index['by_file'] = {}

        file_path = debate_record['file_path']
        if file_path not in index['by_file']:
            index['by_file'][file_path] = []

        if debate_id not in index['by_file'][file_path]:
            index['by_file'][file_path].append(debate_id)

        # Save index
        self._save_index(index)

    def _load_index(self) -> Dict:
        """
        Load debate index.

        Returns:
            Index dictionary
        """
        index_file = self.metadata_dir / 'debate_index.json'

        if not index_file.exists():
            return {
                'all_debates': [],
                'by_file': {},
                'by_pattern': {}
            }

        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_index(self, index: Dict):
        """
        Save debate index.

        Args:
            index: Index dictionary
        """
        index_file = self.metadata_dir / 'debate_index.json'

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def _generate_debate_id(self) -> str:
        """
        Generate unique debate ID.

        Returns:
            Debate ID (timestamp + random hash)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_hash = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]
        return f"{timestamp}_{random_hash}"

    def _hash_content(self, content: str) -> str:
        """
        Hash file content for change detection.

        Args:
            content: File content

        Returns:
            MD5 hash (16 chars)
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
