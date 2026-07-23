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


######-----------------output-----------------######
"""
=== Exercise 2 — supervisor-worker pre-screening ===

APPLICATION APP001: Maria Santos (requesting $25000)
-- Document Verification Worker (deterministic) --
Required: ['bank_statements_3months.pdf', 'id_proof.pdf', 'income_proof.pdf']
Missing: []
Complete: True

-- Credit Assessment Worker (LLM) --
Risk Level: Low. The applicant presents low credit risk because a 742 credit score is strong and the 18-month repayment history shows no missed payments across two credit cards and one auto loan.

-- Supervisor synthesises final recommendation --
Approve — Credit risk is Low based on the strong 742 credit score and clean 18-month repayment history, and document verification is complete with all required documents submitted and no missing items.
================================================================================

APPLICATION APP002: James Whitfield (requesting $15000)
-- Document Verification Worker (deterministic) --
Required: ['id_proof.pdf', 'income_proof.pdf']
Missing: []
Complete: True

-- Credit Assessment Worker (LLM) --
Risk level: Medium. The applicant’s 615 credit score indicates fair credit, and while the repayment history shows some positive behavior with an auto loan paid off early, the two missed credit card payments in the last12 months increase risk despite being resolved within 30 days.

-- Supervisor synthesises final recommendation --
Approve — Credit risk is Medium based on a 615 score and two recent but quickly resolved missed payments, and all required documents were provided and verified as complete.
================================================================================

APPLICATION APP003: Priya Nair (requesting $50000)
-- Document Verification Worker (deterministic) --
Required: ['bank_statements_3months.pdf', 'id_proof.pdf', 'income_proof.pdf', 'property_deed.pdf']
Missing: []
Complete: True

-- Credit Assessment Worker (LLM) --
Risk Level: Low. The applicant’s 780 credit score indicates strong creditworthiness, and the repayment history shows 5 years of consistent on-time payments with zero missed payments across three accounts, plus a mortgage in good standing.

-- Supervisor synthesises final recommendation --
Approve — Credit risk is Low based on a 780 score and 5 years of on-timerepayment with no missed payments, and document verification is completewith all required documents submitted.
================================================================================

APPLICATION APP004: David Chen (requesting $10000)
-- Document Verification Worker (deterministic) --
Required: ['id_proof.pdf', 'income_proof.pdf']
Missing: ['income_proof.pdf']
Complete: False

-- Credit Assessment Worker (LLM) --
High risk — A credit score of 590 indicates weak creditworthiness, and the current 45-day past-due credit card payment in a very limited repayment history suggests elevated risk of future delinquency.

-- Supervisor synthesises final recommendation --
Decline — Credit assessment is High risk due to a 590 score and a current 45-day past-due payment with limited repayment history. Documents are also incomplete, with income_proof.pdf missing.
================================================================================
"""
###--------------DONE------------------###