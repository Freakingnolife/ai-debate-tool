"""File protocol for AI-to-AI communication.

Provides secure, cross-platform file-based communication for debate sessions.
Handles session directories, proposals, metadata, and cleanup.
"""

import hashlib
import json
import os
import getpass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from filelock import FileLock

from .config import load_config


def get_hashed_user() -> str:
    """Get stable hashed user identifier.

    Uses SHA-256 hash of username for privacy and stability.
    Handles os.getlogin() failures gracefully (common on macOS).

    Returns:
        8-character hex string (first 8 chars of SHA-256 hash)

    Example:
        >>> user_hash = get_hashed_user()
        >>> len(user_hash)
        8
        >>> user_hash.isalnum()
        True
    """
    try:
        username = os.getlogin()
    except OSError:
        # Fallback for macOS terminals, SSH sessions, etc.
        username = getpass.getuser()

    return hashlib.sha256(username.encode()).hexdigest()[:8]


def create_session_directory(session_id: str) -> Dict:
    """Initialize file system structure for a debate session.

    Creates directory structure:
        <temp>/ai_debates/<user_hash>/<session_id>/
        ├── session_metadata.json
        ├── .sequence (initialized to 0)
        ├── locks/
        ├── claude/
        ├── codex/
        ├── moderator/
        └── artifacts/

    Args:
        session_id: UUID string for the session

    Returns:
        Dictionary with:
            - success (bool): True if created successfully
            - path (str): Absolute path to session directory
            - error (str): Error message if failed

    Example:
        >>> result = create_session_directory("550e8400-e29b-41d4-a716-446655440000")
        >>> result["success"]
        True
        >>> Path(result["path"]).exists()
        True
    """
    try:
        config = load_config()

        # Path sanitization - reject directory traversal
        session_id_clean = os.path.basename(session_id)
        if ".." in session_id or session_id != session_id_clean:
            return {
                "success": False,
                "path": "",
                "error": "Invalid session_id: directory traversal not allowed",
            }

        # Construct path: <temp>/ai_debates/<user_hash>/<session_id>/
        user_hash = get_hashed_user()
        session_dir = config.temp_dir / "ai_debates" / user_hash / session_id

        # Create directory structure
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "locks").mkdir(exist_ok=True)
        (session_dir / "claude").mkdir(exist_ok=True)
        (session_dir / "codex").mkdir(exist_ok=True)
        (session_dir / "moderator").mkdir(exist_ok=True)
        (session_dir / "artifacts" / "code_samples").mkdir(parents=True, exist_ok=True)
        (session_dir / "artifacts" / "diagrams").mkdir(exist_ok=True)
        (session_dir / "artifacts" / "references").mkdir(exist_ok=True)

        # Initialize .sequence file to 0
        seq_file = session_dir / ".sequence"
        if not seq_file.exists():
            seq_file.write_text("0")

        # Initialize session_metadata.json
        metadata = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "state": "IDLE",
            "current_round": 0,
        }
        (session_dir / "session_metadata.json").write_text(json.dumps(metadata, indent=2))

        return {"success": True, "path": str(session_dir), "error": None}

    except Exception as e:
        return {"success": False, "path": "", "error": f"Failed to create session directory: {e}"}


def get_next_sequence(session_dir: Path) -> int:
    """Get next sequence number atomically.

    Uses file locking to ensure thread-safe increment.
    Handles missing .sequence file gracefully.

    Args:
        session_dir: Path to session directory

    Returns:
        Next sequence number (starting from 1)

    Example:
        >>> session_dir = Path("/tmp/ai_debates/abc123/session1")
        >>> seq1 = get_next_sequence(session_dir)
        >>> seq2 = get_next_sequence(session_dir)
        >>> seq2 == seq1 + 1
        True
    """
    seq_file = session_dir / ".sequence"
    lock_file = session_dir / ".sequence.lock"

    config = load_config()
    with FileLock(lock_file, timeout=config.lock_timeout):
        # Handle missing .sequence file (initialize to 0)
        try:
            current = int(seq_file.read_text().strip())
        except (FileNotFoundError, ValueError):
            current = 0

        next_seq = current + 1
        seq_file.write_text(str(next_seq))
        return next_seq


def write_proposal(
    session_dir: Path, ai_name: str, round_num: int, content: str
) -> Dict:
    """Write AI proposal to file with fine-grained locking.

    Args:
        session_dir: Path to session directory
        ai_name: "claude" or "codex"
        round_num: Round number (1-5)
        content: Proposal text (markdown)

    Returns:
        Dictionary with:
            - success (bool): True if written successfully
            - file_path (str): Path to written file
            - sequence (int): Sequence number used
            - error (str): Error message if failed

    Example:
        >>> result = write_proposal(
        ...     session_dir=Path("/tmp/ai_debates/abc/session1"),
        ...     ai_name="claude",
        ...     round_num=1,
        ...     content="# Proposal\\nUse SimpleJWT..."
        ... )
        >>> result["success"]
        True
    """
    try:
        # Validate ai_name
        if ai_name not in ("claude", "codex"):
            return {
                "success": False,
                "file_path": "",
                "sequence": 0,
                "error": f"Invalid ai_name: {ai_name}. Must be 'claude' or 'codex'",
            }

        # Get next sequence number (atomic)
        sequence = get_next_sequence(session_dir)

        # Construct filename: {ai_name}/round_{round_num}_seq_{seq:03d}.md
        filename = f"round_{round_num}_seq_{sequence:03d}.md"
        file_path = session_dir / ai_name / filename

        # Acquire per-file lock
        lock_file = session_dir / "locks" / f".{ai_name}_round_{round_num}.lock"
        config = load_config()

        with FileLock(lock_file, timeout=config.lock_timeout):
            # Write content
            file_path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "file_path": str(file_path),
            "sequence": sequence,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "file_path": "",
            "sequence": 0,
            "error": f"Failed to write proposal: {e}",
        }


