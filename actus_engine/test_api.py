import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    print("Testing /health...")
    r = requests.get(f"{BASE_URL}/health")
    print(json.dumps(r.json(), indent=2))
    return r.status_code == 200

def test_full_pipeline():
    print("\nTesting /full-pipeline with sample contract...")
    sample_contract = """
    LOAN AGREEMENT
    
    Lender: FinTwin Capital
    Borrower: John Doe
    
    Principal Amount: 50,000 INR
    Interest Rate: 12% per annum (fixed)
    Start Date: 2024-02-01
    Maturity Date: 2025-02-01
    Repayment: The borrower shall pay the principal and interest in equal monthly installments (EMI).
    """
    
    payload = {
        "text": sample_contract,
        "contract_id": "test-loan-001"
    }
    
    try:
        r = requests.post(f"{BASE_URL}/full-pipeline", json=payload)
        if r.status_code == 200:
            data = r.json()
            print("Successfully parsed and simulated!")
            print(f"Contract Type: {data['actusJson']['contractType']}")
            print(f"Total Cash Flow Events: {data['summary']['totalEvents']}")
            print(f"Total Interest: {data['summary']['totalInterest']} INR")
            
            # Print first 3 cash flow events
            print("\nFirst 3 Cash Flows:")
            for cf in data['cashFlows'][:3]:
                print(f"[{cf['time']}] {cf['type']}: {cf['payoff']} {cf['currency']}")
        else:
            print(f"Error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    if test_health():
        test_full_pipeline()
    else:
        print("Server is not healthy. Make sure it's running on port 8000.")
