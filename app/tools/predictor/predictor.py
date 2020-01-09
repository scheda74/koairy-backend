# import matplotlib.pyplot as plt
import json
from ...tools.predictor.neural_nets import NeuralNet

from sklearn.linear_model import LinearRegression
from sklearn.metrics import (mean_absolute_error, mean_squared_error)
from sklearn.neural_network import MLPRegressor
from sklearn import preprocessing as pre

from ...tools.predictor.utils.model_preprocessor import ModelPreProcessor

from ...models.prediction_input import (PredictionInput, example_prediction_input)

from ...crud.emissions import get_simulated_traffic_from_sim
from ...db.mongodb import AsyncIOMotorClient, get_database
from fastapi import Depends
import pandas as pd
import abc


class Predictor(object):
    def __init__(
        self,
        db,
        prediction_params: PredictionInput = example_prediction_input,
        sim_id=None,
        df_traffic=None,
        is_single_sim=True
    ):  
        self.db = db
        self.sim_id = sim_id
        self.df_traffic = df_traffic
        self.predictionModel = prediction_params.predictionModel
        self.prediction_params = prediction_params
        self.is_single_sim = is_single_sim
        self.output_keys = prediction_params.output_keys
    
    async def predict_emissions(self):
        if self.predictionModel == 'lin-reg':
            strategy = LinearRegressionStrategy(
                self.prediction_params,
                self.db,
                self.sim_id,
                self.df_traffic,
                self.is_single_sim
            )
            result = []
            for key in self.output_keys:
                result.append(await strategy.predict_emissions(key))

            # plt.figure(figsize=(20, 10))
            # df = pd.DataFrame.from_dict(result[1]['prediction']).transpose()
            # print(df)
            # df.index = pd.datetime.strptime(df.index, "%Y-%m-%d %H:%M")
            # print(df)
            # df.plot()
            # plt.legend(loc='upper right')
            # plt.show()
            # plt.savefig(PLOT_BASEDIR + '/new_aggr_data')
            raw_emissions = await get_simulated_traffic_from_sim(self.db, self.sim_id)
            raw_emissions = json.loads(raw_emissions['emissions'])
            print(raw_emissions)
            return {'prediction': result, 'traffic': raw_emissions}
        elif self.predictionModel == 'lstm':
            strategy = LongShortTermMemoryRecurrentNeuralNetworkStrategy(
                self.prediction_params,
                self.db,
                self.sim_id,
                self.df_traffic,
                self.is_single_sim
            )
            result = []
            for key in self.output_keys:
                result.append(await strategy.predict_emissions(key))
            raw_emissions = await get_simulated_traffic_from_sim(self.db, self.sim_id)
            return {'prediction': result, 'traffic': json.loads(raw_emissions['emissions'])}
        elif self.predictionModel == 'mlp':
            strategy = MLPRegressorStrategy(
                self.prediction_params,
                self.db,
                self.sim_id,
                self.df_traffic,
                self.is_single_sim
            )
            result = []
            for key in self.output_keys:
                result.append(await strategy.predict_emissions(key))

            # plt.figure(figsize=(20, 10))
            # df = pd.DataFrame.from_dict(result[1]['prediction']).transpose()
            # df.index = pd.datetime.strptime(df.index, "%Y-%m-%d %H:%M")
            # print(df)
            # df.plot()
            # plt.legend(loc='upper right')
            # plt.show()

            raw_emissions = await get_simulated_traffic_from_sim(self.db, self.sim_id)
            raw_emissions = json.loads(raw_emissions['emissions'])
            print(raw_emissions)
            return {'prediction': result, 'traffic': raw_emissions}
        elif self.predictionModel == 'cnn':
            print('cnn not yet specified, lin reg started')
            strategy = LinearRegressionStrategy(
                self.prediction_params,
                self.db,
                self.sim_id,
                self.df_traffic
            )
            result = []
            for key in self.output_keys:
                result.append(await strategy.predict_emissions(key))
            return result
        else:
            print('Specified strategy not found!')


class PredictorStrategyAbstract(object):
    __metaclass__ = abc.ABCMeta

    def __init__(
        self, 
        prediction_params,
        db: AsyncIOMotorClient=Depends(get_database),
        sim_id=None,
        df_traffic=None,
        is_single_sim=True
    ):
        self.db = db
        self.sim_id = sim_id
        self.df_traffic = df_traffic
        self.inputs = prediction_params
        self.box_id = prediction_params.box_id
        self.start_date = prediction_params.start_date
        self.end_date = prediction_params.end_date
        self.start_hour = prediction_params.start_hour
        self.end_hour = prediction_params.end_hour
        self.is_single_sim = is_single_sim
        self.mp = ModelPreProcessor(
            db=self.db,
            inputs=self.inputs,
            sim_id=self.sim_id,
            df_traffic=self.df_traffic,
            is_single_sim=self.is_single_sim
        )
        self.input_keys = prediction_params.input_keys



    @abc.abstractmethod
    def predict_emissions(self, output_key):
        """required method"""

