from fastapi import APIRouter, Depends, HTTPException
# import matplotlib.pyplot as plt
import datetime
import pandas as pd

from ...crud.bremicker import get_bremicker, get_bremicker_by_time
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

# @router.get('/test/calibration')
# async def get_calibration(db: AsyncIOMotorClient=Depends(get_database)):
#     data = [[0, 5.0, 0.0], [600, 1.0, 7.0], [1200, 2.0, 3.0], [1800, 0.0, 4.0], [2400, 2.0, 5.0], [3000, 3.0, 3.0], [3600, 2.0, 4.0], [4200, 2.0, 4.0], [4800, 2.0, 0.0], [5400, 3.0, 5.0], [6000, 3.0, 6.0], [6600, 1.0, 3.0], [7200, 3.0, 4.0], [7800, 3.0, 6.0], [8400, 4.0, 5.0], [9000, 3.0, 2.0], [9600, 3.0, 4.0], [10200, 0.0, 6.0], [10800, 2.0, 7.0]]
#     time_series = [arr[0] for arr in data]
#     real_sensor_count = [arr[1] for arr in data]
#     simulation_sensor_count = [arr[2] for arr in data]
#     data = {'Time': time_series, '#MeasuredVehicles': real_sensor_count, '#SimulatedVehicles': simulation_sensor_count}
#     df = pd.DataFrame.from_dict(data)
#     df = df.set_index('Time')
#     print(df)
#     font = {'family': 'arial',
#             'color': 'black',
#             'weight': 'bold',
#             'size': 16,
#             }
#     df.plot(figsize=(8, 5))
#     plt.xlabel("time in seconds", fontdict=font)
#     plt.ylabel("number of vehicles", fontdict=font)
#     plt.ylim((0, 10))
#     plt.show()
#     return df.to_json(orient='index')

@router.get('/bremicker/current')
async def get_current_bremicker(boxID, db: AsyncIOMotorClient=Depends(get_database)):
    # try:
    print('starting bremicker')
    df_traffic = await get_bremicker_by_time(db, box_id=int(boxID), grouper_freq='H')
    if df_traffic is not None:
        result = df_traffic[int(boxID)]
        return result.to_json(orient='index')
    else:
        raise HTTPException(status_code=500, detail='[BREMICKER] Fetching resulted in None Object')
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail="[BREMICKER] Fetching of current traffic unsuccessful: %s" % str(e))

@router.get('/air/current')
async def get_current_air(db: AsyncIOMotorClient=Depends(get_database)):
    # try:
    air = await fetch_latest_air(db)
    if air is not None:
        return air
    else:
        raise HTTPException(status_code=500, detail='[HAWA DAWA] Fetching of current air quality unsuccessful')
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail="[HAWA DAWA] Fetching of current air quality unsuccessful: %s" % str(e))

@router.get('/bremicker/test')
async def get_current_air(db: AsyncIOMotorClient=Depends(get_database)):
    # try:
    # bremicker = await get_bremicker(db, start_date="2019-08-01", end_date="2019-12-10")
    # bremicker = await get_bremicker(db)
    bremicker = await get_bremicker_by_time(db, start_date="2019-12-11", end_date="2019-12-14", start_hour="7:00", end_hour="10:00", grouper_freq='H')
    if bremicker is not None:
        return bremicker.to_dict(orient='index')
    else:
        raise HTTPException(status_code=500, detail='[BREMICKER] Fetching of traffic data unsuccessful')
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail="[BREMICKER] Fetching of traffic data unsuccessful: %s" % str(e))