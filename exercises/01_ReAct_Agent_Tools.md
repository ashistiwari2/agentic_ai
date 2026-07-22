# Exercise 1 — Build a Single ReAct Agent with Tools

**Difficulty:** Beginner–Intermediate | **Time:** 15–20 min | **Theory link:** 5.2 Single-Agent Architecture / 5.3 Tool Use, Function Calling, and API Integration

---

## 🎯 Goal

Every agent this program builds — supervisor-worker systems, human-in-the-loop workflows, guarded agents — is an extension of one core loop: the model decides it needs more information, calls a tool to get it, and uses the result to decide what to do next. This exercise builds that loop from scratch and gives it a task that genuinely requires chaining three different tools together.

By the end, you will be able to:
- Explain the agent loop: observe → decide → act → observe again
- Define tools with a schema an LLM can understand and call correctly
- Read a full agent reasoning trace and explain why each tool was called, in order
- Explain why a circuit breaker (max iteration limit) is necessary, not optional

**Real-world context:** A banking customer service agent that can look up product information, calculate a loan EMI, and check whether an application window is still open — exactly the multi-tool task this exercise builds, matching the original curriculum's scenario precisely.

---

## 🧠 Concept Primer

### What makes this a "ReAct" agent?

ReAct (Reasoning + Acting) describes an agent that interleaves the two: it reasons about what it needs, takes an action (calls a tool), observes the result, and reasons again with that new information — rather than trying to plan everything upfront or answer from memory alone. The loop in this exercise is a direct, minimal implementation of that pattern.

### How does "tool calling" actually work, mechanically?

You give the LLM a list of tool **schemas** — JSON descriptions of each tool's name, purpose, and expected parameters (but NOT the actual Python code; the model never executes anything itself). When the model decides it needs a tool, it doesn't call it directly — it returns a special response saying "I want to call `calculate_emi` with these arguments." Your code then:
1. Reads that request
2. Actually executes the real Python function with those arguments
3. Sends the result BACK to the model as a new message
4. Calls the model again, now with that result in context

The model can then either request another tool call, or give a final answer. This request → execute → feed-back → repeat cycle IS the agent loop.

### Why does the agent need a circuit breaker?

Nothing inherently stops a language model from deciding it wants to call tools forever — a bug in your tool's return format, an ambiguous task, or a model that gets "confused" could all lead to an infinite loop, each iteration costing real API calls and money. `MAX_ITERATIONS` in this exercise's code is a hard cap: after N iterations without a final answer, the loop stops and reports failure explicitly, rather than running indefinitely. This is a direct, simple example of theory topic 5.9/5.10's "infinite loops and runaway agents: detection and circuit breakers."

---

## Step 1 — The dataset

`data/product_knowledge_base.csv` — 6 banking product entries, searched by the agent's `search_knowledge_base` tool.

---

## Step 2 — Azure OpenAI setup

Needs one deployment that supports tool/function calling (`AZURE_OPENAI_DEPLOYMENT`). See the package `README.md`.

---

## Step 3 — Code walkthrough

### Stage 1 — Define the tools: both the real function AND its schema

```python
def calculate_emi(principal, annual_rate, tenure_months):
    r = (annual_rate / 12) / 100
    n = tenure_months
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return {"monthly_emi": round(emi, 2), ...}

TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "calculate_emi",
        "description": "Calculate the monthly EMI for a loan given principal, annual interest rate, and tenure in months.",
        "parameters": {"type": "object", "properties": {
            "principal": {"type": "number"}, "annual_rate": {"type": "number"}, "tenure_months": {"type": "integer"}},
            "required": ["principal", "annual_rate", "tenure_months"]}
    }},
    ...
]
```

**What this does:** notice there are TWO separate things for every tool — the actual Python function that does the work (verified with the standard reducing-balance EMI formula), and a JSON *schema* describing that function to the model. The model only ever sees the schema — the `description` field is doing real work here, since it's the model's only source of information about when and how to use this tool. A vague description leads to the model calling the tool incorrectly or not calling it when it should.

### Stage 2 — The agent loop itself

