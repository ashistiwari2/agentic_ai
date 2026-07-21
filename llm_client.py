import os
from dotenv import load_dotenv
from openai import AzureOpenAI
 
load_dotenv()
 
# --- Chat client (Responses API) ---
chat_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
 
chat_client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_KEY"],
    base_url=f"{chat_endpoint}/openai/v1/",
    api_version="preview",
)
 
CHAT_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]
 
# --- Embedding client (may be a different resource) ---
embedding_endpoint = os.environ.get(
    "AZURE_OPENAI_EMBEDDING_ENDPOINT", os.environ["AZURE_OPENAI_ENDPOINT"]
).rstrip("/")
embedding_key = os.environ.get("AZURE_OPENAI_EMBEDDING_KEY", os.environ["AZURE_OPENAI_KEY"])
 
embedding_client = AzureOpenAI(
    api_key=embedding_key,
    azure_endpoint=embedding_endpoint,
    api_version="2024-10-21",
)
 
EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "")
 
 
def ask(system_prompt: str, user_prompt: str) -> str:
    """Send a system + user prompt to the chat model and return the reply text."""
    response = chat_client.responses.create(
        model=CHAT_DEPLOYMENT,
        input=[
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        reasoning={"effort": "none"},
    )
    return response.output_text
 
 
def embed(text: str) -> list[float]:
    """Turn a piece of text into an embedding vector (a list of numbers)."""
    response = embedding_client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT,
        input=text,
    )
    return response.data[0].embedding
 
 
def ask_with_tools(system_prompt: str, user_prompt: str, tools: list):
    """Send a prompt along with a list of tool definitions. The model may
    respond with normal text, OR with one or more tool calls it wants you
    to execute. Returns the raw response object so the caller can inspect
    response.output for tool_call items. See 03_tool_use_function_calling.py
    for how to use this."""
    response = chat_client.responses.create(
        model=CHAT_DEPLOYMENT,
        input=[
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        tools=tools,
        reasoning={"effort": "none"},
    )
    return response