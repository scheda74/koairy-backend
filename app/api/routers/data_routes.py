from fastapi import APIRouter, Depends

from ...crud.bremicker import get_current_bremicker_by_time
from ...tools.simulation.parse_emission import Parser
from ...tools.predictor.lin_reg import LinReg
from ...models.simulation_input import SimulationInput, example_simulation_input
from ...models.prediction_input import (
    PlotInput,
    example_plot_input,
    PredictionInput,
    example_prediction_input,
    SinglePredictionInput,
    example_single_prediction_input
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
    parser = Parser(db, simulation_id, inputs.boxID)
    return await parser.get_caqi_data()

@router.post('/traffic')
async def get_training(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
    sim_id = generate_id(inputs)
    df = await ModelPreProcessor(db, sim_id).aggregate_data(inputs.boxID, inputs.start_date, inputs.end_date, inputs.start_hour, inputs.end_hour)
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
    parser = Parser(db, simulation_id, inputs.boxID)
    return await parser.get_caqi_data()


@router.post('/get/sensors')
async def get_sensors(db: AsyncIOMotorClient=Depends(get_database)):
    lr = LinReg(db)
    # await lr.get_hw_data()

@router.post('/simulation/compare')
async def compare_traffic(inputs: SinglePredictionInput = example_single_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
    if inputs.vehicleNumber is None:
        df_traffic = await get_current_bremicker_by_time(db, start_hour=inputs.start_hour, end_hour=inputs.end_hour)
        inputs.vehicleNumber = df_traffic[inputs.boxID].sum() if df_traffic is not None else 1000
    sim_id = generate_single_id(inputs)
    processor = ModelPreProcessor(db, sim_id)
    df = await processor.aggregate_data(inputs.boxID, inputs.start_date, inputs.end_date, inputs.start_hour, inputs.end_hour)
    # df = await processor.aggregate_compare(inputs.boxID, inputs.start_date, inputs.end_date, inputs.start_hour, inputs.end_hour)
    # print(df)
    print(df[[inputs.boxID, 'NOx', 'no2', 'PMx', 'pm10']])
    df = df[[inputs.boxID, 'NOx', 'no2', 'PMx', 'pm10']]
    df = df.rename(columns={inputs.boxID: '#vehicles'})
    df.index = df.index.strftime("%Y-%m-%d %H:%M")
    return df.to_dict(orient='index')
