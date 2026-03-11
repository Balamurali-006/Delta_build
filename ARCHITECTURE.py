"""
================================================================================
SYSTEM ARCHITECTURE ANALYSIS
================================================================================

This document explains how all three folders integrate into one unified pipeline.
"""

# =============================================================================
# 📊 FOLDER ANALYSIS
# =============================================================================

FOLDER_ANALYSIS = {
    "actus_engine": {
        "purpose": "Financial contract analysis and cash flow simulation",
        "main_file": "main_v2.py",
        "technology": "FastAPI + Groq AI + awesome_actus_lib",
        "port": 8000,
        "what_it_does": [
            "1. Receives contract text or PDF",
            "2. Sends to Groq AI to extract ACTUS fields",
            "3. Generates comprehensive cash flow schedule",
            "4. Returns structured JSON output",
        ],
        "key_endpoints": [
            "POST /full-pipeline      → text to structured output",
            "POST /full-pipeline-pdf  → PDF to structured output",
            "GET  /health             → server status",
        ],
        "input": "contract_text or contract_pdf",
        "output": {
            "success": True,
            "actusJson": {
                "contractType": "ANN",
                "notionalPrincipal": 2500000,
                "nominalInterestRate": 0.09,
                "initialExchangeDate": "2024-01-01",
                "maturityDate": "2034-01-01",
                # ... 20+ more fields
            },
            "summary": {
                "contractID": "contract_001",
                "principal": 2500000,
                "totalInterest": 1203456.78,
                "totalCashFlow": 3703456.78,
                "totalEvents": 120,
            },
            "cashFlows": [
                {"type": "IED", "payoff": -2500000, "nominalValue": 2500000},
                {"type": "IP", "payoff": 18750, "nominalValue": 2500000},
                {"type": "PR", "payoff": -15287.67, "nominalValue": 2485713},
                # ... 117 more cash flow events
            ]
        },
        "dependencies": [
            "awesome_actus_lib  - ACTUS contract simulation",
            "groq               - AI for contract parsing",
            "fastapi            - Web framework",
            "pydantic           - Data validation",
            "pdfplumber         - PDF text extraction",
        ],
        "requirements": {
            "GROQ_API_KEY": "Your Groq API key",
            "port_8000": "Must be available",
        }
    },
    
    "Ai_prediction": {
        "purpose": "Risk assessment and default prediction",
        "main_file": "load_model.py",
        "technology": "Scikit-learn + ML model + Pandas",
        "what_it_does": [
            "1. Accepts ACTUS engine output",
            "2. Extracts 20+ risk features from cash flows",
            "3. Runs through trained ML model",
            "4. Predicts default probability (0.0-1.0)",
            "5. Assigns risk category: LOW/MEDIUM/HIGH",
            "6. Provides AI-generated negotiation tips",
        ],
        "input": {
            "success": True,
            "summary": {
                "principal": 2500000,
                "nominalRate": 0.09,
                "totalInterest": 1203456.78,
                "totalCashFlow": 3703456.78,
                "totalEvents": 120,
                # ... more summary fields
            },
            "cashFlows": [
                # ... all cash flow events
            ]
        },
        "features_extracted": [
            "Summary Features:",
            "  - principal, nominal_rate, total_interest, total_cashflow",
            "  - total_events, loan_term_years",
            "  - interest_to_principal ratio",
            "  - cashflow_to_principal ratio",
            "  - avg_monthly_burden, interest_rate_burden",
            "",
            "Cashflow Features:",
            "  - total_pr_events, total_ip_events",
            "  - avg_pr_payment, max_pr_payment",
            "  - avg_ip_payment",
            "  - peak_nominal_value, final_nominal_value",
            "  - avg_accrued, max_accrued",
            "  - balance_growth_ratio, ip_to_pr_ratio",
        ],
        "output": {
            "contract_id": "contract_001",
            "default_probability": 0.2345,  # 23.45% chance of default
            "risk_category": "MEDIUM",      # LOW / MEDIUM / HIGH
            "expected_loss": 450000.50,     # Principal × default_prob × 0.6
            "recommendation": "APPROVE with conditions",
            "negotiation_tips": [  # Only for HIGH risk
                "Increase interest rate: 9.00% → 10.50%",
                "Reduce loan tenure: 10 yrs → 7 yrs",
                "Require collateral: min ₹750,000",
                "Add co-borrower or guarantor",
            ]
        },
        "risk_thresholds": {
            "HIGH": "default_probability > 0.60",
            "MEDIUM": "0.30 < default_probability ≤ 0.60",
            "LOW": "default_probability ≤ 0.30",
        },
        "files_required": [
            "load_model.py           - Main prediction logic",
            "actus_risk_model.pkl    - Trained ML model",
            "feature_cols.json       - Feature column list",
        ],
    },
    
    "blockchain_test": {
        "purpose": "Immutable storage of analysis results on blockchain",
        "main_file": "test_blockchain.py",
        "technology": "Web3.py + Ethereum/Polygon/Tenderly",
        "what_it_does": [
            "1. Connects to blockchain via RPC endpoint",
            "2. Loads smart contract ABI",
            "3. Creates combined payload (ACTUS + AI output)",
            "4. Builds and signs transaction",
            "5. Broadcasts to blockchain",
            "6. Returns transaction hash for audit trail",
        ],
        "input": {
            "ACTUS output": "summary and cashFlows",
            "AI output": "default_probability, risk_category, etc",
        },
        "stored_on_blockchain": {
            "timestamp": "2024-03-11T14:30:00",
            "actus": {
                "contractType": "ANN",
                "principal": 2500000,
                "totalInterest": 1203456.78,
                # ... ACTUS summary
            },
            "risk_prediction": {
                "default_probability": 0.2345,
                "risk_category": "MEDIUM",
                "expected_loss": 450000.50,
                # ... AI output
            }
        },
        "output": {
            "tx_hash": "0x123abc...",
            "status": "Submitted to blockchain",
        },
        "blockchain_config": {
            "RPC_URL": "https://your-endpoint.com",
            "CONTRACT_ADDRESS": "0xYourContractAddress",
            "WALLET_ADDRESS": "0xYourWalletAddress",
            "PRIVATE_KEY": "0xYourPrivateKey",
        },
        "smart_contract_functions": [
            "storeContract(string memory contractData)",
            "getContract() returns (string memory)",
        ],
    }
}


