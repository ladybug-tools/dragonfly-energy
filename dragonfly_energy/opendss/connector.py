# coding=utf-8
"""Electrical connector in OpenDSS."""
from __future__ import division

from ._base import _GeometryBase
from .wire import Wire

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
        wires: A list of Wire objects representing the wire objects carried along
            the electrical connector.

    Properties:
        * identifier
        * display_name
        * geometry
        * wires
    """
    __slots__ = ('_wires',)

    def __init__(self, identifier, geometry, wires):
        """Initialize ElectricalConnector."""
        _GeometryBase.__init__(self, identifier)  # process the identifier
        assert isinstance(geometry, (LineSegment2D, Polyline2D)), 'Expected ' \
            'ladybug_geometry LineSegment2D or Polyline2D. Got {}'.format(type(geometry))
        self._geometry = geometry
        self.wires = wires

    @classmethod
    def from_dict(cls, data):
        """Initialize an ElectricalConnector from a dictionary.

        Args:
            data: A dictionary representation of an ElectricalConnector object.
        """
        # check the type of dictionary
        assert data['type'] == 'ElectricalConnector', 'Expected ElectricalConnector ' \
            'dictionary. Got {}.'.format(data['type'])
        wires = [Wire.from_dict(wire) for wire in data['wires']]
        geo = LineSegment2D.from_dict(data['geometry']) \
            if data['geometry']['type'] == 'LineSegment2D' \
            else Polyline2D.from_dict(data['geometry'])
        con = cls(data['identifier'], geo, wires)
        if 'display_name' in data and data['display_name'] is not None:
            con.display_name = data['display_name']
        return con

    @classmethod
    def from_dict_abridged(cls, data, wires):
        """Initialize an ElectricalConnector from an abridged dictionary.

        Args:
            data: A ElectricalConnectorAbridged dictionary.
            wires: A dictionary with identifiers of Wires as keys and Python
                Wire objects as values.
        """
        assert data['type'] == 'ElectricalConnectorAbridged', \
            'Expected ElectricalConnectorAbridged. Got {}.'.format(data['type'])
        try:
            wires = [wires[wire_id] for wire_id in data['wires']]
        except KeyError as e:
            raise ValueError('Failed to find "{}" in wires.'.format(e))
        geo = LineSegment2D.from_dict(data['geometry']) \
            if data['geometry']['type'] == 'LineSegment2D' \
            else Polyline2D.from_dict(data['geometry'])
        con = cls(data['identifier'], geo, wires)
        if 'display_name' in data and data['display_name'] is not None:
            con.display_name = data['display_name']
        return con

    @property
    def geometry(self):
        """Get a LineSegment2D or Polyline2D representing the electrical connector."""
        return self._geometry

    @property
    def wires(self):
        """Get or set the list of Wire objects carried along the electrical connector."""
        return self._wires

    @wires.setter
    def wires(self, values):
        try:
            if not isinstance(values, tuple):
                values = tuple(values)
        except TypeError:
            raise TypeError('Expected list or tuple for electrical connector wires. '
                            'Got {}'.format(type(values)))
        for wir in values:
            assert isinstance(wir, Wire), 'Expected Wire object' \
                ' for electrical connector wires. Got {}.'.format(type(wir))
            wir.lock()  # lock to avoid editing
        assert len(values) > 0, 'ElectricalConnector must possess at least one wire.'
        self._wires = values

    @property
    def wire_ids(self):
        """A list of wire identifiers in the electrical connector."""
        return [wire.identifier for wire in self._wires]

    def to_dict(self, abridged=False):
        """ElectricalConnector dictionary representation.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True),
                which only specifies the identifiers of wires. (Default: False).
        """
        base = {'type': 'ElectricalConnector'} if not \
            abridged else {'type': 'ElectricalConnectorAbridged'}
        base['identifier'] = self.identifier
        base['geometry'] = self.geometry.to_dict()
        base['wires'] = self.wire_ids if abridged else [w.to_dict() for w in self.wires]
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
                'total_length': self.geometry.length,
                'connector_type': 'Wire',
                'electrical_catalog_name': ''.join(self.wire_ids),
                'name': self.display_name
            },
            'geometry': {
                'type': 'LineString',
                'coordinates': coords
            }
        }

    def __copy__(self):
        new_con = ElectricalConnector(
            self.identifier, self.geometry, [wire for wire in self.wires])
        new_con._display_name = self._display_name
        return new_con

    def __len__(self):
        return len(self._wires)

    def __getitem__(self, key):
        return self._wires[key]

    def __iter__(self):
        return iter(self._wires)

    def __repr__(self):
        return 'ElectricalConnector: {}, [{} wires]'.format(
            self.display_name, len(self.wires))
