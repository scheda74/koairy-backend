
# import os
# import json
# import datetime
# import pandas as pd
# import matplotlib.pyplot as plt
from fastapi import APIRouter, Depends
# from starlette.responses import FileResponse, RedirectResponse

# from app.tools.simulation.parse_emission import Parser
# from app.tools.simulation.simulator import Simulator
# from app.tools.simulation.preprocessor import SimulationPreProcessor
# from app.tools.predictor.lin_reg import LinReg
# from app.tools.predictor.neural_nets.py import NeuralNet
from app.tools.predictor.predictor import Predictor
# from db.database import DB
# from app.models.simulation_input import SimulationInput, example_simulation_input
from app.models.prediction_input import (PlotInput, example_plot_input, PredictionInput, example_prediction_input)
# import db.query_database as query
from app.db.mongodb import AsyncIOMotorClient, get_database
# from app.crud.emissions import get_caqi_emissions_for_sim
# from app.crud.hawa_dawa import (
#     get_hawa_dawa_by_time
#     # get_all_hawa_dawa
# )
# from app.crud.bremicker import (
#     get_bremicker
# )
# from app.core.config import PLOT_BASEDIR

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

# @router.post('/prediction/lstm')
# async def start_lstm(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
#     """
#     Training and prediction using a Long-Short-Term-Memory Recurrent Neural Network
#     """
#     sim_id = generate_id(inputs)
#     return await Predictor(db, inputs, sim_id, predictionModel='lstm').predict_emissions()
#     # nn = NeuralNet(db, sim_id)
#
#     # df_lstm = await nn.start_lstm(boxID=672, input_keys=['temp', 'hum', 'PMx', 'WIND_SPEED', 'WIND_DIR'], output_key='no2')
# # , db: AsyncIOMotorClient=Depends(get_database)
#
# @router.post('/prediction/linreg')
# async def start_linreg(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
#     """
#     Starts training a simple Linear Regression Model with the specified independents (= inputs) and dependent (= output)
#     Next, it'll predict the specified output with the data given to this request
#     """
#     sim_id = generate_id(inputs)
#     return (await Predictor(db, inputs, sim_id, predictionModel='lin-reg').predict_emissions()).to_json(orient='index')
#
# @router.post('/prediction/mlp')
# async def start_mlp(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
#     """
#     Training and prediction using a Multi-Layer-Perceptron Regression Network
#     """
#     sim_id = generate_id(inputs)
#     return (await Predictor(db, inputs, sim_id, predictionModel='mlp').predict_emissions()).to_json(orient='index')
#
# @router.post('/prediction/cnn')
# async def start_conv(inputs: PredictionInput = example_prediction_input, db: AsyncIOMotorClient=Depends(get_database)):
#     """
#     Training and prediction using a Convolutional Neural Network
#     """
#     sim_id = generate_id(inputs)
#     return await (Predictor(db, inputs, sim_id, predictionModel='cnn').predict_emissions()).to_json(orient='index')
#
    
    # sim_id = generate_id(inputs.simulation_input)
    # nn = NeuralNet(db, sim_id)
    # res = await lr.aggregate_data(start_date='2019-08-01', end_date='2019-10-30', start_hour='0:00', end_hour='23:00')
    # return res.to_dict(orient='index')

    # df_pm10_pred = await nn.start_cnn(boxID=672, input_keys=['temp', 'hum', 'PMx', 'WIND_SPEED', 'WIND_DIR'], output_key='pm10')
    # print(df_pm10_pred)
    # df_pm25_pred = await lr.start_cnn(boxID=672, input_keys=['temp', 'hum', 'PMx'], output_key='pm2.5')
    # df_no2_pred = await lr.start_cnn(boxID=672, input_keys=['temp', 'hum', 'NOx'], output_key='no2')
    # df_combined = pd.concat([df_no2_pred, df_pm10_pred, df_pm25_pred], axis=1)
    # print(df_combined)
    # return df_combined.to_dict(orient='list')


def generate_id(inputs):
    src_weights = "".join([str(v).replace('.', '') for v in inputs.srcWeights.values()])
    dst_weights = "".join([str(v).replace('.', '') for v in inputs.dstWeights.values()])
    veh_dist = "".join([str(v).replace('.', '') for v in inputs.vehicleDistribution.values()])
    return ("%s_%s_%s_%s_%s_%s" % (src_weights, dst_weights, veh_dist, inputs.vehicleNumber, inputs.timesteps, inputs.weatherScenario))