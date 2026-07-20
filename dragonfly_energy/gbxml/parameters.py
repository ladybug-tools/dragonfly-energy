# coding=utf-8
"""Parameters for customizing the translation to gbXML."""
from __future__ import division

from .geometry import GBXMLGeometryFormat
from .name import GBXMLNameFormat
from .energy import GBXMLEnergyAttributeFormat
from .version import GBXMLVersionFormat


class GBXMLParameters(object):
    """Complete set of GBXML translation parameters.

    Args:
        ip_units: A boolean to note whether the geometry, space loads, and
            construction properties are reported in IP units (True) or SI
            units (False). (Default: False).

    Properties:
        * ip_units
        * geometry_format
        * name_format
        * energy_attribute_format
        * version_format
    """
    __slots__ = (
        '_ip_units', '_geometry_format', '_name_format',
        '_energy_attribute_format', '_version_format'
    )

    def __init__(self, ip_units=False, geometry_format=None, name_format=None,
                 energy_attribute_format=None, version_format=None):
        """Initialize GBXMLParameters."""
        self.ip_units = ip_units
        self.geometry_format = geometry_format
        self.name_format = name_format
        self.energy_attribute_format = energy_attribute_format
        self.version_format = version_format

    @classmethod
    def for_energyplus(cls):
        """Create default GBXMLParameters for export to EnergyPlus.

        By extension, these parameters are also recommended when exporting gbXMLs
        for OpenStudio, DesignBuilder, or other interfaces built on top of EnergyPlus.
        """
        geometry_format = GBXMLGeometryFormat(
            triangulate_openings=True, triangulate_non_planar=True,
            ignore_multipliers=True
        )
        name_format = GBXMLNameFormat(
            reset_geometry_ids=True, reset_resource_ids=True
        )
        return cls(geometry_format=geometry_format, name_format=name_format)

    @classmethod
    def for_trace_700(cls):
        """Create default GBXMLParameters for export to TRACE 700."""
        geometry_format = GBXMLGeometryFormat(
            exclude_shades=True, exclude_plenums=True,
            rect_geo_format='SimpleArea', ignore_multipliers=True
        )
        name_format = GBXMLNameFormat(
            ground_face_type='SlabOnGrade',
            face_rename_format='{gbxml_type} - {cardinal_direction}',
            subface_rename_format='{gbxml_type} - {cardinal_direction}'
        )
        return cls(
            ip_units=True, geometry_format=geometry_format, name_format=name_format
        )

    @classmethod
    def for_trace_3d_plus(cls):
        """Create default GBXMLParameters for export to TRACE 3D Plus."""
        geometry_format = GBXMLGeometryFormat(
            exclude_roofs=True, exclude_shades=True, exclude_plenums=True,
            opening_simplification='SingleRectWindow', explicit_holes=True
        )
        name_format = GBXMLNameFormat(
            ground_face_type='SlabOnGrade', reset_geometry_ids=True
        )
        return cls(
            ip_units=True, geometry_format=geometry_format, name_format=name_format
        )

    @classmethod
    def for_energy_pro(cls):
        """Create default GBXMLParameters for export to EnergyPro."""
        geometry_format = GBXMLGeometryFormat(
            triangulate_openings=True, triangulate_non_planar=True,
            ignore_multipliers=True
        )
        name_format = GBXMLNameFormat(
            reset_geometry_ids=True, reset_resource_ids=True,
            face_rename_format='{gbxml_type} - {cardinal_direction}',
            subface_rename_format='{gbxml_type} - {cardinal_direction}'
        )
        version_format = GBXMLVersionFormat(gbxml_schema_version='5.00')
        return cls(
            geometry_format=geometry_format, name_format=name_format,
            version_format=version_format
        )

    @property
    def ip_units(self):
        """Get or set a boolean for whether the gbXML is exported in IP units."""
        return self._ip_units

    @ip_units.setter
    def ip_units(self, value):
        self._ip_units = bool(value)

    @property
    def geometry_format(self):
        """Get or set a GBXMLGeometryFormat object for the customizing the geometry export.
        """
        return self._geometry_format

    @geometry_format.setter
    def geometry_format(self, value):
        if value is not None:
            assert isinstance(value, GBXMLGeometryFormat), 'Expected GBXMLGeometryFormat ' \
                'for GBXMLParameters.geometry_format. Got {}.'.format(type(value))
            self._geometry_format = value
        else:
            self._geometry_format = GBXMLGeometryFormat()

    @property
    def name_format(self):
        """Get or set a GBXMLNameFormat object for the customizing the names in export.
        """
        return self._name_format

    @name_format.setter
    def name_format(self, value):
        if value is not None:
            assert isinstance(value, GBXMLNameFormat), 'Expected GBXMLNameFormat ' \
                'for GBXMLParameters.name_format. Got {}.'.format(type(value))
            self._name_format = value
        else:
            self._name_format = GBXMLNameFormat()

    @property
    def energy_attribute_format(self):
        """Get or set a GBXMLEnergyAttributeFormat object for the customizing the export.
        """
        return self._energy_attribute_format

    @energy_attribute_format.setter
    def energy_attribute_format(self, value):
        if value is not None:
            assert isinstance(value, GBXMLEnergyAttributeFormat), \
                'Expected GBXMLEnergyAttributeFormat ' \
                'for GBXMLParameters.energy_attribute_format. Got {}.'.format(type(value))
            self._energy_attribute_format = value
        else:
            self._energy_attribute_format = GBXMLEnergyAttributeFormat()

    @property
    def version_format(self):
        """Get or set a GBXMLVersionFormat object for the customizing the names in export.
        """
        return self._version_format

    @version_format.setter
    def version_format(self, value):
        if value is not None:
            assert isinstance(value, GBXMLVersionFormat), 'Expected GBXMLVersionFormat ' \
                'for GBXMLParameters.version_format. Got {}.'.format(type(value))
            self._version_format = value
        else:
            self._version_format = GBXMLVersionFormat()

    @classmethod
    def from_dict(cls, data):
        """Create a GBXMLParameters object from a dictionary.

        Args:
            data: A GBXMLParameters dictionary in following the format below.

        .. code-block:: python

            {
            "type": "GBXMLParameters",
            "ip_units": False,
            "geometry_format": {}, # Dragonfly GBXMLGeometryFormat dictionary
            "name_format": {}, # Dragonfly GBXMLNameFormat dictionary
            "energy_attribute_format": {}, #GBXMLEnergyAttributeFormat dictionary
            "version_format": {} # Dragonfly GBXMLVersionFormat dictionary
            }
        """
        assert data['type'] == 'GBXMLParameters', \
            'Expected GBXMLParameters dictionary. Got {}.'.format(data['type'])

        ip = data['ip_units'] if 'ip_units' in data else False
        geo = None
        if 'geometry_format' in data and data['geometry_format'] is not None:
            geo = GBXMLGeometryFormat.from_dict(data['geometry_format'])
        name = None
        if 'name_format' in data and data['name_format'] is not None:
            name = GBXMLNameFormat.from_dict(data['name_format'])
        energy = None
        if 'energy_attribute_format' in data and \
                data['energy_attribute_format'] is not None:
            energy = GBXMLEnergyAttributeFormat.from_dict(data['energy_attribute_format'])
        version = None
        if 'version_format' in data and data['version_format'] is not None:
            version = GBXMLVersionFormat.from_dict(data['version_format'])

        return cls(ip, geo, name, energy, version)

    def to_dict(self):
        """GBXMLParameters dictionary representation."""
        return {
            'type': 'GBXMLParameters',
            'ip_units': self.ip_units,
            'geometry_format': self.geometry_format.to_dict(),
            'name_format': self.name_format.to_dict(),
            'energy_attribute_format': self.energy_attribute_format.to_dict(),
            'version_format': self.version_format.to_dict()
        }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __copy__(self):
        return GBXMLParameters(
            self.ip_units,
            self.geometry_format.duplicate(),
            self.name_format.duplicate(),
            self.energy_attribute_format.duplicate(),
            self.version_format.duplicate()
        )

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (
            self.ip_units, hash(self.geometry_format), hash(self.name_format),
            hash(self.energy_attribute_format), hash(self.version_format)
        )

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, GBXMLParameters) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'Energy GBXMLParameters:'
