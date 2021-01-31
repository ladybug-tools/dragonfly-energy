# coding=utf-8
"""Electrical transformer in OpenDSS."""
from __future__ import division

from ._base import _GeometryBase
from .transformerprop import TransformerProperties

from ladybug_geometry.geometry2d.polygon import Polygon2D
from dragonfly.projection import polygon_to_lon_lat


class Transformer(_GeometryBase):
    """Represents a transformer in OpenDSS.

    Args:
        identifier: Text string for a unique electrical transformer ID. Must contain only
            characters that are acceptable in OpenDSS. This will be used to
            identify the object across the exported geoJSON and OpenDSS files.
        geometry: A Polygon2D representing the geometry of the electrical transformer.
        properties: A TransformerProperties object representing the properties of
            the electrical transformer.

    Properties:
        * identifier
        * display_name
        * geometry
        * properties
    """
    __slots__ = ('_properties',)

    def __init__(self, identifier, geometry, properties):
        """Initialize Transformer."""
        _GeometryBase.__init__(self, identifier)  # process the identifier
        assert isinstance(geometry, Polygon2D), 'Expected ladybug_geometry ' \
            'Polygon2D for Transformer geometry. Got {}'.format(type(geometry))
        self._geometry = geometry
        self.properties = properties

    @classmethod
    def from_dict(cls, data, abridged=False):
        """Initialize an Transformer from a dictionary.

        Args:
            data: A dictionary representation of an Transformer object.
        """
        # check the type of dictionary
        assert data['type'] == 'Transformer', 'Expected Transformer ' \
            'dictionary. Got {}.'.format(data['type'])
        props = TransformerProperties.from_dict(data['properties'])
        geo = Polygon2D.from_dict(data['geometry'])
        trans = cls(data['identifier'], geo, props)
        if 'display_name' in data and data['display_name'] is not None:
            trans.display_name = data['display_name']
        return trans

    @property
    def geometry(self):
        """Get a Polygon2D representing the transformer."""
        return self._geometry

    @property
    def properties(self):
        """Get or set a TransformerProperties object for the transformer."""
        return self._properties

    @properties.setter
    def properties(self, value):
        assert isinstance(value, TransformerProperties), \
            'Expected TransformerProperties object' \
            ' for transformer properties. Got {}.'.format(type(value))
        value.lock()
        self._properties = value

    def to_dict(self, abridged=False):
        """Transformer dictionary representation.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True),
                which only specifies the identifiers of properties. (Default: False).
        """
        base = {'type': 'Transformer'} if not \
            abridged else {'type': 'TransformerAbridged'}
        base['identifier'] = self.identifier
        base['geometry'] = self.geometry.to_dict()
        base['properties'] = self.properties.to_dict()
        if self._display_name is not None:
            base['display_name'] = self.display_name
        return base

    def to_geojson_dict(self, origin_lon_lat, conversion_factors):
        """Get Transformer dictionary as it appears in an URBANopt geoJSON.

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
                'district_system_type': 'Transformer',
                'equipment': [
                    self.properties.identifer
                ]
            },
            'geometry': {
                'type': 'Polygon',
                'coordinates': coords
            }
        }

    def __copy__(self):
        new_con = Transformer(self.identifier, self.geometry, self.properties)
        new_con._display_name = self._display_name
        return new_con

    def __repr__(self):
        return 'Transformer: {}'.format(self.display_name)
