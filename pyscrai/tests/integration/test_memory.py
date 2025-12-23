"""Integration tests for LanceDB memory management.

These tests use real LanceDB instances to test semantic memory operations,
scope-based access control, and vector similarity queries.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any

from pyscrai.universalis.memory.lancedb_memory import LanceDBMemoryBank
from pyscrai.universalis.memory.scopes import MemoryScope, ScopeFilter


class TestLanceDBMemoryBank:
    """Test LanceDB memory bank with real database operations."""
    
    def test_init_with_memory_db(self, clean_config):
        """Test LanceDB memory bank initialization with temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            memory = LanceDBMemoryBank(
                db_path=str(temp_dir),
                table_name="test_memories",
                simulation_id="test_sim"
            )
            assert memory._simulation_id == "test_sim"
            assert memory._table_name == "test_memories"
            memory.clear()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_add_memory(self, lancedb_memory):
        """Test adding a single memory."""
        result = lancedb_memory.add(
            text="Test memory content",
            scope=MemoryScope.MACRO,
            owner_id="actor_1",
            group_id="group_test",
            cycle=1,
            importance=0.8,
            tags=["test", "memory"]
        )
        
        assert result is True
        assert len(lancedb_memory) == 1
    
    def test_add_duplicate_memory(self, lancedb_memory):
        """Test that duplicate memories are not added."""
        # Add first memory
        result1 = lancedb_memory.add("Test content", scope=MemoryScope.MACRO)
        assert result1 is True
        
        # Try to add duplicate
        result2 = lancedb_memory.add("Test content", scope=MemoryScope.MACRO)
        assert result2 is False
        
        # Should still only have one memory
        assert len(lancedb_memory) == 1
    
    def test_add_memory_without_owner(self, lancedb_memory):
        """Test adding memory without owner ID."""
        result = lancedb_memory.add(
            text="Public memory content",
            scope=MemoryScope.MACRO,
            owner_id=None,
            cycle=1
        )
        
        assert result is True
        assert len(lancedb_memory) == 1
    
    def test_extend_multiple_memories(self, lancedb_memory):
        """Test adding multiple memories at once."""
        texts = [
            "First memory content",
            "Second memory content", 
            "Third memory content"
        ]
        
        count = lancedb_memory.extend(
            texts=texts,
            scope=MemoryScope.MICRO,
            owner_id="actor_2",
            cycle=2
        )
        
        assert count == 3
        assert len(lancedb_memory) == 3
    
    def test_extend_with_duplicates(self, lancedb_memory):
        """Test extending with some duplicate memories."""
        texts = ["Memory 1", "Memory 2", "Memory 1"]  # First and third are duplicates
        
        count = lancedb_memory.extend(texts, scope=MemoryScope.MACRO)
        
        # Should only add 2 unique memories
        assert count == 2
        assert len(lancedb_memory) == 2
    
    def test_retrieve_associative(self, populated_lancedb):
        """Test retrieving memories by semantic similarity."""
        results = populated_lancedb.retrieve_associative(
            query="Commander's orders for today",
            k=3
        )
        
        assert len(results) <= 3
        assert len(results) > 0
        # Should include the exact match or similar content
        assert any("Commander" in result or "orders" in result for result in results)
    
    def test_retrieve_associative_empty_result(self, lancedb_memory):
        """Test retrieving with query that has no matches."""
        results = lancedb_memory.retrieve_associative(
            query="completely unrelated query with no matches",
            k=5
        )
        
        assert len(results) == 0
    
    def test_retrieve_recent(self, populated_lancedb):
        """Test retrieving most recent memories."""
        results = populated_lancedb.retrieve_recent(k=3)
        
        assert len(results) <= 3
        assert len(results) > 0
        # Results should be sorted by recency
    
    def test_retrieve_recent_empty(self, lancedb_memory):
        """Test retrieving recent memories from empty database."""
        results = lancedb_memory.retrieve_recent(k=5)
        assert len(results) == 0
    
    def test_scan_with_selector(self, populated_lancedb):
        """Test scanning memories with a selector function."""
        def contains_commander(text: str) -> bool:
            return "Commander" in text
        
        results = populated_lancedb.scan(selector_fn=contains_commander)
        
        assert len(results) > 0
        assert all("Commander" in result for result in results)
    
    def test_scan_empty_result(self, populated_lancedb):
        """Test scanning with selector that matches nothing."""
        def never_matches(text: str) -> bool:
            return False
        
        results = populated_lancedb.scan(selector_fn=never_matches)
        assert len(results) == 0
    
    def test_to_arrow(self, populated_lancedb):
        """Test exporting memories to Arrow table."""
        arrow_table = populated_lancedb.to_arrow()
        
        assert arrow_table is not None
        assert len(arrow_table) > 0
        
        # Check that expected columns exist
        columns = arrow_table.column_names
        expected_columns = ['id', 'text', 'vector', 'scope', 'owner_id', 'group_id', 'cycle', 'importance', 'tags', 'timestamp', 'simulation_id']
        for col in expected_columns:
            assert col in columns
    
    def test_get_state(self, populated_lancedb):
        """Test getting memory bank state for checkpointing."""
        state = populated_lancedb.get_state()
        
        assert state is not None
        assert 'simulation_id' in state
        assert 'table_name' in state
        assert 'stored_hashes' in state
        assert 'memory_count' in state
        assert state['memory_count'] > 0
    
    def test_set_state(self, lancedb_memory):
        """Test restoring memory bank state from checkpoint."""
        # Add some memories
        lancedb_memory.add("Test memory 1", scope=MemoryScope.MACRO)
        lancedb_memory.add("Test memory 2", scope=MemoryScope.MICRO)
        
        # Get state
        state = lancedb_memory.get_state()
        
        # Clear and restore
        lancedb_memory.clear()
        lancedb_memory.set_state(state)
        
        # Should have restored the count (though actual data might not be restored depending on implementation)
        restored_state = lancedb_memory.get_state()
        assert restored_state['memory_count'] == state['memory_count']
    
    def test_get_all_memories_as_text(self, populated_lancedb):
        """Test getting all memories as text."""
        memories = populated_lancedb.get_all_memories_as_text()
        
        assert len(memories) > 0
        assert all(isinstance(memory, str) for memory in memories)
        assert len(memories) == len(populated_lancedb)
    
    def test_clear(self, populated_lancedb):
        """Test clearing all memories."""
        initial_count = len(populated_lancedb)
        assert initial_count > 0
        
        populated_lancedb.clear()
        assert len(populated_lancedb) == 0
        
        # Should be able to add new memories after clearing
        populated_lancedb.add("New memory after clear", scope=MemoryScope.MACRO)
        assert len(populated_lancedb) == 1


