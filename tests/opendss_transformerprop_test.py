# coding=utf-8
from dragonfly_energy.opendss.transformerprop import TransformerProperties
from dragonfly_energy.opendss.lib.transformers import TRANSFORMER_PROPERTIES, \
    transformer_prop_by_identifier


def test_tp_init():
    """Test the initialization of TransformerProperties and basic properties."""
    tp = TransformerProperties('Transformer--25KVA CT', 25)
    str(tp)  # test the string representation

    assert tp.identifier == 'Transformer--25KVA CT'
    assert tp.kva == 25
    assert tp.resistance == 0.1
    assert tp.reactance == 0.1
    assert tp.phases == ('A', 'B', 'C')
    assert tp.high_voltage == 13.2
    assert tp.low_voltage == 0.48
    assert not tp.is_center_tap
    assert tp.connection == 'Wye-Wye'


def test_tp_setability():
    """Test the setting of properties of TransformerProperties."""
    tp = TransformerProperties('Transformer--25KVA CT', 25)

    tp.identifier = 'Transformer--50KVA PM'
    assert tp.identifier == 'Transformer--50KVA PM'
    tp.kva = 50
    assert tp.kva == 50
    tp.resistance = 0.15
    assert tp.resistance == 0.15
    tp.reactance = 0.15
    assert tp.reactance == 0.15
    tp.phases = ('A',)
    assert tp.phases == ('A',)
    tp.high_voltage = 20
    assert tp.high_voltage == 20
    tp.low_voltage = 0.5
    assert tp.low_voltage == 0.5
    tp.is_center_tap = True
    assert tp.is_center_tap
    tp.connection = 'Delta-Delta'
    assert tp.connection == 'Delta-Delta'


def test_tp_equality():
    """Test the equality of Wire objects."""
    tp = TransformerProperties('Transformer--25KVA CT', 25)
    tp_dup = tp.duplicate()
    tp_alt = TransformerProperties('Transformer--50KVA CT', 50)

    assert tp is tp
    assert tp is not tp_dup
    assert tp == tp_dup
    tp_dup.kva = 100
    assert tp != tp_dup
    assert tp != tp_alt


def test_tp_dict_methods():
    """Test the to/from dict methods."""
    tp = TransformerProperties('Transformer--25KVA CT', 25)

    tp_dict = tp.to_dict()
    new_tp = TransformerProperties.from_dict(tp_dict)
    assert new_tp == tp
    assert tp_dict == new_tp.to_dict()


def test_tp_electrical_database_dict_methods():
    """Test the to/from electrical_database_dict methods."""
    tp = transformer_prop_by_identifier(TRANSFORMER_PROPERTIES[0])

    tp_dict = tp.to_electrical_database_dict()
    new_tp = TransformerProperties.from_electrical_database_dict(tp_dict)
    assert new_tp == tp
    assert tp_dict == new_tp.to_electrical_database_dict()
