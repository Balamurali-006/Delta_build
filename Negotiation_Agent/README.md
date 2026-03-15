# AI Contract Negotiation Agent

This module automatically re-negotiates contracts that are flagged as **HIGH** or **MEDIUM** risk by our ML model.

## How it works:
1.  **Reads Input**: It looks for the most recent `output.json` in the root of `Delta_build`.
2.  **Risk Re-Analysis**: It re-evaluates the risk using the `Ai_prediction` model to ensure the data is fresh.
3.  **AI Strategy**: It uses a large language model (Llama-3.3-70b via Groq) to act as a "Senior Credit Risk Negotiator."
4.  **Term Optimization**: It identifies which parameters (Interest, Tenure, Collateral) are causing the high risk and suggests mathematical safer alternatives.
5.  **Audit Trail**: Saves the suggestions to `optimized_contract_terms.json`.

## Usage:
After running `orchestrator.py` for any contract, run this agent:
```bash
python Delta_build/Negotiation_Agent/negotiator.py
```

## Expected Output:
- **Analysis**: Reasoning for why the contract is risky.
- **Optimized Terms**: A list of "Current" vs "Suggested" parameters.
- **Revised ACTUS JSON**: A machine-ready JSON structure with the safer terms.
- **Negotiation Summary**: A professional script to use with the borrower.
