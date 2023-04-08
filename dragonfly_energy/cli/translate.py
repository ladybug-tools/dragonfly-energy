"""dragonfly energy translation commands."""
import click
import sys
import os
import logging
import json
import shutil

from ladybug.futil import preparedir
from honeybee.config import folders as hb_folders
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.run import to_openstudio_osw, to_gbxml_osw, run_osw, \
    add_gbxml_space_boundaries
from honeybee_energy.writer import energyplus_idf_version
from honeybee_energy.config import folders
from dragonfly.model import Model


_logger = logging.getLogger(__name__)


@click.group(help='Commands for translating Dragonfly JSON files to/from OSM/IDF.')
def translate():
    pass


@translate.command('model-to-osm')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--sim-par-json', '-sp', help='Full path to a honeybee energy '
    'SimulationParameter JSON that describes all of the settings for '
    'the simulation. If None default parameters will be generated.',
    default=None, show_default=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--multiplier/--full-geometry', ' /-fg', help='Flag to note if the '
              'multipliers on each Building story will be passed along to the '
              'generated Honeybee Room objects or if full geometry objects should be '
              'written for each story in the building.', default=True, show_default=True)
@click.option('--no-plenum/--plenum', ' /-p', help='Flag to indicate whether '
              'ceiling/floor plenums should be auto-generated for the Rooms.',
              default=True, show_default=True)
@click.option('--no-ceil-adjacency/--ceil-adjacency', ' /-a', help='Flag to indicate '
              'whether adjacencies should be solved between interior stories when '
              'Room2Ds perfectly match one another in their floor plate. This ensures '
              'that Surface boundary conditions are used instead of Adiabatic ones. '
              'Note that this input has no effect when the object-per-model is Story.',
              default=True, show_default=True)
@click.option('--folder', '-f', help='Folder on this computer, into which the '
              'working files, OSM and IDF files will be written. If None, the '
              'files will be output in the same location as the model_json.',
              default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--osm-file', '-osm', help='Optional file where the OSM will be copied '
              'after it is translated in the folder. If None, the file will not '
              'be copied.', type=str, default=None, show_default=True)
@click.option('--idf-file', '-idf', help='Optional file where the IDF will be copied '
              'after it is translated in the folder. If None, the file will not '
              'be copied.', type=str, default=None, show_default=True)
@click.option('--log-file', '-log', help='Optional log file to output the paths to the '
              'generated OSM and IDF files if they were successfully created. '
              'By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def model_to_osm(model_json, sim_par_json, multiplier, no_plenum, no_ceil_adjacency,
                 folder, osm_file, idf_file, log_file):
    """Translate a Model DFJSON to an OpenStudio Model.

    \b
    Args:
        model_json: Full path to a Dragonfly Model JSON file.
    """
    try:
        # set the default folder to the default if it's not specified
        if folder is None:
            folder = os.path.dirname(os.path.abspath(model_json))
        preparedir(folder, remove_content=False)

        # generate default simulation parameters
        if sim_par_json is None:
            sim_par = SimulationParameter()
            sim_par.output.add_zone_energy_use()
            sim_par.output.add_hvac_energy_use()
            sim_par_dict = sim_par.to_dict()
            sp_json = os.path.abspath(os.path.join(folder, 'simulation_parameter.json'))
            with open(sp_json, 'w') as fp:
                json.dump(sim_par_dict, fp)

        # re-serialize the Dragonfly Model
        model = Model.from_dfjson(model_json)
        model.convert_to_units('Meters')

        # convert Dragonfly Model to Honeybee
        add_plenum = not no_plenum
        ceil_adjacency = not no_ceil_adjacency
        hb_models = model.to_honeybee(
            object_per_model='District', use_multiplier=multiplier,
            add_plenum=add_plenum, solve_ceiling_adjacencies=ceil_adjacency)
        hb_model = hb_models[0]

        # create the dictionary of the HBJSON for input to OpenStudio CLI
        for room in hb_model.rooms:
            room.remove_colinear_vertices_envelope(0.01, delete_degenerate=True)
        model_dict = hb_model.to_dict(triangulate_sub_faces=True)
        hb_model.properties.energy.add_autocal_properties_to_dict(model_dict)
        hb_model_json = os.path.abspath(os.path.join(folder, 'in.hbjson'))
        with open(hb_model_json, 'w') as fp:
            json.dump(model_dict, fp)

        # Write the osw file to translate the model to osm
        osw = to_openstudio_osw(folder, hb_model_json, sim_par_json)

        # run the measure to translate the model JSON to an openstudio measure
        osm, idf = run_osw(osw)
        # copy the resulting files to the specified locations
        if idf is not None and os.path.isfile(idf):
            if osm_file is not None:
                if not osm_file.lower().endswith('.osm'):
                    osm_file = osm_file + '.osm'
                shutil.copyfile(osm, osm_file)
            if idf_file is not None:
                if not idf_file.lower().endswith('.idf'):
                    idf_file = idf_file + '.idf'
                shutil.copyfile(idf, idf_file)
            log_file.write(json.dumps([osm, idf]))
        else:
            raise Exception('Running OpenStudio CLI failed.')
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@translate.command('model-to-idf')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--sim-par-json', '-sp', help='Full path to a honeybee energy '
    'SimulationParameter JSON that describes all of the settings for the '
    'simulation. If None default parameters will be generated.',
    default=None, show_default=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--multiplier/--full-geometry', ' /-fg', help='Flag to note if the '
              'multipliers on each Building story will be passed along to the '
              'generated Honeybee Room objects or if full geometry objects should be '
              'written for each story in the building.', default=True, show_default=True)
