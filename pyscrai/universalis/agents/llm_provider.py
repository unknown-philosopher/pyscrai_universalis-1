"""
LLM Provider - LangChain/OpenRouter adapter for PyScrAI.

This module provides concrete implementations of the LanguageModel interface
using LangChain with OpenRouter as the backend.
"""

import os
from collections.abc import Collection, Mapping, Sequence
from typing import Any, Optional, Tuple
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langfuse.langchain import CallbackHandler

from pyscrai.universalis.agents.llm_controller import (
    LanguageModel,
    InvalidResponseError,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_TOP_K,
    DEFAULT_TERMINATORS,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_MAX_TOKENS,
)
from pyscrai.utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)


class LangChainOpenRouterModel(LanguageModel):
    """
    LanguageModel implementation using LangChain with OpenRouter.
    
    This adapter wraps the ChatOpenAI class from LangChain and implements
    the Concordia-compatible LanguageModel interface.
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        enable_tracing: bool = True
    ):
        """
        Initialize the LangChain OpenRouter model.
        
        Args:
            model_name: Model to use (defaults to env var MODEL_NAME)
            api_key: OpenRouter API key (defaults to env var)
            base_url: OpenRouter base URL (defaults to env var)
            temperature: Default temperature for sampling
            enable_tracing: Whether to enable Langfuse tracing
        """
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self._base_url = base_url or os.getenv("OPENROUTER_BASE_URL")
        self._model_name = model_name or os.getenv("MODEL_NAME", "xiaomi/mimo-v2-flash:free")
        self._default_temperature = temperature
        
        # Initialize the ChatOpenAI instance
        self._llm = ChatOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            model=self._model_name,
            temperature=temperature
        )
        
        # Initialize Langfuse handler for tracing
        self._langfuse_handler = CallbackHandler() if enable_tracing else None
        
        logger.info(f"Initialized LangChainOpenRouterModel with model: {self._model_name}")
    
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
        Sample text from the model using LangChain.
        
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
        # Configure callbacks
        config = {}
        if self._langfuse_handler:
            config["callbacks"] = [self._langfuse_handler]
        
        # Create a temporary LLM with the specified parameters
        # Note: OpenRouter/LangChain doesn't support all parameters natively
        llm = ChatOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            model=self._model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            request_timeout=timeout
        )
        
        try:
            response = llm.invoke(
                [HumanMessage(content=prompt)],
                config=config
            )
            
            result = response.content
            
            # Apply terminators if specified
            if terminators:
                for terminator in terminators:
                    if terminator in result:
                        result = result.split(terminator)[0]
            
            return result
            
        except Exception as e:
            logger.error(f"Error sampling text: {e}")
            raise
    
    def sample_choice(
        self,
        prompt: str,
        responses: Sequence[str],
        *,
        seed: Optional[int] = None,
    ) -> Tuple[int, str, Mapping[str, Any]]:
        """
        Sample a response from available choices.
        
        This uses a scoring approach where the model is asked to choose
        from the available options.
        
        Args:
            prompt: The initial text to condition on.
            responses: The responses to choose from.
            seed: Optional seed for sampling.
        
        Returns:
            Tuple of (index, response, info).
        
        Raises:
            InvalidResponseError: If unable to produce a valid choice.
        """
        if not responses:
            raise InvalidResponseError("No responses provided to choose from")
        
        # Build a selection prompt
        options_text = "\n".join(
            f"{i+1}. {response}" 
            for i, response in enumerate(responses)
        )
        
        selection_prompt = (
            f"{prompt}\n\n"
            f"Choose ONE of the following options by responding with just the number:\n"
            f"{options_text}\n\n"
            f"Your choice (number only):"
        )
        
        config = {}
        if self._langfuse_handler:
            config["callbacks"] = [self._langfuse_handler]
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = self._llm.invoke(
                    [HumanMessage(content=selection_prompt)],
                    config=config
                )
                
                # Parse the response to get the choice number
                choice_text = response.content.strip()
                
                # Try to extract a number from the response
                import re
                numbers = re.findall(r'\d+', choice_text)
                
                if numbers:
                    choice_num = int(numbers[0])
                    if 1 <= choice_num <= len(responses):
                        index = choice_num - 1
                        return (
                            index, 
                            responses[index], 
                            {"raw_response": choice_text, "attempts": attempt + 1}
                        )
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                continue
        
        raise InvalidResponseError(
            f"Failed to get valid choice after {max_attempts} attempts"
        )
    
    def generate_with_system_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> str:
        """
        Generate text with a system prompt.
        
        This is a convenience method for common chat-style interactions.
        
        Args:
            system_prompt: The system prompt to set context
            user_prompt: The user's input
            **kwargs: Additional arguments passed to the model
        
        Returns:
            The generated response
        """
        config = {}
        if self._langfuse_handler:
            config["callbacks"] = [self._langfuse_handler]
        
        response = self._llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=config
        )
        
        return response.content
    
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model_name
    
    def set_temperature(self, temperature: float) -> None:
        """Update the default temperature."""
        self._default_temperature = temperature
        self._llm = ChatOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            model=self._model_name,
            temperature=temperature
        )


def create_default_model() -> LangChainOpenRouterModel:
    """
    Create a default LLM model instance.
    
    Returns:
        Configured LangChainOpenRouterModel instance
    """
    return LangChainOpenRouterModel()

