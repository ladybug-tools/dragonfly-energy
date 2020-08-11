# coding=utf-8
"""Room2D Energy Properties."""
from honeybee.boundarycondition import Outdoors
from honeybee_energy.properties.room import RoomEnergyProperties
from honeybee_energy.programtype import ProgramType
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.hvac import HVAC_TYPES_DICT
from honeybee_energy.hvac._base import _HVACSystem
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.ventcool.control import VentilationControl
from honeybee_energy.ventcool.opening import VentilationOpening

from honeybee_energy.lib.constructionsets import generic_construction_set
from honeybee_energy.lib.programtypes import plenum_program


class Room2DEnergyProperties(object):
    """Energy Properties for Dragonfly Room2D.

    Args:
        host: A dragonfly_core Room2D object that hosts these properties.
        program_type: A honeybee ProgramType object to specify all default
            schedules and loads for the Room2D. If None, the Room2D will have a
            Plenum program (with no loads or setpoints). Default: None.
        construction_set: A honeybee ConstructionSet object to specify all
            default constructions for the Faces of the Room2D. If None, the
            Room2D will use the honeybee default construction set, which is not
            representative of a particular building code or climate zone.
            Default: None.
        hvac: A honeybee HVAC object (such as an IdealAirSystem) that specifies
            how the Room2D is conditioned. If None, it will be assumed that the
            Room2D is not conditioned. Default: None.

    Properties:
        * host
        * program_type
        * construction_set
        * hvac
        * window_vent_control
        * window_vent_opening
        * is_conditioned
    """

    __slots__ = ('_host', '_program_type', '_construction_set', '_hvac',
                 '_window_vent_control', '_window_vent_opening')

    def __init__(self, host, program_type=None, construction_set=None, hvac=None):
        """Initialize Room2D energy properties."""
        self._host = host
        self.program_type = program_type
        self.construction_set = construction_set
        self.hvac = hvac
        self._window_vent_control = None  # set to None by default
        self._window_vent_opening = None  # set to None by default

    @property
    def host(self):
        """Get the Room2D object hosting these properties."""
        return self._host

    @property
    def program_type(self):
        """Get or set the ProgramType object for the Room2D.

        If not set, it will default to a plenum ProgramType (with no loads assigned).
        """
        if self._program_type is not None:  # set by the user
            return self._program_type
        else:
            return plenum_program

    @program_type.setter
    def program_type(self, value):
        if value is not None:
            assert isinstance(value, ProgramType), 'Expected ProgramType for Room2D ' \
                'program_type. Got {}'.format(type(value))
            value.lock()   # lock in case program type has multiple references
        self._program_type = value

    @property
    def construction_set(self):
        """Get or set the Room2D ConstructionSet object.

        If not set, it will be set by the parent Story or will be the Honeybee
        default generic ConstructionSet.
        """
        if self._construction_set is not None:  # set by the user
            return self._construction_set
        elif self._host.has_parent:  # set by parent story
            return self._host.parent.properties.energy.construction_set
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
    def hvac(self):
        """Get or set the HVAC object for the Room2D.

        If None, it will be assumed that the Room2D is not conditioned.
        """
        return self._hvac

    @hvac.setter
    def hvac(self, value):
        if value is not None:
            assert isinstance(value, _HVACSystem), \
                'Expected HVACSystem for Room2D hvac. Got {}'.format(type(value))
            if value.is_single_room:
                if value._parent is None:
                    value._parent = self.host
                elif value._parent.identifier != self.host.identifier:
                    raise ValueError(
                        '{0} objects can be assigned to a only one Room2D.\n'
                        '{0} "{1}" cannot be assigned to Room "{2}" since it is '
                        'already assigned to "{3}".\nTry duplicating the {0}, '
                        'and then assigning it to this Room.'.format(
                            value.__class__.__name__, value.identifier,
                            self.host.identifier, value._parent.identifier))
            value.lock()   # lock in case hvac has multiple references
        self._hvac = value

    @property
    def window_vent_control(self):
        """Get or set a VentilationControl object to dictate the opening of windows.

        If None or no window_vent_opening object is assigned to this Room2D,
        the windows will never open.
        """
        return self._window_vent_control

    @window_vent_control.setter
    def window_vent_control(self, value):
        if value is not None:
            assert isinstance(value, VentilationControl), 'Expected VentilationControl ' \
                'object for Room2D window_vent_control. Got {}'.format(type(value))
            assert value.schedule.identifier == 'Always On', 'VentilationControl ' \
                'schedule must be default in order to apply it to dragonfly Room2D.'
            value.lock()   # lock because we don't duplicate the object
        self._window_vent_control = value

    @property
    def window_vent_opening(self):
        """Get or set a VentilationOpening object for the operability of all windows.

        If None or no window_vent_control object is assigned to this Room2D,
        the windows will never open.
        """
        return self._window_vent_opening

    @window_vent_opening.setter
    def window_vent_opening(self, value):
        if value is not None:
            assert isinstance(value, VentilationOpening), 'Expected VentilationOpening ' \
                'for Room2D window_vent_opening. Got {}'.format(type(value))
        self._window_vent_opening = value

    @property
    def is_conditioned(self):
        """Boolean to note whether the Room is conditioned."""
        return self._hvac is not None

    def add_default_ideal_air(self):
        """Add a default IdealAirSystem to this Room2D.

        The identifier of this system will be derived from the room identifier.
        """
        self.hvac = IdealAirSystem('{}_IdealAir'.format(self.host.identifier))

    def add_prefix(self, prefix):
        """Change the identifier of attributes unique to this object by adding a prefix.

        Notably, this method only adds the prefix to extension attributes that must
        be unique to the Room (eg. single-room HVAC systems) and does not add the
        prefix to attributes that are shared across several Rooms (eg. ConstructionSets).

        Args:
            prefix: Text that will be inserted at the start of extension
                attribute identifiers.
        """
        if self._hvac is not None and self._hvac.is_single_room:
            new_hvac = self._hvac.duplicate()
            new_hvac._identifier = '{}_{}'.format(prefix, self._hvac.identifier)
            self.hvac = new_hvac

    @classmethod
    def from_dict(cls, data, host):
        """Create Room2DEnergyProperties from a dictionary.

        Note that the dictionary must be a non-abridged version for this
        classmethod to work.

        Args:
            data: A dictionary representation of Room2DEnergyProperties.
            host: A Room2D object that hosts these properties.
        """
        assert data['type'] == 'Room2DEnergyProperties', \
            'Expected Room2DEnergyProperties. Got {}.'.format(data['type'])

        new_prop = cls(host)
        if 'construction_set' in data and data['construction_set'] is not None:
            new_prop.construction_set = \
                ConstructionSet.from_dict(data['construction_set'])
        if 'program_type' in data and data['program_type'] is not None:
            new_prop.program_type = ProgramType.from_dict(data['program_type'])
        if 'hvac' in data and data['hvac'] is not None:
            hvac_class = HVAC_TYPES_DICT[data['hvac']['type']]
            new_prop.hvac = hvac_class.from_dict(data['hvac'])
        cls._deserialize_window_vent(new_prop, data)

        return new_prop

    def apply_properties_from_dict(self, abridged_data, construction_sets,
                                   program_types, hvacs):
        """Apply properties from a Room2DEnergyPropertiesAbridged dictionary.

        Args:
            abridged_data: A Room2DEnergyPropertiesAbridged dictionary (typically
                coming from a Model).
            construction_sets: A dictionary of ConstructionSets with identifiers
                of the sets as keys, which will be used to re-assign construction_sets.
            program_types: A dictionary of ProgramTypes with identifiers of the
                types ask keys, which will be used to re-assign program_types.
            hvacs: A dictionary of HVACSystems with the identifiers of the
                systems as keys, which will be used to re-assign hvac to the Room.
        """
        if 'construction_set' in abridged_data and \
                abridged_data['construction_set'] is not None:
            self.construction_set = construction_sets[abridged_data['construction_set']]
        if 'program_type' in abridged_data and abridged_data['program_type'] is not None:
            self.program_type = program_types[abridged_data['program_type']]
        if 'hvac' in abridged_data and abridged_data['hvac'] is not None:
            self.hvac = hvacs[abridged_data['hvac']]
        self._deserialize_window_vent(self, abridged_data)

    def to_dict(self, abridged=False):
        """Return Room2D energy properties as a dictionary.

        Args:
            abridged: Boolean for whether the full dictionary of the Room2D should
                be written (False) or just the identifier of the the individual
                properties (True). Default: False.
        """
        base = {'energy': {}}
        base['energy']['type'] = 'Room2DEnergyProperties' if not \
            abridged else 'Room2DEnergyPropertiesAbridged'

        # write the ProgramType into the dictionary
        if self._program_type is not None:
            base['energy']['program_type'] = self._program_type.identifier if abridged \
                else self._program_type.to_dict()

        # write the ConstructionSet into the dictionary
        if self._construction_set is not None:
            base['energy']['construction_set'] = \
                self._construction_set.identifier if abridged else \
                self._construction_set.to_dict()

        # write the hvac into the dictionary
        if self._hvac is not None:
            base['energy']['hvac'] = \
                self._hvac.identifier if abridged else self._hvac.to_dict()

        # write the window_vent_control and window_vent_opening into the dictionary
        if self._window_vent_control is not None:
            base['energy']['window_vent_control'] = \
                self.window_vent_control.to_dict(abridged=True)
            base['energy']['window_vent_control']['schedule'] = None
        if self._window_vent_opening is not None:
            base['energy']['window_vent_opening'] = self.window_vent_opening.to_dict()

        return base

    def to_honeybee(self, new_host):
        """Get a honeybee version of this object.

        Args:
            new_host: A honeybee-core Room object that will host these properties.
        """
        constr_set = self.construction_set  # includes story and building-assigned sets
        hb_constr = constr_set if constr_set is not generic_construction_set else None
        hvac = self._hvac.duplicate() if self._hvac is not None and \
            self._hvac.is_single_room else self._hvac
        hb_prop = RoomEnergyProperties(new_host, self._program_type, hb_constr, hvac)
        if self._window_vent_control is not None:
            hb_prop.window_vent_control = self.window_vent_control
        if self._window_vent_opening is not None:
            for face in new_host.faces:  # set all apertures to be operable
                for ap in face.apertures:
                    if isinstance(ap.boundary_condition, Outdoors):
                        ap.is_operable = True
            hb_prop.assign_ventilation_opening(self.window_vent_opening)
        return hb_prop

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        Args:
            new_host: A new Room2D object that hosts these properties.
                If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        hvac = self._hvac.duplicate() if self._hvac is not None and \
            self._hvac.is_single_room else self._hvac
        hb_prop = Room2DEnergyProperties(
            _host, self._program_type, self._construction_set, hvac)
        hb_prop._window_vent_control = self._window_vent_control
        hb_prop._window_vent_opening = self._window_vent_opening
        return hb_prop

    @staticmethod
    def _deserialize_window_vent(new_prop, data):
        """Re-serialize window ventilation objects from a dict and apply to new_prop.

        Args:
            new_prop: A Room2DEnergyProperties to apply the window ventilation to.
            data: A dictionary representation of Room2DEnergyProperties.
        """
        if 'window_vent_control' in data and data['window_vent_control'] is not None:
            new_prop.window_vent_control = \
                VentilationControl.from_dict_abridged(data['window_vent_control'], {})
        if 'window_vent_opening' in data and data['window_vent_opening'] is not None:
            new_prop.window_vent_opening = \
                VentilationOpening.from_dict(data['window_vent_opening'])

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Room2D Energy Properties: {}'.format(self.host.identifier)
