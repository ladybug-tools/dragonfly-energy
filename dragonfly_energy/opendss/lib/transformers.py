"""Library of transformer properties that come standard with dragonfly."""
from ..transformerprop import TransformerProperties

import os
import json

# load the  defaults
_transformers = {}
_data_path = os.path.join(os.path.dirname(__file__), 'extended_catalog.json')
with open(_data_path) as json_file:
    _all_data = json.load(json_file)['SUBSTATIONS AND DISTRIBUTION TRANSFORMERS']
    for dat in reversed(_all_data):  # the last interurban one has transformers
        if '#Interurban:' in dat:
            _default_data = dat['#Interurban:']
            break
for _t_dict in _default_data:
    _t_obj = TransformerProperties.from_electrical_database_dict(_t_dict)
    _t_obj.lock()
    _transformers[_t_dict['Name']] = _t_obj

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
