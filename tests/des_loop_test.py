# coding=utf-8
from dragonfly_energy.des.loop import GHEThermalLoop
from dragonfly_energy.des.ghe import GroundHeatExchanger
from dragonfly_energy.des.connector import ThermalConnector
from dragonfly_energy.des.junction import ThermalJunction

from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane

import json


def test_loop_init():
    """Test the initialization of GHEThermalLoop and basic properties."""
    loop_json = './tests/json/buffalo_ghe_des.json'
    with open(loop_json) as json_file:
        data = json.load(json_file)
    loop = GHEThermalLoop.from_dict(data)
    str(loop)  # test the string representation

    assert isinstance(loop.ground_heat_exchanger, GroundHeatExchanger)
    for conn in loop.connectors:
        assert isinstance(conn, ThermalConnector)
    junctions, _ = loop.junctions()
    for jct in junctions:
        assert isinstance(jct, ThermalJunction)


def test_loop_transform():
    """Test the GHEThermalLoop transform methods."""
    loop_json = './tests/json/buffalo_ghe_des.json'
    with open(loop_json) as json_file:
        data = json.load(json_file)
    loop = GHEThermalLoop.from_dict(data)

    new_loop = loop.duplicate()
    new_loop.move(Vector3D(100, 0))
    assert new_loop.ground_heat_exchanger.geometry[0] != \
        loop.ground_heat_exchanger.geometry[0]
    assert new_loop.connectors[0].geometry.vertices[0] != \
        loop.connectors[0].geometry.vertices[0]

    new_loop = loop.duplicate()
    new_loop.rotate_xy(90, Point3D())
    assert new_loop.ground_heat_exchanger.geometry[0] != \
        loop.ground_heat_exchanger.geometry[0]
    assert new_loop.connectors[0].geometry.vertices[0] != \
        loop.connectors[0].geometry.vertices[0]

    new_loop = loop.duplicate()
    new_loop.reflect(Plane(n=Vector3D(1, 0)))
    assert new_loop.ground_heat_exchanger.geometry[0] != \
        loop.ground_heat_exchanger.geometry[0]
    assert new_loop.connectors[0].geometry.vertices[0] != \
        loop.connectors[0].geometry.vertices[0]

    new_loop = loop.duplicate()
    new_loop.scale(0.5)
    assert new_loop.ground_heat_exchanger.geometry[0] != \
        loop.ground_heat_exchanger.geometry[0]
    assert new_loop.connectors[0].geometry.vertices[0] != \
        loop.connectors[0].geometry.vertices[0]


def test_loop_dict_methods():
    """Test the GHEThermalLoop to/from dict methods."""
    loop_json = './tests/json/buffalo_ghe_des.json'
    with open(loop_json) as json_file:
        data = json.load(json_file)
    loop = GHEThermalLoop.from_dict(data)

    loop_dict = loop.to_dict()
    new_loop = GHEThermalLoop.from_dict(loop_dict)
    assert loop_dict == new_loop.to_dict()
