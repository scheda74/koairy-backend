import os
import sys
import time
import json
from random import randrange, choice, choices
import pandas as pd
from ...core.config import EMISSION_OUTPUT_BASE, SUMO_COMMANDLINE, SUMO_GUI, TRAFFIC_INPUT_BASEDIR, SUMO_CFG
from ...crud.emissions import (get_caqi_emissions_for_sim, get_raw_emissions_from_sim)
from .preprocessor import SimulationPreProcessor
from .parse_emission import Parser

# export SUMO_HOME="/usr/local/opt/sumo/share/sumo"

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import traci


class Simulator:
    def __init__(self, db, inputs, sim_id, cfg_filepath=None, df_traffic=None):
        self.db = db
        self.sim_id = sim_id
        self.inputs = inputs
        self.veh_dist = inputs.vehicleDistribution
        self.timesteps = inputs.timesteps
        self.vehicleNumber = inputs.vehicleNumber
        self.box_id = inputs.box_id

        self.tripinfo_filepath = EMISSION_OUTPUT_BASE + 'tripinfo_%s.xml' % self.sim_id
        self.fcdoutput_filepath = EMISSION_OUTPUT_BASE + 'fcdoutput_%s.xml' % self.sim_id
        self.emission_output_filepath = EMISSION_OUTPUT_BASE + "emission_output_%s.xml" % self.sim_id
        self.add_filepath = TRAFFIC_INPUT_BASEDIR + "%s.add.xml" % self.sim_id
        self.det_out_filepath = TRAFFIC_INPUT_BASEDIR + "det_%s.out.xml" % self.box_id
        self.df_traffic = df_traffic

        if cfg_filepath is not None:
            self.cfg_filepath = cfg_filepath
        else:
            self.cfg_filepath = SUMO_CFG + self.sim_id + ".sumocfg"

    async def run(self):
        current_step = 0
        while traci.simulation.getMinExpectedNumber() > 0:
            if current_step > (self.timesteps * 1.2):
                break
            traci.simulationStep()
            current_step += 1
        traci.close()
        sys.stdout.flush()
        return

    async def start(self):
        # caqi = await get_caqi_emissions_for_sim(self.db, self.sim_id)
        raw = await get_raw_emissions_from_sim(self.db, self.sim_id)
        if raw is not None:
            print("[PARSER] Simulation has already been run. Fetching Data from DB...")
            return raw
        else:
            print("Starting PreProcessor...")
            processor = SimulationPreProcessor(
                db=self.db,
                sim_id=self.sim_id,
                inputs=self.inputs,
                df_traffic=self.df_traffic
            )
            # cfg_filepath = await processor.preprocess_simulation_input()
            self.cfg_filepath = await processor.preprocess_simulation_input()
            # sumoBinary = SUMO_COMMANDLINE
            sumoBinary = SUMO_GUI
            sumoCMD = [
                sumoBinary, 
                "-c", self.cfg_filepath,
                "--tripinfo-output", self.tripinfo_filepath,
                '--fcd-output', self.fcdoutput_filepath, 
                "--emission-output", self.emission_output_filepath,
                "--additional-files", self.add_filepath
            ]
            if not os.path.exists(self.emission_output_filepath):
                print(sumoCMD)
                traci.start(sumoCMD, 4041)
                await self.run()
            else:
                print("[SIMULATOR] Same simulation already exists. Parsing old file...")
            print("Parsing results...")
            parser = Parser(self.db, self.sim_id)
            df = await parser.parse_emissions()
            return df.reset_index().to_json(orient='index')

    async def run_single(self):
        try:
            emission_classes = list(self.veh_dist.keys())
            emission_weights = list(self.veh_dist.values())
            detector_steps = [step * 3600 for step in range(0, int(self.timesteps / 3600) + 1)]
            print(self.df_traffic)
            self.df_traffic = self.df_traffic.reset_index()
            self.df_traffic = self.df_traffic[[self.box_id]]
            self.df_traffic.index = pd.Series(self.df_traffic.index).apply(lambda x: x * 3600)
            max_vehicles = self.df_traffic[self.box_id].max()
            current_step = 0
            detected_vehicles = 0
            while traci.simulation.getMinExpectedNumber() > 0:
                if current_step > (self.timesteps * 1.2):
                    print("[SUMO] Simulation took to long. Aborting after %s simulated seconds" % str(current_step))
                    break
                detected_vehicles += traci.inductionloop.getLastStepVehicleNumber("det_%s_0" % self.box_id)
                detected_vehicles += traci.inductionloop.getLastStepVehicleNumber("det_%s_1" % self.box_id)
                traci.simulationStep()
                if current_step in detector_steps:
                    step = detector_steps.pop(0)
                    vehicle_threshold = self.df_traffic.loc[step][self.box_id]
                    det_veh_number = traci.inductionloop.getLastStepVehicleNumber("det_%s_1" % self.box_id)
                    print('simulated vehicle number at detector 1: %s' % str(det_veh_number))
                    needed_vehicles = detected_vehicles - vehicle_threshold
                    veh_ids = list(traci.inductionloop.getLastStepVehicleIDs("det_%s_0" % self.box_id))
                    veh_ids += list(traci.inductionloop.getLastStepVehicleIDs("det_%s_1" % self.box_id))
                    veh_ids = list(dict.fromkeys(veh_ids))
                    loaded_routes = traci.route.getIDList()
                    print('detected vehicles until now', detected_vehicles)
                    print('current step: ', step)
                    print('vehicle number too much/low: needed vehicles: %s' % str(needed_vehicles))

                    # while needed_vehicles > 0:
                    #     #remove vehicles
                    #     veh = veh_ids.pop(0)
                    #     # print("[TRACI] removed vehicle %s" % veh)
                    #     traci.vehicle.remove(veh)
                    #     needed_vehicles -= 1

                    while needed_vehicles < 0:
                        # add vehicles
                        veh = veh_ids.pop(0) if len(veh_ids) != 0 else randrange(1, max_vehicles + 1, 1)
                        route_id = traci.vehicle.getRouteID(veh) if len(veh_ids) != 0 else choice(loaded_routes)

                        # new_id = datetime.datetime.today().timestamp()
                        new_id = time.time()
                        # print("[TRACI] added vehicle id: %s_%s" % (str(veh), str(new_id)))
                        # print("[TRACI] added vehicle route id", str(route_id))
                        traci.vehicle.add(
                            vehID='%s_%s' % (str(veh), str(new_id)),
                            routeID=route_id,
                            typeID=choices(emission_classes, weights=emission_weights)[0]
                        )
                        needed_vehicles += 1
                    detected_vehicles = 0
                current_step += 1
        except Exception as e:
            raise Exception('[SUMO] An error occurred while running the simulation: %s' % str(e))
        finally:
            traci.close()
            sys.stdout.flush()
            return

    async def start_single(self):
        raw = await get_raw_emissions_from_sim(self.db, self.sim_id)
        if raw is not None:
            print("[PARSER] Simulation has already been run. Fetching Data from DB...")
            return raw
        else:
            print("Starting PreProcessor...")
            processor = SimulationPreProcessor(
                db=self.db,
                sim_id=self.sim_id,
                inputs=self.inputs,
                df_traffic=self.df_traffic
            )
            # cfg_filepath = await processor.preprocess_simulation_input()
            self.cfg_filepath = await processor.preprocess_single_simulation_input()

            sumoBinary = SUMO_COMMANDLINE
            # sumoBinary = SUMO_GUI
            sumoCMD = [
                sumoBinary,
                "-c", self.cfg_filepath,
                "--tripinfo-output", self.tripinfo_filepath,
                '--fcd-output', self.fcdoutput_filepath,
                "--emission-output", self.emission_output_filepath,
                "--additional-files", self.add_filepath
            ]
            if not os.path.exists(self.emission_output_filepath):
                print(sumoCMD)
                traci.start(sumoCMD, 4041)
                await self.run_single()
            else:
                print("[SIMULATOR] Same simulation already exists. Parsing old file...")
            print("Parsing results...")
            parser = Parser(self.db, self.sim_id, self.box_id)
            df = await parser.parse_emissions()
            # df = pd.DataFrame.from_dict(json.loads(raw["emissions"]), orient='index')
            # df = df.groupby(['time', 'lat', 'lng'])[['CO2', 'CO', 'NOx', 'PMx', 'fuel']].sum()
            return df.to_json(orient='index')