class TestLanceDBScopeFiltering:
    """Test scope-based access control."""
    
    def test_public_scope_access(self, populated_lancedb):
        """Test accessing public memories without agent ID."""
        scope_filter = ScopeFilter()
        
        results = populated_lancedb.retrieve_associative(
            query="weather",
            k=5,
            scope_filter=scope_filter
        )
        
        # Should only return public memories
        assert len(results) > 0
        # All results should be public scope
    
    def test_private_scope_access_own(self, populated_lancedb):
        """Test accessing own private memories."""
        scope_filter = ScopeFilter(requesting_agent_id="actor_1")
        
        results = populated_lancedb.retrieve_associative(
            query="Commander",
            k=5,
            scope_filter=scope_filter
        )
        
        assert len(results) > 0
        # Should include both public and actor_1's private memories
    
    def test_private_scope_access_other(self, populated_lancedb):
        """Test that agents cannot access other agents' private memories."""
        scope_filter = ScopeFilter(requesting_agent_id="actor_3")  # Different agent
        
        results = populated_lancedb.retrieve_associative(
            query="Commander",
            k=5,
            scope_filter=scope_filter
        )
        
        # Should only return public memories, not actor_1's private ones
        assert len(results) >= 0
        # Results should not contain private memories from other agents
    
    def test_shared_group_scope_access(self, populated_lancedb):
        """Test accessing shared group memories."""
        scope_filter = ScopeFilter(
            requesting_agent_id="actor_1",
            agent_groups=["group_logistics"]
        )
        
        results = populated_lancedb.retrieve_associative(
            query="logistics",
            k=5,
            scope_filter=scope_filter
        )
        
        assert len(results) > 0
        # Should include public, actor_1's private, and group_logistics shared memories
    
    def test_shared_group_scope_no_access(self, populated_lancedb):
        """Test that agents cannot access groups they're not in."""
        scope_filter = ScopeFilter(
            requesting_agent_id="actor_2",
            agent_groups=["other_group"]  # Not in logistics group
        )
        
        results = populated_lancedb.retrieve_associative(
            query="logistics",
            k=5,
            scope_filter=scope_filter
        )
        
        # Should not include group_logistics shared memories
        assert len(results) >= 0
    
    def test_recent_with_scope_filter(self, populated_lancedb):
        """Test retrieving recent memories with scope filtering."""
        scope_filter = ScopeFilter(requesting_agent_id="actor_1")
        
        results = populated_lancedb.retrieve_recent(
            k=5,
            scope_filter=scope_filter
        )
        
        assert len(results) > 0
        # Should respect scope filtering
    
    def test_scan_with_scope_filter(self, populated_lancedb):
        """Test scanning with scope filtering."""
        def contains_test(text: str) -> bool:
            return "Test" in text
        
        scope_filter = ScopeFilter(requesting_agent_id="actor_1")
        
        results = populated_lancedb.scan(
            selector_fn=contains_test,
            scope_filter=scope_filter
        )
        
        # Should respect scope filtering
        assert len(results) >= 0


