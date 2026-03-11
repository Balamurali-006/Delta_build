from web3 import Web3
import hashlib
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to Ethereum
w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))

# Contract address
contract_address = os.getenv("CONTRACT_ADDRESS")

# ABI
with open("abi.json", "r") as f:
    abi = f.read()

contract = w3.eth.contract(
    address=contract_address,
    abi=abi
)

# Example data
data = "Financial Contract Example"

# Create hash
hash_value = hashlib.sha256(data.encode()).hexdigest()

print("Generated Hash:", hash_value)

# Store hash on blockchain
# Note: You need to have a private key and wallet address set up
# For this test, you'll need to replace with actual values
private_key = os.getenv("PRIVATE_KEY")
wallet_address = os.getenv("WALLET_ADDRESS")

# Build transaction
tx = contract.functions.storeHash(hash_value).build_transaction({
    'from': wallet_address,
    'nonce': w3.eth.get_transaction_count(wallet_address),
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
stored = contract.functions.getHash().call()

print("Stored Hash:", stored)
