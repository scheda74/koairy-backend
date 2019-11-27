import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.db.mongodb_utils import connect_to_mongo, close_mongo_connection


app = FastAPI(title="EM-ViZ API")

app.add_middleware(CORSMiddleware, allow_origins="*", allow_methods=["*"], allow_headers=["*"])

app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)

app.include_router(api_router)


# @app.post('/get/caqi')
# async def get_caqi(inputs: Inputs = example_body):
#     """
#     Returns CAQI values. If not available new simulation will be started
#     """
    
#     # body = await request.get_json()
#     simulation_id = generate_id(inputs)
#     print(inputs)
#     print(simulation_id)
#     parser = Parser(simulation_id)
#     # emission_cycle = await parser.parse_simulated_emissions()
#     caqi = query.get_latest_emissions(simulation_id)
#     if caqi != None:
#         return caqi["emissions"] 
#     else: 
#         return parser.get_caqi_data()

# @app.get('/generate/weights')
# async def generate_weights(self):
#     """
#     Writes new weights with the given inputs from area distribution
#     """
#     body = await request.get_json()
#     simulation_id = generate_id(body)
#     processor = PreProcessor(
#         sim_id=simulation_id,
#         timesteps=body['timesteps'],
#         agents=body['vehicleNumber'], 
#         src_weights=body['srcWeights'], 
#         dst_weights=['dstWeights']
#     )
#     await processor.write_weight_file()
#     return "File written"

# @app.post('/start/simulation')
# async def start_simulation(self):
#     """
#     Starts a new simulation with given input parameters...
#     """
#     body = await request.get_json()
#     sim_id = generate_id(body)
#     print("Starting PreProcessor...")
#     processor = PreProcessor(
#         sim_id=sim_id,
#         timesteps=body['timesteps'],
#         agents=body['vehicleNumber'], 
#         src_weights=body['srcWeights'], 
#         dst_weights=body['dstWeights']
#     )
#     cfg_filepath = await processor.preprocess_simulation_input()
#     # print(cfg_filepath)
#     print("Starting SUMO...")
#     simulator = Simulator(cfg_filepath, sim_id)
#     await simulator.start()
    
#     print("Parsing results...")
#     parser = Parser(sim_id)
#     return parser.get_caqi_data()
    # return await parser.parse_emissions()
    # return "OK"

# def generate_id(inputs):
#     src_weights = "".join([str(v).replace('.', '') for v in inputs.srcWeights.values()])
#     dst_weights = "".join([str(v).replace('.', '') for v in inputs.dstWeights.values()])
#     veh_dist = "".join([str(v).replace('.', '') for v in inputs.vehicleDistribution])
#     return ("%s_%s_%s_%s_%s_%s" % (src_weights, dst_weights, veh_dist, inputs.vehicleNumber, inputs.timesteps, inputs.weatherScenario))

