# coding=utf-8
"""Transformer properties in OpenDSS."""
from __future__ import division

from honeybee._lockable import lockable
from honeybee.typing import float_positive, valid_ep_string


@lockable
class TransformerProperties(object):
    """Represents the properties of a Transformer in OpenDSS.

    Args:
        identifier: Text string for a unique wire property ID. Must contain only
            characters that are acceptable in OpenDSS. This will be used to
            identify the object across the exported geoJSON and OpenDSS files.
        kva:  Base kVA rating of the transformer in kiloVolt-Amps.
        resistance: A number for the electrical resistance of the transformer
            in ohms. (Default: 0.1).
        reactance: A number for the electrical reactance of the transformer
            in ohms. (Default: 0.1).
        phases: A list or tuple of letters (A, B or C) for the phases of the
            transformer. (Default: ('A', 'B', 'C')).
        high_voltage: A number for the high voltage of the transformer in
            kiloVolts. (Default: 13.2).
        low_voltage: A number for the low voltage of the transformer in
            kiloVolts. (Default: 0.48).
        is_center_tap: Boolean for whether the transformer is center-tapped
            (True) or not (False). (Default: False).
        connection: Text for the type of internal connection in the transformer, either
            "Wye-Wye", "Wye-Delta", "Delta-Wye" or "Delta-Delta". (Default: "Wye-Wye").

    Properties:
        * identifier
        * display_name
        * kva
        * resistance
        * reactance
        * phases
        * high_voltage
        * low_voltage
        * is_center_tap
        * connection
    """
    __slots__ = (
        '_locked', '_display_name', '_identifier', '_kva', '_resistance', '_reactance',
        '_phases', '_high_voltage', '_low_voltage', '_is_center_tap', '_connection')

    VALID_PHASES = ('A', 'B', 'C')
    VALID_CONNECTIONS = ('Wye-Wye', 'Wye-Delta', 'Delta-Wye', 'Delta-Delta')

    def __init__(self, identifier, kva, resistance=0.1, reactance=0.1,
                 phases=('A', 'B', 'C'), high_voltage=13.2, low_voltage=0.48,
                 is_center_tap=False, connection='Wye-Wye'):
        """Initialize TransformerProperties"""
        self._locked = False  # unlocked by default
        self._display_name = None
        self.identifier = identifier
        self.kva = kva
        self.resistance = resistance
        self.reactance = reactance
        self.phases = phases
        self.high_voltage = high_voltage
        self.low_voltage = low_voltage
        self.is_center_tap = is_center_tap
        self.connection = connection

    @classmethod
    def from_dict(cls, data):
        """Create a TransformerProperties object from a dictionary.

        Args:
            data: A dictionary representation of a TransformerProperties object
                in the format below.

        .. code-block:: python

            {
            'type': 'TransformerProperties',
            'identifier': 'Transformer--50KVA PM',  # unique identifier
            'kva': 50,  # kVA rating of the transformer
            'resistance': 0.1,  # transformer resistance in ohms
            'reactance': 0.1,  # transformer reactance in ohms
            'phases': ('A', 'B', 'C'),  # transformer phases
            'high_voltage': 13.2,  # transformer high voltage in kV
            'low_voltage': 0.48,  # transformer low voltage in kV
            'is_center_tap': False,  # boolean for if the transformer is center-tapped
            'connection': 'Wye-Wye'  # text for the type of connection
            }
        """
        resistance = data['resistance'] if 'resistance' in data else 0.1
        reactance = data['reactance'] if 'reactance' in data else 0.1
        phases = data['phases'] if 'phases' in data else ('A', 'B', 'C')
        hv = data['high_voltage'] if 'high_voltage' in data else 13.2
        lv = data['low_voltage'] if 'low_voltage' in data else 0.48
        icp = data['is_center_tap'] if 'is_center_tap' in data else False
        con = data['connection'] if 'connection' in data else 'Wye-Wye'
        wire = cls(data['identifier'], data['kva'], resistance, reactance,
                   phases, hv, lv, icp, con)
        if 'display_name' in data and data['display_name'] is not None:
            wire.display_name = data['display_name']
        return wire

    @classmethod
    def from_electrical_database_dict(cls, data):
        """Create from a dictionary as it appears in electrical_database.json.

        Args:
            data: A dictionary representation of an TransformerProperties object
                in the format below.

        .. code-block:: python

            {
            'nameclass': 'Transformer--50KVA PM',  # unique identifier
            'kva': 50,  # kVA rating of the transformer
            'resistance': 0.1,  # transformer resistance in ohms
            'reactance': 0.1,  # transformer reactance in ohms
            'phases': ('A', 'B', 'C'),  # transformer phases
            'high_voltage': 13.2,  # transformer high voltage in kV
            'low_voltage': 0.48,  # transformer low voltage in kV
            'is_center_tap': False,  # boolean for if the transformer is center-tapped
            'connection': 'Wye-Wye'  # text for the type of connection
            }
        """
        return cls(
            data['nameclass'], data['kva'], data['resistance'], data['reactance'],
            data['phases'], data['high_voltage'], data['low_voltage'],
            data['is_center_tap'], data['connection'])

    @property
    def identifier(self):
        """Get or set a text string for the unique object identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, value):
        self._identifier = valid_ep_string(value, 'transformer properties identifier')

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
    def kva(self):
        """Get or set a number for the base kVA rating of the transformer in kVA."""
        return self._kva

    @kva.setter
    def kva(self, value):
        self._kva = float_positive(value, input_name='kva')

    @property
    def resistance(self):
        """Get or set a number for the resistance of the tranformer in ohms."""
        return self._resistance

    @resistance.setter
    def resistance(self, value):
        self._resistance = float_positive(value, 'resistance')

    @property
    def reactance(self):
        """Get or set a number for the reactance of the tranformer in ohms."""
        return self._reactance

    @reactance.setter
    def reactance(self, value):
        self._reactance = float_positive(value, 'reactance')

    @property
    def phases(self):
        """Get or set a list or tuple of letters for the phases of the transformer."""
        return self._phases

    @phases.setter
    def phases(self, values):
        try:
            values = tuple(values)
        except TypeError:
            raise TypeError('Expected list or tuple for phases. '
                            'Got {}'.format(type(values)))
        for v in values:
            assert v in self.VALID_PHASES, 'Phase "{}" is not acceptable. Choose from ' \
                'the following:\n{}'.format(v, '\n'.join(self.VALID_PHASES))
        self._phases = values

    @property
    def high_voltage(self):
        """Get or set a number for the high voltage of the tranformer in kiloVolts."""
        return self._high_voltage

    @high_voltage.setter
    def high_voltage(self, value):
        self._high_voltage = float_positive(value, 'high voltage')

    @property
    def low_voltage(self):
        """Get or set a number for the low voltage of the tranformer in kiloVolts."""
        return self._low_voltage

    @low_voltage.setter
    def low_voltage(self, value):
        self._low_voltage = float_positive(value, 'low voltage')

    @property
    def is_center_tap(self):
        """Get or set a boolean for whether the transformer is center-tapped."""
        return self._is_center_tap

    @is_center_tap.setter
    def is_center_tap(self, value):
        self._is_center_tap = bool(value)

    @property
    def connection(self):
        """Get or set text for the type of internal connection in the transformer."""
        return self._connection

    @connection.setter
    def connection(self, value):
        assert value in self.VALID_CONNECTIONS, 'Phase "{}" is not acceptable. ' \
            'Choose from the following:\n{}'.format(
                value, '\n'.join(self.VALID_CONNECTIONS))
        self._connection = value

    def to_dict(self):
        """Get TransformerProperties dictionary."""
        base = {
            'type': 'TransformerProperties',
            'identifier': self.identifier,
            'kva': self.kva,
            'resistance': self.resistance,
            'reactance': self.reactance,
            'phases': self.phases,
            'high_voltage': self.high_voltage,
            'low_voltage': self.low_voltage,
            'is_center_tap': self.is_center_tap,
            'connection': self.connection}
        if self._display_name is not None:
            base['display_name'] = self._display_name
        return base

    def to_electrical_database_dict(self):
        """Get Wire as it should appear in the URBANopt electrical_database.json."""
        return {
            'nameclass': self.identifier,
            'kva': self.kva,
            'resistance': self.resistance,
            'reactance': self.reactance,
            'phases': self.phases,
            'high_voltage': self.high_voltage,
            'low_voltage': self.low_voltage,
            'is_center_tap': self.is_center_tap,
            'connection': self.connection
        }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_obj = TransformerProperties(
            self.identifier, self.kva, self.resistance, self.reactance, self.phases,
            self.high_voltage, self.low_voltage, self.is_center_tap, self.connection)
        new_obj._display_name = self._display_name
        return new_obj

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (
            self.identifier, self.kva, self.resistance, self.reactance,
            hash(self.phases), self.high_voltage, self.low_voltage,
            self.is_center_tap, self.connection)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, TransformerProperties) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent TransformerProperties."""
        return 'TransformerProperties: {}'.format(self.identifier)
