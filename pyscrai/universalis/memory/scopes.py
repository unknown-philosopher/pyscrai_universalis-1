"""
Memory Scopes - Memory visibility and isolation for PyScrAI Universalis.

This module defines memory scoping to prevent cross-agent memory interference
while allowing appropriate sharing of public information.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Set, Union


class MemoryScope(str, Enum):
    """
    Memory visibility scopes.
    
    - PUBLIC: Accessible to all agents (news, weather, global events)
    - PRIVATE: Only accessible to the owning agent (personal decisions, status)
    - SHARED_GROUP: Accessible to agents in the same group (organizational knowledge)
    """
    PUBLIC = "public"
    PRIVATE = "private"
    SHARED_GROUP = "shared_group"


@dataclass
class MemoryMetadata:
    """
    Metadata attached to a memory entry.
    
    Attributes:
        scope: Visibility scope of the memory
        owner_id: ID of the agent that owns this memory
        group_id: Optional group ID for shared memories
        cycle: Simulation cycle when memory was created
        importance: Importance score (0.0 to 1.0)
        tags: Optional tags for categorization
    """
    scope: MemoryScope = MemoryScope.PRIVATE
    owner_id: Optional[str] = None
    group_id: Optional[str] = None
    cycle: int = 0
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "scope": self.scope.value,
            "owner_id": self.owner_id,
            "group_id": self.group_id,
            "cycle": self.cycle,
            "importance": self.importance,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MemoryMetadata":
        """Create from dictionary."""
        return cls(
            scope=MemoryScope(data.get("scope", "private")),
            owner_id=data.get("owner_id"),
            group_id=data.get("group_id"),
            cycle=data.get("cycle", 0),
            importance=data.get("importance", 0.5),
            tags=data.get("tags", [])
        )


class ScopeFilter:
    """
    Filter for memory retrieval based on scope.
    
    Determines which memories an agent is allowed to access.
    """
    
    def __init__(
        self,
        agent_id: str,
        groups: Optional[Set[str]] = None,
        include_public: bool = True
    ):
        """
        Initialize the scope filter.
        
        Args:
            agent_id: ID of the agent requesting memories
            groups: Set of group IDs the agent belongs to
            include_public: Whether to include public memories
        """
        self.agent_id = agent_id
        self.groups = groups or set()
        self.include_public = include_public
    
    def can_access(self, metadata: MemoryMetadata) -> bool:
        """
        Check if the agent can access a memory.
        
        Args:
            metadata: Memory metadata to check
        
        Returns:
            True if the agent can access the memory
        """
        # Public memories are accessible to all (if enabled)
        if metadata.scope == MemoryScope.PUBLIC and self.include_public:
            return True
        
        # Private memories only accessible to owner
        if metadata.scope == MemoryScope.PRIVATE:
            return metadata.owner_id == self.agent_id
        
        # Shared group memories accessible to group members
        if metadata.scope == MemoryScope.SHARED_GROUP:
            if metadata.group_id and metadata.group_id in self.groups:
                return True
            # Owner can always access their own shared memories
            return metadata.owner_id == self.agent_id
        
        return False
    
    def build_chromadb_filter(self) -> dict:
        """
        Build a ChromaDB where filter for scoped retrieval.
        
        Returns:
            Filter dict for ChromaDB queries
        """
        # Build OR conditions for accessible scopes
        conditions = []
        
        # Public scope
        if self.include_public:
            conditions.append({"scope": MemoryScope.PUBLIC.value})
        
        # Private scope (own memories)
        conditions.append({
            "$and": [
                {"scope": MemoryScope.PRIVATE.value},
                {"owner_id": self.agent_id}
            ]
        })
        
        # Shared group scope
        for group_id in self.groups:
            conditions.append({
                "$and": [
                    {"scope": MemoryScope.SHARED_GROUP.value},
                    {"group_id": group_id}
                ]
            })
        
        # Own shared memories
        conditions.append({
            "$and": [
                {"scope": MemoryScope.SHARED_GROUP.value},
                {"owner_id": self.agent_id}
            ]
        })
        
        if len(conditions) == 1:
            return conditions[0]
        
        return {"$or": conditions}
    
    def build_lancedb_filter(self) -> Optional[str]:
        """
        Build a LanceDB filter expression for scoped retrieval.
        
        Returns:
            SQL filter string for LanceDB queries, or None if no filter needed
        """
        conditions = []
        
        # Public scope
        if self.include_public:
            conditions.append("scope = 'PUBLIC'")
        
        # Private scope (own memories)
        conditions.append(
            f"(scope = 'PRIVATE' AND owner_id = '{self.agent_id}')"
        )
        
        # Shared group scope
        if self.groups:
            group_list = "', '".join(self.groups)
            conditions.append(
                f"(scope = 'SHARED_GROUP' AND group_id IN ('{group_list}'))"
            )
        
        # Own shared memories
        conditions.append(
            f"(scope = 'SHARED_GROUP' AND owner_id = '{self.agent_id}')"
        )
        
        if not conditions:
            return None
        
        # Combine with OR
        return f"({' OR '.join(conditions)})"


def create_public_memory_metadata(cycle: int, importance: float = 0.5) -> MemoryMetadata:
    """Create metadata for a public memory."""
    return MemoryMetadata(
        scope=MemoryScope.PUBLIC,
        cycle=cycle,
        importance=importance
    )


def create_private_memory_metadata(
    owner_id: str, 
    cycle: int, 
    importance: float = 0.5
) -> MemoryMetadata:
    """Create metadata for a private memory."""
    return MemoryMetadata(
        scope=MemoryScope.PRIVATE,
        owner_id=owner_id,
        cycle=cycle,
        importance=importance
    )


def create_shared_memory_metadata(
    owner_id: str,
    group_id: str,
    cycle: int,
    importance: float = 0.5
) -> MemoryMetadata:
    """Create metadata for a shared group memory."""
    return MemoryMetadata(
        scope=MemoryScope.SHARED_GROUP,
        owner_id=owner_id,
        group_id=group_id,
        cycle=cycle,
        importance=importance
    )

