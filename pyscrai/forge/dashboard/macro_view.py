"""
Macro View - Strategic visualization components for PyScrAI Universalis.

This module provides visualization components for macro-level (strategic)
views including graphs, heatmaps, and reports.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from pyscrai.data.schemas.models import WorldState, Actor, Asset
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MacroMetrics:
    """
    Aggregated metrics for macro view display.
    """
    total_actors: int = 0
    total_assets: int = 0
    active_assets: int = 0
    cycle: int = 0
    
    # Resource metrics
    resource_utilization: float = 0.0
    asset_distribution: Dict[str, int] = field(default_factory=dict)
    actor_asset_counts: Dict[str, int] = field(default_factory=dict)
    
    # Event metrics
    events_this_cycle: int = 0
    total_events: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_actors": self.total_actors,
            "total_assets": self.total_assets,
            "active_assets": self.active_assets,
            "cycle": self.cycle,
            "resource_utilization": self.resource_utilization,
            "asset_distribution": self.asset_distribution,
            "actor_asset_counts": self.actor_asset_counts,
            "events_this_cycle": self.events_this_cycle,
            "total_events": self.total_events
        }


@dataclass
class PolicyImpact:
    """Represents the impact of a policy or decision."""
    policy_id: str
    description: str
    cycle: int
    affected_actors: List[str] = field(default_factory=list)
    affected_assets: List[str] = field(default_factory=list)
    impact_score: float = 0.0
    outcome: str = ""


class MacroViewRenderer:
    """
    Renderer for macro-level visualization components.
    """
    
    def __init__(self):
        """Initialize the macro view renderer."""
        self._metrics_history: List[MacroMetrics] = []
        self._policy_impacts: List[PolicyImpact] = []
    
    def compute_metrics(self, world_state: WorldState) -> MacroMetrics:
        """
        Compute macro metrics from current world state.
        
        Args:
            world_state: Current world state
        
        Returns:
            MacroMetrics for display
        """
        # Count actors and assets
        total_actors = len(world_state.actors)
        total_assets = len(world_state.assets)
        
        # Count active assets
        active_assets = sum(
            1 for asset in world_state.assets.values()
            if asset.status in ["active", "ready"]
        )
        
        # Asset distribution by type
        asset_distribution = {}
        for asset in world_state.assets.values():
            asset_type = asset.asset_type
            asset_distribution[asset_type] = asset_distribution.get(asset_type, 0) + 1
        
        # Actor asset counts
        actor_asset_counts = {}
        for actor_id, actor in world_state.actors.items():
            actor_asset_counts[actor_id] = len(actor.assets)
        
        # Calculate resource utilization (simple)
        utilization = active_assets / total_assets if total_assets > 0 else 0.0
        
        metrics = MacroMetrics(
            total_actors=total_actors,
            total_assets=total_assets,
            active_assets=active_assets,
            cycle=world_state.environment.cycle,
            resource_utilization=utilization,
            asset_distribution=asset_distribution,
            actor_asset_counts=actor_asset_counts,
            total_events=len(world_state.environment.global_events)
        )
        
        # Store in history
        self._metrics_history.append(metrics)
        
        return metrics
    
    def get_asset_status_summary(
        self, 
        world_state: WorldState
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get a summary of asset statuses grouped by type.
        
        Args:
            world_state: Current world state
        
        Returns:
            Dict mapping asset types to asset info lists
        """
        summary = {}
        
        for asset in world_state.assets.values():
            asset_type = asset.asset_type
            if asset_type not in summary:
                summary[asset_type] = []
            
            summary[asset_type].append({
                "id": asset.asset_id,
                "name": asset.name,
                "status": asset.status,
                "location": asset.location,
                "attributes": asset.attributes
            })
        
        return summary
    
    def get_actor_overview(
        self, 
        world_state: WorldState
    ) -> List[Dict[str, Any]]:
        """
        Get an overview of all actors.
        
        Args:
            world_state: Current world state
        
        Returns:
            List of actor info dicts
        """
        overview = []
        
        for actor in world_state.actors.values():
            overview.append({
                "id": actor.actor_id,
                "role": actor.role,
                "description": actor.description,
                "asset_count": len(actor.assets),
                "objective_count": len(actor.objectives),
                "resolution": actor.resolution.value if hasattr(actor, 'resolution') else "macro"
            })
        
        return overview
    
    def generate_strategic_report(
        self,
        world_state: WorldState
    ) -> Dict[str, Any]:
        """
        Generate a strategic report for the current state.
        
        Args:
            world_state: Current world state
        
        Returns:
            Strategic report dict
        """
        metrics = self.compute_metrics(world_state)
        
        return {
            "report_type": "strategic",
            "generated_at": datetime.now().isoformat(),
            "cycle": world_state.environment.cycle,
            "environment": {
                "time": world_state.environment.time,
                "weather": world_state.environment.weather
            },
            "metrics": metrics.to_dict(),
            "asset_summary": self.get_asset_status_summary(world_state),
            "actor_overview": self.get_actor_overview(world_state),
            "recent_events": world_state.environment.global_events[-5:]
        }
    
    def get_metrics_trend(
        self, 
        metric_name: str, 
        last_n: int = 10
    ) -> List[Any]:
        """
        Get trend data for a specific metric.
        
        Args:
            metric_name: Name of the metric
            last_n: Number of recent data points
        
        Returns:
            List of metric values
        """
        history = self._metrics_history[-last_n:]
        return [getattr(m, metric_name, None) for m in history]
    
    def record_policy_impact(
        self,
        policy_id: str,
        description: str,
        cycle: int,
        affected_actors: List[str],
        affected_assets: List[str],
        impact_score: float,
        outcome: str
    ) -> PolicyImpact:
        """
        Record a policy impact for tracking.
        
        Args:
            policy_id: Unique policy identifier
            description: Policy description
            cycle: Cycle when policy was applied
            affected_actors: List of affected actor IDs
            affected_assets: List of affected asset IDs
            impact_score: Impact score (-1 to 1)
            outcome: Outcome description
        
        Returns:
            PolicyImpact record
        """
        impact = PolicyImpact(
            policy_id=policy_id,
            description=description,
            cycle=cycle,
            affected_actors=affected_actors,
            affected_assets=affected_assets,
            impact_score=impact_score,
            outcome=outcome
        )
        self._policy_impacts.append(impact)
        return impact
    
    def get_policy_impacts(
        self, 
        last_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get recorded policy impacts."""
        impacts = self._policy_impacts[-last_n:] if last_n else self._policy_impacts
        return [
            {
                "policy_id": p.policy_id,
                "description": p.description,
                "cycle": p.cycle,
                "affected_actors": p.affected_actors,
                "affected_assets": p.affected_assets,
                "impact_score": p.impact_score,
                "outcome": p.outcome
            }
            for p in impacts
        ]


def create_macro_view() -> MacroViewRenderer:
    """Create a macro view renderer instance."""
    return MacroViewRenderer()

