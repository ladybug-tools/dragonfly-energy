# coding=utf-8
"""Thermal Loop of a District Energy System (DES)."""
import os
import uuid
import json

from ladybug_geometry.geometry2d import Point2D, LineSegment2D, Polyline2D, Polygon2D
from ladybug.location import Location
from ladybug.datacollection import HourlyContinuousCollection
from honeybee.typing import valid_ep_string, float_in_range
from honeybee.units import conversion_factor_to_meters
from dragonfly.projection import meters_to_long_lat_factors, \
    origin_long_lat_from_location

from .ghe import GroundHeatExchanger, SoilParameter, FluidParameter, \
    PipeParameter, BoreholeParameter, GHEDesignParameter
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
        ground_heat_exchangers: An array of GroundHeatExchanger objects representing
            the fields of boreholes that supply the loop with thermal capacity.
        connectors: An array of ThermalConnector objects that are included
            within the thermal loop. In order for a given connector to be
            valid within the loop, each end of the connector must touch either
            another connector, a building footprint, or the ground_heat_exchangers. In
            order for the loop as a whole to be valid, the connectors must form a
            single continuous loop when passed through the buildings and the heat
            exchanger field.
        clockwise_flow: A boolean to note whether the direction of flow through the
            loop is clockwise (True) when viewed from above in the GeoJSON or it
            is counterclockwise (False). (Default: False).
        soil_parameters: Optional SoilParameter object to specify the properties
            of the soil in which the loop is operating. If None, default
            values will be used. (Default: None).
        fluid_parameters: Optional FluidParameter object to specify the properties
            of the fluid that is circulating through the loop. If None, default
            values will be used. (Default: None).
        pipe_parameters: Optional PipeParameter object to specify the properties
            of the ground-heat-exchanging pipes used across the loop. If None,
            default values will be used. (Default: None).
        borehole_parameters: Optional BoreholeParameter object to specify the
            properties of the boreholes used across the loop. If None,
            default values will be used. (Default: None).
        design_parameters: Optional GHEDesignParameter object to specify the
            design constraints across the loop. If None, default values
            will be used. (Default: None).

    Properties:
        * identifier
        * display_name
        * ground_heat_exchangers
        * connectors
        * clockwise_flow
        * soil_parameters
        * fluid_parameters
        * pipe_parameters
        * borehole_parameters
        * design_parameters
    """
    __slots__ = (
        '_identifier', '_display_name', '_ground_heat_exchangers', '_connectors',
        '_clockwise_flow', '_soil_parameters', '_fluid_parameters', '_pipe_parameters',
        '_borehole_parameters', '_design_parameters')

    def __init__(self, identifier, ground_heat_exchangers, connectors,
                 clockwise_flow=False, soil_parameters=None, fluid_parameters=None,
                 pipe_parameters=None, borehole_parameters=None, design_parameters=None):
        """Initialize GHEThermalLoop."""
        self.identifier = identifier
        self._display_name = None
        self.ground_heat_exchangers = ground_heat_exchangers
        self.connectors = connectors
        self.clockwise_flow = clockwise_flow
        self.soil_parameters = soil_parameters
        self.fluid_parameters = fluid_parameters
        self.pipe_parameters = pipe_parameters
        self.borehole_parameters = borehole_parameters
        self.design_parameters = design_parameters

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
        ghe = [GroundHeatExchanger.from_dict(g) for g in data['ground_heat_exchangers']]
        conns = [ThermalConnector.from_dict(c) for c in data['connectors']]
        clock = data['clockwise_flow'] if 'clockwise_flow' in data else False
        soil = SoilParameter.from_dict(data['soil_parameters']) \
            if 'soil_parameters' in data else None
        fluid = FluidParameter.from_dict(data['fluid_parameters']) \
            if 'fluid_parameters' in data else None
        pipe = PipeParameter.from_dict(data['pipe_parameters']) \
            if 'pipe_parameters' in data else None
        bore = BoreholeParameter.from_dict(data['borehole_parameters']) \
            if 'borehole_parameters' in data else None
        des = GHEDesignParameter.from_dict(data['design_parameters']) \
            if 'design_parameters' in data else None
        loop = cls(data['identifier'], ghe, conns, clock, soil, fluid, pipe, bore, des)
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
        connector_data, ghe_data = [], []
        for obj_data in data['features']:
            if 'type' in obj_data['properties']:
                if obj_data['properties']['type'] == 'ThermalConnector':
                    connector_data.append(obj_data)
                elif obj_data['properties']['type'] == 'District System' and \
                        obj_data['properties']['district_system_type'] == \
                        'Ground Heat Exchanger':
                    ghe_data.append(obj_data)

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
    def ground_heat_exchangers(self):
        """Get or set a tuple of GroundHeatExchanger objects for the loop's GHEs.
        """
        return self._ground_heat_exchangers

    @ground_heat_exchangers.setter
    def ground_heat_exchangers(self, values):
        try:
            if not isinstance(values, tuple):
                values = tuple(values)
        except TypeError:
            raise TypeError(
                'Expected list or tuple for thermal loop ground_heat_exchangers. '
                'Got {}'.format(type(values)))
        for g in values:
            assert isinstance(g, GroundHeatExchanger), 'Expected GroundHeatExchanger ' \
                'object for thermal loop ground_heat_exchangers. Got {}.'.format(type(g))
        assert len(values) > 0, 'ThermalLoop must possess at least one GHE.'
        self._ground_heat_exchangers = values

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

    @property
    def soil_parameters(self):
        """Get or set a SoilParameter object for the heat exchanger field."""
        return self._soil_parameters

    @soil_parameters.setter
    def soil_parameters(self, value):
        if value is None:
            value = SoilParameter()
        assert isinstance(value, SoilParameter), \
            'Expected SoilParameter object' \
            ' for GroundHeatExchanger. Got {}.'.format(type(value))
        self._soil_parameters = value

    @property
    def fluid_parameters(self):
        """Get or set a FluidParameter object for the heat exchanger field."""
        return self._fluid_parameters

    @fluid_parameters.setter
    def fluid_parameters(self, value):
        if value is None:
            value = FluidParameter()
        assert isinstance(value, FluidParameter), \
            'Expected FluidParameter object' \
            ' for GroundHeatExchanger. Got {}.'.format(type(value))
        self._fluid_parameters = value

    @property
    def pipe_parameters(self):
        """Get or set a PipeParameter object for the heat exchanger field."""
        return self._pipe_parameters

    @pipe_parameters.setter
    def pipe_parameters(self, value):
        if value is None:
            value = PipeParameter()
        assert isinstance(value, PipeParameter), \
            'Expected PipeParameter object' \
            ' for GroundHeatExchanger. Got {}.'.format(type(value))
        self._pipe_parameters = value

    @property
    def borehole_parameters(self):
        """Get or set a BoreholeParameter object for the heat exchanger field."""
        return self._borehole_parameters

    @borehole_parameters.setter
    def borehole_parameters(self, value):
        if value is None:
            value = BoreholeParameter()
        assert isinstance(value, BoreholeParameter), \
            'Expected BoreholeParameter object' \
            ' for GroundHeatExchanger. Got {}.'.format(type(value))
        self._borehole_parameters = value

    @property
    def design_parameters(self):
        """Get or set a GHEDesignParameter object for the heat exchanger field."""
        return self._design_parameters

    @design_parameters.setter
    def design_parameters(self, value):
        if value is None:
            value = GHEDesignParameter()
        assert isinstance(value, GHEDesignParameter), \
            'Expected GHEDesignParameter object' \
            ' for GroundHeatExchanger. Got {}.'.format(type(value))
        self._design_parameters = value

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
        a single continuous loop through the Buildings and the ground_heat_exchangers.
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
        for ghe in self.ground_heat_exchangers:
            footprint_2d.append(ghe.geometry)
            bldg_ids.append(ghe.identifier)

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
        a single continuous loop through the Buildings and the ground_heat_exchangers.

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
                    skip_count = len(conn.geometry.vertices) - 1
                    break
        return ord_conns

    def move(self, moving_vec):
        """Move this object along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the object.
        """
        for ghe in self.ground_heat_exchangers:
            ghe.move(moving_vec)
        for connector in self.connectors:
            connector.move(moving_vec)

    def rotate_xy(self, angle, origin):
        """Rotate this object counterclockwise in the XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        for ghe in self.ground_heat_exchangers:
            ghe.rotate_xy(angle, origin)
        for connector in self.connectors:
            connector.rotate_xy(angle, origin)

    def reflect(self, plane):
        """Reflect this object across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will be reflected.
        """
        for ghe in self.ground_heat_exchangers:
            ghe.reflect(plane)
        for connector in self.connectors:
            connector.reflect(plane)

    def scale(self, factor, origin=None):
        """Scale this object by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        for ghe in self.ground_heat_exchangers:
            ghe.scale(factor, origin)
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
        base['ground_heat_exchangers'] = \
            [g.to_dict() for g in self.ground_heat_exchangers]
        base['connectors'] = [c.to_dict() for c in self.connectors]
        base['clockwise_flow'] = self.clockwise_flow
        base['soil_parameters'] = self.soil_parameters.to_dict()
        base['fluid_parameters'] = self.fluid_parameters.to_dict()
        base['pipe_parameters'] = self.pipe_parameters.to_dict()
        base['borehole_parameters'] = self.borehole_parameters.to_dict()
        base['design_parameters'] = self.design_parameters.to_dict()
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
            buildings: An array of Dragonfly Building objects that are along
                the GHEThermalLoop. Buildings that do not have their footprint
                touching the loop's ThermalConnectors are automatically excluded
                in the result.
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

        # translate ground heat exchangers into the GeoJSON features list
        features_list = []
        for ghe in self.ground_heat_exchangers:
            features_list.append(ghe.to_geojson_dict(origin_lon_lat, convert_facs))

        # get the footprints of the Buildings in 2D space
        footprint_2d, bldg_ids = GHEThermalLoop._building_footprints(
            buildings, tolerance)
        all_feat = footprint_2d + [ghe.geometry for ghe in self.ground_heat_exchangers]
        feat_ids = bldg_ids + [ghe.identifier for ghe in self.ground_heat_exchangers]

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
        for i, jct in enumerate(junctions):
            jct_dict = jct.to_geojson_dict(origin_lon_lat, convert_facs)
            if i == 0:
                jct_dict['properties']['is_ghe_start_loop'] = True
            features_list.append(jct_dict)
        return features_list

    def to_des_param_dict(self, buildings, tolerance=0.01):
        """Get the DES System Parameter dictionary for the ThermalLoop.

        Args:
            buildings: An array of Dragonfly Building objects that are along
                the GHEThermalLoop. Buildings that do not have their footprint
                touching the loop's ThermalConnectors are automatically excluded
                in the result.
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
        junctions, _ = self.junctions(tolerance)
        for jct in junctions:
            for bldg_poly, bldg_id in zip(footprint_2d, bldg_ids):
                if bldg_poly.is_point_on_edge(jct.geometry, tolerance):
                    rel_bldg_ids.add(bldg_id)
        bldg_array = []
        for bldg_id in rel_bldg_ids:
            b_dict = {
                'geojson_id': bldg_id,
                'load_model': 'time_series',
                'load_model_parameters': {
                    'time_series': {
                        'filepath': 'To be populated',
                        'delta_temp_air_cooling': 10,
                        'delta_temp_air_heating': 18,
                        'has_liquid_cooling': True,
                        'has_liquid_heating': True,
                        'has_electric_cooling': False,
                        'has_electric_heating': False,
                        'max_electrical_load': 0,
                        'temp_chw_return': 12,
                        'temp_chw_supply': 7,
                        'temp_hw_return': 35,
                        'temp_hw_supply': 40,
                        'temp_setpoint_cooling': 24,
                        'temp_setpoint_heating': 20
                    }
                },
                'ets_model': 'Fifth Gen Heat Pump',
                'fifth_gen_ets_parameters': {
                    'supply_water_temperature_building': 15,
                    'chilled_water_supply_temp': 5,
                    'hot_water_supply_temp': 50,
                    'cop_heat_pump_heating': 2.5,
                    'cop_heat_pump_cooling': 3.5,
                    'pump_flow_rate': 0.01,
                    'pump_design_head': 150000,
                    'ets_pump_flow_rate': 0.0005,
                    'ets_pump_head': 10000,
                    'fan_design_flow_rate': 0.25,
                    'fan_design_head': 150
                }
            }
            bldg_array.append(b_dict)
        des_dict['buildings'] = bldg_array

        # add the ground loop parameters
        des_param = {
            'fifth_generation': {
                'ghe_parameters': self.to_ghe_param_dict(tolerance)
            }
        }
        des_dict['district_system'] = des_param
        return des_dict

    def to_ghe_param_dict(self, tolerance=0.01):
        """Get the GroundHeatExchanger as it appears in a System Parameter dictionary.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                geometries at which they are considered co-located. (Default: 0.01,
                suitable for objects in meters).
        """
        # compute the geometric constraints of the borehole fields
        geo_pars = []
        for ghe in self.ground_heat_exchangers:
            ghe_geo = ghe.geometry
            max_dim = max((ghe_geo.max.x - ghe_geo.min.x, ghe_geo.max.y - ghe_geo.min.y))
            ang_tol = tolerance / max_dim
            if ghe_geo.is_rectangle(ang_tol):
                ghe_dims = (ghe_geo.segments[0].length, ghe_geo.segments[1].length)
            else:
                rect_geo = ghe_geo.rectangular_approximation()
                ghe_dims = (rect_geo.segments[0].length, rect_geo.segments[1].length)
            geo_par = {
                'ghe_id': ghe.identifier,
                'ghe_geometric_params': {
                    'length_of_ghe': max(ghe_dims),
                    'width_of_ghe': min(ghe_dims)
                },
                'borehole': {
                    'buried_depth': self.borehole_parameters.buried_depth,
                    'diameter': self.borehole_parameters.diameter
                },
                'ground_loads': []
            }
            geo_pars.append(geo_par)
        # handle autocalculated soil temperatures
        u_temp = self.soil_parameters.undisturbed_temperature \
            if self.soil_parameters._undisturbed_temperature is not None \
            else 'Autocalculate'
        # return a dictionary with all of the information
        return {
            'fluid': {
                'fluid_name': self.fluid_parameters.fluid_type,
                'concentration_percent': self.fluid_parameters.concentration,
                'temperature': self.fluid_parameters.temperature
            },
            'grout': {
                'conductivity': self.soil_parameters.grout_conductivity,
                'rho_cp': self.soil_parameters.grout_heat_capacity,
            },
            'soil': {
                'conductivity': self.soil_parameters.conductivity,
                'rho_cp': self.soil_parameters.heat_capacity,
                'undisturbed_temp': u_temp
            },
            'pipe': {
                'inner_diameter': self.pipe_parameters.inner_diameter,
                'outer_diameter': self.pipe_parameters.outer_diameter,
                'shank_spacing': self.pipe_parameters.shank_spacing,
                'roughness': self.pipe_parameters.roughness,
                'conductivity': self.pipe_parameters.conductivity,
                'rho_cp': self.pipe_parameters.heat_capacity,
                'arrangement': self.pipe_parameters.arrangement.lower()
            },
            'simulation': {
                'num_months': self.design_parameters.month_count
            },
            'geometric_constraints': {
                'b_min': self.borehole_parameters.min_spacing,
                'b_max': self.borehole_parameters.max_spacing,
                'max_height': self.borehole_parameters.max_depth,
                'min_height': self.borehole_parameters.min_depth,
                'method': 'rectangle'
            },
            'design': {
                'method': 'AREAPROPORTIONAL',
                'flow_rate': self.design_parameters.flow_rate,
                'flow_type': self.design_parameters.flow_type.lower(),
                'max_eft': self.design_parameters.max_eft,
                'min_eft': self.design_parameters.min_eft
            },
            'ghe_specific_params': geo_pars
        }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    @staticmethod
    def ghe_designer_dict(
        thermal_load, site_geometry, soil_parameters=None, fluid_parameters=None,
        pipe_parameters=None, borehole_parameters=None, design_parameters=None,
        tolerance=0.01):
        """Get a dictionary following the schema of the input JSON for GHEDesigner.

        This includes many of the same parameters that are used to size ground
        heat exchangers in an URBANopt DES system but it requires the input of
        hourly thermal loads.
        
        The dictionary returned by this method can be written to a JSON and
        passed directly to the GHEDesigner CLI in order to receive sizing
        information for the GHE and a G-function that can be used to meet
        the input load in a building energy simulation.

        Args:
            thermal_load: An annual data collection of hourly thermal loads on
                the ground in Watts. These are the heat extraction and heat rejection
                loads directly on the ground heat exchanger and should already
                account for factors like additional heat added or removed by the
                heat pump compressors. Positive values indicate heat extraction
                from the ground and negative values indicate heat rejection to
                the ground.
            site_geometry: A list of horizontal Face3D representing the footprint
                of the site to be populated with boreholes. These Face3D can
                have holes in them and these holes will be excluded from
                borehole placement. Note that it is expected that this geometry's
                dimensions are in meters and, if they are not, then it should
                be scaled before input to this method.
            soil_parameters: Optional SoilParameter object to specify the properties
                of the soil in which the loop is operating. If None, default
                values will be used. (Default: None).
            fluid_parameters: Optional FluidParameter object to specify the properties
                of the fluid that is circulating through the loop. If None, default
                values will be used. (Default: None).
            pipe_parameters: Optional PipeParameter object to specify the properties
                of the ground-heat-exchanging pipes used across the loop. If None,
                default values will be used. (Default: None).
            borehole_parameters: Optional BoreholeParameter object to specify the
                properties of the boreholes used across the loop. If None,
                default values will be used. (Default: None).
            design_parameters: Optional GHEDesignParameter object to specify the
                design constraints across the loop. If None, default values
                will be used. (Default: None).
            tolerance: The minimum difference between the coordinate values of two
                geometries at which they are considered co-located. (Default: 0.01,
                suitable for objects in meters).
        """
        # check that the inputs are what we expect
        assert isinstance(thermal_load, HourlyContinuousCollection), \
            'Expected hourly continuous data collection for thermal_load. ' \
            'Got {}'.format(type(thermal_load))
        period = thermal_load.header.analysis_period
        assert period.is_annual and period.timestep == 1, 'Hourly thermal load ' \
            'is not annual. Analysis period is: {}.'.format(period)
        assert thermal_load.header.unit == 'W', 'Expected load data collection to be in Watts. ' \
            'Got {}.'.format(thermal_load.header.unit)

        # process the input geometry into the format needed for GHEDesigner
        site_boundaries, site_holes = [], []
        for face in site_geometry:
            bnd_poly = Polygon2D([Point2D(pt.x, pt.y) for pt in face.boundary])
            bnd_poly = bnd_poly.remove_colinear_vertices(tolerance)
            if bnd_poly.is_clockwise:
                bnd_poly = bnd_poly.reverse()
            site_boundaries.append([[pt.x, pt.y] for pt in bnd_poly])
            if face.has_holes:
                for hole in face.holes:
                    hole_poly = Polygon2D([Point2D(pt.x, pt.y) for pt in hole])
                    hole_poly = hole_poly.remove_colinear_vertices(tolerance)
                    if hole_poly.is_clockwise:
                        hole_poly = hole_poly.reverse()
                    site_holes.append([[pt.x, pt.y] for pt in hole_poly])

        # set defaults if any of the inputs are unspecified
        soil = soil_parameters if soil_parameters is not None else SoilParameter()
        fluid = fluid_parameters if fluid_parameters is not None else FluidParameter()
        pipe = pipe_parameters if pipe_parameters is not None else PipeParameter()
        borehole = borehole_parameters if borehole_parameters is not None \
            else BoreholeParameter()
        design = design_parameters if pipe_parameters is not None \
            else GHEDesignParameter()
        u_temp = 18.3 if soil._undisturbed_temperature is None \
            else soil.undisturbed_temperature

        # return a dictionary with all of the inputs
        return {
            'fluid': {
                'fluid_name': fluid.fluid_type,
                'concentration_percent': fluid.concentration,
                'temperature': fluid.temperature
            },
            'grout': {
                'conductivity': soil.grout_conductivity,
                'rho_cp': soil.grout_heat_capacity
            },
            'soil': {
                'conductivity': soil.conductivity,
                'rho_cp': soil.heat_capacity,
                'undisturbed_temp': u_temp
            },
            'pipe': {
                'inner_diameter': pipe.inner_diameter,
                'outer_diameter': pipe.outer_diameter,
                'shank_spacing': pipe.shank_spacing,
                'roughness': pipe.roughness,
                'conductivity': pipe.conductivity,
                'rho_cp': pipe.heat_capacity,
                'arrangement': pipe.arrangement.upper()
            },
                'borehole': {
                'buried_depth': borehole.buried_depth,
                'diameter': borehole.diameter
            },
            'simulation': {
                'num_months': design.month_count
            },
            'geometric_constraints': {
                'b_min': borehole.min_spacing,
                'b_max_x': borehole.max_spacing,
                'b_max_y': borehole.max_spacing,
                'max_height': borehole.max_depth,
                'min_height': borehole.min_depth,
                'property_boundary': site_boundaries,
                'no_go_boundaries': site_holes,
                'method': 'BIRECTANGLECONSTRAINED'
            },
            'design': {
                'flow_rate': design.flow_rate,
                'flow_type': 'BOREHOLE',
                'max_eft': design.max_eft,
                'min_eft': design.min_eft
            },
            'loads': {
                'ground_loads': thermal_load.values
            }
        }

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
        for jct in junctions:
            for ds_obj in self.ground_heat_exchangers:
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
            self.identifier,
            tuple(ghe.duplicate() for ghe in self.ground_heat_exchangers),
            tuple(conn.duplicate() for conn in self.connectors), self.clockwise_flow,
            self.soil_parameters.duplicate(), self.fluid_parameters.duplicate(),
            self.pipe_parameters.duplicate(), self.borehole_parameters.duplicate())
        new_loop._display_name = self._display_name
        return new_loop

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'GHEThermalLoop: {}'.format(self.display_name)


