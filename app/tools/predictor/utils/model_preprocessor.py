import numpy as np 
import pandas as pd
import datetime
from fastapi import Depends
from ....db.mongodb import AsyncIOMotorClient, get_database
from ....crud.emissions import (
    get_raw_emissions_from_sim,
    get_aggregated_data_from_sim,
    insert_aggregated_data
)
from ...simulation.simulator import Simulator
from .bremicker_boxes import bremicker_boxes
from ...simulation.parse_emission import Parser
from ....models.prediction_input import PredictionInput
from ....crud.hawa_dawa import get_hawa_dawa_by_time
from ....crud.bremicker import get_bremicker_by_time
from .weather import fetch_weather_data


class ModelPreProcessor():
    def __init__(self,
                inputs: PredictionInput,
                db: AsyncIOMotorClient=Depends(get_database),
                sim_id=None,
                df_traffic=None):
        self.db = db
        self.sim_id = sim_id
        self.inputs = inputs
        self.box_id = inputs.box_id
        self.input_keys = inputs.input_keys
        self.output_key = inputs.output_key
        self.start_date = inputs.start_date
        self.end_date = inputs.end_date
        self.start_hour = inputs.start_hour
        self.end_hour = inputs.end_hour
        self.df_traffic = df_traffic

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
    async def aggregate_data(self, box_id=672, start_date='2019-08-01', end_date=None, start_hour='7:00', end_hour='10:00'):
        # box_id=int(box_id)
        if end_date is None:
            end_date = end_date = datetime.date.today().strftime("%Y-%m-%d")
        data = await get_aggregated_data_from_sim(self.db, self.sim_id)
        if data is not None:
            try:
                df = pd.DataFrame.from_dict(data["aggregated"], orient='index')
                df.index = pd.to_datetime(df.index)
                df = df.rename(columns={str(self.box_id): self.box_id})
                return df
            except Exception as e:
                raise Exception("[MODEL PREPROCESSOR] Error while formatting aggregated data from db: %s" % str(e))

        print("[MODEL PREPROCESSOR] Aggregated data for simulation not found! Fetching from sources...")
        # df_air = await self.fetch_air_and_traffic(box_id, start_date, end_date, start_hour, end_hour)
        df_air = await self.fetch_air_and_traffic(start_date, end_date, start_hour, end_hour)

        df_air.index.name = 'time'
        
        df_sim = await self.fetch_simulated_emissions(self.db, self.sim_id, self.box_id)
        df_sim = df_sim.groupby('time')[self.raw_emission_columns].sum()
        if df_sim.shape[0] == 0:
            raise Exception('[MODEL PREPROCESSOR] simulation dataframe empty. Something went wrong')

        df_nox = df_sim['NOx']
        df_pmx = df_sim['PMx']
        nox_var = df_nox.var(axis=0)
        nox_std = df_nox.std(axis=0)
        nox_mean = df_nox.mean(axis=0)
        pmx_var = df_pmx.var(axis=0)
        pmx_std = df_pmx.std(axis=0)
        pmx_mean = df_pmx.mean(axis=0)
        print('Var NOx: %s -- Var PMx: %s \n' % (nox_var, pmx_var))
        print('Std NOx: %s -- Std PMx: %s \n' % (nox_std, pmx_std))
        print('Mean NOx: %s -- Mean PMx: %s \n' % (nox_mean, pmx_mean))

        sim_rows = df_sim.shape[0]
        air_rows = df_air.shape[0]
        rows_needed = (air_rows / (sim_rows / 60))
        # ratio_nox = 1 - (nox_std / nox_mean)
        # ratio_pmx = 1 - (pmx_std / pmx_mean)
        
        print("%s rows needed" % rows_needed)
        # print("%s ratio_nox" % ratio_nox)
        # print("%s ratio_pmx" % ratio_pmx)
        
        nox_frames = [df_sim[['NOx']] * val for val in np.arange(0.8, 1.2, 0.4 / rows_needed)]
        df_nox = pd.concat(nox_frames, axis=0, ignore_index=True)
        df_nox = df_nox.groupby(df_nox.index // 60).sum()
        # self.save_df_to_plot(df_nox, 'nox_simulated_oversampled')

        # pmx_frames = [df_sim[['PMx']] * val for val in np.arange(1 - ratio_pmx, 1 + ratio_pmx, (ratio_pmx * 2) / rows_needed)]
        pmx_frames = [df_sim[['PMx']] * val for val in np.arange(0.8, 1.2, 0.4 / rows_needed)]
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
        return df_combined.dropna()


    async def aggregate_real_data(self, box_id=672, start_date='2019-08-01', end_date='2019-10-20', start_hour='7:00', end_hour='10:00'):
        # box_id=int(box_id)
        df_air = await self.fetch_air_and_traffic(start_date, end_date, start_hour, end_hour)
        df_air.index.name = 'time'

        return df_air

    async def aggregate_compare(self, box_id=672, start_date='2019-08-01', end_date='2019-10-20', start_hour='7:00', end_hour='10:00'):
        # box_id=int(box_id)
        df_air = await self.fetch_air_and_traffic(start_date, end_date, start_hour, end_hour)
        df_air.index.name = 'time'
        print(df_air[['no2', 'pm10']])
        df_sim = await self.fetch_simulated_emissions(self.db, self.sim_id, self.box_id)
        df_sim = df_sim.groupby('time')[self.raw_emission_columns].sum()

        # print(df_sim)
        df_sim = df_sim.groupby(df_sim.index // 60)[self.raw_emission_columns].sum()
        print(df_sim)
        return df_sim
        # return [df_air, df_sim]

    async def fetch_air_and_traffic(self, start_date='2019-08-01', end_date='2019-12-01', start_hour='7:00', end_hour='10:00'):
        # NOTE: Get real weather data and format it accordingly. Here we'll look at 2019 from 7:00 to 10:00
        df_traffic = await get_bremicker_by_time(
            self.db,
            self.box_id,
            self.start_date,
            self.end_date,
            self.start_hour,
            self.end_hour
        )

        # df_traffic = df_traffic.loc[~df_traffic.duplicated(keep='first')]
        df_hawa = await get_hawa_dawa_by_time(
            self.db, 
            self.start_date,
            self.end_date,
            self.start_hour,
            self.end_hour,
            self.box_id
        )
        # df_hawa = df_hawa.loc[~df_hawa.index.duplicated(keep='first')]

        df_wind = await fetch_weather_data(start_date, end_date, start_hour, end_hour)
        # df_wind = df_wind.loc[~df_wind.index.duplicated(keep='first')]

        df = pd.concat([df_hawa, df_traffic, df_wind], axis=1)
        # .fillna(method='ffill').fillna(method='bfill')
        return df

    async def fetch_simulated_emissions(self, db, sim_id, box_id=672):
        # NOTE: First we fetch the simulated emissions
        lat, lng = [round(bremicker_boxes[box_id]['lat'], 3), round(bremicker_boxes[box_id]['lng'], 3)]
        # print(lat, lng)
        raw_emissions = await get_raw_emissions_from_sim(db, sim_id)
        if raw_emissions is None:
            print("[PARSER] Raw emissions not in db. Looking to parse the output files")
            parser = Parser(self.db, self.sim_id)
            raw_emissions = await parser.parse_emissions()
            if raw_emissions is None:
                print("[PARSER] Output files don't exist. Starting simulation...")
                simulator = Simulator(
                    db=self.db,
                    sim_id=self.sim_id,
                    inputs=self.inputs,
                    df_traffic=self.df_traffic
                )
                if self.df_traffic is not None:
                    print("Starting SUMO...")
                    await simulator.start_single()
                else:
                    print("Starting SUMO...")
                    await simulator.start()
                raw_emissions = await get_raw_emissions_from_sim(self.db, self.sim_id)
                raw_emissions = pd.DataFrame(pd.read_json(raw_emissions["emissions"], orient='index'))
        else:
            raw_emissions = pd.DataFrame(pd.read_json(raw_emissions["emissions"], orient='index'))
        df = raw_emissions
        print(df)
        mask = (round(df['lat'], 3) == lat) & (round(df['lng'], 3) == lng)
        df = df.loc[mask]
        print(df)
        return df.fillna(method='ffill')
