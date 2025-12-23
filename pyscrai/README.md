# GeoScrAI / PyScrAI Universalis - Developer Guide

Welcome to **GeoScrAI** (formerly PyScrAI Universalis), a spatial linguistic simulation engine that enables multi-resolution agent-based simulations with memory-driven behavior, LLM-powered decision-making, and real-time geographic constraints.

## Table of Contents

- [What is GeoScrAI?](#what-is-geoscrai)
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Key Concepts](#key-concepts)
- [Running Simulations](#running-simulations)
- [Extending GeoScrAI](#extending-geoscrai)
- [API Reference](#api-reference)

## What is GeoScrAI?

GeoScrAI is a "Data-Driven Monolith" that combines:

- **Spatial State Management**: DuckDB with spatial extension for geographic queries
- **Semantic Memory**: LanceDB for vector-based associative memory with Arrow integration
- **Multi-Resolution Agents**: Both "Macro" (strategic) and "Micro" (individual) agents
- **LLM-Powered Adjudication**: The "Archon" uses language models with spatial context
- **Real-Time UI**: NiceGUI-based interface with live map updates

### Key Differences from Previous Architecture

| Feature | Old (MongoDB/ChromaDB) | New (DuckDB/LanceDB) |
|---------|------------------------|----------------------|
| State Storage | MongoDB (Document Store) | DuckDB (OLAP SQL + Spatial) |
| Memory | ChromaDB (HTTP/Local) | LanceDB (Native Vector) |
| Physics | Python constraint functions | SQL spatial queries |
| UI | FastAPI + Flet (Polling) | NiceGUI (WebSocket) |
| Loop | Mesa (ABM Framework) | Asyncio (Interruptible) |

## Architecture Overview

GeoScrAI follows a **Triad Architecture** with three distinct layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    GeoScrAI Universalis                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Architect   │  │  Universalis │  │    Forge     │      │
│  │ (Design Time)│  │ (Run Time)   │  │  (UI/API)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  • Schema Init   │  • Simulation  │  • NiceGUI App        │
│  • Seeder        │  • Archon      │  • Map Visualization  │
│  • Validator     │  • Agents      │  • God Mode Controls  │
│  • Builder       │  • Memory      │                       │
│                  │  • DuckDB State│                       │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   DuckDB    │────▶│  WorldState  │────▶│   Archon    │
│  (Spatial)  │     │  (Pydantic)  │     │ (LangGraph) │
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                    │
       │                   │                    ▼
       │                   │            ┌─────────────┐
       │                   │            │   Agents    │
       │                   │            │ (Macro/Micro)│
       │                   │            └─────────────┘
       │                   │                    │
       ▼                   ▼                    ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   LanceDB   │◀────│   Memory     │◀────│   Intents   │
│  (Vectors)  │     │   Stream     │     │             │
└─────────────┘     └──────────────┘     └─────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- No external databases required (DuckDB and LanceDB run embedded)
- LLM API key (OpenRouter, OpenAI, or local)

### Installation

```bash
# Clone the repository
cd pyscrai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install PyScrAI in editable mode
pip install -e .
```

### Configuration

Copy `.example.env` to `.env` and configure:

```bash
# LLM Provider (OpenRouter example)
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
MODEL_NAME=xiaomi/mimo-v2-flash:free

# Database (optional - defaults to local files)
DUCKDB_PATH=./database/geoscrai.duckdb
LANCEDB_PATH=./database/lancedb

# UI
HOST=0.0.0.0
PORT=8080
```

### Run Your First Simulation

```bash
# Seed and start with UI
python -m pyscrai.main --seed

# Or run in headless mode
python -m pyscrai.main --seed --no-ui --cycles 10
```

The UI will be available at `http://localhost:8080`.

## Project Structure

```
pyscrai/
├── architect/           # Design-time tools
│   ├── builder.py      # World/Scenario builders
│   ├── validator.py    # Multi-level validation
│   ├── seeder.py       # DuckDB seeding
│   ├── schema_init.py  # Database initialization
│   └── pipeline.py     # Seed-to-state compilation
│
├── universalis/         # Run-time engine
│   ├── engine.py       # Async SimulationEngine
│   ├── state/          # DuckDB state management
│   │   └── duckdb_manager.py  # Spatial queries
│   ├── archon/         # Adjudication logic
│   │   ├── adjudicator.py     # LangGraph workflow
│   │   ├── feasibility.py     # Constraint checking
│   │   └── spatial_constraints.py  # SQL-based physics
│   ├── agents/         # Agent implementations
│   │   ├── macro_agent.py
│   │   ├── micro_agent.py
│   │   └── llm_provider.py
│   └── memory/         # Memory system
│       ├── lancedb_memory.py  # Vector memory
│       ├── associative.py     # ChromaDB (legacy)
│       ├── scopes.py
│       └── stream.py
│
├── forge/              # UI layer
│   └── ui.py           # NiceGUI application
│
├── data/               # Data storage
│   └── schemas/
│       ├── models.py   # Pydantic models
│       └── schema.sql  # DuckDB schema
│
├── config.py           # Configuration
└── main.py             # Entry point
```

## Key Concepts

### 1. Spatial State (DuckDB)

World state is stored in DuckDB with spatial extension:

```sql
-- Entities table with GEOMETRY column
SELECT * FROM entities 
WHERE ST_DWithin(geometry, ST_Point(-118.25, 34.05), 0.1);

-- Check path blockage
SELECT name FROM terrain 
WHERE passable = FALSE 
  AND ST_Intersects(geometry, ST_MakeLine(...));
```

### 2. Semantic Memory (LanceDB)

Associative memory with vector search and Arrow integration:

```python
from pyscrai.universalis.memory import LanceDBMemoryBank

memory = LanceDBMemoryBank(simulation_id="MyScenario")
memory.add("Observed fire spreading north", scope=MemoryScope.PRIVATE)
relevant = memory.retrieve_associative("fire movement", k=5)
```

### 3. Spatial Constraints

Physics enforced by database queries, not Python code:

```python
from pyscrai.universalis.archon import SpatialConstraintChecker

checker = SpatialConstraintChecker()

# Check if movement is feasible
result = checker.validate_movement(
    entity_id="Truck_01",
    target_lon=-118.30,
    target_lat=34.10
)
# Returns: (passed: bool, [constraint_results])
```

### 4. God Mode (Interrupts)

Simulation can be paused between phases:

```python
engine.pause()  # Pause at current cycle
# Inspect/modify state
engine.resume()  # Continue
```

### 5. Resolution Toggle

Agents operate at different scales:
- **Macro Agents**: Strategic, organizational-level
- **Micro Agents**: Individual, social-level with relationships

## Running Simulations

### With UI

```bash
python -m pyscrai.main --seed
```

### Headless Mode

```bash
python -m pyscrai.main --no-ui --cycles 100
```

### Programmatic Usage

```python
import asyncio
from pyscrai.universalis.engine import SimulationEngine
from pyscrai.universalis.archon import Archon
from pyscrai.architect.seeder import seed_simulation

# Seed database
seed_simulation(simulation_id="MyScenario")

# Initialize
archon = Archon()
engine = SimulationEngine(sim_id="MyScenario")
engine.attach_archon(archon)

# Run cycles
async def run():
    for _ in range(10):
        result = await engine.async_step()
        print(f"Cycle {result['cycle']}: {result['summary']}")

asyncio.run(run())
```

## Extending GeoScrAI

### Adding Custom Terrain

```python
from pyscrai.data.schemas.models import Terrain, TerrainType

terrain = Terrain(
    terrain_id="custom_mountains",
    name="Rocky Mountains",
    terrain_type=TerrainType.MOUNTAINS,
    geometry_wkt="POLYGON((-105 39, -104 39, -104 40, -105 40, -105 39))",
    movement_cost=3.0,
    passable=True
)

state_manager.add_terrain(terrain)
```

### Custom Spatial Constraints

```python
from pyscrai.universalis.archon.feasibility import FeasibilityEngine, Constraint

engine = FeasibilityEngine()

def check_weather_constraint(intent: str, world_state) -> bool:
    if "fly" in intent.lower() and world_state.environment.weather == "Storm":
        return False
    return True

engine.register_constraint(Constraint(
    name="weather_flying",
    constraint_type=ConstraintType.PHYSICAL,
    check_fn=check_weather_constraint,
    error_message="Cannot fly in storm conditions"
))
```

### Adding Dashboard Components

The NiceGUI app can be extended in `pyscrai/forge/ui.py`:

```python
@ui.page('/custom')
def custom_page():
    with ui.card():
        ui.label("Custom Analysis")
        # Add custom visualizations
```

## API Reference

### Core Classes

- `SimulationEngine`: Async simulation engine with DuckDB backend
- `DuckDBStateManager`: Spatial state storage and queries
- `LanceDBMemoryBank`: Vector memory with Arrow integration
- `Archon`: LangGraph-based adjudication with spatial context
- `SpatialConstraintChecker`: SQL-based physics validation

### Key Functions

- `seed_simulation()`: Initialize DuckDB with scenario
- `init_database()`: Create schema and load extensions
- `create_app()` / `run_app()`: NiceGUI application

## Migration Notes

If migrating from the MongoDB/ChromaDB version:

1. **No external services needed**: DuckDB and LanceDB run embedded
2. **Data migration**: Use `seed_simulation()` to create new data
3. **Constraint changes**: Update custom constraints to use spatial queries
4. **UI changes**: FastAPI endpoints replaced by NiceGUI pages

## License

[Add your license here]

---

**Welcome to GeoScrAI!** Start with `python -m pyscrai.main --seed` and explore the spatial simulation capabilities.
