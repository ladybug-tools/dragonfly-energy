"""dragonfly energy translation commands."""
import click
import sys
import os
import logging
import json
import shutil

from ladybug.futil import preparedir
from ladybug.commandutil import process_content_to_output
from ladybug.epw import EPW
from honeybee.config import folders as hb_folders
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.run import to_openstudio_osw, to_gbxml_osw, to_sdd_osw, run_osw, \
    add_gbxml_space_boundaries, set_gbxml_floor_types, trace_compatible_model_json, \
    _parse_os_cli_failure
from honeybee_energy.writer import energyplus_idf_version
from honeybee_energy.config import folders
from dragonfly.model import Model


_logger = logging.getLogger(__name__)


@click.group(help='Commands for translating Dragonfly JSON files to/from OSM/IDF.')
def translate():
    pass


@translate.command('model-to-osm')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--sim-par-json', '-sp', help='Full path to a honeybee energy '
              'SimulationParameter JSON that describes all of the settings for '
              'the simulation. If None default parameters will be generated.',
              default=None, show_default=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--epw-file', '-epw', help='Full path to an EPW file to be associated '
              'with the exported OSM. This is typically not necessary but may be '
              'used when a sim-par-json is specified that requests a HVAC sizing '
              'calculation to be run as part of the translation process but no design '
              'days are inside this simulation parameter.',
              default=None, show_default=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--multiplier/--full-geometry', ' /-fg', help='Flag to note if the '
              'multipliers on each Building story will be passed along to the '
              'generated Honeybee Room objects or if full geometry objects should be '
              'written for each story in the building.', default=True, show_default=True)
@click.option('--plenum/--no-plenum', '-p/-np', help='Flag to indicate whether '
              'ceiling/floor plenum depths assigned to Room2Ds should generate '
              'distinct 3D Rooms in the translation.', default=True, show_default=True)
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
@click.option('--geometry-ids/--geometry-names', ' /-gn', help='Flag to note whether a '
              'cleaned version of all geometry display names should be used instead '
              'of identifiers when translating the Model to OSM and IDF. '
              'Using this flag will affect all Rooms, Faces, Apertures, '
              'Doors, and Shades. It will generally result in more read-able names '
              'in the OSM and IDF but this means that it will not be easy to map '
              'the EnergyPlus results back to the original Honeybee Model. Cases '
              'of duplicate IDs resulting from non-unique names will be resolved '
              'by adding integers to the ends of the new IDs that are derived from '
              'the name.', default=True, show_default=True)
@click.option('--resource-ids/--resource-names', ' /-rn', help='Flag to note whether a '
              'cleaned version of all resource display names should be used instead '
              'of identifiers when translating the Model to OSM and IDF. '
              'Using this flag will affect all Materials, Constructions, '
              'ConstructionSets, Schedules, Loads, and ProgramTypes. It will generally '
              'result in more read-able names for the resources in the OSM and IDF. '
              'Cases of duplicate IDs resulting from non-unique names will be resolved '
              'by adding integers to the ends of the new IDs that are derived from '
              'the name.', default=True, show_default=True)
