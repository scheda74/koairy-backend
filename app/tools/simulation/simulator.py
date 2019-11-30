import os
import sys
import datetime
from random import randrange, choice, choices
import pandas as pd
from ...core.config import EMISSION_OUTPUT_BASE, SUMO_COMMANDLINE, SUMO_GUI, TRAFFIC_INPUT_BASEDIR
from ...crud.emissions import (get_caqi_emissions_for_sim, get_raw_emissions_from_sim)

# export SUMO_HOME="/usr/local/opt/sumo/share/sumo"

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import traci

class Simulator:
    def __init__(self, db, cfg_filepath, sim_id, veh_dist, timesteps, df_traffic=None, boxID=672):
        self.db = db
        self.sim_id = sim_id
        self.cfg_filepath = cfg_filepath
        self.veh_dist = veh_dist
        self.timesteps = timesteps
        self.boxID = boxID
        self.tripinfo_filepath = EMISSION_OUTPUT_BASE + 'tripinfo_%s.xml' % self.sim_id
        self.fcdoutput_filepath = EMISSION_OUTPUT_BASE + 'fcdoutput_%s.xml' % self.sim_id
        self.emission_output_filepath = EMISSION_OUTPUT_BASE + "emission_output_%s.xml" % self.sim_id
        self.add_filepath = TRAFFIC_INPUT_BASEDIR + "%s.add.xml" % self.boxID
        self.det_out_filepath = TRAFFIC_INPUT_BASEDIR + "det_%s.out.xml" % self.boxID
        self.df_traffic = df_traffic


    async def run(self):
        # step = 0
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            # print(step)
            # step += 1
        traci.close()
        sys.stdout.flush()
        return

    async def start(self):
        # caqi = await get_caqi_emissions_for_sim(self.db, self.sim_id)
        raw = await get_raw_emissions_from_sim(self.db, self.sim_id)
        if raw is not None:
            print("[PARSER] Simulation has already been run. Fetching Data from DB...")
            return
        else: 
            sumoBinary = SUMO_COMMANDLINE
            sumoCMD = [
                sumoBinary, 
                "-c", self.cfg_filepath,
                "--tripinfo-output", self.tripinfo_filepath,
                '--fcd-output', self.fcdoutput_filepath, 
                "--emission-output", self.emission_output_filepath
            ]
            if not os.path.exists(self.emission_output_filepath):
                print(sumoCMD)
                traci.start(sumoCMD, 4041)
                await self.run()
            else:
                print("[SIMULATOR] Same simulation already exists. Parsing old file...")
            return


    async def run_update(self):
        emission_classes = list(self.veh_dist.keys())
        emission_weights = list(self.veh_dist.values())
        detector_steps = [step * 3600 for step in range(0, int(self.timesteps / 3600) + 1)]
        self.df_traffic = self.df_traffic.reset_index()
        self.df_traffic = self.df_traffic[[self.boxID]]
        self.df_traffic.index = pd.Series(self.df_traffic.index).apply(lambda x: x * 3600)
        max_vehicles = self.df_traffic[self.boxID].max()
        print(self.df_traffic)
        current_step = 0
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            if current_step in detector_steps:
                step = detector_steps.pop(0)

                vehicle_threshold = self.df_traffic.loc[step][self.boxID]
                det_veh_number = traci.inductionloop.getLastStepVehicleNumber("det_0")

                needed_vehicles = det_veh_number - vehicle_threshold
                veh_ids = list(traci.inductionloop.getLastStepVehicleIDs("det_0"))
                loaded_routes = traci.route.getIDList()

                print('current step: ', step)
                print('vehicle number too much/low: needed vehicles: %s' % str(needed_vehicles))
                print('simulated vehicle number %s' % str(det_veh_number))

                while needed_vehicles > 0:
                    #remove vehicles
                    veh = veh_ids.pop(0)
                    # print("[TRACI] removed vehicle %s" % veh)
                    traci.vehicle.remove(veh)
                    needed_vehicles -= 1

                while needed_vehicles < 0:
                    # add vehicles
                    veh = veh_ids.pop(0) if len(veh_ids) != 0 else randrange(1, max_vehicles + 1, 1)
                    route_id = traci.vehicle.getRouteID(veh) if len(veh_ids) != 0 else choice(loaded_routes)

                    new_id = datetime.datetime.today().timestamp()
                    print("[TRACI] added vehicle id: %s_%s" % (str(veh), str(new_id)))
                    # print("[TRACI] added vehicle route id", str(route_id))
                    traci.vehicle.add(
                        vehID='%s_%s' % (str(veh), str(new_id)),
                        routeID=route_id,
                        typeID=choices(emission_classes, weights=emission_weights)[0]
                    )
                    needed_vehicles += 1
            current_step += 1

        traci.close()
        sys.stdout.flush()
        return

    async def start_single(self):
        raw = await get_raw_emissions_from_sim(self.db, self.sim_id)
        if raw is not None:
            print("[PARSER] Simulation has already been run. Fetching Data from DB...")
            return
        else:
            if self.df_traffic is None:
                self.df_traffic = 400
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
                await self.run_update()
            else:
                print("[SIMULATOR] Same simulation already exists. Parsing old file...")
            return
