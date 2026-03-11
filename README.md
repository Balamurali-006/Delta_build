# 🚀 Unified Financial Pipeline Orchestrator

**One Script to Rule Them All** — Orchestrates ACTUS Contract Analysis → AI Risk Prediction → Blockchain Storage

![Pipeline Flow](./docs/flow.txt)

```
Contract Text/PDF
      ↓
┌─────────────────────────────┐
│  ACTUS Engine (FastAPI)     │  ← Port 8000 (Uvicorn)
│  - Parse contract via Groq  │
│  - Generate cash flows      │
└─────────────────────────────┘
      ↓
      {success, summary, cashFlows}
      ↓
┌─────────────────────────────┐
│  AI Risk Prediction Model   │
│  - Load ML model            │
│  - Predict default risk     │
│  - Recommend action         │
└─────────────────────────────┘
      ↓
      {risk_category, default_probability, ...}
      ↓
┌─────────────────────────────┐
│  Blockchain Storage         │
│  - Connect via Web3.py      │
│  - Store combined output    │
│  - Return tx hash           │
└─────────────────────────────┘
      ↓
   ✅ Complete Audit Trail
```

---

## 📋 Quick Start

### Prerequisites
- **Python 3.9+**
- **Environment Setup**: Create `.env` files in each folder

### 1. Install Dependencies

```bash
# ACTUS Engine
cd actus_engine
pip install -r requirements.txt
# Ensure GROQ_API_KEY is in .env

# Blockchain
cd ../blockchain_test
pip install web3 python-dotenv
# Configure .env with RPC_URL, CONTRACT_ADDRESS, WALLET_ADDRESS, PRIVATE_KEY

# Back to root
cd ..
pip install requests  # For orchestrator
```

### 2. Configure Environment Files

#### `actus_engine/.env`
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

#### `blockchain_test/.env`
```env
RPC_URL=https://your-rpc-endpoint.com
CONTRACT_ADDRESS=0x...
WALLET_ADDRESS=0x...
PRIVATE_KEY=0x...
```

#### `Ai_prediction/` (no .env needed, but requires model files)
- `actus_risk_model.pkl` — Trained ML model
- `feature_cols.json` — Feature list

### 3. Run the Orchestrator

**Demo Mode** (built-in test contract):
```bash
python orchestrator.py --demo
```

**With Your Contract Text**:
```bash
python orchestrator.py --contract-text "your contract text..."
```

**From a File**:
```bash
python orchestrator.py --contract-text ./path/to/contract.txt
```

**Keep Engine Running** (for manual testing):
```bash
python orchestrator.py --demo --keep-running
```

---

## 🔄 Full Workflow Explanation

### Step 1: ACTUS Engine Processing
The orchestrator:
1. Starts the FastAPI server (`main_v2.py`) on port 8000
2. Sends contract text to `/full-pipeline` endpoint
3. Groq AI extracts ACTUS fields (contract type, principal, interest rate, etc.)
4. `awesome_actus_lib` simulates cash flows
5. Returns structured JSON with:
   - `summary` — high-level contract details
   - `cashFlows` — list of all payment events

**Response Structure**:
```json
{
  "success": true,
  "actusJson": {
    "contractType": "ANN",
    "notionalPrincipal": 2500000,
    "nominalInterestRate": 0.09,
    ...
  },
  "summary": {
    "contractID": "contract_001",
    "principal": 2500000.0,
    "totalInterest": 1203456.78,
    "totalCashFlow": 3703456.78,
    "totalEvents": 120,
    ...
  },
  "cashFlows": [
    {"type": "IED", "payoff": -2500000, "nominalValue": 2500000, ...},
    {"type": "IP", "payoff": 18750, "nominalValue": 2500000, ...},
    ...
  ]
}
```

### Step 2: AI Risk Prediction
The orchestrator calls `Ai_prediction/load_model.py`:
1. Loads trained ML model (`actus_risk_model.pkl`)
2. Extracts 20+ features from ACTUS output (summary + cashflows)
3. Predicts **default probability** (0.0 → 1.0)
4. Assigns **risk category**: LOW | MEDIUM | HIGH
5. Returns recommendation: APPROVE | APPROVE WITH CONDITIONS | REJECT

