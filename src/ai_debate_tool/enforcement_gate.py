"""Enforcement gate for AI debate consensus.

Blocks code execution until consensus is reached or user explicitly overrides.
"""

from pathlib import Path
from typing import Dict, List, Optional

from .config import load_config
from .file_protocol import read_metadata


def check_debate_required(request: str, file_paths: Optional[List[str]] = None) -> Dict:
    """Determine if a code change requires AI debate.

    Phase 0: Placeholder logic (always returns required=True for testing).
    Phase 1: Will implement full complexity scoring algorithm.

    Args:
        request: User's implementation request
        file_paths: List of files to be modified (optional)

    Returns:
        Dictionary with:
            - required (bool): True if debate needed
            - complexity_score (int): 0-100 complexity score
            - reason (str): Explanation of decision

    Example:
        >>> result = check_debate_required("Fix typo in README")
        >>> result["required"]
        False
        >>> result["complexity_score"] < 40
        True

        >>> result = check_debate_required("Refactor authentication to use JWT")
        >>> result["required"]
        True
        >>> result["complexity_score"] >= 40
        True
    """
    config = load_config()

    # Check if debate system is enabled
    if not config.enabled:
        return {
            "required": False,
            "complexity_score": 0,
            "reason": "AI debate system is disabled",
        }

    # Phase 0: Placeholder complexity scoring
    # Simple heuristic based on keywords and file count
    complexity_score = _calculate_placeholder_complexity(request, file_paths or [])

    # Check threshold
    required = complexity_score >= config.complexity_threshold

    if required:
        reason = f"Complexity score {complexity_score} >= threshold {config.complexity_threshold}"
    else:
        reason = f"Complexity score {complexity_score} < threshold {config.complexity_threshold}"

    return {
        "required": required,
        "complexity_score": complexity_score,
        "reason": reason,
    }


def _calculate_placeholder_complexity(request: str, file_paths: List[str]) -> int:
    """Placeholder complexity scoring for Phase 0.

    Phase 1 will replace this with multi-factor algorithm.

    Args:
        request: User's implementation request
        file_paths: List of files to be modified

    Returns:
        Complexity score (0-100)
    """
    score = 0

    # Factor 1: File count (max 20 points)
    file_count = len(file_paths)
    if file_count == 0:
        score += 5
    elif file_count == 1:
        score += 10
    elif file_count <= 3:
        score += 15
    else:
        score += 20

    # Factor 2: Architectural keywords (max 50 points)
    architectural_keywords = [
        "refactor",
        "redesign",
        "migrate",
        "architecture",
        "authentication",
        "authorization",
        "security",
        "database",
        "api",
        "schema",
        "jwt",
        "token",
        "caching",
        "cache",
        "workflow",
        "approval",
        "integration",
        "service",
        "infrastructure",
        "deployment",
    ]
    request_lower = request.lower()
    keyword_matches = sum(1 for kw in architectural_keywords if kw in request_lower)
    score += min(keyword_matches * 12, 50)

    # Factor 3: Scope indicators and feature additions (max 25 points)
    scope_keywords = ["system-wide", "all", "entire", "multiple", "cross-cutting", "implement", "new feature", "add new"]
    scope_matches = sum(1 for kw in scope_keywords if kw in request_lower)
    score += min(scope_matches * 12, 25)

    # Bonus for "add" + architectural term combinations (e.g., "add caching layer")
    if "add " in request_lower:
        for kw in architectural_keywords:
            if kw in request_lower:
                score += 5
                break

    # Factor 4: Simple change indicators (reduce score)
    simple_keywords = ["typo", "fix", "comment", "documentation", "readme"]
    simple_matches = sum(1 for kw in simple_keywords if kw in request_lower)
    if simple_matches > 0:
        score = max(0, score - 30)

    return min(score, 100)


