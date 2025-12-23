"""
Schema Initialization - DuckDB schema setup for PyScrAI Universalis.

This module provides functions to initialize the DuckDB database with
the required schema and spatial extension.
"""

from pathlib import Path
from typing import Optional

import duckdb

from pyscrai.config import get_config
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


def init_database(
    db_path: Optional[str] = None,
    schema_path: Optional[str] = None,
    force_recreate: bool = False
) -> duckdb.DuckDBPyConnection:
    """
    Initialize the DuckDB database with schema.
    
    Args:
        db_path: Path to DuckDB database file
        schema_path: Path to schema.sql file
        force_recreate: If True, drop and recreate tables
    
    Returns:
        DuckDB connection object
    """
    config = get_config()
    db_path = db_path or config.duckdb.path
    
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to DuckDB
    conn = duckdb.connect(db_path)
    
    # Load spatial extension
    load_spatial_extension(conn)
    
    # Find schema file
    if schema_path is None:
        schema_path = Path(__file__).parent.parent / "data" / "schemas" / "schema.sql"
    else:
        schema_path = Path(schema_path)
    
    # Apply schema
    if schema_path.exists():
        apply_schema(conn, schema_path, force_recreate)
    else:
        logger.warning(f"Schema file not found: {schema_path}")
        create_minimal_schema(conn)
    
    logger.info(f"Database initialized: {db_path}")
    return conn


def load_spatial_extension(conn: duckdb.DuckDBPyConnection) -> None:
    """Load the DuckDB spatial extension."""
    try:
        conn.execute("INSTALL spatial;")
        logger.info("Spatial extension installed")
    except Exception as e:
        logger.debug(f"Spatial extension may already be installed: {e}")
    
    try:
        conn.execute("LOAD spatial;")
        logger.info("Spatial extension loaded")
    except Exception as e:
        logger.warning(f"Could not load spatial extension: {e}")


def apply_schema(
    conn: duckdb.DuckDBPyConnection,
    schema_path: Path,
    force_recreate: bool = False
) -> None:
    """
    Apply schema from SQL file to database.
    
    Args:
        conn: DuckDB connection
        schema_path: Path to schema.sql file
        force_recreate: If True, drop existing tables first
    """
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    if force_recreate:
        # Drop existing tables
        tables = ['world_state_snapshots', 'relationships', 'terrain', 'entities', 'environment']
        for table in tables:
            try:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
                logger.debug(f"Dropped table: {table}")
            except Exception as e:
                logger.debug(f"Could not drop table {table}: {e}")
    
    # Execute schema statements
    for statement in schema_sql.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                conn.execute(statement)
            except Exception as e:
                # Some statements might fail (e.g., CREATE IF NOT EXISTS when exists)
                logger.debug(f"Schema statement skipped: {e}")
    
    logger.info("Schema applied successfully")


def create_minimal_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Create minimal schema if schema.sql not found.
    
    Args:
        conn: DuckDB connection
    """
    conn.execute("""
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
    
    conn.execute("""
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
    
    conn.execute("""
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
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS world_state_snapshots (
            id VARCHAR PRIMARY KEY,
            simulation_id VARCHAR NOT NULL,
            cycle INTEGER NOT NULL,
            state_json JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    logger.info("Minimal schema created")


def create_spatial_indexes(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Create spatial indexes for better query performance.
    
    Should be called after initial data load.
    
    Args:
        conn: DuckDB connection
    """
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_geometry ON entities USING RTREE (geometry)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_terrain_geometry ON terrain USING RTREE (geometry)")
        logger.info("Spatial indexes created")
    except Exception as e:
        logger.warning(f"Could not create spatial indexes: {e}")


def verify_schema(conn: duckdb.DuckDBPyConnection) -> bool:
    """
    Verify that required tables exist.
    
    Args:
        conn: DuckDB connection
    
    Returns:
        True if all required tables exist
    """
    required_tables = ['environment', 'entities', 'terrain', 'world_state_snapshots']
    
    result = conn.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'main'
    """).fetchall()
    
    existing_tables = {row[0] for row in result}
    
    missing = set(required_tables) - existing_tables
    if missing:
        logger.warning(f"Missing tables: {missing}")
        return False
    
    logger.info("Schema verification passed")
    return True

