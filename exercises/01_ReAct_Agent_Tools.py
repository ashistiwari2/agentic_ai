import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import AzureOpenAI, BadRequestError


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "product_knowledge_base.csv"
load_dotenv()


def calculate_emi(principal, annual_rate, tenure_months):
    r = (annual_rate / 12) / 100
    n = tenure_months
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return {
        "monthly_emi": round(emi, 2),
        "principal": principal,
        "annual_rate": annual_rate,
        "tenure_months": tenure_months,
    }


def search_knowledge_base(query, kb_df):
    query_text = str(query).strip().lower()
    if not query_text:
        return {"doc_id": None, "text": "No query provided."}

    filtered = kb_df[kb_df["text"].str.contains(query_text, case=False, na=False)]
    if filtered.empty:
        return {"doc_id": None, "text": "No matching knowledge-base entry found."}

    row = filtered.iloc[0]
    return {"doc_id": row["doc_id"], "text": row["text"]}


def get_current_date():
    today = datetime.today()
    month = today.month
    if month <= 3:
        quarter = "Q1"
    elif month <= 6:
        quarter = "Q2"
    elif month <= 9:
        quarter = "Q3"
    else:
        quarter = "Q4"
    return {"current_date": today.strftime("%Y-%m-%d"), "quarter": quarter, "year": today.year}


def check_eligibility(credit_score, requested_amount):
    eligible = bool(credit_score > 650 and requested_amount <= 75000)
    return {
        "eligible": eligible,
        "credit_score": credit_score,
        "requested_amount": requested_amount,
        "reason": "Meets the score and amount thresholds." if eligible else "Does not meet the eligibility thresholds.",
    }


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the banking knowledge base for product details such as interest rates, loan terms, or product eligibility information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search text or product topic to look up."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_emi",
            "description": "Calculate the monthly EMI for a loan given principal, annual interest rate, and tenure in months.",
            "parameters": {
                "type": "object",
                "properties": {
                    "principal": {"type": "number"},
                    "annual_rate": {"type": "number"},
                    "tenure_months": {"type": "integer"},
                },
                "required": ["principal", "annual_rate", "tenure_months"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Return today's date and the current quarter/year so the agent can determine whether a product application window is open.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_eligibility",
            "description": "Check whether a borrower is eligible for a loan request using a simple rule: credit_score > 650 and requested_amount <= 75000.",
            "parameters": {
                "type": "object",
                "properties": {
                    "credit_score": {"type": "number"},
                    "requested_amount": {"type": "number"},
                },
                "required": ["credit_score", "requested_amount"],
            },
        },
    },
]


TOOL_FUNCTIONS = {
    "search_knowledge_base": lambda query, kb_df=None: search_knowledge_base(query, kb_df),
    "calculate_emi": calculate_emi,
    "get_current_date": get_current_date,
    "check_eligibility": check_eligibility,
}


def build_client():
    missing = [
        key
        for key in (
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_DEPLOYMENT",
        )
        if not os.getenv(key)
    ]
    if missing:
        print("[WARNING] Azure OpenAI not configured — missing: " + ", ".join(missing))
        return None, None

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=endpoint,
        api_version=api_version,
    )
    return client, os.environ["AZURE_OPENAI_DEPLOYMENT"]


def execute_tool(name, args, kb_df):
    if name == "search_knowledge_base":
        return search_knowledge_base(args["query"], kb_df)
    if name == "calculate_emi":
        return calculate_emi(**args)
    if name == "get_current_date":
        return get_current_date()
    if name == "check_eligibility":
        return check_eligibility(**args)
    raise ValueError(f"Unknown tool: {name}")


def call_llm_with_tools(client, deployment, messages, temperature=0):
    try:
        return client.chat.completions.create(
            model=deployment,
            messages=messages,
            tools=TOOLS_SCHEMA,
            temperature=temperature,
        )
    except BadRequestError as exc:
        if "temperature" in str(exc).lower():
            return client.chat.completions.create(
                model=deployment,
                messages=messages,
                tools=TOOLS_SCHEMA,
            )
        raise


def run_agent(client, deployment, kb_df, user_task, max_iterations=6):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful banking customer-service agent. Use the available tools to answer the user’s question. "
                "When a tool result is returned, use it in the next step instead of guessing. "
                "Keep your final answer concise and grounded in the evidence from the tool results."
            ),
        },
        {"role": "user", "content": user_task},
    ]

    for iteration in range(1, max_iterations + 1):
        response = call_llm_with_tools(client, deployment, messages, temperature=0)
        message = response.choices[0].message

        if not message.tool_calls:
            print(f"[Iteration {iteration}] Agent gives final answer (no more tool calls needed).")
            return message.content

        print(f"[Iteration {iteration}] Agent requests {len(message.tool_calls)} tool call(s):")
        assistant_message = message.model_dump(exclude_none=True)
        messages.append(assistant_message)

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"  -> {name}({arguments})")
            result = execute_tool(name, arguments, kb_df)
            print(f"     result: {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return "[Agent stopped: hit max_iterations without reaching a final answer]"


if __name__ == "__main__":
    kb_df = pd.read_csv(DATA_PATH)
    client, deployment = build_client()

    if client is None or deployment is None:
        raise SystemExit(0)

    task = (
        "I have a credit score of 720 and want to borrow $30,000 for 24 months on the Flexi Personal Loan. "
        "Am I eligible, and what would my EMI be?"
    )

    print("TASK:", task)
    print()
    final_answer = run_agent(client, deployment, kb_df, task, max_iterations=6)
    print()
    print("FINAL ANSWER:")
    print(final_answer)
