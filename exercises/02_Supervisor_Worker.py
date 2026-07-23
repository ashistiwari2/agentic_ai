import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import AzureOpenAI, BadRequestError


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "loan_applications.csv"
load_dotenv()


def get_required_documents(requested_amount):
    required = ["income_proof.pdf", "id_proof.pdf"]
    if requested_amount > 20000:
        required.append("bank_statements_3months.pdf")
    if requested_amount > 40000:
        required.append("property_deed.pdf")
    return required


def document_verification_worker(application_row):
    submitted = set(doc.strip() for doc in application_row["submitted_documents"].split(",") if doc.strip())
    required = set(get_required_documents(application_row["requested_amount"]))
    missing = sorted(required - submitted)
    return {
        "required_documents": sorted(required),
        "missing_documents": missing,
        "complete": len(missing) == 0,
    }


CREDIT_WORKER_SYSTEM_PROMPT = (
    "You are a Credit Assessment Worker. Your ONLY job is to assess credit risk based on the credit score "
    "and repayment history provided. You do not see or consider document completeness — that is a different "
    "worker's job. Return a short risk assessment with a risk level (Low, Medium, or High) and a one-sentence "
    "reason that references the repayment history and credit score only."
)


SUPERVISOR_SYSTEM_PROMPT = (
    "You are a loan pre-screening supervisor. You receive two reports: one from the Credit Assessment Worker "
    "and one from the Document Verification Worker. Synthesize them into ONE final recommendation: "
    "Approve, Conditional Approval, or Decline. Business logic: if credit risk is High, recommend Decline "
    "regardless of documents. If credit risk is Low or Medium and documents are incomplete, recommend "
    "Conditional Approval. If credit risk is Low or Medium and documents are complete, recommend Approve. "
    "Give a short, practical rationale using both worker outputs."
)


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


def call_chat_model(client, deployment, messages, temperature=0):
    try:
        return client.chat.completions.create(
            model=deployment,
            messages=messages,
            temperature=temperature,
        )
    except BadRequestError as exc:
        if "temperature" in str(exc).lower():
            return client.chat.completions.create(
                model=deployment,
                messages=messages,
            )
        raise


def credit_assessment_worker(client, deployment, application_row):
    user_prompt = (
        f"Credit score: {application_row['credit_score']}\n"
        f"Repayment history: {application_row['repayment_history_summary']}\n"
        "Assess the applicant's risk level and explain the reasoning in one short paragraph."
    )
    response = call_chat_model(
        client,
        deployment,
        [
            {"role": "system", "content": CREDIT_WORKER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def supervisor_synthesize(client, deployment, application_row, credit_result, doc_result):
    user_prompt = (
        f"Application: {application_row['application_id']} - {application_row['applicant_name']}\n"
        f"Requested amount: ${application_row['requested_amount']}\n"
        f"Credit Assessment Worker report:\n{credit_result}\n\n"
        f"Document Verification Worker report:\n"
        f"Complete: {doc_result['complete']}\n"
        f"Required documents: {json.dumps(doc_result['required_documents'])}\n"
        f"Missing documents: {json.dumps(doc_result['missing_documents'])}\n"
        "Please return only the final recommendation with a brief rationale."
    )
    response = call_chat_model(
        client,
        deployment,
        [
            {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def main():
    df = pd.read_csv(DATA_PATH)

    client, deployment = build_client()

    print("=== Exercise 2 — supervisor-worker pre-screening ===")
    print()

    for _, row in df.iterrows():
        doc_result = document_verification_worker(row)
        print(f"APPLICATION {row['application_id']}: {row['applicant_name']} (requesting ${row['requested_amount']})")
        print("-- Document Verification Worker (deterministic) --")
        print(f"Required: {doc_result['required_documents']}")
        print(f"Missing: {doc_result['missing_documents']}")
        print(f"Complete: {doc_result['complete']}")
        print()

        if client is None or deployment is None:
            print("-- Credit Assessment Worker (LLM) --")
            print("Skipped: Azure OpenAI settings are not configured in this environment.")
            print("-- Supervisor synthesis --")
            print("Deferred: the supervisor needs the Azure-backed credit and synthesis results to complete the final recommendation.")
            print("=" * 80)
            print()
            continue

        print("-- Credit Assessment Worker (LLM) --")
        credit_result = credit_assessment_worker(client, deployment, row)
        print(credit_result)
        print()

        print("-- Supervisor synthesises final recommendation --")
        final_recommendation = supervisor_synthesize(client, deployment, row, credit_result, doc_result)
        print(final_recommendation)
        print("=" * 80)
        print()


if __name__ == "__main__":
    main()
