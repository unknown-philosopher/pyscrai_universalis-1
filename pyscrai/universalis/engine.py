"""
Simulation Engine - The Heartbeat of PyScrAI Universalis.

This module contains the Mesa-based simulation engine that manages
the temporal pulse of the simulation.
"""

import mesa
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
import os
from dotenv import load_dotenv

from pyscrai.data.schemas.models import WorldState, Environment
from pyscrai.universalis.memory.associative import ChromaDBMemoryBank
from pyscrai.universalis.memory.stream import MemoryStream
from pyscrai.config import get_config
from pyscrai.utils.logger import get_logger

if TYPE_CHECKING:
    from pyscrai.universalis.archon.adjudicator import Archon

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


class SimulationEngine(mesa.Model):
    """
    The Master Simulation Engine.
    
    Manages the simulation clock using Mesa and coordinates the
    Perception → Action → Adjudication workflow.
    
    Attributes:
        sim_id: Unique identifier for this simulation
        steps: Current cycle number
        db: MongoDB database connection
        states_collection: MongoDB collection for world states
        archon: Optional Archon instance for adjudication
        memory_bank: ChromaDB-backed associative memory
        memory_stream: Chronological event log
    """
    
    def __init__(
        self, 
        sim_id: str,
        mongo_uri: Optional[str] = None,
        db_name: Optional[str] = None,
        archon: Optional["Archon"] = None
    ):
        """
        Initialize the simulation engine.
        
        Args:
            sim_id: Unique identifier for this simulation
            mongo_uri: MongoDB connection URI (defaults to env var)
            db_name: Database name (defaults to env var)
            archon: Optional Archon instance for adjudication
        """
        super().__init__()
        self.sim_id = sim_id
        self.config = get_config()
        
        # --- 1. Persistence Layer (MongoDB) ---
        self._mongo_uri = mongo_uri or self.config.database.uri
        self._db_name = db_name or self.config.database.db_name
        
        try:
            self._client: MongoClient = MongoClient(self._mongo_uri)
            self.db: Database = self._client[self._db_name]
            self.states_collection: Collection = self.db["world_states"]
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise RuntimeError(f"Cannot initialize engine without MongoDB: {e}")
        
        # --- 2. Memory Layer (ChromaDB + Stream) ---
        # Initialize these ONCE here so they persist across ticks
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
        latest = self.states_collection.find_one(
            {"simulation_id": sim_id}, 
            sort=[("environment.cycle", -1)]
        )
        self.steps = latest["environment"]["cycle"] if latest else 0
        logger.info(f"Engine {self.sim_id} Initialized at Cycle {self.steps}")
    
    def _init_memory_systems(self) -> None:
        """
        Initialize memory systems with embedding function.
        
        Tries HTTP client first, falls back to persistent client if HTTP fails.
        
        Raises:
            RuntimeError: If memory initialization fails
        """
        from pyscrai.universalis.memory.embeddings import get_embedding_function
        
        embedding_fn = None
        try:
            embedding_fn = get_embedding_function()
        except ImportError as e:
            logger.warning(f"Failed to import embedding function: {e}")
            logger.warning("Will use ChromaDB default embeddings")
        
        # Try HTTP client first (if configured)
        if self.config.chromadb.use_http:
            try:
                logger.info(
                    f"Attempting to connect to ChromaDB at "
                    f"{self.config.chromadb.host}:{self.config.chromadb.port}"
                )
                self.memory_bank = ChromaDBMemoryBank(
                    collection_name=self.config.chromadb.collection_name,
                    simulation_id=self.sim_id,
                    chroma_host=self.config.chromadb.host,
                    chroma_port=self.config.chromadb.port,
                    embedding_function=embedding_fn
                )
                logger.info("✅ Connected to ChromaDB via HTTP client")
            except Exception as e:
                logger.warning(f"HTTP client failed: {e}")
                logger.info("Falling back to persistent client...")
                # Fall through to persistent client
                self._init_persistent_memory(embedding_fn)
        else:
            # Use persistent client directly
            self._init_persistent_memory(embedding_fn)
        
        # Initialize memory stream (always succeeds)
        self.memory_stream = MemoryStream(simulation_id=self.sim_id)
        logger.info("Memory systems initialized successfully")
    
    def _init_persistent_memory(self, embedding_fn=None) -> None:
        """
        Initialize ChromaDB using persistent client (local storage).
        
        Args:
            embedding_fn: Optional embedding function
        """
        import tempfile
        from pathlib import Path
        
        # Determine persist directory
        if self.config.chromadb.persist_directory:
            persist_dir = Path(self.config.chromadb.persist_directory)
        else:
            # Use temp directory for this simulation
            base_dir = Path(__file__).parent.parent.parent / "database" / "chroma-data"
            base_dir.mkdir(parents=True, exist_ok=True)
            persist_dir = base_dir / self.sim_id
        
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Using persistent ChromaDB at: {persist_dir}")
        
        self.memory_bank = ChromaDBMemoryBank(
            collection_name=self.config.chromadb.collection_name,
            simulation_id=self.sim_id,
            persist_directory=str(persist_dir),
            embedding_function=embedding_fn
        )
        logger.info("✅ Initialized ChromaDB with persistent client")
    
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
        Fetch the latest world state from MongoDB.
        
        Returns:
            WorldState if found, None otherwise
        """
        latest_doc = self.states_collection.find_one(
            {"simulation_id": self.sim_id},
            sort=[("environment.cycle", -1)]
        )
        
        if latest_doc:
            # Remove MongoDB internal ID before rehydrating
            latest_doc.pop("_id", None)
            return WorldState(**latest_doc)
        return None
    
    def save_adjudicated_state(self, world_state: WorldState) -> None:
        """
        Serializes the final adjudicated state and pushes to MongoDB.
        
        Args:
            world_state: The adjudicated world state to persist
        """
        # Ensure the timestamp is current before saving
        world_state.last_updated = datetime.now()
        
        # Convert Pydantic model to dict for MongoDB
        self.states_collection.insert_one(world_state.model_dump())
        logger.info(f"Cycle {world_state.environment.cycle} adjudicated and saved to MongoDB.")
    
    def step(self) -> Dict[str, Any]:
        """
        The Master Tick.
        
        1. Advances the temporal pulse (Mesa)
        2. Triggers the cognitive bridge (Archon/LangGraph)
        3. Persists the ground truth (MongoDB)
        
        Returns:
            Dict with cycle number, status, and summary
        
        Raises:
            Exception: If adjudication fails, exception is logged but result dict is still returned
        """
        try:
            # 1. Advance Mesa internal step counter
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
            
            # 4. Save the adjudicated result to the Ledger (MongoDB)
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
        logger.info(f"Engine {self.sim_id} reset to Cycle 0")
    
    def shutdown(self) -> None:
        """
        Clean up resources on engine shutdown.
        
        Closes database connections and performs cleanup.
        """
        if hasattr(self, '_client'):
            self._client.close()
            logger.info("MongoDB connection closed")
        # ChromaDB client cleanup handled automatically
        logger.info(f"Engine {self.sim_id} shutdown complete")
