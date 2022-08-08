# coding=utf-8
"""Road along which RNM will place electrical connectors."""
from __future__ import division

from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.polyline import Polyline2D
from dragonfly.projection import polygon_to_lon_lat

from ._base import _GeometryBase


class Road(_GeometryBase):
    """Represents a road along which RNM will place electrical connectors.

    Args:
        identifier: Text string for a unique road ID. Must contain only characters
            that are acceptable in RNM and OpenDSS. This will be used to
            identify the object across the exported geoJSON, RNM and OpenDSS files.
        geometry: A LineSegment2D or Polyline2D representing the geometry of the road.

    Properties:
        * identifier
        * display_name
        * geometry
    """
    __slots__ = ()

    def __init__(self, identifier, geometry):
        """Initialize Road."""
        _GeometryBase.__init__(self, identifier)  # process the identifier
        assert isinstance(geometry, (LineSegment2D, Polyline2D)), 'Expected ' \
            'ladybug_geometry LineSegment2D or Polyline2D. Got {}'.format(type(geometry))
        self._geometry = geometry

    @classmethod
    def from_dict(cls, data):
        """Initialize a Road from a dictionary.

        Args:
            data: A dictionary representation of a Road object.
        """
        # check the type of dictionary
        assert data['type'] == 'Road', 'Expected Road ' \
            'dictionary. Got {}.'.format(data['type'])
        geo = LineSegment2D.from_dict(data['geometry']) \
            if data['geometry']['type'] == 'LineSegment2D' \
            else Polyline2D.from_dict(data['geometry'])
        road = cls(data['identifier'], geo)
        if 'display_name' in data and data['display_name'] is not None:
            road.display_name = data['display_name']
        return road

    @property
    def geometry(self):
        """Get a LineSegment2D or Polyline2D representing the road geometry."""
        return self._geometry

    def to_dict(self):
        """Road dictionary representation."""
        base = {'type': 'Road'}
        base['identifier'] = self.identifier
        base['geometry'] = self.geometry.to_dict()
        if self._display_name is not None:
            base['display_name'] = self.display_name
        return base

    def to_geojson_dict(self, origin_lon_lat, conversion_factors):
        """Get Road dictionary as it appears in an URBANopt geoJSON.

        Args:
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
                'type': 'Road',
                'total_length': round(self.geometry.length, 1),
                'name': self.display_name
            },
            'geometry': {
                'type': 'LineString',
                'coordinates': coords
            }
        }

    def __copy__(self):
        new_con = Road(self.identifier, self.geometry)
        new_con._display_name = self._display_name
        return new_con

    def __repr__(self):
        return 'Road: {}'.format(self.display_name)
