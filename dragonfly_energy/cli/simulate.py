"""dragonfly energy simulation running commands."""
import click
import sys
import os
import logging
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed

from ladybug.epw import EPW
from ladybug.stat import STAT
from ladybug.futil import preparedir
from ladybug.commandutil import process_content_to_output
from honeybee.config import folders
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.cli.simulate import simulate_model as simulate_model_hb
from dragonfly.model import Model
from dragonfly_energy.run import run_urbanopt, _recommended_processor_count


_logger = logging.getLogger(__name__)


@click.group(help='Commands for simulating Dragonfly JSON files in EnergyPlus.')
def simulate():
    pass


@simulate.command('model')
@click.argument(
    'model-file',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True)
)
@click.argument(
    'epw-file',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True)
)
@click.option(
    '--sim-par-json', '-sp', help='Full path to a honeybee energy '
    'SimulationParameter JSON that describes all of the settings for '
    'the simulation.', default=None, show_default=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True)
)
@click.option(
    '--obj-per-model', '-o', help='Text to describe how the input Model '
    'should be divided across the output Models. Choose from: District, '
    'Building, Story.', type=str, default='Building', show_default=True
)
@click.option(
    '--shade-dist', '-sd', help='An optional number to note the distance '
    'beyond which other buildings shade should not be exported into a given '
    'Model. If None, all other buildings will be included as context shade in '
    'each and every Model. Set to 0 to exclude all neighboring buildings '
    'from the resulting models.', type=float, default=None, show_default=True
)
@click.option(
    '--multiplier/--full-geometry', ' /-fg', help='Flag to note if the '
    'multipliers on each Building story will be passed along to the '
    'generated Honeybee Room objects or if full geometry objects should be '
    'written for each story in the building.', default=True, show_default=True
)
@click.option(
    '--plenum/--no-plenum', '-p/-np', help='Flag to indicate whether '
    'ceiling/floor plenum depths assigned to Room2Ds should generate '
    'distinct 3D Rooms in the translation.', default=True, show_default=True
)
@click.option(
    '--ceil-adjacency/--no-ceil-adjacency', '-a/-na', help='Flag to indicate '
    'whether adjacencies should be solved between stories. This ensures '
    'that Surface boundary conditions are used instead of Adiabatic ones. '
    'Note that this input has no effect when the object-per-model is Story.',
    default=True, show_default=True
)
@click.option(
    '--merge-method', '-m', help='Text to describe how the Room2Ds should '
    'be merged into individual Rooms during the translation. Specifying a '
    'value here can be an effective way to reduce the number of Room '
    'volumes in the resulting Model and, ultimately, yield a faster simulation '
    'time with less results to manage. Choose from: None, Zones, PlenumZones, '
    'Stories, PlenumStories.', type=str, default='None', show_default=True
)
@click.option(
    '--measures', '-ms', help='Full path to a folder containing an OSW JSON '
    'be used as the base for the execution of the OpenStudio CLI. While this '
    'OSW can contain paths to measures that exist anywhere on the machine, '
    'the best practice is to copy the measures into this measures '
    'folder and use relative paths within the OSW. '
    'This makes it easier to move the inputs for this command from one '
    'machine to another.', default=None, show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True)
)
@click.option(
    '--additional-idf', '-ai', help='An IDF file with text to be appended to '
    'all EnergyPlus models generated from the Dragonfly Model before '
    'simulation. This input can be used to include EnergyPlus objects that are not '
    'natively supported.', default=None, show_default=True,
    type=click.Path(exists=False, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--report-units', '-r', help='A text value to set the units of the '
    'OpenStudio Results report that this command can output. Choose from the '
    'following:\nnone - no results report will be produced\nsi - all units '
    'will be in SI\nip - all units will be in IP.',
    type=str, default='none', show_default=True)
@click.option(
    '--viz-variable', '-v', help='Text for an EnergyPlus output variable to '
    'be visualized on the geometry in an output view_data HTML report. '
    'If unspecified, no view_data report is produced. Multiple variables '
    'can be requested by using multiple -v options. For example\n'
    ' -v "Zone Air System Sensible Heating Rate" -v "Zone Air System '
    'Sensible Cooling Rate"',
    type=str, default=None, show_default=True, multiple=True)
@click.option(
    '--cpu-count', '-c', help='Optional integer to specify the number of'
    'processors to be used in simulating each model derived from the input model.'
    'If unspecified, this will be one less than the total number of processors '
    'available on the machine.', type=int, default=None, show_default=True)
@click.option(
    '--folder', '-f', help='Folder on this computer, into which the IDF '
    'and result files will be written. If unspecified, the files will be output '
    'to the honeybee default simulation folder and placed in a project '
    'folder with the same name as the input model.',
    default=None, show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True)
)
def simulate_model_cli(
    model_file, epw_file, sim_par_json, obj_per_model, shade_dist,
    multiplier, plenum, ceil_adjacency, merge_method, measures, additional_idf,
    report_units, viz_variable, cpu_count, folder
):
    """Simulate a Dragonfly Model JSON file in EnergyPlus.

    \b
    Args:
        model_file: Full path to a Dragonfly Model JSON file. This can also be a
            GeoJSON following the Dragonfly GeoJSON schema.
        epw_file: Full path to an .epw file.
    """
    try:
        full_geometry = not multiplier
        no_plenum = not plenum
        no_ceil_adjacency = not ceil_adjacency
        simulate_model(
            model_file, epw_file, sim_par_json, obj_per_model, shade_dist,
            full_geometry, no_plenum, no_ceil_adjacency, merge_method,
            measures, additional_idf, report_units, viz_variable, cpu_count, folder
        )
    except Exception as e:
        _logger.exception('Model simulation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def simulate_model(
    model_file, epw_file, sim_par_json=None, obj_per_model='Building', shade_dist=None,
    full_geometry=False, no_plenum=False, no_ceil_adjacency=False, merge_method='None',
    measures=None, additional_idf=None, report_units=None, viz_variable=None,
    cpu_count=None, folder=None, multiplier=True, plenum=True, ceil_adjacency=True
):
    """Simulate a Dragonfly Model JSON file in EnergyPlus.

    Args:
        model_file: Full path to a Dragonfly Model JSON file. This can also be a
            GeoJSON following the Dragonfly GeoJSON schema.
        epw_file: Full path to an .epw file.
        sim_par_json: Full path to a honeybee energy SimulationParameter JSON that
            describes all of the settings for the simulation. If None, default
            parameters will be generated.
        obj_per_model: Text to describe how the input Buildings should be
            divided across the output Models. (Default: 'Building'). Choose from
            the following options:

            * District - All buildings will be added to a single Honeybee Model.
                Such a Model can take a long time to simulate so this is only
                recommended for small numbers of buildings or cases where
                exchange of data between Buildings is necessary.
            * Building - Each building will be exported into its own Model.
                For each Model, the other buildings input to this component will
                appear as context shade geometry.
            * Story - Each Story of each Building will be exported into its
                own Model. For each Honeybee Model, the other input Buildings
                will appear as context shade geometry as will all of the other
                stories of the same building.

        shade_dist: An optional number to note the distance beyond which other
            buildings shade should not be exported into a Model. This can include
            the units of the distance (eg. 100ft) or, if no units are provided,
            the value will be interpreted in the dragonfly model units. If None,
            all other buildings will be included as context shade in each and
            every Model. Set to 0 to exclude all neighboring buildings from the
            resulting models. (Default: None).
        full_geometry: Boolean to note if the multipliers on each Building story
            will be passed along to the generated Honeybee Room objects or if
            full geometry objects should be written for each story in the
            building. (Default: False).
        no_plenum: Boolean to indicate whether ceiling/floor plenum depths
            assigned to Room2Ds should generate distinct 3D Rooms in the
            translation. (Default: False).
        no_ceil_adjacency: Boolean to indicate whether adjacencies should be solved
            between interior stories. This ensures that Surface boundary conditions
            are used instead of Adiabatic ones. Note that this input has no
            effect when the object-per-model is Story. (Default: False).
        merge_method: An optional text string to describe how the Room2Ds should
            be merged into individual Rooms during the translation. Specifying a
            value here can be an effective way to reduce the number of Room
            volumes in the resulting Model and, ultimately, yield a faster simulation
            time with less results to manage. Note that Room2Ds will only be merged if
            they form a contiguous volume. Otherwise, there will be multiple Rooms per
            zone or story, each with an integer added at the end of their
            identifiers. Choose from the following options:

            * None - No merging will occur
            * Zones - Room2Ds in the same zone will be merged
            * PlenumZones - Only plenums in the same zone will be merged
            * Stories - Rooms in the same story will be merged
            * PlenumStories - Only plenums in the same story will be merged

        measures: Full path to a folder containing an OSW JSON be used as the base
            for the execution of the OpenStudio CLI. While this OSW can contain
            paths to measures that exist anywhere on the machine, the best practice
            is to copy the measures into this measures folder and use relative
            paths within the OSW. This makes it easier to move the inputs for
            this command from one machine to another.
        additional_idf: An IDF file with text to be appended to all EnergyPlus
            models generated from the Dragonfly Model before simulation. This
            input can be used to include EnergyPlus objects that are not
            natively supported.
        report_units: Text to set the units of the OpenStudio Results report
            that this command can output for each EnergyPlus model. Choose from
            the following:

            * none - no results report will be produced
            * si - all units will be in SI
            * ip - all units will be in IP

        viz_variable: An optional list of text values for EnergyPlus output
            variables to be visualized on the geometry in an output HTML report.
            For example, ["Zone Air System Sensible Heating Rate", "Zone Air System
            Sensible Cooling Rate"]. If None, no view_data report is produced.
        cpu_count: Optional integer to specify the number of processors to be
            used in simulating each model derived from the input model.
        folder: Folder on this computer, into which the IDF and result files will
            be written. If unspecified, the files will be output to the honeybee
            default simulation folder and placed in a project folder with the
            same name as the input model.
    """
    # get a ddy variable that might get used later
    epw_folder, epw_file_name = os.path.split(epw_file)
    ddy_file = os.path.join(epw_folder, epw_file_name.replace('.epw', '.ddy'))
    stat_file = os.path.join(epw_folder, epw_file_name.replace('.epw', '.stat'))

    # set the default folder to the default if it's not specified
    if folder is None:
        proj_name = os.path.basename(model_file).replace('.json', '')
        proj_name = proj_name.replace('.dfjson', '')
        proj_name = proj_name.replace('.geojson', '')
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

    if sim_par_json is None:  # generate some default simulation parameters
        sim_par = SimulationParameter()
        sim_par.output.add_zone_energy_use()
        sim_par.output.add_hvac_energy_use()
        sim_par.output.add_electricity_generation()
        sim_par.output.reporting_frequency = 'Monthly'
        sim_par.timestep = 1  # use hourly timestep for fast default simulation
        sim_par.shadow_calculation.solar_distribution = 'FullExterior'  # for speed!
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
    if sim_par.sizing_parameter.climate_zone is None and \
            os.path.isfile(stat_file):
        stat_obj = STAT(stat_file)
        sim_par.sizing_parameter.climate_zone = stat_obj.ashrae_climate_zone

    # re-serialize the Dragonfly Model from a DFJSON or GeoJSON
    with open(model_file) as json_file:
        data = json.load(json_file)
    if 'type' in data and data['type'] == 'Model':
        model = Model.from_dict(data)
        model.convert_to_units('Meters')
    else:  # assume that it is a GeoJSON
        model, _ = Model.from_geojson(model_file)
        model.separate_top_bottom_floors()

    # convert Dragonfly Model to Honeybee
    no_plenum = not plenum
    ceil_adjacency = not no_ceil_adjacency
    hb_models = model.to_honeybee(
        obj_per_model, shade_dist, use_multiplier=multiplier, exclude_plenums=no_plenum,
        solve_ceiling_adjacencies=ceil_adjacency, merge_method=merge_method
    )

    # write Honeybee models to JSONs in their own sub-folders
    hbjson_files = []
    for hb_model in hb_models:
        directory = os.path.join(folder, hb_model.identifier)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        hbjson_files.append(hb_model.to_hbjson(folder=directory))

    # if there is only one file, run the simulation so we can see the progress
    if len(hbjson_files) == 1:
        sim_folder = os.path.dirname(hbjson_files[0])
        simulate_model_hb(
            hbjson_files[0], epw_file, sim_par_json,
            measures=measures, additional_idf=additional_idf,
            report_units=report_units, viz_variable=viz_variable, folder=sim_folder
        )
        return

    # execute simulations in parallel
    cpu_count = cpu_count if cpu_count is not None else _recommended_processor_count()
    print('Simulating {} models with {} processors.'.format(len(hbjson_files), cpu_count))
    with ProcessPoolExecutor(max_workers=cpu_count) as executor:
        # submit all tasks to the executor
        futures = {
            executor.submit(
                    _simulate_hbjson,
                    path,
                    epw_file,
                    sim_par_json,
                    measures,
                    additional_idf,
                    report_units,
                    viz_variable
                ): path
            for path in hbjson_files
        }
        # yield results as soon as each process completes
        for future in as_completed(futures):
            success, original_path, msg = future.result()
            filename = os.path.basename(original_path)
            if success:
                suc_str = 'SUCCESS: Simulated {}'
                print(suc_str.format(filename))
            else:
                print('FAILED: Could not simulate {}'.format(filename))
                print('   Error details: {}'.format(msg.strip()))


