"""Tests the features that dragonfly_energy adds to dragonfly_core Room2D."""
from dragonfly.room2d import Room2D
from dragonfly.windowparameter import SimpleWindowRatio
from dragonfly.shadingparameter import Overhang

from dragonfly_energy.properties.room2d import Room2DEnergyProperties

from honeybee.boundarycondition import boundary_conditions as bcs

from honeybee_energy.programtype import ProgramType
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.hvac.allair.vav import VAV
from honeybee_energy.ventcool.opening import VentilationOpening
from honeybee_energy.ventcool.control import VentilationControl
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.material.opaque import EnergyMaterial
from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.ruleset import ScheduleRuleset
import honeybee_energy.lib.scheduletypelimits as schedule_types
from honeybee_energy.lib.programtypes import office_program

from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_geometry.geometry3d.face import Face3D

from ladybug.dt import Time


def test_energy_properties():
    """Test the existence of the Room2D energy properties."""
    pts = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    ashrae_base = SimpleWindowRatio(0.4)
    overhang = Overhang(1)
    boundarycs = (bcs.outdoors, bcs.ground, bcs.outdoors, bcs.ground)
    window = (ashrae_base, None, ashrae_base, None)
    shading = (overhang, None, None, None)
    room = Room2D('SquareShoebox', Face3D(pts), 3, boundarycs, window, shading)

    room.properties.energy.program_type = office_program
    room.properties.energy.add_default_ideal_air()

    assert hasattr(room.properties, 'energy')
    assert isinstance(room.properties.energy, Room2DEnergyProperties)
    assert isinstance(room.properties.energy.construction_set, ConstructionSet)
    assert isinstance(room.properties.energy.program_type, ProgramType)
    assert isinstance(room.properties.energy.hvac, IdealAirSystem)
    assert room.properties.energy.program_type == office_program
    assert room.properties.energy.is_conditioned


def test_default_properties():
    """Test the auto-assigning of Room2D properties."""
    pts = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    ashrae_base = SimpleWindowRatio(0.4)
    room = Room2D('SquareShoebox', Face3D(pts), 3)
    room.set_outdoor_window_parameters(ashrae_base)

    assert room.properties.energy.construction_set.identifier == \
        'Default Generic Construction Set'
    assert room.properties.energy.program_type.identifier == 'Plenum'
    assert room.properties.energy.hvac is None
    assert not room.properties.energy.is_conditioned


def test_set_construction_set():
    """Test the setting of a ConstructionSet on a Room2D."""
    pts = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    ashrae_base = SimpleWindowRatio(0.4)
    overhang = Overhang(1)
    boundarycs = (bcs.outdoors, bcs.ground, bcs.outdoors, bcs.ground)
    window = (ashrae_base, None, ashrae_base, None)
    shading = (overhang, None, None, None)
    room = Room2D('SquareShoebox', Face3D(pts), 3, boundarycs, window, shading)

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

    room.properties.energy.construction_set = mass_set
    assert room.properties.energy.construction_set == mass_set

    hb_room, adj = room.to_honeybee()
    assert hb_room.properties.energy.construction_set == mass_set
    assert hb_room[1].properties.energy.construction == thick_constr
    assert hb_room[5].properties.energy.construction == thin_constr
    assert hb_room[1].shades[0].properties.energy.construction == shade_constr


