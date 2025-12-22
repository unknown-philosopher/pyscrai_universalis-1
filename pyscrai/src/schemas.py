from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class Asset(BaseModel):
    asset_id: str
    name: str
    asset_type: str  # e.g., "battalion", "vehicle", "facility"
    location: Dict[str, float]  # {"lat": 0.0, "lon": 0.0}
    status: str = "active"
    attributes: Dict[str, Any] = {}

class Actor(BaseModel):
    actor_id: str
    role: str  # e.g., "Commander_Red", "Mayor"
    description: str
    assets: List[str] = []  # List of asset_ids they control
    objectives: List[str] = []

class Environment(BaseModel):
    cycle: int = 0
    time: str = "08:00"
    weather: str = "Clear"
    global_events: List[str] = []  # A running log of major events

class WorldState(BaseModel):
    simulation_id: str
    environment: Environment
    actors: Dict[str, Actor]
    assets: Dict[str, Asset]
    last_updated: datetime = Field(default_factory=datetime.now)