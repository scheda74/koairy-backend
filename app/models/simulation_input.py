from fastapi import FastAPI, Body
from typing import Dict
from pydantic import BaseModel, Schema

class SimulationInput(BaseModel):
    weatherScenario: int = Schema(0, description='Choose between different weather scenarios')
    vehicleDistribution: Dict[str, float] = Schema(..., description='Distribution of emission classes')
    srcWeights: Dict[str, float] = Schema(..., description='Percentage of how many vehicles (agents) start from an area')
    dstWeights: Dict[str, float] = Schema(..., description='Percentage of how many vehicles (agents) end in an area')
    vehicleNumber: int = 9500
    timesteps: int = Schema(10800, description="Seconds of simulation, default 10800s => 3 hours")

example_simulation_input = Body(
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
        'timesteps': 10800
    }
)