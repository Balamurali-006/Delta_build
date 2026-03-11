from Ai_prediction.load_model import predict_risk,_build_minimal_actus_output

contract=_build_minimal_actus_output(2000000,0.09,10)
print('contract',contract['summary']['contractID'])
print('result', predict_risk(contract))
