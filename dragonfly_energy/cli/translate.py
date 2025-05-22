"""dragonfly energy translation commands."""
import click
import sys
import os
import logging
import json
import tempfile

from ladybug.commandutil import process_content_to_output
from ladybug.epw import EPW
from ladybug.stat import STAT
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.run import HB_OS_MSG
from honeybee_energy.writer import energyplus_idf_version, _preprocess_model_for_trace
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
@click.option('--folder', '-f', help='Deprecated input that is no longer used.',
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
        folder: Deprecated input that is no longer used.
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
    # check that honeybee-openstudio is installed
    try:
        from honeybee_openstudio.openstudio import openstudio, OSModel
        from honeybee_openstudio.simulation import simulation_parameter_to_openstudio, \
            assign_epw_to_model
        from honeybee_openstudio.writer import model_to_openstudio
    except ImportError as e:  # honeybee-openstudio is not installed
        raise ImportError('{}\n{}'.format(HB_OS_MSG, e))
    if folder is not None:
        print('--folder is deprecated and no longer used.')

    # initialize the OpenStudio model that will hold everything
    os_model = OSModel()
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

    if epw_file is not None:
        epw_folder, epw_file_name = os.path.split(epw_file)
        ddy_file = os.path.join(epw_folder, epw_file_name.replace('.epw', '.ddy'))
        stat_file = os.path.join(epw_folder, epw_file_name.replace('.epw', '.stat'))
        if len(sim_par.sizing_parameter.design_days) == 0 and \
                os.path.isfile(ddy_file):
            try:
                sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
            except AssertionError:  # no design days within the DDY file
                ddy_from_epw(epw_file, sim_par)
        elif len(sim_par.sizing_parameter.design_days) == 0:
            ddy_from_epw(epw_file, sim_par)
        if sim_par.sizing_parameter.climate_zone is None and os.path.isfile(stat_file):
            stat_obj = STAT(stat_file)
            sim_par.sizing_parameter.climate_zone = stat_obj.ashrae_climate_zone
        set_cz = True if sim_par.sizing_parameter.climate_zone is None else False
        assign_epw_to_model(epw_file, os_model, set_cz)

    # translate the simulation parameter and model to an OpenStudio Model
    simulation_parameter_to_openstudio(sim_par, os_model)

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
    model_to_openstudio(
        hb_model, os_model, use_geometry_names=geometry_names,
        use_resource_names=resource_names, print_progress=True)
    gen_files = []

    # write the OpenStudio Model if specified
    if osm_file is not None:
        osm = os.path.abspath(osm_file)
        os_model.save(osm, overwrite=True)
        gen_files.append(osm)

    # write the IDF if specified
    if idf_file is not None:
        idf = os.path.abspath(idf_file)
        idf_translator = openstudio.energyplus.ForwardTranslator()
        workspace = idf_translator.translateModel(os_model)
        workspace.save(idf, overwrite=True)
        gen_files.append(idf)

    return process_content_to_output(json.dumps(gen_files, indent=4), log_file)


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
@click.option('--osw-folder', '-osw', help='Deprecated input that is no longer used.',
              default=None,
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
        osw_folder: Deprecated input that is no longer used.
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
    # check that honeybee-openstudio is installed
    try:
        from honeybee_openstudio.writer import model_to_gbxml
    except ImportError as e:  # honeybee-openstudio is not installed
        raise ImportError('{}\n{}'.format(HB_OS_MSG, e))
    if osw_folder is not None:
        print('--osw-folder is deprecated and no longer used.')

    # re-serialize the Dragonfly Model
    model = Model.from_dfjson(model_file)
    model.convert_to_units('Meters')
    model.tolerance = 0.01  # ensure roof calculation happens at E+ native tolerance

    # convert Dragonfly Model to Honeybee
    multiplier = not full_geometry
    hb_models = model.to_honeybee(
        object_per_model='District', use_multiplier=multiplier,
        exclude_plenums=no_plenum, solve_ceiling_adjacencies=ceil_adjacency,
        enforce_adj=False)
    hb_model = hb_models[0]

    # translate the model to a gbXML string
    gbxml_str = model_to_gbxml(
        hb_model, triangulate_non_planar_orphaned=triangulate_non_planar,
        triangulate_subfaces=triangulate_subfaces, full_geometry=complete_geometry,
        interior_face_type=interior_face_type, ground_face_type=ground_face_type
    )

    # write out the gbXML file
    return process_content_to_output(gbxml_str, output_file)


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
@click.option('--single-window/--detailed-windows', ' /-dw', help='Flag to note '
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
@click.option('--osw-folder', '-osw', help='Deprecated input that is no longer used.',
              default=None,
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
        osw_folder: Deprecated input that is no longer used.
        output_file: Optional gbXML file to output the string of the translation.
            By default it will be returned from this method.
    """
    # check that honeybee-openstudio is installed
    try:
        from honeybee_openstudio.writer import model_to_gbxml
    except ImportError as e:  # honeybee-openstudio is not installed
        raise ImportError('{}\n{}'.format(HB_OS_MSG, e))
    if osw_folder is not None:
        print('--osw-folder is deprecated and no longer used.')

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

    # translate the honeybee model to a TRACE-compatible gbXML string
    single_window = not detailed_windows
    hb_model = _preprocess_model_for_trace(
        hb_model, single_window=single_window, rect_sub_distance=rect_sub_distance,
        frame_merge_distance=frame_merge_distance)
    gbxml_str = model_to_gbxml(hb_model)

    # write out the gbXML file
    return process_content_to_output(gbxml_str, output_file)


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
@click.option('--osw-folder', '-osw', help='Deprecated input that is no longer used.',
              default=None,
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
        osw_folder: Deprecated input that is no longer used.
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
    # check that honeybee-openstudio is installed
    try:
        from honeybee_openstudio.openstudio import openstudio
        from honeybee_openstudio.writer import model_to_openstudio
    except ImportError as e:  # honeybee-openstudio is not installed
        raise ImportError('{}\n{}'.format(HB_OS_MSG, e))
    if osw_folder is not None:
        print('--folder is deprecated and no longer used.')

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

    # convert the Honeybee model to an OpenStudio Model
    os_model = model_to_openstudio(hb_model, use_simple_window_constructions=True)

    # write the SDD
    out_path = None
    if output_file is None or output_file.endswith('-'):
        out_directory = tempfile.gettempdir()
        f_name = os.path.basename(model_file).lower()
        f_name = f_name.replace('.hbjson', '.xml').replace('.json', '.xml')
        out_path = os.path.join(out_directory, f_name)
    sdd = os.path.abspath(output_file) if out_path is None else out_path
    sdd_translator = openstudio.sdd.SddForwardTranslator()
    sdd_translator.modelToSDD(os_model, sdd)

    # return the file contents if requested
    if out_path is not None:
        with open(sdd, 'r') as sdf:
            file_contents = sdf.read()
        if output_file is None:
            return file_contents
        else:
            print(file_contents)
