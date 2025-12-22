"""
Archon module - Adjudication logic for PyScrAI Universalis.

The Archon is the omniscient referee of the simulation, responsible for:
- Adjudicating actor actions
- Checking feasibility of intents
- Generating rationales for decisions
- Simulating environmental shifts (Gaia)
"""

from pyscrai.universalis.archon.interface import (
    ArchonInterface, 
    AdjudicationResult, 
    FeasibilityReport
)
from pyscrai.universalis.archon.adjudicator import Archon

__all__ = [
    "ArchonInterface",
    "AdjudicationResult",
    "FeasibilityReport",
    "Archon",
]
