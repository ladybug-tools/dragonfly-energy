# coding=utf-8
"""Parameters for customizing energy attributes assigned to the objects in gbXML files."""
from __future__ import division


class GBXMLEnergyAttributeFormat(object):
    """Customize the energy attributes assigned to the objects in the gbXML.

    Args:
        ventilation_components: Boolean to note whether outdoor air ventilation values
            in the gbXML are written as a single total OAFlowPerZone (False)
            or ventilation criteria are written as separate criteria (True).
            That is, separate specifications for OAFlowPerPerson, OAFlowPerArea,
            etc. Note that the total ventilation accounts for the ventilation
            effectiveness while the individual flows do not. (Default: False).

    Properties:
        * ventilation_components
    """
    __slots__ = ('_ventilation_components',)

    def __init__(self, ventilation_components=False):
        """Initialize GBXMLEnergyAttributeFormat."""
        self.ventilation_components = ventilation_components

    @property
    def ventilation_components(self):
        """Get or set a boolean for whether to use individual ventilation components."""
        return self._ventilation_components

    @ventilation_components.setter
    def ventilation_components(self, value):
        self._ventilation_components = bool(value)

    @classmethod
    def from_dict(cls, data):
        """Create a GBXMLEnergyAttributeFormat object from a dictionary.

        Args:
            data: A GBXMLEnergyAttributeFormat dictionary in following the format below.

        .. code-block:: python

            {
            "type": "GBXMLEnergyAttributeFormat",
            "ventilation_components": True
            }
        """
        # check that it is the correct type
        assert data['type'] == 'GBXMLEnergyAttributeFormat', \
            'Expected GBXMLEnergyAttributeFormat dictionary. Got {}.'.format(data['type'])
        vc = data['ventilation_components'] if 'ventilation_components' in data else False
        return cls(vc)

    def to_dict(self):
        """GBXMLEnergyAttributeFormat dictionary representation."""
        return {
            'type': 'GBXMLEnergyAttributeFormat',
            'ventilation_components': self.ventilation_components
        }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __copy__(self):
        return GBXMLEnergyAttributeFormat(self.ventilation_components)

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.ventilation_components,)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, GBXMLEnergyAttributeFormat) and \
            self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        """Represent GBXMLEnergyAttributeFormat."""
        return 'GBXMLEnergyAttributeFormat:'
