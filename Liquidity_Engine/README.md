# Liquidity Forecasting Engine (Modular)

This module automates the process of portfolio-level liquidity analysis.

## How it works:
1.  Place **ACTUS JSON** contract files into the `contracts/` directory.
2.  Run `liquidity_forecaster.py`.
3.  The engine will:
    - Send each contract to your local ACTUS simulation server (port 8000).
    - Aggregate all incoming cash flows by year.
    - Match them against the bank's projected outflows (configurable in the script).
    - Detect years with liquidity shortages.
    - Save a detailed report to `liquidity_report.json`.

## Usage:
Make sure your ACTUS engine is running (e.g. `main_v2.py`), then:
```bash
python Liquidity_Engine/liquidity_forecaster.py
```

## Configuration:
You can manually update the `BANK_OUTFLOWS` dictionary in `liquidity_forecaster.py` to simulate different banking scenarios (e.g., predicted deposit withdrawals, operational costs, etc.).
