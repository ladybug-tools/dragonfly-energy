# coding=utf-8
from dragonfly_energy.opendss.connector import ElectricalConnector
from dragonfly_energy.opendss.wire import Wire

from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane

import pytest


def test_connector_init():
    """Test the initialization of ElectricalConnector and basic properties."""
    geo = LineSegment2D.from_end_points(Point2D(0, 0), Point2D(100, 0))
    wire = Wire('OH AL 2/0 A')
    connector = ElectricalConnector('Connector_1', geo, [wire])
    str(connector)  # test the string representation

    assert connector.identifier == 'Connector_1'
    assert connector.geometry == geo
    assert len(connector) == 1
    assert len(connector.wires) == 1
    assert connector.wires[0] == wire
    assert connector[0] == wire
    assert connector.wire_ids == ['OH AL 2/0 A']


def test_connector_transform():
    """Test the ElectricalConnector transform methods."""
    geo = LineSegment2D.from_end_points(Point2D(0, 0), Point2D(100, 0))
    wire = Wire('OH AL 2/0 A')
    connector = ElectricalConnector('Connector_1', geo, [wire])

    new_connector = connector.duplicate()
    new_connector.move(Vector3D(100, 0))
    assert new_connector.geometry.p1 == Point2D(100, 0)

    new_connector = connector.duplicate()
    new_connector.rotate_xy(90, Point3D())
    assert new_connector.geometry.p2.y == pytest.approx(100, rel=1e-3)

    new_connector = connector.duplicate()
    new_connector.reflect(Plane(n=Vector3D(1, 0)))
    assert new_connector.geometry.p2.x == pytest.approx(-100, rel=1e-3)

    new_connector = connector.duplicate()
    new_connector.scale(0.5)
    assert new_connector.geometry.p2.x == pytest.approx(50, rel=1e-3)


def test_connector_dict_methods():
    """Test the ElectricalConnector to/from dict methods."""
    geo = LineSegment2D.from_end_points(Point2D(0, 0), Point2D(100, 0))
    wire = Wire('OH AL 2/0 A')
    connector = ElectricalConnector('Connector_1', geo, [wire])

    connector_dict = connector.to_dict()
    new_connector = ElectricalConnector.from_dict(connector_dict)
    assert connector_dict == new_connector.to_dict()
