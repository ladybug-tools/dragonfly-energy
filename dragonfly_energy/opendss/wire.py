# coding=utf-8
"""Wire in OpenDSS."""
from __future__ import division

from honeybee._lockable import lockable
from honeybee.typing import float_in_range, float_positive, valid_ep_string


@lockable
class Wire(object):
    """Represents the properties of a wire in OpenDSS.

    Args:
        identifier: Text string for a unique wire property ID. Must contain only
            characters that are acceptable in OpenDSS. This will be used to
            identify the object across the exported geoJSON and OpenDSS files.
        height: A number for the height of the wire above the ground in meters.
            Negative values indicate wires below ground. (Default: 16).
        relative_x: A number for the X offset relative to the wire line geometry
            in meters. For convenience, one of the conductors in a given wire is
            usually assigned the 0 position. (Default: 0).
        phase: Text for the phase of the wire. Must be one of the following values
            (A, B, C, N, S1, S2). (Default: A).
        ampacity: A number for the ampacity of the wire in amps. (Default: 220).
        geometrical_mean_radius: A number for the geometric mean of distances between
            the strands of the conductor in meters. (Default: 0.0039).
        resistance: A number for the electrical resistance of the conductor in
            ohms per meter of wire. (Default: 0.0003937).
        diameter: A number for the diameter of the wire in meters. (Default: 0.01).

    Properties:
        * identifier
        * display_name
        * height
        * relative_x
        * phase
        * ampacity
        * geometrical_mean_radius
        * resistance
        * diameter
    """
    __slots__ = (
        '_locked', '_display_name', '_identifier', '_height', '_relative_x', '_phase',
        '_ampacity', '_geometrical_mean_radius', '_resistance', '_diameter')

    VALID_PHASES = ('A', 'B', 'C', 'N', 'S1', 'S2')

    def __init__(self, identifier, height=16, relative_x=0, phase='A', ampacity=220,
                 geometrical_mean_radius=0.0039, resistance=0.0003937, diameter=0.01):
        """Initialize Wire"""
        self._locked = False  # unlocked by default
        self._display_name = None
        self.identifier = identifier
        self.height = height
        self.relative_x = relative_x
        self.phase = phase
        self.ampacity = ampacity
        self.geometrical_mean_radius = geometrical_mean_radius
        self.resistance = resistance
        self.diameter = diameter

    @classmethod
    def from_dict(cls, data):
        """Create a Wire object from a dictionary.

        Args:
            data: A dictionary representation of a Wire object in the format below.

        .. code-block:: python

            {
            'type': 'Wire',
            'identifier': 'OH AL 2/0 A',  # unique wire property identifier
            'height': 16,  # height of the wire above the ground in meters
            'relative_x': 0,  # number for the x offset from the wire line in meters
            'phase': 'A',  # text for the phase of the wire
            'ampacity': 220,  # ampacity of the wire in amps
            'geometrical_mean_radius': 0.0039,  # gmr in meters
            'resistance': 0.0003937,  # resistance of the wire in ohms/m
            'diameter': 0.01  # diameter of the wire in meters
            }
        """
        height = data['height'] if 'height' in data else 16
        rel_x = data['relative_x'] if 'relative_x' in data else 0
        phase = data['phase'] if 'phase' in data else 'A'
        amp = data['ampacity'] if 'ampacity' in data else 220
        gmr = data['geometrical_mean_radius'] if 'geometrical_mean_radius' in data \
            else 0.0039
        res = data['resistance'] if 'resistance' in data else 0.0003937
        dim = data['diameter'] if 'diameter' in data else 0.01
        wire = cls(data['identifier'], height, rel_x, phase, amp, gmr, res, dim)
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
            'height': 16,  # height of the wire above the ground in meters
            'x': 0,  # number for the x offset from the wire line in meters
            'phase': 'A',  # text for the phase of the wire
            'ampacity': 220,  # ampacity of the wire in amps
            'gmr': 0.0039,  # gmr in meters
            'resistance': 0.0003937,  # resistance of the wire in ohms/m
            'diameter': 0.01  # diameter of the wire in meters
            }
        """
        return cls(
            data['nameclass'], data['height'], data['x'], data['phase'],
            data['ampacity'], data['gmr'], data['resistance'], data['diameter'])

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
    def height(self):
        """Get or set a number for the height above the ground in meters."""
        return self._height

    @height.setter
    def height(self, value):
        self._height = float_in_range(value, input_name='height')

    @property
    def relative_x(self):
        """Get or set a number for the X offset relative to the wire line in meters."""
        return self._relative_x

    @relative_x.setter
    def relative_x(self, value):
        self._relative_x = float_in_range(value, input_name='relative_x')

    @property
    def phase(self):
        """Get or set text for the phase of the wire."""
        return self._phase

    @phase.setter
    def phase(self, value):
        assert value in self.VALID_PHASES, 'Phase "{}" is not acceptable. ' \
            'Choose from the following:\n{}'.format(value, '\n'.join(self.VALID_PHASES))
        self._phase = value

    @property
    def ampacity(self):
        """Get or set a number for the ampacity of the wire in amps."""
        return self._ampacity

    @ampacity.setter
    def ampacity(self, value):
        self._ampacity = float_positive(value, 'ampacity')

    @property
    def geometrical_mean_radius(self):
        """Get or set a number for the geometrical mean radius of the wire in meters."""
        return self._geometrical_mean_radius

    @geometrical_mean_radius.setter
    def geometrical_mean_radius(self, value):
        self._geometrical_mean_radius = float_positive(value, 'geometrical_mean_radius')

    @property
    def resistance(self):
        """Get or set a number for the resistance of the wire in ohms per meter of wire.
        """
        return self._resistance

    @resistance.setter
    def resistance(self, value):
        self._resistance = float_positive(value, 'resistance')

    @property
    def diameter(self):
        """Get or set a number for the diameter of the wire in meters."""
        return self._diameter

    @diameter.setter
    def diameter(self, value):
        self._diameter = float_positive(value, 'diameter')

    def to_dict(self):
        """Get Wire dictionary."""
        base = {
            'type': 'Wire',
            'identifier': self.identifier,
            'height': self.height,
            'relative_x': self.relative_x,
            'phase': self.phase,
            'ampacity': self.ampacity,
            'geometrical_mean_radius': self.geometrical_mean_radius,
            'resistance': self.resistance,
            'diameter': self.diameter}
        if self._display_name is not None:
            base['display_name'] = self._display_name
        return base

    def to_electrical_database_dict(self):
        """Get Wire as it should appear in the URBANopt electrical_database.json."""
        return {
            'nameclass': self.identifier,
            'height': self.height,
            'x': self.relative_x,
            'phase': self.phase,
            'ampacity': self.ampacity,
            'gmr': self.geometrical_mean_radius,
            'resistance': self.resistance,
            'diameter': self.diameter
        }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_obj = Wire(
            self.identifier, self.height, self.relative_x, self.phase, self.ampacity,
            self.geometrical_mean_radius, self.resistance, self.diameter)
        new_obj._display_name = self._display_name
        return new_obj

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (
            self.identifier, self.height, self.relative_x, self.phase, self.ampacity,
            self.geometrical_mean_radius, self.resistance, self.diameter)

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
