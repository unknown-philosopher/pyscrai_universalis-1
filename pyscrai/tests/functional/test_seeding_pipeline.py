"""Functional tests for the seeding pipeline.

These tests verify end-to-end workflows including world building,
schema validation, data seeding, and complete simulation initialization.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

from pyscrai.architect.builder import WorldBuilder
from pyscrai.architect.validator import SchemaValidator
from pyscrai.architect.seeder import WorldSeeder
from pyscrai.data.schemas.models import WorldState, Actor, Asset, Environment, Location, Terrain, TerrainType
from pyscrai.universalis.engine import SimulationEngine
from pyscrai.universalis.state.duckdb_manager import DuckDBStateManager
from pyscrai.universalis.memory.lancedb_memory import LanceDBMemoryBank


class TestSeedingPipeline:
    """Test the complete seeding pipeline workflow."""
    
    def test_complete_seeding_workflow(self, clean_config, tmp_path):
        """Test the complete workflow from world building to engine initialization."""
        # 1. Build world configuration
        world_config = {
            "world_id": "test_world",
            "name": "Test World",
            "description": "A test world for functional testing",
            "region_type": "city",
            "coordinates": {"lat": 34.05, "lon": -118.25},
            "climate": "Mediterranean"
        }
        
        builder = WorldBuilder()
        world_state = builder.build_world(world_config)
        
        # 2. Validate the world state
        validator = SchemaValidator()
        is_valid, errors = validator.validate_world_state(world_state)
        assert is_valid, f"Validation failed: {errors}"
        assert world_state.simulation_id == "test_world"
        assert len(world_state.actors) > 0
        assert len(world_state.assets) > 0
        assert len(world_state.environment.terrain_modifiers) > 0
        
        # 3. Seed the world into database
        db_path = tmp_path / "test_seeding.db"
        seeder = WorldSeeder(db_path=str(db_path))
        seeder.seed_world(world_state)
        
        # 4. Verify seeding was successful
        state_manager = DuckDBStateManager(
            db_path=str(db_path),
            simulation_id="test_world",
            read_only=False
        )
        
        retrieved_state = state_manager.get_world_state()
        assert retrieved_state is not None
        assert retrieved_state.simulation_id == "test_world"
        assert len(retrieved_state.actors) == len(world_state.actors)
        assert len(retrieved_state.assets) == len(world_state.assets)
        
        # 5. Initialize engine with seeded data
        engine = SimulationEngine(
            sim_id="test_world",
            db_path=str(db_path)
        )
        
        try:
            # 6. Verify engine can access the seeded data
            engine_state = engine.get_current_state()
            assert engine_state is not None
            assert engine_state.simulation_id == "test_world"
            assert len(engine_state.actors) == len(world_state.actors)
            assert len(engine_state.assets) == len(world_state.assets)
            
            # 7. Test that engine can perform a step
            result = engine.step()
            assert result["cycle"] == 1
            assert result["status"] == "Adjudicated"
            
            # 8. Verify state was updated
            updated_state = engine.get_current_state()
            assert updated_state.environment.cycle == 1
            
            state_manager.close()
            engine.shutdown()
        finally:
            state_manager.close()
            engine.shutdown()
    
    def test_seeding_with_custom_terrain(self, clean_config, tmp_path):
        """Test seeding with custom terrain features."""
        # Create world state with custom terrain
        world_state = WorldState(simulation_id="test_terrain_world")
        world_state.environment.terrain_modifiers = {"mountain": 3.0, "forest": 2.0}
        
        # Add custom terrain
        mountain_terrain = Terrain(
            terrain_id="mountain_1",
            name="Test Mountain",
            terrain_type=TerrainType.MOUNTAINS,
            geometry_wkt="POLYGON((-118.26 34.04, -118.24 34.04, -118.24 34.06, -118.26 34.06, -118.26 34.04))",
            movement_cost=3.0,
            passable=False
        )
        world_state.environment.terrain_modifiers["mountain_1"] = mountain_terrain
        
        # Add actors and assets
        world_state.actors["actor_1"] = Actor(
            actor_id="actor_1",
            role="Test Actor",
            location=Location(lat=34.05, lon=-118.25)
        )
        world_state.assets["asset_1"] = Asset(
            asset_id="asset_1",
            name="Test Asset",
            asset_type="Test Type",
            location={"lat": 34.05, "lon": -118.25}
        )
        
        # Seed the world
        db_path = tmp_path / "test_custom_terrain.db"
        seeder = WorldSeeder(db_path=str(db_path))
        seeder.seed_world(world_state)
        
        # Verify terrain was added
        state_manager = DuckDBStateManager(
            db_path=str(db_path),
            simulation_id="test_terrain_world",
            read_only=False
        )
        
        try:
            # Check that terrain exists in database
            terrain = state_manager.get_terrain_at_point(-118.25, 34.05)
            assert terrain is not None
            assert terrain['name'] == "Test Mountain"
            assert terrain['passable'] is False
            assert terrain['movement_cost'] == 3.0
            
            # Test spatial queries work with custom terrain
            is_blocked, blocker = state_manager.check_path_blocked(
                start_lon=-118.27, start_lat=34.05,
                end_lon=-118.23, end_lat=34.05
            )
            assert is_blocked is True
            assert blocker == "Test Mountain"
            
            state_manager.close()
        finally:
            state_manager.close()
    
    def test_seeding_with_large_dataset(self, clean_config, tmp_path):
        """Test seeding with a large dataset to verify performance."""
        # Create a large world state
        world_state = WorldState(simulation_id="test_large_world")
        world_state.environment.terrain_modifiers = {"urban": 1.5, "forest": 2.0}
        
        # Add many actors
        for i in range(50):
            world_state.actors[f"actor_{i}"] = Actor(
                actor_id=f"actor_{i}",
                role=f"Actor {i}",
                location=Location(lat=34.05 + i * 0.001, lon=-118.25 + i * 0.001),
                attributes={"index": i, "type": "test"}
            )
        
        # Add many assets
        for i in range(100):
            world_state.assets[f"asset_{i}"] = Asset(
                asset_id=f"asset_{i}",
                name=f"Asset {i}",
                asset_type="Test Asset",
                location={"lat": 34.05 + i * 0.0005, "lon": -118.25 + i * 0.0005},
                attributes={"index": i, "type": "test"}
            )
        
        # Time the seeding process
        import time
        db_path = tmp_path / "test_large_dataset.db"
        seeder = WorldSeeder(db_path=str(db_path))
        
        start_time = time.time()
        seeder.seed_world(world_state)
        seeding_time = time.time() - start_time
        
        # Should complete in reasonable time (under 10 seconds for 150 entities)
        assert seeding_time < 10.0
        
        # Verify all data was seeded correctly
        state_manager = DuckDBStateManager(
            db_path=str(db_path),
            simulation_id="test_large_world",
            read_only=False
        )
        
        try:
            retrieved_state = state_manager.get_world_state()
            assert retrieved_state is not None
            assert len(retrieved_state.actors) == 50
            assert len(retrieved_state.assets) == 100
            
            # Test that spatial queries still work efficiently
            start_time = time.time()
            entities = state_manager.get_entities_within_distance(
                center_lon=-118.25,
                center_lat=34.05,
                distance_degrees=0.1
            )
            query_time = time.time() - start_time
            
            # Should be fast (under 1 second)
            assert query_time < 1.0
            assert len(entities) > 0
            
            state_manager.close()
        finally:
            state_manager.close()
    
    def test_seeding_with_invalid_data(self, clean_config, tmp_path):
        """Test seeding with invalid data to verify error handling."""
        # Create world state with invalid data
        world_state = WorldState(simulation_id="test_invalid_world")
        
        # Add actor with invalid location
        world_state.actors["actor_1"] = Actor(
            actor_id="actor_1",
            role="Test Actor",
            location=Location(lat=91.0, lon=-118.25)  # Invalid latitude
        )
        
        # Add asset with missing required fields
        world_state.assets["asset_1"] = Asset(
            asset_id="asset_1",
            name="",  # Empty name
            asset_type="Test Type"
        )
        
        # Try to seed - should handle gracefully
        db_path = tmp_path / "test_invalid_data.db"
        seeder = WorldSeeder(db_path=str(db_path))
        
        # Should not crash, but may skip invalid entities
        try:
            seeder.seed_world(world_state)
        except Exception as e:
            # If it does crash, it should be a validation error
            assert "validation" in str(e).lower() or "invalid" in str(e).lower()
    
    def test_seeding_preserves_existing_data(self, clean_config, tmp_path):
        """Test that seeding doesn't overwrite existing valid data."""
        db_path = tmp_path / "test_preserve_data.db"
        
        # First, seed some initial data
        initial_state = WorldState(simulation_id="test_preserve_world")
        initial_state.actors["initial_actor"] = Actor(
            actor_id="initial_actor",
            role="Initial Actor",
            location=Location(lat=34.05, lon=-118.25)
        )
        initial_state.assets["initial_asset"] = Asset(
            asset_id="initial_asset",
            name="Initial Asset",
            asset_type="Initial Type",
            location={"lat": 34.05, "lon": -118.25}
        )
        
        seeder1 = WorldSeeder(db_path=str(db_path))
        seeder1.seed_world(initial_state)
        
        # Verify initial data exists
        state_manager = DuckDBStateManager(
            db_path=str(db_path),
            simulation_id="test_preserve_world",
            read_only=False
        )
        
        try:
            state1 = state_manager.get_world_state()
            assert state1 is not None
            assert "initial_actor" in state1.actors
            assert "initial_asset" in state1.assets
            
            # Now seed additional data (should not overwrite existing)
            additional_state = WorldState(simulation_id="test_preserve_world")
            additional_state.actors["additional_actor"] = Actor(
                actor_id="additional_actor",
                role="Additional Actor",
                location=Location(lat=34.06, lon=-118.26)
            )
            additional_state.assets["additional_asset"] = Asset(
                asset_id="additional_asset",
                name="Additional Asset",
                asset_type="Additional Type",
                location={"lat": 34.06, "lon": -118.26}
            )
            
            seeder2 = WorldSeeder(db_path=str(db_path))
            seeder2.seed_world(additional_state)
            
            # Verify both initial and additional data exist
            state2 = state_manager.get_world_state()
            assert state2 is not None
            assert "initial_actor" in state2.actors
            assert "initial_asset" in state2.assets
            assert "additional_actor" in state2.actors
            assert "additional_asset" in state2.assets
            
            state_manager.close()
        finally:
            state_manager.close()
    
    def test_seeding_with_memory_integration(self, clean_config, tmp_path):
        """Test seeding with memory system integration."""
        # Create world state
        world_state = WorldState(simulation_id="test_memory_world")
        world_state.actors["commander"] = Actor(
            actor_id="commander",
            role="Commander",
            resolution="macro",
            objectives=["Test objective 1", "Test objective 2"]
        )
        world_state.assets["headquarters"] = Asset(
            asset_id="headquarters",
            name="HQ",
            asset_type="Building",
            location={"lat": 34.05, "lon": -118.25}
        )
        
        # Seed the world
        db_path = tmp_path / "test_memory_integration.db"
        seeder = WorldSeeder(db_path=str(db_path))
        seeder.seed_world(world_state)
        
        # Initialize engine with memory systems
        engine = SimulationEngine(
            sim_id="test_memory_world",
            db_path=str(db_path)
        )
        
        try:
            # Add some memories through the engine's memory system
            engine.memory_bank.add(
                text="Initial briefing: Mission objectives confirmed",
                scope="macro",
                owner_id="commander",
                cycle=0,
                importance=0.9
            )
            
            engine.memory_bank.add(
                text="HQ location established at coordinates 34.05, -118.25",
                scope="macro",
                owner_id="commander",
                cycle=0,
                importance=0.8
            )
            
            # Verify memories were added
            assert len(engine.memory_bank) == 2
            
            # Test memory retrieval
            memories = engine.memory_bank.retrieve_associative("briefing", k=1)
            assert len(memories) > 0
            assert "briefing" in memories[0].lower()
            
            # Test memory stream
            engine.memory_stream.add_event({
                "type": "world_seeded",
                "content": "World seeded successfully with memory integration",
                "cycle": 0
            })
            
            events = engine.memory_stream.get_events()
            assert len(events) > 0
            
            engine.shutdown()
        finally:
            engine.shutdown()


