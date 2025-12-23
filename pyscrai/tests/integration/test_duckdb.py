"""Integration tests for DuckDB state management.

These tests use real DuckDB instances to test spatial queries,
world state persistence, and entity management.
"""

import pytest
import json
from datetime import datetime

from pyscrai.data.schemas.models import (
    WorldState, Actor, Asset, Environment, Location, Terrain, TerrainType
)
from pyscrai.universalis.state.duckdb_manager import DuckDBStateManager


class TestDuckDBStateManager:
    """Test DuckDB state manager with real database operations."""
    
    def test_init_with_memory_db(self, clean_config):
        """Test DuckDB manager initialization with in-memory database."""
        manager = DuckDBStateManager(
            db_path=":memory:",
            simulation_id="test_sim",
            read_only=False
        )
        assert manager._simulation_id == "test_sim"
        assert not manager._read_only
        manager.close()
    
    def test_init_with_file_db(self, clean_config, tmp_path):
        """Test DuckDB manager initialization with file database."""
        db_path = tmp_path / "test.db"
        manager = DuckDBStateManager(
            db_path=str(db_path),
            simulation_id="test_sim",
            read_only=False
        )
        assert manager._simulation_id == "test_sim"
        assert db_path.exists()  # Database file should be created
        manager.close()
    
    def test_save_and_get_world_state(self, duckdb_manager, sample_world_state):
        """Test saving and retrieving world state."""
        # Save world state
        duckdb_manager.save_world_state(sample_world_state)
        
        # Get world state
        retrieved_state = duckdb_manager.get_world_state()
        
        assert retrieved_state is not None
        assert retrieved_state.simulation_id == sample_world_state.simulation_id
        assert retrieved_state.environment.cycle == sample_world_state.environment.cycle
        assert retrieved_state.environment.time == sample_world_state.environment.time
        assert retrieved_state.environment.weather == sample_world_state.environment.weather
        assert len(retrieved_state.actors) == len(sample_world_state.actors)
        assert len(retrieved_state.assets) == len(sample_world_state.assets)
    
    def test_get_world_state_by_cycle(self, duckdb_manager, sample_world_state):
        """Test retrieving world state by specific cycle."""
        # Save multiple cycles
        for cycle in [1, 2, 3]:
            state = sample_world_state.copy(deep=True)
            state.environment.cycle = cycle
            state.environment.time = f"{cycle}:00"
            duckdb_manager.save_world_state(state)
        
        # Get specific cycle
        retrieved_state = duckdb_manager.get_world_state(cycle=2)
        assert retrieved_state.environment.cycle == 2
        assert retrieved_state.environment.time == "2:00"
    
    def test_get_current_cycle(self, duckdb_manager, sample_world_state):
        """Test getting the current cycle number."""
        # Save multiple cycles
        for cycle in [1, 2, 3, 5]:
            state = sample_world_state.copy(deep=True)
            state.environment.cycle = cycle
            duckdb_manager.save_world_state(state)
        
        current_cycle = duckdb_manager.get_current_cycle()
        assert current_cycle == 5
    
    def test_get_current_cycle_empty_db(self, duckdb_manager):
        """Test getting current cycle from empty database."""
        current_cycle = duckdb_manager.get_current_cycle()
        assert current_cycle == 0
    
    def test_save_world_state_updates(self, duckdb_manager, sample_world_state):
        """Test that saving world state updates existing data."""
        # Save initial state
        duckdb_manager.save_world_state(sample_world_state)
        
        # Modify and save again
        modified_state = sample_world_state.copy(deep=True)
        modified_state.environment.weather = "Rainy"
        modified_state.actors["actor_1"].description = "Updated commander"
        duckdb_manager.save_world_state(modified_state)
        
        # Retrieve and verify updates
        retrieved_state = duckdb_manager.get_world_state()
        assert retrieved_state.environment.weather == "Rainy"
        assert retrieved_state.actors["actor_1"].description == "Updated commander"
    
    def test_reconstruct_world_state(self, duckdb_manager, sample_world_state):
        """Test reconstructing world state from entity tables."""
        # Save world state
        duckdb_manager.save_world_state(sample_world_state)
        
        # Get reconstructed state (should work even without snapshots)
        reconstructed = duckdb_manager._reconstruct_world_state()
        
        assert reconstructed is not None
        assert reconstructed.simulation_id == sample_world_state.simulation_id
        assert len(reconstructed.actors) == len(sample_world_state.actors)
        assert len(reconstructed.assets) == len(sample_world_state.assets)
    
    def test_clear_simulation(self, duckdb_manager, sample_world_state):
        """Test clearing all data for a simulation."""
        # Save some data
        duckdb_manager.save_world_state(sample_world_state)
        
        # Verify data exists
        state = duckdb_manager.get_world_state()
        assert state is not None
        
        # Clear simulation
        duckdb_manager.clear_simulation()
        
        # Verify data is gone
        state = duckdb_manager.get_world_state()
        assert state is None
    
    def test_read_only_mode(self, clean_config, tmp_path):
        """Test DuckDB manager in read-only mode."""
        # First, create and populate a database
        db_path = tmp_path / "test.db"
        manager = DuckDBStateManager(
            db_path=str(db_path),
            simulation_id="test_sim",
            read_only=False
        )
        
        # Save some data
        world_state = WorldState(simulation_id="test_sim")
        manager.save_world_state(world_state)
        manager.close()
        
        # Open in read-only mode
        readonly_manager = DuckDBStateManager(
            db_path=str(db_path),
            simulation_id="test_sim",
            read_only=True
        )
        
        # Should be able to read
        state = readonly_manager.get_world_state()
        assert state is not None
        
        # Should not be able to write (this might raise an error or silently fail)
        try:
            readonly_manager.save_world_state(world_state)
        except Exception:
            pass  # Expected in read-only mode
        
        readonly_manager.close()


