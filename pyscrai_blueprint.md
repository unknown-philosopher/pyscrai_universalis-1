# PyScrAI Universalis

### Architecture Overview

**Core Technologies**
- **Python**: Main programming language, UV for package mangement.
- **Pydantic**: Data validation and schema enforcement.
- **LangChain & LangGraph**: Agent logic and orchestration.
- **Langfuse**: LLM trace observability.
- **FastAPI**: API bridge between UI and simulation.
- **Mesa**: Simulation clock and turn management.

**User Interface**
- **Flet**: Desktop UI framework.
- **Flet-Map**: Spatial rendering (future, not MVP).

**Data & Storage**
- **MongoDB**: World state ledger.
- **ChromaDB**: Actor memory/history.
---

| Category         | Component         | Description                                                        |
|------------------|------------------|--------------------------------------------------------------------|
| **UI**           | Flet & Flet-Map  | Python desktop app with interactive spatial rendering.              |
| **Communication**| FastAPI          | Fast bridge between UI and simulation engine.                       |
| **Logic Heart**  | Mesa             | Deterministic clock for turn-based cycles.                          |
| **Orchestrator** | LangGraph        | Manages cycle: Perception → Action → Adjudication.                  |
| **"Minds"**      | LangChain Agents | Sentient actors using natural language.                             |
| **Judge**        | The Archon       | Referees intents, simulates environment.                            |
| **State Store**  | MongoDB          | JSON ledger for world state.                                        |
| **Memory Store** | ChromaDB         | Actor RAG history/Long term Memory.                                                  |
| **Monitor**      | Langfuse         | Observability for LLM decisions.                                    |

---

### Component Responsibilities

| Component   | Responsibility                                                    | Technical Implementation            |
|-------------|-------------------------------------------------------------------|-------------------------------------|
| **The Archon**  | Referee, environment simulation, state validation.            | LangGraph / Pydantic                |
| **Actors**      | Sentient agents, strategy via RAG.                            | LangChain / ChromaDB                |
| **Assets**      | Controlled units/resources.                                   | MongoDB sub-objects                 |
| **Chronos**     | Master clock, cycle management.                               | Mesa / FastAPI                      |
| **Ledger**      | Cycle snapshots, semantic history.                            | MongoDB / ChromaDB                  |
                    |

## Overview
The Agnostic Linguistic Simulation Engine is a multi-layered framework that transforms natural language configurations into dynamic, turn-based "Generative World" experiences. At its core, Mesa provides the deterministic temporal heartbeat, triggering a high-level orchestration loop managed by LangGraph. Built upon utilization of a speciality Architect Agent (Langchain). 

### Scenario Fabrication & Simulation Initialization
The **Scenario Fabrication** phase is the preparatory gateway where abstract natural language concepts are transformed into a validated, machine-readable simulation seed. It begins with the user engaging a specialized **Architect Agent**, which utilizes a **Pydantic-driven** interactive dialogue to extract essential parameters such as geographic scale, temporal resolution, and the specific roster of **Actors** and **Assets**. Once the narrative goals are established, the Architect generates a structured JSON configuration that defines the initial "Ground Truth" for the **Archon** and seeds the **MongoDB** state store. This fabrication process also involves initializing the **ChromaDB** vector space with a "World Primer"—a foundational set of embeddings that provide historical context and specific mission objectives—ensuring that when **Mesa** triggers the first cycle, every entity is properly grounded in the linguistic and physical reality of the chosen scenario.

#### **The Fabrication Workflow**
1. **Narrative Input**: User describes the scenario (e.g., "A wildfire containment effort in the Sierra Nevada").
2. **Architect Interview**: The agent asks clarifying questions to define the **Resolution Lock** and unit capacities.
3. **JSON Generation**: The system produces a master schema-compliant file containing environment variables, actor personas, and asset attributes.
4. **Seed & Validation**: The **Archon** performs a dry-run validation of the JSON to ensure logic consistency.
5. **Initialization**: **MongoDB** stores the cycle-zero state, and **ChromaDB** is primed with the scenario's backstory.

## Operational Flow & Logic
Asynchronous Perception: In each cycle, sentient Actors (powered by LangChain) perceive the world through an async-first FastAPI layer. They retrieve real-time state data from MongoDB and deep historical context from ChromaDB, utilizing temporal metadata filtering to ensure RAG results are prioritized by relevance to the current cycle.

Strategic Intent: Actors can communicate, interact, or issue commands to each other and/or to their subordinate Assets—non-sentient entities (e.g., battalions, trucks) (Given the Scenario) that becomes managed via a Command Buffer pattern. These intents are strictly validated against a root Pydantic Master Schema before being passed to adjudication.

Unified Adjudication: The Archon acts as the centralized judge, executing a dual-pass logic: first simulating environmental shifts (such as fire spread or storm intensification) and then resolving actor conflicts to maintain a consistent "Ground Truth".

Persistence & Observability: The final cycle state is committed to MongoDB, while a linguistic summary is logged to ChromaDB for future recall. The entire process is mirrored in a modern Flet desktop interface—featuring real-time Flet-Map spatial rendering—while Langfuse provides comprehensive observability, tracing every linguistic decision with unique cycle tags for full auditability.