# coding=utf-8
import pytest

from dragonfly.model import Model
from dragonfly.building import Building
from dragonfly.story import Story
from dragonfly.room2d import Room2D
from dragonfly.context import ContextShade
from dragonfly.windowparameter import SimpleWindowRatio
from dragonfly.shadingparameter import Overhang

from dragonfly_energy.properties.model import ModelEnergyProperties

import honeybee.model as hb_model
from honeybee.boundarycondition import Outdoors, Surface

from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.window import WindowConstruction
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.construction.air import AirBoundaryConstruction
from honeybee_energy.material._base import _EnergyMaterialBase
from honeybee_energy.material.opaque import EnergyMaterial
from honeybee_energy.schedule.ruleset import ScheduleRuleset
from honeybee_energy.load.lighting import Lighting

from honeybee_energy.lib.programtypes import office_program, plenum_program
import honeybee_energy.lib.scheduletypelimits as schedule_types
from honeybee_energy.lib.materials import clear_glass, air_gap, roof_membrane, \
    wood, insulation
from honeybee_energy.lib.constructions import generic_exterior_wall, \
    generic_interior_wall, generic_interior_floor, generic_interior_ceiling, \
    generic_double_pane

from ladybug_geometry.geometry2d.pointvector import Point2D, Vector2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.face import Face3D


def test_energy_properties():
    """Test the existence of the Model energy properties."""
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    pts_3 = (Point3D(0, 10, 3), Point3D(0, 20, 3), Point3D(10, 20, 3), Point3D(10, 10, 3))
    pts_4 = (Point3D(10, 10, 3), Point3D(10, 20, 3), Point3D(20, 20, 3), Point3D(20, 10, 3))
    room2d_1 = Room2D('Office1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office4', Face3D(pts_4), 3)
    story = Story('OfficeFloor', [room2d_1, room2d_2, room2d_3, room2d_4])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story.multiplier = 4
    for room in story.room_2ds:
        room.properties.energy.program_type = office_program
        room.properties.energy.add_default_ideal_air()
    building = Building('OfficeBuilding', [story])

    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    tree_canopy = ContextShade('TreeCanopy', [tree_canopy_geo1, tree_canopy_geo2])
    bright_leaves = ShadeConstruction('Bright Light Leaves', 0.5, 0.5, True)
    tree_canopy.properties.energy.construction = bright_leaves
    tree_trans = ScheduleRuleset.from_constant_value(
        'Tree Transmittance', 0.5, schedule_types.fractional)
    tree_canopy.properties.energy.transmittance_schedule = tree_trans

    model = Model('NewDevelopment', [building], [tree_canopy])

    assert hasattr(model.properties, 'energy')
    assert isinstance(model.properties.energy, ModelEnergyProperties)
    assert isinstance(model.properties.host, Model)
    assert len(model.properties.energy.materials) == 15
    for mat in model.properties.energy.materials:
        assert isinstance(mat, _EnergyMaterialBase)
    assert len(model.properties.energy.constructions) == 16
    for cnst in model.properties.energy.constructions:
        assert isinstance(
            cnst, (WindowConstruction, OpaqueConstruction,
                   ShadeConstruction, AirBoundaryConstruction))
    assert len(model.properties.energy.shade_constructions) == 1
    assert len(model.properties.energy.construction_sets) == 0
    assert isinstance(model.properties.energy.global_construction_set, ConstructionSet)
    assert len(model.properties.energy.schedule_type_limits) == 3
    assert len(model.properties.energy.schedules) == 8
    assert len(model.properties.energy.shade_schedules) == 1
    assert len(model.properties.energy.program_types) == 1


def test_check_duplicate_construction_set_identifiers():
    """Test the check_duplicate_construction_set_identifiers method."""
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    room2d_1 = Room2D('Office1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office2', Face3D(pts_2), 3)
    story = Story('OfficeFloor', [room2d_1, room2d_2])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story.multiplier = 4
    for room in story.room_2ds:
        room.properties.energy.program_type = office_program
        room.properties.energy.add_default_ideal_air()
    building = Building('OfficeBuilding', [story])
    building.separate_top_bottom_floors()

    constr_set = ConstructionSet('Attic Construction Set')
    polyiso = EnergyMaterial('PolyIso', 0.2, 0.03, 43, 1210, 'MediumRough')
    roof_constr = OpaqueConstruction('Attic Roof Construction',
                                     [roof_membrane, polyiso, wood])
    floor_constr = OpaqueConstruction('Attic Floor Construction',
                                      [wood, insulation, wood])
    constr_set.floor_set.interior_construction = floor_constr
    constr_set.roof_ceiling_set.exterior_construction = roof_constr
    building.unique_room_2ds[-1].properties.energy.construction_set = constr_set
    building.unique_room_2ds[-2].properties.energy.construction_set = constr_set

    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    tree_canopy = ContextShade('TreeCanopy', [tree_canopy_geo1, tree_canopy_geo2])

    model = Model('NewDevelopment', [building], [tree_canopy])

    assert model.properties.energy.check_duplicate_construction_set_identifiers(False)
    constr_set.unlock()
    constr_set.identifier = 'Default Generic Construction Set'
    constr_set.lock()
    assert not model.properties.energy.check_duplicate_construction_set_identifiers(False)
    with pytest.raises(ValueError):
        model.properties.energy.check_duplicate_construction_set_identifiers(True)