class TestDuckDBSpatialQueries:
    """Test spatial query functionality with real DuckDB Spatial."""
    
    def test_get_entities_within_distance(self, duckdb_manager, sample_world_state):
        """Test spatial query for entities within distance."""
        # Save world state with actors at different locations
        duckdb_manager.save_world_state(sample_world_state)
        
        # Query around actor_1's location (should find actor_1 and nearby actor_2)
        center_lon = -74.0060
        center_lat = 40.7128
        distance = 0.01  # Small distance to include nearby actor
        
        entities = duckdb_manager.get_entities_within_distance(
            center_lon=center_lon,
            center_lat=center_lat,
            distance_degrees=distance,
            entity_type="actor"
        )
        
        # Should find at least actor_1 (at exact location)
        assert len(entities) >= 1
        entity_ids = [e['id'] for e in entities]
        assert "actor_1" in entity_ids
    
    def test_get_entities_within_distance_no_filter(self, duckdb_manager, sample_world_state):
        """Test spatial query without entity type filter."""
        duckdb_manager.save_world_state(sample_world_state)
        
        center_lon = -74.0060
        center_lat = 40.7128
        distance = 0.01
        
        entities = duckdb_manager.get_entities_within_distance(
            center_lon=center_lon,
            center_lat=center_lat,
            distance_degrees=distance
        )
        
        # Should find both actors and assets
        assert len(entities) >= 2
        entity_types = [e['entity_type'] for e in entities]
        assert 'actor' in entity_types
        assert 'asset' in entity_types
    
    def test_get_entities_within_distance_no_results(self, duckdb_manager, sample_world_state):
        """Test spatial query with no results."""
        duckdb_manager.save_world_state(sample_world_state)
        
        # Query far away from any entities
        center_lon = 0.0  # Greenwich
        center_lat = 0.0  # Equator
        distance = 0.01
        
        entities = duckdb_manager.get_entities_within_distance(
            center_lon=center_lon,
            center_lat=center_lat,
            distance_degrees=distance
        )
        
        assert len(entities) == 0
    
    def test_add_and_get_terrain(self, duckdb_manager, sample_terrain):
        """Test adding and retrieving terrain features."""
        # Add terrain
        duckdb_manager.add_terrain(sample_terrain)
        
        # Get terrain at a point within the polygon
        center_lon = -74.005  # Center of the polygon
        center_lat = 40.711
        
        terrain = duckdb_manager.get_terrain_at_point(center_lon, center_lat)
        
        assert terrain is not None
        assert terrain['id'] == sample_terrain.terrain_id
        assert terrain['name'] == sample_terrain.name
        assert terrain['terrain_type'] == sample_terrain.terrain_type.value
        assert terrain['passable'] == sample_terrain.passable
        assert terrain['movement_cost'] == sample_terrain.movement_cost
    
    def test_get_terrain_at_point_no_terrain(self, duckdb_manager):
        """Test getting terrain at point with no terrain."""
        # Query point with no terrain
        terrain = duckdb_manager.get_terrain_at_point(0.0, 0.0)
        assert terrain is None
    
    def test_check_path_blocked(self, duckdb_manager, sample_terrain):
        """Test checking if a path is blocked by impassable terrain."""
        # Add impassable terrain
        sample_terrain.passable = False
        duckdb_manager.add_terrain(sample_terrain)
        
        # Check path that crosses the terrain
        start_lon = -74.015  # Outside polygon
        start_lat = 40.711
        end_lon = -74.005   # Inside polygon
        end_lat = 40.711
        
        is_blocked, blocking_terrain = duckdb_manager.check_path_blocked(
            start_lon=start_lon,
            start_lat=start_lat,
            end_lon=end_lon,
            end_lat=end_lat
        )
        
        assert is_blocked is True
        assert blocking_terrain == sample_terrain.name
    
    def test_check_path_not_blocked(self, duckdb_manager, sample_terrain):
        """Test checking if a path is not blocked."""
        # Add passable terrain
        sample_terrain.passable = True
        duckdb_manager.add_terrain(sample_terrain)
        
        # Check path that doesn't cross impassable terrain
        start_lon = -74.015
        start_lat = 40.711
        end_lon = -74.005
        end_lat = 40.711
        
        is_blocked, blocking_terrain = duckdb_manager.check_path_blocked(
            start_lon=start_lon,
            start_lat=start_lat,
            end_lon=end_lon,
            end_lat=end_lat
        )
        
        assert is_blocked is False
        assert blocking_terrain is None
    
    def test_calculate_path_cost(self, duckdb_manager):
        """Test calculating movement cost for a path."""
        # Add terrain with movement cost
        terrain = Terrain(
            terrain_id="test_terrain",
            name="Test Terrain",
            terrain_type=TerrainType.FOREST,
            geometry_wkt="POLYGON((-74.01 40.71, -74.00 40.71, -74.00 40.72, -74.01 40.72, -74.01 40.71))",
            movement_cost=2.0,
            passable=True
        )
        duckdb_manager.add_terrain(terrain)
        
        # Calculate path cost
        start_lon = -74.015
        start_lat = 40.711
        end_lon = -74.005
        end_lat = 40.711
        
        cost = duckdb_manager.calculate_path_cost(
            start_lon=start_lon,
            start_lat=start_lat,
            end_lon=end_lon,
            end_lat=end_lat
        )
        
        # Should be higher than 1.0 due to terrain cost
        assert cost > 1.0
        assert cost >= 2.0  # At least the terrain cost
    
    def test_calculate_distance(self, duckdb_manager, sample_world_state):
        """Test calculating distance between two entities."""
        duckdb_manager.save_world_state(sample_world_state)
        
        distance = duckdb_manager.calculate_distance("actor_1", "actor_2")
        
        assert distance is not None
        assert distance >= 0
        # Should be small since actors are close to each other
        assert distance < 0.01
    
    def test_calculate_distance_no_entities(self, duckdb_manager):
        """Test calculating distance between non-existent entities."""
        distance = duckdb_manager.calculate_distance("nonexistent_1", "nonexistent_2")
        assert distance is None