# =============================================================================
# 🔄 DATA FLOW AND INTEGRATION
# =============================================================================

DATA_FLOW = """
┌──────────────────────────────────────────────────────────────────────────────┐
│                            UNIFIED PIPELINE                                   │
└──────────────────────────────────────────────────────────────────────────────┘

INPUT
│
│  Contract Text or PDF
│
▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          🚀 ORCHESTRATOR.PY                                   │
│  (Your single entry point - coordinates all three components)                │
└──────────────────────────────────────────────────────────────────────────────┘
│
├─ START: ACTUS Engine Server
│
▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    📋 ACTUS ENGINE (actus_engine/)                            │
│                   FastAPI on http://localhost:8000                            │
│                                                                               │
│  Input:   Contract text or PDF                                               │
│           ↓                                                                   │
│           [Groq AI] Extracts ACTUS fields                                     │
│           ↓                                                                   │
│           [awesome_actus_lib] Generates cash flows                            │
│           ↓                                                                   │
│  Output:  {                                                                   │
│    "success": true,                                                           │
│    "summary": {                                                               │
│      "principal": 2500000,                                                    │
│      "totalInterest": 1203456.78,                                             │
│      "totalCashFlow": 3703456.78,                                             │
│      "totalEvents": 120                                                       │
│    },                                                                         │
│    "cashFlows": [                                                             │
│      {"type": "IED", "payoff": -2500000, ...},                               │
│      {"type": "IP", "payoff": 18750, ...},                                   │
│      ...120 events...                                                         │
│    ]                                                                          │
│  }                                                                            │
└──────────────────────────────────────────────────────────────────────────────┘
│
├─ PASS OUTPUT TO NEXT STAGE
│
▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    🤖 AI PREDICTION (Ai_prediction/)                          │
│              Machine Learning Risk Assessment Model                           │
│                                                                               │
│  Input:   ACTUS output {summary, cashFlows}                                   │
│           ↓                                                                   │
│           [Feature Extraction] 20+ ML features                                │
│             - interest_to_principal ratio                                     │
│             - balance_growth_ratio                                            │
│             - ip_to_pr_ratio                                                  │
│             - avg_monthly_burden                                              │
│             - ...                                                             │
│           ↓                                                                   │
│           [ML Model] Loaded from actus_risk_model.pkl                         │
│           ↓                                                                   │
│  Output:  {                                                                   │
│    "contract_id": "contract_001",                                             │
│    "default_probability": 0.2345,  (23.45%)                                   │
│    "risk_category": "MEDIUM",                                                 │
│    "expected_loss": 450000.50,                                                │
│    "recommendation": "APPROVE with conditions",                               │
│    "negotiation_tips": [...]                                                  │
│  }                                                                            │
└──────────────────────────────────────────────────────────────────────────────┘
│
├─ PASS COMBINED OUTPUT TO BLOCKCHAIN
│
▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                  ⛓️  BLOCKCHAIN (blockchain_test/)                            │
│              Decentralized Immutable Storage via Web3.py                      │
│                                                                               │
│  Input:   Combined {ACTUS summary + AI risk prediction}                       │
│           ↓                                                                   │
│           [Web3 Connection] Connect to RPC endpoint                           │
│           ↓                                                                   │
│           [Smart Contract] Load ABI and contract instance                     │
│           ↓                                                                   │
│           [Transaction Build] Create storeContract(jsonData) call             │
│           ↓                                                                   │
│           [Sign] Sign with private key                                        │
│           ↓                                                                   │
│           [Broadcast] Send to blockchain network                              │
│           ↓                                                                   │
│  Output:  {                                                                   │
│    "tx_hash": "0x123abc...",                                                  │
│    "status": "Submitted to blockchain"                                        │
│  }                                                                            │
└──────────────────────────────────────────────────────────────────────────────┘
│
▼
OUTPUT: COMPLETE AUDIT TRAIL
│
├─ Contract parsed with ACTUS standards ✓
├─ Risk assessed by AI model ✓
├─ Results stored immutably on blockchain ✓
└─ Audit trail with tx hash for verification ✓
"""


