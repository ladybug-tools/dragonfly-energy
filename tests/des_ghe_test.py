# coding=utf-8
from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.polygon import Polygon2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane

from dragonfly_energy.des.ghe import GroundHeatExchanger

import pytest


def test_ghe_init():
    """Test the initialization of GroundHeatExchanger and basic properties."""
    pts = (Point2D(0, 0), Point2D(2, 0), Point2D(2, 2), Point2D(0, 2))
    polygon = Polygon2D(pts)
    ghe = GroundHeatExchanger('GroundHeatExchanger_1', polygon)
    str(ghe)  # test the string representation

    assert ghe.identifier == 'GroundHeatExchanger_1'
    assert ghe.geometry == polygon


def test_ghe_transform():
    """Test the GroundHeatExchanger transform methods."""
    pts = (Point2D(0, 0), Point2D(2, 0), Point2D(2, 2), Point2D(0, 2))
    polygon = Polygon2D(pts)
    ghe = GroundHeatExchanger('GroundHeatExchanger_1', polygon)

    new_ghe = ghe.duplicate()
    new_ghe.move(Vector3D(100, 0))
    assert new_ghe.geometry[0] == Point2D(100, 0)

    new_ghe = ghe.duplicate()
    new_ghe.rotate_xy(90, Point3D())
    assert new_ghe.geometry[1].y == pytest.approx(2, rel=1e-3)

    new_ghe = ghe.duplicate()
    new_ghe.reflect(Plane(n=Vector3D(1, 0)))
    assert new_ghe.geometry[1].x == pytest.approx(-2, rel=1e-3)

    new_ghe = ghe.duplicate()
    new_ghe.scale(0.5)
    assert new_ghe.geometry[1].x == pytest.approx(1, rel=1e-3)


def test_ghe_dict_methods():
    """Test the GroundHeatExchanger to/from dict methods."""
    pts = (Point2D(0, 0), Point2D(2, 0), Point2D(2, 2), Point2D(0, 2))
    polygon = Polygon2D(pts)
    ghe = GroundHeatExchanger('GroundHeatExchanger_1', polygon)

    ghe_dict = ghe.to_dict()
    new_ghe = GroundHeatExchanger.from_dict(ghe_dict)
    assert ghe_dict == new_ghe.to_dict()
