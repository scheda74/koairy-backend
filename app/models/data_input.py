from fastapi import FastAPI, Body
from pydantic import BaseModel, Schema
from app.models.simulation_input import (SimulationInput, example_simulation_input)

class DataInput(SimulationInput):
    start_date: str = Schema(..., description='Choose starting date')
    end_date: str = Schema(..., description='Choose an end date')
    start_hour: str = Schema(..., description='Hour when to start')
    end_hour: str = Schema(..., description='Hour when to end')
    boxID: int = Schema(..., description='Number of Bremicker Box used for traffic data')

example_data_input = Body(
    ...,
    example={
        "start_date": '2019-08-01',
        "end_date": '2019-10-20',
        "start_hour": '0:00',
        "end_hour": '23:00',
        "boxID": 672
    }
)