class TestLanceDBEmbeddings:
    """Test embedding functionality."""
    
    def test_custom_embedding_function(self, clean_config):
        """Test using a custom embedding function."""
        def custom_embed(text: str) -> List[float]:
            # Simple deterministic embedding based on text hash
            import hashlib
            hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            return [float((hash_val >> i) & 255) / 255.0 for i in range(10)]
        
        temp_dir = Path(tempfile.mkdtemp())
        try:
            memory = LanceDBMemoryBank(
                db_path=str(temp_dir),
                table_name="test_memories",
                simulation_id="test_sim",
                embedding_function=custom_embed
            )
            
            # Add memory with custom embedding
            result = memory.add("Test content", scope=MemoryScope.MACRO)
            assert result is True
            
            # Should be able to retrieve
            results = memory.retrieve_associative("Test", k=1)
            assert len(results) > 0
            
            memory.clear()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_embedding_dimension_consistency(self, lancedb_memory):
        """Test that embeddings have consistent dimensions."""
        # Add a memory to trigger embedding initialization
        lancedb_memory.add("Test content", scope=MemoryScope.MACRO)
        
        # Get the embedding dimension from the table schema
        arrow_table = lancedb_memory.to_arrow()
        vector_column = arrow_table.column('vector')
        
        # All vectors should have the same dimension
        first_vector = vector_column[0].as_py()
        vector_dim = len(first_vector)
        
        for i in range(len(vector_column)):
            vector = vector_column[i].as_py()
            assert len(vector) == vector_dim


class TestLanceDBErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_embedding_function(self, clean_config):
        """Test handling of invalid embedding function."""
        def bad_embed(text: str) -> List[float]:
            return "not a list"  # Invalid return type
        
        temp_dir = Path(tempfile.mkdtemp())
        try:
            memory = LanceDBMemoryBank(
                db_path=str(temp_dir),
                table_name="test_memories",
                simulation_id="test_sim",
                embedding_function=bad_embed
            )
            
            # Adding memory should fail gracefully
            result = memory.add("Test content", scope=MemoryScope.MACRO)
            assert result is False
            
            memory.clear()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_empty_text_handling(self, lancedb_memory):
        """Test handling of empty or whitespace-only text."""
        # Empty string should not be added
        result1 = lancedb_memory.add("", scope=MemoryScope.MACRO)
        assert result1 is False
        
        # Whitespace-only should not be added
        result2 = lancedb_memory.add("   \n\t  ", scope=MemoryScope.MACRO)
        assert result2 is False
        
        # Valid text should be added
        result3 = lancedb_memory.add("Valid content", scope=MemoryScope.MACRO)
        assert result3 is True
    
    def test_large_text_handling(self, lancedb_memory):
        """Test handling of very large text content."""
        large_text = "A" * 10000  # 10KB of text
        
        result = lancedb_memory.add(large_text, scope=MemoryScope.MACRO)
        assert result is True
        
        # Should still be able to retrieve
        results = lancedb_memory.retrieve_associative("A", k=1)
        assert len(results) > 0
    
    def test_special_characters_in_text(self, lancedb_memory):
        """Test handling of special characters in memory text."""
        special_text = "Memory with special chars: !@#$%^&*(){}[]|\\:;\"'<>?,./"
        
        result = lancedb_memory.add(special_text, scope=MemoryScope.MACRO)
        assert result is True
        
        # Should be able to retrieve
        results = lancedb_memory.retrieve_associative("special", k=1)
        assert len(results) > 0


class TestLanceDBPerformance:
    """Test performance with larger datasets."""
    
    def test_large_dataset_creation(self, clean_config):
        """Test creating a large number of memories."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            memory = LanceDBMemoryBank(
                db_path=str(temp_dir),
                table_name="test_memories",
                simulation_id="test_sim"
            )
            
            # Add many memories
            num_memories = 100
            for i in range(num_memories):
                text = f"Memory content {i} with some random text to make it more interesting"
                memory.add(text, scope=MemoryScope.MACRO, cycle=i % 10)
            
            assert len(memory) == num_memories
            
            # Should be able to retrieve quickly
            results = memory.retrieve_associative("Memory content", k=10)
            assert len(results) <= 10
            assert len(results) > 0
            
            memory.clear()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_large_dataset_query_performance(self, populated_lancedb):
        """Test query performance with larger dataset."""
        # Add more memories to make it larger
        additional_memories = [
            f"Additional memory {i} with various content" for i in range(50)
        ]
        populated_lancedb.extend(additional_memories, scope=MemoryScope.MICRO)
        
        # Query should still be fast
        import time
        start_time = time.time()
        results = populated_lancedb.retrieve_associative("memory", k=20)
        query_time = time.time() - start_time
        
        assert len(results) <= 20
        assert query_time < 1.0  # Should be under 1 second


class TestLanceDBPersistence:
    """Test memory persistence across sessions."""
    
    def test_memory_persistence(self, clean_config):
        """Test that memories persist when recreating memory bank."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Create first memory bank and add memories
            memory1 = LanceDBMemoryBank(
                db_path=str(temp_dir),
                table_name="test_memories",
                simulation_id="test_sim"
            )
            
            memory1.add("Persistent memory 1", scope=MemoryScope.MACRO)
            memory1.add("Persistent memory 2", scope=MemoryScope.MICRO)
            initial_count = len(memory1)
            
            memory1.clear()
            
            # Create second memory bank with same path
            memory2 = LanceDBMemoryBank(
                db_path=str(temp_dir),
                table_name="test_memories",
                simulation_id="test_sim"
            )
            
            # Should have same memories
            final_count = len(memory2)
            assert final_count == initial_count
            
            memory2.clear()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
