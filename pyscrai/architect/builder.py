"""
World Builder - Tools for creating .WORLD files for PyScrAI Universalis.

This module provides tools for compiling raw data sources into
properly formatted .WORLD files.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from pyscrai.architect.validator import WorldValidator, FullValidationResult
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WorldDefinition:
    """Definition for a world being built."""
    world_id: str
    name: str
    era_year: int
    era_period: str = "modern"
    technology_level: int = 7
    regions: List[Dict[str, Any]] = field(default_factory=list)
    asset_types: List[Dict[str, Any]] = field(default_factory=list)
    actor_templates: List[Dict[str, Any]] = field(default_factory=list)
    rules: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "world_id": self.world_id,
            "name": self.name,
            "version": "1.0.0",
            "era": {
                "year": self.era_year,
                "period": self.era_period,
                "technology_level": self.technology_level
            },
            "geography": {
                "regions": self.regions
            },
            "infrastructure": {
                "asset_types": self.asset_types
            },
            "actor_templates": self.actor_templates,
            "rules": self.rules
        }


class WorldBuilder:
    """
    Builder for creating .WORLD files.
    
    Provides a fluent API for defining worlds step by step.
    """
    
    def __init__(self, world_id: str, name: str):
        """
        Initialize the world builder.
        
        Args:
            world_id: Unique identifier for the world
            name: Human-readable name
        """
        self._definition = WorldDefinition(
            world_id=world_id,
            name=name,
            era_year=2023
        )
        self._validator = WorldValidator()
    
    def set_era(
        self, 
        year: int, 
        period: str = "modern",
        technology_level: int = 7
    ) -> "WorldBuilder":
        """
        Set the era for this world.
        
        Args:
            year: The year this world represents
            period: Era period (prehistoric, ancient, medieval, industrial, modern, future)
            technology_level: Technology level (1-10)
        
        Returns:
            self for chaining
        """
        self._definition.era_year = year
        self._definition.era_period = period
        self._definition.technology_level = min(10, max(1, technology_level))
        return self
    
    def add_region(
        self,
        region_id: str,
        name: str,
        region_type: str,
        lat: float = 0.0,
        lon: float = 0.0,
        climate: str = "temperate"
    ) -> "WorldBuilder":
        """
        Add a region to the world.
        
        Args:
            region_id: Unique region identifier
            name: Region name
            region_type: Type of region (city, rural, wilderness, etc.)
            lat: Latitude
            lon: Longitude
            climate: Climate type
        
        Returns:
            self for chaining
        """
        self._definition.regions.append({
            "region_id": region_id,
            "name": name,
            "type": region_type,
            "coordinates": {"lat": lat, "lon": lon},
            "climate": climate
        })
        return self
    
    def add_asset_type(
        self,
        type_id: str,
        name: str,
        category: str,
        attributes_schema: Optional[Dict] = None
    ) -> "WorldBuilder":
        """
        Add an asset type definition.
        
        Args:
            type_id: Unique type identifier
            name: Type name
            category: Category (vehicle, building, equipment, etc.)
            attributes_schema: Schema for type-specific attributes
        
        Returns:
            self for chaining
        """
        self._definition.asset_types.append({
            "type_id": type_id,
            "name": name,
            "category": category,
            "attributes_schema": attributes_schema or {}
        })
        return self
    
    def add_actor_template(
        self,
        template_id: str,
        role: str,
        resolution: str = "macro",
        default_objectives: Optional[List[str]] = None
    ) -> "WorldBuilder":
        """
        Add an actor template.
        
        Args:
            template_id: Unique template identifier
            role: Role name
            resolution: Agent resolution (macro or micro)
            default_objectives: Default objectives for this role
        
        Returns:
            self for chaining
        """
        self._definition.actor_templates.append({
            "template_id": template_id,
            "role": role,
            "resolution": resolution,
            "default_objectives": default_objectives or []
        })
        return self
    
    def set_rules(
        self,
        physics: Optional[Dict] = None,
        economics: Optional[Dict] = None,
        social: Optional[Dict] = None
    ) -> "WorldBuilder":
        """
        Set world rules.
        
        Args:
            physics: Physical rules
            economics: Economic rules
            social: Social rules
        
        Returns:
            self for chaining
        """
        self._definition.rules = {
            "physics": physics or {},
            "economics": economics or {},
            "social": social or {}
        }
        return self
    
    def validate(self) -> FullValidationResult:
        """
        Validate the current world definition.
        
        Returns:
            FullValidationResult
        """
        return self._validator.validate_world(self._definition.to_dict())
    
    def build(self) -> Dict[str, Any]:
        """
        Build and return the world definition.
        
        Returns:
            World definition dictionary
        """
        return self._definition.to_dict()
    
    def save(
        self, 
        output_dir: Optional[str] = None,
        validate_first: bool = True
    ) -> bool:
        """
        Save the world to a .WORLD file.
        
        Args:
            output_dir: Directory to save to (defaults to data/worlds)
            validate_first: Whether to validate before saving
        
        Returns:
            True if saved successfully
        """
        if validate_first:
            result = self.validate()
            if not result.valid:
                logger.error(f"Validation failed: {result.all_errors}")
                return False
        
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "worlds"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"{self._definition.world_id}.world.json"
        
        try:
            with open(output_path, 'w') as f:
                json.dump(self._definition.to_dict(), f, indent=2)
            logger.info(f"World saved to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving world: {e}")
            return False


class ScenarioBuilder:
    """
    Builder for creating .SCENARIO files.
    """
    
    def __init__(self, scenario_id: str, name: str, world_id: Optional[str] = None):
        """
        Initialize the scenario builder.
        
        Args:
            scenario_id: Unique scenario identifier
            name: Human-readable name
            world_id: Optional base world ID
        """
        self._data = {
            "scenario_id": scenario_id,
            "name": name,
            "world_id": world_id,
            "description": "",
            "version": "1.0.0",
            "initial_cycle": 0,
            "initial_time": "08:00",
            "initial_weather": "Clear",
            "initial_events": [],
            "actors": [],
            "assets": [],
            "patches": [],
            "variables": {}
        }
        self._validator = WorldValidator()
    
    def set_description(self, description: str) -> "ScenarioBuilder":
        """Set scenario description."""
        self._data["description"] = description
        return self
    
    def set_initial_conditions(
        self,
        cycle: int = 0,
        time: str = "08:00",
        weather: str = "Clear"
    ) -> "ScenarioBuilder":
        """Set initial conditions."""
        self._data["initial_cycle"] = cycle
        self._data["initial_time"] = time
        self._data["initial_weather"] = weather
        return self
    
    def add_initial_event(self, event: str) -> "ScenarioBuilder":
        """Add an initial event."""
        self._data["initial_events"].append(event)
        return self
    
    def add_actor(
        self,
        actor_id: str,
        role: str,
        description: str = "",
        resolution: str = "macro",
        assets: Optional[List[str]] = None,
        objectives: Optional[List[str]] = None
    ) -> "ScenarioBuilder":
        """Add an actor to the scenario."""
        self._data["actors"].append({
            "actor_id": actor_id,
            "role": role,
            "description": description,
            "resolution": resolution,
            "assets": assets or [],
            "objectives": objectives or []
        })
        return self
    
    def add_asset(
        self,
        asset_id: str,
        name: str,
        asset_type: str,
        lat: float = 0.0,
        lon: float = 0.0,
        status: str = "active",
        attributes: Optional[Dict] = None
    ) -> "ScenarioBuilder":
        """Add an asset to the scenario."""
        self._data["assets"].append({
            "asset_id": asset_id,
            "name": name,
            "asset_type": asset_type,
            "location": {"lat": lat, "lon": lon},
            "status": status,
            "attributes": attributes or {}
        })
        return self
    
    def add_patch(
        self,
        op: str,
        path: str,
        value: Any = None,
        from_path: Optional[str] = None
    ) -> "ScenarioBuilder":
        """Add a JSON Patch operation."""
        patch = {"op": op, "path": path}
        if value is not None:
            patch["value"] = value
        if from_path is not None:
            patch["from"] = from_path
        self._data["patches"].append(patch)
        return self
    
    def set_variable(self, key: str, value: Any) -> "ScenarioBuilder":
        """Set a scenario variable."""
        self._data["variables"][key] = value
        return self
    
    def validate(self) -> FullValidationResult:
        """Validate the scenario."""
        return self._validator.validate_scenario(self._data)
    
    def build(self) -> Dict[str, Any]:
        """Build and return the scenario definition."""
        return self._data
    
    def save(
        self,
        output_dir: Optional[str] = None,
        validate_first: bool = True
    ) -> bool:
        """Save the scenario to a .SCENARIO file."""
        if validate_first:
            result = self.validate()
            if not result.valid:
                logger.error(f"Validation failed: {result.all_errors}")
                return False
        
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "scenarios"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"{self._data['scenario_id']}.scenario.json"
        
        try:
            with open(output_path, 'w') as f:
                json.dump(self._data, f, indent=2)
            logger.info(f"Scenario saved to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving scenario: {e}")
            return False

