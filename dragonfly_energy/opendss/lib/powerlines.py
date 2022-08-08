"""Library of power lines that come standard with dragonfly."""
import os
import json

from ..powerline import PowerLine
from .wires import _wires


# load the  defaults
_power_lines = {}
_data_path = os.path.join(os.path.dirname(__file__), 'extended_catalog.json')
with open(_data_path) as json_file:
    _all_data = json.load(json_file)['LINES']
    _default_data = _all_data[1]['#Interurban Zone A:'] + \
        _all_data[2]['#Urban-Overhead'] + _all_data[3]['#Urban-Underground']
for _t_dict in _default_data:
    _t_obj = PowerLine.from_electrical_database_dict(_t_dict, _wires)
    _t_obj.lock()
    _power_lines[_t_dict['Name']] = _t_obj

POWER_LINES = tuple(_power_lines.keys())


def power_line_by_identifier(power_line_identifier):
    """Get power line properties from the library given the identifier.

    Args:
        power_line_identifier: A text string for the identifier of the power line.
    """
    try:
        return _power_lines[power_line_identifier]
    except KeyError:
        raise ValueError(
            '"{}" was not found in the power line library.'.format(
                power_line_identifier))
