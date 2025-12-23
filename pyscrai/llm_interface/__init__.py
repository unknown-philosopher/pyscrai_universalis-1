"""
LLM Interface - Language Model abstraction for PyScrAI Universalis.

This module provides the LanguageModel interface and related utilities
for interacting with LLMs in a Concordia-compatible way.
"""

from abc import ABC, abstractmethod
from collections.abc import Collection, Mapping, Sequence
from typing import Any, Optional, Tuple

# Default parameters for LLM calls
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.95
DEFAULT_TOP_K = 40
DEFAULT_TERMINATORS: tuple[str, ...] = ()
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_TOKENS = 1024


class InvalidResponseError(Exception):
    """Raised when the LLM produces an invalid response."""
    pass


class LanguageModel(ABC):
    """
    Abstract interface for language models.
    
    This interface is compatible with Concordia's language model abstraction,
    allowing for easy swapping of different LLM backends.
    """
    
    @abstractmethod
    def sample_text(
        self,
        prompt: str,
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        terminators: Collection[str] = DEFAULT_TERMINATORS,
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
        top_k: int = DEFAULT_TOP_K,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        seed: Optional[int] = None,
    ) -> str:
        """
        Sample text from the model.
        
        Args:
            prompt: The initial text to condition on.
            max_tokens: The maximum number of tokens in the response.
            terminators: The response will be terminated before any of these characters.
            temperature: Temperature for the model.
            top_p: Filters tokens based on cumulative probability.
            top_k: Filters tokens by selecting the top_k most probable tokens.
            timeout: Timeout for the request.
            seed: Optional seed for sampling.
        
        Returns:
            The sampled response (does not include the prompt).
        """
        pass
    
    @abstractmethod
    def sample_choice(
        self,
        prompt: str,
        responses: Sequence[str],
        *,
        seed: Optional[int] = None,
    ) -> Tuple[int, str, Mapping[str, Any]]:
        """
        Sample a response from available choices.
        
        Args:
            prompt: The initial text to condition on.
            responses: The responses to choose from.
            seed: Optional seed for sampling.
        
        Returns:
            Tuple of (index, response, info).
        
        Raises:
            InvalidResponseError: If unable to produce a valid choice.
        """
        pass


# Export commonly used items
__all__ = [
    'LanguageModel',
    'InvalidResponseError',
    'DEFAULT_TEMPERATURE',
    'DEFAULT_TOP_P',
    'DEFAULT_TOP_K',
    'DEFAULT_TERMINATORS',
    'DEFAULT_TIMEOUT_SECONDS',
    'DEFAULT_MAX_TOKENS',
]

