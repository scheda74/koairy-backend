# import numpy as np
# import pandas as pd
# # import matplotlib.pyplot as plt
# import datetime
# import json
# import math
#
# from app.tools.simulation.parse_emission import Parser
# from app.tools.predictor.utils.bremicker_boxes import bremicker_boxes
# import app.tools.simulation.calc_caqi as aqi
#
# from app.core.config import (
#     WEATHER_BASEDIR,
#     WEATHER_PRESSURE,
#     WEATHER_TEMP_HUMID,
#     WEATHER_WIND,
#     AIR_BASEDIR,
#     PLOT_BASEDIR,
#     EMISSION_OUTPUT
# )
#
# from fastapi import Depends
# from app.crud.bremicker import (get_bremicker_by_time, get_current_bremicker_by_time)
# from app.db.mongodb import AsyncIOMotorClient, get_database
#
# from keras.models import Sequential
# from keras.layers import Dense
# from keras.layers import LSTM
# from sklearn.linear_model import LinearRegression
# from sklearn.metrics import (mean_absolute_error, mean_squared_error)
# from sklearn.neural_network import MLPRegressor
# from sklearn import preprocessing as pre
#
# from ...tools.predictor.utils.model_preprocessor import ModelPreProcessor
#
# # from .predictor import PredictorStrategyAbstract
#
# class LinReg():
#     def __init__(self, db: AsyncIOMotorClient, sim_id=None, existing_regr=None):
#         super().__init__()
#         # self.db = db
#         # self.sim_id = sim_id
#         self.existing_regr = existing_regr
#         self.raw_emission_columns = ['CO', 'NOx', 'PMx']
#         self.real_emission_columns = ['no2', 'pm2.5', 'pm10', 'o3', 'WIND_SPEED', 'WIND_DIR']
#         self.mp = ModelPreProcessor(self.db, self.sim_id)
#
#     async def start_mlp(
#         self,
#         start_date='2019-08-01',
#         end_date='2019-10-20',
#         start_hour='7:00',
#         end_hour='10:00',
#         data=None,
#         box_id=672,
#         input_keys=['temp', 'hum', 'PMx', 'WIND_SPEED', 'WIND_DIR'],
#         output_key='pm10'
#     ):
#         input_keys.append(box_id)
#         df = await self.mp.aggregate_data(box_id, start_date, end_date, start_hour, end_hour)
#         # print('aggregated')
#         # print(df)
#
#         rows = round(df.shape[0] * 0.8)
#         df_train = df.iloc[:rows]
#         df_test = df.iloc[rows:]
#         scaler = pre.StandardScaler()
#         train_scaled = scaler.fit_transform(df.iloc[:rows][input_keys])
#         test_scaled = scaler.fit_transform(df.iloc[rows:][input_keys])
#
#         model = MLPRegressor(
#             hidden_layer_sizes=(10,),
#             activation='relu',
#             solver='adam',
#             learning_rate='adaptive',
#             max_iter=1000,
#             learning_rate_init=0.01,
#             alpha=0.01
#         )
#         model.fit(train_scaled, df_train[output_key])
#
#         # df_test[output_key + '_mlp_predicted'] = model.predict(df_test[input_keys])
#         df_test[output_key + '_mlp_predicted'] = model.predict(test_scaled)
#         df_test = df_test[[output_key, '%s_mlp_predicted' % output_key]]
#         df_test['MeanAbsErr'] = str(
#             mean_absolute_error(df_test[output_key].to_numpy(), df_test['%s_mlp_predicted' % output_key].to_numpy())
#         )
#
#         result = df_test[['MeanAbsErr', output_key, '%s_mlp_predicted' % output_key]]
#         # print(result)
#         print("Mean Abs Error MLP: " + str(mean_absolute_error(result[output_key].to_numpy(), result['%s_mlp_predicted' % output_key].to_numpy())))
#         # self.save_df_to_plot(result[[output_key, '%s_mlp_predicted' % output_key]], 'new_%s_mlp_dist_regressor' % output_key.replace('.', '-'))
#         result.index = result.index.strftime('%Y-%m-%d %H:%M')
#         return result
#
#     async def start_lin_reg(
#         self,
#         start_date='2019-08-01',
#         end_date='2019-10-20',
#         start_hour='7:00',
#         end_hour='10:00',
#         data=None,
#         box_id=672,
#         input_keys=['temp', 'hum', 'PMx', 'WIND_SPEED', 'WIND_DIR'],
#         output_key='pm10'
#     ):
#         input_keys.append(box_id)
#
#         df_combined = await self.mp.aggregate_data(box_id, start_date, end_date, start_hour, end_hour)
#         print(df_combined)
#         rows = round(df_combined.shape[0] * 0.8)
#         df_train = df_combined.iloc[:rows]
#         df_test = df_combined.iloc[rows:]
#
#         # regr = await self.train_model(df_train, input_keys, output_key)
#
#         if data != None:
#             df_test = data
#
#         model = LinearRegression()
#         model.fit(df_train[input_keys], df_train[output_key])
#
#         print('Intercept: \n', model.intercept_)
#         print('Coefficients: \n', model.coef_)
#         df_test[output_key + '_lin_predicted'] = model.predict(df_test[input_keys])
#         df_test['MeanAbsErr'] = str(mean_absolute_error(df_test[output_key].to_numpy(), df_test['%s_lin_predicted' % output_key].to_numpy()))
#         # print(df_test)
#         # df_test = df_test.reset_index()
#         result = df_test[['MeanAbsErr', output_key, '%s_lin_predicted' % output_key]]
#         print("Mean Abs Error LinReg: " + str(mean_absolute_error(result[output_key].to_numpy(), result['%s_lin_predicted' % output_key].to_numpy())))
#         # self.save_df_to_plot(result[[output_key, '%s_lin_predicted' % output_key]], 'new_%s_lin_dist_prediction' % output_key)
#         result.index = result.index.strftime('%Y-%m-%d %H:%M')
#         return result