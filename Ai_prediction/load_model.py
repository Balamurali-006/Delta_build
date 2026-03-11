"""
ACTUS Risk Model — Load & Predict
===================================
Loads the trained actus_risk_model.pkl and predicts
default risk from real ACTUS engine output.

The model now expects the set of features produced by the
training notebook; these are derived from two parts of the
ACTUS engine output:
  * `summary` block (principal, nominalRate, totalInterest,
    totalCashFlow, totalEvents, startDate/maturityDate, …)
  * `cashFlows` list (IED, PR, IP, MD events with payoffs and
    nominal values)

A minimal example of the JSON you should supply is:

    {
        "success": true,
        "summary": {
            "contractType":  "ANN",
            "contractID":    "contract01",
            "currency":      "INR",
            "principal":      2000000,
            "nominalRate":    0.09,
            "startDate":     "2024-01-01",
            "maturityDate":  "2034-01-01",
            "totalEvents":    241,
            "totalInterest":  2906303.73,
            "totalPrincipal": 2000000,
            "totalCashFlow":  4906303.73,
            "confidence":    "HIGH"
        },
        "cashFlows": [
            {"type":"IED", "payoff":-2000000,  "nominalValue":2000000, "nominalAccrued":0},
            {"type":"PR",  "payoff":-15287.67, "nominalValue":2015287, "nominalAccrued":15287.67},
            ...
        ]
    }

(The engine will normally supply many more cashflow events.)

USAGE:
    # From Python
    from load_model import predict_risk
    result = predict_risk(actus_output)

    # From CLI — full ACTUS JSON file
    python load_model.py --json contract.json

    # From CLI — minimal inline args
    python load_model.py --principal 2000000 --nominal_rate 0.09 --loan_term_years 10
"""

import pickle
import json
import argparse
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

from sklearn import __version__ as sk_version
from sklearn.exceptions import InconsistentVersionWarning
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)


# ─────────────────────────────────────────────────────────
# STEP 1 — LOAD MODEL & FEATURE LIST
# ─────────────────────────────────────────────────────────

with open("actus_risk_model.pkl", "rb") as f:
    model = pickle.load(f)

with open("feature_cols.json", "r") as f:
    FEATURE_COLS = json.load(f)

print("✅ Model loaded!")
print(f"   sklearn version   : {sk_version}")
print(f"   Features expected : {len(FEATURE_COLS)}\n")


# ─────────────────────────────────────────────────────────
# STEP 2 — FEATURE EXTRACTION (matches Colab training code)
# ─────────────────────────────────────────────────────────

def extract_summary_features(summary: dict) -> dict:
    """
    Extract static features from ACTUS summary block.

    Keys used:
        principal, nominalRate, totalInterest,
        totalCashFlow, totalEvents, startDate, maturityDate
    """
    principal      = float(summary.get("principal",      0))
    nominal_rate   = float(summary.get("nominalRate",    0))
    total_interest = float(summary.get("totalInterest",  0))
    total_cashflow = float(summary.get("totalCashFlow",  0))
    total_events   = int(summary.get("totalEvents",      0))

    # Loan term in years derived from ACTUS dates
    try:
        start    = datetime.strptime(summary["startDate"][:10],    "%Y-%m-%d")
        maturity = datetime.strptime(summary["maturityDate"][:10], "%Y-%m-%d")
        loan_term_years = round((maturity - start).days / 365.25, 2)
    except Exception:
        loan_term_years = 0

    # Derived ratio features
    interest_to_principal = round(total_interest / principal, 4)     if principal       > 0 else 0
    cashflow_to_principal = round(total_cashflow / principal, 4)     if principal       > 0 else 0
    avg_monthly_burden    = round(total_cashflow / total_events, 2)  if total_events    > 0 else 0
    interest_rate_burden  = round(nominal_rate * loan_term_years, 4) if loan_term_years > 0 else 0

    return {
        # ── ACTUS Summary Fields ──
        "principal":             principal,
        "nominal_rate":          nominal_rate,
        "total_interest":        total_interest,
        "total_cashflow":        total_cashflow,
        "total_events":          total_events,
        "loan_term_years":       loan_term_years,
        # ── Derived ──
        "interest_to_principal": interest_to_principal,
        "cashflow_to_principal": cashflow_to_principal,
        "avg_monthly_burden":    avg_monthly_burden,
        "interest_rate_burden":  interest_rate_burden,
    }


