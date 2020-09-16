# coding=utf-8
"""Module for running geoJSON and OpenStudio files through URBANopt."""
from __future__ import division

from .config import folders
from honeybee_energy.config import folders as hb_energy_folders

import os
import json
import shutil
import subprocess

from ladybug.futil import preparedir, write_to_file


def base_honeybee_osw(
        project_directory, sim_par_json=None, additional_measures=None, base_osw=None,
        epw_file=None, skip_report=True):
    """Create a honeybee_workflow.osw to be used as a base in URBANopt simulations.

    This method will also copy the Honeybee.rb mapper to this folder if it is
    available in the config of this library.

    Args:
        project_directory: Full path to a folder out of which the URBANopt simulation
            will be run. This is the folder that contains the feature geoJSON.
        sim_par_json: Optional file path to the SimulationParameter JSON.
            If None, the OpenStudio models generated in the URBANopt run will
            not have everything they need to be simulate-able unless such parameters
            are supplied from one of the additional_measures or the base_osw.
        additional_measures: An optional array of honeybee-energy Measure objects
            to be included in the output osw. These Measure objects must have
            values for all required input arguments or an exception will be
            raised while running this function.
        base_osw: Optional file path to an existing OSW JSON be used as the base
            for the honeybee_workflow.osw. This is another way that outside measures
            can be incorporated into the workflow.
        epw_file: Optional file path to an EPW that should be associated with the
            output energy model.
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
    if additional_measures:
        measure_paths = set()  # set of all unique measure paths
        # ensure measures are correctly ordered
        m_dict = {'ModelMeasure': [], 'EnergyPlusMeasure': [], 'ReportingMeasure': []}
        for measure in additional_measures:
            m_dict[measure.type].append(measure)
        sorted_measures = m_dict['ModelMeasure'] + m_dict['EnergyPlusMeasure'] + \
            m_dict['ReportingMeasure']
        for measure in sorted_measures:
            measure.validate()  # ensure that all required arguments have values
            measure_paths.add(os.path.dirname(measure.folder))
            osw_dict['steps'].append(measure.to_osw_dict())  # add measure to workflow
        for m_path in measure_paths:  # add outside measure paths
            osw_dict['measure_paths'].append(m_path)

    # add default feature reports if they aren't already in the steps
    all_measures = [step['measure_dir_name'] for step in osw_dict['steps']]
    if 'default_feature_reports' not in all_measures:
        report_measure_dict = {
            'arguments': {
                'feature_id': None,
                'feature_name': None,
                'feature_type': None
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
    uo -m command is run to generate the scenario .csv file from the exported
    geoJSON and mapper.

    Args:
        feature_geojson: An URBANopt feature geoJSON to be prepared for URBANopt
            simulation.
        cpu_count: A positive integer for the number of CPUs to use in the
            simulation. (Default: 2).
        verbose: Boolean to note if the simulation should be run with verbose
            reporting of progress.

    Returns:
        Path to the .csv file for the URBANopt scenario.
    """
    # copy the Gemfile into the folder containing the feature_geojson
    assert folders.urbanopt_gemfile_path, \
        'No URBANopt Gemfile was found in dragonfly_energy.config.folders.\n' \
        'This file must exist to run URBANopt.'
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

    # run the command to generate the scenario csv file
    if os.name == 'nt':  # we are on Windows
        _make_scenario_windows(feature_geojson)
    else:  # we are on Mac, Linux, or some other unix-based system
        _make_scenario_unix(feature_geojson)
    scenario = os.path.join(uo_folder, 'honeybee_scenario.csv')
    assert os.path.isfile(scenario), \
        'URBANopt scenario CSV creation creation failed.\n' \
        'Be sure that you have installed the URBANopt CLI correctly.'

    return scenario


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
    assert folders.urbanopt_env_path, \
        'No URBANopt installation was found in dragonfly_energy.config.folders.'
    # run the simulation
    if os.name == 'nt':  # we are on Windows
        directory = _run_urbanopt_windows(feature_geojson, scenario_csv)
    else:  # we are on Mac, Linux, or some other unix-based system
        directory = _run_urbanopt_unix(feature_geojson, scenario_csv)

    # output the simulation files
    return _output_urbanopt_files(directory)


def _make_scenario_windows(feature_geojson):
    """Generate a scenario file using URBANopt CLI on a Windows-based os.

    A batch file will be used to run the URBANopt CLI.

    Args:
        feature_geojson: The full path to a .geojson file.
    """
    directory, feature_name = os.path.split(feature_geojson)
    clean_feature = feature_geojson.replace('\\', '/')
    # Write the batch file to call URBANopt CLI
    working_drive = directory[:2]
    batch = '{}\ncd {}\ncall {}\nuo create -s {}'.format(
        working_drive, working_drive, folders.urbanopt_env_path, clean_feature)
    batch_file = os.path.join(directory, 'make_scenario.bat')
    write_to_file(batch_file, batch, True)

    # run the batch file
    os.system(batch_file)


def _make_scenario_unix(feature_geojson):
    """Generate a scenario file using URBANopt CLI on a Unix-based os.

    This includes both Mac OS and Linux since a shell will be used to run
    the URBANopt CLI.

    Args:
        feature_geojson: The full path to a .geojson file.
    """
    directory, feature_name = os.path.split(feature_geojson)
    clean_feature = feature_geojson.replace('\\', '/')
    # Write the shell script to call OpenStudio CLI
    shell = '#!/usr/bin/env bash\nsource {}\nuo create -s {}'.format(
        folders.urbanopt_env_path, clean_feature)
    shell_file = os.path.join(directory, 'make_scenario.sh')
    write_to_file(shell_file, shell, True)

    # make the shell script executable using subprocess.check_call
    # this is more reliable than native Python chmod on Mac
    subprocess.check_call(['chmod', 'u+x', shell_file])

    # run the shell script
    subprocess.call(shell_file)


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
