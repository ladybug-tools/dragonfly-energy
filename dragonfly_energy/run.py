# coding=utf-8
"""Module for running geoJSON and OpenStudio files through URBANopt."""
from __future__ import division

import os
import json
import shutil
import subprocess

from ladybug.futil import preparedir, write_to_file
from ladybug.epw import EPW
from ladybug.config import folders as lb_folders
from honeybee.config import folders as hb_folders
from honeybee_energy.config import folders as hb_energy_folders
from honeybee_energy.result.emissions import emissions_region

from .config import folders
from .measure import MapperMeasure
from .reopt import REoptParameter

# Custom environment used to run Python packages without conflicts
PYTHON_ENV = os.environ.copy()
PYTHON_ENV['PYTHONHOME'] = ''

# Number to prevent GHE Designer simulations that would max out the memory
MAX_BOREHOLES = 10000


def base_honeybee_osw(
        project_directory, sim_par_json=None, additional_measures=None,
        additional_mapper_measures=None, base_osw=None, epw_file=None,
        skip_report=True, emissions_year=None):
    """Create a honeybee_workflow.osw to be used as a base in URBANopt simulations.

    This method will also copy the Honeybee.rb mapper to this folder if it is
    available in the config of this library.

    Args:
        project_directory: Full path to a folder out of which the URBANopt simulation
            will be run. This is the folder that contains the feature geoJSON.
        sim_par_json: Optional file path to the SimulationParameter JSON.
            If None, the OpenStudio models generated in the URBANopt run will
            not have everything they need to be simulate-able unless such
            parameters are supplied from one of the additional_measures or the
            base_osw. (Default: None).
        additional_measures: An optional array of honeybee-energy Measure objects
            to be included in the output osw. These Measure objects must have
            values for all required input arguments or an exception will be
            raised while running this function. (Default: None).
        additional_mapper_measures: An optional array of dragonfly-energy MapperMeasure
            objects to be included in the output osw. These MapperMeasure objects
            must have values for all required input arguments or an exception will
            be raised while running this function. (Default: None).
        base_osw: Optional file path to an existing OSW JSON be used as the base
            for the honeybee_workflow.osw. This is another way that outside measures
            can be incorporated into the workflow. (Default: None).
        epw_file: Optional file path to an EPW that should be associated with the
            output energy model. (Default: None).
        skip_report: Set to True to have the URBANopt default feature reporting
            measure skipped as part of the workflow. If False, the measure will
            be run after all simulations are complete. Note that this input
            has no effect if the default_feature_reports measure is already
            in the base_osw or additional_measures. (Default: True).
        emissions_year: An optional integer to set the year for which carbon emissions
            will be computed. If not for a historical year, values must be an even
            number and be between 2020 and 2050. If None, no carbon emission
            calculations will be included in the simulation. (Default: None).

    Returns:
        The file path to the honeybee_workflow.osw written out by this method.
        This is used as the base for translating all features in the geoJSON.
    """
    # create a dictionary representation of the .osw with steps to run
    # the model measure and the simulation parameter measure
    if base_osw is None:
        osw_dict = {'steps': [], 'name': None, 'description': None}
    else:
        assert os.path.isfile(base_osw), 'No base OSW file found at {}.'.format(base_osw)
        with open(base_osw, 'r') as base_file:
            osw_dict = json.load(base_file)

    # add a simulation parameter step if it is specified
    if sim_par_json is not None:
        sim_par_dict = {
            'arguments': {
                'simulation_parameter_json': sim_par_json
            },
            'measure_dir_name': 'from_honeybee_simulation_parameter'
        }
        osw_dict['steps'].insert(0, sim_par_dict)

    # add the model json serialization into the steps
    model_measure_dict = {
        'arguments': {
            'model_json': 'model_json_to_be_mapped.json'
        },
        'measure_dir_name': 'from_honeybee_model'
    }
    osw_dict['steps'].insert(0, model_measure_dict)

    # assign the measure_paths to the osw_dict
    if 'measure_paths' not in osw_dict:
        osw_dict['measure_paths'] = []
    if hb_energy_folders.honeybee_openstudio_gem_path:  # add honeybee-openstudio measure
        m_dir = os.path.join(hb_energy_folders.honeybee_openstudio_gem_path, 'measures')
        osw_dict['measure_paths'].append(m_dir)

    # add the emissions reporting if a year has been selected
    if emissions_year is not None and epw_file is not None:
        epw_obj = EPW(epw_file)
        ems_region = emissions_region(epw_obj.location)
        if ems_region is not None:
            if emissions_year < 2020:
                hist_yr, fut_yr = emissions_year, 2030
            else:
                hist_yr, fut_yr = 2019, emissions_year
            emissions_measure_dict = {
                'arguments': {
                    'future_subregion': ems_region[0],
                    'hourly_historical_subregion': ems_region[2],
                    'annual_historical_subregion': ems_region[1],
                    'future_year': str(fut_yr),
                    'hourly_historical_year': '2019',
                    'annual_historical_year': str(hist_yr)
                },
                'measure_dir_name': 'add_ems_emissions_reporting'
            }
            osw_dict['steps'].append(emissions_measure_dict)

    # add any additional measures to the osw_dict
    if additional_measures or additional_mapper_measures:
        measures = []
        if additional_measures is not None:
            measures.extend(additional_measures)
        if additional_mapper_measures is not None:
            measures.extend(additional_mapper_measures)
        measure_paths = set()  # set of all unique measure paths
        # ensure measures are correctly ordered
        m_dict = {'ModelMeasure': [], 'EnergyPlusMeasure': [], 'ReportingMeasure': []}
        for measure in measures:
            m_dict[measure.type].append(measure)
        sorted_measures = m_dict['ModelMeasure'] + m_dict['EnergyPlusMeasure'] + \
            m_dict['ReportingMeasure']
        for measure in sorted_measures:
            measure.validate()  # ensure that all required arguments have values
            measure_paths.add(os.path.dirname(measure.folder))
            osw_dict['steps'].append(measure.to_osw_dict())  # add measure to workflow
            if isinstance(measure, MapperMeasure):
                _add_mapper_measure(project_directory, measure)
        for m_path in measure_paths:  # add outside measure paths
            osw_dict['measure_paths'].append(m_path)

    # add default feature reports if they aren't in the steps
    all_measures = [step['measure_dir_name'] for step in osw_dict['steps']]
    if 'default_feature_reports' not in all_measures:
        report_measure_dict = {
            'arguments': {
                'feature_id': None,
                'feature_name': None,
                'feature_type': None,
                'feature_location': None
            },
            'measure_dir_name': 'default_feature_reports'
        }
        if skip_report:
            report_measure_dict['arguments']['__SKIP__'] = True
        osw_dict['steps'].append(report_measure_dict)

    # if there is a system parameter JSON, make sure the EPW is copied and referenced
    if epw_file is not None:
        osw_dict['weather_file'] = epw_file
        sys_param_file = os.path.join(project_directory, 'system_params.json')
        if os.path.isfile(sys_param_file):
            # make sure the Modelica measure runs as part of the simulation
            modelica_measures = [
                {
                    'measure_dir_name': 'export_time_series_modelica',
                    'arguments': {'__SKIP__': False}
                },
                {
                    'measure_dir_name': 'export_modelica_loads',
                    'arguments': {'__SKIP__': False}
                },
            ]
            osw_dict['steps'].extend(modelica_measures)

            # copy the EPW to the project directory
            epw_f_name = os.path.split(epw_file)[-1]
            target_epw = os.path.join(project_directory, epw_f_name)
            shutil.copy(epw_file, target_epw)
            # create a MOS file from the EPW
            epw_obj = EPW(target_epw)
            mos_file = os.path.join(
                project_directory, epw_f_name.replace('.epw', '.mos'))
            epw_obj.to_mos(mos_file)
            # find the path to the feature GeoJSON
            feature_geojson = None
            for fp in os.listdir(project_directory):
                if fp.endswith('.geojson'):
                    feature_geojson = os.path.join(project_directory, fp)
                    break
            if not feature_geojson:
                raise ValueError(
                    'No feature geojson file was found in: {}'.format(project_directory))
            # write the EPW path into the GeoJSON
            with open(feature_geojson, 'r') as gjf:
                geo_dict = json.load(gjf)
            if 'project' in geo_dict:
                if 'weather_filename' not in geo_dict['project']:
                    geo_dict['project']['weather_filename'] = epw_f_name
                    with open(feature_geojson, 'w') as fp:
                        json.dump(geo_dict, fp, indent=4)

            # if the DES system is GSHP, specify any autocalculated ground temperatures
            with open(sys_param_file, 'r') as spf:
                sys_dict = json.load(spf)
            if 'district_system' in sys_dict:
                if 'fifth_generation' in sys_dict['district_system']:
                    g5_par = sys_dict['district_system']['fifth_generation']
                    if 'ghe_parameters' in g5_par:
                        ghe_par = g5_par['ghe_parameters']
                        if 'soil' in ghe_par and 'undisturbed_temp' in ghe_par['soil']:
                            soil_par = ghe_par['soil']
                            if soil_par['undisturbed_temp'] == 'Autocalculate':
                                epw_obj = EPW(epw_file)
                                soil_par['undisturbed_temp'] = \
                                    epw_obj.dry_bulb_temperature.average
                                with open(sys_param_file, 'w') as fp:
                                    json.dump(sys_dict, fp, indent=4)

    # write the dictionary to a honeybee_workflow.osw
    mappers_dir = os.path.join(project_directory, 'mappers')
    if not os.path.isdir(mappers_dir):
        preparedir(mappers_dir)
    osw_json = os.path.join(mappers_dir, 'honeybee_workflow.osw')
    with open(osw_json, 'w') as fp:
        json.dump(osw_dict, fp, indent=4)

    # copy the Honeybee.rb mapper if it exists in the config
    if folders.mapper_path:
        shutil.copy(folders.mapper_path, os.path.join(mappers_dir, 'Honeybee.rb'))

    return os.path.abspath(osw_json)


