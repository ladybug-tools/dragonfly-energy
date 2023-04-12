# coding=utf-8
from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane

from dragonfly_energy.des.connector import ThermalConnector

import pytest


def test_connector_init():
    """Test the initialization of ThermalConnector and basic properties."""
    geo = LineSegment2D.from_end_points(Point2D(0, 0), Point2D(100, 0))
    connector = ThermalConnector('Connector_1', geo)
    str(connector)  # test the string representation

    assert connector.identifier == 'Connector_1'
    assert connector.geometry == geo


def test_connector_transform():
    """Test the ThermalConnector transform methods."""
    geo = LineSegment2D.from_end_points(Point2D(0, 0), Point2D(100, 0))
    connector = ThermalConnector('Connector_1', geo)

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
    """Test the ThermalConnector to/from dict methods."""
    geo = LineSegment2D.from_end_points(Point2D(0, 0), Point2D(100, 0))
    connector = ThermalConnector('Connector_1', geo)

    connector_dict = connector.to_dict()
    new_connector = ThermalConnector.from_dict(connector_dict)
    assert connector_dict == new_connector.to_dict()