class LinearRegressionStrategy(PredictorStrategyAbstract):
    async def predict_emissions(self, output_key):
        """Start Linear Regression Model Training and Prediction"""
        input_keys = self.input_keys
        if output_key == 'no2':
            input_keys.append('NOx')
        else:
            input_keys.append('PMx')
        self.inputs.input_keys.append(self.inputs.box_id)
        df_combined = await self.mp.aggregate_data(
            self.box_id,
            self.start_date,
            self.end_date,
            self.start_hour,
            self.end_hour
        )
        # print(df_combined)

        df_train, df_test = format_test_train_set(df_combined, self.end_date)

        model = LinearRegression()
        model.fit(df_train[input_keys], df_train[output_key])


        df_test[output_key + '_predicted'] = model.predict(df_test[input_keys])
        if output_key == 'no2':
            sim_key = 'NOx'
        else:
            sim_key = 'PMx'
        # df_test[sim_key + '_simulated'] = df_test[sim_key]
        df_test = df_test.rename(columns={sim_key: sim_key + '_simulated'})
        # df_test['MeanAbsErr'] = str(
        #     mean_absolute_error(df_test[output_key].to_numpy(),
        #                         df_test['%s_predicted' % output_key].to_numpy()))
        result = df_test[[output_key, '%s_predicted' % output_key, '%s_simulated' % sim_key]]
        mea = mean_absolute_error(result[output_key].to_numpy(), result['%s_predicted' % output_key].to_numpy())
        # self.save_df_to_plot(result[[output_key, '%s_lin_predicted' % output_key]], 'new_%s_lin_dist_prediction' % output_key)
        result.index = result.index.strftime('%Y-%m-%d %H:%M')
        max_key = result.idxmax(axis=1).iloc[0]
        result = result.to_dict(orient='index')
        return {'key': output_key, 'mea': mea, 'prediction': result, 'maxKey': max_key}


class MLPRegressorStrategy(PredictorStrategyAbstract):
    async def predict_emissions(self, output_key):
        """Start MLP Model Training and Prediction"""
        input_keys = self.input_keys
        if output_key == 'no2':
            input_keys.append('NOx')
        else:
            input_keys.append('PMx')
        self.inputs.input_keys.append(self.inputs.box_id)
        # mp = ModelPreProcessor(db=self.db, inputs=self.inputs, sim_id=self.sim_id)
        df = await self.mp.aggregate_data(
            self.box_id,
            self.start_date,
            self.end_date,
            self.start_hour,
            self.end_hour
        )
        # print(df)
        df_train, df_test = format_test_train_set(df, self.end_date)

        scaler = pre.StandardScaler()
        train_scaled = scaler.fit_transform(df_train[input_keys])
        test_scaled = scaler.fit_transform(df_test[input_keys])

        model = MLPRegressor(
            hidden_layer_sizes=(10,),
            activation='relu',
            solver='adam',
            learning_rate='adaptive',
            max_iter=1000,
            learning_rate_init=0.01,
            alpha=0.01
        )
        model.fit(train_scaled, df_train[output_key])

        # df_test[output_key + '_mlp_predicted'] = model.predict(df_test[input_keys])
        df_test[output_key + '_predicted'] = model.predict(test_scaled)
        # df_test = df_test[[output_key, '%s_predicted' % output_key]]
        # df_test['MeanAbsErr'] = str(
        #     mean_absolute_error(df_test[output_key].to_numpy(), df_test['%s_predicted' % output_key].to_numpy())
        # )
        if output_key == 'no2':
            sim_key = 'NOx'
        else:
            sim_key = 'PMx'
        df_test = df_test.rename(columns={sim_key: sim_key + '_simulated'})
        # df_test[output_key + '_simulated'] = df_test[sim_key]
        result = df_test[[output_key, '%s_predicted' % output_key, '%s_simulated' % sim_key]]
        # print(result)
        mea = mean_absolute_error(result[output_key].to_numpy(), result['%s_predicted' % output_key].to_numpy())
        # self.save_df_to_plot(result[[output_key, '%s_mlp_predicted' % output_key]], 'new_%s_mlp_dist_regressor' % output_key.replace('.', '-'))
        result.index = result.index.strftime('%Y-%m-%d %H:%M')
        # print(result)
        max_key = result.idxmax(axis=1).iloc[0]
        result = result.to_dict(orient='index')
        return {'key': output_key, 'mea': mea, 'prediction': result, 'maxKey': max_key}


class LongShortTermMemoryRecurrentNeuralNetworkStrategy(PredictorStrategyAbstract):
    async def predict_emissions(self, output_key):
        """Start LSTM Model Training and Prediction"""
        input_keys = self.input_keys
        if output_key == 'no2':
            input_keys.append('NOx')
        else:
            input_keys.append('PMx')
        nn = NeuralNet(self.db, self.sim_id)
        return await nn.start_lstm(
            start_date=self.start_date,
            end_date=self.end_date,
            start_hour=self.start_hour,
            end_hour=self.end_hour,
            box_id=self.box_id,
            input_keys=input_keys,
            output_key=output_key
        )


class ConvolutionalNeuralNetworkStrategy(PredictorStrategyAbstract):
    async def predict_emissions(self, output_key):
        """check road and do sth"""
        return {}


def format_test_train_set(df, end_date):
    print("[MODEL PREPROCESSOR] end date to predict: " + end_date)
    date_to_predict = pd.datetime.strptime(end_date + " 00:00", "%Y-%m-%d %H:%M")
    date_to_predict = df.index[df.index.get_loc(date_to_predict, method='nearest')].replace(hour=0)

    train_mask = (df.index < date_to_predict)
    df_train = df.loc[train_mask]
    predict_mask = (df.index >= date_to_predict)
    df_test = df.loc[predict_mask]
    return [df_train, df_test]
    # rows = round(df.shape[0] * 0.8)
    # df_train = df.iloc[:rows]
    # df_test = df.iloc[rows:]
    # return [df_train, df_test]
