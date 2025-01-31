# coding=utf-8
"""Building Energy Properties."""
import os
import json

from ladybug.header import Header
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.datatype.power import Power
from ladybug.datatype.time import Time

from honeybee_energy.config import folders
from honeybee_energy.programtype import ProgramType
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.hvac._base import _HVACSystem
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.hvac import HVAC_TYPES_DICT
from honeybee_energy.shw import SHWSystem
from honeybee_energy.lib.constructions import ceiling_plenum_bottom, floor_plenum_top
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
        * ceiling_plenum_construction
        * floor_plenum_construction
        * des_cooling_load
        * des_heating_load
        * des_hot_water_load
        * has_des_loads
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
        '90.1-2016': ('2016', 'ASHRAE_2016'),
        '90.1-2019': ('2019', 'ASHRAE_2019')
    }
    __slots__ = (
        '_host', '_construction_set',
        '_ceiling_plenum_construction', '_floor_plenum_construction',
        '_des_cooling_load', '_des_heating_load', '_des_hot_water_load'
    )

    def __init__(self, host, construction_set=None):
        """Initialize Building energy properties."""
        self._host = host
        self.construction_set = construction_set
        self._ceiling_plenum_construction = None  # can be set later
        self._floor_plenum_construction = None  # can be set later
        self._des_cooling_load = None  # can be set later
        self._des_heating_load = None  # can be set later
        self._des_hot_water_load = None  # can be set later

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

    @property
    def ceiling_plenum_construction(self):
        """Get or set an opaque construction for the bottoms of ceiling plenums.

        Materials should be ordered from the plenum side to the room side.
        By default, this is a simple acoustic tile construction.
        """
        if self._ceiling_plenum_construction:  # set by user
            return self._ceiling_plenum_construction
        return ceiling_plenum_bottom

    @ceiling_plenum_construction.setter
    def ceiling_plenum_construction(self, value):
        if value is not None:
            assert isinstance(value, OpaqueConstruction), \
                'Expected Opaque Construction for ceiling_plenum_construction. ' \
                'Got {}'.format(type(value))
            value.lock()  # lock editing in case construction has multiple references
        self._ceiling_plenum_construction = value

    @property
    def floor_plenum_construction(self):
        """Get or set an opaque construction for the tops of floor plenums.

        Materials should be ordered from the plenum side to the room side.
        By default, this is a simple wood plank construction.
        """
        if self._floor_plenum_construction:  # set by user
            return self._floor_plenum_construction
        return floor_plenum_top

    @floor_plenum_construction.setter
    def floor_plenum_construction(self, value):
        if value is not None:
            assert isinstance(value, OpaqueConstruction), \
                'Expected Opaque Construction for floor_plenum_construction. ' \
                'Got {}'.format(type(value))
            value.lock()  # lock editing in case construction has multiple references
        self._floor_plenum_construction = value

    @property
    def des_cooling_load(self):
        """Get or set an optional data collection for building cooling loads for a DES.

        Note that any data collection input here must be an HourlyContinuousCollection,
        it must be annual, and it must have a data type of Power in Watts.
        """
        return self._des_cooling_load

    @des_cooling_load.setter
    def des_cooling_load(self, value):
        if value is not None:
            value = self._check_data_coll(value, 'DES Cooling')
        self._des_cooling_load = value

    @property
    def des_heating_load(self):
        """Get or set an optional data collection for building heating loads for a DES.

        Note that any data collection input here must be an HourlyContinuousCollection,
        it must be annual, and it must have a data type of Power in Watts.
        """
        return self._des_heating_load

    @des_heating_load.setter
    def des_heating_load(self, value):
        if value is not None:
            value = self._check_data_coll(value, 'DES Heating')
        self._des_heating_load = value

    @property
    def des_hot_water_load(self):
        """Get or set an optional data collection for building hot water loads for a DES.

        Note that any data collection input here must be an HourlyContinuousCollection,
        it must be annual, and it must have a data type of Power in Watts.
        """
        return self._des_hot_water_load

    @des_hot_water_load.setter
    def des_hot_water_load(self, value):
        if value is not None:
            value = self._check_data_coll(value, 'DES Hot Water')
        self._des_hot_water_load = value

    @property
    def has_des_loads(self):
        """Get a boolean for whether this Building has DES loads assigned to it."""
        return self._des_cooling_load is not None or self._des_heating_load is not None \
            or self._des_hot_water_load is not None

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
                under the BUILDING_TYPES constant of the honeybee_energy.lib.programtypes
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

    def make_plenums(self, room_ids, conditioned=False, remove_infiltration=False):
        """Turn Room2Ds on this host Building into plenums with no internal loads.

        This includes removing all people, lighting, equipment, hot water, and
        mechanical ventilation. By default, the heating/cooling system and
        setpoints will also be removed but they can optionally be kept. Infiltration
        is kept by default but can optionally be removed as well.

        This is useful to appropriately assign properties for closets,
        underfloor spaces, and drop ceilings.

        Args:
            room_ids: A list of identifiers for Room2Ds on this Building to be
                converted into plenums.
            conditioned: Boolean to indicate whether the plenums are conditioned with
                heating/cooling systems. If True, the setpoints of the Room will also
                be kept in addition to the heating/cooling system (Default: False).
            remove_infiltration: Boolean to indicate whether infiltration should be
                removed from the Rooms. (Default: False).
        """
        # set up variables to be used in plenum property assignment
        room_ids = set(room_ids)
        plenum_programs = {}
        # loop through the Room2Ds and split the plenum if they're selected
        for rm in self.host.unique_room_2ds:
            if rm.identifier in room_ids:
                rm_props = rm.properties.energy
                # remove or add the HVAC system as needed
                if conditioned and not rm_props.is_conditioned:
                    rm.add_default_ideal_air()
                elif not conditioned:
                    rm_props.hvac = None
                rm_props._shw = None
                # remove process loads and operable windows
                rm_props._process_loads = []
                rm_props._window_vent_control = None
                rm_props._window_vent_opening = None
                # remove the loads and reapply infiltration/setpoints as needed
                infiltration = None if remove_infiltration or \
                    rm_props.program_type is None else rm_props.program_type.infiltration
                setpoint = None if not conditioned or rm_props.program_type is None \
                    else rm_props.program_type.infiltration
                if infiltration is None and setpoint is None:
                    rm_props.program_type = None
                else:
                    pln_prog_id = '{} Plenum'.format(rm_props.program_type.identifier)
                    try:  # see if we already have a program created
                        pln_prog = plenum_programs[pln_prog_id]
                    except KeyError:  # create a new plenum program type
                        pln_prog = ProgramType(pln_prog_id, infiltration=infiltration,
                                               setpoint=setpoint)
                        plenum_programs[pln_prog_id] = pln_prog
                    rm_props.program_type = pln_prog

    def apply_ceiling_plenum_face_properties(self, room_faces, plenum_faces):
        """Apply the ceiling_plenum_construction to Honeybee Faces.

        Args:
            room_faces: A list of Honeybee Faces for the occupied Rooms that
                interface with ceiling plenums.
            plenum_faces: A list of Honeybee Faces for the ceiling plenum Rooms
                that interface with the occupied Rooms.
        """
        self._apply_plenum_face_properties(
            self.ceiling_plenum_construction, room_faces, plenum_faces)

    def apply_floor_plenum_face_properties(self, room_faces, plenum_faces):
        """Apply the floor_plenum_construction to Honeybee Faces.

        Args:
            room_faces: A list of Honeybee Faces for the occupied Rooms that
                interface with floor plenums.
            plenum_faces: A list of Honeybee Faces for the floor plenum Rooms
                that interface with the occupied Rooms.
        """
        self._apply_plenum_face_properties(
            self.floor_plenum_construction, room_faces, plenum_faces)

    @staticmethod
    def _apply_plenum_face_properties(room_con, room_faces, plenum_faces):
        """Base function for applying plenum constructions"""
        plenum_con = room_con if room_con.is_symmetric else \
            OpaqueConstruction('{} Rev'.format(room_con.identifier),
                               tuple(reversed(room_con.materials)))
        for r_face in room_faces:
            r_face.properties.energy.construction = room_con
        for p_face in plenum_faces:
            p_face.properties.energy.construction = plenum_con

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
        if 'ceiling_plenum_construction' in data and \
                data['ceiling_plenum_construction'] is not None:
            new_prop.ceiling_plenum_construction = \
                OpaqueConstruction.from_dict(data['ceiling_plenum_construction'])
        if 'floor_plenum_construction' in data and \
                data['floor_plenum_construction'] is not None:
            new_prop.ceiling_plenum_construction = \
                OpaqueConstruction.from_dict(data['floor_plenum_construction'])
        if 'des_cooling_load' in data and data['des_cooling_load'] is not None:
            new_prop.des_cooling_load = \
                HourlyContinuousCollection.from_dict(data['des_cooling_load'])
        if 'des_heating_load' in data and data['des_heating_load'] is not None:
            new_prop.des_heating_load = \
                HourlyContinuousCollection.from_dict(data['des_heating_load'])
        if 'des_hot_water_load' in data and data['des_hot_water_load'] is not None:
            new_prop.des_heating_load = \
                HourlyContinuousCollection.from_dict(data['des_hot_water_load'])
        return new_prop

    def apply_properties_from_dict(self, abridged_data, construction_sets, constructions):
        """Apply properties from a BuildingEnergyPropertiesAbridged dictionary.

        Args:
            abridged_data: A BuildingEnergyPropertiesAbridged dictionary (typically
                coming from a Model).
            construction_sets: A dictionary of ConstructionSets with identifiers
                of the sets as keys, which will be used to re-assign construction_sets.
            constructions: A dictionary with construction identifiers as keys
                and honeybee construction objects as values.
        """
        if 'construction_set' in abridged_data and \
                abridged_data['construction_set'] is not None:
            self.construction_set = construction_sets[abridged_data['construction_set']]
        if 'ceiling_plenum_construction' in abridged_data and \
                abridged_data['ceiling_plenum_construction'] is not None:
            self.ceiling_plenum_construction = \
                constructions[abridged_data['ceiling_plenum_construction']]
        if 'floor_plenum_construction' in abridged_data and \
                abridged_data['floor_plenum_construction'] is not None:
            self.floor_plenum_construction = \
                constructions[abridged_data['floor_plenum_construction']]
        if 'des_cooling_load' in abridged_data and \
                abridged_data['des_cooling_load'] is not None:
            self.des_cooling_load = \
                HourlyContinuousCollection.from_dict(abridged_data['des_cooling_load'])
        if 'des_heating_load' in abridged_data and \
                abridged_data['des_heating_load'] is not None:
            self.des_heating_load = \
                HourlyContinuousCollection.from_dict(abridged_data['des_heating_load'])
        if 'des_hot_water_load' in abridged_data and \
                abridged_data['des_hot_water_load'] is not None:
            self.des_heating_load = \
                HourlyContinuousCollection.from_dict(abridged_data['des_hot_water_load'])

    def apply_properties_from_geojson_dict(self, data):
        """Apply properties from a geoJSON dictionary.

        Args:
            data: A dictionary representation of a geoJSON feature properties.
                Specifically, this should be the "properties" key describing
                a Polygon or MultiPolygon object.
        """
        # determine the vintage of the building
        template = data['template'] if 'template' in data else '90.1-2019'
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

        # write the properties into the dictionary
        if self._construction_set is not None:
            base['energy']['construction_set'] = \
                self._construction_set.identifier if abridged else \
                self._construction_set.to_dict()
        if self._ceiling_plenum_construction is not None:
            base['energy']['ceiling_plenum_construction'] = \
                self._ceiling_plenum_construction.identifier if abridged else \
                self._ceiling_plenum_construction.to_dict()
        if self._floor_plenum_construction is not None:
            base['energy']['floor_plenum_construction'] = \
                self._floor_plenum_construction.identifier if abridged else \
                self._floor_plenum_construction.to_dict()
        if self._des_cooling_load is not None:
            base['energy']['des_cooling_load'] = self._des_cooling_load.to_dict()
        if self._des_heating_load is not None:
            base['energy']['des_heating_load'] = self._des_heating_load.to_dict()
        if self._des_hot_water_load is not None:
            base['energy']['des_hot_water_load'] = self._des_hot_water_load.to_dict()

        return base

    def to_building_load_csv(self):
        """Get a CSV file string of building loads for DES simulation."""
        time_col, cool, heat, water = self._building_loads()
        total = cool + heat
        header = (
            'SecondsFromStart',
            'TotalSensibleLoad',
            'TotalCoolingSensibleLoad',
            'TotalHeatingSensibleLoad',
            'TotalWaterHeating'
        )
        file_lines = [','.join(header)]
        for s, t, c, h, hw in zip(time_col, total, cool, heat, water):
            text_vals = [str(v) for v in (s, t, c, h, hw)]
            file_lines.append(','.join(text_vals))
        return '\n'.join(file_lines)

    def to_building_load_json(self):
        """Get a JSON file string of peak loads for DES simulation."""
        _, cool, heat, water = self._building_loads()
        peak_dict = {
            'ExportModelicaLoads': 
            {
                'applicable': True,
                'energyplus_runtime': 1,
                'peak_cooling_load': cool.min,
                'peak_heating_load': heat.max,
                'peak_water_heating': water.max
            }
        }
        return json.dumps(peak_dict, indent=4)

    def to_building_load_mos(self):
        """Get a MOS file string of building loads for DES simulation."""
        time_col, cool, heat, water = self._building_loads()
        file_lines = [
            '#1',
            '#Exported loads from Dragonfly',
            '\n',
            '#First column: Seconds in the year (loads are hourly)',
            '#Second column: cooling loads in Watts (as negative numbers).',
            '#Third column: space heating loads in Watts',
            '#Fourth column: water heating loads in Watts',
            '\n'
        ]
        file_lines.append('#Peak space cooling load = {} Watts'.format(cool.min))
        file_lines.append('#Peak space heating load = {} Watts'.format(heat.max))
        file_lines.append('#Peak water heating load = {} Watts'.format(water.max))
        file_lines.append('double tab1({},4)'.format(len(time_col)))
        for s, c, h, hw in zip(time_col, cool, heat, water):
            text_vals = [str(v) for v in (s, c, h, hw)]
            file_lines.append(';'.join(text_vals))
        return '\n'.join(file_lines)

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        new_host: A new Building object that hosts these properties.
            If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        new_prop = BuildingEnergyProperties(_host, self._construction_set)
        new_prop._ceiling_plenum_construction = self._ceiling_plenum_construction
        new_prop._floor_plenum_construction = self._floor_plenum_construction
        new_prop._des_cooling_load = self._des_cooling_load
        new_prop._des_heating_load = self._des_heating_load
        new_prop._des_hot_water_load = self._des_hot_water_load
        return new_prop

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

    def _building_loads(self):
        """Get data collections for cooling, heating, and hot water."""
        assert self.has_des_loads, 'Building "{}" has no building loads assigned ' \
            'to it for DES simulation.'.format(self.host.display_name)
        base_col = self._base_load_collection()
        a_per = base_col.header.analysis_period
        def_vals = [0] * len(base_col)
        def_col = HourlyContinuousCollection(Header(Power(), 'W', a_per), def_vals)
        cool = self._des_cooling_load if self._des_cooling_load is not None else def_col
        heat = self._des_heating_load if self._des_heating_load is not None else def_col
        water = self._des_hot_water_load \
            if self._des_hot_water_load is not None else def_col
        # negate cooling as DES simulation needs it that way
        cool = cool.duplicate()
        neg_cool_vals = []
        for val in cool.values:
            v = -val if val != 0 else val
            neg_cool_vals.append(v)
        cool.values = neg_cool_vals
        # make a collection for time in seconds
        sec_step = int(3600.0 / a_per.timestep)
        time_vals = list(range(sec_step, sec_step * (len(base_col) + 1), sec_step))
        time_col = HourlyContinuousCollection(Header(Time(), 'sec', a_per), time_vals)
        return time_col, cool, heat, water

    def _base_load_collection(self):
        """Get a data collection to serve as the basis for writing DES loads."""
        if self._des_cooling_load is not None:
            return self._des_cooling_load
        if self._des_heating_load is not None:
            return self._des_heating_load
        if self._des_heating_load is not None:
            return self._des_hot_water_load

    @staticmethod
    def _check_data_coll(value, name):
        """Check the data type and units of a Data Collection."""
        assert isinstance(value, HourlyContinuousCollection), 'Expected ' \
            'HourlyContinuousCollection for {}. Got {}'.format(name, type(value))
        assert value.header.analysis_period.is_annual, '{} data analysis period ' \
            'is not annual. {}'.format(name, value.header.analysis_period)
        assert isinstance(value.header.data_type, Power), '{} must be Power in W. ' \
            'Got {} in {}'.format(name, value.header.data_type.name, value.header.unit)
        if value.header.unit != 'W':
            value = value.to_unit('W')
        return value

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Building Energy Properties: {}'.format(self.host.identifier)
