import requests
import json

payload = {
    "text": "A home loan of 20,00,000 INR at 9% interest for 10 years, starting 2024-01-01. Monthly EMI payments",
    "contract_id": "homeloan-test"
}

r = requests.post("http://localhost:8000/full-pipeline", json=payload)
print(r.status_code)
if r.status_code == 200:
    print("Success!")
    data = r.json()
    print(f"Contract Type: {data['actusJson']['contractType']}")
    print(f"Total Events: {data['summary']['totalEvents']}")
else:
    print(r.text)