@click.option('--log-file', '-log', help='Optional log file to output the paths to the '
              'generated OSM and IDF files if they were successfully created. '
              'By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def model_to_osm_cli(
        model_file, sim_par_json, epw_file, multiplier, plenum, no_ceil_adjacency,
        folder, osm_file, idf_file, geometry_ids, resource_ids, log_file):
    """Translate a Dragonfly Model to an OpenStudio Model.

    \b
    Args:
        model_file: Path to either a DFJSON or DFpkl file. This can also be a
            HBJSON or a HBpkl from which a Dragonfly model should be derived.
    """
    try:
        full_geometry = not multiplier
        no_plenum = not plenum
        ceil_adjacency = not no_ceil_adjacency
        geo_names = not geometry_ids
        res_names = not resource_ids
        model_to_osm(
            model_file, sim_par_json, epw_file, full_geometry, no_plenum, ceil_adjacency,
            folder, osm_file, idf_file, geo_names, res_names, log_file)
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def model_to_osm(
    model_file, sim_par_json=None, epw_file=None,
    full_geometry=False, no_plenum=False, ceil_adjacency=False,
    folder=None, osm_file=None, idf_file=None,
    geometry_names=False, resource_names=False, log_file=None,
    multiplier=True, plenum=True, no_ceil_adjacency=True,
    geometry_ids=True, resource_ids=True
):
    """Translate a Dragonfly Model to an OpenStudio Model.

    Args:
        model_file: Path to either a DFJSON or DFpkl file. This can also be a
            HBJSON or a HBpkl from which a Dragonfly model should be derived.
        sim_par_json: Full path to a honeybee energy SimulationParameter JSON that
            describes all of the settings for the simulation. If None, default
            parameters will be generated.
        epw_file: Full path to an EPW file to be associated with the exported OSM.
            This is typically not necessary but may be used when a sim-par-json is
            specified that requests a HVAC sizing calculation to be run as part
            of the translation process but no design days are inside this
            simulation parameter.
        full_geometry: Boolean to note if the multipliers on each Building story
            will be passed along to the generated Honeybee Room objects or if
            full geometry objects should be written for each story in the
            building. (Default: False).
        no_plenum: Boolean to indicate whether ceiling/floor plenum depths
            assigned to Room2Ds should generate distinct 3D Rooms in the
            translation. (Default: False).
        ceil_adjacency: Boolean to indicate whether adjacencies should be solved
            between interior stories when Room2Ds perfectly match one another
            in their floor plate. This ensures that Surface boundary conditions
            are used instead of Adiabatic ones. Note that this input has no
            effect when the object-per-model is Story. (Default: False).
        folder: Folder on this computer, into which the working files, OSM and IDF
            files will be written. If None, the files will be output in the
            same location as the model_file.
        osm_file: Optional path where the OSM will be copied after it is translated
            in the folder. If None, the file will not be copied.
        idf_file: Optional path where the IDF will be copied after it is translated
            in the folder. If None, the file will not be copied.
        geometry_names: Boolean to note whether a cleaned version of all geometry
            display names should be used instead of identifiers when translating
            the Model to OSM and IDF. Using this flag will affect all Rooms, Faces,
            Apertures, Doors, and Shades. It will generally result in more read-able
            names in the OSM and IDF but this means that it will not be easy to map
            the EnergyPlus results back to the original Honeybee Model. Cases
            of duplicate IDs resulting from non-unique names will be resolved
            by adding integers to the ends of the new IDs that are derived from
            the name. (Default: False).
        resource_names: Boolean to note whether a cleaned version of all resource
            display names should be used instead of identifiers when translating
            the Model to OSM and IDF. Using this flag will affect all Materials,
            Constructions, ConstructionSets, Schedules, Loads, and ProgramTypes.
            It will generally result in more read-able names for the resources
            in the OSM and IDF. Cases of duplicate IDs resulting from non-unique
            names will be resolved by adding integers to the ends of the new IDs
            that are derived from the name. (Default: False).
        bypass_check: Boolean to note whether the Model should be re-serialized
            to Python and checked before it is translated to .osm. The check is
            not needed if the model-json was exported directly from the
            honeybee-energy Python library. (Default: False).
        log_file: Optional log file to output the paths to the generated OSM and]
            IDF files if they were successfully created. By default this string
            will be returned from this method.
    """
    # set the default folder to the default if it's not specified
    if folder is None:
        folder = os.path.dirname(os.path.abspath(model_file))
    preparedir(folder, remove_content=False)

    # generate default simulation parameters
    if sim_par_json is None:
        sim_par = SimulationParameter()
        sim_par.output.add_zone_energy_use()
        sim_par.output.add_hvac_energy_use()
        sim_par.output.add_electricity_generation()
        sim_par.output.reporting_frequency = 'Monthly'
    else:
        with open(sim_par_json) as json_file:
            data = json.load(json_file)
        sim_par = SimulationParameter.from_dict(data)

    # perform a check to be sure the EPW file is specified for sizing runs
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

    if sim_par.sizing_parameter.efficiency_standard is not None:
        assert epw_file is not None, 'An epw_file must be specified for ' \
            'translation to OSM whenever a Simulation Parameter ' \
            'efficiency_standard is specified.\nNo EPW was specified yet the ' \
            'Simulation Parameter efficiency_standard is "{}".'.format(
                sim_par.sizing_parameter.efficiency_standard
            )
        epw_folder, epw_file_name = os.path.split(epw_file)
        ddy_file = os.path.join(epw_folder, epw_file_name.replace('.epw', '.ddy'))
        if len(sim_par.sizing_parameter.design_days) == 0 and \
                os.path.isfile(ddy_file):
            try:
                sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
            except AssertionError:  # no design days within the DDY file
                ddy_from_epw(epw_file, sim_par)
        elif len(sim_par.sizing_parameter.design_days) == 0:
            ddy_from_epw(epw_file, sim_par)
        sim_par_json = write_sim_par(sim_par)
    elif sim_par_json is None:
        sim_par_json = write_sim_par(sim_par)

    # re-serialize the Dragonfly Model
    model = Model.from_file(model_file)
    model.convert_to_units('Meters')

    # convert Dragonfly Model to Honeybee
    multiplier = not full_geometry
    hb_models = model.to_honeybee(
        object_per_model='District', use_multiplier=multiplier,
        exclude_plenums=no_plenum, solve_ceiling_adjacencies=ceil_adjacency,
        enforce_adj=False)
    hb_model = hb_models[0]

    # create the HBJSON for input to OpenStudio CLI
    hb_model_json = _measure_compatible_model_json(
        hb_model, folder, use_geometry_names=geometry_names,
        use_resource_names=resource_names)

    # Write the osw file to translate the model to osm
    osw = to_openstudio_osw(folder, hb_model_json, sim_par_json, epw_file=epw_file)

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
        if log_file is None:
            return json.dumps([osm, idf], indent=4)
        else:
            log_file.write(json.dumps([osm, idf], indent=4))
    else:
        _parse_os_cli_failure(folder)


@translate.command('model-to-idf')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--sim-par-json', '-sp', help='Full path to a honeybee energy '
              'SimulationParameter JSON that describes all of the settings for '
              'the simulation. If None default parameters will be generated.',
              default=None, show_default=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--multiplier/--full-geometry', ' /-fg', help='Flag to note if the '
              'multipliers on each Building story will be passed along to the '
              'generated Honeybee Room objects or if full geometry objects should be '
              'written for each story in the building.', default=True, show_default=True)
@click.option('--plenum/--no-plenum', '-p/-np', help='Flag to indicate whether '
              'ceiling/floor plenum depths assigned to Room2Ds should generate '
              'distinct 3D Rooms in the translation.', default=True, show_default=True)
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
@click.option('--geometry-ids/--geometry-names', ' /-gn', help='Flag to note whether a '
              'cleaned version of all geometry display names should be used instead '
              'of identifiers when translating the Model to IDF. Using this flag will '
              'affect all Rooms, Faces, Apertures, Doors, and Shades. It will '
              'generally result in more read-able names in the IDF but this means that '
              'it will not be easy to map the EnergyPlus results back to the original '
              'Honeybee Model. Cases of duplicate IDs resulting from non-unique names '
              'will be resolved by adding integers to the ends of the new IDs that are '
              'derived from the name.', default=True, show_default=True)