def prepare_urbanopt_folder(feature_geojson, cpu_count=None, verbose=False):
    """Prepare a directory with a feature geoJSON for URBANopt simulation.

    This includes copying the Gemfile to the folder and generating the runner.conf
    to specify the number of CPUs to be used in the simulation. Lastly, the
    the scenario .csv file will be generated from the feature_geojson.

    Args:
        feature_geojson: An URBANopt feature geoJSON to be prepared for URBANopt
            simulation.
        cpu_count: A positive integer for the number of CPUs to use in the
            simulation. This number should not exceed the number of CPUs on the
            machine running the simulation and should be lower if other tasks
            are running while the simulation is running. If set to None, it
            should automatically default to one less than the number of CPUs
            currently available on the machine (or 1 if the machine has only
            one processor). (Default: None).
        verbose: Boolean to note if the simulation should be run with verbose
            reporting of progress. (Default: False).

    Returns:
        Path to the .csv file for the URBANopt scenario.
    """
    # copy the Gemfile into the folder containing the feature_geojson
    assert folders.urbanopt_gemfile_path, \
        'No URBANopt Gemfile was found in dragonfly_energy.config.folders.\n' \
        'This file must exist to run URBANopt.'
    folders.check_urbanopt_version()
    uo_folder = os.path.dirname(feature_geojson)
    shutil.copy(folders.urbanopt_gemfile_path, os.path.join(uo_folder, 'Gemfile'))

    # auto-assign the number of processors if None
    cpu_count = _recommended_processor_count() if cpu_count is None else cpu_count

    # generate the runner.conf to set the number of CPUs based on the input
    runner_dict = {
        'file_version': '0.1.0',
        'max_datapoints': 1000000000,
        'num_parallel': cpu_count,
        'run_simulations': True,
        'verbose': verbose
    }
    runner_conf = os.path.join(uo_folder, 'runner.conf')
    with open(runner_conf, 'w') as fp:
        json.dump(runner_dict, fp, indent=2)

    # generate the scenario csv file
    return _make_scenario(feature_geojson)


def run_urbanopt(feature_geojson, scenario_csv, cpu_count=None):
    """Run a feature and scenario file through URBANopt on any operating system.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.
        cpu_count: This input is deprecated and currently not used given that
            the runner.conf generated in the prepare_urbanopt_folder step
            correctly identifies the number of CPUs to be used.

    Returns:
        A series of file paths to the simulation output files

        -   osm -- Array of paths to .osm files for all generated OpenStudio models.

        -   idf -- Array of paths to .idf files containing the input for the
            EnergyPlus simulation.

        -   sql -- Array of paths to .sqlite files containing all simulation results.

        -   zsz -- Array of paths to .csv files containing detailed zone load
            information recorded over the course of the design days.

        -   rdd -- Array of paths to .rdd files containing all possible outputs
            that can be requested from the simulation.

        -   html -- Array of paths to .html files containing all summary reports.

        -   err -- Array of paths to .err files containing all errors and warnings
            from the simulation.
    """
    folders.check_urbanopt_version()
    # run the simulation
    if os.name == 'nt':  # we are on Windows
        directory, stderr = \
            _run_urbanopt_windows(feature_geojson, scenario_csv)
    else:  # we are on Mac, Linux, or some other unix-based system
        directory, stderr = \
            _run_urbanopt_unix(feature_geojson, scenario_csv)

    # output the simulation files
    return _output_urbanopt_files(directory, stderr)


