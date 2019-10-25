# coding=utf-8
from dragonfly.building import Building
from dragonfly.story import Story
from dragonfly.room2d import Room2D
from dragonfly.glazingparameter import SimpleGlazingRatio

from dragonfly_energy.properties.building import BuildingEnergyProperties

from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.idealair import IdealAirSystem
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.material.opaque import EnergyMaterial
from honeybee_energy.lib.programtypes import office_program

from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_geometry.geometry3d.face import Face3D


def test_building_init():
    """Test the initalization of Building objects and basic properties."""
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    pts_3 = (Point3D(0, 10, 3), Point3D(0, 20, 3), Point3D(10, 20, 3), Point3D(10, 10, 3))
    pts_4 = (Point3D(10, 10, 3), Point3D(10, 20, 3), Point3D(20, 20, 3), Point3D(20, 10, 3))
    room2d_1 = Room2D('Office 1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office 2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office 3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office 4', Face3D(pts_4), 3)
    story = Story('Office Floor', [room2d_1, room2d_2, room2d_3, room2d_4])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_glazing_parameters(SimpleGlazingRatio(0.4))
    story.multiplier = 4
    building = Building('Office Building', [story])

    assert hasattr(building.properties, 'energy')
    assert isinstance(building.properties.energy, BuildingEnergyProperties)
    assert isinstance(building.properties.energy.construction_set, ConstructionSet)


def test_set_construction_set():
    """Test the setting of a ConstructionSet on a Building."""
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    pts_3 = (Point3D(0, 10, 3), Point3D(0, 20, 3), Point3D(10, 20, 3), Point3D(10, 10, 3))
    pts_4 = (Point3D(10, 10, 3), Point3D(10, 20, 3), Point3D(20, 20, 3), Point3D(20, 10, 3))
    room2d_1 = Room2D('Office 1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office 2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office 3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office 4', Face3D(pts_4), 3)
    story = Story('Office Floor', [room2d_1, room2d_2, room2d_3, room2d_4])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_glazing_parameters(SimpleGlazingRatio(0.4))
    story.multiplier = 4
    building = Building('Office Building', [story])

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

    building.properties.energy.construction_set = mass_set
    assert building.properties.energy.construction_set == mass_set
    assert building[0].properties.energy.construction_set == mass_set

    hb_model = building.to_honeybee()
    assert len(hb_model.properties.energy.construction_sets) == 1
    assert hb_model.properties.energy.construction_sets[0] == mass_set
    assert hb_model.rooms[0].properties.energy.construction_set == mass_set


def test_set_all_room_2d_program_type():
    """Test the set_all_room_2d_program_type method on a Story."""
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    pts_3 = (Point3D(0, 10, 3), Point3D(0, 20, 3), Point3D(10, 20, 3), Point3D(10, 10, 3))
    pts_4 = (Point3D(10, 10, 3), Point3D(10, 20, 3), Point3D(20, 20, 3), Point3D(20, 10, 3))
    room2d_1 = Room2D('Office 1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office 2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office 3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office 4', Face3D(pts_4), 3)
    story = Story('Office Floor', [room2d_1, room2d_2, room2d_3, room2d_4])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_glazing_parameters(SimpleGlazingRatio(0.4))
    story.multiplier = 4
    building = Building('Office Building', [story])

    lab_program = office_program.duplicate()
    lab_program.name = 'Bio Laboratory'
    lab_program.electric_equipment.watts_per_area = 50
    lab_program.ventilation.flow_per_person = 0
    lab_program.ventilation.flow_per_area = 0
    lab_program.ventilation.air_changes_per_hour = 6

    building.properties.energy.set_all_room_2d_program_type(lab_program)

    assert all(room_2d.properties.energy.program_type == lab_program
               for room_2d in building.unique_room_2ds)


def test_set_all_room_2d_hvac():
    """Test the set_all_room_2d_hvac method on a Story."""
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    pts_3 = (Point3D(0, 10, 3), Point3D(0, 20, 3), Point3D(10, 20, 3), Point3D(10, 10, 3))
    pts_4 = (Point3D(10, 10, 3), Point3D(10, 20, 3), Point3D(20, 20, 3), Point3D(20, 10, 3))
    room2d_1 = Room2D('Office 1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office 2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office 3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office 4', Face3D(pts_4), 3)
    story = Story('Office Floor', [room2d_1, room2d_2, room2d_3, room2d_4])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_glazing_parameters(SimpleGlazingRatio(0.4))
    story.multiplier = 4
    building = Building('Office Building', [story])

    sensible = 0.8
    latent = 0.7
    ideal_air_sys = IdealAirSystem(sensible_heat_recovery=sensible,
                                   latent_heat_recovery=latent)

    building.properties.energy.set_all_room_2d_hvac(ideal_air_sys)

    assert all(room.properties.energy.hvac == ideal_air_sys
               for room in building.unique_room_2ds)
    assert all(room.properties.energy.hvac.sensible_heat_recovery == sensible
               for room in building.unique_room_2ds)
    assert all(room.properties.energy.hvac.latent_heat_recovery == latent
               for room in building.unique_room_2ds)


