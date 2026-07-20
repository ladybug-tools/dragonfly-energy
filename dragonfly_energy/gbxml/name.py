# coding=utf-8
"""Parameters for customizing the names and IDs of objects in gbXML files."""
from __future__ import division

from honeybee.typing import valid_string


class GBXMLNameFormat(object):
    """Customize the names and IDs of objects in the gbXML.

    Args:
        interior_face_type: Text string for the type to be used for all interior
            floor/ceiling faces. (Default: InteriorFloor). Choose from the following.

            * InteriorFloor
            * Ceiling

        ground_face_type: Text string for the type to be used for all ground-contact
            floor faces. If AutoAssign, the ground types will be SlabOnGrade for floors
            belonging to rooms with any above-ground walls and UndergroundSlab
            for floors in rooms with all underground walls. Choose from the following.

            * AutoAssign
            * UndergroundSlab
            * SlabOnGrade
            * RaisedFloor

        face_rename_format: An optional text string for the pattern with which
            faces will be renamed. Any property on the honeybee Face class may be
            used (eg. gbxml_str) and each property should be put in curly brackets.
            Nested properties can be specified by using "." to denote nesting levels
            (eg. properties.energy.construction.display_name). Functions that
            return string outputs can also be passed here as long as these
            functions defaults specified for all arguments.
        subface_rename_format: An optional text string for the pattern with which
            apertures and doors will be renamed. Any property that exists on both
            the honeybee Aperture and honeybee Door class may be used (eg. gbxml_str)
            and each property should be put in curly brackets. Nested
            properties can be specified by using "." to denote nesting levels
            (eg. properties.energy.construction.display_name). Functions that
            return string outputs can also be passed here as long as these
            functions defaults specified for all arguments.
        reset_geometry_ids: Boolean to note whether a cleaned version of geometry
            display names should be used for the IDs that appear within
            the gbXML file. Using this flag will affect all Rooms, Faces,
            Apertures, Doors, and Shades. It will generally result in more
            read-able IDs in the gbXML file but this means that it will not be
            easy to map results back to the input Model. Cases of duplicate IDs
            resulting from non-unique names will be resolved by adding integers
            to the ends of the new IDs that are derived from the name. (Default: False).
        reset_resource_ids: Boolean to note whether a cleaned version of all
            resource display names should be used for the IDs that appear within
            the gbXML file. Using this flag will affect all Materials,
            Constructions, ConstructionSets, Schedules, Loads, and ProgramTypes.
            It will generally result in more read-able names for the resources
            in the gbXML file. Cases of duplicate IDs resulting from non-unique
            names will be resolved by adding integers to the ends of the new
            IDs that are derived from the name. (Default: False).

    Properties:
        * interior_face_type
        * ground_face_type
        * face_rename_format
        * subface_rename_format
        * reset_geometry_ids
        * reset_resource_ids
    """
    __slots__ = (
        '_interior_face_type', '_ground_face_type', '_face_rename_format',
        '_subface_rename_format', '_reset_geometry_ids', '_reset_resource_ids'
    )
    INTERIOR_TYPES = ('InteriorFloor', 'Ceiling')
    GROUND_TYPES = ('AutoAssign', 'UndergroundSlab', 'SlabOnGrade', 'RaisedFloor')

    def __init__(
        self, interior_face_type='InteriorFloor', ground_face_type='AutoAssign',
        face_rename_format=None, subface_rename_format=None,
        reset_geometry_ids=False, reset_resource_ids=False
    ):
        """Initialize GBXMLGeometryFormat."""
        self.interior_face_type = interior_face_type
        self.ground_face_type = ground_face_type
        self.face_rename_format = face_rename_format
        self.subface_rename_format = subface_rename_format
        self.reset_geometry_ids = reset_geometry_ids
        self.reset_resource_ids = reset_resource_ids

    @property
    def interior_face_type(self):
        """Get or set text for the type to use for interior floors/ceilings.

        Choose from the options below:

        * InteriorFloor
        * Ceiling
        """
        return self._interior_face_type

    @interior_face_type.setter
    def interior_face_type(self, value):
        clean_input = valid_string(value).lower()
        for key in self.INTERIOR_TYPES:
            if key.lower() == clean_input:
                value = key
                break
        else:
            raise ValueError(
                'interior_face_type {} is not recognized.\nChoose from the '
                'following:\n{}'.format(value, self.INTERIOR_TYPES))
        self._interior_face_type = value

    @property
    def ground_face_type(self):
        """Get or set text for the type to use for all ground-contact floor faces.

        Choose from the options below:

        * AutoAssign
        * UndergroundSlab
        * SlabOnGrade
        * RaisedFloor
        """
        return self._ground_face_type

    @ground_face_type.setter
    def ground_face_type(self, value):
        clean_input = valid_string(value).lower()
        for key in self.GROUND_TYPES:
            if key.lower() == clean_input:
                value = key
                break
        else:
            raise ValueError(
                'ground_face_type {} is not recognized.\nChoose from the '
                'following:\n{}'.format(value, self.GROUND_TYPES))
        self._ground_face_type = value

    @property
    def face_rename_format(self):
        """Get or set a string for the pattern with which faces will be renamed.
        """
        return self._face_rename_format

    @face_rename_format.setter
    def face_rename_format(self, value):
        if value is not None:
            try:
                value = str(value)
            except UnicodeEncodeError:  # Python 2 machine lacking the character set
                pass  # keep it as unicode
        self._face_rename_format = value

    @property
    def subface_rename_format(self):
        """Get or set a string for the pattern with which sub-faces will be renamed.
        """
        return self._subface_rename_format

    @subface_rename_format.setter
    def subface_rename_format(self, value):
        if value is not None:
            try:
                value = str(value)
            except UnicodeEncodeError:  # Python 2 machine lacking the character set
                pass  # keep it as unicode
        self._subface_rename_format = value

    @property
    def reset_geometry_ids(self):
        """Get or set a boolean for whether the IDs of geometry are set from the names."""
        return self._reset_geometry_ids

    @reset_geometry_ids.setter
    def reset_geometry_ids(self, value):
        self._reset_geometry_ids = bool(value)

    @property
    def reset_resource_ids(self):
        """Get or set a boolean for whether the IDs of resources are set from the names."""
        return self._reset_resource_ids

    @reset_resource_ids.setter
    def reset_resource_ids(self, value):
        self._reset_resource_ids = bool(value)

    @classmethod
    def from_dict(cls, data):
        """Create a GBXMLNameFormat object from a dictionary.

        Args:
            data: A GBXMLNameFormat dictionary in following the format below.

        .. code-block:: python

            {
            "type": "GBXMLNameFormat",
            "interior_face_type": "Ceiling",
            "ground_face_type": "SlabOnGrade",
            "face_rename_format": "{gbxml_type} - {cardinal_direction}",
            "subface_rename_format: "{gbxml_type} - {cardinal_direction}",
            "reset_geometry_ids": False,
            "reset_resource_ids": False
            }
        """
        # check that it is the correct type
        assert data['type'] == 'GBXMLNameFormat', \
            'Expected GBXMLNameFormat dictionary. Got {}.'.format(data['type'])
        ift = data['interior_face_type'] if 'interior_face_type' in data else 'InteriorFloor'
        gft = data['ground_face_type'] if 'ground_face_type' in data else 'AutoAssign'
        frf = data['face_rename_format'] if 'face_rename_format' in data else None
        orf = data['subface_rename_format'] if 'subface_rename_format' in data else None
        gid = data['reset_geometry_ids'] if 'reset_geometry_ids' in data else False
        rid = data['reset_resource_ids'] if 'reset_resource_ids' in data else False

        return cls(ift, gft, frf, orf, gid, rid)

    def to_dict(self):
        """GBXMLGeometryFormat dictionary representation."""
        return {
            'type': 'GBXMLGeometryFormat',
            'interior_face_type': self.interior_face_type,
            'ground_face_type': self.ground_face_type,
            'face_rename_format': self.face_rename_format,
            'subface_rename_format': self.subface_rename_format,
            'reset_geometry_ids': self.reset_geometry_ids,
            'reset_resource_ids': self.reset_resource_ids
        }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __copy__(self):
        return GBXMLNameFormat(
            self.interior_face_type,
            self.ground_face_type,
            self.face_rename_format,
            self.subface_rename_format,
            self.reset_geometry_ids,
            self.reset_resource_ids
        )

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (
            self.interior_face_type, self.ground_face_type,
            self.face_rename_format, self.subface_rename_format,
            self.reset_geometry_ids, self.reset_resource_ids
        )

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, GBXMLNameFormat) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        """Represent GBXMLNameFormat."""
        return 'GBXMLNameFormat:'
