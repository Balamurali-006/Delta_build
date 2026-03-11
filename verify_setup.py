#!/usr/bin/env python3
"""
COMPONENT VERIFICATION SCRIPT
Verify each component is working before running orchestrator.py

Usage:
    python verify_setup.py                 # Full check
    python verify_setup.py --actus-only    # Just check ACTUS
    python verify_setup.py --ai-only       # Just check AI
    python verify_setup.py --blockchain-only  # Just check blockchain
"""

import os
import sys
import subprocess
import importlib.util
import argparse
from pathlib import Path
from typing import Tuple, Optional

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")

def success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

# ─────────────────────────────────────────────────────────────────────────────
# ACTUS ENGINE VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def verify_actus() -> bool:
    print_header("VERIFYING ACTUS ENGINE (actus_engine/)")
    
    all_good = True
    
    # 1. Check if main_v2.py exists
    actus_dir = Path("actus_engine")
    main_file = actus_dir / "main_v2.py"
    
    if main_file.exists():
        success(f"Found {main_file}")
    else:
        error(f"Missing {main_file}")
        return False
    
    # 2. Check .env file
    env_file = actus_dir / ".env"
    if env_file.exists():
        success(f"Found {env_file}")
        with open(env_file) as f:
            content = f.read()
            if "GROQ_API_KEY" in content:
                success("GROQ_API_KEY is configured")
            else:
                error("GROQ_API_KEY not found in .env")
                all_good = False
    else:
        error(f"Missing {env_file} - Create it with GROQ_API_KEY")
        all_good = False
    
    # 3. Check requirements
    requirements_file = actus_dir / "requirements.txt"
    if requirements_file.exists():
        success(f"Found {requirements_file}")
        with open(requirements_file) as f:
            requirements = f.read()
            required_packages = ["fastapi", "uvicorn", "groq", "pydantic", "awesome-actus-lib"]
            for pkg in required_packages:
                if pkg.lower() in requirements.lower():
                    success(f"  ✓ {pkg} in requirements")
                else:
                    warning(f"  ⚠ {pkg} not found, may need manual install")
    else:
        warning(f"No {requirements_file}")
        all_good = False
    
    # 4. Try importing key modules
    try:
        import fastapi
        success("FastAPI installed ✓")
    except ImportError:
        error("FastAPI NOT installed - run: pip install fastapi")
        all_good = False
    
    try:
        import groq
        success("Groq SDK installed ✓")
    except ImportError:
        error("Groq SDK NOT installed - run: pip install groq")
        all_good = False
    
    # 5. Check if uvicorn is available
    try:
        result = subprocess.run(
            [sys.executable, "-m", "uvicorn", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            success(f"Uvicorn available: {result.stdout.strip()}")
        else:
            error("Uvicorn not available")
            all_good = False
    except Exception as e:
        error(f"Cannot run uvicorn: {e}")
        all_good = False
    
    # 6. Check port 8000 availability
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8000))
        sock.close()
        
        if result != 0:
            success("Port 8000 is available")
        else:
            warning("Port 8000 is already in use - running will fail")
            all_good = False
    except Exception as e:
        warning(f"Could not check port: {e}")
    
    return all_good


