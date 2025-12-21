from pymongo import MongoClient
from datetime import datetime
from src.schemas import WorldState, Environment, Actor, Asset
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to Mongo
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
db_name = os.getenv("MONGO_DB_NAME", "universalis_mongodb")
client = MongoClient(mongo_uri)
db = client[db_name]
collection = db["world_states"]

def seed_simulation():
    print("Seeding Database for Scenario: Alpha_Scenario...")
    
    # Define Initial Scenario State (Cycle 0)
    initial_state = WorldState(
        simulation_id="Alpha_Scenario",
        environment=Environment(
            cycle=0, 
            time="06:00", 
            weather="Dry, High Winds",
            global_events=["Simulation Initialized: Wildfire Warning in effect."]
        ),
        actors={
            "Actor_FireChief": Actor(
                actor_id="Actor_FireChief", 
                role="Incident Commander", 
                description="Responsible for managing city fire response assets.",
                assets=["Truck_01", "Helo_Alpha"]
            )
        },
        assets={
            "Truck_01": Asset(
                asset_id="Truck_01",
                name="Fire Truck Alpha",
                asset_type="Ground Unit",
                location={"lat": 34.05, "lon": -118.25},
                attributes={"water_level": 100, "fuel": 100}
            ),
            "Helo_Alpha": Asset(
                asset_id="Helo_Alpha",
                name="Water Bomber 1",
                asset_type="Air Unit",
                location={"lat": 34.10, "lon": -118.30},
                attributes={"status": "grounded"}
            )
        }
    )

    # Clear old data for this scenario ID only
    collection.delete_many({"simulation_id": "Alpha_Scenario"})
    
    # Insert Cycle 0
    collection.insert_one(initial_state.model_dump())
    print("✅ Database Seeded Successfully!")

if __name__ == "__main__":
    seed_simulation()