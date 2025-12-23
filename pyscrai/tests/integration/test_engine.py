"""Integration tests for the Simulation Engine.

These tests verify the engine's async operations, cycle management,
spatial queries, and integration with state and memory systems.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from pyscrai.universalis.engine import SimulationEngine
from pyscrai.data.schemas.models import WorldState, Actor, Asset, Environment, Location
from pyscrai.universalis.state.duckdb_manager import DuckDBStateManager
from pyscrai.universalis.memory.lancedb_memory import LanceDBMemoryBank


class TestSimulationEngine:
    """Test the Simulation Engine core functionality."""
    
    def test_engine_initialization(self, clean_config, tmp_path):
        """Test engine initialization with all components."""
        db_path = tmp_path / "test_engine.db"
        engine = SimulationEngine(
            sim_id="test_engine",
            db_path=str(db_path)
        )
        
        try:
            assert engine.sim_id == "test_engine"
            assert engine.steps == 0
            assert engine.running is False
            assert engine.paused is False
            assert engine.archon is None
            
            # Check that state manager was created
            assert isinstance(engine.state_manager, DuckDBStateManager)
            assert engine.state_manager._simulation_id == "test_engine"
            
            # Check that memory systems were initialized
            assert hasattr(engine, 'memory_bank')
            assert hasattr(engine, 'memory_stream')
            assert isinstance(engine.memory_bank, LanceDBMemoryBank)
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_engine_initialization_with_archon(self, clean_config, tmp_path, mocker):
        """Test engine initialization with Archon attached."""
        db_path = tmp_path / "test_engine_archon.db"
        mock_archon = Mock()
        mock_archon.set_memory_systems = Mock()
        
        engine = SimulationEngine(
            sim_id="test_engine_archon",
            db_path=str(db_path),
            archon=mock_archon
        )
        
        try:
            assert engine.archon == mock_archon
            mock_archon.set_memory_systems.assert_called_once()
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_get_current_state_empty(self, clean_config, tmp_path):
        """Test getting current state from empty database."""
        db_path = tmp_path / "test_empty.db"
        engine = SimulationEngine(
            sim_id="test_empty",
            db_path=str(db_path)
        )
        
        try:
            state = engine.get_current_state()
            assert state is None
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_get_current_state_with_data(self, clean_config, tmp_path, sample_world_state):
        """Test getting current state with existing data."""
        db_path = tmp_path / "test_with_data.db"
        engine = SimulationEngine(
            sim_id="test_with_data",
            db_path=str(db_path)
        )
        
        try:
            # Save initial state
            engine.state_manager.save_world_state(sample_world_state)
            
            # Get current state
            state = engine.get_current_state()
            assert state is not None
            assert state.simulation_id == sample_world_state.simulation_id
            assert len(state.actors) == len(sample_world_state.actors)
            assert len(state.assets) == len(sample_world_state.assets)
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_save_adjudicated_state(self, clean_config, tmp_path, sample_world_state):
        """Test saving adjudicated state to DuckDB."""
        db_path = tmp_path / "test_save.db"
        engine = SimulationEngine(
            sim_id="test_save",
            db_path=str(db_path)
        )
        
        try:
            # Modify the state to simulate adjudication
            adjudicated_state = sample_world_state.copy(deep=True)
            adjudicated_state.environment.weather = "Rainy"
            adjudicated_state.environment.cycle = 2
            
            # Save adjudicated state
            engine.save_adjudicated_state(adjudicated_state)
            
            # Verify it was saved
            retrieved_state = engine.get_current_state()
            assert retrieved_state.environment.weather == "Rainy"
            assert retrieved_state.environment.cycle == 2
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_step_sync(self, clean_config, tmp_path, sample_world_state):
        """Test synchronous step operation."""
        db_path = tmp_path / "test_step_sync.db"
        engine = SimulationEngine(
            sim_id="test_step_sync",
            db_path=str(db_path)
        )
        
        try:
            # Save initial state
            engine.state_manager.save_world_state(sample_world_state)
            
            # Perform step
            result = engine.step()
            
            assert result["cycle"] == 1
            assert result["status"] == "Adjudicated"
            assert "summary" in result
            
            # Check that cycle was incremented in database
            current_cycle = engine.state_manager.get_current_cycle()
            assert current_cycle == 1
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_async_step(self, clean_config, tmp_path, sample_world_state):
        """Test asynchronous step operation."""
        db_path = tmp_path / "test_async_step.db"
        engine = SimulationEngine(
            sim_id="test_async_step",
            db_path=str(db_path)
        )
        
        try:
            # Save initial state
            engine.state_manager.save_world_state(sample_world_state)
            
            # Perform async step
            result = await engine.async_step()
            
            assert result["cycle"] == 1
            assert result["status"] == "Adjudicated"
            assert "summary" in result
            
            # Check that cycle was incremented in database
            current_cycle = engine.state_manager.get_current_cycle()
            assert current_cycle == 1
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_async_step_with_archon(self, clean_config, tmp_path, sample_world_state, mocker):
        """Test async step with Archon adjudication."""
        db_path = tmp_path / "test_async_step_archon.db"
        mock_archon = Mock()
        mock_archon.set_memory_systems = Mock()
        mock_archon.run_cycle = Mock(return_value={
            "world_state": sample_world_state,
            "archon_summary": "Test adjudication summary"
        })
        
        engine = SimulationEngine(
            sim_id="test_async_step_archon",
            db_path=str(db_path),
            archon=mock_archon
        )
        
        try:
            # Save initial state
            engine.state_manager.save_world_state(sample_world_state)
            
            # Perform async step
            result = await engine.async_step()
            
            assert result["cycle"] == 1
            assert result["status"] == "Adjudicated"
            assert result["summary"] == "Test adjudication summary"
            
            # Verify Archon was called
            mock_archon.run_cycle.assert_called_once()
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_async_step_with_error(self, clean_config, tmp_path, sample_world_state, mocker):
        """Test async step handling of errors gracefully."""
        db_path = tmp_path / "test_async_step_error.db"
        mock_archon = Mock()
        mock_archon.set_memory_systems = Mock()
        mock_archon.run_cycle = Mock(side_effect=Exception("Test error"))
        
        engine = SimulationEngine(
            sim_id="test_async_step_error",
            db_path=str(db_path),
            archon=mock_archon
        )
        
        try:
            # Save initial state
            engine.state_manager.save_world_state(sample_world_state)
            
            # Perform async step - should handle error gracefully
            result = await engine.async_step()
            
            assert result["cycle"] == 1
            assert result["status"] == "Adjudicated"  # Should still be adjudicated
            assert "Test error" in result["summary"]
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_run_loop(self, clean_config, tmp_path, sample_world_state):
        """Test the simulation run loop."""
        db_path = tmp_path / "test_run_loop.db"
        engine = SimulationEngine(
            sim_id="test_run_loop",
            db_path=str(db_path)
        )
        
        try:
            # Save initial state
            engine.state_manager.save_world_state(sample_world_state)
            
            # Run loop for a short time
            loop_task = asyncio.create_task(engine.run_loop(tick_interval_ms=100))  # 100ms interval
            
            # Let it run for a few cycles
            await asyncio.sleep(0.5)  # 5 cycles
            
            # Stop the loop
            engine.stop()
            await asyncio.sleep(0.1)  # Allow task to complete
            
            # Check that cycles were processed
            current_cycle = engine.state_manager.get_current_cycle()
            assert current_cycle >= 5  # Should have processed at least 5 cycles
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_pause_and_resume(self, clean_config, tmp_path, sample_world_state):
        """Test pausing and resuming the simulation."""
        db_path = tmp_path / "test_pause_resume.db"
        engine = SimulationEngine(
            sim_id="test_pause_resume",
            db_path=str(db_path)
        )
        
        try:
            # Save initial state
            engine.state_manager.save_world_state(sample_world_state)
            
            # Start the loop
            loop_task = asyncio.create_task(engine.run_loop(tick_interval_ms=100))
            
            # Let it run for a bit
            await asyncio.sleep(0.2)  # 2 cycles
            initial_cycle = engine.state_manager.get_current_cycle()
            assert initial_cycle >= 2
            
            # Pause the simulation
            engine.pause()
            assert engine.paused is True
            
            # Wait and check that cycles don't increment while paused
            await asyncio.sleep(0.3)  # Should not process cycles while paused
            paused_cycle = engine.state_manager.get_current_cycle()
            assert paused_cycle == initial_cycle  # Should be same as before pause
            
            # Resume the simulation
            engine.resume()
            assert engine.paused is False
            
            # Wait and check that cycles resume
            await asyncio.sleep(0.2)  # 2 more cycles
            resumed_cycle = engine.state_manager.get_current_cycle()
            assert resumed_cycle > paused_cycle
            
            # Stop the loop
            engine.stop()
            await asyncio.sleep(0.1)
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_reset(self, clean_config, tmp_path, sample_world_state):
        """Test resetting the simulation to cycle 0."""
        db_path = tmp_path / "test_reset.db"
        engine = SimulationEngine(
            sim_id="test_reset",
            db_path=str(db_path)
        )
        
        try:
            # Save initial state and advance cycles
            engine.state_manager.save_world_state(sample_world_state)
            engine.step()  # Cycle 1
            engine.step()  # Cycle 2
            
            # Verify we're at cycle 2
            assert engine.state_manager.get_current_cycle() == 2
            assert engine.steps == 2
            
            # Reset
            engine.reset()
            
            # Verify reset to cycle 0
            assert engine.steps == 0
            assert engine.state_manager.get_current_cycle() == 0
            
            # Verify state is cleared
            state = engine.get_current_state()
            assert state is None
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_attach_archon(self, clean_config, tmp_path):
        """Test attaching an Archon to a running engine."""
        db_path = tmp_path / "test_attach_archon.db"
        engine = SimulationEngine(
            sim_id="test_attach_archon",
            db_path=str(db_path)
        )
        
        try:
            assert engine.archon is None
            
            # Create and attach Archon
            mock_archon = Mock()
            mock_archon.set_memory_systems = Mock()
            
            engine.attach_archon(mock_archon)
            
            assert engine.archon == mock_archon
            mock_archon.set_memory_systems.assert_called_once()
            
            engine.shutdown()
        finally:
            engine.shutdown()


class TestSimulationEngineSpatialQueries:
    """Test spatial query functionality through the engine."""
    
    def test_get_entities_near(self, clean_config, tmp_path, sample_world_state):
        """Test getting entities near a location."""
        db_path = tmp_path / "test_get_entities_near.db"
        engine = SimulationEngine(
            sim_id="test_get_entities_near",
            db_path=str(db_path)
        )
        
        try:
            # Save world state with actors at specific locations
            engine.state_manager.save_world_state(sample_world_state)
            
            # Query around actor_1's location
            center_lon = -74.0060
            center_lat = 40.7128
            radius = 0.01
            
            entities = engine.get_entities_near(
                lon=center_lon,
                lat=center_lat,
                radius_degrees=radius,
                entity_type="actor"
            )
            
            # Should find at least actor_1
            assert len(entities) >= 1
            entity_ids = [e['id'] for e in entities]
            assert "actor_1" in entity_ids
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_get_entities_near_no_filter(self, clean_config, tmp_path, sample_world_state):
        """Test getting entities near a location without type filter."""
        db_path = tmp_path / "test_get_entities_near_no_filter.db"
        engine = SimulationEngine(
            sim_id="test_get_entities_near_no_filter",
            db_path=str(db_path)
        )
        
        try:
            engine.state_manager.save_world_state(sample_world_state)
            
            entities = engine.get_entities_near(
                lon=-74.0060,
                lat=40.7128,
                radius_degrees=0.01
            )
            
            # Should find both actors and assets
            assert len(entities) >= 2
            entity_types = [e['entity_type'] for e in entities]
            assert 'actor' in entity_types
            assert 'asset' in entity_types
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_get_entities_near_no_results(self, clean_config, tmp_path):
        """Test getting entities near a location with no results."""
        db_path = tmp_path / "test_get_entities_near_no_results.db"
        engine = SimulationEngine(
            sim_id="test_get_entities_near_no_results",
            db_path=str(db_path)
        )
        
        try:
            entities = engine.get_entities_near(
                lon=0.0,  # Greenwich
                lat=0.0,  # Equator
                radius_degrees=0.01
            )
            
            assert len(entities) == 0
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_check_movement_feasible(self, clean_config, tmp_path, sample_terrain):
        """Test checking if movement is feasible."""
        db_path = tmp_path / "test_check_movement_feasible.db"
        engine = SimulationEngine(
            sim_id="test_check_movement_feasible",
            db_path=str(db_path)
        )
        
        try:
            # Add impassable terrain
            sample_terrain.passable = False
            engine.state_manager.add_terrain(sample_terrain)
            
            # Check movement that crosses the terrain
            start_lon = -74.015
            start_lat = 40.711
            end_lon = -74.005
            end_lat = 40.711
            
            is_feasible, reason, cost = engine.check_movement_feasible(
                start_lon=start_lon,
                start_lat=start_lat,
                end_lon=end_lon,
                end_lat=end_lat
            )
            
            assert is_feasible is False
            assert "blocked" in reason.lower()
            assert cost == float('inf')
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_check_movement_feasible_clear_path(self, clean_config, tmp_path):
        """Test checking movement feasibility on a clear path."""
        db_path = tmp_path / "test_check_movement_feasible_clear.db"
        engine = SimulationEngine(
            sim_id="test_check_movement_feasible_clear",
            db_path=str(db_path)
        )
        
        try:
            # Check movement on clear path
            is_feasible, reason, cost = engine.check_movement_feasible(
                start_lon=-74.015,
                start_lat=40.711,
                end_lon=-74.005,
                end_lat=40.711
            )
            
            assert is_feasible is True
            assert "clear" in reason.lower()
            assert cost >= 1.0  # Should be at least 1.0 (normal cost)
            
            engine.shutdown()
        finally:
            engine.shutdown()


class TestSimulationEngineMemoryIntegration:
    """Test memory system integration."""
    
    def test_memory_bank_initialization(self, clean_config, tmp_path):
        """Test that memory bank is properly initialized."""
        db_path = tmp_path / "test_memory_init.db"
        engine = SimulationEngine(
            sim_id="test_memory_init",
            db_path=str(db_path)
        )
        
        try:
            assert hasattr(engine, 'memory_bank')
            assert hasattr(engine, 'memory_stream')
            assert engine.memory_bank is not None
            assert engine.memory_stream is not None
            
            # Test adding memory
            result = engine.memory_bank.add(
                text="Test memory from engine",
                scope="macro",
                cycle=1
            )
            assert result is True
            assert len(engine.memory_bank) == 1
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_memory_stream_initialization(self, clean_config, tmp_path):
        """Test that memory stream is properly initialized."""
        db_path = tmp_path / "test_stream_init.db"
        engine = SimulationEngine(
            sim_id="test_stream_init",
            db_path=str(db_path)
        )
        
        try:
            assert hasattr(engine, 'memory_stream')
            assert engine.memory_stream is not None
            
            # Test adding to stream
            engine.memory_stream.add_event({
                "type": "test_event",
                "content": "Test event content",
                "cycle": 1
            })
            
            # Should be able to retrieve
            events = engine.memory_stream.get_events()
            assert len(events) > 0
            
            engine.shutdown()
        finally:
            engine.shutdown()


class TestSimulationEngineErrorHandling:
    """Test error handling and edge cases."""
    
    def test_engine_initialization_failure(self, clean_config, tmp_path):
        """Test handling of engine initialization failures."""
        # This would test scenarios where memory initialization fails
        # For now, we'll test with a valid initialization
        db_path = tmp_path / "test_init_failure.db"
        engine = SimulationEngine(
            sim_id="test_init_failure",
            db_path=str(db_path)
        )
        
        try:
            assert engine.sim_id == "test_init_failure"
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_step_with_corrupted_state(self, clean_config, tmp_path):
        """Test step handling with corrupted or invalid state."""
        db_path = tmp_path / "test_corrupted_state.db"
        engine = SimulationEngine(
            sim_id="test_corrupted_state",
            db_path=str(db_path)
        )
        
        try:
            # Try to step with no initial state
            result = engine.step()
            
            # Should handle gracefully and create initial state
            assert result["cycle"] == 1
            assert result["status"] == "Adjudicated"
            
            # Should have created an initial state
            state = engine.get_current_state()
            assert state is not None
            assert state.environment.cycle == 1
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_multiple_engine_instances(self, clean_config, tmp_path):
        """Test multiple engine instances with same simulation ID."""
        db_path = tmp_path / "test_multiple_instances.db"
        
        # Create first engine
        engine1 = SimulationEngine(
            sim_id="test_multiple",
            db_path=str(db_path)
        )
        
        try:
            # Save some state
            world_state = engine1.get_current_state()
            if world_state is None:
                from pyscrai.data.schemas.models import WorldState, Environment
                world_state = WorldState(
                    simulation_id="test_multiple",
                    environment=Environment(cycle=1)
                )
            engine1.save_adjudicated_state(world_state)
            
            # Create second engine with same ID
            engine2 = SimulationEngine(
                sim_id="test_multiple",
                db_path=str(db_path)
            )
            
            try:
                # Should be able to read the same state
                state1 = engine1.get_current_state()
                state2 = engine2.get_current_state()
                
                assert state1 is not None
                assert state2 is not None
                assert state1.environment.cycle == state2.environment.cycle
                
                engine2.shutdown()
            finally:
                engine1.shutdown()
        finally:
            pass  # Engines already shut down


class TestSimulationEnginePerformance:
    """Test performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_concurrent_steps(self, clean_config, tmp_path, sample_world_state):
        """Test handling multiple concurrent steps."""
        db_path = tmp_path / "test_concurrent_steps.db"
        engine = SimulationEngine(
            sim_id="test_concurrent_steps",
            db_path=str(db_path)
        )
        
        try:
            # Save initial state
            engine.state_manager.save_world_state(sample_world_state)
            
            # Run multiple steps concurrently
            tasks = [engine.async_step() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            # All should complete successfully
            assert len(results) == 5
            for i, result in enumerate(results):
                assert result["cycle"] == i + 1
                assert result["status"] == "Adjudicated"
            
            # Final cycle should be 5
            final_cycle = engine.state_manager.get_current_cycle()
            assert final_cycle == 5
            
            engine.shutdown()
        finally:
            engine.shutdown()
    
    def test_large_state_handling(self, clean_config, tmp_path):
        """Test handling of large world states."""
        db_path = tmp_path / "test_large_state.db"
        engine = SimulationEngine(
            sim_id="test_large_state",
            db_path=str(db_path)
        )
        
        try:
            # Create a large world state
            large_state = engine.get_current_state()
            if large_state is None:
                from pyscrai.data.schemas.models import WorldState, Environment, Actor, Asset, Location
                large_state = WorldState(
                    simulation_id="test_large_state",
                    environment=Environment(cycle=1)
                )
            
            # Add many actors and assets
            for i in range(100):
                actor_id = f"actor_{i}"
                asset_id = f"asset_{i}"
                
                large_state.actors[actor_id] = Actor(
                    actor_id=actor_id,
                    role=f"Actor {i}",
                    location=Location(lat=40.0 + i * 0.001, lon=-74.0 + i * 0.001)
                )
                
                large_state.assets[asset_id] = Asset(
                    asset_id=asset_id,
                    name=f"Asset {i}",
                    asset_type="Test Asset",
                    location={"lat": 40.0 + i * 0.001, "lon": -74.0 + i * 0.001}
                )
            
            # Save large state
            start_time = time.time()
            engine.save_adjudicated_state(large_state)
            save_time = time.time() - start_time
            
            # Should complete in reasonable time (under 5 seconds)
            assert save_time < 5.0
            
            # Should be able to retrieve
            retrieved_state = engine.get_current_state()
            assert retrieved_state is not None
            assert len(retrieved_state.actors) == 100
            assert len(retrieved_state.assets) == 100
            
            engine.shutdown()
        finally:
            engine.shutdown()
