"""
Simulation Engine - The Heartbeat of PyScrAI Universalis.

This module contains the Mesa-based simulation engine that manages
the temporal pulse of the simulation.
"""

import mesa
from datetime import datetime
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
import os
from dotenv import load_dotenv

from pyscrai.data.schemas.models import WorldState, Environment
from pyscrai.utils.logger import get_logger

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
    """
    
    def __init__(
        self, 
        sim_id: str,
        mongo_uri: Optional[str] = None,
        db_name: Optional[str] = None,
        archon: Optional[Any] = None
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
        self.archon = archon
        
        # Database connection
        self._mongo_uri = mongo_uri or os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self._db_name = db_name or os.getenv("MONGO_DB_NAME", "universalis_mongodb")
        
        self._client: MongoClient = MongoClient(self._mongo_uri)
        self.db: Database = self._client[self._db_name]
        self.states_collection: Collection = self.db["world_states"]
        
        # Sync cycle count from DB if restarting, else 0
        latest = self.states_collection.find_one(
            {"simulation_id": sim_id}, 
            sort=[("environment.cycle", -1)]
        )
        self.steps = latest["environment"]["cycle"] if latest else 0
        logger.info(f"Engine {self.sim_id} Initialized at Cycle {self.steps}")
    
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
        """
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
        
        if self.archon:
            # Use the Archon for adjudication
            final_output = self.archon.run_cycle(current_world_state)
            archon_summary = final_output.get("archon_summary", "No summary provided")
            final_world_state = final_output.get("world_state", current_world_state)
        else:
            # No archon attached - just pass through
            logger.warning("No Archon attached - passing world state through unchanged")
            archon_summary = "No adjudication (Archon not attached)"
            final_world_state = current_world_state
        
        # 4. Save the adjudicated result to the Ledger (MongoDB)
        self.save_adjudicated_state(final_world_state)
        
        return {
            "cycle": self.steps, 
            "status": "Adjudicated", 
            "summary": archon_summary
        }
    
    def attach_archon(self, archon: Any) -> None:
        """
        Attach an Archon instance for adjudication.
        
        Args:
            archon: The Archon instance to use for adjudication
        """
        self.archon = archon
        logger.info(f"Archon attached to engine {self.sim_id}")
    
    def reset(self) -> None:
        """Reset the simulation to cycle 0."""
        self.steps = 0
        logger.info(f"Engine {self.sim_id} reset to Cycle 0")

