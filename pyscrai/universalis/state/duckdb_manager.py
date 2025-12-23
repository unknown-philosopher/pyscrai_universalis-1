"""
DuckDB State Manager - Physical state storage for PyScrAI Universalis.

This module provides DuckDB-based storage and querying for the simulation
world state, including spatial queries for movement and perception.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb

from pyscrai.data.schemas.models import (
    WorldState, 
    Actor, 
    Asset, 
    Environment,
    Location,
    Terrain,
    TerrainType,
)
from pyscrai.config import get_config
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


class DuckDBStateManager:
    """
    DuckDB-based state manager with spatial query support.
    
    Handles all physical state storage and retrieval, replacing MongoDB.
    Uses DuckDB Spatial extension for geographic queries.
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        simulation_id: Optional[str] = None,
        read_only: bool = False
    ):
        """
        Initialize the DuckDB state manager.
        
        Args:
            db_path: Path to DuckDB database file (defaults to config)
            simulation_id: Simulation identifier
            read_only: Open database in read-only mode
        """
        config = get_config()
        self._db_path = db_path or config.duckdb.path
        self._simulation_id = simulation_id or config.simulation.simulation_id
        self._read_only = read_only
        
        # Ensure directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to DuckDB
        self._conn = duckdb.connect(
            self._db_path, 
            read_only=read_only
        )
        
        # Load spatial extension
        self._init_spatial()
        
        # Initialize schema
        if not read_only:
            self._init_schema()
        
        logger.info(f"DuckDB State Manager initialized: {self._db_path}")
    
    def _init_spatial(self) -> None:
        """Initialize the DuckDB spatial extension."""
        try:
            self._conn.execute("INSTALL spatial;")
            self._conn.execute("LOAD spatial;")
            logger.info("DuckDB Spatial extension loaded")
        except Exception as e:
            logger.warning(f"Spatial extension may already be loaded: {e}")
            try:
                self._conn.execute("LOAD spatial;")
            except:
                pass
    
    def _init_schema(self) -> None:
        """Initialize database schema from schema.sql."""
        schema_path = Path(__file__).parent.parent.parent / "data" / "schemas" / "schema.sql"
        
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Execute schema statements (skip comments and empty lines)
            for statement in schema_sql.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        self._conn.execute(statement)
                    except Exception as e:
                        # Some statements might fail (e.g., CREATE OR REPLACE on first run)
                        logger.debug(f"Schema statement skipped: {e}")
            
            logger.info("Database schema initialized")
        else:
            logger.warning(f"Schema file not found: {schema_path}")
            self._create_minimal_schema()
    
    def _create_minimal_schema(self) -> None:
        """Create minimal schema if schema.sql not found."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id VARCHAR PRIMARY KEY,
                simulation_id VARCHAR NOT NULL,
                entity_type VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                description VARCHAR DEFAULT '',
                geometry GEOMETRY,
                properties JSON DEFAULT '{}',
                status VARCHAR DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS environment (
                id VARCHAR PRIMARY KEY,
                simulation_id VARCHAR NOT NULL,
                cycle INTEGER NOT NULL DEFAULT 0,
                time_of_day VARCHAR NOT NULL DEFAULT '00:00',
                weather VARCHAR NOT NULL DEFAULT 'Clear',
                global_events JSON DEFAULT '[]',
                terrain_modifiers JSON DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS terrain (
                id VARCHAR PRIMARY KEY,
                simulation_id VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                terrain_type VARCHAR NOT NULL,
                geometry GEOMETRY,
                movement_cost DOUBLE DEFAULT 1.0,
                passable BOOLEAN DEFAULT TRUE,
                properties JSON DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS world_state_snapshots (
                id VARCHAR PRIMARY KEY,
                simulation_id VARCHAR NOT NULL,
                cycle INTEGER NOT NULL,
                state_json JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    # =========================================================================
    # WORLD STATE OPERATIONS
    # =========================================================================
    
    def get_world_state(self, cycle: Optional[int] = None) -> Optional[WorldState]:
        """
        Get the current or specified cycle's world state.
        
        Args:
            cycle: Specific cycle to retrieve (None = latest)
        
        Returns:
            WorldState if found, None otherwise
        """
        # First try to get from snapshot
        if cycle is not None:
            result = self._conn.execute("""
                SELECT state_json FROM world_state_snapshots
                WHERE simulation_id = ? AND cycle = ?
                LIMIT 1
            """, [self._simulation_id, cycle]).fetchone()
        else:
            result = self._conn.execute("""
                SELECT state_json FROM world_state_snapshots
                WHERE simulation_id = ?
                ORDER BY cycle DESC
                LIMIT 1
            """, [self._simulation_id]).fetchone()
        
        if result:
            state_dict = json.loads(result[0]) if isinstance(result[0], str) else result[0]
            return WorldState(**state_dict)
        
        # Fallback: reconstruct from entities and environment tables
        return self._reconstruct_world_state()
    
    def _reconstruct_world_state(self) -> Optional[WorldState]:
        """Reconstruct WorldState from entity and environment tables."""
        # Get environment
        env_result = self._conn.execute("""
            SELECT cycle, time_of_day, weather, global_events, terrain_modifiers
            FROM environment
            WHERE simulation_id = ?
            ORDER BY cycle DESC
            LIMIT 1
        """, [self._simulation_id]).fetchone()
        
        if not env_result:
            return None
        
        cycle, time_of_day, weather, global_events, terrain_modifiers = env_result
        
        environment = Environment(
            cycle=cycle,
            time=time_of_day,
            weather=weather,
            global_events=json.loads(global_events) if isinstance(global_events, str) else (global_events or []),
            terrain_modifiers=json.loads(terrain_modifiers) if isinstance(terrain_modifiers, str) else (terrain_modifiers or {})
        )
        
        # Get actors
        actors = {}
        actor_results = self._conn.execute("""
            SELECT id, name, description, 
                   ST_X(geometry) as lon, ST_Y(geometry) as lat,
                   properties, status
            FROM entities
            WHERE simulation_id = ? AND entity_type = 'actor' AND status != 'deleted'
        """, [self._simulation_id]).fetchall()
        
        for row in actor_results:
            entity_id, name, description, lon, lat, properties, status = row
            props = json.loads(properties) if isinstance(properties, str) else (properties or {})
            
            actor = Actor(
                actor_id=entity_id,
                role=props.get('role', name),
                description=description or '',
                resolution=props.get('resolution', 'macro'),
                assets=props.get('assets', []),
                objectives=props.get('objectives', []),
                location=Location(lat=lat, lon=lon) if lat and lon else None,
                attributes=props.get('attributes', {}),
                status=status
            )
            actors[entity_id] = actor
        
        # Get assets
        assets = {}
        asset_results = self._conn.execute("""
            SELECT id, name, description,
                   ST_X(geometry) as lon, ST_Y(geometry) as lat,
                   properties, status
            FROM entities
            WHERE simulation_id = ? AND entity_type = 'asset' AND status != 'deleted'
        """, [self._simulation_id]).fetchall()
        
        for row in asset_results:
            entity_id, name, description, lon, lat, properties, status = row
            props = json.loads(properties) if isinstance(properties, str) else (properties or {})
            
            asset = Asset(
                asset_id=entity_id,
                name=name,
                asset_type=props.get('asset_type', 'Unknown'),
                location={'lat': lat, 'lon': lon} if lat and lon else {},
                attributes=props.get('attributes', {}),
                status=status
            )
            assets[entity_id] = asset
        
        return WorldState(
            simulation_id=self._simulation_id,
            environment=environment,
            actors=actors,
            assets=assets
        )
    
    def save_world_state(self, world_state: WorldState) -> None:
        """
        Save the world state to DuckDB.
        
        This saves both a complete snapshot and updates the entity tables.
        
        Args:
            world_state: WorldState to persist
        """
        cycle = world_state.environment.cycle
        
        # Save snapshot
        snapshot_id = f"{self._simulation_id}_cycle_{cycle}"
        state_json = world_state.model_dump_json()
        
        self._conn.execute("""
            INSERT OR REPLACE INTO world_state_snapshots (id, simulation_id, cycle, state_json)
            VALUES (?, ?, ?, ?)
        """, [snapshot_id, self._simulation_id, cycle, state_json])
        
        # Update environment
        env_id = f"{self._simulation_id}_env"
        self._conn.execute("""
            INSERT OR REPLACE INTO environment 
            (id, simulation_id, cycle, time_of_day, weather, global_events, terrain_modifiers, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            env_id,
            self._simulation_id,
            cycle,
            world_state.environment.time,
            world_state.environment.weather,
            json.dumps(world_state.environment.global_events),
            json.dumps(world_state.environment.terrain_modifiers)
        ])
        
        # Update entities (actors)
        for actor_id, actor in world_state.actors.items():
            self._upsert_entity(
                entity_id=actor_id,
                entity_type='actor',
                name=actor.role,
                description=actor.description,
                location=actor.location,
                properties={
                    'role': actor.role,
                    'resolution': actor.resolution.value if hasattr(actor.resolution, 'value') else actor.resolution,
                    'assets': actor.assets,
                    'objectives': actor.objectives,
                    'attributes': actor.attributes
                },
                status=actor.status
            )
        
        # Update entities (assets)
        for asset_id, asset in world_state.assets.items():
            location = asset.get_location_obj()
            self._upsert_entity(
                entity_id=asset_id,
                entity_type='asset',
                name=asset.name,
                description='',
                location=location,
                properties={
                    'asset_type': asset.asset_type,
                    'attributes': asset.attributes
                },
                status=asset.status
            )
        
        logger.info(f"World state saved: Cycle {cycle}")
    
    def _upsert_entity(
        self,
        entity_id: str,
        entity_type: str,
        name: str,
        description: str,
        location: Optional[Location],
        properties: Dict[str, Any],
        status: str
    ) -> None:
        """Insert or update an entity."""
        if location:
            self._conn.execute("""
                INSERT OR REPLACE INTO entities 
                (id, simulation_id, entity_type, name, description, geometry, properties, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ST_Point(?, ?), ?, ?, CURRENT_TIMESTAMP)
            """, [
                entity_id,
                self._simulation_id,
                entity_type,
                name,
                description,
                location.lon,
                location.lat,
                json.dumps(properties),
                status
            ])
        else:
            self._conn.execute("""
                INSERT OR REPLACE INTO entities 
                (id, simulation_id, entity_type, name, description, properties, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [
                entity_id,
                self._simulation_id,
                entity_type,
                name,
                description,
                json.dumps(properties),
                status
            ])
    
    def get_current_cycle(self) -> int:
        """Get the current (latest) cycle number."""
        result = self._conn.execute("""
            SELECT MAX(cycle) FROM environment WHERE simulation_id = ?
        """, [self._simulation_id]).fetchone()
        
        return result[0] if result and result[0] is not None else 0
    
    # =========================================================================
    # SPATIAL QUERIES
    # =========================================================================
    
    def get_entities_within_distance(
        self,
        center_lon: float,
        center_lat: float,
        distance_degrees: float,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all entities within a certain distance of a point.
        
        Args:
            center_lon: Center longitude
            center_lat: Center latitude
            distance_degrees: Distance in degrees (~111km per degree)
            entity_type: Filter by entity type (optional)
        
        Returns:
            List of entity dictionaries
        """
        if entity_type:
            results = self._conn.execute("""
                SELECT id, entity_type, name, 
                       ST_X(geometry) as lon, ST_Y(geometry) as lat,
                       ST_Distance(geometry, ST_Point(?, ?)) as distance,
                       properties, status
                FROM entities
                WHERE simulation_id = ? 
                  AND entity_type = ?
                  AND ST_DWithin(geometry, ST_Point(?, ?), ?)
                  AND status != 'deleted'
                ORDER BY distance
            """, [center_lon, center_lat, self._simulation_id, entity_type,
                  center_lon, center_lat, distance_degrees]).fetchall()
        else:
            results = self._conn.execute("""
                SELECT id, entity_type, name,
                       ST_X(geometry) as lon, ST_Y(geometry) as lat,
                       ST_Distance(geometry, ST_Point(?, ?)) as distance,
                       properties, status
                FROM entities
                WHERE simulation_id = ?
                  AND ST_DWithin(geometry, ST_Point(?, ?), ?)
                  AND status != 'deleted'
                ORDER BY distance
            """, [center_lon, center_lat, self._simulation_id,
                  center_lon, center_lat, distance_degrees]).fetchall()
        
        return [
            {
                'id': r[0],
                'entity_type': r[1],
                'name': r[2],
                'lon': r[3],
                'lat': r[4],
                'distance': r[5],
                'properties': json.loads(r[6]) if isinstance(r[6], str) else r[6],
                'status': r[7]
            }
            for r in results
        ]
    
    def get_terrain_at_point(
        self,
        lon: float,
        lat: float
    ) -> Optional[Dict[str, Any]]:
        """
        Get terrain information at a specific point.
        
        Args:
            lon: Longitude
            lat: Latitude
        
        Returns:
            Terrain dictionary or None
        """
        result = self._conn.execute("""
            SELECT id, name, terrain_type, movement_cost, passable, properties
            FROM terrain
            WHERE simulation_id = ?
              AND ST_Contains(geometry, ST_Point(?, ?))
            LIMIT 1
        """, [self._simulation_id, lon, lat]).fetchone()
        
        if result:
            return {
                'id': result[0],
                'name': result[1],
                'terrain_type': result[2],
                'movement_cost': result[3],
                'passable': result[4],
                'properties': json.loads(result[5]) if isinstance(result[5], str) else result[5]
            }
        return None
    
    def check_path_blocked(
        self,
        start_lon: float,
        start_lat: float,
        end_lon: float,
        end_lat: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a path between two points crosses impassable terrain.
        
        Args:
            start_lon, start_lat: Starting point
            end_lon, end_lat: Ending point
        
        Returns:
            Tuple of (is_blocked, blocking_terrain_name)
        """
        result = self._conn.execute("""
            SELECT name, terrain_type
            FROM terrain
            WHERE simulation_id = ?
              AND passable = FALSE
              AND ST_Intersects(
                  geometry,
                  ST_MakeLine(ST_Point(?, ?), ST_Point(?, ?))
              )
            LIMIT 1
        """, [self._simulation_id, start_lon, start_lat, end_lon, end_lat]).fetchone()
        
        if result:
            return True, result[0]
        return False, None
    
    def calculate_path_cost(
        self,
        start_lon: float,
        start_lat: float,
        end_lon: float,
        end_lat: float
    ) -> float:
        """
        Calculate the movement cost for a path based on terrain.
        
        Args:
            start_lon, start_lat: Starting point
            end_lon, end_lat: Ending point
        
        Returns:
            Total movement cost (1.0 = normal)
        """
        result = self._conn.execute("""
            SELECT COALESCE(MAX(movement_cost), 1.0) as max_cost
            FROM terrain
            WHERE simulation_id = ?
              AND ST_Intersects(
                  geometry,
                  ST_MakeLine(ST_Point(?, ?), ST_Point(?, ?))
              )
        """, [self._simulation_id, start_lon, start_lat, end_lon, end_lat]).fetchone()
        
        return result[0] if result else 1.0
    
    def calculate_distance(
        self,
        entity1_id: str,
        entity2_id: str
    ) -> Optional[float]:
        """
        Calculate distance between two entities (in degrees).
        
        Args:
            entity1_id: First entity ID
            entity2_id: Second entity ID
        
        Returns:
            Distance in degrees, or None if entities not found
        """
        result = self._conn.execute("""
            SELECT ST_Distance(e1.geometry, e2.geometry)
            FROM entities e1, entities e2
            WHERE e1.id = ? AND e2.id = ?
              AND e1.simulation_id = ? AND e2.simulation_id = ?
        """, [entity1_id, entity2_id, self._simulation_id, self._simulation_id]).fetchone()
        
        return result[0] if result else None
    
    # =========================================================================
    # TERRAIN OPERATIONS
    # =========================================================================
    
    def add_terrain(self, terrain: Terrain) -> None:
        """Add a terrain feature to the database."""
        self._conn.execute("""
            INSERT OR REPLACE INTO terrain
            (id, simulation_id, name, terrain_type, geometry, movement_cost, passable, properties)
            VALUES (?, ?, ?, ?, ST_GeomFromText(?), ?, ?, ?)
        """, [
            terrain.terrain_id,
            self._simulation_id,
            terrain.name,
            terrain.terrain_type.value if hasattr(terrain.terrain_type, 'value') else terrain.terrain_type,
            terrain.geometry_wkt,
            terrain.movement_cost,
            terrain.passable,
            json.dumps(terrain.attributes)
        ])
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def clear_simulation(self) -> None:
        """Clear all data for the current simulation."""
        self._conn.execute("DELETE FROM entities WHERE simulation_id = ?", [self._simulation_id])
        self._conn.execute("DELETE FROM environment WHERE simulation_id = ?", [self._simulation_id])
        self._conn.execute("DELETE FROM terrain WHERE simulation_id = ?", [self._simulation_id])
        self._conn.execute("DELETE FROM world_state_snapshots WHERE simulation_id = ?", [self._simulation_id])
        logger.info(f"Cleared simulation: {self._simulation_id}")
    
    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
        logger.info("DuckDB connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global instance
_state_manager: Optional[DuckDBStateManager] = None


def get_state_manager(
    simulation_id: Optional[str] = None,
    force_new: bool = False
) -> DuckDBStateManager:
    """
    Get the global state manager instance.
    
    Args:
        simulation_id: Optional simulation ID override
        force_new: Force creation of a new instance
    
    Returns:
        DuckDBStateManager instance
    """
    global _state_manager
    
    if _state_manager is None or force_new:
        _state_manager = DuckDBStateManager(simulation_id=simulation_id)
    
    return _state_manager

