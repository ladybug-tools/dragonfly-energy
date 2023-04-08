# coding=utf-8
"""Thermal junction in a District Energy System (DES)."""
from __future__ import division

from .._base import _GeometryBase

from ladybug_geometry.geometry2d.pointvector import Point2D
from honeybee.typing import valid_ep_string
from dragonfly.projection import polygon_to_lon_lat


class ThermalJunction(_GeometryBase):
    """Represents an thermal junction connecting two objects in a DES.

    Args:
        identifier: Text string for a unique thermal junction ID. Must contain only
            characters that are acceptable in a DED. This will be used to
            identify the object across the exported geoJSON and DES files.
        geometry: A LineSegment2D or Polyline2D representing the geometry of the
            thermal junction.
        system_identifier: An optional text string for the identifier of a district
            system object associated with the junction. District system objects
            include Ground Heat Exchangers. (Default: None).
        building_identifier: An optional text string for the identifier of a Building
            object associated with the junction. (Default: None).

    Properties:
        * identifier
        * display_name
        * geometry
        * system_identifier
        * building_identifier
    """
    __slots__ = ('_system_identifier', '_building_identifier')

    def __init__(self, identifier, geometry, system_identifier=None,
                 building_identifier=None):
        """Initialize ThermalJunction."""
        _GeometryBase.__init__(self, identifier)  # process the identifier
        assert isinstance(geometry, Point2D), 'Expected ladybug_geometry ' \
            'Point2D for ThermalJunction. Got {}'.format(type(geometry))
        self._geometry = geometry
        self.system_identifier = system_identifier
        self.building_identifier = building_identifier

    @property
    def geometry(self):
        """Get a Point2D representing the ThermalJunction."""
        return self._geometry

    @property
    def system_identifier(self):
        """Get or set a text string for the ID of a Transformer or Substation."""
        return self._system_identifier

    @system_identifier.setter
    def system_identifier(self, value):
        self._system_identifier = valid_ep_string(value, 'system_identifier') \
            if value is not None else None

    @property
    def building_identifier(self):
        """Get or set a text string for the ID of a dragonfly Building."""
        return self._building_identifier

    @building_identifier.setter
    def building_identifier(self, value):
        self._building_identifier = valid_ep_string(value, 'building_identifier') \
            if value is not None else None

    def to_geojson_dict(self, origin_lon_lat, conversion_factors):
        """Get an ThermalJunction dictionary as it appears in an URBANopt geoJSON.

        Args:
            origin_lon_lat: An array of two numbers in degrees. The first value
                represents the longitude of the scene origin in degrees (between -180
                and +180). The second value represents latitude of the scene origin
                in degrees (between -90 and +90). Note that the "scene origin" is the
                (0, 0) coordinate in the 2D space of the input polygon.
            conversion_factors: A tuple with two values used to translate between
                meters and longitude, latitude.
        """
        pt = (self.geometry.x, self.geometry.y)
        coord = polygon_to_lon_lat([pt], origin_lon_lat, conversion_factors)[0]
        geo_dict = {
            'type': 'Feature',
            'properties': {
                'id': self.identifier,
                'type': 'ThermalJunction'
            },
            'geometry': {
                'type': 'Point',
                'coordinates': coord
            }
        }
        if self._system_identifier is not None:
            geo_dict['properties']['DSId'] = self._system_identifier
        if self._building_identifier is not None:
            geo_dict['properties']['buildingId'] = self._building_identifier
        return geo_dict

    def __copy__(self):
        new_jct = ThermalJunction(
            self.identifier, self.geometry, self._system_identifier,
            self._building_identifier)
        new_jct._display_name = self._display_name
        return new_jct

    def __repr__(self):
        return 'ThermalJunction: {}'.format(self.display_name)