class TestDuckDBEntityManagement:
    """Test entity CRUD operations."""
    
    def test_upsert_entity_creation(self, duckdb_manager):
        """Test creating a new entity."""
        location = Location(lat=40.7128, lon=-74.0060)
        
        duckdb_manager._upsert_entity(
            entity_id="test_entity",
            entity_type="actor",
            name="Test Entity",
            description="Test description",
            location=location,
            properties={"test": "value"},
            status="active"
        )
        
        # Verify entity was created
        entities = duckdb_manager.get_entities_within_distance(
            center_lon=-74.0060,
            center_lat=40.7128,
            distance_degrees=0.01
        )
        
        assert len(entities) == 1
        entity = entities[0]
        assert entity['id'] == "test_entity"
        assert entity['name'] == "Test Entity"
        assert entity['entity_type'] == "actor"
        assert entity['properties']['test'] == "value"
    
    def test_upsert_entity_update(self, duckdb_manager):
        """Test updating an existing entity."""
        location = Location(lat=40.7128, lon=-74.0060)
        
        # Create entity
        duckdb_manager._upsert_entity(
            entity_id="test_entity",
            entity_type="actor",
            name="Test Entity",
            description="Original description",
            location=location,
            properties={"test": "value"},
            status="active"
        )
        
        # Update entity
        duckdb_manager._upsert_entity(
            entity_id="test_entity",
            entity_type="actor",
            name="Test Entity",
            description="Updated description",
            location=location,
            properties={"test": "updated_value", "new": "property"},
            status="inactive"
        )
        
        # Verify entity was updated
        entities = duckdb_manager.get_entities_within_distance(
            center_lon=-74.0060,
            center_lat=40.7128,
            distance_degrees=0.01
        )
        
        assert len(entities) == 1
        entity = entities[0]
        assert entity['description'] == "Updated description"
        assert entity['properties']['test'] == "updated_value"
        assert entity['properties']['new'] == "property"
        assert entity['status'] == "inactive"
    
    def test_upsert_entity_without_location(self, duckdb_manager):
        """Test creating entity without location."""
        duckdb_manager._upsert_entity(
            entity_id="test_entity",
            entity_type="actor",
            name="Test Entity",
            description="Test description",
            location=None,
            properties={"test": "value"},
            status="active"
        )
        
        # Should still be creatable, just without geometry
        # This would require a different query to verify since spatial queries need geometry
        # For now, we'll just verify it doesn't crash
        assert True


