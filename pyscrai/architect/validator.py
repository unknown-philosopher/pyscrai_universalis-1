"""
Validator - Multi-level validation for PyScrAI Universalis.

This module provides schema, type, and constraint validation
for .WORLD and .SCENARIO files.
"""

import json
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)

# Try to import jsonschema, fallback to basic validation if not available
try:
    import jsonschema
    from jsonschema import validate, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    logger.warning("jsonschema not installed. Install with: pip install jsonschema")


class ValidationLevel(str, Enum):
    """Levels of validation."""
    SCHEMA = "schema"
    TYPE = "type"
    CONSTRAINT = "constraint"
    CONTEXTUAL = "contextual"


@dataclass
class ValidationResult:
    """Result of validation."""
    valid: bool
    level: ValidationLevel
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "level": self.level.value,
            "errors": self.errors,
            "warnings": self.warnings
        }


@dataclass
class FullValidationResult:
    """Result of full multi-level validation."""
    valid: bool
    results: Dict[ValidationLevel, ValidationResult] = field(default_factory=dict)
    
    @property
    def all_errors(self) -> List[str]:
        errors = []
        for result in self.results.values():
            errors.extend(result.errors)
        return errors
    
    @property
    def all_warnings(self) -> List[str]:
        warnings = []
        for result in self.results.values():
            warnings.extend(result.warnings)
        return warnings


class SchemaValidator:
    """JSON Schema validation."""
    
    def __init__(self, schemas_dir: Optional[str] = None):
        """
        Initialize the schema validator.
        
        Args:
            schemas_dir: Directory containing schema files
        """
        if schemas_dir is None:
            # Default to data/schemas directory
            schemas_dir = os.path.join(
                os.path.dirname(__file__), 
                "..", "data", "schemas"
            )
        
        self._schemas_dir = Path(schemas_dir)
        self._loaded_schemas: Dict[str, Dict] = {}
    
    def _load_schema(self, schema_name: str) -> Optional[Dict]:
        """Load a schema from file."""
        if schema_name in self._loaded_schemas:
            return self._loaded_schemas[schema_name]
        
        schema_path = self._schemas_dir / f"{schema_name}_schema.json"
        if not schema_path.exists():
            logger.error(f"Schema file not found: {schema_path}")
            return None
        
        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            self._loaded_schemas[schema_name] = schema
            return schema
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schema {schema_name}: {e}")
            return None
    
    def validate_world(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate data against the world schema.
        
        Args:
            data: Data to validate
        
        Returns:
            ValidationResult
        """
        return self._validate_against_schema(data, "world")
    
    def validate_scenario(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate data against the scenario schema.
        
        Args:
            data: Data to validate
        
        Returns:
            ValidationResult
        """
        return self._validate_against_schema(data, "scenario")
    
    def _validate_against_schema(
        self, 
        data: Dict[str, Any], 
        schema_name: str
    ) -> ValidationResult:
        """Validate data against a named schema."""
        errors = []
        warnings = []
        
        schema = self._load_schema(schema_name)
        if schema is None:
            errors.append(f"Could not load schema: {schema_name}")
            return ValidationResult(
                valid=False,
                level=ValidationLevel.SCHEMA,
                errors=errors
            )
        
        if HAS_JSONSCHEMA:
            try:
                validate(instance=data, schema=schema)
            except ValidationError as e:
                errors.append(f"Schema validation failed: {e.message}")
                if e.path:
                    errors.append(f"  at path: {'/'.join(str(p) for p in e.path)}")
        else:
            # Basic validation without jsonschema
            required = schema.get("required", [])
            for field in required:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            level=ValidationLevel.SCHEMA,
            errors=errors,
            warnings=warnings
        )


