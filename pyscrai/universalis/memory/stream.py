"""
Memory Stream - Chronological event log for PyScrAI Universalis.

This module provides a chronological event stream for storing and
retrieving simulation events with full traceability.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import threading
import json

from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


class EventType(str, Enum):
    """Types of events in the memory stream."""
    OBSERVATION = "observation"
    INTENT = "intent"
    ADJUDICATION = "adjudication"
    RATIONALE = "rationale"
    STATE_CHANGE = "state_change"
    SYSTEM = "system"
    ACTOR_ACTION = "actor_action"
    ENVIRONMENT = "environment"


@dataclass
class StreamEvent:
    """
    A single event in the memory stream.
    
    Attributes:
        event_type: Type of the event
        content: Event content/description
        cycle: Simulation cycle when event occurred
        timestamp: Real-world timestamp
        actor_id: Optional actor involved in the event
        metadata: Additional event metadata
        linked_events: IDs of related events
    """
    event_type: EventType
    content: str
    cycle: int
    timestamp: datetime = field(default_factory=datetime.now)
    actor_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    linked_events: List[str] = field(default_factory=list)
    event_id: str = field(default="")
    
    def __post_init__(self):
        """Generate event ID if not provided."""
        if not self.event_id:
            import hashlib
            content = f"{self.event_type.value}:{self.content}:{self.cycle}:{self.timestamp.isoformat()}"
            self.event_id = hashlib.md5(content.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "content": self.content,
            "cycle": self.cycle,
            "timestamp": self.timestamp.isoformat(),
            "actor_id": self.actor_id,
            "metadata": self.metadata,
            "linked_events": self.linked_events
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamEvent":
        """Create from dictionary."""
        return cls(
            event_id=data.get("event_id", ""),
            event_type=EventType(data["event_type"]),
            content=data["content"],
            cycle=data["cycle"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            actor_id=data.get("actor_id"),
            metadata=data.get("metadata", {}),
            linked_events=data.get("linked_events", [])
        )


class MemoryStream:
    """
    Chronological event stream for simulation traceability.
    
    Stores events in order and provides retrieval methods for
    debugging, analysis, and UI display.
    """
    
    def __init__(
        self,
        simulation_id: str = "default",
        max_events: int = 10000
    ):
        """
        Initialize the memory stream.
        
        Args:
            simulation_id: Simulation identifier
            max_events: Maximum events to keep in memory
        """
        self._simulation_id = simulation_id
        self._max_events = max_events
        self._events: List[StreamEvent] = []
        self._lock = threading.Lock()
        self._event_index: Dict[str, StreamEvent] = {}
        
        logger.info(f"Memory stream initialized for simulation: {simulation_id}")
    
    def add_event(
        self,
        event_type: EventType,
        content: str,
        cycle: int,
        actor_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        linked_events: Optional[List[str]] = None
    ) -> StreamEvent:
        """
        Add an event to the stream.
        
        Args:
            event_type: Type of the event
            content: Event content/description
            cycle: Simulation cycle
            actor_id: Optional actor involved
            metadata: Additional metadata
            linked_events: IDs of related events
        
        Returns:
            The created StreamEvent
        """
        event = StreamEvent(
            event_type=event_type,
            content=content,
            cycle=cycle,
            actor_id=actor_id,
            metadata=metadata or {},
            linked_events=linked_events or []
        )
        
        with self._lock:
            self._events.append(event)
            self._event_index[event.event_id] = event
            
            # Trim if exceeding max
            if len(self._events) > self._max_events:
                removed = self._events.pop(0)
                del self._event_index[removed.event_id]
        
        return event
    
    def add_observation(
        self,
        content: str,
        cycle: int,
        actor_id: str,
        **kwargs
    ) -> StreamEvent:
        """Add an observation event."""
        return self.add_event(
            EventType.OBSERVATION, content, cycle, actor_id, **kwargs
        )
    
    def add_intent(
        self,
        content: str,
        cycle: int,
        actor_id: str,
        **kwargs
    ) -> StreamEvent:
        """Add an intent event."""
        return self.add_event(
            EventType.INTENT, content, cycle, actor_id, **kwargs
        )
    
    def add_adjudication(
        self,
        content: str,
        cycle: int,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> StreamEvent:
        """Add an adjudication event."""
        return self.add_event(
            EventType.ADJUDICATION, content, cycle, metadata=metadata, **kwargs
        )
    
    def add_rationale(
        self,
        content: str,
        cycle: int,
        linked_adjudication: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StreamEvent:
        """
        Add a rationale event for traceability.
        
        Args:
            content: The rationale explanation
            cycle: Simulation cycle
            linked_adjudication: ID of the related adjudication event
            metadata: Additional metadata
        
        Returns:
            The created rationale event
        """
        linked = [linked_adjudication] if linked_adjudication else []
        return self.add_event(
            EventType.RATIONALE, 
            content, 
            cycle, 
            metadata=metadata,
            linked_events=linked
        )
    
    def get_event(self, event_id: str) -> Optional[StreamEvent]:
        """Get a specific event by ID."""
        with self._lock:
            return self._event_index.get(event_id)
    
    def get_events_by_cycle(self, cycle: int) -> List[StreamEvent]:
        """Get all events from a specific cycle."""
        with self._lock:
            return [e for e in self._events if e.cycle == cycle]
    
    def get_events_by_type(
        self, 
        event_type: EventType,
        limit: Optional[int] = None
    ) -> List[StreamEvent]:
        """Get events of a specific type."""
        with self._lock:
            events = [e for e in self._events if e.event_type == event_type]
            if limit:
                events = events[-limit:]
            return events
    
    def get_events_by_actor(
        self, 
        actor_id: str,
        limit: Optional[int] = None
    ) -> List[StreamEvent]:
        """Get events for a specific actor."""
        with self._lock:
            events = [e for e in self._events if e.actor_id == actor_id]
            if limit:
                events = events[-limit:]
            return events
    
    def get_recent_events(self, limit: int = 10) -> List[StreamEvent]:
        """Get the most recent events."""
        with self._lock:
            return self._events[-limit:]
    
    def get_rationales_for_cycle(self, cycle: int) -> List[StreamEvent]:
        """Get all rationales for a specific cycle."""
        with self._lock:
            return [
                e for e in self._events 
                if e.event_type == EventType.RATIONALE and e.cycle == cycle
            ]
    
    def search(
        self,
        query: str,
        event_types: Optional[List[EventType]] = None,
        actor_id: Optional[str] = None,
        cycle_range: Optional[tuple] = None
    ) -> List[StreamEvent]:
        """
        Search events with filters.
        
        Args:
            query: Text to search for in content
            event_types: Filter by event types
            actor_id: Filter by actor
            cycle_range: Tuple of (min_cycle, max_cycle)
        
        Returns:
            List of matching events
        """
        query_lower = query.lower()
        
        with self._lock:
            results = []
            for event in self._events:
                # Check query match
                if query_lower not in event.content.lower():
                    continue
                
                # Check event type filter
                if event_types and event.event_type not in event_types:
                    continue
                
                # Check actor filter
                if actor_id and event.actor_id != actor_id:
                    continue
                
                # Check cycle range
                if cycle_range:
                    min_cycle, max_cycle = cycle_range
                    if event.cycle < min_cycle or event.cycle > max_cycle:
                        continue
                
                results.append(event)
            
            return results
    
    def get_state(self) -> Dict[str, Any]:
        """Get state for checkpointing."""
        with self._lock:
            return {
                "simulation_id": self._simulation_id,
                "events": [e.to_dict() for e in self._events]
            }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore state from checkpoint."""
        with self._lock:
            self._events = [
                StreamEvent.from_dict(e) 
                for e in state.get("events", [])
            ]
            self._event_index = {e.event_id: e for e in self._events}
    
    def export_to_json(self) -> str:
        """Export stream to JSON string."""
        with self._lock:
            return json.dumps(
                [e.to_dict() for e in self._events],
                indent=2
            )
    
    def clear(self) -> None:
        """Clear all events."""
        with self._lock:
            self._events.clear()
            self._event_index.clear()
    
    def __len__(self) -> int:
        """Return number of events."""
        with self._lock:
            return len(self._events)