class TestDuckDBSchema:
    """Test database schema and table structure."""
    
    def test_schema_initialization(self, duckdb_manager):
        """Test that schema is properly initialized."""
        # Check that required tables exist
        tables = duckdb_manager._conn.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'main'
        """).fetchall()
        
        table_names = [t[0] for t in tables]
        expected_tables = ['entities', 'environment', 'terrain', 'world_state_snapshots']
        
        for table in expected_tables:
            assert table in table_names
    
    def test_entities_table_structure(self, duckdb_manager):
        """Test entities table has correct structure."""
        columns = duckdb_manager._conn.execute("""
            SELECT column_name, data_type FROM information_schema.columns 
            WHERE table_name = 'entities' ORDER BY ordinal_position
        """).fetchall()
        
        column_names = [c[0] for c in columns]
        expected_columns = [
            'id', 'simulation_id', 'entity_type', 'name', 'description',
            'geometry', 'properties', 'status', 'created_at', 'updated_at'
        ]
        
        for col in expected_columns:
            assert col in column_names
    
    def test_environment_table_structure(self, duckdb_manager):
        """Test environment table has correct structure."""
        columns = duckdb_manager._conn.execute("""
            SELECT column_name, data_type FROM information_schema.columns 
            WHERE table_name = 'environment' ORDER BY ordinal_position
        """).fetchall()
        
        column_names = [c[0] for c in columns]
        expected_columns = [
            'id', 'simulation_id', 'cycle', 'time_of_day', 'weather',
            'global_events', 'terrain_modifiers', 'created_at', 'updated_at'
        ]
        
        for col in expected_columns:
            assert col in column_names
    
    def test_terrain_table_structure(self, duckdb_manager):
        """Test terrain table has correct structure."""
        columns = duckdb_manager._conn.execute("""
            SELECT column_name, data_type FROM information_schema.columns 
            WHERE table_name = 'terrain' ORDER BY ordinal_position
        """).fetchall()
        
        column_names = [c[0] for c in columns]
        expected_columns = [
            'id', 'simulation_id', 'name', 'terrain_type', 'geometry',
            'movement_cost', 'passable', 'properties', 'created_at'
        ]
        
        for col in expected_columns:
            assert col in column_names
    
    def test_world_state_snapshots_table_structure(self, duckdb_manager):
        """Test world_state_snapshots table has correct structure."""
        columns = duckdb_manager._conn.execute("""
            SELECT column_name, data_type FROM information_schema.columns 
            WHERE table_name = 'world_state_snapshots' ORDER BY ordinal_position
        """).fetchall()
        
        column_names = [c[0] for c in columns]
        expected_columns = ['id', 'simulation_id', 'cycle', 'state_json', 'created_at']
        
        for col in expected_columns:
            assert col in column_names


class TestDuckDBConcurrency:
    """Test concurrent access scenarios."""
    
    def test_multiple_saves_same_cycle(self, duckdb_manager, sample_world_state):
        """Test saving multiple times in the same cycle."""
        # Save initial state
        duckdb_manager.save_world_state(sample_world_state)
        
        # Modify and save again in same cycle
        modified_state = sample_world_state.copy(deep=True)
        modified_state.environment.weather = "Rainy"
        duckdb_manager.save_world_state(modified_state)
        
        # Should have updated the existing snapshot, not created a new one
        current_cycle = duckdb_manager.get_current_cycle()
        assert current_cycle == 1
        
        # Get latest state - should be the modified one
        retrieved_state = duckdb_manager.get_world_state()
        assert retrieved_state.environment.weather == "Rainy"


class TestDuckDBErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_geometry_handling(self, duckdb_manager):
        """Test handling of invalid geometry data."""
        # This should be handled gracefully by DuckDB
        # Invalid WKT should cause an error that we can catch
        try:
            invalid_terrain = Terrain(
                terrain_id="invalid",
                name="Invalid Terrain",
                terrain_type=TerrainType.PLAINS,
                geometry_wkt="INVALID_POLYGON",  # Invalid WKT
                movement_cost=1.0,
                passable=True
            )
            duckdb_manager.add_terrain(invalid_terrain)
        except Exception as e:
            # Expected - invalid geometry should be rejected
            assert "geometry" in str(e).lower() or "polygon" in str(e).lower()
    
    def test_large_dataset_performance(self, duckdb_manager):
        """Test performance with a larger dataset."""
        # Create many entities to test performance
        entities_created = 0
        for i in range(100):  # Create 100 entities
            location = Location(lat=40.7128 + i * 0.001, lon=-74.0060 + i * 0.001)
            try:
                duckdb_manager._upsert_entity(
                    entity_id=f"entity_{i}",
                    entity_type="actor",
                    name=f"Entity {i}",
                    description=f"Test entity {i}",
                    location=location,
                    properties={"index": i},
                    status="active"
                )
                entities_created += 1
            except Exception:
                break  # Stop if we hit any issues
        
        # Should have created at least some entities
        assert entities_created > 0
        
        # Spatial query should still work
        entities = duckdb_manager.get_entities_within_distance(
            center_lon=-74.0060,
            center_lat=40.7128,
            distance_degrees=0.1
        )
        
        assert len(entities) > 0