@click.option('--resource-ids/--resource-names', ' /-rn', help='Flag to note whether a '
              'cleaned version of all resource display names should be used instead '
              'of identifiers when translating the Model to IDF. Using this flag will '
              'affect all Materials, Constructions, ConstructionSets, Schedules, '
              'Loads, and ProgramTypes. It will generally result in more read-able '
              'names for the resources in the IDF. Cases of duplicate IDs resulting '
              'from non-unique names will be resolved by adding integers to the ends '
              'of the new IDs that are derived from the name.',
              default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional IDF file to output the IDF string '
              'of the translation. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def model_to_idf_cli(
    model_file, sim_par_json, multiplier, plenum, no_ceil_adjacency,
    additional_str, compact_schedules, hvac_to_ideal_air,
    geometry_ids, resource_ids, output_file
):
    """Translate a Dragonfly Model to an IDF using direct-to-idf translators.

    The resulting IDF should be simulate-able but not all Model properties might
    make it into the IDF given that the direct-to-idf translators are used.

    \b
    Args:
        model_file: Path to either a DFJSON or DFpkl file. This can also be a
            HBJSON or a HBpkl from which a Dragonfly model should be derived.
    """
    try:
        full_geometry = not multiplier
        no_plenum = not plenum
        ceil_adjacency = not no_ceil_adjacency
        csv_schedules = not compact_schedules
        hvac_check = not hvac_to_ideal_air
        geo_names = not geometry_ids
        res_names = not resource_ids
        model_to_idf(
            model_file, sim_par_json, full_geometry, no_plenum, ceil_adjacency,
            additional_str, csv_schedules,
            hvac_check, geo_names, res_names, output_file)
    except Exception as e:
        _logger.exception('Model translation failed.\n{}\n'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def model_to_idf(
    model_file, sim_par_json=None,
    full_geometry=False, no_plenum=False, ceil_adjacency=False,
    additional_str='', csv_schedules=False, hvac_check=False,
    geometry_names=False, resource_names=False, output_file=None,
    multiplier=True, plenum=True, no_ceil_adjacency=True,
    compact_schedules=True, hvac_to_ideal_air=True, geometry_ids=True, resource_ids=True
):
    """Translate a Dragonfly Model to an IDF using direct-to-idf translators.

    The resulting IDF should be simulate-able but not all Model properties might
    make it into the IDF given that the direct-to-idf translators are used.

    Args:
        model_file: Path to either a DFJSON or DFpkl file. This can also be a
            HBJSON or a HBpkl from which a Dragonfly model should be derived.
        sim_par_json: Full path to a honeybee energy SimulationParameter JSON that
            describes all of the settings for the simulation. If None, default
            parameters will be generated.
        full_geometry: Boolean to note if the multipliers on each Building story
            will be passed along to the generated Honeybee Room objects or if
            full geometry objects should be written for each story in the
            building. (Default: False).
        no_plenum: Boolean to indicate whether ceiling/floor plenum depths
            assigned to Room2Ds should generate distinct 3D Rooms in the
            translation. (Default: False).
        ceil_adjacency: Boolean to indicate whether adjacencies should be solved
            between interior stories when Room2Ds perfectly match one another
            in their floor plate. This ensures that Surface boundary conditions
            are used instead of Adiabatic ones. Note that this input has no
            effect when the object-per-model is Story. (Default: False).
        additional_str: Text string for additional lines that should be added
            to the IDF.
        csv_schedules: Boolean to note whether any ScheduleFixedIntervals in the
            model should be included in the IDF string as a Schedule:Compact or
            they should be written as CSV Schedule:File and placed in a directory
            next to the output_file. (Default: False).
        hvac_check: Boolean to note whether any detailed HVAC system templates
            should be converted to an equivalent IdealAirSystem upon export.
            If hvac-check is used and the Model contains detailed systems, a
            ValueError will be raised. (Default: False).
        geometry_names: Boolean to note whether a cleaned version of all geometry
            display names should be used instead of identifiers when translating
            the Model to OSM and IDF. Using this flag will affect all Rooms, Faces,
            Apertures, Doors, and Shades. It will generally result in more read-able
            names in the OSM and IDF but this means that it will not be easy to map
            the EnergyPlus results back to the original Honeybee Model. Cases
            of duplicate IDs resulting from non-unique names will be resolved
            by adding integers to the ends of the new IDs that are derived from
            the name. (Default: False).
        resource_names: Boolean to note whether a cleaned version of all resource
            display names should be used instead of identifiers when translating
            the Model to OSM and IDF. Using this flag will affect all Materials,
            Constructions, ConstructionSets, Schedules, Loads, and ProgramTypes.
            It will generally result in more read-able names for the resources
            in the OSM and IDF. Cases of duplicate IDs resulting from non-unique
            names will be resolved by adding integers to the ends of the new IDs
            that are derived from the name. (Default: False).
        output_file: Optional IDF file to output the IDF string of the translation.
            By default this string will be returned from this method.
    """
    # check that the simulation parameters are there and load them
    if sim_par_json is not None:
        with open(sim_par_json) as json_file:
            data = json.load(json_file)
        sim_par = SimulationParameter.from_dict(data)
    else:
        sim_par = SimulationParameter()
        sim_par.output.add_zone_energy_use()
        sim_par.output.add_hvac_energy_use()
        sim_par.output.add_electricity_generation()
        sim_par.output.reporting_frequency = 'Monthly'

    # re-serialize the Dragonfly Model
    model = Model.from_file(model_file)
    model.convert_to_units('Meters')

    # convert Dragonfly Model to Honeybee
    multiplier = not full_geometry
    hb_models = model.to_honeybee(
        object_per_model='District', use_multiplier=multiplier,
        exclude_plenums=no_plenum, solve_ceiling_adjacencies=ceil_adjacency,
        enforce_adj=False)
    hb_model = hb_models[0]

    # reset the IDs to be derived from the display_names if requested
    if geometry_names:
        model.reset_ids()
    if resource_names:
        model.properties.energy.reset_resource_ids()

    # set the schedule directory in case it is needed
    sch_directory = None
    if csv_schedules:
        sch_path = os.path.abspath(model_file) if 'stdout' in str(output_file) \
            else os.path.abspath(str(output_file))
        sch_directory = os.path.join(os.path.split(sch_path)[0], 'schedules')

    # create the strings for simulation parameters and model
    ver_str = energyplus_idf_version() if folders.energyplus_version \
        is not None else ''
    sim_par_str = sim_par.to_idf()
    hvac_to_ideal_air = not hvac_check
    model_str = hb_model.to.idf(
        hb_model, schedule_directory=sch_directory,
        use_ideal_air_equivalent=hvac_to_ideal_air)
    idf_str = '\n\n'.join([ver_str, sim_par_str, model_str, additional_str])

    # write out the result
    return process_content_to_output(idf_str, output_file)


@translate.command('model-to-gbxml')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--multiplier/--full-geometry', ' /-fg', help='Flag to note if the '
              'multipliers on each Building story will be passed along to the '
              'generated Honeybee Room objects or if full geometry objects should be '
              'written for each story in the building.', default=True, show_default=True)
