from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from llm_client import ask

#step-1 define the state #typeddict 

class AgentState(TypedDict):
    question: str
    draft_answer: str
    is_good_enough: bool
    attempts: Annotated[int, operator.add]

#step 2 - nodes

def generate_node(state: AgentState) -> dict:
    draft = ask("Answr concisely.", state["question"])
    print(f"[generate] Draft: {draft}")
    return {"draft_answer":draft, "attempts":1}

def critique_node(state: AgentState) -> dict:
    verdict = ask(
        "Reply with ONLY 'yes' or 'no': is this a complete, correct, well-formed answer to the question?",
        f"Question:{state['question']}\nAnswer: {state['draft_answer']}"
    )
    is_good ="yes" in verdict.lower()
    print(f"[critique] Good enough? {is_good}")
    return {"is_good_enough": is_good}

#step-3 

def route_after_critique(state: AgentState) -> str:
    if state["is_good_enough"] or state["attempts"] >=3:
        return "end"
    return "retry"

#step-4

graph_builder = StateGraph(AgentState)
graph_builder.add_node("generate", generate_node)
graph_builder.add_node("critique",critique_node)

graph_builder.set_entry_point("generate")
graph_builder.add_edge("generate", "critique")

graph_builder.add_conditional_edges("critique",
route_after_critique,{"retry":"generate", "end":END},)

#STEP-5

checkpointer = MemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)

#step 6 run it

config = {"configurable":{"thread_id":"demo-session-1"}}
result = graph.invoke(
    {"question":"What year did the first iPhone release, and who announced it?", "attempts":0},
    config = config,
)

print(f"Answer:{result['draft_answer']}")
print(f"Attempts taken: {result['attempts']}")

###-----------OUTPUT----------------###
"""
[generate] Draft: The first iPhone was released in **2007**, and it was announced by **Steve Jobs**.
[critique] Good enough? True
Answer:The first iPhone was released in **2007**, and it was announced by **Steve Jobs**.
Attempts taken: 1
"""
###-----------DONE------------------###