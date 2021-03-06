from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from ...tools.predictor.predictor import Predictor
from ...models.prediction_input import (
    PredictionInput,
    example_prediction_input,
    # SinglePredictionInput,
    # example_single_prediction_input
)
from ...crud.bremicker import get_bremicker, get_bremicker_by_time
from ...crud.emissions import drop_simulation_data
from ...db.mongodb import AsyncIOMotorClient, get_database
from .utils import (generate_id, generate_single_id, delete_simulation_files)

router = APIRouter()

@router.post('/prediction')
async def start_prediction(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Training and prediction using full map
    """
    sim_id = generate_id(inputs)
    try:
    # df_traffic = await get_latest_bremicker(db, inputs.start_hour, inputs.end_hour)
        df_traffic = await get_bremicker_by_time(db, start_hour=inputs.start_hour, end_hour=inputs.end_hour)
        if inputs.vehicleNumber is None:
            inputs.vehicleNumber = round(df_traffic.sum(axis=1, skipna=True).sum(axis=0) * 1.25)
            print("Simulation with %s vehicles" % str(inputs.vehicleNumber))
        # print('sim id:', sim_id)
        result = await Predictor(db, inputs, sim_id, df_traffic=df_traffic, is_single_sim=False).predict_emissions()
        await delete_simulation_files()
        return result
    except Exception as e:
        print("Error caught: %s" % str(e))
        await drop_simulation_data(db, sim_id)
        raise HTTPException(status_code=500, detail="Prediction failed: %s" % str(e))

@router.post('/prediction/single')
async def start_single_prediction(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Training and prediction of a single area
    """
    sim_id = generate_single_id(inputs)
    try:
        # df_traffic = await get_latest_bremicker(db, inputs.start_hour, inputs.end_hour)
        df_traffic = await get_bremicker_by_time(db, start_hour=inputs.start_hour, end_hour=inputs.end_hour)
        print(df_traffic)
        if inputs.vehicleNumber is None:
            inputs.vehicleNumber = int(df_traffic[inputs.box_id].sum()) if df_traffic is not None else 1000
        print(inputs.vehicleNumber)

        result = await Predictor(db, inputs, sim_id, df_traffic=df_traffic, is_single_sim=True).predict_emissions()
        await delete_simulation_files()
        return result
    except Exception as e:
        print(str(e))
        await drop_simulation_data(db, sim_id)
        raise HTTPException(status_code=500, detail=str(e))