**Response Structure**:
```json
{
  "contract_id": "contract_001",
  "default_probability": 0.2345,
  "risk_category": "MEDIUM",
  "expected_loss": 450000.50,
  "recommendation": "APPROVE with conditions",
  "negotiation_tips": [
    "Increase interest rate: 9.00% → 10.50%",
    "Reduce loan tenure: 10 yrs → 7 yrs",
    ...
  ]
}
```

### Step 3: Blockchain Storage
The orchestrator calls blockchain functionality via Web3.py:
1. Connects to RPC endpoint (via Web3)
2. Loads smart contract ABI
3. Creates transaction to store combined data:
   ```json
   {
     "timestamp": "2024-03-11T14:30:00",
     "actus": { /* ACTUS summary */ },
     "risk_prediction": { /* AI output */ }
   }
   ```
4. Signs with private key
5. Broadcasts transaction
6. Returns transaction hash

---

## 📊 Understanding the Output

### Example Complete Report
```
================================================================================
   UNIFIED ORCHESTRATOR — COMPLETE PIPELINE REPORT
================================================================================

📋 STEP 1 — CONTRACT PARSING (ACTUS ENGINE)
────────────────────────────────────────────────────────────────────────────────
   Contract Type    : ANN
   Contract ID      : contract_001
   Principal        : ₹ 25,00,000.00
   Interest Rate    :           9.00%
   Start Date       : 2024-01-01
   Maturity Date    : 2034-01-01
   Total Interest   : ₹ 12,03,456.78
   Total Cashflow   : ₹ 37,03,456.78
   Total Events     :            120 cash flow events

🤖 STEP 2 — RISK ANALYSIS (AI PREDICTION MODEL)
────────────────────────────────────────────────────────────────────────────────
   Risk Category       : 🟡  MEDIUM
   Default Probability :           23.45%
   Expected Loss       : ₹    4,50,000.50
   Recommendation      : APPROVE with conditions

   🔧 NEGOTIATION TIPS (HIGH RISK):
      • Increase interest rate: 9.00% → 10.50%
      • Reduce loan tenure: 10 yrs → 7 yrs
      • Require collateral: min ₹7,50,000

⛓️  STEP 3 — BLOCKCHAIN STORAGE
────────────────────────────────────────────────────────────────────────────────
   Transaction Hash : 0xabc123...
   Status           : Submitted to blockchain

================================================================================
```

---

## 🛠️ Troubleshooting

### ❌ "ACTUS engine failed to start"
```bash
# Check if port 8000 is in use
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill existing process or use different port
# Edit ACTUS_PORT in orchestrator.py
```

### ❌ "Timeout calling ACTUS pipeline"
- Groq API is slow (first request takes ~20-30s)
- Increase timeout in orchestrator.py:
  ```python
  response = requests.post(..., timeout=300)  # 5 minutes
  ```

### ❌ "Cannot import AI model"
```bash
# Ensure model files exist
ls -la Ai_prediction/actus_risk_model.pkl
ls -la Ai_prediction/feature_cols.json

# Or train the model:
# See Ai_prediction/ for training notebooks
```

### ❌ "Cannot connect to blockchain RPC"
```env
# Verify in blockchain_test/.env:
RPC_URL=https://your-rpc.com  # Must be valid endpoint
CONTRACT_ADDRESS=0x...        # Must be deployed
WALLET_ADDRESS=0x...          # Must have funds for gas
PRIVATE_KEY=0x...             # Must match wallet
```

### ❌ "Transaction rejected by blockchain"
- Insufficient gas: increase `'gas': 2000000` in orchestrator.py
- Insufficient funds: wallet needs ETH/MATIC for gas fees
- Contract function error: verify ABI matches deployed contract

---

## 🚀 Advanced Usage

### Custom Contract JSON (Skip Parsing)
```bash
# If you already have ACTUS JSON, skip Groq parsing
python orchestrator.py --contract-json contracts/my_contract.json
```

### Keep Engine Running for Interactive Testing
```bash
python orchestrator.py --demo --keep-running

# In another terminal, test endpoints manually:
curl http://localhost:8000/health
curl -X POST http://localhost:8000/full-pipeline \
  -H "Content-Type: application/json" \
  -d '{"text": "...", "contract_id": "test01"}'
```