# =============================================================================
# 🔗 COMPONENT DEPENDENCIES
# =============================================================================

INTEGRATION_POINTS = {
    "Orchestrator ↔ ACTUS": {
        "mechanism": "HTTP REST API (requests library)",
        "method": "POST /full-pipeline",
        "orchestrator_code": """
            response = requests.post(
                "http://localhost:8000/full-pipeline",
                json={"text": contract_text, "contract_id": contract_id},
                timeout=120
            )
            actus_output = response.json()
        """,
        "data_transferred": "Contract text → ACTUS JSON + cash flows",
    },
    
    "Orchestrator ↔ AI Prediction": {
        "mechanism": "Direct Python function import (sys.path manipulation)",
        "method": "from load_model import predict_risk",
        "orchestrator_code": """
            sys.path.insert(0, str(ai_dir))
            from load_model import predict_risk as predict_risk_fn
            result = predict_risk_fn(actus_output)
        """,
        "data_transferred": "ACTUS output → risk prediction",
    },
    
    "Orchestrator ↔ Blockchain": {
        "mechanism": "Direct Python module import",
        "method": "Web3 client + smart contract ABI",
        "orchestrator_code": """
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            contract = w3.eth.contract(address=contract_address, abi=abi)
            tx = contract.functions.storeContract(json_data).build_transaction({...})
        """,
        "data_transferred": "ACTUS + AI output → blockchain storage",
    },
}


# =============================================================================
# ⚙️ CONFIGURATION & ENVIRONMENT
# =============================================================================

ENVIRONMENT_SETUP = {
    "actus_engine/.env": {
        "GROQ_API_KEY": "Your API key from https://console.groq.com",
        "GROQ_MODEL": "llama-3.3-70b-versatile (or other)",
    },
    
    "blockchain_test/.env": {
        "RPC_URL": "https://your-blockchain-rpc.com",
        "CONTRACT_ADDRESS": "0xYourDeployedContractAddress",
        "WALLET_ADDRESS": "0xYourWalletPublicAddress",
        "PRIVATE_KEY": "0xYourPrivateKeyWithoutPassword",
    },
    
    "Running Environment": {
        "PYTHON_VERSION": "3.9+",
        "PORT_8000": "Must be available for ACTUS FastAPI",
        "DISK_SPACE": "~500MB for dependencies",
    }
}


