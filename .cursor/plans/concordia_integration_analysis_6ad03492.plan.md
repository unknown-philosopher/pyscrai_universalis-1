---
name: Concordia Integration Analysis
overview: Analyze PyScrAI Universalis to identify beneficial integrations with Concordia's framework components, focusing on language model abstractions, memory systems, agent architecture, and game master patterns.
todos:
  - id: analyze-llm-integration
    content: Analyze Concordia LanguageModel interface and create adapter for LangChain/OpenRouter
    status: pending
  - id: analyze-memory-integration
    content: Evaluate Concordia AssociativeMemoryBank vs ChromaDB for PyScrAI memory needs
    status: pending
  - id: analyze-component-system
    content: Assess component-based agent architecture integration with Mesa/LangGraph workflow
    status: pending
  - id: document-integration-plan
    content: Create detailed integration plan with file-by-file changes and migration strategy
    status: pending
    dependencies:
      - analyze-llm-integration
      - analyze-memory-integration
      - analyze-component-system
---

# Concordia Framework Integration Analysis

for PyScrAI Universalis

## Executive Summary

PyScrAI Universalis is a turn-based simulation engine using Mesa (simulation clock), LangGraph (cognitive loop), and FastAPI (API layer). Concordia provides a mature agent framework with component-based architecture, sophisticated memory systems, and structured agent lifecycles. Several integration opportunities exist that could enhance PyScrAI's capabilities.

## Current PyScrAI Architecture

**Core Stack:**

- **Mesa 3.0**: Simulation clock and cycle management
- **LangGraph**: Perception → Action → Adjudication workflow
- **FastAPI**: REST API for simulation control
- **MongoDB**: World state persistence (ground truth ledger)
- **ChromaDB**: Planned for vector memory (not yet implemented)
- **LangChain + OpenRouter**: LLM provider via ChatOpenAI
- **Langfuse**: Observability/tracing

**Current Limitations:**

1. Simple prompt-based actors without persistent memory
2. No associative memory retrieval (ChromaDB mentioned but unused)
3. Basic observation handling (just appends to global_events)
4. No structured agent lifecycle or component system
5. Direct LLM calls without abstraction layer

## Concordia Capabilities

**Key Features:**

