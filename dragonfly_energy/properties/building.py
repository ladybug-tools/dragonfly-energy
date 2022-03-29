# coding=utf-8
"""Building Energy Properties."""
import os
import json

from honeybee_energy.config import folders
from honeybee_energy.programtype import ProgramType
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.hvac._base import _HVACSystem
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.hvac import HVAC_TYPES_DICT
from honeybee_energy.shw import SHWSystem

from honeybee_energy.lib.constructionsets import generic_construction_set, \
    construction_set_by_identifier
from honeybee_energy.lib.programtypes import building_program_type_by_identifier


class BuildingEnergyProperties(object):
    """Energy Properties for Dragonfly Building.

    Args:
        host: A dragonfly_core Building object that hosts these properties.
        construction_set: A honeybee ConstructionSet object to specify all
            default constructions for the Faces of the Building. If None, the
            Building will use the honeybee default construction set, which is not
            representative of a particular building code or climate zone.
            Default: None.

    Properties:
        * host
        * construction_set
    """
    _HVAC_REGISTRY = None
    _HVAC_TYPES_DICT = HVAC_TYPES_DICT
    _VINTAGE_MAP = {
        'DOE Ref Pre-1980': ('pre_1980', 'DOE_Ref_Pre_1980'),
        'DOE Ref 1980-2004': ('1980_2004', 'DOE_Ref_1980_2004'),
        '90.1-2004': ('2004', 'ASHRAE_2004'),
        '90.1-2007': ('2007', 'ASHRAE_2007'),
        '90.1-2010': ('2010', 'ASHRAE_2010'),
        '90.1-2013': ('2013', 'ASHRAE_2013'),
    }
    __slots__ = ('_host', '_construction_set')

    def __init__(self, host, construction_set=None):
        """Initialize Building energy properties."""
        self._host = host
        self.construction_set = construction_set

    @property
    def host(self):
        """Get the Building object hosting these properties."""
        return self._host

    @property
    def construction_set(self):
        """Get or set the Building ConstructionSet object.

        If not set, it will be the Honeybee default generic ConstructionSet.
        """
        if self._construction_set is not None:  # set by the user
            return self._construction_set
        else:
            return generic_construction_set

    @construction_set.setter
    def construction_set(self, value):
        if value is not None:
            assert isinstance(value, ConstructionSet), \
                'Expected ConstructionSet. Got {}'.format(type(value))
            value.lock()   # lock in case construction set has multiple references
        self._construction_set = value

    def averaged_program_type(self, identifier=None, timestep_resolution=1):
        """Get a ProgramType that is averaged across all of the children Room2Ds.

        The weights used in the averaging process are the floor area weights and they
        account for the multipliers on the child Story objects.

        Args:
            identifier: A unique ID text string for the new averaged ProgramType.
                Must be < 100 characters and not contain any EnergyPlus special
                characters. This will be used to identify the object across a model
                and in the exported IDF. If None, the resulting ProgramType will
                use the identifier of the host Building. (Default: None)
            timestep_resolution: An optional integer for the timestep resolution
                at which the schedules will be averaged. Any schedule details
                smaller than this timestep will be lost in the averaging process.
                Default: 1.
        """
        # get the default identifier of the ProgramType if None
        identifier = identifier if identifier is not None else \
            '{}_Program'.format(self.host.identifier)

        # compute the floor area weights and programs
        flr_areas = []
        program_types = []
        for story in self.host.unique_stories:
            for room in story.room_2ds:
                flr_areas.append(room.floor_area * story.multiplier)
                program_types.append(room.properties.energy.program_type)
        total_area = sum(flr_areas)
        weights = [room_area / total_area for room_area in flr_areas]

        # compute the averaged program
        return ProgramType.average(
            identifier, program_types, weights, timestep_resolution)

    def set_all_room_2d_program_type(self, program_type):
        """Set all of the children Room2Ds of this Building to have the same ProgramType.

        Args:
            program_type: A ProgramType to assign to all children Room2Ds.
        """
        assert isinstance(program_type, ProgramType), 'Expected ProgramType for ' \
            'Building set_all_room_2d_program_type. Got {}'.format(type(program_type))
        for room_2d in self.host.unique_room_2ds:
            room_2d.properties.energy.program_type = program_type

    def set_all_program_type_from_building_type(self, building_type):
        """Set the children Room2Ds to have a program mix from a building_type.

        Args:
            building_type: A text string for the type of building. This must appear
                under the BUILDING_TYPES contant of the honeybee_energy.lib.programtypes
                module to be successful.
        """
        program = building_program_type_by_identifier(building_type)
        self.set_all_room_2d_program_type(program)

    def set_all_room_2d_hvac(self, hvac, conditioned_only=True):
        """Set all children Room2Ds of this Building to have the same HVAC system.

        Args:
            hvac: An HVAC system with properties that will be assigned to all
                children Room2Ds.
            conditioned_only: Boolean to note whether the input hvac should only
                be applied to rooms that are already conditioned. If False, the
                hvac will be applied to all rooms. (Default: True).
        """
        assert isinstance(hvac, _HVACSystem), 'Expected HVACSystem for Building.' \
            'set_all_room_2d_hvac. Got {}'.format(type(hvac))

        new_hvac = hvac.duplicate()
        new_hvac._identifier = '{}_{}'.format(hvac.identifier, self.host.identifier)
        for room_2d in self.host.unique_room_2ds:
            if not conditioned_only or room_2d.properties.energy.is_conditioned:
                room_2d.properties.energy.hvac = new_hvac

    def add_default_ideal_air(self):
        """Add a default IdealAirSystem to all children Room2Ds of this Story.

        The identifier of the systems will be derived from the room identifiers.
        """
        for room_2d in self.host.unique_room_2ds:
            room_2d.properties.energy.add_default_ideal_air()

    def set_all_room_2d_shw(self, shw):
        """Set all children Room2Ds of this Building to have the same SHW system.

        Args:
            shw: A Service Hot Water (SHW) system with properties that will be
                assigned to all children Room2Ds.
        """
        assert isinstance(shw, SHWSystem), 'Expected SHWSystem for Building.' \
            'set_all_room_2d_shw. Got {}'.format(type(shw))

        new_shw = shw.duplicate()
        new_shw._identifier = '{}_{}'.format(shw.identifier, self.host.identifier)
        for room_2d in self.host.unique_room_2ds:
            room_2d.properties.energy.shw = new_shw

    def diversify(self, occupancy_stdev=20, lighting_stdev=20,
                  electric_equip_stdev=20, gas_equip_stdev=20, hot_water_stdev=20,
                  infiltration_stdev=20, schedule_offset=1, timestep=1):
        """Diversify the ProgramTypes assigned to this Building's Room2Ds.

        This method uses a random number generator and gaussian distribution to
        generate loads that vary about the original "mean" programs. Note that the
        randomly generated values can be set to something predictable by using the
        native Python random.seed() method before running this method.

        In addition to diversifying load values, approximately 2/3 of the schedules
        in the resulting Room2Ds will be offset from the mean by the input
        schedule_offset (1/3 ahead and another 1/3 behind).

        Args:
            occupancy_stdev: A number between 0 and 100 for the percent of the
                occupancy people_per_area representing one standard deviation
                of diversification from the mean. (Default 20 percent).
            lighting_stdev: A number between 0 and 100 for the percent of the
                lighting watts_per_area representing one standard deviation
                of diversification from the mean. (Default 20 percent).
            electric_equip_stdev: A number between 0 and 100 for the percent of the
                electric equipment watts_per_area representing one standard deviation
                of diversification from the mean. (Default 20 percent).
            gas_equip_stdev: A number between 0 and 100 for the percent of the
                gas equipment watts_per_area representing one standard deviation
                of diversification from the mean. (Default 20 percent).
            hot_water_stdev: A number between 0 and 100 for the percent of the
                service hot water flow_per_area representing one standard deviation
                of diversification from the mean. (Default 20 percent).
            infiltration_stdev: A number between 0 and 100 for the percent of the
                infiltration flow_per_exterior_area representing one standard deviation
                of diversification from the mean. (Default 20 percent).
            schedule_offset: A positive integer for the number of timesteps at which all
                schedules of the resulting programs will be shifted - roughly 1/3 of
                the programs ahead and another 1/3 behind. (Default: 1).
            timestep: An integer for the number of timesteps per hour at which the
                shifting is occurring. This must be a value between 1 and 60, which
                is evenly divisible by 60. 1 indicates that each step is an hour
                while 60 indicates that each step is a minute. (Default: 1).
        """
        # build a dictionary with the unique ProgramTypes and their assigned rooms
        program_dict = {}
        for room_2d in self.host.unique_room_2ds:
            p_type = room_2d.properties.energy.program_type
            try:  # see if we have already found the program
                program_dict[p_type.identifier][1].append(room_2d)
            except KeyError:  # this is the firs time encountering the program
                program_dict[p_type.identifier] = [p_type, [room_2d]]

        # loop through the dictionary and generate + assign diversified programs
        for prog_list in program_dict.values():
            prog, rooms = prog_list[0], prog_list[1]
            div_programs = prog.diversify(
                len(rooms), occupancy_stdev, lighting_stdev, electric_equip_stdev,
                gas_equip_stdev, hot_water_stdev, infiltration_stdev,
                schedule_offset, timestep)
            for room, d_prog in zip(rooms, div_programs):
                room.properties.energy.program_type = d_prog

    @classmethod
    def from_dict(cls, data, host):
        """Create BuildingEnergyProperties from a dictionary.

        Note that the dictionary must be a non-abridged version for this
        classmethod to work.

        Args:
            data: A dictionary representation of BuildingEnergyProperties.
            host: A Building object that hosts these properties.
        """
        assert data['type'] == 'BuildingEnergyProperties', \
            'Expected BuildingEnergyProperties. Got {}.'.format(data['type'])

        new_prop = cls(host)
        if 'construction_set' in data and data['construction_set'] is not None:
            new_prop.construction_set = \
                ConstructionSet.from_dict(data['construction_set'])

        return new_prop

    def apply_properties_from_dict(self, abridged_data, construction_sets):
        """Apply properties from a BuildingEnergyPropertiesAbridged dictionary.

        Args:
            abridged_data: A BuildingEnergyPropertiesAbridged dictionary (typically
                coming from a Model).
            construction_sets: A dictionary of ConstructionSets with identifiers
                of the sets as keys, which will be used to re-assign construction_sets.
        """
        if 'construction_set' in abridged_data and \
                abridged_data['construction_set'] is not None:
            self.construction_set = construction_sets[abridged_data['construction_set']]

    def to_dict(self, abridged=False):
        """Return Building energy properties as a dictionary.

        Args:
            abridged: Boolean for whether the full dictionary of the Building should
                be written (False) or just the identifier of the the individual
                properties (True). Default: False.
        """
        base = {'energy': {}}
        base['energy']['type'] = 'BuildingEnergyProperties' if not \
            abridged else 'BuildingEnergyPropertiesAbridged'

        # write the ConstructionSet into the dictionary
        if self._construction_set is not None:
            base['energy']['construction_set'] = \
                self._construction_set.identifier if abridged else \
                self._construction_set.to_dict()

        return base

    def apply_properties_from_geojson_dict(self, data):
        """Apply properties from a geoJSON dictionary.

        Args:
            data: A dictionary representation of a geoJSON feature properties.
                Specifically, this should be the "properties" key describing
                a Polygon or MultiPolygon object.
        """
        # determine the vintage of the building
        template = data['template'] if 'template' in data else '90.1-2013'
        vintage = self._VINTAGE_MAP[template]

        # assign the construction set based on climate zone
        if 'climate_zone' in data:
            zone_int = str(data['climate_zone'])[0]
            c_set_id = '{}::{}{}::SteelFramed'.format(
                vintage[0], 'ClimateZone', zone_int)
            try:
                self.construction_set = construction_set_by_identifier(c_set_id)
            except ValueError:  # not a construction set in the library
                pass

        # assign the program based on the building type
        if 'building_type' in data:
            try:
                self.set_all_program_type_from_building_type(data['building_type'])
            except ValueError:  # not a building type in the library
                pass

        # assign the HVAC based on the name
        if 'system_type' in data:
            hvac_instance = self._hvac_from_long_name(data['system_type'], vintage[1])
            if hvac_instance is not None:
                self.set_all_room_2d_hvac(hvac_instance, False)

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        new_host: A new Building object that hosts these properties.
            If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        return BuildingEnergyProperties(_host, self._construction_set)

    def _hvac_from_long_name(self, hvac_long_name, vintage='ASHRAE_2013'):
        """Get an HVAC class instance from it's long name (as found in a geoJSON)."""
        hvac_reg = None
        if BuildingEnergyProperties._HVAC_REGISTRY is None:
            ext_folder = [f for f in folders.standards_extension_folders
                          if f.endswith('honeybee_energy_standards')]
            if len(ext_folder) == 1:
                hvac_reg = os.path.join(ext_folder[0], 'hvac_registry.json')
                if os.path.isfile(hvac_reg):
                    with open(hvac_reg, 'r') as f:
                        BuildingEnergyProperties._HVAC_REGISTRY = json.load(f)
                        BuildingEnergyProperties._HVAC_REGISTRY['Ideal Air System'] = \
                            'IdealAirSystem'
                        hvac_reg = BuildingEnergyProperties._HVAC_REGISTRY
        if hvac_reg is not None:
            try:
                hvac_class = self._HVAC_TYPES_DICT[hvac_reg[hvac_long_name]]
            except KeyError:  # HVAC type is not in the library
                return None
            if hvac_class is IdealAirSystem:
                return IdealAirSystem('{} {}'.format(self.host.identifier, 'Ideal Air'))
            else:  # assume it is an HVAC template
                hvac_id = '{} {}'.format(self.host.identifier, hvac_reg[hvac_long_name])
                return hvac_class(hvac_id, vintage, hvac_reg[hvac_long_name])

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Building Energy Properties: {}'.format(self.host.identifier)