class TypeValidator:
    """Pydantic model type validation."""
    
    def validate_world_state(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate data can be converted to WorldState.
        
        Args:
            data: Data to validate
        
        Returns:
            ValidationResult
        """
        from pyscrai.data.schemas.models import WorldState, Environment, Actor, Asset
        
        errors = []
        warnings = []
        
        try:
            # Try to construct the models
            if "environment" in data:
                Environment(**data["environment"])
            
            if "actors" in data:
                for actor_id, actor_data in data["actors"].items():
                    if isinstance(actor_data, dict):
                        Actor(**actor_data)
            
            if "assets" in data:
                for asset_id, asset_data in data["assets"].items():
                    if isinstance(asset_data, dict):
                        Asset(**asset_data)
            
            # Try full WorldState
            if all(k in data for k in ["simulation_id", "environment", "actors", "assets"]):
                WorldState(**data)
                
        except Exception as e:
            errors.append(f"Type validation failed: {str(e)}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            level=ValidationLevel.TYPE,
            errors=errors,
            warnings=warnings
        )


class ConstraintValidator:
    """Constraint and logical consistency validation."""
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate constraints and logical consistency.
        
        Args:
            data: Data to validate
        
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        # Check actor-asset relationships
        if "actors" in data and "assets" in data:
            for actor_id, actor in data["actors"].items():
                if isinstance(actor, dict) and "assets" in actor:
                    for asset_id in actor.get("assets", []):
                        if asset_id not in data["assets"]:
                            errors.append(
                                f"Actor {actor_id} references non-existent asset: {asset_id}"
                            )
        
        # Check for duplicate IDs
        if "actors" in data:
            actor_ids = []
            for actor_id, actor in data["actors"].items():
                if isinstance(actor, dict):
                    aid = actor.get("actor_id", actor_id)
                    if aid in actor_ids:
                        errors.append(f"Duplicate actor ID: {aid}")
                    actor_ids.append(aid)
        
        if "assets" in data:
            asset_ids = []
            for asset_id, asset in data["assets"].items():
                if isinstance(asset, dict):
                    aid = asset.get("asset_id", asset_id)
                    if aid in asset_ids:
                        errors.append(f"Duplicate asset ID: {aid}")
                    asset_ids.append(aid)
        
        # Check location validity
        if "assets" in data:
            for asset_id, asset in data["assets"].items():
                if isinstance(asset, dict) and "location" in asset:
                    loc = asset["location"]
                    if "lat" in loc and (loc["lat"] < -90 or loc["lat"] > 90):
                        errors.append(f"Invalid latitude for asset {asset_id}")
                    if "lon" in loc and (loc["lon"] < -180 or loc["lon"] > 180):
                        errors.append(f"Invalid longitude for asset {asset_id}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            level=ValidationLevel.CONSTRAINT,
            errors=errors,
            warnings=warnings
        )


class WorldValidator:
    """Main validator combining all validation levels."""
    
    def __init__(self, schemas_dir: Optional[str] = None):
        """Initialize the world validator."""
        self._schema_validator = SchemaValidator(schemas_dir)
        self._type_validator = TypeValidator()
        self._constraint_validator = ConstraintValidator()
    
    def validate_world(
        self, 
        data: Dict[str, Any],
        levels: Optional[List[ValidationLevel]] = None
    ) -> FullValidationResult:
        """
        Validate a .WORLD file with multiple validation levels.
        
        Args:
            data: World data to validate
            levels: Validation levels to run (default: all)
        
        Returns:
            FullValidationResult
        """
        if levels is None:
            levels = [ValidationLevel.SCHEMA, ValidationLevel.CONSTRAINT]
        
        results = {}
        all_valid = True
        
        if ValidationLevel.SCHEMA in levels:
            result = self._schema_validator.validate_world(data)
            results[ValidationLevel.SCHEMA] = result
            all_valid = all_valid and result.valid
        
        if ValidationLevel.CONSTRAINT in levels:
            result = self._constraint_validator.validate(data)
            results[ValidationLevel.CONSTRAINT] = result
            all_valid = all_valid and result.valid
        
        return FullValidationResult(valid=all_valid, results=results)
    
    def validate_scenario(
        self, 
        data: Dict[str, Any],
        levels: Optional[List[ValidationLevel]] = None
    ) -> FullValidationResult:
        """
        Validate a .SCENARIO file with multiple validation levels.
        
        Args:
            data: Scenario data to validate
            levels: Validation levels to run (default: all)
        
        Returns:
            FullValidationResult
        """
        if levels is None:
            levels = [ValidationLevel.SCHEMA, ValidationLevel.TYPE, ValidationLevel.CONSTRAINT]
        
        results = {}
        all_valid = True
        
        if ValidationLevel.SCHEMA in levels:
            result = self._schema_validator.validate_scenario(data)
            results[ValidationLevel.SCHEMA] = result
            all_valid = all_valid and result.valid
        
        if ValidationLevel.TYPE in levels:
            result = self._type_validator.validate_world_state(data)
            results[ValidationLevel.TYPE] = result
            all_valid = all_valid and result.valid
        
        if ValidationLevel.CONSTRAINT in levels:
            result = self._constraint_validator.validate(data)
            results[ValidationLevel.CONSTRAINT] = result
            all_valid = all_valid and result.valid
        
        return FullValidationResult(valid=all_valid, results=results)


# Convenience functions
def validate_world(data: Dict[str, Any]) -> FullValidationResult:
    """Validate a world definition."""
    validator = WorldValidator()
    return validator.validate_world(data)


def validate_scenario(data: Dict[str, Any]) -> FullValidationResult:
    """Validate a scenario definition."""
    validator = WorldValidator()
    return validator.validate_scenario(data)

