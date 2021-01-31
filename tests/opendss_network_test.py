# coding=utf-8
from dragonfly_energy.opendss.network import ElectricalNetwork
from dragonfly_energy.opendss.substation import Substation
from dragonfly_energy.opendss.transformer import Transformer
from dragonfly_energy.opendss.connector import ElectricalConnector
from dragonfly_energy.opendss.junction import ElectricalJunction
from dragonfly_energy.opendss.transformerprop import TransformerProperties
from dragonfly_energy.opendss.wire import Wire

from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane

import json


def test_network_init():
    """Test the initialization of ElectricalNetwork and basic properties."""
    network_json = './tests/json/buffalo_electric_grid.json'
    with open(network_json) as json_file:
        data = json.load(json_file)
    network = ElectricalNetwork.from_dict(data)
    str(network)  # test the string representation

    assert isinstance(network.substation, Substation)
    for trans in network.transformers:
        assert isinstance(trans, Transformer)
    for conn in network.connectors:
        assert isinstance(conn, ElectricalConnector)
    for tp in network.transformer_properties:
        assert isinstance(tp, TransformerProperties)
    for wire in network.wires:
        assert isinstance(wire, Wire)
    junctions, _ = network.junctions()
    for jct in junctions:
        assert isinstance(jct, ElectricalJunction)


def test_network_transform():
    """Test the ElectricalNetwork transform methods."""
    network_json = './tests/json/buffalo_electric_grid.json'
    with open(network_json) as json_file:
        data = json.load(json_file)
    network = ElectricalNetwork.from_dict(data)

    new_network = network.duplicate()
    new_network.move(Vector3D(100, 0))
    assert new_network.substation.geometry[0] != network.substation.geometry[0]
    assert new_network.transformers[0].geometry[0] != network.transformers[0].geometry[0]
    assert new_network.connectors[0].geometry.vertices[0] != \
        network.connectors[0].geometry.vertices[0]

    new_network = network.duplicate()
    new_network.rotate_xy(90, Point3D())
    assert new_network.substation.geometry[0] != network.substation.geometry[0]
    assert new_network.transformers[0].geometry[0] != network.transformers[0].geometry[0]
    assert new_network.connectors[0].geometry.vertices[0] != \
        network.connectors[0].geometry.vertices[0]

    new_network = network.duplicate()
    new_network.reflect(Plane(n=Vector3D(1, 0)))
    assert new_network.substation.geometry[0] != network.substation.geometry[0]
    assert new_network.transformers[0].geometry[0] != network.transformers[0].geometry[0]
    assert new_network.connectors[0].geometry.vertices[0] != \
        network.connectors[0].geometry.vertices[0]

    new_network = network.duplicate()
    new_network.scale(0.5)
    assert new_network.substation.geometry[0] != network.substation.geometry[0]
    assert new_network.transformers[0].geometry[0] != network.transformers[0].geometry[0]
    assert new_network.connectors[0].geometry.vertices[0] != \
        network.connectors[0].geometry.vertices[0]


def test_network_dict_methods():
    """Test the ElectricalNetwork to/from dict methods."""
    network_json = './tests/json/buffalo_electric_grid.json'
    with open(network_json) as json_file:
        data = json.load(json_file)
    network = ElectricalNetwork.from_dict(data)

    network_dict = network.to_dict()
    new_network = ElectricalNetwork.from_dict(network_dict)
    assert network_dict == new_network.to_dict()
