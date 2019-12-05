from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from ...tools.predictor.predictor import Predictor
from ...models.prediction_input import (
    PredictionInput,
    example_prediction_input,
    # SinglePredictionInput,
    # example_single_prediction_input
)
from ...crud.bremicker import fetch_latest_bremicker
from ...db.mongodb import AsyncIOMotorClient, get_database
from .utils import (generate_id, generate_single_id)

router = APIRouter()

@router.post('/prediction')
async def start_prediction(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Training and prediction using a Long-Short-Term-Memory Recurrent Neural Network
    """
    sim_id = generate_id(inputs)
    try:
        df_traffic = await fetch_latest_bremicker(db, inputs.start_hour, inputs.end_hour)
        if inputs.vehicleNumber is None:
            inputs.vehicleNumber = df_traffic.sum(axis=1, skipna=True).sum(axis=0)
            print("Simulation with %s vehicles" % str(inputs.vehicleNumber))
            # inputs.vehicleNumber = int(df_traffic[inputs.box_id].sum()) if df_traffic is not None else 1000
        return await Predictor(db, inputs, sim_id, df_traffic=df_traffic, is_single_sim=False).predict_emissions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/prediction/single')
async def start_single_prediction(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Training and prediction using a Long-Short-Term-Memory Recurrent Neural Network
    """
    try:
        df_traffic = await fetch_latest_bremicker(db, inputs.start_hour, inputs.end_hour)
        if inputs.vehicleNumber is None:
            inputs.vehicleNumber = int(df_traffic[inputs.box_id].sum()) if df_traffic is not None else 1000

        sim_id = generate_single_id(inputs)
        result = await Predictor(db, inputs, sim_id, df_traffic=df_traffic, is_single_sim=True).predict_emissions()
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))
    else:
        return result
        # return df.to_json(orient='index')

