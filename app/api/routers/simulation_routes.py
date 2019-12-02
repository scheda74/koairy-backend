from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from ...tools.simulation.parse_emission import Parser
from ...tools.simulation.simulator import Simulator
from ...tools.simulation.preprocessor import SimulationPreProcessor

from ...models.simulation_input import SimulationInput, example_simulation_input
from ...db.mongodb import AsyncIOMotorClient, get_database
from ...crud.bremicker import fetch_latest_bremicker
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
        inputs=inputs
        # timesteps=inputs.timesteps,
        # agents=inputs.vehicleNumber,
        # src_weights=inputs.srcWeights,
        # dst_weights=inputs.dstWeights,
        # veh_dist=inputs.vehicleDistribution
    )
    cfg_filepath = await processor.preprocess_simulation_input()

    print("Starting SUMO...")
    simulator = Simulator(db, inputs, cfg_filepath, sim_id)
    await simulator.start()
    
    print("Parsing results...")
    parser = Parser(db, sim_id, inputs.box_id)
    return await parser.get_caqi_data()


@router.post('/simulation/single')
async def start_single_simulation(inputs: SimulationInput = example_simulation_input,
                                  db: AsyncIOMotorClient = Depends(get_database)
                                  ):
    """
    Starts a new simulation with given input parameters...
    """
    try:
        df_traffic = await fetch_latest_bremicker(db, inputs.start_hour, inputs.end_hour)
        if inputs.vehicleNumber is None:
            inputs.vehicleNumber = int(df_traffic[inputs.box_id].sum()) if df_traffic is not None else 1000
        sim_id = generate_single_id(inputs)

        print("Starting SUMO...")
        simulator = Simulator(
            db=db,
            sim_id=sim_id,
            inputs=inputs,
            df_traffic=df_traffic
        )
        result = await simulator.start_single()
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))
    else:
        return result


