from fastapi import Body
from typing import Dict
from pydantic import BaseModel, Schema

class SingleSimulationInput(BaseModel):
    vehicleDistribution: Dict[str, float] = Schema(..., description='Distribution of emission classes')
    vehicleNumber: int = Schema(None, description="Specify number of vehicles")
    timesteps: int = Schema(10800, description="Seconds of simulation, default 10800s => 3 hours")
    boxID: int = Schema(672, description='Select sensor location')
    start_hour: str = Schema('07:00', description='Select sensor location')
    end_hour: str = Schema('10:00', description='Select sensor location')

example_single_simulation_input = Body(
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
        'weatherScenario': None,
        'vehicleNumber': None,
        'timesteps': 10800,
        'boxID': 672,
        'start_hour': '07:00',
        'end_hour': '10:00'
    }
)