from web3 import Web3
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# RPC and contract information
rpc_url = os.getenv("RPC_URL")
contract_address = os.getenv("CONTRACT_ADDRESS")

# provider
w3 = Web3(Web3.HTTPProvider(rpc_url))
print("Connected:", w3.is_connected())

# Load ABI
with open("artifacts/contracts/ContractRegistry.sol/ContractRegistry.json") as f:
    contract_json = json.load(f)

abi = contract_json["abi"]

# Connect to smart contract
contract = w3.eth.contract(address=contract_address, abi=abi)

# wallet info (Tenderly won't expose local accounts)
wallet_address = os.getenv("WALLET_ADDRESS")
private_key = os.getenv("PRIVATE_KEY")

# ACTUS-style contract input
actus_contract = {
    "contractType": "PAM",
    "principal": 100000,
    "interestRate": 0.08,
    "maturityDate": "2028-01-01"
}

contract_string = json.dumps(actus_contract)

# Store contract data
nonce = w3.eth.get_transaction_count(wallet_address)
txn = contract.functions.storeContract(contract_string).build_transaction({
    'from': wallet_address,
    'nonce': nonce,
    'gas': 2000000,
    'gasPrice': w3.to_wei('20', 'gwei')
})

signed_txn = w3.eth.account.sign_transaction(txn, private_key=private_key)
tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
print("Transaction:", tx_hash.hex())

# Retrieve stored contract
stored = contract.functions.getContract().call()

print("Stored Contract:", stored)