from fastapi import APIRouter, Depends
import datetime

from ...crud.bremicker import get_current_bremicker_by_time, get_latest_bremicker_by_box_id
from ...crud.hawa_dawa import fetch_latest_air
from ...tools.simulation.parse_emission import Parser
from ...tools.predictor.lin_reg import LinReg
from ...models.simulation_input import SimulationInput, example_simulation_input
from ...models.prediction_input import (
    PredictionInput,
    example_prediction_input
)
from .utils import generate_single_id, generate_id
from ...db.mongodb import AsyncIOMotorClient, get_database
from ...tools.predictor.utils.model_preprocessor import ModelPreProcessor


router = APIRouter()


@router.post('/traffic/current')
async def get_traffic(inputs: SimulationInput = example_simulation_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Returns CAQI values. If not available new simulation will be started
    """
    print(inputs)
    simulation_id = generate_id(inputs)
    print("[PARSER] Get CAQI data from simulation with id {simulation_id}")
    parser = Parser(db, simulation_id, inputs.box_id)
    return await parser.get_caqi_data()

@router.post('/traffic')
async def get_training(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
    sim_id = generate_id(inputs)
    df = await ModelPreProcessor(db, sim_id).aggregate_data(inputs.box_id, inputs.start_date, inputs.end_date, inputs.start_hour, inputs.end_hour)
    df.index = df.index.strftime("%Y-%m-%d %H:%M")
    return df.to_json(orient='index')

@router.post('/get/caqi')
async def get_caqi(inputs: SimulationInput = example_simulation_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Returns CAQI values. If not available new simulation will be started
    """
    print(inputs)
    simulation_id = generate_id(inputs)
    print("[PARSER] Get CAQI data from simulation with id {simulation_id}")
    parser = Parser(db, simulation_id, inputs.box_id)
    return await parser.get_caqi_data()


@router.post('/get/sensors')
async def get_sensors(db: AsyncIOMotorClient=Depends(get_database)):
    lr = LinReg(db)
    # await lr.get_hw_data()

@router.post('/simulation/compare')
async def compare_traffic(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
    if inputs.vehicleNumber is None:
        df_traffic = await get_current_bremicker_by_time(db, start_hour=inputs.start_hour, end_hour=inputs.end_hour)
        inputs.vehicleNumber = df_traffic[inputs.box_id].sum() if df_traffic is not None else 1000
    sim_id = generate_single_id(inputs)
    processor = ModelPreProcessor(db, sim_id)
    # df = await processor.aggregate_data(inputs.box_id, inputs.start_date, inputs.end_date, inputs.start_hour, inputs.end_hour)
    # print(df[[inputs.box_id, 'NOx', 'no2', 'PMx', 'pm10']])
    # df = df[[inputs.box_id, 'NOx', 'no2', 'PMx', 'pm10']]
    # df = df.rename(columns={inputs.box_id: '#vehicles'})
    # df.index = df.index.strftime("%Y-%m-%d %H:%M")
    # return df.to_dict(orient='index')
    df = await processor.aggregate_compare(inputs.box_id, inputs.start_date, inputs.end_date, inputs.start_hour, inputs.end_hour)
    return df.to_dict(orient='index')

@router.get('/bremicker/current')
async def get_current_bremicker(box_id, db: AsyncIOMotorClient=Depends(get_database)):
    time = datetime.datetime.today().strftime('%H:%M')
    df_traffic = await get_latest_bremicker_by_box_id(db, box_id=box_id)
    if df_traffic is not None:
        # df_traffic = df_traffic[int(box_id)]
        df_traffic.index = df_traffic.index.strftime("%Y-%m-%d %H:%M")
        print(df_traffic)
        return df_traffic.to_json(orient='index')
    else:
        return {'msg': 'Fetching of Bremicker Data unsuccessful', 'status': 404}

@router.get('/air/current')
async def get_current_air(db: AsyncIOMotorClient=Depends(get_database)):
    # time = datetime.datetime.today().strftime('%H:%M')
    air = await fetch_latest_air(db)
    if air is not None:
        # df_air.index = df_air.index.strftime("%Y-%m-%d %H:%M")
        # return df_air.to_json(orient='index')
        return air
    else:
        return {'msg': 'Fetching of Bremicker Data unsuccessful'}