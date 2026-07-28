from llm_client import ask

#offile evalution - 

test_set = [
    {"question": "What is the capital of France?","expected_answer":"Paris"},
    {"question": "what is 12 * 12?", "expected_answer":"144"},
]

offline_results =[]

for case in test_set:
    actual = ask("Answer concisely.", case["question"])
    passed = case["expected_answer"].lower() in actual.lower()
    offline_results.append(passed)
    print(f"Q: {case['question']} | Expected: {case['expected_answer']}| Got:{actual.strip()} | {'PASS' if passed else 'FAIL'}")

print(f"offline pass rate:{sum(offline_results)}/{len(offline_results)}")

###-----------OUTPUT----------------###
"""
Q: What is the capital of France? | Expected: Paris| Got:Paris. | PASS
Q: what is 12 * 12? | Expected: 144| Got:144 | PASS
offline pass rate:2/2
"""
###----------DONE-----------------###