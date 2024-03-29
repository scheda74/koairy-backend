from fastapi import Body
from pydantic import Schema
from .simulation_input import (SimulationInput, example_simulation_input)


class PredictionInput(SimulationInput):
    start_date: str = Schema('2019-08-01', description='Set a start date', alias="startDate")
    end_date: str = Schema('2020-01-01', description='Set an end date', alias="endDate")
    start_hour: str = Schema('7:00', description='Set a starting hour', alias="startHour")
    end_hour: str = Schema('10:00', description='Set an ending hour', alias="endHour")
    input_keys: list = Schema(['temp', 'hum', 'WIND_SPEED', 'WIND_DIR'], description='Give a list of keys which will train your model', alias='inputKeys')
    output_keys: list = Schema(['pm10', 'no2'], description='Specify pollutant key you wish to predict', alias='outputKeys')
    box_id: int = Schema(672, description='Specify the bremicker sensor location', alias='boxID')
    predictionModel: str = Schema('lstm', description='Specify what ML model should be used.')
    temp: int = Schema(15, description='Specify temperature. If none given current weather data will be used')
    hum: int = Schema(90, description='Specify relative humidity. If none given current weather data will be used')
    vehicleNumber: int = None


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
        'vehicleNumber': None,
        'timesteps': 10800,
        'temp': 15,
        'hum': 90,
        'startDate': '2019-08-01',
        'endDate': '2020-01-04',
        'start_hour': '7:00',
        'end_hour': '10:00',
        'input_keys': ['temp', 'hum', 'WIND_SPEED', 'WIND_DIR'],
        'output_key': ['pm10', 'no2'],
        'box_id': 672,
        'predictionModel': 'lin-reg'
    }
)

# class SinglePredictionInput(SingleSimulationInput):
#     start_date: str = Schema('2019-08-01', description='Set a start date')
#     end_date: str = Schema('2019-11-10', description='Set an end date')
#     start_hour: str = Schema('7:00', description='Set a starting hour')
#     end_hour: str = Schema('10:00', description='Set an ending hour')
#     input_keys: list = Schema(['temp', 'hum', 'PMx', 'WIND_SPEED', 'WIND_DIR'], description='Give a list of keys which will train your model')
#     output_key: str = Schema('pm10', description='Give pollutant key you wish to predict')
#     box_id: int = Schema(672, description='Specify the bremicker sensor location')
#     predictionModel: str = Schema('lstm', description='Specify what ML model should be used.')
#     temp: int = Schema(15, description='Specify temperature. If none given current weather data will be used')
#     hum: int = Schema(90, description='Specify relative humidity. If none given current weather data will be used')
#
# example_single_prediction_input = Body(
#     ...,
#     example={
#         'vehicleDistribution': {
#             'HBEFA3/PC_D_EU2': 0.007,
#             'HBEFA3/PC_D_EU3': 0.0251,
#             'HBEFA3/PC_D_EU4': 0.0934,
#             'HBEFA3/PC_D_EU5': 0.0890,
#             'HBEFA3/PC_D_EU6': 0.1,
#             'HBEFA3/PC_G_EU2': 0.0764,
#             'HBEFA3/PC_G_EU3': 0.0342,
#             'HBEFA3/PC_G_EU4': 0.1907,
#             'HBEFA3/PC_G_EU5': 0.1802,
#             'HBEFA3/PC_G_EU6': 0.163,
#             'HBEFA3/PC_Alternative': 0.02
#         },
#         'weatherScenario': None,
#         'temp': 15,
#         'hum': 90,
#         'vehicleNumber': None,
#         'timesteps': 10800,
#         'start_date': '2019-08-01',
#         'end_date': '2019-11-10',
#         'start_hour': '7:00',
#         'end_hour': '10:00',
#         'input_keys': ['temp', 'hum', 'PMx', 'WIND_SPEED', 'WIND_DIR'],
#         'output_key': 'pm10',
#         'box_id': 672,
#         'predictionModel': 'lstm'
#     }
# )

