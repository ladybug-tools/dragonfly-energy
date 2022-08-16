# coding=utf-8
"""Methods to write files for URBANopt simulation from a Model."""
from ladybug_geometry.geometry2d import Point2D
from ladybug.futil import nukedir, preparedir
from honeybee.config import folders
from honeybee.model import Model as hb_model

import os
import re
import json


def model_to_urbanopt(
    model, location, point=Point2D(0, 0), shade_distance=None, use_multiplier=True,
    add_plenum=False, solve_ceiling_adjacencies=False, electrical_network=None,
    road_network=None, ground_pv=None, folder=None, tolerance=0.01
):
    r"""Generate an URBANopt feature geoJSON and honeybee JSONs from a dragonfly Model.

    Args:
        model: A dragonfly Model for which an URBANopt feature geoJSON and
            corresponding honeybee Model JSONs will be returned.
        location: A ladybug Location object possessing longitude and latitude data.
        point: A ladybug_geometry Point2D for where the location object exists
            within the space of a scene. The coordinates of this point are
            expected to be in the units of this Model. (Default: (0, 0)).
        shade_distance: An optional number to note the distance beyond which other
            objects' shade should not be exported into a given honeybee Model. This
            is helpful for reducing the simulation run time of each Model when other
            connected buildings are too far away to have a meaningful impact on
            the results. If None, all other buildings will be included as context
            shade in each and every Model. Set to 0 to exclude all neighboring
            buildings from the resulting models. (Default: None).
        use_multiplier: If True, the multipliers on the Model's Stories will be
            passed along to the generated Honeybee Room objects, indicating the
            simulation will be run once for each unique room and then results
            will be multiplied. If False, full geometry objects will be written
            for each and every floor in the building that are represented through
            multipliers and all resulting multipliers will be 1. (Default: True).
        add_plenum: Boolean to indicate whether ceiling/floor plenums should
            be auto-generated for the Rooms. (Default: False).
        solve_ceiling_adjacencies: Boolean to note whether adjacencies should be
            solved between interior stories when Room2Ds perfectly match one
            another in their floor plate. This ensures that Surface boundary
            conditions are used instead of Adiabatic ones. Note that this input
            has no effect when the object_per_model is Story. (Default: False).
        electrical_network: An optional OpenDSS ElectricalNetwork that's associated
            with the dragonfly Model. (Default: None).
        road_network: An optional RNM RoadNetwork that's associated with the
            dragonfly Model. (Default: None).
        ground_pv: An optional list of REopt GroundMountPV objects representing
            ground-mounted photovoltaic fields to be included in the REopt
            simulation. (Default: None).
        folder: An optional folder to be used as the root of the model's
            URBANopt folder. If None, the files will be written into a sub-directory
            of the honeybee-core default_simulation_folder.
        tolerance: The minimum distance between points at which they are
            not considered touching. (Default: 0.01, suitable for objects
            in meters).

    Returns:
        A tuple with three values.

        feature_geojson -- The path to an URBANopt feature geoJSON that has
            been written by this method.

        hb_model_jsons -- An array of file paths to honeybee Model JSONS that
            correspond to the detailed_model_filename keys in the feature_geojson.

        hb_models -- An array of honeybee Model objects that were generated in
            process of writing the URBANopt files.
    """
    # make sure the model is in meters and, if it's not, duplicate and scale it
    conversion_factor = None
    if model.units != 'Meters':
        conversion_factor = hb_model.conversion_factor_to_meters(model.units)
        point = point.scale(conversion_factor)
        if shade_distance is not None:
            shade_distance = shade_distance * conversion_factor
        tolerance = tolerance * conversion_factor
        model = model.duplicate()  # duplicate the model to avoid mutating the input
        model.convert_to_units('Meters')
        if electrical_network is not None:
            electrical_network.scale(conversion_factor)
        if road_network is not None:
            road_network.scale(conversion_factor)
        if ground_pv is not None:
            for g_pv in ground_pv:
                g_pv.scale(conversion_factor)

    # prepare the folder for simulation
    tr_msg = 'The following simulation folder is too long to be used with URBANopt:' \
        '\n{}\nSpecify a shorter folder path in which to write the GeoJSON.'
    if folder is None:  # use the default simulation folder
        assert len(folders.default_simulation_folder) < 55, \
            tr_msg.format(folders.default_simulation_folder)
        sim_dir = re.sub(r'[^.A-Za-z0-9_-]', '_', model.display_name)
        folder = os.path.join(folders.default_simulation_folder, sim_dir)
        if len(folder) >= 60:
            tr_len = 58 - len(folders.default_simulation_folder)
            folder = os.path.join(folders.default_simulation_folder, sim_dir[:tr_len])
    else:
        assert len(folder) < 60, tr_msg.format(folder)

    # get rid of anything that exists in the folder already
    if os.path.isdir(folder):
        files = os.listdir(folder)
        for f in files:
            if f == '.bundle':
                continue
            path = os.path.join(folder, f)
            if os.path.isdir(path):
                nukedir(path, True)
            else:
                os.remove(path)
    else:
        preparedir(folder)  # create the directory if it's not there

    # prepare the folder into which honeybee Model JSONs will be written
    hb_model_folder = os.path.join(folder, 'hb_json')  # folder for honeybee JSONs
    preparedir(hb_model_folder)

    # create GeoJSON dictionary
    geojson_dict = model.to_geojson_dict(location, point, tolerance=tolerance)
    for feature_dict in geojson_dict['features']:  # add the detailed model filename
        if feature_dict['properties']['type'] == 'Building':
            bldg_id = feature_dict['properties']['id']
            feature_dict['properties']['detailed_model_filename'] = \
                os.path.join(hb_model_folder, '{}.json'.format(bldg_id))

    # add the electrical network to the GeoJSON dictionary
    if electrical_network is not None:
        electric_features = electrical_network.to_geojson_dict(
            model.buildings, location, point, tolerance=tolerance)
        geojson_dict['features'].extend(electric_features)
        electric_json = os.path.join(folder, 'electrical_database.json')
        with open(electric_json, 'w') as fp:
            json.dump(electrical_network.to_electrical_database_dict(), fp, indent=4)
        if conversion_factor is not None:
            electrical_network.scale(1 / conversion_factor)

    # add the road network to the GeoJSON dictionary
    if road_network is not None:
        road_features = road_network.to_geojson_dict(location, point)
        geojson_dict['features'].extend(road_features)
        if conversion_factor is not None:
            road_network.scale(1 / conversion_factor)

    # add the ground-mounted PV to the GeoJSON dictionary
    if ground_pv is not None and len(ground_pv) != 0:
        pv_features = [g_pv.to_geojson_dict(location, point) for g_pv in ground_pv]
        geojson_dict['features'].extend(pv_features)
        if conversion_factor is not None:
            for g_pv in ground_pv:
                g_pv.scale(1 / conversion_factor)

    # write out the GeoJSON file
    feature_geojson = os.path.join(folder, '{}.geojson'.format(model.identifier))
    with open(feature_geojson, 'w') as fp:
        json.dump(geojson_dict, fp, indent=4)

    # write out the honeybee Model JSONS from the model
    hb_model_jsons = []
    hb_models = model.to_honeybee(
        'Building', shade_distance, use_multiplier, add_plenum,
        solve_ceiling_adjacencies=solve_ceiling_adjacencies, tolerance=tolerance)
    for bldg_model in hb_models:
        bld_path = os.path.join(hb_model_folder, '{}.json'.format(bldg_model.identifier))
        model_dict = bldg_model.to_dict(triangulate_sub_faces=True)
        with open(bld_path, 'w') as fp:
            json.dump(model_dict, fp)
        hb_model_jsons.append(bld_path)

    return feature_geojson, hb_model_jsons, hb_models