def test_set_program_type():
    """Test the setting of a ProgramType on a Room2D."""
    lab_equip_day = ScheduleDay('Daily Lab Equipment', [0.25, 0.5, 0.25],
                                [Time(0, 0), Time(9, 0), Time(20, 0)])
    lab_equipment = ScheduleRuleset('Lab Equipment', lab_equip_day,
                                    None, schedule_types.fractional)
    lab_vent_day = ScheduleDay('Daily Lab Ventilation', [0.5, 1, 0.5],
                               [Time(0, 0), Time(9, 0), Time(20, 0)])
    lab_ventilation = ScheduleRuleset('Lab Ventilation', lab_vent_day,
                                      None, schedule_types.fractional)
    lab_program = office_program.duplicate()
    lab_program.identifier = 'Bio Laboratory'
    lab_program.electric_equipment.watts_per_area = 50
    lab_program.electric_equipment.schedule = lab_equipment
    lab_program.ventilation.flow_per_person = 0
    lab_program.ventilation.flow_per_area = 0
    lab_program.ventilation.air_changes_per_hour = 6
    lab_program.ventilation.schedule = lab_ventilation

    pts = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    ashrae_base = SimpleWindowRatio(0.4)
    room = Room2D('SquareShoebox', Face3D(pts), 3)
    room.set_outdoor_window_parameters(ashrae_base)

    room.properties.energy.program_type = lab_program

    assert room.properties.energy.program_type.identifier == 'Bio Laboratory'
    assert room.properties.energy.program_type == lab_program

    hb_room, adj = room.to_honeybee()
    assert hb_room.properties.energy.electric_equipment.watts_per_area == 50
    assert hb_room.properties.energy.electric_equipment.schedule == lab_equipment
    assert hb_room.properties.energy.ventilation.flow_per_person == 0
    assert hb_room.properties.energy.ventilation.flow_per_area == 0
    assert hb_room.properties.energy.ventilation.air_changes_per_hour == 6
    assert hb_room.properties.energy.ventilation.schedule == lab_ventilation


def test_set_ideal_air():
    """Test the setting of a IdealAirSystems on a Room2D."""
    pts = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    ashrae_base = SimpleWindowRatio(0.4)
    room = Room2D('SquareShoebox', Face3D(pts), 3)
    room.set_outdoor_window_parameters(ashrae_base)

    sensible = 0.8
    latent = 0.7
    ideal_air_sys = IdealAirSystem('Test HVAC', sensible_heat_recovery=sensible,
                                   latent_heat_recovery=latent)

    room.properties.energy.hvac = ideal_air_sys

    assert room.properties.energy.hvac == ideal_air_sys
    assert room.properties.energy.hvac.sensible_heat_recovery == sensible
    assert room.properties.energy.hvac.latent_heat_recovery == latent

    hb_room, adj = room.to_honeybee()
    assert hb_room.properties.energy.hvac == ideal_air_sys
    assert hb_room.properties.energy.hvac.sensible_heat_recovery == sensible
    assert hb_room.properties.energy.hvac.latent_heat_recovery == latent


def test_set_vav():
    """Test the setting of a VAV system on a Room2D."""
    pts = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    ashrae_base = SimpleWindowRatio(0.4)
    room = Room2D('SquareShoebox', Face3D(pts), 3)
    room.set_outdoor_window_parameters(ashrae_base)

    hvac_sys = VAV('Test HVAC')
    hvac_sys.economizer_type = 'DifferentialDryBulb'
    hvac_sys.sensible_heat_recovery = 0.8
    hvac_sys.latent_heat_recovery = 0.65

    room.properties.energy.hvac = hvac_sys

    assert room.properties.energy.hvac == hvac_sys
    assert room.properties.energy.hvac.sensible_heat_recovery == 0.8
    assert room.properties.energy.hvac.latent_heat_recovery == 0.65

    hb_room, adj = room.to_honeybee()
    assert hb_room.properties.energy.hvac == hvac_sys
    assert hb_room.properties.energy.hvac.economizer_type == 'DifferentialDryBulb'
    assert hb_room.properties.energy.hvac.sensible_heat_recovery == 0.8
    assert hb_room.properties.energy.hvac.latent_heat_recovery == 0.65


def test_set_window_opening():
    """Test the setting of window openings on a Room2D."""
    pts = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    ashrae_base = SimpleWindowRatio(0.4)
    room = Room2D('SquareShoebox', Face3D(pts), 3)
    room.set_outdoor_window_parameters(ashrae_base)

    ventilation = VentilationControl()
    ventilation.min_indoor_temperature = 22
    ventilation.max_indoor_temperature = 28
    ventilation.min_outdoor_temperature = 12
    ventilation.max_outdoor_temperature = 32
    ventilation.delta_temperature = 0

    opening = VentilationOpening()
    opening.fraction_area_operable = 0.25
    opening.fraction_height_operable = 0.5
    opening.wind_cross_vent = True

    room.properties.energy.window_vent_control = ventilation
    room.properties.energy.window_vent_opening = opening

    hb_room, adj = room.to_honeybee()
    assert hb_room.properties.energy.window_vent_control == ventilation
    assert hb_room[1].apertures[0].properties.energy.vent_opening == opening


