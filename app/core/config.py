import os
from dotenv import load_dotenv
from databases import DatabaseURL
import app.tools.simulation as simulation
import app.tools.predictor.data.weather as weather
import app.tools.predictor.data.airquality as airquality
import app.tools.predictor.data.plots as plots

load_dotenv(".env")

PROJECT_NAME = os.getenv("PROJECT_NAME", "EM-ViZ FastAPI")
HAWA_DAWA_API_KEY = '22e28dcf-8207-4626-ced1-5afaff1834d6'
HAWA_DAWA_URL = 'https://data.hawadawa.com/airapi/bytopic/kirchheim/hour?'

BREMICKER_URL = 'http://smart-mobility.ge57.spacenet.de/bremicker/measures'
BREMICKER_API_KEY = 'r4LwN9jVYVHHV1iu'

MONGODB_URL = os.getenv("MONGODB_URL", "")  # deploying without docker-compose
if not MONGODB_URL:
    MONGO_HOST = os.getenv("MONGO_HOST", "0.0.0.0")
    MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
    MONGO_USER = os.getenv("MONGO_ROOT", "root")
    MONGO_PASS = os.getenv("MONGO_PASSWORD", "example")
    MONGO_DB = os.getenv("MONGO_DB", "mongo-db")

    MONGODB_URL = DatabaseURL(
        f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"
    )
    # /{MONGO_DB}
else:
    MONGODB_URL = DatabaseURL(MONGODB_URL)


import os, sys

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")


BASEDIR = os.path.dirname(simulation.__file__)
DEFAULT_NET_INPUT = BASEDIR + "/data/traffic-input/net/road-network-default.net.xml"
NET_BASEDIR = BASEDIR + "/data/traffic-input/net/road-network_"
TRAFFIC_INPUT_BASEDIR = BASEDIR + "/data/traffic-input/"
DET_OUT_BASEDIR = BASEDIR + "/data/traffic-input/det_"
ALL_DET_FILEPATH = BASEDIR + "/data/traffic-input/net/det.add.xml"
AREA_OF_INTEREST = BASEDIR + "/data/traffic-input/areas-of-interest.taz.xml"
TRIP_OUTPUT = BASEDIR + "/data/traffic-input/trip-"
ROUTE_OUTPUT = BASEDIR + "/data/traffic-input/route-"
WEIGHT_INPUT = BASEDIR + "/data/traffic-input/weight-"
EMISSION_OUTPUT_BASE = BASEDIR + "/data/emission-output/"
EMISSION_OUTPUT = BASEDIR + "/data/emission-output/test_emission_output.xml"
SUMO_CFG = BASEDIR + "/data/traffic-input/simulation-"

SUMO_ROOT = os.environ['SUMO_HOME']
SUMO_GUI = SUMO_ROOT + "/bin/sumo-gui"
SUMO_COMMANDLINE = SUMO_ROOT + "/bin/sumo"
SUMO_EM_DRIVING_CYCLE = SUMO_ROOT + "/bin/emissionsDrivingCycle"
RANDOM_TRIP_TOOL = tools + "/randomTrips.py"

WEATHER_BASEDIR = os.path.dirname(weather.__file__)
WEATHER_WIND = WEATHER_BASEDIR + "/wind_munich_2019.txt"
WEATHER_PRESSURE = WEATHER_BASEDIR + "/pressure_munich_2019.txt"
WEATHER_TEMP_HUMID = WEATHER_BASEDIR + "/temp_humidity_munich_2019.txt"

AIR_BASEDIR = os.path.dirname(airquality.__file__)

PLOT_BASEDIR = os.path.dirname(plots.__file__)

PHEMLIGHT_PATH = SUMO_ROOT + "/data/emissions/PHEMlight"

VALID_AREA_IDS = {
    'aschheim_west',
    'ebersberg_east',
    'feldkirchen_west',
    'heimstetten_industrial_1',
    'heimstetten_industrial_2',
    'heimstetten_residential',
    'kirchheim_industrial_east',
    'kirchheim_industrial_west',
    'kirchheim_residential',
    'unassigned_edges'
}


database_name = os.getenv("MONGO_DB", "mongo-db")
caqi_emission_collection_name = "caqi_emissions"
raw_emission_collection_name = "raw_emissions"
simulated_traffic_collection_name = "simulated_traffic"
bremicker_collection_name = "bremicker"
air_hawa_collection_name = "air_hawa"
training_data_collection_name = "training"