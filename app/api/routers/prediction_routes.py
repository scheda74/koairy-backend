from fastapi import APIRouter, Depends, HTTPException
from ...tools.predictor.predictor import Predictor
from ...models.prediction_input import (
    PredictionInput,
    example_prediction_input,
    # SinglePredictionInput,
    # example_single_prediction_input
)
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
    sim_id = generate_single_id(inputs)
    try:
        df = await Predictor(db, inputs, sim_id).predict_emissions()
    except Exception as e:
        # return {'msg': str(e), 'status': 500}
        raise HTTPException(status_code=500, detail=str(e))
    else:
        return df.to_json(orient='index')

# https://machinelearningmastery.com/time-series-prediction-lstm-recurrent-neural-networks-python-keras/