@click.option('--no-plenum/--plenum', ' /-p', help='Flag to indicate whether '
              'ceiling/floor plenums should be auto-generated for the Rooms.',
              default=True, show_default=True)
@click.option('--no-ceil-adjacency/--ceil-adjacency', ' /-a', help='Flag to indicate '
              'whether adjacencies should be solved between interior stories when '
              'Room2Ds perfectly match one another in their floor plate. This ensures '
              'that Surface boundary conditions are used instead of Adiabatic ones. '
              'Note that this input has no effect when the object-per-model is Story.',
              default=True, show_default=True)
@click.option('--additional-str', '-a', help='Text string for additional lines that '
              'should be added to the IDF.', type=str, default='', show_default=True)
@click.option('--compact-schedules/--csv-schedules', ' /-c', help='Flag to note '
              'whether any ScheduleFixedIntervals in the model should be included '
              'in the IDF string as a Schedule:Compact or they should be written as '
              'CSV Schedule:File and placed in a directory next to the output-file.',
              default=True, show_default=True)
@click.option('--hvac-to-ideal-air/--hvac-check', ' /-h', help='Flag to note '
              'whether any detailed HVAC system templates should be converted to '
              'an equivalent IdealAirSystem upon export. If hvac-check is used'
              'and the Model contains detailed systems, a ValueError will '
              'be raised.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional IDF file to output the IDF string '
              'of the translation. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def model_to_idf(model_json, sim_par_json, multiplier, no_plenum, no_ceil_adjacency,
                 additional_str, compact_schedules, hvac_to_ideal_air, output_file):
    """Translate a Model JSON file to an IDF using direct-to-idf translators.

    The resulting IDF should be simulate-able but not all Model properties might
    make it into the IDF given that the direct-to-idf translators are used.

    \b
    Args:
        model_json: Full path to a Dragonfly Model JSON file.
    """
    try:
        # check that the simulation parameters are there and load them
        if sim_par_json is not None:
            with open(sim_par_json) as json_file:
                data = json.load(json_file)
            sim_par = SimulationParameter.from_dict(data)
        else:
            sim_par = SimulationParameter()
            sim_par.output.add_zone_energy_use()
            sim_par.output.add_hvac_energy_use()

        # re-serialize the Dragonfly Model
        model = Model.from_dfjson(model_json)
        model.convert_to_units('Meters')

        # convert Dragonfly Model to Honeybee
        add_plenum = not no_plenum
        ceil_adjacency = not no_ceil_adjacency
        hb_models = model.to_honeybee(
            object_per_model='District', use_multiplier=multiplier,
            add_plenum=add_plenum, solve_ceiling_adjacencies=ceil_adjacency)
        hb_model = hb_models[0]

        # set the schedule directory in case it is needed
        sch_directory = None
        if not compact_schedules:
            sch_path = os.path.abspath(model_json) if 'stdout' in str(output_file) \
                else os.path.abspath(str(output_file))
            sch_directory = os.path.join(os.path.split(sch_path)[0], 'schedules')

        # create the strings for simulation parameters and model
        ver_str = energyplus_idf_version() if folders.energyplus_version \
            is not None else ''
        sim_par_str = sim_par.to_idf()
        model_str = hb_model.to.idf(
            hb_model, schedule_directory=sch_directory,
            use_ideal_air_equivalent=hvac_to_ideal_air)
        idf_str = '\n\n'.join([ver_str, sim_par_str, model_str, additional_str])

        # write out the IDF file
        output_file.write(idf_str)
    except Exception as e:
        _logger.exception('Model translation failed.\n{}\n'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@translate.command('model-to-gbxml')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--multiplier/--full-geometry', ' /-fg', help='Flag to note if the '
              'multipliers on each Building story will be passed along to the '
              'generated Honeybee Room objects or if full geometry objects should be '
              'written for each story in the building.', default=True, show_default=True)
