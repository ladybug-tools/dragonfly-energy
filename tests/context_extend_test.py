"""Tests the features that dragonfly_energy adds to dragonfly_core ContextShade."""
from dragonfly.context import ContextShade

from dragonfly_energy.properties.context import ContextShadeEnergyProperties

from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.schedule.ruleset import ScheduleRuleset

import honeybee_energy.lib.scheduletypelimits as schedule_types

from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.face import Face3D


def test_energy_properties():
    """Test the existence of the ContextShade energy properties."""
    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    tree_canopy = ContextShade('TreeCanopy', [tree_canopy_geo1, tree_canopy_geo2])

    assert hasattr(tree_canopy.properties, 'energy')
    assert isinstance(tree_canopy.properties.energy, ContextShadeEnergyProperties)
    assert isinstance(tree_canopy.properties.energy.construction, ShadeConstruction)
    assert tree_canopy.properties.energy.transmittance_schedule is None


def test_set_construction_schedule():
    """Test the setting of a Construction and Schedule on a ContextShade."""
    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    tree_canopy = ContextShade('TreeCanopy', [tree_canopy_geo1, tree_canopy_geo2])

    bright_leaves = ShadeConstruction('Bright Light Leaves', 0.5, 0.5, True)
    tree_trans = ScheduleRuleset.from_constant_value(
        'Tree Transmittance', 0.5, schedule_types.fractional)
    
    tree_canopy.properties.energy.construction = bright_leaves
    tree_canopy.properties.energy.transmittance_schedule = tree_trans

    assert tree_canopy.properties.energy.construction == bright_leaves
    assert tree_canopy.properties.energy.transmittance_schedule == tree_trans


def test_duplicate():
    """Test what happens to energy properties when duplicating a Room2D."""
    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    shade_original = ContextShade('TreeCanopy', [tree_canopy_geo1, tree_canopy_geo2])
    shade_dup_1 = shade_original.duplicate()

    bright_leaves = ShadeConstruction('Bright Light Leaves', 0.5, 0.5, True)
    tree_trans = ScheduleRuleset.from_constant_value(
        'Tree Transmittance', 0.5, schedule_types.fractional)

    assert shade_original.properties.energy.host is shade_original
    assert shade_dup_1.properties.energy.host is shade_dup_1
    assert shade_original.properties.energy.host is not \
        shade_dup_1.properties.energy.host

    assert shade_original.properties.energy.construction == \
        shade_dup_1.properties.energy.construction
    shade_dup_1.properties.energy.construction = bright_leaves
    assert shade_original.properties.energy.construction != \
        shade_dup_1.properties.energy.construction

    shade_dup_2 = shade_dup_1.duplicate()

    assert shade_dup_1.properties.energy.construction == \
        shade_dup_2.properties.energy.construction
    shade_dup_2.properties.energy.construction = None
    assert shade_dup_1.properties.energy.construction != \
        shade_dup_2.properties.energy.construction


def test_to_dict():
    """Test the Building to_dict method with energy properties."""
    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    tree_canopy = ContextShade('TreeCanopy', [tree_canopy_geo1, tree_canopy_geo2])

    sd = tree_canopy.to_dict()
    assert 'properties' in sd
    assert sd['properties']['type'] == 'ContextShadeProperties'
    assert 'energy' in sd['properties']
    assert sd['properties']['energy']['type'] == 'ContextShadeEnergyProperties'
    assert 'construction' not in sd['properties']['energy'] or \
        sd['properties']['energy']['construction'] is None

    bright_leaves = ShadeConstruction('Bright Light Leaves', 0.5, 0.5, True)
    tree_trans = ScheduleRuleset.from_constant_value(
        'Tree Transmittance', 0.5, schedule_types.fractional)
    tree_canopy.properties.energy.construction = bright_leaves
    tree_canopy.properties.energy.transmittance_schedule = tree_trans

    sd = tree_canopy.to_dict()
    assert sd['properties']['energy']['construction'] is not None
    assert sd['properties']['energy']['transmittance_schedule'] is not None


def test_from_dict():
    """Test the Story from_dict method with energy properties."""
    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    tree_canopy = ContextShade('TreeCanopy', [tree_canopy_geo1, tree_canopy_geo2])

    bright_leaves = ShadeConstruction('Bright Light Leaves', 0.5, 0.5, True)
    tree_trans = ScheduleRuleset.from_constant_value(
        'Tree Transmittance', 0.5, schedule_types.fractional)
    tree_canopy.properties.energy.construction = bright_leaves
    tree_canopy.properties.energy.transmittance_schedule = tree_trans

    sd = tree_canopy.to_dict()
    new_shd = ContextShade.from_dict(sd)
    assert new_shd.properties.energy.construction == bright_leaves
    assert new_shd.properties.energy.transmittance_schedule == tree_trans
    assert new_shd.to_dict() == sd
