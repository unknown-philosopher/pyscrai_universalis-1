"""Test configuration and utilities for PyScrAI Universalis.

This module provides test utilities, configuration helpers, and
common test data for the test suite.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import json

from pyscrai.data.schemas.models import (
    WorldState, Actor, Asset, Environment, Location, Terrain, TerrainType
)


class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_sample_world_state(simulation_id: str = "test_simulation") -> WorldState:
        """Create a sample world state for testing."""
        return WorldState(
            simulation_id=simulation_id,
            environment=Environment(
                cycle=1,
                time="12:00",
                weather="Clear",
                global_events=["Test event 1", "Test event 2"],
                terrain_modifiers={"mountain": 2.0, "forest": 1.5}
            ),
            actors={
                "actor_1": Actor(
                    actor_id="actor_1",
                    role="Commander",
                    description="Test commander",
                    resolution="macro",
                    assets=["asset_1", "asset_2"],
                    objectives=["Objective 1", "Objective 2"],
                    location=Location(lat=40.7128, lon=-74.0060),
                    attributes={"rank": "General", "experience": 10}
                ),
                "actor_2": Actor(
                    actor_id="actor_2",
                    role="Scout",
                    description="Test scout",
                    resolution="micro",
                    assets=["asset_3"],
                    objectives=["Reconnaissance"],
                    location=Location(lat=40.7130, lon=-74.0065),
                    attributes={"speed": 5.0, "stealth": 8.0}
                ),
                "actor_3": Actor(
                    actor_id="actor_3",
                    role="Engineer",
                    description="Test engineer",
                    resolution="macro",
                    assets=[],
                    objectives=["Construction"],
                    location=Location(lat=40.7125, lon=-74.0055),
                    attributes={"skill": "engineering"}
                )
            },
            assets={
                "asset_1": Asset(
                    asset_id="asset_1",
                    name="Tank Unit",
                    asset_type="Ground Unit",
                    location={"lat": 40.7128, "lon": -74.0060, "elevation": 10.0},
                    attributes={"type": "armor", "health": 100, "ammo": 50},
                    status="active"
                ),
                "asset_2": Asset(
                    asset_id="asset_2",
                    name="Supply Truck",
                    asset_type="Logistics",
                    location={"lat": 40.7129, "lon": -74.0061},
                    attributes={"capacity": 1000, "speed": 30.0},
                    status="active"
                ),
                "asset_3": Asset(
                    asset_id="asset_3",
                    name="Recon Drone",
                    asset_type="Air Unit",
                    location={"lat": 40.7130, "lon": -74.0065},
                    attributes={"range": 5000, "battery": 80.0},
                    status="active"
                ),
                "asset_4": Asset(
                    asset_id="asset_4",
                    name="Command Center",
                    asset_type="Building",
                    location={"lat": 40.7120, "lon": -74.0070},
                    attributes={"size": "large", "defenses": 5},
                    status="active"
                )
            }
        )
    
    @staticmethod
    def create_sample_terrain(terrain_id: str = "test_terrain") -> Terrain:
        """Create a sample terrain for testing."""
        return Terrain(
            terrain_id=terrain_id,
            name="Test Terrain",
            terrain_type=TerrainType.PLAINS,
            geometry_wkt="POLYGON((-74.01 40.71, -74.00 40.71, -74.00 40.72, -74.01 40.72, -74.01 40.71))",
            movement_cost=1.0,
            passable=True,
            attributes={"difficulty": "easy"}
        )
    
    @staticmethod
    def create_sample_mountain_terrain() -> Terrain:
        """Create a sample mountain terrain for testing."""
        return Terrain(
            terrain_id="mountain_1",
            name="Test Mountain",
            terrain_type=TerrainType.MOUNTAINS,
            geometry_wkt="POLYGON((-74.01 40.71, -74.00 40.71, -74.00 40.72, -74.01 40.72, -74.01 40.71))",
            movement_cost=3.0,
            passable=False,
            attributes={"elevation": 1500, "difficulty": "hard"}
        )
    
    @staticmethod
    def create_sample_water_terrain() -> Terrain:
        """Create a sample water terrain for testing."""
        return Terrain(
            terrain_id="water_1",
            name="Test Water",
            terrain_type=TerrainType.WATER,
            geometry_wkt="POLYGON((-74.015 40.715, -74.005 40.715, -74.005 40.725, -74.015 40.725, -74.015 40.715))",
            movement_cost=float('inf'),
            passable=False,
            attributes={"depth": 10, "current": "moderate"}
        )
    
    @staticmethod
    def create_large_world_state(simulation_id: str = "large_test_world", num_actors: int = 50, num_assets: int = 100) -> WorldState:
        """Create a large world state for performance testing."""
        world_state = WorldState(simulation_id=simulation_id)
        world_state.environment.terrain_modifiers = {"urban": 1.5, "forest": 2.0, "mountain": 3.0}
        
        # Add many actors
        for i in range(num_actors):
            world_state.actors[f"actor_{i}"] = Actor(
                actor_id=f"actor_{i}",
                role=f"Actor {i}",
                location=Location(lat=40.71 + i * 0.001, lon=-74.00 + i * 0.001),
                attributes={"index": i, "type": "test", "group": f"group_{i % 5}"}
            )
        
        # Add many assets
        for i in range(num_assets):
            world_state.assets[f"asset_{i}"] = Asset(
                asset_id=f"asset_{i}",
                name=f"Asset {i}",
                asset_type="Test Asset",
                location={"lat": 40.71 + i * 0.0005, "lon": -74.00 + i * 0.0005},
                attributes={"index": i, "type": "test", "category": f"category_{i % 10}"}
            )
        
        return world_state


class TestConfigHelper:
    """Helper for test configuration."""
    
    @staticmethod
    def get_test_config() -> Dict[str, Any]:
        """Get a standard test configuration."""
        return {
            "world_id": "test_world",
            "name": "Test World",
            "description": "A test world for functional testing",
            "region_type": "city",
            "coordinates": {"lat": 34.05, "lon": -118.25},
            "climate": "Mediterranean"
        }
    
    @staticmethod
    def get_test_simulation_config() -> Dict[str, Any]:
        """Get a test simulation configuration."""
        return {
            "simulation_id": "test_simulation",
            "tick_interval_ms": 100,
            "auto_run": False,
            "perception_radius_degrees": 0.1
        }


class TestDatabaseHelper:
    """Helper for test database operations."""
    
    @staticmethod
    def create_temp_db_path() -> Path:
        """Create a temporary database path for testing."""
        return Path(tempfile.mkdtemp(prefix="pyscrai_test_")) / "test.db"
    
    @staticmethod
    def cleanup_temp_db(db_path: Path) -> None:
        """Clean up temporary database files."""
        if db_path.exists():
            shutil.rmtree(db_path.parent, ignore_errors=True)


class TestMemoryHelper:
    """Helper for test memory operations."""
    
    @staticmethod
    def create_test_memories() -> List[Dict[str, Any]]:
        """Create a list of test memories."""
        return [
            {
                "text": "Commander's orders for today",
                "scope": "macro",
                "owner_id": "actor_1",
                "group_id": None,
                "cycle": 1,
                "importance": 0.9,
                "tags": ["orders", "strategy"]
            },
            {
                "text": "Scout report from northern sector",
                "scope": "micro",
                "owner_id": "actor_2",
                "group_id": None,
                "cycle": 1,
                "importance": 0.8,
                "tags": ["report", "recon"]
            },
            {
                "text": "Supply status update",
                "scope": "macro",
                "owner_id": "actor_1",
                "group_id": "group_logistics",
                "cycle": 1,
                "importance": 0.7,
                "tags": ["logistics", "status"]
            },
            {
                "text": "Enemy movement detected",
                "scope": "micro",
                "owner_id": "actor_2",
                "group_id": None,
                "cycle": 1,
                "importance": 0.95,
                "tags": ["enemy", "threat"]
            },
            {
                "text": "Weather conditions stable",
                "scope": "macro",
                "owner_id": None,
                "group_id": None,
                "cycle": 1,
                "importance": 0.3,
                "tags": ["weather", "environment"]
            }
        ]


class TestSpatialHelper:
    """Helper for spatial test operations."""
    
    @staticmethod
    def create_test_polygon(center_lon: float, center_lat: float, radius_km: float = 1.0) -> str:
        """Create a test terrain polygon around a center point."""
        # Approximate conversion: 1 degree ≈ 111 km
        degree_radius = radius_km / 111.0
        
        return f"""POLYGON((
            {center_lon - degree_radius} {center_lat - degree_radius},
            {center_lon + degree_radius} {center_lat - degree_radius},
            {center_lon + degree_radius} {center_lat + degree_radius},
            {center_lon - degree_radius} {center_lat + degree_radius},
            {center_lon - degree_radius} {center_lat - degree_radius}
        ))"""
    
    @staticmethod
    def calculate_distance_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate approximate distance in degrees between two points."""
        # Simple approximation for testing
        return ((lat2 - lat1)**2 + (lon2 - lon1)**2)**0.5


