import pandas as pd

# Configuration
APPROVAL_THRESHOLD = 10000
SUSPICIOUS_MEMO_PHRASES = ["urgent", "per phone instructions", "asap"]

# Stage 1 — Automatic risk-signal flagging
def flag_risk_signals(row):
    signals = []
    if row["amount"] > 100000:
        signals.append(f"very large amount (${row['amount']:,})")
    memo_lower = str(row["memo"]).lower()
    for phrase in SUSPICIOUS_MEMO_PHRASES:
        if phrase in memo_lower:
            signals.append(f"memo contains suspicious phrase: '{phrase}'")
    if "unknown" in str(row["recipient_name"]).lower():
        signals.append("recipient name suggests an unverified/unfamiliar party")
    return signals

# Stage 2 — The interrupt point itself
def get_human_decision(summary_text):
    print(f"\n{summary_text}")
    decision = input("\nApprove, Reject, or Modify this transfer? [a/r/m]: ")
    return decision

# Stage 3 — Deciding based on the human's actual response
def process_decision(decision, row):
    decision = decision.strip().lower()
    if decision == "a":
        return f"✅ APPROVED — transfer {row['transfer_id']} would now be executed."
    elif decision == "r":
        return f"❌ REJECTED — transfer {row['transfer_id']} cancelled, sender notified."
    elif decision == "m":
        return f"✏️  MODIFICATION REQUESTED — transfer {row['transfer_id']} routed back to preparer for changes."
    else:
        return f"⚠️  INVALID INPUT ('{decision}') — defaulting to REJECTED for safety."

# Main workflow
def main():
    # Load data
    df = pd.read_csv("data/transfer_requests.csv")
    
    for _, row in df.iterrows():
        transfer_id = row["transfer_id"]
        amount = row["amount"]
        
        # Check if transfer exceeds threshold
        if amount > APPROVAL_THRESHOLD:
            print(f"\nTransfer {transfer_id} exceeds the ${APPROVAL_THRESHOLD:,} approval threshold — PAUSING for human review.")
            #transfer_id,sender_name,recipient_name,amount,currency,memo
            # Build summary
            summary = f"""
Transfer ID:  {row['transfer_id']}
From:         {row['sender_name']}
To:           {row['recipient_name']}
Amount:       {row['amount']:,} {row['currency']}
Memo:         {row['memo']}"""
            
            # Flag risk signals
            signals = flag_risk_signals(row)
            if signals:
                signals_text = "; ".join(signals)
                summary += f"\n⚠️  RISK SIGNALS FLAGGED: {signals_text}"
            else:
                summary += "\nNo automatic risk signals flagged."
            
            # Get human decision
            decision = get_human_decision(summary)
            result = process_decision(decision, row)
            print(result)
        else:
            # Auto-process below threshold
            print(f"\nTransfer {transfer_id} (${amount:,}) is below the approval threshold — auto-processing without human review.")
            print(f"✅ Transfer {transfer_id} executed automatically.")

if __name__ == "__main__":
    main()

###------------OUTPUT----------------###
"""
Transfer TR001 exceeds the $10,000 approval threshold — PAUSING for human review.


Transfer ID:  TR001
From:         Acme Logistics Ltd
To:           Global Freight Partners
Amount:       48,500 USD
Memo:         Q3 shipping contract settlement
No automatic risk signals flagged.

Approve, Reject, or Modify this transfer? [a/r/m]: a
✅ APPROVED — transfer TR001 would now be executed.

Transfer TR002 exceeds the $10,000 approval threshold — PAUSING for human review.


Transfer ID:  TR002
From:         Acme Logistics Ltd
To:           Unknown Recipient Corp
Amount:       125,000 USD
Memo:         Urgent - per phone instructions
⚠️  RISK SIGNALS FLAGGED: very large amount ($125,000); memo contains suspicious phrase: 'urgent'; memo contains suspicious phrase: 'per phone instructions'; recipient name suggests an unverified/unfamiliar party

Approve, Reject, or Modify this transfer? [a/r/m]: a
✅ APPROVED — transfer TR002 would now be executed.

Transfer TR003 ($9,200) is below the approval threshold — auto-processing without human review.
✅ Transfer TR003 executed automatically.
"""
###------------DONE----------------###