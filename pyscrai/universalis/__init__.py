"""
Universalis module - Run Time Simulation Engine for PyScrAI.

This module contains the core simulation engine components:
- engine: Async simulation engine with DuckDB state management
- state: DuckDB-based state storage with spatial queries
- memory: Associative memory system with LanceDB backend
- agents: Agent logic (macro/micro agents, LLM controller)
- archon: Adjudication logic and spatial feasibility checking
- environment: Physics and world state simulation
"""

from pyscrai.universalis.engine import SimulationEngine
from pyscrai.universalis.state import DuckDBStateManager, get_state_manager

__all__ = [
    "SimulationEngine",
    "DuckDBStateManager",
    "get_state_manager",
]
