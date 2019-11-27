import json
from fastapi import APIRouter, Depends


from app.tools.simulation.parse_emission import Parser
from app.tools.simulation.simulator import Simulator
from app.tools.simulation.preprocessor import SimulationPreProcessor

from app.models.simulation_input import SimulationInput, example_simulation_input
from app.db.mongodb import AsyncIOMotorClient, get_database

router = APIRouter()

@router.post('/start/simulation')
async def start_simulation(inputs: SimulationInput = example_simulation_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Starts a new simulation with given input parameters...
    """
    sim_id = generate_id(inputs)
    print("Starting PreProcessor...")
    processor = SimulationPreProcessor(
        sim_id=sim_id,
        timesteps=inputs.timesteps,
        agents=inputs.vehicleNumber, 
        src_weights=inputs.srcWeights, 
        dst_weights=inputs.dstWeights,
        veh_dist=inputs.vehicleDistribution
    )
    cfg_filepath = await processor.preprocess_simulation_input()

    print("Starting SUMO...")
    simulator = Simulator(db, cfg_filepath, sim_id)
    await simulator.start()
    
    print("Parsing results...")
    parser = Parser(db, sim_id)
    return await parser.get_caqi_data()


@router.get('/generate/weights')
async def generate_weights(inputs: SimulationInput = example_simulation_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Writes new weights with the given inputs from area distribution
    """
    sim_id = generate_id(inputs)
    processor = SimulationPreProcessor(
        sim_id=sim_id,
        timesteps=inputs.timesteps,
        agents=inputs.vehicleNumber, 
        src_weights=inputs.srcWeights, 
        dst_weights=inputs.dstWeights
    )
    await processor.write_weight_file()
    return "File written"


def generate_id(inputs):
    src_weights = "".join([str(v).replace('.', '') for v in inputs.srcWeights.values()])
    dst_weights = "".join([str(v).replace('.', '') for v in inputs.dstWeights.values()])
    veh_dist = "".join([str(v).replace('.', '') for v in inputs.vehicleDistribution.values()])
    return ("%s_%s_%s_%s_%s_%s" % (src_weights, dst_weights, veh_dist, inputs.vehicleNumber, inputs.timesteps, inputs.weatherScenario))