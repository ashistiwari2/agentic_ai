#employee - expense reimbursment = request - policy - budget

from agent_core import run_agent
from llm_client import ask

POLICY_LIMITS = {"travel": 1000, "meals": 100, "equipment": 500}
DEPARTMENT_BUDGETS = {"engineering": 2500, "sales": 800}

decision_log={}

def check_policy_limit(category: str, amount:float) -> str:
    limit = POLICY_LIMITS.get(category)
    if limit is None:
        return f"No policy found for category '{category}'."
    if amount <=limit:
        return f"Within policy: ${amount} is under the ${limit} limit for {category}."
    return f"EXCEEDS policy: ${amount} is over the ${limit} limit for {category}."

def check_budget_remaining(department: str) -> str:
    remaining = DEPARTMENT_BUDGETS.get(department)
    if remaining is None:
        return f"No budget record found for department '{department}'."
    return f"{department} has ${remaining} remaining this quarter."

def log_decision(request_id: str, decision: str) -> str:
    if request_id in decision_log:
        return f"Request {request_id} already logged as {decision_log[request_id]} (skipping duplicate.)"
    decision_log[request_id] =decision
    return f"Logged decision for {request_id}: {decision}"

POLICY_TOOL = {
    "type":"function","name":"check_policy_limit",
    "description":"Check if an expense amount is within company policy for its category.",
    "parameters":{"type":"object", "properties":{
        "category":{"type":"string", "description":"travel, meals, or equipment"},
        "amount":{"type":"number"},
    }, "required":["category","amount"]},
}

BUDGET_TOOL = {
    "type":"function","name":"check_budget_remaining",
    "description":"Check how much budget a department has left this quarter.",
    "parameters":{"type":"object", "properties":{
        "department":{"type":"string", "description":" e.g. 'engineering' "},
    }, "required":["department"]},
}

LOG_TOOL = {
    "type":"function","name":"log_decision",
    "description":"Log the final decision for a reimbursement request.",
    "parameters":{"type":"object", "properties":{
        "request_id":{"type":"string"},
        "decision":{"type":"string", "description":" e.g. 'approved' or 'rejected'"},
    }, "required":["request_id","decision"]},
}

request = "Request EXP-201: $650 equipment purchase for the engineering department."

#Single-agent architecture

print("A single agent(has every tool)")

single_agent_answer = run_agent(
    system_prompt="You process expense reimbursements. Check policy AND budget, then log your decision.",
    user_request= request,
    tools=[POLICY_TOOL, BUDGET_TOOL, LOG_TOOL],
    tool_functions={
        "check_policy_limit": check_policy_limit,
        "check_budget_remaining": check_budget_remaining,
        "log_decision": log_decision,
    },
)
print("Result:" , single_agent_answer)

#multi-agent architecture

print("Multi-agent (each with one tool)")

policy_agent_finding = run_agent(
    system_prompt="You ONLY check policy compliance for expense requests. Report your finding.",
    user_request= request,
    tools=[POLICY_TOOL],
    tool_functions={
        "check_policy_limit": check_policy_limit,
    },
)


budget_agent_finding = run_agent(
    system_prompt="You ONLY check deparment budget for expense request. Report your finding.",
    user_request= request,
    tools=[BUDGET_TOOL],
    tool_functions={
        "check_budget_remaining": check_budget_remaining
    },
)

print("policy agent finding:", policy_agent_finding)
print("budget agent finding:", budget_agent_finding)

combined_decision = ask(
    "Given these two indepent findings, decide APPROVE or REJECT, with a one-sentence reason.",
    f"Policy finding: {policy_agent_finding}\nBudget finding:{budget_agent_finding}"
)
print("Combined decision:", combined_decision)

#planner-executor architecture

print("planner -executor")

plan = ask(
    "Break down how to process this expense request into a short numbered"
    "list of checks that need to happen before a decision can be made.",
    request
)
print("plan:\n" ,plan)

executor_answer = run_agent(
    system_prompt=f"Follow this plan using your tools, then give a final APPROVE/REJECT decision:\n{plan}",
    user_request= request,
    tools=[POLICY_TOOL, BUDGET_TOOL, LOG_TOOL],
    tool_functions={
        "check_policy_limit": check_policy_limit,
        "check_budget_remaining": check_budget_remaining,
        "log_decision": log_decision,
    },
)
print("\nExecutor result:", executor_answer)

#Supervisor-worker architecture 

print("supervisor-worker")

worker_a_result = run_agent(
    "You are Worker A: policy complinace specialist.", request,
    [POLICY_TOOL],{"check_policy_limit": check_policy_limit}
)

worker_b_result = run_agent(
    "You are Worker B: budget specialist.", request,
    [BUDGET_TOOL], {"check_budget_remaining":check_budget_remaining},
)