```python
def run_agent(client, deployment, kb_df, user_task):
    messages = [{"role": "system", "content": "..."}, {"role": "user", "content": user_task}]

    for iteration in range(1, MAX_ITERATIONS + 1):
        response = call_llm_with_tools(client, deployment, messages, temperature=0)
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content  # final answer — no more tools needed

        messages.append(message)
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            result = execute_tool(name, args, kb_df)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})
```

**What this does, precisely:**
- The loop calls the model, then checks `message.tool_calls` — if it's empty/None, the model decided it has enough information and gave a final answer, so we return it.
- If there ARE tool calls, we append the model's OWN request message to the conversation history (`messages.append(message)`) — this is essential, the model needs to see its own prior tool request in context to understand what the following tool result is answering.
- For each requested tool call: `json.loads(tool_call.function.arguments)` parses the arguments the model generated (it returns them as a JSON string, not a Python dict, so this parsing step is required); `execute_tool()` dispatches to the real function; the result is appended as a special `"role": "tool"` message, paired with the exact `tool_call_id` the model used to request it — this ID pairing is how the model knows which result answers which request, especially when multiple tools are called in one turn.
- The loop then repeats — the model sees the tool result and decides whether it needs another tool or can now answer.

---

## Expected Output (illustrative)

```
TASK: I'm considering the Flexi Personal Loan for $40,000 over 36 months. What would my monthly EMI be, and is the application window for this quarter's new loan products still open today?

[Iteration 1] Agent requests 1 tool call(s):
  -> search_knowledge_base({'query': 'Flexi Personal Loan interest rate'})
     result: {'doc_id': 'PROD001', 'text': 'The Flexi Personal Loan offers amounts...9.5%...'}

[Iteration 2] Agent requests 1 tool call(s):
  -> calculate_emi({'principal': 40000, 'annual_rate': 9.5, 'tenure_months': 36})
     result: {'monthly_emi': 1281.32, ...}

[Iteration 3] Agent requests 1 tool call(s):
  -> get_current_date({})
     result: {'current_date': '2026-07-19', 'quarter': 'Q3', 'year': 2026}

[Iteration 4] Agent gives final answer (no more tool calls needed):
Your monthly EMI on a $40,000 Flexi Personal Loan over 36 months at 9.5% would be approximately $1,281.32.
As for the application window: yes, it's currently Q3 2026, and this quarter's new loan products remain open until September 30th.
```
*(Verified: the tool functions and the full agent-loop mechanics — including message threading and tool_call_id pairing — were tested directly with a scripted tool-call sequence and produce exactly this shape of output. The specific tool CALL ORDER the live model chooses may vary slightly, but the final synthesised answer should match this pattern.)*

---

## 🛠 Common Pitfalls

- **Forgetting to append the model's own tool-call message before the tool results:** if you only append the `"role": "tool"` results without first appending the model's request message, the model loses track of what it asked for — always append both, in order.
- **Mismatched `tool_call_id`:** if you use the wrong ID when returning a tool result (e.g., when multiple tools are called in one turn), the model can't correctly match results to requests. Always use the exact ID from the corresponding `tool_call.id`.
- **No circuit breaker:** always cap iterations. A production agent without one is a real operational risk, not a theoretical one.
- **Vague tool descriptions:** if the model calls the wrong tool, or doesn't call a tool it should have, the `description` field is usually the first place to look — it's the model's only guide to when a tool applies.

---

## 🏠 Homework Exercise

1. Add a 4th tool: `check_eligibility(credit_score, requested_amount)` that returns a simple eligibility verdict (e.g., eligible if `credit_score > 650` and `requested_amount <= 75000`).
2. Give the agent a task requiring all 4 tools in sequence (e.g., "I have a credit score of 720, want to borrow $30,000 for 24 months on the Flexi Personal Loan — am I eligible, and what would my EMI be?").
3. Run it and check the trace: does the agent call the tools in a sensible order, or does it try `calculate_emi` before checking eligibility? What does that tell you about how much control you have (or don't have) over an agent's tool-call ORDER versus just which tools it uses?

**Hints:**
- You generally can't force a strict tool-call order through the schema alone — the model decides sequencing based on its own reasoning about the task. If order genuinely matters (e.g., don't calculate EMI for an ineligible applicant), you'd need either a stronger system prompt instruction about sequencing, or a more constrained architecture (like the Planner-Executor pattern from the theory session) rather than a free-form ReAct loop.
