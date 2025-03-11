# coding=utf-8
"""Thermal connector in a District Energy System."""
from __future__ import division

from .._base import _GeometryBase

from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.polyline import Polyline2D
from honeybee.typing import float_positive, float_in_range
from dragonfly.projection import polygon_to_lon_lat


class ThermalConnector(_GeometryBase):
    """Represents a thermal connector carrying hot, chilled or ambient water in a DES.

    Args:
        identifier: Text string for a unique thermal connector ID. Must contain only
            characters that are acceptable in a DES. This will be used to
            identify the object across the exported geoJSON and DES files.
        geometry: A LineSegment2D or Polyline2D representing the geometry of the
            thermal connector.

    Properties:
        * identifier
        * display_name
        * geometry
    """
    __slots__ = ()

    def __init__(self, identifier, geometry):
        """Initialize ThermalConnector."""
        _GeometryBase.__init__(self, identifier)  # process the identifier
        assert isinstance(geometry, (LineSegment2D, Polyline2D)), 'Expected ' \
            'ladybug_geometry LineSegment2D or Polyline2D. Got {}'.format(type(geometry))
        self._geometry = geometry

    @classmethod
    def from_dict(cls, data):
        """Initialize an ThermalConnector from a dictionary.

        Args:
            data: A dictionary representation of an ThermalConnector object.
        """
        # check the type of dictionary
        assert data['type'] == 'ThermalConnector', 'Expected ThermalConnector ' \
            'dictionary. Got {}.'.format(data['type'])
        geo = LineSegment2D.from_dict(data['geometry']) \
            if data['geometry']['type'] == 'LineSegment2D' \
            else Polyline2D.from_dict(data['geometry'])
        con = cls(data['identifier'], geo)
        if 'display_name' in data and data['display_name'] is not None:
            con.display_name = data['display_name']
        return con

    @classmethod
    def from_dict_abridged(cls, data):
        """Initialize an ThermalConnector from an abridged dictionary.

        Args:
            data: A ThermalConnector dictionary.
        """
        return cls.from_dict(data)

    @classmethod
    def from_geojson_dict(
            cls, data, origin_lon_lat, conversion_factors):
        """Get a ThermalConnector from a dictionary as it appears in a GeoJSON.

        Args:
            data: A GeoJSON dictionary representation of an ThermalConnector feature.
            origin_lon_lat: An array of two numbers in degrees. The first value
                represents the longitude of the scene origin in degrees (between -180
                and +180). The second value represents latitude of the scene origin
                in degrees (between -90 and +90). Note that the "scene origin" is the
                (0, 0) coordinate in the 2D space of the input polygon.
            conversion_factors: A tuple with two values used to translate between
                meters and longitude, latitude.
        """
        geo = cls._geojson_coordinates_to_line2d(
            data['geometry']['coordinates'], origin_lon_lat, conversion_factors)
        return cls(data['properties']['id'], geo)

    @property
    def geometry(self):
        """Get a LineSegment2D or Polyline2D representing the thermal connector."""
        return self._geometry

    def reverse(self):
        """Reverse the direction of this object's geometry.

        This is useful when trying to orient the connector to the direction
        of flow within a larger loop.
        """
        self._geometry = self._geometry.flip() \
            if isinstance(self._geometry, LineSegment2D) else self._geometry.reverse()

    def to_dict(self):
        """ThermalConnector dictionary representation."""
        base = {'type': 'ThermalConnector'}
        base['identifier'] = self.identifier
        base['geometry'] = self.geometry.to_dict()
        if self._display_name is not None:
            base['display_name'] = self.display_name
        return base

    def to_geojson_dict(self, start_id, end_id, origin_lon_lat, conversion_factors,
                        start_feature_id=None, end_feature_id=None):
        """Get ThermalConnector dictionary as it appears in an URBANopt geoJSON.

        Args:
            start_id: Identifier of the junction at the start of the pipe.
            end_id: Identifier of the junction at the end of the pipe.
            origin_lon_lat: An array of two numbers in degrees. The first value
                represents the longitude of the scene origin in degrees (between -180
                and +180). The second value represents latitude of the scene origin
                in degrees (between -90 and +90). Note that the "scene origin" is the
                (0, 0) coordinate in the 2D space of the input polygon.
            conversion_factors: A tuple with two values used to translate between
                meters and longitude, latitude.
            start_feature_id: Optional identifier for a feature (Building or GHE field)
                at the start of the pipe.
            end_feature_id: Optional identifier for a feature (Building or GHE field)
                at the end of the pipe.
        """
        # translate the geometry coordinates to latitude and longitude
        if isinstance(self.geometry, LineSegment2D):
            pts = [(pt.x, pt.y) for pt in (self.geometry.p1, self.geometry.p2)]
        else:  # it's a polyline
            pts = [(pt.x, pt.y) for pt in self.geometry.vertices]
        coords = polygon_to_lon_lat(pts, origin_lon_lat, conversion_factors)
        # assign all of the properties to the connector
        conn_props = {
            'id': self.identifier,
            'type': 'ThermalConnector',
            'name': self.display_name,
            'startJunctionId': start_id,
            'endJunctionId': end_id,
            'total_length': round(self.geometry.length, 2),
            'connector_type': 'OnePipe',
            'fluid_temperature_type': 'Ambient',
            'flow_direction': 'Unspecified'

        }
        if start_feature_id is not None:
            conn_props['startFeatureId'] = start_feature_id
        if end_feature_id is not None:
            conn_props['endFeatureId'] = end_feature_id
        # return the full dictionary
        return {
            'type': 'Feature',
            'properties': conn_props,
            'geometry': {
                'type': 'LineString',
                'coordinates': coords
            }
        }

    def __copy__(self):
        new_con = ThermalConnector(self.identifier, self.geometry)
        new_con._display_name = self._display_name
        return new_con

    def __repr__(self):
        return 'ThermalConnector: {}'.format(self.display_name)


