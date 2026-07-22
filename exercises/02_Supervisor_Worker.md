# Exercise 2 — Multi-Agent Supervisor-Worker System

**Difficulty:** Intermediate | **Time:** 15–20 min | **Theory link:** 5.2 Supervisor-Worker Architecture

---

## 🎯 Goal

Some tasks are genuinely better split across multiple specialised agents than handled by one generalist — this exercise builds a supervisor that decomposes a loan pre-screening task and delegates to two workers with distinct responsibilities, then synthesises their separate findings into one final recommendation.

By the end, you will be able to:
- Explain when a multi-agent architecture is worth the added complexity over a single agent
- Build a supervisor that delegates to specialist workers and synthesises their outputs
- Recognise that not every "worker" needs to be an LLM call — some are just deterministic functions with a clear right answer

**Real-world case — Banking:** A commercial bank automated its initial loan pre-screening workflow using exactly this supervisor-worker pattern, reducing the time from application submission to first eligibility decision from 3 business days to under 4 minutes for the majority of applications.

---

## 🧠 Concept Primer

### Why split this into a supervisor and two workers, instead of one agent doing everything?

Credit risk assessment and document completeness checking are genuinely different kinds of tasks. Credit assessment requires interpreting a repayment history narrative and forming a risk judgment — a good fit for an LLM's language understanding. Document completeness checking is a simple set comparison with ONE correct answer — required documents either were or weren't submitted. Splitting these into separate workers means each one can be built, tested, and reasoned about independently, and — as this exercise deliberately demonstrates — the RIGHT tool for each job isn't always "call an LLM."

### Why does the Document Verification Worker not use an LLM at all?

This is the most important design decision in this exercise. An LLM call for "does this list of submitted documents cover this list of required documents" would be slower, cost money, and introduce a small but real chance of an incorrect judgment on a task that a single line of set arithmetic (`required - submitted`) answers perfectly, every time, deterministically. Using an LLM here would be a worse engineering decision, not a more sophisticated one. Real multi-agent systems mix deterministic workers and LLM-based workers deliberately, based on which kind of reasoning each sub-task actually needs.

### What is the supervisor actually doing that a worker doesn't?

The supervisor never assesses credit risk or checks documents itself — its entire job is task decomposition (deciding what needs to happen and in what shape) and result synthesis (combining two independent, specialist findings into one coherent final recommendation with the right business logic — e.g., "any High credit risk means Decline, REGARDLESS of document completeness"). This separation of concerns is the essence of the supervisor-worker pattern.

---

## Step 1 — The dataset

`data/loan_applications.csv` — 4 applications with varying credit profiles and document completeness, deliberately including one applicant (APP004) missing a required document.

---

## Step 2 — Azure OpenAI setup

Needs one deployment (`AZURE_OPENAI_DEPLOYMENT`). See the package `README.md`.

---

## Step 3 — Code walkthrough

### Stage 1 — The deterministic Document Verification Worker

```python
def get_required_documents(requested_amount):
    required = ["income_proof.pdf", "id_proof.pdf"]
    if requested_amount > 20000:
        required.append("bank_statements_3months.pdf")
    if requested_amount > 40000:
        required.append("property_deed.pdf")
    return required

def document_verification_worker(application_row):
    submitted = set(d.strip() for d in application_row["submitted_documents"].split(","))
    required = set(get_required_documents(application_row["requested_amount"]))
    missing = required - submitted
    return {"required_documents": sorted(required), "missing_documents": sorted(missing), "complete": len(missing) == 0}
```

**What this does:** required documents scale with the requested loan amount (larger loans need more verification — a realistic business rule), and `required - submitted` is Python set subtraction, giving exactly the documents that are required but weren't submitted. **Verified directly against the dataset:** APP001, APP002, and APP003 all come back complete; APP004 correctly comes back missing `income_proof.pdf`.

### Stage 2 — The LLM-based Credit Assessment Worker