def run_default_report(feature_geojson, scenario_csv):
    """Generate default reports after an URBANopt simulation is run.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        A series of file paths to the report output files

        -   csv -- Path to a CSV file containing default scenario results.

        -   report_json -- Path to a JSON file containing default scenario results.
    """
    folders.check_urbanopt_version()
    assert os.path.isfile(feature_geojson), \
        'No feature_geojson as found at the specified path: {}.'.format(feature_geojson)
    assert os.path.isfile(scenario_csv), \
        'No scenario_csv as found at the specified path: {}.'.format(scenario_csv)
    # run the report command
    if os.name == 'nt':  # we are on Windows
        return _run_default_report_windows(feature_geojson, scenario_csv)
    else:  # we are on Mac, Linux, or some other unix-based system
        return _run_default_report_unix(feature_geojson, scenario_csv)


def run_reopt(feature_geojson, scenario_csv, urdb_label, reopt_parameters=None,
              developer_key=None):
    """Run a feature and scenario file through REopt post processing.

    Note that the URBANopt simulation must already be run with the input feature_geojson
    and scenario_csv in order for the post-processing to be successful.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to a .csv file for the URBANopt scenario.
        urdb_label: Text string for the Utility Rate Database (URDB) label for the
            particular electrical utility rate for the optimization. The label is
            the last term of the URL of a utility rate detail page (eg. the label for
            the rate at https://openei.org/apps/IURDB/rate/view/5b0d83af5457a3f276733305
            is 5b0d83af5457a3f276733305). Utility rates for specific locations
            can be looked up in the REopt Lite tool (https://reopt.nrel.gov/tool)
            and the label can be obtained by clicking on "Rate Details" link
            for a particular selected rate.
        reopt_parameters: A REoptParameter object to describe the major assumptions
            of the REopt analysis. If None some default parameters will be
            generated for a typical analysis. (Default: None).
        developer_key: Text string for the NREL developer key. You can get a developer
            key at (https://developer.nrel.gov/). (Default: None).

    Returns:
        A series of file paths to the simulation output files

        -   csv -- Path to a CSV file containing scenario optimization results.

        -   report_json -- Path to a JSON file containing scenario optimization results.
    """
    # run checks on the inputs
    folders.check_urbanopt_version()
    assert folders.reopt_assumptions_path, \
        'No REopt assumptions were found in dragonfly_energy.config.folders.'
    assert os.path.isfile(feature_geojson), \
        'No feature_geojson as found at the specified path: {}.'.format(feature_geojson)
    assert os.path.isfile(scenario_csv), \
        'No scenario_csv as found at the specified path: {}.'.format(scenario_csv)
    developer_key = developer_key if developer_key is not None \
        else 'bo8jGuFfk7DBDpTlzShuxWuAGletBq1j5AhcUhCD'
    project_folder = os.path.dirname(feature_geojson)

    # write the parameter file
    if reopt_parameters is None:  # generate some defaults
        reopt_parameters = REoptParameter()
        reopt_parameters.pv_parameter.max_kw = 1000000000
        reopt_parameters.storage_parameter.max_kw = 1000000
        reopt_parameters.generator_parameter.max_kw = 1000000000
    else:
        assert isinstance(reopt_parameters, REoptParameter), \
            'Expected REoptParameter. Got {}.'.format(type(reopt_parameters))
    reopt_folder = os.path.join(project_folder, 'reopt')
    if not os.path.isdir(reopt_folder):
        os.mkdir(reopt_folder)
    reopt_par_json = os.path.join(reopt_folder, 'reopt_assumptions.json')
    reopt_dict = reopt_parameters.to_assumptions_dict(
        folders.reopt_assumptions_path, urdb_label)
    with open(reopt_par_json, 'w') as fp:
        json.dump(reopt_dict, fp, indent=4)

    # run the simulation
    if os.name == 'nt':  # we are on Windows
        directory = _run_reopt_windows(feature_geojson, scenario_csv, developer_key)
    else:  # we are on Mac, Linux, or some other unix-based system
        directory = _run_reopt_unix(feature_geojson, scenario_csv, developer_key)

    # output the simulation files
    return _output_reopt_files(directory)


def run_rnm(feature_geojson, scenario_csv, underground_ratio=0.9, lv_only=True,
            nodes_per_building=1):
    """Run a feature and scenario file through RNM post processing.

    Note that the URBANopt simulation must already be run with the input feature_geojson
    and scenario_csv in order for the RNM post-processing to be successful.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to a .csv file for the URBANopt scenario.
        underground_ratio: A number between 0 and 1 for the ratio of overall cables
            that are underground vs. overhead in the analysis. (Default: 0.9).
        lv_only: Boolean to note whether to consider only low voltage consumers
            in the analysis. (Default: True).
        nodes_per_building: Positive integer for the maximum number of low voltage
            nodes to represent a single building. (Default: 1).

    Returns:
        Path to a folder that contains all of the RNM output files.
    """
    # load the information from the GeoJSON
    geo_dict, project_dict = None, None
    if os.path.isfile(feature_geojson):
        with open(feature_geojson, 'r') as fg:
            geo_dict = json.load(fg)
            project_dict = geo_dict['project']
    # change the GeoJSON to have the RNM inputs
    if geo_dict is not None:
        proj = geo_dict['project']
        if 'underground_cables_ratio' not in proj or \
                proj['underground_cables_ratio'] != underground_ratio or \
                'only_lv_consumers' not in proj or \
                proj['only_lv_consumers'] != lv_only or \
                'max_number_of_lv_nodes_per_building' not in proj or \
                proj['max_number_of_lv_nodes_per_building'] != nodes_per_building:
            geo_dict['project']['underground_cables_ratio'] = underground_ratio
            geo_dict['project']['only_lv_consumers'] = lv_only
            geo_dict['project']['max_number_of_lv_nodes_per_building'] = \
                nodes_per_building
            with open(feature_geojson, 'w') as fp:
                json.dump(geo_dict, fp, indent=4)
    # run the simulation
    folders.check_urbanopt_version()
    if os.name == 'nt':  # we are on Windows
        directory = _run_rnm_windows(feature_geojson, scenario_csv)
    else:  # we are on Mac, Linux, or some other unix-based system
        directory = _run_rnm_unix(feature_geojson, scenario_csv)
    # get the path to the results folder
    scenario_name = os.path.basename(scenario_csv).replace('.csv', '')
    rnm_path = os.path.join(directory, 'run', scenario_name, 'rnm-us', 'results')
    # copy the project information into the RNM GeoJSON
    if os.path.isdir(rnm_path):
        rnm_geojson = os.path.join(rnm_path, 'GeoJSON', 'Distribution_system.json')
        with open(rnm_geojson, 'r') as fg:
            rnm_dict = json.load(fg)
        rnm_dict['project'] = project_dict
        with open(rnm_geojson, 'w') as fp:
            json.dump(rnm_dict, fp, indent=4)
        return rnm_path


