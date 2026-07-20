# coding=utf-8
"""Parameters for customizing the program information and schema version in gbXML files."""
from __future__ import division

from honeybee.typing import valid_string


class GBXMLVersionFormat(object):
    """Customize the program information and schema version in the gbXML.

    Args:
        program_name: Optional text to set the name of the software that will
            appear under the programId and ProductName tags of the DocumentHistory
            section. This can be set things like "Ladybug Tools" or "Pollination"
            or some other software in which this gbXML export capability is being
            run. If None, the "OpenStudio" will be used. (Default: None).
        program_version: Optional text to set the version of the software that
            will appear under the DocumentHistory section. If None, and the
            program_name is also unspecified, only the version of OpenStudio will
            appear. Otherwise, this will default to "0.0.0" given that the version
            field is required. (Default: None).
        gbxml_schema_version: Optional text to set the version of the gbXML schema
            that is specified in the XML header (eg. "5.00"). If None, this
            will default to the latest version. (Default: None).

    Properties:
        * program_name
        * program_version
        * gbxml_schema_version
    """
    __slots__ = ('_program_name', '_program_version', '_gbxml_schema_version')
    SCHEMA_VERSIONS = (
        '0.35', '0.36', '0.37', '5.00', '5.01', '5.10', '5.11', '5.12',
        '6.00', '6.01', '7.03', '8.01'
    )

    def __init__(self, program_name=None, program_version=None, gbxml_schema_version=None):
        """Initialize GBXMLVersionFormat."""
        self.program_name = program_name
        self.program_version = program_version
        self.gbxml_schema_version = gbxml_schema_version

    @property
    def program_name(self):
        """Get or set text to set the name of the exporting software."""
        return self._program_name

    @program_name.setter
    def program_name(self, value):
        if value is not None:
            try:
                value = str(value)
            except UnicodeEncodeError:  # Python 2 machine lacking the character set
                pass  # keep it as unicode
        self._program_name = value

    @property
    def program_version(self):
        """Get or set text to set the version of the exporting software."""
        return self._program_version

    @program_version.setter
    def program_version(self, value):
        if value is not None:
            try:
                value = str(value)
            except UnicodeEncodeError:  # Python 2 machine lacking the character set
                pass  # keep it as unicode
        self._program_version = value

    @property
    def gbxml_schema_version(self):
        """Get or set text for the version of the gbXML schema to use."""
        return self._gbxml_schema_version

    @gbxml_schema_version.setter
    def gbxml_schema_version(self, value):
        if value is not None:
            clean_input = valid_string(value).lower()
            for key in self.SCHEMA_VERSIONS:
                if key.lower() == clean_input:
                    value = key
                    break
            else:
                raise ValueError(
                    'gbxml_schema_version {} is not recognized.\nChoose from the '
                    'following:\n{}'.format(value, self.SCHEMA_VERSIONS))
        self._gbxml_schema_version = value

    @classmethod
    def from_dict(cls, data):
        """Create a GBXMLNameFormat object from a dictionary.

        Args:
            data: A GBXMLVersionFormat dictionary in following the format below.

        .. code-block:: python

            {
            "type": "GBXMLVersionFormat",
            "program_name": "Pollination Model Editor",
            "program_version": "2.27.1.0",
            "gbxml_schema_version": "8.01"
            }
        """
        # check that it is the correct type
        assert data['type'] == 'GBXMLVersionFormat', \
            'Expected GBXMLVersionFormat dictionary. Got {}.'.format(data['type'])
        pn = data['program_name'] if 'program_name' in data else None
        pv = data['program_version'] if 'program_version' in data else None
        sv = data['gbxml_schema_version'] if 'gbxml_schema_version' in data else None
        return cls(pn, pv, sv)

    def to_dict(self):
        """GBXMLVersionFormat dictionary representation."""
        return {
            'type': 'GBXMLVersionFormat',
            'program_name': self.program_name,
            'program_version': self.program_version,
            'gbxml_schema_version': self.gbxml_schema_version
        }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __copy__(self):
        return GBXMLVersionFormat(
            self.program_name,
            self.program_version,
            self.gbxml_schema_version
        )

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.program_name, self.program_version, self.gbxml_schema_version)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, GBXMLVersionFormat) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        """Represent GBXMLVersionFormat."""
        return 'GBXMLVersionFormat:'
