"""
Seed-to-State Pipeline - World compilation for PyScrAI Universalis.

This module provides the pipeline for merging .WORLD (static base)
with .SCENARIO (dynamic delta) files to create initial WorldState.
"""

import json
import copy
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field

from pyscrai.data.schemas.models import WorldState, Environment, Actor, Asset
from pyscrai.architect.validator import WorldValidator, FullValidationResult
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """Result of the seed-to-state pipeline."""
    success: bool
    world_state: Optional[WorldState] = None
    validation_result: Optional[FullValidationResult] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class JSONPatch:
    """
    JSON Patch implementation (RFC 6902).
    
    Supports operations: add, remove, replace, move, copy, test
    """
    
    @staticmethod
    def apply(document: Dict, patches: List[Dict]) -> Dict:
        """
        Apply JSON Patch operations to a document.
        
        Args:
            document: The document to patch
            patches: List of patch operations
        
        Returns:
            Patched document
        """
        result = copy.deepcopy(document)
        
        for patch in patches:
            op = patch.get("op")
            path = patch.get("path", "")
            value = patch.get("value")
            from_path = patch.get("from")
            
            if op == "add":
                result = JSONPatch._add(result, path, value)
            elif op == "remove":
                result = JSONPatch._remove(result, path)
            elif op == "replace":
                result = JSONPatch._replace(result, path, value)
            elif op == "move":
                result = JSONPatch._move(result, path, from_path)
            elif op == "copy":
                result = JSONPatch._copy(result, path, from_path)
            elif op == "test":
                if not JSONPatch._test(result, path, value):
                    raise ValueError(f"Test failed at path: {path}")
        
        return result
    
    @staticmethod
    def _parse_path(path: str) -> List[str]:
        """Parse JSON Pointer path."""
        if not path:
            return []
        if not path.startswith("/"):
            raise ValueError(f"Invalid path: {path}")
        parts = path[1:].split("/")
        return [p.replace("~1", "/").replace("~0", "~") for p in parts]
    
    @staticmethod
    def _get_value(doc: Dict, path: str) -> Any:
        """Get value at path."""
        parts = JSONPatch._parse_path(path)
        current = doc
        for part in parts:
            if isinstance(current, dict):
                current = current[part]
            elif isinstance(current, list):
                current = current[int(part)]
        return current
    
    @staticmethod
    def _set_value(doc: Dict, path: str, value: Any) -> Dict:
        """Set value at path."""
        parts = JSONPatch._parse_path(path)
        if not parts:
            return value
        
        current = doc
        for part in parts[:-1]:
            if isinstance(current, dict):
                if part not in current:
                    current[part] = {}
                current = current[part]
            elif isinstance(current, list):
                current = current[int(part)]
        
        last = parts[-1]
        if isinstance(current, dict):
            current[last] = value
        elif isinstance(current, list):
            if last == "-":
                current.append(value)
            else:
                current[int(last)] = value
        
        return doc
    
    @staticmethod
    def _add(doc: Dict, path: str, value: Any) -> Dict:
        return JSONPatch._set_value(doc, path, value)
    
    @staticmethod
    def _remove(doc: Dict, path: str) -> Dict:
        parts = JSONPatch._parse_path(path)
        current = doc
        for part in parts[:-1]:
            if isinstance(current, dict):
                current = current[part]
            elif isinstance(current, list):
                current = current[int(part)]
        
        last = parts[-1]
        if isinstance(current, dict):
            del current[last]
        elif isinstance(current, list):
            del current[int(last)]
        
        return doc
    
    @staticmethod
    def _replace(doc: Dict, path: str, value: Any) -> Dict:
        return JSONPatch._set_value(doc, path, value)
    
    @staticmethod
    def _move(doc: Dict, path: str, from_path: str) -> Dict:
        value = JSONPatch._get_value(doc, from_path)
        doc = JSONPatch._remove(doc, from_path)
        return JSONPatch._add(doc, path, value)
    
    @staticmethod
    def _copy(doc: Dict, path: str, from_path: str) -> Dict:
        value = copy.deepcopy(JSONPatch._get_value(doc, from_path))
        return JSONPatch._add(doc, path, value)
    
    @staticmethod
    def _test(doc: Dict, path: str, value: Any) -> bool:
        return JSONPatch._get_value(doc, path) == value