def run_des_sys_param(feature_geojson, scenario_csv):
    """Run the GMT command to add the time series building loads to the sys param JSON.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to a .csv file for the URBANopt scenario.
    """
    # get the directory and parse the system parameter file
    directory = os.path.dirname(feature_geojson)
    sys_param_file = os.path.join(directory, 'system_params.json')
    assert os.path.isfile(sys_param_file), \
        'No DES system parameter was found for this model.\n' \
        'Make sure that the des_loop_ was assigned in the GeoJSON export\n' \
        'before running the URBANopt simulation.'

    # parse the system parameter file to understand the type of system
    with open(sys_param_file, 'r') as spf:
        sp_dict = json.load(spf)
    des_dict = sp_dict['district_system']
    ghe_sys = True if 'fifth_generation' in des_dict and \
        'ghe_parameters' in des_dict['fifth_generation'] else False

    # run the command that adds the building loads to the system parameter
    ext = '.exe' if os.name == 'nt' else ''
    shell = True if os.name == 'nt' else False
    uo_des_exe = os.path.join(
        hb_folders.python_scripts_path, 'uo_des{}'.format(ext))
    build_cmd = '"{des_exe}" build-sys-param "{sp_file}" "{scenario}" "{feature}" ' \
        'time_series -o'.format(
            des_exe=uo_des_exe, sp_file=sys_param_file,
            scenario=scenario_csv, feature=feature_geojson)
    if ghe_sys:
        build_cmd = '{} --ghe'.format(build_cmd)
    process = subprocess.Popen(
        build_cmd, stderr=subprocess.PIPE, shell=shell, env=PYTHON_ENV
    )
    stderr = process.communicate()
    if not os.path.isfile(sys_param_file):
        msg = 'Failed to add building loads to the DES system parameter file.\n' \
            'No file found at:\n{}\n{}'.format(sys_param_file, stderr[1])
        print(msg)
        raise Exception(msg)
    else:
        print(stderr[1])

    # after the loads have been added, put pack the properties of the DES
    with open(sys_param_file, 'r') as spf:
        sp_dict = json.load(spf)
    if ghe_sys:
        original_ghe_par = des_dict['fifth_generation']['ghe_parameters']
        ghe_par = sp_dict['district_system']['fifth_generation']['ghe_parameters']
        ghe_par['fluid'] = original_ghe_par['fluid']
        ghe_par['grout'] = original_ghe_par['grout']
        ghe_par['soil'] = original_ghe_par['soil']
        ghe_par['pipe'] = original_ghe_par['pipe']
        ghe_par['geometric_constraints'] = original_ghe_par['geometric_constraints']
        ghe_par['ghe_specific_params'] = original_ghe_par['ghe_specific_params']
    else:
        sp_dict['district_system'] = des_dict
    with open(sys_param_file, 'w') as spf:
        json.dump(sp_dict, spf, indent=2)

    # if the DES system has a ground heat exchanger, run the thermal network package
    if ghe_sys:
        # check to be sure the user will not max out their RAM
        total_area = 0
        for ghe_sp in ghe_par['ghe_specific_params']:
            ghe_len = ghe_sp['ghe_geometric_params']['length_of_ghe']
            ghe_wth = ghe_sp['ghe_geometric_params']['width_of_ghe']
            total_area += ghe_len * ghe_wth
        bh_count = int(total_area / (ghe_par['geometric_constraints']['b_min'] ** 2))
        if bh_count > MAX_BOREHOLES:
            msg = 'The inputs suggest that there may be as many as {} boreholes in the ' \
                'GHE field\nand this will cause your machine to run out of memory.\n' \
                'A smaller GHE field or a larger minimum borehole spacing is needed ' \
                'such that fewer\nthan {} boreholes are generated and the sizing ' \
                'simulation can succeed.'.format(bh_count, MAX_BOREHOLES)
            raise ValueError(msg)
        # run the GHE Designer to size the system
        tn_exe = os.path.join(
            hb_folders.python_scripts_path, 'thermalnetwork{}'.format(ext))
        scn_name = os.path.basename(scenario_csv).replace('.csv', '')
        scn_dir = os.path.join(directory, 'run', scn_name)
        ghe_dir = os.path.join(scn_dir, 'ghe_dir')
        build_cmd = \
            '"{tn_exe}" -y "{sp_file}" -s "{scenario}" -f "{feature}" -o {out_p}'.format(
                tn_exe=tn_exe, sp_file=sys_param_file,
                scenario=scn_dir, feature=feature_geojson, out_p=ghe_dir)
        process = subprocess.Popen(
            build_cmd, stderr=subprocess.PIPE, shell=False, env=PYTHON_ENV
        )
        # if any errors were found in the sizing simulation, raise them to the user
        stderr = process.communicate()[1]
        stderr_str = str(stderr.strip())
        print(stderr_str)
        if 'ValueError' in stderr_str:  # pass the exception onto the user
            msg = stderr_str.split('ValueError: ')[-1].strip()
            raise ValueError(msg)
        # add the borehole length and count to the system parameter file
        with open(sys_param_file, 'r') as spf:
            sp_dict = json.load(spf)
        ghe_par_dict = sp_dict['district_system']['fifth_generation']['ghe_parameters']
        for ghe_s_par in ghe_par_dict['ghe_specific_params']:
            r_dir = ghe_par['ghe_dir']
            res_file = os.path.join(r_dir, ghe_s_par['ghe_id'], 'SimulationSummary.json')
            with open(res_file, 'r') as rf:
                res_dict = json.load(rf)
            ghe_s_par['borehole']['length_of_boreholes'] = \
                res_dict['ghe_system']['active_borehole_length']['value']
            ghe_s_par['borehole']['number_of_boreholes'] = \
                res_dict['ghe_system']['number_of_boreholes']
        with open(sys_param_file, 'w') as spf:
            json.dump(sp_dict, spf, indent=2)
    return sys_param_file


