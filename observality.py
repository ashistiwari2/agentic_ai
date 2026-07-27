import time
import json

from llm_client import ask

#trace logger

trace = []

def log_step(step_type, detail, duration=None):
    entry={
        "step":len(trace) + 1,
        "type": step_type,
        "detail":detail,
        "duration_sec": round(duration, 3) if duration else None,
    }
    trace.append(entry)

#run a small multip-step task while tacing every step

def traced_ask(system_prompt, user_prompt, step_label):
    start = time.time()
    result = ask(system_prompt, user_prompt)
    duration = time.time() -start
    log_step(step_label, {"input":user_prompt, "output":result},duration)
    return result

user_goal = "Draft a short apology email for a delayed shipment"

log_step("start", {"goal":user_goal})

draft = traced_ask("Write a short, professional apology email.",user_goal,"generate")
review = traced_ask("Point out ONE thing to improve in this email, briefly",draft,"review")
final = traced_ask(f"Improve the email based on this feedback:{review}", draft, "revise")

log_step("end", {"final_output":final})

#print the trace like a debug tool 

print("agent trace")
for entry in trace:
    print(f"\nStep {entry['step']} [{entry['type']}] ({entry['duration_sec']}s)")
    print(json.dumps(entry["detail"], indent=2)[:300])

#token cost -tracing

print("cost attribution")
total_calls = sum(1 for e in trace if e["type"]in ("generate", "review", "revise"))
print(f"Total model calls this ran:{total_calls}")

####-----------------OUTPUT-----------------####
"""
agent trace

Step 1 [start] (Nones)
{
  "goal": "Draft a short apology email for a delayed shipment"
}

Step 2 [generate] (3.915s)
{
  "input": "Draft a short apology email for a delayed shipment",
  "output": "Subject: Apology for Your Delayed Shipment\n\nDear [Customer Name],\n\nI sincerely apologize for the delay with your shipment. We understand how frustrating this can be and regret any inconvenience caused.\n\nOur team is

Step 3 [review] (2.608s)
{
  "input": "Subject: Apology for Your Delayed Shipment\n\nDear [Customer Name],\n\nI sincerely apologize for the delay with your shipment. We understand how frustrating this can be and regret any inconvenience caused.\n\nOur team is actively working to resolve the issue and ensure your order reach

Step 4 [revise] (2.647s)
{
  "input": "Subject: Apology for Your Delayed Shipment\n\nDear [Customer Name],\n\nI sincerely apologize for the delay with your shipment. We understand how frustrating this can be and regret any inconvenience caused.\n\nOur team is actively working to resolve the issue and ensure your order reach

Step 5 [end] (Nones)
{
  "final_output": "Subject: Update and Apology for Your Delayed Shipment\n\nDear [Customer Name],\n\nI sincerely apologize for the delaywith your shipment. Due to unexpected carrier issues, your order has taken longer than originally anticipated. We understand how frustrating this can be and regr
cost attribution
Total model calls this ran:3
"""
####-----------------DONE-------------------####
