"""
LLM Controller - Language Model abstraction layer for PyScrAI Universalis.

This module implements the Concordia-style LanguageModel interface,
providing a consistent abstraction for LLM operations.
"""

from abc import ABC, abstractmethod
from collections.abc import Collection, Mapping, Sequence
from typing import Any, Optional, Tuple
from dataclasses import dataclass

# Default configuration values (matching Concordia)
DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 0.95
DEFAULT_TOP_K = 64
DEFAULT_TERMINATORS: Tuple[str, ...] = ()
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_TOKENS = 5000


class InvalidResponseError(Exception):
    """Exception to throw when exceeding max attempts to get a choice."""
    pass


class LanguageModel(ABC):
    """
    Abstract base class for language models.
    
    This interface is compatible with Concordia's LanguageModel,
    allowing for interoperability with Concordia components.
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
            seed: Optional seed for sampling. If None, a random seed will be used.
        
        Returns:
            The sampled response (does not include the prompt).
        
        Raises:
            TimeoutError: If the operation times out.
        """
        raise NotImplementedError
    
    @abstractmethod
    def sample_choice(
        self,
        prompt: str,
        responses: Sequence[str],
        *,
        seed: Optional[int] = None,
    ) -> Tuple[int, str, Mapping[str, Any]]:
        """
        Sample a response from those available.
        
        Args:
            prompt: The initial text to condition on.
            responses: The responses to score.
            seed: Optional seed for sampling. If None, a random seed will be used.
        
        Returns:
            Tuple of (index, response, info):
            - index: The index of the sampled response
            - response: The sampled response string
            - info: Additional information about the sampling process
        
        Raises:
            InvalidResponseError: If unable to produce a valid choice.
        """
        raise NotImplementedError


@dataclass
class LLMResponse:
    """
    Response from an LLM call.
    
    Attributes:
        content: The generated text content
        tokens_used: Number of tokens used
        model: Model that generated the response
        metadata: Additional metadata from the provider
    """
    content: str
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    metadata: Optional[Mapping[str, Any]] = None


class LLMController:
    """
    High-level controller for LLM operations.
    
    Provides additional functionality on top of the base LanguageModel
    interface, including retry logic, caching, and observability.
    """
    
    def __init__(
        self,
        model: LanguageModel,
        max_retries: int = 3,
        enable_caching: bool = False
    ):
        """
        Initialize the LLM controller.
        
        Args:
            model: The underlying LanguageModel implementation
            max_retries: Maximum number of retry attempts
            enable_caching: Whether to cache responses
        """
        self._model = model
        self._max_retries = max_retries
        self._enable_caching = enable_caching
        self._cache: dict = {}
    
    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        **kwargs
    ) -> str:
        """
        Generate text with automatic retries.
        
        Args:
            prompt: The prompt to generate from
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional arguments passed to sample_text
        
        Returns:
            Generated text
        """
        # Check cache
        if self._enable_caching:
            cache_key = f"{prompt}:{max_tokens}:{temperature}"
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        last_error = None
        for attempt in range(self._max_retries):
            try:
                result = self._model.sample_text(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                # Cache result
                if self._enable_caching:
                    self._cache[cache_key] = result
                
                return result
            except Exception as e:
                last_error = e
                continue
        
        raise last_error or Exception("Failed to generate text after retries")
    
    def choose(
        self,
        prompt: str,
        options: Sequence[str],
        **kwargs
    ) -> Tuple[int, str]:
        """
        Choose from a list of options.
        
        Args:
            prompt: The prompt context
            options: List of options to choose from
            **kwargs: Additional arguments passed to sample_choice
        
        Returns:
            Tuple of (index, chosen_option)
        """
        index, response, _ = self._model.sample_choice(prompt, options, **kwargs)
        return index, response
    
    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._cache.clear()

