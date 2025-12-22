"""
Associative Memory - ChromaDB-backed memory system for PyScrAI Universalis.

This module implements a ChromaDB adapter that provides Concordia-compatible
AssociativeMemoryBank interface with scope-based access control.
"""

import os
import threading
import hashlib
from collections.abc import Callable, Sequence
from typing import Any, Dict, List, Optional
from datetime import datetime

import chromadb
from chromadb.config import Settings

from pyscrai.universalis.memory.scopes import (
    MemoryScope,
    MemoryMetadata,
    ScopeFilter,
    create_public_memory_metadata,
    create_private_memory_metadata,
)
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


class ChromaDBMemoryBank:
    """
    ChromaDB-backed associative memory implementing Concordia interface.
    
    Provides semantic memory retrieval with scope-based access control
    for multi-agent simulations.
    """
    
    def __init__(
        self,
        collection_name: str = "pyscrai_memories",
        simulation_id: Optional[str] = None,
        chroma_host: Optional[str] = None,
        chroma_port: Optional[int] = None,
        embedding_function: Optional[Callable[[str], List[float]]] = None,
        persist_directory: Optional[str] = None
    ):
        """
        Initialize the ChromaDB memory bank.
        
        Args:
            collection_name: Name of the ChromaDB collection
            simulation_id: Simulation identifier for namespacing
            chroma_host: ChromaDB host (for HTTP client)
            chroma_port: ChromaDB port (for HTTP client)
            embedding_function: Custom embedding function
            persist_directory: Local persistence directory (for persistent client)
        """
        self._collection_name = collection_name
        self._simulation_id = simulation_id or "default"
        self._lock = threading.Lock()
        self._stored_hashes: set = set()
        
        # Initialize ChromaDB client
        if chroma_host and chroma_port:
            # HTTP client for remote ChromaDB
            self._client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port
            )
        elif persist_directory:
            # Persistent local client
            self._client = chromadb.PersistentClient(
                path=persist_directory
            )
        else:
            # In-memory client (default for testing)
            self._client = chromadb.Client()
        
        # Set up embedding function
        self._embedding_function = embedding_function
        
        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=f"{self._collection_name}_{self._simulation_id}",
            metadata={"simulation_id": self._simulation_id}
        )
        
        logger.info(f"ChromaDB memory bank initialized: {self._collection_name}_{self._simulation_id}")
    
    def set_embedder(self, embedder: Callable[[str], List[float]]) -> None:
        """Set the embedding function."""
        self._embedding_function = embedder
    
    def _compute_hash(self, text: str, metadata: MemoryMetadata) -> str:
        """Compute a unique hash for a memory entry."""
        content = f"{text}:{metadata.owner_id}:{metadata.scope.value}"
        return hashlib.md5(content.encode()).hexdigest()
    
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
        # Clean the text
        text = text.replace('\n', ' ').strip()
        if not text:
            return False
        
        # Create metadata
        metadata = MemoryMetadata(
            scope=scope,
            owner_id=owner_id,
            group_id=group_id,
            cycle=cycle,
            importance=importance,
            tags=tags or []
        )
        
        # Check for duplicates
        content_hash = self._compute_hash(text, metadata)
        
        with self._lock:
            if content_hash in self._stored_hashes:
                return False
            
            # Generate unique ID
            memory_id = f"{self._simulation_id}_{content_hash}"
            
            # Prepare metadata for ChromaDB
            chroma_metadata = {
                "scope": scope.value,
                "owner_id": owner_id or "",
                "group_id": group_id or "",
                "cycle": cycle,
                "importance": importance,
                "tags": ",".join(tags or []),
                "timestamp": datetime.now().isoformat(),
                "simulation_id": self._simulation_id
            }
            
            # Add to collection
            if self._embedding_function:
                embedding = self._embedding_function(text)
                self._collection.add(
                    ids=[memory_id],
                    documents=[text],
                    embeddings=[embedding],
                    metadatas=[chroma_metadata]
                )
            else:
                # Let ChromaDB handle embeddings
                self._collection.add(
                    ids=[memory_id],
                    documents=[text],
                    metadatas=[chroma_metadata]
                )
            
            self._stored_hashes.add(content_hash)
            return True
    
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
        count = 0
        for text in texts:
            if self.add(text, scope=scope, owner_id=owner_id, **kwargs):
                count += 1
        return count
    
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
        if k <= 0:
            return []
        
        # Build where filter
        where_filter = None
        if scope_filter:
            where_filter = scope_filter.build_chromadb_filter()
        
        with self._lock:
            results = self._collection.query(
                query_texts=[query],
                n_results=k,
                where=where_filter
            )
        
        if results and results['documents']:
            return results['documents'][0]
        return []
    
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
        if k <= 0:
            return []
        
        # Build where filter
        where_filter = None
        if scope_filter:
            where_filter = scope_filter.build_chromadb_filter()
        
        with self._lock:
            # Get all matching memories
            results = self._collection.get(
                where=where_filter,
                include=["documents", "metadatas"]
            )
        
        if not results or not results['documents']:
            return []
        
        # Sort by timestamp (most recent first)
        items = list(zip(results['documents'], results['metadatas']))
        items.sort(
            key=lambda x: x[1].get('timestamp', ''), 
            reverse=True
        )
        
        return [item[0] for item in items[:k]]
    
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
        # Build where filter
        where_filter = None
        if scope_filter:
            where_filter = scope_filter.build_chromadb_filter()
        
        with self._lock:
            results = self._collection.get(
                where=where_filter,
                include=["documents"]
            )
        
        if not results or not results['documents']:
            return []
        
        # Apply selector function
        return [doc for doc in results['documents'] if selector_fn(doc)]
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state for checkpointing.
        
        Returns:
            State dictionary
        """
        with self._lock:
            return {
                "simulation_id": self._simulation_id,
                "collection_name": self._collection_name,
                "stored_hashes": list(self._stored_hashes),
                "memory_count": len(self._stored_hashes)
            }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Restore state from checkpoint.
        
        Args:
            state: State dictionary from get_state()
        """
        with self._lock:
            self._stored_hashes = set(state.get('stored_hashes', []))
    
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
        where_filter = None
        if scope_filter:
            where_filter = scope_filter.build_chromadb_filter()
        
        with self._lock:
            results = self._collection.get(
                where=where_filter,
                include=["documents"]
            )
        
        if results and results['documents']:
            return results['documents']
        return []
    
    def __len__(self) -> int:
        """Return the number of memories in the bank."""
        with self._lock:
            return self._collection.count()
    
    def clear(self) -> None:
        """Clear all memories from the bank."""
        with self._lock:
            # Delete and recreate collection
            self._client.delete_collection(
                name=f"{self._collection_name}_{self._simulation_id}"
            )
            self._collection = self._client.create_collection(
                name=f"{self._collection_name}_{self._simulation_id}",
                metadata={"simulation_id": self._simulation_id}
            )
            self._stored_hashes.clear()
        logger.info(f"Memory bank cleared: {self._collection_name}_{self._simulation_id}")

