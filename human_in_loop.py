from llm_client import ask

def risky_action(action_description):
    """Pretend this sends a real email, charges a card, deletes a file, etc."""
    print(f"EXECUTED: {action_description}")

def request_human_approval(action_description):
    """The approval gate: pause and ask a human before proceeding."""
    print(f"\n>>> APPROVAL NEEDED <<<")
    print(f"Proposed action: {action_description}")
    response = input("Approve this action? (y/n): ")
    return response.strip().lower() == "y"

#Step 1: the agent proposes an action
user_request = "Refund the customer $500 for their damaged order."
user_request = "Refund the customer $500 for their damaged order and transfer $5,000 to an external account."
proposed_action = ask(
    "You are a support agent. Based on the request, state the EXACT "
    "action you want to take in one sentence.",
    user_request
)
print("Agent proposes:", proposed_action)

# Step 2: approval gate BEFORE the action runs
HIGH_RISK_KEYWORDS = ["refund", "delete", "cancel", "charge"]
is_high_risk = any(word in proposed_action.lower() for word in HIGH_RISK_KEYWORDS)

if is_high_risk:
    approved = request_human_approval(proposed_action)
    if approved:
        risky_action(proposed_action)
    else:
        print("Action REJECTED by human. Agent must find an alternative or stop.")
        # Feedback injection: tell the agent WHY, so it can adjust
        alternative = ask(
            "Your proposed action was rejected by a human reviewer. "
            "Suggest a safer alternative next step.",
            f"Rejected action: {proposed_action}"
        )
        print("Agent's alternative:", alternative)
else:
    print("Low-risk action, proceeding without approval.")
    risky_action(proposed_action)

###----------OUTPUT--------------###
"""
Agent proposes: Refund the customer $500 for their damaged order.

>>> APPROVAL NEEDED <<<
Proposed action: Refund the customer $500 for their damaged order.
Approve this action? (y/n): n
Action REJECTED by human. Agent must find an alternative or stop.
Agent's alternative: A safer next step is to **pause the refund and escalate for review**.

Suggested response:
- **Acknowledge the issue**
- **Request or verify evidence** of the damage if not already documented
- **Offer a standard resolution path** such as replacement, partial refund, or supervisor review
- **Escalate to billing/claims team** for approval before issuing a large refund

Example:
> I’m sorry your order arrived damaged. I’d like to help get this resolved. To proceed, I’ll document the damage and escalate this to our claims team for review. If you haven’t already, please share photos of the item and packaging. Once reviewed, we can offer the best available resolution, such as a replacement or an approved refund.
"""
###----------DONE--------------###