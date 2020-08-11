# coding=utf-8
from dragonfly.building import Building
from dragonfly.story import Story
from dragonfly.room2d import Room2D
from dragonfly.windowparameter import SimpleWindowRatio

from dragonfly_energy.properties.building import BuildingEnergyProperties

from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.material.opaque import EnergyMaterial
from honeybee_energy.lib.programtypes import office_program
from honeybee_energy.programtype import ProgramType
from honeybee_energy.load.people import People
from honeybee_energy.load.lighting import Lighting
from honeybee_energy.load.equipment import ElectricEquipment
from honeybee_energy.load.infiltration import Infiltration
from honeybee_energy.load.ventilation import Ventilation
from honeybee_energy.load.setpoint import Setpoint
from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.ruleset import ScheduleRuleset

import honeybee_energy.lib.scheduletypelimits as schedule_types

from ladybug.dt import Time

from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_geometry.geometry3d.face import Face3D

import pytest


def test_building_init():
    """Test the initalization of Building objects and basic properties."""
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
    building = Building('OfficeBuilding', [story])

    assert hasattr(building.properties, 'energy')
    assert isinstance(building.properties.energy, BuildingEnergyProperties)
    assert isinstance(building.properties.energy.construction_set, ConstructionSet)


def test_set_construction_set():
    """Test the setting of a ConstructionSet on a Building."""
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
    building = Building('OfficeBuilding', [story])

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
    """Test the set_all_room_2d_program_type method on a Building."""
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
    building = Building('OfficeBuilding', [story])

    lab_program = office_program.duplicate()
    lab_program.identifier = 'Bio Laboratory'
    lab_program.electric_equipment.watts_per_area = 50
    lab_program.ventilation.flow_per_person = 0
    lab_program.ventilation.flow_per_area = 0
    lab_program.ventilation.air_changes_per_hour = 6

    building.properties.energy.set_all_room_2d_program_type(lab_program)

    assert all(room_2d.properties.energy.program_type == lab_program
               for room_2d in building.unique_room_2ds)


def test_set_all_room_2d_hvac():
    """Test the set_all_room_2d_hvac method on a Building."""
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
    building = Building('OfficeBuilding', [story])

    sensible = 0.8
    latent = 0.7
    ideal_air_sys = IdealAirSystem('Office Ideal Air', sensible_heat_recovery=sensible,
                                   latent_heat_recovery=latent)

    building.properties.energy.set_all_room_2d_hvac(ideal_air_sys, False)

    assert all(isinstance(room.properties.energy.hvac, IdealAirSystem)
               for room in building.unique_room_2ds)
    assert all(room.properties.energy.hvac.sensible_heat_recovery == sensible
               for room in building.unique_room_2ds)
    assert all(room.properties.energy.hvac.latent_heat_recovery == latent
               for room in building.unique_room_2ds)


