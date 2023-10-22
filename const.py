DOMAIN = "fmi_waterlevel"
API_BASE_URL = "https://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=getFeature"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.5249.62 Safari/537.36"
STORED_QUERY_OBSERVATIONS = "fmi::observations::mareograph::instant::simple&parameters=WLEVN2K_PT1S_INSTANT"
STORED_QUERY_FORECAST = "fmi::forecast::sealevel::point::simple"
FMISID_LOCATIONS = ["Föglö", "Hamina", "Hanko", "Helsinki", "Kaskinen", "Kemi", "Oulu", "Pietarsaari", "Pori", "Porvoo",
                    "Raahe", "Rauma", "Turku", "Vaasa"]
FMISID_VALUES = [134252, 134254, 134253, 132310, 134251, 100539, 134248, 134250, 134266, 100669, 100540, 134224, 134225,
                 134223]

CONF_LOCATION = "location"
CONF_HOURS = "hours"
CONF_FORECAST_HOURS = "forecast_hours"
CONF_STEP = "step"
CONF_OVERLAP = "overlap"
