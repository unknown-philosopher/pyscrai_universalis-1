import os
from typing import TypedDict, List
from dotenv import load_dotenv

# LangChain / OpenRouter / Langfuse Imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langfuse.langchain import CallbackHandler
from langgraph.graph import StateGraph, END

# Local Imports
from src.schemas import WorldState

# Load environment variables
load_dotenv()

# --- SETUP LLM & OBSERVABILITY ---
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
openrouter_base_url = os.getenv("OPENROUTER_BASE_URL")
model_name = os.getenv("MODEL_NAME", "xiaomi/mimo-v2-flash:free")

# Initialize the Archon's Brain (LLM)
llm = ChatOpenAI(
    api_key=openrouter_api_key,
    base_url=openrouter_base_url,
    model=model_name,
    temperature=0.7
)

# Initialize Langfuse Handler for Tracing
langfuse_handler = CallbackHandler()

# --- GRAPH STATE DEFINITION ---
class AgentState(TypedDict):
    world_state: WorldState
    actor_intents: List[str]
    archon_summary: str

# --- NODE 1: PERCEPTION (The Actors) ---
def actor_perception_node(state: AgentState):
    print("--- 🧠 NODE: ACTORS PERCEIVING ---")
    
    # Placeholder: In the future, this will loop through Actors and perform RAG
    # For now, we simulate a mock intent based on the cycle
    cycle = state["world_state"].environment.cycle
    
    if cycle == 1:
        intent = "Actor_FireChief: Order Truck_01 to move to Sector 7 due to smoke reports."
    else:
        intent = f"Actor_FireChief: Maintain position and assess situation (Cycle {cycle})."
    
    state["actor_intents"] = [intent]
    return state

# --- NODE 2: ADJUDICATION (The Archon) ---
def archon_adjudication_node(state: AgentState):
    print("--- ⚖️ NODE: ARCHON ADJUDICATING ---")
    
    current_state = state["world_state"]
    intents = "\n".join(state["actor_intents"])
    
    # 1. Construct the Prompt for the Archon
    system_prompt = (
        "You are the Archon, the omniscient referee of a simulation. "
        "Your goal is to adjudicate actor actions and simulate environmental shifts (Gaia). "
        "Analyze the current state and the actor intents. "
        "Output a concise summary of what happens next."
    )
    
    user_prompt = (
        f"Current Cycle: {current_state.environment.cycle}\n"
        f"Current Weather: {current_state.environment.weather}\n"
        f"Recent Events: {current_state.environment.global_events[-3:] if current_state.environment.global_events else 'None'}\n\n"
        f"Actor Intents:\n{intents}\n\n"
        "Adjudicate the result of this cycle:"
    )

    # 2. Invoke the LLM with Langfuse Tracing
    try:
        response = llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
            config={"callbacks": [langfuse_handler]}
        )
        summary = response.content
    except Exception as e:
        summary = f"Archon Error: {str(e)}"

    # 3. Update the World State (Ground Truth)
    # Append the LLM's narrative to the global events log
    state["world_state"].environment.global_events.append(summary)
    state["archon_summary"] = summary
    
    return state

# --- COMPILE THE GRAPH ---
workflow = StateGraph(AgentState)

workflow.add_node("perception", actor_perception_node)
workflow.add_node("adjudication", archon_adjudication_node)

workflow.set_entry_point("perception")
workflow.add_edge("perception", "adjudication")
workflow.add_edge("adjudication", END)

simulation_brain = workflow.compile()