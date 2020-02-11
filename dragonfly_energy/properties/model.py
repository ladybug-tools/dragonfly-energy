# coding=utf-8
"""Model Energy Properties."""
from dragonfly.extensionutil import model_extension_dicts

from honeybee_energy.lib.constructionsets import generic_construction_set

from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.construction.air import AirBoundaryConstruction
from honeybee_energy.programtype import ProgramType
import honeybee_energy.properties.model as hb_model_properties


try:
    from itertools import izip as zip  # python 2
except ImportError:
    pass   # python 3


class ModelEnergyProperties(object):
    """Energy Properties for Dragonfly Model.

    Args:
        host: A dragonfly_core Model object that hosts these properties.
        terrain_type: Text for the terrain type in which the model sits.
            Choose from: 'Ocean', 'Country', 'Suburbs', 'Urban', 'City'.
            Default: 'City'.

    Properties:
        * host
        * terrain_type
        * materials
        * constructions
        * shade_constructions
        * construction_sets
        * global_construction_set
        * schedule_type_limits
        * schedules
        * shade_schedules
        * program_type_schedules
        * hvac_schedules
        * program_types
    """
    TERRAIN_TYPES = hb_model_properties.ModelEnergyProperties.TERRAIN_TYPES

    def __init__(self, host, terrain_type='City'):
        """Initialize Model energy properties."""
        self._host = host
        self.terrain_type = terrain_type

    @property
    def host(self):
        """Get the Model object hosting these properties."""
        return self._host

    @property
    def terrain_type(self):
        """Get or set a text string for the terrain in which the model sits.

        This is used to determine the wind profile over the height of the
        building. Default is 'City'. Choose from the following options:

        * Ocean
        * Country
        * Suburbs
        * Urban
        * City
        """
        return self._terrain_type

    @terrain_type.setter
    def terrain_type(self, value):
        if value is not None:
            assert value in self.TERRAIN_TYPES, 'Input terrain_type "{}" is ' \
                'not valid. Choose from the following options:\n{}'.format(
                    value, self.TERRAIN_TYPES)
            self._terrain_type = value
        else:
            self._terrain_type = 'City'

    @property
    def materials(self):
        """List of all unique materials contained within the model.

        This includes materials across all Room2Ds, Stories, and Building
        ConstructionSets, and the global_construction_set.
        """
        materials = []
        for constr in self.constructions:
            try:
                materials.extend(constr.materials)
            except AttributeError:
                pass  # ShadeConstruction
        return list(set(materials))

    @property
    def constructions(self):
        """A list of all unique constructions in the model.

        This includes constructions across all Room2Ds, Stories, and Building
        ConstructionSets, and the global_construction_set.
        """
        bldg_constrs = []
        for cnstr_set in self.construction_sets:
            bldg_constrs.extend(cnstr_set.modified_constructions_unique)
        all_constrs = self.global_construction_set.constructions_unique + \
            bldg_constrs + self.shade_constructions
        return list(set(all_constrs))

    @property
    def shade_constructions(self):
        """A list of all unique constructions assigned to ContextShades in the model."""
        constructions = []
        for shade in self.host.context_shades:
            if shade.properties.energy.is_construction_set_by_user:
                if not self._instance_in_array(
                        shade.properties.energy.construction, constructions):
                    constructions.append(shade.properties.energy.construction)
        return list(set(constructions))

    @property
    def construction_sets(self):
        """A list of all unique Building-Assigned ConstructionSets in the Model.

        Note that this includes ConstructionSets assigned to individual Stories and
        Room2Ds in the Building.
        """
        construction_sets = []
        for bldg in self.host.buildings:
            self._check_and_add_obj_constr_set(bldg, construction_sets)
            for story in bldg.unique_stories:
                self._check_and_add_obj_constr_set(story, construction_sets)
                for room in story.room_2ds:
                    self._check_and_add_obj_constr_set(room, construction_sets)
        return list(set(construction_sets))  # catch equivalent construction sets

    @property
    def global_construction_set(self):
        """A default ConstructionSet object for all unassigned objects in the Model.

        This ConstructionSet will be written in its entirety to the dictionary
        representation of ModelEnergyProperties as well as the resulting OpenStudio
        model.  This is to ensure that all objects lacking a construction specification
        always have a default.
        """
        return generic_construction_set

    @property
    def schedule_type_limits(self):
        """List of all unique schedule type limits contained within the model.

        This includes schedules across all ContextShades and Room2Ds.
        """
        type_limits = []
        for sched in self.schedules:
            t_lim = sched.schedule_type_limit
            if t_lim is not None and not self._instance_in_array(t_lim, type_limits):
                type_limits.append(t_lim)
        return list(set(type_limits))

    @property
    def schedules(self):
        """A list of all unique schedules in the model.

        This includes schedules across all ProgramTypes and ContextShades.
        """
        all_scheds = self.hvac_schedules + self.program_type_schedules + \
            self.shade_schedules
        return list(set(all_scheds))

    @property
    def shade_schedules(self):
        """A list of all unique schedules assigned to ContextShades in the model.
        """
        schedules = []
        for shade in self.host._context_shades:
            self._check_and_add_shade_schedule(shade, schedules)
        return list(set(schedules))

    @property
    def program_type_schedules(self):
        """A list of all unique schedules assigned to ProgramTypes in the model."""
        schedules = []
        for p_type in self.program_types:
            for sched in p_type.schedules:
                self._check_and_add_schedule(sched, schedules)
        return list(set(schedules))

    @property
    def hvac_schedules(self):
        """A list of all unique HVAC-assigned schedules in the model."""
        schedules = []
        for hvac in self.hvacs:
            for sched in hvac.schedules:
                self._check_and_add_schedule(sched, schedules)
        return list(set(schedules))

    @property
    def program_types(self):
        """A list of all unique ProgramTypes in the Model."""
        program_types = []
        for bldg in self.host._buildings:
            for story in bldg:
                for room in story:
                    if room.properties.energy._program_type is not None:
                        if not self._instance_in_array(
                                room.properties.energy._program_type, program_types):
                            program_types.append(room.properties.energy._program_type)
        return list(set(program_types))  # catch equivalent program types

    @property
    def hvacs(self):
        """A list of all unique HVAC systems in the Model."""
        hvacs = []
        for bldg in self.host._buildings:
            for story in bldg:
                for room in story:
                    if room.properties.energy._hvac is not None:
                        if not self._instance_in_array(
                                room.properties.energy._hvac, hvacs):
                            hvacs.append(room.properties.energy._hvac)
        return hvacs

    def check_duplicate_construction_set_names(self, raise_exception=True):
        """Check that there are no duplicate ConstructionSet names in the model."""
        con_set_names = set()
        duplicate_names = set()
        for con_set in self.construction_sets + [self.global_construction_set]:
            if con_set.name not in con_set_names:
                con_set_names.add(con_set.name)
            else:
                duplicate_names.add(con_set.name)
        if len(duplicate_names) != 0:
            if raise_exception:
                raise ValueError(
                    'The model has the following duplicated ConstructionSet '
                    'names:\n{}'.format('\n'.join(duplicate_names)))
            return False
        return True

    def check_duplicate_program_type_names(self, raise_exception=True):
        """Check that there are no duplicate ProgramType names in the model."""
        p_type_names = set()
        duplicate_names = set()
        for p_type in self.program_types:
            if p_type.name not in p_type_names:
                p_type_names.add(p_type.name)
            else:
                duplicate_names.add(p_type.name)
        if len(duplicate_names) != 0:
            if raise_exception:
                raise ValueError(
                    'The model has the following duplicated ProgramType '
                    'names:\n{}'.format('\n'.join(duplicate_names)))
            return False
        return True

    def check_duplicate_hvac_names(self, raise_exception=True):
        """Check that there are no duplicate HVAC names in the model."""
        hvac_names = set()
        duplicate_names = set()
        for hvac in self.hvacs:
            if hvac.name not in hvac_names:
                hvac_names.add(hvac.name)
            else:
                duplicate_names.add(hvac.name)
        if len(duplicate_names) != 0:
            if raise_exception:
                raise ValueError(
                    'The model has the following duplicated HVAC system '
                    'names:\n{}'.format('\n'.join(duplicate_names)))
            return False
        return True

    def apply_properties_from_dict(self, data):
        """Apply the energy properties of a dictionary to the host Model of this object.

        Args:
            data: A dictionary representation of an entire honeybee-core Model.
                Note that this dictionary must have ModelEnergyProperties in order
                for this method to successfully apply the energy properties.
        """
        assert 'energy' in data['properties'], \
            'Dictionary possesses no ModelEnergyProperties.'

        # set the terrain
        if 'terrain_type' in data['properties']['energy']:
            self.terrain_type = data['properties']['energy']['terrain_type']

        materials, constructions, construction_sets, schedule_type_limits, \
            schedules, program_types, hvacs = \
            hb_model_properties.ModelEnergyProperties.load_properties_from_dict(data)

        # collect lists of energy property dictionaries
        building_e_dicts, story_e_dicts, room2d_e_dicts, context_e_dicts = \
            model_extension_dicts(data, 'energy', [], [], [], [])

        # apply energy properties to objects using the energy property dictionaries
        for bldg, b_dict in zip(self.host.buildings, building_e_dicts):
            bldg.properties.energy.apply_properties_from_dict(b_dict, construction_sets)
        for story, s_dict in zip(self.host.stories, story_e_dicts):
            story.properties.energy.apply_properties_from_dict(s_dict, construction_sets)
        for room, r_dict in zip(self.host.room_2ds, room2d_e_dicts):
            room.properties.energy.apply_properties_from_dict(
                r_dict, construction_sets, program_types, hvacs)
        for shade, s_dict in zip(self.host.context_shades, context_e_dicts):
            shade.properties.energy.apply_properties_from_dict(
                s_dict, constructions, schedules)

    def to_dict(self, include_global_construction_set=True):
        """Return Model energy properties as a dictionary.

        Args:
            include_global_construction_set: Boolean to note whether the
                global_construction_set should be included within the dictionary. This
                will ensure that all objects lacking a construction specification always
                have a default construction. Default: True.
        """
        base = {'energy': {'type': 'ModelEnergyProperties'}}

        # add the terrain
        base['energy']['terrain_type'] = self.terrain_type

        # add all materials, constructions and construction sets to the dictionary
        schs = self._add_constr_type_objs_to_dict(base, include_global_construction_set)

        # add all schedule type limits, schedules, and program types to the dictionary
        self._add_sched_type_objs_to_dict(base, schs)

        return base

    def to_honeybee(self, new_host):
        """Get a honeybee version of this object.

        Args:
            new_host: A honeybee-core Model object that will host these properties.
        """
        return hb_model_properties.ModelEnergyProperties(new_host, self.terrain_type)

    def duplicate(self, new_host=None):
        """Get a copy of this Model.

        Args:
            new_host: A new Model object that hosts these properties.
                If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        return ModelEnergyProperties(_host, self.terrain_type)

    def _add_constr_type_objs_to_dict(self, base, include_global_construction_set=True):
        """Add materials, constructions and construction sets to a base dictionary.

        Args:
            base: A base dictionary for a Dragonfly Model.
            include_global_construction_set: Boolean to note whether the
                global_construction_set should be included within the dictionary.
                This will ensure that all objects lacking a construction
                specification always have a default construction. Default: True.
        """
        # add all ConstructionSets to the dictionary
        base['energy']['construction_sets'] = []
        if include_global_construction_set:
            base['energy']['global_construction_set'] = self.global_construction_set.name
            base['energy']['construction_sets'].append(
                self.global_construction_set.to_dict(abridged=True,
                                                     none_for_defaults=False))
        construction_sets = self.construction_sets
        for cnstr_set in construction_sets:
            base['energy']['construction_sets'].append(cnstr_set.to_dict(abridged=True))

        # add all unique Constructions to the dictionary
        room_constrs = []
        for cnstr_set in construction_sets:
            room_constrs.extend(cnstr_set.modified_constructions_unique)
        all_constrs = room_constrs + self.shade_constructions
        if include_global_construction_set:
            all_constrs.extend(self.global_construction_set.constructions_unique)
        constructions = tuple(set(all_constrs))
        base['energy']['constructions'] = []
        for cnst in constructions:
            try:
                base['energy']['constructions'].append(cnst.to_dict(abridged=True))
            except TypeError:  # ShadeConstruction
                base['energy']['constructions'].append(cnst.to_dict())

        # add all unique Materials to the dictionary
        materials = []
        for cnstr in constructions:
            try:
                materials.extend(cnstr.materials)
            except AttributeError:
                pass  # ShadeConstruction
        base['energy']['materials'] = [mat.to_dict() for mat in set(materials)]

        # extract all of the schedules from the constructions
        schedules = []
        for constr in constructions:
            if isinstance(constr, AirBoundaryConstruction):
                self._check_and_add_schedule(constr.air_mixing_schedule, schedules)
        return schedules

    def _add_sched_type_objs_to_dict(self, base, schs):
        """Add schedule type limits, schedules, and program types to a base dictionary.

        Args:
            base: A base dictionary for a Dragonfly Model.
            schs: A list of additional schedules to be serialized to the
                base dictionary.
        """
        # add all unique hvacs to the dictionary
        hvacs = self.hvacs
        base['energy']['hvacs'] = []
        for hvac in hvacs:
            base['energy']['hvacs'].append(hvac.to_dict(abridged=True))

        # add all unique ProgramTypes to the dictionary
        program_types = self.program_types
        base['energy']['program_types'] = []
        for p_type in program_types:
            base['energy']['program_types'].append(p_type.to_dict(abridged=True))

        # add all unique Schedules to the dictionary
        p_type_scheds = []
        for p_type in program_types:
            for sched in p_type.schedules:
                self._check_and_add_schedule(sched, p_type_scheds)
        hvac_scheds = []
        for hvac in hvacs:
            for sched in hvac.schedules:
                self._check_and_add_schedule(sched, hvac_scheds)
        all_scheds = hvac_scheds + p_type_scheds + self.shade_schedules + schs
        schedules = tuple(set(all_scheds))
        base['energy']['schedules'] = []
        for sched in schedules:
            base['energy']['schedules'].append(sched.to_dict(abridged=True))

        # add all unique ScheduleTypeLimits to the dictionary
        type_limits = []
        for sched in schedules:
            t_lim = sched.schedule_type_limit
            if t_lim is not None and not self._instance_in_array(t_lim, type_limits):
                type_limits.append(t_lim)
        base['energy']['schedule_type_limits'] = \
            [s_typ.to_dict() for s_typ in set(type_limits)]

    def _check_and_add_obj_constr_set(self, obj, construction_sets):
        """Check if a construction set is assigned to an object and add it to a list."""
        c_set = obj.properties.energy._construction_set
        if c_set is not None:
            if not self._instance_in_array(c_set, construction_sets):
                construction_sets.append(c_set)

    def _check_and_add_shade_schedule(self, obj, schedules):
        """Check if a schedule is assigned to a shade and add it to a list."""
        sched = obj.properties.energy._transmittance_schedule
        if sched is not None:
            if not self._instance_in_array(sched, schedules):
                schedules.append(sched)

    def _check_and_add_schedule(self, sched, schedules):
        """Check if a schedule is in a list and add it if not."""
        if not self._instance_in_array(sched, schedules):
            schedules.append(sched)

    @staticmethod
    def _instance_in_array(object_instance, object_array):
        """Check if a specific object instance is already in an array.

        This can be much faster than  `if object_instance in object_arrary`
        when you expect to be testing a lot of the same instance of an object for
        inclusion in an array since the builtin method uses an == operator to
        test inclusion.
        """
        for val in object_array:
            if val is object_instance:
                return True
        return False

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Model Energy Properties:\n host: {}'.format(self.host.name)
