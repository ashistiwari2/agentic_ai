from llm_client import ask

question = "What is our return policy for sale items?"
context = "Return Policy: Items may be returned within 30 days with a receipt. Sale items marked Final Sale cannot be returned."
response = ask("Answer using only the given context.",f"Context:{context}\n\nQuestion: {question}")

print(f"Question: {question}")
print(f"Response beig evaluated: {response}\n")

def score_metric(mentric_name, rubric, question, respone, context=None):
    prompt =f"Question: {question}\nResponse: {respone}"
    if context:
        prompt += f"\nContext:{context}"
    result = ask(
        f"Score the response's {mentric_name} from 1-5 using this rubric:\n{rubric}\n"
        "Reply in the format:\nSCORE: <number>\nREASON: <one sentence>", prompt
    )
    return result

metrics = {
    "Relevance":"5 = directly addresses the question. 1 = off-topic or ignores the question.",
    "Correctness":"5 = factually accurate. 1 = contains false or fabricated information.",
    "Completeness":"5 = fully answers all parts of the question. 1 = leaves out important information.",
    "Coherence":"5 = clear, logically structured, easy to follow. 1 = confusing or disjointed.",
    "Groundedness":"5 = every claim is directly supported by the given context. 1= makes claims the context doesn't support.",
}

for metric_name, rubric in metrics.items():
    result = score_metric(metric_name, rubric, question, response, context)
    print(result)
    print()

###-----------------OUTPUT-------------------###
"""
Question: What is our return policy for sale items?
Response beig evaluated: Sale items marked **Final Sale** cannot be returned.

SCORE: 5
REASON: The response directly answers the question by stating that sale items marked Final Sale cannot be returned, which matches the provided policy context.

SCORE: 5
REASON: The response exactly matches the policy stated in the context that sale items marked Final Sale cannot be returned.

SCORE: 5
REASON: The response directly and accurately answers the question using the relevant return policy detail for sale items.

SCORE: 5
REASON: The response is clear, directly answers the question, and matches the provided return policy without unnecessary detail.

SCORE: 5
REASON: The response exactly matches the policy stated in the provided context.
"""
###-----------------DONE-------------------###