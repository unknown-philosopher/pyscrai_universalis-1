"""
Pydantic Models for PyScrAI Universalis.

This module defines the core data models used throughout the simulation:
- WorldState: The complete state of a simulation at a point in time
- Actor: An agent that can perform actions
- Asset: A resource controlled by actors
- Environment: Environmental conditions (time, weather, events)
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ResolutionType(str, Enum):
    """Resolution type for agents."""
    MACRO = "macro"  # Strategic, organizational-level
    MICRO = "micro"  # Individual, social-level


class EntityType(str, Enum):
    """Type of entity in the simulation."""
    ACTOR = "actor"
    ASSET = "asset"
    TERRAIN = "terrain"
    LANDMARK = "landmark"


class TerrainType(str, Enum):
    """Types of terrain that affect movement and actions."""
    PLAINS = "plains"
    MOUNTAINS = "mountains"
    FOREST = "forest"
    WATER = "water"
    URBAN = "urban"
    DESERT = "desert"
    ROAD = "road"


class Location(BaseModel):
    """Geographic location with optional elevation."""
    lat: float = Field(..., description="Latitude in degrees")
    lon: float = Field(..., description="Longitude in degrees")
    elevation: Optional[float] = Field(None, description="Elevation in meters")
    
    def to_wkt_point(self) -> str:
        """Convert to WKT POINT format for DuckDB Spatial."""
        return f"POINT({self.lon} {self.lat})"


class Actor(BaseModel):
    """
    An agent that can perform actions in the simulation.
    
    Actors can be either MACRO (strategic) or MICRO (individual) resolution.
    """
    actor_id: str = Field(..., description="Unique identifier")
    role: str = Field(..., description="Role or title of the actor")
    description: str = Field("", description="Description of the actor")
    resolution: ResolutionType = Field(
        ResolutionType.MACRO, 
        description="Resolution type (macro/micro)"
    )
    assets: List[str] = Field(
        default_factory=list, 
        description="List of asset IDs controlled by this actor"
    )
    objectives: List[str] = Field(
        default_factory=list,
        description="Actor's objectives"
    )
    location: Optional[Location] = Field(
        None, 
        description="Current location"
    )
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes"
    )
    status: str = Field("active", description="Current status")


class Asset(BaseModel):
    """
    A resource or unit that can be controlled by actors.
    """
    asset_id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Display name")
    asset_type: str = Field(..., description="Type of asset (Ground Unit, Air Unit, etc.)")
    location: Dict[str, float] = Field(
        default_factory=dict,
        description="Location as {lat, lon}"
    )
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Asset-specific attributes"
    )
    status: str = Field("active", description="Current status")
    
    def get_location_obj(self) -> Optional[Location]:
        """Get location as Location object."""
        if self.location and "lat" in self.location and "lon" in self.location:
            return Location(
                lat=self.location["lat"],
                lon=self.location["lon"],
                elevation=self.location.get("elevation")
            )
        return None


class Environment(BaseModel):
    """
    Environmental state of the simulation.
    """
    cycle: int = Field(0, description="Current simulation cycle")
    time: str = Field("00:00", description="Current time (HH:MM format)")
    weather: str = Field("Clear", description="Current weather conditions")
    global_events: List[str] = Field(
        default_factory=list,
        description="Global events log"
    )
    terrain_modifiers: Dict[str, float] = Field(
        default_factory=dict,
        description="Terrain-based modifiers"
    )


class WorldState(BaseModel):
    """
    The complete state of a simulation at a point in time.
    
    This is the "ground truth" that gets persisted and used by
    agents and the Archon for decision-making.
    """
    simulation_id: str = Field(..., description="Unique simulation identifier")
    environment: Environment = Field(
        default_factory=Environment,
        description="Environmental state"
    )
    actors: Dict[str, Actor] = Field(
        default_factory=dict,
        description="Map of actor_id -> Actor"
    )
    assets: Dict[str, Asset] = Field(
        default_factory=dict,
        description="Map of asset_id -> Asset"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Intent(BaseModel):
    """
    An intent generated by an agent.
    """
    actor_id: str = Field(..., description="Actor who generated this intent")
    content: str = Field(..., description="The intent text/description")
    cycle: int = Field(..., description="Cycle when intent was generated")
    priority: float = Field(0.5, description="Priority (0-1)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class Terrain(BaseModel):
    """
    Terrain feature that affects movement and actions.
    Used for spatial constraints in DuckDB.
    """
    terrain_id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Display name")
    terrain_type: TerrainType = Field(..., description="Type of terrain")
    geometry_wkt: str = Field(..., description="WKT geometry (POLYGON or MULTIPOLYGON)")
    movement_cost: float = Field(1.0, description="Movement cost modifier")
    passable: bool = Field(True, description="Whether entities can pass through")
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes"
    )

