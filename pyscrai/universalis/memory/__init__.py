"""
Memory module - Cognitive backbone for PyScrAI agents.

This module manages a hybrid memory architecture:
- lancedb_memory: LanceDB-backed associative memory with Arrow integration
- associative: ChromaDB-backed associative memory (legacy/fallback)
- scopes: Memory scoping (PUBLIC, PRIVATE, SHARED_GROUP)
- pruning: Memory consolidation and relevance decay
- stream: Chronological event log for traceability
- embeddings: Sentence transformer integration
"""

# Primary memory system (LanceDB)
from pyscrai.universalis.memory.lancedb_memory import LanceDBMemoryBank

# Legacy memory system (ChromaDB - for backward compatibility)
from pyscrai.universalis.memory.associative import ChromaDBMemoryBank

# Scopes
from pyscrai.universalis.memory.scopes import (
    MemoryScope,
    MemoryMetadata,
    ScopeFilter,
    create_public_memory_metadata,
    create_private_memory_metadata,
    create_shared_memory_metadata
)

# Stream
from pyscrai.universalis.memory.stream import (
    MemoryStream,
    StreamEvent,
    EventType
)

# Pruning
from pyscrai.universalis.memory.pruning import (
    MemoryPruner,
    PruningConfig,
    RelevanceDecay,
    MemoryConsolidator,
    create_default_pruner
)

__all__ = [
    # Primary memory (LanceDB)
    "LanceDBMemoryBank",
    # Legacy memory (ChromaDB)
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