def test_check_duplicate_program_type_identifiers():
    """Test the check_duplicate_program_type_identifiers method."""
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    room2d_1 = Room2D('Office1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office2', Face3D(pts_2), 3)
    story = Story('OfficeFloor', [room2d_1, room2d_2])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story.multiplier = 4
    for room in story.room_2ds:
        room.properties.energy.program_type = office_program
        room.properties.energy.add_default_ideal_air()
    building = Building('OfficeBuilding', [story])
    building.separate_top_bottom_floors()

    attic_program_type = plenum_program.duplicate()
    attic_program_type.identifier = 'Attic Space'
    schedule = ScheduleRuleset.from_constant_value(
        'Always Dim', 1, schedule_types.fractional)
    lighting = Lighting('Attic Lighting', 3, schedule)
    attic_program_type.lighting = lighting
    building.unique_room_2ds[-1].properties.energy.program_type = attic_program_type
    building.unique_room_2ds[-2].properties.energy.program_type = attic_program_type

    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    tree_canopy = ContextShade('TreeCanopy', [tree_canopy_geo1, tree_canopy_geo2])

    model = Model('NewDevelopment', [building], [tree_canopy])

    assert model.properties.energy.check_duplicate_program_type_identifiers(False)
    attic_program_type.unlock()
    attic_program_type.identifier = office_program.identifier
    attic_program_type.lock()
    assert not model.properties.energy.check_duplicate_program_type_identifiers(False)
    with pytest.raises(ValueError):
        model.properties.energy.check_duplicate_program_type_identifiers(True)


def test_to_from_dict():
    """Test the Model to_dict and from_dict method."""
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    room2d_1 = Room2D('Office1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office2', Face3D(pts_2), 3)
    story = Story('OfficeFloor', [room2d_1, room2d_2])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story.multiplier = 4
    for room in story.room_2ds:
        room.properties.energy.program_type = office_program
        room.properties.energy.add_default_ideal_air()
    building = Building('OfficeBuilding', [story])
    building.separate_top_bottom_floors()

    attic_program_type = plenum_program.duplicate()
    attic_program_type.identifier = 'Attic Space'
    schedule = ScheduleRuleset.from_constant_value(
        'Always Dim', 1, schedule_types.fractional)
    lighting = Lighting('Attic Lighting', 3, schedule)
    attic_program_type.lighting = lighting
    building.unique_room_2ds[-1].properties.energy.program_type = attic_program_type
    building.unique_room_2ds[-2].properties.energy.program_type = attic_program_type

    constr_set = ConstructionSet('Attic Construction Set')
    polyiso = EnergyMaterial('PolyIso', 0.2, 0.03, 43, 1210, 'MediumRough')
    roof_constr = OpaqueConstruction('Attic Roof Construction',
                                     [roof_membrane, polyiso, wood])
    floor_constr = OpaqueConstruction('Attic Floor Construction',
                                      [wood, insulation, wood])
    constr_set.floor_set.interior_construction = floor_constr
    constr_set.roof_ceiling_set.exterior_construction = roof_constr
    building.unique_room_2ds[-1].properties.energy.construction_set = constr_set
    building.unique_room_2ds[-2].properties.energy.construction_set = constr_set

    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    tree_canopy = ContextShade('TreeCanopy', [tree_canopy_geo1, tree_canopy_geo2])
    bright_leaves = ShadeConstruction('Bright Light Leaves', 0.5, 0.5, True)
    tree_canopy.properties.energy.construction = bright_leaves
    tree_trans = ScheduleRuleset.from_constant_value(
        'Tree Transmittance', 0.5, schedule_types.fractional)
    tree_canopy.properties.energy.transmittance_schedule = tree_trans

    model = Model('NewDevelopment', [building], [tree_canopy])

    model.north_angle = 15
    model_dict = model.to_dict()
    new_model = Model.from_dict(model_dict)
    assert model_dict == new_model.to_dict()

    assert polyiso in new_model.properties.energy.materials
    assert roof_constr in new_model.properties.energy.constructions
    assert floor_constr in new_model.properties.energy.constructions
    assert constr_set in new_model.properties.energy.construction_sets
    assert new_model.buildings[0].unique_room_2ds[-1].properties.energy.construction_set == constr_set

    assert schedule in new_model.properties.energy.schedules
    assert attic_program_type in new_model.properties.energy.program_types
    assert new_model.buildings[0].unique_room_2ds[-1].properties.energy.program_type == attic_program_type

    assert bright_leaves in new_model.properties.energy.constructions
    assert tree_trans in new_model.properties.energy.schedules
    assert new_model.context_shades[0].properties.energy.construction == bright_leaves
    assert new_model.context_shades[0].properties.energy.transmittance_schedule == tree_trans