class TestEngineHelper:
    """Helper for test engine operations."""
    
    @staticmethod
    def create_test_archon_mock():
        """Create a mock Archon for testing."""
        from unittest.mock import Mock
        
        mock_archon = Mock()
        mock_archon.set_memory_systems = Mock()
        
        def mock_run_cycle(state):
            # Simple adjudication that modifies the state slightly
            adjudicated_state = state.copy(deep=True)
            adjudicated_state.environment.weather = f"Cycle {state.environment.cycle} Weather"
            adjudicated_state.environment.global_events.append(f"Event from cycle {state.environment.cycle}")
            return {
                "world_state": adjudicated_state,
                "archon_summary": f"Adjudicated cycle {state.environment.cycle}"
            }
        
        mock_archon.run_cycle = mock_run_cycle
        return mock_archon


class TestValidationHelper:
    """Helper for test validation operations."""
    
    @staticmethod
    def validate_world_state_structure(world_state: WorldState) -> List[str]:
        """Validate the structure of a world state."""
        errors = []
        
        if not world_state.simulation_id:
            errors.append("Missing simulation_id")
        
        if world_state.environment.cycle < 0:
            errors.append("Invalid cycle number")
        
        if not isinstance(world_state.actors, dict):
            errors.append("Actors should be a dictionary")
        
        if not isinstance(world_state.assets, dict):
            errors.append("Assets should be a dictionary")
        
        # Validate actors
        for actor_id, actor in world_state.actors.items():
            if actor.actor_id != actor_id:
                errors.append(f"Actor ID mismatch: {actor_id} != {actor.actor_id}")
            
            if not actor.role:
                errors.append(f"Actor {actor_id} missing role")
        
        # Validate assets
        for asset_id, asset in world_state.assets.items():
            if asset.asset_id != asset_id:
                errors.append(f"Asset ID mismatch: {asset_id} != {asset.asset_id}")
            
            if not asset.name:
                errors.append(f"Asset {asset_id} missing name")
        
        return errors
    
    @staticmethod
    def validate_spatial_data(world_state: WorldState) -> List[str]:
        """Validate spatial data in world state."""
        errors = []
        
        # Check actor locations
        for actor_id, actor in world_state.actors.items():
            if actor.location:
                if not (-90 <= actor.location.lat <= 90):
                    errors.append(f"Actor {actor_id} has invalid latitude: {actor.location.lat}")
                
                if not (-180 <= actor.location.lon <= 180):
                    errors.append(f"Actor {actor_id} has invalid longitude: {actor.location.lon}")
        
        # Check asset locations
        for asset_id, asset in world_state.assets.items():
            if asset.location and "lat" in asset.location and "lon" in asset.location:
                lat = asset.location["lat"]
                lon = asset.location["lon"]
                
                if not (-90 <= lat <= 90):
                    errors.append(f"Asset {asset_id} has invalid latitude: {lat}")
                
                if not (-180 <= lon <= 180):
                    errors.append(f"Asset {asset_id} has invalid longitude: {lon}")
        
        return errors


