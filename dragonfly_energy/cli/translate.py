"""dragonfly energy translation commands."""
import click
import sys
import os
import logging
import json

from ladybug.futil import preparedir
from honeybee.config import folders as hb_folders
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.run import to_openstudio_osw, run_osw
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
@click.option('--sim-par-json', '-sp', help='Full path to a honeybee energy '
              'SimulationParameter JSON that describes all of the settings for '
              'the simulation. If None default parameters will be generated.',
              default=None, show_default=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--obj-per-model', '-o', help='Text to describe how the input Model '
              'should be divided across the output Models. Choose from: District, '
              'Building, Story.', type=str, default="Building", show_default=True)
@click.option('--multiplier/--full-geometry', ' /-fg', help='Flag to note if the '
              'multipliers on each Building story will be passed along to the '
              'generated Honeybee Room objects or if full geometry objects should be '
              'written for each story in the building.', default=True, show_default=True)
@click.option('--no-plenum/--plenum', ' /-p', help='Flag to indicate whether '
              'ceiling/floor plenums should be auto-generated for the Rooms.',
              default=True, show_default=True)
@click.option('--no-cap/--cap', ' /-c', help='Flag to indicate whether context shade '
              'buildings should be capped with a top face.',
              default=True, show_default=True)
@click.option('--shade-dist', '-sd', help='An optional number to note the distance beyond'
              ' which other buildings shade should not be exported into a given Model. '
              'If None, all other buildings will be included as context shade in '
              'each and every Model. Set to 0 to exclude all neighboring buildings '
              'from the resulting models.', type=float, default=None, show_default=True)
@click.option('--folder', '-f', help='Folder on this computer, into which the IDF '
              'and result files will be written. If None, the files will be output '
              'to the honeybee default simulation folder and placed in a project '
              'folder with the same name as the model json.',
              default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output a dictionary '
              'with the paths of the generated files under the following keys: '
              'osm, idf. By default the list will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def model_to_osm(model_json, sim_par_json, obj_per_model, multiplier, no_plenum, no_cap,
                 shade_dist, folder, log_file):
    """Translate a Model JSON file into an OpenStudio Model.

    \b
    Args:
        model_json: Full path to a Dragonfly Model JSON file.
    """
    try:
        # set the default folder to the default if it's not specified
        if folder is None:
            proj_name = \
                os.path.basename(model_json).replace('.json', '').replace('.dfjson', '')
            folder = os.path.join(
                hb_folders.default_simulation_folder, proj_name, 'OpenStudio')
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
        with open(model_json) as json_file:
            data = json.load(json_file)
        model = Model.from_dict(data)
        model.convert_to_units('Meters')

        # convert Dragonfly Model to Honeybee
        add_plenum = not no_plenum
        cap = not no_cap
        hb_models = model.to_honeybee(
            obj_per_model, shade_dist, multiplier, add_plenum, cap)

        # write out the honeybee JSONs
        osms = []
        idfs = []
        for hb_model in hb_models:
            model_dict = hb_model.to_dict(triangulate_sub_faces=True)
            directory = os.path.join(folder, hb_model.identifier)
            file_path = os.path.join(directory, '{}.json'.format(hb_model.identifier))
            preparedir(directory, remove_content=False)  # create the directory
            with open(file_path, 'w') as fp:
                json.dump(model_dict, fp, indent=4)

            # Write the osw file to translate the model to osm
            osw = to_openstudio_osw(directory, file_path, sim_par_json)

            # run the measure to translate the model JSON to an openstudio measure
            if os.path.isfile(osw):
                osm, idf = run_osw(osw)
                if osm is not None and os.path.isfile(osm):
                    osms.append(osm)
                    idfs.append(idf)
                else:
                    raise Exception('Running OpenStudio CLI failed.')
            else:
                raise Exception('Writing OSW file failed.')
        log_file.write(json.dumps({'osm': osms, 'idf': idfs}))
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@translate.command('model-to-idf')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--sim-par-json', '-sp', help='Full path to a honeybee energy '
              'SimulationParameter JSON that describes all of the settings for the '
              'simulation. If None default parameters will be generated.',
              default=None, show_default=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--obj-per-model', '-o', help='Text to describe how the input Model '
              'should be divided across the output Models. Choose from: District, '
              'Building, Story.', type=str, default="Building", show_default=True)
@click.option('--multiplier/--full-geometry', ' /-fg', help='Flag to note if the '
              'multipliers on each Building story will be passed along to the '
              'generated Honeybee Room objects or if full geometry objects should be '
              'written for each story in the building.', default=True, show_default=True)
@click.option('--no-plenum/--plenum', ' /-p', help='Flag to indicate whether '
              'ceiling/floor plenums should be auto-generated for the Rooms.',
              default=True, show_default=True)
@click.option('--no-cap/--cap', ' /-c', help='Flag to indicate whether context shade '
              'buildings should be capped with a top face.',
              default=True, show_default=True)
@click.option('--shade-dist', '-sd', help='An optional number to note the distance beyond'
              ' which other buildings shade should not be exported into a given Model. '
              'If None, all other buildings will be included as context shade in '
              'each and every Model. Set to 0 to exclude all neighboring buildings '
              'from the resulting models.', type=float, default=None, show_default=True)
@click.option('--folder', '-f', help='Folder on this computer, into which the IDF '
              'and result files will be written. If None, the files will be output '
              'to the honeybee default simulation folder and placed in a project '
              'folder with the same name as the model json.',
              default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output the list of IDFs '
              'paths. By default the list will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def model_to_idf(model_json, sim_par_json, obj_per_model, multiplier, no_plenum, no_cap,
                 shade_dist, folder, log_file):
    """Translate a Model JSON file to an IDF using direct-to-idf translators.

    The resulting IDF should be simulate-able but not all Model properties might
    make it into the IDF given that the direct-to-idf translators are used.

    \b
    Args:
        model_json: Full path to a Dragonfly Model JSON file.
    """
    try:
        # set the default folder to the default if it's not specified
        if folder is None:
            proj_name = \
                os.path.basename(model_json).replace('.json', '').replace('.dfjson', '')
            folder = os.path.join(
                hb_folders.default_simulation_folder, proj_name, 'EnergyPlus')
        preparedir(folder, remove_content=False)

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
        with open(model_json) as json_file:
            data = json.load(json_file)
        df_model = Model.from_dict(data)
        df_model.convert_to_units('Meters')

        # convert Dragonfly Model to Honeybee
        add_plenum = not no_plenum
        cap = not no_cap
        hb_models = df_model.to_honeybee(
            obj_per_model, shade_dist, multiplier, add_plenum, cap)

        # set the schedule directory in case it is needed
        sch_path = os.path.abspath(model_json) if 'stdout' in str(log_file) \
            else os.path.abspath(str(log_file))
        sch_directory = os.path.join(os.path.split(sch_path)[0], 'schedules')

        # write out the honeybee JSONs
        idfs = []
        for hb_model in hb_models:
            # create the strings for simulation paramters and model
            ver_str = energyplus_idf_version() if folders.energyplus_version \
                is not None else ''
            sim_par_str = sim_par.to_idf()
            model_str = hb_model.to.idf(hb_model, schedule_directory=sch_directory)
            idf_str = '\n\n'.join([ver_str, sim_par_str, model_str])

            # write out the IDF files
            idf_path = os.path.join(folder, '{}.idf'.format(hb_model.identifier))
            with open(idf_path, 'w') as idf_file:
                idf_file.write(idf_str)
            idfs.append(idf_path)
        log_file.write('\n'.join(idfs))
    except Exception as e:
        _logger.exception('Model translation failed.\n{}\n'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
