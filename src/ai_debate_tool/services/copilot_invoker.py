"""Copilot Invoker Service

Automatically invokes GitHub Copilot via VS Code bridge extension.
Enables 100% automation without API costs.

Phase 7.2 Implementation - Full automation with local Copilot.
"""

import requests
from typing import Dict, Optional
import time


class CopilotConfig:
    """Configuration for Copilot bridge."""

    def __init__(
        self,
        endpoint: str = "http://localhost:8765",
        model: str = "gpt-5-codex",
        timeout: int = 60,
        max_retries: int = 3
    ):
        """Initialize Copilot configuration.

        Args:
            endpoint: Copilot bridge HTTP endpoint (default: http://localhost:8765)
            model: Preferred Copilot model (default: gpt-5-codex)
            timeout: Request timeout in seconds (default: 60)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries


class CopilotInvoker:
    """Copilot invoker for automatic code analysis.

    Communicates with VS Code Copilot Bridge extension to invoke
    GitHub Copilot (GPT-5.1-Codex) without API costs.

    Provides 100% automation for AI debates by automatically getting
    Codex's response instead of manual copy/paste.
    """

    def __init__(self, config: Optional[CopilotConfig] = None):
        """Initialize Copilot invoker.

        Args:
            config: Optional Copilot configuration
        """
        self.config = config or CopilotConfig()

    def invoke(self, prompt: str, model: Optional[str] = None) -> Optional[Dict]:
        """Invoke Copilot with prompt.

        Args:
            prompt: Prompt to send to Copilot
            model: Optional model override (uses config default if None)

        Returns:
            Dictionary with:
                - success (bool): True if invocation succeeded
                - response (str): Copilot's response
                - model (str): Model used
                - vendor (str): Vendor (usually 'copilot')
                - error (str): Error message if failed (None if success)

            Returns None if Copilot bridge is unavailable.
        """
        # Use provided model or config default
        model_to_use = model or self.config.model

        # Build request
        url = f"{self.config.endpoint}/invoke-copilot"
        payload = {
            'prompt': prompt,
            'model': model_to_use
        }

        # Try with retries
        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout
                )

                # Parse response
                if response.status_code == 200:
                    result = response.json()
                    return {
                        'success': True,
                        'response': result.get('response', ''),
                        'model': result.get('model', model_to_use),
                        'vendor': result.get('vendor', 'copilot'),
                        'error': None
                    }
                elif response.status_code == 503:
                    # Copilot not available
                    result = response.json()
                    return {
                        'success': False,
                        'response': '',
                        'model': model_to_use,
                        'vendor': 'copilot',
                        'error': result.get('message', 'Copilot not available')
                    }
                else:
                    # Other error
                    try:
                        result = response.json()
                        error_msg = result.get('message', f'HTTP {response.status_code}')
                    except Exception:
                        error_msg = f'HTTP {response.status_code}'

                    # Retry on server errors
                    if response.status_code >= 500 and attempt < self.config.max_retries - 1:
                        time.sleep(1)  # Wait before retry
                        continue

                    return {
                        'success': False,
                        'response': '',
                        'model': model_to_use,
                        'vendor': 'copilot',
                        'error': error_msg
                    }

            except (requests.exceptions.ConnectionError, ConnectionError):
                # Bridge not running
                if attempt < self.config.max_retries - 1:
                    time.sleep(1)  # Wait before retry
                    continue

                return {
                    'success': False,
                    'response': '',
                    'model': model_to_use,
                    'vendor': 'copilot',
                    'error': 'Copilot bridge not running. Start VS Code with Copilot Bridge extension.'
                }

            except requests.exceptions.Timeout:
                # Timeout
                if attempt < self.config.max_retries - 1:
                    time.sleep(1)  # Wait before retry
                    continue

                return {
                    'success': False,
                    'response': '',
                    'model': model_to_use,
                    'vendor': 'copilot',
                    'error': f'Request timeout after {self.config.timeout} seconds'
                }

            except Exception as e:
                # Unexpected error (don't retry)
                return {
                    'success': False,
                    'response': '',
                    'model': model_to_use,
                    'vendor': 'copilot',
                    'error': f'Unexpected error: {str(e)}'
                }

        # Max retries exhausted
        return {
            'success': False,
            'response': '',
            'model': model_to_use,
            'vendor': 'copilot',
            'error': f'Failed after {self.config.max_retries} attempts'
        }

    def is_available(self) -> bool:
        """Check if Copilot bridge is available.

        Returns:
            True if bridge is running and healthy, False otherwise
        """
        try:
            url = f"{self.config.endpoint}/health"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_status(self) -> Dict:
        """Get Copilot bridge status.

        Returns:
            Dictionary with:
                - available (bool): Whether bridge is available
                - endpoint (str): Bridge endpoint
                - model (str): Configured model
                - error (str): Error message if unavailable (None if available)
        """
        available = self.is_available()

        if available:
            return {
                'available': True,
                'endpoint': self.config.endpoint,
                'model': self.config.model,
                'error': None
            }
        else:
            return {
                'available': False,
                'endpoint': self.config.endpoint,
                'model': self.config.model,
                'error': 'Copilot bridge not running. Start VS Code with Copilot Bridge extension.'
            }
