"""Measured instrument geometry shared by Blender, Three and Unity (glTF metres)."""
accelerometer={
    "id":"accelerometer","node":"prop_accelerometer","massNode":"accel_proof_mass","slideAxis":[0,-1,0],
    "metersPerG":.162,"referenceG":1.,"zeroCenter":[-.760,1.349,-5.20],"restCenter":[-.760,1.187,-5.20],
    "gRange":[-.18,1.18],"testId":"accel_test","testNode":"prop_accel_test","testAxis":[0,0,-1],
    "testTravel":.009,"testDeltaG":.10,"testPivot":[-.658,1.099,-5.191],
    "springs":[{"node":"accel_spring_upper","axis":"y","restLength":.232,"fixedEndSign":1,"turns":7,"radius":.0092,"wireRadius":.00145,
                "fixedEnd":[-.781,1.444,-5.219],"restMovingEnd":[-.781,1.212,-5.219]},
               {"node":"accel_spring_lower","axis":"y","restLength":.060,"fixedEndSign":-1,"turns":5,"radius":.0092,"wireRadius":.00145,
                "fixedEnd":[-.781,1.102,-5.219],"restMovingEnd":[-.781,1.162,-5.219]}]}
capillary={
    "id":"capillary_cell","node":"prop_capillary_cell","center":[2.067,1.326,-.671],"right":[0,0,1],
    "up":[0,1,0],"normal":[-1,0,0],"radius":.102,"depth":.022,"liquidFraction":.77,"gasFraction":.23,
    "lowGCenter":[.008,.0036],"liquidNode":"capillary_liquid","gasNode":"capillary_gas",
    "standInNodes":["capillary_liquid","capillary_gas"],"primerId":"capillary_primer",
    "primerNode":"prop_capillary_primer","primerAxis":[1,0,0],"primerTravel":.009,"primerPivot":[2.060,1.299,-.506],
    "wetFilm":.00025,"paneFilm":.00016,"wick":{"u":-.073,"vLimits":[-.059,.059],"width":.0048},
    "geometryUV":"U increases toward +Z (viewer right); V increases toward +Y (up). Both span the inner diameter.",
    "activeVolumeMl":719.09,"chargeMl":553.70}
