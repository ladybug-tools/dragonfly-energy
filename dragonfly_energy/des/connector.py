# coding=utf-8
"""Thermal connector in a District Energy System."""
from __future__ import division

from .._base import _GeometryBase

from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.polyline import Polyline2D
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
            'total_length': round(self.geometry.length, 2)
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
