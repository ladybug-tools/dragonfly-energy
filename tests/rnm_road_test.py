# coding=utf-8
from dragonfly_energy.opendss.road import Road

from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane

import pytest


def test_road_init():
    """Test the initialization of Road and basic properties."""
    geo = LineSegment2D.from_end_points(Point2D(0, 0), Point2D(100, 0))
    road = Road('Sesame_Street', geo)
    str(road)  # test the string representation

    assert road.identifier == 'Sesame_Street'
    assert road.geometry == geo


def test_road_transform():
    """Test the Road transform methods."""
    geo = LineSegment2D.from_end_points(Point2D(0, 0), Point2D(100, 0))
    road = Road('Sesame_Street', geo)

    new_road = road.duplicate()
    new_road.move(Vector3D(100, 0))
    assert new_road.geometry.p1 == Point2D(100, 0)

    new_road = road.duplicate()
    new_road.rotate_xy(90, Point3D())
    assert new_road.geometry.p2.y == pytest.approx(100, rel=1e-3)

    new_road = road.duplicate()
    new_road.reflect(Plane(n=Vector3D(1, 0)))
    assert new_road.geometry.p2.x == pytest.approx(-100, rel=1e-3)

    new_road = road.duplicate()
    new_road.scale(0.5)
    assert new_road.geometry.p2.x == pytest.approx(50, rel=1e-3)


def test_road_dict_methods():
    """Test the Road to/from dict methods."""
    geo = LineSegment2D.from_end_points(Point2D(0, 0), Point2D(100, 0))
    road = Road('Sesame_Street', geo)

    road_dict = road.to_dict()
    new_road = Road.from_dict(road_dict)
    assert road_dict == new_road.to_dict()
