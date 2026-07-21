import json
from llm_client import chat_client, CHAT_DEPLOYMENT
 
 
def run_agent(system_prompt, user_request, tools, tool_functions, max_iterations=6, verbose=True):
    """
    system_prompt:  instructions for the agent
    user_request:   the task/question to solve
    tools:          list of tool definitions (JSON Schema, same format
                     as 03_tool_use_function_calling.py)
    tool_functions: dict mapping tool name -> the real Python function
                     to call, e.g. {"check_ticket": check_ticket}
    max_iterations: safety cap -- see 5.9/5.10 (circuit breaker pattern)
 
    Returns the agent's final text answer.
    """
    input_items = [
        {"role": "developer", "content": system_prompt},
        {"role": "user", "content": user_request},
    ]
    previous_response_id = None
 
    for iteration in range(1, max_iterations + 1):
        response = chat_client.responses.create(
            model=CHAT_DEPLOYMENT,
            input=input_items,
            tools=tools,
            previous_response_id=previous_response_id,
        )
 
        tool_calls = [item for item in response.output if item.type == "function_call"]
 
        # No tool calls means the model thinks it's done -- return its answer.
        if not tool_calls:
            if verbose:
                print(f"[iteration {iteration}] Agent gave a final answer (no more tools needed).")
            return response.output_text
 
        # The model wants to call one or more tools. EXECUTE them for real.
        input_items = []
        for call in tool_calls:
            args = json.loads(call.arguments)
            if verbose:
                print(f"[iteration {iteration}] Agent calls: {call.name}({args})")
            try:
                result = tool_functions[call.name](**args)
            except Exception as e:
                result = f"ERROR calling {call.name}: {e}"
            if verbose:
                print(f"    -> result: {result}")
            input_items.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": str(result),
            })
 
        previous_response_id = response.id
 
    return "[Agent stopped: hit max_iterations without reaching a final answer]"
 