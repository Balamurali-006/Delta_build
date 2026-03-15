import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from groq import Groq
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
OUTPUT_JSON_PATH = BASE_DIR / "output.json"
AI_PREDICTION_DIR = BASE_DIR / "Ai_prediction"
ACTUS_ENGINE_DIR = BASE_DIR / "actus_engine"
REPORT_OUTPUT = Path(__file__).parent / "optimized_contract_terms.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("NegotiationAgent")

# ─────────────────────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────────────────────

def get_risk_analysis(actus_output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Runs the ML risk prediction model on the ACTUS output."""
    log.info("🔍 Running ML Risk Prediction...")
    original_cwd = os.getcwd()
    try:
        # We need to be in the AI directory to load pickle/json files
        os.chdir(str(AI_PREDICTION_DIR))
        sys.path.insert(0, str(AI_PREDICTION_DIR))
        
        from load_model import predict_risk
        risk_result = predict_risk(actus_output)
        
        return risk_result
    except Exception as e:
        log.error(f"❌ ML Risk Prediction failed: {e}")
        return None
    finally:
        os.chdir(original_cwd)
        if str(AI_PREDICTION_DIR) in sys.path:
            sys.path.remove(str(AI_PREDICTION_DIR))

def get_groq_client():
    """Loads API key and initializes Groq client."""
    env_path = ACTUS_ENGINE_DIR / ".env"
    load_dotenv(env_path)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        log.error("❌ GROQ_API_KEY not found in actus_engine/.env")
        return None
    return Groq(api_key=api_key)

# ─────────────────────────────────────────────────────────────────────────────
# NEGOTIATION LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def negotiate_terms(actus_output: Dict[str, Any], risk_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Uses Groq AI to suggest optimized contract terms based on risk."""
    client = get_groq_client()
    if not client:
        return None

    summary = actus_output.get("summary", {})
    risk_cat = risk_result.get("risk_category", "UNKNOWN")
    prob = risk_result.get("default_probability", 0.0)

    log.info(f"🤖 AI Agent negotiating for Risk Level: {risk_cat} ({prob*100:.1f}%)")

    prompt = f"""
    You are a Senior Bank Credit Risk Negotiator.
    We have a loan contract that has been analyzed by an ACTUS engine and an ML Risk Model.
    
    CURRENT CONTRACT TERMS:
    - Principal: {summary.get('principal')} {summary.get('currency')}
    - Interest Rate: {summary.get('nominalRate', 0)*100}%
    - Term: {summary.get('startDate')} to {summary.get('maturityDate')}
    - Type: {summary.get('contractType')}
    
    ML RISK ASSESSMENT:
    - Risk Category: {risk_cat}
    - Default Probability: {prob*100:.2f}%
    - Expected Loss: {risk_result.get('expected_loss')}
    
    YOUR TASK:
    1. Analyze why this is {risk_cat} risk.
    2. If risk is HIGH or MEDIUM, suggest at least 3 specific "Optimized Terms" to make the loan safer for the bank.
    3. If risk is LOW, suggest 1-2 "Market Optimizations" (e.g., cross-selling or slight rate adjustments).
    4. Provide a revised JSON structure for the core ACTUS terms.

    Return your response STRICTLY as a JSON object with this structure:
    {{
        "analysis": "Brief risk analysis",
        "action_required": true/false,
        "optimized_terms": [
            {{ "parameter": "Interest Rate", "current": "7%", "suggested": "8.5%", "reason": "..." }},
            ...
        ],
        "revised_actus_json": {{
             "nominalInterestRate": 0.085,
             "maturityDate": "...",
             ...
        }},
        "negotiation_summary": "Short professional pitch for the borrower"
    }}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a specialized financial negotiation agent. Return only JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        log.error(f"❌ AI Negotiation failed: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def run_agent():
    # 1. Load output.json
    if not OUTPUT_JSON_PATH.exists():
        log.error(f"❌ {OUTPUT_JSON_PATH} not found. Run the orchestrator first!")
        return

    try:
        with open(OUTPUT_JSON_PATH, "r") as f:
            actus_output = json.load(f)
    except Exception as e:
        log.error(f"❌ Failed to read output.json: {e}")
        return

    # 2. Get Risk Analysis
    risk_result = get_risk_analysis(actus_output)
    if not risk_result:
        return

    # 3. Negotiate
    negotiated_data = negotiate_terms(actus_output, risk_result)
    if not negotiated_data:
        return

    # 4. Save Results
    final_output = {
        "status": "SUCCESS",
        "original_risk": risk_result,
        "optimized_contract_terms": negotiated_data
    }
    
    with open(REPORT_OUTPUT, "w") as f:
        json.dump(final_output, f, indent=2)

    log.info(f"✅ Negotiation Agent complete. Report saved to {REPORT_OUTPUT}")
    
    # Simple Console Output
    print("\n" + "="*60)
    print("      🚀 AI CONTRACT NEGOTIATION REPORT")
    print("="*60)
    print(f"Risk Level: {risk_result['risk_category']} ({risk_result['default_probability']*100:.1f}%)")
    print(f"Analysis:   {negotiated_data.get('analysis')}")
    print("\nSUGGESTED CHANGES:")
    for term in negotiated_data.get("optimized_terms", []):
        print(f"  • {term['parameter']}: {term['current']} → {term['suggested']}")
        print(f"    Reason: {term['reason']}")
    print("\nNEGOTIATION SUMMARY:")
    print(negotiated_data.get("negotiation_summary"))
    print("="*60 + "\n")

if __name__ == "__main__":
    run_agent()
