"""
Feasibility Engine - Constraint checking for PyScrAI Universalis.

This module provides constraint checking to determine if an intent is 
feasible given the current world state. Uses DuckDB spatial queries
for geographic constraints.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

from pyscrai.data.schemas.models import WorldState, Actor, Asset, Location
from pyscrai.universalis.archon.interface import FeasibilityReport
from pyscrai.universalis.archon.spatial_constraints import (
    SpatialConstraintChecker,
    SpatialConstraintResult,
    SpatialConstraintType
)
from pyscrai.universalis.state.duckdb_manager import get_state_manager
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
    SPATIAL = "spatial"


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
    of the simulation (budget, logistics, physical laws, spatial constraints).
    Uses DuckDB spatial queries for geographic validation.
    """
    
    def __init__(self, simulation_id: Optional[str] = None):
        """
        Initialize the feasibility engine with default constraints.
        
        Args:
            simulation_id: Optional simulation ID for spatial queries
        """
        self._constraints: List[Constraint] = []
        self._spatial_checker: Optional[SpatialConstraintChecker] = None
        self._simulation_id = simulation_id
        
        self._register_default_constraints()
    
    def _get_spatial_checker(self) -> SpatialConstraintChecker:
        """Get or create the spatial constraint checker."""
        if self._spatial_checker is None:
            self._spatial_checker = SpatialConstraintChecker(
                simulation_id=self._simulation_id
            )
        return self._spatial_checker
    
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
        
        # Spatial movement constraint
        self._constraints.append(Constraint(
            name="spatial_movement",
            constraint_type=ConstraintType.SPATIAL,
            check_fn=self._check_spatial_movement,
            error_message="Movement blocked by terrain or distance"
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
    
    def _check_spatial_movement(
        self,
        intent: str,
        world_state: WorldState
    ) -> bool:
        """
        Check if spatial movement in the intent is feasible.
        
        Parses intent for movement-related keywords and validates:
        - Target location is passable terrain
        - Path to target is not blocked
        """
        # Check for movement keywords
        movement_keywords = ['move', 'go', 'travel', 'deploy', 'relocate', 'dispatch', 'send']
        has_movement = any(kw in intent.lower() for kw in movement_keywords)
        
        if not has_movement:
            return True  # No movement to validate
        
        # Try to extract coordinates from intent
        # Pattern: lat/lon pairs like "34.05, -118.25" or "to (34.05, -118.25)"
        coord_pattern = r'[-]?\d+\.?\d*[,\s]+[-]?\d+\.?\d*'
        matches = re.findall(coord_pattern, intent)
        
        if not matches:
            return True  # No coordinates to validate
        
        try:
            spatial_checker = self._get_spatial_checker()
            
            for match in matches:
                parts = re.split(r'[,\s]+', match.strip())
                if len(parts) >= 2:
                    try:
                        lat = float(parts[0])
                        lon = float(parts[1])
                        
                        # Check terrain passability
                        result = spatial_checker.check_terrain_passability(lon, lat)
                        if not result.passed:
                            logger.warning(f"Spatial constraint failed: {result.message}")
                            return False
                    except ValueError:
                        continue
            
            return True
        except Exception as e:
            logger.warning(f"Spatial constraint check error: {e}")
            return True  # Default to allowing if spatial check fails
    
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
        elif constraint_type == ConstraintType.SPATIAL.value:
            return "Choose a different route or destination to avoid impassable terrain"
        
        return None
    
    # =========================================================================
    # SPATIAL CONSTRAINT METHODS (DuckDB-backed)
    # =========================================================================
    
    def check_movement_feasibility(
        self,
        entity_id: str,
        target_lon: float,
        target_lat: float,
        max_distance_degrees: Optional[float] = None
    ) -> FeasibilityReport:
        """
        Check if an entity can move to a target location using spatial queries.
        
        Args:
            entity_id: Entity to move
            target_lon, target_lat: Target coordinates
            max_distance_degrees: Maximum movement distance
        
        Returns:
            FeasibilityReport with spatial constraint results
        """
        spatial_checker = self._get_spatial_checker()
        
        passed, results = spatial_checker.validate_movement(
            entity_id=entity_id,
            target_lon=target_lon,
            target_lat=target_lat,
            max_distance_degrees=max_distance_degrees
        )
        
        violations = []
        for result in results:
            if not result.passed:
                violations.append({
                    "constraint": result.constraint_type.value,
                    "type": ConstraintType.SPATIAL.value,
                    "message": result.message,
                    "details": result.details
                })
        
        recommendations = []
        if not passed:
            recommendations.append("Consider alternative routes or closer destinations")
        
        return FeasibilityReport(
            feasible=passed,
            intent=f"Move {entity_id} to ({target_lon}, {target_lat})",
            constraints_checked=[r.constraint_type.value for r in results],
            violations=violations,
            recommendations=recommendations
        )
    
    def check_distance_constraint(
        self,
        entity1_id: str,
        entity2_id: str,
        max_distance_degrees: float
    ) -> bool:
        """
        Check if two entities are within maximum distance using spatial SQL.
        
        Args:
            entity1_id: First entity ID
            entity2_id: Second entity ID
            max_distance_degrees: Maximum allowed distance
        
        Returns:
            True if within distance, False otherwise
        """
        spatial_checker = self._get_spatial_checker()
        result = spatial_checker.check_distance_constraint(
            entity1_id, entity2_id, max_distance_degrees
        )
        return result.passed
    
    def check_path_feasibility(
        self,
        start_lon: float,
        start_lat: float,
        end_lon: float,
        end_lat: float
    ) -> tuple:
        """
        Check if a path between two points is feasible.
        
        Args:
            start_lon, start_lat: Starting coordinates
            end_lon, end_lat: Ending coordinates
        
        Returns:
            Tuple of (is_feasible, movement_cost, blocker_name)
        """
        spatial_checker = self._get_spatial_checker()
        result = spatial_checker.check_path_constraint(
            start_lon, start_lat, end_lon, end_lat
        )
        
        if result.passed:
            return True, result.details.get('movement_cost', 1.0), None
        else:
            return False, float('inf'), result.details.get('blocker')
    
    # =========================================================================
    # LEGACY UTILITY METHODS (kept for backward compatibility)
    # =========================================================================
    
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
