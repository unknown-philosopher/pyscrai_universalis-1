"""Shared fixtures and configuration for PyScrAI Universalis tests."""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import pytest
import duckdb
import pyarrow as pa

from pyscrai.config import PyScrAIConfig, get_config, reload_config
from pyscrai.data.schemas.models import (
    WorldState, Actor, Asset, Environment, Location, Terrain, TerrainType
)
from pyscrai.universalis.state.duckdb_manager import DuckDBStateManager
from pyscrai.universalis.memory.lancedb_memory import LanceDBMemoryBank
from pyscrai.universalis.engine import SimulationEngine

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def test_config() -> PyScrAIConfig:
    """Create a test configuration with temporary directories."""
    # Create temporary directories for testing
    temp_dir = Path(tempfile.mkdtemp(prefix="pyscrai_test_"))
    
    config = PyScrAIConfig(
        duckdb=duckdb.DuckDBConfig(
            path=str(temp_dir / "test_geoscrai.duckdb"),
            read_only=False
        ),
        lancedb=lancedb.LanceDBConfig(
            path=str(temp_dir / "test_lancedb"),
            table_name="test_memories"
        ),
        simulation=SimulationConfig(
            simulation_id="test_simulation",
            tick_interval_ms=100,  # Fast for testing
            auto_run=False
        )
    )
    
    # Ensure directories exist
    config.ensure_directories()
    
    yield config
    
    # Cleanup after tests
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def clean_config(test_config: PyScrAIConfig) -> Generator[PyScrAIConfig, None, None]:
    """Provide a clean config for each test."""
    # Store original config
    original_config = get_config()
    
    try:
        # Set test config as global
        global config
        config = test_config
        yield test_config
    finally:
        # Restore original config
        config = original_config


@pytest.fixture
def duckdb_manager(clean_config: PyScrAIConfig) -> Generator[DuckDBStateManager, None, None]:
    """Create a DuckDB state manager for testing."""
    manager = DuckDBStateManager(
        db_path=clean_config.duckdb.path,
        simulation_id=clean_config.simulation.simulation_id,
        read_only=False
    )
    
    yield manager
    
    manager.close()


@pytest.fixture
def lancedb_memory(clean_config: PyScrAIConfig) -> Generator[LanceDBMemoryBank, None, None]:
    """Create a LanceDB memory bank for testing."""
    memory = LanceDBMemoryBank(
        db_path=clean_config.lancedb.path,
        table_name=clean_config.lancedb.table_name,
        simulation_id=clean_config.simulation.simulation_id
    )
    
    yield memory
    
    memory.clear()


@pytest.fixture
def sample_world_state() -> WorldState:
    """Create a sample world state for testing."""
    return WorldState(
        simulation_id="test_simulation",
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
            )
        }
    )


@pytest.fixture
def sample_terrain() -> Terrain:
    """Create a sample terrain for testing."""
    return Terrain(
        terrain_id="mountain_1",
        name="Test Mountain",
        terrain_type=TerrainType.MOUNTAINS,
        geometry_wkt="POLYGON((-74.01 40.71, -74.00 40.71, -74.00 40.72, -74.01 40.72, -74.01 40.71))",
        movement_cost=3.0,
        passable=False,
        attributes={"elevation": 1500, "difficulty": "hard"}
    )


@pytest.fixture
def sample_memory_data() -> list:
    """Create sample memory data for testing."""
    return [
        ("Commander's orders for today", "macro", "actor_1", None, 1, 0.9, ["orders", "strategy"]),
        ("Scout report from northern sector", "micro", "actor_2", None, 1, 0.8, ["report", "recon"]),
        ("Supply status update", "macro", "actor_1", "group_logistics", 1, 0.7, ["logistics", "status"]),
        ("Enemy movement detected", "micro", "actor_2", None, 1, 0.95, ["enemy", "threat"]),
        ("Weather conditions stable", "macro", None, None, 1, 0.3, ["weather", "environment"]),
    ]


