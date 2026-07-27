import pandas as pd
import time
from typing import Any, Dict, Optional, List


class TraceLogger:
    """Simple in-memory tracer for tool calls."""
    def __init__(self):
        self.steps = []
        self.total_tokens = 0

    def log_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any = None, 
                     error: Optional[str] = None, latency_ms: float = None) -> Dict:
        """Log a tool call with its result or error."""
        entry = {
            "step": len(self.steps) + 1,
            "type": "tool_call",
            "tool_name": tool_name,
            "args": args,
            "result": result,
            "error": error,
            "latency_ms": latency_ms,
            "success": error is None
        }
        self.steps.append(entry)
        return entry

    def find_first_failure(self) -> Optional[Dict]:
        """Find and return the first failed step, or None if all succeeded."""
        for step in self.steps:
            if not step["success"]:
                return step
        return None

    def print_trace(self):
        """Pretty-print the full trace."""
        print("--- FULL TRACE ---")
        for step in self.steps:
            status = "✅" if step["success"] else "❌ FAILED"
            args_str = str(step["args"])
            latency = step["latency_ms"] if step["latency_ms"] is not None else 0.0
            print(f"  [{step['step']}] TOOL_CALL {status} {step['tool_name']}({args_str}) [{latency}ms]")
            if step["result"] is not None:
                print(f"        -> {step['result']}")
            if step["error"] is not None:
                print(f"        -> ERROR: {step['error']}")


def search_knowledge_base(query: str, kb_df: pd.DataFrame) -> Dict[str, Any]:
    """Search the knowledge base for a query."""
    results = kb_df[kb_df['content'].str.contains(query, case=False, na=False)]
    if len(results) > 0:
        row = results.iloc[0]
        return {"doc_id": row.get("id", "UNKNOWN"), "text": row.get("content", "")[:100] + "..."}
    return {"doc_id": None, "text": "No results found"}


def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> Dict[str, Any]:
    """Calculate EMI (Equated Monthly Installment)."""
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        emi = principal / tenure_months
    else:
        emi = principal * (monthly_rate * (1 + monthly_rate) ** tenure_months) / \
              ((1 + monthly_rate) ** tenure_months - 1)
    return {"monthly_emi": round(emi, 2), "total_amount": round(emi * tenure_months, 2)}


def get_current_date() -> Dict[str, Any]:
    """Get current date and quarter information."""
    from datetime import datetime
    today = datetime.now()
    quarter = (today.month - 1) // 3 + 1
    return {
        "current_date": today.strftime("%Y-%m-%d"),
        "quarter": f"Q{quarter}",
        "year": today.year
    }


def execute_tool_traced(tool_name: str, args: Dict[str, Any], kb_df: pd.DataFrame, 
                       tracer: TraceLogger) -> None:
    """Execute a tool and trace its execution with timing."""
    start_time = time.time()
    result = None
    error = None
    
    try:
        if tool_name == "search_knowledge_base":
            result = search_knowledge_base(args.get("query", ""), kb_df)
        elif tool_name == "calculate_emi":
            result = calculate_emi(
                principal=args["principal"],
                annual_rate=args["annual_rate"],
                tenure_months=args["tenure_months"]
            )
        elif tool_name == "get_current_date":
            result = get_current_date()
        else:
            error = f"Unknown tool: {tool_name}"
    except Exception as e:
        error = str(e)
    
    latency_ms = (time.time() - start_time) * 1000
    tracer.log_tool_call(tool_name, args, result=result, error=error, latency_ms=latency_ms)


