# coding=utf-8
from dragonfly_energy.opendss.substation import Substation

from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.polygon import Polygon2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane

import pytest


def test_substation_init():
    """Test the initialization of Substation and basic properties."""
    pts = (Point2D(0, 0), Point2D(2, 0), Point2D(2, 2), Point2D(0, 2))
    polygon = Polygon2D(pts)
    substation = Substation('Substation_1', polygon)
    str(substation)  # test the string representation

    assert substation.identifier == 'Substation_1'
    assert substation.geometry == polygon


def test_substation_transform():
    """Test the Substation transform methods."""
    pts = (Point2D(0, 0), Point2D(2, 0), Point2D(2, 2), Point2D(0, 2))
    polygon = Polygon2D(pts)
    substation = Substation('Substation_1', polygon)

    new_substation = substation.duplicate()
    new_substation.move(Vector3D(100, 0))
    assert new_substation.geometry[0] == Point2D(100, 0)

    new_substation = substation.duplicate()
    new_substation.rotate_xy(90, Point3D())
    assert new_substation.geometry[1].y == pytest.approx(2, rel=1e-3)

    new_substation = substation.duplicate()
    new_substation.reflect(Plane(n=Vector3D(1, 0)))
    assert new_substation.geometry[1].x == pytest.approx(-2, rel=1e-3)

    new_substation = substation.duplicate()
    new_substation.scale(0.5)
    assert new_substation.geometry[1].x == pytest.approx(1, rel=1e-3)


def test_substation_dict_methods():
    """Test the Substation to/from dict methods."""
    pts = (Point2D(0, 0), Point2D(2, 0), Point2D(2, 2), Point2D(0, 2))
    polygon = Polygon2D(pts)
    substation = Substation('Substation_1', polygon)

    substation_dict = substation.to_dict()
    new_substation = Substation.from_dict(substation_dict)
    assert substation_dict == new_substation.to_dict()
