# coding=utf-8
"""Wire in OpenDSS."""
from __future__ import division

from honeybee._lockable import lockable
from honeybee.typing import float_positive, int_positive, valid_ep_string


@lockable
class Wire(object):
    """Represents the properties of a wire in OpenDSS.

    Args:
        identifier: Text string for a unique wire property ID. Must contain only
            characters that are acceptable in OpenDSS. This will be used to
            identify the object across the exported geoJSON and OpenDSS files.
        ampacity: A number for the ampacity of the wire in amps. (Default: 220).
        geometrical_mean_radius: A number for the geometric mean of distances between
            the strands of the conductor in millimeters. (Default: 3.9).
        resistance: A number for the electrical resistance of the conductor in
            ohms per kilometer of wire. (Default: 0.3937).
        diameter: A number for the diameter of the wire in millimeters. (Default: 10).
        voltage_level: Text to denote the level of voltage that the wire is designed to
            carry. Choose from ("LV", "MV", "LV or MV"). (Default: "MV").
        wire_type: Text for the type of wire, denoting whether the wire is overhead
            (OH) or underground (UG). Choose from ('OH', 'UG', 'UG concentric
            neutral'). (Default: "OH").
        concentric_properties: A ConcentricProperties object to denote the concentric
            neutral properties of the Wire. This must be specified when the wire_type
            is "UG concentric neutral." (Default: None).

    Properties:
        * identifier
        * display_name
        * ampacity
        * geometrical_mean_radius
        * resistance
        * diameter
        * voltage_level
        * wire_type
        * concentric_properties
    """
    __slots__ = (
        '_locked', '_display_name', '_identifier', '_ampacity',
        '_geometrical_mean_radius', '_resistance', '_diameter',
        '_voltage_level', '_wire_type', '_concentric_properties'
    )

    VALID_VOLTAGE_LEVELS = ('LV', 'MV', 'LV or MV')
    VALID_WIRE_TYPES = ('OH', 'UG', 'UG concentric neutral')

    def __init__(self, identifier, ampacity=220, geometrical_mean_radius=3.9,
                 resistance=0.3937, diameter=10, voltage_level='MV',
                 wire_type='OH', concentric_properties=None):
        """Initialize Wire"""
        self._locked = False  # unlocked by default
        self._display_name = None
        self.identifier = identifier
        self.ampacity = ampacity
        self.geometrical_mean_radius = geometrical_mean_radius
        self.resistance = resistance
        self.diameter = diameter
        self.voltage_level = voltage_level
        self.concentric_properties = concentric_properties
        self.wire_type = wire_type

    @classmethod
    def from_dict(cls, data):
        """Create a Wire object from a dictionary.

        Args:
            data: A dictionary representation of a Wire object in the format below.

        .. code-block:: python

            {
            'type': 'Wire',
            'identifier': 'OH AL 2/0 A',  # unique wire property identifier
            'ampacity': 220,  # ampacity of the wire in amps
            'geometrical_mean_radius': 3.9,  # gmr in mm
            'resistance': 0.3937,  # resistance of the wire in ohms/km
            'diameter': 10,  # diameter of the wire in mm
            'voltage_level': 'LV or MV',  # text for the voltage level
            'wire_type': 'OH'  # text for the type of wire
            }
        """
        amp = data['ampacity'] if 'ampacity' in data else 220
        gmr = data['geometrical_mean_radius'] if 'geometrical_mean_radius' in data \
            else 3.9
        res = data['resistance'] if 'resistance' in data else 0.3937
        dim = data['diameter'] if 'diameter' in data else 10
        vl = data['voltage_level'] if 'voltage_level' in data else 'MV'
        wt = data['wire_type'] if 'wire_type' in data else 'OH'
        c_prop = ConcentricProperties.from_dict(data['concentric_properties']) \
            if 'concentric_properties' in data and \
            data['concentric_properties'] is not None else None
        wire = cls(data['identifier'], amp, gmr, res, dim, vl, wt, c_prop)
        if 'display_name' in data and data['display_name'] is not None:
            wire.display_name = data['display_name']
        return wire

    @classmethod
    def from_electrical_database_dict(cls, data):
        """Create a Wire from an dictionary as it appears in electrical_database.json.

        Args:
            data: A dictionary representation of a Wire object in the format below.

        .. code-block:: python

            {
            'nameclass': 'OH AL 2/0 A',  # unique wire property identifier
            'ampacity (A)': 220,  # ampacity of the wire in amps
            'gmr (mm)': 3.9,  # gmr in meters
            'resistance (ohm/km)': 0.3937,  # resistance of the wire in ohms/km
            'diameter (mm)': 10,  # diameter of the wire in meters
            'voltage level': 'MV',
            'type': 'OH'
            }
        """
        c_prop = None
        if data['type'] == 'UG concentric neutral':
            c_prop = ConcentricProperties(
                data['gmr neutral (mm)'],
                data['resistance neutral (ohm/km)'],
                data['concentric diameter neutral strand (mm)'],
                data['concentric neutral outside diameter (mm)'],
                data['# concentric neutral strands']
            )
        return cls(
            data['nameclass'], data['ampacity (A)'], data['gmr (mm)'],
            data['resistance (ohm/km)'], data['diameter (mm)'],
            data['voltage level'], data['type'], c_prop)

    @property
    def identifier(self):
        """Get or set a text string for the unique object identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, value):
        self._identifier = valid_ep_string(value, 'wire identifier')

    @property
    def display_name(self):
        """Get or set a string for the object name without any character restrictions.

        If not set, this will be equal to the identifier.
        """
        if self._display_name is None:
            return self._identifier
        return self._display_name

    @display_name.setter
    def display_name(self, value):
        try:
            self._display_name = str(value)
        except UnicodeEncodeError:  # Python 2 machine lacking the character set
            self._display_name = value  # keep it as unicode

    @property
    def ampacity(self):
        """Get or set a number for the ampacity of the wire in amps."""
        return self._ampacity

    @ampacity.setter
    def ampacity(self, value):
        self._ampacity = float_positive(value, 'ampacity')

    @property
    def geometrical_mean_radius(self):
        """Get or set a number for the geometrical mean radius of the wire in mm."""
        return self._geometrical_mean_radius

    @geometrical_mean_radius.setter
    def geometrical_mean_radius(self, value):
        self._geometrical_mean_radius = float_positive(value, 'geometrical_mean_radius')

    @property
    def resistance(self):
        """Get or set a number for the resistance of the wire in ohms per km of wire.
        """
        return self._resistance

    @resistance.setter
    def resistance(self, value):
        self._resistance = float_positive(value, 'resistance')

    @property
    def diameter(self):
        """Get or set a number for the diameter of the wire in mm."""
        return self._diameter

    @diameter.setter
    def diameter(self, value):
        self._diameter = float_positive(value, 'diameter')

    @property
    def voltage_level(self):
        """Get or set text for the voltage level of the wire. (LV, MV, LV or MV)."""
        return self._voltage_level

    @voltage_level.setter
    def voltage_level(self, value):
        assert value in self.VALID_VOLTAGE_LEVELS, 'Voltage level "{}" is not ' \
            'acceptable. Choose from:\n{}'.format(value, '\n'.join(self.VALID_PHASES))
        self._voltage_level = value

    @property
    def wire_type(self):
        """Get or set a text string for the type of wire."""
        return self._wire_type

    @wire_type.setter
    def wire_type(self, value):
        assert value in self.VALID_WIRE_TYPES, 'Wire type "{}" is not acceptable. ' \
            'Choose from:\n{}'.format(value, '\n'.join(self.VALID_WIRE_TYPES))
        if value == 'UG concentric neutral':
            assert self.concentric_properties is not None, 'Wire concentric_properties' \
                ' must be specified in order to use "UG concentric neutral."'
        self._wire_type = value

    @property
    def concentric_properties(self):
        """Get or set an array of Wire objects for the phases of the wires."""
        return self._concentric_properties

    @concentric_properties.setter
    def concentric_properties(self, value):
        if value is not None:
            assert isinstance(value, ConcentricProperties), \
                'Expected Wire ConcentricProperties. Got {}.'.format(type(value))
        self._concentric_properties = value

    def to_dict(self):
        """Get Wire dictionary."""
        base = {
            'type': 'Wire',
            'identifier': self.identifier,
            'ampacity': self.ampacity,
            'geometrical_mean_radius': self.geometrical_mean_radius,
            'resistance': self.resistance,
            'diameter': self.diameter,
            'voltage_level': self.voltage_level,
            'wire_type': self.wire_type
        }
        if self.concentric_properties is not None:
            base['concentric_properties'] = self.concentric_properties.to_dict()
        if self._display_name is not None:
            base['display_name'] = self._display_name
        return base

    def to_electrical_database_dict(self):
        """Get Wire as it should appear in the URBANopt electrical database.json."""
        base = {
            'nameclass': self.identifier,
            'ampacity (A)': self.ampacity,
            'gmr (mm)': self.geometrical_mean_radius,
            'resistance (ohm/km)': self.resistance,
            'diameter (mm)': self.diameter,
            'voltage level': self.voltage_level,
            'type': self.wire_type
        }
        if self.concentric_properties is not None:
            c_prop = self.concentric_properties
            base['gmr neutral (mm)'] = c_prop.geometrical_mean_radius
            base['resistance neutral (ohm/km)'] = c_prop.resistance
            base['concentric diameter neutral strand (mm)'] = \
                c_prop.concentric_strand_diameter
            base['concentric neutral outside diameter (mm)'] = \
                c_prop.concentric_outside_diameter
            base['# concentric neutral strands'] = c_prop.strand_count
        return base

    def lock(self):
        """The lock() method will also lock the concentric_properties."""
        self._locked = True
        if self.concentric_properties is not None:
            self.concentric_properties.lock()

    def unlock(self):
        """The unlock() method will also unlock the concentric_properties."""
        self._locked = False
        if self.concentric_properties is not None:
            self.concentric_properties.unlock()

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_obj = Wire(
            self.identifier, self.ampacity, self.geometrical_mean_radius,
            self.resistance, self.diameter, self.voltage_level, self.wire_type)
        new_obj._display_name = self._display_name
        return new_obj

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (
            self.identifier, self.ampacity, self.geometrical_mean_radius,
            self.resistance, self.diameter, self.voltage_level, self.wire_type)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, Wire) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent wire."""
        return 'Wire: {}'.format(self.identifier)


