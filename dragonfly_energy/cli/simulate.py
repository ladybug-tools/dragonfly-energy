"""dragonfly energy simulation running commands."""

try:
    import click
except ImportError:
    raise ImportError(
        'click is not installed. Try `pip install . [cli]` command.'
    )

from dragonfly.model import Model

from ladybug.futil import preparedir

from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.run import to_openstudio_osw, run_osw, run_idf, \
    output_energyplus_files

import sys
import os
import logging
import json

_logger = logging.getLogger(__name__)


@click.group(help='Commands for simulating Dragonfly JSON files in EnergyPlus.')
def simulate():
    pass


@simulate.command('model')
@click.argument('model-json')
@click.argument('epw-file')
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
@click.option('--base-osw', help='Full path to an OSW JSON be used as the base for '
              'the execution of the OpenStuduo CLI. This can be used to add '
              'measures in the workflow.', default=None, show_default=True)
@click.option('--folder', help='Folder on this computer, into which the OSM and IDF '
              'files will be written. If None, the files will be output in the'
              'same location as the model_json.', default=None, show_default=True)
@click.option('--log-file', help='Optional log file to output the progress of the'
              'translation. By default this will be printed out to stdout',
              type=click.File('w'), default='-')
def simulate_model(model_json, epw_file, sim_par_json, obj_per_model, use_multiplier,
                   add_plenum, shade_dist, base_osw, folder, log_file):
    """Simulate a Dragonfly Model JSON file in EnergyPlus.
    \n
    Args:
        model_json: Full path to a Dragonfly Model JSON file.
        epw_file: Full path to an .epw file.
    """
    try:
        # check that the model JSON is there
        assert os.path.isfile(model_json), \
            'No Model JSON file found at {}.'.format(model_json)
        assert os.path.isfile(epw_file), 'No EPW file found at {}.'.format(epw_file)

        # set the default folder if it's not specified
        if folder is None:
            folder = os.path.split(os.path.abspath(model_json))[0]

        # process the simulation parameters
        if sim_par_json is None:  # generate some default simulation parameters
            sim_par = SimulationParameter()
            sim_par.output.add_zone_energy_use()
            epw_folder, epw_file_name = os.path.split(epw_file)
            ddy_file = os.path.join(epw_folder, epw_file_name.replace('.epw', '.ddy'))
            if os.path.isfile(ddy_file):
                sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
            # write out the simulation parameters to a JSON
            sim_par_dict = sim_par.to_dict()
            sim_par_json = os.path.abspath(
                os.path.join(folder, 'simulation_parameter.json'))
            with open(sim_par_json, 'w') as fp:
                json.dump(sim_par_dict, fp)
            log_file.write('Default SimulationParameters were auto-generated.\n')
        else:
            assert os.path.isfile(sim_par_json), \
                'No simulation parameter file found at {}.'.format(sim_par_json)

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
        sqls = []
        for hb_model in hb_models:
            model_dict = hb_model.to_dict(triangulate_sub_faces=True)
            directory = os.path.join(folder, hb_model.identifier)
            file_path = os.path.join(directory, '{}.json'.format(hb_model.identifier))
            preparedir(directory, remove_content=False)  # create the directory
            with open(file_path, 'w') as fp:
                json.dump(model_dict, fp, indent=4)

            # Write the osw file to translate the model to osm
            osw = to_openstudio_osw(directory, file_path, sim_par_json,
                                    base_osw=base_osw, epw_file=epw_file)

            # run the measure to translate the model JSON to an openstudio measure
            if osw is not None and os.path.isfile(osw):
                if base_osw is None:  # separate the OS CLI run from the E+ run
                    osm, idf = run_osw(osw)
                    if idf is not None and os.path.isfile(idf):
                        sql, eio, rdd, html, err = run_idf(idf, epw_file)
                        osms.append(osm)
                        idfs.append(idf)
                        sqls.append(sql)
                        if err is None or not os.path.isfile(err):
                            raise Exception('Running EnergyPlus failed.')
                    else:
                        raise Exception('Running OpenStudio CLI failed.')
                else:  # run the whole simulation with the OpenStudio CLI
                    osm, idf = run_osw(osw, measures_only=False)
                    if idf is None or not os.path.isfile(idf):
                        raise Exception('Running OpenStudio CLI failed.')
                    sql, eio, rdd, html, err = \
                        output_energyplus_files(os.path.dirname(idf))
                    if err is None or not os.path.isfile(err):
                        raise Exception('Running EnergyPlus failed.')
                    osms.append(osm)
                    idfs.append(idf)
                    sqls.append(sql)
            else:
                raise Exception('Writing OSW file failed.')
        log_file.write('The following OSMs were generated:\n{}\n'.format('\n'.join(osms)))
        log_file.write('The following IDFs were generated:\n{}\n'.format('\n'.join(idfs)))
        log_file.write('The following SQLs were generated:\n{}\n'.format('\n'.join(sqls)))
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
