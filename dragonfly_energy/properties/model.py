# coding=utf-8
"""Model Energy Properties."""
try:
    from itertools import izip as zip  # python 2
except ImportError:
    pass   # python 3

from honeybee.extensionutil import room_extension_dicts
from honeybee_energy.construction.windowshade import WindowConstructionShade
from honeybee_energy.construction.dynamic import WindowConstructionDynamic
from honeybee_energy.construction.air import AirBoundaryConstruction
import honeybee_energy.properties.model as hb_model_properties
from honeybee_energy.lib.constructions import generic_context
from honeybee_energy.lib.constructionsets import generic_construction_set
from honeybee.checkdup import check_duplicate_identifiers

from dragonfly.extensionutil import model_extension_dicts


class ModelEnergyProperties(object):
    """Energy Properties for Dragonfly Model.

    Args:
        host: A dragonfly_core Model object that hosts these properties.

    Properties:
        * host
        * materials
        * constructions
        * face_constructions
        * shade_constructions
        * construction_sets
        * global_construction_set
        * schedule_type_limits
        * schedules
        * construction_schedules
        * shade_schedules
        * program_type_schedules
        * hvac_schedules
        * misc_room_schedules
        * program_types
        * hvacs
        * shws
    """

    def __init__(self, host):
        """Initialize Model energy properties."""
        self._host = host

    @property
    def host(self):
        """Get the Model object hosting these properties."""
        return self._host

    @property
    def materials(self):
        """Get a list of all unique materials contained within the model.

        This includes materials across all Room2Ds, Stories, and Building
        ConstructionSets but it does NOT include the Honeybee generic default
        construction set.
        """
        materials = []
        for constr in self.constructions:
            try:
                materials.extend(constr.materials)
                if constr.has_frame:
                    materials.append(constr.frame)
                if isinstance(constr, WindowConstructionShade):
                    if constr.is_switchable_glazing:
                        materials.append(constr.switched_glass_material)
                    if constr.shade_location == 'Between':
                        materials.append(constr.window_construction.materials[-2])
            except AttributeError:
                pass  # ShadeConstruction
        return list(set(materials))

    @property
    def constructions(self):
        """Get a list of all unique constructions in the model.

        This includes materials across all Room2Ds, Stories, and Building
        ConstructionSets but it does NOT include the Honeybee generic default
        construction set.
        """
        bldg_constrs = []
        for cnstr_set in self.construction_sets:
            bldg_constrs.extend(cnstr_set.modified_constructions_unique)
        all_constrs = bldg_constrs + self.face_constructions + self.shade_constructions
        return list(set(all_constrs))

    @property
    def face_constructions(self):
        """Get a list of all unique constructions assigned to Faces, Apertures and Doors.

        These objects only exist under the Building.room_3ds property
        """
        constructions = []
        for bldg in self.host.buildings:
            for face in bldg.room_3d_faces:
                self._check_and_add_obj_construction(face, constructions)
                for ap in face.apertures:
                    self._check_and_add_obj_construction(ap, constructions)
                for dr in face.doors:
                    self._check_and_add_obj_construction(dr, constructions)
        return list(set(constructions))

    @property
    def shade_constructions(self):
        """Get a list of all unique constructions assigned to ContextShades in the model.

        This will also include any Shade objects assigned to the 3D Honeybee Rooms
        of any Model Buildings.
        """
        constructions = []
        for shade in self.host.context_shades:
            self._check_and_add_obj_construction(shade, constructions)
        for bldg in self.host.buildings:
            for shd in bldg.room_3d_shades:
                self._check_and_add_obj_construction(shd, constructions)
        return list(set(constructions))

    @property
    def construction_sets(self):
        """Get a list of all unique ConstructionSets in the Model.

        Note that this includes ConstructionSets assigned to individual Stories,
        Room2Ds and 3D Honeybee Rooms in the Model's Buildings.
        """
        construction_sets = []
        for bldg in self.host.buildings:
            self._check_and_add_obj_constr_set(bldg, construction_sets)
            for story in bldg.unique_stories:
                self._check_and_add_obj_constr_set(story, construction_sets)
                for room in story.room_2ds:
                    self._check_and_add_obj_constr_set(room, construction_sets)
            for room in bldg.room_3ds:
                self._check_and_add_obj_constr_set(room, construction_sets)
        return list(set(construction_sets))  # catch equivalent construction sets

    @property
    def global_construction_set(self):
        """The global energy construction set.

        This is what is used whenever there is no construction_set assigned to a
        Room2D, a parent Story, or a parent Building.
        """
        return generic_construction_set

    @property
    def schedule_type_limits(self):
        """Get a list of all unique schedule type limits contained within the model.

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
        """Get a list of all unique schedules in the model.

        This includes schedules across all ProgramTypes and ContextShades.
        """
        all_scheds = self.hvac_schedules + self.program_type_schedules + \
            self.misc_room_schedules + self.shade_schedules + self.construction_schedules
        return list(set(all_scheds))

    @property
    def construction_schedules(self):
        """Get a list of all unique schedules assigned to constructions in the model.

        This includes schedules on al AirBoundaryConstructions, WindowConstructionShade,
        and WindowConstructionDynamic.
        """
        schedules = []
        for constr in self.constructions:
            if isinstance(constr, AirBoundaryConstruction):
                self._check_and_add_schedule(constr.air_mixing_schedule, schedules)
            elif isinstance(constr, WindowConstructionShade):
                if constr.schedule is not None:
                    self._check_and_add_schedule(constr.schedule, schedules)
            elif isinstance(constr, WindowConstructionDynamic):
                self._check_and_add_schedule(constr.schedule, schedules)
        return list(set(schedules))

    @property
    def shade_schedules(self):
        """Get a list of all unique schedules assigned to ContextShades in the model.
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
        """Get a list of all unique HVAC-assigned schedules in the model."""
        schedules = []
        for hvac in self.hvacs:
            for sched in hvac.schedules:
                self._check_and_add_schedule(sched, schedules)
        return list(set(schedules))

    @property
    def misc_room_schedules(self):
        """Get a list of all unique schedules assigned directly to Rooms in the model.

        This includes schedules for process loads and window ventilation control
        that are assigned to Room2Ds. It also includes any schedules assigned directly
        to 3D Honeybee Rooms of the model (not through the room program).

        Note that this does not include schedules from ProgramTypes assigned to the
        rooms. For this, use the program_type_schedules property.
        """
        scheds = []
        for bldg in self.host._buildings:
            for story in bldg:
                for room in story:
                    window_vent = room.properties.energy._window_vent_control
                    processes = room.properties.energy._process_loads
                    if window_vent is not None:
                        self._check_and_add_schedule(window_vent.schedule, scheds)
                    if len(processes) != 0:
                        for process in processes:
                            self._check_and_add_schedule(process.schedule, scheds)
            for room in bldg.room_3ds:
                people = room.properties.energy._people
                lighting = room.properties.energy._lighting
                electric_equipment = room.properties.energy._electric_equipment
                gas_equipment = room.properties.energy._gas_equipment
                shw = room.properties.energy._service_hot_water
                infiltration = room.properties.energy._infiltration
                ventilation = room.properties.energy._ventilation
                setpoint = room.properties.energy._setpoint
                window_vent = room.properties.energy._window_vent_control
                processes = room.properties.energy._process_loads
                fans = room.properties.energy._fans
                if people is not None:
                    self._check_and_add_schedule(people.occupancy_schedule, scheds)
                    self._check_and_add_schedule(people.activity_schedule, scheds)
                if lighting is not None:
                    self._check_and_add_schedule(lighting.schedule, scheds)
                if electric_equipment is not None:
                    self._check_and_add_schedule(electric_equipment.schedule, scheds)
                if gas_equipment is not None:
                    self._check_and_add_schedule(gas_equipment.schedule, scheds)
                if shw is not None:
                    self._check_and_add_schedule(shw.schedule, scheds)
                if infiltration is not None:
                    self._check_and_add_schedule(infiltration.schedule, scheds)
                if ventilation is not None and ventilation.schedule is not None:
                    self._check_and_add_schedule(ventilation.schedule, scheds)
                if setpoint is not None:
                    self._check_and_add_schedule(setpoint.heating_schedule, scheds)
                    self._check_and_add_schedule(setpoint.cooling_schedule, scheds)
                    if setpoint.humidifying_schedule is not None:
                        self._check_and_add_schedule(
                            setpoint.humidifying_schedule, scheds)
                        self._check_and_add_schedule(
                            setpoint.dehumidifying_schedule, scheds)
                if window_vent is not None:
                    self._check_and_add_schedule(window_vent.schedule, scheds)
                if len(processes) != 0:
                    for process in processes:
                        self._check_and_add_schedule(process.schedule, scheds)
                if len(fans) != 0:
                    for fan in fans:
                        self._check_and_add_schedule(fan.control.schedule, scheds)
        return list(set(scheds))

    @property
    def program_types(self):
        """Get a list of all unique ProgramTypes in the Model.

        This includes ProgramTypes assigned to both Room2Ds and 3D Honeybee Rooms.
        """
        program_types = []
        for bldg in self.host._buildings:
            for story in bldg:
                for room in story:
                    if room.properties.energy._program_type is not None:
                        if not self._instance_in_array(
                                room.properties.energy._program_type, program_types):
                            program_types.append(room.properties.energy._program_type)
            for room in bldg.room_3ds:
                if room.properties.energy._program_type is not None:
                    if not self._instance_in_array(
                            room.properties.energy._program_type, program_types):
                        program_types.append(room.properties.energy._program_type)
        return list(set(program_types))  # catch equivalent program types

    @property
    def hvacs(self):
        """Get a list of all unique HVAC systems in the Model."""
        hvacs = []
        for bldg in self.host._buildings:
            for story in bldg:
                for room in story:
                    if room.properties.energy._hvac is not None:
                        if not self._instance_in_array(
                                room.properties.energy._hvac, hvacs):
                            hvacs.append(room.properties.energy._hvac)
            for room in bldg.room_3ds:
                if room.properties.energy._hvac is not None:
                    if not self._instance_in_array(room.properties.energy._hvac, hvacs):
                        hvacs.append(room.properties.energy._hvac)
        return hvacs

    @property
    def shws(self):
        """Get a list of all unique Service Hot Water (SHW) systems in the Model."""
        shws = []
        for bldg in self.host._buildings:
            for story in bldg:
                for room in story:
                    if room.properties.energy._shw is not None:
                        if not self._instance_in_array(
                                room.properties.energy._shw, shws):
                            shws.append(room.properties.energy._shw)
            for room in bldg.room_3ds:
                if room.properties.energy._shw is not None:
                    if not self._instance_in_array(room.properties.energy._shw, shws):
                        shws.append(room.properties.energy._shw)
        return shws

    def check_all(self, raise_exception=True):
        """Check all of the aspects of the Model energy properties.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if any errors are found. If False, this method will simply
                return a text string with all errors that were found.

        Returns:
            A text string with all errors that were found. This string will be empty
            of no errors were found.
        """
        msgs = []
        # perform checks for key honeybee model schema rules
        msgs.append(self.check_duplicate_construction_set_identifiers(False))
        msgs.append(self.check_duplicate_program_type_identifiers(False))
        msgs.append(self.check_duplicate_hvac_identifiers(False))
        msgs.append(self.check_duplicate_shw_identifiers(False))
        # output a final report of errors or raise an exception
        full_msgs = [msg for msg in msgs if msg != '']
        full_msg = '\n'.join(full_msgs)
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_duplicate_construction_set_identifiers(
            self, raise_exception=True, detailed=False):
        """Check that there are no duplicate ConstructionSet identifiers in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        return check_duplicate_identifiers(
            self.construction_sets, raise_exception, 'ConstructionSet',
            detailed, '020003', 'Energy',
            error_type='Duplicate ConstructionSet Identifier')

    def check_duplicate_program_type_identifiers(
            self, raise_exception=True, detailed=False):
        """Check that there are no duplicate ProgramType identifiers in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        return check_duplicate_identifiers(
            self.program_types, raise_exception, 'ProgramType',
            detailed, '020006', 'Energy', error_type='Duplicate ProgramType Identifier')

    def check_duplicate_hvac_identifiers(self, raise_exception=True, detailed=False):
        """Check that there are no duplicate HVAC identifiers in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        return check_duplicate_identifiers(
            self.hvacs, raise_exception, 'HVAC', detailed, '020007', 'Energy',
            error_type='Duplicate HVAC Identifier')

    def check_duplicate_shw_identifiers(self, raise_exception=True, detailed=False):
        """Check that there are no duplicate SHW identifiers in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        return check_duplicate_identifiers(
            self.shws, raise_exception, 'SHW', detailed, '020008', 'Energy',
            error_type='Duplicate SHW Identifier')

    def apply_properties_from_dict(self, data):
        """Apply the energy properties of a dictionary to the host Model of this object.

        Args:
            data: A dictionary representation of an entire dragonfly-core Model.
                Note that this dictionary must have ModelEnergyProperties in order
                for this method to successfully apply the energy properties.
        """
        assert 'energy' in data['properties'], \
            'Dictionary possesses no ModelEnergyProperties.'
        _, constructions, construction_sets, _, schedules, program_types, hvacs, shws = \
            hb_model_properties.ModelEnergyProperties.load_properties_from_dict(data)

        # collect lists of energy property dictionaries
        building_e_dicts, story_e_dicts, room2d_e_dicts, context_e_dicts = \
            model_extension_dicts(data, 'energy', [], [], [], [])

        # apply energy properties to objects using the energy property dictionaries
        for bldg, b_dict in zip(self.host.buildings, building_e_dicts):
            if b_dict is not None:
                bldg.properties.energy.apply_properties_from_dict(
                    b_dict, construction_sets)
            if bldg.has_room_3ds and b_dict is not None and 'room_3ds' in b_dict and \
                    b_dict['room_3ds'] is not None:
                room_e_dicts, face_e_dicts, shd_e_dicts, ap_e_dicts, dr_e_dicts = \
                    room_extension_dicts(b_dict['room_3ds'], 'energy', [], [], [], [], [])
                for room, r_dict in zip(bldg.room_3ds, room_e_dicts):
                    if r_dict is not None:
                        room.properties.energy.apply_properties_from_dict(
                            r_dict, construction_sets, program_types, hvacs, shws,
                            schedules, constructions)
                for face, f_dict in zip(bldg.room_3d_faces, face_e_dicts):
                    if f_dict is not None:
                        face.properties.energy.apply_properties_from_dict(
                            f_dict, constructions)
                for aperture, a_dict in zip(bldg.room_3d_apertures, ap_e_dicts):
                    if a_dict is not None:
                        aperture.properties.energy.apply_properties_from_dict(
                            a_dict, constructions)
                for door, d_dict in zip(bldg.room_3d_doors, dr_e_dicts):
                    if d_dict is not None:
                        door.properties.energy.apply_properties_from_dict(
                            d_dict, constructions)
                for shade, s_dict in zip(bldg.room_3d_shades, shd_e_dicts):
                    if s_dict is not None:
                        shade.properties.energy.apply_properties_from_dict(
                            s_dict, constructions, schedules)
        for story, s_dict in zip(self.host.stories, story_e_dicts):
            if s_dict is not None:
                story.properties.energy.apply_properties_from_dict(
                    s_dict, construction_sets)
        for room, r_dict in zip(self.host.room_2ds, room2d_e_dicts):
            if r_dict is not None:
                room.properties.energy.apply_properties_from_dict(
                    r_dict, construction_sets, program_types, hvacs, shws, schedules)
        for shade, s_dict in zip(self.host.context_shades, context_e_dicts):
            if s_dict is not None:
                shade.properties.energy.apply_properties_from_dict(
                    s_dict, constructions, schedules)

    def to_dict(self):
        """Return Model energy properties as a dictionary."""
        base = {'energy': {'type': 'ModelEnergyProperties'}}

        # add all materials, constructions and construction sets to the dictionary
        schs = self._add_constr_type_objs_to_dict(base)

        # add all schedule type limits, schedules, and program types to the dictionary
        self._add_sched_type_objs_to_dict(base, schs)

        return base

    def to_honeybee(self, new_host):
        """Get a honeybee version of this object.

        Args:
            new_host: A honeybee-core Model object that will host these properties.
        """
        return hb_model_properties.ModelEnergyProperties(new_host)

    def duplicate(self, new_host=None):
        """Get a copy of this Model.

        Args:
            new_host: A new Model object that hosts these properties.
                If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        return ModelEnergyProperties(_host)

    def _add_constr_type_objs_to_dict(self, base):
        """Add materials, constructions and construction sets to a base dictionary.

        Args:
            base: A base dictionary for a Dragonfly Model.
        """
        # add the global construction set to the dictionary
        gs = self.global_construction_set.to_dict(abridged=True, none_for_defaults=False)
        gs['type'] = 'GlobalConstructionSet'
        del gs['identifier']
        g_constr = self.global_construction_set.constructions_unique
        g_materials = []
        for constr in g_constr:
            try:
                g_materials.extend(constr.materials)
            except AttributeError:
                pass  # ShadeConstruction or AirBoundaryConstruction
        gs['context_construction'] = generic_context.identifier
        gs['constructions'] = [generic_context.to_dict()]
        for cnst in g_constr:
            try:
                gs['constructions'].append(cnst.to_dict(abridged=True))
            except TypeError:  # ShadeConstruction
                gs['constructions'].append(cnst.to_dict())
        gs['materials'] = [mat.to_dict() for mat in set(g_materials)]
        base['energy']['global_construction_set'] = gs

        # add all ConstructionSets to the dictionary
        base['energy']['construction_sets'] = []
        construction_sets = self.construction_sets
        for cnstr_set in construction_sets:
            base['energy']['construction_sets'].append(cnstr_set.to_dict(abridged=True))

        # add all unique Constructions to the dictionary
        room_constrs = []
        for cnstr_set in construction_sets:
            room_constrs.extend(cnstr_set.modified_constructions_unique)
        mass_constrs = []
        for bldg in self.host.buildings:
            for room in bldg.room_3ds:
                for int_mass in room.properties.energy._internal_masses:
                    constr = int_mass.construction
                    if not self._instance_in_array(constr, mass_constrs):
                        mass_constrs.append(constr)
        all_constrs = room_constrs + self.face_constructions + self.shade_constructions
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
                if cnstr.has_frame:
                    materials.append(cnstr.frame)
                if isinstance(cnstr, WindowConstructionShade):
                    if cnstr.is_switchable_glazing:
                        materials.append(cnstr.switched_glass_material)
                    if cnstr.shade_location == 'Between':
                        materials.append(cnstr.window_construction.materials[-2])
            except AttributeError:
                pass  # ShadeConstruction
        base['energy']['materials'] = [mat.to_dict() for mat in set(materials)]

        # extract all of the schedules from the constructions
        schedules = []
        for constr in constructions:
            if isinstance(constr, AirBoundaryConstruction):
                self._check_and_add_schedule(constr.air_mixing_schedule, schedules)
            elif isinstance(constr, WindowConstructionShade):
                if constr.schedule is not None:
                    self._check_and_add_schedule(constr.schedule, schedules)
            elif isinstance(constr, WindowConstructionDynamic):
                self._check_and_add_schedule(constr.schedule, schedules)
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

        # add all unique shws to the dictionary
        base['energy']['shws'] = [shw.to_dict() for shw in self.shws]

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
        all_scheds = hvac_scheds + p_type_scheds + self.misc_room_schedules + \
            self.shade_schedules + schs
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

    def _check_and_add_obj_construction(self, obj, constructions):
        """Check if a construction is assigned to an object and add it to a list."""
        constr = obj.properties.energy._construction
        if constr is not None:
            if not self._instance_in_array(constr, constructions):
                constructions.append(constr)

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

        This can be much faster than  `if object_instance in object_array`
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
        return 'Model Energy Properties: {}'.format(self.host.identifier)