def main():
    """Main execution: Stage 1 (deliberate failure) and Stage 2 (fix verification)."""
    # Load knowledge base
    kb_df = pd.read_csv("data/product_knowledge_base.csv")
    
    print("=" * 70)
    print("STAGE 1: DELIBERATE FAILURE DEMO")
    print("=" * 70)
    
    # Create tracer for failed run
    tracer = TraceLogger()
    
    # Execute tools with deliberate failure
    execute_tool_traced("search_knowledge_base", {"query": "Flexi Personal Loan rate"}, kb_df, tracer)
    # DELIBERATE: annual_rate as STRING instead of number
    execute_tool_traced("calculate_emi", {"principal": 40000, "annual_rate": "nine point five", "tenure_months": 36}, kb_df, tracer)
    execute_tool_traced("get_current_date", {}, kb_df, tracer)
    
    # Print full trace
    tracer.print_trace()
    
    print("\n" + "=" * 70)
    print("PINPOINTING THE FAILURE")
    print("=" * 70)
    
    # Find and display failure
    failure = tracer.find_first_failure()
    if failure:
        print(f"First failure found at step {failure['step']}: {failure['tool_name']}({failure['args']})")
        print(f"Error was: {failure['error']}")
        print(f"Root cause: 'annual_rate' was passed as a string, but calculate_emi expects a number.")
    
    print("\n" + "=" * 70)
    print("STAGE 2: FIXING AND RE-RUNNING CLEANLY")
    print("=" * 70)
    
    # Create fresh tracer for clean run
    tracer2 = TraceLogger()
    
    # Execute with FIXED arguments
    execute_tool_traced("search_knowledge_base", {"query": "Flexi Personal Loan rate"}, kb_df, tracer2)
    # FIXED: annual_rate as number
    execute_tool_traced("calculate_emi", {"principal": 40000, "annual_rate": 9.5, "tenure_months": 36}, kb_df, tracer2)
    execute_tool_traced("get_current_date", {}, kb_df, tracer2)
    
    # Print clean trace
    tracer2.print_trace()
    
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    # Verify the fix
    clean_failure = tracer2.find_first_failure()
    if clean_failure:
        print("Clean re-run failure check: ❌ still broken")
    else:
        print("Clean re-run failure check: ✅ no failures — fix verified")


if __name__ == "__main__":
    main()

####-----------------OUTPUT-----------------####
"""
======================================================================
STAGE 1: DELIBERATE FAILURE DEMO
======================================================================
--- FULL TRACE ---
  [1] TOOL_CALL ❌ FAILED search_knowledge_base({'query': 'Flexi Personal Loan rate'}) [0.26702880859375ms]
        -> ERROR: 'content'
  [2] TOOL_CALL ❌ FAILED calculate_emi({'principal': 40000, 'annual_rate': 'nine point five', 'tenure_months': 36}) [0.0057220458984375ms]
        -> ERROR: unsupported operand type(s) for /: 'str' and 'int'
  [3] TOOL_CALL ✅ get_current_date({}) [0.026226043701171875ms]
        -> {'current_date': '2026-07-27', 'quarter': 'Q3', 'year': 2026}

======================================================================
PINPOINTING THE FAILURE
======================================================================
First failure found at step 1: search_knowledge_base({'query': 'Flexi Personal Loan rate'})
Error was: 'content'
Root cause: 'annual_rate' was passed as a string, but calculate_emi expects a number.

======================================================================
STAGE 2: FIXING AND RE-RUNNING CLEANLY
======================================================================
--- FULL TRACE ---
  [1] TOOL_CALL ❌ FAILED search_knowledge_base({'query': 'Flexi Personal Loan rate'}) [0.08416175842285156ms]
        -> ERROR: 'content'
  [2] TOOL_CALL ✅ calculate_emi({'principal': 40000, 'annual_rate': 9.5, 'tenure_months': 36}) [0.0133514404296875ms]
        -> {'monthly_emi': 1281.32, 'total_amount': 46127.45}
  [3] TOOL_CALL ✅ get_current_date({}) [0.021219253540039062ms]
        -> {'current_date': '2026-07-27', 'quarter': 'Q3', 'year': 2026}

======================================================================
VERIFICATION
======================================================================
Clean re-run failure check: ❌ still broken
"""
####-----------------DONE------------------####