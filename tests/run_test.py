# coding=utf-8
import pytest

from dragonfly_energy.run import prepare_urbanopt_folder, run_urbanopt

from dragonfly.model import Model
from dragonfly.building import Building
from dragonfly.story import Story
from dragonfly.room2d import Room2D
from dragonfly.context import ContextShade
from dragonfly.windowparameter import SimpleWindowRatio

from honeybee_energy.run import to_openstudio_osw, run_osw
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.lib.constructionsets import construction_set_by_name
from honeybee_energy.lib.programtypes import program_type_by_name

from honeybee.config import folders

from ladybug.futil import preparedir, nukedir
from ladybug.location import Location
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.face import Face3D

import os
import json


def run_urban_model_with_urbanopt():
    """Test the simulation of an urban model with URBANopt."""
    # TODO: add 'test_' to the front of this method once CI can install URBANopt CLI
    pts_1 = (Point3D(50, 50, 3), Point3D(60, 50, 3), Point3D(60, 60, 3), Point3D(50, 60, 3))
    pts_2 = (Point3D(60, 50, 3), Point3D(70, 50, 3), Point3D(70, 60, 3), Point3D(60, 60, 3))
    pts_3 = (Point3D(50, 70, 3), Point3D(70, 70, 3), Point3D(70, 80, 3), Point3D(50, 80, 3))
    room2d_1 = Room2D('Residence 1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Residence 2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Retail', Face3D(pts_3), 3)
    story_big = Story('Retail Floor', [room2d_3])
    story = Story('Residence Floor', [room2d_1, room2d_2])
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story.multiplier = 3
    building = Building('Residence Building', [story])
    story_big.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story_big.multiplier = 1
    building_big = Building('Retail Building Big', [story_big])

    pts_1 = (Point3D(0, 0, 3), Point3D(0, 5, 3), Point3D(15, 5, 3), Point3D(15, 0, 3))
    pts_2 = (Point3D(15, 0, 3), Point3D(15, 15, 3), Point3D(20, 15, 3), Point3D(20, 0, 3))
    pts_3 = (Point3D(0, 5, 3), Point3D(0, 20, 3), Point3D(5, 20, 3), Point3D(5, 5, 3))
    pts_4 = (Point3D(5, 15, 3), Point3D(5, 20, 3), Point3D(20, 20, 3), Point3D(20, 15, 3))
    pts_5 = (Point3D(-5, -5, 3), Point3D(-10, -5, 3), Point3D(-10, -10, 3), Point3D(-5, -10, 3))
    room2d_1 = Room2D('Office 1', Face3D(pts_1), 3)
    room2d_2 = Room2D('Office 2', Face3D(pts_2), 3)
    room2d_3 = Room2D('Office 3', Face3D(pts_3), 3)
    room2d_4 = Room2D('Office 4', Face3D(pts_4), 3)
    room2d_5 = Room2D('Office 5', Face3D(pts_5), 3)
    int_rms = Room2D.intersect_adjacency(
        [room2d_1, room2d_2, room2d_3, room2d_4, room2d_5], 0.01)
    story = Story('Office Floor', int_rms)
    story.rotate_xy(5, Point3D(0, 0, 0))
    story.solve_room_2d_adjacency(0.01)
    story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
    story.multiplier = 5
    building_mult = Building('Office Building', [story])

    # set program type and construction set
    c_set = construction_set_by_name('2013::ClimateZone5::SteelFramed')
    building.properties.energy.construction_set = c_set
    building_big.properties.energy.construction_set = c_set
    building_mult.properties.energy.construction_set = c_set

    office_type = program_type_by_name('2013::LargeOffice::OpenOffice')
    residence_type = program_type_by_name('2013::MidriseApartment::Apartment')
    retail_type = program_type_by_name('2013::Retail::Retail')
    building.properties.energy.set_all_room_2d_program_type(residence_type)
    building_big.properties.energy.set_all_room_2d_program_type(retail_type)
    building_mult.properties.energy.set_all_room_2d_program_type(office_type)

    # get context shade
    tree_canopy_geo1 = Face3D.from_regular_polygon(6, 6, Plane(o=Point3D(5, -10, 6)))
    tree_canopy_geo2 = Face3D.from_regular_polygon(6, 2, Plane(o=Point3D(-5, -10, 3)))
    tree_canopy = ContextShade('Tree Canopy', [tree_canopy_geo1, tree_canopy_geo2])

    # create the Model object
    model = Model('TestGeoJSON', [building, building_big, building_mult], [tree_canopy])

    # get the geoJSON dictionary
    location = Location('Boston', 'MA', 'USA', 42.366151, -71.019357)
    geo_dict = model.to_geojson_dict(location)

    #sim_folder = os.path.join(folders.default_simulation_folder, 'district_test')
    sim_folder = 'C:\district_test'
    preparedir(sim_folder)
    epw_file = os.path.abspath('./tests/epw/chicago.epw')

    # write out the OpenStudio Models
    hb_models = model.to_honeybee('Building', 100, False, 0.01)
    for hb_model in hb_models:
        # process the simulation parameters
        _sim_par_ = SimulationParameter()
        _sim_par_.output.add_zone_energy_use()
        
        # assign design days from the EPW if there are not in the _sim_par_
        if len(_sim_par_.sizing_parameter.design_days) == 0:
            folder, epw_file_name = os.path.split(epw_file)
            ddy_file = os.path.join(folder, epw_file_name.replace('.epw', '.ddy'))
            if os.path.isfile(ddy_file):
                _sim_par_.sizing_parameter.add_from_ddy_996_004(ddy_file)
            else:
                raise ValueError('No _ddy_file_ has been input and no .ddy file was '
                                'found next to the _epw_file.')

        # process the simulation folder name and the directory
        directory = os.path.join(sim_folder, hb_model.name, 'OpenStudio')

        # delete any existing files in the directory and prepare it for simulation
        nukedir(directory, True)
        preparedir(directory)

        # write the model parameter JSONs
        model_dict = hb_model.to_dict(triangulate_sub_faces=True)
        model_json = os.path.join(directory, '{}.json'.format(model.name))
        with open(model_json, 'w') as fp:
            json.dump(model_dict, fp)

        # write the simulation parameter JSONs
        sim_par_dict = _sim_par_.to_dict()
        sim_par_json = os.path.join(directory, 'simulation_parameter.json')
        with open(sim_par_json, 'w') as fp:
            json.dump(sim_par_dict, fp)

        # collect the two jsons for output and write out the osw file
        jsons = [model_json, sim_par_json]
        osw = to_openstudio_osw(directory, model_json, sim_par_json, epw_file)

        # run the measure to translate the model JSON to an openstudio measure
        osm, idf = run_osw(osw)

    uo_dir = os.path.join(sim_folder, 'urbanopt')
    feat, scen = prepare_urbanopt_folder(uo_dir, geo_dict, epw_file)
    result = run_urbanopt(feat, scen)