@click.option('--plenum/--no-plenum', '-p/-np', help='Flag to indicate whether '
              'ceiling/floor plenum depths assigned to Room2Ds should generate '
              'distinct 3D Rooms in the translation.', default=True, show_default=True)
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
@click.option('--default-subfaces/--triangulate-subfaces', ' /-t',
              help='Flag to note whether sub-faces (including Apertures and Doors) '
              'should be triangulated if they have more than 4 sides (True) or whether '
              'they should be left as they are (False). This triangulation is '
              'necessary when exporting directly to EnergyPlus since it cannot accept '
              'sub-faces with more than 4 vertices.', default=True, show_default=True)
@click.option('--triangulate-non-planar/--permit-non-planar', ' /-np',
              help='Flag to note whether any non-planar orphaned geometry in the '
              'model should be triangulated upon export. This can be helpful because '
              'OpenStudio simply raises an error when it encounters non-planar '
              'geometry, which would hinder the ability to save gbXML files that are '
              'to be corrected in other software.', default=True, show_default=True)
@click.option('--minimal/--complete-geometry', ' /-cg', help='Flag to note whether space '
              'boundaries and shell geometry should be included in the exported '
              'gbXML vs. just the minimal required non-manifold geometry.',
              default=True, show_default=True)
@click.option('--interior-face-type', '-ift', help='Text string for the type to be '
              'used for all interior floor faces. If unspecified, the interior types '
              'will be left as they are. Choose from: InteriorFloor, Ceiling.',
              type=str, default='', show_default=True)
@click.option('--ground-face-type', '-gft', help='Text string for the type to be '
              'used for all ground-contact floor faces. If unspecified, the ground '
              'types will be left as they are. Choose from: UndergroundSlab, '
              'SlabOnGrade, RaisedFloor.', type=str, default='', show_default=True)
@click.option('--output-file', '-f', help='Optional gbXML file to output the string '
              'of the translation. By default it printed out to stdout', default='-',
              type=click.Path(file_okay=True, dir_okay=False, resolve_path=True))