class SeedToStatePipeline:
    """
    Pipeline for compiling .WORLD + .SCENARIO into WorldState.
    """
    
    def __init__(
        self,
        worlds_dir: Optional[str] = None,
        scenarios_dir: Optional[str] = None,
        validate: bool = True
    ):
        """
        Initialize the pipeline.
        
        Args:
            worlds_dir: Directory containing .WORLD files
            scenarios_dir: Directory containing .SCENARIO files
            validate: Whether to validate files
        """
        base_dir = Path(__file__).parent.parent / "data"
        self._worlds_dir = Path(worlds_dir) if worlds_dir else base_dir / "worlds"
        self._scenarios_dir = Path(scenarios_dir) if scenarios_dir else base_dir / "scenarios"
        self._validate = validate
        self._validator = WorldValidator() if validate else None
    
    def compile(
        self,
        scenario_id: str,
        world_id: Optional[str] = None
    ) -> PipelineResult:
        """
        Compile a scenario into a WorldState.
        
        Args:
            scenario_id: ID of the scenario to compile
            world_id: Optional world ID override
        
        Returns:
            PipelineResult with the compiled WorldState
        """
        errors = []
        warnings = []
        
        # Load scenario
        scenario_data = self._load_scenario(scenario_id)
        if scenario_data is None:
            return PipelineResult(
                success=False,
                errors=[f"Could not load scenario: {scenario_id}"]
            )
        
        # Determine world_id
        world_id = world_id or scenario_data.get("world_id")
        
        # Load world if specified
        world_data = None
        if world_id:
            world_data = self._load_world(world_id)
            if world_data is None:
                warnings.append(f"Could not load world: {world_id}, proceeding without base")
        
        # Validate scenario
        validation_result = None
        if self._validate:
            validation_result = self._validator.validate_scenario(scenario_data)
            if not validation_result.valid:
                errors.extend(validation_result.all_errors)
                if errors:
                    return PipelineResult(
                        success=False,
                        validation_result=validation_result,
                        errors=errors,
                        warnings=warnings
                    )
        
        # Merge world + scenario
        try:
            merged = self._merge(world_data, scenario_data)
            world_state = self._build_world_state(merged, scenario_id)
            
            return PipelineResult(
                success=True,
                world_state=world_state,
                validation_result=validation_result,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error compiling scenario: {e}")
            return PipelineResult(
                success=False,
                errors=[str(e)],
                warnings=warnings
            )
    
    def _load_world(self, world_id: str) -> Optional[Dict]:
        """Load a .WORLD file."""
        world_path = self._worlds_dir / f"{world_id}.world.json"
        if not world_path.exists():
            return None
        
        try:
            with open(world_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading world {world_id}: {e}")
            return None
    
    def _load_scenario(self, scenario_id: str) -> Optional[Dict]:
        """Load a .SCENARIO file."""
        scenario_path = self._scenarios_dir / f"{scenario_id}.scenario.json"
        if not scenario_path.exists():
            return None
        
        try:
            with open(scenario_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading scenario {scenario_id}: {e}")
            return None
    
    def _merge(
        self, 
        world_data: Optional[Dict], 
        scenario_data: Dict
    ) -> Dict:
        """
        Merge world base with scenario delta.
        
        Args:
            world_data: Base world data (can be None)
            scenario_data: Scenario delta
        
        Returns:
            Merged data
        """
        # Start with world data or empty dict
        merged = copy.deepcopy(world_data) if world_data else {}
        
        # Apply JSON Patch operations if specified
        patches = scenario_data.get("patches", [])
        if patches:
            merged = JSONPatch.apply(merged, patches)
        
        # Apply scenario overrides
        merged["scenario_id"] = scenario_data.get("scenario_id")
        merged["scenario_name"] = scenario_data.get("name")
        
        # Environment from scenario
        merged["environment"] = {
            "cycle": scenario_data.get("initial_cycle", 0),
            "time": scenario_data.get("initial_time", "08:00"),
            "weather": scenario_data.get("initial_weather", "Clear"),
            "global_events": scenario_data.get("initial_events", [])
        }
        
        # Merge actors
        merged["actors"] = {}
        for actor in scenario_data.get("actors", []):
            actor_id = actor["actor_id"]
            merged["actors"][actor_id] = actor
        
        # Merge assets
        merged["assets"] = {}
        for asset in scenario_data.get("assets", []):
            asset_id = asset["asset_id"]
            merged["assets"][asset_id] = asset
        
        # Apply variables
        variables = scenario_data.get("variables", {})
        merged["variables"] = variables
        
        return merged
    
    def _build_world_state(
        self, 
        merged: Dict, 
        simulation_id: str
    ) -> WorldState:
        """
        Build a WorldState from merged data.
        
        Args:
            merged: Merged world + scenario data
            simulation_id: Simulation identifier
        
        Returns:
            WorldState instance
        """
        # Build Environment
        env_data = merged.get("environment", {})
        environment = Environment(
            cycle=env_data.get("cycle", 0),
            time=env_data.get("time", "08:00"),
            weather=env_data.get("weather", "Clear"),
            global_events=env_data.get("global_events", [])
        )
        
        # Build Actors
        actors = {}
        for actor_id, actor_data in merged.get("actors", {}).items():
            actors[actor_id] = Actor(
                actor_id=actor_data.get("actor_id", actor_id),
                role=actor_data.get("role", "Unknown"),
                description=actor_data.get("description", ""),
                assets=actor_data.get("assets", []),
                objectives=actor_data.get("objectives", [])
            )
        
        # Build Assets
        assets = {}
        for asset_id, asset_data in merged.get("assets", {}).items():
            assets[asset_id] = Asset(
                asset_id=asset_data.get("asset_id", asset_id),
                name=asset_data.get("name", "Unknown"),
                asset_type=asset_data.get("asset_type", "Unknown"),
                location=asset_data.get("location", {"lat": 0.0, "lon": 0.0}),
                status=asset_data.get("status", "active"),
                attributes=asset_data.get("attributes", {})
            )
        
        return WorldState(
            simulation_id=simulation_id,
            environment=environment,
            actors=actors,
            assets=assets
        )
    
    def compile_from_dicts(
        self,
        world_data: Optional[Dict],
        scenario_data: Dict,
        simulation_id: str
    ) -> PipelineResult:
        """
        Compile from in-memory dictionaries.
        
        Args:
            world_data: Base world data
            scenario_data: Scenario delta
            simulation_id: Simulation identifier
        
        Returns:
            PipelineResult
        """
        try:
            merged = self._merge(world_data, scenario_data)
            world_state = self._build_world_state(merged, simulation_id)
            
            return PipelineResult(
                success=True,
                world_state=world_state
            )
        except Exception as e:
            return PipelineResult(
                success=False,
                errors=[str(e)]
            )

