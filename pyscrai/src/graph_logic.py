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
    print("---  NODE: ACTORS PERCEIVING ---")
    
    world = state["world_state"]
    env = world.environment
    all_intents = []

    # 1. Loop through all actors in the simulation
    for actor_id, actor in world.actors.items():
        
        # 2. Build Context Strings
        recent_events = "\n- ".join(env.global_events[-3:]) if env.global_events else "None"
        asset_list = ", ".join(actor.assets) if actor.assets else "None"
        objectives_list = "\n- ".join(actor.objectives) if actor.objectives else "None"
        
        # 3. Construct the Prompt
        # This gives the LLM the "Mind" of the specific actor
        prompt_content = (
            f"You are {actor.role} (ID: {actor_id}).\n"
            f"Description: {actor.description}\n"
            f"Objectives:\n- {objectives_list}\n"
            f"Assets under command: {asset_list}\n\n"
            f"Current Situation:\n"
            f"- Cycle: {env.cycle}\n"
            f"- Time: {env.time}\n"
            f"- Weather: {env.weather}\n"
            f"- Recent Events:\n- {recent_events}\n\n"
            "Based on your role and the situation, what is your strategic intent for this cycle? "
            "Be concise. Refer to your assets by name if moving them."
        )

        try:
            # 4. Invoke LLM (The Mind)
            # We use the same 'llm' instance defined globally in graph_logic.py
            response = llm.invoke(
                [HumanMessage(content=prompt_content)],
                config={"callbacks": [langfuse_handler]}
            )
            
            # Format: "Actor_ID: [LLM Response]"
            intent_str = f"{actor_id}: {response.content}"
            all_intents.append(intent_str)
            print(f"   > {actor_id} decided: {response.content[:50]}...")

        except Exception as e:
            error_msg = f"{actor_id} failed to act: {str(e)}"
            all_intents.append(error_msg)
            print(error_msg)

    # 5. Update State
    state["actor_intents"] = all_intents
    return state

# --- NODE 2: ADJUDICATION (The Archon) ---
def archon_adjudication_node(state: AgentState):
    print("---  NODE: ARCHON ADJUDICATING ---")
    
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