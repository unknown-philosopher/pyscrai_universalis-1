"""
Context Validator - Historical/contextual validation for PyScrAI Universalis.

This module ensures temporal consistency, preventing anachronisms
like 18th-century technology in a 2023 scenario.
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from pyscrai.architect.validator import ValidationResult, ValidationLevel
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


class EraPeriod(str, Enum):
    """Historical era periods."""
    PREHISTORIC = "prehistoric"
    ANCIENT = "ancient"
    MEDIEVAL = "medieval"
    INDUSTRIAL = "industrial"
    MODERN = "modern"
    FUTURE = "future"


@dataclass
class EraConstraints:
    """Constraints for a specific era."""
    period: EraPeriod
    year_range: tuple  # (min_year, max_year)
    allowed_tech_levels: range
    forbidden_terms: Set[str] = field(default_factory=set)
    required_terms: Set[str] = field(default_factory=set)
    
    def contains_year(self, year: int) -> bool:
        """Check if a year falls within this era."""
        return self.year_range[0] <= year <= self.year_range[1]


# Define era constraints
ERA_CONSTRAINTS = {
    EraPeriod.PREHISTORIC: EraConstraints(
        period=EraPeriod.PREHISTORIC,
        year_range=(-10000, -3000),
        allowed_tech_levels=range(1, 2),
        forbidden_terms={"computer", "electricity", "engine", "vehicle", "phone"},
        required_terms=set()
    ),
    EraPeriod.ANCIENT: EraConstraints(
        period=EraPeriod.ANCIENT,
        year_range=(-3000, 500),
        allowed_tech_levels=range(1, 4),
        forbidden_terms={"computer", "electricity", "engine", "phone", "internet"},
        required_terms=set()
    ),
    EraPeriod.MEDIEVAL: EraConstraints(
        period=EraPeriod.MEDIEVAL,
        year_range=(500, 1500),
        allowed_tech_levels=range(2, 5),
        forbidden_terms={"computer", "electricity", "engine", "phone", "internet"},
        required_terms=set()
    ),
    EraPeriod.INDUSTRIAL: EraConstraints(
        period=EraPeriod.INDUSTRIAL,
        year_range=(1500, 1950),
        allowed_tech_levels=range(4, 8),
        forbidden_terms={"computer", "internet", "smartphone", "drone"},
        required_terms=set()
    ),
    EraPeriod.MODERN: EraConstraints(
        period=EraPeriod.MODERN,
        year_range=(1950, 2050),
        allowed_tech_levels=range(6, 10),
        forbidden_terms={"teleporter", "warp_drive", "time_machine"},
        required_terms=set()
    ),
    EraPeriod.FUTURE: EraConstraints(
        period=EraPeriod.FUTURE,
        year_range=(2050, 10000),
        allowed_tech_levels=range(8, 11),
        forbidden_terms=set(),
        required_terms=set()
    ),
}


class ContextValidator:
    """
    Validates historical and contextual consistency.
    """
    
    def __init__(self, custom_constraints: Optional[Dict[EraPeriod, EraConstraints]] = None):
        """
        Initialize the context validator.
        
        Args:
            custom_constraints: Optional custom era constraints
        """
        self._constraints = custom_constraints or ERA_CONSTRAINTS
    
    def determine_era(self, year: int) -> Optional[EraPeriod]:
        """
        Determine the era period for a given year.
        
        Args:
            year: The year to check
        
        Returns:
            EraPeriod or None
        """
        for period, constraints in self._constraints.items():
            if constraints.contains_year(year):
                return period
        return None
    
    def validate_scenario_context(
        self,
        scenario_data: Dict[str, Any],
        world_data: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate a scenario for historical/contextual consistency.
        
        Args:
            scenario_data: Scenario definition
            world_data: Optional base world definition
        
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        # Determine target era from world or scenario
        era_info = None
        if world_data and "era" in world_data:
            era_info = world_data["era"]
        elif "era" in scenario_data:
            era_info = scenario_data["era"]
        
        if era_info is None:
            warnings.append("No era information found, skipping contextual validation")
            return ValidationResult(
                valid=True,
                level=ValidationLevel.CONTEXTUAL,
                warnings=warnings
            )
        
        year = era_info.get("year", 2023)
        period = era_info.get("period", "modern")
        tech_level = era_info.get("technology_level", 7)
        
        # Get era constraints
        try:
            era_period = EraPeriod(period)
            constraints = self._constraints.get(era_period)
        except ValueError:
            warnings.append(f"Unknown era period: {period}")
            constraints = None
        
        if constraints:
            # Check technology level
            if tech_level not in constraints.allowed_tech_levels:
                errors.append(
                    f"Technology level {tech_level} is not appropriate for {period} era "
                    f"(allowed: {constraints.allowed_tech_levels.start}-{constraints.allowed_tech_levels.stop-1})"
                )
            
            # Check for forbidden terms in scenario
            self._check_forbidden_terms(scenario_data, constraints, errors)
            
            # Check actor roles for anachronisms
            self._check_actor_anachronisms(scenario_data, era_period, errors, warnings)
            
            # Check asset types for anachronisms
            self._check_asset_anachronisms(scenario_data, era_period, errors, warnings)
        
        return ValidationResult(
            valid=len(errors) == 0,
            level=ValidationLevel.CONTEXTUAL,
            errors=errors,
            warnings=warnings
        )
    
    def _check_forbidden_terms(
        self,
        data: Dict[str, Any],
        constraints: EraConstraints,
        errors: List[str]
    ) -> None:
        """Check for forbidden terms in the data."""
        # Convert data to string for simple term checking
        data_str = str(data).lower()
        
        for term in constraints.forbidden_terms:
            if term.lower() in data_str:
                errors.append(
                    f"Term '{term}' is anachronistic for {constraints.period.value} era"
                )
    
    def _check_actor_anachronisms(
        self,
        scenario_data: Dict[str, Any],
        era_period: EraPeriod,
        errors: List[str],
        warnings: List[str]
    ) -> None:
        """Check actors for anachronistic roles."""
        anachronistic_roles = {
            EraPeriod.PREHISTORIC: {"programmer", "pilot", "engineer", "scientist"},
            EraPeriod.ANCIENT: {"pilot", "programmer", "astronaut"},
            EraPeriod.MEDIEVAL: {"pilot", "programmer", "astronaut", "electrician"},
            EraPeriod.INDUSTRIAL: {"programmer", "astronaut", "data_scientist"},
        }
        
        forbidden_roles = anachronistic_roles.get(era_period, set())
        
        for actor in scenario_data.get("actors", []):
            role = actor.get("role", "").lower()
            for forbidden in forbidden_roles:
                if forbidden in role:
                    errors.append(
                        f"Actor role '{actor.get('role')}' is anachronistic for {era_period.value} era"
                    )
    
    def _check_asset_anachronisms(
        self,
        scenario_data: Dict[str, Any],
        era_period: EraPeriod,
        errors: List[str],
        warnings: List[str]
    ) -> None:
        """Check assets for anachronistic types."""
        anachronistic_assets = {
            EraPeriod.PREHISTORIC: {"vehicle", "helicopter", "computer", "phone"},
            EraPeriod.ANCIENT: {"helicopter", "computer", "phone", "tank"},
            EraPeriod.MEDIEVAL: {"helicopter", "computer", "phone", "tank", "car"},
            EraPeriod.INDUSTRIAL: {"helicopter", "computer", "smartphone", "drone"},
        }
        
        forbidden_types = anachronistic_assets.get(era_period, set())
        
        for asset in scenario_data.get("assets", []):
            asset_type = asset.get("asset_type", "").lower()
            for forbidden in forbidden_types:
                if forbidden in asset_type:
                    errors.append(
                        f"Asset type '{asset.get('asset_type')}' is anachronistic for {era_period.value} era"
                    )
    
    def validate_world_context(
        self,
        world_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a world definition for internal consistency.
        
        Args:
            world_data: World definition
        
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        era_info = world_data.get("era", {})
        year = era_info.get("year", 2023)
        period = era_info.get("period", "modern")
        
        # Check year matches period
        determined_era = self.determine_era(year)
        if determined_era:
            try:
                declared_era = EraPeriod(period)
                if determined_era != declared_era:
                    warnings.append(
                        f"Year {year} typically belongs to {determined_era.value} era, "
                        f"but declared as {declared_era.value}"
                    )
            except ValueError:
                warnings.append(f"Unknown era period: {period}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            level=ValidationLevel.CONTEXTUAL,
            errors=errors,
            warnings=warnings
        )


# Convenience function
def validate_context(
    scenario_data: Dict[str, Any],
    world_data: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    """Validate contextual consistency."""
    validator = ContextValidator()
    return validator.validate_scenario_context(scenario_data, world_data)

