import json
from llm_client import chat_client, CHAT_DEPLOYMENT

#step-1 

def get_order_status(order_id: str) -> str:
    """Preted this looks up a real database."""
    fake_orders ={
        "A1023":"shipped, arriving in 2 days",
        "B4471":"delayed due to weather",
    }
    return fake_orders.get(order_id, "order not found")

#step-2
tools =[
    {
        "type":"function",
        "name":"get_order_status",
        "description":"Look up the shipping status of a customer's order by order ID.",
        "parameters":{
            "type":"object",
            "properties":{
                "order_id":{
                    "type":"string",
                    "description": "The order ID, e.g. 'A1023'"
                }
            },
            "required":["order_id"]
        }
    }
]

#step-3
user_question = "can you check on order A1023 for me?"

response = chat_client.responses.create(
    model=CHAT_DEPLOYMENT,
    input=[
        {"role":"developer", "content":"You are a customer support agent. Use tools when needed."},
        {"role":"user","content": user_question},
    ],
    tools=tools,
)

#step-4 

tool_calls = [item for item in response.output if item.type == "function_call"]

if tool_calls:
    call =tool_calls[0]
    print(f"Model wants to call:{call.name}({call.arguments})")
    args = json.loads(call.arguments)
    tool_result = get_order_status(**args)
    print(f"Tool result: {tool_result}")

    followup = chat_client.responses.create(
        model=CHAT_DEPLOYMENT,
        previous_response_id=response.id,
        input=[
            {
                "type":"function_call_output",
                "call_id":call.call_id,
                "output":tool_result
            }
        ],
    )
    print("final answer:", followup.output_text)
else:
    print("model answered directly, not tool needed", response.output_text)

###---------OUTPUT------------------###
"""
Model wants to call:get_order_status({"order_id":"A1023"})
Tool result: shipped, arriving in 2 days
final answer: Order A1023 has shipped and is expected to arrive in 2 days.
"""
###----------DONE------------------###