def model_to_gbxml_cli(
    model_file, multiplier, plenum, no_ceil_adjacency,
    osw_folder, default_subfaces, triangulate_non_planar, minimal,
    interior_face_type, ground_face_type, output_file
):
    """Translate a Dragonfly Model to a gbXML file.

    \b
    Args:
        model_file: Path to either a DFJSON or DFpkl file. This can also be a
            HBJSON or a HBpkl from which a Dragonfly model should be derived.
    """
    try:
        full_geometry = not multiplier
        no_plenum = not plenum
        ceil_adjacency = not no_ceil_adjacency
        triangulate_subfaces = not default_subfaces
        permit_non_planar = not triangulate_non_planar
        complete_geometry = not minimal
        model_to_gbxml(
            model_file, osw_folder, full_geometry, no_plenum, ceil_adjacency,
            triangulate_subfaces, permit_non_planar, complete_geometry,
            interior_face_type, ground_face_type, output_file)
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def model_to_gbxml(
    model_file, osw_folder=None, full_geometry=False,
    no_plenum=False, ceil_adjacency=False,
    triangulate_subfaces=False, permit_non_planar=False, complete_geometry=False,
    interior_face_type='', ground_face_type='', output_file=None,
    multiplier=True, plenum=True, no_ceil_adjacency=True,
    default_subfaces=True, triangulate_non_planar=True, minimal=True,
):
    """Translate a Dragonfly Model to a gbXML file.

    Args:
        model_file: Path to either a DFJSON or DFpkl file. This can also be a
            HBJSON or a HBpkl from which a Dragonfly model should be derived.
        osw_folder: Folder on this computer, into which the working files will
            be written. If None, it will be written into a temp folder in the
            default simulation folder.
        full_geometry: Boolean to note if the multipliers on each Building story
            will be passed along to the generated Honeybee Room objects or if
            full geometry objects should be written for each story in the
            building. (Default: False).
        no_plenum: Boolean to indicate whether ceiling/floor plenum depths
            assigned to Room2Ds should generate distinct 3D Rooms in the
            translation. (Default: False).
        ceil_adjacency: Boolean to indicate whether adjacencies should be solved
            between interior stories when Room2Ds perfectly match one another
            in their floor plate. This ensures that Surface boundary conditions
            are used instead of Adiabatic ones. Note that this input has no
            effect when the object-per-model is Story. (Default: False).
        triangulate_subfaces: Boolean to note whether sub-faces (including
            Apertures and Doors) should be triangulated if they have more
            than 4 sides (True) or whether they should be left as they are (False).
            This triangulation is necessary when exporting directly to EnergyPlus
            since it cannot accept sub-faces with more than 4 vertices. (Default: False).
        permit_non_planar: Boolean to note whether any non-planar orphaned geometry
            in the model should be triangulated upon export. This can be helpful
            because OpenStudio simply raises an error when it encounters non-planar
            geometry, which would hinder the ability to save gbXML files that are
            to be corrected in other software. (Default: False).
        complete_geometry: Boolean to note whether space boundaries and shell geometry
            should be included in the exported gbXML vs. just the minimal required
            non-manifold geometry. (Default: False).
        interior_face_type: Text string for the type to be used for all interior
            floor faces. If unspecified, the interior types will be left as they are.
            Choose from: InteriorFloor, Ceiling.
        ground_face_type: Text string for the type to be used for all ground-contact
            floor faces. If unspecified, the ground types will be left as they are.
            Choose from: UndergroundSlab, SlabOnGrade, RaisedFloor.
        bypass_check: Boolean to note whether the Model should be re-serialized
            to Python and checked before it is translated to .osm. The check is
            not needed if the model-json was exported directly from the
            honeybee-energy Python library. (Default: False).
        output_file: Optional gbXML file to output the string of the translation.
            By default it will be returned from this method.
    """
    # set the default folder if it's not specified
    out_path = None
    out_directory = os.path.join(hb_folders.default_simulation_folder, 'temp_translate') \
        if osw_folder is None else osw_folder
    if output_file.endswith('-'):
        f_name = os.path.basename(model_file).lower()
        f_name = f_name.replace('.dfjson', '.xml').replace('.json', '.xml')
        f_name = f_name.replace('.dfplk', '.xml').replace('.pkl', '.xml')
        f_name = f_name.replace('.hbjson', '.xml').replace('.hbpkl', '.xml')
        out_path = os.path.join(out_directory, f_name)
    elif output_file.endswith('.gbxml'):  # avoid OpenStudio complaining about .gbxml
        f_name = os.path.basename(model_file).lower()
        f_name = f_name.replace('.gbxml', '.xml')
        out_path = os.path.join(out_directory, f_name)
    preparedir(out_directory)

    # re-serialize the Dragonfly Model
    model = Model.from_dfjson(model_file)
    model.convert_to_units('Meters')

    # convert Dragonfly Model to Honeybee
    multiplier = not full_geometry
    hb_models = model.to_honeybee(
        object_per_model='District', use_multiplier=multiplier,
        exclude_plenums=no_plenum, solve_ceiling_adjacencies=ceil_adjacency,
        enforce_adj=False)
    hb_model = hb_models[0]

    # create the dictionary of the HBJSON for input to OpenStudio CLI
    tri_non_planar = not permit_non_planar
    hb_model_json = _measure_compatible_model_json(
            hb_model, out_directory, simplify_window_cons=True,
            triangulate_sub_faces=triangulate_subfaces,
            triangulate_non_planar_orphaned=tri_non_planar)

    # Write the osw file and translate the model to gbXML
    out_f = out_path if output_file is None or output_file.endswith('-') else output_file
    osw = to_gbxml_osw(hb_model_json, out_f, osw_folder)
    if not complete_geometry and not (interior_face_type or ground_face_type):
        file_contents = _run_translation_osw(osw, out_path)
    else:
        _, idf = run_osw(osw, silent=True)
        if idf is not None and os.path.isfile(idf):
            if interior_face_type or ground_face_type:
                int_ft = interior_face_type if interior_face_type != '' else None
                gnd_ft = ground_face_type if ground_face_type != '' else None
                set_gbxml_floor_types(out_f, int_ft, gnd_ft)
            if complete_geometry:
                add_gbxml_space_boundaries(out_f, hb_model)
            if out_path is not None:  # load the JSON string to stdout
                with open(out_path) as json_file:
                    file_contents = json_file.read()
        else:
            _parse_os_cli_failure(osw_folder)

    # return the file contents if requested
    if file_contents is not None:
        if output_file is None:
            return file_contents
        else:
            print(file_contents)


@translate.command('model-to-trace-gbxml')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--multiplier/--full-geometry', ' /-fg', help='Flag to note if the '
              'multipliers on each Building story will be passed along to the '
              'generated Honeybee Room objects or if full geometry objects should be '
              'written for each story in the building.', default=True, show_default=True)
@click.option('--plenum/--no-plenum', '-p/-np', help='Flag to indicate whether '
              'ceiling/floor plenum depths assigned to Room2Ds should generate '
              'distinct 3D Rooms in the translation.', default=True, show_default=True)
@click.option('--no-ceil-adjacency/--ceil-adjacency', ' /-a', help='Flag to indicate '
              'whether adjacencies should be solved between interior stories when '
              'Room2Ds perfectly match one another in their floor plate. This ensures '
              'that Surface boundary conditions are used instead of Adiabatic ones. '
              'Note that this input has no effect when the object-per-model is Story.',
              default=True, show_default=True)
@click.option('--single-window/--detailed-windows', ' /-fg', help='Flag to note '
              'whether all windows within walls should be converted to a single '
              'window with an area that matches the original geometry.',
              default=True, show_default=True)
@click.option('--rect-sub-distance', '-r', help='A number for the resolution at which '
              'non-rectangular Apertures will be subdivided into smaller rectangular '
              'units. This is required as TRACE 3D plus cannot model non-rectangular '
              'geometries. This can include the units of the distance (eg. 0.5ft) or, '
              'if no units are provided, the value will be interpreted in the '
              'honeybee model units.',
              type=str, default='0.15m', show_default=True)
@click.option('--frame-merge-distance', '-m', help='A number for the maximum distance '
              'between non-rectangular Apertures at which point the Apertures will be '
              'merged into a single rectangular geometry. This is often helpful when '
              'there are several triangular Apertures that together make a rectangle '
              'when they are merged across their frames. This can include the units '
              'of the distance (eg. 0.5ft) or, if no units are provided, the value '
              'will be interpreted in the honeybee model units',
              type=str, default='0.2m', show_default=True)
