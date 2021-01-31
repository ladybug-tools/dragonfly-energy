"""dragonfly energy simulation running commands."""
import click
import sys
import os
import logging
import json

from dragonfly.model import Model
from honeybee.config import folders
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.run import to_openstudio_osw, run_osw, run_idf, \
    output_energyplus_files
from ladybug.futil import preparedir
from ladybug.epw import EPW


_logger = logging.getLogger(__name__)


@click.group(help='Commands for simulating Dragonfly JSON files in EnergyPlus.')
def simulate():
    pass


@simulate.command('model')
@click.argument('model-json', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('epw-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--sim-par-json', '-sp', help='Full path to a honeybee energy '
              'SimulationParameter JSON that describes all of the settings for '
              'the simulation.',default=None, show_default=True,
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
@click.option('--base-osw', '-osw', help='Full path to an OSW JSON be used as the '
              'base for the execution of the OpenStuduo CLI. This can be used to add '
              'measures in the workflow.', default=None, show_default=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--folder', '-f', help='Folder on this computer, into which the IDF '
              'and result files will be written. If None, the files will be output '
              'to the honeybee default simulation folder and placed in a project '
              'folder with the same name as the model json.',
              default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output a dictionary '
              'with the paths of the generated files under the following keys: '
              'osm, idf, sql. By default the list will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def simulate_model(model_json, epw_file, sim_par_json, obj_per_model, multiplier,
                   no_plenum, no_cap, shade_dist, base_osw, folder, log_file):
    """Simulate a Dragonfly Model JSON file in EnergyPlus.

    \b
    Args:
        model_json: Full path to a Dragonfly Model JSON file.
        epw_file: Full path to an .epw file.
    """
    try:
        # get a ddy variable that might get used later
        epw_folder, epw_file_name = os.path.split(epw_file)
        ddy_file = os.path.join(epw_folder, epw_file_name.replace('.epw', '.ddy'))

        # set the default folder to the default if it's not specified
        if folder is None:
            proj_name = \
                os.path.basename(model_json).replace('.json', '').replace('.dfjson', '')
            folder = os.path.join(
                folders.default_simulation_folder, proj_name, 'OpenStudio')
        preparedir(folder, remove_content=False)

        # process the simulation parameters and write new ones if necessary
        def ddy_from_epw(epw_file, sim_par):
            """Produce a DDY from an EPW file."""
            epw_obj = EPW(epw_file)
            des_days = [epw_obj.approximate_design_day('WinterDesignDay'),
                        epw_obj.approximate_design_day('SummerDesignDay')]
            sim_par.sizing_parameter.design_days = des_days

        def write_sim_par(sim_par):
            """Write simulation parameter object to a JSON."""
            sim_par_dict = sim_par.to_dict()
            sp_json = os.path.abspath(os.path.join(folder, 'simulation_parameter.json'))
            with open(sp_json, 'w') as fp:
                json.dump(sim_par_dict, fp)
            return sp_json

        if sim_par_json is None:  # generate some default simulation parameters
            sim_par = SimulationParameter()
            sim_par.output.add_zone_energy_use()
            sim_par.output.add_hvac_energy_use()
        else:
            with open(sim_par_json) as json_file:
                data = json.load(json_file)
            sim_par = SimulationParameter.from_dict(data)
        if len(sim_par.sizing_parameter.design_days) == 0 and os.path.isfile(ddy_file):
            try:
                sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
            except AssertionError:  # no design days within the DDY file
                ddy_from_epw(epw_file, sim_par)
        elif len(sim_par.sizing_parameter.design_days) == 0:
            ddy_from_epw(epw_file, sim_par)
        sim_par_json = write_sim_par(sim_par)

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
        log_file.write(json.dumps({'osm': osms, 'idf': idfs, 'sql': sqls}))
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