def test_averaged_program_type():
    """Test the averaged_program_type method."""
    pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
    pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
    room2d_1 = Room2D('Office1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office2', Face3D(pts_2), 3)

    simple_office = ScheduleDay('Simple Weekday Occupancy', [0, 1, 0],
                                [Time(0, 0), Time(9, 0), Time(17, 0)])
    occ_schedule = ScheduleRuleset('Office Occupancy Schedule', simple_office,
                                   None, schedule_types.fractional)
    light_schedule = occ_schedule.duplicate()
    light_schedule.identifier = 'Office Lighting-Equip Schedule'
    light_schedule.default_day_schedule.values = [0.25, 1, 0.25]
    equip_schedule = light_schedule.duplicate()
    inf_schedule = ScheduleRuleset.from_constant_value(
        'Infiltration Schedule', 1, schedule_types.fractional)
    heat_setpt = ScheduleRuleset.from_constant_value(
        'Office Heating Schedule', 21, schedule_types.temperature)
    cool_setpt = ScheduleRuleset.from_constant_value(
        'Office Cooling Schedule', 24, schedule_types.temperature)

    people = People('Open Office People', 0.05, occ_schedule)
    lighting = Lighting('Open Office Lighting', 10, light_schedule)
    equipment = ElectricEquipment('Open Office Equipment', 10, equip_schedule)
    infiltration = Infiltration('Office Infiltration', 0.0002, inf_schedule)
    ventilation = Ventilation('Office Ventilation', 0.005, 0.0003)
    setpoint = Setpoint('Office Setpoints', heat_setpt, cool_setpt)
    office_program = ProgramType('Open Office Program', people, lighting, equipment,
                                 None, infiltration, ventilation, setpoint)
    plenum_program = ProgramType('Plenum Program')

    room2d_1.properties.energy.program_type = office_program
    room2d_2.properties.energy.program_type = plenum_program

    story = Story('OfficeFloor', [room2d_1, room2d_2])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story.multiplier = 4
    building = Building('OfficeBuilding', [story])

    office_avg = building.properties.energy.averaged_program_type('Office Avg Program')

    assert office_avg.people.people_per_area == pytest.approx(0.025, rel=1e-3)
    assert office_avg.people.occupancy_schedule.default_day_schedule.values == \
        office_program.people.occupancy_schedule.default_day_schedule.values
    assert office_avg.people.latent_fraction == \
        office_program.people.latent_fraction
    assert office_avg.people.radiant_fraction == \
        office_program.people.radiant_fraction

    assert office_avg.lighting.watts_per_area == pytest.approx(5, rel=1e-3)
    assert office_avg.lighting.schedule.default_day_schedule.values == \
        office_program.lighting.schedule.default_day_schedule.values
    assert office_avg.lighting.return_air_fraction == \
        office_program.lighting.return_air_fraction
    assert office_avg.lighting.radiant_fraction == \
        office_program.lighting.radiant_fraction
    assert office_avg.lighting.visible_fraction == \
        office_program.lighting.visible_fraction

    assert office_avg.electric_equipment.watts_per_area == pytest.approx(5, rel=1e-3)
    assert office_avg.electric_equipment.schedule.default_day_schedule.values == \
        office_program.electric_equipment.schedule.default_day_schedule.values
    assert office_avg.electric_equipment.radiant_fraction == \
        office_program.electric_equipment.radiant_fraction
    assert office_avg.electric_equipment.latent_fraction == \
        office_program.electric_equipment.latent_fraction
    assert office_avg.electric_equipment.lost_fraction == \
        office_program.electric_equipment.lost_fraction

    assert office_avg.gas_equipment is None

    assert office_avg.infiltration.flow_per_exterior_area == \
        pytest.approx(0.0001, rel=1e-3)
    assert office_avg.infiltration.schedule.default_day_schedule.values == \
        office_program.infiltration.schedule.default_day_schedule.values
    assert office_avg.infiltration.constant_coefficient == \
        office_program.infiltration.constant_coefficient
    assert office_avg.infiltration.temperature_coefficient == \
        office_program.infiltration.temperature_coefficient
    assert office_avg.infiltration.velocity_coefficient == \
        office_program.infiltration.velocity_coefficient

    assert office_avg.ventilation.flow_per_person == pytest.approx(0.0025, rel=1e-3)
    assert office_avg.ventilation.flow_per_area == pytest.approx(0.00015, rel=1e-3)
    assert office_avg.ventilation.flow_per_zone == pytest.approx(0, rel=1e-3)
    assert office_avg.ventilation.air_changes_per_hour == pytest.approx(0, rel=1e-3)
    assert office_avg.ventilation.schedule is None

    assert office_avg.setpoint.heating_setpoint == pytest.approx(21, rel=1e-3)
    assert office_avg.setpoint.cooling_setpoint == pytest.approx(24, rel=1e-3)


def test_duplicate():
    """Test what happens to energy properties during duplication."""
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
    story.multiplier = 4
    building_original = Building('OfficeBuilding', [story])
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

    building_dup_2 = building_dup_1.duplicate()

    assert building_dup_1.properties.energy.construction_set == \
        building_dup_2.properties.energy.construction_set
    building_dup_2.properties.energy.construction_set = None
    assert building_dup_1.properties.energy.construction_set != \
        building_dup_2.properties.energy.construction_set


def test_to_dict():
    """Test the Building to_dict method with energy properties."""
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
    story.multiplier = 4
    building = Building('OfficeBuilding', [story])

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
    room2d_1 = Room2D('Office1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office4', Face3D(pts_4), 3)
    story = Story('OfficeFloor', [room2d_1, room2d_2, room2d_3, room2d_4])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story.multiplier = 4
    building = Building('OfficeBuilding', [story])

    mass_set = ConstructionSet('Thermal Mass Construction Set')
    building.properties.energy.construction_set = mass_set

    bd = building.to_dict()
    new_bldg = Building.from_dict(bd)
    assert new_bldg.properties.energy.construction_set.identifier == \
        'Thermal Mass Construction Set'
    assert new_bldg.to_dict() == bd
