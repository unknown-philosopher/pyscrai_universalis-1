# PyScrAI Universalis - Developer Onboarding Guide

Welcome to **PyScrAI Universalis**, an agnostic linguistic simulation engine that enables multi-resolution agent-based simulations with memory-driven behavior and LLM-powered decision-making.

## Table of Contents

- [What is PyScrAI?](#what-is-pyscrai)
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Key Concepts](#key-concepts)
- [Running Simulations](#running-simulations)
- [Extending PyScrAI](#extending-pyscrai)
- [API Reference](#api-reference)
- [Contributing](#contributing)

## What is PyScrAI?

PyScrAI Universalis is a simulation engine that combines:

- **Multi-Resolution Agents**: Both "Macro" (strategic/organizational) and "Micro" (individual/social) agents coexist in the same simulation
- **Memory-Driven Behavior**: ChromaDB-backed associative memory with semantic retrieval, scoping, and pruning
- **LLM-Powered Adjudication**: The "Archon" uses language models to adjudicate actions and simulate outcomes
- **Fractal Design**: Agents can operate at different scales simultaneously, enabling complex emergent behaviors

### Use Cases

- **Crisis Simulation**: Model organizational responses to emergencies (wildfires, disasters)
- **Social Simulation**: Simulate individual agents with relationships, memories, and personal goals
- **Policy Analysis**: Test policy decisions in a simulated environment with realistic agent behavior
- **Training Scenarios**: Create dynamic training environments for decision-makers

## Architecture Overview

PyScrAI follows a **Triad Architecture** with three distinct layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    PyScrAI Universalis                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Architect   │  │  Universalis │  │    Forge     │      │
│  │ (Design Time)│  │ (Run Time)   │  │  (UI/API)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  • World Builder  │  • Simulation  │  • FastAPI Server     │
│  • Validator      │  • Archon      │  • Dashboard          │
│  • Seeder         │  • Agents      │  • Map/Visualization  │
│  • Pipeline       │  • Memory      │                       │
│                   │  • Engine      │                       │
└─────────────────────────────────────────────────────────────┘
```

### The Triad Layers

#### 1. **Architect** (`pyscrai/architect/`)
Design-time tools for creating and validating simulation worlds:
- **Builder**: Fluent API for creating `.WORLD` and `.SCENARIO` files
- **Validator**: Multi-level validation (schema, type, constraint, contextual)
- **Seeder**: Database initialization with scenario data
- **Pipeline**: Compiles `.WORLD` (base) + `.SCENARIO` (delta) → `WorldState`

#### 2. **Universalis** (`pyscrai/universalis/`)
Run-time simulation engine:
- **Engine**: Mesa-based simulation clock and cycle management
- **Archon**: Omniscient adjudicator using LangGraph + LLM
- **Agents**: Macro (strategic) and Micro (social) agent implementations
- **Memory**: ChromaDB-backed associative memory with scoping and pruning

#### 3. **Forge** (`pyscrai/forge/`)
UI/API layer for controlling and visualizing simulations:
- **App**: FastAPI REST endpoints for simulation control
- **Dashboard**: Unified viewport with Macro/Micro resolution toggle
- **Components**: Map, timeline, event log, status bar

## Quick Start

### Prerequisites

- Python 3.10+
- MongoDB (running locally or remote)
- (Optional) ChromaDB for persistent memory
- LLM API key (OpenRouter, OpenAI, or local proxy)

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
pip install -e pyscrai/
```

### Configuration

Copy `.example.env` to `.env` and configure:

```bash
# LLM Provider (OpenRouter example)
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
MODEL_NAME=xiaomi/mimo-v2-flash:free

# MongoDB
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=universalis_mongodb

# Optional: Langfuse for observability
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_SECRET_KEY=your_secret
LANGFUSE_HOST=http://localhost:3000
```

### Run Your First Simulation

```bash
# Seed the database with initial scenario
python -m pyscrai.main --seed

# Start the simulation server
python -m pyscrai.main --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Try:

- `GET /` - Health check
- `GET /state` - Current world state
- `POST /simulation/tick` - Advance one cycle
- `GET /simulation/info` - Simulation metadata

## Development Setup

### Project Structure

```
pyscrai/
├── architect/          # Design-time tools
│   ├── builder.py     # World/Scenario builders
│   ├── validator.py   # Multi-level validation
│   ├── seeder.py      # Database seeding
│   ├── pipeline.py    # Seed-to-state compilation
│   └── context_validator.py  # Historical validation
│
├── universalis/        # Run-time engine
│   ├── engine.py      # Mesa SimulationEngine
│   ├── archon/        # Adjudication logic
│   │   ├── interface.py
│   │   ├── adjudicator.py
│   │   └── feasibility.py
│   ├── agents/        # Agent implementations
│   │   ├── macro_agent.py
│   │   ├── micro_agent.py
│   │   ├── llm_controller.py
│   │   └── observation.py
│   ├── memory/        # Memory system
│   │   ├── associative.py  # ChromaDBMemoryBank
│   │   ├── scopes.py       # Memory scoping
│   │   ├── stream.py       # Event log
│   │   └── pruning.py      # Memory maintenance
│   └── environment/   # Physics/world simulation
│
├── forge/             # UI/API layer
│   ├── app.py         # FastAPI server
│   └── dashboard/     # Visualization components
│       ├── viewport.py
│       ├── macro_view.py
│       └── micro_view.py
│
├── data/              # Data storage
│   ├── schemas/       # JSON schemas
│   ├── worlds/        # .WORLD files
│   └── scenarios/     # .SCENARIO files
│
├── utils/             # Shared utilities
│   ├── logger.py
│   └── converters.py
│
└── main.py            # Bootloader entry point
```

### Running Tests

```bash
# Run all tests (when test suite is added)
pytest tests/

# Run with coverage
pytest --cov=pyscrai tests/
```

### Code Style

We follow PEP 8 with some exceptions:
- Use type hints for all function signatures
- Docstrings in Google style
- Maximum line length: 100 characters

## Key Concepts

### 1. World State

The `WorldState` is the "ground truth" of the simulation:

```python
from pyscrai.data.schemas.models import WorldState

world_state = WorldState(
    simulation_id="Alpha_Scenario",
    environment=Environment(cycle=0, time="08:00", weather="Clear"),
    actors={...},  # Dict[str, Actor]
    assets={...}   # Dict[str, Asset]
)
```

### 2. Agents

**Macro Agents** (`MacroAgent`): Strategic, organizational-level decision makers
- Manage multiple assets
- Make policy-level decisions
- Focus on objectives and resource allocation

**Micro Agents** (`MicroAgent`): Individual, socially-aware agents
- Have personal memories and relationships
- Make character-driven decisions
- Respond to emotional states and social context

### 3. The Archon

The Archon is the omniscient referee that:
- Processes actor intents
- Checks feasibility (budget, logistics, physical constraints)
- Adjudicates outcomes using LLM reasoning
- Generates rationales for traceability

### 4. Memory System

PyScrAI uses a hybrid memory architecture:

- **Associative Memory** (`ChromaDBMemoryBank`): Semantic retrieval using embeddings
- **Memory Scopes**: PUBLIC, PRIVATE, SHARED_GROUP to prevent cross-agent interference
- **Memory Stream**: Chronological event log for debugging and visualization
- **Memory Pruning**: Automatic relevance decay and consolidation

### 5. Resolution Toggle

The dashboard can switch between:
- **Macro View**: Strategic overview, metrics, policy impacts
- **Micro View**: Individual agent inspection, memories, relationships

## Running Simulations

### Basic Usage

```python
from pyscrai.universalis.engine import SimulationEngine
from pyscrai.universalis.archon.adjudicator import Archon
from pyscrai.architect.seeder import seed_simulation

# Seed the database
seed_simulation(simulation_id="MyScenario")

# Initialize engine with Archon
archon = Archon()
engine = SimulationEngine(sim_id="MyScenario")
engine.attach_archon(archon)

# Run cycles
for _ in range(10):
    result = engine.step()
    print(f"Cycle {result['cycle']}: {result['summary']}")
```

### Creating Custom Scenarios

```python
from pyscrai.architect.builder import ScenarioBuilder

builder = ScenarioBuilder("my_scenario", "My Custom Scenario", world_id="base_world")
builder.set_description("A custom scenario for testing")
builder.set_initial_conditions(cycle=0, time="06:00", weather="Rainy")
builder.add_actor(
    actor_id="Actor_Mayor",
    role="City Mayor",
    description="Responsible for city-wide decisions",
    resolution="macro",
    objectives=["Protect citizens", "Manage resources"]
)
builder.add_asset(
    asset_id="Truck_01",
    name="Emergency Response Vehicle",
    asset_type="Ground Unit",
    lat=34.05,
    lon=-118.25
)
builder.save()
```

### Using the API

```python
import requests

# Start simulation
response = requests.post("http://localhost:8000/simulation/tick")
print(response.json())
# {"cycle": 1, "status": "Adjudicated", "summary": "..."}

# Get current state
state = requests.get("http://localhost:8000/state").json()
print(f"Cycle: {state['environment']['cycle']}")
```

## Extending PyScrAI

### Adding Custom Constraints

Extend the `FeasibilityEngine`:

```python
from pyscrai.universalis.archon.feasibility import FeasibilityEngine, Constraint, ConstraintType

engine = FeasibilityEngine()

# Add custom constraint
def check_custom_constraint(intent: str, world_state: WorldState) -> bool:
    # Your validation logic
    return True

engine.register_constraint(Constraint(
    name="custom_check",
    constraint_type=ConstraintType.POLICY,
    check_fn=check_custom_constraint,
    error_message="Custom constraint violated"
))
```

### Creating Custom Agent Types

```python
from pyscrai.universalis.agents.macro_agent import MacroAgent, MacroAgentConfig
from pyscrai.data.schemas.models import Actor

class CustomMacroAgent(MacroAgent):
    def generate_intent(self, world_state, context=None):
        # Override with custom logic
        intent = super().generate_intent(world_state, context)
        # Modify intent...
        return intent
```

### Adding Dashboard Components

```python
from pyscrai.forge.dashboard.components import MapComponent

map_component = MapComponent()
map_component.update_from_world_state(world_state)
map_data = map_component.get_render_data()
```

## API Reference

### Core Classes

- `SimulationEngine`: Main simulation engine
- `Archon`: Adjudication system
- `MacroAgent` / `MicroAgent`: Agent implementations
- `ChromaDBMemoryBank`: Memory storage
- `WorldBuilder` / `ScenarioBuilder`: World creation tools
- `UnifiedViewport`: Dashboard viewport

### Key Functions

- `seed_simulation()`: Initialize database
- `validate_world()` / `validate_scenario()`: Validation
- `create_viewport()`: Dashboard initialization

See docstrings in source files for detailed API documentation.

## Contributing

### Development Workflow

1. **Create a feature branch**: `git checkout -b feature/my-feature`
2. **Make changes**: Follow code style and add tests
3. **Test locally**: Ensure all tests pass
4. **Submit PR**: Include description of changes

### Areas for Contribution

- **New Agent Types**: Implement specialized agent behaviors
- **Memory Strategies**: Alternative memory implementations
- **Visualization**: Enhanced dashboard components
- **Validation Rules**: Additional constraint validators
- **Documentation**: Examples, tutorials, API docs

### Questions?

- Check existing issues on GitHub
- Review the master development plan in `.cursor/plans/`
- Examine example code in `pyscrai_deprecated/` for reference

## License

[Add your license here]

## Acknowledgments

PyScrAI Universalis integrates concepts from:
- **Concordia**: Memory and LLM abstraction patterns
- **Mesa**: Agent-based modeling framework
- **LangGraph**: Workflow orchestration
- **ChromaDB**: Vector database for semantic memory

---

**Welcome to PyScrAI!** Start by running `python -m pyscrai.main --seed` and exploring the codebase. Happy simulating! 🚀

