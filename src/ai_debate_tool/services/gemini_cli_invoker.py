"""Gemini CLI Invoker

Python client for invoking Google Gemini CLI directly (without MCP server).

This provides automation for AI debates using the Gemini CLI.

Architecture:
    Python -> subprocess -> Gemini CLI -> Gemini AI -> Response

Usage:
    from ai_debate_tool.services.gemini_cli_invoker import GeminiCLIInvoker

    invoker = GeminiCLIInvoker()

    # Check availability
    if invoker.is_available():
        result = invoker.invoke("Write a Python function that adds two numbers")
        if result['success']:
            print(result['response'])

Configuration:
    class GeminiCLIConfig:
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
class GeminiCLIConfig:
    """Configuration for Gemini CLI invocation."""
    timeout: int = 120  # Timeout in seconds
    retry_count: int = 2  # Retries on failure
    model: str = "gemini-2.5-pro"  # Model to use


class GeminiCLIInvoker:
    """Invoke Gemini CLI directly for automated AI debates.

    This invokes Gemini CLI via subprocess for multi-model debates.

    Example:
        >>> invoker = GeminiCLIInvoker()
        >>> if invoker.is_available():
        ...     result = invoker.invoke("Explain this code: def foo(): pass")
        ...     print(result['response'])
    """

    def __init__(self, config: Optional[GeminiCLIConfig] = None):
        """Initialize Gemini CLI invoker.

        Args:
            config: Optional configuration (uses defaults if not provided)
        """
        self.config = config or GeminiCLIConfig()
        self.temp_dir = Path(tempfile.gettempdir()) / "gemini_cli_invoker"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        # Use shell=True on Windows to find .cmd files
        self.use_shell = platform.system() == 'Windows'

    def is_available(self) -> bool:
        """Check if Gemini CLI is installed and available.

        Returns:
            True if Gemini CLI is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['gemini', '--version'],
                capture_output=True,
                text=True,
                timeout=5,
                shell=self.use_shell
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_status(self) -> Dict:
        """Get Gemini CLI status information.

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
                'method': 'gemini-cli',
                'error': 'Gemini CLI not found. Install with: npm install -g @google/gemini-cli'
            }

        try:
            result = subprocess.run(
                ['gemini', '--version'],
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
                'method': 'gemini-cli'
            }
        except Exception as e:
            return {
                'available': False,
                'version': None,
                'model': self.config.model,
                'method': 'gemini-cli',
                'error': str(e)
            }

    def invoke(self, prompt: str, model: Optional[str] = None) -> Dict:
        """Invoke Gemini CLI with a prompt.

        Args:
            prompt: The prompt to send to Gemini
            model: Model to use (optional, uses config default)

        Returns:
            Dictionary with:
                - success (bool): Invocation successful
                - response (str): Gemini's response
                - model (str): Model used
                - vendor (str): 'gemini-cli'
                - error (str): Error message if failed
        """
        if not self.is_available():
            return {
                'success': False,
                'response': '',
                'model': model or self.config.model,
                'vendor': 'gemini-cli',
                'error': 'Gemini CLI not available. Install with: npm install -g @google/gemini-cli'
            }

        model_to_use = model or self.config.model

        # Try multiple times with retry logic
        for attempt in range(self.config.retry_count + 1):
            try:
                # Use gemini with optimized flags for speed:
                # -y: YOLO mode (auto-accept all actions)
                # --sandbox false: disable sandboxing for faster execution
                # -o text: simple text output (no JSON overhead)
                # positional prompt instead of -p (deprecated flag)
                result = subprocess.run(
                    ['gemini', prompt, '-y', '--sandbox', 'false', '-o', 'text'],
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout,
                    encoding='utf-8',
                    shell=self.use_shell
                )

                if result.returncode == 0:
                    # Gemini sends response to stdout
                    response = result.stdout.strip()

                    if response:
                        return {
                            'success': True,
                            'response': response,
                            'model': model_to_use,
                            'vendor': 'gemini-cli',
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
                            'vendor': 'gemini-cli',
                            'error': f"Gemini CLI returned empty response. stderr: {result.stderr[:500]}"
                        }
                else:
                    # Non-zero return code
                    if attempt < self.config.retry_count:
                        continue
                    return {
                        'success': False,
                        'response': '',
                        'model': model_to_use,
                        'vendor': 'gemini-cli',
                        'error': f"Gemini CLI failed with code {result.returncode}. stderr: {result.stderr[:500]}"
                    }

            except subprocess.TimeoutExpired:
                if attempt < self.config.retry_count:
                    continue
                return {
                    'success': False,
                    'response': '',
                    'model': model_to_use,
                    'vendor': 'gemini-cli',
                    'error': f"Gemini CLI timed out after {self.config.timeout} seconds"
                }

            except Exception as e:
                if attempt < self.config.retry_count:
                    continue
                return {
                    'success': False,
                    'response': '',
                    'model': model_to_use,
                    'vendor': 'gemini-cli',
                    'error': f"Error invoking Gemini CLI: {str(e)}"
                }

        # Should never reach here
        return {
            'success': False,
            'response': '',
            'model': model_to_use,
            'vendor': 'gemini-cli',
            'error': 'All retry attempts failed'
        }


# Convenience function for quick invocations
def invoke_gemini(prompt: str, timeout: int = 120) -> Dict:
    """Quick Gemini CLI invocation (convenience function).

    Args:
        prompt: Prompt to send to Gemini
        timeout: Timeout in seconds

    Returns:
        Response dictionary

    Example:
        >>> result = invoke_gemini("Write a Python hello world function")
        >>> if result['success']:
        ...     print(result['response'])
    """
    config = GeminiCLIConfig(timeout=timeout)
    invoker = GeminiCLIInvoker(config)
    return invoker.invoke(prompt)
