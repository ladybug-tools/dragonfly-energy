# coding=utf-8
"""Electrical connector in OpenDSS."""
from __future__ import division

from ._base import _GeometryBase
from .powerline import PowerLine

from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.polyline import Polyline2D
from dragonfly.projection import polygon_to_lon_lat


class ElectricalConnector(_GeometryBase):
    """Represents an electrical connector carrying wires in OpenDSS.

    Args:
        identifier: Text string for a unique electrical connector ID. Must contain only
            characters that are acceptable in OpenDSS. This will be used to
            identify the object across the exported geoJSON and OpenDSS files.
        geometry: A LineSegment2D or Polyline2D representing the geometry of the
            electrical connector.
        power_line: A PowerLine object representing the wires carried along the
            electrical connector and their arrangement.

    Properties:
        * identifier
        * display_name
        * geometry
        * power_line
        * phase_count
        * nominal_voltage
    """
    __slots__ = ('_power_line',)

    def __init__(self, identifier, geometry, power_line):
        """Initialize ElectricalConnector."""
        _GeometryBase.__init__(self, identifier)  # process the identifier
        assert isinstance(geometry, (LineSegment2D, Polyline2D)), 'Expected ' \
            'ladybug_geometry LineSegment2D or Polyline2D. Got {}'.format(type(geometry))
        self._geometry = geometry
        self.power_line = power_line

    @classmethod
    def from_dict(cls, data):
        """Initialize an ElectricalConnector from a dictionary.

        Args:
            data: A dictionary representation of an ElectricalConnector object.
        """
        # check the type of dictionary
        assert data['type'] == 'ElectricalConnector', 'Expected ElectricalConnector ' \
            'dictionary. Got {}.'.format(data['type'])
        power_line = PowerLine.from_dict(data['power_line'])
        geo = LineSegment2D.from_dict(data['geometry']) \
            if data['geometry']['type'] == 'LineSegment2D' \
            else Polyline2D.from_dict(data['geometry'])
        con = cls(data['identifier'], geo, power_line)
        if 'display_name' in data and data['display_name'] is not None:
            con.display_name = data['display_name']
        return con

    @classmethod
    def from_dict_abridged(cls, data, power_lines):
        """Initialize an ElectricalConnector from an abridged dictionary.

        Args:
            data: A ElectricalConnectorAbridged dictionary.
            power_lines: A dictionary with identifiers of PowerLines as keys and Python
                PowerLine objects as values.
        """
        assert data['type'] == 'ElectricalConnectorAbridged', \
            'Expected ElectricalConnectorAbridged. Got {}.'.format(data['type'])
        try:
            power_line = power_lines[data['power_line']]
        except KeyError as e:
            raise ValueError('Failed to find "{}" in power lines.'.format(e))
        geo = LineSegment2D.from_dict(data['geometry']) \
            if data['geometry']['type'] == 'LineSegment2D' \
            else Polyline2D.from_dict(data['geometry'])
        con = cls(data['identifier'], geo, power_line)
        if 'display_name' in data and data['display_name'] is not None:
            con.display_name = data['display_name']
        return con

    @classmethod
    def from_rnm_geojson_dict(
            cls, data, origin_lon_lat, conversion_factors, power_lines):
        """Get an ElectricalConnector from a dictionary as it appears in an RNM GeoJSON.

        Args:
            data: A GeoJSON dictionary representation of an ElectricalConnector feature.
            origin_lon_lat: An array of two numbers in degrees. The first value
                represents the longitude of the scene origin in degrees (between -180
                and +180). The second value represents latitude of the scene origin
                in degrees (between -90 and +90). Note that the "scene origin" is the
                (0, 0) coordinate in the 2D space of the input polygon.
            conversion_factors: A tuple with two values used to translate between
                meters and longitude, latitude.
            power_lines: A dictionary with identifiers of PowerLines as keys and Python
                PowerLine objects as values.
        """
        geo = cls._geojson_coordinates_to_line2d(
            data['geometry']['coordinates'], origin_lon_lat, conversion_factors)
        try:
            power_line = power_lines[data['properties']['Equip']]
        except KeyError as e:
            raise ValueError('Failed to find "{}" in power lines.'.format(e))
        return cls(data['properties']['Code'], geo, power_line)

    @property
    def geometry(self):
        """Get a LineSegment2D or Polyline2D representing the electrical connector."""
        return self._geometry

    @property
    def power_line(self):
        """Get or set the PowerLine object carried along the electrical connector."""
        return self._power_line

    @power_line.setter
    def power_line(self, value):
        assert isinstance(value, PowerLine), 'Expected PowerLine object' \
            ' for electrical connector power_line. Got {}.'.format(type(value))
        value.lock()  # lock to avoid editing
        self._power_line = value

    @property
    def phase_count(self):
        """Get an integer for the number of phases this connector supports."""
        return self._power_line.phase_count

    @property
    def nominal_voltage(self):
        """Get an integer for the nominal voltage of this connector."""
        return self._power_line.nominal_voltage

    def to_dict(self, abridged=False):
        """ElectricalConnector dictionary representation.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True),
                which only specifies the identifier of the power line. (Default: False).
        """
        base = {'type': 'ElectricalConnector'} if not \
            abridged else {'type': 'ElectricalConnectorAbridged'}
        base['identifier'] = self.identifier
        base['geometry'] = self.geometry.to_dict()
        base['power_line'] = self.power_line.identifier if abridged \
            else self.power_line.to_dict()
        if self._display_name is not None:
            base['display_name'] = self.display_name
        return base

    def to_geojson_dict(self, start_id, end_id, origin_lon_lat, conversion_factors):
        """Get ElectricalConnector dictionary as it appears in an URBANopt geoJSON.

        Args:
            start_id: Identifier of the junction at the start of the wire.
            end_id: Identifier of the junction at the end of the wire.
            origin_lon_lat: An array of two numbers in degrees. The first value
                represents the longitude of the scene origin in degrees (between -180
                and +180). The second value represents latitude of the scene origin
                in degrees (between -90 and +90). Note that the "scene origin" is the
                (0, 0) coordinate in the 2D space of the input polygon.
            conversion_factors: A tuple with two values used to translate between
                meters and longitude, latitude.
        """
        if isinstance(self.geometry, LineSegment2D):
            pts = [(pt.x, pt.y) for pt in (self.geometry.p1, self.geometry.p2)]
        else:  # it's a polyline
            pts = [(pt.x, pt.y) for pt in self.geometry.vertices]
        coords = polygon_to_lon_lat(pts, origin_lon_lat, conversion_factors)
        return {
            'type': 'Feature',
            'properties': {
                'id': self.identifier,
                'type': 'ElectricalConnector',
                'startJunctionId': start_id,
                'endJunctionId': end_id,
                'total_length': round(self.geometry.length, 2),
                'connector_type': 'Wire',
                'electrical_catalog_name': self.power_line.identifier,
                'name': self.display_name
            },
            'geometry': {
                'type': 'LineString',
                'coordinates': coords
            }
        }

    def __copy__(self):
        new_con = ElectricalConnector(self.identifier, self.geometry, self.power_line)
        new_con._display_name = self._display_name
        return new_con

    def __repr__(self):
        return 'ElectricalConnector: {}, [{} wires]'.format(
            self.display_name, self.power_line.wire_count)
