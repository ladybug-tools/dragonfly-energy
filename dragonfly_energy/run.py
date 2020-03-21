# coding=utf-8
"""Module for running geoJSON and OpenStudio files through URBANopt."""
from __future__ import division

import os
import json
import shutil
import subprocess

from ladybug.futil import nukedir, write_to_file


def prepare_urbanopt_folder(uo_folder, geojson_dict, epw_file_path, cpu_count=2):
    """Prepare a directory for URBANopt simulation.

    This includes deleting any uo_folder that already exists, running the uo -p
    command, and deleting several files it generates like example_project.json,
    the Buffalo EPW files, the .osm files, and the HighEfficiency mapper. Then,
    a geoJOSN is exported using the input geojson_dict. Then, the ChangeBuildingLocation
    measure is skipped in the base_workdlow.osw. Lastly, the uo -m command
    is run to generate the scenario csv file from the exported geoJSON and
    Baseline mapper.

    Args:
        uo_folder: The directory into which the URBANopt simulation will be run.
        geojson_dict: A Python dictionary in a geoJSON style, which will serve
            as the basis of a feature file for the URBANopt simulation. This
            dictionary can be obtained from a dragonfly Model by calling the
            to_geojson_dict method.
        epw_file_path: The full path to an EPW file to be used for the simulation.
        cpu_count: A positive integer for the number of CPUs to use in the
            simulation. (Default: 2).

    Returns:
        Paths to the following files

        -   feature -- Path to a .geojson file containing the footprints of buildings
            to be simulated.

        -   scenario -- Path to a .csv file for the URBANopt scenario.
    """
    # nuke the directory if it already exists
    if os.path.isdir(uo_folder):
        nukedir(uo_folder, True)
    
    # run the folder creation command and check that it was created
    cmd_str = 'uo -p {}'.format(uo_folder)
    os.system(cmd_str)
    assert os.path.isfile(os.path.join(uo_folder, 'Gemfile')), \
        'URBANopt project folder creation failed.\n' \
        'Be sure that you have installed the URBANopt CLI correctly.'

    # delete the EPW file and replace it with the correct file
    weather_dir = os.path.join(uo_folder, 'weather')
    nukedir(weather_dir, False)
    epw_name = os.path.split(epw_file_path)[-1]
    shutil.copy(epw_file_path, os.path.join(weather_dir, epw_name))

    # delete the OSM files and the HighEfficiency mapper
    osm_dir = os.path.join(uo_folder, 'osm_building')
    nukedir(osm_dir, False)
    os.remove(os.path.join(uo_folder, 'mappers', 'HighEfficiency.rb'))

    # skip the ChangeBuildingLocation measure
    base_osw = os.path.join(uo_folder, 'mappers', 'base_workflow.osw')
    with open(base_osw, 'r+') as f:
        data = json.load(f)
        data['steps'][1]['arguments']['__SKIP__'] = True
        f.seek(0)  # reset file position to the beginning
        json.dump(data, f, indent=2)
        f.truncate()  # remove remaining part
    
    # set the CPU count based on the input
    if cpu_count != 2:
        runner_conf = os.path.join(uo_folder, 'runner.conf')
        with open(runner_conf, 'r+') as f:
            data = json.load(f)
            data['num_parallel'] = cpu_count
            f.seek(0)  # reset file position to the beginning
            json.dump(data, f, indent=2)
            f.truncate()  # remove remaining part

    # delete the example_project.json and write out the geoJSON
    os.remove(os.path.join(uo_folder, 'example_project.json'))
    try:
        model_name = geojson_dict['project']['id']
        geojson_dict['project']['weather_filename'] = epw_name
    except KeyError:
        model_name = 'unnamed'
    feature = os.path.join(uo_folder, '{}.geojson'.format(model_name))
    with open(feature, 'w') as fp:
        json.dump(geojson_dict, fp, indent=4)

    # run the command to generate the scenario csv file
    if os.name == 'nt':  # we are on Windows
        _make_scenario_windows(feature)
    else:  # we are on Mac, Linux, or some other unix-based system
        _make_scenario_unix(feature)
    scenario = os.path.join(uo_folder, 'baseline_scenario.csv')
    assert os.path.isfile(scenario), \
        'URBANopt scenario CSV creation creation failed.'

    return feature, scenario


def run_urbanopt(feature_file_path, scenario_file_path):
    """Run a feature and scenario file through URBANopt on any operating system.

    Args:
        feature_file_path: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_file_path: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        A series of file paths to the simulation output files

        -   sql -- Array of paths to .sqlite files containing all simulation results.

        -   zsz -- Array of paths to .csv files containing detailed zone load
            information recorded over the course of the design days.

        -   rdd -- Array of paths to .rdd files containing all possible outputs
            that can be requested from the simulation.

        -   html -- Array of paths to .html files containing all summary reports.

        -   err -- Array of paths to .err files containing all errors and warnings from the
            simulation.
    """
    # run the simulation
    if os.name == 'nt':  # we are on Windows
        directory = _run_urbanopt_windows(feature_file_path, scenario_file_path)
    else:  # we are on Mac, Linux, or some other unix-based system
        directory = _run_urbanopt_unix(feature_file_path, scenario_file_path)

    # output the simulation files
    return _output_urbanopt_files(directory)