def test_duplicate():
    """Test what happens to energy properties when duplicating a Room2D."""
    mass_set = ConstructionSet('Thermal Mass Construction Set')
    pts = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    ashrae_base = SimpleWindowRatio(0.4)
    room_original = Room2D('SquareShoebox', Face3D(pts), 3)
    room_original.set_outdoor_window_parameters(ashrae_base)
    room_dup_1 = room_original.duplicate()

    assert room_original.properties.energy.host is room_original
    assert room_dup_1.properties.energy.host is room_dup_1
    assert room_original.properties.energy.host is not \
        room_dup_1.properties.energy.host

    assert room_original.properties.energy.construction_set == \
        room_dup_1.properties.energy.construction_set
    room_dup_1.properties.energy.construction_set = mass_set
    assert room_original.properties.energy.construction_set != \
        room_dup_1.properties.energy.construction_set

    room_dup_2 = room_dup_1.duplicate()

    assert room_dup_1.properties.energy.construction_set == \
        room_dup_2.properties.energy.construction_set
    room_dup_2.properties.energy.construction_set = None
    assert room_dup_1.properties.energy.construction_set != \
        room_dup_2.properties.energy.construction_set


def test_to_dict():
    """Test the Room2D to_dict method with energy properties."""
    mass_set = ConstructionSet('Thermal Mass Construction Set')
    pts = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    ashrae_base = SimpleWindowRatio(0.4)
    overhang = Overhang(1)
    boundarycs = (bcs.outdoors, bcs.ground, bcs.outdoors, bcs.ground)
    window = (ashrae_base, None, ashrae_base, None)
    shading = (overhang, None, None, None)
    room = Room2D('ShoeBoxZone', Face3D(pts), 3, boundarycs, window, shading)

    rd = room.to_dict()
    assert 'properties' in rd
    assert rd['properties']['type'] == 'Room2DProperties'
    assert 'energy' in rd['properties']
    assert rd['properties']['energy']['type'] == 'Room2DEnergyProperties'
    assert 'program_type' not in rd['properties']['energy'] or \
        rd['properties']['energy']['program_type'] is None
    assert 'construction_set' not in rd['properties']['energy'] or \
        rd['properties']['energy']['construction_set'] is None
    assert 'hvac' not in rd['properties']['energy'] or \
        rd['properties']['energy']['hvac'] is None

    room.properties.energy.construction_set = mass_set
    room.properties.energy.program_type = office_program
    rd = room.to_dict()
    assert rd['properties']['energy']['construction_set'] is not None
    assert rd['properties']['energy']['program_type'] is not None


def test_from_dict():
    """Test the Room2D from_dict method with energy properties."""
    pts = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    ashrae_base = SimpleWindowRatio(0.4)
    room = Room2D('SquareShoebox', Face3D(pts), 3)
    room.set_outdoor_window_parameters(ashrae_base)

    mass_set = ConstructionSet('Thermal Mass Construction Set')
    room.properties.energy.construction_set = mass_set

    rd = room.to_dict()
    new_room = Room2D.from_dict(rd)
    assert new_room.properties.energy.construction_set.identifier == \
        'Thermal Mass Construction Set'
    assert new_room.to_dict() == rd


def test_from_dict_vent_opening():
    """Test the Room2D from_dict method with ventilation opening energy properties."""
    pts = (Point3D(0, 0, 3), Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(0, 10, 3))
    ashrae_base = SimpleWindowRatio(0.4)
    room = Room2D('SquareShoebox', Face3D(pts), 3)
    room.set_outdoor_window_parameters(ashrae_base)

    ventilation = VentilationControl()
    ventilation.min_indoor_temperature = 22
    ventilation.max_indoor_temperature = 28
    ventilation.min_outdoor_temperature = 12
    ventilation.max_outdoor_temperature = 32
    ventilation.delta_temperature = 0

    opening = VentilationOpening()
    opening.fraction_area_operable = 0.25
    opening.fraction_height_operable = 0.5
    opening.wind_cross_vent = True

    room.properties.energy.window_vent_control = ventilation
    room.properties.energy.window_vent_opening = opening

    rd = room.to_dict()
    new_room = Room2D.from_dict(rd)
    assert new_room.to_dict() == rd
