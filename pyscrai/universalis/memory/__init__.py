"""
Memory module - Cognitive backbone for PyScrAI agents.

This module manages a hybrid memory architecture:
- associative: ChromaDB-backed associative memory with semantic retrieval
- scopes: Memory scoping (PUBLIC, PRIVATE, SHARED_GROUP)
- pruning: Memory consolidation and relevance decay
- stream: Chronological event log for traceability
- embeddings: Sentence transformer integration
"""

from pyscrai.universalis.memory.associative import ChromaDBMemoryBank
from pyscrai.universalis.memory.scopes import (
    MemoryScope,
    MemoryMetadata,
    ScopeFilter,
    create_public_memory_metadata,
    create_private_memory_metadata,
    create_shared_memory_metadata
)
from pyscrai.universalis.memory.stream import (
    MemoryStream,
    StreamEvent,
    EventType
)
from pyscrai.universalis.memory.pruning import (
    MemoryPruner,
    PruningConfig,
    RelevanceDecay,
    MemoryConsolidator,
    create_default_pruner
)

__all__ = [
    # Associative memory
    "ChromaDBMemoryBank",
    # Scopes
    "MemoryScope",
    "MemoryMetadata",
    "ScopeFilter",
    "create_public_memory_metadata",
    "create_private_memory_metadata",
    "create_shared_memory_metadata",
    # Stream
    "MemoryStream",
    "StreamEvent",
    "EventType",
    # Pruning
    "MemoryPruner",
    "PruningConfig",
    "RelevanceDecay",
    "MemoryConsolidator",
    "create_default_pruner",
]