def _make_scenario_windows(feature_file_path):
    """Generate a scenario file using URBANopt CLI on a Windows-based os.

    A batch file will be used to run the URBANopt CLI.

    Args:
        feature_file_path: The full path to a .geojson file.
    """
    directory, feature_name = os.path.split(feature_file_path)
    clean_feature = feature_file_path.replace('\\', '/')
    # Write the batch file to call URBANopt CLI
    working_drive = directory[:2]
    batch = '{}\ncd {}\nuo -m -f {}'.format(
        working_drive, directory, clean_feature)
    batch_file = os.path.join(directory, 'make_scenario.bat')
    write_to_file(batch_file, batch, True)

    # run the batch file
    os.system(batch_file)


def _make_scenario_unix(feature_file_path):
    """Generate a scenario file using URBANopt CLI on a Unix-based os.

    This includes both Mac OS and Linux since a shell will be used to run
    the URBANopt CLI.

    Args:
        feature_file_path: The full path to a .geojson file.
    """
    directory, feature_name = os.path.split(feature_file_path)
    clean_feature = feature_file_path.replace('\\', '/')
    # Write the shell script to call OpenStudio CLI
    shell = '#!/usr/bin/env bash\nuo -m -f {}'.format(clean_feature)
    shell_file = os.path.join(directory, 'make_scenario.sh')
    write_to_file(shell_file, shell, True)

    # make the shell script executable using subprocess.check_call
    # this is more reliable than native Python chmod on Mac
    subprocess.check_call(['chmod','u+x', shell_file])

    # run the shell script
    subprocess.call(shell_file)


def _run_urbanopt_windows(feature_file_path, scenario_file_path):
    """Run a feature and scenario file through URBANopt on a Windows-based os.

    A batch file will be used to run the simulation.

    Args:
        feature_file_path: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_file_path: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        Path to the folder out of which the simulation was run.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_file_path, scenario_file_path)

    # Write the batch file to call URBANopt CLI
    working_drive = directory[:2]
    batch = '{}\nuo -r -f {} -s {}'.format(
        working_drive, feature_file_path, scenario_file_path)
    batch_file = os.path.join(directory, 'run_simulation.bat')
    write_to_file(batch_file, batch, True)

    # run the batch file
    os.system(batch_file)

    return directory


def _run_urbanopt_unix(feature_file_path, scenario_file_path):
    """Run a feature and scenario file through URBANopt on a Unix-based os.

    This includes both Mac OS and Linux since a shell will be used to run
    the simulation.

    Args:
        feature_file_path: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_file_path: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        Path to the folder out of which the simulation was run.
    """
    # check the input file
    directory = _check_urbanopt_file(feature_file_path, scenario_file_path)

    # Write the shell script to call OpenStudio CLI
    shell = '#!/usr/bin/env bash\nuo -r -f {} -s {}'.format(
        feature_file_path, scenario_file_path)
    shell_file = os.path.join(directory, 'run_simulation.sh')
    write_to_file(shell_file, shell, True)

    # make the shell script executable using subprocess.check_call
    # this is more reliable than native Python chmod on Mac
    subprocess.check_call(['chmod','u+x', shell_file])

    # run the shell script
    subprocess.call(shell_file)

    return directory


def _check_urbanopt_file(feature_file_path, scenario_file_path):
    """Prepare an OSW file to be run through OpenStudio CLI.

    Args:
        feature_file_path: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_file_path: The full path to  a .csv file for the URBANopt scenario.

    Returns:
        The folder in which the OSW exists and out of which the OpenStudio CLI
        will operate.
    """
    # check the input files
    assert os.path.isfile(feature_file_path), \
        'No feature file found at {}.'.format(feature_file_path)
    assert os.path.isfile(scenario_file_path), \
        'No scenario file found at {}.'.format(scenario_file_path)
    return os.path.split(feature_file_path)[0]


def _output_urbanopt_files(directory):
    """Get the paths to the simulation output files given the urbanopt directory.

    Args:
        directory: The path to where the URBANopt feature and scenario files
            were simulated.

    Returns:
        A series of file paths to the simulation output files

        -   sql -- Array of paths to .sqlite files containing all simulation results.

        -   zsz -- Array of paths to .csv files containing detailed zone load
            information recorded over the course of the design days.

        -   rdd -- Array of paths to .rdd files containing all possible outputs
            that can be requested from the simulation.

        -   html -- Array of paths to .html files containing all summary reports.

        -   err -- Array of paths to .err files containing all errors and warnings from the
            simulation.
    """
    # empty list which will be filled with simulation output files
    sql = []
    zsz = []
    rdd = []
    html = []
    err = []

    # generate paths to the simulation files and check their existance
    sim_dir = os.path.join(directory, 'run', 'baseline_scenario')
    for bldg_name in os.listdir(sim_dir):
        bldg_dir = os.path.join(sim_dir, bldg_name)
        sql_file = os.path.join(bldg_dir, 'eplusout.sql')
        if os.path.isfile(sql_file):
            sql.append(sql_file)
        zsz_file = os.path.join(bldg_dir, 'epluszsz.csv')
        if os.path.isfile(zsz_file):
            zsz.append(zsz_file)
        rdd_file = os.path.join(bldg_dir, 'eplusout.rdd')
        if os.path.isfile(rdd_file):
            rdd.append(rdd_file)
        html_file = os.path.join(bldg_dir, 'eplusout.html')
        if os.path.isfile(html_file):
            html.append(html_file)
        err_file = os.path.join(bldg_dir, 'eplusout.err')
        if os.path.isfile(err_file):
            err.append(err_file)

    return sql, zsz, rdd, html, err
