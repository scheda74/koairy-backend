import os
import sys
from ...core.config import EMISSION_OUTPUT_BASE, SUMO_COMMANDLINE, TRAFFIC_INPUT_BASEDIR
from ...crud.emissions import (get_caqi_emissions_for_sim, get_raw_emissions_from_sim)

# export SUMO_HOME="/usr/local/opt/sumo/share/sumo"

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import traci

class Simulator:
    def __init__(self, db, cfg_filepath, sim_id, timesteps, df_traffic=None, boxID=672):
        self.db = db
        self.sim_id = sim_id
        self.cfg_filepath = cfg_filepath
        self.timesteps = timesteps
        self.boxID = boxID
        self.tripinfo_filepath = EMISSION_OUTPUT_BASE + 'tripinfo_%s.xml' % self.sim_id
        self.fcdoutput_filepath = EMISSION_OUTPUT_BASE + 'fcdoutput_%s.xml' % self.sim_id
        self.emission_output_filepath = EMISSION_OUTPUT_BASE + "emission_output_%s.xml" % self.sim_id
        self.add_filepath = TRAFFIC_INPUT_BASEDIR + "%s_.add.xml" % self.boxID
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
        detector_steps = [step for step in range(0, int(self.timesteps / 3600))]
        self.df_traffic = self.df_traffic.reset_index()
        self.df_traffic = self.df_traffic[[self.boxID]]
        current_step = 0

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            step = detector_steps.pop(0) if len(detector_steps) != 0 else
            if current_step == (3600 * step):
                vehicle_threshold = self.df_traffic.iloc[step][self.boxID]
                det_veh_number = traci.inductionLoop.getLastStepVehicleNumber("det_0")
                vehicles = det_veh_number - vehicle_threshold


                det_vehs = traci.inductionLoop.getLastStepVehicleIDs("det_0")
                for veh in enumerate(det_vehs):
                    while vehicles > 0:
                        # remove vehicles

                        vehicles -= 1
                    while vehicles < 0:
                        # add vehicles
                        vehicles += 1
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
            sumoBinary = SUMO_COMMANDLINE
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
            return