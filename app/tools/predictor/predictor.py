
from app.tools.predictor.neural_nets import NeuralNet
from app.tools.predictor.lin_reg import LinReg

from app.models.prediction_input import (PredictionInput, example_prediction_input)

from app.db.mongodb import AsyncIOMotorClient, get_database
from fastapi import Depends

import abc


class Predictor(object):
    def __init__(
        self,
        db,
        prediction_params: PredictionInput = example_prediction_input,
        sim_id=None,
        predictionModel='lin-reg'
    ):  
        self.db = db
        self.sim_id = sim_id
        self.predictionModel = prediction_params.predictionModel
        self.prediction_params = prediction_params
    
    async def predict_emissions(self):
        if self.predictionModel == 'lin-reg':
            return await LinearRegressionStrategy(
                self.prediction_params,
                self.db,
                self.sim_id
            ).predict_emissions()
        elif self.predictionModel == 'lstm':
            return await LongShortTermMemoryRecurrentNeuralNetworkStrategy(
                self.prediction_params,
                self.db,
                self.sim_id
            ).predict_emissions()
        elif self.predictionModel == 'mlp':
            return await MLPRegressorStrategy(
                self.prediction_params,
                self.db,
                self.sim_id
            ).predict_emissions()
        elif self.predictionModel == 'cnn':
            print('cnn not yet specified, lin reg started')
            return await LinearRegressionStrategy(
                self.prediction_params,
                self.db,
                self.sim_id
            ).predict_emissions()
        else:
            print('Specified strategy not found!')

class PredictorStrategyAbstract(object):
    __metaclass__ = abc.ABCMeta

    def __init__(
        self, 
        prediction_params,
        db: AsyncIOMotorClient=Depends(get_database),
        sim_id=None
    ):
        self.db = db
        self.sim_id = sim_id
        self.boxID = str(prediction_params.boxID)
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
        lr = LinReg(self.db, self.sim_id)
        return await lr.start_lin_reg(
            start_date=self.start_date, 
            end_date=self.end_date, 
            start_hour=self.start_hour, 
            end_hour=self.end_hour, 
            boxID=self.boxID, 
            input_keys=self.input_keys, 
            output_key=self.output_key
        )


class MLPRegressorStrategy(PredictorStrategyAbstract):
    async def predict_emissions(self):
        """Start MLP Model Training and Prediction"""
        lr = LinReg(self.db, self.sim_id)
        return await lr.start_mlp(
            start_date=self.start_date,
            end_date=self.end_date,
            start_hour=self.start_hour,
            end_hour=self.end_hour,
            boxID=self.boxID,
            input_keys=self.input_keys,
            output_key=self.output_key
        )

class LongShortTermMemoryRecurrentNeuralNetworkStrategy(PredictorStrategyAbstract):
    async def predict_emissions(self):
        """Start LSTM Model Training and Prediction"""
        nn = NeuralNet(self.db, self.sim_id)
        return await nn.start_lstm(
            start_date=self.start_date,
            end_date=self.end_date,
            start_hour=self.start_hour,
            end_hour=self.end_hour,
            boxID=self.boxID,
            input_keys=self.input_keys,
            output_key=self.output_key
        )

class ConvolutionalNeuralNetworkStrategy(PredictorStrategyAbstract):
    async def predict_emissions(self):
        """check road and do sth"""
        return {}