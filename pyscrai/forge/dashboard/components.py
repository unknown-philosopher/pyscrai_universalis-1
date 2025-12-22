"""
Shared Components - Common UI components for PyScrAI Universalis dashboard.

This module provides shared components used across both macro and micro views.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from pyscrai.data.schemas.models import WorldState
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MapMarker:
    """A marker on the map."""
    id: str
    name: str
    lat: float
    lon: float
    marker_type: str = "default"
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimelineEvent:
    """An event on the timeline."""
    cycle: int
    content: str
    event_type: str = "event"
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 0.5


class MapComponent:
    """
    Map overlay component for displaying asset locations.
    """
    
    def __init__(
        self,
        default_center: tuple = (34.05, -118.25),
        default_zoom: int = 10
    ):
        """
        Initialize the map component.
        
        Args:
            default_center: Default center coordinates (lat, lon)
            default_zoom: Default zoom level
        """
        self._center = default_center
        self._zoom = default_zoom
        self._markers: List[MapMarker] = []
        self._layers: Dict[str, bool] = {
            "assets": True,
            "events": False,
            "weather": False,
            "traffic": False
        }
    
    def update_from_world_state(self, world_state: WorldState) -> None:
        """
        Update map markers from world state.
        
        Args:
            world_state: Current world state
        """
        self._markers.clear()
        
        for asset in world_state.assets.values():
            self._markers.append(MapMarker(
                id=asset.asset_id,
                name=asset.name,
                lat=asset.location.get("lat", 0),
                lon=asset.location.get("lon", 0),
                marker_type=asset.asset_type,
                status=asset.status,
                metadata=asset.attributes
            ))
    
    def set_center(self, lat: float, lon: float) -> None:
        """Set map center."""
        self._center = (lat, lon)
    
    def set_zoom(self, zoom: int) -> None:
        """Set zoom level."""
        self._zoom = max(1, min(20, zoom))
    
    def toggle_layer(self, layer_name: str) -> bool:
        """Toggle a layer on/off."""
        if layer_name in self._layers:
            self._layers[layer_name] = not self._layers[layer_name]
        return self._layers.get(layer_name, False)
    
    def get_render_data(self) -> Dict[str, Any]:
        """Get data for rendering the map."""
        return {
            "center": {"lat": self._center[0], "lon": self._center[1]},
            "zoom": self._zoom,
            "markers": [
                {
                    "id": m.id,
                    "name": m.name,
                    "lat": m.lat,
                    "lon": m.lon,
                    "type": m.marker_type,
                    "status": m.status
                }
                for m in self._markers
            ],
            "layers": self._layers
        }
    
    def focus_on_marker(self, marker_id: str) -> bool:
        """Focus the map on a specific marker."""
        for marker in self._markers:
            if marker.id == marker_id:
                self._center = (marker.lat, marker.lon)
                self._zoom = 15
                return True
        return False


class TimelineComponent:
    """
    Timeline scrubber component for navigating simulation history.
    """
    
    def __init__(self, max_events: int = 100):
        """
        Initialize the timeline component.
        
        Args:
            max_events: Maximum events to display
        """
        self._events: List[TimelineEvent] = []
        self._max_events = max_events
        self._current_cycle = 0
        self._selected_cycle: Optional[int] = None
    
    def add_event(
        self,
        cycle: int,
        content: str,
        event_type: str = "event",
        importance: float = 0.5
    ) -> None:
        """Add an event to the timeline."""
        event = TimelineEvent(
            cycle=cycle,
            content=content,
            event_type=event_type,
            importance=importance
        )
        self._events.append(event)
        
        # Trim if exceeding max
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
    
    def set_current_cycle(self, cycle: int) -> None:
        """Set the current cycle."""
        self._current_cycle = cycle
    
    def select_cycle(self, cycle: int) -> List[TimelineEvent]:
        """
        Select a cycle and return its events.
        
        Args:
            cycle: Cycle to select
        
        Returns:
            List of events in that cycle
        """
        self._selected_cycle = cycle
        return [e for e in self._events if e.cycle == cycle]
    
    def get_render_data(self) -> Dict[str, Any]:
        """Get data for rendering the timeline."""
        # Group events by cycle
        events_by_cycle = {}
        for event in self._events:
            if event.cycle not in events_by_cycle:
                events_by_cycle[event.cycle] = []
            events_by_cycle[event.cycle].append({
                "content": event.content,
                "type": event.event_type,
                "importance": event.importance,
                "timestamp": event.timestamp.isoformat()
            })
        
        return {
            "current_cycle": self._current_cycle,
            "selected_cycle": self._selected_cycle,
            "events_by_cycle": events_by_cycle,
            "cycle_range": {
                "min": min(events_by_cycle.keys()) if events_by_cycle else 0,
                "max": max(events_by_cycle.keys()) if events_by_cycle else 0
            }
        }


class EventLogComponent:
    """
    Event log component for displaying recent events.
    """
    
    def __init__(self, max_display: int = 20):
        """
        Initialize the event log component.
        
        Args:
            max_display: Maximum events to display
        """
        self._events: List[Dict[str, Any]] = []
        self._max_display = max_display
        self._filters: Dict[str, bool] = {
            "adjudication": True,
            "actor_action": True,
            "environment": True,
            "system": True
        }
    
    def add_event(
        self,
        content: str,
        event_type: str,
        cycle: int,
        source: Optional[str] = None
    ) -> None:
        """Add an event to the log."""
        self._events.append({
            "content": content,
            "type": event_type,
            "cycle": cycle,
            "source": source,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim if exceeding max
        if len(self._events) > self._max_display * 2:
            self._events = self._events[-self._max_display:]
    
    def toggle_filter(self, event_type: str) -> bool:
        """Toggle a filter on/off."""
        if event_type in self._filters:
            self._filters[event_type] = not self._filters[event_type]
        return self._filters.get(event_type, True)
    
    def get_filtered_events(self) -> List[Dict[str, Any]]:
        """Get events with current filters applied."""
        filtered = [
            e for e in self._events
            if self._filters.get(e["type"], True)
        ]
        return filtered[-self._max_display:]
    
    def get_render_data(self) -> Dict[str, Any]:
        """Get data for rendering the event log."""
        return {
            "events": self.get_filtered_events(),
            "filters": self._filters,
            "total_count": len(self._events)
        }


class StatusBarComponent:
    """
    Status bar component showing simulation status.
    """
    
    def __init__(self):
        """Initialize the status bar component."""
        self._status = "idle"
        self._message = ""
        self._cycle = 0
        self._time = "00:00"
        self._weather = "Clear"
    
    def update(
        self,
        status: Optional[str] = None,
        message: Optional[str] = None,
        cycle: Optional[int] = None,
        time: Optional[str] = None,
        weather: Optional[str] = None
    ) -> None:
        """Update status bar values."""
        if status is not None:
            self._status = status
        if message is not None:
            self._message = message
        if cycle is not None:
            self._cycle = cycle
        if time is not None:
            self._time = time
        if weather is not None:
            self._weather = weather
    
    def update_from_world_state(self, world_state: WorldState) -> None:
        """Update from world state."""
        self._cycle = world_state.environment.cycle
        self._time = world_state.environment.time
        self._weather = world_state.environment.weather
    
    def get_render_data(self) -> Dict[str, Any]:
        """Get data for rendering the status bar."""
        return {
            "status": self._status,
            "message": self._message,
            "cycle": self._cycle,
            "time": self._time,
            "weather": self._weather
        }


# Factory functions

def create_map_component() -> MapComponent:
    """Create a map component."""
    return MapComponent()


def create_timeline_component() -> TimelineComponent:
    """Create a timeline component."""
    return TimelineComponent()


def create_event_log_component() -> EventLogComponent:
    """Create an event log component."""
    return EventLogComponent()


def create_status_bar_component() -> StatusBarComponent:
    """Create a status bar component."""
    return StatusBarComponent()

