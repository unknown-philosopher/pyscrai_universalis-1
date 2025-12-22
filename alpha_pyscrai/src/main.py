import mesa
from fastapi import FastAPI
import uvicorn
from datetime import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Import the cognitive bridge
from graph_logic import simulation_brain

# Import local schemas
from schemas import WorldState, Environment

# Load env variables
load_dotenv()

app = FastAPI(title="PyScrAI Universalis Engine")

# --- DATABASE CONNECTION ---
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
db_name = os.getenv("MONGO_DB_NAME", "universalis_mongodb")

client = MongoClient(mongo_uri)
db = client[db_name]
states_collection = db["world_states"]

# --- MESA 3.0 MODEL (The Heartbeat) ---
class SimulationEngine(mesa.Model):
    def __init__(self, sim_id: str):
        super().__init__()
        self.sim_id = sim_id
        # Sync cycle count from DB if restarting, else 0
        latest = states_collection.find_one(
            {"simulation_id": sim_id}, 
            sort=[("environment.cycle", -1)]
        )
        self.steps = latest["environment"]["cycle"] if latest else 0
        print(f"Engine {self.sim_id} Initialized at Cycle {self.steps}")

    def save_adjudicated_state(self, world_state: WorldState):
        """Serializes the final adjudicated state from the Mind and pushes to MongoDB"""
        # Ensure the timestamp is current before saving
        world_state.last_updated = datetime.now()
        
        # Convert Pydantic model to dict for MongoDB
        states_collection.insert_one(world_state.model_dump())
        print(f"✅ Cycle {world_state.environment.cycle} adjudicated and saved to MongoDB.")

    def step(self):
        """
        The Master Tick:
        1. Advances the temporal pulse (Mesa)
        2. Triggers the cognitive bridge (LangGraph)
        3. Persists the ground truth (MongoDB)
        """
        # 1. Advance Mesa internal step counter
        # In Mesa 3.0+, manual increment is safest if not using their new Runner
        self.steps += 1 
        
        # 2. Fetch the previous state to act as the baseline
        # (Or create a fresh one if it's cycle 1)
        latest_doc = states_collection.find_one(
            {"simulation_id": self.sim_id},
            sort=[("environment.cycle", -1)]
        )
        
        if latest_doc:
            # Rehydrate Pydantic object from DB
            current_world_state = WorldState(**latest_doc)
            # Update cycle number for the new tick
            current_world_state.environment.cycle = self.steps
        else:
            # Fallback for fresh start (though Seed DB is preferred)
            current_world_state = WorldState(
                simulation_id=self.sim_id,
                environment=Environment(
                    cycle=self.steps, 
                    time=datetime.now().strftime("%H:%M")
                ),
                actors={},
                assets={}
            )

        # 3. Invoke the Cognitive Bridge (The Mind)
        print(f"--- Triggering LangGraph for Cycle {self.steps} ---")
        brain_input = {
            "world_state": current_world_state, 
            "actor_intents": [], 
            "archon_summary": ""
        }
        
        # The graph executes and returns the modified state
        final_output = simulation_brain.invoke(brain_input)
        
        # 4. Save the adjudicated result to the Ledger (MongoDB)
        self.save_adjudicated_state(final_output["world_state"])
        
        return {
            "cycle": self.steps, 
            "status": "Adjudicated", 
            "summary": final_output.get("archon_summary", "No summary provided")
        }

# --- ENGINE INITIALIZATION ---
sim_engine = SimulationEngine(sim_id="Alpha_Scenario")

# --- API ENDPOINTS ---

@app.get("/")
async def root():
    return {"message": "PyScrAI Universalis Engine is Pulsing"}

@app.post("/simulation/tick")
async def run_tick():
    """Manually trigger a full Perception-Action-Adjudication cycle"""
    return sim_engine.step()

@app.get("/state")
async def get_state():
    """Fetch the latest ground truth from the MongoDB ledger"""
    latest = states_collection.find_one(
        {"simulation_id": sim_engine.sim_id},
        sort=[("environment.cycle", -1)]
    )
    if latest:
        latest.pop("_id") # Remove Mongo's internal ID
        return latest
    return {"error": "No state found in ledger"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)