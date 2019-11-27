from fastapi import FastAPI, Body
from typing import Dict
from pydantic import BaseModel, Schema
from app.models.simulation_input import (SimulationInput, example_simulation_input)

class PlotInput(BaseModel):
    start_date: str = Schema('2019-08-01', description='Set a start date')
    end_date: str = Schema('2019-10-25', description='Set an end date')
    start_hour: str = Schema('6:00', description='Set a starting hour')
    end_hour: str = Schema('11:00', description='Set an ending hour')
    keys_to_compare: list = Schema(..., description='Give a list of keys you want to plot')

example_plot_input = Body(
    ...,
    example={
        'start_date': '2019-08-01',
        'end_date': '2019-10-25',
        'start_hour': '0:00',
        'end_hour': '0:00',
        'keys_to_compare': ['veh', 'TEMP', 'no2']
    }
)

class PredictionInput(SimulationInput):
    start_date: str = Schema('2019-08-01', description='Set a start date')
    end_date: str = Schema('2019-11-10', description='Set an end date')
    start_hour: str = Schema('7:00', description='Set a starting hour')
    end_hour: str = Schema('10:00', description='Set an ending hour')
    input_keys: list = Schema(['temp', 'hum', 'PMx', 'WIND_SPEED', 'WIND_DIR'], description='Give a list of keys which will train your model')
    output_key: str = Schema('pm10', description='Give pollutant key you wish to predict')
    boxID: int = Schema(672, description='Specify the bremicker sensor location')
    predictionModel: str = Schema('lstm', description='Specify what ML model should be used.')

example_prediction_input = Body(
    ...,
    example={
        'vehicleDistribution': {
            'HBEFA3/PC_D_EU2': 0.007,
            'HBEFA3/PC_D_EU3': 0.0251,
            'HBEFA3/PC_D_EU4': 0.0934,
            'HBEFA3/PC_D_EU5': 0.0890, 
            'HBEFA3/PC_D_EU6': 0.1,
            'HBEFA3/PC_G_EU2': 0.0764,
            'HBEFA3/PC_G_EU3': 0.0342,
            'HBEFA3/PC_G_EU4': 0.1907,
            'HBEFA3/PC_G_EU5': 0.1802, 
            'HBEFA3/PC_G_EU6': 0.163, 
            'HBEFA3/PC_Alternative': 0.02
        },
        'weatherScenario': 0,
        'srcWeights': {
            'aschheim_west': 0.1,
            'ebersberg_east': 0.37,
            'feldkirchen_west': 0.1,
            'heimstetten_industrial_1': 0.01,
            'heimstetten_industrial_2': 0.01,
            'heimstetten_residential': 0.18,
            'kirchheim_industrial_east': 0.01,
            'kirchheim_industrial_west': 0.01,
            'kirchheim_residential': 0.16,
            'unassigned_edges': 0.05
        },
        'dstWeights': {
            'aschheim_west': 0.16,
            'ebersberg_east': 0.07,
            'feldkirchen_west': 0.16,
            'heimstetten_industrial_1': 0.14,
            'heimstetten_industrial_2': 0.14,
            'heimstetten_residential': 0.06,
            'kirchheim_industrial_east': 0.06,
            'kirchheim_industrial_west': 0.11,
            'kirchheim_residential': 0.05,
            'unassigned_edges': 0.05
        },
        'vehicleNumber': 9500,
        'timesteps': 10800,
        'start_date': '2019-08-01',
        'end_date': '2019-11-10',
        'start_hour': '7:00',
        'end_hour': '10:00',
        'input_keys': ['temp', 'hum', 'PMx', 'WIND_SPEED', 'WIND_DIR'],
        'output_key': 'pm10',
        'boxID': 672,
        'predictionModel': 'lstm'
    }
)