class TestPerformanceHelper:
    """Helper for performance testing."""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs) -> tuple:
        """Measure execution time of a function."""
        import time
        
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        return result, execution_time
    
    @staticmethod
    def assert_execution_time_under(func, max_time: float, *args, **kwargs) -> Any:
        """Assert that function execution time is under a threshold."""
        result, execution_time = TestPerformanceHelper.measure_execution_time(func, *args, **kwargs)
        
        if execution_time > max_time:
            raise AssertionError(f"Execution time {execution_time:.2f}s exceeded maximum {max_time}s")
        
        return result


class TestAsyncHelper:
    """Helper for async testing."""
    
    @staticmethod
    async def run_with_timeout(coro, timeout: float = 10.0):
        """Run a coroutine with a timeout."""
        import asyncio
        
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise AssertionError(f"Operation timed out after {timeout} seconds")


# Common test data constants
TEST_COORDINATES = {
    "los_angeles": {"lat": 34.05, "lon": -118.25},
    "new_york": {"lat": 40.71, "lon": -74.01},
    "chicago": {"lat": 41.88, "lon": -87.63},
    "houston": {"lat": 29.76, "lon": -95.37}
}

TEST_TERRAIN_TYPES = [
    TerrainType.PLAINS,
    TerrainType.MOUNTAINS,
    TerrainType.FOREST,
    TerrainType.WATER,
    TerrainType.URBAN,
    TerrainType.DESERT,
    TerrainType.ROAD
]

TEST_RESOLUTION_TYPES = ["macro", "micro"]

TEST_ACTOR_ROLES = [
    "Commander", "Scout", "Engineer", "Medic", "Pilot", 
    "Soldier", "Spy", "Diplomat", "Scientist", "Logistics"
]

TEST_ASSET_TYPES = [
    "Ground Unit", "Air Unit", "Naval Unit", "Building", 
    "Vehicle", "Supply", "Weapon", "Communication"
]
