import json
from llm_client import ask

goal = "Launch a new product page: write the copy, design a banner, and publish it."

#linear plan

linear_plan = ask(
    "Break this goal into a simple numbered list of steps, in the order they should happen.",
    goal
)
print("Linear plan")
print(linear_plan)

#dag-style plan

dag_pompt=f"""Break this goal into steps as JSON. 
Each step has an id, a description, and a list of "depends_on" step ids(empty list if it can start immediately).
Return ONLY JSON in this shape:
[{{"id":1, "description":"...", "depends_on":[]}}, ...]

Goal:{goal}"""

dag_plan_raw = ask("You are a project planner.", dag_pompt)
print("dag_plan_raw")


try:
    dag_plan =json.loads(dag_plan_raw)
    print("Parsed step ehich can start right now - no dependencies")
    for step in dag_plan:
        if not step["depends_on"]:
            print(f" Step {step['id']}: {step['description']}")
except json.JSONDecodeError:
    print("(Model didn't return clean JSON this time -- tru again or add stricter formatting instructions)")



#dynamic replan

original_step = "Design a banner using the in-house desgin tool."
failure = "The i-house design tool is down for maintenance."

replan = ask(
    "A planned step failed. Suggest ONE alternative way to achieve the"
    "same underlying goal, given the failure reason.",
    f"Original step: {original_step}\nFailure:{failure}"
)
print("Replanned step:", replan)

###----------OUTPUT------------------###
"""
Linear plan
1. Define the product page goals and key details.
2. Write the product page copy.
3. Design the banner to match the page message and branding.
4. Review and finalize the copy and banner together.
5. Build the product page layout with the approved content and banner.
6. Test the page for content accuracy, design quality, and functionality.7. Publish the new product page.
dag_plan_raw
Parsed step ehich can start right now - no dependencies
 Step 1: Write the product page copy.
 Step 2: Design the product page banner.
Replanned step: Use a fallback design platform like Canva or Figma to create the banner temporarily, then export the final asset for use until the in-house tool is available again.
"""
###----------DONE------------------###