@lockable
class ConcentricProperties(object):
    """Represents the concentric neutral properties of a wire in OpenDSS.

    Args:
        geometrical_mean_radius: A number for the geometric mean of distances between
            the neutral strands in millimeters. (Default: 0.8).
        resistance: A number for the electrical resistance of the neutral strands in
            ohms per kilometer of wire. (Default: 5.8).
        concentric_strand_diameter: A number for the diameter of the neutral strand
            in millimeters. (Default: 2).
        concentric_outside_diameter:A number for the outside diameter of the neutral
            strand in millimeters. (Default: 45).
        strand_count: A positive integer for the number of concentric neutral
            strands. (Default: 24)

    Properties:
        * geometrical_mean_radius
        * resistance
        * concentric_strand_diameter
        * concentric_outside_diameter
        * strand_count
    """
    __slots__ = (
        '_locked', '_geometrical_mean_radius', '_resistance',
        '_concentric_strand_diameter', '_concentric_outside_diameter', '_strand_count'
    )

    def __init__(
            self, geometrical_mean_radius=0.8, resistance=5.8,
            concentric_strand_diameter=2, concentric_outside_diameter=45,
            strand_count=24):
        """Initialize ConcentricProperties"""
        self._locked = False  # unlocked by default
        self.geometrical_mean_radius = geometrical_mean_radius
        self.resistance = resistance
        self.concentric_strand_diameter = concentric_strand_diameter
        self.concentric_outside_diameter = concentric_outside_diameter
        self.strand_count = strand_count

    @classmethod
    def from_dict(cls, data):
        """Create a ConcentricProperties object from a dictionary.

        Args:
            data: A dictionary representation of a ConcentricProperties object
                in the format below.

        .. code-block:: python

            {
            'type': 'ConcentricProperties',
            'geometrical_mean_radius': 0.8,  # gmr in mm
            'resistance': 5.8,  # resistance of the wire in ohms/km
            'concentric_strand_diameter': 2,  # diameter of the wire in mm
            'concentric_outside_diameter': 45,  # outside diameter of the wire in mm
            'strand_count': 24  # integer for the number of strands
            }
        """
        gmr = data['geometrical_mean_radius'] if 'geometrical_mean_radius' in data \
            else 0.8
        res = data['resistance'] if 'resistance' in data else 5.8
        s_dim = data['concentric_strand_diameter'] if 'concentric_strand_diameter' \
            in data else 2
        o_dim = data['concentric_outside_diameter'] if 'concentric_outside_diameter' \
            in data else 45
        sc = data['strand_count'] if 'strand_count' in data else 24
        return cls(gmr, res, s_dim, o_dim, sc)

    @property
    def geometrical_mean_radius(self):
        """Get or set a number for the geometrical mean radius of the strands in mm."""
        return self._geometrical_mean_radius

    @geometrical_mean_radius.setter
    def geometrical_mean_radius(self, value):
        self._geometrical_mean_radius = float_positive(value, 'geometrical_mean_radius')

    @property
    def resistance(self):
        """Get or set a number for the resistance of the strands in ohms per km of wire.
        """
        return self._resistance

    @resistance.setter
    def resistance(self, value):
        self._resistance = float_positive(value, 'resistance')

    @property
    def concentric_strand_diameter(self):
        """Get or set a number for the diameter of the neutral strand in mm."""
        return self._concentric_strand_diameter

    @concentric_strand_diameter.setter
    def concentric_strand_diameter(self, value):
        self._concentric_strand_diameter = \
            float_positive(value, 'concentric_strand_diameter')

    @property
    def concentric_outside_diameter(self):
        """Get or set a number for the outside diameter of the neutral strand in mm."""
        return self._concentric_outside_diameter

    @concentric_outside_diameter.setter
    def concentric_outside_diameter(self, value):
        self._concentric_outside_diameter = \
            float_positive(value, 'concentric_outside_diameter')

    @property
    def strand_count(self):
        """Get or set a positive integer for the number of concentric neutral strands.
        """
        return self._strand_count

    @strand_count.setter
    def strand_count(self, value):
        self._strand_count = int_positive(value, 'strand_count')

    def to_dict(self):
        """Get ConcentricProperties dictionary."""
        return {
            'type': 'ConcentricProperties',
            'geometrical_mean_radius': self.geometrical_mean_radius,
            'resistance': self.resistance,
            'concentric_strand_diameter': self.concentric_strand_diameter,
            'concentric_outside_diameter': self.concentric_outside_diameter,
            'strand_count': self.strand_count
        }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_obj = ConcentricProperties(
            self.geometrical_mean_radius, self.resistance,
            self.concentric_strand_diameter, self.concentric_outside_diameter,
            self.strand_count)
        return new_obj

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (
            self.geometrical_mean_radius, self.resistance,
            self.concentric_strand_diameter, self.concentric_outside_diameter,
            self.strand_count)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, Wire) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent wire."""
        return 'ConcentricProperties: [{} strands]'.format(self.strand_count)
