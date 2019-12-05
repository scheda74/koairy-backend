from fastapi import APIRouter, Depends, HTTPException
import datetime
import pandas as pd

from ...crud.bremicker import get_current_bremicker_by_time, get_latest_bremicker_by_box_id, fetch_latest_bremicker
from ...crud.hawa_dawa import fetch_latest_air
from ...tools.simulation.parse_emission import Parser
from ...models.simulation_input import SimulationInput, example_simulation_input
from ...models.prediction_input import (
    PredictionInput,
    example_prediction_input
)
from .utils import generate_single_id, generate_id
from ...db.mongodb import AsyncIOMotorClient, get_database
from ...tools.predictor.utils.model_preprocessor import ModelPreProcessor


router = APIRouter()


# @router.post('/traffic/current')
# async def get_traffic(inputs: SimulationInput = example_simulation_input, db: AsyncIOMotorClient=Depends(get_database)):
#     """
#     Returns CAQI values. If not available new simulation will be started
#     """
#     print(inputs)
#     simulation_id = generate_id(inputs)
#     print("[PARSER] Get CAQI data from simulation with id {simulation_id}")
#     parser = Parser(db, simulation_id, inputs.box_id)
#     return await parser.get_caqi_data()
#
# @router.post('/traffic')
# async def get_training(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
#     sim_id = generate_id(inputs)
#     df = await ModelPreProcessor(db, sim_id).aggregate_data(inputs.box_id, inputs.start_date, inputs.end_date, inputs.start_hour, inputs.end_hour)
#     df.index = df.index.strftime("%Y-%m-%d %H:%M")
#     return df.to_json(orient='index')

# @router.post('/get/caqi')
# async def get_caqi(inputs: SimulationInput = example_simulation_input, db: AsyncIOMotorClient=Depends(get_database)):
#     """
#     Returns CAQI values. If not available new simulation will be started
#     """
#     print(inputs)
#     simulation_id = generate_id(inputs)
#     print("[PARSER] Get CAQI data from simulation with id {simulation_id}")
#     parser = Parser(db, simulation_id, inputs.box_id)
#     return await parser.get_caqi_data()
#
#
# # @router.post('/get/sensors')
# # async def get_sensors(db: AsyncIOMotorClient=Depends(get_database)):
#     # lr = LinReg(db)
#     # await lr.get_hw_data()
#
# @router.post('/simulation/compare')
# async def compare_traffic(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
#     if inputs.vehicleNumber is None:
#         df_traffic = await get_current_bremicker_by_time(db, start_hour=inputs.start_hour, end_hour=inputs.end_hour)
#         inputs.vehicleNumber = df_traffic[inputs.box_id].sum() if df_traffic is not None else 1000
#     sim_id = generate_single_id(inputs)
#     processor = ModelPreProcessor(db, sim_id)
#     # df = await processor.aggregate_data(inputs.box_id, inputs.start_date, inputs.end_date, inputs.start_hour, inputs.end_hour)
#     # print(df[[inputs.box_id, 'NOx', 'no2', 'PMx', 'pm10']])
#     # df = df[[inputs.box_id, 'NOx', 'no2', 'PMx', 'pm10']]
#     # df = df.rename(columns={inputs.box_id: '#vehicles'})
#     # df.index = df.index.strftime("%Y-%m-%d %H:%M")
#     # return df.to_dict(orient='index')
#     df = await processor.aggregate_compare(inputs.box_id, inputs.start_date, inputs.end_date, inputs.start_hour, inputs.end_hour)
#     return df.to_dict(orient='index')

@router.get('/bremicker/current')
async def get_current_bremicker(boxID, db: AsyncIOMotorClient=Depends(get_database)):
    try:
        # time = datetime.datetime.today().strftime('%H:%M')
        df_traffic = await fetch_latest_bremicker(db)
        if df_traffic is not None:
            df_traffic = df_traffic.reset_index()
            df_traffic = df_traffic.groupby([pd.Grouper(key='time', freq='H')]).sum()
            result = df_traffic[int(boxID)]
            result.index = result.index.strftime("%Y-%m-%d %H:%M")
            return result.to_json(orient='index')
        else:
            raise HTTPException(status_code=500, detail='Fetching of Bremicker Data unsuccessful')
    except Exception as e:
        raise HTTPException(status_code=500, detail="[Bremicker] Fetching of current air quality unsuccessful: %s" % str(e))

@router.get('/air/current')
async def get_current_air(db: AsyncIOMotorClient=Depends(get_database)):
    try:
        air = await fetch_latest_air(db)
        if air is not None:
            return air
        else:
            raise HTTPException(status_code=500, detail='[HAWA DAWA] Fetching of current air quality unsuccessful')
    except Exception as e:
        raise HTTPException(status_code=500, detail="[HAWA DAWA] Fetching of current air quality unsuccessful: %s" % str(e))