def extract_cashflow_features(cashflows: list) -> dict:
    """
    Extract dynamic risk features from ACTUS cashFlow event list.

    Event types:
        IED → Initial Exchange Date (loan disbursement)
        PR  → Principal Redemption payment
        IP  → Interest Payment
        MD  → Maturity Date (final repayment)
    """
    pr_events = [e for e in cashflows if e.get("type") == "PR"]
    ip_events = [e for e in cashflows if e.get("type") == "IP"]
    md_events = [e for e in cashflows if e.get("type") == "MD"]

    nominal_values  = [abs(e.get("nominalValue",   0)) for e in cashflows]
    nominal_accrued = [abs(e.get("nominalAccrued", 0)) for e in cashflows]
    pr_payoffs      = [abs(e.get("payoff", 0))         for e in pr_events]
    ip_payoffs      = [abs(e.get("payoff", 0))         for e in ip_events]

    peak_nominal_value  = max(nominal_values)                        if nominal_values  else 0
    final_nominal_value = abs(md_events[0].get("payoff", 0))         if md_events       else 0
    avg_accrued         = round(np.mean(nominal_accrued), 2)         if nominal_accrued else 0
    max_accrued         = round(max(nominal_accrued), 2)             if nominal_accrued else 0
    avg_pr_payment      = round(np.mean(pr_payoffs), 2)              if pr_payoffs      else 0
    max_pr_payment      = round(max(pr_payoffs), 2)                  if pr_payoffs      else 0
    avg_ip_payment      = round(np.mean(ip_payoffs), 2)              if ip_payoffs      else 0
    total_pr_events     = len(pr_events)
    total_ip_events     = len(ip_events)

    # Balance growth: how much the outstanding balance grew over loan life
    initial_nominal      = nominal_values[0] if nominal_values else 1
    balance_growth_ratio = round(peak_nominal_value / initial_nominal, 4) if initial_nominal > 0 else 1

    # IP-to-PR ratio: how much interest vs principal is being paid
    total_pr       = sum(pr_payoffs)
    total_ip       = sum(ip_payoffs)
    ip_to_pr_ratio = round(total_ip / total_pr, 4) if total_pr > 0 else 0

    return {
        # ── Cashflow Event Features ──
        "total_pr_events":      total_pr_events,
        "total_ip_events":      total_ip_events,
        "avg_pr_payment":       avg_pr_payment,
        "max_pr_payment":       max_pr_payment,
        "avg_ip_payment":       avg_ip_payment,
        "peak_nominal_value":   peak_nominal_value,
        "final_nominal_value":  final_nominal_value,
        "avg_accrued":          avg_accrued,
        "max_accrued":          max_accrued,
        # ── Derived Cashflow Ratios ──
        "balance_growth_ratio": balance_growth_ratio,
        "ip_to_pr_ratio":       ip_to_pr_ratio,
    }


# ─────────────────────────────────────────────────────────
# STEP 3 — MAIN PREDICT FUNCTION
# ─────────────────────────────────────────────────────────