# ─────────────────────────────────────────────────────────────────────────────
# AI PREDICTION VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def verify_ai() -> bool:
    print_header("VERIFYING AI PREDICTION (Ai_prediction/)")
    
    all_good = True
    ai_dir = Path("Ai_prediction")
    
    # 1. Check load_model.py
    load_model_file = ai_dir / "load_model.py"
    if load_model_file.exists():
        success(f"Found {load_model_file}")
    else:
        error(f"Missing {load_model_file}")
        return False
    
    # 2. Check model file
    model_file = ai_dir / "actus_risk_model.pkl"
    if model_file.exists():
        success(f"Found {model_file} ({os.path.getsize(model_file) / 1024 / 1024:.1f} MB)")
    else:
        error(f"Missing {model_file} - Model must be trained first")
        all_good = False
    
    # 3. Check feature columns file
    features_file = ai_dir / "feature_cols.json"
    if features_file.exists():
        success(f"Found {features_file}")
        try:
            import json
            with open(features_file) as f:
                features = json.load(f)
            success(f"  ✓ Contains {len(features) if isinstance(features, list) else 'unknown'} features")
        except Exception as e:
            error(f"  ✗ Cannot parse feature_cols.json: {e}")
            all_good = False
    else:
        error(f"Missing {features_file}")
        all_good = False
    
    # 4. Check required packages
    required = ["sklearn", "pandas", "numpy"]
    for pkg in required:
        try:
            __import__(pkg)
            success(f"{pkg} installed ✓")
        except ImportError:
            error(f"{pkg} NOT installed - run: pip install {pkg}")
            all_good = False
    
    # 5. Try loading the module
    try:
        sys.path.insert(0, str(ai_dir))
        spec = importlib.util.spec_from_file_location("load_model", load_model_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        success("load_model.py loads successfully ✓")
        sys.path.pop(0)
    except Exception as e:
        error(f"Cannot load load_model.py: {e}")
        all_good = False
        sys.path.pop(0) if 0 < len(sys.path) else None
    
    return all_good


# ─────────────────────────────────────────────────────────────────────────────
# BLOCKCHAIN VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def verify_blockchain() -> bool:
    print_header("VERIFYING BLOCKCHAIN (blockchain_test/)")
    
    all_good = True
    bc_dir = Path("blockchain_test")
    
    # 1. Check test_blockchain.py
    test_file = bc_dir / "test_blockchain.py"
    if test_file.exists():
        success(f"Found {test_file}")
    else:
        error(f"Missing {test_file}")
        return False
    
    # 2. Check .env file
    env_file = bc_dir / ".env"
    if env_file.exists():
        success(f"Found {env_file}")
        with open(env_file) as f:
            content = f.read()
            required_keys = ["RPC_URL", "CONTRACT_ADDRESS", "WALLET_ADDRESS", "PRIVATE_KEY"]
            for key in required_keys:
                if key in content:
                    # Check if value is set
                    for line in content.split('\n'):
                        if line.startswith(key):
                            if "=" in line:
                                value = line.split("=", 1)[1].strip()
                                if value and value != "your" and not value.endswith("..."):
                                    success(f"  ✓ {key} is set")
                                else:
                                    warning(f"  ⚠ {key} appears empty or placeholder")
                                    all_good = False
                                break
                else:
                    error(f"  ✗ {key} not found in .env")
                    all_good = False
    else:
        error(f"Missing {env_file} - Create it with blockchain credentials")
        all_good = False
    
    # 3. Check for ABI file
    abi_file = bc_dir / "artifacts/contracts/ContractRegistry.sol/ContractRegistry.json"
    if abi_file.exists():
        success(f"Found contract ABI: {abi_file}")
        try:
            import json
            with open(abi_file) as f:
                abi_data = json.load(f)
            if "abi" in abi_data:
                success(f"  ✓ ABI valid ({len(abi_data['abi'])} functions/events)")
            else:
                warning("  ⚠ ABI file missing 'abi' key")
        except Exception as e:
            error(f"  ✗ Cannot parse ABI: {e}")
            all_good = False
    else:
        warning(f"Missing {abi_file} - Blockchain storage may fail")
        all_good = False
    
    # 4. Check Web3 installation
    try:
        import web3
        success("Web3.py installed ✓")
    except ImportError:
        error("Web3.py NOT installed - run: pip install web3")
        all_good = False
    
    # 5. Check if RPC is reachable (if configured)
    if env_file.exists():
        try:
            from dotenv import dotenv_values
            env_vars = dotenv_values(str(env_file))
            rpc_url = env_vars.get("RPC_URL", "")
            
            if rpc_url and rpc_url != "https://your-rpc-endpoint.com":
                try:
                    import requests
                    response = requests.post(rpc_url, json={"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}, timeout=5)
                    if response.status_code == 200:
                        success(f"RPC endpoint is reachable: {rpc_url}")
                    else:
                        warning(f"RPC endpoint returned status {response.status_code}")
                except Exception as e:
                    warning(f"Cannot reach RPC endpoint: {e}")
                    info("  (This is OK if you don't need blockchain yet)")
        except Exception as e:
            info(f"Cannot check RPC: {e}")
    
    return all_good


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def verify_orchestrator() -> bool:
    print_header("VERIFYING ORCHESTRATOR")
    
    all_good = True
    
    # 1. Check orchestrator.py exists
    orch_file = Path("orchestrator.py")
    if orch_file.exists():
        success(f"Found {orch_file}")
    else:
        error(f"Missing {orch_file}")
        return False
    
    # 2. Check required packages
    required = ["requests", "python-dotenv"]
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
            success(f"{pkg} installed ✓")
        except ImportError:
            error(f"{pkg} NOT installed - run: pip install {pkg}")
            all_good = False
    
    return all_good


# ─────────────────────────────────────────────────────────────────────────────
# MAIN VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Verify BC pipeline setup")
    parser.add_argument("--actus-only", action="store_true")
    parser.add_argument("--ai-only", action="store_true")
    parser.add_argument("--blockchain-only", action="store_true")
    parser.add_argument("--orchestrator-only", action="store_true")
    
    args = parser.parse_args()
    
    results = {}
    
    if args.actus_only or (not any([args.ai_only, args.blockchain_only, args.orchestrator_only])):
        results["ACTUS"] = verify_actus()
    
    if args.ai_only or (not any([args.actus_only, args.blockchain_only, args.orchestrator_only])):
        results["AI Prediction"] = verify_ai()
    
    if args.blockchain_only or (not any([args.actus_only, args.ai_only, args.orchestrator_only])):
        results["Blockchain"] = verify_blockchain()
    
    if args.orchestrator_only or (not any([args.actus_only, args.ai_only, args.blockchain_only])):
        results["Orchestrator"] = verify_orchestrator()
    
    # Final summary
    print_header("SUMMARY")
    
    all_passed = True
    for component, passed in results.items():
        status = f"{Colors.GREEN}✓ READY{Colors.RESET}" if passed else f"{Colors.RED}✗ ISSUES{Colors.RESET}"
        print(f"{component}: {status}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        success("All components ready! You can now run:")
        print(f"{Colors.BOLD}  python orchestrator.py --demo{Colors.RESET}\n")
    else:
        error("Some components need attention. Review issues above.")
        print(f"\nFor help, see: {Colors.BOLD}README.md{Colors.RESET}\n")
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
