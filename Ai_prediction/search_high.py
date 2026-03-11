import random
from load_model import predict_risk

for i in range(10000):
    c = {
        "loan_amount": random.choice([5000,10000,20000,50000,100000]),
        "interest_rate": random.choice([0.08,0.1,0.12,0.15,0.2]),
        "loan_term_months": random.choice([12,24,36,48,60,72,120]),
        "credit_score": random.choice([300,400,500,550,580,600,620]),
        "collateral_ratio": random.choice([0.0,0.1,0.2]),
        "grade_encoded": random.choice([5,6,7]),
        "annual_income": random.choice([20000,30000,40000]),
        "dti": random.uniform(20,60),
        "emp_length_years": random.choice([0,1,2,3])
    }
    res = predict_risk(c)
    if res['risk_category']=='HIGH':
        print('found', c, res)
        break
