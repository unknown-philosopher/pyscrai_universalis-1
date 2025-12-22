# PyScrAI 

In PyScrAI, the user doesn't "joystick" a character; the user **injects intent** or **alters context**, and the Agent (supported by the LLM) determines how to execute that within their social reality.

### 1. The Spectrum of Resolution

We are moving away from "Classes" (Macro vs. Micro) and toward **"Resolution."**

* **The .WORLD File (The Bounds):** Defines the maximum resolution of data available.
* *Example:* The `US_2023.world` file contains data down to the county level for the whole country, but perhaps down to specific neighborhoods or "key agent" networks for specific active regions. It sets the "Physics" of the simulation (economic flows, weather patterns, social graph propagation rules).

* **The .SCENARIO File (The Lens):** Sets the active focus.

* **Macro Resolution:** The user functions as a "Node of Influence," operating at the layer of grand strategy and systemic guidance. In this mode, you do not issue tactical unit commands; instead, you formulate and enact broad Policy and Directives. The Archon—the simulation's executive logic layer—interprets these directives, cross-referencing them with environmental feasibility, geopolitical provenance, and competing external factors. The Archon then executes the "moves" on the world stage, returning the consequences to the user via high-fidelity systemic metrics such as Approval Ratings, GDP fluctuations, and Casualty Reports. This creates a realistic "fog of leadership" where intent must navigate the friction of reality.
* **Micro Resolution (AgentSociety Style):** The user is an "Observer/Participant." You don't "play" the character like a video game. You view their **Memory Stream**, see their **Current Plan**, and influence their **Reflections**.
* *Action:* Instead of "Press 'A' to Attack," the user might input a high-level directive: *"Prioritize finding insulin for your grandmother."* The Universalis Engine then calculates how the Agent attempts to achieve this based on their personality, relationships, and the environment.

---

### 2. PyScrAI: Repository Structure (v0.1)

Keeping "Flow over Complexity" in mind, this structure enforces the separation of the Triad (Architect, Universalis, Forge) while providing a shared space for the data that binds them.

```text
pyscrai/
├── main.py                   # The application entry point (bootloader)
├── config.py                 # Global configuration (paths, API keys, resolution settings)
├── requirements.txt          # Python dependencies
│
├── architect/                # [Design Time] Tools for creating Worlds/Scenarios
│   ├── __init__.py
│   ├── builder.py            # Logic for compiling raw data into .WORLD format
│   ├── seeder.py             # Tools to ingest real-world data (Census, USGS, etc.)
│   └── validator.py          # Ensures .WORLD files don't break simulation rules
│
├── universalis/              # [Run Time] The Simulation Engine
│   ├── __init__.py
│   ├── engine.py             # The main simulation loop (The "Heartbeat")
│   ├── memory/               # The "Concordia" style memory systems
│   │   ├── associative.py    # Vector database logic for agent memories
│   │   └── stream.py         # The chronological log of events
│   ├── agents/               # Logic for the entities
│   │   ├── llm_controller.py # Interface with the LLM (OpenAI/Anthropic/Local)
│   │   ├── macro_agent.py    # Logic for Organizations/Nations
│   │   └── micro_agent.py    # Logic for Individuals (Social/Routine based)
│   └── environment/          # Physics and World State
│       ├── weather.py
│       └── logistics.py
│
├── forge/                    # [Run Time] The UI / Visualization
│   ├── __init__.py
│   ├── app.py                # Main UI application wrapper
│   ├── dashboard/            # The 2D overlay elements
│   │   ├── macro_view.py     # Graphs, Heatmaps, Reports
│   │   └── micro_view.py     # Agent Inspection, Dialogue History, Memory visualizer
│   └── map/                  # The Interactive Map renderer
│       ├── renderer.py
│       └── layers.py         # Layers for Weather, Population, Traffic, etc.
│
├── data/                     # Storage for Simulation Files
|   |- - database/            # Database storage (chromadb, mongodb, etc)
│   ├── schemas/              # JSON/YAML schemas defining valid structure
│   ├── worlds/               # .WORLD files (The Static Base)
│   │   └── us_2023.world
│   └── scenarios/            # .SCENARIO files (The Dynamic Overlay)
│       ├── crisis_macro.scn
│       └── crisis_micro.scn
│
├── utils/                    # Shared helper functions
│   ├── logger.py
│   └── converters.py         # Helpers to convert Lat/Lon to Grid, etc.
│
└── tests/                    # Unit and Integration tests
    ├── test_engine.py
    └── test_agents.py

```

### 3. Key Structural Decisions Explained

* **`universalis/memory/`**: This directory serves as the cognitive backbone of the simulation. Following the AgentSociety/Concordia model, this module manages a hybrid memory architecture critical to the Micro engine. It distinguishes between Archival Memory (a vector database for long-term storage and retrieval) and Active Context (a "tight," running summarization of immediate relevance kept with the actor). Crucially, this system allows for Emergent Character Evolution: by leveraging the inherent stochastic nature of LLMs (controlled hallucinations), agents can organically develop new traits or emphasize specific memories based on their personas. This introduces a degree of randomness that mimics human subjectivity, ensuring agents are not just static data points but evolving entities.
* **`data/schemas/`**: Since the Architect creates files and Universalis reads them, we need strict Schemas (likely JSON Schema or Pydantic models) to ensure they speak the same language.
* **`agents/llm_controller.py`**: We abstract the LLM calls here. This allows us to swap models easily (e.g., use GPT-4 for the "President" agent but a cheaper/faster local Llama-3 model for "Civilian #402").
