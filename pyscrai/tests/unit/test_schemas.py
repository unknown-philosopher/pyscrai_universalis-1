"""Unit tests for PyScrAI Universalis schemas and models.

These tests focus on data validation, serialization, and basic model behavior
without any database or I/O operations.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from pyscrai.data.schemas.models import (
    WorldState, Actor, Asset, Environment, Location, Terrain, TerrainType, 
    ResolutionType, EntityType, Intent
)


class TestLocation:
    """Test Location model and its methods."""
    
    def test_location_creation(self):
        """Test basic Location creation and validation."""
        location = Location(lat=40.7128, lon=-74.0060, elevation=10.0)
        assert location.lat == 40.7128
        assert location.lon == -74.0060
        assert location.elevation == 10.0
    
    def test_location_creation_without_elevation(self):
        """Test Location creation without elevation (should be None)."""
        location = Location(lat=40.7128, lon=-74.0060)
        assert location.elevation is None
    
    def test_location_validation_invalid_lat(self):
        """Test Location validation with invalid latitude."""
        with pytest.raises(ValidationError):
            Location(lat=91.0, lon=-74.0060)  # Latitude must be -90 to 90
    
    def test_location_validation_invalid_lon(self):
        """Test Location validation with invalid longitude."""
        with pytest.raises(ValidationError):
            Location(lat=40.7128, lon=181.0)  # Longitude must be -180 to 180
    
    def test_location_to_wkt_point(self):
        """Test WKT POINT conversion."""
        location = Location(lat=40.7128, lon=-74.0060)
        wkt = location.to_wkt_point()
        assert wkt == "POINT(-74.006 40.7128)"
    
    def test_location_to_wkt_point_with_elevation(self):
        """Test WKT POINT conversion with elevation (should be ignored)."""
        location = Location(lat=40.7128, lon=-74.0060, elevation=10.0)
        wkt = location.to_wkt_point()
        assert wkt == "POINT(-74.006 40.7128)"  # Elevation not included in POINT


class TestActor:
    """Test Actor model and its behavior."""
    
    def test_actor_creation_minimal(self):
        """Test Actor creation with minimal required fields."""
        actor = Actor(actor_id="actor_1", role="Commander")
        assert actor.actor_id == "actor_1"
        assert actor.role == "Commander"
        assert actor.resolution == ResolutionType.MACRO  # Default
        assert actor.status == "active"  # Default
        assert actor.assets == []  # Default
        assert actor.objectives == []  # Default
        assert actor.attributes == {}  # Default
    
    def test_actor_creation_full(self):
        """Test Actor creation with all fields."""
        location = Location(lat=40.7128, lon=-74.0060)
        actor = Actor(
            actor_id="actor_1",
            role="Commander",
            description="Test commander",
            resolution=ResolutionType.MICRO,
            assets=["asset_1", "asset_2"],
            objectives=["Objective 1", "Objective 2"],
            location=location,
            attributes={"rank": "General", "experience": 10},
            status="active"
        )
        assert actor.actor_id == "actor_1"
        assert actor.role == "Commander"
        assert actor.description == "Test commander"
        assert actor.resolution == ResolutionType.MICRO
        assert actor.assets == ["asset_1", "asset_2"]
        assert actor.objectives == ["Objective 1", "Objective 2"]
        assert actor.location == location
        assert actor.attributes == {"rank": "General", "experience": 10}
        assert actor.status == "active"
    
    def test_actor_validation_invalid_resolution(self):
        """Test Actor validation with invalid resolution."""
        with pytest.raises(ValidationError):
            Actor(actor_id="actor_1", role="Commander", resolution="invalid")
    
    def test_actor_to_dict(self):
        """Test Actor serialization to dict."""
        actor = Actor(actor_id="actor_1", role="Commander")
        actor_dict = actor.model_dump()
        assert actor_dict["actor_id"] == "actor_1"
        assert actor_dict["role"] == "Commander"
        assert actor_dict["resolution"] == "macro"
        assert actor_dict["status"] == "active"


class TestAsset:
    """Test Asset model and its behavior."""
    
    def test_asset_creation_minimal(self):
        """Test Asset creation with minimal required fields."""
        asset = Asset(asset_id="asset_1", name="Tank", asset_type="Ground Unit")
        assert asset.asset_id == "asset_1"
        assert asset.name == "Tank"
        assert asset.asset_type == "Ground Unit"
        assert asset.status == "active"  # Default
        assert asset.attributes == {}  # Default
        assert asset.location == {}  # Default
    
    def test_asset_creation_full(self):
        """Test Asset creation with all fields."""
        asset = Asset(
            asset_id="asset_1",
            name="Tank",
            asset_type="Ground Unit",
            location={"lat": 40.7128, "lon": -74.0060, "elevation": 10.0},
            attributes={"type": "armor", "health": 100, "ammo": 50},
            status="active"
        )
        assert asset.asset_id == "asset_1"
        assert asset.name == "Tank"
        assert asset.asset_type == "Ground Unit"
        assert asset.location == {"lat": 40.7128, "lon": -74.0060, "elevation": 10.0}
        assert asset.attributes == {"type": "armor", "health": 100, "ammo": 50}
        assert asset.status == "active"
    
    def test_asset_get_location_obj(self):
        """Test Asset get_location_obj method."""
        asset = Asset(
            asset_id="asset_1",
            name="Tank",
            asset_type="Ground Unit",
            location={"lat": 40.7128, "lon": -74.0060, "elevation": 10.0}
        )
        location = asset.get_location_obj()
        assert location is not None
        assert location.lat == 40.7128
        assert location.lon == -74.0060
        assert location.elevation == 10.0
    
    def test_asset_get_location_obj_empty(self):
        """Test Asset get_location_obj method with empty location."""
        asset = Asset(asset_id="asset_1", name="Tank", asset_type="Ground Unit")
        location = asset.get_location_obj()
        assert location is None
    
    def test_asset_get_location_obj_partial(self):
        """Test Asset get_location_obj method with partial location data."""
        asset = Asset(
            asset_id="asset_1",
            name="Tank",
            asset_type="Ground Unit",
            location={"lat": 40.7128}  # Missing lon
        )
        location = asset.get_location_obj()
        assert location is None  # Should return None if lat or lon missing


class TestEnvironment:
    """Test Environment model and its behavior."""
    
    def test_environment_creation_minimal(self):
        """Test Environment creation with minimal fields."""
        env = Environment()
        assert env.cycle == 0
        assert env.time == "00:00"
        assert env.weather == "Clear"
        assert env.global_events == []
        assert env.terrain_modifiers == {}
    
    def test_environment_creation_full(self):
        """Test Environment creation with all fields."""
        env = Environment(
            cycle=5,
            time="14:30",
            weather="Rainy",
            global_events=["Event 1", "Event 2"],
            terrain_modifiers={"mountain": 2.0, "forest": 1.5}
        )
        assert env.cycle == 5
        assert env.time == "14:30"
        assert env.weather == "Rainy"
        assert env.global_events == ["Event 1", "Event 2"]
        assert env.terrain_modifiers == {"mountain": 2.0, "forest": 1.5}


class TestWorldState:
    """Test WorldState model and its behavior."""
    
    def test_world_state_creation_minimal(self):
        """Test WorldState creation with minimal fields."""
        world_state = WorldState(simulation_id="test_sim")
        assert world_state.simulation_id == "test_sim"
        assert world_state.environment.cycle == 0
        assert world_state.actors == {}
        assert world_state.assets == {}
        assert isinstance(world_state.last_updated, datetime)
        assert world_state.metadata == {}
    
    def test_world_state_creation_full(self):
        """Test WorldState creation with all fields."""
        actor = Actor(actor_id="actor_1", role="Commander")
        asset = Asset(asset_id="asset_1", name="Tank", asset_type="Ground Unit")
        env = Environment(cycle=1, time="12:00", weather="Clear")
        
        world_state = WorldState(
            simulation_id="test_sim",
            environment=env,
            actors={"actor_1": actor},
            assets={"asset_1": asset},
            metadata={"version": "1.0"}
        )
        
        assert world_state.simulation_id == "test_sim"
        assert world_state.environment == env
        assert world_state.actors == {"actor_1": actor}
        assert world_state.assets == {"asset_1": asset}
        assert world_state.metadata == {"version": "1.0"}
        assert isinstance(world_state.last_updated, datetime)
    
    def test_world_state_to_json(self):
        """Test WorldState serialization to JSON."""
        world_state = WorldState(simulation_id="test_sim")
        json_str = world_state.model_dump_json()
        assert "test_sim" in json_str
        assert "simulation_id" in json_str
    
    def test_world_state_from_json(self):
        """Test WorldState deserialization from JSON."""
        json_str = '{"simulation_id": "test_sim", "environment": {"cycle": 1}}'
        world_state = WorldState.model_validate_json(json_str)
        assert world_state.simulation_id == "test_sim"
        assert world_state.environment.cycle == 1


class TestTerrain:
    """Test Terrain model and its behavior."""
    
    def test_terrain_creation_minimal(self):
        """Test Terrain creation with minimal fields."""
        terrain = Terrain(
            terrain_id="terrain_1",
            name="Test Terrain",
            terrain_type=TerrainType.PLAINS,
            geometry_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
        )
        assert terrain.terrain_id == "terrain_1"
        assert terrain.name == "Test Terrain"
        assert terrain.terrain_type == TerrainType.PLAINS
        assert terrain.geometry_wkt == "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
        assert terrain.movement_cost == 1.0  # Default
        assert terrain.passable is True  # Default
        assert terrain.attributes == {}  # Default
    
    def test_terrain_creation_full(self):
        """Test Terrain creation with all fields."""
        terrain = Terrain(
            terrain_id="terrain_1",
            name="Mountain",
            terrain_type=TerrainType.MOUNTAINS,
            geometry_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            movement_cost=3.0,
            passable=False,
            attributes={"elevation": 1500, "difficulty": "hard"}
        )
        assert terrain.terrain_id == "terrain_1"
        assert terrain.name == "Mountain"
        assert terrain.terrain_type == TerrainType.MOUNTAINS
        assert terrain.geometry_wkt == "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
        assert terrain.movement_cost == 3.0
        assert terrain.passable is False
        assert terrain.attributes == {"elevation": 1500, "difficulty": "hard"}


class TestIntent:
    """Test Intent model and its behavior."""
    
    def test_intent_creation_minimal(self):
        """Test Intent creation with minimal fields."""
        intent = Intent(actor_id="actor_1", content="Test intent", cycle=1)
        assert intent.actor_id == "actor_1"
        assert intent.content == "Test intent"
        assert intent.cycle == 1
        assert intent.priority == 0.5  # Default
        assert intent.metadata == {}  # Default
    
    def test_intent_creation_full(self):
        """Test Intent creation with all fields."""
        intent = Intent(
            actor_id="actor_1",
            content="Attack the enemy base",
            cycle=5,
            priority=0.9,
            metadata={"urgency": "high", "target": "base_alpha"}
        )
        assert intent.actor_id == "actor_1"
        assert intent.content == "Attack the enemy base"
        assert intent.cycle == 5
        assert intent.priority == 0.9
        assert intent.metadata == {"urgency": "high", "target": "base_alpha"}


class TestEnums:
    """Test enum values and behavior."""
    
    def test_resolution_type_values(self):
        """Test ResolutionType enum values."""
        assert ResolutionType.MACRO.value == "macro"
        assert ResolutionType.MICRO.value == "micro"
        assert len(ResolutionType) == 2
    
    def test_entity_type_values(self):
        """Test EntityType enum values."""
        assert EntityType.ACTOR.value == "actor"
        assert EntityType.ASSET.value == "asset"
        assert EntityType.TERRAIN.value == "terrain"
        assert EntityType.LANDMARK.value == "landmark"
        assert len(EntityType) == 4
    
    def test_terrain_type_values(self):
        """Test TerrainType enum values."""
        assert TerrainType.PLAINS.value == "plains"
        assert TerrainType.MOUNTAINS.value == "mountains"
        assert TerrainType.FOREST.value == "forest"
        assert TerrainType.WATER.value == "water"
        assert TerrainType.URBAN.value == "urban"
        assert TerrainType.DESERT.value == "desert"
        assert TerrainType.ROAD.value == "road"
        assert len(TerrainType) == 7


class TestModelValidation:
    """Test model validation and edge cases."""
    
    def test_actor_empty_id(self):
        """Test Actor validation with empty actor_id."""
        with pytest.raises(ValidationError):
            Actor(actor_id="", role="Commander")
    
    def test_asset_empty_id(self):
        """Test Asset validation with empty asset_id."""
        with pytest.raises(ValidationError):
            Asset(asset_id="", name="Tank", asset_type="Ground Unit")
    
    def test_world_state_empty_simulation_id(self):
        """Test WorldState validation with empty simulation_id."""
        with pytest.raises(ValidationError):
            WorldState(simulation_id="")
    
    def test_terrain_empty_id(self):
        """Test Terrain validation with empty terrain_id."""
        with pytest.raises(ValidationError):
            Terrain(
                terrain_id="",
                name="Test",
                terrain_type=TerrainType.PLAINS,
                geometry_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
            )
    
    def test_intent_empty_actor_id(self):
        """Test Intent validation with empty actor_id."""
        with pytest.raises(ValidationError):
            Intent(actor_id="", content="Test", cycle=1)
    
    def test_intent_invalid_cycle(self):
        """Test Intent validation with invalid cycle."""
        with pytest.raises(ValidationError):
            Intent(actor_id="actor_1", content="Test", cycle=-1)
    
    def test_intent_invalid_priority(self):
        """Test Intent validation with invalid priority."""
        with pytest.raises(ValidationError):
            Intent(actor_id="actor_1", content="Test", cycle=1, priority=1.5)
        
        with pytest.raises(ValidationError):
            Intent(actor_id="actor_1", content="Test", cycle=1, priority=-0.1)


class TestModelSerialization:
    """Test model serialization and deserialization."""
    
    def test_actor_serialization_roundtrip(self):
        """Test Actor serialization and deserialization."""
        original = Actor(actor_id="actor_1", role="Commander", resolution=ResolutionType.MICRO)
        json_str = original.model_dump_json()
        restored = Actor.model_validate_json(json_str)
        assert original == restored
    
    def test_asset_serialization_roundtrip(self):
        """Test Asset serialization and deserialization."""
        original = Asset(
            asset_id="asset_1",
            name="Tank",
            asset_type="Ground Unit",
            location={"lat": 40.7128, "lon": -74.0060}
        )
        json_str = original.model_dump_json()
        restored = Asset.model_validate_json(json_str)
        assert original == restored
    
    def test_world_state_serialization_roundtrip(self):
        """Test WorldState serialization and deserialization."""
        actor = Actor(actor_id="actor_1", role="Commander")
        asset = Asset(asset_id="asset_1", name="Tank", asset_type="Ground Unit")
        original = WorldState(simulation_id="test_sim", actors={"actor_1": actor}, assets={"asset_1": asset})
        
        json_str = original.model_dump_json()
        restored = WorldState.model_validate_json(json_str)
        
        assert original.simulation_id == restored.simulation_id
        assert original.environment.cycle == restored.environment.cycle
        assert len(restored.actors) == 1
        assert len(restored.assets) == 1
        assert restored.actors["actor_1"].actor_id == "actor_1"
        assert restored.assets["asset_1"].asset_id == "asset_1"