def test_duplicate():
    """Test what happens to energy properties when duplicating a Room2D."""
    mass_set = ConstructionSet('Thermal Mass Construction Set')
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    pts_3 = (Point3D(0, 10, 3), Point3D(0, 20, 3), Point3D(10, 20, 3), Point3D(10, 10, 3))
    pts_4 = (Point3D(10, 10, 3), Point3D(10, 20, 3), Point3D(20, 20, 3), Point3D(20, 10, 3))
    room2d_1 = Room2D('Office 1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office 2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office 3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office 4', Face3D(pts_4), 3)
    story = Story('Office Floor', [room2d_1, room2d_2, room2d_3, room2d_4])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_glazing_parameters(SimpleGlazingRatio(0.4))
    story.multiplier = 4
    building_original = Building('Office Building', [story])
    building_dup_1 = building_original.duplicate()

    assert building_original.properties.energy.host is building_original
    assert building_dup_1.properties.energy.host is building_dup_1
    assert building_original.properties.energy.host is not \
        building_dup_1.properties.energy.host

    assert building_original.properties.energy.construction_set == \
        building_dup_1.properties.energy.construction_set
    building_dup_1.properties.energy.construction_set = mass_set
    assert building_original.properties.energy.construction_set != \
        building_dup_1.properties.energy.construction_set

    room_dup_2 = building_dup_1.duplicate()

    assert building_dup_1.properties.energy.construction_set == \
        room_dup_2.properties.energy.construction_set
    room_dup_2.properties.energy.construction_set = None
    assert building_dup_1.properties.energy.construction_set != \
        room_dup_2.properties.energy.construction_set


def test_to_dict():
    """Test the Story to_dict method with energy properties."""
    mass_set = ConstructionSet('Thermal Mass Construction Set')
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    pts_3 = (Point3D(0, 10, 3), Point3D(0, 20, 3), Point3D(10, 20, 3), Point3D(10, 10, 3))
    pts_4 = (Point3D(10, 10, 3), Point3D(10, 20, 3), Point3D(20, 20, 3), Point3D(20, 10, 3))
    room2d_1 = Room2D('Office 1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office 2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office 3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office 4', Face3D(pts_4), 3)
    story = Story('Office Floor', [room2d_1, room2d_2, room2d_3, room2d_4])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_glazing_parameters(SimpleGlazingRatio(0.4))
    story.multiplier = 4
    building = Building('Office Building', [story])

    bd = building.to_dict()
    assert 'properties' in bd
    assert bd['properties']['type'] == 'BuildingProperties'
    assert 'energy' in bd['properties']
    assert bd['properties']['energy']['type'] == 'BuildingEnergyProperties'
    assert 'construction_set' not in bd['properties']['energy'] or \
        bd['properties']['energy']['construction_set'] is None

    building.properties.energy.construction_set = mass_set
    bd = building.to_dict()
    assert bd['properties']['energy']['construction_set'] is not None


def test_from_dict():
    """Test the Story from_dict method with energy properties."""
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    pts_3 = (Point3D(0, 10, 3), Point3D(0, 20, 3), Point3D(10, 20, 3), Point3D(10, 10, 3))
    pts_4 = (Point3D(10, 10, 3), Point3D(10, 20, 3), Point3D(20, 20, 3), Point3D(20, 10, 3))
    room2d_1 = Room2D('Office 1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office 2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office 3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office 4', Face3D(pts_4), 3)
    story = Story('Office Floor', [room2d_1, room2d_2, room2d_3, room2d_4])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_glazing_parameters(SimpleGlazingRatio(0.4))
    story.multiplier = 4
    building = Building('Office Building', [story])

    mass_set = ConstructionSet('Thermal Mass Construction Set')
    building.properties.energy.construction_set = mass_set

    bd = building.to_dict()
    new_bldg = Building.from_dict(bd)
    assert new_bldg.properties.energy.construction_set.name == \
        'Thermal Mass Construction Set'
    assert new_bldg.to_dict() == bd
