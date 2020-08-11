"""Tests the features that dragonfly_energy adds to dragonfly_core Story."""
from dragonfly.story import Story
from dragonfly.room2d import Room2D
from dragonfly.windowparameter import SimpleWindowRatio

from dragonfly_energy.properties.story import StoryEnergyProperties

from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.material.opaque import EnergyMaterial
from honeybee_energy.lib.programtypes import office_program

import honeybee.model as hb_model

from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_geometry.geometry3d.face import Face3D


def test_energy_properties():
    """Test the existence of the Story energy properties."""
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

    assert hasattr(story.properties, 'energy')
    assert isinstance(story.properties.energy, StoryEnergyProperties)
    assert isinstance(story.properties.energy.construction_set, ConstructionSet)


def test_set_construction_set():
    """Test the setting of a ConstructionSet on a Story."""
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

    mass_set = ConstructionSet('Thermal Mass Construction Set')
    concrete20 = EnergyMaterial('20cm Concrete', 0.2, 2.31, 2322, 832,
                                'MediumRough', 0.95, 0.75, 0.8)
    concrete10 = EnergyMaterial('10cm Concrete', 0.1, 2.31, 2322, 832,
                                'MediumRough', 0.95, 0.75, 0.8)
    thick_constr = OpaqueConstruction('Thick Concrete Construction', [concrete20])
    thin_constr = OpaqueConstruction('Thin Concrete Construction', [concrete10])
    shade_constr = ShadeConstruction('Light Shelf', 0.5, 0.5)
    mass_set.wall_set.exterior_construction = thick_constr
    mass_set.roof_ceiling_set.interior_construction = thin_constr
    mass_set.shade_construction = shade_constr

    story.properties.energy.construction_set = mass_set
    assert story.properties.energy.construction_set == mass_set
    assert story[0].properties.energy.construction_set == mass_set

    rooms = story.to_honeybee()
    model = hb_model.Model(story.identifier, rooms)
    assert len(model.properties.energy.construction_sets) == 1
    assert model.properties.energy.construction_sets[0] == mass_set
    assert model.rooms[0].properties.energy.construction_set == mass_set


def test_set_all_room_2d_program_type():
    """Test the set_all_room_2d_program_type method on a Story."""
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

    lab_program = office_program.duplicate()
    lab_program.identifier = 'Bio Laboratory'
    lab_program.electric_equipment.watts_per_area = 50
    lab_program.ventilation.flow_per_person = 0
    lab_program.ventilation.flow_per_area = 0
    lab_program.ventilation.air_changes_per_hour = 6

    story.properties.energy.set_all_room_2d_program_type(lab_program)

    assert all(room_2d.properties.energy.program_type == lab_program
               for room_2d in story.room_2ds)


def test_set_all_room_2d_hvac():
    """Test the set_all_room_2d_hvac method on a Story."""
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

    sensible = 0.8
    latent = 0.7
    ideal_air_sys = IdealAirSystem('Office HVAC', sensible_heat_recovery=sensible,
                                   latent_heat_recovery=latent)

    story.properties.energy.set_all_room_2d_hvac(ideal_air_sys, False)

    assert all(isinstance(room.properties.energy.hvac, IdealAirSystem)
               for room in story.room_2ds)
    assert all(room.properties.energy.hvac.sensible_heat_recovery == sensible
               for room in story.room_2ds)
    assert all(room.properties.energy.hvac.latent_heat_recovery == latent
               for room in story.room_2ds)


def test_duplicate():
    """Test what happens to energy properties when duplicating a Room2D."""
    mass_set = ConstructionSet('Thermal Mass Construction Set')
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    pts_3 = (Point3D(0, 10, 3), Point3D(0, 20, 3), Point3D(10, 20, 3), Point3D(10, 10, 3))
    pts_4 = (Point3D(10, 10, 3), Point3D(10, 20, 3), Point3D(20, 20, 3), Point3D(20, 10, 3))
    room2d_1 = Room2D('Office1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office4', Face3D(pts_4), 3)
    story_original = Story('OfficeFloor', [room2d_1, room2d_2, room2d_3, room2d_4])
    story_original.solve_room_2d_adjacency(0.01)
    story_original.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story_dup_1 = story_original.duplicate()

    assert story_original.properties.energy.host is story_original
    assert story_dup_1.properties.energy.host is story_dup_1
    assert story_original.properties.energy.host is not \
        story_dup_1.properties.energy.host

    assert story_original.properties.energy.construction_set == \
        story_dup_1.properties.energy.construction_set
    story_dup_1.properties.energy.construction_set = mass_set
    assert story_original.properties.energy.construction_set != \
        story_dup_1.properties.energy.construction_set

    room_dup_2 = story_dup_1.duplicate()

    assert story_dup_1.properties.energy.construction_set == \
        room_dup_2.properties.energy.construction_set
    room_dup_2.properties.energy.construction_set = None
    assert story_dup_1.properties.energy.construction_set != \
        room_dup_2.properties.energy.construction_set


def test_to_dict():
    """Test the Story to_dict method with energy properties."""
    mass_set = ConstructionSet('Thermal Mass Construction Set')
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

    sd = story.to_dict()
    assert 'properties' in sd
    assert sd['properties']['type'] == 'StoryProperties'
    assert 'energy' in sd['properties']
    assert sd['properties']['energy']['type'] == 'StoryEnergyProperties'
    assert 'construction_set' not in sd['properties']['energy'] or \
        sd['properties']['energy']['construction_set'] is None

    story.properties.energy.construction_set = mass_set
    sd = story.to_dict()
    assert sd['properties']['energy']['construction_set'] is not None


def test_from_dict():
    """Test the Story from_dict method with energy properties."""
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

    mass_set = ConstructionSet('Thermal Mass Construction Set')
    story.properties.energy.construction_set = mass_set

    sd = story.to_dict()
    new_story = Story.from_dict(sd)
    assert new_story.properties.energy.construction_set.identifier == \
        'Thermal Mass Construction Set'
    assert new_story.to_dict() == sd
