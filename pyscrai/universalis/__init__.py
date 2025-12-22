"""
Universalis module - Run Time Simulation Engine for PyScrAI.

This module contains the core simulation engine components:
- engine: Mesa-based simulation clock and cycle management
- memory: Associative memory system with ChromaDB backend
- agents: Agent logic (macro/micro agents, LLM controller)
- archon: Adjudication logic and feasibility checking
- environment: Physics and world state simulation
"""

from pyscrai.universalis.engine import SimulationEngine

__all__ = [
    "SimulationEngine",
]

