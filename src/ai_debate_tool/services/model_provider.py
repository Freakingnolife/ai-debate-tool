"""Model Provider Interface

Abstract interface for AI model providers, enabling true multi-model debates.

Providers:
- CodexCLIProvider: Uses Codex CLI (subprocess) - OpenAI
- GeminiCLIProvider: Uses Gemini CLI (subprocess) - Google
- CopilotBridgeProvider: Uses VS Code Copilot Bridge (HTTP)

Usage:
    from ai_debate_tool.services.model_provider import get_available_providers

    providers = get_available_providers()  # Returns list of 2-3 providers
    for provider in providers:
        result = await provider.invoke(prompt)
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .codex_cli_invoker import CodexCLIInvoker, CodexCLIConfig
from .gemini_cli_invoker import GeminiCLIInvoker, GeminiCLIConfig
from .copilot_invoker import CopilotInvoker, CopilotConfig


@dataclass
class ModelResponse:
    """Response from a model provider."""
    success: bool
    response: str
    score: Optional[int] = None
    model: str = "unknown"
    vendor: str = "unknown"
    error: Optional[str] = None
    elapsed_time: float = 0.0


class ModelProvider(ABC):
    """Abstract interface for AI model providers."""

    @abstractmethod
    async def invoke(self, prompt: str) -> ModelResponse:
        """Invoke model with prompt and return response.

        Args:
            prompt: The prompt to send to the model

        Returns:
            ModelResponse with success status and response text
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available.

        Returns:
            True if provider can be used, False otherwise
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider display name.

        Returns:
            Human-readable provider name (e.g., "Claude", "Codex CLI")
        """
        pass

    @abstractmethod
    def get_vendor(self) -> str:
        """Get provider vendor.

        Returns:
            Vendor identifier (e.g., "anthropic", "openai", "google", "copilot")
        """
        pass


class CodexCLIProvider(ModelProvider):
    """Codex CLI provider - invokes Codex via subprocess.

    This is the most reliable provider as it uses the locally installed
    Codex CLI and doesn't require any additional setup.
    """

    def __init__(self, config: Optional[CodexCLIConfig] = None):
        """Initialize Codex CLI provider.

        Args:
            config: Optional Codex CLI configuration
        """
        self.invoker = CodexCLIInvoker(config)
        self._name = "Codex CLI"

    async def invoke(self, prompt: str) -> ModelResponse:
        """Invoke Codex CLI with prompt.

        Args:
            prompt: The prompt to send

        Returns:
            ModelResponse with Codex's response
        """
        import time
        start = time.time()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.invoker.invoke,
            prompt
        )

        elapsed = time.time() - start

        if result['success']:
            # Extract score if present in response
            score = self._extract_score(result['response'])
            return ModelResponse(
                success=True,
                response=result['response'],
                score=score,
                model=result.get('model', 'codex'),
                vendor='openai',
                elapsed_time=elapsed
            )
        else:
            return ModelResponse(
                success=False,
                response='',
                model=result.get('model', 'codex'),
                vendor='openai',
                error=result.get('error', 'Unknown error'),
                elapsed_time=elapsed
            )

    def is_available(self) -> bool:
        """Check if Codex CLI is available."""
        return self.invoker.is_available()

    def get_name(self) -> str:
        """Get provider name."""
        return self._name

    def get_vendor(self) -> str:
        """Get vendor identifier."""
        return "openai"

    def _extract_score(self, response: str, default: int = 75) -> int:
        """Extract numerical score from response.

        Args:
            response: Response text
            default: Default score if not found

        Returns:
            Extracted score (0-100)
        """
        import re

        patterns = [
            r'(?:score|rating):\s*(\d{1,3})',
            r'(\d{1,3})\s*/\s*100',
            r'(?:give|assign)\s+(?:it\s+)?(?:a\s+)?(\d{1,3})'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                if 0 <= score <= 100:
                    return score

        return default


class GeminiCLIProvider(ModelProvider):
    """Gemini CLI provider - invokes Google Gemini via subprocess.

    Uses the locally installed Gemini CLI for multi-vendor debates.
    Install with: npm install -g @google/gemini-cli
    """

    def __init__(self, config: Optional[GeminiCLIConfig] = None):
        """Initialize Gemini CLI provider.

        Args:
            config: Optional Gemini CLI configuration
        """
        self.invoker = GeminiCLIInvoker(config)
        self._name = "Gemini CLI"

    async def invoke(self, prompt: str) -> ModelResponse:
        """Invoke Gemini CLI with prompt.

        Args:
            prompt: The prompt to send

        Returns:
            ModelResponse with Gemini's response
        """
        import time
        start = time.time()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.invoker.invoke,
            prompt
        )

        elapsed = time.time() - start

        if result['success']:
            # Extract score if present in response
            score = self._extract_score(result['response'])
            return ModelResponse(
                success=True,
                response=result['response'],
                score=score,
                model=result.get('model', 'gemini'),
                vendor='google',
                elapsed_time=elapsed
            )
        else:
            return ModelResponse(
                success=False,
                response='',
                model=result.get('model', 'gemini'),
                vendor='google',
                error=result.get('error', 'Unknown error'),
                elapsed_time=elapsed
            )

    def is_available(self) -> bool:
        """Check if Gemini CLI is available."""
        return self.invoker.is_available()

    def get_name(self) -> str:
        """Get provider name."""
        return self._name

    def get_vendor(self) -> str:
        """Get vendor identifier."""
        return "google"

    def _extract_score(self, response: str, default: int = 75) -> int:
        """Extract numerical score from response."""
        import re

        patterns = [
            r'(?:score|rating):\s*(\d{1,3})',
            r'(\d{1,3})\s*/\s*100',
            r'(?:give|assign)\s+(?:it\s+)?(?:a\s+)?(\d{1,3})'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                if 0 <= score <= 100:
                    return score

        return default


class CopilotBridgeProvider(ModelProvider):
    """Copilot Bridge provider - invokes Copilot via VS Code extension.

    Requires the Copilot Bridge VS Code extension to be running.
    Communicates via HTTP on localhost:8765.
    """

    def __init__(self, config: Optional[CopilotConfig] = None):
        """Initialize Copilot Bridge provider.

        Args:
            config: Optional Copilot configuration
        """
        self.invoker = CopilotInvoker(config)
        self._name = "GitHub Copilot"

    async def invoke(self, prompt: str) -> ModelResponse:
        """Invoke Copilot via bridge.

        Args:
            prompt: The prompt to send

        Returns:
            ModelResponse with Copilot's response
        """
        import time
        start = time.time()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.invoker.invoke,
            prompt
        )

        elapsed = time.time() - start

        if result and result.get('success'):
            score = self._extract_score(result['response'])
            return ModelResponse(
                success=True,
                response=result['response'],
                score=score,
                model=result.get('model', 'copilot'),
                vendor='copilot',
                elapsed_time=elapsed
            )
        else:
            return ModelResponse(
                success=False,
                response='',
                model='copilot',
                vendor='copilot',
                error=result.get('error', 'Copilot bridge not available') if result else 'No response',
                elapsed_time=elapsed
            )

    def is_available(self) -> bool:
        """Check if Copilot Bridge is available."""
        return self.invoker.is_available()

    def get_name(self) -> str:
        """Get provider name."""
        return self._name

    def get_vendor(self) -> str:
        """Get vendor identifier."""
        return "copilot"

    def _extract_score(self, response: str, default: int = 75) -> int:
        """Extract numerical score from response."""
        import re

        patterns = [
            r'(?:score|rating):\s*(\d{1,3})',
            r'(\d{1,3})\s*/\s*100',
            r'(?:give|assign)\s+(?:it\s+)?(?:a\s+)?(\d{1,3})'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                if 0 <= score <= 100:
                    return score

        return default


def get_available_providers() -> List[ModelProvider]:
    """Get all available providers for multi-model debates.

    Returns list of available providers (2-3 models).

    Detection priority:
    1. All three available -> [Codex, Gemini, Copilot]
    2. Codex + Gemini -> [Codex, Gemini]
    3. Codex + Copilot -> [Codex, Copilot]
    4. Codex only -> [Codex, Codex] (same model, different instances)

    Returns:
        List of available ModelProvider instances
    """
    codex = CodexCLIProvider()
    gemini = GeminiCLIProvider()
    copilot = CopilotBridgeProvider()

    providers = []

    # Add available providers in priority order
    if codex.is_available():
        providers.append(codex)
    if gemini.is_available():
        providers.append(gemini)
    if copilot.is_available():
        providers.append(copilot)

    # If we have at least 2 providers, return them
    if len(providers) >= 2:
        return providers

    # Fallback: If only one provider, duplicate it
    if len(providers) == 1:
        # Create a second instance of the same provider
        if codex.is_available():
            providers.append(CodexCLIProvider())
        elif gemini.is_available():
            providers.append(GeminiCLIProvider())
        elif copilot.is_available():
            providers.append(CopilotBridgeProvider())

    # If no providers available, return Codex anyway (will fail gracefully)
    if len(providers) == 0:
        return [codex, CodexCLIProvider()]

    return providers


def get_provider_pair() -> Tuple[ModelProvider, ModelProvider]:
    """Get the best available provider pair for debates (legacy 2-model API).

    Returns tuple of (primary_provider, counter_provider).

    Returns:
        Tuple of (primary, counter) ModelProvider instances
    """
    providers = get_available_providers()
    if len(providers) >= 2:
        return (providers[0], providers[1])
    return (providers[0], providers[0])


def get_provider_status() -> Dict:
    """Get status of all available providers.

    Returns:
        Dictionary with provider availability info
    """
    codex = CodexCLIProvider()
    gemini = GeminiCLIProvider()
    copilot = CopilotBridgeProvider()

    available_providers = get_available_providers()
    provider_names = [p.get_name() for p in available_providers]

    return {
        'codex_cli': {
            'available': codex.is_available(),
            'name': codex.get_name(),
            'vendor': codex.get_vendor()
        },
        'gemini_cli': {
            'available': gemini.is_available(),
            'name': gemini.get_name(),
            'vendor': gemini.get_vendor()
        },
        'copilot_bridge': {
            'available': copilot.is_available(),
            'name': copilot.get_name(),
            'vendor': copilot.get_vendor()
        },
        'active_providers': provider_names,
        'provider_count': len(available_providers),
        'multi_vendor': len(set(p.get_vendor() for p in available_providers)) > 1
    }


def _get_recommended_pair_names(codex: CodexCLIProvider, gemini: GeminiCLIProvider, copilot: CopilotBridgeProvider) -> str:
    """Get human-readable description of recommended provider configuration."""
    providers = []
    if codex.is_available():
        providers.append("Codex")
    if gemini.is_available():
        providers.append("Gemini")
    if copilot.is_available():
        providers.append("Copilot")

    if len(providers) == 3:
        return "Codex + Gemini + Copilot (3-model debate)"
    elif len(providers) == 2:
        return f"{providers[0]} + {providers[1]} (2-model debate)"
    elif len(providers) == 1:
        return f"{providers[0]} (single model, dual perspective)"
    else:
        return "No providers available"