class HorizontalPipeParameter(object):
    """Represents the properties of horizontal pipes contained within ThermalConnectors.

    Args:
        buried_depth: The buried depth of the pipes in meters. (Default: 1.5)
        diameter_ratio: A number for the ratio of pipe outer diameter to pipe
            wall thickness. (Default: 11).
        pressure_drop_per_meter: A number for the pressure drop in pascals per
            meter of pipe. (Default: 300).
        insulation_conductivity: A positive number for the conductivity of the pipe
            insulation material in W/m-K. If no insulation exists, this value
            should be a virtual insulation layer of soil since this value must
            be greater than zero. (Default: 3.0).
        insulation_thickness: A positive number for the thickness of pipe insulation
            in meters. If no insulation exists, this value should be a virtual
            insulation layer of soil since this value must be greater than
            zero. (Default: 0.2)
        heat_capacity: A number for the volumetric heat capacity of the pipe wall
            material in J/m3-K. (Default: 2,139,000).
        roughness: A number for the linear dimension of bumps on the pipe surface
            in meters. (Default: 1e-06)

    Properties:
        * buried_depth
        * diameter_ratio
        * pressure_drop_per_meter
        * insulation_conductivity
        * insulation_thickness
        * heat_capacity
        * roughness
    """
    __slots__ = ('_buried_depth', '_diameter_ratio', '_pressure_drop_per_meter',
                 '_insulation_conductivity', '_insulation_thickness',
                 '_heat_capacity', '_roughness')

    def __init__(
            self, buried_depth=1.5, diameter_ratio=11, pressure_drop_per_meter=300,
            insulation_conductivity=3.0, insulation_thickness=0.2,
            heat_capacity=2139000, roughness=1e-06):
        """Initialize HorizontalPipeParameter."""
        self.buried_depth = buried_depth
        self.diameter_ratio = diameter_ratio
        self.pressure_drop_per_meter = pressure_drop_per_meter
        self.insulation_conductivity = insulation_conductivity
        self.insulation_thickness = insulation_thickness
        self.heat_capacity = heat_capacity
        self.roughness = roughness

    @classmethod
    def from_dict(cls, data):
        """Create a HorizontalPipeParameter object from a dictionary

        Args:
            data: A dictionary representation of an HorizontalPipeParameter object
                in the format below.

        .. code-block:: python

            {
            'type': 'HorizontalPipeParameter',
            'buried_depth': 2.0,  # float for buried depth in meters
            'diameter_ratio': 11,  # float for diameter ratio
            'pressure_drop_per_meter': 250, # float for pressure drop in Pa/m
            'insulation_conductivity': 0.6,  # float in W/m2-K
            'insulation_thickness': 0.3,  # float for thickness in meters
            'heat_capacity': 1542000,  # float in J/m3-K
            'roughness': 1e-06  # float for the dimension of the surface bumps in meters
            }
        """
        bur_d = data['buried_depth'] if 'buried_depth' in data else 1.5
        d_ratio = data['diameter_ratio'] if 'diameter_ratio' in data else 11
        pd = data['pressure_drop_per_meter'] \
            if 'pressure_drop_per_meter' in data else 300
        cond = data['insulation_conductivity'] \
            if 'insulation_conductivity' in data else 3.0
        thick = data['insulation_thickness'] \
            if 'insulation_thickness' in data else 0.2
        cap = data['heat_capacity'] if 'heat_capacity' in data else 2139000
        rough = data['roughness'] if 'roughness' in data else 1e-06
        return cls(bur_d, d_ratio, pd, cond, thick, cap, rough)

    @property
    def buried_depth(self):
        """Get or set a number for the buried depth of the pipes in meters."""
        return self._buried_depth

    @buried_depth.setter
    def buried_depth(self, value):
        self._buried_depth = float_positive(value, 'pipe buried depth')

    @property
    def diameter_ratio(self):
        """Get or set a number for the ratio of pipe outer diameter to pipe wall thickness.
        """
        return self._diameter_ratio

    @diameter_ratio.setter
    def diameter_ratio(self, value):
        self._diameter_ratio = float_in_range(value, 11, 17, 'pipe diameter ratio')

    @property
    def pressure_drop_per_meter(self):
        """Get or set a number for the pressure drop in pascals per meter of pipe."""
        return self._pressure_drop_per_meter

    @pressure_drop_per_meter.setter
    def pressure_drop_per_meter(self, value):
        self._pressure_drop_per_meter = \
            float_positive(value, 'pipe pressure drop per meter')

    @property
    def insulation_conductivity(self):
        """Get or set a number for the conductivity of the insulation material in W/m-K.
        """
        return self._insulation_conductivity

    @insulation_conductivity.setter
    def insulation_conductivity(self, value):
        self._insulation_conductivity = \
            float_positive(value, 'pipe insulation conductivity')
        assert self._insulation_conductivity != 0, \
            'Insulation conductivity cannot be zero.'

    @property
    def insulation_thickness(self):
        """Get or set a number for the thickness of the insulation material in meters.
        """
        return self._insulation_thickness

    @insulation_thickness.setter
    def insulation_thickness(self, value):
        self._insulation_thickness = \
            float_positive(value, 'pipe insulation thickness')
        assert self._insulation_thickness != 0, 'Insulation thickness cannot be zero.'

    @property
    def heat_capacity(self):
        """Get or set a number for the volumetric heat capacity of the pipe in J/m3-K."""
        return self._heat_capacity

    @heat_capacity.setter
    def heat_capacity(self, value):
        self._heat_capacity = float_positive(value, 'pipe heat capacity')

    @property
    def roughness(self):
        """Get or set a number for the dimension of the pipe surface bumps in meters."""
        return self._roughness

    @roughness.setter
    def roughness(self, value):
        self._roughness = float_positive(value, 'pipe roughness')

    def to_dict(self):
        """Get HorizontalPipeParameter dictionary."""
        base = {'type': 'HorizontalPipeParameter'}
        base['buried_depth'] = self.buried_depth
        base['diameter_ratio'] = self.diameter_ratio
        base['pressure_drop_per_meter'] = self.pressure_drop_per_meter
        base['insulation_conductivity'] = self.insulation_conductivity
        base['insulation_thickness'] = self.insulation_thickness
        base['heat_capacity'] = self.heat_capacity
        base['roughness'] = self.roughness
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return HorizontalPipeParameter(
            self.buried_depth, self.diameter_ratio, self.pressure_drop_per_meter,
            self.insulation_conductivity, self.insulation_thickness,
            self.heat_capacity, self.roughness)

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent HorizontalPipeParameter."""
        return 'HorizontalPipeParameter: [pressure drop: {} Pa/m]'.format(
            self.pressure_drop_per_meter)
