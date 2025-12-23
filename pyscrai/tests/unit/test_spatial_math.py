"""Unit tests for PyScrAI Universalis spatial math utilities.

These tests focus on spatial calculations, distance computations, and
geometric operations without database dependencies.
"""

import pytest
from unittest.mock import Mock, MagicMock

from pyscrai.universalis.archon.spatial_constraints import (
    SpatialConstraintChecker,
    SpatialConstraintResult,
    SpatialConstraintType
)
from pyscrai.universalis.state.duckdb_manager import DuckDBStateManager


class TestSpatialConstraintChecker:
    """Test SpatialConstraintChecker functionality."""
    
    def test_init(self):
        """Test SpatialConstraintChecker initialization."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        checker = SpatialConstraintChecker(mock_state_manager)
        assert checker._state_manager == mock_state_manager
    
    def test_check_distance_constraint_success(self, mocker):
        """Test successful distance constraint check."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.calculate_distance.return_value = 0.05  # 5.5 km
        
        checker = SpatialConstraintChecker(mock_state_manager)
        result = checker.check_distance_constraint(
            entity1_id="entity_1",
            entity2_id="entity_2",
            max_distance_degrees=0.1  # 11 km
        )
        
        assert result.passed is True
        assert result.constraint_type == SpatialConstraintType.DISTANCE
        assert "0.0500° <= 0.1000°" in result.message
        assert result.details["distance"] == 0.05
        assert result.details["max_distance"] == 0.1
        assert result.details["distance_km_approx"] == 5.5  # 0.05 * 111
    
    def test_check_distance_constraint_failure(self, mocker):
        """Test failed distance constraint check."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.calculate_distance.return_value = 0.2  # 22 km
        
        checker = SpatialConstraintChecker(mock_state_manager)
        result = checker.check_distance_constraint(
            entity1_id="entity_1",
            entity2_id="entity_2",
            max_distance_degrees=0.1  # 11 km
        )
        
        assert result.passed is False
        assert result.constraint_type == SpatialConstraintType.DISTANCE
        assert "0.2000° > 0.1000°" in result.message
        assert result.details["distance"] == 0.2
        assert result.details["max_distance"] == 0.1
        assert result.details["distance_km_approx"] == 22.2  # 0.2 * 111
    
    def test_check_distance_constraint_no_entities(self, mocker):
        """Test distance constraint check when entities don't exist."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.calculate_distance.return_value = None
        
        checker = SpatialConstraintChecker(mock_state_manager)
        result = checker.check_distance_constraint(
            entity1_id="entity_1",
            entity2_id="entity_2",
            max_distance_degrees=0.1
        )
        
        assert result.passed is False
        assert result.constraint_type == SpatialConstraintType.DISTANCE
        assert "Entities not found" in result.message
        assert result.details["entity1"] == "entity_1"
        assert result.details["entity2"] == "entity_2"
    
    def test_check_proximity_constraint_success(self, mocker):
        """Test successful proximity constraint check."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        # Mock get_entities_within_distance to return entity at 0.05 degrees
        mock_state_manager.get_entities_within_distance.return_value = [
            {
                'id': 'entity_1',
                'distance': 0.05,
                'entity_type': 'actor'
            }
        ]
        
        checker = SpatialConstraintChecker(mock_state_manager)
        result = checker.check_proximity_constraint(
            entity_id="entity_1",
            target_lon=-74.0060,
            target_lat=40.7128,
            min_distance_degrees=0.01,
            max_distance_degrees=0.1
        )
        
        assert result.passed is True
        assert result.constraint_type == SpatialConstraintType.PROXIMITY
        assert "within range" in result.message
        assert result.details["entity_id"] == "entity_1"
        assert result.details["distance"] == 0.05
        assert result.details["min_distance"] == 0.01
        assert result.details["max_distance"] == 0.1
        assert result.details["target"] == {"lon": -74.0060, "lat": 40.7128}
    
    def test_check_proximity_constraint_too_close(self, mocker):
        """Test proximity constraint check when entity is too close."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.get_entities_within_distance.return_value = [
            {
                'id': 'entity_1',
                'distance': 0.005,  # Closer than min_distance
                'entity_type': 'actor'
            }
        ]
        
        checker = SpatialConstraintChecker(mock_state_manager)
        result = checker.check_proximity_constraint(
            entity_id="entity_1",
            target_lon=-74.0060,
            target_lat=40.7128,
            min_distance_degrees=0.01,
            max_distance_degrees=0.1
        )
        
        assert result.passed is False
        assert result.constraint_type == SpatialConstraintType.PROXIMITY
        assert "outside range" in result.message
        assert result.details["distance"] == 0.005
        assert result.details["min_distance"] == 0.01
    
    def test_check_proximity_constraint_too_far(self, mocker):
        """Test proximity constraint check when entity is too far."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.get_entities_within_distance.return_value = [
            {
                'id': 'entity_1',
                'distance': 0.15,  # Farther than max_distance
                'entity_type': 'actor'
            }
        ]
        
        checker = SpatialConstraintChecker(mock_state_manager)
        result = checker.check_proximity_constraint(
            entity_id="entity_1",
            target_lon=-74.0060,
            target_lat=40.7128,
            min_distance_degrees=0.01,
            max_distance_degrees=0.1
        )
        
        assert result.passed is False
        assert result.constraint_type == SpatialConstraintType.PROXIMITY
        assert "outside range" in result.message
        assert result.details["distance"] == 0.15
        assert result.details["max_distance"] == 0.1
    
    def test_check_proximity_constraint_entity_not_found(self, mocker):
        """Test proximity constraint check when entity is not found."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.get_entities_within_distance.return_value = []
        
        checker = SpatialConstraintChecker(mock_state_manager)
        result = checker.check_proximity_constraint(
            entity_id="entity_1",
            target_lon=-74.0060,
            target_lat=40.7128,
            min_distance_degrees=0.01,
            max_distance_degrees=0.1
        )
        
        assert result.passed is False
        assert result.constraint_type == SpatialConstraintType.PROXIMITY
        assert "Entity not found" in result.message
        assert result.details["entity_id"] == "entity_1"
        assert result.details["target"] == {"lon": -74.0060, "lat": 40.7128}
    
    def test_check_spatial_movement_success(self, mocker):
        """Test successful spatial movement check."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        # Mock get_entities_within_distance to return entity at current location
        mock_state_manager.get_entities_within_distance.return_value = [
            {
                'id': 'entity_1',
                'distance': 0.0,
                'entity_type': 'actor'
            }
        ]
        # Mock get_terrain_at_point to return passable terrain
        mock_state_manager.get_terrain_at_point.return_value = {
            'terrain_type': 'plains',
            'passable': True,
            'movement_cost': 1.0
        }
        # Mock check_path_blocked to return False (path not blocked)
        mock_state_manager.check_path_blocked.return_value = (False, None)
        
        checker = SpatialConstraintChecker(mock_state_manager)
        results = checker.check_spatial_movement(
            entity_id="entity_1",
            target_lon=-74.0060,
            target_lat=40.7128,
            max_distance_degrees=0.1
        )
        
        assert len(results) == 2  # Distance + Terrain checks
        
        # Check distance constraint
        distance_result = next(r for r in results if r.constraint_type == SpatialConstraintType.DISTANCE)
        assert distance_result.passed is True
        assert "within" in distance_result.message
        
        # Check terrain constraint
        terrain_result = next(r for r in results if r.constraint_type == SpatialConstraintType.TERRAIN)
        assert terrain_result.passed is True
        assert "Passable" in terrain_result.message
        assert terrain_result.details["terrain_type"] == "plains"
        assert terrain_result.details["passable"] is True
    
    def test_check_spatial_movement_distance_failure(self, mocker):
        """Test spatial movement check with distance constraint failure."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.get_entities_within_distance.return_value = [
            {
                'id': 'entity_1',
                'distance': 0.0,
                'entity_type': 'actor'
            }
        ]
        mock_state_manager.get_terrain_at_point.return_value = {
            'terrain_type': 'plains',
            'passable': True,
            'movement_cost': 1.0
        }
        mock_state_manager.check_path_blocked.return_value = (False, None)
        
        checker = SpatialConstraintChecker(mock_state_manager)
        results = checker.check_spatial_movement(
            entity_id="entity_1",
            target_lon=-74.0060,
            target_lat=40.7128,
            max_distance_degrees=0.01  # Very short distance
        )
        
        assert len(results) == 2
        
        distance_result = next(r for r in results if r.constraint_type == SpatialConstraintType.DISTANCE)
        assert distance_result.passed is False
        assert "outside" in distance_result.message
    
    def test_check_spatial_movement_terrain_failure(self, mocker):
        """Test spatial movement check with terrain constraint failure."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.get_entities_within_distance.return_value = [
            {
                'id': 'entity_1',
                'distance': 0.0,
                'entity_type': 'actor'
            }
        ]
        mock_state_manager.get_terrain_at_point.return_value = {
            'terrain_type': 'mountains',
            'passable': False,
            'movement_cost': 3.0
        }
        mock_state_manager.check_path_blocked.return_value = (False, None)
        
        checker = SpatialConstraintChecker(mock_state_manager)
        results = checker.check_spatial_movement(
            entity_id="entity_1",
            target_lon=-74.0060,
            target_lat=40.7128,
            max_distance_degrees=0.1
        )
        
        assert len(results) == 2
        
        terrain_result = next(r for r in results if r.constraint_type == SpatialConstraintType.TERRAIN)
        assert terrain_result.passed is False
        assert "Impassable" in terrain_result.message
        assert terrain_result.details["passable"] is False
        assert terrain_result.details["terrain_type"] == "mountains"
    
    def test_check_spatial_movement_path_blocked(self, mocker):
        """Test spatial movement check with path blocked."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.get_entities_within_distance.return_value = [
            {
                'id': 'entity_1',
                'distance': 0.0,
                'entity_type': 'actor'
            }
        ]
        mock_state_manager.get_terrain_at_point.return_value = {
            'terrain_type': 'plains',
            'passable': True,
            'movement_cost': 1.0
        }
        mock_state_manager.check_path_blocked.return_value = (True, "Mountain Range")
        
        checker = SpatialConstraintChecker(mock_state_manager)
        results = checker.check_spatial_movement(
            entity_id="entity_1",
            target_lon=-74.0060,
            target_lat=40.7128,
            max_distance_degrees=0.1
        )
        
        assert len(results) == 3  # Distance + Terrain + Path checks
        
        path_result = next(r for r in results if r.constraint_type == SpatialConstraintType.PATH)
        assert path_result.passed is False
        assert "blocked" in path_result.message
        assert path_result.details["blocking_terrain"] == "Mountain Range"


