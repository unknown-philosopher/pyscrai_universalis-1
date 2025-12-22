"""
Micro View - Individual agent visualization components for PyScrAI Universalis.

This module provides visualization components for micro-level (individual)
views including agent inspection, memory visualization, and relationship graphs.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from pyscrai.data.schemas.models import WorldState, Actor
from pyscrai.universalis.memory.stream import MemoryStream, StreamEvent, EventType
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentProfile:
    """
    Detailed profile of an agent for micro view display.
    """
    actor_id: str
    role: str
    description: str
    state: str = "unknown"
    memory_count: int = 0
    relationship_count: int = 0
    recent_intents: List[str] = field(default_factory=list)
    objectives: List[str] = field(default_factory=list)
    assets: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "role": self.role,
            "description": self.description,
            "state": self.state,
            "memory_count": self.memory_count,
            "relationship_count": self.relationship_count,
            "recent_intents": self.recent_intents,
            "objectives": self.objectives,
            "assets": self.assets
        }


@dataclass
class MemoryEntry:
    """A memory entry for display."""
    text: str
    cycle: int
    importance: float
    scope: str
    timestamp: str


@dataclass
class RelationshipInfo:
    """Relationship information for display."""
    target_id: str
    target_role: str
    sentiment: float
    trust: float
    familiarity: float
    tags: List[str] = field(default_factory=list)


class MicroViewRenderer:
    """
    Renderer for micro-level (individual agent) visualization components.
    """
    
    def __init__(self, memory_stream: Optional[MemoryStream] = None):
        """
        Initialize the micro view renderer.
        
        Args:
            memory_stream: Optional memory stream for event access
        """
        self._memory_stream = memory_stream
        self._agent_states: Dict[str, str] = {}
        self._agent_memories: Dict[str, List[MemoryEntry]] = {}
        self._agent_relationships: Dict[str, List[RelationshipInfo]] = {}
    
    def get_agent_profile(
        self,
        actor: Actor,
        world_state: WorldState
    ) -> AgentProfile:
        """
        Get a detailed profile of an agent.
        
        Args:
            actor: The actor to profile
            world_state: Current world state
        
        Returns:
            AgentProfile for display
        """
        # Get recent intents from memory stream
        recent_intents = []
        if self._memory_stream:
            intent_events = self._memory_stream.get_events_by_actor(
                actor.actor_id, limit=5
            )
            recent_intents = [
                e.content for e in intent_events 
                if e.event_type == EventType.INTENT
            ]
        
        # Get counts
        memory_count = len(self._agent_memories.get(actor.actor_id, []))
        relationship_count = len(self._agent_relationships.get(actor.actor_id, []))
        
        return AgentProfile(
            actor_id=actor.actor_id,
            role=actor.role,
            description=actor.description,
            state=self._agent_states.get(actor.actor_id, "unknown"),
            memory_count=memory_count,
            relationship_count=relationship_count,
            recent_intents=recent_intents,
            objectives=actor.objectives,
            assets=actor.assets
        )
    
    def update_agent_state(self, actor_id: str, state: str) -> None:
        """Update the displayed state of an agent."""
        self._agent_states[actor_id] = state
    
    def add_memory_entry(
        self,
        actor_id: str,
        text: str,
        cycle: int,
        importance: float = 0.5,
        scope: str = "private"
    ) -> None:
        """Add a memory entry for display."""
        if actor_id not in self._agent_memories:
            self._agent_memories[actor_id] = []
        
        entry = MemoryEntry(
            text=text,
            cycle=cycle,
            importance=importance,
            scope=scope,
            timestamp=datetime.now().isoformat()
        )
        self._agent_memories[actor_id].append(entry)
    
    def get_agent_memories(
        self,
        actor_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get memories for an agent.
        
        Args:
            actor_id: The actor's ID
            limit: Maximum memories to return
        
        Returns:
            List of memory dicts
        """
        memories = self._agent_memories.get(actor_id, [])
        recent = memories[-limit:]
        
        return [
            {
                "text": m.text,
                "cycle": m.cycle,
                "importance": m.importance,
                "scope": m.scope,
                "timestamp": m.timestamp
            }
            for m in recent
        ]
    
    def add_relationship(
        self,
        actor_id: str,
        target_id: str,
        target_role: str,
        sentiment: float = 0.0,
        trust: float = 0.5,
        familiarity: float = 0.0,
        tags: Optional[List[str]] = None
    ) -> None:
        """Add or update a relationship for display."""
        if actor_id not in self._agent_relationships:
            self._agent_relationships[actor_id] = []
        
        # Check if relationship exists
        for rel in self._agent_relationships[actor_id]:
            if rel.target_id == target_id:
                rel.sentiment = sentiment
                rel.trust = trust
                rel.familiarity = familiarity
                rel.tags = tags or rel.tags
                return
        
        # Add new relationship
        self._agent_relationships[actor_id].append(RelationshipInfo(
            target_id=target_id,
            target_role=target_role,
            sentiment=sentiment,
            trust=trust,
            familiarity=familiarity,
            tags=tags or []
        ))
    
    def get_relationship_graph(
        self,
        actor_id: str
    ) -> Dict[str, Any]:
        """
        Get relationship data formatted for graph display.
        
        Args:
            actor_id: The actor's ID
        
        Returns:
            Graph data dict with nodes and edges
        """
        relationships = self._agent_relationships.get(actor_id, [])
        
        nodes = [{"id": actor_id, "type": "self"}]
        edges = []
        
        for rel in relationships:
            nodes.append({
                "id": rel.target_id,
                "role": rel.target_role,
                "type": "other"
            })
            
            edges.append({
                "source": actor_id,
                "target": rel.target_id,
                "sentiment": rel.sentiment,
                "trust": rel.trust,
                "familiarity": rel.familiarity,
                "tags": rel.tags
            })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def get_conversation_history(
        self,
        actor_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get conversation/interaction history for an agent.
        
        Args:
            actor_id: The actor's ID
            limit: Maximum entries to return
        
        Returns:
            List of conversation entries
        """
        if not self._memory_stream:
            return []
        
        events = self._memory_stream.get_events_by_actor(actor_id, limit=limit)
        
        conversation = []
        for event in events:
            if event.event_type in [EventType.INTENT, EventType.OBSERVATION]:
                conversation.append({
                    "type": event.event_type.value,
                    "content": event.content,
                    "cycle": event.cycle,
                    "timestamp": event.timestamp.isoformat()
                })
        
        return conversation
    
    def generate_agent_report(
        self,
        actor: Actor,
        world_state: WorldState
    ) -> Dict[str, Any]:
        """
        Generate a detailed report for an agent.
        
        Args:
            actor: The actor
            world_state: Current world state
        
        Returns:
            Detailed agent report
        """
        profile = self.get_agent_profile(actor, world_state)
        
        # Get asset details
        asset_details = []
        for asset_id in actor.assets:
            if asset_id in world_state.assets:
                asset = world_state.assets[asset_id]
                asset_details.append({
                    "id": asset.asset_id,
                    "name": asset.name,
                    "type": asset.asset_type,
                    "status": asset.status
                })
        
        return {
            "report_type": "agent",
            "generated_at": datetime.now().isoformat(),
            "cycle": world_state.environment.cycle,
            "profile": profile.to_dict(),
            "memories": self.get_agent_memories(actor.actor_id),
            "relationships": self.get_relationship_graph(actor.actor_id),
            "conversations": self.get_conversation_history(actor.actor_id),
            "assets": asset_details
        }


class MemoryVisualizer:
    """
    Visualizer for agent memory systems.
    """
    
    def __init__(self):
        """Initialize the memory visualizer."""
        self._memory_snapshots: Dict[str, List[Dict]] = {}
    
    def add_snapshot(
        self,
        actor_id: str,
        memories: List[Dict[str, Any]],
        cycle: int
    ) -> None:
        """Add a memory snapshot for an actor."""
        if actor_id not in self._memory_snapshots:
            self._memory_snapshots[actor_id] = []
        
        self._memory_snapshots[actor_id].append({
            "cycle": cycle,
            "memories": memories,
            "count": len(memories)
        })
    
    def get_memory_timeline(
        self,
        actor_id: str
    ) -> List[Dict[str, Any]]:
        """Get memory count over time for timeline display."""
        snapshots = self._memory_snapshots.get(actor_id, [])
        return [
            {"cycle": s["cycle"], "count": s["count"]}
            for s in snapshots
        ]
    
    def get_memory_distribution(
        self,
        actor_id: str
    ) -> Dict[str, int]:
        """Get distribution of memories by scope."""
        snapshots = self._memory_snapshots.get(actor_id, [])
        if not snapshots:
            return {}
        
        # Use latest snapshot
        latest = snapshots[-1]["memories"]
        distribution = {}
        
        for memory in latest:
            scope = memory.get("scope", "unknown")
            distribution[scope] = distribution.get(scope, 0) + 1
        
        return distribution


def create_micro_view(
    memory_stream: Optional[MemoryStream] = None
) -> MicroViewRenderer:
    """Create a micro view renderer instance."""
    return MicroViewRenderer(memory_stream=memory_stream)

