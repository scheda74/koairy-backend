import os
import sys
import subprocess
import xml.etree.ElementTree as ET
from lxml import etree
from random import choices
from ...tools.predictor.utils.bremicker_boxes import bremicker_boxes
from ...core.config import (
    AREA_OF_INTEREST,
    WEIGHT_INPUT,
    TRIP_OUTPUT,
    ROUTE_OUTPUT,
    DEFAULT_NET_INPUT,
    NET_BASEDIR,
    SUMO_CFG,
    VALID_AREA_IDS,
    RANDOM_TRIP_TOOL,
    TRAFFIC_INPUT_BASEDIR,
    DET_OUT_BASEDIR
)
# from ...models.prediction_input import PredictionInput
# from ...models.simulation_input import SimulationInput

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import sumolib


# self.sim_id = sim_id
# self.timesteps = timesteps
# self.agents = agents
# self.src_weights = src_weights
# self.dst_weights = dst_weights
# self.veh_dist = veh_dist
# # self.weight_type = weight_type
# self.fringe_factor = fringe_factor
# self.new_net_path = new_net_path
#
# self.weights_filepath = WEIGHT_INPUT + "%s.src.xml" % self.sim_id
# self.weights_filepath_prefix = WEIGHT_INPUT + self.sim_id
# self.trip_filepath = TRIP_OUTPUT + self.sim_id + ".trip.xml"
# self.route_filepath = ROUTE_OUTPUT + self.sim_id + ".rou.xml"
# self.net_filepath = new_net_path if new_net_path != None else DEFAULT_NET_INPUT
# self.cfg_filepath = SUMO_CFG + self.sim_id + ".sumocfg"
# new_net_path=None,
# timesteps=10800,
# agents=9500,
# src_weights={
#     'aschheim_west': 0.1,
#     'ebersberg_east': 0.37,
#     'feldkirchen_west': 0.1,
#     'heimstetten_industrial_1': 0.01,
#     'heimstetten_industrial_2': 0.01,
#     'heimstetten_residential': 0.18,
#     'kirchheim_industrial_east': 0.01,
#     'kirchheim_industrial_west': 0.01,
#     'kirchheim_residential': 0.16,
#     'unassigned_edges': 0.05
# },
# dst_weights={
#     'aschheim_west': 0.16,
#     'ebersberg_east': 0.07,
#     'feldkirchen_west': 0.16,
#     'heimstetten_industrial_1': 0.14,
#     'heimstetten_industrial_2': 0.14,
#     'heimstetten_residential': 0.06,
#     'kirchheim_industrial_east': 0.06,
#     'kirchheim_industrial_west': 0.11,
#     'kirchheim_residential': 0.05,
#     'unassigned_edges': 0.05
# },
# veh_dist={
#     'HBEFA3/PC_D_EU2': 0.007,
#     'HBEFA3/PC_D_EU3': 0.0251,
#     'HBEFA3/PC_D_EU4': 0.0934,
#     'HBEFA3/PC_D_EU5': 0.0890,
#     'HBEFA3/PC_D_EU6': 0.1,
#     'HBEFA3/PC_G_EU2': 0.0764,
#     'HBEFA3/PC_G_EU3': 0.0342,
#     'HBEFA3/PC_G_EU4': 0.1907,
#     'HBEFA3/PC_G_EU5': 0.1802,
#     'HBEFA3/PC_G_EU6': 0.163,
#     'HBEFA3/PC_Alternative': 0.02
# },
class SimulationPreProcessor:
    def __init__(
        self,
        sim_id,
        db,
        inputs,
        fringe_factor=1,
        df_traffic=None
    ):
        self.db = db
        self.sim_id = sim_id
        self.box_id = inputs.box_id
        self.timesteps = inputs.timesteps
        self.veh_dist = inputs.vehicleDistribution
        self.src_weights = inputs.srcWeights
        self.dst_weights = inputs.dstWeights
        self.fringe_factor = fringe_factor
        self.df_traffic = df_traffic

        if inputs.vehicleNumber is None:
            if self.df_traffic is None:
                self.agents = 400  # default value if user didn't specify it and bremicker request failed
            else:
                self.agents = self.df_traffic[self.box_id].max()
        else:
            self.agents = inputs.vehicleNumber

        self.weights_filepath = WEIGHT_INPUT + "%s.src.xml" % self.sim_id
        self.weights_filepath_prefix = WEIGHT_INPUT + self.sim_id
        self.trip_filepath = TRIP_OUTPUT + self.sim_id + ".trip.xml"
        self.route_filepath = ROUTE_OUTPUT + self.sim_id + ".rou.xml"
        self.cfg_filepath = SUMO_CFG + self.sim_id + ".sumocfg"
        self.add_filepath = TRAFFIC_INPUT_BASEDIR + "%s.add.xml" % self.sim_id
        self.det_out_filepath = TRAFFIC_INPUT_BASEDIR + "det_%s.out.xml" % self.sim_id

        new_net_path = NET_BASEDIR + "%s.net.xml" % self.box_id
        if not os.path.exists(new_net_path):
            new_net_path = DEFAULT_NET_INPUT
        self.net_filepath = new_net_path

        self.net = sumolib.net.readNet(self.net_filepath)

    def write_sumocfg_file(self):
        configuration_tag = ET.Element('configuration')

        input_tag = ET.SubElement(
            configuration_tag,
            'input'
        )
        net_file_tag = ET.SubElement(
            input_tag,
            'net-file',
            {'value': self.net_filepath}
        )
        route_files_tag = ET.SubElement(
            input_tag,
            'route-files',
            {'value': self.route_filepath}
        )
        gui_settings_file_tag = ET.SubElement(
            input_tag,
            'gui-settings-file',
            {'value': 'gui-settings-origin-dest-vehicles.cfg'}
        )

        time_tag = ET.SubElement(configuration_tag, 'time')
        begin_tag = ET.SubElement(time_tag, 'begin', {'value': '0'})
        end_tag = ET.SubElement(time_tag, 'end', {'value': str(self.timesteps)})

        processing_tag = ET.SubElement(configuration_tag, 'processing')
        junction_blocker_ignore_tag = ET.SubElement(processing_tag, 'ignore-junction-blocker', {'value': '1'})

        configuration_file = ET.ElementTree(configuration_tag)
        configuration_file.write(self.cfg_filepath)

        # pretty formatting
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(self.cfg_filepath, parser)
        tree.write(self.cfg_filepath, pretty_print=True)

    def write_weight_file(
        self,
        weights_per_area,
        weight_type='dst'
    ):
        filepath = self.weights_filepath_prefix + ".%s.xml" % weight_type
        print("Writing/Formatting weight file...")
        weights_per_area_keys = set(weights_per_area.keys())

        if weights_per_area_keys.symmetric_difference(VALID_AREA_IDS) != set():
            raise ValueError('area_ids must only be exactly %r.' % VALID_AREA_IDS)
        if weight_type != 'src' and weight_type != 'dst':
            raise ValueError("weight_type must be 'src' or 'dst'")

        edges_per_area = {}
        taz_tree = ET.parse(AREA_OF_INTEREST)
        taz_root = taz_tree.getroot()

        for taz in taz_root.iter('taz'):
            if (taz.get('id') in VALID_AREA_IDS):
                edges_per_area['{0}'.format(taz.get('id'))] = taz.get('edges').split()

        if not os.path.exists(filepath):
            self.init_weight_file(edges_per_area, filepath)

        scenario_weights_tree = ET.parse(filepath)
        scenario_weights_root = scenario_weights_tree.getroot()

        for edge in scenario_weights_root.iter('edge'):
            edge_id = edge.get('id')
            if (edge_id in edges_per_area['aschheim_west']):
                edge.set('value', '{0}'\
                .format(weights_per_area['aschheim_west']/len(edges_per_area['aschheim_west'])))
            elif (edge_id in edges_per_area['ebersberg_east']):
                edge.set('value', '{0}'\
                .format(weights_per_area['ebersberg_east']/len(edges_per_area['ebersberg_east'])))
            elif (edge_id in edges_per_area['feldkirchen_west']):
                edge.set('value', '{0}'\
                .format(weights_per_area['feldkirchen_west']/len(edges_per_area['feldkirchen_west'])))
            elif (edge_id in edges_per_area['heimstetten_industrial_1']):
                edge.set('value', '{0}'\
                .format(weights_per_area['heimstetten_industrial_1']/len(edges_per_area['heimstetten_industrial_1'])))
            elif (edge_id in edges_per_area['heimstetten_industrial_2']):
                edge.set('value', '{0}'\
                .format(weights_per_area['heimstetten_industrial_2']/len(edges_per_area['heimstetten_industrial_2'])))
            elif (edge_id in edges_per_area['heimstetten_residential']):
                edge.set('value', '{0}'\
                .format(weights_per_area['heimstetten_residential']/len(edges_per_area['heimstetten_residential'])))
            elif (edge_id in edges_per_area['kirchheim_industrial_east']):
                edge.set('value', '{0}'\
                .format(weights_per_area['kirchheim_industrial_east']/len(edges_per_area['kirchheim_industrial_east'])))
            elif (edge_id in edges_per_area['kirchheim_industrial_west']):
                edge.set('value', '{0}'\
                .format(weights_per_area['kirchheim_industrial_west']/len(edges_per_area['kirchheim_industrial_west'])))
            elif (edge_id in edges_per_area['kirchheim_residential']):
                edge.set('value', '{0}'\
                .format(weights_per_area['kirchheim_residential']/len(edges_per_area['kirchheim_residential'])))
            elif (edge_id in edges_per_area['unassigned_edges']):
                edge.set('value', '{0}'\
                .format(weights_per_area['unassigned_edges']/len(edges_per_area['unassigned_edges'])))

        scenario_weights_tree.write(filepath)
        return

    def init_weight_file(self, edges_per_area, filepath):
        print("Weight file not found - Initializing new weight file...")
        root = ET.Element('edgedata')
        interval = ET.SubElement(root, 'interval', {'begin': '0', 'end': str(self.timesteps)})

        for area_id, edges in edges_per_area.items():
            for edge in edges:
                ET.SubElement(interval, 'edge', {'id': edge, 'value': '0'})

        tree = ET.ElementTree(root)
        tree.write(filepath)

        #pretty formatting
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(filepath, parser)
        tree.write(filepath, pretty_print=True)

    def write_random_trips_and_routes(self):
        # path_to_script = tools + '/randomTrips.py'
        print("Writing random trips and route files...")
        cmd = "python %s -n %s -e %s -o %s --route-file %s --validate --fringe-factor %s -p %s --weights-prefix %s"\
                % ( RANDOM_TRIP_TOOL,
                    self.net_filepath,
                    self.timesteps, 
                    self.trip_filepath, 
                    self.route_filepath,
                    self.fringe_factor, 
                    ((self.timesteps-0) / (self.agents * 1.0)),
                    self.weights_filepath_prefix
                )
        subprocess.call(cmd.split())

        self.add_vehicle_type_to_routes()
    
    def add_vehicle_type_to_routes(self):
        emission_classes = list(self.veh_dist.keys())
        emission_weights = list(self.veh_dist.values())

        tree = ET.parse(self.route_filepath)
        root = tree.getroot()
        
        for elem in emission_classes:
            el = ET.Element('vType', {'id': elem, 'emissionClass': elem})
            root.insert(0, el)
        
        for vehicle in root.iter('vehicle'):
            choice = choices(emission_classes, weights=emission_weights)
            print(choice)
            vehicle.set('type', choice[0])
        tree.write(self.route_filepath)

    def write_detector_add_file(self):
        detectors = []
        xy_pos = self.net.convertLonLat2XY(bremicker_boxes[self.box_id]['lng'], bremicker_boxes[self.box_id]['lat'])
        # look 10m around the position
        lanes = self.net.getNeighboringLanes(xy_pos[0], xy_pos[1], 10)
        # attention, result is unsorted
        best_lane = None
        ref_d = 9999.
        for lane, dist in lanes:
            if dist < ref_d:
                ref_d = dist
                best_lane = lane
        pos, d = best_lane.getClosestLanePosAndDist(xy_pos)
        detectors.append(sumolib.sensors.inductive_loop.InductiveLoop('det_0', best_lane.getID(), pos, (self.timesteps / 3600), self.det_out_filepath))
        sumolib.files.additional.write(self.add_filepath, detectors)

    async def preprocess_simulation_input(self):
        print("path: %s" % self.weights_filepath)
        if not os.path.exists(self.weights_filepath) or \
                not os.path.exists(self.cfg_filepath) or \
                not os.path.exists(self.route_filepath) or \
                not os.path.exists(self.trip_filepath):
            self.write_sumocfg_file()
            self.write_weight_file(self.src_weights, 'src')  # create .src file
            self.write_weight_file(self.dst_weights, 'dst')  # create .dst file
            self.write_random_trips_and_routes()
        elif not os.path.exists(self.cfg_filepath):
            self.write_sumocfg_file()
        else:
            print("[PreProcessor] weight, routes and trip file already exists. Starting SUMO anyway...")
        
        return self.cfg_filepath

    async def preprocess_single_simulation_input(self):
        if not os.path.exists(self.cfg_filepath) or \
                not os.path.exists(self.route_filepath) or \
                not os.path.exists(self.add_filepath) or \
                not os.path.exists(self.trip_filepath):
            self.write_sumocfg_file()
            self.write_detector_add_file()
            self.write_random_trips_and_routes()
        else:
            print("[PreProcessor] routes and trip file already exists. Starting SUMO anyway...")

        return self.cfg_filepath
