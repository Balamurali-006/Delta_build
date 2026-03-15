import os
import json
import requests
import logging
from collections import defaultdict
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
ACTUS_URL = "http://localhost:8000/simulate"
CONTRACTS_DIR = BASE_DIR / "contracts"
OUTPUT_FILE = BASE_DIR / "liquidity_report.json"


# Mock Bank Outflows (You can update these to match your hackathon scenario)
# Format: { "Year": Amount }
BANK_OUTFLOWS = {
    "2024": 500000,
    "2025": 1200000,
    "2026": 2000000,
    "2027": 1500000,
    "2028": 1500000,
    "2029": 1000000,
    "2030": 1000000,
    "2031": 1000000,
    "2032": 1000000,
    "2033": 1000000,
    "2034": 5000000 # Example: Large bond repayment or maturity
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("LiquidityEngine")

# ─────────────────────────────────────────────────────────────────────────────
# CORE LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def get_portfolio_cashflows():
    """
    Reads all JSON files in the contracts directory, sends them to ACTUS,
    and returns a combined list of cash flow events.
    """
    all_events = []
    
    if not CONTRACTS_DIR.exists():
        log.error(f"Directory '{CONTRACTS_DIR}' not found!")
        return []

    json_files = list(CONTRACTS_DIR.glob("*.json"))
    if not json_files:
        log.warning(f"No JSON files found in '{CONTRACTS_DIR}'")
        return []

    log.info(f"Found {len(json_files)} contracts to process...")

    for file_path in json_files:
        log.info(f"Processing {file_path.name}...")
        try:
            with open(file_path, "r") as f:
                actus_json = json.load(f)
            
            # The API expects either the direct JSON or the "contracts" list format
            # Our updated /simulate endpoint handles both.
            payload = {"actus_json": actus_json, "contract_id": file_path.stem}
            
            response = requests.post(ACTUS_URL, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get("cashFlows", [])
                all_events.extend(events)
                log.info(f"   Successfully fetched {len(events)} events.")
            else:
                log.error(f"   Failed to process {file_path.name}: {response.text}")
        
        except Exception as e:
            log.error(f"   Error processing {file_path.name}: {e}")

    return all_events

def run_forecast():
    """
    Aggregates cashflows, matches with outflows, and detects risk.
    """
    # 1. Fetch all raw cashflows from the ACTUS engine
    raw_events = get_portfolio_cashflows()
    if not raw_events:
        log.error("No cashflow data available. Forecast aborted.")
        return

    # 2. Aggregate Inflows by Year
    # We only count positive payoffs (money coming into the bank)
    # And specifically 'IP' (Interest) and 'PR' (Principal) and 'MD' (Maturity)
    portfolio_inflow = defaultdict(float)
    
    for event in raw_events:
        # Standard ACTUS: Positive payoff usually means inflow for the RPA (Lender)
        # Note: IED is usually negative (payout). We want the repayments.
        if event["payoff"] > 0:
            # Extract year from "2024-01-01T00:00"
            year = event["time"].split("-")[0]
            portfolio_inflow[year] += event["payoff"]

    # 3. Calculate Net Liquidity
    forecast = {}
    
    # Use all unique years from both inflows and outflows
    all_years = sorted(set(portfolio_inflow.keys()) | set(BANK_OUTFLOWS.keys()))

    for year in all_years:
        inflow = portfolio_inflow.get(year, 0.0)
        outflow = BANK_OUTFLOWS.get(year, 0.0)
        net = inflow - outflow
        
        forecast[year] = {
            "inflow": round(inflow, 2),
            "outflow": round(outflow, 2),
            "net_liquidity": round(net, 2),
            "status": "SAFE" if net >= 0 else "RISK"
        }

    # 4. Save and Report
    with open(OUTPUT_FILE, "w") as f:
        json.dump(forecast, f, indent=2)

    log.info(f"✅ Liquidity Forecast complete. Report saved to {OUTPUT_FILE}")
    
    # Simple console table
    print("\n" + "="*60)
    print(f"{'YEAR':<10} | {'INFLOW':<12} | {'OUTFLOW':<12} | {'NET':<12} | {'STATUS'}")
    print("-" * 60)
    for year in sorted(forecast.keys()):
        f = forecast[year]
        status_icon = "⚠️" if f["status"] == "RISK" else "✅"
        print(f"{year:<10} | {f['inflow']:<12,.2f} | {f['outflow']:<12,.2f} | {f['net_liquidity']:<12,.2f} | {status_icon} {f['status']}")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Ensure health check before starting
    try:
        requests.get("http://localhost:8000/health", timeout=2)
        run_forecast()
    except:
        log.error("ACTUS Engine not responding on http://localhost:8000. Please start the server first.")
