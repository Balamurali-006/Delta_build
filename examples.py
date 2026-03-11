"""
EXAMPLE: Using the Orchestrator Programmatically

This file shows how to integrate the orchestrator into your own Python code
(backend service, batch processor, API, etc.)
"""

import sys
from pathlib import Path
import json

# Add orchestrator to path
orchestrator_path = Path(__file__).parent / "orchestrator.py"
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import (
    start_actus_engine,
    stop_actus_engine,
    call_actus_pipeline,
    predict_risk,
    store_to_blockchain,
    print_complete_report,
)


# =============================================================================
# EXAMPLE 1: Simple One-Shot Pipeline
# =============================================================================

def example_simple():
    """Run the complete pipeline with default settings."""
    
    contract_text = """
    LOAN AGREEMENT dated 1st January 2024
    
    PRINCIPAL: 50 Lakhs (50,00,000 INR)
    INTEREST RATE: 8.5% per annum
    TENURE: 5 years
    START DATE: 2024-01-01
    END DATE: 2029-01-01
    
    Monthly EMI payments commencing February 2024.
    """
    
    try:
        # Start engine
        if not start_actus_engine():
            print("Failed to start ACTUS engine")
            return
        
        # Run ACTUS pipeline
        actus_output = call_actus_pipeline(contract_text)
        if not actus_output:
            print("ACTUS pipeline failed")
            return
        
        # Run AI prediction
        risk_result = predict_risk(actus_output)
        
        # Store to blockchain (optional)
        tx_hash = store_to_blockchain(actus_output, risk_result or {})
        
        # Display results
        print_complete_report(contract_text, actus_output, risk_result, tx_hash)
        
    finally:
        stop_actus_engine()


# =============================================================================
# EXAMPLE 2: Error Handling and Custom Logic
# =============================================================================

def example_with_error_handling():
    """Run pipeline with detailed error handling."""
    
    contract_text = "Your contract text here..."
    result = {
        "success": False,
        "stages": {}
    }
    
    try:
        # Stage 1: Start engine
        print("🚀 Starting ACTUS engine...")
        if not start_actus_engine():
            result["stages"]["actus_start"] = "FAILED"
            return result
        result["stages"]["actus_start"] = "SUCCESS"
        
        # Stage 2: Call ACTUS pipeline
        print("📋 Parsing contract with ACTUS...")
        actus_output = call_actus_pipeline(contract_text)
        if not actus_output:
            result["stages"]["actus_pipeline"] = "FAILED"
            return result
        result["stages"]["actus_pipeline"] = "SUCCESS"
        result["actus_summary"] = actus_output.get("summary", {})
        
        # Stage 3: AI prediction
        print("🤖 Running AI risk prediction...")
        try:
            risk_result = predict_risk(actus_output)
            result["stages"]["ai_prediction"] = "SUCCESS"
            result["risk_prediction"] = risk_result
        except Exception as e:
            print(f"⚠️  AI prediction failed: {e}")
            result["stages"]["ai_prediction"] = "FAILED (optional)"
            risk_result = None
        
        # Stage 4: Blockchain storage
        print("⛓️  Storing to blockchain...")
        try:
            tx_hash = store_to_blockchain(actus_output, risk_result or {})
            if tx_hash:
                result["stages"]["blockchain"] = "SUCCESS"
                result["tx_hash"] = tx_hash
            else:
                result["stages"]["blockchain"] = "SKIPPED (not configured)"
        except Exception as e:
            print(f"⚠️  Blockchain storage failed: {e}")
            result["stages"]["blockchain"] = "FAILED"
        
        result["success"] = True
        return result
        
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        result["error"] = str(e)
        return result
    
    finally:
        stop_actus_engine()


# =============================================================================
# EXAMPLE 3: Batch Processing Multiple Contracts
# =============================================================================

def example_batch_processing():
    """Process multiple contracts from a file."""
    
    contracts = [
        {
            "id": "LOAN_001",
            "text": "Loan of 10 lakhs at 9% for 5 years..."
        },
        {
            "id": "LOAN_002",
            "text": "Loan of 25 lakhs at 8.5% for 10 years..."
        },
        {
            "id": "LOAN_003",
            "text": "Loan of 5 lakhs at 10% for 3 years..."
        },
    ]
    
    results = []
    
    try:
        # Start engine once for all contracts
        if not start_actus_engine():
            return results
        
        for contract in contracts:
            print(f"\n📄 Processing {contract['id']}...")
            
            try:
                # Run ACTUS
                actus_output = call_actus_pipeline(
                    contract['text'],
                    contract_id=contract['id']
                )
                
                if not actus_output:
                    results.append({
                        "contract_id": contract['id'],
                        "status": "FAILED",
                        "error": "ACTUS pipeline failed"
                    })
                    continue
                
                # Run AI prediction
                risk_result = predict_risk(actus_output)
                
                # Store blockchain
                tx_hash = store_to_blockchain(actus_output, risk_result or {})
                
                results.append({
                    "contract_id": contract['id'],
                    "status": "SUCCESS",
                    "summary": actus_output.get("summary", {}),
                    "risk": risk_result,
                    "tx_hash": tx_hash,
                })
                
            except Exception as e:
                results.append({
                    "contract_id": contract['id'],
                    "status": "ERROR",
                    "error": str(e)
                })
        
        return results
        
    finally:
        stop_actus_engine()


