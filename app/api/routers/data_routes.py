from fastapi import APIRouter, Depends, HTTPException
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


@router.get('/bremicker/current')
async def get_current_bremicker(boxID, db: AsyncIOMotorClient=Depends(get_database)):
    try:
        df_traffic = await get_bremicker_by_time(db, box_id=int(boxID), grouper_freq='H')
        if df_traffic is not None:
            return df_traffic.to_json(orient='index')
        else:
            raise HTTPException(status_code=500, detail='[BREMICKER] Fetching resulted in None Object')
    except Exception as e:
        raise HTTPException(status_code=500, detail="[BREMICKER] Fetching of current traffic unsuccessful: %s" % str(e))

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