def run_des_modelica(sys_param_json, feature_geojson, scenario_csv):
    """Run the GMT command to create the Modelica files from the system param JSON.

    Args:
        sys_param_json: The full path to a system parameter JSON from which the
            Modelica files will be generated.
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to a .csv file for the URBANopt scenario.

    Returns:
        The path to the folder where the Modelica files have been written.
    """
    # run the simulation
    if os.name == 'nt':  # we are on Windows
        modelica_dir, stderr = \
            _generate_modelica_windows(sys_param_json, feature_geojson, scenario_csv)
    else:  # we are on Mac, Linux, or some other unix-based system
        modelica_dir, stderr = \
            _generate_modelica_unix(sys_param_json, feature_geojson, scenario_csv)
    if not os.path.isdir(modelica_dir):
        msg = 'Failed to translate DES to Modelica.\n' \
            'No results were found at:\n{}\n{}'.format(modelica_dir, stderr)
        print(msg)
        raise Exception(msg)
    else:
        _add_water_heating_patch(modelica_dir)
    return modelica_dir


def run_modelica_docker(modelica_project_dir):
    """Execute Modelica files of a DES.

    Args:
        modelica_project_dir: The full path to the folder in which the Modelica
            files were written.

    Returns:
        The path to where the results have been written.
    """
    # run the simulation
    if os.name == 'nt':  # we are on Windows
        modelica_dir, stderr = _run_modelica_windows(modelica_project_dir)
    else:  # we are on Mac, Linux, or some other unix-based system
        modelica_dir, stderr = _run_modelica_unix(modelica_project_dir)
    if not os.path.isdir(modelica_dir):
        msg = 'Failed to execute Modelica simulation.\n' \
            'No results were found at:\n{}\n{}'.format(modelica_dir, stderr)
        print(msg)
        raise Exception(msg)
    return modelica_dir


def _add_mapper_measure(project_directory, mapper_measure):
    """Add mapper measure arguments to a geoJSON and the mapper_measures.json.

    Args:
        project_directory: Full path to a folder out of which the URBANopt simulation
            will be run. This is the folder that contains the feature geoJSON.
        mapper_measure: A MapperMeasure object to add.
    """
    # find the feature geoJSON and parse in the dictionary
    for proj_file in os.listdir(project_directory):
        if proj_file.endswith('geojson'):
            geojson_file = os.path.join(project_directory, proj_file)
            break
    with open(geojson_file, 'r') as base_file:
        geojson_dict = json.load(base_file)

    # find or start the mapper_measures.json
    mapper_dir = os.path.join(project_directory, 'mappers')
    map_meas_file = os.path.join(mapper_dir, 'mapper_measures.json')
    if os.path.isfile(map_meas_file):
        with open(map_meas_file, 'r') as base_file:
            map_meas_list = json.load(base_file)
    else:
        map_meas_list = []

    # loop through the mapper measure and assign any mapper arguments
    for m_arg in mapper_measure.arguments:
        if isinstance(m_arg.value, tuple):  # argument to map to buildings
            for i, feat in enumerate(geojson_dict['features']):
                try:
                    if feat['properties']['type'] == 'Building':
                        feat['properties'][m_arg.identifier] = m_arg.value[i]
                except IndexError:
                    raise ValueError(
                        'Number of MapperMeasure arguments ({}) does not equal the '
                        'number of buildings in the model ({}).'.format(
                            len(m_arg.value), len(geojson_dict['features'])))
                except KeyError:  # definitely not a building
                    pass
            m_arg_info = [
                os.path.basename(mapper_measure.folder),
                m_arg.identifier, m_arg.identifier]
            map_meas_list.append(m_arg_info)

    # write the geoJSON and the mapper_measures.json
    if not os.path.isdir(mapper_dir):
        os.mkdir(mapper_dir)
    with open(geojson_file, 'w') as fp:
        json.dump(geojson_dict, fp, indent=4)
    with open(map_meas_file, 'w') as fp:
        json.dump(map_meas_list, fp, indent=4)


def _make_scenario(feature_geojson):
    """Generate a scenario CSV file for URBANopt simulation.

    Args:
        feature_geojson: The full path to a .geojson file.
    """
    # load the geoJSON to a dictionary
    with open(feature_geojson, 'r') as base_file:
        geo_dict = json.load(base_file)

    # loop through the building features and add them to the CSV
    scenario_matrix = [['Feature Id', 'Feature Name', 'Mapper Class']]
    hb_mapper = 'URBANopt::Scenario::HoneybeeMapper'
    for feature in geo_dict['features']:
        try:
            if feature['properties']['type'] == 'Building':
                props = feature['properties']
                f_row = [props['id'], props['name'], hb_mapper]
                scenario_matrix.append(f_row)
        except KeyError:  # definitely not a building
            pass

    # write the scenario CSV file
    uo_folder = os.path.dirname(feature_geojson)
    scenario = os.path.join(uo_folder, 'honeybee_scenario.csv')
    with open(scenario, 'w') as fp:
        for row in scenario_matrix:
            fp.write('{}\n'.format(','.join(row)))
    return scenario


def _recommended_processor_count():
    """Get an integer for one less than the number of processors on this machine.

    This method should work on all of the major operating systems and in
    both IronPython and cPython. If, for whatever reason, the number of
    processors could not be sensed, a value of 1 will be returned.
    """
    try:  # assume that we are in cPython
        cpu_count = os.cpu_count()
    except AttributeError:  # we are probably in IronPython
        try:
            from System.Environment import ProcessorCount
            cpu_count = ProcessorCount
        except ImportError:  # no idea what Python this is; let's play it safe
            cpu_count = 1
    return 1 if cpu_count is None or cpu_count <= 1 else cpu_count - 1