def predict_risk(actus_output: dict) -> dict:
    """
    Predict default risk from a full ACTUS engine output.

    Args:
        actus_output : dict
            The full JSON your ACTUS engine returns.
            Must contain: success, summary, cashFlows

    Returns:
        {
            "contract_id":         str,
            "default_probability": float  (0.0 → 1.0),
            "risk_category":       str    (LOW / MEDIUM / HIGH),
            "expected_loss":       float  (in contract currency),
            "recommendation":      str,
            "negotiation_tips":    list[str]  (only present if HIGH risk)
        }
    """
    if not actus_output.get("success", False):
        return {"error": "ACTUS engine returned success=false"}

    summary   = actus_output.get("summary",   {})
    cashflows = actus_output.get("cashFlows", [])

    # Extract features — identical logic to Colab training
    s_feats   = extract_summary_features(summary)
    c_feats   = extract_cashflow_features(cashflows)
    all_feats = {**s_feats, **c_feats}

    # Build model input row
    input_df     = pd.DataFrame([all_feats])[FEATURE_COLS].fillna(0)
    default_prob = float(model.predict_proba(input_df)[0][1])

    principal     = s_feats["principal"]
    expected_loss = round(principal * default_prob * 0.6, 2)

    if default_prob > 0.6:
        risk_category  = "HIGH"
        recommendation = "REJECT or renegotiate terms"
    elif default_prob > 0.3:
        risk_category  = "MEDIUM"
        recommendation = "APPROVE with conditions"
    else:
        risk_category  = "LOW"
        recommendation = "APPROVE"

    result = {
        "contract_id":         summary.get("contractID", "unknown"),
        "default_probability": round(default_prob, 4),
        "risk_category":       risk_category,
        "expected_loss":       expected_loss,
        "recommendation":      recommendation,
    }

    # AI negotiation tips — only shown for HIGH risk contracts
    if risk_category == "HIGH":
        rate = s_feats["nominal_rate"]
        term = s_feats["loan_term_years"]
        result["negotiation_tips"] = [
            f"Increase interest rate:  {rate*100:.2f}% → {(rate + 0.015)*100:.2f}%",
            f"Reduce loan tenure:      {term:.0f} yrs → {max(term - 3, 3):.0f} yrs",
            f"Require collateral:      min ₹{principal * 0.3:,.0f}",
            "Add co-borrower or guarantor",
        ]

    return result


# ─────────────────────────────────────────────────────────
# STEP 4 — PRETTY PRINT REPORT
# ─────────────────────────────────────────────────────────

def print_result(result: dict, summary: dict):
    currency = summary.get("currency", "INR")
    sym      = "₹" if currency == "INR" else "$"

    risk_icons = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
    icon       = risk_icons.get(result.get("risk_category", ""), "⚪")

    print("=" * 54)
    print("   ACTUS RISK PREDICTION REPORT")
    print("=" * 54)
    print(f"  Contract ID      : {result['contract_id']}")
    print(f"  Contract Type    : {summary.get('contractType', 'ANN')}")
    print(f"  Currency         : {currency}")
    print(f"  Principal        : {sym}{summary.get('principal', 0):>15,.2f}")
    print(f"  Nominal Rate     : {summary.get('nominalRate', 0)*100:.2f}%")
    print(f"  Total Interest   : {sym}{summary.get('totalInterest', 0):>15,.2f}")
    print(f"  Total Cashflow   : {sym}{summary.get('totalCashFlow', 0):>15,.2f}")
    print(f"  Total Events     : {summary.get('totalEvents', 0)}")
    print(f"  Period           : {summary.get('startDate', '')} → {summary.get('maturityDate', '')}")
    print(f"  ACTUS Confidence : {summary.get('confidence', 'N/A')}")
    print("-" * 54)
    print(f"  Default Prob     : {result['default_probability']*100:.1f}%")
    print(f"  Risk Category    : {icon}  {result['risk_category']}")
    print(f"  Expected Loss    : {sym}{result['expected_loss']:>15,.2f}")
    print(f"  Recommendation   : {result['recommendation']}")
    if "negotiation_tips" in result:
        print("-" * 54)
        print("  AI NEGOTIATION TIPS:")
        for tip in result["negotiation_tips"]:
            print(f"    → {tip}")
    print("=" * 54)


# ─────────────────────────────────────────────────────────
# STEP 5 — CLI ENTRY POINT
# ─────────────────────────────────────────────────────────

