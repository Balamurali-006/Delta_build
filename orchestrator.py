"""
================================================================================
UNIFIED ORCHESTRATOR — ACTUS → AI Risk → Blockchain
================================================================================

This single script orchestrates the entire pipeline:
1. Start ACTUS engine on port 8000 (uvicorn)
2. Send contract to /full-pipeline endpoint
3. Feed ACTUS output to AI risk prediction model
4. Store combined result to blockchain
5. Display complete audit trail

USAGE:
    python orchestrator.py --contract-text "your contract text"
    python orchestrator.py --contract-json "path/to/contract.json"
    python orchestrator.py --demo  (uses built-in test contract)

ENVIRONMENT:
    Create .env files in:
      - actus_engine/.env      (GROQ_API_KEY, GROQ_MODEL)
      - blockchain_test/.env   (RPC_URL, CONTRACT_ADDRESS, WALLET_ADDRESS, PRIVATE_KEY)
"""

import os
import sys
import json
import time
import argparse
import subprocess
import requests
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import signal

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────────────────────────────────────

ACTUS_PORT = 8000
ACTUS_URL = f"http://localhost:{ACTUS_PORT}"
FULL_PIPELINE_ENDPOINT = f"{ACTUS_URL}/full-pipeline"

uvicorn_process = None

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — START ACTUS ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def start_actus_engine() -> bool:
    """
    Start the ACTUS FastAPI server using uvicorn in the background.
    """
    global uvicorn_process
    
    actus_dir = Path(__file__).parent / "actus_engine"
    
    log.info(f"Starting ACTUS engine from: {actus_dir}")
    
    try:
        uvicorn_process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "main_v2:app",
                f"--host", "127.0.0.1",
                f"--port", str(ACTUS_PORT),
                "--log-level", "info"
            ],
            cwd=str(actus_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        # Give it time to start
        time.sleep(3)
        
        # Check if process is still running
        poll_result = uvicorn_process.poll()
        if poll_result is not None:
            # Process died, capture error output
            _, stderr = uvicorn_process.communicate()
            log.error(f"❌ ACTUS engine process exited with code {poll_result}")
            if stderr:
                log.error(f"Stderr: {stderr}")
            return False
        
        # Check if it's running and responding
        try:
            resp = requests.get(f"{ACTUS_URL}/health", timeout=5)
            if resp.status_code == 200:
                log.info(f"✅ ACTUS engine running on {ACTUS_URL}")
                return True
        except requests.exceptions.ConnectionError:
            # Try to get stderr output in case port is not responding
            uvicorn_process.terminate()
            try:
                uvicorn_process.wait(timeout=2)
                _, stderr = uvicorn_process.communicate()
                if stderr:
                    log.error(f"Stderr: {stderr}")
            except:
                pass
        
        log.error("❌ ACTUS engine failed to start")
        return False
        
    except Exception as e:
        log.error(f"❌ Failed to start ACTUS engine: {e}")
        return False


def stop_actus_engine():
    """Kill the ACTUS engine process gracefully."""
    global uvicorn_process
    
    if uvicorn_process:
        try:
            uvicorn_process.terminate()
            uvicorn_process.wait(timeout=5)
            log.info("✅ ACTUS engine stopped")
        except subprocess.TimeoutExpired:
            uvicorn_process.kill()
            log.warning("⚠️  ACTUS engine killed (forced)")
        except Exception as e:
            log.error(f"Error stopping ACTUS engine: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — CALL ACTUS /full-pipeline ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

def call_actus_pipeline(contract_input: str, contract_id: str = "contract_001") -> Optional[Dict[str, Any]]:
    """
    POST to ACTUS endpoints and return the response dict.

    The parameter `contract_input` may be any of:
      * raw text to send to `/full-pipeline`
      * path to a text file
      * path to a PDF file (will call `/full-pipeline-pdf`)

    If the call is successful the JSON result is written to ``output.json``
    in the current working directory so that a frontend/UI can later pick it up.

    Returns the full response:
    {
        "success": true,
        "actusJson": {...},
        "summary": {...},
        "cashFlows": [...]
    }
    """
    log.info("📤 Sending contract to ACTUS pipeline...")

    # decide which endpoint to hit and build request accordingly
    try:
        if os.path.isfile(contract_input):
            # user passed a file path
            if contract_input.lower().endswith(".pdf"):
                # PDF variant
                with open(contract_input, "rb") as f:
                    files = {"file": (os.path.basename(contract_input), f, "application/pdf")}
                    params = {"contract_id": contract_id}
                    response = requests.post(
                        f"{ACTUS_URL}/full-pipeline-pdf",
                        files=files,
                        params=params,
                        timeout=120,
                    )
            else:
                # assume plain text file
                with open(contract_input, "r", encoding="utf-8") as f:
                    text = f.read()
                payload = {"text": text, "contract_id": contract_id}
                response = requests.post(
                    FULL_PIPELINE_ENDPOINT,
                    json=payload,
                    timeout=120,
                )
        else:
            # treat input as raw text
            payload = {"text": contract_input, "contract_id": contract_id}
            response = requests.post(
                FULL_PIPELINE_ENDPOINT,
                json=payload,
                timeout=120,
            )

        if response.status_code != 200:
            log.error(f"❌ ACTUS returned {response.status_code}")
            log.error(f"   Response: {response.text[:500]}")
            return None

        result = response.json()
        if result.get("success"):
            log.info(f"✅ ACTUS pipeline succeeded")
            log.info(f"   Contract Type: {result['summary'].get('contractType')}")
            log.info(f"   Principal: {result['summary'].get('principal')}")
            log.info(f"   Total Events: {result['summary'].get('totalEvents')}")

            # write to disk for UI/demo purposes
            try:
                with open("output.json", "w", encoding="utf-8") as out_f:
                    json.dump(result, out_f, indent=2)
                log.info("📝 Written pipeline output to output.json")
            except Exception as e:
                log.warning(f"⚠️  Could not write output.json: {e}")

            return result
        else:
            log.error(f"❌ ACTUS pipeline failed: {result}")
            return None

    except requests.exceptions.Timeout:
        log.error(f"❌ ACTUS request timeout (120s). Groq API may be slow.")
        return None
    except requests.exceptions.ConnectionError:
        log.error(f"❌ Cannot connect to ACTUS engine at {ACTUS_URL}")
        log.error(f"   Make sure it's running: python orchestrator.py --demo")
        return None
    except Exception as e:
        log.error(f"❌ ACTUS call failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — FEED OUTPUT TO AI PREDICTION MODEL
# ─────────────────────────────────────────────────────────────────────────────

def predict_risk(actus_output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Import the AI prediction model and run risk analysis.
    
    The model expects:
    {
        "success": true,
        "summary": {...},
        "cashFlows": [...]
    }
    """
    log.info("🤖 Running AI risk prediction model...")
    
    ai_dir = Path(__file__).parent / "Ai_prediction"
    
    try:
        # Change to AI directory and add to path
        original_cwd = os.getcwd()
        os.chdir(str(ai_dir))
        sys.path.insert(0, str(ai_dir))
        
        # Import the prediction function
        from load_model import predict_risk as predict_risk_fn
        
        # Call it with ACTUS output
        result = predict_risk_fn(actus_output)
        
        if "error" in result:
            log.error(f"❌ AI prediction error: {result['error']}")
            return None
        
        log.info(f"✅ AI prediction complete")
        log.info(f"   Risk Category: {result.get('risk_category')}")
        log.info(f"   Default Probability: {result.get('default_probability', 0)*100:.1f}%")
        log.info(f"   Expected Loss: {result.get('expected_loss')}")
        log.info(f"   Recommendation: {result.get('recommendation')}")
        
        return result
        
    except ImportError as e:
        log.error(f"❌ Cannot import AI model: {e}")
        log.error(f"   Make sure {ai_dir / 'load_model.py'} exists")
        log.error(f"   Make sure {ai_dir / 'actus_risk_model.pkl'} exists")
        return None
    except Exception as e:
        log.error(f"❌ AI prediction failed: {e}")
        return None
    finally:
        # Restore original directory and path
        os.chdir(original_cwd)
        sys.path.pop(0)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — STORE TO BLOCKCHAIN
# ─────────────────────────────────────────────────────────────────────────────

def store_to_blockchain(
    actus_output: Dict[str, Any],
    risk_prediction: Dict[str, Any],
) -> Optional[str]:
    """
    Store the combined ACTUS + AI output to blockchain using Web3.
    
    This replicates test_blockchain.py logic but parameterized.
    """
    log.info("⛓️  Storing to blockchain...")
    
    blockchain_dir = Path(__file__).parent / "blockchain_test"
    
    try:
        # Add blockchain directory to path temporarily
        sys.path.insert(0, str(blockchain_dir))
        
        from web3 import Web3
        from dotenv import load_dotenv
        
        # Load .env for blockchain config
        env_file = blockchain_dir / ".env"
        if not env_file.exists():
            log.warning(f"⚠️  No .env in {blockchain_dir}. Blockchain storage skipped.")
            return None
        
        from dotenv import dotenv_values
        blockchain_env = dotenv_values(str(env_file))
        
        rpc_url = blockchain_env.get("RPC_URL")
        contract_address = blockchain_env.get("CONTRACT_ADDRESS")
        wallet_address = blockchain_env.get("WALLET_ADDRESS")
        private_key = blockchain_env.get("PRIVATE_KEY")
        
        if not all([rpc_url, contract_address, wallet_address, private_key]):
            log.warning("⚠️  Blockchain .env missing required fields. Skipping blockchain storage.")
            return None
        
        # Connect to Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            log.error("❌ Cannot connect to blockchain RPC")
            return None
        
        log.info(f"✅ Connected to blockchain: {rpc_url}")
        
        # Load contract ABI
        abi_file = blockchain_dir / "artifacts/contracts/ContractRegistry.sol/ContractRegistry.json"
        if not abi_file.exists():
            log.error(f"❌ ABI file not found: {abi_file}")
            return None
        
        with open(abi_file) as f:
            contract_json = json.load(f)
        
        abi = contract_json["abi"]
        contract = w3.eth.contract(address=contract_address, abi=abi)
        
        # Prepare combined payload
        combined_data = {
            "timestamp": datetime.now().isoformat(),
            "actus": actus_output.get("summary", {}),
            "risk_prediction": risk_prediction,
        }
        
        contract_string = json.dumps(combined_data)
        log.info(f"📝 Contract data size: {len(contract_string)} bytes")
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(wallet_address)
        txn = contract.functions.storeContract(contract_string).build_transaction({
            'from': wallet_address,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.to_wei('20', 'gwei')
        })
        
        # Sign and send
        signed_txn = w3.eth.account.sign_transaction(txn, private_key=private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_hex = tx_hash.hex()
        
        log.info(f"✅ Transaction submitted: {tx_hex}")
        
        # Wait for confirmation (optional, with timeout)
        try:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            log.info(f"✅ Transaction confirmed in block {receipt['blockNumber']}")
        except Exception as e:
            log.warning(f"⚠️  Transaction receipt not ready yet: {e}")
        
        return tx_hex
        
    except ImportError as e:
        log.error(f"❌ Web3 not installed: {e}")
        log.info("   Install with: pip install web3 python-dotenv")
        return None
    except Exception as e:
        log.error(f"❌ Blockchain storage failed: {e}")
        return None
    finally:
        sys.path.pop(0)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — DISPLAY COMPLETE REPORT
# ─────────────────────────────────────────────────────────────────────────────

def print_complete_report(
    contract_text: str,
    actus_output: Dict[str, Any],
    risk_prediction: Optional[Dict[str, Any]],
    tx_hash: Optional[str],
):
    """Pretty-print the complete end-to-end pipeline result."""
    
    summary = actus_output.get("summary", {})
    currency = summary.get("currency", "INR")
    sym = "₹" if currency == "INR" else "$"
    
    risk_icons = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
    risk_icon = "⚪"
    if risk_prediction:
        risk_icon = risk_icons.get(risk_prediction.get("risk_category", ""), "⚪")
    
    print("\n" + "=" * 80)
    print("   UNIFIED ORCHESTRATOR — COMPLETE PIPELINE REPORT")
    print("=" * 80)
    
    print("\n📋 STEP 1 — CONTRACT PARSING (ACTUS ENGINE)")
    print("-" * 80)
    print(f"   Contract Type    : {summary.get('contractType', 'N/A')}")
    print(f"   Contract ID      : {summary.get('contractID', 'N/A')}")
    print(f"   Principal        : {sym}{summary.get('principal', 0):>15,.2f}")
    print(f"   Interest Rate    : {summary.get('nominalRate', 0)*100:>15.2f}%")
    print(f"   Start Date       : {summary.get('startDate', 'N/A')}")
    print(f"   Maturity Date    : {summary.get('maturityDate', 'N/A')}")
    print(f"   Total Interest   : {sym}{summary.get('totalInterest', 0):>15,.2f}")
    print(f"   Total Cashflow   : {sym}{summary.get('totalCashFlow', 0):>15,.2f}")
    print(f"   Total Events     : {summary.get('totalEvents', 0):>15} cash flow events")
    
    if risk_prediction:
        print("\n🤖 STEP 2 — RISK ANALYSIS (AI PREDICTION MODEL)")
        print("-" * 80)
        print(f"   Risk Category       : {risk_icon}  {risk_prediction.get('risk_category', 'N/A')}")
        print(f"   Default Probability : {risk_prediction.get('default_probability', 0)*100:>15.1f}%")
        print(f"   Expected Loss       : {sym}{risk_prediction.get('expected_loss', 0):>15,.2f}")
        print(f"   Recommendation      : {risk_prediction.get('recommendation', 'N/A')}")
        
        if "negotiation_tips" in risk_prediction:
            print(f"\n   🔧 NEGOTIATION TIPS (HIGH RISK):")
            for tip in risk_prediction["negotiation_tips"]:
                print(f"      • {tip}")
    
    if tx_hash:
        print("\n⛓️  STEP 3 — BLOCKCHAIN STORAGE")
        print("-" * 80)
        print(f"   Transaction Hash : {tx_hash}")
        print(f"   Status           : Submitted to blockchain")
    
    print("\n" + "=" * 80)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ORCHESTRATION FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def run_orchestrator(contract_text: str, contract_id: str = "contract_001"):
    """Main orchestration logic."""
    
    try:
        # Step 1: Start ACTUS engine
        if not start_actus_engine():
            log.error("❌ Failed to start ACTUS engine. Exiting.")
            return False
        
        # Step 2: Call ACTUS pipeline
        actus_output = call_actus_pipeline(contract_text, contract_id)
        if not actus_output:
            log.error("❌ ACTUS pipeline failed. Exiting.")
            return False
        
        # Step 3: Run AI risk prediction
        risk_prediction = predict_risk(actus_output)
        if not risk_prediction:
            log.warning("⚠️  AI prediction failed, continuing without risk analysis...")
        
        # Step 4: Store to blockchain (optional)
        tx_hash = store_to_blockchain(actus_output, risk_prediction or {})
        
        # Step 5: Display complete report
        print_complete_report(contract_text, actus_output, risk_prediction, tx_hash)
        
        return True
        
    except KeyboardInterrupt:
        log.info("⚠️  Orchestrator interrupted by user")
        return False
    except Exception as e:
        log.error(f"❌ Orchestrator failed: {e}")
        return False
    finally:
        # Always stop the ACTUS engine on exit
        stop_actus_engine()


# ─────────────────────────────────────────────────────────────────────────────
# DEMO CONTRACT
# ─────────────────────────────────────────────────────────────────────────────

DEMO_CONTRACT_TEXT = """
LOAN AGREEMENT

This Loan Agreement ("Agreement") dated 1st January 2024, entered into between:

LENDER: ABC Bank Limited, Mumbai
BORROWER: XYZ Company Private Limited, Bangalore

1. LOAN DETAILS
   - Loan Amount: 25 Lakhs (25,00,000 INR)
   - Interest Rate: 9% per annum
   - Tenure: 10 years
   - Loan Start Date: 2024-01-01
   - Loan Maturity Date: 2034-01-01

2. REPAYMENT TERMS
   - Monthly EMI (Equated Monthly Installment)
   - First EMI Due: February 1, 2024
   - Payment Frequency: Monthly on the 1st of each month

3. DISBURSEMENT
   - Full amount to be disbursed on loan start date
   - Day Count Convention: 365-day year

4. DEFAULT CLAUSE
   Non-payment of monthly EMI within 15 days of due date shall 
   constitute default and invoke penalty interest of 2% per annum.
"""


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Unified ACTUS → AI Risk → Blockchain Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Run with demo contract
  python orchestrator.py --demo

  # Use contract from file (text or PDF)
  python orchestrator.py --contract-file "data/contract1.pdf"
  python orchestrator.py --contract-file "data/contract1.txt"

  # Pass raw text directly
  python orchestrator.py --contract-text "Some loan terms ..."

  # Use ACTUS JSON directly (skip parsing)
  python orchestrator.py --contract-json "path/to/contract.json"

  # Keep engine running for manual testing
  python orchestrator.py --demo --keep-running
        """
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use built-in demo contract"
    )
    
    parser.add_argument(
        "--contract-file",
        type=str,
        help="Path to contract file (text or .pdf)"
    )

    parser.add_argument(
        "--contract-text",
        type=str,
        help="Raw contract text (if not using --contract-file/demo)"
    )
    
    parser.add_argument(
        "--contract-json",
        type=str,
        help="Path to ACTUS JSON file (skips parsing)"
    )
    
    parser.add_argument(
        "--contract-id",
        default="contract_001",
        help="Contract ID (default: contract_001)"
    )
    
    parser.add_argument(
        "--keep-running",
        action="store_true",
        help="Keep ACTUS engine running after orchestrator completes"
    )
    
    args = parser.parse_args()
    
    # Determine contract source
    if args.demo:
        contract_text = DEMO_CONTRACT_TEXT
        log.info("📚 Using DEMO contract")
    elif args.contract_file:
        if not os.path.isfile(args.contract_file):
            log.error(f"Contract file not found: {args.contract_file}")
            sys.exit(1)
        # we don't read here; call_actus_pipeline will handle file paths specially
        contract_text = args.contract_file
        log.info(f"📁 Using contract file {args.contract_file}")
    elif args.contract_text:
        # if it's a file path, the new call_actus_pipeline will also handle it, but
        # keep old behavior of reading text so that raw strings still work.
        if os.path.isfile(args.contract_text) and not args.contract_text.lower().endswith('.pdf'):
            with open(args.contract_text, "r", encoding="utf-8") as f:
                contract_text = f.read()
            log.info(f"📄 Loaded contract from {args.contract_text}")
        else:
            contract_text = args.contract_text
            log.info("📝 Using provided contract text")
    else:
        parser.print_help()
        sys.exit(1)
    
    # Run orchestrator
    success = run_orchestrator(contract_text, args.contract_id)
    
    # Handle --keep-running
    if args.keep_running and uvicorn_process:
        log.info("🔄 Keeping ACTUS engine running...")
        log.info(f"📡 Available at {ACTUS_URL}")
        log.info("   Press Ctrl+C to stop")
        try:
            uvicorn_process.wait()
        except KeyboardInterrupt:
            log.info("Stopping...")
            stop_actus_engine()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
