from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ResolutionType(str, Enum):
    """Resolution type for agents - Macro (strategic) or Micro (social)."""
    MACRO = "macro"
    MICRO = "micro"


class Asset(BaseModel):
    """
    Represents a controllable asset in the simulation.
    
    Assets are physical or virtual resources that actors can control
    and use to achieve their objectives.
    """
    asset_id: str
    name: str
    asset_type: str  # e.g., "battalion", "vehicle", "facility"
    location: Dict[str, float]  # {"lat": 0.0, "lon": 0.0}
    status: str = "active"
    attributes: Dict[str, Any] = {}


class Actor(BaseModel):
    """
    Represents an agent in the simulation.
    
    Actors are the decision-making entities that perceive the world,
    form intents, and take actions.
    """
    actor_id: str
    role: str  # e.g., "Commander_Red", "Mayor"
    description: str
    assets: List[str] = []  # List of asset_ids they control
    objectives: List[str] = []
    resolution: ResolutionType = ResolutionType.MACRO  # Default to macro for backward compat


class Environment(BaseModel):
    """
    Represents the environmental state of the simulation.
    
    Contains temporal information and global events that affect all actors.
    """
    cycle: int = 0
    time: str = "08:00"
    weather: str = "Clear"
    global_events: List[str] = []  # A running log of major events


class WorldState(BaseModel):
    """
    The complete state of the simulation world.
    
    This is the "ground truth" that is persisted to MongoDB after each cycle.
    """
    simulation_id: str
    environment: Environment
    actors: Dict[str, Actor]
    assets: Dict[str, Asset]
    last_updated: datetime = Field(default_factory=datetime.now)

