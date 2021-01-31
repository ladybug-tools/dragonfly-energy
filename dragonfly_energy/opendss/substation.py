# coding=utf-8
"""Electrical substation in OpenDSS."""
from ._base import _GeometryBase

from ladybug_geometry.geometry2d.polygon import Polygon2D
from dragonfly.projection import polygon_to_lon_lat


class Substation(_GeometryBase):
    """Represents a substation in OpenDSS.

    Args:
        identifier: Text string for a unique electrical substation ID. Must contain only
            characters that are acceptable in OpenDSS. This will be used to
            identify the object across the exported geoJSON and OpenDSS files.
        geometry: A Polygon2D representing the geometry of the electrical substation.

    Properties:
        * identifier
        * display_name
        * geometry
    """
    __slots__ = ()

    def __init__(self, identifier, geometry):
        """Initialize Substation."""
        _GeometryBase.__init__(self, identifier)  # process the identifier
        assert isinstance(geometry, Polygon2D), 'Expected ladybug_geometry ' \
            'Polygon2D for Substation geometry. Got {}'.format(type(geometry))
        self._geometry = geometry

    @classmethod
    def from_dict(cls, data):
        """Initialize an Substation from a dictionary.

        Args:
            data: A dictionary representation of an Substation object.
        """
        # check the type of dictionary
        assert data['type'] == 'Substation', 'Expected Substation ' \
            'dictionary. Got {}.'.format(data['type'])
        geo = Polygon2D.from_dict(data['geometry'])
        trans = cls(data['identifier'], geo)
        if 'display_name' in data and data['display_name'] is not None:
            trans.display_name = data['display_name']
        return trans

    @property
    def geometry(self):
        """Get a Polygon2D representing the substation."""
        return self._geometry

    def to_dict(self):
        """Substation dictionary representation."""
        base = {'type': 'Substation'}
        base['identifier'] = self.identifier
        base['geometry'] = self.geometry.to_dict()
        if self._display_name is not None:
            base['display_name'] = self.display_name
        return base

    def to_geojson_dict(self, origin_lon_lat, conversion_factors):
        """Get Substation dictionary as it appears in an URBANopt geoJSON.

        Args:
            origin_lon_lat: An array of two numbers in degrees. The first value
                represents the longitude of the scene origin in degrees (between -180
                and +180). The second value represents latitude of the scene origin
                in degrees (between -90 and +90). Note that the "scene origin" is the
                (0, 0) coordinate in the 2D space of the input polygon.
            conversion_factors: A tuple with two values used to translate between
                meters and longitude, latitude.
        """
        pts = [(pt.x, pt.y) for pt in self.geometry.vertices]
        coords = [polygon_to_lon_lat(pts, origin_lon_lat, conversion_factors)]
        return {
            'type': 'Feature',
            'properties': {
                'id': self.identifier,
                'geometryType': 'Rectangle',
                'name': self.display_name,
                'type': 'District System',
                'footprint_area': self.geometry.area,
                'footprint_perimeter': self.geometry.perimeter,
                'district_system_type': 'Electrical Substation',
            },
            'geometry': {
                'type': 'Polygon',
                'coordinates': coords
            }
        }

    def __copy__(self):
        new_con = Substation(self.identifier, self.geometry)
        new_con._display_name = self._display_name
        return new_con

    def __repr__(self):
        return 'Substation: {}'.format(self.display_name)
