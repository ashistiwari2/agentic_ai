import json 
from llm_client import ask

#golden dataset - human curated - trused q/a pairs

golden_dataset =[
    {"question":"what is our return policy?", "golden_answer":"Returns are accepted within 30 days with a receipt.","source":"handbook.txt"},
    {"question":"How long does shipping take?","golden_answer":"Standard shipping take 3-5 business days.","source":"handbook.txt"},
]

print(json.dumps(golden_dataset, indent=2))

#synthetic test set generation - using an llm to generate mose cases

source_document = (
    "Warranty Policy: All electronics come with a 1-year manufacturer warranty covering defects in materials and workmanship. The warranty doesn't cover accidental damage or water damage."
)

synthetic_qa_raw = ask(
    "Generate 3 diverse question/answer pairs a customer might ask about this document. Return ONLY JSON: a list of object with 'question' and 'golden_answer' keys.", source_document
)

print("generated synthetic test cases:")
print(synthetic_qa_raw)

try: 
    synthetic_qa = json.loads(synthetic_qa_raw)
    golden_dataset.extend(synthetic_qa)
    print(f"\nGolden dataset now has {len(golden_dataset)} cases (2 human + {len(synthetic_qa)} synthetic).")
except json.JSONDecodeError:
    print("(Model didn't return clean JSON this time -- add stricter formatting instructions if this happens often.)")

###-----------OUTPUT-------------------###
"""
[
  {
    "question": "what is our return policy?",
    "golden_answer": "Returns are accepted within 30 days with a receipt.",
    "source": "handbook.txt"
  },
  {
    "question": "How long does shipping take?",
    "golden_answer": "Standard shipping take 3-5 business days.",
    "source": "handbook.txt"
  }
]
generated synthetic test cases:
[
  {
    "question": "How long is the warranty for electronics?",
    "golden_answer": "All electronics come with a 1-year manufacturer warranty."
  },
  {
    "question": "What does the warranty cover?",
    "golden_answer": "The warranty covers defects in materials and workmanship."
  },
  {
    "question": "Does the warranty include accidental or water damage?",
    "golden_answer": "No. The warranty does not cover accidental damage or water damage."
  }
]

Golden dataset now has 5 cases (2 human + 3 synthetic).
"""
###----------DONE----------------------###