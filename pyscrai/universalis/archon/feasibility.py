"""
Feasibility Engine - Constraint checking for PyScrAI Universalis.

This module provides mathematical constraint checking to determine
if an intent is feasible given the current world state.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

from pyscrai.data.schemas.models import WorldState, Actor, Asset
from pyscrai.universalis.archon.interface import FeasibilityReport
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


class ConstraintType(str, Enum):
    """Types of constraints that can be checked."""
    BUDGET = "budget"
    LOGISTICS = "logistics"
    PHYSICAL = "physical"
    TEMPORAL = "temporal"
    RESOURCE = "resource"
    POLICY = "policy"


@dataclass
class Constraint:
    """A single constraint to be checked."""
    name: str
    constraint_type: ConstraintType
    check_fn: Callable[[str, WorldState], bool]
    error_message: str = ""
    

class FeasibilityEngine:
    """
    Engine for checking feasibility of intents.
    
    Validates whether an intent can be executed within the constraints
    of the simulation (budget, logistics, physical laws, etc.).
    """
    
    def __init__(self):
        """Initialize the feasibility engine with default constraints."""
        self._constraints: List[Constraint] = []
        self._register_default_constraints()
    
    def _register_default_constraints(self) -> None:
        """Register the default set of constraints."""
        # Resource availability constraint
        self._constraints.append(Constraint(
            name="resource_availability",
            constraint_type=ConstraintType.RESOURCE,
            check_fn=self._check_resource_availability,
            error_message="Required resources are not available"
        ))
        
        # Asset status constraint
        self._constraints.append(Constraint(
            name="asset_operational",
            constraint_type=ConstraintType.PHYSICAL,
            check_fn=self._check_asset_operational,
            error_message="Referenced asset is not operational"
        ))
        
        # Actor authorization constraint
        self._constraints.append(Constraint(
            name="actor_authorized",
            constraint_type=ConstraintType.POLICY,
            check_fn=self._check_actor_authorization,
            error_message="Actor is not authorized to perform this action"
        ))
    
    def register_constraint(self, constraint: Constraint) -> None:
        """
        Register a new constraint.
        
        Args:
            constraint: The constraint to register
        """
        self._constraints.append(constraint)
        logger.info(f"Registered constraint: {constraint.name}")
    
    def check_feasibility(
        self, 
        intent: str, 
        world_state: WorldState,
        actor_id: Optional[str] = None
    ) -> FeasibilityReport:
        """
        Check if an intent is feasible given the world state.
        
        Args:
            intent: The intent string to check
            world_state: Current world state
            actor_id: Optional actor ID for authorization checks
        
        Returns:
            FeasibilityReport with assessment details
        """
        violations = []
        constraints_checked = []
        recommendations = []
        
        for constraint in self._constraints:
            constraints_checked.append(constraint.name)
            
            try:
                is_valid = constraint.check_fn(intent, world_state)
                if not is_valid:
                    violations.append({
                        "constraint": constraint.name,
                        "type": constraint.constraint_type.value,
                        "message": constraint.error_message
                    })
            except Exception as e:
                logger.warning(f"Constraint check {constraint.name} failed: {e}")
                # Don't add as violation, just log the error
        
        # Generate recommendations for violations
        for violation in violations:
            rec = self._generate_recommendation(violation, world_state)
            if rec:
                recommendations.append(rec)
        
        feasible = len(violations) == 0
        
        return FeasibilityReport(
            feasible=feasible,
            intent=intent,
            constraints_checked=constraints_checked,
            violations=violations,
            recommendations=recommendations
        )
    
    def _check_resource_availability(
        self, 
        intent: str, 
        world_state: WorldState
    ) -> bool:
        """
        Check if required resources are available.
        
        This is a basic implementation that checks if mentioned assets exist.
        """
        # Extract asset references from intent (simple keyword matching)
        for asset_id, asset in world_state.assets.items():
            if asset_id.lower() in intent.lower() or asset.name.lower() in intent.lower():
                # Check if asset has required attributes
                if asset.status == "destroyed" or asset.status == "unavailable":
                    return False
                
                # Check fuel/resource levels if applicable
                if "fuel" in asset.attributes:
                    if asset.attributes["fuel"] <= 0:
                        return False
        
        return True
    
    def _check_asset_operational(
        self, 
        intent: str, 
        world_state: WorldState
    ) -> bool:
        """
        Check if referenced assets are operational.
        """
        for asset_id, asset in world_state.assets.items():
            if asset_id.lower() in intent.lower() or asset.name.lower() in intent.lower():
                if asset.status not in ["active", "ready", "standby"]:
                    return False
        
        return True
    
    def _check_actor_authorization(
        self, 
        intent: str, 
        world_state: WorldState
    ) -> bool:
        """
        Check if actor is authorized to perform the action.
        
        This checks if an actor controls the assets they're trying to use.
        """
        # Extract actor references from intent
        for actor_id, actor in world_state.actors.items():
            if actor_id.lower() in intent.lower():
                # Check if actor controls mentioned assets
                for asset_id in world_state.assets.keys():
                    if asset_id.lower() in intent.lower():
                        if asset_id not in actor.assets:
                            return False
        
        return True
    
    def _generate_recommendation(
        self, 
        violation: Dict[str, Any], 
        world_state: WorldState
    ) -> Optional[str]:
        """
        Generate a recommendation for resolving a constraint violation.
        
        Args:
            violation: The violation details
            world_state: Current world state
        
        Returns:
            Recommendation string or None
        """
        constraint_type = violation.get("type")
        
        if constraint_type == ConstraintType.RESOURCE.value:
            return "Consider reallocating resources or waiting for replenishment"
        elif constraint_type == ConstraintType.PHYSICAL.value:
            return "Asset may need repairs or status update before use"
        elif constraint_type == ConstraintType.POLICY.value:
            return "Request authorization or use assets under your control"
        elif constraint_type == ConstraintType.BUDGET.value:
            return "Review budget allocation or reduce scope of operation"
        elif constraint_type == ConstraintType.LOGISTICS.value:
            return "Consider alternative routes or staging areas"
        
        return None
    
    def check_budget_constraint(
        self, 
        cost: float, 
        available_budget: float
    ) -> bool:
        """
        Utility method to check budget constraints.
        
        Args:
            cost: Cost of the proposed action
            available_budget: Available budget
        
        Returns:
            True if within budget, False otherwise
        """
        return cost <= available_budget
    
    def check_distance_constraint(
        self, 
        origin: Dict[str, float], 
        destination: Dict[str, float], 
        max_distance: float
    ) -> bool:
        """
        Utility method to check distance constraints.
        
        Args:
            origin: Origin location {"lat": float, "lon": float}
            destination: Destination location {"lat": float, "lon": float}
            max_distance: Maximum allowed distance
        
        Returns:
            True if within distance, False otherwise
        """
        # Simple Euclidean distance (for more accuracy, use Haversine)
        import math
        
        lat_diff = origin.get("lat", 0) - destination.get("lat", 0)
        lon_diff = origin.get("lon", 0) - destination.get("lon", 0)
        distance = math.sqrt(lat_diff**2 + lon_diff**2)
        
        return distance <= max_distance
    
    def check_time_constraint(
        self, 
        required_time: float, 
        available_time: float
    ) -> bool:
        """
        Utility method to check time constraints.
        
        Args:
            required_time: Time required for the action
            available_time: Time available
        
        Returns:
            True if within time, False otherwise
        """
        return required_time <= available_time