def _run_urbanopt_windows(feature_geojson, scenario_csv):
    """Run a feature and scenario file through URBANopt on a Windows-based os.

    A batch file will be used to run the simulation.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        A tuple with two values.

        -   directory -- Path to the folder out of which the simulation was run.

        -   stderr -- The standard error message, which should get to the user
            in the event of simulation failure.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # Write the batch file to call URBANopt CLI
    working_drive = directory[:2]
    batch = '{}\ncd {}\ncall "{}"\nuo run -f "{}" -s "{}"'.format(
        working_drive, working_drive, folders.urbanopt_env_path,
        feature_geojson, scenario_csv)
    batch_file = os.path.join(directory, 'run_simulation.bat')
    write_to_file(batch_file, batch, True)
    # run the batch file
    process = subprocess.Popen(
        '"{}"'.format(batch_file), stderr=subprocess.PIPE, env=PYTHON_ENV
    )
    result = process.communicate()
    stderr = result[1]
    return directory, stderr


def _run_urbanopt_unix(feature_geojson, scenario_csv):
    """Run a feature and scenario file through URBANopt on a Unix-based os.

    This includes both Mac OS and Linux since a shell will be used to run
    the simulation.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        A tuple with two values.

        -   directory -- Path to the folder out of which the simulation was run.

        -   stderr -- The standard error message, which should get to the user
            in the event of simulation failure.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # Write the shell script to call URBANopt CLI
    shell = '#!/usr/bin/env bash\nsource "{}"\nuo run -f "{}" -s "{}"'.format(
        folders.urbanopt_env_path, feature_geojson, scenario_csv)
    shell_file = os.path.join(directory, 'run_simulation.sh')
    write_to_file(shell_file, shell, True)
    # make the shell script executable using subprocess.check_call
    # this is more reliable than native Python chmod on Mac
    subprocess.check_call(['chmod', 'u+x', shell_file])
    # run the shell script
    process = subprocess.Popen(
        '"{}"'.format(shell_file), stderr=subprocess.PIPE, env=PYTHON_ENV, shell=True
    )
    result = process.communicate()
    stderr = result[1]
    return directory, stderr


def _check_urbanopt_file(feature_geojson, scenario_csv):
    """Prepare an OSW file to be run through URBANopt CLI.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        The folder in which the OSW exists and out of which the OpenStudio CLI
        will operate.
    """
    # check the input files
    assert os.path.isfile(feature_geojson), \
        'No feature file found at {}.'.format(feature_geojson)
    assert os.path.isfile(scenario_csv), \
        'No scenario file found at {}.'.format(scenario_csv)
    return os.path.split(feature_geojson)[0]


def _output_urbanopt_files(directory, stderr=''):
    """Get the paths to the simulation output files given the urbanopt directory.

    Args:
        directory: The path to where the URBANopt feature and scenario files
            were simulated.
        stderr: The URBANopt standard error message, which will be returned to
            the user in the event that no simulation folder was found.

    Returns:
        A series of file paths to the simulation output files

        -   osm -- Array of paths to .osm files for all generated OpenStudio models.

        -   idf -- Array of paths to .idf files containing the input for the
            EnergyPlus simulation.

        -   sql -- Array of paths to .sqlite files containing all simulation results.

        -   zsz -- Array of paths to .csv files containing detailed zone load
            information recorded over the course of the design days.

        -   rdd -- Array of paths to .rdd files containing all possible outputs
            that can be requested from the simulation.

        -   html -- Array of paths to .htm files containing all summary reports.

        -   err -- Array of paths to .err files containing all errors and
            warnings from the simulation.
    """
    # empty list which will be filled with simulation output files
    osm = []
    idf = []
    sql = []
    zsz = []
    rdd = []
    html = []
    err = []

    # parse the GeoJSON so that we can get the correct order of result files
    sim_dir = os.path.join(directory, 'run', 'honeybee_scenario')
    if not os.path.isdir(sim_dir):
        msg = 'The URBANopt simulation failed to run.\n' \
            'No results were found at:\n{}\n{}'.format(sim_dir, stderr)
        print(msg)
        raise Exception(msg)
    geojson = [f for f in os.listdir(directory) if f.endswith('.geojson')]
    if len(geojson) == 1:
        geo_file = os.path.join(directory, geojson[0])
        with open(geo_file, 'r') as base_file:
            geo_dict = json.load(base_file)
        bldg_names = []
        for ft in geo_dict['features']:
            if 'properties' in ft and 'type' in ft['properties']:
                if ft['properties']['type'] == 'Building' and 'id' in ft['properties']:
                    bldg_names.append(ft['properties']['id'])
    else:
        bldg_names = os.listdir(sim_dir)

    # generate paths to the simulation files and check their existence
    for bldg_name in bldg_names:
        bldg_dir = os.path.join(sim_dir, bldg_name)
        osm_file = os.path.join(bldg_dir, 'in.osm')
        if os.path.isfile(osm_file):
            osm.append(osm_file)
        idf_file = os.path.join(bldg_dir, 'in.idf')
        if os.path.isfile(idf_file):
            idf.append(idf_file)
        sql_file = os.path.join(bldg_dir, 'eplusout.sql')
        if os.path.isfile(sql_file):
            sql.append(sql_file)
        zsz_file = os.path.join(bldg_dir, 'epluszsz.csv')
        if os.path.isfile(zsz_file):
            zsz.append(zsz_file)
        rdd_file = os.path.join(bldg_dir, 'eplusout.rdd')
        if os.path.isfile(rdd_file):
            rdd.append(rdd_file)
        html_file = os.path.join(bldg_dir, 'eplustbl.htm')
        if os.path.isfile(html_file):
            html.append(html_file)
        err_file = os.path.join(bldg_dir, 'eplusout.err')
        if os.path.isfile(err_file):
            err.append(err_file)

    return osm, idf, sql, zsz, rdd, html, err


def _run_default_report_windows(feature_geojson, scenario_csv):
    """Generate default reports on a Windows-based os.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        Paths to the scenario CSV and JSON reports.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # Write the batch file to call URBANopt CLI
    working_drive = directory[:2]
    batch = '{}\ncd {}\ncall "{}"\nuo process --default -f "{}" -s "{}"'.format(
        working_drive, working_drive, folders.urbanopt_env_path,
        feature_geojson, scenario_csv)
    batch_file = os.path.join(directory, 'run_default_report.bat')
    write_to_file(batch_file, batch, True)
    # run the batch file and return output files
    os.system('"{}"'.format(batch_file))
    result_folder = os.path.basename(scenario_csv).lower().replace('.csv', '')
    run_folder = os.path.join(directory, 'run', result_folder)
    return os.path.join(run_folder, 'default_scenario_report.csv'), \
        os.path.join(run_folder, 'default_scenario_report.json')


def _run_default_report_unix(feature_geojson, scenario_csv):
    """Generate default reports on a Unix-based os.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        Paths to the scenario CSV and JSON reports.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # Write the shell script to call OpenStudio CLI
    shell = '#!/usr/bin/env bash\nsource "{}"\n' \
        'uo process --default -f "{}" -s "{}"'.format(
            folders.urbanopt_env_path, feature_geojson, scenario_csv)
    shell_file = os.path.join(directory, 'run_default_report.sh')
    write_to_file(shell_file, shell, True)
    # make the shell script executable using subprocess.check_call
    # this is more reliable than native Python chmod on Mac
    subprocess.check_call(['chmod', 'u+x', shell_file])
    # run the shell script
    subprocess.call(shell_file)
    result_folder = os.path.basename(scenario_csv).lower().replace('.csv', '')
    run_folder = os.path.join(directory, 'run', result_folder)
    return os.path.join(run_folder, 'default_scenario_report.csv'), \
        os.path.join(run_folder, 'default_scenario_report.json')


