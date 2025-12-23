"""
Archon module - Adjudication logic for PyScrAI Universalis.

The Archon is the omniscient referee of the simulation, responsible for:
- Adjudicating actor actions
- Checking feasibility of intents
- Generating rationales for decisions
- Simulating environmental shifts (Gaia)
- Validating spatial constraints using DuckDB
"""

from pyscrai.universalis.archon.interface import (
    ArchonInterface, 
    AdjudicationResult, 
    FeasibilityReport
)
from pyscrai.universalis.archon.adjudicator import Archon
from pyscrai.universalis.archon.feasibility import (
    FeasibilityEngine,
    Constraint,
    ConstraintType
)
from pyscrai.universalis.archon.spatial_constraints import (
    SpatialConstraintChecker,
    SpatialConstraintResult,
    SpatialConstraintType
)

__all__ = [
    # Interface
    "ArchonInterface",
    "AdjudicationResult",
    "FeasibilityReport",
    # Adjudicator
    "Archon",
    # Feasibility
    "FeasibilityEngine",
    "Constraint",
    "ConstraintType",
    # Spatial Constraints
    "SpatialConstraintChecker",
    "SpatialConstraintResult",
    "SpatialConstraintType",
]
