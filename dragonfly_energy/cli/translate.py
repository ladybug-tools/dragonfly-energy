"""dragonfly energy translation commands."""

try:
    import click
except ImportError:
    raise ImportError(
        'click is not installed. Try `pip install . [cli]` command.'
    )

from dragonfly.model import Model

from ladybug.futil import preparedir

from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.run import to_openstudio_osw, run_osw
from honeybee_energy.writer import energyplus_idf_version
from honeybee_energy.config import folders

import sys
import os
import logging
import json

_logger = logging.getLogger(__name__)


@click.group(help='Commands for translating Dragonfly JSON files to/from OSM/IDF.')
def translate():
    pass


@translate.command('model-to-osm')
@click.argument('model-json')
@click.option('--sim-par-json', help='Full path to a honeybee energy SimulationParameter'
              ' JSON that describes all of the settings for the simulation.',
              default=None)
@click.option('--obj-per-model', help='Text to describe how the input Model should '
              'be divided across the output Models. Choose from: "Building" "District".',
              default="Building", show_default=True)
@click.option('--use-multiplier', help='Boolean to note if the multipliers on each '
              'Building story will be passed along to the generated Honeybee Room '
              'objects. If False, full geometry objects will be written for each '
              'story in the building.', default=True, show_default=True)
@click.option('--add-plenum', help='Boolean to indicate whether ceiling/floor plenums '
              'should be auto-generated for the Rooms.', default=False, show_default=True)
@click.option('--shade-dist', help='An optional number to note the distance beyond '
              'which other buildings shade should not be exported into a given Model. '
              'If None, all other buildings will be included as context shade in '
              'each and every Model. Set to 0 to exclude all neighboring buildings '
              'from the resulting models.', default=None, show_default=True)
@click.option('--folder', help='Folder on this computer, into which the OSM and IDF '
              'files will be written. If None, the files will be output in the'
              'same location as the model_json.', default=None, show_default=True)
@click.option('--log-file', help='Optional log file to output the progress of the'
              'translation. By default this will be printed out to stdout',
              type=click.File('w'), default='-')
def model_to_osm(model_json, sim_par_json, obj_per_model, use_multiplier, add_plenum,
                 shade_dist, folder, log_file):
    """Translate a Model JSON file into an OpenStudio Model.
    \n
    Args:
        model_json: Full path to a Dragonfly Model JSON file.
    """
    try:
        # check that the model JSON is there
        assert os.path.isfile(model_json), \
            'No Model JSON file found at {}.'.format(model_json)

        # set the default folder if it's not specified
        if folder is None:
            folder = os.path.split(os.path.abspath(model_json))[0]

        # check that the simulation parameters are there
        if sim_par_json is not None:
            assert os.path.isfile(sim_par_json), \
                'No simulation parameter file found at {}.'.format(sim_par_json)
        else:
            log_file.write('Creating default simulation parameters.\n')
            sim_par = SimulationParameter()
            sim_par.output.add_zone_energy_use()
            sim_par_json = os.path.join(folder, 'simulation_parameter.json')
            with open(sim_par_json, 'w') as fp:
                json.dump(sim_par.to_dict(), fp)

        # re-serialize the Dragonfly Model
        log_file.write('Re-serailizing Dragonfly model JSON.\n')
        with open(model_json) as json_file:
            data = json.load(json_file)
        model = Model.from_dict(data)
        model.convert_to_units('Meters')

        # convert Dragonfly Model to Honeybee
        log_file.write('Converting Dragonfly Models to Honeybee.\n')
        hb_models = model.to_honeybee(
            obj_per_model, shade_dist, use_multiplier, add_plenum)

        # write out the honeybee JSONs
        log_file.write('Writing Honeybee Models to JSON.\n')
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
        log_file.write('The following OSMs were generated:\n{}\n'.format('\n'.join(osms)))
        log_file.write('The following IDFs were generated:\n{}\n'.format('\n'.join(idfs)))
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@translate.command('model-to-idf')
@click.argument('model-json')
@click.option('--sim-par-json', help='Full path to a honeybee energy SimulationParameter'
              ' JSON that describes all of the settings for the simulation.',
              default=None)
@click.option('--obj-per-model', help='Text to describe how the input Model should '
              'be divided across the output Models. Choose from: "Building" "District".',
              default="Building", show_default=True)
@click.option('--use-multiplier', help='Boolean to note if the multipliers on each '
              'Building story will be passed along to the generated Honeybee Room '
              'objects. If False, full geometry objects will be written for each '
              'story in the building.', default=True, show_default=True)
@click.option('--add-plenum', help='Boolean to indicate whether ceiling/floor plenums '
              'should be auto-generated for the Rooms.', default=False, show_default=True)
@click.option('--shade-dist', help='An optional number to note the distance beyond '
              'which other buildings shade should not be exported into a given Model. '
              'If None, all other buildings will be included as context shade in '
              'each and every Model. Set to 0 to exclude all neighboring buildings '
              'from the resulting models.', default=None, show_default=True)
@click.option('--folder', help='Folder on this computer, into which the OSM and IDF '
              'files will be written. If None, the files will be output in the'
              'same location as the model_json.', default=None, show_default=True)
@click.option('--log-file', help='Optional log file to output the list of IDF files '
              'generated. By default this will be printed out to stdout',
              type=click.File('w'), default='-')
def model_to_idf(model_json, sim_par_json, obj_per_model, use_multiplier, add_plenum,
                 shade_dist, folder, log_file):
    """Translate a Model JSON file to an IDF using direct-to-idf translators.
    \n
    The resulting IDF should be simulate-able but not all Model properties might
    make it into the IDF given that the direct-to-idf translators are used.
    \n
    Args:
        model_json: Full path to a Model JSON file.
    """
    try:
        # check that the model JSON is there
        assert os.path.isfile(model_json), \
            'No Model JSON file found at {}.'.format(model_json)

        # set the default folder if it's not specified
        if folder is None:
            folder = os.path.split(os.path.abspath(model_json))[0]

        # check that the simulation parameters are there and load them
        if sim_par_json is not None:
            assert os.path.isfile(sim_par_json), \
                'No simulation parameter file found at {}.'.format(sim_par_json)
            with open(sim_par_json) as json_file:
                data = json.load(json_file)
            sim_par = SimulationParameter.from_dict(data)
        else:
            sim_par = SimulationParameter()
            sim_par.output.add_zone_energy_use()

        # re-serialize the Dragonfly Model
        with open(model_json) as json_file:
            data = json.load(json_file)
        df_model = Model.from_dict(data)
        df_model.convert_to_units('Meters')

        # convert Dragonfly Model to Honeybee
        hb_models = df_model.to_honeybee(
            obj_per_model, shade_dist, use_multiplier, add_plenum)

        # set the schedule directory in case it is needed
        sch_path = os.path.abspath(model_json) if 'stdout' in str(log_file) \
            else os.path.abspath(str(log_file))
        sch_directory = os.path.join(os.path.split(sch_path)[0], 'schedules')

        # write out the honeybee JSONs
        idfs = []
        for hb_model in hb_models:
            # create the strings for simulation paramters and model
            ver_str = energyplus_idf_version() if folders.energyplus_version \
                is not None else energyplus_idf_version((9, 2, 0))
            sim_par_str = sim_par.to_idf()
            model_str = hb_model.to.idf(hb_model, schedule_directory=sch_directory)
            idf_str = '\n\n'.join([ver_str, sim_par_str, model_str])

            # write out the IDF file
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
