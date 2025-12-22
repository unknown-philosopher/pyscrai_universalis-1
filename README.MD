# PyScrAI Universalis

**PyScrAI Universalis** is an agnostic linguistic simulation engine. It orchestrates "Sentient" Actors (powered by LLMs) within a deterministic turn-based environment to create dynamic "Generative Worlds."

* **The Heart:** [Mesa](https://www.google.com/search?q=https://mesa-agent.org/) manages the clock and simulation cycles.
* **The Brain:** [LangGraph](https://langchain-ai.github.io/langgraph/) manages the cognitive loop (Perception  Action  Adjudication).
* **The Bridge:** [FastAPI](https://fastapi.tiangolo.com/) connects the simulation logic to the UI and external triggers.

## 🛠 Tech Stack

* **Language:** Python 3.10+
* **Data:** MongoDB (World Ledger), ChromaDB (Vector Memory).
* **Validation:** Pydantic.
* **Observability:** Langfuse.
* **LLM Provider:** OpenRouter (configurable).

## 🚀 Quick Start

### 1. Prerequisites

* **Python 3.10+** installed.
* **MongoDB** running locally on port `27017`.
* **Docker** installed (for ChromaDB/Langfuse).

### 2. Environment Setup

Create a `.env` file in the root directory:

```bash
MONGO_URI="mongodb://localhost:27017/"
MONGO_DB_NAME="universalis_mongodb"
OPENROUTER_API_KEY="sk-..."
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
MODEL_NAME="xiaomi/mimo-v2-flash:free"

```

### 3. Installation

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

```

### 4. Start Infrastructure

Start the vector database (ChromaDB) using Docker:

```powershell
docker run -d --name universalis-chromadb -p 8000:8000 --volume "path/to/project/chroma-data:/data" chromadb/chroma:latest

```

*(Or use `start_services.bat` if configured)*.

### 5. Seed the World

Initialize the database with the "Alpha Scenario" (Cycle 0):

```bash
python pyscrai/src/seed_mongodb.py

```

*This resets the `world_states` collection and spawns initial actors/assets.*

### 6. Run the Engine

Launch the API server:

```bash
python pyscrai/src/main.py

```

The engine is now pulsing at `http://0.0.0.0:8000`.

---

## 🎮 Usage

**Advance the Simulation (Tick)**
Trigger a full Perception-Action-Adjudication cycle:

```bash
curl -X POST http://localhost:8000/simulation/tick

```

**Get World State**
Retrieve the current "Ground Truth" ledger:

```bash
curl http://localhost:8000/state

```

---

## 📂 Project Structure

| File | Description |
| --- | --- |
| `src/main.py` | **The Heartbeat.** Runs the FastAPI server and Mesa clock. |
| `src/graph_logic.py` | **The Mind.** Contains LangGraph nodes for Actor Perception and Archon Adjudication. |
| `src/schemas.py` | **The Laws.** Pydantic models defining `WorldState`, `Actor`, and `Asset`. |
| `src/seed_mongodb.py` | **The Genesis.** Resets the DB and creates the initial scenario. |
| `data/` | `data\chroma-data` Local storage for vector embeddings (mapped to Docker)
`data\mongo-data` Local storage for MongoDB database files. |