1. **Component-Based Agent Architecture**: Modular, composable agent behaviors
2. **Associative Memory System**: Vector-based memory with semantic retrieval
3. **Structured Agent Lifecycle**: PRE_ACT → POST_ACT → UPDATE phases
4. **Observation Management**: Sophisticated observation-to-memory pipeline
5. **Language Model Abstraction**: Pluggable LLM interface supporting multiple providers
6. **Game Master Pattern**: Structured environment simulation (aligns with PyScrAI's "Archon")
7. **State Management**: Checkpointing and state serialization

## Integration Opportunities

### 1. Language Model Abstraction Layer

**Current State:** PyScrAI directly uses `ChatOpenAI` from LangChain with OpenRouter.**Benefit:** Create a Concordia-style `LanguageModel` adapter that wraps LangChain/OpenRouter, providing:

- Consistent interface for switching providers
- Built-in retry logic and error handling
- Token usage tracking
- Temperature/parameter management

**Files to Modify:**

- `pyscrai/src/graph_logic.py`: Replace direct `ChatOpenAI` usage
- Create `pyscrai/src/llm_provider.py`: New abstraction layer

**Integration Approach:**

- Create `LangChainOpenRouterModel` class implementing Concordia's `LanguageModel` interface
- Wrap existing `ChatOpenAI` instance with Langfuse callbacks
- Maintain backward compatibility with current LangGraph nodes

### 2. Associative Memory System

**Current State:** ChromaDB is mentioned in docs but not implemented. Actors have no persistent memory.**Benefit:** Integrate Concordia's `AssociativeMemoryBank` or adapt it for ChromaDB:

- Semantic memory retrieval for actors
- Context-aware action generation
- Long-term memory persistence across cycles

**Files to Modify:**

- `pyscrai/src/graph_logic.py`: Add memory retrieval to `actor_perception_node`
- Create `pyscrai/src/memory.py`: Memory management module
- Optionally integrate with ChromaDB backend

**Integration Approach:**

- Use Concordia's `AssociativeMemoryBank` with sentence transformers
- OR create ChromaDB-backed adapter implementing same interface
- Store actor observations and decisions in memory
- Retrieve relevant memories during perception phase

### 3. Component-Based Agent Architecture

**Current State:** Actors are simple dictionaries with role/description. Actions are direct LLM prompts.**Benefit:** Adopt Concordia's component system for richer agent behaviors:

- Modular agent capabilities (memory, planning, relationships)
- Structured observation processing
- Context-aware action generation
- Phase-based lifecycle management

**Files to Modify:**

- `pyscrai/src/schemas.py`: Extend `Actor` model
- `pyscrai/src/graph_logic.py`: Refactor `actor_perception_node` to use components
- Create `pyscrai/src/agents/`: New agent module structure

**Integration Approach:**

- Create `PyScrAIActor` class extending Concordia's `EntityAgent`
- Implement custom components for PyScrAI-specific needs (asset management, objectives)
- Keep Mesa integration for simulation timing
- Maintain LangGraph workflow but enhance nodes with component system

### 4. Enhanced Observation System

**Current State:** Observations are simple strings appended to `global_events`.**Benefit:** Use Concordia's observation components:

- Structured observation processing
- Automatic memory integration
- Filtering and prioritization
- Historical observation retrieval

**Files to Modify:**

- `pyscrai/src/graph_logic.py`: Enhance observation handling
- Integrate with memory system (see #2)

**Integration Approach:**

- Use `ObservationToMemory` component pattern
- Implement `LastNObservations` for actor context
- Store observations in associative memory

### 5. Game Master / Archon Enhancement

**Current State:** Archon is a simple LLM prompt that adjudicates actor intents.**Benefit:** Leverage Concordia's Game Master patterns:

- Structured event resolution
- Multi-step reasoning chains
- Consistent world state management
- Better integration with agent observations

**Files to Modify:**

- `pyscrai/src/graph_logic.py`: Enhance `archon_adjudication_node`
- Create `pyscrai/src/game_master.py`: Structured GM module

**Integration Approach:**

- Adapt Concordia's `GenericGameMaster` patterns
- Maintain PyScrAI's turn-based adjudication model
- Add structured reasoning steps for complex scenarios

## Recommended Integration Priority

### Phase 1: Foundation (High Impact, Low Risk)

1. **Language Model Abstraction** - Clean interface, easy to test
2. **Basic Memory System** - Use Concordia's `AssociativeMemoryBank` directly

### Phase 2: Enhancement (Medium Impact, Medium Risk)

3. **Observation Components** - Improve actor context awareness
4. **Component-Based Actors** - Start with memory component, expand gradually

### Phase 3: Advanced (High Impact, Higher Risk)

5. **Full Agent Architecture** - Complete component system adoption
6. **Game Master Patterns** - Structured adjudication system

## Implementation Considerations

**Compatibility:**

- Concordia uses pandas DataFrames for memory; PyScrAI uses MongoDB
- Need adapter layer for state persistence
- Mesa's step-based model aligns with Concordia's phase system

**Dependencies:**

- Concordia requires sentence-transformers for embeddings
- May need to add numpy/pandas if not already present
- Consider dependency management (Concordia is large)

**Architecture:**

- Keep Mesa for simulation timing (works well)
- Keep LangGraph for workflow (can be enhanced with components)
- Keep FastAPI for API (no changes needed)
- Enhance actors with Concordia patterns incrementally

## Questions to Resolve

1. **Memory Backend**: Use Concordia's pandas-based memory or adapt for ChromaDB?