```python
CREDIT_WORKER_SYSTEM_PROMPT = """You are a Credit Assessment Worker... Your ONLY job is to assess credit risk
based on the credit score and repayment history provided. You do not see or consider document completeness —
that is a different worker's job."""

def credit_assessment_worker(client, deployment, application_row):
    user_prompt = f"Credit score: {application_row['credit_score']}\nRepayment history: {application_row['repayment_history_summary']}..."
    ...
```

**What this does:** notice the system prompt explicitly tells this worker what it does NOT consider — document completeness. This is deliberate role isolation: each worker should reason ONLY about its own specialty, so its output is a clean, focused judgment the supervisor can trust and combine, rather than a worker trying (and potentially failing) to reason about things outside its assigned scope.

### Stage 3 — The supervisor synthesises both findings

```python
SUPERVISOR_SYSTEM_PROMPT = """... Synthesise their findings into ONE final recommendation: "Approve",
"Conditional Approval" (if documents are missing but credit risk is Low or Medium), or "Decline"
(if credit risk is High, regardless of documents)."""

def supervisor_synthesize(client, deployment, credit_result, doc_result, application_row):
    user_prompt = f"Credit Assessment Worker report:\n{credit_result}\n\nDocument Verification Worker report:\n  Complete: {doc_result['complete']}..."
```

**What this does:** the supervisor's prompt encodes the actual BUSINESS LOGIC for combining two workers' findings (a specific priority rule: high credit risk always declines, regardless of documents) — this decision logic lives at the supervisor level, not inside either worker, which is exactly the "task decomposition, delegation, quality control" role described in the theory session for supervisor agents.

---

## Expected Output (illustrative)

```
APPLICATION APP004: David Chen (requesting $10000)

-- Supervisor delegates to Document Verification Worker (deterministic) --
Required: ['id_proof.pdf', 'income_proof.pdf']
Missing:  ['income_proof.pdf']

-- Supervisor delegates to Credit Assessment Worker (LLM) --
Risk Level: High
Reasoning: A credit card currently 45 days past due combined with no other credit history is a significant red flag.

-- Supervisor synthesises final recommendation --
Recommendation: Decline
David Chen's application should be declined due to High credit risk (a currently past-due account), which
overrides any consideration of the missing income proof document — the credit risk finding alone is
sufficient grounds for decline per policy.
```
*(The Document Verification Worker's output above is verified exact — directly tested against this dataset. The Credit Assessment Worker and Supervisor outputs are illustrative of the expected reasoning pattern; exact wording depends on the live model.)*

---

## 🛠 Common Pitfalls

- **Letting a worker see information outside its scope:** if the Credit Assessment Worker's prompt accidentally included document completeness info, its "risk" judgment could get contaminated by an unrelated factor — keep worker inputs strictly scoped to what that worker is responsible for.
- **Putting business logic inside a worker instead of the supervisor:** if you asked the Credit Assessment Worker to also decide "approve or decline," you'd lose the clean separation — the WORKER assesses, the SUPERVISOR decides, using both workers' findings together.
- **Assuming every worker needs to be "AI":** the biggest lesson of this exercise is the opposite — always ask whether a sub-task has a single deterministically correct answer before reaching for an LLM call.

---

## 🏠 Homework Exercise

1. Add a 3rd worker: an **Income Verification Worker** — add an `income_bracket` or `monthly_income` column to a new applicant row in `data/loan_applications.csv`, and decide whether this worker should be deterministic (like Document Verification) or LLM-based (like Credit Assessment). Justify your choice in a comment.
2. Wire it into the supervisor's synthesis step alongside the existing two workers.
3. Update the supervisor's business logic (in `SUPERVISOR_SYSTEM_PROMPT`) to incorporate the new worker's finding into the final recommendation — e.g., "Decline regardless of credit risk if income is below a certain threshold relative to the requested amount."

**Hints:**
- Income-to-loan-ratio checks are usually a great candidate for a deterministic worker (a simple ratio calculation), similar to Document Verification — but if you wanted the worker to also assess income STABILITY from a free-text employment description, that part would lean LLM-based. You could even split this into two workers if you wanted to practice the "one worker, one clear responsibility" principle further.
