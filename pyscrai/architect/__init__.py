"""
Architect module - Design Time tools for PyScrAI Universalis.

This module contains tools for creating Worlds and Scenarios:
- builder: Compile raw data into .WORLD format
- seeder: Initialize DuckDB database with scenario data
- schema_init: Initialize database schema
- validator: Multi-level validation (schema, type, historical/contextual)
- pipeline: Seed-to-state compilation
- context_validator: Historical/contextual validation rules
"""

from pyscrai.architect.seeder import (
    seed_simulation,
    seed_custom_scenario,
    seed_from_file,
    get_seeded_simulations
)
from pyscrai.architect.schema_init import (
    init_database,
    load_spatial_extension,
    apply_schema,
    create_spatial_indexes,
    verify_schema
)
from pyscrai.architect.validator import (
    WorldValidator,
    SchemaValidator,
    TypeValidator,
    ConstraintValidator,
    ValidationLevel,
    ValidationResult,
    FullValidationResult,
    validate_world,
    validate_scenario
)
from pyscrai.architect.builder import (
    WorldBuilder,
    ScenarioBuilder,
    WorldDefinition
)
from pyscrai.architect.pipeline import (
    SeedToStatePipeline,
    PipelineResult,
    JSONPatch
)
from pyscrai.architect.context_validator import (
    ContextValidator,
    EraPeriod,
    EraConstraints,
    validate_context
)

__all__ = [
    # Seeder
    "seed_simulation",
    "seed_custom_scenario",
    "seed_from_file",
    "get_seeded_simulations",
    # Schema Init
    "init_database",
    "load_spatial_extension",
    "apply_schema",
    "create_spatial_indexes",
    "verify_schema",
    # Validator
    "WorldValidator",
    "SchemaValidator",
    "TypeValidator",
    "ConstraintValidator",
    "ValidationLevel",
    "ValidationResult",
    "FullValidationResult",
    "validate_world",
    "validate_scenario",
    # Builder
    "WorldBuilder",
    "ScenarioBuilder",
    "WorldDefinition",
    # Pipeline
    "SeedToStatePipeline",
    "PipelineResult",
    "JSONPatch",
    # Context validator
    "ContextValidator",
    "EraPeriod",
    "EraConstraints",
    "validate_context",
]
