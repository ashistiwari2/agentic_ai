# faithfulness, answer relevance, metadata- citation -accuracy, hallucination rate 

from llm_client import ask 

context_chunks =[
    {"id":"chunk1", "text":"Refunds are issued within 5-7 business days."},
    {"id":"chunk2", "text":"Sale items marked Final Sale cannot be returned."},
]

question = "How long do refunds take and can I return a sale item?"

#debiberate hallucination

response_with_hallucination = (
    "Refunds are issued within 5-7 business days [chunk1]. Sale items can be returned within 60 days for store credit [chunk2]."
)

#faithfulness: does the response contradict or go beyond the context?

faithfulness_check = ask(
    "For EACH claim in the response, check if it's supported by the context."
    "List any claims that are NOT supported or contradict the context.",
    f"Context: {[c['text'] for c in context_chunks]}\nResponse:{response_with_hallucination}"
)

print(faithfulness_check)
#relevance: does the response actually address what was asked ?

relevance_score = ask(
    "Rate 1-5: does this response address ALL parts of the question asked? Reply with SCORE: <n> and a reason.",
    f"Question:{question}\nResponse: {response_with_hallucination}"
)
print(relevance_score)


###------------OUTPUT------------###
"""
Unsupported or contradictory claims:
- “Sale items can be returned within 60 days for store credit [chunk2].” This contradicts the context, which says: “Sale items marked Final Sale cannot be returned.”

Supported claims:
- “Refunds are issued within 5-7 business days [chunk1].” Supported by the context.
SCORE: 5 - It answers both parts: refund timing (“within 5–7 business days”) and the sale item return policy (“can be returned within 60 days for store credit”).
"""
###------------DONE-------------------###