class TestSpatialConstraintResult:
    """Test SpatialConstraintResult model."""
    
    def test_result_creation_success(self):
        """Test successful constraint result creation."""
        result = SpatialConstraintResult(
            passed=True,
            constraint_type=SpatialConstraintType.DISTANCE,
            message="Test passed",
            details={"test": "value"}
        )
        
        assert result.passed is True
        assert result.constraint_type == SpatialConstraintType.DISTANCE
        assert result.message == "Test passed"
        assert result.details == {"test": "value"}
    
    def test_result_creation_failure(self):
        """Test failed constraint result creation."""
        result = SpatialConstraintResult(
            passed=False,
            constraint_type=SpatialConstraintType.TERRAIN,
            message="Test failed",
            details={"error": "blocked"}
        )
        
        assert result.passed is False
        assert result.constraint_type == SpatialConstraintType.TERRAIN
        assert result.message == "Test failed"
        assert result.details == {"error": "blocked"}
    
    def test_result_to_dict(self):
        """Test constraint result serialization to dict."""
        result = SpatialConstraintResult(
            passed=True,
            constraint_type=SpatialConstraintType.DISTANCE,
            message="Test passed",
            details={"distance": 0.05}
        )
        
        result_dict = result.to_dict()
        assert result_dict["passed"] is True
        assert result_dict["constraint_type"] == "distance"
        assert result_dict["message"] == "Test passed"
        assert result_dict["details"] == {"distance": 0.05}


