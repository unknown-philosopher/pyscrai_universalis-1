"""
Seeder - Database initialization for PyScrAI Universalis.

This module provides functions to seed the DuckDB database with
initial scenario data including actors, assets, and terrain.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from pyscrai.data.schemas.models import (
    WorldState, 
    Environment, 
    Actor, 
    Asset,
    Location,
    Terrain,
    TerrainType,
    ResolutionType
)
from pyscrai.universalis.state.duckdb_manager import DuckDBStateManager, get_state_manager
from pyscrai.architect.schema_init import init_database, verify_schema
from pyscrai.config import get_config
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


def seed_simulation(
    simulation_id: str = "Alpha_Scenario",
    db_path: Optional[str] = None,
    clear_existing: bool = True
) -> WorldState:
    """
    Seed the database with an initial scenario.
    
    Args:
        simulation_id: Unique identifier for the simulation
        db_path: Path to DuckDB database (defaults to config)
        clear_existing: Whether to clear existing data for this simulation_id
    
    Returns:
        The initial WorldState that was seeded
    """
    logger.info(f"Seeding Database for Scenario: {simulation_id}...")
    
    # Initialize database and schema
    conn = init_database(db_path)
    
    # Create state manager
    state_manager = DuckDBStateManager(
        db_path=db_path,
        simulation_id=simulation_id
    )
    
    if clear_existing:
        state_manager.clear_simulation()
        logger.info(f"Cleared existing data for {simulation_id}")
    
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
                resolution=ResolutionType.MACRO,
                assets=["Truck_01", "Helo_Alpha"],
                objectives=[
                    "Protect civilian lives and property",
                    "Coordinate fire response assets effectively",
                    "Maintain communication with all units"
                ],
                location=Location(lat=34.05, lon=-118.25)
            )
        },
        assets={
            "Truck_01": Asset(
                asset_id="Truck_01",
                name="Fire Truck Alpha",
                asset_type="Ground Unit",
                location={"lat": 34.05, "lon": -118.25},
                attributes={"water_level": 100, "fuel": 100},
                status="active"
            ),
            "Helo_Alpha": Asset(
                asset_id="Helo_Alpha",
                name="Water Bomber 1",
                asset_type="Air Unit",
                location={"lat": 34.10, "lon": -118.30},
                attributes={"status": "grounded"},
                status="standby"
            )
        }
    )
    
    # Save to DuckDB
    state_manager.save_world_state(initial_state)
    
    # Optionally add some default terrain
    _seed_default_terrain(state_manager, simulation_id)
    
    logger.info("Database Seeded Successfully!")
    
    return initial_state


def _seed_default_terrain(
    state_manager: DuckDBStateManager,
    simulation_id: str
) -> None:
    """
    Seed default terrain features for the simulation.
    
    Args:
        state_manager: DuckDB state manager
        simulation_id: Simulation identifier
    """
    # Add some example terrain (mountains blocking direct routes)
    terrain_features = [
        Terrain(
            terrain_id=f"{simulation_id}_mountains_1",
            name="San Gabriel Mountains",
            terrain_type=TerrainType.MOUNTAINS,
            geometry_wkt="POLYGON((-118.1 34.2, -118.0 34.2, -118.0 34.3, -118.1 34.3, -118.1 34.2))",
            movement_cost=3.0,
            passable=True,  # Passable but slow
            attributes={"elevation_range": "1500-3000m"}
        ),
        Terrain(
            terrain_id=f"{simulation_id}_water_1",
            name="Los Angeles River",
            terrain_type=TerrainType.WATER,
            geometry_wkt="POLYGON((-118.25 34.04, -118.24 34.04, -118.24 34.06, -118.25 34.06, -118.25 34.04))",
            movement_cost=float('inf'),
            passable=False,  # Impassable
            attributes={"type": "river"}
        ),
        Terrain(
            terrain_id=f"{simulation_id}_urban_1",
            name="Downtown LA",
            terrain_type=TerrainType.URBAN,
            geometry_wkt="POLYGON((-118.26 34.04, -118.23 34.04, -118.23 34.06, -118.26 34.06, -118.26 34.04))",
            movement_cost=1.5,
            passable=True,
            attributes={"density": "high"}
        )
    ]
    
    for terrain in terrain_features:
        try:
            state_manager.add_terrain(terrain)
            logger.debug(f"Added terrain: {terrain.name}")
        except Exception as e:
            logger.warning(f"Could not add terrain {terrain.name}: {e}")


def seed_custom_scenario(
    simulation_id: str,
    environment: Dict[str, Any],
    actors: Dict[str, Dict[str, Any]],
    assets: Dict[str, Dict[str, Any]],
    terrain: Optional[List[Dict[str, Any]]] = None,
    db_path: Optional[str] = None,
    clear_existing: bool = True
) -> WorldState:
    """
    Seed the database with a custom scenario.
    
    Args:
        simulation_id: Unique identifier for the simulation
        environment: Environment configuration dict
        actors: Dict of actor configurations
        assets: Dict of asset configurations
        terrain: Optional list of terrain feature dicts
        db_path: Path to DuckDB database (defaults to config)
        clear_existing: Whether to clear existing data for this simulation_id
    
    Returns:
        The initial WorldState that was seeded
    """
    logger.info(f"Seeding Custom Scenario: {simulation_id}...")
    
    # Initialize database
    conn = init_database(db_path)
    
    # Create state manager
    state_manager = DuckDBStateManager(
        db_path=db_path,
        simulation_id=simulation_id
    )
    
    if clear_existing:
        state_manager.clear_simulation()
    
    # Build the WorldState from provided data
    env = Environment(**environment)
    
    # Build actors with proper Location handling
    actor_models = {}
    for k, v in actors.items():
        # Handle location conversion
        if 'location' in v and v['location']:
            if isinstance(v['location'], dict):
                v['location'] = Location(**v['location'])
        actor_models[k] = Actor(**v)
    
    asset_models = {k: Asset(**v) for k, v in assets.items()}
    
    initial_state = WorldState(
        simulation_id=simulation_id,
        environment=env,
        actors=actor_models,
        assets=asset_models
    )
    
    # Save to DuckDB
    state_manager.save_world_state(initial_state)
    
    # Add terrain if provided
    if terrain:
        for t in terrain:
            terrain_obj = Terrain(**t)
            state_manager.add_terrain(terrain_obj)
    
    logger.info(f"Custom Scenario {simulation_id} Seeded Successfully!")
    
    return initial_state


def seed_from_file(
    scenario_file: str,
    simulation_id: Optional[str] = None,
    db_path: Optional[str] = None,
    clear_existing: bool = True
) -> WorldState:
    """
    Seed the database from a JSON scenario file.
    
    Args:
        scenario_file: Path to scenario JSON file
        simulation_id: Override simulation ID (uses file's if not provided)
        db_path: Path to DuckDB database
        clear_existing: Whether to clear existing data
    
    Returns:
        The initial WorldState that was seeded
    """
    scenario_path = Path(scenario_file)
    
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_file}")
    
    with open(scenario_path, 'r') as f:
        data = json.load(f)
    
    sim_id = simulation_id or data.get('simulation_id', scenario_path.stem)
    
    return seed_custom_scenario(
        simulation_id=sim_id,
        environment=data.get('environment', {}),
        actors=data.get('actors', {}),
        assets=data.get('assets', {}),
        terrain=data.get('terrain'),
        db_path=db_path,
        clear_existing=clear_existing
    )


def get_seeded_simulations(db_path: Optional[str] = None) -> List[str]:
    """
    Get list of simulation IDs that have been seeded.
    
    Args:
        db_path: Path to DuckDB database
    
    Returns:
        List of simulation IDs
    """
    import duckdb
    
    config = get_config()
    db_path = db_path or config.duckdb.path
    
    if not Path(db_path).exists():
        return []
    
    conn = duckdb.connect(db_path, read_only=True)
    
    try:
        result = conn.execute("""
            SELECT DISTINCT simulation_id FROM environment
        """).fetchall()
        
        return [row[0] for row in result]
    except Exception:
        return []
    finally:
        conn.close()


if __name__ == "__main__":
    seed_simulation()
