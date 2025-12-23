"""
Memory Bank Interface - Abstract base class for memory implementations.

This module defines the common interface that all memory bank implementations
must follow, enabling polymorphic usage across different backends.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Optional, List, Dict, Any

from pyscrai.universalis.memory.scopes import MemoryScope, ScopeFilter


class MemoryBank(ABC):
    """
    Abstract base class for associative memory banks.
    
    Provides a common interface for different memory implementations
    (LanceDB, ChromaDB, etc.) to ensure compatibility with agents.
    """
    
    @abstractmethod
    def add(
        self,
        text: str,
        scope: MemoryScope = MemoryScope.PRIVATE,
        owner_id: Optional[str] = None,
        group_id: Optional[str] = None,
        cycle: int = 0,
        importance: float = 0.5,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Add a memory entry to the bank.
        
        Args:
            text: The memory text content
            scope: Visibility scope for the memory
            owner_id: ID of the owning agent
            group_id: Optional group ID for shared memories
            cycle: Simulation cycle when memory was created
            importance: Importance score (0.0 to 1.0)
            tags: Optional tags for categorization
        
        Returns:
            True if memory was added, False if duplicate
        """
        pass
    
    @abstractmethod
    def extend(
        self,
        texts: Sequence[str],
        scope: MemoryScope = MemoryScope.PRIVATE,
        owner_id: Optional[str] = None,
        **kwargs
    ) -> int:
        """
        Add multiple memories at once.
        
        Args:
            texts: List of memory texts to add
            scope: Visibility scope for all memories
            owner_id: ID of the owning agent
            **kwargs: Additional arguments passed to add()
        
        Returns:
            Number of memories successfully added
        """
        pass
    
    @abstractmethod
    def retrieve_associative(
        self,
        query: str,
        k: int = 5,
        scope_filter: Optional[ScopeFilter] = None
    ) -> Sequence[str]:
        """
        Retrieve memories most similar to a query.
        
        Args:
            query: The query string
            k: Number of memories to retrieve
            scope_filter: Optional scope filter for access control
        
        Returns:
            List of memory texts, sorted by similarity
        """
        pass
    
    @abstractmethod
    def retrieve_recent(
        self,
        k: int = 5,
        scope_filter: Optional[ScopeFilter] = None
    ) -> Sequence[str]:
        """
        Retrieve most recent memories.
        
        Args:
            k: Number of memories to retrieve
            scope_filter: Optional scope filter for access control
        
        Returns:
            List of memory texts, sorted by recency
        """
        pass
    
    @abstractmethod
    def scan(
        self,
        selector_fn: Callable[[str], bool],
        scope_filter: Optional[ScopeFilter] = None
    ) -> Sequence[str]:
        """
        Retrieve memories matching a selector function.
        
        Args:
            selector_fn: Function that returns True for matching memories
            scope_filter: Optional scope filter for access control
        
        Returns:
            List of matching memory texts
        """
        pass
    
    @abstractmethod
    def get_all_memories_as_text(
        self,
        scope_filter: Optional[ScopeFilter] = None
    ) -> Sequence[str]:
        """
        Get all memories as text.
        
        Args:
            scope_filter: Optional scope filter for access control
        
        Returns:
            List of all memory texts
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all memories from the bank."""
        pass
    
    @abstractmethod
    def __len__(self) -> int:
        """Return the number of memories in the bank."""
        pass
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state for checkpointing.
        
        Returns:
            State dictionary
        """
        pass
    
    @abstractmethod
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Restore state from checkpoint.
        
        Args:
            state: State dictionary from get_state()
        """
        pass
    
    def set_embedder(self, embedder: Callable[[str], List[float]]) -> None:
        """
        Set the embedding function.
        
        Args:
            embedder: Function that converts text to embedding vector
        """
        # Default implementation - subclasses can override if needed
        pass