def _run_reopt_windows(feature_geojson, scenario_csv, developer_key):
    """Run a feature and scenario file through REopt on a Windows-based os.

    A batch file will be used to run the simulation.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.
        developer_key: Text string for the NREL developer key.

    Returns:
        Path to the folder in which results should be contained.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # Write the batch file to call URBANopt CLI
    working_drive = directory[:2]
    batch = '{}\ncd {}\ncall "{}"\nSET GEM_DEVELOPER_KEY={}\n' \
        'uo process --reopt-scenario -f "{}" -s "{}"'.format(
            working_drive, working_drive, folders.urbanopt_env_path, developer_key,
            feature_geojson, scenario_csv)
    batch_file = os.path.join(directory, 'run_reopt.bat')
    write_to_file(batch_file, batch, True)
    # run the batch file
    os.system('"{}"'.format(batch_file))
    result_folder = os.path.basename(scenario_csv).lower().replace('.csv', '')
    return os.path.join(directory, 'run', result_folder)


def _run_reopt_unix(feature_geojson, scenario_csv, developer_key):
    """Run a feature and scenario file through REopt on a Unix-based os.

    This includes both Mac OS and Linux since a shell will be used to run
    the simulation.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.
        developer_key: Text string for the NREL developer key.

    Returns:
        Path to the folder in which results should be contained.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # Write the shell script to call OpenStudio CLI
    shell = '#!/usr/bin/env bash\nsource "{}"\nGEM_DEVELOPER_KEY={}\n' \
        'uo process --reopt-scenario -f "{}" -s "{}"'.format(
            folders.urbanopt_env_path, developer_key, feature_geojson, scenario_csv)
    shell_file = os.path.join(directory, 'run_reopt.sh')
    write_to_file(shell_file, shell, True)
    # make the shell script executable using subprocess.check_call
    # this is more reliable than native Python chmod on Mac
    subprocess.check_call(['chmod', 'u+x', shell_file])
    # run the shell script
    subprocess.call(shell_file)
    result_folder = os.path.basename(scenario_csv).lower().replace('.csv', '')
    return os.path.join(directory, 'run', result_folder)


def _output_reopt_files(directory):
    """Get the paths to the simulation output files given the reopt directory.

    Args:
        directory: The path to the folder in which results should be contained.

    Returns:
        A series of file paths to the simulation output files

        -   csv -- Path to a CSV file containing scenario optimization results.

        -   report_json -- Path to a JSON file containing scenario optimization results.
    """
    # generate paths to the simulation files
    csv_file = os.path.join(directory, 'scenario_optimization.csv')
    report_json_file = os.path.join(directory, 'scenario_optimization.json')
    # check that the simulation files exist
    csv = csv_file if os.path.isfile(csv_file) else None
    report_json = report_json_file if os.path.isfile(report_json_file) else None
    return csv, report_json


def _run_rnm_windows(feature_geojson, scenario_csv):
    """Run a feature and scenario file through RNM on a Windows-based os.

    A batch file will be used to run the simulation.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        Path to the project folder.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # Write the batch file to call URBANopt CLI
    working_drive = directory[:2]
    batch = '{}\ncd {}\ncall "{}"\nuo rnm --feature "{}" --scenario "{}"'.format(
        working_drive, working_drive, folders.urbanopt_env_path,
        feature_geojson, scenario_csv)
    batch_file = os.path.join(directory, 'run_rnm.bat')
    write_to_file(batch_file, batch, True)
    # run the batch file
    os.system('"{}"'.format(batch_file))
    return directory


def _run_rnm_unix(feature_geojson, scenario_csv):
    """Run a feature and scenario file through RNM on a Unix-based os.

    This includes both Mac OS and Linux since a shell script will be used to run
    the simulation.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        Path to the project folder.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # Write the shell script to call URBANopt CLI
    shell = '#!/usr/bin/env bash\nsource "{}"\nuo rnm --feature "{}" -s-scenario ' \
        '"{}"'.format(folders.urbanopt_env_path, feature_geojson, scenario_csv)
    shell_file = os.path.join(directory, 'run_rnm.sh')
    write_to_file(shell_file, shell, True)
    # make the shell script executable using subprocess.check_call
    # this is more reliable than native Python chmod on Mac
    subprocess.check_call(['chmod', 'u+x', shell_file])
    # run the shell script
    subprocess.call(shell_file)
    return directory


