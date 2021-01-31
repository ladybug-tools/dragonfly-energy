# coding=utf-8
from dragonfly_energy.opendss.transformer import Transformer
from dragonfly_energy.opendss.transformerprop import TransformerProperties

from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.polygon import Polygon2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane

import pytest


def test_transformer_init():
    """Test the initialization of Transformer and basic properties."""
    pts = (Point2D(0, 0), Point2D(2, 0), Point2D(2, 2), Point2D(0, 2))
    polygon = Polygon2D(pts)
    tp = TransformerProperties('Transformer--25KVA CT', 25)
    transformer = Transformer('Transformer_1', polygon, tp)
    str(transformer)  # test the string representation

    assert transformer.identifier == 'Transformer_1'
    assert transformer.geometry == polygon
    assert transformer.properties == tp


def test_transformer_transform():
    """Test the Transformer transform methods."""
    pts = (Point2D(0, 0), Point2D(2, 0), Point2D(2, 2), Point2D(0, 2))
    polygon = Polygon2D(pts)
    tp = TransformerProperties('Transformer--25KVA CT', 25)
    transformer = Transformer('Transformer_1', polygon, tp)

    new_transformer = transformer.duplicate()
    new_transformer.move(Vector3D(100, 0))
    assert new_transformer.geometry[0] == Point2D(100, 0)

    new_transformer = transformer.duplicate()
    new_transformer.rotate_xy(90, Point3D())
    assert new_transformer.geometry[1].y == pytest.approx(2, rel=1e-3)

    new_transformer = transformer.duplicate()
    new_transformer.reflect(Plane(n=Vector3D(1, 0)))
    assert new_transformer.geometry[1].x == pytest.approx(-2, rel=1e-3)

    new_transformer = transformer.duplicate()
    new_transformer.scale(0.5)
    assert new_transformer.geometry[1].x == pytest.approx(1, rel=1e-3)


def test_transformer_dict_methods():
    """Test the Transformer to/from dict methods."""
    pts = (Point2D(0, 0), Point2D(2, 0), Point2D(2, 2), Point2D(0, 2))
    polygon = Polygon2D(pts)
    tp = TransformerProperties('Transformer--25KVA CT', 25)
    transformer = Transformer('Transformer_1', polygon, tp)

    transformer_dict = transformer.to_dict()
    new_transformer = Transformer.from_dict(transformer_dict)
    assert transformer_dict == new_transformer.to_dict()
