from llm_client import ask, embed
from vector_math import cosine_similarity

#short-memory - simple in-context scratchpad

print("short-memory")

scratchpad =[]

def remember(note):
    scratchpad.append(note)

remember("User's name is Priya.")
remember("User is asking about the premium plan.")

context = "\n".join(scratchpad)
answer = ask("Use this scratchpad as context.", f"{context}\n\nQuestion: What's my name?")
print(answer)

#converstional -memory 

print("converstional -memory")

full_history =[
    "User: I'm looking for a lptop for video editing.",
    "Assistant: Great, What's your budget?",
    "User: Around $1500.",
    "Assistant: I'd recommend something with 16GB+ RAM and dedicated GPU.",
    "User: Does that come in a lighter model too?",
]

summary=ask(
    "Summrize this conversation so far in 1 sentence, keeping only what's need to continue helping the user.",
    "\n".join(full_history[:-1])
)

print(summary)

latest_message = full_history[-1]
reply = ask("Continue the conversation using this summary as context.", f"{summary}\n\n{latest_message}")
print(reply)

#vector - memory

print("vector - memory")

past_memories =[
    "User previously said they prefer aisle seats when booking flights.",
    "User previously mentioned they're vegetarian.",
    "User previously asked about refund policies for hotel bookings.",
]

memory_vectors =[embed(m) for m in past_memories]

new_question = "Can you help me book a flight?"

question_vector = embed(new_question)

best_memory = max(
    zip(past_memories, memory_vectors),
    key = lambda pair: cosine_similarity(question_vector, pair[1])
)[0]
print(best_memory)
answer = ask ("Use this remembered fact if relevant,", f"Memory {best_memory}\n\nQuestion {new_question}")
print(answer)

###-------------OUTPUT------------------###
"""
short-memory
Your name is Priya.
converstional -memory
The user wants a laptop for video editing with a budget of around $1500, and we’ve already noted they should look for at least 16GB RAM and a dedicated GPU.
Yes—if you want something lighter for video editing around $1500, there are definitely options, but there’s usually a tradeoff:

- lighter laptop = easier to carry
- heavier laptop = usually better cooling and stronger sustained performance

For a lighter model, I’d look for:

- 14" or lightweight 15" chassis
- at least 16GB RAM
- dedicated GPU if possible
- Ryzen 7 / Intel i7 or better
- good color-accurate display if you edit video seriously

Some lighter types to consider:
- ASUS Zephyrus G14 — well-known for being portable and still powerful
- Lenovo Slim Pro 7 / 9 series — lighter creator-style laptops
- Acer Swift X — often a good balance of weight, GPU, and price
- ASUS Vivobook Pro 14/15 — relatively portable with creator-focused specs

If you want, I can narrow it down to:
1. best lightest option,
2. best battery life,
3. best editing performance under $1500.
vector - memory
User previously said they prefer aisle seats when booking flights.
Absolutely — I can help you book a flight.

I’ll also keep in mind that you prefer an aisle seat.

Please send me:
1. Departure city or airport
2. Destination city or airport
3. Departure date
4. Return date, if round trip
5. Number of travelers
6. Cabin class, if you have a preference
7. Any airline, budget, or time preferences

If you want, you can send it in one line like:
“NYC to London, Sept 12–19, 1 traveler, economy, under $800, nonstop preferred.”
"""
###-------------DONE------------------###