# coding=utf-8
from dragonfly_energy.opendss.wire import Wire
from dragonfly_energy.opendss.lib.wires import WIRES, wire_by_identifier


def test_wire_init():
    """Test the initialization of Wire and basic properties."""
    wire = Wire('OH AL 2/0 A')
    str(wire)  # test the string representation

    assert wire.identifier == 'OH AL 2/0 A'
    assert wire.height == 16
    assert wire.relative_x == 0
    assert wire.phase == 'A'
    assert wire.ampacity == 220
    assert wire.geometrical_mean_radius == 0.0039
    assert wire.resistance == 0.0003937
    assert wire.diameter == 0.01


def test_wire_setability():
    """Test the setting of properties of Wire."""
    wire = Wire('OH AL 2/0 A')

    wire.identifier = 'OH AL 2/0 B'
    assert wire.identifier == 'OH AL 2/0 B'
    wire.height = -6
    assert wire.height == -6
    wire.relative_x = 1
    assert wire.relative_x == 1
    wire.phase = 'B'
    assert wire.phase == 'B'
    wire.ampacity = 200
    assert wire.ampacity == 200
    wire.geometrical_mean_radius = 0.004
    assert wire.geometrical_mean_radius == 0.004
    wire.resistance = 0.0004
    assert wire.resistance == 0.0004
    wire.diameter = 0.015
    assert wire.diameter == 0.015


def test_wire_equality():
    """Test the equality of Wire objects."""
    wire = Wire('OH AL 2/0 A')
    wire_dup = wire.duplicate()
    wire_alt = Wire('OH AL 2/0 A', -6)

    assert wire is wire
    assert wire is not wire_dup
    assert wire == wire_dup
    wire_dup.height = 17
    assert wire != wire_dup
    assert wire != wire_alt


def test_wire_dict_methods():
    """Test the to/from dict methods."""
    wire = Wire('OH AL 2/0 A', -6)

    wire_dict = wire.to_dict()
    new_wire = Wire.from_dict(wire_dict)
    assert new_wire == wire
    assert wire_dict == new_wire.to_dict()


def test_wire_electrical_database_dict_methods():
    """Test the to/from electrical_database_dict methods."""
    wire = wire_by_identifier(WIRES[0])

    wire_dict = wire.to_electrical_database_dict()
    new_wire = Wire.from_electrical_database_dict(wire_dict)
    assert new_wire == wire
    assert wire_dict == new_wire.to_electrical_database_dict()
