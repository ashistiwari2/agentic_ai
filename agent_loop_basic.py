from agent_core import run_agent

tickets={

    "IT-4521":{"issue":"Email service down","status":"open", "service":"email-service"},

}

service_health ={"email-service":"unhealthy", "vpn=service":"healthy"}

def check_ticket_status(ticket_id:str) -> str:

    ticket = tickets.get(ticket_id)

    if not ticket:

        return f"No ticket found with ID {ticket_id}."

    return f"Ticket {ticket_id}:{ticket['issue']} (status:{ticket['status']}, service: {ticket['service']})"

def check_service_health(service_name: str) -> str:

    status = service_health.get(service_name,"unknown")

    return f"{service_name} is currently {status}."

def restart_service(service_name: str) -> str:

    service_health[service_name] = "healthy"

    return f"{service_name} has been restarted and is now healthy."

def escalate_to_human(reason:str) -> str:

    return f"Escalated to human support team. Reason:{reason}"

tool_functions = {

    "check_ticket_status":check_ticket_status,

    "check_service_health":check_service_health,

    "restart_service":restart_service,

    "escalate_to_human": escalate_to_human,

}

tools = [

    {

        "type":"function", "name":"check_ticket_status",

        "description":"Look up the details and status of support ticket by ID.",

        "parameters":{"type":"object","properties":{

            "ticket_id":{"type":"string", "description" :"e.g. 'IT-4521'"}

        }, "required":["ticket_id"]},

    },

    {

        "type":"function", "name":"check_service_health",

        "description":"Check whether a specific service is currently healthy or unhealthy",

        "parameters":{"type":"object","properties":{

            "service_name":{"type":"string", "description" :"e.g. 'email-service'"}

        }, "required":["service_name"]},

    },

    {

        "type":"function", "name":"restart_service",

        "description":"Restart a specific service to attempt to fix a health issue. Only use this if the service is confirmed unhealthy.",

        "parameters":{"type":"object","properties":{

            "service_name":{"type":"string"}

        }, "required":["service_name"]},

    },

    {

        "type":"function", "name":"escalate_to_human",

        "description":"Escalate the issue to a human when it cannot be resolved with the available tools.",

        "parameters":{"type":"object","properties":{

            "reason":{"type":"string", "description" :"why this needs human attention"}

        }, "required":["reason"]},

    },

]

system_prompt =(

    "You are an IT helpdesk agent. Given a user's issue, investigate using"

    "the available tools, take corrective action if you can, and only"

    "escalate to a human if the tools can't resolve it. Explain what you"

    "did in you final answer."

)

user_request ="My email isn't working, ticket IT-4521. Can you look into it?"

print("running the agent now\n")

final_answer = run_agent(system_prompt, user_request, tools, tool_functions)

print("final answer")

print(final_answer)

###----------OUTPUT------------------###
"""
running the agent now

[iteration 1] Agent calls: check_ticket_status({'ticket_id': 'IT-4521'})
    -> result: Ticket IT-4521:Email service down (status:open, service: email-service)
[iteration 1] Agent calls: check_service_health({'service_name': 'email-service'})
    -> result: email-service is currently unhealthy.
[iteration 2] Agent calls: restart_service({'service_name': 'email-service'})
    -> result: email-service has been restarted and is now healthy.
[iteration 3] Agent gave a final answer (no more tools needed).
final answer
I checked ticket IT-4521 and confirmed it was related to the email service being down.

What I did:
- Verified the ticket status: `open`
- Checked `email-service` health: it was `unhealthy`
- Restarted `email-service`
- Confirmed it is now `healthy`

Your email should be working again now. Please try it once more, and if you're still having issues, let me know and I'll investigate further.
"""
###----------DONE------------------###