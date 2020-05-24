# coding=utf-8
import pytest

from dragonfly_energy.run import base_honeybee_osw

from dragonfly.model import Model
from dragonfly.building import Building
from dragonfly.story import Story
from dragonfly.room2d import Room2D
from dragonfly.context import ContextShade
from dragonfly.windowparameter import SimpleWindowRatio

from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.measure import Measure
from honeybee_energy.lib.programtypes import office_program

from ladybug.location import Location
from ladybug.futil import nukedir

from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.face import Face3D

import os
import json


def test_base_honeybee_osw():
    """Test the simulation of an urban model with URBANopt."""
    pts_1 = (Point3D(50, 50, 3), Point3D(60, 50, 3), Point3D(60, 60, 3), Point3D(50, 60, 3))
    pts_2 = (Point3D(60, 50, 3), Point3D(70, 50, 3), Point3D(70, 60, 3), Point3D(60, 60, 3))
    pts_3 = (Point3D(50, 70, 3), Point3D(70, 70, 3), Point3D(70, 80, 3), Point3D(50, 80, 3))
    room2d_1 = Room2D('Residence1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Residence2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Retail', Face3D(pts_3), 3)
    story_big = Story('RetailFloor', [room2d_3])
    story = Story('ResidenceFloor', [room2d_1, room2d_2])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story.multiplier = 3
    building = Building('ResidenceBuilding', [story])
    story_big.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story_big.multiplier = 1
    building_big = Building('RetailBuildingBig', [story_big])

    pts_1 = (Point3D(0, 0, 3), Point3D(0, 5, 3), Point3D(15, 5, 3), Point3D(15, 0, 3))
    pts_2 = (Point3D(15, 0, 3), Point3D(15, 15, 3), Point3D(20, 15, 3), Point3D(20, 0, 3))
    pts_3 = (Point3D(0, 5, 3), Point3D(0, 20, 3), Point3D(5, 20, 3), Point3D(5, 5, 3))
    pts_4 = (Point3D(5, 15, 3), Point3D(5, 20, 3), Point3D(20, 20, 3), Point3D(20, 15, 3))
    pts_5 = (Point3D(-5, -5, 3), Point3D(-10, -5, 3), Point3D(-10, -10, 3), Point3D(-5, -10, 3))
    room2d_1 = Room2D('Office1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office4', Face3D(pts_4), 3)
    room2d_5 = Room2D('Office5', Face3D(pts_5), 3)
    int_rms = Room2D.intersect_adjacency(
        [room2d_1, room2d_2, room2d_3, room2d_4, room2d_5], 0.01)
    story = Story('OfficeFloor', int_rms)
    story.rotate_xy(5, Point3D(0, 0, 0))
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story.multiplier = 5
    building_mult = Building('OfficeBuilding', [story])

    # set program type
    building.properties.energy.set_all_room_2d_program_type(office_program)
    building_big.properties.energy.set_all_room_2d_program_type(office_program)
    building_mult.properties.energy.set_all_room_2d_program_type(office_program)

    # get context shade
    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    tree_canopy = ContextShade('TreeCanopy', [tree_canopy_geo1, tree_canopy_geo2])

    # create the Model object
    model = Model('TestGeoJSON', [building, building_big, building_mult], [tree_canopy])

    # create the urbanopt feature geoJSON
    location = Location('Boston', 'MA', 'USA', 42.366151, -71.019357)
    sim_folder = './tests/simulation'
    geojson, hb_model_jsons, hb_models = \
        model.to.urbanopt(model, location, folder=sim_folder)
    
    # create the simulation parameters
    sim_par = SimulationParameter()
    sim_par.output.add_zone_energy_use()
    ddy_file = './tests/epw/chicago.ddy'
    sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
    simpar_json_path = './tests/simulation/simulation_parameter.json'
    with open(simpar_json_path, 'w') as fp:
        json.dump(sim_par.to_dict(), fp)

    # load up an additional measure to include
    measure_path = './tests/measure/edit_fraction_radiant_of_lighting_and_equipment'
    measure = Measure(measure_path)
    measure.arguments[0].value = 0.25
    measure.arguments[1].value = 0.25

    # create the honeybee osw
    epw_file = './tests/epw/chicago.epw'
    base_workflow = base_honeybee_osw(
        sim_folder, simpar_json_path, additional_measures=[measure], epw_file=epw_file)

    assert os.path.isfile(base_workflow)

    # clean up the files
    nukedir(sim_folder, True)
