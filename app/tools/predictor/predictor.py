
from ...tools.predictor.neural_nets import NeuralNet

from sklearn.linear_model import LinearRegression
from sklearn.metrics import (mean_absolute_error, mean_squared_error)
from sklearn.neural_network import MLPRegressor
from sklearn import preprocessing as pre

from ...tools.predictor.utils.model_preprocessor import ModelPreProcessor

from ...models.prediction_input import (PredictionInput, example_prediction_input)

from ...db.mongodb import AsyncIOMotorClient, get_database
from fastapi import Depends

import abc


class Predictor(object):
    def __init__(
        self,
        db,
        prediction_params: PredictionInput = example_prediction_input,
        sim_id=None,
        df_traffic=None
    ):  
        self.db = db
        self.sim_id = sim_id
        self.df_traffic=df_traffic
        self.predictionModel = prediction_params.predictionModel
        self.prediction_params = prediction_params
    
    async def predict_emissions(self):
        if self.predictionModel == 'lin-reg':
            return await LinearRegressionStrategy(
                self.prediction_params,
                self.db,
                self.sim_id,
                self.df_traffic
            ).predict_emissions()
        elif self.predictionModel == 'lstm':
            return await LongShortTermMemoryRecurrentNeuralNetworkStrategy(
                self.prediction_params,
                self.db,
                self.sim_id,
                self.df_traffic
            ).predict_emissions()
        elif self.predictionModel == 'mlp':
            return await MLPRegressorStrategy(
                self.prediction_params,
                self.db,
                self.sim_id,
                self.df_traffic
            ).predict_emissions()
        elif self.predictionModel == 'cnn':
            print('cnn not yet specified, lin reg started')
            return await LinearRegressionStrategy(
                self.prediction_params,
                self.db,
                self.sim_id,
                self.df_traffic
            ).predict_emissions()
        else:
            print('Specified strategy not found!')


class PredictorStrategyAbstract(object):
    __metaclass__ = abc.ABCMeta

    def __init__(
        self, 
        prediction_params,
        db: AsyncIOMotorClient=Depends(get_database),
        sim_id=None,
        df_traffic=None
    ):
        self.db = db
        self.sim_id = sim_id
        self.df_traffic=df_traffic
        self.inputs = prediction_params
        self.box_id = prediction_params.box_id
        self.input_keys = prediction_params.input_keys
        self.output_key = prediction_params.output_key
        self.start_date = prediction_params.start_date
        self.end_date = prediction_params.end_date
        self.start_hour = prediction_params.start_hour
        self.end_hour = prediction_params.end_hour


    @abc.abstractmethod
    def predict_emissions(self):
        """required method"""

class LinearRegressionStrategy(PredictorStrategyAbstract):
    async def predict_emissions(self):
        """Start Linear Regression Model Training and Prediction"""
        self.inputs.input_keys.append(self.inputs.box_id)
        mp = ModelPreProcessor(db=self.db, inputs=self.inputs, sim_id=self.sim_id, df_traffic=self.df_traffic)
        df_combined = await mp.aggregate_data(
            self.box_id,
            self.start_date,
            self.end_date,
            self.start_hour,
            self.end_hour
        )
        print(df_combined)
        rows = round(df_combined.shape[0] * 0.8)
        df_train = df_combined.iloc[:rows]
        df_test = df_combined.iloc[rows:]

        model = LinearRegression()
        model.fit(df_train[self.input_keys], df_train[self.output_key])

        print('Intercept: \n', model.intercept_)
        print('Coefficients: \n', model.coef_)
        df_test[self.output_key + '_predicted'] = model.predict(df_test[self.input_keys])
        df_test['MeanAbsErr'] = str(
            mean_absolute_error(df_test[self.output_key].to_numpy(),
                                df_test['%s_predicted' % self.output_key].to_numpy()))
        # print(df_test)
        # df_test = df_test.reset_index()
        result = df_test[[self.output_key, '%s_predicted' % self.output_key]]
        print("Mean Abs Error LinReg: " + str(
            mean_absolute_error(result[self.output_key].to_numpy(),
                                result['%s_predicted' % self.output_key].to_numpy())))
        # self.save_df_to_plot(result[[output_key, '%s_lin_predicted' % output_key]], 'new_%s_lin_dist_prediction' % output_key)
        result.index = result.index.strftime('%Y-%m-%d %H:%M')
        return result


class MLPRegressorStrategy(PredictorStrategyAbstract):
    async def predict_emissions(self):
        """Start MLP Model Training and Prediction"""
        self.inputs.input_keys.append(self.inputs.box_id)
        mp = ModelPreProcessor(db=self.db, inputs=self.inputs, sim_id=self.sim_id)
        df = await mp.aggregate_data()
        # print('aggregated')
        # print(df)

        rows = round(df.shape[0] * 0.8)
        df_train = df.iloc[:rows]
        df_test = df.iloc[rows:]
        scaler = pre.StandardScaler()
        train_scaled = scaler.fit_transform(df.iloc[:rows][self.input_keys])
        test_scaled = scaler.fit_transform(df.iloc[rows:][self.input_keys])

        model = MLPRegressor(
            hidden_layer_sizes=(10,),
            activation='relu',
            solver='adam',
            learning_rate='adaptive',
            max_iter=1000,
            learning_rate_init=0.01,
            alpha=0.01
        )
        model.fit(train_scaled, df_train[self.output_key])

        # df_test[output_key + '_mlp_predicted'] = model.predict(df_test[input_keys])
        df_test[self.output_key + '_predicted'] = model.predict(test_scaled)
        df_test = df_test[[self.output_key, '%s_predicted' % self.output_key]]
        df_test['MeanAbsErr'] = str(
            mean_absolute_error(df_test[self.output_key].to_numpy(), df_test['%s_predicted' % self.output_key].to_numpy())
        )

        result = df_test[[self.output_key, '%s_predicted' % self.output_key]]
        # print(result)
        print("Mean Abs Error MLP: " + str(
            mean_absolute_error(result[self.output_key].to_numpy(), result['%s_predicted' % self.output_key].to_numpy())))
        # self.save_df_to_plot(result[[output_key, '%s_mlp_predicted' % output_key]], 'new_%s_mlp_dist_regressor' % output_key.replace('.', '-'))
        result.index = result.index.strftime('%Y-%m-%d %H:%M')
        return result


class LongShortTermMemoryRecurrentNeuralNetworkStrategy(PredictorStrategyAbstract):
    async def predict_emissions(self):
        """Start LSTM Model Training and Prediction"""
        nn = NeuralNet(self.db, self.sim_id)
        return await nn.start_lstm(
            start_date=self.start_date,
            end_date=self.end_date,
            start_hour=self.start_hour,
            end_hour=self.end_hour,
            box_id=self.box_id,
            input_keys=self.input_keys,
            output_key=self.output_key
        )


class ConvolutionalNeuralNetworkStrategy(PredictorStrategyAbstract):
    async def predict_emissions(self):
        """check road and do sth"""
        return {}