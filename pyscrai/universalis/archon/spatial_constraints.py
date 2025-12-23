"""
Spatial Constraints - DuckDB-based constraint checking for PyScrAI Universalis.

This module provides SQL-based constraint checking using DuckDB Spatial
extension for geographic feasibility validation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from pyscrai.data.schemas.models import WorldState, Location
from pyscrai.universalis.state.duckdb_manager import DuckDBStateManager, get_state_manager
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


class SpatialConstraintType(str, Enum):
    """Types of spatial constraints."""
    DISTANCE = "distance"
    TERRAIN = "terrain"
    PATH = "path"
    PROXIMITY = "proximity"
    ZONE = "zone"


@dataclass
class SpatialConstraintResult:
    """Result of a spatial constraint check."""
    passed: bool
    constraint_type: SpatialConstraintType
    message: str
    details: Dict[str, Any]


class SpatialConstraintChecker:
    """
    DuckDB-based spatial constraint checker.
    
    Uses SQL queries to validate spatial constraints like:
    - Distance limits between entities
    - Terrain passability
    - Path blocking by impassable terrain
    - Zone restrictions
    """
    
    def __init__(
        self,
        state_manager: Optional[DuckDBStateManager] = None,
        simulation_id: Optional[str] = None
    ):
        """
        Initialize the spatial constraint checker.
        
        Args:
            state_manager: DuckDB state manager (uses global if not provided)
            simulation_id: Simulation ID for queries
        """
        self._state_manager = state_manager or get_state_manager(simulation_id)
        self._simulation_id = simulation_id or self._state_manager._simulation_id
    
    def check_distance_constraint(
        self,
        entity1_id: str,
        entity2_id: str,
        max_distance_degrees: float
    ) -> SpatialConstraintResult:
        """
        Check if two entities are within maximum distance.
        
        Args:
            entity1_id: First entity ID
            entity2_id: Second entity ID
            max_distance_degrees: Maximum allowed distance in degrees
        
        Returns:
            SpatialConstraintResult with check outcome
        """
        distance = self._state_manager.calculate_distance(entity1_id, entity2_id)
        
        if distance is None:
            return SpatialConstraintResult(
                passed=False,
                constraint_type=SpatialConstraintType.DISTANCE,
                message=f"Could not find entities {entity1_id} and/or {entity2_id}",
                details={"entity1": entity1_id, "entity2": entity2_id}
            )
        
        passed = distance <= max_distance_degrees
        
        return SpatialConstraintResult(
            passed=passed,
            constraint_type=SpatialConstraintType.DISTANCE,
            message=f"Distance {distance:.4f}° {'<=' if passed else '>'} {max_distance_degrees}°",
            details={
                "entity1": entity1_id,
                "entity2": entity2_id,
                "distance": distance,
                "max_distance": max_distance_degrees,
                "distance_km_approx": distance * 111  # Rough conversion
            }
        )
    
    def check_terrain_passability(
        self,
        lon: float,
        lat: float
    ) -> SpatialConstraintResult:
        """
        Check if a location has passable terrain.
        
        Args:
            lon: Longitude
            lat: Latitude
        
        Returns:
            SpatialConstraintResult with terrain info
        """
        terrain = self._state_manager.get_terrain_at_point(lon, lat)
        
        if terrain is None:
            # No terrain defined = passable (default)
            return SpatialConstraintResult(
                passed=True,
                constraint_type=SpatialConstraintType.TERRAIN,
                message="No terrain restrictions at this location",
                details={"lon": lon, "lat": lat, "terrain": None}
            )
        
        passed = terrain['passable']
        
        return SpatialConstraintResult(
            passed=passed,
            constraint_type=SpatialConstraintType.TERRAIN,
            message=f"Terrain '{terrain['name']}' ({terrain['terrain_type']}) is {'passable' if passed else 'impassable'}",
            details={
                "lon": lon,
                "lat": lat,
                "terrain": terrain['name'],
                "terrain_type": terrain['terrain_type'],
                "movement_cost": terrain['movement_cost'],
                "passable": passed
            }
        )
    
    def check_path_constraint(
        self,
        start_lon: float,
        start_lat: float,
        end_lon: float,
        end_lat: float
    ) -> SpatialConstraintResult:
        """
        Check if a path between two points is passable.
        
        Args:
            start_lon, start_lat: Starting point
            end_lon, end_lat: Ending point
        
        Returns:
            SpatialConstraintResult with path feasibility
        """
        is_blocked, blocker = self._state_manager.check_path_blocked(
            start_lon, start_lat, end_lon, end_lat
        )
        
        if is_blocked:
            return SpatialConstraintResult(
                passed=False,
                constraint_type=SpatialConstraintType.PATH,
                message=f"Path blocked by {blocker}",
                details={
                    "start": {"lon": start_lon, "lat": start_lat},
                    "end": {"lon": end_lon, "lat": end_lat},
                    "blocker": blocker
                }
            )
        
        # Calculate path cost
        cost = self._state_manager.calculate_path_cost(
            start_lon, start_lat, end_lon, end_lat
        )
        
        return SpatialConstraintResult(
            passed=True,
            constraint_type=SpatialConstraintType.PATH,
            message=f"Path clear with movement cost {cost:.2f}",
            details={
                "start": {"lon": start_lon, "lat": start_lat},
                "end": {"lon": end_lon, "lat": end_lat},
                "movement_cost": cost
            }
        )
    
    def check_proximity_constraint(
        self,
        entity_id: str,
        target_lon: float,
        target_lat: float,
        min_distance_degrees: float = 0,
        max_distance_degrees: float = float('inf')
    ) -> SpatialConstraintResult:
        """
        Check if an entity is within a distance range of a point.
        
        Args:
            entity_id: Entity to check
            target_lon, target_lat: Target point
            min_distance_degrees: Minimum required distance
            max_distance_degrees: Maximum allowed distance
        
        Returns:
            SpatialConstraintResult with proximity info
        """
        # Get entity location
        entities = self._state_manager.get_entities_within_distance(
            center_lon=target_lon,
            center_lat=target_lat,
            distance_degrees=max_distance_degrees * 2  # Search wider
        )
        
        entity = next((e for e in entities if e['id'] == entity_id), None)
        
        if entity is None:
            return SpatialConstraintResult(
                passed=False,
                constraint_type=SpatialConstraintType.PROXIMITY,
                message=f"Entity {entity_id} not found or too far",
                details={"entity_id": entity_id}
            )
        
        distance = entity['distance']
        passed = min_distance_degrees <= distance <= max_distance_degrees
        
        return SpatialConstraintResult(
            passed=passed,
            constraint_type=SpatialConstraintType.PROXIMITY,
            message=f"Entity at distance {distance:.4f}° ({'within' if passed else 'outside'} range)",
            details={
                "entity_id": entity_id,
                "distance": distance,
                "min_distance": min_distance_degrees,
                "max_distance": max_distance_degrees,
                "target": {"lon": target_lon, "lat": target_lat}
            }
        )
    
    def check_zone_constraint(
        self,
        lon: float,
        lat: float,
        allowed_terrain_types: Optional[List[str]] = None,
        forbidden_terrain_types: Optional[List[str]] = None
    ) -> SpatialConstraintResult:
        """
        Check if a location is in an allowed/forbidden zone.
        
        Args:
            lon: Longitude
            lat: Latitude
            allowed_terrain_types: List of allowed terrain types (if specified)
            forbidden_terrain_types: List of forbidden terrain types
        
        Returns:
            SpatialConstraintResult with zone check result
        """
        terrain = self._state_manager.get_terrain_at_point(lon, lat)
        
        if terrain is None:
            # No terrain = allowed by default
            return SpatialConstraintResult(
                passed=True,
                constraint_type=SpatialConstraintType.ZONE,
                message="No zone restrictions at this location",
                details={"lon": lon, "lat": lat}
            )
        
        terrain_type = terrain['terrain_type']
        
        # Check forbidden types
        if forbidden_terrain_types and terrain_type in forbidden_terrain_types:
            return SpatialConstraintResult(
                passed=False,
                constraint_type=SpatialConstraintType.ZONE,
                message=f"Location in forbidden zone: {terrain_type}",
                details={
                    "lon": lon,
                    "lat": lat,
                    "terrain_type": terrain_type,
                    "forbidden_types": forbidden_terrain_types
                }
            )
        
        # Check allowed types
        if allowed_terrain_types and terrain_type not in allowed_terrain_types:
            return SpatialConstraintResult(
                passed=False,
                constraint_type=SpatialConstraintType.ZONE,
                message=f"Location not in allowed zone: {terrain_type} not in {allowed_terrain_types}",
                details={
                    "lon": lon,
                    "lat": lat,
                    "terrain_type": terrain_type,
                    "allowed_types": allowed_terrain_types
                }
            )
        
        return SpatialConstraintResult(
            passed=True,
            constraint_type=SpatialConstraintType.ZONE,
            message=f"Location in valid zone: {terrain_type}",
            details={
                "lon": lon,
                "lat": lat,
                "terrain_type": terrain_type
            }
        )
    
    def validate_movement(
        self,
        entity_id: str,
        target_lon: float,
        target_lat: float,
        max_distance_degrees: Optional[float] = None
    ) -> Tuple[bool, List[SpatialConstraintResult]]:
        """
        Validate if an entity can move to a target location.
        
        Checks:
        1. Distance constraint (if max_distance specified)
        2. Terrain passability at target
        3. Path clearance
        
        Args:
            entity_id: Entity to move
            target_lon, target_lat: Target coordinates
            max_distance_degrees: Maximum movement distance (optional)
        
        Returns:
            Tuple of (all_passed, list of constraint results)
        """
        results = []
        
        # Get entity's current location
        entities = self._state_manager.get_entities_within_distance(
            center_lon=target_lon,
            center_lat=target_lat,
            distance_degrees=1.0  # Search within 1 degree
        )
        
        entity = next((e for e in entities if e['id'] == entity_id), None)
        
        if entity is None:
            # Entity not found - try to get it directly
            conn = self._state_manager._conn
            result = conn.execute("""
                SELECT ST_X(geometry) as lon, ST_Y(geometry) as lat
                FROM entities
                WHERE id = ? AND simulation_id = ?
            """, [entity_id, self._simulation_id]).fetchone()
            
            if result is None:
                return False, [SpatialConstraintResult(
                    passed=False,
                    constraint_type=SpatialConstraintType.DISTANCE,
                    message=f"Entity {entity_id} not found",
                    details={"entity_id": entity_id}
                )]
            
            start_lon, start_lat = result
        else:
            start_lon, start_lat = entity['lon'], entity['lat']
        
        # Check distance if specified
        if max_distance_degrees is not None:
            import math
            distance = math.sqrt((target_lon - start_lon)**2 + (target_lat - start_lat)**2)
            
            result = SpatialConstraintResult(
                passed=distance <= max_distance_degrees,
                constraint_type=SpatialConstraintType.DISTANCE,
                message=f"Movement distance {distance:.4f}° {'<=' if distance <= max_distance_degrees else '>'} {max_distance_degrees}°",
                details={
                    "distance": distance,
                    "max_distance": max_distance_degrees
                }
            )
            results.append(result)
        
        # Check terrain at target
        terrain_result = self.check_terrain_passability(target_lon, target_lat)
        results.append(terrain_result)
        
        # Check path
        path_result = self.check_path_constraint(start_lon, start_lat, target_lon, target_lat)
        results.append(path_result)
        
        all_passed = all(r.passed for r in results)
        
        return all_passed, results

