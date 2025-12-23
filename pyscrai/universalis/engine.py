"""
Simulation Engine - The Heartbeat of PyScrAI Universalis (GeoScrAI).

This module contains the async simulation engine that manages
the temporal pulse of the simulation using DuckDB for state storage.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING

from pyscrai.data.schemas.models import WorldState, Environment
from pyscrai.universalis.state.duckdb_manager import DuckDBStateManager, get_state_manager
from pyscrai.universalis.memory.stream import MemoryStream
from pyscrai.config import get_config
from pyscrai.utils.logger import get_logger

if TYPE_CHECKING:
    from pyscrai.universalis.archon.adjudicator import Archon
    from pyscrai.universalis.memory.associative import LanceDBMemoryBank

logger = get_logger(__name__)


class SimulationEngine:
    """
    The Master Simulation Engine.
    
    Manages the simulation clock and coordinates the
    Perception → Action → Adjudication workflow using async operations.
    
    Attributes:
        sim_id: Unique identifier for this simulation
        steps: Current cycle number
        state_manager: DuckDB state manager
        archon: Optional Archon instance for adjudication
        memory_bank: LanceDB-backed associative memory
        memory_stream: Chronological event log
        running: Whether the simulation is currently running
        paused: Whether the simulation is paused (for God Mode)
    """
    
    def __init__(
        self, 
        sim_id: str,
        db_path: Optional[str] = None,
        archon: Optional["Archon"] = None
    ):
        """
        Initialize the simulation engine.
        
        Args:
            sim_id: Unique identifier for this simulation
            db_path: Optional path to DuckDB database
            archon: Optional Archon instance for adjudication
        """
        self.sim_id = sim_id
        self.config = get_config()
        
        # --- 1. Persistence Layer (DuckDB) ---
        self.state_manager = DuckDBStateManager(
            db_path=db_path,
            simulation_id=sim_id
        )
        
        # --- 2. Memory Layer (LanceDB + Stream) ---
        logger.info(f"Initializing Memory Systems for {sim_id}...")
        try:
            self._init_memory_systems()
        except Exception as e:
            logger.error(f"Memory initialization failed: {e}")
            raise RuntimeError(f"Cannot initialize engine without memory systems: {e}")
        
        # --- 3. Cognitive Layer (Archon) ---
        self.archon = archon
        if self.archon:
            self._inject_memory_into_archon()

        # Sync cycle count from DB if restarting, else 0
        self.steps = self.state_manager.get_current_cycle()
        
        # --- 4. Control Flags ---
        self.running = False
        self.paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        
        logger.info(f"Engine {self.sim_id} Initialized at Cycle {self.steps}")
    
    def _init_memory_systems(self) -> None:
        """
        Initialize memory systems with LanceDB.
        
        Raises:
            RuntimeError: If memory initialization fails
        """
        # Import here to avoid circular imports
        from pyscrai.universalis.memory.lancedb_memory import LanceDBMemoryBank
        
        try:
            self.memory_bank = LanceDBMemoryBank(
                simulation_id=self.sim_id
            )
            logger.info("✅ LanceDB Memory Bank initialized")
        except Exception as e:
            logger.warning(f"LanceDB initialization failed: {e}")
            # Fallback to in-memory if needed
            raise
        
        # Initialize memory stream (always succeeds)
        self.memory_stream = MemoryStream(simulation_id=self.sim_id)
        logger.info("Memory systems initialized successfully")
    
    def _inject_memory_into_archon(self) -> None:
        """
        Inject memory systems into Archon.
        
        Raises:
            TypeError: If Archon doesn't support memory injection
        """
        if not hasattr(self.archon, 'set_memory_systems'):
            raise TypeError(
                f"Archon {type(self.archon)} must implement set_memory_systems() method"
            )
        self.archon.set_memory_systems(self.memory_bank, self.memory_stream)
        logger.info("Memory systems injected into Archon")
    
    def get_current_state(self) -> Optional[WorldState]:
        """
        Fetch the latest world state from DuckDB.
        
        Returns:
            WorldState if found, None otherwise
        """
        return self.state_manager.get_world_state()
    
    def save_adjudicated_state(self, world_state: WorldState) -> None:
        """
        Serializes the final adjudicated state and saves to DuckDB.
        
        Args:
            world_state: The adjudicated world state to persist
        """
        # Ensure the timestamp is current before saving
        world_state.last_updated = datetime.now()
        
        self.state_manager.save_world_state(world_state)
        logger.info(f"Cycle {world_state.environment.cycle} adjudicated and saved to DuckDB.")
    
    def step(self) -> Dict[str, Any]:
        """
        The Master Tick (synchronous version).
        
        1. Advances the temporal pulse
        2. Triggers the cognitive bridge (Archon/LangGraph)
        3. Persists the ground truth (DuckDB)
        
        Returns:
            Dict with cycle number, status, and summary
        """
        return asyncio.get_event_loop().run_until_complete(self.async_step())
    
    async def async_step(self) -> Dict[str, Any]:
        """
        The Master Tick (async version with interrupt support).
        
        1. Waits for unpause if paused (God Mode support)
        2. Advances the temporal pulse
        3. Triggers the cognitive bridge (Archon/LangGraph)
        4. Persists the ground truth (DuckDB)
        
        Returns:
            Dict with cycle number, status, and summary
        
        Raises:
            Exception: If adjudication fails, exception is logged but result dict is still returned
        """
        try:
            # Wait for unpause if paused
            await self._pause_event.wait()
            
            # 1. Advance step counter
            self.steps += 1 
            
            # 2. Fetch the previous state to act as the baseline
            current_world_state = self.get_current_state()
            
            if current_world_state:
                # Update cycle number for the new tick
                current_world_state.environment.cycle = self.steps
            else:
                # Fallback for fresh start (though Seed DB is preferred)
                current_world_state = WorldState(
                    simulation_id=self.sim_id,
                    environment=Environment(
                        cycle=self.steps, 
                        time=datetime.now().strftime("%H:%M")
                    ),
                    actors={},
                    assets={}
                )
            
            # 3. Invoke the Cognitive Bridge (The Mind)
            logger.info(f"--- Triggering Cognitive Bridge for Cycle {self.steps} ---")
            
            archon_summary = "No summary provided"
            final_world_state = current_world_state
            
            if self.archon:
                try:
                    # Use the Archon for adjudication
                    final_output = self.archon.run_cycle(current_world_state)
                    archon_summary = final_output.get("archon_summary", "No summary provided")
                    final_world_state = final_output.get("world_state", current_world_state)
                except Exception as e:
                    logger.error(f"Error during Archon adjudication: {e}", exc_info=True)
                    archon_summary = f"Adjudication error: {str(e)}"
                    # Continue with current state
            else:
                # No archon attached - just pass through
                logger.warning("No Archon attached - passing world state through unchanged")
                archon_summary = "No adjudication (Archon not attached)"
            
            # 4. Save the adjudicated result to DuckDB
            try:
                self.save_adjudicated_state(final_world_state)
            except Exception as e:
                logger.error(f"Error saving state: {e}", exc_info=True)
                # Continue anyway - state might be saved next cycle
            
            return {
                "cycle": self.steps, 
                "status": "Adjudicated", 
                "summary": archon_summary
            }
        except Exception as e:
            logger.error(f"Critical error in step(): {e}", exc_info=True)
            # Return error result instead of None
            return {
                "cycle": self.steps,
                "status": "Error",
                "summary": f"Step failed: {str(e)}"
            }
    
    async def run_loop(self, tick_interval_ms: Optional[int] = None) -> None:
        """
        Run the simulation loop continuously.
        
        Args:
            tick_interval_ms: Milliseconds between ticks (defaults to config)
        """
        interval = (tick_interval_ms or self.config.simulation.tick_interval_ms) / 1000.0
        self.running = True
        
        logger.info(f"Starting simulation loop with {interval}s interval")
        
        try:
            while self.running:
                result = await self.async_step()
                logger.info(f"Cycle {result['cycle']}: {result['status']}")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Simulation loop cancelled")
        finally:
            self.running = False
    
    def stop(self) -> None:
        """Stop the simulation loop."""
        self.running = False
        logger.info("Simulation stop requested")
    
    def pause(self) -> None:
        """
        Pause the simulation (God Mode).
        
        The simulation will complete the current cycle and then wait.
        """
        self.paused = True
        self._pause_event.clear()
        logger.info("Simulation paused (God Mode active)")
    
    def resume(self) -> None:
        """Resume a paused simulation."""
        self.paused = False
        self._pause_event.set()
        logger.info("Simulation resumed")
    
    def attach_archon(self, archon: "Archon") -> None:
        """
        Attach an Archon instance and inject memory systems.
        
        Args:
            archon: The Archon instance to use for adjudication
        
        Raises:
            TypeError: If Archon doesn't support memory injection
        """
        self.archon = archon
        self._inject_memory_into_archon()
        logger.info(f"Archon attached to engine {self.sim_id}")
    
    def reset(self) -> None:
        """Reset the simulation to cycle 0."""
        self.steps = 0
        self.state_manager.clear_simulation()
        logger.info(f"Engine {self.sim_id} reset to Cycle 0")
    
    def shutdown(self) -> None:
        """
        Clean up resources on engine shutdown.
        
        Closes database connections and performs cleanup.
        """
        self.stop()
        self.state_manager.close()
        logger.info(f"Engine {self.sim_id} shutdown complete")
    
    # =========================================================================
    # SPATIAL QUERY HELPERS
    # =========================================================================
    
    def get_entities_near(
        self,
        lon: float,
        lat: float,
        radius_degrees: Optional[float] = None,
        entity_type: Optional[str] = None
    ) -> list:
        """
        Get entities near a location (perception sphere).
        
        Args:
            lon: Center longitude
            lat: Center latitude
            radius_degrees: Search radius (defaults to config)
            entity_type: Filter by type ('actor', 'asset', etc.)
        
        Returns:
            List of nearby entity dictionaries
        """
        radius = radius_degrees or self.config.simulation.perception_radius_degrees
        return self.state_manager.get_entities_within_distance(
            center_lon=lon,
            center_lat=lat,
            distance_degrees=radius,
            entity_type=entity_type
        )
    
    def check_movement_feasible(
        self,
        start_lon: float,
        start_lat: float,
        end_lon: float,
        end_lat: float
    ) -> tuple:
        """
        Check if movement between two points is feasible.
        
        Args:
            start_lon, start_lat: Starting coordinates
            end_lon, end_lat: Destination coordinates
        
        Returns:
            Tuple of (is_feasible, reason, cost)
        """
        is_blocked, blocker = self.state_manager.check_path_blocked(
            start_lon, start_lat, end_lon, end_lat
        )
        
        if is_blocked:
            return False, f"Path blocked by {blocker}", float('inf')
        
        cost = self.state_manager.calculate_path_cost(
            start_lon, start_lat, end_lon, end_lat
        )
        
        return True, "Path clear", cost
