"""
Viewport - Unified dashboard viewport for PyScrAI Universalis.

This module provides a unified viewport with resolution toggle
for switching between macro (strategic) and micro (individual) views.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from pyscrai.data.schemas.models import WorldState, Actor
from pyscrai.forge.dashboard.macro_view import MacroViewRenderer, create_macro_view
from pyscrai.forge.dashboard.micro_view import MicroViewRenderer, create_micro_view
from pyscrai.universalis.memory.stream import MemoryStream
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


class ViewResolution(str, Enum):
    """View resolution modes."""
    MACRO = "macro"
    MICRO = "micro"


@dataclass
class ViewportState:
    """
    Current state of the viewport.
    """
    resolution: ViewResolution = ViewResolution.MACRO
    selected_actor_id: Optional[str] = None
    show_map: bool = True
    show_timeline: bool = True
    show_events: bool = True
    cycle: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolution": self.resolution.value,
            "selected_actor_id": self.selected_actor_id,
            "show_map": self.show_map,
            "show_timeline": self.show_timeline,
            "show_events": self.show_events,
            "cycle": self.cycle,
            "timestamp": self.timestamp.isoformat()
        }


class UnifiedViewport:
    """
    Unified viewport that switches between macro and micro views.
    
    Provides a consistent interface for visualization regardless
    of the current resolution mode.
    """
    
    def __init__(
        self,
        memory_stream: Optional[MemoryStream] = None
    ):
        """
        Initialize the unified viewport.
        
        Args:
            memory_stream: Optional memory stream for event access
        """
        self._state = ViewportState()
        self._macro_view = create_macro_view()
        self._micro_view = create_micro_view(memory_stream)
        self._memory_stream = memory_stream
        
        # Event handlers
        self._resolution_change_handlers: List[Callable] = []
        self._actor_select_handlers: List[Callable] = []
    
    @property
    def resolution(self) -> ViewResolution:
        """Get current resolution mode."""
        return self._state.resolution
    
    @property
    def selected_actor(self) -> Optional[str]:
        """Get currently selected actor ID."""
        return self._state.selected_actor_id
    
    def toggle_resolution(self) -> ViewResolution:
        """
        Toggle between macro and micro resolution.
        
        Returns:
            New resolution mode
        """
        if self._state.resolution == ViewResolution.MACRO:
            self._state.resolution = ViewResolution.MICRO
        else:
            self._state.resolution = ViewResolution.MACRO
        
        # Notify handlers
        for handler in self._resolution_change_handlers:
            handler(self._state.resolution)
        
        logger.info(f"Viewport resolution changed to: {self._state.resolution.value}")
        return self._state.resolution
    
    def set_resolution(self, resolution: ViewResolution) -> None:
        """
        Set the resolution mode.
        
        Args:
            resolution: Resolution mode to set
        """
        if self._state.resolution != resolution:
            self._state.resolution = resolution
            for handler in self._resolution_change_handlers:
                handler(resolution)
    
    def select_actor(self, actor_id: str) -> None:
        """
        Select an actor for micro view.
        
        Args:
            actor_id: ID of the actor to select
        """
        self._state.selected_actor_id = actor_id
        
        # Auto-switch to micro view when actor is selected
        if self._state.resolution == ViewResolution.MACRO:
            self.set_resolution(ViewResolution.MICRO)
        
        # Notify handlers
        for handler in self._actor_select_handlers:
            handler(actor_id)
        
        logger.info(f"Selected actor: {actor_id}")
    
    def deselect_actor(self) -> None:
        """Deselect the current actor."""
        self._state.selected_actor_id = None
    
    def render(self, world_state: WorldState) -> Dict[str, Any]:
        """
        Render the current view based on resolution mode.
        
        Args:
            world_state: Current world state
        
        Returns:
            Rendered view data
        """
        self._state.cycle = world_state.environment.cycle
        self._state.timestamp = datetime.now()
        
        if self._state.resolution == ViewResolution.MACRO:
            return self._render_macro_view(world_state)
        else:
            return self._render_micro_view(world_state)
    
    def _render_macro_view(self, world_state: WorldState) -> Dict[str, Any]:
        """Render the macro (strategic) view."""
        report = self._macro_view.generate_strategic_report(world_state)
        
        return {
            "view_type": "macro",
            "viewport_state": self._state.to_dict(),
            "content": {
                "report": report,
                "metrics_trend": {
                    "utilization": self._macro_view.get_metrics_trend("resource_utilization"),
                    "active_assets": self._macro_view.get_metrics_trend("active_assets")
                },
                "policy_impacts": self._macro_view.get_policy_impacts(last_n=5)
            },
            "shared": self._get_shared_components(world_state)
        }
    
    def _render_micro_view(self, world_state: WorldState) -> Dict[str, Any]:
        """Render the micro (individual) view."""
        actor_report = None
        
        if self._state.selected_actor_id:
            if self._state.selected_actor_id in world_state.actors:
                actor = world_state.actors[self._state.selected_actor_id]
                actor_report = self._micro_view.generate_agent_report(actor, world_state)
        
        # Get list of all actors for selection
        actor_list = [
            {
                "id": a.actor_id,
                "role": a.role,
                "resolution": a.resolution.value if hasattr(a, 'resolution') else "macro"
            }
            for a in world_state.actors.values()
        ]
        
        return {
            "view_type": "micro",
            "viewport_state": self._state.to_dict(),
            "content": {
                "selected_actor_report": actor_report,
                "available_actors": actor_list
            },
            "shared": self._get_shared_components(world_state)
        }
    
    def _get_shared_components(self, world_state: WorldState) -> Dict[str, Any]:
        """Get data for shared UI components."""
        return {
            "environment": {
                "cycle": world_state.environment.cycle,
                "time": world_state.environment.time,
                "weather": world_state.environment.weather
            },
            "recent_events": world_state.environment.global_events[-5:],
            "map_data": self._get_map_data(world_state) if self._state.show_map else None,
            "timeline_data": self._get_timeline_data() if self._state.show_timeline else None
        }
    
    def _get_map_data(self, world_state: WorldState) -> Dict[str, Any]:
        """Get data for map overlay."""
        # Asset locations
        asset_markers = []
        for asset in world_state.assets.values():
            asset_markers.append({
                "id": asset.asset_id,
                "name": asset.name,
                "type": asset.asset_type,
                "lat": asset.location.get("lat", 0),
                "lon": asset.location.get("lon", 0),
                "status": asset.status
            })
        
        return {
            "markers": asset_markers,
            "center": {"lat": 34.05, "lon": -118.25},  # Default center
            "zoom": 10
        }
    
    def _get_timeline_data(self) -> Dict[str, Any]:
        """Get data for timeline scrubber."""
        return {
            "current_cycle": self._state.cycle,
            "events_by_cycle": {}  # Would be populated from memory stream
        }
    
    def on_resolution_change(self, handler: Callable) -> None:
        """Register a handler for resolution changes."""
        self._resolution_change_handlers.append(handler)
    
    def on_actor_select(self, handler: Callable) -> None:
        """Register a handler for actor selection."""
        self._actor_select_handlers.append(handler)
    
    def set_panel_visibility(
        self,
        show_map: Optional[bool] = None,
        show_timeline: Optional[bool] = None,
        show_events: Optional[bool] = None
    ) -> None:
        """Set visibility of optional panels."""
        if show_map is not None:
            self._state.show_map = show_map
        if show_timeline is not None:
            self._state.show_timeline = show_timeline
        if show_events is not None:
            self._state.show_events = show_events
    
    def get_state(self) -> Dict[str, Any]:
        """Get current viewport state."""
        return self._state.to_dict()
    
    # Proxy methods for direct view access
    
    def get_macro_view(self) -> MacroViewRenderer:
        """Get the macro view renderer."""
        return self._macro_view
    
    def get_micro_view(self) -> MicroViewRenderer:
        """Get the micro view renderer."""
        return self._micro_view


def create_viewport(
    memory_stream: Optional[MemoryStream] = None
) -> UnifiedViewport:
    """
    Create a unified viewport instance.
    
    Args:
        memory_stream: Optional memory stream for event access
    
    Returns:
        Configured UnifiedViewport
    """
    return UnifiedViewport(memory_stream=memory_stream)

