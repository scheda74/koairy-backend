# import os, sys
# import subprocess
# import xml.etree.ElementTree as ET
# from lxml import etree
# from random import choices
# from ...tools.predictor.utils.bremicker_boxes import bremicker_boxes
# from ...core.config import (
#     AREA_OF_INTEREST,
#     WEIGHT_INPUT,
#     TRIP_OUTPUT,
#     ROUTE_OUTPUT,
#     DEFAULT_NET_INPUT,
#     NET_BASEDIR,
#     SUMO_CFG,
#     VALID_AREA_IDS,
#     RANDOM_TRIP_TOOL,
#     TRAFFIC_INPUT_BASEDIR,
#     DET_OUT_BASEDIR
# )
#
# from ..predictor.predictor import Predictor
#
# if 'SUMO_HOME' in os.environ:
#     tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
#     sys.path.append(tools)
# else:
#     sys.exit("please declare environment variable 'SUMO_HOME'")
#
# import sumolib
#
#
#
# class SingleSimulationPreProcessor():
#     def __init__(
#             self,
#             db,
#             sim_id,
#             # timesteps=10800,
#             # vehicleNumber=None,
#             # box_id=672,
#             # veh_dist={
#             #     'HBEFA3/PC_D_EU2': 0.007,
#             #     'HBEFA3/PC_D_EU3': 0.0251,
#             #     'HBEFA3/PC_D_EU4': 0.0934,
#             #     'HBEFA3/PC_D_EU5': 0.0890,
#             #     'HBEFA3/PC_D_EU6': 0.1,
#             #     'HBEFA3/PC_G_EU2': 0.0764,
#             #     'HBEFA3/PC_G_EU3': 0.0342,
#             #     'HBEFA3/PC_G_EU4': 0.1907,
#             #     'HBEFA3/PC_G_EU5': 0.1802,
#             #     'HBEFA3/PC_G_EU6': 0.163,
#             #     'HBEFA3/PC_Alternative': 0.02
#             # },
#             fringe_factor=1,
#             df_traffic=None
#     ):
#         self.db = db
#         self.sim_id = sim_id
#         self.box_id = box_id
#         self.timesteps = timesteps
#         self.veh_dist = veh_dist
#         self.fringe_factor = fringe_factor
#         self.df_traffic = df_traffic
#
#         if vehicleNumber is None:
#             if self.df_traffic is None:
#                 self.agents = 400  # default value if user didn't specify it and bremicker request failed
#             else:
#                 self.agents = self.df_traffic[self.box_id].max()
#         else:
#             self.agents = vehicleNumber
#
#         self.trip_filepath = TRIP_OUTPUT + self.sim_id + ".trip.xml"
#         self.route_filepath = ROUTE_OUTPUT + self.sim_id + ".rou.xml"
#         self.cfg_filepath = SUMO_CFG + self.sim_id + ".sumocfg"
#         self.add_filepath = TRAFFIC_INPUT_BASEDIR + "%s.add.xml" % self.box_id
#         self.det_out_filepath = TRAFFIC_INPUT_BASEDIR + "det_%s.out.xml" % self.box_id
#
#         new_net_path = NET_BASEDIR + "%s.net.xml" % box_id
#         if not os.path.exists(new_net_path):
#             new_net_path = DEFAULT_NET_INPUT
#         self.net_filepath = new_net_path
#
#         self.net = sumolib.net.readNet(self.net_filepath)
#
#     def write_sumocfg_file(self):
#         configuration_tag = ET.Element('configuration')
#
#         input_tag = ET.SubElement(
#             configuration_tag,
#             'input'
#         )
#         net_file_tag = ET.SubElement(
#             input_tag,
#             'net-file',
#             {'value': self.net_filepath}
#         )
#         route_files_tag = ET.SubElement(
#             input_tag,
#             'route-files',
#             {'value': self.route_filepath}
#         )
#         gui_settings_file_tag = ET.SubElement(
#             input_tag,
#             'gui-settings-file'
#         )
#
#         time_tag = ET.SubElement(configuration_tag, 'time')
#         begin_tag = ET.SubElement(time_tag, 'begin', {'value': '0'})
#         end_tag = ET.SubElement(time_tag, 'end', {'value': str(self.timesteps)})
#
#         processing_tag = ET.SubElement(configuration_tag, 'processing')
#         junction_blocker_ignore_tag = ET.SubElement(processing_tag, 'ignore-junction-blocker', {'value': '1'})
#
#         configuration_file = ET.ElementTree(configuration_tag)
#         configuration_file.write(self.cfg_filepath)
#
#         # pretty formatting
#         parser = etree.XMLParser(remove_blank_text=True)
#         tree = etree.parse(self.cfg_filepath, parser)
#         tree.write(self.cfg_filepath, pretty_print=True)
#
#     def generate_trip_file(self, begin, end):
#         if os.path.exists(self.trip_filepath):
#             return
#         cmd = 'python %s --net-file %s --weight-files'
#
#     def write_random_trips_and_routes(self):
#         print("Writing random trips and route files...")
#         cmd = "python %s -n %s -e %s -o %s --route-file %s --validate --fringe-factor %s -p %s" \
#               % (RANDOM_TRIP_TOOL,
#                  self.net_filepath,
#                  self.timesteps,
#                  self.trip_filepath,
#                  self.route_filepath,
#                  self.fringe_factor,
#                  (self.timesteps / (self.agents * 1.0))
#                  )
#         subprocess.call(cmd.split())
#         self.add_vehicle_type_to_routes()
#
#     def add_vehicle_type_to_routes(self):
#         emission_classes = list(self.veh_dist.keys())
#         emission_weights = list(self.veh_dist.values())
#
#         tree = ET.parse(self.route_filepath)
#         root = tree.getroot()
#
#         for elem in emission_classes:
#             el = ET.Element('vType', {'id': elem, 'emissionClass': elem})
#             root.insert(0, el)
#
#         for vehicle in root.iter('vehicle'):
#             choice = choices(emission_classes, weights=emission_weights)
#             print(choice)
#             vehicle.set('type', choice[0])
#
#         tree.write(self.route_filepath)
#
#     def write_detector_add_file(self):
#         detectors = []
#         xy_pos = self.net.convertLonLat2XY(bremicker_boxes[self.box_id]['lng'], bremicker_boxes[self.box_id]['lat'])
#         # look 10m around the position
#         lanes = self.net.getNeighboringLanes(xy_pos[0], xy_pos[1], 10)
#         # attention, result is unsorted
#         bestLane = None
#         ref_d = 9999.
#         for lane, dist in lanes:
#             # now process them and determine a "bestLane"
#             # ...
#             if dist < ref_d:
#                 ref_d = dist
#                 bestLane = lane
#         pos, d = bestLane.getClosestLanePosAndDist(xy_pos)
#         detectors.append(sumolib.sensors.inductive_loop.InductiveLoop('det_0', bestLane.getID(), pos, (self.timesteps / 3600), self.det_out_filepath, friendlyPos=False))
#         sumolib.files.additional.write(self.add_filepath, detectors)
#
#     async def preprocess_simulation_input(self):
#         if not os.path.exists(self.cfg_filepath):
#             self.write_sumocfg_file()
#             self.write_detector_add_file()
#             self.write_random_trips_and_routes()
#         elif not os.path.exists(self.cfg_filepath):
#             self.write_sumocfg_file()
#         else:
#             print("[PreProcessor] routes and trip file already exists. Starting SUMO anyway...")
#
#         return self.cfg_filepath
