from awesome_actus_lib import ANN, PublicActusService

ann_contract = ANN(
    calendar="NOCALENDAR",
    businessDayConvention="SCF",

    contractID="ann01",
    contractRole="RPA",

    counterpartyID="CP01",
    creatorID="creator01",

    contractDealDate="2012-12-28",
    initialExchangeDate="2013-01-01",
    statusDate="2012-12-30",

    currency="USD",

    notionalPrincipal=5000,
    nominalInterestRate=0.08,
    dayCountConvention="A365",

    maturityDate="2014-01-01",

    cycleAnchorDateOfPrincipalRedemption="2013-02-01",
    cycleOfPrincipalRedemption="P1ML0",
    nextPrincipalRedemptionPayment=434.866594118346,

    cycleAnchorDateOfInterestPayment="2013-02-01",
    cycleOfInterestPayment="P1ML0",

    rateMultiplier=1.0,
    rateSpread=0.0
)

simulationService = PublicActusService()

event_stream = simulationService.generateEvents(portfolio=ann_contract)

print(event_stream.events_df)