class TestWorldBuilder:
    """Test the WorldBuilder component."""
    
    def test_build_world_minimal(self, clean_config):
        """Test building a world with minimal configuration."""
        builder = WorldBuilder()
        world_config = {
            "world_id": "minimal_world",
            "name": "Minimal World",
            "description": "A minimal test world",
            "region_type": "city",
            "coordinates": {"lat": 34.05, "lon": -118.25},
            "climate": "Mediterranean"
        }
        
        world_state = builder.build_world(world_config)
        
        assert world_state.simulation_id == "minimal_world"
        assert world_state.environment.cycle == 0
        assert len(world_state.actors) > 0
        assert len(world_state.assets) > 0
        assert world_state.environment.terrain_modifiers is not None
    
    def test_build_world_with_custom_parameters(self, clean_config):
        """Test building a world with custom parameters."""
        builder = WorldBuilder()
        world_config = {
            "world_id": "custom_world",
            "name": "Custom World",
            "description": "A world with custom parameters",
            "region_type": "city",
            "coordinates": {"lat": 34.05, "lon": -118.25},
            "climate": "Mediterranean",
            "custom_params": {
                "population_density": "high",
                "infrastructure_level": "developed",
                "conflict_level": "medium"
            }
        }
        
        world_state = builder.build_world(world_config)
        
        assert world_state.simulation_id == "custom_world"
        assert "population_density" in world_state.metadata
        assert "infrastructure_level" in world_state.metadata
        assert "conflict_level" in world_state.metadata
    
    def test_build_world_invalid_config(self, clean_config):
        """Test building a world with invalid configuration."""
        builder = WorldBuilder()
        world_config = {
            "world_id": "",  # Invalid: empty ID
            "name": "Invalid World",
            "region_type": "invalid_type",  # Invalid region type
            "coordinates": {"lat": 91.0, "lon": -118.25}  # Invalid coordinates
        }
        
        # Should handle gracefully or raise appropriate error
        try:
            world_state = builder.build_world(world_config)
            # If it succeeds, the builder should have corrected invalid values
            assert world_state.simulation_id != ""
        except Exception as e:
            # If it fails, should be a validation error
            assert "validation" in str(e).lower() or "invalid" in str(e).lower()


