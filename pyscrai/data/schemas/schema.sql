-- DuckDB Schema for GeoScrAI/PyScrAI Universalis
-- This schema defines the spatial database structure for the simulation engine.
-- Uses DuckDB Spatial extension for geographic queries.

-- =============================================================================
-- EXTENSION LOADING
-- =============================================================================
-- Note: Extensions are loaded programmatically, not in schema file
-- INSTALL spatial;
-- LOAD spatial;

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Environment table: Stores cycle-level simulation state
CREATE TABLE IF NOT EXISTS environment (
    id VARCHAR PRIMARY KEY,
    simulation_id VARCHAR NOT NULL,
    cycle INTEGER NOT NULL DEFAULT 0,
    time_of_day VARCHAR NOT NULL DEFAULT '00:00',
    weather VARCHAR NOT NULL DEFAULT 'Clear',
    global_events JSON DEFAULT '[]',
    terrain_modifiers JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (simulation_id, cycle)
);

-- Entities table: Unified table for actors and assets with spatial geometry
CREATE TABLE IF NOT EXISTS entities (
    id VARCHAR PRIMARY KEY,
    simulation_id VARCHAR NOT NULL,
    entity_type VARCHAR NOT NULL,  -- 'actor', 'asset', 'landmark'
    name VARCHAR NOT NULL,
    description VARCHAR DEFAULT '',
    
    -- Spatial data (GEOMETRY column for DuckDB Spatial)
    geometry GEOMETRY,
    
    -- Entity-specific properties stored as JSON for flexibility
    properties JSON DEFAULT '{}',
    
    -- Status and timestamps
    status VARCHAR DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Terrain table: Stores terrain features as polygons for spatial queries
CREATE TABLE IF NOT EXISTS terrain (
    id VARCHAR PRIMARY KEY,
    simulation_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    terrain_type VARCHAR NOT NULL,  -- 'plains', 'mountains', 'forest', 'water', etc.
    
    -- Spatial geometry (POLYGON or MULTIPOLYGON)
    geometry GEOMETRY,
    
    -- Movement and accessibility
    movement_cost DOUBLE DEFAULT 1.0,  -- Multiplier for movement (1.0 = normal)
    passable BOOLEAN DEFAULT TRUE,      -- Whether entities can pass through
    
    -- Additional properties
    properties JSON DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relationships table: Stores relationships between entities
CREATE TABLE IF NOT EXISTS relationships (
    id VARCHAR PRIMARY KEY,
    simulation_id VARCHAR NOT NULL,
    source_entity_id VARCHAR NOT NULL,
    target_entity_id VARCHAR NOT NULL,
    relationship_type VARCHAR NOT NULL,  -- 'controls', 'ally', 'enemy', 'neutral'
    strength DOUBLE DEFAULT 0.5,          -- Relationship strength (0-1)
    properties JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (simulation_id, source_entity_id, target_entity_id, relationship_type)
);

-- World state snapshots: Historical record of complete world states
CREATE TABLE IF NOT EXISTS world_state_snapshots (
    id VARCHAR PRIMARY KEY,
    simulation_id VARCHAR NOT NULL,
    cycle INTEGER NOT NULL,
    state_json JSON NOT NULL,  -- Complete WorldState as JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (simulation_id, cycle)
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Index for simulation lookups
CREATE INDEX IF NOT EXISTS idx_entities_simulation ON entities(simulation_id);
CREATE INDEX IF NOT EXISTS idx_terrain_simulation ON terrain(simulation_id);
CREATE INDEX IF NOT EXISTS idx_environment_simulation ON environment(simulation_id);
CREATE INDEX IF NOT EXISTS idx_relationships_simulation ON relationships(simulation_id);

-- Index for entity type filtering
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_terrain_type ON terrain(terrain_type);

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status);

-- =============================================================================
-- SPATIAL INDEXES (created after data load for better performance)
-- =============================================================================
-- Note: DuckDB spatial indexes are created using R-tree
-- These should be created after initial data load:
-- CREATE INDEX idx_entities_geometry ON entities USING RTREE (geometry);
-- CREATE INDEX idx_terrain_geometry ON terrain USING RTREE (geometry);

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- View: Active actors with their locations
CREATE OR REPLACE VIEW active_actors AS
SELECT 
    id,
    simulation_id,
    name,
    description,
    geometry,
    ST_X(geometry) as lon,
    ST_Y(geometry) as lat,
    properties,
    status
FROM entities
WHERE entity_type = 'actor' AND status = 'active';

-- View: Active assets with their locations
CREATE OR REPLACE VIEW active_assets AS
SELECT 
    id,
    simulation_id,
    name,
    description,
    geometry,
    ST_X(geometry) as lon,
    ST_Y(geometry) as lat,
    properties,
    status
FROM entities
WHERE entity_type = 'asset' AND status = 'active';

-- View: Impassable terrain
CREATE OR REPLACE VIEW impassable_terrain AS
SELECT 
    id,
    simulation_id,
    name,
    terrain_type,
    geometry
FROM terrain
WHERE passable = FALSE;

-- =============================================================================
-- UTILITY FUNCTIONS (as SQL macros)
-- =============================================================================

-- Macro: Calculate distance between two entities (in degrees, approximate km = degrees * 111)
CREATE OR REPLACE MACRO entity_distance(entity1_id, entity2_id) AS (
    SELECT ST_Distance(e1.geometry, e2.geometry)
    FROM entities e1, entities e2
    WHERE e1.id = entity1_id AND e2.id = entity2_id
);

-- Macro: Check if entity is within distance of a point
CREATE OR REPLACE MACRO entity_within_distance(entity_id, lon, lat, distance_degrees) AS (
    SELECT ST_DWithin(
        geometry, 
        ST_Point(lon, lat), 
        distance_degrees
    )
    FROM entities
    WHERE id = entity_id
);

-- Macro: Get terrain type at a point
CREATE OR REPLACE MACRO terrain_at_point(lon, lat) AS (
    SELECT terrain_type, movement_cost, passable
    FROM terrain
    WHERE ST_Contains(geometry, ST_Point(lon, lat))
    LIMIT 1
);

-- =============================================================================
-- SAMPLE QUERIES (for reference)
-- =============================================================================

-- Example: Find all entities within 0.1 degrees (~11km) of a point
-- SELECT * FROM entities 
-- WHERE ST_DWithin(geometry, ST_Point(-118.25, 34.05), 0.1);

-- Example: Check if movement path crosses impassable terrain
-- SELECT COUNT(*) > 0 as blocked
-- FROM impassable_terrain
-- WHERE ST_Intersects(geometry, ST_MakeLine(ST_Point(-118.25, 34.05), ST_Point(-118.30, 34.10)));

-- Example: Get movement cost for a path
-- SELECT COALESCE(SUM(movement_cost), 1.0) as total_cost
-- FROM terrain
-- WHERE ST_Intersects(geometry, ST_MakeLine(ST_Point(-118.25, 34.05), ST_Point(-118.30, 34.10)));

