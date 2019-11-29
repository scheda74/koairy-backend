import numpy as np 
import pandas as pd
# import matplotlib.pyplot as plt
import datetime
import json
import math

from fastapi import Depends
from ....db.mongodb import AsyncIOMotorClient, get_database
from ....crud.emissions import (
    get_raw_emissions_from_sim,
    get_aggregated_data_from_sim,
    insert_aggregated_data
)
from ....crud.hawa_dawa import get_hawa_dawa_by_time
from ....crud.bremicker import get_bremicker_by_time
from .weather import fetch_weather_data
from .bremicker_boxes import bremicker_boxes
from ...simulation.parse_emission import Parser
import app.tools.simulation.calc_caqi as aqi
from app.core.config import (
    WEATHER_BASEDIR,
    WEATHER_PRESSURE,
    WEATHER_TEMP_HUMID, 
    WEATHER_WIND,
    AIR_BASEDIR,
    PLOT_BASEDIR,
    EMISSION_OUTPUT
)

from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (mean_absolute_error, mean_squared_error)
from sklearn.neural_network import MLPRegressor
from sklearn import preprocessing as pre



class ModelPreProcessor():
    def __init__(self, db: AsyncIOMotorClient=Depends(get_database), sim_id=None):
        self.db = db
        self.sim_id = sim_id
        self.raw_emission_columns = ['CO', 'NOx', 'PMx']

    def create_dataset(self, dataset, look_back=1):
        dataX, dataY = [], []
        for i in range(len(dataset)-look_back-1):
            a = dataset[i:(i+look_back), 0]
            dataX.append(a)
            dataY.append(dataset[i + look_back, 0])
        return np.array(dataX), np.array(dataY)


    ###############################################################################################
    ####################################### DATA SCALING ##########################################
    ###############################################################################################

    ## This is same as StandardScaler
    def normalize_data(self, column):
        std = column.std(axis=0)
        var = column.var(axis=0)
        mean = column.mean(axis=0)
        print('Var: \n', var)
        print('Std: \n', std)
        print('Mean: \n', mean)
        return (column - mean) / std



    ######################################################################################################
    ################################## DATA AGGREGATION FUNCTIONS ########################################
    ######################################################################################################
    async def aggregate_data(self, boxID=672, start_date='2019-08-01', end_date='2019-11-10', start_hour='7:00', end_hour='10:00'):
        boxID=int(boxID)
        data = await get_aggregated_data_from_sim(self.db, self.sim_id)
        if data is not None:
            try:
                df = pd.DataFrame.from_dict(data["aggregated"], orient='index')
                df.index = pd.to_datetime(df.index)
                df = df.rename(columns={str(boxID): boxID})
                return df
            except Exception as e:
                print("[MODEL PREPROCESSOR] Error while formatting aggregated data from db: %s" % str(e))

        print("[MODEL PREPROCESSOR] Aggregated data for simulation not found! Fetching from sources...")
        df_air = await self.fetch_air_and_traffic(boxID, start_date, end_date, start_hour, end_hour)

        df_air.index.name = 'time'
        
        df_sim = await self.fetch_simulated_emissions(boxID)
        df_sim = df_sim.groupby('time')[self.raw_emission_columns].sum()
        # print(df_sim)

        df_nox = df_sim['NOx']
        df_pmx = df_sim['PMx']
        nox_var = df_nox.var(axis=0)
        nox_std = df_nox.std(axis=0)
        nox_mean = df_nox.mean(axis=0)
        pmx_var = df_pmx.var(axis=0)
        pmx_std = df_pmx.std(axis=0)
        pmx_mean = df_pmx.mean(axis=0)
        print('Var: \n', nox_var, pmx_var)
        print('Std: \n', nox_std, pmx_std)
        print('Mean: \n', nox_mean, pmx_mean)
        # print(df_air.shape)
        # ratio = ((nox_std / nox_mean) + (pmx_std / pmx_mean)) / 2
        sim_rows = df_sim.shape[0]
        air_rows = df_air.shape[0]
        rows_needed = (air_rows / (sim_rows / 60))
        ratio_nox = 1 - (nox_std / nox_mean)
        ratio_pmx = 1 - (pmx_std / pmx_mean)
        
        print("%s rows needed" % rows_needed)
        print("%s ratio_nox" % ratio_nox)
        print("%s ratio_pmx" % ratio_pmx)
        
        nox_frames = [df_sim[['NOx']] * val for val in np.arange(1 - ratio_nox, 1 + ratio_nox, (ratio_nox * 2) / rows_needed)]
        df_nox = pd.concat(nox_frames, axis=0, ignore_index=True)
        df_nox = df_nox.groupby(df_nox.index // 60).sum()
        # self.save_df_to_plot(df_nox, 'nox_simulated_oversampled')

        pmx_frames = [df_sim[['PMx']] * val for val in np.arange(1 - ratio_pmx, 1 + ratio_pmx, (ratio_pmx * 2) / rows_needed)]
        df_pmx = pd.concat(pmx_frames, axis=0, ignore_index=True)
        df_pmx = df_pmx.groupby(df_pmx.index // 60).sum()
        # self.save_df_to_plot(df_pmx, 'pmx_simulated_oversampled')

        df = pd.concat([df_nox, df_pmx], axis=1)

        df_combined = pd.concat([df_air.reset_index(), df], axis=1).set_index('time')
        df_combined = df_combined[df_combined.index.notnull()]
        
        # .fillna(method='ffill')
        df_combined = df_combined.interpolate(method='time')
        df_formatted = df_combined.copy()
        df_formatted.index = df_formatted.index.strftime("%Y-%m-%d %H:%M")
        df_formatted = df_formatted.rename(columns={'pm2.5': 'pm25'})
        df_formatted.columns = df_formatted.columns.astype(str)
        await insert_aggregated_data(self.db, self.sim_id, df_formatted.to_dict(orient='index'))
        return df_combined


    async def aggregate_real_data(self, boxID=672, start_date='2019-08-01', end_date='2019-10-20', start_hour='7:00', end_hour='10:00'):
        boxID=int(boxID)
        df_air = await self.fetch_air_and_traffic(boxID, start_date, end_date, start_hour, end_hour)
        df_air.index.name = 'time'

        return df_air

    async def aggregate_compare(self, boxID=672, start_date='2019-08-01', end_date='2019-10-20', start_hour='7:00', end_hour='10:00'):
        boxID=int(boxID)
        df_air = await self.fetch_air_and_traffic(boxID, start_date, end_date, start_hour, end_hour)
        df_air.index.name = 'time'
        print(df_air[['no2', 'pm10']])
        df_sim = await self.fetch_simulated_emissions(boxID)
        df_sim = df_sim.groupby('time')[self.raw_emission_columns].sum()

        # print(df_sim)
        df_sim = df_sim.groupby(df_sim.index // 60)[self.raw_emission_columns].sum()
        print(df_sim)
        return df_sim
        # return [df_air, df_sim]

    #####################################################################################################
    ################################## DATA COLLECTION FUNCTIONS ########################################
    #####################################################################################################
    ## NOTE: This in crud probably
    async def fetch_simulated_emissions(self, box_id, entries=['CO', 'NOx', 'PMx', 'fuel']):
        # NOTE: First we fetch the simulated emissions
        parser = Parser(self.db, self.sim_id)
        lat, lng = [round(bremicker_boxes[box_id]['lat'], 3), round(bremicker_boxes[box_id]['lng'], 3)]
        # print(lat, lng)
        raw_emissions = await get_raw_emissions_from_sim(self.db, self.sim_id)
        if raw_emissions is None:
            raw_emissions = parser.parse_emissions()
        df = pd.DataFrame(pd.read_json(raw_emissions["emissions"], orient='index'))
        mask = (round(df['lat'], 3) == lat) & (round(df['lng'], 3) == lng)
        df = df.loc[mask]
        return df.fillna(method='ffill')



        

    async def fetch_air_and_traffic(self, boxID, start_date='2019-08-01', end_date='2019-11-01', start_hour='7:00', end_hour='10:00'):
        # NOTE: Get real weather data and format it accordingly. Here we'll look at 2019 from 7:00 to 10:00
        boxID = int(boxID)
        df_traffic = await get_bremicker_by_time(
            self.db,
            boxID,
            start_date,
            end_date, 
            start_hour,
            end_hour
        )

        # df_traffic = df_traffic.loc[~df_traffic.duplicated(keep='first')]
        df_hawa = await get_hawa_dawa_by_time(
            self.db, 
            start_date,
            end_date, 
            start_hour, 
            end_hour
        )
        df_hawa = df_hawa.loc[~df_hawa.index.duplicated(keep='first')]

        df_wind = await fetch_weather_data(start_date, end_date, start_hour, end_hour)
        # df_wind = df_wind.loc[~df_wind.index.duplicated(keep='first')]

        df = pd.concat([df_hawa, df_traffic, df_wind], axis=1)
        # .fillna(method='ffill').fillna(method='bfill')
        return df

    ###############################################################################################
    ################################## BREMICKER FUNCTIONS ########################################
    ###############################################################################################
    # async def get_bremicker(self):
    #     traffic_frames = [await self.get_bremicker_from_file(AIR_BASEDIR + '/air_2019_%0*d.json' % (2, index)) for index in range(1, 11)]
    #     return pd.concat(traffic_frames, keys=['%d' % index for index in range(1, 11)]).dropna()

    # async def get_bremicker_from_file(self, filepath):
    #     data = json.load(open(filepath))
    #     return pd.DataFrame(
    #         dict([ (k, pd.Series(v)) for k, v in data['features'][1]['properties']['timeValueSeries'].items() ])
    #     )

    # async def get_bremicker_sensors_from_file(self, filepath):
    #     data = json.load(open(filepath))
    #     traffic_frames = []
    #     for feature in data['features']:
    #         if feature['properties']['type'] == 'bremicker':
    #             sensor = {}
    #             sensor['coordinates'] = feature['geometry']['coordinates']
    #             df = pd.DataFrame(
    #                 dict([ (k, pd.Series(v)) for k, v in feature['properties']['timeValueSeries'].items() ])
    #             )
    #             sensor['vehicleNumber'] = feature['properties']['timeValueSeries'].items()
    #             traffic_frames.append(sensor)
    #     return traffic_frames


    #######################################################################################
    #################################AIR FUNCTIONS#########################################
    #######################################################################################
    # async def format_real_air_by_key(self, df, key, start_date, end_date, start_hour, end_hour):
    #     df = pd.DataFrame(df[key].tolist())
    #     df['time'] = pd.to_datetime(df['time'])
    #     df = df[['time', 'value']]
    #     mask = (df['time'] > start_date) & (df['time'] <= end_date)
    #     df = df.loc[mask].set_index('time')
    #     df = df.rename(columns={ 'value': key })
    #     return df.between_time(start_hour, end_hour)

    # async def get_real_air(self):
    #     air_frames = [await self.get_real_air_from_file(AIR_BASEDIR + '/air_2019_%0*d.json' % (2, index)) for index in range(1, 11)]
    #     return pd.concat(air_frames, keys=['%d' % index for index in range(1, 11)]).dropna()

    # async def get_real_air_from_file(self, filepath):
    #     data = json.load(open(filepath))
    #     return pd.DataFrame(
    #         dict([ (k, pd.Series(v)) for k, v in data['features'][6]['properties']['timeValueSeries'].items() ])
    #     )


    # def save_df_to_plot(self, df, filename):
    #     if not df.empty:
    #         df.plot(figsize=(18, 5))
    #         plt.savefig(PLOT_BASEDIR + '/' + filename)
    #     else:
    #         print('[PLOT] Error saving plot. Dataframe empty!')