@pytest.fixture
def populated_duckdb(duckdb_manager: DuckDBStateManager, sample_world_state: WorldState) -> DuckDBStateManager:
    """Populate DuckDB with test data."""
    duckdb_manager.save_world_state(sample_world_state)
    return duckdb_manager


@pytest.fixture
def populated_lancedb(lancedb_memory: LanceDBMemoryBank, sample_memory_data: list) -> LanceDBMemoryBank:
    """Populate LanceDB with test data."""
    from pyscrai.universalis.memory.scopes import MemoryScope
    
    for text, scope_str, owner_id, group_id, cycle, importance, tags in sample_memory_data:
        scope = MemoryScope.MACRO if scope_str == "macro" else MemoryScope.MICRO
        lancedb_memory.add(
            text=text,
            scope=scope,
            owner_id=owner_id,
            group_id=group_id,
            cycle=cycle,
            importance=importance,
            tags=tags
        )
    return lancedb_memory


@pytest.fixture
def test_engine(clean_config: PyScrAIConfig) -> Generator[SimulationEngine, None, None]:
    """Create a simulation engine for testing."""
    engine = SimulationEngine(config=clean_config)
    yield engine
    # Cleanup handled by config cleanup


# Test utilities
def create_test_terrain_polygon(center_lon: float, center_lat: float, radius_km: float = 1.0) -> str:
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


def assert_world_state_equal(actual: WorldState, expected: WorldState) -> None:
    """Assert that two world states are equal."""
    assert actual.simulation_id == expected.simulation_id
    assert actual.environment.cycle == expected.environment.cycle
    assert actual.environment.time == expected.environment.time
    assert actual.environment.weather == expected.environment.weather
    assert actual.environment.global_events == expected.environment.global_events
    assert actual.environment.terrain_modifiers == expected.environment.terrain_modifiers
    
    # Check actors
    assert len(actual.actors) == len(expected.actors)
    for actor_id, expected_actor in expected.actors.items():
        actual_actor = actual.actors[actor_id]
        assert actual_actor.actor_id == expected_actor.actor_id
        assert actual_actor.role == expected_actor.role
        assert actual_actor.description == expected_actor.description
        assert actual_actor.resolution == expected_actor.resolution
        assert actual_actor.assets == expected_actor.assets
        assert actual_actor.objectives == expected_actor.objectives
        assert actual_actor.attributes == expected_actor.attributes
        assert actual_actor.status == expected_actor.status
        
        if expected_actor.location:
            assert actual_actor.location.lat == expected_actor.location.lat
            assert actual_actor.location.lon == expected_actor.location.lon
            assert actual_actor.location.elevation == expected_actor.location.elevation
    
    # Check assets
    assert len(actual.assets) == len(expected.assets)
    for asset_id, expected_asset in expected.assets.items():
        actual_asset = actual.assets[asset_id]
        assert actual_asset.asset_id == expected_asset.asset_id
        assert actual_asset.name == expected_asset.name
        assert actual_asset.asset_type == expected_asset.asset_type
        assert actual_asset.attributes == expected_asset.attributes
        assert actual_asset.status == expected_asset.status
        
        if expected_asset.location:
            assert actual_asset.location == expected_asset.location


# Mock classes for testing
class MockLLMProvider:
    """Mock LLM provider for testing."""
    
    def __init__(self, responses: dict = None):
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = None
        self.last_params = None
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        self.last_params = kwargs
        
        # Return mock response based on prompt content
        if "intent" in prompt.lower():
            return "Test intent response"
        elif "action" in prompt.lower():
            return "Test action response"
        else:
            return f"Mock response for: {prompt[:50]}..."
    
    def embed_text(self, text: str) -> list:
        """Mock embedding function."""
        import random
        random.seed(hash(text) % (2**32))
        return [random.random() for _ in range(384)]


class MockObservation:
    """Mock observation for testing."""
    
    def __init__(self, actor_id: str, content: str, cycle: int = 1):
        self.actor_id = actor_id
        self.content = content
        self.cycle = cycle
        self.timestamp = "2025-01-01T12:00:00Z"


# Pytest markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.functional = pytest.mark.functional