def test_to_honeybee():
    """Test the Model to_honeybee method."""
    pts_1 = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(20, 0, 3), Point3D(20, 10, 3), Point3D(10, 10, 3))
    pts_3 = (Point3D(0, 20, 3), Point3D(20, 20, 3), Point3D(20, 30, 3), Point3D(0, 30, 3))
    room2d_1 = Room2D('Office1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office3', Face3D(pts_3), 3)
    story_big = Story('OfficeFloorBig', [room2d_3])
    story = Story('OfficeFloor', [room2d_1, room2d_2])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story.multiplier = 4
    building = Building('OfficeBuilding', [story])
    building.separate_top_bottom_floors()
    story_big.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story_big.multiplier = 4
    building_big = Building('OfficeBuildingBig', [story_big])
    building_big.separate_top_bottom_floors()

    attic_program_type = plenum_program.duplicate()
    attic_program_type.identifier = 'Attic Space'
    schedule = ScheduleRuleset.from_constant_value(
        'Always Dim', 1, schedule_types.fractional)
    lighting = Lighting('Attic Lighting', 3, schedule)
    attic_program_type.lighting = lighting
    building.unique_room_2ds[-1].properties.energy.program_type = attic_program_type
    building.unique_room_2ds[-2].properties.energy.program_type = attic_program_type

    constr_set = ConstructionSet('Attic Construction Set')
    polyiso = EnergyMaterial('PolyIso', 0.2, 0.03, 43, 1210, 'MediumRough')
    roof_constr = OpaqueConstruction('Attic Roof Construction',
                                     [roof_membrane, polyiso, wood])
    floor_constr = OpaqueConstruction('Attic Floor Construction',
                                      [wood, insulation, wood])
    constr_set.floor_set.interior_construction = floor_constr
    constr_set.roof_ceiling_set.exterior_construction = roof_constr
    building.unique_room_2ds[-1].properties.energy.construction_set = constr_set
    building.unique_room_2ds[-2].properties.energy.construction_set = constr_set
    
    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    tree_canopy = ContextShade('TreeCanopy', [tree_canopy_geo1, tree_canopy_geo2])
    bright_leaves = ShadeConstruction('Bright Light Leaves', 0.5, 0.5, True)
    tree_canopy.properties.energy.construction = bright_leaves
    tree_trans = ScheduleRuleset.from_constant_value(
        'Tree Transmittance', 0.5, schedule_types.fractional)
    tree_canopy.properties.energy.transmittance_schedule = tree_trans

    model = Model('NewDevelopment', [building, building_big], [tree_canopy])

    hb_models = model.to_honeybee('Building', 10, False, 0.01)
    assert len(hb_models) == 2

    assert polyiso in hb_models[0].properties.energy.materials
    assert roof_constr in hb_models[0].properties.energy.constructions
    assert floor_constr in hb_models[0].properties.energy.constructions
    assert constr_set in hb_models[0].properties.energy.construction_sets
    assert hb_models[0].rooms[-1].properties.energy.construction_set == constr_set

    assert polyiso not in hb_models[1].properties.energy.materials
    assert roof_constr not in hb_models[1].properties.energy.constructions
    assert floor_constr not in hb_models[1].properties.energy.constructions
    assert constr_set not in hb_models[1].properties.energy.construction_sets

    assert schedule in hb_models[0].properties.energy.schedules
    assert attic_program_type in hb_models[0].properties.energy.program_types
    assert hb_models[0].rooms[-1].properties.energy.program_type == attic_program_type

    assert schedule not in hb_models[1].properties.energy.schedules
    assert attic_program_type not in hb_models[1].properties.energy.program_types

    assert bright_leaves in hb_models[0].properties.energy.constructions
    assert tree_trans in hb_models[0].properties.energy.schedules
    assert hb_models[0].orphaned_shades[-1].properties.energy.construction == bright_leaves
    assert hb_models[0].orphaned_shades[-1].properties.energy.transmittance_schedule == tree_trans

    assert bright_leaves not in hb_models[-1].properties.energy.constructions
    assert tree_trans not in hb_models[-1].properties.energy.schedules
