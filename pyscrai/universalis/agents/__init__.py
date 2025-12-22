"""
Agents module - Agent logic for PyScrAI Universalis.

This module contains:
- llm_controller: LLM abstraction layer implementing Concordia interface
- llm_provider: LangChain/OpenRouter adapter
- macro_agent: Strategic/organizational agents
- micro_agent: Individual/social agents with memory-driven behavior
- observation: Observation processing pipeline
"""

from pyscrai.universalis.agents.llm_controller import (
    LanguageModel,
    LLMController,
    LLMResponse,
    InvalidResponseError
)
from pyscrai.universalis.agents.llm_provider import (
    LangChainOpenRouterModel,
    create_default_model
)
from pyscrai.universalis.agents.macro_agent import (
    MacroAgent,
    MacroAgentConfig,
    MacroIntent,
    create_macro_agent
)
from pyscrai.universalis.agents.micro_agent import (
    MicroAgent,
    MicroAgentConfig,
    MicroAgentState,
    MicroIntent,
    create_micro_agent
)
from pyscrai.universalis.agents.observation import (
    ObservationProcessor,
    Observation,
    ObservationType,
    ObservationPriority,
    ObservationFilter,
    create_observation_processor
)

__all__ = [
    # LLM
    "LanguageModel",
    "LLMController",
    "LLMResponse",
    "InvalidResponseError",
    "LangChainOpenRouterModel",
    "create_default_model",
    # Macro agent
    "MacroAgent",
    "MacroAgentConfig",
    "MacroIntent",
    "create_macro_agent",
    # Micro agent
    "MicroAgent",
    "MicroAgentConfig",
    "MicroAgentState",
    "MicroIntent",
    "create_micro_agent",
    # Observation
    "ObservationProcessor",
    "Observation",
    "ObservationType",
    "ObservationPriority",
    "ObservationFilter",
    "create_observation_processor",
]
