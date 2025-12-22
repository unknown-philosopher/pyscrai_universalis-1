"""
Archon Interface - Abstract interface for the Archon adjudication system.

This module defines the interface that all Archon implementations must follow,
ensuring consistent behavior across different adjudication strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pyscrai.data.schemas.models import WorldState


@dataclass
class FeasibilityReport:
    """
    Report from feasibility checking.
    
    Contains details about whether an intent is feasible
    and any constraint violations found.
    """
    feasible: bool
    intent: str
    constraints_checked: List[str] = field(default_factory=list)
    violations: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feasible": self.feasible,
            "intent": self.intent,
            "constraints_checked": self.constraints_checked,
            "violations": self.violations,
            "recommendations": self.recommendations
        }


@dataclass
class AdjudicationResult:
    """
    Result of an adjudication cycle.
    
    Contains the updated world state, summary, and detailed rationales
    for traceability.
    """
    world_state: WorldState
    summary: str
    rationales: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding world_state which needs special handling)."""
        return {
            "summary": self.summary,
            "rationales": self.rationales,
            "success": self.success,
            "errors": self.errors
        }


class ArchonInterface(ABC):
    """
    Abstract interface for Archon implementations.
    
    The Archon is the omniscient referee of the simulation, responsible for:
    - Adjudicating actor actions
    - Checking feasibility of intents
    - Generating rationales for decisions
    - Simulating environmental shifts (Gaia)
    """
    
    @abstractmethod
    def adjudicate(
        self, 
        world_state: WorldState, 
        actor_intents: List[str]
    ) -> AdjudicationResult:
        """
        Adjudicate actor intents and return the result.
        
        This is the main entry point for adjudication. It takes the current
        world state and all actor intents, then determines the outcomes.
        
        Args:
            world_state: Current world state
            actor_intents: List of actor intent strings
        
        Returns:
            AdjudicationResult with updated state and rationale
        """
        pass
    
    @abstractmethod
    def check_feasibility(
        self, 
        intent: str, 
        world_state: WorldState
    ) -> FeasibilityReport:
        """
        Check if an intent is feasible given the world state.
        
        This method validates whether an intent can be executed within
        the constraints of the simulation (budget, logistics, physical laws).
        
        Args:
            intent: The intent to check
            world_state: Current world state
        
        Returns:
            FeasibilityReport with assessment details
        """
        pass
    
    @abstractmethod
    def generate_rationale(self, result: AdjudicationResult) -> str:
        """
        Generate a human-readable rationale for an adjudication result.
        
        This is used for traceability - allowing the Forge to display
        why a certain strategic move succeeded or failed.
        
        Args:
            result: The adjudication result
        
        Returns:
            Human-readable rationale string
        """
        pass