# =============================================================================
# 🔐 SECURITY MODEL
# =============================================================================

SECURITY = {
    "API Keys": {
        "Groq API Key": "Stored in actus_engine/.env (never in code)",
        "Blockchain Private Key": "Stored in blockchain_test/.env (never in code)",
        "Risk": "If exposed, attacker can call Groq API with your quota",
    },
    
    "Transactions": {
        "Blockchain Tx": "Publicly visible on blockchain (by design)",
        "Data Sensitivity": "Stored in plaintext on blockchain",
        "Recommendation": "Don't store sensitive PII on blockchain",
    },
    
    "Best Practices": [
        "✓ Use environment variables, not hardcoded keys",
        "✓ Add .env to .gitignore",
        "✓ Rotate keys periodically",
        "✓ Use hardware wallets for production",
        "✓ Limit API key permissions",
        "✓ Monitor blockchain tx hash in logs",
    ]
}


# =============================================================================
# 📊 EXAMPLE: COMPLETE END-TO-END EXECUTION
# =============================================================================

EXAMPLE_EXECUTION = """
USER RUNS:
    python orchestrator.py --demo

ORCHESTRATOR DOES:

1️⃣  START ACTUS ENGINE
    → Starts: uvicorn main_v2:app --host 127.0.0.1 --port 8000
    → Waits 3 seconds
    → Checks: GET http://localhost:8000/health
    → Result: ✅ ACTUS engine running on http://localhost:8000

2️⃣  SEND CONTRACT TO ACTUS
    → POST http://localhost:8000/full-pipeline
    → Payload: {
        "text": "LOAN AGREEMENT... (1000+ chars)",
        "contract_id": "contract_001"
      }
    → Groq processes for ~20-30 seconds
    → Result: {
        "success": true,
        "summary": {
          "contractType": "ANN",
          "principal": 2500000,
          "nominalRate": 0.09,
          "totalInterest": 1203456.78,
          "totalCashFlow": 3703456.78,
          "totalEvents": 120
        },
        "cashFlows": [
          {"type": "IED", "payoff": -2500000, ...},
          {"type": "IP", "payoff": 18750, ...},
          ... 120 total events ...
        ]
      }

3️⃣  RUN AI RISK PREDICTION
    → Import: from Ai_prediction/load_model.py
    → Call: predict_risk(actus_output)
    → Feature extraction: 20+ ML features
    → Model prediction: default_probability = 0.2345
    → Result: {
        "contract_id": "contract_001",
        "default_probability": 0.2345,
        "risk_category": "MEDIUM",
        "expected_loss": 450000.50,
        "recommendation": "APPROVE with conditions",
        "negotiation_tips": [...]
      }

4️⃣  STORE TO BLOCKCHAIN
    → Connect to RPC: blockchain_test/.env
    → Load contract ABI
    → Build transaction with combined payload
    → Sign transaction with private key
    → Broadcast to blockchain
    → Result: {
        "tx_hash": "0x123abc...",
        "status": "Submitted to blockchain"
      }

5️⃣  DISPLAY COMPLETE REPORT
    → Print formatted report with all three stages
    → Show risk assessment summary
    → Show blockchain tx for audit trail
    → Suggest next actions based on risk
"""


# =============================================================================
# 📋 SUMMARY
# =============================================================================

if __name__ == "__main__":
    print(__doc__)
    print("\n" + "=" * 80)
    print("FOLDER ANALYSIS")
    print("=" * 80)
    for folder, details in FOLDER_ANALYSIS.items():
        print(f"\n📁 {folder}")
        print(f"   Purpose: {details['purpose']}")
        print(f"   Main: {details['main_file']}")
        print(f"   Tech: {details['technology']}")
    
    print("\n" + "=" * 80)
    print("DATA FLOW")
    print("=" * 80)
    print(DATA_FLOW)
    
    print("\n" + "=" * 80)
    print("EXAMPLE EXECUTION")
    print("=" * 80)
    print(EXAMPLE_EXECUTION)
    
    print("\n" + "=" * 80)
    print("READY TO RUN!")
    print("=" * 80)
    print("\nRun this command:")
    print("  python orchestrator.py --demo")
    print("\nOr see full options:")
    print("  python orchestrator.py --help")
    print()
