"""
Seeder - Database initialization for PyScrAI Universalis.

This module provides functions to seed the MongoDB database with
initial scenario data.
"""

from pymongo import MongoClient
from datetime import datetime
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

from pyscrai.data.schemas.models import WorldState, Environment, Actor, Asset
from pyscrai.utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)


def get_mongo_collection(
    collection_name: str = "world_states",
    mongo_uri: Optional[str] = None,
    db_name: Optional[str] = None
):
    """
    Get a MongoDB collection.
    
    Args:
        collection_name: Name of the collection
        mongo_uri: MongoDB URI (defaults to env var)
        db_name: Database name (defaults to env var)
    
    Returns:
        MongoDB collection
    """
    uri = mongo_uri or os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    name = db_name or os.getenv("MONGO_DB_NAME", "universalis_mongodb")
    
    client = MongoClient(uri)
    db = client[name]
    return db[collection_name]


def seed_simulation(
    simulation_id: str = "Alpha_Scenario",
    mongo_uri: Optional[str] = None,
    db_name: Optional[str] = None,
    clear_existing: bool = True
) -> WorldState:
    """
    Seed the database with an initial scenario.
    
    Args:
        simulation_id: Unique identifier for the simulation
        mongo_uri: MongoDB URI (defaults to env var)
        db_name: Database name (defaults to env var)
        clear_existing: Whether to clear existing data for this simulation_id
    
    Returns:
        The initial WorldState that was seeded
    """
    logger.info(f"Seeding Database for Scenario: {simulation_id}...")
    
    collection = get_mongo_collection(
        mongo_uri=mongo_uri,
        db_name=db_name
    )
    
    # Define Initial Scenario State (Cycle 0)
    initial_state = WorldState(
        simulation_id=simulation_id,
        environment=Environment(
            cycle=0, 
            time="06:00", 
            weather="Dry, High Winds",
            global_events=["Simulation Initialized: Wildfire Warning in effect."]
        ),
        actors={
            "Actor_FireChief": Actor(
                actor_id="Actor_FireChief", 
                role="Incident Commander", 
                description="Responsible for managing city fire response assets.",
                assets=["Truck_01", "Helo_Alpha"],
                objectives=[
                    "Protect civilian lives and property",
                    "Coordinate fire response assets effectively",
                    "Maintain communication with all units"
                ]
            )
        },
        assets={
            "Truck_01": Asset(
                asset_id="Truck_01",
                name="Fire Truck Alpha",
                asset_type="Ground Unit",
                location={"lat": 34.05, "lon": -118.25},
                attributes={"water_level": 100, "fuel": 100}
            ),
            "Helo_Alpha": Asset(
                asset_id="Helo_Alpha",
                name="Water Bomber 1",
                asset_type="Air Unit",
                location={"lat": 34.10, "lon": -118.30},
                attributes={"status": "grounded"}
            )
        }
    )
    
    if clear_existing:
        # Clear old data for this scenario ID only
        deleted = collection.delete_many({"simulation_id": simulation_id})
        logger.info(f"Cleared {deleted.deleted_count} existing documents for {simulation_id}")
    
    # Insert Cycle 0
    collection.insert_one(initial_state.model_dump())
    logger.info("Database Seeded Successfully!")
    
    return initial_state


def seed_custom_scenario(
    simulation_id: str,
    environment: Dict[str, Any],
    actors: Dict[str, Dict[str, Any]],
    assets: Dict[str, Dict[str, Any]],
    mongo_uri: Optional[str] = None,
    db_name: Optional[str] = None,
    clear_existing: bool = True
) -> WorldState:
    """
    Seed the database with a custom scenario.
    
    Args:
        simulation_id: Unique identifier for the simulation
        environment: Environment configuration dict
        actors: Dict of actor configurations
        assets: Dict of asset configurations
        mongo_uri: MongoDB URI (defaults to env var)
        db_name: Database name (defaults to env var)
        clear_existing: Whether to clear existing data for this simulation_id
    
    Returns:
        The initial WorldState that was seeded
    """
    logger.info(f"Seeding Custom Scenario: {simulation_id}...")
    
    collection = get_mongo_collection(
        mongo_uri=mongo_uri,
        db_name=db_name
    )
    
    # Build the WorldState from provided data
    env = Environment(**environment)
    actor_models = {k: Actor(**v) for k, v in actors.items()}
    asset_models = {k: Asset(**v) for k, v in assets.items()}
    
    initial_state = WorldState(
        simulation_id=simulation_id,
        environment=env,
        actors=actor_models,
        assets=asset_models
    )
    
    if clear_existing:
        deleted = collection.delete_many({"simulation_id": simulation_id})
        logger.info(f"Cleared {deleted.deleted_count} existing documents for {simulation_id}")
    
    collection.insert_one(initial_state.model_dump())
    logger.info(f"Custom Scenario {simulation_id} Seeded Successfully!")
    
    return initial_state


if __name__ == "__main__":
    seed_simulation()

