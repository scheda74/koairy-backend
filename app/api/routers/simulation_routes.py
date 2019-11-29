from fastapi import APIRouter, Depends
from ...tools.simulation.parse_emission import Parser
from ...tools.simulation.simulator import Simulator
from ...tools.simulation.preprocessor import SimulationPreProcessor
from ...tools.simulation.single_preprocessor import SingleSimulationPreProcessor

from ...models.simulation_input import SimulationInput, example_simulation_input
from ...models.single_simulation_input import SingleSimulationInput, example_single_simulation_input
from ...db.mongodb import AsyncIOMotorClient, get_database
from ...crud.bremicker import get_current_bremicker_by_time
from .utils import (generate_id, generate_single_id)

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
    simulator = Simulator(db, cfg_filepath, sim_id, veh_dist=inputs.vehicleDistribution, timesteps=inputs.timesteps)
    await simulator.start()
    
    print("Parsing results...")
    parser = Parser(db, sim_id, inputs.boxID)
    return await parser.get_caqi_data()


@router.post('/simulation/single')
async def start_single_simulation(inputs: SingleSimulationInput = example_single_simulation_input,
                                  db: AsyncIOMotorClient = Depends(get_database)
                                  ):
    """
    Starts a new simulation with given input parameters...
    """
    df_traffic = None
    if inputs.vehicleNumber is None:
        df_traffic = await get_current_bremicker_by_time(db, start_hour=inputs.start_hour, end_hour=inputs.end_hour)
        inputs.vehicleNumber = df_traffic[inputs.boxID].sum() if df_traffic is not None else 1000
    print(inputs.vehicleNumber)
    sim_id = generate_single_id(inputs)

    print("Starting PreProcessor...")
    processor = SingleSimulationPreProcessor(
        db=db,
        sim_id=sim_id,
        timesteps=inputs.timesteps,
        vehicleNumber=inputs.vehicleNumber,
        veh_dist=inputs.vehicleDistribution,
        df_traffic=df_traffic,
        boxID=inputs.boxID
    )
    cfg_filepath = await processor.preprocess_simulation_input()

    print("Starting SUMO...")
    simulator = Simulator(
        db,
        cfg_filepath,
        sim_id,
        veh_dist=inputs.vehicleDistribution,
        timesteps=inputs.timesteps,
        df_traffic=df_traffic
    )
    await simulator.start_single()

    print("Parsing results...")
    parser = Parser(db, sim_id, inputs.boxID)
    result = await parser.get_caqi_data()
    print(result)


# @router.get('/generate/weights')
# async def generate_weights(inputs: SimulationInput = example_simulation_input, db: AsyncIOMotorClient=Depends(get_database)):
#     """
#     Writes new weights with the given inputs from area distribution
#     """
#     sim_id = generate_id(inputs)
#     processor = SimulationPreProcessor(
#         sim_id=sim_id,
#         timesteps=inputs.timesteps,
#         agents=inputs.vehicleNumber,
#         src_weights=inputs.srcWeights,
#         dst_weights=inputs.dstWeights
#     )
#     await processor.write_weight_file()
#     return "File written"


