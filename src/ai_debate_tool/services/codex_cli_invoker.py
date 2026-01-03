"""Codex CLI Invoker

Python client for invoking Codex CLI directly (without MCP server).

This provides 100% automation for AI debates using the Codex CLI.

Architecture:
    Python → subprocess → Codex CLI → Codex AI → Response

Usage:
    from ai_debate_tool.services.codex_cli_invoker import CodexCLIInvoker

    invoker = CodexCLIInvoker()

    # Check availability
    if invoker.is_available():
        result = invoker.invoke("Write a Python function that adds two numbers")
        if result['success']:
            print(result['response'])

Configuration:
    class CodexCLIConfig:
        timeout: int = 120  # Timeout in seconds
        retry_count: int = 2  # Number of retries on failure
"""

import subprocess
import tempfile
import platform
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class CodexCLIConfig:
    """Configuration for Codex CLI invocation."""
    timeout: int = 120  # Timeout in seconds
    retry_count: int = 2  # Retries on failure
    model: str = "gpt-5-codex-max"  # Model to use (reported, not enforced)


class CodexCLIInvoker:
    """Invoke Codex CLI directly for automated AI debates.

    This bypasses the MCP server approach and directly invokes Codex CLI
    via subprocess. Simpler and more reliable for our use case.

    Example:
        >>> invoker = CodexCLIInvoker()
        >>> if invoker.is_available():
        ...     result = invoker.invoke("Explain this code: def foo(): pass")
        ...     print(result['response'])
    """

    def __init__(self, config: Optional[CodexCLIConfig] = None):
        """Initialize Codex CLI invoker.

        Args:
            config: Optional configuration (uses defaults if not provided)
        """
        self.config = config or CodexCLIConfig()
        self.temp_dir = Path(tempfile.gettempdir()) / "codex_cli_invoker"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        # Use shell=True on Windows to find .cmd files
        self.use_shell = platform.system() == 'Windows'

    def is_available(self) -> bool:
        """Check if Codex CLI is installed and available.

        Returns:
            True if Codex CLI is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['codex', '--version'],
                capture_output=True,
                text=True,
                timeout=5,
                shell=self.use_shell
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_status(self) -> Dict:
        """Get Codex CLI status information.

        Returns:
            Dictionary with:
                - available (bool): CLI is available
                - version (str): CLI version
                - model (str): Model being used
                - method (str): Invocation method
        """
        if not self.is_available():
            return {
                'available': False,
                'version': None,
                'model': self.config.model,
                'method': 'codex-cli',
                'error': 'Codex CLI not found. Install with: npm install -g @openai/codex'
            }

        try:
            result = subprocess.run(
                ['codex', '--version'],
                capture_output=True,
                text=True,
                timeout=5,
                shell=self.use_shell
            )
            version = result.stdout.strip() if result.returncode == 0 else 'unknown'

            return {
                'available': True,
                'version': version,
                'model': self.config.model,
                'method': 'codex-cli'
            }
        except Exception as e:
            return {
                'available': False,
                'version': None,
                'model': self.config.model,
                'method': 'codex-cli',
                'error': str(e)
            }

    def invoke(self, prompt: str, model: Optional[str] = None) -> Dict:
        """Invoke Codex CLI with a prompt.

        Args:
            prompt: The prompt to send to Codex
            model: Model to use (optional, uses config default)

        Returns:
            Dictionary with:
                - success (bool): Invocation successful
                - response (str): Codex's response
                - model (str): Model used
                - vendor (str): 'codex-cli'
                - error (str): Error message if failed
        """
        if not self.is_available():
            return {
                'success': False,
                'response': '',
                'model': model or self.config.model,
                'vendor': 'codex-cli',
                'error': 'Codex CLI not available. Install with: npm install -g @openai/codex'
            }

        model_to_use = model or self.config.model

        # Try multiple times with retry logic
        for attempt in range(self.config.retry_count + 1):
            try:
                # Use codex exec with stdin to avoid command line length limits
                # --full-auto: enables workspace-write permissions and automatic execution
                # --skip-git-repo-check: allows running outside git repos
                # -: read prompt from stdin
                result = subprocess.run(
                    ['codex', 'exec', '--full-auto', '--skip-git-repo-check', '-'],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout,
                    encoding='utf-8',
                    shell=self.use_shell
                )

                if result.returncode == 0:
                    # Codex exec sends final agent message to stdout
                    response = result.stdout.strip()

                    if response:
                        return {
                            'success': True,
                            'response': response,
                            'model': model_to_use,
                            'vendor': 'codex-cli',
                            'error': None
                        }
                    else:
                        # Empty response, check stderr for error
                        if result.stderr:
                            # Continue to retry
                            if attempt < self.config.retry_count:
                                continue
                        # No response and no retry left
                        return {
                            'success': False,
                            'response': '',
                            'model': model_to_use,
                            'vendor': 'codex-cli',
                            'error': f"Codex CLI returned empty response. stderr: {result.stderr[:500]}"
                        }
                else:
                    # Non-zero return code
                    if attempt < self.config.retry_count:
                        continue
                    return {
                        'success': False,
                        'response': '',
                        'model': model_to_use,
                        'vendor': 'codex-cli',
                        'error': f"Codex CLI failed with code {result.returncode}. stderr: {result.stderr[:500]}"
                    }

            except subprocess.TimeoutExpired:
                if attempt < self.config.retry_count:
                    continue
                return {
                    'success': False,
                    'response': '',
                    'model': model_to_use,
                    'vendor': 'codex-cli',
                    'error': f"Codex CLI timed out after {self.config.timeout} seconds"
                }

            except Exception as e:
                if attempt < self.config.retry_count:
                    continue
                return {
                    'success': False,
                    'response': '',
                    'model': model_to_use,
                    'vendor': 'codex-cli',
                    'error': f"Error invoking Codex CLI: {str(e)}"
                }

        # Should never reach here
        return {
            'success': False,
            'response': '',
            'model': model_to_use,
            'vendor': 'codex-cli',
            'error': 'All retry attempts failed'
        }


# Convenience function for quick invocations
def invoke_codex(prompt: str, timeout: int = 120) -> Dict:
    """Quick Codex CLI invocation (convenience function).

    Args:
        prompt: Prompt to send to Codex
        timeout: Timeout in seconds

    Returns:
        Response dictionary

    Example:
        >>> result = invoke_codex("Write a Python hello world function")
        >>> if result['success']:
        ...     print(result['response'])
    """
    config = CodexCLIConfig(timeout=timeout)
    invoker = CodexCLIInvoker(config)
    return invoker.invoke(prompt)
