import os
import json
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from fastapi import APIRouter, Depends
from starlette.responses import FileResponse, RedirectResponse

from app.tools.simulation.parse_emission import Parser
from app.tools.simulation.simulator import Simulator
from app.tools.simulation.preprocessor import SimulationPreProcessor
from app.tools.predictor.lin_reg import LinReg
# from db.database import DB
from app.models.simulation_input import SimulationInput, example_simulation_input
from app.models.data_input import DataInput, example_data_input
from app.models.prediction_input import (PlotInput, example_plot_input, PredictionInput, example_prediction_input)
# import db.query_database as query
from app.db.mongodb import AsyncIOMotorClient, get_database
from app.tools.predictor.utils.model_preprocessor import ModelPreProcessor
from app.crud.emissions import get_caqi_emissions_for_sim
from app.crud.hawa_dawa import (
    get_hawa_dawa_by_time
    # get_all_hawa_dawa
)
from app.crud.bremicker import (
    get_bremicker
)
from app.core.config import PLOT_BASEDIR

router = APIRouter()


@router.post('/traffic/current')
async def get_traffic(inputs: SimulationInput = example_simulation_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Returns CAQI values. If not available new simulation will be started
    """
    print(inputs)
    simulation_id = generate_id(inputs)
    print("[PARSER] Get CAQI data from simulation with id {simulation_id}")
    parser = Parser(db, simulation_id)
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
    parser = Parser(db, simulation_id)
    return await parser.get_caqi_data()

@router.post('/get/mean/vehicle')
async def get_mean_vehicles(inputs: SimulationInput = example_simulation_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Starts training a simple Linear Regression Model with the specified independents (= inputs) and dependent (= output)
    Next, it'll predict the specified output with the data given to this request
    """
    sim_id = generate_id(inputs)
    lr = LinReg(db, sim_id)
    df = await lr.get_mean_vehicle_by_hour('2019-08-22', '2019-10-24', '07:00', '11:00')
    return df.to_dict(orient='list')

@router.post('/get/sensors')
async def get_sensors(db: AsyncIOMotorClient=Depends(get_database)):
    lr = LinReg(db)
    # await lr.get_hw_data()

@router.post('/get/plot')
async def get_plot(inputs: PlotInput = example_plot_input, db: AsyncIOMotorClient=Depends(get_database)):
    """
    Plot a line chart of the given attributes in a specific timeframe
    """
    lr = LinReg(db)
    df = await lr.aggregate_data(inputs.start_date, inputs.end_date, inputs.start_hour, inputs.end_hour)
    df = df[inputs.keys_to_compare]

    filename = PLOT_BASEDIR + '/' + 'fromrequest'
    df.plot(figsize=(18, 5))
    plt.ioff()
    plt.savefig(filename)
    # return FileResponse(plt.savefig(), media_type='image/png')
    return 'Done'


def generate_id(inputs):
    src_weights = "".join([str(v).replace('.', '') for v in inputs.srcWeights.values()])
    dst_weights = "".join([str(v).replace('.', '') for v in inputs.dstWeights.values()])
    veh_dist = "".join([str(v).replace('.', '') for v in inputs.vehicleDistribution.values()])
    return ("%s_%s_%s_%s_%s_%s" % (src_weights, dst_weights, veh_dist, inputs.vehicleNumber, inputs.timesteps, inputs.weatherScenario))