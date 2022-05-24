# coding=utf-8
"""Electrical network in OpenDSS."""
import uuid

from .substation import Substation
from .transformer import Transformer
from .connector import ElectricalConnector
from .junction import ElectricalJunction
from .transformerprop import TransformerProperties
from .wire import Wire

from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.polygon import Polygon2D
from honeybee.typing import valid_ep_string
from dragonfly.projection import meters_to_long_lat_factors, \
    origin_long_lat_from_location


class ElectricalNetwork(object):
    """Represents an electrical network in OpenDSS.

    This includes a substation, transformers, and all electrical connectors needed
    to connect these objects to Dragonfly Buildings.

    Args:
        identifier: Text string for a unique electrical network ID. Must contain only
            characters that are acceptable in OpenDSS. This will be used to
            identify the object across the exported geoJSON and OpenDSS files.
        substation: A Substation object representing the electrical substation
            supplying the network with electricity.
        transformers: An array of Transformer objects that are included within the
            electrical network. Generally, there should always be a transformer
            somewhere between the substation and a given building.
        connectors: An array of ElectricalConnector objects that are included
            within the electrical network. In order for a given connector to be
            valid within the network, each end of the connector must touch either
            another connector or a building footprint/transformer/substation. In
            order for the network as a whole to be valid, all Buildings and
            Transformers must be connected back to the Substation via connectors.

    Properties:
        * identifier
        * display_name
        * substation
        * transformers
        * connectors
        * transformer_properties
        * wires
    """
    __slots__ = ('_identifier', '_display_name', '_substation',
                 '_transformers', '_connectors')

    def __init__(self, identifier, substation, transformers, connectors):
        """Initialize ElectricalNetwork."""
        self.identifier = identifier
        self._display_name = None
        self.substation = substation
        self.transformers = transformers
        self.connectors = connectors

    @classmethod
    def from_dict(cls, data):
        """Initialize an ElectricalNetwork from a dictionary.

        Args:
            data: A dictionary representation of an ElectricalNetwork object.
        """
        # check the type of dictionary
        assert data['type'] == 'ElectricalNetwork', 'Expected ElectricalNetwork ' \
            'dictionary. Got {}.'.format(data['type'])
        # re-serialize transformer properties and wires
        t_props = {tp['identifier']: TransformerProperties.from_dict(tp)
                   for tp in data['transformer_properties']}
        wires = {w['identifier']: Wire.from_dict(w) for w in data['wires']}
        # re-serialize geometry objects
        substation = Substation.from_dict(data['substation'])
        transformers = [Transformer.from_dict_abridged(trans, t_props)
                        for trans in data['transformers']]
        conns = [ElectricalConnector.from_dict_abridged(c, wires)
                 for c in data['connectors']]
        net = cls(data['identifier'], substation, transformers, conns)
        if 'display_name' in data and data['display_name'] is not None:
            net.display_name = data['display_name']
        return net

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
    def substation(self):
        """Get or set a Substation object for the network's substation."""
        return self._substation

    @substation.setter
    def substation(self, value):
        assert isinstance(value, Substation), \
            'Expected Substation for electrical network. Got {}.'.format(type(value))
        self._substation = value

    @property
    def transformers(self):
        """Get or set the list of Transformer objects within the network."""
        return self._transformers

    @transformers.setter
    def transformers(self, values):
        try:
            if not isinstance(values, tuple):
                values = tuple(values)
        except TypeError:
            raise TypeError('Expected list or tuple for electrical network '
                            'transformers. Got {}'.format(type(values)))
        for t in values:
            assert isinstance(t, Transformer), 'Expected Transformer object' \
                ' for electrical network transformers. Got {}.'.format(type(t))
        assert len(values) > 0, 'ElectricalNetwork must have at least one transformer.'
        self._transformers = values

    @property
    def connectors(self):
        """Get or set the list of ElectricalConnector objects within the network."""
        return self._connectors

    @connectors.setter
    def connectors(self, values):
        try:
            if not isinstance(values, tuple):
                values = tuple(values)
        except TypeError:
            raise TypeError('Expected list or tuple for electrical network connectors. '
                            'Got {}'.format(type(values)))
        for c in values:
            assert isinstance(c, ElectricalConnector), 'Expected ElectricalConnector ' \
                'object for electrical network connectors. Got {}.'.format(type(c))
        assert len(values) > 0, 'ElectricalNetwork must possess at least one connector.'
        self._connectors = values

    @property
    def transformer_properties(self):
        """A list of all unique TransformerProperties in the network."""
        t_props = []
        for trans in self.transformers:
            if not self._instance_in_array(trans.properties, t_props):
                t_props.append(trans.properties)
        return list(set(t_props))  # catch duplicated/equivalent objects

    @property
    def wires(self):
        """A list of all unique Wires in the network."""
        wires = []
        for connector in self.connectors:
            for wire in connector.wires:
                if not self._instance_in_array(wire, wires):
                    wires.append(wire)
        return list(set(wires))  # catch duplicated/equivalent objects

    def junctions(self, tolerance=0.01):
        """Get a list of ElectricalJunction objects for the unique network junctions.

        The resulting ElectricalJunction objects will be associated with Transformers
        and Substations that they are in contact with across the network (within
        the tolerance). However, they won't have any building_identifier associated
        with them. The assign_junction_buildings method on this object can be used
        to associate the junctions with an array of Dragonfly Buildings.

        Args:
            tolerance: The minimum difference between the coordinate values of two
                faces at which they can be considered centered adjacent. (Default: 0.01,
                suitable for objects in meters).

        Returns:
             A tuple with two items.

            -   junctions - A list of lists of the unique ElectricalJunction objects
                that exist across the network.

            -   connector_junction_ids - A list of lists that align with the connectors
                in the network. Each sub-list contains two sting values for the junction
                IDs for each of the start and end of each of the connectors.
        """
        # loop through the connectors and find all unique junction objects
        junctions, connector_junction_ids = [], []
        for connector in self.connectors:
            verts = connector.geometry.vertices
            end_pts, jct_ids = (verts[0], verts[-1]), []
            for jct_pt in end_pts:
                for exist_jct in junctions:
                    if jct_pt.is_equivalent(exist_jct.geometry, tolerance):
                        jct_ids.append(exist_jct.identifier)
                        break
                else:  # we have found a new unique junction
                    new_jct_id = str(uuid.uuid4())
                    junctions.append(ElectricalJunction(new_jct_id, jct_pt))
                    jct_ids.append(new_jct_id)
            connector_junction_ids.append(jct_ids)

        # loop through connectors and associate them with Transformers or the Substation
        all_ds_objs = self.transformers + (self.substation,)
        for jct in junctions:
            for ds_obj in all_ds_objs:
                if ds_obj.geometry.is_point_on_edge(jct.geometry, tolerance):
                    jct.system_identifier = ds_obj.identifier
                    break
        return junctions, connector_junction_ids

    def move(self, moving_vec):
        """Move this object along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the object.
        """
        self._substation.move(moving_vec)
        for transformer in self.transformers:
            transformer.move(moving_vec)
        for connector in self.connectors:
            connector.move(moving_vec)

    def rotate_xy(self, angle, origin):
        """Rotate this object counterclockwise in the XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._substation.rotate_xy(angle, origin)
        for transformer in self.transformers:
            transformer.rotate_xy(angle, origin)
        for connector in self.connectors:
            connector.rotate_xy(angle, origin)

    def reflect(self, plane):
        """Reflect this object across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will be reflected.
        """
        self._substation.reflect(plane)
        for transformer in self.transformers:
            transformer.reflect(plane)
        for connector in self.connectors:
            connector.reflect(plane)

    def scale(self, factor, origin=None):
        """Scale this object by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        self._substation.scale(factor, origin)
        for transformer in self.transformers:
            transformer.scale(factor, origin)
        for connector in self.connectors:
            connector.scale(factor, origin)

    def to_dict(self):
        """ElectricalNetwork dictionary representation."""
        base = {'type': 'ElectricalNetwork'}
        base['identifier'] = self.identifier
        base['substation'] = self.substation.to_dict()
        base['transformers'] = [trans.to_dict(True) for trans in self.transformers]
        base['connectors'] = [c.to_dict(True) for c in self.connectors]
        base['transformer_properties'] = \
            [tp.to_dict() for tp in self.transformer_properties]
        base['wires'] = [w.to_dict() for w in self.wires]
        if self._display_name is not None:
            base['display_name'] = self.display_name
        return base

    def to_geojson_dict(self, buildings, location, point=Point2D(0, 0), tolerance=0.01):
        """Get ElectricalNetwork dictionary as it appears in an URBANopt geoJSON.

        The resulting dictionary array can be directly appended to the "features"
        key of a base geoJSON dict in order to represent the network in the
        geoJSON. Note that, in order to successfully run OpenDSS, you will also
        have to write an electrical_database.json from this ElectricalNetwork using
        the to_electrical_database_dict method.

        Args:
            buildings: An array of Dragonfly Building objects in the same units
                system as the ElectricalNetwork geometry.
            location: A ladybug Location object possessing longitude and latitude data.
            point: A ladybug_geometry Point2D for where the location object exists
                within the space of a scene. The coordinates of this point are
                expected to be in the units of this Model. (Default: (0, 0)).
            tolerance: The minimum difference between the coordinate values of two
                faces at which they can be considered centered adjacent. (Default: 0.01,
                suitable for objects in meters).
        """
        # get the conversion factors over to (longitude, latitude)
        origin_lon_lat = origin_long_lat_from_location(location, point)
        convert_facs = meters_to_long_lat_factors(origin_lon_lat)

        # translate substation and transformers into the geoJSON features list
        features_list = [self.substation.to_geojson_dict(origin_lon_lat, convert_facs)]
        for trans in self.transformers:
            features_list.append(trans.to_geojson_dict(origin_lon_lat, convert_facs))

        # translate connectors and junctions into the geoJSON features list
        junctions, connector_jct_ids = self.junctions(tolerance)
        for conn, jct_ids in zip(self.connectors, connector_jct_ids):
            conn_dict = conn.to_geojson_dict(
                jct_ids[0], jct_ids[1], origin_lon_lat, convert_facs)
            features_list.append(conn_dict)
        final_junctions = self.assign_junction_buildings(junctions, buildings, tolerance)
        for jct in final_junctions:
            features_list.append(jct.to_geojson_dict(origin_lon_lat, convert_facs))
        return features_list

    def to_electrical_database_dict(self):
        """Get ElectricalNetwork as it should appear in the electrical_database.json."""
        base = {}
        base['transformer_properties'] = \
            [tp.to_electrical_database_dict() for tp in self.transformer_properties]
        base['wires'] = [wire.to_electrical_database_dict() for wire in self.wires]
        base['capacitor_properties'] = [{
            'nameclass': 'Capacitor--150KVAR',
            'kvar': 150,
            'resistance': 0.1,
            'phases': ['A', 'B', 'C'],
            'control_type': 'Voltage',
            'connection': 'Wye-Wye'
        }]
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    @staticmethod
    def assign_junction_buildings(junctions, buildings, tolerance=0.01):
        """Assign building_identifiers to a list of junctions using dragonfly Buildings.

        Junctions will be assigned to a given Building if they are touching
        the footprint of that building in 2D space.

        Args:
            junctions: An array of ElectricalJunction objects to be associated
                with Dragonfly Buildings.
            buildings: An array of Dragonfly Building objects in the same units
                system as the ElectricalNetwork geometry.
            tolerance: The minimum difference between the coordinate values of two
                faces at which they can be considered centered adjacent. (Default: 0.01,
                suitable for objects in meters).
        """
        # get the footprints of the Buildings in 2D space
        footprint_2d, bldg_ids = [], []
        for bldg in buildings:
            footprint = bldg.footprint(tolerance)
            for face3d in footprint:
                pts_2d = [Point2D(pt.x, pt.y) for pt in face3d.vertices]
                footprint_2d.append(Polygon2D(pts_2d))
                bldg_ids.append(bldg.identifier)

        # loop through connectors and associate them with the Buildings
        for jct in junctions:
            for bldg_poly, bldg_id in zip(footprint_2d, bldg_ids):
                if bldg_poly.is_point_on_edge(jct.geometry, tolerance):
                    jct.building_identifier = bldg_id
                    break
        return junctions

    @staticmethod
    def _instance_in_array(object_instance, object_array):
        """Check if a specific object instance is already in an array.

        This can be much faster than `if object_instance in object_array`
        when you expect to be testing a lot of the same instance of an object for
        inclusion in an array since the builtin method uses an == operator to
        test inclusion.
        """
        for val in object_array:
            if val is object_instance:
                return True
        return False

    def __copy__(self):
        new_net = ElectricalNetwork(
            self.identifier, self.substation.duplicate(),
            tuple(trans.duplicate() for trans in self.transformers),
            tuple(conn.duplicate() for conn in self.connectors))
        new_net._display_name = self._display_name
        return new_net

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'ElectricalNetwork: {}'.format(self.display_name)
