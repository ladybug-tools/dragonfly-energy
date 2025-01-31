# coding=utf-8
"""Methods to write files for URBANopt simulation from a Model."""
import sys
import os
import re
import json
import shutil

from ladybug_geometry.geometry2d import Point2D
from ladybug.futil import nukedir, preparedir
from ladybug.epw import EPW
from honeybee.config import folders
from honeybee.model import Model as hb_model


def model_to_urbanopt(
    model, location, point=Point2D(0, 0), shade_distance=None, use_multiplier=True,
    exclude_plenums=False, solve_ceiling_adjacencies=False,
    des_loop=None, electrical_network=None, road_network=None, ground_pv=None,
    folder=None, tolerance=None
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
        exclude_plenums: Boolean to indicate whether ceiling/floor plenum depths
            assigned to Room2Ds should be ignored during translation. This
            results in each Room2D translating to a single Honeybee Room at
            the full floor_to_ceiling_height instead of a base Room with (a)
            plenum Room(s). (Default: False).
        solve_ceiling_adjacencies: Boolean to note whether adjacencies should be
            solved between interior stories when Room2Ds perfectly match one
            another in their floor plate. This ensures that Surface boundary
            conditions are used instead of Adiabatic ones. Note that this input
            has no effect when the object_per_model is Story. (Default: False).
        des_loop: An optional District Energy System (DES) ThermalLoop that's
            associated with the dragonfly Model. (Default: None).
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
            not considered touching. If None, the Model tolerance will be used.

    Returns:
        A tuple with three values.

        feature_geojson -- The path to an URBANopt feature geoJSON that has
            been written by this method.

        hb_model_jsons -- An array of file paths to honeybee Model JSONs that
            correspond to the detailed_model_filename keys in the feature_geojson.

        hb_models -- An array of honeybee Model objects that were generated in
            process of writing the URBANopt files.
    """
    # make sure the model is in meters and, if it's not, duplicate and scale it
    conversion_factor, original_units = None, 'Meters'
    tolerance = model.tolerance if tolerance is None else tolerance
    if model.units != 'Meters':
        original_units = model.units
        conversion_factor = hb_model.conversion_factor_to_meters(model.units)
        point = point.scale(conversion_factor)
        if shade_distance is not None:
            shade_distance = shade_distance * conversion_factor
        tolerance = tolerance * conversion_factor
        model = model.duplicate()  # duplicate the model to avoid mutating the input
        model.convert_to_units('Meters')
        if des_loop is not None:
            des_loop.scale(conversion_factor)
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

    # get rid of all simulation files that exists in the folder already
    dir_to_delete = ('hb_json', 'mappers', 'run')
    ext_to_delete = ('.bat', '.geojson', '.epw', '.mos')
    file_to_delete = (
        'Gemfile', 'Gemfile.lock', 'honeybee_scenario.csv', 'runner.conf',
        'simulation_parameter.json', 'system_params.json',
        'electrical_database.json', 'network.json'
    )
    if os.path.isdir(folder):
        files = os.listdir(folder)
        for f in files:
            path = os.path.join(folder, f)
            if os.path.isdir(path):
                if f in dir_to_delete:
                    nukedir(path, True)
            else:
                if f in file_to_delete:
                    os.remove(path)
                elif f.endswith(ext_to_delete):
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

    # add the DES to the GeoJSON dictionary
    if des_loop is not None:
        if hasattr(des_loop, 'to_geojson_dict'):
            des_features = des_loop.to_geojson_dict(
                model.buildings, location, point, tolerance=tolerance)
            geojson_dict['features'].extend(des_features)
        sys_p_json = os.path.join(folder, 'system_params.json')
        with open(sys_p_json, 'w') as fp:
            des_dict = des_loop.to_des_param_dict(model.buildings, tolerance=tolerance)
            json.dump(des_dict, fp, indent=2)
        if conversion_factor is not None:
            des_loop.scale(1 / conversion_factor)

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
    if (sys.version_info < (3, 0)):  # we need to manually encode it as UTF-8
        with open(feature_geojson, 'wb') as fp:
            obj_str = json.dumps(geojson_dict, indent=4, ensure_ascii=False)
            fp.write(obj_str.encode('utf-8'))
    else:
        with open(feature_geojson, 'w', encoding='utf-8') as fp:
            obj_str = json.dump(geojson_dict, fp, indent=4, ensure_ascii=False)

    # write out the honeybee Model JSONs from the model
    hb_model_jsons = []
    hb_models = model.to_honeybee(
        'Building', shade_distance, use_multiplier, exclude_plenums,
        solve_ceiling_adjacencies=solve_ceiling_adjacencies, tolerance=tolerance)
    for bldg_model in hb_models:
        try:
            bldg_model.remove_degenerate_geometry(0.01)
        except ValueError:
            error = 'Failed to remove degenerate Geometry.\nYour Model units system is: {}. ' \
                'Is this correct?'.format(original_units)
            raise ValueError(error)
        model_dict = bldg_model.to_dict(triangulate_sub_faces=True)
        bldg_model.properties.energy.add_autocal_properties_to_dict(model_dict)
        bld_path = os.path.join(hb_model_folder, '{}.json'.format(bldg_model.identifier))
        if (sys.version_info < (3, 0)):  # we need to manually encode it as UTF-8
            with open(bld_path, 'wb') as fp:
                obj_str = json.dumps(model_dict, indent=4, ensure_ascii=False)
                fp.write(obj_str.encode('utf-8'))
        else:
            with open(bld_path, 'w', encoding='utf-8') as fp:
                obj_str = json.dump(model_dict, fp, indent=4, ensure_ascii=False)
        hb_model_jsons.append(bld_path)

    return feature_geojson, hb_model_jsons, hb_models


def model_to_des(
    model, des_loop, epw_file, location=None, point=Point2D(0, 0),
    folder=None, tolerance=None
):
    r"""Generate an URBANopt feature geoJSON and DES input files from a dragonfly Model.

    This method is intended specifically for the case that District Energy
    System (DES) simulation is to be performed without using URBANopt to generate
    building energy loads through EnergyPlus. Accordingly, ALL Dragonfly Buildings
    in the Model must have DES loads assigned directly to them in order for this
    method to run correctly.

    Args:
        model: A dragonfly Model for which an URBANopt feature geoJSON and
            corresponding DES input files will be generated.
        des_loop: A District Energy System (DES) ThermalLoop that is associated
            with the dragonfly Model.
        epw_file: The file path to an EPW that should be associated with the
            output energy model.
        location: An optional ladybug Location object possessing longitude and
            latitude data. If None, the Location data will be pulled from the
            input epw_file, effectively placing the GeoJSON at the location
            of the EPW
        point: A ladybug_geometry Point2D for where the location object exists
            within the space of a scene. The coordinates of this point are
            expected to be in the units of this Model. (Default: (0, 0)).
        folder: An optional folder to be used as the root of the model's
            URBANopt folder. If None, the files will be written into a sub-directory
            of the honeybee-core default_simulation_folder.
        tolerance: The minimum distance between points at which they are
            not considered touching. If None, the Model tolerance will be used.

    Returns:
        A tuple with three values.

        feature_geojson -- The path to an URBANopt feature geoJSON that has
            been written by this method.

        scenario_csv -- The path to an URBANopt scenario CSV that has
            been written by this method.

        system_parameters -- The path to the DES system parameter JSON that has
            been written by this method.
    """
    # make sure the model is in meters and, if it's not, duplicate and scale it
    conversion_factor = None
    tolerance = model.tolerance if tolerance is None else tolerance
    if model.units != 'Meters':
        conversion_factor = hb_model.conversion_factor_to_meters(model.units)
        point = point.scale(conversion_factor)
        tolerance = tolerance * conversion_factor
        model = model.duplicate()  # duplicate the model to avoid mutating the input
        model.convert_to_units('Meters')
        des_loop.scale(conversion_factor)

    # prepare the folder for simulation
    if folder is None:  # use the default simulation folder
        folder = os.path.join(
            folders.default_simulation_folder,
            re.sub(r'[^.A-Za-z0-9_-]', '_', model.display_name)
        )
    nukedir(folder, True)  # get rid of anything that exists in the folder already
    preparedir(folder)  # create the directory if it's not there

    # create GeoJSON dictionary
    epw_obj = EPW(epw_file)
    if location is None:
        location = epw_obj.location
    geojson_dict = model.to_geojson_dict(location, point, tolerance=tolerance)

    # create the scenario CSV file
    scenario_matrix = [['Feature Id', 'Feature Name', 'Mapper Class']]
    hb_mapper = 'URBANopt::Scenario::HoneybeeMapper'
    for feature in geojson_dict['features']:
        try:
            if feature['properties']['type'] == 'Building':
                props = feature['properties']
                f_row = [props['id'], props['name'], hb_mapper]
                scenario_matrix.append(f_row)
        except KeyError:  # definitely not a building
            pass
    scenario_csv = os.path.join(folder, 'honeybee_scenario.csv')
    with open(scenario_csv, 'w') as fp:
        for row in scenario_matrix:
            fp.write('{}\n'.format(','.join(row)))

    # write the Building loads into the scenario result folder
    scn_dir = os.path.join(folder, 'run', 'honeybee_scenario')
    for bldg in model.buildings:
        csv_data = bldg.properties.energy.to_building_load_csv()
        json_data = bldg.properties.energy.to_building_load_json()
        mos_data = bldg.properties.energy.to_building_load_mos()
        bldg_dir = os.path.join(scn_dir, bldg.identifier)
        measure_dir = os.path.join(bldg_dir, '004_export_modelica_loads')
        preparedir(measure_dir)
        csv_path = os.path.join(measure_dir, 'building_loads.csv')
        json_path = os.path.join(bldg_dir, 'results.json')
        mos_path = os.path.join(measure_dir, 'modelica.mos')
        with open(csv_path, 'w') as fp:
            fp.write(csv_data)
        with open(json_path, 'w') as fp:
            fp.write(json_data)
        with open(mos_path, 'w') as fp:
            fp.write(mos_data)

    # add the DES to the GeoJSON dictionary
    if hasattr(des_loop, 'to_geojson_dict'):
        des_features = des_loop.to_geojson_dict(
            model.buildings, location, point, tolerance=tolerance)
        geojson_dict['features'].extend(des_features)
    des_dict = des_loop.to_des_param_dict(model.buildings, tolerance=tolerance)
    if conversion_factor is not None:  # put back the correct scale for the DES
        des_loop.scale(1 / conversion_factor)

    # copy the EPW to the project directory
    epw_f_name = os.path.split(epw_file)[-1]
    target_epw = os.path.join(folder, epw_f_name)
    shutil.copy(epw_file, target_epw)
    # create a MOS file from the EPW
    epw_obj = EPW(target_epw)
    mos_file = os.path.join(folder, epw_f_name.replace('.epw', '.mos'))
    epw_obj.to_mos(mos_file)
    # write the EPW path into the GeoJSON
    if 'project' in geojson_dict:
        if 'weather_filename' not in geojson_dict['project']:
            geojson_dict['project']['weather_filename'] = epw_f_name

    # if the DES system is GSHP, specify any autocalculated ground temperatures
    if 'district_system' in des_dict:
        if 'fifth_generation' in des_dict['district_system']:
            g5_par = des_dict['district_system']['fifth_generation']
            if 'soil' in g5_par and 'undisturbed_temp' in g5_par['soil']:
                soil_par = g5_par['soil']
                if soil_par['undisturbed_temp'] == 'Autocalculate':
                    epw_obj = EPW(epw_file)
                    soil_par['undisturbed_temp'] = \
                        epw_obj.dry_bulb_temperature.average

    # write out the GeoJSON and system parameter files
    feature_geojson = os.path.join(folder, '{}.geojson'.format(model.identifier))
    system_parameters = os.path.join(folder, 'system_params.json')
    if (sys.version_info < (3, 0)):  # we need to manually encode it as UTF-8
        with open(feature_geojson, 'wb') as fp:
            obj_str = json.dumps(geojson_dict, indent=4, ensure_ascii=False)
            fp.write(obj_str.encode('utf-8'))
        with open(system_parameters, 'wb') as fp:
            obj_str = json.dumps(des_dict, indent=2, ensure_ascii=False)
            fp.write(obj_str.encode('utf-8'))
    else:
        with open(feature_geojson, 'w', encoding='utf-8') as fp:
            obj_str = json.dump(geojson_dict, fp, indent=4, ensure_ascii=False)
        with open(system_parameters, 'w') as fp:
            json.dump(des_dict, fp, indent=2)

    return feature_geojson, scenario_csv, system_parameters