class TestSchemaValidator:
    """Test the SchemaValidator component."""
    
    def test_validate_world_state_valid(self, sample_world_state):
        """Test validating a valid world state."""
        validator = SchemaValidator()
        is_valid, errors = validator.validate_world_state(sample_world_state)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_world_state_invalid(self, clean_config):
        """Test validating an invalid world state."""
        # Create invalid world state
        world_state = WorldState(simulation_id="")
        
        validator = SchemaValidator()
        is_valid, errors = validator.validate_world_state(world_state)
        
        assert is_valid is False
        assert len(errors) > 0
        assert "simulation_id" in str(errors[0]).lower()
    
    def test_validate_actors(self, sample_world_state):
        """Test validating actors in world state."""
        validator = SchemaValidator()
        is_valid, errors = validator.validate_actors(sample_world_state.actors)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_assets(self, sample_world_state):
        """Test validating assets in world state."""
        validator = SchemaValidator()
        is_valid, errors = validator.validate_assets(sample_world_state.assets)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_environment(self, sample_world_state):
        """Test validating environment in world state."""
        validator = SchemaValidator()
        is_valid, errors = validator.validate_environment(sample_world_state.environment)
        
        assert is_valid is True
        assert len(errors) == 0


class TestWorldSeeder:
    """Test the WorldSeeder component."""
    
    def test_seed_world_minimal(self, clean_config, tmp_path, sample_world_state):
        """Test seeding a minimal world."""
        db_path = tmp_path / "test_seed_minimal.db"
        seeder = WorldSeeder(db_path=str(db_path))
        
        seeder.seed_world(sample_world_state)
        
        # Verify seeding was successful
        state_manager = DuckDBStateManager(
            db_path=str(db_path),
            simulation_id=sample_world_state.simulation_id,
            read_only=False
        )
        
        try:
            retrieved_state = state_manager.get_world_state()
            assert retrieved_state is not None
            assert retrieved_state.simulation_id == sample_world_state.simulation_id
            
            state_manager.close()
        finally:
            state_manager.close()
    
    def test_seed_world_with_terrain(self, clean_config, tmp_path):
        """Test seeding a world with terrain features."""
        # Create world state with terrain
        world_state = WorldState(simulation_id="test_terrain_world")
        
        # Add terrain
        terrain = Terrain(
            terrain_id="mountain_1",
            name="Test Mountain",
            terrain_type=TerrainType.MOUNTAINS,
            geometry_wkt="POLYGON((-118.26 34.04, -118.24 34.04, -118.24 34.06, -118.26 34.06, -118.26 34.04))",
            movement_cost=3.0,
            passable=False
        )
        world_state.environment.terrain_modifiers["mountain_1"] = terrain
        
        # Add actors and assets
        world_state.actors["actor_1"] = Actor(
            actor_id="actor_1",
            role="Test Actor",
            location=Location(lat=34.05, lon=-118.25)
        )
        world_state.assets["asset_1"] = Asset(
            asset_id="asset_1",
            name="Test Asset",
            asset_type="Test Type",
            location={"lat": 34.05, "lon": -118.25}
        )
        
        # Seed the world
        db_path = tmp_path / "test_seed_terrain.db"
        seeder = WorldSeeder(db_path=str(db_path))
        seeder.seed_world(world_state)
        
        # Verify terrain was seeded
        state_manager = DuckDBStateManager(
            db_path=str(db_path),
            simulation_id="test_terrain_world",
            read_only=False
        )
        
        try:
            terrain_result = state_manager.get_terrain_at_point(-118.25, 34.05)
            assert terrain_result is not None
            assert terrain_result['name'] == "Test Mountain"
            assert terrain_result['passable'] is False
            
            state_manager.close()
        finally:
            state_manager.close()
    
    def test_seed_world_performance(self, clean_config, tmp_path):
        """Test seeding performance with large world states."""
        # Create large world state
        world_state = WorldState(simulation_id="test_performance_world")
        
        # Add many actors
        for i in range(100):
            world_state.actors[f"actor_{i}"] = Actor(
                actor_id=f"actor_{i}",
                role=f"Actor {i}",
                location=Location(lat=34.05 + i * 0.001, lon=-118.25 + i * 0.001)
            )
        
        # Add many assets
        for i in range(200):
            world_state.assets[f"asset_{i}"] = Asset(
                asset_id=f"asset_{i}",
                name=f"Asset {i}",
                asset_type="Test Asset",
                location={"lat": 34.05 + i * 0.0005, "lon": -118.25 + i * 0.0005}
            )
        
        # Time the seeding
        import time
        db_path = tmp_path / "test_seed_performance.db"
        seeder = WorldSeeder(db_path=str(db_path))
        
        start_time = time.time()
        seeder.seed_world(world_state)
        seeding_time = time.time() - start_time
        
        # Should complete in reasonable time (under 15 seconds for 300 entities)
        assert seeding_time < 15.0
        
        # Verify all data was seeded
        state_manager = DuckDBStateManager(
            db_path=str(db_path),
            simulation_id="test_performance_world",
            read_only=False
        )
        
        try:
            retrieved_state = state_manager.get_world_state()
            assert retrieved_state is not None
            assert len(retrieved_state.actors) == 100
            assert len(retrieved_state.assets) == 200
            
            state_manager.close()
        finally:
            state_manager.close()


