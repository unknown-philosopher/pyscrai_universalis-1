"""
Memory Pruning - Relevance decay and consolidation for PyScrAI Universalis.

This module provides memory maintenance to prevent retrieval latency
as the simulation runs for many cycles.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import threading

from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PruningConfig:
    """
    Configuration for memory pruning.
    
    Attributes:
        decay_rate: Rate at which importance decays per cycle (0.0-1.0)
        min_importance: Minimum importance threshold for keeping memories
        consolidation_threshold: Similarity threshold for merging memories
        prune_interval: Number of cycles between pruning runs
        max_memories: Maximum memories before forced pruning
    """
    decay_rate: float = 0.05
    min_importance: float = 0.1
    consolidation_threshold: float = 0.85
    prune_interval: int = 100
    max_memories: int = 10000


class RelevanceDecay:
    """
    Handles relevance decay of memories over time.
    
    Older memories gradually lose importance unless they are
    accessed or reinforced.
    """
    
    def __init__(self, decay_rate: float = 0.05):
        """
        Initialize relevance decay handler.
        
        Args:
            decay_rate: Rate of decay per cycle (0.0-1.0)
        """
        self.decay_rate = decay_rate
    
    def calculate_decayed_importance(
        self,
        original_importance: float,
        cycles_elapsed: int,
        access_count: int = 0
    ) -> float:
        """
        Calculate the decayed importance of a memory.
        
        Args:
            original_importance: Original importance score
            cycles_elapsed: Number of cycles since creation
            access_count: Number of times memory was accessed
        
        Returns:
            Decayed importance score
        """
        # Apply exponential decay
        decay_factor = (1 - self.decay_rate) ** cycles_elapsed
        
        # Boost for frequently accessed memories
        access_boost = min(1.0, access_count * 0.1)
        
        decayed = original_importance * decay_factor
        boosted = decayed + (access_boost * (1 - decayed))
        
        return max(0.0, min(1.0, boosted))
    
    def should_prune(
        self,
        importance: float,
        cycles_elapsed: int,
        min_importance: float = 0.1
    ) -> bool:
        """
        Determine if a memory should be pruned.
        
        Args:
            importance: Current importance score
            cycles_elapsed: Cycles since creation
            min_importance: Minimum threshold
        
        Returns:
            True if memory should be pruned
        """
        decayed = self.calculate_decayed_importance(importance, cycles_elapsed)
        return decayed < min_importance


class MemoryConsolidator:
    """
    Handles consolidation of similar memories.
    
    Merges semantically similar memories to reduce redundancy
    and improve retrieval efficiency.
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.85,
        similarity_fn: Optional[Callable[[str, str], float]] = None
    ):
        """
        Initialize the consolidator.
        
        Args:
            similarity_threshold: Threshold for merging (0.0-1.0)
            similarity_fn: Function to compute similarity between texts
        """
        self.threshold = similarity_threshold
        self._similarity_fn = similarity_fn or self._default_similarity
    
    def _default_similarity(self, text1: str, text2: str) -> float:
        """
        Default similarity function using Jaccard index.
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            Similarity score (0.0-1.0)
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def find_similar_memories(
        self,
        memories: List[str],
        target: str
    ) -> List[int]:
        """
        Find memories similar to a target.
        
        Args:
            memories: List of memory texts
            target: Target memory text
        
        Returns:
            List of indices of similar memories
        """
        similar = []
        for i, memory in enumerate(memories):
            similarity = self._similarity_fn(memory, target)
            if similarity >= self.threshold:
                similar.append(i)
        return similar
    
    def consolidate_pair(
        self,
        memory1: str,
        memory2: str,
        importance1: float = 0.5,
        importance2: float = 0.5
    ) -> tuple:
        """
        Consolidate two memories into one.
        
        Args:
            memory1: First memory text
            memory2: Second memory text
            importance1: Importance of first memory
            importance2: Importance of second memory
        
        Returns:
            Tuple of (consolidated_text, new_importance)
        """
        # Use the more important memory as base
        if importance1 >= importance2:
            base = memory1
            secondary = memory2
        else:
            base = memory2
            secondary = memory1
        
        # Simple consolidation: keep the base, boost importance
        new_importance = min(1.0, max(importance1, importance2) * 1.2)
        
        return base, new_importance


class MemoryPruner:
    """
    Main pruning orchestrator for memory maintenance.
    """
    
    def __init__(self, config: Optional[PruningConfig] = None):
        """
        Initialize the pruner.
        
        Args:
            config: Pruning configuration
        """
        self.config = config or PruningConfig()
        self._decay = RelevanceDecay(self.config.decay_rate)
        self._consolidator = MemoryConsolidator(self.config.consolidation_threshold)
        self._lock = threading.Lock()
        self._last_prune_cycle = 0
    
    def should_run_pruning(self, current_cycle: int) -> bool:
        """
        Check if pruning should run this cycle.
        
        Args:
            current_cycle: Current simulation cycle
        
        Returns:
            True if pruning should run
        """
        with self._lock:
            cycles_since = current_cycle - self._last_prune_cycle
            return cycles_since >= self.config.prune_interval
    
    def run_pruning(
        self,
        memories: List[Dict[str, Any]],
        current_cycle: int
    ) -> List[Dict[str, Any]]:
        """
        Run the pruning process on a list of memories.
        
        Args:
            memories: List of memory dicts with 'text', 'importance', 'cycle' keys
            current_cycle: Current simulation cycle
        
        Returns:
            Pruned list of memories
        """
        with self._lock:
            self._last_prune_cycle = current_cycle
        
        logger.info(f"Running memory pruning at cycle {current_cycle}")
        initial_count = len(memories)
        
        # Step 1: Apply relevance decay and filter
        surviving = []
        for memory in memories:
            cycles_elapsed = current_cycle - memory.get('cycle', 0)
            importance = memory.get('importance', 0.5)
            access_count = memory.get('access_count', 0)
            
            if not self._decay.should_prune(
                importance, 
                cycles_elapsed, 
                self.config.min_importance
            ):
                # Update importance with decay
                new_importance = self._decay.calculate_decayed_importance(
                    importance, cycles_elapsed, access_count
                )
                memory['importance'] = new_importance
                surviving.append(memory)
        
        # Step 2: Consolidate similar memories
        # (simplified - full implementation would use embeddings)
        consolidated = self._consolidate_memories(surviving)
        
        # Step 3: Enforce max memories limit
        if len(consolidated) > self.config.max_memories:
            # Sort by importance and keep top memories
            consolidated.sort(key=lambda x: x.get('importance', 0), reverse=True)
            consolidated = consolidated[:self.config.max_memories]
        
        pruned_count = initial_count - len(consolidated)
        logger.info(f"Pruning complete: removed {pruned_count} memories")
        
        return consolidated
    
    def _consolidate_memories(
        self,
        memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Consolidate similar memories.
        
        Args:
            memories: List of memory dicts
        
        Returns:
            Consolidated list
        """
        if len(memories) < 2:
            return memories
        
        # Simple consolidation based on text similarity
        texts = [m.get('text', '') for m in memories]
        to_remove = set()
        
        for i, memory in enumerate(memories):
            if i in to_remove:
                continue
            
            similar = self._consolidator.find_similar_memories(
                texts[i+1:], memory.get('text', '')
            )
            
            for j in similar:
                actual_idx = i + 1 + j
                if actual_idx not in to_remove:
                    # Consolidate into current memory
                    other = memories[actual_idx]
                    _, new_importance = self._consolidator.consolidate_pair(
                        memory.get('text', ''),
                        other.get('text', ''),
                        memory.get('importance', 0.5),
                        other.get('importance', 0.5)
                    )
                    memory['importance'] = new_importance
                    to_remove.add(actual_idx)
        
        return [m for i, m in enumerate(memories) if i not in to_remove]
    
    def update_access(
        self,
        memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update memory when accessed (reinforcement).
        
        Args:
            memory: Memory dict to update
        
        Returns:
            Updated memory dict
        """
        memory['access_count'] = memory.get('access_count', 0) + 1
        memory['last_accessed'] = datetime.now().isoformat()
        return memory


def create_default_pruner() -> MemoryPruner:
    """Create a pruner with default configuration."""
    return MemoryPruner()

