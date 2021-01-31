"""Library of wires that come standard with dragonfly."""
from ..wire import Wire

import os
import json

# load the  defaults
_wires = {}
_data_path = os.path.join(os.path.dirname(__file__), 'electrical_database.json')
with open(_data_path) as json_file:
    _default_data = json.load(json_file)['wires']
for _t_dict in _default_data:
    _t_obj = Wire.from_electrical_database_dict(_t_dict)
    _t_obj.lock()
    _wires[_t_dict['nameclass']] = _t_obj

WIRES = tuple(_wires.keys())


def wire_by_identifier(wire_identifier):
    """Get wire properties from the library given the identifier.

    Args:
        wire_identifier: A text string for the identifier of the wire.
    """
    try:
        return _wires[wire_identifier]
    except KeyError:
        raise ValueError(
            '"{}" was not found in the wire property library.'.format(wire_identifier))
