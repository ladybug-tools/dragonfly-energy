# coding=utf-8
"""PowerLine in OpenDSS."""
from __future__ import division

from honeybee._lockable import lockable
from honeybee.typing import float_in_range, float_positive, int_positive, valid_ep_string

from .wire import Wire


@lockable
class PowerLine(object):
    """Represents the properties of a power line in OpenDSS.

    Args:
        identifier: Text string for a unique wire property ID. Must contain only
            characters that are acceptable in OpenDSS. This will be used to
            identify the object across the exported geoJSON and OpenDSS files.
        wires: An array of Wire objects for the wires contained within the power line.
        heights: An array of numbers that align with the wires and denote the height
            of the wire above the ground in meters. Negative values indicate wires
            below ground.
        relative_xs: An array of numbers that align with the wires and denote the
            X offset relative to the wire line geometry in meters. For convenience,
            one of the conductors in a given wire is usually assigned the 0 position.
        phases: An array of text values that align with the wires and denote the
            phases of the wire. Must be one of the following values (A, B, C, N, S1, S2).
        phase_count: An optional integer for the number of phases carried along the
            power line. If None, it wil be inferred from the phases with only
            phases A, B, C considered distinct from one another. (Default: None).
        nominal_voltage: An optional number for the nominal voltage along the
            power line. This is not required for OpenDSS simulation since this
            value can be inferred from surrounding transformers and substations
            but it it sometimes useful to assign a value directly to the
            power line object. (Default: None).

    Properties:
        * identifier
        * display_name
        * wires
        * heights
        * relative_xs
        * phases
        * phase_count
        * nominal_voltage
        * wire_count
        * wire_ids
    """
    __slots__ = (
        '_locked', '_display_name', '_identifier', '_wire_count', '_wires', '_heights',
        '_relative_xs', '_phases', '_phase_count', '_nominal_voltage'
    )
    VALID_PHASES = ('A', 'B', 'C', 'N', 'S1', 'S2')

    def __init__(self, identifier, wires, heights, relative_xs, phases,
                 phase_count=None, nominal_voltage=None):
        """Initialize PowerLine"""
        self._locked = False  # unlocked by default
        self._display_name = None
        self.identifier = identifier
        self._wire_count = len(wires)
        assert self._wire_count > 0, 'PowerLine must possess at least one wire.'
        self.wires = wires
        self.heights = heights
        self.relative_xs = relative_xs
        self.phases = phases
        self.phase_count = phase_count
        self.nominal_voltage = nominal_voltage

    @classmethod
    def from_dict(cls, data):
        """Create a PowerLine object from a dictionary.

        Args:
            data: A dictionary representation of a PowerLine object in the format below.

        .. code-block:: python

            {
            'type': 'PowerLine',
            'identifier': '3P_OH_AL_ACSR_477kcmil_Hawk_12_47_0',  # unique identifier
            'wires': [{}],  # a list of wire definitions for the wires in the line
            'heights': [16],  # height of the wire above the ground in meters
            'relative_x': [0],  # number for the x offset from the wire line in meters
            'phases': ['A']  # text for the phases of the wire
            }
        """
        wires = [Wire.from_dict(wd) for wd in data['wires']]
        pc = data['phase_count'] if 'phase_count' in data else None
        vol = data['nominal_voltage'] if 'nominal_voltage' in data else None
        p_line = cls(data['identifier'], wires, data['heights'],
                     data['relative_xs'], data['phases'], pc, vol)
        if 'display_name' in data and data['display_name'] is not None:
            p_line.display_name = data['display_name']
        return p_line

    @classmethod
    def from_dict_abridged(cls, data, wires):
        """Create a PowerLine object from a dictionary.

        Args:
            data: A dictionary representation of a PowerLine object in the format below.
            wires: A dictionary with identifiers of wires as keys and Python
                wire objects as values.

        .. code-block:: python

            {
            'type': 'PowerLine',
            'identifier': '3P_OH_AL_ACSR_477kcmil_Hawk_12_47_0',  # unique identifier
            'wires': [''],  # a list of wire identifiers for the wires in the line
            'heights': [16],  # height of the wire above the ground in meters
            'relative_x': [0],  # number for the x offset from the wire line in meters
            'phases': ['A']  # text for the phases of the wire
            }
        """
        try:
            wires = [wires[wd] for wd in data['wires']]
        except KeyError as e:
            raise ValueError('Failed to find {} in wires.'.format(e))
        pc = data['phase_count'] if 'phase_count' in data else None
        vol = data['nominal_voltage'] if 'nominal_voltage' in data else None
        p_line = cls(data['identifier'], wires, data['heights'],
                     data['relative_xs'], data['phases'], pc, vol)
        if 'display_name' in data and data['display_name'] is not None:
            p_line.display_name = data['display_name']
        return p_line

    @classmethod
    def from_electrical_database_dict(cls, data, wires):
        """Create a PowerLine from an dictionary as it appears in a database.json.

        Args:
            data: A dictionary representation of a PowerLine object in the format below.
            wires: A dictionary with identifiers of wires as keys and Python
                wire objects as values.

        .. code-block:: python

            {
            'Name': '3P_OH_AL_ACSR_336kcmil_Merlin_12_47_0',  # unique identifier
            "Line geometry": [
                    {
                        "wire": "OH ACSR 336kcmil",
                        "phase": "A",
                        "x (m)": 0.0,
                        "height (m)": 10
                    },
                    {
                        "wire": "OH ACSR 336kcmil",
                        "phase": "B",
                        "x (m)": 0.304,
                        "height (m)": 10
                    }
                ]
            }
        """
        try:
            wire_ids = [w_i['wire'] for w_i in data['Line geometry']]
            wire_objs = [wires[w_id] for w_id in wire_ids]
        except KeyError as e:
            raise ValueError('Failed to find {} in wires.'.format(e))
        heights = [w_i['height (m)'] for w_i in data['Line geometry']]
        rel_xs = [w_i['x (m)'] for w_i in data['Line geometry']]
        phases = [w_i['phase'] for w_i in data['Line geometry']]
        pc = data['Nphases'] if 'Nphases' in data else None
        vol = data['Voltage(kV)'] if 'Voltage(kV)' in data else None
        return cls(data['Name'], wire_objs, heights, rel_xs, phases, pc, vol)

    @property
    def identifier(self):
        """Get or set a text string for the unique object identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, value):
        self._identifier = valid_ep_string(value, 'power line identifier')

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
    def wires(self):
        """Get or set an array of Wire objects for the phases of the wires."""
        return self._wires

    @wires.setter
    def wires(self, value):
        for w in value:
            assert isinstance(w, Wire), 'Expected Wire object. Got {}.'.format(type(w))
        self._wires = tuple(value)
        assert len(self._wires) == self._wire_count, \
            'Number of wires cannot be changed from {} to {}. Initialize a new ' \
            'PowerLine object to change the number of wires.'.format(
                len(self._wires), self._wire_count)

    @property
    def heights(self):
        """Get or set an array of numbers for the heights above the ground in meters."""
        return self._heights

    @heights.setter
    def heights(self, value):
        self._heights = tuple(
            float_in_range(h, input_name='power line height') for h in value)
        assert len(self._heights) == self._wire_count, \
            'Number of heights [{}] does not match the number of wires [{}].'.format(
                len(self._heights), self._wire_count)

    @property
    def relative_xs(self):
        """Get or set a array of numbers for the X offset relative to the wire in meters.
        """
        return self._relative_xs

    @relative_xs.setter
    def relative_xs(self, value):
        self._relative_xs = tuple(
            float_in_range(x, input_name='power line relative_x') for x in value)
        assert len(self._relative_xs) == self._wire_count, \
            'Number of heights [{}] does not match the number of wires [{}].'.format(
                len(self._relative_xs), self._wire_count)

    @property
    def phases(self):
        """Get or set an array of text for the phases of the wires."""
        return self._phases

    @phases.setter
    def phases(self, value):
        for p in value:
            assert p in self.VALID_PHASES, 'Phase "{}" is not acceptable. ' \
                'Choose from the following:\n{}'.format(p, '\n'.join(self.VALID_PHASES))
        self._phases = tuple(value)
        assert len(self._phases) == self._wire_count, \
            'Number of heights [{}] does not match the number of wires [{}].'.format(
                len(self._phases), self._wire_count)

    @property
    def phase_count(self):
        """Get or set an integer for the number of phases carried along the line."""
        if self._phase_count is not None:
            return self._phase_count
        all_phases = [p for p in self._phases if p in ('A', 'B', 'C')]
        return len(all_phases) if len(all_phases) != 0 else 1

    @phase_count.setter
    def phase_count(self, value):
        if value is not None:
            value = int_positive(value, 'power line phase count')
        self._phase_count = value

    @property
    def nominal_voltage(self):
        """Get or set a number for nominal voltage of the power line in kiloVolts."""
        return self._nominal_voltage

    @nominal_voltage.setter
    def nominal_voltage(self, value):
        if value is not None:
            value = float_positive(value, 'nominal voltage')
        self._nominal_voltage = value

    @property
    def wire_count(self):
        """Get an integer for the number of wires in the power line."""
        return self._wire_count

    @property
    def wire_ids(self):
        """Get a list of wire identifiers in the power line."""
        return [wire.identifier for wire in self._wires]

    def to_dict(self, abridged=False):
        """Get PowerLine dictionary.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True),
                which only specifies the identifiers of wires. (Default: False).
        """
        base = {'type': 'PowerLine'} if not abridged else {'type': 'PowerLineAbridged'}
        base['identifier'] = self.identifier
        base['wires'] = self.wire_ids if abridged else [w.to_dict() for w in self.wires]
        base['heights'] = self.heights
        base['relative_xs'] = self.relative_xs
        base['phases'] = self.phases
        if self._phase_count is not None:
            base['phase_count'] = self._phase_count
        if self._nominal_voltage is not None:
            base['nominal_voltage'] = self._nominal_voltage
        if self._display_name is not None:
            base['display_name'] = self._display_name
        return base

    def to_electrical_database_dict(self):
        """Get Wire as it should appear in the URBANopt database.json."""
        base = {'Name': self.identifier}
        line_geo = []
        all_props = zip(self.wires, self.heights, self.relative_xs, self.phases)
        for wire, hgt, r_x, pha in all_props:
            w_dict = {
                'wire': wire.identifier,
                'phase': pha,
                'x (m)': r_x,
                'height (m)': hgt
            }
            line_geo.append(w_dict)
        base['Line geometry'] = line_geo
        if self._phase_count is not None:
            base['Nphases'] = self._phase_count
        if self._nominal_voltage is not None:
            base['Voltage(kV)'] = self._nominal_voltage
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_obj = PowerLine(
            self.identifier, self.wires, self.heights, self.relative_xs, self.phases,
            self._phase_count, self._nominal_voltage)
        new_obj._display_name = self._display_name
        return new_obj

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.identifier,) + tuple(hash(w) for w in self.wires) + \
            self.heights + self.relative_xs + self.phases + \
            (self._phase_count, self._nominal_voltage)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, PowerLine) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        return len(self._wires)

    def __getitem__(self, key):
        return self._wires[key]

    def __iter__(self):
        return iter(self._wires)

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent wire."""
        return 'PowerLine: {}'.format(self.identifier)
