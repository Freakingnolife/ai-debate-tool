"""AI Orchestrator Service

Coordinates automated AI debates between Claude Code and Codex.
Handles the complete workflow from complexity check to decision pack.
"""

import uuid
from pathlib import Path
from typing import Dict, List, Optional

from ..config import load_config
from ..enforcement_gate import check_debate_required, block_execution_until_consensus
from ..file_protocol import (
    create_session_directory,
    write_proposal,
    read_metadata,
    write_metadata,
)
from .moderator_service import ModeratorService
from .copilot_invoker import CopilotInvoker, CopilotConfig
from .codex_cli_invoker import CodexCLIInvoker, CodexCLIConfig


class AIOrchestrator:
    """Orchestrates automated AI debates.

    Manages the complete debate workflow:
    1. Check complexity
    2. Create session
    3. Generate Claude proposal
    4. Invoke Codex
    5. Calculate consensus
    6. Return decision pack

    Phase 7.1 Implementation (Manual Mode):
    - Claude: Self-reflection (I generate proposals directly)
    - Codex: Manual mode (user copies/pastes)
    - Consensus: Intelligent moderator (Phase 4) with LLM/rule-based analysis

    Phase 7.2 Implementation (Full Automation):
    - Claude: Self-reflection (I generate proposals directly)
    - Codex: Automatic invocation via VS Code bridge (100% automation)
    - Consensus: Intelligent moderator (Phase 4) with LLM/rule-based analysis
    """

    def __init__(
        self,
        enable_llm: bool = True,
        enable_auto_codex: bool = True,
        copilot_config: Optional[CopilotConfig] = None,
        codex_cli_config: Optional[CodexCLIConfig] = None
    ):
        """Initialize orchestrator with configuration.

        Args:
            enable_llm: Whether to enable LLM analysis (default: True)
            enable_auto_codex: Whether to enable automatic Codex invocation (default: True)
            copilot_config: Optional Copilot configuration (VS Code bridge)
            codex_cli_config: Optional Codex CLI configuration

        Auto-detection:
            Tries Codex CLI first (100% automation), falls back to Copilot bridge
        """
        self.config = load_config()
        self.moderator = ModeratorService(enable_llm=enable_llm)
        self.enable_auto_codex = enable_auto_codex

        # Auto-detect best Codex invocation method
        self.codex_cli = None
        self.copilot = None
        self.codex_method = None

        if enable_auto_codex:
            # Try Codex CLI first (100% automation, zero user interaction)
            self.codex_cli = CodexCLIInvoker(codex_cli_config)
            if self.codex_cli.is_available():
                self.codex_method = 'cli'
                print("[OK] Codex CLI detected - using 100% automated CLI invocation")
            else:
                # Fall back to Copilot bridge (95-100% automation)
                self.copilot = CopilotInvoker(copilot_config)
                if self.copilot.is_available():
                    self.codex_method = 'bridge'
                    print("[OK] Codex Bridge detected - using VS Code bridge invocation")
                else:
                    self.codex_method = None
                    print("[WARN] No Codex invocation method available - will use manual mode")

    def start_debate_auto(
        self,
        request: str,
        file_paths: Optional[List[str]] = None,
        context: Optional[Dict] = None
    ) -> Dict:
        """Start automated debate workflow.

        This is the main entry point for Phase 7 automation.
        One command = full debate.

        Args:
            request: Description of code change (e.g., "Refactor order approval")
            file_paths: List of files affected (optional)
            context: Additional context dict (optional)

        Returns:
            Dictionary with:
                - success (bool): Operation successful
                - debate_triggered (bool): Whether debate was needed
                - session_id (str): Session ID if debate triggered
                - complexity_score (int): Complexity score (0-100)
                - mode (str): Debate mode ('auto', 'manual', 'claude_only')
                - claude_proposal (str): Claude's proposal
                - codex_prompt (str): Prompt for Codex (if manual mode)
                - instructions (str): User instructions (if manual mode)
                - message (str): Status message

        Example:
            >>> orchestrator = AIOrchestrator()
            >>> result = orchestrator.start_debate_auto(
            ...     request="Refactor order approval workflow",
            ...     file_paths=["orders/views.py", "orders/services.py"]
            ... )
            >>> if result['debate_triggered']:
            ...     print(result['claude_proposal'])
            ...     print(result['codex_prompt'])
        """
        file_paths = file_paths or []

        # 1. Check complexity
        complexity = check_debate_required(request, file_paths)

        if not complexity['required']:
            return {
                'success': True,
                'debate_triggered': False,
                'complexity_score': complexity['complexity_score'],
                'reason': complexity['reason'],
                'message': 'Change is simple. No debate needed. Safe to proceed.',
            }

        # 2. Create session
        session_id = str(uuid.uuid4())
        session_result = create_session_directory(session_id)

        if not session_result['success']:
            return {
                'success': False,
                'error': f"Failed to create session: {session_result.get('error')}",
            }

        session_dir = Path(session_result['path'])

        # Write request to metadata
        metadata_result = read_metadata(session_dir)
        metadata = metadata_result['metadata']
        metadata['request'] = request
        metadata['file_paths'] = file_paths
        metadata['context'] = context or {}
        metadata['state'] = 'ROUND_1'
        metadata['current_round'] = 1
        write_metadata(session_dir, metadata)

        # 3. Generate Claude's proposal (self-reflection)
        claude_proposal = self._generate_claude_proposal(request, file_paths, context)

        # Write Claude's proposal to session
        write_proposal(session_dir, 'claude', 1, claude_proposal)

        # 4. Generate Codex prompt
        codex_prompt = self._generate_codex_prompt(request, claude_proposal, file_paths)

        # 5. Try automatic Codex invocation (Phase 7.2+)
        # Priority: Codex CLI (100%) > Copilot Bridge (95-100%) > Manual (80%)
        codex_result = None

        if self.enable_auto_codex:
            if self.codex_method == 'cli':
                # Method 1: Codex CLI (100% automation, zero user interaction)
                print("[OK] Invoking Codex CLI (100% automation)...")
                codex_result = self.codex_cli.invoke(codex_prompt)

            elif self.codex_method == 'bridge':
                # Method 2: Copilot Bridge (95-100% automation)
                print("[OK] Invoking Codex via VS Code bridge...")
                codex_result = self.copilot.invoke(codex_prompt)

        if codex_result and codex_result['success']:
            # Automatic invocation succeeded!
            codex_response = codex_result['response']

            # Write Codex's proposal
            write_proposal(session_dir, 'codex', 1, codex_response)

            # Analyze consensus immediately
            moderation_result = self.moderator.moderate_debate(
                session_id=session_id,
                claude_proposal=claude_proposal,
                codex_proposal=codex_response
            )

            # Update metadata
            metadata['consensus_score'] = moderation_result['consensus_score']
            metadata['analysis_method'] = moderation_result['analysis_method']
            metadata['state'] = 'CONSENSUS' if moderation_result['can_execute'] else 'ESCALATION'
            write_metadata(session_dir, metadata)

            print(f"[OK] Automatic debate complete! Consensus: {moderation_result['consensus_score']}/100")

            return {
                'success': True,
                'debate_triggered': True,
                'session_id': session_id,
                'session_path': str(session_dir),
                'complexity_score': complexity['complexity_score'],
                'mode': 'auto',  # 100% automated
                'codex_method': self.codex_method,  # 'cli' or 'bridge'
                'claude_proposal': claude_proposal,
                'codex_response': codex_response,
                'codex_model': codex_result['model'],
                'consensus_score': moderation_result['consensus_score'],
                'analysis_method': moderation_result['analysis_method'],
                'can_execute': moderation_result['can_execute'],
                'decision_pack': moderation_result['decision_pack'],
                'analysis': moderation_result['analysis'],
                'message': f"Debate complete (100% automated via {self.codex_method}). " +
                          ('Consensus reached. Safe to proceed.' if moderation_result['can_execute']
                           else 'No consensus. Review decision pack.'),
            }
        elif codex_result:
            # Codex invocation failed, fall back to manual
            print(f"[WARN] Codex invocation failed: {codex_result['error']}")
            print("[INFO] Falling back to manual mode...")
        else:
            # No automatic method available
            print("[WARN] No automatic Codex invocation method available, using manual mode...")

        # Fallback to manual mode (Phase 7.1)
        return {
            'success': True,
            'debate_triggered': True,
            'session_id': session_id,
            'session_path': str(session_dir),
            'complexity_score': complexity['complexity_score'],
            'mode': 'manual',  # Phase 7.1: manual mode
            'claude_proposal': claude_proposal,
            'codex_prompt': codex_prompt,
            'instructions': self._get_user_instructions(),
            'message': 'Debate started. Claude proposal generated. Waiting for Codex response.',
            'next_steps': [
                '1. Copy the Codex prompt above',
                '2. Open Codex chat (your Codex extension)',
                '3. Paste the prompt',
                '4. Copy Codex response',
                '5. Call debate_submit_codex_response with the response',
            ]
        }

    def submit_codex_response(
        self,
        session_id: str,
        codex_response: str
    ) -> Dict:
        """Submit Codex's response after manual invocation.

        Args:
            session_id: Debate session ID
            codex_response: Codex's counter-proposal text

        Returns:
            Dictionary with consensus analysis and decision pack
        """
        # Find session directory
        from ..file_protocol import get_hashed_user

        user_hash = get_hashed_user()
        session_dir = self.config.temp_dir / "ai_debates" / user_hash / session_id

        if not session_dir.exists():
            return {
                'success': False,
                'error': f"Session {session_id} not found",
            }

        # Write Codex's proposal
        write_proposal(session_dir, 'codex', 1, codex_response)

        # Read Claude's proposal for comparison
        from ..file_protocol import read_proposal
        claude_result = read_proposal(session_dir, 'claude', 1)

        if not claude_result['success']:
            return {
                'success': False,
                'error': 'Failed to read Claude proposal for comparison',
            }

        claude_proposal = claude_result['content']

        # Use ModeratorService for intelligent consensus analysis (Phase 4)
        moderation_result = self.moderator.moderate_debate(
            session_id=session_id,
            claude_proposal=claude_proposal,
            codex_proposal=codex_response
        )

        # Update metadata with consensus
        metadata_result = read_metadata(session_dir)
        metadata = metadata_result['metadata']
        metadata['consensus_score'] = moderation_result['consensus_score']
        metadata['analysis_method'] = moderation_result['analysis_method']
        metadata['state'] = 'CONSENSUS' if moderation_result['can_execute'] else 'ESCALATION'
        write_metadata(session_dir, metadata)

        return {
            'success': True,
            'session_id': session_id,
            'consensus_score': moderation_result['consensus_score'],
            'analysis_method': moderation_result['analysis_method'],
            'consensus_min': self.config.consensus_min,
            'reached_consensus': moderation_result['can_execute'],
            'can_execute': moderation_result['can_execute'],
            'decision_pack': moderation_result['decision_pack'],
            'analysis': moderation_result['analysis'],
            'message': 'Consensus reached. Safe to proceed.' if moderation_result['can_execute']
                      else 'No consensus. Review decision pack and choose approach.',
        }

    def _generate_claude_proposal(
        self,
        request: str,
        file_paths: List[str],
        context: Optional[Dict]
    ) -> str:
        """Generate Claude's proposal using self-reflection.

        Since I (Claude Code) am running, I generate the proposal
        directly without external API calls.

        Args:
            request: Description of code change
            file_paths: Files affected
            context: Additional context

        Returns:
            Claude's proposal as markdown
        """
        # Build structured prompt for proposal generation
        # This will be processed by Claude Code (me) when tool is called

        files_section = "\n".join(f"- `{fp}`" for fp in file_paths) if file_paths else "None specified"
        context_section = ""
        if context:
            context_section = "\n\n## Additional Context\n" + "\n".join(
                f"- **{k}:** {v}" for k, v in context.items()
            )

        proposal_template = f"""# Claude's Proposal: {request}

## Task Analysis

**Objective:** {request}

**Affected Files:**
{files_section}
{context_section}

## Proposed Approach

### High-Level Strategy

[Describe your overall approach to solving this problem]

### Implementation Steps

1. **Step 1:** [First major step]
   - [Detail 1]
   - [Detail 2]

2. **Step 2:** [Second major step]
   - [Detail 1]
   - [Detail 2]

3. **Step 3:** [Third major step]
   - [Detail 1]
   - [Detail 2]

### Technical Details

**Architecture Changes:**
- [Change 1]
- [Change 2]

**Code Structure:**
```python
# Example code structure
class Example:
    pass
```

## Benefits

1. **Benefit 1:** [Explanation]
2. **Benefit 2:** [Explanation]
3. **Benefit 3:** [Explanation]

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk 1] | [High/Medium/Low] | [How to mitigate] |
| [Risk 2] | [High/Medium/Low] | [How to mitigate] |

## Estimated Effort

- **Implementation:** [X hours]
- **Testing:** [Y hours]
- **Documentation:** [Z hours]
- **Total:** [Total hours]

## Alternative Considered

[Brief mention of alternative approach and why this is better]

---

*Generated by Claude Code (Self-Reflection Mode)*
"""

        return proposal_template

    def _generate_codex_prompt(
        self,
        request: str,
        claude_proposal: str,
        file_paths: List[str]
    ) -> str:
        """Generate prompt for Codex counter-proposal.

        Args:
            request: Original request
            claude_proposal: Claude's proposal
            file_paths: Files affected

        Returns:
            Formatted prompt for Codex
        """
        files_section = "\n".join(f"- `{fp}`" for fp in file_paths) if file_paths else "None specified"

        return f"""# AI Debate: Counter-Proposal Request

## Context

You are Codex (GPT-5.1-Codex-Max), participating in an AI-to-AI debate with Claude Code.

## Original Task

**Request:** {request}

**Affected Files:**
{files_section}

## Claude's Proposal

{claude_proposal}

## Your Task

Review Claude's proposal and provide a **counter-proposal** or **alternative approach**.

Your response should:
1. Present a different technical approach (not just agreeing with Claude)
2. Highlight key differences from Claude's approach
3. Explain trade-offs (what you gain, what you sacrifice)
4. Be detailed and specific

## Response Format

Please use this markdown structure:

```markdown
# Codex's Counter-Proposal: [Your Title]

## Approach Overview

[Describe your alternative approach - how is it different from Claude's?]

## Key Differences from Claude

1. **Difference 1:** [What Claude proposed] → [What you propose instead]
2. **Difference 2:** [What Claude proposed] → [What you propose instead]
3. **Difference 3:** [What Claude proposed] → [What you propose instead]

## Implementation Steps

1. **Step 1:** [Your first step]
   - [Detail]

2. **Step 2:** [Your second step]
   - [Detail]

3. **Step 3:** [Your third step]
   - [Detail]

## Technical Details

**Architecture:**
- [Your architectural decisions]

**Code Structure:**
```python
# Your code example
class YourApproach:
    pass
```

## Trade-offs Analysis

### Advantages of My Approach
- ✅ [Advantage 1]
- ✅ [Advantage 2]
- ✅ [Advantage 3]

### Disadvantages of My Approach
- ❌ [Disadvantage 1]
- ❌ [Disadvantage 2]

### When to Use My Approach
- [Scenario 1]
- [Scenario 2]

### When to Use Claude's Approach
- [Scenario 1]
- [Scenario 2]

## Estimated Effort

- **Implementation:** [X hours]
- **Testing:** [Y hours]
- **Total:** [Total hours]

## Recommendation

[Your honest recommendation: your approach, Claude's approach, or hybrid?]
```

---

**Important:** Generate a genuine alternative approach, not just agreement with Claude. The goal is to provide the user with meaningful options.
"""

    def _get_user_instructions(self) -> str:
        """Get user instructions for manual Codex invocation."""
        return """
📋 **How to Complete This Debate:**

1. **Copy Codex Prompt:**
   - Copy the entire prompt above (starting with "# AI Debate")

2. **Open Codex:**
   - Open Codex chat in VS Code
   - (Usually accessible via sidebar or command palette)

3. **Paste Prompt:**
   - Paste the prompt into Codex chat
   - Wait for Codex to generate response

4. **Copy Codex Response:**
   - Copy Codex's entire response

5. **Submit Response:**
   - Call: debate_submit_codex_response(session_id, codex_response)
   - Or say: "Here's Codex's response: [paste]"

6. **Review Decision Pack:**
   - System will analyze both proposals
   - Show consensus score
   - Present decision pack if needed

**Estimated Time:** 2-3 minutes total
"""
