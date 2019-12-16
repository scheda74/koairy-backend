import os
import sys
import subprocess
import pandas as pd
import xml.etree.ElementTree as ET
from lxml import etree
from random import choices, randrange
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
    DET_OUT_BASEDIR,
    ALL_DET_FILEPATH
)
# from ...models.prediction_input import PredictionInput
# from ...models.simulation_input import SimulationInput

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import sumolib


class SimulationPreProcessor:
    def __init__(
        self,
        sim_id,
        db,
        inputs,
        fringe_factor=1,
        df_traffic=None,
        is_single_sim=True
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
        self.is_single_sim = is_single_sim

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
        self.det_out_filepath = TRAFFIC_INPUT_BASEDIR + "det_%s.out.xml" % self.sim_id

        if self.is_single_sim:
            new_net_path = NET_BASEDIR + "%s.net.xml" % self.box_id
            self.add_filepath = TRAFFIC_INPUT_BASEDIR + "%s.add.xml" % self.sim_id
        else:
            new_net_path = DEFAULT_NET_INPUT
            self.add_filepath = ALL_DET_FILEPATH

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
        additional_file_tag = ET.SubElement(
            input_tag,
            'additional-files',
            {'value': self.add_filepath}
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
        # self.adjust_vehicle_departure()
        self.add_vehicle_type_to_routes()

    def adjust_vehicle_departure(self):
        df_traffic = self.df_traffic.copy()
        df_traffic = df_traffic.fillna(0)
        df_traffic = df_traffic.reset_index()
        df_traffic = df_traffic[bremicker_boxes.keys()]
        df_traffic.index = pd.Series(df_traffic.index).apply(lambda z: z * 600)
        detector_steps = [step * 600 for step in range(0, df_traffic.shape[0])]

        tree = ET.parse(self.route_filepath)
        root = tree.getroot()
        for vehicle in root.iter('vehicle'):
            for box_id in bremicker_boxes.keys():
                box = bremicker_boxes[box_id]
                for step in detector_steps:
                    vehicle_threshold = df_traffic.loc[step][box_id]
                    while vehicle_threshold >= 0:
                        edges = vehicle.find('route').get('edges').split()
                        if box['edge_1'] in edges or box['edge_2'] in edges:
                            departure_time = randrange(step - 600, step, 1) if step != 0 else 0
                            vehicle.set('depart', str(departure_time))
                            print('%s vehicles left, at %s seconds' % (vehicle_threshold, departure_time))
                        vehicle_threshold -= 1
        tree.write(self.route_filepath)

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

    def write_detector_add_file(self, box_ids):
        detectors = []
        print('writing detector file')
        for box_id in box_ids:
            print('for box id %s ' % str(box_id))
            lat = bremicker_boxes[box_id]['lat']
            lng = bremicker_boxes[box_id]['lng']
            xy_pos = self.net.convertLonLat2XY(lng, lat)

            best_lane = self.get_lane_at_pos(xy_pos)
            pos, d = best_lane.getClosestLanePosAndDist(xy_pos)
            new_xy = best_lane.getBoundingBox()

            neighbor_lane = self.get_lane_at_pos(new_xy)
            # neighbor_lane = best_lane.getNeigh()
            neighbor_pos, neighbor_d = neighbor_lane.getClosestLanePosAndDist(new_xy)

            detectors.append(
                sumolib.sensors.inductive_loop.InductiveLoop('det_%s_0' % box_id, best_lane.getID(), pos, (self.timesteps / 3600), self.det_out_filepath)
            )
            detectors.append(
                sumolib.sensors.inductive_loop.InductiveLoop('det_%s_1' % box_id, neighbor_lane.getID(), neighbor_pos, (self.timesteps / 3600), self.det_out_filepath)
            )
        sumolib.files.additional.write(self.add_filepath, detectors)

    def get_lane_at_pos(self, xy_pos):
        # look 10m around the position
        lanes = self.net.getNeighboringLanes(xy_pos[0], xy_pos[1], 10)
        # attention, result is unsorted
        print(lanes)
        best_lane = None
        ref_d = 9999.
        for lane, dist in lanes:
            if dist < ref_d:
                ref_d = dist
                best_lane = lane
        # pos, d = best_lane.getClosestLanePosAndDist(xy_pos)
        if best_lane is None:
            raise Exception('[SIMULATION PREPROCESSOR] lane next to position %s %s not found!' % (str(xy_pos[0]), str(xy_pos[1])))
        return best_lane

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
            # self.write_detector_add_file(list(bremicker_boxes.keys()))
        # elif not os.path.exists(self.cfg_filepath):
        #     self.write_sumocfg_file()
        else:
            print("[PreProcessor] weight, routes and trip file already exists. Starting SUMO anyway...")
        
        return self.cfg_filepath

    async def preprocess_single_simulation_input(self):
        print("[SUMO] Simulating with %s agents" % str(self.agents))
        if not os.path.exists(self.cfg_filepath) or \
                not os.path.exists(self.route_filepath) or \
                not os.path.exists(self.add_filepath) or \
                not os.path.exists(self.trip_filepath):
            self.write_sumocfg_file()
            self.write_detector_add_file([self.box_id])
            self.write_random_trips_and_routes()
        else:
            print("[PreProcessor] routes and trip file already exists. Starting SUMO anyway...")

        return self.cfg_filepath