@click.option('--osw-folder', '-osw', help='Folder on this computer, into which the '
              'working files will be written. If None, it will be written into a '
              'temp folder in the default simulation folder.', default=None,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--output-file', '-f', help='Optional gbXML file to output the string '
              'of the translation. By default it printed out to stdout.', default='-',
              type=click.Path(file_okay=True, dir_okay=False, resolve_path=True))
def model_to_trace_gbxml_cli(
    model_file, multiplier, plenum, no_ceil_adjacency,
    single_window, rect_sub_distance, frame_merge_distance,
    osw_folder, output_file
):
    """Translate a Dragonfly Model to a TRACE-compatible gbXML file.

    \b
    Args:
        model_file: Path to either a DFJSON or DFpkl file. This can also be a
            HBJSON or a HBpkl from which a Dragonfly model should be derived.
    """
    try:
        full_geometry = not multiplier
        no_plenum = not plenum
        ceil_adjacency = not no_ceil_adjacency
        detailed_windows = not single_window
        model_to_trace_gbxml(
            model_file, full_geometry, no_plenum, ceil_adjacency, detailed_windows,
            rect_sub_distance, frame_merge_distance, osw_folder, output_file)
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def model_to_trace_gbxml(
    model_file, full_geometry=False, no_plenum=False, ceil_adjacency=False,
    detailed_windows=False, rect_sub_distance='0.15m',
    frame_merge_distance='0.2m', osw_folder=None, output_file=None,
    multiplier=True, plenum=True, no_ceil_adjacency=True, single_window=True
):
    """Translate a Dragonfly Model to a gbXML file that is compatible with TRACE.

    Args:
        model_file: Path to either a DFJSON or DFpkl file. This can also be a
            HBJSON or a HBpkl from which a Dragonfly model should be derived.
        full_geometry: Boolean to note if the multipliers on each Building story
            will be passed along to the generated Honeybee Room objects or if
            full geometry objects should be written for each story in the
            building. (Default: False).
        no_plenum: Boolean to indicate whether ceiling/floor plenum depths
            assigned to Room2Ds should generate distinct 3D Rooms in the
            translation. (Default: False).
        ceil_adjacency: Boolean to indicate whether adjacencies should be solved
            between interior stories when Room2Ds perfectly match one another
            in their floor plate. This ensures that Surface boundary conditions
            are used instead of Adiabatic ones. Note that this input has no
            effect when the object-per-model is Story. (Default: False).
        detailed_windows: A boolean for whether all windows within walls should be
            left as they are (True) or converted to a single window with an area
            that matches the original geometry (False). (Default: False).
        rect_sub_distance: A number for the resolution at which non-rectangular
            Apertures will be subdivided into smaller rectangular units. This is
            required as TRACE 3D plus cannot model non-rectangular geometries.
            This can include the units of the distance (eg. 0.5ft) or, if no units
            are provided, the value will be interpreted in the honeybee model
            units. (Default: 0.15m).
        frame_merge_distance: A number for the maximum distance between non-rectangular
            Apertures at which point the Apertures will be merged into a single
            rectangular geometry. This is often helpful when there are several
            triangular Apertures that together make a rectangle when they are
            merged across their frames. This can include the units of the
            distance (eg. 0.5ft) or, if no units are provided, the value will
            be interpreted in the honeybee model units. (Default: 0.2m).
        osw_folder: Folder on this computer, into which the working files will
            be written. If None, it will be written into a temp folder in the
            default simulation folder.
        output_file: Optional gbXML file to output the string of the translation.
            By default it will be returned from this method.
    """
    # set the default folder if it's not specified
    out_path = None
    out_directory = os.path.join(hb_folders.default_simulation_folder, 'temp_translate') \
        if osw_folder is None else osw_folder
    if output_file.endswith('-'):
        f_name = os.path.basename(model_file).lower()
        f_name = f_name.replace('.dfjson', '.xml').replace('.json', '.xml')
        f_name = f_name.replace('.dfplk', '.xml').replace('.pkl', '.xml')
        f_name = f_name.replace('.hbjson', '.xml').replace('.hbpkl', '.xml')
        out_path = os.path.join(out_directory, f_name)
    elif output_file.endswith('.gbxml'):  # avoid OpenStudio complaining about .gbxml
        f_name = os.path.basename(model_file).lower()
        f_name = f_name.replace('.gbxml', '.xml')
        out_path = os.path.join(out_directory, f_name)
    preparedir(out_directory)

    # re-serialize the Dragonfly Model
    model = Model.from_dfjson(model_file)
    model.convert_to_units('Meters')

    # convert Dragonfly Model to Honeybee
    multiplier = not full_geometry
    hb_models = model.to_honeybee(
        object_per_model='District', use_multiplier=multiplier,
        exclude_plenums=no_plenum, solve_ceiling_adjacencies=ceil_adjacency,
        enforce_adj=False)
    hb_model = hb_models[0]
    hb_model_file = os.path.join(out_directory, 'in.hbjson')
    with open(hb_model_file, 'w', encoding='utf-8') as hmf:
        json.dump(hb_model.to_dict(), hmf, ensure_ascii=False)

    # run the Model re-serialization and check if specified
    single_window = not detailed_windows
    hb_model_file = trace_compatible_model_json(
        hb_model_file, out_directory, single_window,
        rect_sub_distance, frame_merge_distance)

    # Write the osw file and translate the model to gbXML
    out_f = out_path if output_file is None or output_file.endswith('-') else output_file
    osw = to_gbxml_osw(hb_model_file, out_f, osw_folder)
    file_contents = _run_translation_osw(osw, out_path)

    # return the file contents if requested
    if file_contents is not None:
        if output_file is None:
            return file_contents
        else:
            print(file_contents)


