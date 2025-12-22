"""
Observation Processing - Structured observation handling for PyScrAI Universalis.

This module provides a pipeline for processing observations, filtering,
prioritizing, and automatically storing them in agent memory.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from datetime import datetime

from pyscrai.data.schemas.models import WorldState, Actor
from pyscrai.universalis.memory.associative import ChromaDBMemoryBank
from pyscrai.universalis.memory.scopes import MemoryScope
from pyscrai.universalis.memory.stream import MemoryStream, EventType
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


class ObservationType(str, Enum):
    """Types of observations."""
    ENVIRONMENT = "environment"
    ACTOR_ACTION = "actor_action"
    ASSET_STATUS = "asset_status"
    EVENT = "event"
    COMMUNICATION = "communication"
    SYSTEM = "system"


class ObservationPriority(str, Enum):
    """Priority levels for observations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class Observation:
    """
    A single observation.
    
    Attributes:
        content: The observation text
        obs_type: Type of observation
        priority: Priority level
        source_id: ID of the source (actor, asset, or system)
        target_ids: IDs of targets this observation is relevant to
        cycle: Simulation cycle
        timestamp: Real-world timestamp
        metadata: Additional metadata
    """
    content: str
    obs_type: ObservationType
    priority: ObservationPriority = ObservationPriority.MEDIUM
    source_id: Optional[str] = None
    target_ids: List[str] = field(default_factory=list)
    cycle: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "obs_type": self.obs_type.value,
            "priority": self.priority.value,
            "source_id": self.source_id,
            "target_ids": self.target_ids,
            "cycle": self.cycle,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ObservationFilter:
    """Filter for selecting observations."""
    obs_types: Optional[List[ObservationType]] = None
    min_priority: Optional[ObservationPriority] = None
    source_ids: Optional[List[str]] = None
    target_ids: Optional[List[str]] = None
    
    def matches(self, obs: Observation) -> bool:
        """Check if an observation matches this filter."""
        if self.obs_types and obs.obs_type not in self.obs_types:
            return False
        
        if self.min_priority:
            priority_order = [
                ObservationPriority.BACKGROUND,
                ObservationPriority.LOW,
                ObservationPriority.MEDIUM,
                ObservationPriority.HIGH,
                ObservationPriority.CRITICAL
            ]
            if priority_order.index(obs.priority) < priority_order.index(self.min_priority):
                return False
        
        if self.source_ids and obs.source_id not in self.source_ids:
            return False
        
        if self.target_ids:
            if not any(t in self.target_ids for t in obs.target_ids):
                return False
        
        return True


