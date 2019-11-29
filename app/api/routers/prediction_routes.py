from fastapi import APIRouter, Depends
from app.tools.predictor.predictor import Predictor
from app.models.prediction_input import (PlotInput, example_plot_input, PredictionInput, example_prediction_input)
from app.db.mongodb import AsyncIOMotorClient, get_database
from .utils import (generate_id, generate_single_id)

router = APIRouter()

@router.post('/prediction')
async def start_prediction(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Training and prediction using a Long-Short-Term-Memory Recurrent Neural Network
    """
    sim_id = generate_id(inputs)
    df = await Predictor(db, inputs, sim_id, predictionModel=inputs.predictionModel).predict_emissions()
    return df.to_json(orient='index')

# https://machinelearningmastery.com/time-series-prediction-lstm-recurrent-neural-networks-python-keras/