def read_proposal(session_dir: Path, ai_name: str, round_num: int) -> Dict:
    """Read AI proposal from file.

    Finds the latest proposal file for the given AI and round.

    Args:
        session_dir: Path to session directory
        ai_name: "claude" or "codex"
        round_num: Round number (1-5)

    Returns:
        Dictionary with:
            - success (bool): True if read successfully
            - content (str): Proposal text (markdown)
            - file_path (str): Path to file read
            - error (str): Error message if failed

    Example:
        >>> result = read_proposal(
        ...     session_dir=Path("/tmp/ai_debates/abc/session1"),
        ...     ai_name="claude",
        ...     round_num=1
        ... )
        >>> result["success"]
        True
    """
    try:
        # Validate ai_name
        if ai_name not in ("claude", "codex"):
            return {
                "success": False,
                "content": "",
                "file_path": "",
                "error": f"Invalid ai_name: {ai_name}. Must be 'claude' or 'codex'",
            }

        # Find latest file: {ai_name}/round_{round_num}_seq_*.md (max sequence)
        ai_dir = session_dir / ai_name
        pattern = f"round_{round_num}_seq_*.md"
        matching_files = sorted(ai_dir.glob(pattern))

        if not matching_files:
            return {
                "success": False,
                "content": "",
                "file_path": "",
                "error": f"No proposal found for {ai_name} round {round_num}",
            }

        # Read latest file (highest sequence number)
        latest_file = matching_files[-1]
        content = latest_file.read_text(encoding="utf-8")

        return {
            "success": True,
            "content": content,
            "file_path": str(latest_file),
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "content": "",
            "file_path": "",
            "error": f"Failed to read proposal: {e}",
        }


def write_metadata(session_dir: Path, metadata: Dict) -> Dict:
    """Write session metadata to file.

    Args:
        session_dir: Path to session directory
        metadata: Metadata dictionary to write

    Returns:
        Dictionary with:
            - success (bool): True if written successfully
            - error (str): Error message if failed

    Example:
        >>> metadata = {"session_id": "123", "state": "ROUND_1"}
        >>> result = write_metadata(Path("/tmp/session"), metadata)
        >>> result["success"]
        True
    """
    try:
        # Update timestamp
        metadata["updated_at"] = datetime.now().isoformat()

        # Write to file
        metadata_file = session_dir / "session_metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return {"success": True, "error": None}

    except Exception as e:
        return {"success": False, "error": f"Failed to write metadata: {e}"}


def read_metadata(session_dir: Path) -> Dict:
    """Read session metadata from file.

    Args:
        session_dir: Path to session directory

    Returns:
        Dictionary with:
            - success (bool): True if read successfully
            - metadata (dict): Session metadata
            - error (str): Error message if failed

    Example:
        >>> result = read_metadata(Path("/tmp/session"))
        >>> result["success"]
        True
        >>> "session_id" in result["metadata"]
        True
    """
    try:
        metadata_file = session_dir / "session_metadata.json"

        if not metadata_file.exists():
            return {
                "success": False,
                "metadata": {},
                "error": "Metadata file not found",
            }

        content = metadata_file.read_text(encoding="utf-8")
        metadata = json.loads(content)

        return {"success": True, "metadata": metadata, "error": None}

    except Exception as e:
        return {
            "success": False,
            "metadata": {},
            "error": f"Failed to read metadata: {e}",
        }


def cleanup_old_sessions(max_age_days: Optional[int] = None) -> Dict:
    """Delete old session directories.

    Args:
        max_age_days: Delete sessions older than N days (default from config)

    Returns:
        Dictionary with:
            - success (bool): True if cleanup completed
            - deleted_count (int): Number of sessions deleted
            - error (str): Error message if failed

    Example:
        >>> result = cleanup_old_sessions(max_age_days=7)
        >>> result["success"]
        True
        >>> result["deleted_count"] >= 0
        True
    """
    try:
        config = load_config()
        if max_age_days is None:
            max_age_days = config.cleanup_days

        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        deleted_count = 0

        # Scan <temp>/ai_debates/<user_hash>/
        user_hash = get_hashed_user()
        base_dir = config.temp_dir / "ai_debates" / user_hash

        if not base_dir.exists():
            return {"success": True, "deleted_count": 0, "error": None}

        # Check each session directory
        for session_dir in base_dir.iterdir():
            if not session_dir.is_dir():
                continue

            # Read metadata to get created_at
            metadata_result = read_metadata(session_dir)
            if not metadata_result["success"]:
                continue

            metadata = metadata_result["metadata"]
            created_at_str = metadata.get("created_at")
            if not created_at_str:
                continue

            # Parse created_at timestamp
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except ValueError:
                continue

            # Delete if older than cutoff
            if created_at < cutoff_date:
                import shutil

                shutil.rmtree(session_dir)
                deleted_count += 1

        return {"success": True, "deleted_count": deleted_count, "error": None}

    except Exception as e:
        return {
            "success": False,
            "deleted_count": 0,
            "error": f"Failed to cleanup sessions: {e}",
        }