@translate.command('model-to-sdd')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--multiplier/--full-geometry', ' /-fg', help='Flag to note if the '
              'multipliers on each Building story will be passed along to the '
              'generated Honeybee Room objects or if full geometry objects should be '
              'written for each story in the building.', default=True, show_default=True)
@click.option('--plenum/--no-plenum', '-p/-np', help='Flag to indicate whether '
              'ceiling/floor plenum depths assigned to Room2Ds should generate '
              'distinct 3D Rooms in the translation.', default=True, show_default=True)
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
@click.option('--geometry-ids/--geometry-names', ' /-gn', help='Flag to note whether a '
              'cleaned version of all geometry display names should be used instead '
              'of identifiers when translating the Model to SDD. Using this flag will '
              'affect all Rooms, Faces, Apertures, Doors, and Shades. It will '
              'generally result in more read-able names in the SDD but this means that '
              'it will not be easy to map the EnergyPlus results back to the original '
              'Honeybee Model. Cases of duplicate IDs resulting from non-unique names '
              'will be resolved by adding integers to the ends of the new IDs that are '
              'derived from the name.', default=True, show_default=True)
@click.option('--resource-ids/--resource-names', ' /-rn', help='Flag to note whether a '
              'cleaned version of all resource display names should be used instead '
              'of identifiers when translating the Model to SDD. Using this flag will '
              'affect all Materials, Constructions, ConstructionSets, Schedules, '
              'Loads, and ProgramTypes. It will generally result in more read-able '
              'names for the resources in the SDD. Cases of duplicate IDs resulting '
              'from non-unique names will be resolved by adding integers to the ends '
              'of the new IDs that are derived from the name.',
              default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional gbXML file to output the string '
              'of the translation. By default it printed out to stdout', default='-',
              type=click.Path(file_okay=True, dir_okay=False, resolve_path=True))
def model_to_sdd_cli(
    model_file, multiplier, plenum, no_ceil_adjacency, osw_folder,
    geometry_ids, resource_ids, output_file
):
    """Translate a Dragonfly Model to a CBECC SDD file.

    \b
    Args:
        model_file: Path to either a DFJSON or DFpkl file. This can also be a
            HBJSON or a HBpkl from which a Dragonfly model should be derived.
    """
    try:
        full_geometry = not multiplier
        no_plenum = not plenum
        ceil_adjacency = not no_ceil_adjacency
        geo_names = not geometry_ids
        res_names = not resource_ids
        model_to_sdd(
            model_file, full_geometry, no_plenum, ceil_adjacency,
            osw_folder, geo_names, res_names, output_file)
    except Exception as e:
        _logger.exception('Model translation failed.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def model_to_sdd(
    model_file, full_geometry=False, no_plenum=False, ceil_adjacency=False,
    osw_folder=None, geometry_names=False, resource_names=False, output_file=None,
    multiplier=True, plenum=True, no_ceil_adjacency=True,
    geometry_ids=True, resource_ids=True
):
    """Translate a Dragonfly Model to a CBECC SDD file.

    Args:
        model_file: Path to either a DFJSON or DFpkl file. This can also be a
            HBJSON or a HBpkl from which a Dragonfly model should be derived.
        full_geometry: Boolean to note if the multipliers on each Building story
            will be passed along to the generated Honeybee Room objects or if
            full geometry objects should be written for each story in the
            building. (Default: False).
        no_plenum: Boolean to indicate whether ceiling/floor plenum depths
            assigned to Room2Ds should generate distinct 3D Rooms in the
            translation. (Default: False).
        ceil_adjacency: Boolean to indicate whether adjacencies should be solved
            between interior stories when Room2Ds perfectly match one another
            in their floor plate. This ensures that Surface boundary conditions
            are used instead of Adiabatic ones. Note that this input has no
            effect when the object-per-model is Story. (Default: False).
        osw_folder: Folder on this computer, into which the working files will
            be written. If None, it will be written into a temp folder in the
            default simulation folder.
        geometry_names: Boolean to note whether a cleaned version of all geometry
            display names should be used instead of identifiers when translating
            the Model to OSM and IDF. Using this flag will affect all Rooms, Faces,
            Apertures, Doors, and Shades. It will generally result in more read-able
            names in the OSM and IDF but this means that it will not be easy to map
            the EnergyPlus results back to the original Honeybee Model. Cases
            of duplicate IDs resulting from non-unique names will be resolved
            by adding integers to the ends of the new IDs that are derived from
            the name. (Default: False).
        resource_names: Boolean to note whether a cleaned version of all resource
            display names should be used instead of identifiers when translating
            the Model to OSM and IDF. Using this flag will affect all Materials,
            Constructions, ConstructionSets, Schedules, Loads, and ProgramTypes.
            It will generally result in more read-able names for the resources
            in the OSM and IDF. Cases of duplicate IDs resulting from non-unique
            names will be resolved by adding integers to the ends of the new IDs
            that are derived from the name. (Default: False).
        output_file: Optional SDD file to output the string of the translation.
            By default it will be returned from this method.
    """
    # set the default folder if it's not specified
    out_path = None
    out_directory = os.path.join(hb_folders.default_simulation_folder, 'temp_translate') \
        if osw_folder is None else osw_folder
    if output_file.endswith('-'):
        f_name = os.path.basename(model_file).lower()
        f_name = f_name.replace('.dfjson', '.xml').replace('.json', '.xml')
        f_name = f_name.replace('.dfplk', '.xml').replace('.pkl', '.xml')
        f_name = f_name.replace('.hbjson', '.xml').replace('.hbpkl', '.xml')
        out_path = os.path.join(out_directory, f_name)
    elif output_file.endswith('.gbxml'):  # avoid OpenStudio complaining about .gbxml
        f_name = os.path.basename(model_file).lower()
        f_name = f_name.replace('.gbxml', '.xml')
        out_path = os.path.join(out_directory, f_name)
    preparedir(out_directory)

    # re-serialize the Dragonfly Model
    model = Model.from_dfjson(model_file)
    model.convert_to_units('Meters')

    # convert Dragonfly Model to Honeybee
    multiplier = not full_geometry
    hb_models = model.to_honeybee(
        object_per_model='District', use_multiplier=multiplier,
        exclude_plenums=no_plenum, solve_ceiling_adjacencies=ceil_adjacency,
        enforce_adj=False)
    hb_model = hb_models[0]

    # create the dictionary of the HBJSON for input to OpenStudio CLI
    hb_model_json = _measure_compatible_model_json(
        hb_model, out_directory, simplify_window_cons=True,
        triangulate_sub_faces=True, use_geometry_names=geometry_names,
        use_resource_names=resource_names)

    # Write the osw file and translate the model to SDD
    out_f = out_path if output_file.endswith('-') else output_file
    osw = to_sdd_osw(hb_model_json, out_f, osw_folder)
    file_contents = _run_translation_osw(osw, out_path)

    # return the file contents if requested
    if file_contents is not None:
        if output_file is None:
            return file_contents
        else:
            print(file_contents)