def block_execution_until_consensus(session_id: str, session_dir: Optional[Path] = None) -> Dict:
    """Prevent code execution until consensus is reached or user overrides.

    Checks debate session state and determines if execution should proceed.

    Args:
        session_id: Active debate session UUID
        session_dir: Optional path to session directory (auto-detected if None)

    Returns:
        Dictionary with:
            - can_execute (bool): True if execution allowed
            - consensus_score (int): 0-100 consensus score (or None)
            - user_override (bool): True if user overrode consensus requirement
            - decision_pack (dict): Escalation info (if consensus failed)
            - error (str): Error message if failed

    Example:
        >>> result = block_execution_until_consensus("550e8400-...")
        >>> if result["can_execute"]:
        ...     # Proceed with execution
        ...     pass
        >>> else:
        ...     print(result["decision_pack"])
    """
    try:
        config = load_config()

        # Check if debate system is enabled
        if not config.enabled:
            return {
                "can_execute": True,
                "consensus_score": None,
                "user_override": False,
                "decision_pack": None,
                "error": None,
            }

        # Auto-detect session directory if not provided
        if session_dir is None:
            from .file_protocol import get_hashed_user

            user_hash = get_hashed_user()
            session_dir = config.temp_dir / "ai_debates" / user_hash / session_id

        # Check if session exists
        if not session_dir.exists():
            return {
                "can_execute": False,
                "consensus_score": None,
                "user_override": False,
                "decision_pack": None,
                "error": f"Session not found: {session_id}",
            }

        # Read session metadata
        metadata_result = read_metadata(session_dir)
        if not metadata_result["success"]:
            return {
                "can_execute": False,
                "consensus_score": None,
                "user_override": False,
                "decision_pack": None,
                "error": metadata_result["error"],
            }

        metadata = metadata_result["metadata"]
        state = metadata.get("state", "IDLE")
        consensus_score = metadata.get("consensus_score")
        user_override = metadata.get("user_override", False)

        # Check state
        if state == "CONSENSUS":
            # Consensus reached - allow execution
            return {
                "can_execute": True,
                "consensus_score": consensus_score,
                "user_override": False,
                "decision_pack": None,
                "error": None,
            }

        elif state == "ESCALATION" and user_override:
            # User explicitly overrode - allow execution
            return {
                "can_execute": True,
                "consensus_score": consensus_score,
                "user_override": True,
                "decision_pack": None,
                "error": None,
            }

        elif state == "ESCALATION":
            # Consensus failed - block execution, return decision pack
            decision_pack = _generate_decision_pack(metadata, session_dir)
            return {
                "can_execute": False,
                "consensus_score": consensus_score,
                "user_override": False,
                "decision_pack": decision_pack,
                "error": None,
            }

        else:
            # Still debating or in other state - block execution
            return {
                "can_execute": False,
                "consensus_score": consensus_score,
                "user_override": False,
                "decision_pack": {
                    "summary": f"Debate in progress (state: {state})",
                    "current_round": metadata.get("current_round", 0),
                    "max_rounds": metadata.get("max_rounds", 5),
                },
                "error": None,
            }

    except Exception as e:
        return {
            "can_execute": False,
            "consensus_score": None,
            "user_override": False,
            "decision_pack": None,
            "error": f"Failed to check consensus: {e}",
        }


def _generate_decision_pack(metadata: Dict, session_dir: Path) -> Dict:
    """Generate decision pack for user escalation.

    Phase 0: Basic decision pack with placeholder data.
    Phase 6: Will implement full comparison table and analysis.

    Args:
        metadata: Session metadata
        session_dir: Path to session directory

    Returns:
        Decision pack dictionary
    """
    from .file_protocol import read_proposal

    # Read proposals (if available)
    claude_proposal = read_proposal(session_dir, "claude", metadata.get("current_round", 1))
    codex_proposal = read_proposal(session_dir, "codex", metadata.get("current_round", 1))

    decision_pack = {
        "summary": "AIs could not reach consensus",
        "rounds": metadata.get("current_round", 0),
        "consensus_score": metadata.get("consensus_score", 0),
        "request": metadata.get("request", ""),
        # Proposals
        "claude_approach": claude_proposal.get("content", "Not available") if claude_proposal["success"] else "Not available",
        "codex_approach": codex_proposal.get("content", "Not available") if codex_proposal["success"] else "Not available",
        # Placeholder for Phase 6
        "comparison_table": None,
        "moderator_recommendation": None,
        "key_differences": None,
    }

    return decision_pack


def mark_user_override(session_id: str, session_dir: Optional[Path] = None) -> Dict:
    """Mark session as user-overridden.

    Allows execution to proceed despite lack of consensus.

    Args:
        session_id: Active debate session UUID
        session_dir: Optional path to session directory

    Returns:
        Dictionary with:
            - success (bool): True if override recorded
            - error (str): Error message if failed

    Example:
        >>> result = mark_user_override("550e8400-...")
        >>> result["success"]
        True
    """
    try:
        config = load_config()

        # Auto-detect session directory
        if session_dir is None:
            from .file_protocol import get_hashed_user

            user_hash = get_hashed_user()
            session_dir = config.temp_dir / "ai_debates" / user_hash / session_id

        # Read metadata
        metadata_result = read_metadata(session_dir)
        if not metadata_result["success"]:
            return {"success": False, "error": metadata_result["error"]}

        metadata = metadata_result["metadata"]

        # Set user override flag
        metadata["user_override"] = True
        metadata["outcome"] = "user_override"

        # Write metadata
        from .file_protocol import write_metadata

        write_result = write_metadata(session_dir, metadata)

        return write_result

    except Exception as e:
        return {"success": False, "error": f"Failed to mark override: {e}"}