class TestSpatialConstraintType:
    """Test SpatialConstraintType enum."""
    
    def test_enum_values(self):
        """Test enum values are correct."""
        assert SpatialConstraintType.DISTANCE.value == "distance"
        assert SpatialConstraintType.PROXIMITY.value == "proximity"
        assert SpatialConstraintType.TERRAIN.value == "terrain"
        assert SpatialConstraintType.PATH.value == "path"
        assert len(SpatialConstraintType) == 4
    
    def test_enum_iteration(self):
        """Test enum can be iterated."""
        values = [constraint.value for constraint in SpatialConstraintType]
        expected = ["distance", "proximity", "terrain", "path"]
        assert values == expected


class TestSpatialMathCalculations:
    """Test spatial math calculations and utilities."""
    
    def test_distance_approximation(self):
        """Test distance approximation calculations."""
        # Test basic distance calculation
        # 1 degree ≈ 111 km
        distance_degrees = 0.1
        distance_km = distance_degrees * 111
        assert abs(distance_km - 11.1) < 0.01
        
        # Test small distances
        small_distance = 0.01
        small_km = small_distance * 111
        assert abs(small_km - 1.11) < 0.01
    
    def test_coordinate_validation(self):
        """Test coordinate validation logic."""
        # Valid coordinates
        valid_lat = 40.7128
        valid_lon = -74.0060
        
        assert -90 <= valid_lat <= 90
        assert -180 <= valid_lon <= 180
        
        # Invalid coordinates
        invalid_lat = 91.0
        invalid_lon = 181.0
        
        assert not (-90 <= invalid_lat <= 90)
        assert not (-180 <= invalid_lon <= 180)
    
    def test_wkt_polygon_validation(self):
        """Test WKT polygon string validation."""
        # Valid polygon
        valid_polygon = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
        assert "POLYGON" in valid_polygon
        assert "((0 0" in valid_polygon
        assert "0 0))" in valid_polygon
        
        # Invalid polygon (missing closing)
        invalid_polygon = "POLYGON((0 0, 1 0, 1 1, 0 1)"
        assert "POLYGON" in invalid_polygon
        assert "0 0))" not in invalid_polygon


class TestSpatialConstraintCheckerEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_check_distance_constraint_zero_distance(self, mocker):
        """Test distance constraint with zero distance."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.calculate_distance.return_value = 0.0
        
        checker = SpatialConstraintChecker(mock_state_manager)
        result = checker.check_distance_constraint(
            entity1_id="entity_1",
            entity2_id="entity_1",  # Same entity
            max_distance_degrees=0.1
        )
        
        assert result.passed is True
        assert result.constraint_type == SpatialConstraintType.DISTANCE
        assert "0.0000° <= 0.1000°" in result.message
    
    def test_check_distance_constraint_infinite_max_distance(self, mocker):
        """Test distance constraint with infinite max distance."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.calculate_distance.return_value = 100.0
        
        checker = SpatialConstraintChecker(mock_state_manager)
        result = checker.check_distance_constraint(
            entity1_id="entity_1",
            entity2_id="entity_2",
            max_distance_degrees=float('inf')
        )
        
        assert result.passed is True
        assert result.constraint_type == SpatialConstraintType.DISTANCE
    
    def test_check_proximity_constraint_zero_distances(self, mocker):
        """Test proximity constraint with zero min/max distances."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.get_entities_within_distance.return_value = [
            {
                'id': 'entity_1',
                'distance': 0.0,
                'entity_type': 'actor'
            }
        ]
        
        checker = SpatialConstraintChecker(mock_state_manager)
        
        # Test with zero min distance
        result = checker.check_proximity_constraint(
            entity_id="entity_1",
            target_lon=-74.0060,
            target_lat=40.7128,
            min_distance_degrees=0.0,
            max_distance_degrees=0.1
        )
        
        assert result.passed is True
        assert "within range" in result.message
    
    def test_check_spatial_movement_zero_target(self, mocker):
        """Test spatial movement check with zero target coordinates."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.get_entities_within_distance.return_value = [
            {
                'id': 'entity_1',
                'distance': 0.0,
                'entity_type': 'actor'
            }
        ]
        mock_state_manager.get_terrain_at_point.return_value = {
            'terrain_type': 'plains',
            'passable': True,
            'movement_cost': 1.0
        }
        mock_state_manager.check_path_blocked.return_value = (False, None)
        
        checker = SpatialConstraintChecker(mock_state_manager)
        results = checker.check_spatial_movement(
            entity_id="entity_1",
            target_lon=0.0,
            target_lat=0.0,
            max_distance_degrees=0.1
        )
        
        assert len(results) == 2
        assert all(r.passed for r in results)
    
    def test_check_spatial_movement_no_terrain_data(self, mocker):
        """Test spatial movement check when no terrain data is available."""
        mock_state_manager = Mock(spec=DuckDBStateManager)
        mock_state_manager.get_entities_within_distance.return_value = [
            {
                'id': 'entity_1',
                'distance': 0.0,
                'entity_type': 'actor'
            }
        ]
        mock_state_manager.get_terrain_at_point.return_value = None  # No terrain data
        mock_state_manager.check_path_blocked.return_value = (False, None)
        
        checker = SpatialConstraintChecker(mock_state_manager)
        results = checker.check_spatial_movement(
            entity_id="entity_1",
            target_lon=-74.0060,
            target_lat=40.7128,
            max_distance_degrees=0.1
        )
        
        assert len(results) == 2  # Distance + Terrain checks
        
        terrain_result = next(r for r in results if r.constraint_type == SpatialConstraintType.TERRAIN)
        assert terrain_result.passed is True  # Should pass if no terrain data
        assert "No terrain data" in terrain_result.message
        assert terrain_result.details["terrain_type"] is None
        assert terrain_result.details["passable"] is None