class ObservationProcessor:
    """
    Pipeline for processing and distributing observations.
    """
    
    def __init__(
        self,
        memory_bank: Optional[ChromaDBMemoryBank] = None,
        memory_stream: Optional[MemoryStream] = None,
        auto_store: bool = True
    ):
        """
        Initialize the observation processor.
        
        Args:
            memory_bank: Optional memory bank for storage
            memory_stream: Optional event stream for logging
            auto_store: Whether to automatically store observations
        """
        self._memory_bank = memory_bank
        self._memory_stream = memory_stream
        self._auto_store = auto_store
        self._pending: List[Observation] = []
        self._filters: Dict[str, ObservationFilter] = {}
        self._handlers: List[Callable[[Observation], None]] = []
    
    def add_observation(
        self,
        content: str,
        obs_type: ObservationType,
        priority: ObservationPriority = ObservationPriority.MEDIUM,
        source_id: Optional[str] = None,
        target_ids: Optional[List[str]] = None,
        cycle: int = 0,
        **metadata
    ) -> Observation:
        """
        Add a new observation to be processed.
        
        Args:
            content: Observation text
            obs_type: Type of observation
            priority: Priority level
            source_id: Source identifier
            target_ids: Target identifiers
            cycle: Simulation cycle
            **metadata: Additional metadata
        
        Returns:
            The created Observation
        """
        obs = Observation(
            content=content,
            obs_type=obs_type,
            priority=priority,
            source_id=source_id,
            target_ids=target_ids or [],
            cycle=cycle,
            metadata=metadata
        )
        
        self._pending.append(obs)
        
        # Call registered handlers
        for handler in self._handlers:
            try:
                handler(obs)
            except Exception as e:
                logger.error(f"Handler error: {e}")
        
        # Auto-store if enabled
        if self._auto_store:
            self._store_observation(obs)
        
        return obs
    
    def register_handler(
        self, 
        handler: Callable[[Observation], None]
    ) -> None:
        """Register a handler to be called for each observation."""
        self._handlers.append(handler)
    
    def register_filter(
        self, 
        name: str, 
        filter_config: ObservationFilter
    ) -> None:
        """Register a named filter for observation selection."""
        self._filters[name] = filter_config
    
    def _store_observation(self, obs: Observation) -> None:
        """Store observation in memory systems."""
        # Store in memory bank
        if self._memory_bank:
            # Determine scope based on target_ids
            if obs.target_ids:
                # Store as accessible to targets
                for target_id in obs.target_ids:
                    self._memory_bank.add(
                        obs.content,
                        scope=MemoryScope.PRIVATE,
                        owner_id=target_id,
                        cycle=obs.cycle,
                        importance=self._priority_to_importance(obs.priority)
                    )
            else:
                # Store as public
                self._memory_bank.add(
                    obs.content,
                    scope=MemoryScope.PUBLIC,
                    cycle=obs.cycle,
                    importance=self._priority_to_importance(obs.priority)
                )
        
        # Log to event stream
        if self._memory_stream:
            self._memory_stream.add_observation(
                content=obs.content,
                cycle=obs.cycle,
                actor_id=obs.source_id,
                metadata=obs.to_dict()
            )
    
    def _priority_to_importance(self, priority: ObservationPriority) -> float:
        """Convert priority to importance score."""
        mapping = {
            ObservationPriority.BACKGROUND: 0.2,
            ObservationPriority.LOW: 0.4,
            ObservationPriority.MEDIUM: 0.5,
            ObservationPriority.HIGH: 0.7,
            ObservationPriority.CRITICAL: 0.9
        }
        return mapping.get(priority, 0.5)
    
    def get_observations_for_actor(
        self,
        actor_id: str,
        filter_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Observation]:
        """
        Get observations relevant to a specific actor.
        
        Args:
            actor_id: The actor's ID
            filter_name: Optional named filter to apply
            limit: Maximum number to return
        
        Returns:
            List of relevant observations
        """
        relevant = []
        
        for obs in self._pending:
            # Check if actor is a target or if no targets specified
            if actor_id in obs.target_ids or not obs.target_ids:
                if filter_name and filter_name in self._filters:
                    if self._filters[filter_name].matches(obs):
                        relevant.append(obs)
                else:
                    relevant.append(obs)
        
        # Sort by priority (highest first)
        priority_order = [
            ObservationPriority.CRITICAL,
            ObservationPriority.HIGH,
            ObservationPriority.MEDIUM,
            ObservationPriority.LOW,
            ObservationPriority.BACKGROUND
        ]
        relevant.sort(key=lambda x: priority_order.index(x.priority))
        
        if limit:
            relevant = relevant[:limit]
        
        return relevant
    
    def process_world_state_change(
        self,
        old_state: WorldState,
        new_state: WorldState,
        cycle: int
    ) -> List[Observation]:
        """
        Generate observations from world state changes.
        
        Args:
            old_state: Previous world state
            new_state: Current world state
            cycle: Current simulation cycle
        
        Returns:
            List of generated observations
        """
        observations = []
        
        # Check for new global events
        old_events = set(old_state.environment.global_events)
        new_events = new_state.environment.global_events
        
        for event in new_events:
            if event not in old_events:
                obs = self.add_observation(
                    content=event,
                    obs_type=ObservationType.EVENT,
                    priority=ObservationPriority.HIGH,
                    source_id="archon",
                    cycle=cycle
                )
                observations.append(obs)
        
        # Check for weather changes
        if old_state.environment.weather != new_state.environment.weather:
            obs = self.add_observation(
                content=f"Weather changed to: {new_state.environment.weather}",
                obs_type=ObservationType.ENVIRONMENT,
                priority=ObservationPriority.MEDIUM,
                source_id="gaia",
                cycle=cycle
            )
            observations.append(obs)
        
        # Check for asset status changes
        for asset_id, new_asset in new_state.assets.items():
            if asset_id in old_state.assets:
                old_asset = old_state.assets[asset_id]
                if old_asset.status != new_asset.status:
                    obs = self.add_observation(
                        content=f"{new_asset.name} status: {old_asset.status} -> {new_asset.status}",
                        obs_type=ObservationType.ASSET_STATUS,
                        priority=ObservationPriority.HIGH,
                        source_id=asset_id,
                        cycle=cycle
                    )
                    observations.append(obs)
        
        return observations
    
    def clear_pending(self) -> None:
        """Clear pending observations."""
        self._pending.clear()
    
    def get_pending_count(self) -> int:
        """Get number of pending observations."""
        return len(self._pending)


def create_observation_processor(
    memory_bank: Optional[ChromaDBMemoryBank] = None,
    memory_stream: Optional[MemoryStream] = None
) -> ObservationProcessor:
    """
    Create an observation processor with default configuration.
    
    Args:
        memory_bank: Optional memory bank
        memory_stream: Optional event stream
    
    Returns:
        Configured ObservationProcessor
    """
    return ObservationProcessor(
        memory_bank=memory_bank,
        memory_stream=memory_stream,
        auto_store=True
    )

