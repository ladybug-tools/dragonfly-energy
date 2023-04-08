# coding=utf-8
"""Thermal Loop of a District Energy System (DES)."""
import os
import uuid
import json

from ladybug_geometry.geometry2d import Point2D, LineSegment2D, Polyline2D, Polygon2D
from ladybug.location import Location
from honeybee.typing import valid_ep_string
from honeybee.units import conversion_factor_to_meters
from dragonfly.projection import meters_to_long_lat_factors, \
    origin_long_lat_from_location

from .ghe import GroundHeatExchanger
from .connector import ThermalConnector
from .junction import ThermalJunction


class GHEThermalLoop(object):
    """Represents an Ground Heat Exchanger Thermal Loop in a DES.

    This includes a GroundHeatExchanger and all thermal connectors needed
    to connect these objects to Dragonfly Buildings in a loop.

    Args:
        identifier: Text string for a unique thermal loop ID. Must contain only
            characters that are acceptable in OpenDSS. This will be used to
            identify the object across the exported geoJSON and OpenDSS files.
        ground_heat_exchanger: A GroundHeatExchanger object representing the field
            of boreholes that supplies the loop with thermal capacity.
        connectors: An array of ThermalConnector objects that are included
            within the thermal loop. In order for a given connector to be
            valid within the loop, each end of the connector must touch either
            another connector, a building footprint, or the ground_heat_exchanger. In
            order for the loop as a whole to be valid, the connectors must form a
            single continuous loop when passed through the buildings and the heat
            exchanger field.
        clockwise_flow: A boolean to note whether the direction of flow through the
            loop is clockwise (True) when viewed from above in the GeoJSON or it
            is counterclockwise (False). (Default: False).

    Properties:
        * identifier
        * display_name
        * ground_heat_exchanger
        * connectors
        * clockwise_flow
    """
    __slots__ = (
        '_identifier', '_display_name', '_ground_heat_exchanger', '_connectors',
        '_clockwise_flow')

    def __init__(self, identifier, ground_heat_exchanger, connectors,
                 clockwise_flow=False):
        """Initialize GHEThermalLoop."""
        self.identifier = identifier
        self._display_name = None
        self.ground_heat_exchanger = ground_heat_exchanger
        self.connectors = connectors
        self.clockwise_flow = clockwise_flow

    @classmethod
    def from_dict(cls, data):
        """Initialize an GHEThermalLoop from a dictionary.

        Args:
            data: A dictionary representation of an GHEThermalLoop object.
        """
        # check the type of dictionary
        assert data['type'] == 'GHEThermalLoop', 'Expected GHEThermalLoop ' \
            'dictionary. Got {}.'.format(data['type'])
        # re-serialize geometry objects
        ghe = GroundHeatExchanger.from_dict(data['ground_heat_exchanger'])
        conns = [ThermalConnector.from_dict(c) for c in data['connectors']]
        clock = data['clockwise_flow'] if 'clockwise_flow' in data else False
        loop = cls(data['identifier'], ghe, conns, clock)
        if 'display_name' in data and data['display_name'] is not None:
            loop.display_name = data['display_name']
        return loop

    @classmethod
    def from_geojson(
            cls, geojson_file_path, location=None, point=None, units='Meters',
            clockwise_flow=False):
        """Get an GHEThermalLoop from a dictionary as it appears in a GeoJSON.

        Args:
            geojson_file_path: Text for the full path to the geojson file to load
                as GHEThermalLoop.
            location: An optional ladybug location object with longitude and
                latitude data defining the origin of the geojson file. If None,
                an attempt will be made to sense the location from the project
                point in the GeoJSON (if it exists). If nothing is found, the
                origin is autocalcualted as the bottom-left corner of the bounding
                box of all building footprints in the geojson file. (Default: None).
            point: A ladybug_geometry Point2D for where the location object exists
                within the space of a scene. The coordinates of this point are
                expected to be in the units input. If None, an attempt will be
                made to sense the CAD coordinates from the GeoJSON if they
                exist. If not found, they will default to (0, 0).
            units: Text for the units system in which the model geometry
                exists. Default: 'Meters'. Choose from the following:

                * Meters
                * Millimeters
                * Feet
                * Inches
                * Centimeters

                Note that this method assumes the point coordinates are in the
                same units.
            clockwise_flow: A boolean to note whether the direction of flow through the
                loop is clockwise (True) when viewed from above in the GeoJSON or it
                is counterclockwise (False). (Default: False).
        """
        # parse the geoJSON into a dictionary
        with open(geojson_file_path, 'r') as fp:
            data = json.load(fp)

        # extract the CAD coordinates and location from the GeoJSON if they exist
        if 'project' in data:
            prd = data['project']
            if 'latitude' in prd and 'longitude' in prd and location is None:
                location = Location(latitude=prd['latitude'], longitude=prd['longitude'])
            if 'cad_coordinates' in prd and point is None:
                point = Point2D(*prd['cad_coordinates'])
        if point is None:  # just use the world origin if no point was found
            point = Point2D(0, 0)

        # Get the list of thermal connector and GHE data
        connector_data, ghe_data = [], None
        for obj_data in data['features']:
            if 'type' in obj_data['properties']:
                if obj_data['properties']['type'] == 'ThermalConnector':
                    connector_data.append(obj_data)
                elif obj_data['properties']['type'] == 'District System' and \
                        obj_data['properties']['district_system_type'] == \
                        'Ground Heat Exchanger':
                    ghe_data = obj_data

        # if model units is not Meters, convert non-meter user inputs to meters
        scale_to_meters = conversion_factor_to_meters(units)
        if units != 'Meters':
            point = point.scale(scale_to_meters)

        # Get long and lat in the geojson that correspond to the model origin (point).
        # If location is None, derive coordinates from the geojson geometry.
        if location is None:
            point_lon_lat = cls._bottom_left_coordinate_from_geojson(connector_data)
            location = Location(longitude=point_lon_lat[0], latitude=point_lon_lat[1])

        # The model point may not be at (0, 0), so shift the longitude and latitude to
        # get the equivalent point in longitude and latitude for (0, 0) in the model.
        origin_lon_lat = origin_long_lat_from_location(location, point)
        _convert_facs = meters_to_long_lat_factors(origin_lon_lat)
        convert_facs = 1 / _convert_facs[0], 1 / _convert_facs[1]

        # extract the connectors
        connectors = []
        for con_data in connector_data:
            con_obj = ThermalConnector.from_geojson_dict(
                con_data, origin_lon_lat, convert_facs)
            connectors.append(con_obj)
        # extract the substation
        ghe_field = GroundHeatExchanger.from_geojson_dict(
            ghe_data, origin_lon_lat, convert_facs)

        # create the loop and adjust for the units
        base_name = os.path.basename(geojson_file_path)
        loop_id = base_name.replace('.json', '').replace('.geojson', '')
        loop = cls(loop_id, ghe_field, connectors, clockwise_flow)
        if units != 'Meters':
            loop.convert_to_units(units)
        return loop

    @staticmethod
    def _bottom_left_coordinate_from_geojson(connector_data):
        """Calculate the bottom-left bounding box coordinate from geojson coordinates.

        Args:
            connector_data: a list of dictionaries containing geojson geometries that
                represent thermal connectors.

        Returns:
            The bottom-left most corner of the bounding box around the coordinates.
        """
        xs, ys = [], []
        for conn in connector_data:
            conn_coords = conn['geometry']['coordinates']
            if conn['geometry']['type'] == 'LineString':
                for pt in conn_coords:
                    xs.append(pt[0])
                    ys.append(pt[1])
        return min(xs), min(ys)

    @property
    def identifier(self):
        """Get or set the text string for unique object identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, identifier):
        self._identifier = valid_ep_string(identifier, 'identifier')

    @property
    def display_name(self):
        """Get or set a string for the object name without any character restrictions.

        If not set, this will be equal to the identifier.
        """
        if self._display_name is None:
            return self._identifier
        return self._display_name

    @display_name.setter
    def display_name(self, value):
        try:
            self._display_name = str(value)
        except UnicodeEncodeError:  # Python 2 machine lacking the character set
            self._display_name = value  # keep it as unicode

    @property
    def ground_heat_exchanger(self):
        """Get or set a GroundHeatExchanger object for the loop's ground heat exchanger.
        """
        return self._ground_heat_exchanger

    @ground_heat_exchanger.setter
    def ground_heat_exchanger(self, value):
        assert isinstance(value, GroundHeatExchanger), \
            'Expected GroundHeatExchanger for thermal loop. Got {}.'.format(type(value))
        self._ground_heat_exchanger = value

    @property
    def connectors(self):
        """Get or set the list of ThermalConnector objects within the loop."""
        return self._connectors

    @connectors.setter
    def connectors(self, values):
        try:
            if not isinstance(values, tuple):
                values = tuple(values)
        except TypeError:
            raise TypeError('Expected list or tuple for thermal loop connectors. '
                            'Got {}'.format(type(values)))
        for c in values:
            assert isinstance(c, ThermalConnector), 'Expected ThermalConnector ' \
                'object for thermal loop connectors. Got {}.'.format(type(c))
        assert len(values) > 0, 'ThermalLoop must possess at least one connector.'
        self._connectors = values

    @property
    def clockwise_flow(self):
        """Get or set a boolean for whether the flow through the loop is clockwise."""
        return self._clockwise_flow

    @clockwise_flow.setter
    def clockwise_flow(self, value):
        self._clockwise_flow = bool(value)

    def junctions(self, tolerance=0.01):
        """Get a list of ThermalJunction objects for the unique thermal loop junctions.

        The resulting ThermalJunction objects will be associated with the loop's
        GroundHeatExchanger if they are in contact with it (within the tolerance).
        However, they won't have any building_identifier associated with them.
        The assign_junction_buildings method on this object can be used
        to associate the junctions with an array of Dragonfly Buildings.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                faces at which they can be considered centered adjacent. (Default: 0.01,
                suitable for objects in meters).

        Returns:
             A tuple with two items.

            -   junctions - A list of lists of the unique ThermalJunction objects
                that exist across the loop.

            -   connector_junction_ids - A list of lists that align with the connectors
                in the loop. Each sub-list contains two string values for the junction
                IDs for each of the start and end of each of the connectors.
        """
        return self._junctions_from_connectors(self.connectors, tolerance)

    def loop_polygon(self, buildings, tolerance=0.01):
        """Get a Polygon2D for the single continuous loop formed by connectors.

        This method will raise an exception if the ThermalConnectors do not form
        a single continuous loop through the Buildings and the ground_heat_exchanger.
        The Polygon2D will have the correct clockwise ordering according to this
        object's clockwise_flow property.

        Args:
            buildings: An array of Dragonfly Building objects in the same units
                system as the GHEThermalLoop geometry.
            tolerance: The minimum difference between the coordinate values of two
                geometries at which they are considered co-located. (Default: 0.01,
                suitable for objects in meters).
        """
        # get the footprints of the Buildings in 2D space and the GHE field
        footprint_2d, bldg_ids = GHEThermalLoop._building_footprints(
            buildings, tolerance)
        footprint_2d.append(self.ground_heat_exchanger.geometry)
        bldg_ids.append('Ground Heat Exchanger')

        # determine which ThermalConnectors are linked to the buildings
        feat_dict = {}
        for bldg_poly, bldg_id in zip(footprint_2d, bldg_ids):
            for conn in self.connectors:
                c_p1, c_p2 = conn.geometry.p1, conn.geometry.p2
                p1_con = bldg_poly.is_point_on_edge(c_p1, tolerance)
                p2_con = bldg_poly.is_point_on_edge(c_p2, tolerance)
                if p1_con or p2_con:
                    rel_pt = c_p1 if p1_con else c_p2
                    try:  # assume that the first connection has been found
                        feat_dict[bldg_id].append(rel_pt)
                    except KeyError:  # this is the first connection
                        feat_dict[bldg_id] = [rel_pt]

        # create a list with all line segment geometry in the loop
        loop_segs = []
        for conn in self.connectors:
            if isinstance(conn.geometry, LineSegment2D):
                loop_segs.append(conn.geometry)
            else:  # assume that it is a PolyLine2D
                loop_segs.extend(conn.geometry.segments)
        for feat_id, f_pts in feat_dict.items():
            if len(f_pts) == 2:  # valid connection with clear supply and return
                loop_segs.append(LineSegment2D.from_end_points(f_pts[0], f_pts[1]))
            elif len(f_pts) < 2:  # only one connection; raise an error
                msg = 'Feature "{}" contains only a single connection to a ' \
                    'ThermalConnector and cannot be integrated into a valid ' \
                    'loop.'.format(feat_id)
                raise ValueError(msg)
            else:  # multiple connections; raise an error
                msg = 'Feature "{}" contains {} connections to ThermalConnectors and ' \
                    'cannot be integrated into a valid loop.'.format(feat_id, len(f_pts))
                raise ValueError(msg)

        # join all of the segments together into a single polygon and set the order
        loop_geos = Polyline2D.join_segments(loop_segs, tolerance)
        assert len(loop_geos) == 1, 'A total of {} different loops were found across ' \
            'all ThermalConnectors.\nOnly one loop is allowed.'.format(len(loop_geos))
        loop_geo = loop_geos[0]
        assert loop_geo.is_closed(tolerance), 'The ThermalConnectors form an ' \
            'open loop.\nThis loop must be closed in order to be valid.'
        loop_poly = loop_geo.to_polygon(tolerance)
        if loop_poly.is_clockwise is not self.clockwise_flow:
            loop_poly = loop_poly.reverse()
        return loop_poly

    def ordered_connectors(self, buildings, tolerance=0.01):
        """Get the ThermalConnectors of this GHEThermalLoop correctly ordered in a loop.

        The resulting connectors will not only be ordered correctly along the loop
        but the orientation of the connector geometries will be property coordinated
        with the clockwise_flow property on this object.

        This method will raise an exception if the ThermalConnectors do not form
        a single continuous loop through the Buildings and the ground_heat_exchanger.

        Args:
            buildings: An array of Dragonfly Building objects in the same units
                system as the GHEThermalLoop geometry.
            tolerance: The minimum difference between the coordinate values of two
                geometries at which they are considered co-located. (Default: 0.01,
                suitable for objects in meters).
        """
        # first get a Polygon2D for the continuous loop
        loop_poly = self.loop_polygon(buildings, tolerance)

        # loop through the polygon segments and find each matching thermal connector
        ord_conns, skip_count, tol = [], 0, tolerance
        for loop_seg in loop_poly.segments:
            if skip_count != 0:
                skip_count -= 1
                continue
            for conn in self.connectors:
                if isinstance(conn.geometry, LineSegment2D) and \
                        conn.geometry.is_equivalent(loop_seg, tol):
                    if not conn.geometry.p1.is_equivalent(loop_seg.p1, tol):
                        conn.reverse()
                    ord_conns.append(conn)
                    break
                elif isinstance(conn.geometry, Polyline2D) and \
                        (conn.geometry.p1.is_equivalent(loop_seg.p1, tol) or
                         conn.geometry.p2.is_equivalent(loop_seg.p1, tol)):
                    if not conn.geometry.p1.is_equivalent(loop_seg.p1, tol):
                        conn.reverse()
                    ord_conns.append(conn)
                    skip_count = len(conn.geometry.vertices) - 2
                    break
        return ord_conns

    def move(self, moving_vec):
        """Move this object along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the object.
        """
        self._ground_heat_exchanger.move(moving_vec)
        for connector in self.connectors:
            connector.move(moving_vec)

    def rotate_xy(self, angle, origin):
        """Rotate this object counterclockwise in the XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._ground_heat_exchanger.rotate_xy(angle, origin)
        for connector in self.connectors:
            connector.rotate_xy(angle, origin)

    def reflect(self, plane):
        """Reflect this object across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will be reflected.
        """
        self._ground_heat_exchanger.reflect(plane)
        for connector in self.connectors:
            connector.reflect(plane)

    def scale(self, factor, origin=None):
        """Scale this object by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        self._ground_heat_exchanger.scale(factor, origin)
        for connector in self.connectors:
            connector.scale(factor, origin)

    def convert_to_units(self, units='Meters', starting_units='Meters'):
        """Convert all of the geometry in this ThermalLoop to certain units.

        Args:
            units: Text for the units to which the Model geometry should be
                converted. (Default: Meters). Choose from the following:

                * Meters
                * Millimeters
                * Feet
                * Inches
                * Centimeters

            starting_units: The starting units system of the loop. (Default: Meters).
        """
        if starting_units != units:
            scale_fac1 = conversion_factor_to_meters(starting_units)
            scale_fac2 = conversion_factor_to_meters(units)
            scale_fac = scale_fac1 / scale_fac2
            self.scale(scale_fac)

    def to_dict(self):
        """GHEThermalLoop dictionary representation."""
        base = {'type': 'GHEThermalLoop'}
        base['identifier'] = self.identifier
        base['ground_heat_exchanger'] = self.ground_heat_exchanger.to_dict()
        base['connectors'] = [c.to_dict(True) for c in self.connectors]
        base['clockwise_flow'] = self.clockwise_flow
        if self._display_name is not None:
            base['display_name'] = self.display_name
        return base

    def to_geojson_dict(self, buildings, location, point=Point2D(0, 0), tolerance=0.01):
        """Get GHEThermalLoop dictionary as it appears in an URBANopt geoJSON.

        The resulting dictionary array can be directly appended to the "features"
        key of a base GeoJSON dict in order to represent the loop in the
        GeoJSON. Note that, in order to successfully simulate the DES, you will also
        have to write a system_parameter.json from this GHEThermalLoop using
        the to_des_param_dict method.

        Args:
            buildings: An array of Dragonfly Building objects in the same units
                system as the GHEThermalLoop geometry.
            location: A ladybug Location object possessing longitude and latitude data.
            point: A ladybug_geometry Point2D for where the location object exists
                within the space of a scene. The coordinates of this point are
                expected to be in the units of this Model. (Default: (0, 0)).
            tolerance: The minimum difference between the coordinate values of two
                geometries at which they are considered co-located. (Default: 0.01,
                suitable for objects in meters).
        """
        # get the conversion factors over to (longitude, latitude)
        origin_lon_lat = origin_long_lat_from_location(location, point)
        convert_facs = meters_to_long_lat_factors(origin_lon_lat)

        # translate ground heat exchanger into the GeoJSON features list
        features_list = []
        ghe = self.ground_heat_exchanger.to_geojson_dict(origin_lon_lat, convert_facs)
        features_list.append(ghe)

        # get the footprints of the Buildings in 2D space
        footprint_2d, bldg_ids = GHEThermalLoop._building_footprints(
            buildings, tolerance)
        all_feat = footprint_2d + [self.ground_heat_exchanger.geometry]
        feat_ids = bldg_ids + [self.ground_heat_exchanger.identifier]

        # order the connectors correctly on the loop and translate them to features
        ordered_conns = self.ordered_connectors(buildings, tolerance)
        junctions, connector_jct_ids = self._junctions_from_connectors(
            ordered_conns, tolerance)
        for conn, jct_ids in zip(self.connectors, connector_jct_ids):
            st_feat, end_feat, cp1, cp2 = None, None, conn.geometry.p1, conn.geometry.p2
            for f_poly, f_id in zip(all_feat, feat_ids):
                if f_poly.is_point_on_edge(cp1, tolerance):
                    st_feat = f_id
                elif f_poly.is_point_on_edge(cp2, tolerance):
                    end_feat = f_id
            conn_dict = conn.to_geojson_dict(
                jct_ids[0], jct_ids[1], origin_lon_lat, convert_facs, st_feat, end_feat)
            features_list.append(conn_dict)

        # translate junctions into the GeoJSON features list
        for jct in junctions:
            for bldg_poly, bldg_id in zip(footprint_2d, bldg_ids):
                if bldg_poly.is_point_on_edge(jct.geometry, tolerance):
                    jct.building_identifier = bldg_id
                    break
        for jct in junctions:
            features_list.append(jct.to_geojson_dict(origin_lon_lat, convert_facs))
        return features_list

    def to_des_param_dict(self, buildings, tolerance=0.01):
        """Get the DES System Parameter dictionary for the ThermalLoop.

        Args:
            buildings: An array of Dragonfly Building objects in the same units
                system as the GHEThermalLoop geometry.
            tolerance: The minimum difference between the coordinate values of two
                geometries at which they are considered co-located. (Default: 0.01,
                suitable for objects in meters).
        """
        # set up a dictionary to be updated with the params
        des_dict = {}

        # add the relevant buildings to the DES parameter dictionary
        footprint_2d, bldg_ids = GHEThermalLoop._building_footprints(
            buildings, tolerance)
        rel_bldg_ids = set()
        junctions, connector_jct_ids = self.junctions(tolerance)
        for jct in junctions:
            for bldg_poly, bldg_id in zip(footprint_2d, bldg_ids):
                if bldg_poly.is_point_on_edge(jct.geometry, tolerance):
                    rel_bldg_ids.add(bldg_id)
        bldg_array = []
        for bldg_id in rel_bldg_ids:
            b_dict = {
                'geojson_id': bldg_id,
                'load_model': 'time_series',
                'ets_model': 'Indirect Heating and Cooling'
            }
            bldg_array.append(b_dict)
        des_dict['buildings'] = bldg_array

        # TODO: Figure out if these system parameters have any meaning
        # add some dummy system parameters for now
        des_param = {
            'fourth_generation': {
                'central_cooling_plant_parameters': {
                    'heat_flow_nominal': 7999,
                    'cooling_tower_fan_power_nominal': 4999,
                    'mass_chw_flow_nominal': 9.9,
                    'chiller_water_flow_minimum': 9.9,
                    'mass_cw_flow_nominal': 9.9,
                    'chw_pump_head': 300000,
                    'cw_pump_head': 200000,
                    'pressure_drop_chw_nominal': 5999,
                    'pressure_drop_cw_nominal': 5999,
                    'pressure_drop_setpoint': 49999,
                    'temp_setpoint_chw': 6,
                    'pressure_drop_chw_valve_nominal': 5999,
                    'pressure_drop_cw_pum_nominal': 5999,
                    'temp_air_wb_nominal': 24.9,
                    'temp_cw_in_nominal': 34.9,
                    'cooling_tower_water_temperature_difference_nominal': 6.56,
                    'delta_temp_approach': 3.25,
                    'ratio_water_air_nominal': 0.6
                },
                'central_heating_plant_parameters': {
                    'heat_flow_nominal': 8001,
                    'mass_hhw_flow_nominal': 11,
                    'boiler_water_flow_minimum': 11,
                    'pressure_drop_hhw_nominal': 55001,
                    'pressure_drop_setpoint': 50000,
                    'temp_setpoint_hhw': 54,
                    'pressure_drop_hhw_valve_nominal': 6001,
                    'chp_installed': False
                }
            }
        }
        des_dict['district_system'] = des_param

        # add the ground loop parameters
        des_dict.update(self.ground_heat_exchanger.to_des_param_dict())
        return des_dict

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    @staticmethod
    def assign_junction_buildings(junctions, buildings, tolerance=0.01):
        """Assign building_identifiers to a list of junctions using dragonfly Buildings.

        Junctions will be assigned to a given Building if they are touching
        the footprint of that building in 2D space.

        Args:
            junctions: An array of ThermalJunction objects to be associated
                with Dragonfly Buildings.
            buildings: An array of Dragonfly Building objects in the same units
                system as the ThermalLoop geometry.
            tolerance: The minimum difference between the coordinate values of two
                geometries at which they are considered co-located. (Default: 0.01,
                suitable for objects in meters).
        """
        # get the footprints of the Buildings in 2D space
        footprint_2d, bldg_ids = GHEThermalLoop._building_footprints(
            buildings, tolerance)

        # loop through connectors and associate them with the Buildings
        for jct in junctions:
            for bldg_poly, bldg_id in zip(footprint_2d, bldg_ids):
                if bldg_poly.is_point_on_edge(jct.geometry, tolerance):
                    jct.building_identifier = bldg_id
                    break
        return junctions

    def _junctions_from_connectors(self, connectors, tolerance):
        """Get a list of ThermalJunction objects given a list of ThermalConnectors.
        """
        # loop through the connectors and find all unique junction objects
        junctions, connector_junction_ids = [], []
        for connector in connectors:
            verts = connector.geometry.vertices
            end_pts, jct_ids = (verts[0], verts[-1]), []
            for jct_pt in end_pts:
                for exist_jct in junctions:
                    if jct_pt.is_equivalent(exist_jct.geometry, tolerance):
                        jct_ids.append(exist_jct.identifier)
                        break
                else:  # we have found a new unique junction
                    new_jct_id = str(uuid.uuid4())
                    junctions.append(ThermalJunction(new_jct_id, jct_pt))
                    jct_ids.append(new_jct_id)
            connector_junction_ids.append(jct_ids)

        # loop through district system objects to determine adjacent junctions
        all_ds_objs = (self.ground_heat_exchanger,)
        for jct in junctions:
            for ds_obj in all_ds_objs:
                if ds_obj.geometry.is_point_on_edge(jct.geometry, tolerance):
                    jct.system_identifier = ds_obj.identifier
                    break
        return junctions, connector_junction_ids

    @staticmethod
    def _building_footprints(buildings, tolerance=0.01):
        """Get Polygon2Ds for each Dragonfly Building footprint."""
        # get the footprints of the Buildings in 2D space
        footprint_2d, bldg_ids = [], []
        for bldg in buildings:
            footprint = bldg.footprint(tolerance)
            for face3d in footprint:
                pts_2d = [Point2D(pt.x, pt.y) for pt in face3d.vertices]
                footprint_2d.append(Polygon2D(pts_2d))
                bldg_ids.append(bldg.identifier)
        return footprint_2d, bldg_ids

    def __copy__(self):
        new_loop = GHEThermalLoop(
            self.identifier, self.ground_heat_exchanger.duplicate(),
            tuple(conn.duplicate() for conn in self.connectors), self.clockwise_flow)
        new_loop._display_name = self._display_name
        return new_loop

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'GHEThermalLoop: {}'.format(self.display_name)
