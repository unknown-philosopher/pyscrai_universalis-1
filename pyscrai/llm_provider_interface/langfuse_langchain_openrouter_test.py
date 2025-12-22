import os
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
openrouter_base_url = os.getenv("OPENROUTER_BASE_URL")

llm = ChatOpenAI(
    api_key=openrouter_api_key,
    model="xiaomi/mimo-v2-flash:free",
    base_url=openrouter_base_url
)

langfuse_handler = CallbackHandler()

def arbitrary_test_tool(input_text: str) -> str:
    """A generic test tool for LLM agent testing."""
    return f"Test tool received: {input_text}"

agent = create_agent(
    model=llm,
    tools=[arbitrary_test_tool],
    system_prompt="You are a helpful assistant running an arbitrary test.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "run the arbitrary test tool with input 'foo'"}]},
    config={"callbacks": [langfuse_handler]}
)
print(result)