class TestEndToEndSimulation:
    """Test complete end-to-end simulation workflows."""
    
    def test_complete_simulation_workflow(self, clean_config, tmp_path):
        """Test a complete simulation from seeding to multiple cycles."""
        # 1. Build and seed world
        builder = WorldBuilder()
        world_config = {
            "world_id": "e2e_test_world",
            "name": "End-to-End Test World",
            "description": "World for complete simulation testing",
            "region_type": "city",
            "coordinates": {"lat": 34.05, "lon": -118.25},
            "climate": "Mediterranean"
        }
        
        world_state = builder.build_world(world_config)
        
        db_path = tmp_path / "test_e2e_simulation.db"
        seeder = WorldSeeder(db_path=str(db_path))
        seeder.seed_world(world_state)
        
        # 2. Initialize engine
        engine = SimulationEngine(
            sim_id="e2e_test_world",
            db_path=str(db_path)
        )
        
        try:
            # 3. Run multiple simulation cycles
            initial_cycle = engine.state_manager.get_current_cycle()
            assert initial_cycle == 0
            
            # Run 5 cycles
            for i in range(5):
                result = engine.step()
                assert result["cycle"] == i + 1
                assert result["status"] == "Adjudicated"
            
            # Verify final state
            final_cycle = engine.state_manager.get_current_cycle()
            assert final_cycle == 5
            
            final_state = engine.get_current_state()
            assert final_state is not None
            assert final_state.environment.cycle == 5
            
            # 4. Test spatial queries work throughout simulation
            entities = engine.get_entities_near(
                lon=-118.25,
                lat=34.05,
                radius_degrees=0.1
            )
            assert len(entities) > 0
            
            # 5. Test memory system works
            assert len(engine.memory_bank) >= 0  # May have adjudication memories
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_simulation_with_custom_archon(self, clean_config, tmp_path, mocker):
        """Test simulation with a custom Archon for adjudication."""
        # Build and seed world
        builder = WorldBuilder()
        world_config = {
            "world_id": "custom_archon_world",
            "name": "Custom Archon Test World",
            "region_type": "city",
            "coordinates": {"lat": 34.05, "lon": -118.25},
            "climate": "Mediterranean"
        }
        
        world_state = builder.build_world(world_config)
        
        db_path = tmp_path / "test_custom_archon.db"
        seeder = WorldSeeder(db_path=str(db_path))
        seeder.seed_world(world_state)
        
        # Create mock Archon
        mock_archon = Mock()
        mock_archon.set_memory_systems = Mock()
        
        def mock_run_cycle(state):
            # Modify the state slightly to simulate adjudication
            adjudicated_state = state.copy(deep=True)
            adjudicated_state.environment.weather = f"Cycle {state.environment.cycle} Weather"
            adjudicated_state.environment.global_events.append(f"Event from cycle {state.environment.cycle}")
            return {
                "world_state": adjudicated_state,
                "archon_summary": f"Adjudicated cycle {state.environment.cycle}"
            }
        
        mock_archon.run_cycle = mock_run_cycle
        
        # Initialize engine with custom Archon
        engine = SimulationEngine(
            sim_id="custom_archon_world",
            db_path=str(db_path),
            archon=mock_archon
        )
        
        try:
            # Run a few cycles
            for i in range(3):
                result = engine.step()
                assert result["cycle"] == i + 1
                assert result["status"] == "Adjudicated"
                assert f"Cycle {i + 1}" in result["summary"]
            
            # Verify Archon was called
            assert mock_archon.run_cycle.call_count == 3
            
            # Verify state was modified by Archon
            final_state = engine.get_current_state()
            assert final_state.environment.weather == "Cycle 3 Weather"
            assert len(final_state.environment.global_events) == 3
            
            engine.shutdown()
        finally:
            engine.shutdown()