def _simulate_hbjson(
    hbjson_path, epw_file, sim_par_json, measures, additional_idf,
    report_units, viz_variable
):
    """Translate a HBJSON file in EnergyPlus."""
    # honeybee-energy CLI command for translation
    sim_folder = os.path.dirname(hbjson_path)
    cmd = [
        folders.python_exe_path, '-m',
        'honeybee_energy', 'simulate', 'model',
        hbjson_path, epw_file, '--folder', sim_folder
    ]
    if sim_par_json is not None:
        cmd.append('--sim-par-json')
        cmd.append(sim_par_json)
    if measures is not None:
        cmd.append('--measures')
        cmd.append(measures)
    if additional_idf is not None:
        cmd.append('--additional-idf')
        cmd.append(additional_idf)
    if str(report_units).lower() in ('si', 'ip'):
        cmd.append('--report-units')
        cmd.append(report_units)
    if viz_variable is not None and len(viz_variable) != 0:
        for var in viz_variable:
            cmd.append('--viz-variable')
            cmd.append(var)
    try:
        # execute the CLI command
        process = subprocess.run(
            cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return True, hbjson_path, process.stdout
    except subprocess.CalledProcessError as e:
        return False, hbjson_path, e.stderr


@simulate.command('urbanopt')
@click.argument(
    'feature-file',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True)
)
@click.argument(
    'scenario-file',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True)
)
@click.option(
    '--log-file', '-log', help='Optional log file to output the paths to the '
    'generated simulation files if they were successfully created. '
    'By default this will be printed out to stdout',
    type=click.File('w'), default='-', show_default=True)
def simulate_urbanopt_cli(feature_file, scenario_file, log_file):
    """Simulate am URBANopt project folder that is already prepared for simulation.

    \b
    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.
    """
    try:
        simulate_urbanopt(feature_file, scenario_file, log_file)
    except Exception as e:
        _logger.exception('URBANopt simulation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def simulate_urbanopt(feature_file, scenario_file, log_file=None):
    """Simulate am URBANopt project folder that is already prepared for simulation.

    Args:
        feature_geojson: The full path to a .geojson file containing the
            footprints of buildings to be simulated.
        scenario_csv: The full path to  a .csv file for the URBANopt scenario.
        log_file: Optional log file to output the paths to the generated
            simulation files if they were successfully created. By default this
            string will be returned from this method.
    """
    # run the URBANopt CLI to complete the simulation
    osm, idf, sql, zsz, rdd, html, err = run_urbanopt(feature_file, scenario_file)

    # process all of the output files into the log file
    gen_files = {
        'osm': osm,
        'idf': idf,
        'sql': sql,
        'zsz': zsz,
        'rdd': rdd,
        'html': html,
        'err': err
    }
    return process_content_to_output(json.dumps(gen_files, indent=4), log_file)