# =============================================================================
# EXAMPLE 4: Integration with Web Framework (FastAPI)
# =============================================================================

def example_fastapi_integration():
    """
    Example of integrating orchestrator into FastAPI.
    
    from fastapi import FastAPI, BackgroundTasks
    from pydantic import BaseModel
    from orchestrator import run_orchestrator
    
    app = FastAPI()
    
    class ContractRequest(BaseModel):
        text: str
        contract_id: str = "contract_001"
    
    @app.post("/analyze")
    async def analyze_contract(request: ContractRequest, background_tasks: BackgroundTasks):
        '''Analyze contract and store results.'''
        
        def process_contract():
            result = run_orchestrator(request.text, request.contract_id)
            # Save to database, send notification, etc.
        
        background_tasks.add_task(process_contract)
        return {"status": "processing", "contract_id": request.contract_id}
    
    @app.get("/status/{contract_id}")
    async def get_status(contract_id: str):
        '''Get status of contract analysis.'''
        # Query database for results
        pass
    """
    
    print(__doc__)


# =============================================================================
# EXAMPLE 5: Custom Risk Thresholds
# =============================================================================

def example_custom_risk_logic():
    """Apply custom risk logic on top of AI predictions."""
    
    contract_text = "Your contract..."
    
    try:
        start_actus_engine()
        
        actus_output = call_actus_pipeline(contract_text)
        if not actus_output:
            return
        
        risk_result = predict_risk(actus_output)
        summary = actus_output.get("summary", {})
        
        # Custom business logic
        custom_decision = apply_business_rules(risk_result, summary)
        
        # Store with custom decision
        store_to_blockchain(actus_output, {
            **risk_result,
            "custom_decision": custom_decision
        })
        
    finally:
        stop_actus_engine()


def apply_business_rules(risk_result, summary):
    """
    Apply custom business rules beyond AI prediction.
    
    Example: Apply different thresholds for different loan amounts.
    """
    
    if not risk_result:
        return None
    
    principal = summary.get("principal", 0)
    default_prob = risk_result.get("default_probability", 0)
    
    # Custom thresholds by loan amount
    if principal > 100_000_000:  # Large loan (1 crore+)
        threshold = 0.25  # Stricter: 25%
    elif principal > 10_000_000:  # Medium loan (10 lakhs+)
        threshold = 0.35  # Standard: 35%
    else:  # Small loan
        threshold = 0.45  # Lenient: 45%
    
    if default_prob > threshold:
        recommendation = f"REJECT - Default prob {default_prob*100:.1f}% > threshold {threshold*100:.0f}%"
    else:
        recommendation = f"APPROVE - Default prob {default_prob*100:.1f}% < threshold {threshold*100:.0f}%"
    
    return {
        "threshold": threshold,
        "custom_recommendation": recommendation
    }


# =============================================================================
# EXAMPLE 6: Save Results to JSON
# =============================================================================

def example_save_results():
    """Save pipeline results to JSON for archival."""
    
    contract_text = "Your contract..."
    contract_id = "CONTRACT_001"
    
    try:
        start_actus_engine()
        
        actus_output = call_actus_pipeline(contract_text, contract_id)
        if not actus_output:
            return
        
        risk_result = predict_risk(actus_output)
        tx_hash = store_to_blockchain(actus_output, risk_result or {})
        
        # Combine all results
        complete_result = {
            "contract_id": contract_id,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "actus": actus_output,
            "risk_prediction": risk_result,
            "blockchain": {
                "tx_hash": tx_hash,
                "status": "submitted"
            }
        }
        
        # Save to file
        output_file = f"results/{contract_id}.json"
        Path("results").mkdir(exist_ok=True)
        
        with open(output_file, "w") as f:
            json.dump(complete_result, f, indent=2)
        
        print(f"✅ Results saved to {output_file}")
        
        return complete_result
        
    finally:
        stop_actus_engine()


# =============================================================================
# MAIN: RUN EXAMPLES
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Orchestrator examples")
    parser.add_argument("--example", choices=[
        "simple",
        "error-handling",
        "batch",
        "fastapi",
        "custom-logic",
        "save-json"
    ], default="simple")
    
    args = parser.parse_args()
    
    if args.example == "simple":
        print("Running: Simple one-shot pipeline")
        example_simple()
    
    elif args.example == "error-handling":
        print("Running: Pipeline with error handling")
        result = example_with_error_handling()
        print(f"\nPipeline result: {json.dumps(result, indent=2)}")
    
    elif args.example == "batch":
        print("Running: Batch processing multiple contracts")
        results = example_batch_processing()
        print(f"\nBatch results: {json.dumps(results, indent=2)}")
    
    elif args.example == "fastapi":
        print("Running: FastAPI integration example")
        example_fastapi_integration()
    
    elif args.example == "custom-logic":
        print("Running: Custom risk logic")
        example_custom_risk_logic()
    
    elif args.example == "save-json":
        print("Running: Save results to JSON")
        result = example_save_results()
        print(f"\nComplete result: {json.dumps(result, indent=2)}")