def _build_minimal_actus_output(principal: float, nominal_rate: float, loan_term_years: float) -> dict:
    """
    Build a minimal ACTUS-style dict from raw numbers.
    Used by CLI when no full JSON is provided.
    Computes summary totals via annuity formula.
    Cashflows list left empty — model uses summary features only.
    """
    term_mo      = int(loan_term_years * 12)
    monthly_rate = nominal_rate / 12

    if monthly_rate > 0:
        monthly_payment = (
            principal
            * (monthly_rate * (1 + monthly_rate) ** term_mo)
            / ((1 + monthly_rate) ** term_mo - 1)
        )
    else:
        monthly_payment = principal / term_mo

    total_cashflow = round(monthly_payment * term_mo, 2)
    total_interest = round(total_cashflow - principal,  2)
    total_events   = term_mo * 2   # PR + IP per month

    start    = datetime.today().strftime("%Y-%m-%d")
    try:
        from dateutil.relativedelta import relativedelta
        maturity = (datetime.today() + relativedelta(years=int(loan_term_years))).strftime("%Y-%m-%d")
    except ImportError:
        maturity = str(datetime.today().year + int(loan_term_years)) + "-01-01"

    return {
        "success": True,
        "summary": {
            "contractID":    "cli_contract",
            "contractType":  "ANN",
            "currency":      "INR",
            "principal":      principal,
            "nominalRate":    nominal_rate,
            "loan_term_years": loan_term_years,
            "startDate":      start,
            "maturityDate":   maturity,
            "totalEvents":    total_events,
            "totalInterest":  total_interest,
            "totalPrincipal": principal,
            "totalCashFlow":  total_cashflow,
            "confidence":    "MEDIUM",
        },
        "cashFlows": []  # no cashflow events in minimal mode
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ACTUS Risk Predictor",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python load_model.py --json contract.json
  python load_model.py --principal 2000000 --nominal_rate 0.09 --loan_term_years 10
        """
    )
    parser.add_argument("--json",            help="Path to ACTUS engine output JSON file")
    parser.add_argument("--principal",        type=float, help="Loan principal amount (e.g. 2000000)")
    parser.add_argument("--nominal_rate",     type=float, help="Nominal interest rate decimal (e.g. 0.09)")
    parser.add_argument("--loan_term_years",  type=float, help="Loan term in years (e.g. 10)")
    args = parser.parse_args()

    contracts = []

    if args.json:
        # ── Best mode: full ACTUS JSON file with summary + cashFlows
        with open(args.json, "r") as jf:
            data = json.load(jf)
        contracts = data if isinstance(data, list) else [data]
        print(f"📂 Loaded {len(contracts)} contract(s) from {args.json}\n")

    elif args.principal and args.nominal_rate and args.loan_term_years:
        # ── Minimal mode: build summary only from CLI args
        contracts = [_build_minimal_actus_output(
            args.principal, args.nominal_rate, args.loan_term_years
        )]
        print("🔧 Built minimal ACTUS output from CLI args\n")

    else:
        # ── Demo mode: use the sample contract from the hackathon data
        print("ℹ️  No input provided — running with sample ACTUS contract...\n")
        contracts = [{
            "success": True,
            "summary": {
                "contractType":  "ANN",
                "contractID":    "demo_contract_01",
                "currency":      "INR",
                "principal":      2000000,
                "nominalRate":    0.09,
                "startDate":     "2024-01-01",
                "maturityDate":  "2034-01-01",
                "totalEvents":    241,
                "totalInterest":  2906303.73,
                "totalPrincipal": 2000000,
                "totalCashFlow":  4906303.73,
                "confidence":    "HIGH"
            },
            "cashFlows": [
                {"type": "IED", "payoff": -2000000,    "nominalValue": 2000000,    "nominalAccrued": 0},
                {"type": "PR",  "payoff": -15287.67,   "nominalValue": 2015287.67, "nominalAccrued": 15287.67},
                {"type": "IP",  "payoff":  15287.67,   "nominalValue": 2015287.67, "nominalAccrued": 0},
                {"type": "PR",  "payoff": -14410.69,   "nominalValue": 2029698.36, "nominalAccrued": 14410.69},
                {"type": "IP",  "payoff":  14410.69,   "nominalValue": 2029698.36, "nominalAccrued": 0},
                {"type": "PR",  "payoff": -15514.68,   "nominalValue": 2045213.04, "nominalAccrued": 15514.68},
                {"type": "IP",  "payoff":  15514.68,   "nominalValue": 2045213.04, "nominalAccrued": 0},
                {"type": "MD",  "payoff":  4869085.24, "nominalValue": 0,          "nominalAccrued": 0},
            ]
        }]

    for contract in contracts:
        result = predict_risk(contract)
        print_result(result, contract.get("summary", {}))
        print()
