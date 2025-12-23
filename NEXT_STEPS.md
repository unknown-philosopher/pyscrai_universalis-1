# GeoScrAI Next Steps & Action Plan

## 🎯 Current Status: ~85% Complete

Core migration is done. Critical fixes needed before production use.

## 🚨 Critical Issues (Fix First)

### 1. Agent Memory Type Mismatch ⚠️ BLOCKER
**Problem**: Agents expect `ChromaDBMemoryBank` but engine provides `LanceDBMemoryBank`

**Files to Fix**:
- `pyscrai/universalis/agents/macro_agent.py`
- `pyscrai/universalis/agents/micro_agent.py`  
- `pyscrai/universalis/agents/observation.py`

**Solution**: Create `MemoryBank` interface, update agents to use it

### 2. Scope Filter LanceDB Support ⚠️
**Problem**: `ScopeFilter` only has `build_chromadb_filter()`, needs LanceDB version

**Files to Fix**:
- `pyscrai/universalis/memory/scopes.py`
- `pyscrai/universalis/memory/lancedb_memory.py`

**Solution**: Add `build_lancedb_filter()` method

### 3. Map Markers Not Cleared ⚠️
**Problem**: Map markers accumulate, never cleared

**Files to Fix**:
- `pyscrai/forge/ui.py` (line ~280)

**Solution**: Track markers, clear before adding new ones

## 📋 Immediate Action Plan

### Week 1: Critical Fixes
- [ ] Fix agent memory integration (2-3 hours)
- [ ] Fix scope filtering (1-2 hours)
- [ ] Fix map markers (1 hour)
- [ ] Test basic simulation cycle (1 hour)

**Total**: ~1 day

### Week 2: Feature Completion
- [ ] Implement LangGraph interrupts for God Mode
- [ ] Complete terrain visualization
- [ ] Add state modification UI
- [ ] Create hybrid query examples

**Total**: ~3-4 days

### Week 3: Testing
- [ ] Unit tests for DuckDB/LanceDB components
- [ ] Integration tests for full cycle
- [ ] Performance benchmarks
- [ ] Scope filtering edge case tests

**Total**: ~4-5 days

### Week 4: Documentation
- [ ] API reference
- [ ] Spatial query examples
- [ ] God Mode guide
- [ ] Migration guide

**Total**: ~2-3 days

## ✅ What's Working

- ✅ DuckDB schema and spatial queries
- ✅ LanceDB memory system
- ✅ Async simulation engine
- ✅ Spatial constraint checking
- ✅ Basic NiceGUI interface
- ✅ Seeding and initialization

## ⚠️ What Needs Work

- ⚠️ Agent memory integration (type mismatch)
- ⚠️ Scope filtering (LanceDB support)
- ⚠️ Map visualization (marker management)
- ⚠️ LangGraph interrupts (node-level)
- ⚠️ Terrain overlay (WKT → GeoJSON conversion)
- ⚠️ Testing (no tests yet)

## 🔮 Future Enhancements

- Hybrid queries (LanceDB + DuckDB joins)
- Advanced visualization (heatmaps, paths)
- Performance optimizations
- Memory relationship graphs

## 📝 Quick Start for Fixes

### Fix #1: Agent Memory Interface

```python
# Create: pyscrai/universalis/memory/interface.py
from abc import ABC, abstractmethod
from typing import Sequence, Optional
from pyscrai.universalis.memory.scopes import MemoryScope, ScopeFilter

class MemoryBank(ABC):
    @abstractmethod
    def add(self, text: str, scope: MemoryScope, ...) -> bool:
        pass
    
    @abstractmethod
    def retrieve_associative(self, query: str, k: int, ...) -> Sequence[str]:
        pass
    # ... other methods
```

Then update agents to use `MemoryBank` instead of `ChromaDBMemoryBank`.

### Fix #2: Scope Filter

```python
# In scopes.py, add:
def build_lancedb_filter(self) -> Optional[str]:
    """Build LanceDB filter expression."""
    conditions = []
    # ... similar logic to ChromaDB but return SQL string
    return " AND ".join(conditions) if conditions else None
```

### Fix #3: Map Markers

```python
# In ui.py, track markers:
self._markers = []

# In _update_map_markers:
for marker in self._markers:
    marker.delete()
self._markers.clear()

# When adding:
marker = self.map_component.marker(...)
self._markers.append(marker)
```

## 🎯 Success Criteria

**Phase 1 Complete** when:
- ✅ Simulation runs end-to-end without errors
- ✅ Agents can retrieve memories correctly
- ✅ Map displays current state accurately

**Phase 2 Complete** when:
- ✅ God Mode works at workflow nodes
- ✅ Terrain visualization functional
- ✅ All UI features working

**Phase 3 Complete** when:
- ✅ >80% test coverage
- ✅ All tests passing
- ✅ Performance documented

## 📚 Resources

- Full analysis: `.cursor/plans/post_migration_analysis.md`
- Migration plan: `.cursor/plans/geoscrai_migration_plan_*.md`
- DuckDB Spatial docs: https://duckdb.org/docs/extensions/spatial
- LanceDB docs: https://lancedb.github.io/lancedb/