@click.option('--no-plenum/--plenum', ' /-p', help='Flag to indicate whether '
              'ceiling/floor plenums should be auto-generated for the Rooms.',
              default=True, show_default=True)
@click.option('--no-ceil-adjacency/--ceil-adjacency', ' /-a', help='Flag to indicate '
              'whether adjacencies should be solved between interior stories when '
              'Room2Ds perfectly match one another in their floor plate. This ensures '
              'that Surface boundary conditions are used instead of Adiabatic ones. '
              'Note that this input has no effect when the object-per-model is Story.',
              default=True, show_default=True)
@click.option('--osw-folder', '-osw', help='Folder on this computer, into which the '
              'working files will be written. If None, it will be written into the a '
              'temp folder in the default simulation folder.', default=None,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--minimal/--full-geometry', ' /-fg', help='Flag to note whether space '
              'boundaries and shell geometry should be included in the exported '
              'gbXML vs. just the minimal required non-manifold geometry.',
              default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional gbXML file to output the string '
              'of the translation. By default it printed out to stdout', default='-',
              type=click.Path(file_okay=True, dir_okay=False, resolve_path=True))
def model_to_gbxml(model_json, multiplier, no_plenum, no_ceil_adjacency,
                   osw_folder, minimal, output_file):
    """Translate a Model DFJSON to a gbXML file.

    \b
    Args:
        model_json: Full path to a Dragonfly Model JSON file.
    """
    try:
        # set the default folder if it's not specified
        out_path = None
        out_directory = os.path.join(
            hb_folders.default_simulation_folder, 'temp_translate')
        if output_file.endswith('-'):
            f_name = os.path.basename(model_json).lower()
            f_name = f_name.replace('.dfjson', '.xml').replace('.json', '.xml')
            out_path = os.path.join(out_directory, f_name)
        preparedir(out_directory)

        # re-serialize the Dragonfly Model
        model = Model.from_dfjson(model_json)
        model.convert_to_units('Meters')

        # convert Dragonfly Model to Honeybee
        add_plenum = not no_plenum
        ceil_adjacency = not no_ceil_adjacency
        hb_models = model.to_honeybee(
            object_per_model='District', use_multiplier=multiplier,
            add_plenum=add_plenum, solve_ceiling_adjacencies=ceil_adjacency)
        hb_model = hb_models[0]

        # create the dictionary of the HBJSON for input to OpenStudio CLI
        for room in hb_model.rooms:
            room.remove_colinear_vertices_envelope(0.01, delete_degenerate=True)
        model_dict = hb_model.to_dict(triangulate_sub_faces=True)
        hb_model.properties.energy.add_autocal_properties_to_dict(model_dict)
        hb_model_json = os.path.abspath(os.path.join(out_directory, 'in.hbjson'))
        with open(hb_model_json, 'w') as fp:
            json.dump(model_dict, fp)

        # Write the osw file and translate the model to gbXML
        out_f = out_path if output_file.endswith('-') else output_file
        osw = to_gbxml_osw(hb_model_json, out_f, osw_folder)
        if minimal:
            _run_translation_osw(osw, out_path)
        else:
            _, idf = run_osw(osw, silent=True)
            if idf is not None and os.path.isfile(idf):
                hb_model = Model.from_hbjson(hb_model_json)
                add_gbxml_space_boundaries(out_f, hb_model)
                if out_path is not None:  # load the JSON string to stdout
                    with open(out_path) as json_file:
                        print(json_file.read())
            else:
                raise Exception('Running OpenStudio CLI failed.')
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def _run_translation_osw(osw, out_path):
    """Generic function used by all import methods that run OpenStudio CLI."""
    # run the measure to translate the model JSON to an openstudio measure
    _, idf = run_osw(osw, silent=True)
    if idf is not None and os.path.isfile(idf):
        if out_path is not None:  # load the JSON string to stdout
            with open(out_path) as json_file:
                print(json_file.read())
    else:
        raise Exception('Running OpenStudio CLI failed.')
