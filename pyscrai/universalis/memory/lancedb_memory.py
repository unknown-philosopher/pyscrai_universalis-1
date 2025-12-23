"""
LanceDB Memory Bank - Vector memory system for PyScrAI Universalis.

This module implements a LanceDB adapter that provides Concordia-compatible
AssociativeMemoryBank interface with scope-based access control and
Arrow integration for hybrid queries with DuckDB.
"""

import hashlib
import threading
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyarrow as pa

from pyscrai.universalis.memory.scopes import (
    MemoryScope,
    MemoryMetadata,
    ScopeFilter,
)
from pyscrai.universalis.memory.interface import MemoryBank
from pyscrai.config import get_config
from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)

# Try to import lancedb
try:
    import lancedb
    from lancedb.embeddings import get_registry
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False
    logger.warning("LanceDB not available. Install with: pip install lancedb")


class LanceDBMemoryBank(MemoryBank):
    """
    LanceDB-backed associative memory implementing Concordia interface.
    
    Provides semantic memory retrieval with scope-based access control
    for multi-agent simulations. Uses Arrow for zero-copy integration
    with DuckDB spatial queries.
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        table_name: Optional[str] = None,
        simulation_id: Optional[str] = None,
        embedding_function: Optional[Callable[[str], List[float]]] = None
    ):
        """
        Initialize the LanceDB memory bank.
        
        Args:
            db_path: Path to LanceDB storage
            table_name: Name of the memory table
            simulation_id: Simulation identifier for namespacing
            embedding_function: Custom embedding function
        """
        if not LANCEDB_AVAILABLE:
            raise RuntimeError("LanceDB is not installed. Install with: pip install lancedb")
        
        config = get_config()
        self._db_path = db_path or config.lancedb.path
        self._table_name = table_name or config.lancedb.table_name
        self._simulation_id = simulation_id or config.simulation.simulation_id
        self._embedding_dim = config.lancedb.embedding_dim
        
        self._lock = threading.Lock()
        self._stored_hashes: set = set()
        
        # Ensure directory exists
        Path(self._db_path).mkdir(parents=True, exist_ok=True)
        
        # Connect to LanceDB
        self._db = lancedb.connect(self._db_path)
        
        # Set up embedding function
        self._embedding_function = embedding_function
        if self._embedding_function is None:
            self._init_default_embeddings()
        
        # Get or create table
        self._init_table()
        
        logger.info(f"LanceDB memory bank initialized: {self._db_path}/{self._table_name}")
    
    def _init_default_embeddings(self) -> None:
        """Initialize default sentence-transformers embedding function."""
        try:
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer('all-MiniLM-L6-v2')
            self._embedding_dim = model.get_sentence_embedding_dimension()
            
            def embed_fn(text: str) -> List[float]:
                return model.encode(text).tolist()
            
            self._embedding_function = embed_fn
            logger.info("Initialized sentence-transformers embeddings")
        except ImportError:
            logger.warning("sentence-transformers not available, using random embeddings")
            import random
            
            def random_embed(text: str) -> List[float]:
                random.seed(hash(text) % (2**32))
                return [random.random() for _ in range(self._embedding_dim)]
            
            self._embedding_function = random_embed
    
    def _init_table(self) -> None:
        """Initialize or get the memory table."""
        full_table_name = f"{self._table_name}_{self._simulation_id}"
        
        try:
            # Try to open existing table
            self._table = self._db.open_table(full_table_name)
            logger.info(f"Opened existing table: {full_table_name}")
        except Exception:
            # Create new table with schema
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("text", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), self._embedding_dim)),
                pa.field("scope", pa.string()),
                pa.field("owner_id", pa.string()),
                pa.field("group_id", pa.string()),
                pa.field("cycle", pa.int32()),
                pa.field("importance", pa.float32()),
                pa.field("tags", pa.string()),
                pa.field("timestamp", pa.string()),
                pa.field("simulation_id", pa.string()),
            ])
            
            # Create empty table
            self._table = self._db.create_table(
                full_table_name,
                schema=schema,
                mode="overwrite"
            )
            logger.info(f"Created new table: {full_table_name}")
    
    def set_embedder(self, embedder: Callable[[str], List[float]]) -> None:
        """Set the embedding function."""
        self._embedding_function = embedder
    
    def _compute_hash(self, text: str, owner_id: Optional[str], scope: MemoryScope) -> str:
        """Compute a unique hash for a memory entry."""
        content = f"{text}:{owner_id or ''}:{scope.value}"
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
        
        # Check for duplicates
        content_hash = self._compute_hash(text, owner_id, scope)
        
        with self._lock:
            if content_hash in self._stored_hashes:
                return False
            
            # Generate embedding
            embedding = self._embedding_function(text)
            
            # Generate unique ID
            memory_id = f"{self._simulation_id}_{content_hash}"
            
            # Prepare data for LanceDB
            data = [{
                "id": memory_id,
                "text": text,
                "vector": embedding,
                "scope": scope.value,
                "owner_id": owner_id or "",
                "group_id": group_id or "",
                "cycle": cycle,
                "importance": importance,
                "tags": ",".join(tags or []),
                "timestamp": datetime.now().isoformat(),
                "simulation_id": self._simulation_id
            }]
            
            # Add to table
            self._table.add(data)
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
        
        with self._lock:
            # Generate query embedding
            query_embedding = self._embedding_function(query)
            
            # Build search
            search = self._table.search(query_embedding).limit(k * 2)  # Get extra for filtering
            
            # Apply scope filter if provided
            if scope_filter:
                filter_expr = scope_filter.build_lancedb_filter()
                if filter_expr:
                    search = search.where(filter_expr)
            
            # Execute search
            results = search.to_list()
            
            # Extract texts
            return [r['text'] for r in results[:k]]
    
    def _build_lance_filter(self, scope_filter: ScopeFilter) -> Optional[str]:
        """
        Build a LanceDB filter expression from ScopeFilter.
        
        DEPRECATED: Use scope_filter.build_lancedb_filter() instead.
        This method is kept for backward compatibility but adds simulation_id filtering.
        """
        conditions = []
        
        # Always filter by simulation
        conditions.append(f"simulation_id = '{self._simulation_id}'")
        
        # Use the ScopeFilter's build method
        scope_condition = scope_filter.build_lancedb_filter()
        if scope_condition:
            conditions.append(scope_condition)
        
        return " AND ".join(conditions) if conditions else None
    
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
        
        with self._lock:
            # Get all data and sort by timestamp
            try:
                df = self._table.to_pandas()
            except Exception:
                return []
            
            if df.empty:
                return []
            
            # Apply scope filter
            if scope_filter:
                df = self._apply_pandas_filter(df, scope_filter)
            
            # Sort by timestamp descending
            df = df.sort_values('timestamp', ascending=False)
            
            return df['text'].head(k).tolist()
    
    def _apply_pandas_filter(self, df, scope_filter: ScopeFilter):
        """Apply scope filter to a pandas DataFrame."""
        # Filter by simulation
        df = df[df['simulation_id'] == self._simulation_id]
        
        if scope_filter.requesting_agent_id:
            agent_id = scope_filter.requesting_agent_id
            groups = scope_filter.agent_groups or []
            
            mask = (
                (df['scope'] == 'PUBLIC') |
                ((df['scope'] == 'PRIVATE') & (df['owner_id'] == agent_id)) |
                ((df['scope'] == 'SHARED_GROUP') & (df['group_id'].isin(groups)))
            )
            df = df[mask]
        else:
            df = df[df['scope'] == 'PUBLIC']
        
        return df
    
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
        with self._lock:
            try:
                df = self._table.to_pandas()
            except Exception:
                return []
            
            if df.empty:
                return []
            
            # Apply scope filter
            if scope_filter:
                df = self._apply_pandas_filter(df, scope_filter)
            
            # Apply selector function
            return [text for text in df['text'] if selector_fn(text)]
    
    def to_arrow(self) -> pa.Table:
        """
        Export memories as an Arrow table for DuckDB integration.
        
        This enables hybrid queries joining memory with spatial data.
        
        Returns:
            PyArrow Table with all memories
        """
        with self._lock:
            return self._table.to_arrow()
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state for checkpointing.
        
        Returns:
            State dictionary
        """
        with self._lock:
            return {
                "simulation_id": self._simulation_id,
                "table_name": self._table_name,
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
        with self._lock:
            try:
                df = self._table.to_pandas()
            except Exception:
                return []
            
            if df.empty:
                return []
            
            if scope_filter:
                df = self._apply_pandas_filter(df, scope_filter)
            
            return df['text'].tolist()
    
    def __len__(self) -> int:
        """Return the number of memories in the bank."""
        with self._lock:
            return len(self._stored_hashes)
    
    def clear(self) -> None:
        """Clear all memories from the bank."""
        with self._lock:
            full_table_name = f"{self._table_name}_{self._simulation_id}"
            
            # Drop and recreate table
            self._db.drop_table(full_table_name)
            self._init_table()
            self._stored_hashes.clear()
        
        logger.info(f"Memory bank cleared: {self._table_name}_{self._simulation_id}")

