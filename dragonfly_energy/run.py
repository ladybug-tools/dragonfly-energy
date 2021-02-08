# coding=utf-8
"""Module for running geoJSON and OpenStudio files through URBANopt."""
from __future__ import division

import os
import json
import shutil
import subprocess

from .config import folders
from .measure import MapperMeasure
from .reopt import REoptParameter

from honeybee_energy.config import folders as hb_energy_folders
from ladybug.futil import preparedir, write_to_file


def base_honeybee_osw(
        project_directory, sim_par_json=None, additional_measures=None,
        additional_mapper_measures=None, base_osw=None, epw_file=None, skip_report=True):
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
            in the base_osw or additional_measures (Default: True)

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

    # addd the model json serialization into the steps
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

    # add default feature reports if they aren't already in the steps
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

    # assign the epw_file to the osw if it is input
    if epw_file is not None:
        osw_dict['weather_file'] = epw_file

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


def prepare_urbanopt_folder(feature_geojson, cpu_count=2, verbose=False):
    """Prepare a directory with a feature geoJSON for URBANopt simulation.

    This includes copying the Gemfile to the folder and generating the runner.conf
    to specify the number of CPUs to be used in the simulation. Lastly, the
    the scenario .csv file will be generated from the feature_geojson.

    Args:
        feature_geojson: An URBANopt feature geoJSON to be prepared for URBANopt
            simulation.
        cpu_count: A positive integer for the number of CPUs to use in the
            simulation. (Default: 2).
        verbose: Boolean to note if the simulation should be run with verbose
            reporting of progress. (Default: False).

    Returns:
        Path to the .csv file for the URBANopt scenario.
    """
    # copy the Gemfile into the folder containing the feature_geojson
    assert folders.urbanopt_gemfile_path, \
        'No URBANopt Gemfile was found in dragonfly_energy.config.folders.\n' \
        'This file must exist to run URBANopt.'
    if not folders.urbanopt_env_path:
        folders.generate_urbanopt_env_path()
    assert folders.urbanopt_env_path, \
        'No URBANopt installation was found in dragonfly_energy.config.folders.'
    uo_folder = os.path.dirname(feature_geojson)
    shutil.copy(folders.urbanopt_gemfile_path, os.path.join(uo_folder, 'Gemfile'))

    # generate the runner.conf to set the number of CPUs based on the input
    runner_dict = {
        'file_version': '0.1.0',
        'max_datapoints': 1000000000,
        'num_parallel': cpu_count,
        'run_simulations': True,
        'verbose': False
    }
    runner_conf = os.path.join(uo_folder, 'runner.conf')
    with open(runner_conf, 'w') as fp:
        json.dump(runner_dict, fp, indent=2)

    # generate the scenario csv file
    return _make_scenario(feature_geojson)


def run_urbanopt(feature_geojson, scenario_csv):
    """Run a feature and scenario file through URBANopt on any operating system.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

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
    if not folders.urbanopt_env_path:
        folders.generate_urbanopt_env_path()
    assert folders.urbanopt_env_path, \
        'No URBANopt installation was found in dragonfly_energy.config.folders.'
    # run the simulation
    if os.name == 'nt':  # we are on Windows
        directory = _run_urbanopt_windows(feature_geojson, scenario_csv)
    else:  # we are on Mac, Linux, or some other unix-based system
        directory = _run_urbanopt_unix(feature_geojson, scenario_csv)

    # output the simulation files
    return _output_urbanopt_files(directory)


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
    if not folders.urbanopt_env_path:
        folders.generate_urbanopt_env_path()
    assert folders.urbanopt_env_path, \
        'No URBANopt installation was found in dragonfly_energy.config.folders.'
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
    if not folders.urbanopt_env_path:
        folders.generate_urbanopt_env_path()
    assert folders.urbanopt_env_path, \
        'No URBANopt installation was found in dragonfly_energy.config.folders.'
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
    if reopt_parameters is None:  # genrate some defaults
        reopt_parameters = REoptParameter()
        reopt_parameters.pv_parameter.max_kw = 1000000000
        reopt_parameters.storage_parameter.max_kw = 1000000
        reopt_parameters.generator_parameter.max_kw = 1000000000
    else:
        assert isinstance(reopt_parameters, REoptParameter), \
            'Expected REoptParameter. Got {}.'.format(type(reopt_parameters))
    reopt_folder =  os.path.join(project_folder, 'reopt')
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


def _run_urbanopt_windows(feature_geojson, scenario_csv):
    """Run a feature and scenario file through URBANopt on a Windows-based os.

    A batch file will be used to run the simulation.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        Path to the folder out of which the simulation was run.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # Write the batch file to call URBANopt CLI
    working_drive = directory[:2]
    batch = '{}\ncd {}\ncall {}\nuo run -f {} -s {}'.format(
        working_drive, working_drive, folders.urbanopt_env_path,
        feature_geojson, scenario_csv)
    batch_file = os.path.join(directory, 'run_simulation.bat')
    write_to_file(batch_file, batch, True)
    # run the batch file
    os.system(batch_file)
    return directory


def _run_urbanopt_unix(feature_geojson, scenario_csv):
    """Run a feature and scenario file through URBANopt on a Unix-based os.

    This includes both Mac OS and Linux since a shell will be used to run
    the simulation.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        Path to the folder out of which the simulation was run.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_geojson, scenario_csv)
    # Write the shell script to call OpenStudio CLI
    shell = '#!/usr/bin/env bash\nsource {}\nuo -r -f {} -s {}'.format(
        folders.urbanopt_env_path, feature_geojson, scenario_csv)
    shell_file = os.path.join(directory, 'run_simulation.sh')
    write_to_file(shell_file, shell, True)
    # make the shell script executable using subprocess.check_call
    # this is more reliable than native Python chmod on Mac
    subprocess.check_call(['chmod', 'u+x', shell_file])
    # run the shell script
    subprocess.call(shell_file)
    return directory


def _check_urbanopt_file(feature_geojson, scenario_csv):
    """Prepare an OSW file to be run through OpenStudio CLI.

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


def _output_urbanopt_files(directory):
    """Get the paths to the simulation output files given the urbanopt directory.

    Args:
        directory: The path to where the URBANopt feature and scenario files
            were simulated.

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

    # generate paths to the simulation files and check their existence
    sim_dir = os.path.join(directory, 'run', 'honeybee_scenario')
    for bldg_name in os.listdir(sim_dir):
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
    batch = '{}\ncd {}\ncall {}\nuo process --default -f {} -s {}'.format(
        working_drive, working_drive, folders.urbanopt_env_path,
        feature_geojson, scenario_csv)
    batch_file = os.path.join(directory, 'run_default_report.bat')
    write_to_file(batch_file, batch, True)
    # run the batch file and return output files
    os.system(batch_file)
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
    shell = '#!/usr/bin/env bash\nsource {}\n' \
        'uo process --default -f {} -s {}'.format(
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
    batch = '{}\ncd {}\ncall {}\nSET GEM_DEVELOPER_KEY={}\n' \
        'uo process --reopt-scenario -f {} -s {}'.format(
            working_drive, working_drive, folders.urbanopt_env_path, developer_key,
            feature_geojson, scenario_csv)
    batch_file = os.path.join(directory, 'run_reopt.bat')
    write_to_file(batch_file, batch, True)
    # run the batch file
    os.system(batch_file)
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
    shell = '#!/usr/bin/env bash\nsource {}\nGEM_DEVELOPER_KEY={}\n' \
        'uo process --reopt-scenario -f {} -s {}'.format(
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