def _generate_modelica_windows(sys_param_json, feature_geojson, scenario_csv):
    """Generate Modelica files for a DES on a Windows-based os.

    A batch file will be used to run the simulation.

    Args:
        sys_param_json: The full path to a system parameter JSON from which the
            Modelica files will be generated.
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        A tuple with two values.

        -   modelica_dir -- Path to the folder in which the Modelica files were written.

        -   stderr -- The standard error message, which should get to the user
            in the event of simulation failure.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # get the path to the MBL installation
    install_directory = os.path.join(lb_folders.ladybug_tools_folder, 'resources')
    mbl_dir = os.path.join(install_directory, 'mbl')
    assert os.path.isdir(mbl_dir), \
        'No Modelica Buildings Library installation was found on this machine.'
    # get the paths to the output files
    scn_name = os.path.basename(scenario_csv).replace('.csv', '')
    modelica_dir = os.path.join(directory, 'run', scn_name, 'des_modelica')
    uo_des_exe = os.path.join(hb_folders.python_scripts_path, 'uo_des.exe')
    # Write the batch file to call the GMT
    working_drive = directory[:2]
    batch = '{}\ncd {}\ncall "{}"\nSET "MODELICAPATH={}"\n"{}" create-model ' \
        '"{}" "{}" "{}" --overwrite'.format(
            working_drive, working_drive, folders.urbanopt_env_path, mbl_dir,
            uo_des_exe, sys_param_json, feature_geojson, modelica_dir)
    batch_file = os.path.join(directory, 'generate_modelica.bat')
    write_to_file(batch_file, batch, True)
    # run the batch file
    process = subprocess.Popen(
        '"{}"'.format(batch_file), stderr=subprocess.PIPE, env=PYTHON_ENV
    )
    result = process.communicate()
    stderr = result[1]
    return modelica_dir, stderr


def _generate_modelica_unix(sys_param_json, feature_geojson, scenario_csv):
    """Generate Modelica files for a DES on a Unix-based os.

    This includes both Mac OS and Linux since a shell will be used to run
    the simulation.

    Args:
        sys_param_json: The full path to a system parameter JSON from which the
            Modelica files will be generated.
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        A tuple with two values.

        -   directory -- Path to the folder out of which the simulation was run.

        -   stderr -- The standard error message, which should get to the user
            in the event of simulation failure.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # get the path to the MBL installation
    install_directory = os.path.join(lb_folders.ladybug_tools_folder, 'resources')
    mbl_dir = os.path.join(install_directory, 'mbl')
    assert os.path.isdir(mbl_dir), \
        'No Modelica Buildings Library installation was found on this machine.'
    # get the paths to the output files
    scn_name = os.path.basename(scenario_csv).replace('.csv', '')
    modelica_dir = os.path.join(directory, 'run', scn_name, 'des_modelica')
    uo_des_exe = os.path.join(hb_folders.python_scripts_path, 'uo_des')
    # write the shell script to call the GMT
    shell = '#!/usr/bin/env bash\nsource "{}"\nexport MODELICAPATH="{}"\n' \
        '"{}" create-model "{}" "{}" "{}" --overwrite'.format(
            folders.urbanopt_env_path, mbl_dir,
            uo_des_exe, sys_param_json, feature_geojson, modelica_dir)
    shell_file = os.path.join(directory, 'generate_modelica.sh')
    write_to_file(shell_file, shell, True)
    # make the shell script executable using subprocess.check_call
    # this is more reliable than native Python chmod on Mac
    subprocess.check_call(['chmod', 'u+x', shell_file])
    # run the shell script
    process = subprocess.Popen(
        '"{}"'.format(shell_file), stderr=subprocess.PIPE, env=PYTHON_ENV, shell=True
    )
    result = process.communicate()
    stderr = result[1]
    return modelica_dir, stderr


def _add_water_heating_patch(modelica_dir):
    """Add a dummy value for water heating for MBL 10 limitation."""
    data_dir = os.path.join(modelica_dir, 'Loads', 'Resources', 'Data')
    if os.path.isdir(data_dir):
        for bldg_dir in os.listdir(data_dir):
            mo_load_file = os.path.join(data_dir, bldg_dir, 'modelica.mos')
            if os.path.isfile(mo_load_file):
                fixed_lines, fl_found = [], False
                with open(mo_load_file, 'r') as mlf:
                    for line in mlf:
                        if line == '#Peak water heating load = 0 Watts\n':
                            nl = '#Peak water heating load = 1 Watts\n'
                            fixed_lines.append(nl)
                        elif not fl_found and ';' in line:
                            split_vals = line.split(';')
                            split_vals[-1] = '1.0\n'
                            fixed_lines.append(';'.join(split_vals))
                            fl_found = True
                        else:
                            fixed_lines.append(line)
                with open(mo_load_file, 'w') as mlf:
                    mlf.write(''.join(fixed_lines))


def _run_modelica_windows(modelica_project_dir):
    """Execute Modelica files of a DES on a Windows-based OS.

    A batch file will be used to run the simulation.

    Args:
        modelica_project_dir: The full path to the folder in which the Modelica
            files were written.

    Returns:
        A tuple with two values.

        -   results -- Path to where the results were written.

        -   stderr -- The standard error message, which should get to the user
            in the event of simulation failure.
    """
    # make sure that docker is installed
    assert folders.docker_version_str is not None, \
        'No Docker installation was found on this machine.\n' \
        'This is needed to execute Modelica simulations.'
    # get the paths to the output files
    directory = os.path.dirname(modelica_project_dir)
    project_name = os.path.basename(modelica_project_dir)
    results = os.path.join(
        modelica_project_dir,
        '{}.Districts.DistrictEnergySystem_results'.format(project_name))
    uo_des_exe = os.path.join(hb_folders.python_scripts_path, 'uo_des.exe')
    # Write the batch file to call the GMT
    working_drive = modelica_project_dir[:2]
    batch = '{}\ncd {}\ncall "{}"\n"{}" run-model "{}"'.format(
        working_drive, working_drive, folders.urbanopt_env_path,
        uo_des_exe, modelica_project_dir)
    batch_file = os.path.join(directory, 'run_modelica.bat')
    write_to_file(batch_file, batch, True)
    # run the batch file
    process = subprocess.Popen(
        '"{}"'.format(batch_file), stderr=subprocess.PIPE, env=PYTHON_ENV
    )
    result = process.communicate()
    stderr = result[1]
    return results, stderr


def _run_modelica_unix(modelica_project_dir):
    """Execute Modelica files of a DES on a Unix-based OS.

    This includes both Mac OS and Linux since a shell will be used to run
    the simulation.

    Args:
        modelica_project_dir: The full path to the folder in which the Modelica
            files were written.

    Returns:
        A tuple with two values.

        -   results -- Path to where the results were written.

        -   stderr -- The standard error message, which should get to the user
            in the event of simulation failure.
    """
    # make sure that docker is installed
    assert folders.docker_version_str is not None, \
        'No Docker installation was found on this machine.\n' \
        'This is needed to execute Modelica simulations.'
    # get the paths to the output files
    directory = os.path.dirname(modelica_project_dir)
    project_name = os.path.basename(modelica_project_dir)
    results = os.path.join(
        modelica_project_dir,
        '{}.Districts.DistrictEnergySystem_results'.format(project_name))
    uo_des_exe = os.path.join(hb_folders.python_scripts_path, 'uo_des')
    # write the shell script to call the GMT
    shell = '#!/usr/bin/env bash\nsource "{}"\n"{}" run-model "{}"'.format(
        folders.urbanopt_env_path, uo_des_exe, modelica_project_dir)
    shell_file = os.path.join(directory, 'run_modelica.sh')
    write_to_file(shell_file, shell, True)
    # make the shell script executable using subprocess.check_call
    # this is more reliable than native Python chmod on Mac
    subprocess.check_call(['chmod', 'u+x', shell_file])
    # run the shell script
    process = subprocess.Popen(
        '"{}"'.format(shell_file), stderr=subprocess.PIPE, env=PYTHON_ENV, shell=True
    )
    result = process.communicate()
    stderr = result[1]
    return results, stderr