supervisor_review = run_agent(
    system_prompt=(
        "You are the supervisor. Review both workers' findings below,"
        "make a final APPROVE/REJECT call, anf log it.\n"
        f"Worker A(policy): {worker_a_result}"
        f"Worker B(budget): {worker_b_result}"
    ),
    user_request=request,
    tools=[LOG_TOOL],
    tool_functions={"log_decision": log_decision},
)

print(supervisor_review)

##--------OUTPUT---------------#
"""
A single agent(has every tool)
[iteration 1] Agent calls: check_policy_limit({'category': 'equipment', 'amount': 650})
    -> result: EXCEEDS policy: $650 is over the $500 limit for equipment.
[iteration 1] Agent calls: check_budget_remaining({'department': 'engineering'})
    -> result: engineering has $2500 remaining this quarter.
[iteration 2] Agent calls: log_decision({'request_id': 'EXP-201', 'decision': 'rejected'})
    -> result: Logged decision for EXP-201: rejected
[iteration 3] Agent gave a final answer (no more tools needed).
Result: Request EXP-201 is rejected.

- Policy: equipment limit is $500, and $650 exceeds it.
- Budget: engineering has $2500 remaining, but policy violation means it cannot be approved.

Decision logged as rejected.
Multi-agent (each with one tool)
[iteration 1] Agent calls: check_policy_limit({'category': 'equipment', 'amount': 650})
    -> result: EXCEEDS policy: $650 is over the $500 limit for equipment.
[iteration 2] Agent gave a final answer (no more tools needed).
[iteration 1] Agent calls: check_budget_remaining({'department': 'engineering'})
    -> result: engineering has $2500 remaining this quarter.
[iteration 2] Agent gave a final answer (no more tools needed).
policy agent finding: EXP-201: Not compliant. The $650 equipment expense exceedsthe $500 equipment policy limit.
budget agent finding: Engineering has $2,500 remaining this quarter.

For request EXP-201 ($650 equipment purchase), the department appears to have sufficient budget remaining.
Combined decision: REJECT — Although Engineering has sufficient budget remaining, EXP-201 is not compliant because the $650 equipment expense exceeds the $500 equipment policy limit.
planner -executor
plan:
 1. Confirm the request details: EXP-201, amount $650, equipment purchase, engineering department.  
2. Verify the business purpose and that the equipment is necessary for department operations.  
3. Check whether the purchase fits within the engineering department’s approved budget.  
4. Confirm the correct expense category/accounting treatment for equipment.  
5. Review company purchasing policy for any limits, approval thresholds, or required procurement steps at $650.  
6. Check whether quotes, vendor selection, or preferred supplier rules apply.  
7. Verify that the requester has authority to submit the expense and identify who must approve it.  
8. Ensure supporting documentation is available, such as item description, price, and vendor information.  
9. Check for tax, shipping, or other extra costs that may affect the total amount.  
10. Once all checks are complete, route for the required approval or decline if any policy/budget requirement is not met.
[iteration 1] Agent calls: check_policy_limit({'category': 'equipment', 'amount': 650})
    -> result: EXCEEDS policy: $650 is over the $500 limit for equipment.
[iteration 1] Agent calls: check_budget_remaining({'department': 'engineering'})
    -> result: engineering has $2500 remaining this quarter.
[iteration 2] Agent calls: log_decision({'request_id': 'EXP-201', 'decision': 'rejected'})
    -> result: Request EXP-201 already logged as rejected (skipping duplicate.)
[iteration 3] Agent gave a final answer (no more tools needed).

Executor result: REJECT

- Request: EXP-201
- Amount: $650
- Category: equipment
- Department: engineering

Findings:
- Budget: engineering has $2500 remaining this quarter, so budget is sufficient.
- Policy: equipment purchases over $500 exceed company policy limit. At $650, this request is over the allowed limit.

Because the request fails the equipment policy threshold, it cannot be approved as submitted.  
If needed, it should be rerouted through the required higher-level procurement/approval process rather than reimbursed directly.
supervisor-worker
[iteration 1] Agent calls: check_policy_limit({'category': 'equipment', 'amount': 650})
    -> result: EXCEEDS policy: $650 is over the $500 limit for equipment.
[iteration 2] Agent gave a final answer (no more tools needed).
[iteration 1] Agent calls: check_budget_remaining({'department': 'engineering'})
    -> result: engineering has $2500 remaining this quarter.
[iteration 2] Agent gave a final answer (no more tools needed).
[iteration 1] Agent calls: log_decision({'request_id': 'EXP-201', 'decision': 'rejected'})
    -> result: Request EXP-201 already logged as rejected (skipping duplicate.)
[iteration 2] Agent gave a final answer (no more tools needed).
REJECT — exceeds the $500 equipment policy limit, even though budget is available.
"""
###----------------------DONE-------------------------#####