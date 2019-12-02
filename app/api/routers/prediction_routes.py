from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from ...tools.predictor.predictor import Predictor
from ...models.prediction_input import (
    PredictionInput,
    example_prediction_input,
    # SinglePredictionInput,
    # example_single_prediction_input
)
from ...crud.bremicker import get_current_bremicker_by_time
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
        df = await Predictor(db, inputs, sim_id).predict_emissions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    else:
        return df.to_json(orient='index')

@router.post('/prediction/single')
async def start_single_prediction(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Training and prediction using a Long-Short-Term-Memory Recurrent Neural Network
    """
    try:
        df_traffic = None
        if inputs.vehicleNumber is None:
            df_traffic = await get_current_bremicker_by_time(db, start_hour=inputs.start_hour, end_hour=inputs.end_hour)
            # if there are 2 hours or less (around midnight) take yesterday!
            if df_traffic.shape[0] < 3:
                yesterday = datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d')
                df_traffic = await get_current_bremicker_by_time(db, start_date=yesterday, start_hour=inputs.start_hour, end_hour=inputs.end_hour)
            inputs.vehicleNumber = int(df_traffic[inputs.box_id].sum()) if df_traffic is not None else 1000

        sim_id = generate_single_id(inputs)
        df = await Predictor(db, inputs, sim_id, df_traffic=df_traffic).predict_emissions()
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))
    else:
        return df.to_json(orient='index')