### Batch Process Multiple Contracts
```python
# Save as batch_orchestrator.py
import subprocess
import sys

contracts = [
    "contract1.txt",
    "contract2.txt",
    "contract3.txt",
]

for contract in contracts:
    print(f"\n\n{'='*80}\nProcessing {contract}\n{'='*80}")
    subprocess.run([sys.executable, "orchestrator.py", "--contract-text", contract])
```

---

## 📁 Folder Structure

```
BC/
├── orchestrator.py              ← 🚀 RUN THIS (main orchestrator)
├── README.md                    ← You are here
│
├── actus_engine/
│   ├── main_v2.py              ← FastAPI server
│   ├── actus_simulation.py      ← Test simulation
│   ├── requirement
s.txt        ← Dependencies
│   ├── .env                     ← Config (GROQ_API_KEY)
│   └── venv/                    ← Virtual env
│
├── Ai_prediction/
│   ├── load_model.py            ← ML prediction logic
│   ├── feature_cols.json        ← Model features
│   ├── actus_risk_model.pkl     ← Trained model
│   └── search_high.py           ← Utilities
│
└── blockchain_test/
    ├── test_blockchain.py       ← Blockchain interaction
    ├── deploy.js                ← Contract deployment
    ├── package.json             ← Node dependencies
    ├── requirements.txt         ← Python dependencies
    ├── .env                     ← Config (RPC, keys)
    ├── contracts/               ← Solidity contracts
    │   └── ContractRegistry.sol
    ├── artifacts/               ← Compiled contracts
    └── scripts/
        └── deploy.js
```

---

## 🔐 Security Notes

⚠️ **NEVER commit `.env` files to Git!**
```bash
# Add to .gitignore
echo ".env" >> .gitignore
```

⚠️ **Protect Private Keys**
- Use environment variables, not hardcoded keys
- Consider hardware wallets for production
- Rotate keys regularly

---

## 📚 API Endpoints Available

Once running, the ACTUS engine exposes:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check server status |
| `/parse-contract` | POST | Text → ACTUS JSON |
| `/parse-pdf` | POST | PDF → ACTUS JSON |
| `/simulate` | POST | ACTUS JSON → Cash Flows |
| `/full-pipeline` | POST | Text → Full Output |
| `/full-pipeline-pdf` | POST | PDF → Full Output |

**Full Docs**: http://localhost:8000/docs (Swagger UI)

---

## 🤝 Integration Examples

### 1. **Microservice Architecture**
Use `orchestrator.py` as a backend service:
```python
from orchestrator import run_orchestrator

# In your FastAPI/Flask app
result = run_orchestrator(contract_text="...")
return result
```

### 2. **Webhook Notifications**
Extend orchestrator to post results to webhook:
```python
import requests

# After blockchain storage
requests.post("https://your-webhook.com", json={
    "contract_id": contract_id,
    "tx_hash": tx_hash,
    "risk": risk_prediction,
})
```

### 3. **Database Logging**
Store results in your database:
```python
db.contracts.insert_one({
    "contract_id": contract_id,
    "actus_summary": actus_output["summary"],
    "ai_prediction": risk_prediction,
    "blockchain_tx": tx_hash,
    "timestamp": datetime.now(),
})
```

---

## 📞 Support

For issues, check:
1. **Logs** — Orchestrator prints detailed logs
2. **Individual components** — Test each folder separately:
   ```bash
   cd actus_engine && python test_api.py
   cd ../Ai_prediction && python load_model.py --demo
   cd ../blockchain_test && python test_blockchain.py
   ```
3. **Requirements** — Install missing packages:
   ```bash
   pip install -r requirements.txt  # In each folder
   ```

---

## ✅ Summary

You now have **ONE command** to orchestrate your entire financial pipeline:

```bash
python orchestrator.py --demo
```

This single file:
- ✅ Starts ACTUS engine on port 8000
- ✅ Parses contracts via Groq AI
- ✅ Generates cash flows
- ✅ Predicts default risk
- ✅ Stores to blockchain
- ✅ Displays complete audit trail

**Happy analyzing! 🚀**
