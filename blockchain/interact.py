from web3 import Web3
import hashlib
import os
import json
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to Ethereum
w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))

# Contract address
contract_address = os.getenv("CONTRACT_ADDRESS")

# ABI
with open("abi.json", "r") as f:
    abi = json.load(f)

contract = w3.eth.contract(
    address=contract_address,
    abi=abi
)

# Wallets
private_key = os.getenv("PRIVATE_KEY")
wallet_address = os.getenv("WALLET_ADDRESS")

# Prepare structured financial data (JSON)
if len(sys.argv) > 1:
    data_str = sys.argv[1]
else:
    combined_data = {
        "contractID": "DB-DEMO-001",
        "contractType": "PAM",
        "principal": 2500000,
        "risk_category": "LOW",
        "timestamp": "2024-03-12T12:00:00"
    }
    data_str = json.dumps(combined_data)

print(f"Storing data on-chain: {data_str}")

# Build transaction
nonce = w3.eth.get_transaction_count(wallet_address)
tx = contract.functions.storeContract(data_str).build_transaction({
    'from': wallet_address,
    'nonce': nonce,
    'gas': 2000000,
    'gasPrice': w3.to_wei('50', 'gwei')
})

# Sign transaction
signed_tx = w3.eth.account.sign_transaction(tx, private_key)

# Send transaction
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

print("Transaction Hash:", tx_hash.hex())

# Wait for transaction receipt
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print("Transaction confirmed in block:", tx_receipt.blockNumber)

# Read data from blockchain
stored = contract.functions.getContract().call()

print("Stored Data:", stored)