def _run_translation_osw(osw, out_path):
    """Generic function used by all import methods that run OpenStudio CLI."""
    # run the measure to translate the model JSON to an openstudio measure
    _, idf = run_osw(osw, silent=True)
    if idf is not None and os.path.isfile(idf):
        if out_path is not None:  # load the JSON string to stdout
            with open(out_path) as json_file:
                print(json_file.read())
    else:
        _parse_os_cli_failure(os.path.dirname(osw))


def _measure_compatible_model_json(
        parsed_model, destination_directory, simplify_window_cons=False,
        triangulate_sub_faces=True, triangulate_non_planar_orphaned=False,
        use_geometry_names=False, use_resource_names=False):
    """Convert a Honeybee Model to a HBJSON compatible with the honeybee_openstudio_gem.

    Args:
        parsed_model: A honeybee Model object.
        destination_directory: The directory into which the Model JSON that is
            compatible with the honeybee_openstudio_gem should be written. If None,
            this will be the same location as the input model_json_path. (Default: None).
        simplify_window_cons: Boolean to note whether window constructions should
            be simplified during the translation. This is useful when the ultimate
            destination of the OSM is a format that does not supported layered
            window constructions (like gbXML). (Default: False).
        triangulate_sub_faces: Boolean to note whether sub-faces (including
            Apertures and Doors) should be triangulated if they have more than
            4 sides (True) or whether they should be left as they are (False).
            This triangulation is necessary when exporting directly to EnergyPlus
            since it cannot accept sub-faces with more than 4 vertices. (Default: True).
        triangulate_non_planar_orphaned: Boolean to note whether any non-planar
            orphaned geometry in the model should be triangulated upon export.
            This can be helpful because OpenStudio simply raises an error when
            it encounters non-planar geometry, which would hinder the ability
            to save gbXML files that are to be corrected in other
            software. (Default: False).
        enforce_rooms: Boolean to note whether this method should enforce the
            presence of Rooms in the Model, which is as necessary prerequisite
            for simulation in EnergyPlus. (Default: False).
        use_geometry_names: Boolean to note whether a cleaned version of all
            geometry display names should be used instead of identifiers when
            translating the Model to OSM and IDF. Using this flag will affect
            all Rooms, Faces, Apertures, Doors, and Shades. It will generally
            result in more read-able names in the OSM and IDF but this means
            that it will not be easy to map the EnergyPlus results back to the
            input Honeybee Model. Cases of duplicate IDs resulting from
            non-unique names will be resolved by adding integers to the ends
            of the new IDs that are derived from the name. (Default: False).
        use_resource_names: Boolean to note whether a cleaned version of all
            resource display names should be used instead of identifiers when
            translating the Model to OSM and IDF. Using this flag will affect
            all Materials, Constructions, ConstructionSets, Schedules, Loads,
            and ProgramTypes. It will generally result in more read-able names
            for the resources in the OSM and IDF. Cases of duplicate IDs
            resulting from non-unique names will be resolved by adding integers
            to the ends of the new IDs that are derived from the name. (Default: False).

    Returns:
        The full file path to the new Model JSON written out by this method.
    """
    # remove degenerate geometry within native E+ tolerance of 0.01 meters
    try:
        parsed_model.remove_degenerate_geometry(0.01)
    except ValueError as e:
        error = 'Failed to remove degenerate Rooms.\n{}'.format(e)
        raise ValueError(error)
    if triangulate_non_planar_orphaned:
        parsed_model.triangulate_non_planar_quads(0.01)

    # remove the HVAC from any Rooms lacking setpoints
    rem_msgs = parsed_model.properties.energy.remove_hvac_from_no_setpoints()
    if len(rem_msgs) != 0:
        print('\n'.join(rem_msgs))

    # reset the IDs to be derived from the display_names if requested
    if use_geometry_names:
        parsed_model.reset_ids()
    if use_resource_names:
        parsed_model.properties.energy.reset_resource_ids()

    # get the dictionary representation of the Model and add auto-calculated properties
    model_dict = parsed_model.to_dict(triangulate_sub_faces=triangulate_sub_faces)
    parsed_model.properties.energy.add_autocal_properties_to_dict(model_dict)
    if simplify_window_cons:
        parsed_model.properties.energy.simplify_window_constructions_in_dict(model_dict)

    # write the dictionary into a file
    dest_file_path = os.path.join(destination_directory, 'in.hbjson')
    preparedir(destination_directory, remove_content=False)  # create the directory
    with open(dest_file_path, 'w', encoding='utf-8') as fp:
        json.dump(model_dict, fp, ensure_ascii=False)

    return os.path.abspath(dest_file_path)
