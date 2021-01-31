"""Library of transformer properties that come standard with dragonfly."""
from ..transformerprop import TransformerProperties

import os
import json

# load the  defaults
_transformers = {}
_data_path = os.path.join(os.path.dirname(__file__), 'electrical_database.json')
with open(_data_path) as json_file:
    _default_data = json.load(json_file)['transformer_properties']
for _t_dict in _default_data:
    _t_obj = TransformerProperties.from_electrical_database_dict(_t_dict)
    _t_obj.lock()
    _transformers[_t_dict['nameclass']] = _t_obj

TRANSFORMER_PROPERTIES = tuple(_transformers.keys())


def transformer_prop_by_identifier(transformer_identifier):
    """Get transformer properties from the library given the identifier.

    Args:
        transformer_identifier: A text string for the identifier of the transformer
            properties.
    """
    try:
        return _transformers[transformer_identifier]
    except KeyError:
        raise ValueError(
            '"{}" was not found in the transformer property library.'.format(
                transformer_identifier))
