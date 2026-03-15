import os
import json
import copy
import re
import sys
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_risk_report(risk_report: dict) -> dict:
    def _clean_num(s):
        # Extract digits, decimal points, and minus signs
        match = re.search(r"[-+]?\d*\.?\d+", str(s).replace(",", ""))
        return match.group(0) if match else "0"

    raw_pd = _clean_num(risk_report.get("Default Probability", "0.1"))
    raw_el = _clean_num(risk_report.get("Expected Loss", "0"))
    
    return {
        "risk_category":       risk_report.get("Risk Category", "UNKNOWN").strip(),
        "default_probability": float(raw_pd) / 100.0 if "%" in str(risk_report.get("Default Probability")) else float(raw_pd),
        "expected_loss":       float(raw_el),
        "recommendation":      risk_report.get("Recommendation", "UNKNOWN").strip(),
    }


def _extract_rate_shock(scenario: str) -> float:
    """Parse a rate shock value (percentage points) from a natural-language string."""
    patterns = [
        r'(?:rise|hike|increase|up|raise|shock)[^\d]*(\d+\.?\d*)\s*%',
        r'(\d+\.?\d*)\s*%?\s*(?:rate|interest)',
        r'(\d+\.?\d*)\s*(?:percentage points?|bps?\b)',
        r'(?:rates?)[^\d]*(\d+\.?\d*)',
    ]
    for p in patterns:
        m = re.search(p, scenario, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            return val / 100.0 if val > 20 else val
    return 0.0


def _recalculate_cashflows(cash_flows: list, original_rate: float,
                            shocked_rate: float) -> tuple:
    """Scale all IP events by rate ratio. Returns (revised_flows, total_interest)."""
    if original_rate <= 0:
        return cash_flows, 0.0
    ratio = shocked_rate / original_rate
    revised, total = [], 0.0
    for cf in cash_flows:
        c = copy.deepcopy(cf)
        if cf["type"] == "IP":
            c["payoff"] = round(cf["payoff"] * ratio, 4)
            c["nominalRate"] = shocked_rate
            total += c["payoff"]
        revised.append(c)
    return revised, round(total, 2)


# ---------------------------------------------------------------------------
# StressTestingAgent
# ---------------------------------------------------------------------------

class StressTestingAgent:

    _SYSTEM_PROMPT = """You are a senior bank credit risk analyst and ACTUS financial contract expert.
You receive structured data from the DeltaBuild pipeline:
- An ACTUS cashflow schedule (PAM bullet-principal contract)
- The current AI risk assessment (risk category, default probability, expected loss)
- A stressed cashflow schedule after quantitative recalculation
- An economic shock scenario description

Reason through the credit and liquidity implications. Be precise, use only numbers
from the data provided. Do NOT invent figures.

Respond ONLY with valid JSON (no markdown, no preamble, no trailing text):
{
  "scenario_name": "<short descriptive title>",
  "revised_risk_category": "LOW | MEDIUM | HIGH | CRITICAL",
  "revised_default_probability_pct": <float>,
  "revised_expected_loss": <float>,
  "cashflow_impact_summary": "<2-3 sentences on how cashflows changed>",
  "risk_impact_statement": "<2-3 sentences on how the risk profile changed>",
  "liquidity_warnings": ["<warning 1>", "<warning 2>"],
  "recommendation": "APPROVE | CONDITIONAL APPROVE | REVIEW | REJECT",
  "recommendation_rationale": "<1-2 sentence rationale>"
}"""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model   = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in .env")
        self.client = Groq(api_key=self.api_key)
        print("Stress Testing Agent initialized.")

    def run_scenario(self, output_json_path: str, risk_report: dict,
                     scenario_description: str) -> dict:
        """
        Main entry point for stress testing.
        1. Read output.json
        2. Recalculate cashflows quantitatively
        3. Use Groq LLM to assess risk impact
        4. Return structured report
        """
        # 1. Load ACTUS data
        with open(output_json_path, "r") as f:
            actus = json.load(f)

        summary = actus.get("summary", {})
        flows   = actus.get("cashFlows", [])

        # 2. Parse risk inputs
        risk          = _parse_risk_report(risk_report)
        original_rate = float(summary.get("nominalRate", 0))
        principal     = float(summary.get("principal", 0))
        orig_interest = float(summary.get("totalInterest", 0))
        orig_cashflow = float(summary.get("totalCashFlow", 0))

        # 3. Quantitative cashflow recalculation
        rate_shock       = _extract_rate_shock(scenario_description)
        shocked_rate     = original_rate + (rate_shock / 100.0)
        revised_flows, revised_interest = _recalculate_cashflows(
            flows, original_rate, shocked_rate
        )
        revised_cashflow = principal + revised_interest

        # 4. Build LLM prompt
        ip_sample = [cf for cf in revised_flows if cf["type"] == "IP"][:4]
        prompt = f"""
CONTRACT SUMMARY (ACTUS PAM):
  Contract ID   : {summary.get('contractID')}
  Contract Type : {summary.get('contractType')}
  Currency      : {summary.get('currency', 'INR')}
  Principal     : {principal:,.2f}
  Start Date    : {summary.get('startDate')}
  Maturity Date : {summary.get('maturityDate')}
  Original Rate : {original_rate * 100:.3f}%
  Shocked Rate  : {shocked_rate * 100:.3f}%

SCENARIO: {scenario_description}

BASE CASE:
  Total Interest       : {orig_interest:,.2f}
  Total Cashflow       : {orig_cashflow:,.2f}
  Risk Category        : {risk['risk_category']}
  Default Probability  : {risk['default_probability'] * 100:.3f}%
  Expected Loss        : {risk['expected_loss']:,.2f}
  Recommendation       : {risk['recommendation']}

STRESSED CASE (after rate recalculation):
  Revised Total Interest : {revised_interest:,.2f}  (delta: {revised_interest - orig_interest:+,.2f})
  Revised Total Cashflow : {revised_cashflow:,.2f}  (delta: {revised_cashflow - orig_cashflow:+,.2f})
  Sample stressed IP payments: {json.dumps(ip_sample, indent=2)}

BULLET REPAYMENT NOTE:
  Principal of {principal:,.2f} is due in full on {summary.get('maturityDate')} (MD event).
  This is the single largest cashflow risk event in the schedule.

Produce the JSON risk assessment now.
""".strip()

        # 5. Call Groq
        print(f"\n  Calling Groq ({self.model})...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )
        raw_text = response.choices[0].message.content.strip()
        
        def _robust_json_loads(s):
            # 1. Basic cleaning
            s = s.strip()
            # 2. Try direct load
            try: return json.loads(s)
            except: pass
            
            # 3. Handle common LLM markdown pollution
            s = re.sub(r"^```(?:json)?", "", s, flags=re.MULTILINE|re.IGNORECASE).strip()
            s = re.sub(r"```$", "", s, flags=re.MULTILINE|re.IGNORECASE).strip()
            
            # 4. Extract first { and last }
            match = re.search(r'\{.*\}', s, re.DOTALL)
            if match:
                s = match.group()
            
            # 5. Fix trailing commas (e.g. { "a": 1, })
            s = re.sub(r',\s*(\}|\])', r'\1', s)
            
            # 6. Final attempt
            try: return json.loads(s)
            except Exception as e:
                print(f"  [!] All JSON parsing attempts failed: {e}")
                raise e

        try:
            llm = _robust_json_loads(raw_text)
        except Exception as e:
            print(f"  [!] Using emergency fallback JSON due to: {e}")
            print(f"  [!] Raw Response was: {raw_text}")
            llm = {
                "scenario_name": "Analysis Failure",
                "revised_risk_category": "UNKNOWN",
                "revised_default_probability_pct": 0,
                "revised_expected_loss": 0,
                "cashflow_impact_summary": "AI processing failed.",
                "risk_impact_statement": f"AI Engine returned invalid JSON structure: {str(e)}",
                "liquidity_warnings": ["Parsing Error"],
                "recommendation": "REVIEW",
                "recommendation_rationale": "System failed to parse valid response from the LLM."
            }

        # 6. Build and print report
        cur = summary.get("currency", "INR")
        sym = "Rs." if cur == "INR" else cur + " "

        report_lines = [
            "",
            "=" * 68,
            "         DeltaBuild -- Scenario Stress Testing Report",
            "=" * 68,
            f"  Contract   : {summary.get('contractID')}  ({summary.get('contractType')})",
            f"  Principal  : {sym}{principal:,.2f}",
            f"  Base Rate  : {original_rate * 100:.2f}%   ->   Shocked Rate: {shocked_rate * 100:.2f}%",
            "",
            "-" * 68,
            f"  SCENARIO   : {llm.get('scenario_name', scenario_description)}",
            "-" * 68,
            "",
            "  -- CASHFLOW COMPARISON --",
            f"  {'':28} {'BASE CASE':>18}   {'STRESSED':>18}   {'DELTA':>14}",
            f"  {'Total Interest':<28} {sym}{orig_interest:>15,.2f}   "
            f"{sym}{revised_interest:>15,.2f}   "
            f"{revised_interest - orig_interest:>+14,.2f}",
            f"  {'Total Cashflow':<28} {sym}{orig_cashflow:>15,.2f}   "
            f"{sym}{revised_cashflow:>15,.2f}   "
            f"{revised_cashflow - orig_cashflow:>+14,.2f}",
            "",
            "  -- RISK COMPARISON --",
            f"  {'':28} {'BASE CASE':>18}   {'STRESSED':>18}",
            f"  {'Risk Category':<28} {risk['risk_category']:>18}   "
            f"{llm.get('revised_risk_category', 'N/A'):>18}",
            f"  {'Default Probability':<28} {risk['default_probability']*100:>17.3f}%   "
            f"{llm.get('revised_default_probability_pct', 0):>17.3f}%",
            f"  {'Expected Loss':<28} {sym}{risk['expected_loss']:>15,.2f}   "
            f"{sym}{llm.get('revised_expected_loss', 0):>15,.2f}",
            "",
            "  -- LLM ASSESSMENT (Groq) --",
            f"  Cashflow Impact:",
            f"    {llm.get('cashflow_impact_summary', 'N/A')}",
            "",
            f"  Risk Statement:",
            f"    {llm.get('risk_impact_statement', 'N/A')}",
            "",
            "  -- LIQUIDITY WARNINGS --",
        ]

        warnings = llm.get("liquidity_warnings", [])
        if warnings:
            for w in warnings:
                report_lines.append(f"  [!] {w}")
        else:
            report_lines.append("  [OK] No critical liquidity warnings flagged.")

        report_lines += [
            "",
            "  -- RECOMMENDATION --",
            f"  {llm.get('recommendation', 'N/A')}",
            f"  {llm.get('recommendation_rationale', '')}",
            "=" * 68,
        ]

        report = "\n".join(report_lines)
        print(report)

        # 7. Save JSON
        out = {
            "scenario": scenario_description,
            "base_case": {
                "total_interest":      orig_interest,
                "total_cashflow":      orig_cashflow,
                "risk_category":       risk["risk_category"],
                "default_probability": risk["default_probability"] * 100,
                "expected_loss":       risk["expected_loss"],
            },
            "stressed_case": {
                "shocked_rate_pct":        shocked_rate * 100,
                "revised_total_interest":  revised_interest,
                "revised_total_cashflow":  revised_cashflow,
                "delta_interest":          revised_interest - orig_interest,
                **llm,
            },
        }
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "stress_test_output.json")
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\n  JSON saved -> {out_path}\n")

        return {"report": report, "data": out, "llm_raw": llm}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    RISK_REPORT = {
        "Risk Category":       "LOW",
        "Default Probability": "0.1%",
        "Expected Loss":       "Rs. 1,263.96",
        "Recommendation":      "APPROVE",
    }

    OUTPUT_JSON = "../output.json"

    scenario = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Interest rates rise by 2%"

    print(f"\nDeltaBuild -- Scenario Stress Testing Agent")
    print(f"  Scenario : {scenario}")
    print(f"  Model    : {os.getenv('GROQ_MODEL', 'llama-3.1-70b-versatile')}")
    print("-" * 68)

    agent = StressTestingAgent()
    agent.run_scenario(
        output_json_path=OUTPUT_JSON,
        risk_report=RISK_REPORT,
        scenario_description=scenario,
    )