class FourthGenThermalLoop(object):
    """Represents a Fourth Generation Heating/Cooling Thermal Loop in a DES.

    Args:
        identifier: Text string for a unique thermal loop ID. Must contain only
            characters that are acceptable in OpenDSS. This will be used to
            identify the object across the exported geoJSON and OpenDSS files.
        chilled_water_setpoint: A number for the temperature of chilled water
            in the DES in degrees C. (Default: 6).
        hot_water_setpoint: A number for the temperature of hot water in the DES
            in degrees C. (Default: 54).

    Properties:
        * identifier
        * display_name
        * chilled_water_setpoint
        * hot_water_setpoint
    """
    __slots__ = (
        '_identifier', '_display_name', '_chilled_water_setpoint', '_hot_water_setpoint')

    def __init__(self, identifier, chilled_water_setpoint=6, hot_water_setpoint=54):
        """Initialize GHEThermalLoop."""
        self.identifier = identifier
        self._display_name = None
        self.chilled_water_setpoint = chilled_water_setpoint
        self.hot_water_setpoint = hot_water_setpoint

    @classmethod
    def from_dict(cls, data):
        """Initialize an FourthGenThermalLoop from a dictionary.

        Args:
            data: A dictionary representation of an FourthGenThermalLoop object.
        """
        # check the type of dictionary
        assert data['type'] == 'FourthGenThermalLoop', 'Expected FourthGenThermalLoop ' \
            'dictionary. Got {}.'.format(data['type'])
        cwt = data['chilled_water_setpoint'] if 'chilled_water_setpoint' in data \
            and data['chilled_water_setpoint'] is not None else 6
        hwt = data['hot_water_setpoint'] if 'hot_water_setpoint' in data \
            and data['hot_water_setpoint'] is not None else 54
        loop = cls(data['identifier'], cwt, hwt)
        if 'display_name' in data and data['display_name'] is not None:
            loop.display_name = data['display_name']
        return loop

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
    def chilled_water_setpoint(self):
        """Get or set a number for the chilled water setpoint in degrees C."""
        return self._chilled_water_setpoint

    @chilled_water_setpoint.setter
    def chilled_water_setpoint(self, value):
        self._chilled_water_setpoint = \
            float_in_range(value, 0, 20, 'chilled water setpoint')

    @property
    def hot_water_setpoint(self):
        """Get or set a number for the hot water setpoint in degrees C."""
        return self._hot_water_setpoint

    @hot_water_setpoint.setter
    def hot_water_setpoint(self, value):
        self._hot_water_setpoint = \
            float_in_range(value, 24, 100, 'hot water setpoint')

    def to_dict(self):
        """FourthGenThermalLoop dictionary representation."""
        base = {'type': 'FourthGenThermalLoop'}
        base['identifier'] = self.identifier
        base['chilled_water_setpoint'] = self.chilled_water_setpoint
        base['hot_water_setpoint'] = self.hot_water_setpoint
        if self._display_name is not None:
            base['display_name'] = self.display_name
        return base

    def to_des_param_dict(self, buildings, tolerance=0.01):
        """Get the DES System Parameter dictionary for the ThermalLoop.

        Args:
            buildings: An array of Dragonfly Building objects that are along the
                FourthGenThermalLoop. Buildings that do not have their footprint
                touching the loop's ThermalConnectors are automatically excluded
                in the result.
            tolerance: The minimum difference between the coordinate values of two
                geometries at which they are considered co-located. (Default: 0.01,
                suitable for objects in meters).
        """
        # set up a dictionary to be updated with the params
        des_dict = {}
        # add the relevant buildings to the DES parameter dictionary
        bldg_array = []
        for bldg in buildings:
            b_dict = {
                'geojson_id': bldg.identifier,
                'load_model': 'time_series',
                'load_model_parameters': {
                    'time_series': {
                        'filepath': 'To be populated',
                        'delta_temp_air_cooling': 10,
                        'delta_temp_air_heating': 18,
                        'has_liquid_cooling': True,
                        'has_liquid_heating': True,
                        'has_electric_cooling': False,
                        'has_electric_heating': False,
                        'max_electrical_load': 0,
                        'temp_chw_return': 12,
                        'temp_chw_supply': 7,
                        'temp_hw_return': 35,
                        'temp_hw_supply': 40,
                        'temp_setpoint_cooling': 24,
                        'temp_setpoint_heating': 20
                    }
                },
                'ets_model': 'Indirect Heating and Cooling',
                'ets_indirect_parameters': {
                    'heat_flow_nominal': 8000,
                    'heat_exchanger_efficiency': 0.8,
                    'nominal_mass_flow_district': 0,
                    'nominal_mass_flow_building': 0,
                    'valve_pressure_drop': 6000,
                    'heat_exchanger_secondary_pressure_drop': 500,
                    'heat_exchanger_primary_pressure_drop': 500,
                    'cooling_supply_water_temperature_building': 7,
                    'heating_supply_water_temperature_building': 50,
                    'delta_temp_chw_building': 5,
                    'delta_temp_chw_district': 8,
                    'delta_temp_hw_building': 15,
                    'delta_temp_hw_district': 20,
                    'cooling_controller_y_max': 1,
                    'cooling_controller_y_min': 0,
                    'heating_controller_y_max': 1,
                    'heating_controller_y_min': 0
                }
            }
            bldg_array.append(b_dict)
        des_dict['buildings'] = bldg_array

        # add the ground loop parameters
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
                    'temp_setpoint_chw': self.chilled_water_setpoint,
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
                    'temp_setpoint_hhw': self.hot_water_setpoint,
                    'pressure_drop_hhw_valve_nominal': 6001,
                    'chp_installed': False
                }
            }
        }
        des_dict['district_system'] = des_param
        return des_dict

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_loop = FourthGenThermalLoop(
            self.identifier, self.chilled_water_setpoint, self.hot_water_setpoint)
        new_loop._display_name = self._display_name
        return new_loop

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'FourthGenThermalLoop: {}'.format(self.display_name)
