# coding=utf-8
"""Room2D Energy Properties."""
from honeybee.boundarycondition import Outdoors
from honeybee_energy.properties.room import RoomEnergyProperties
from honeybee_energy.programtype import ProgramType
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.hvac import HVAC_TYPES_DICT
from honeybee_energy.hvac._base import _HVACSystem
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.shw import SHWSystem
from honeybee_energy.ventcool.control import VentilationControl
from honeybee_energy.ventcool.opening import VentilationOpening
from honeybee_energy.load.process import Process

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
        * shw
        * window_vent_control
        * window_vent_opening
        * process_loads
        * is_conditioned
    """

    __slots__ = ('_host', '_program_type', '_construction_set', '_hvac', '_shw',
                 '_window_vent_control', '_window_vent_opening', '_process_loads')

    def __init__(
            self, host, program_type=None, construction_set=None, hvac=None, shw=None):
        """Initialize Room2D energy properties."""
        self._host = host
        self.program_type = program_type
        self.construction_set = construction_set
        self.hvac = hvac
        self.shw = shw
        self._window_vent_control = None  # set to None by default
        self._window_vent_opening = None  # set to None by default
        self._process_loads = []

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
            value.lock()   # lock in case hvac has multiple references
        self._hvac = value

    @property
    def shw(self):
        """Get or set the SHWSystem object for the Room2D.

        If None, all hot water loads will be met with a system that doesn't compute
        fuel or electricity usage.
        """
        return self._shw

    @shw.setter
    def shw(self, value):
        if value is not None:
            assert isinstance(value, SHWSystem), \
                'Expected SHWSystem for Room shw. Got {}'.format(type(value))
            value.lock()   # lock in case shw has multiple references
        self._shw = value

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
    def process_loads(self):
        """Get or set an array of Process objects for process loads within the Room2D."""
        return tuple(self._process_loads)

    @process_loads.setter
    def process_loads(self, value):
        for val in value:
            assert isinstance(val, Process), 'Expected Process ' \
                'object for Room process_loads. Got {}'.format(type(val))
            val.lock()   # lock because we don't duplicate the object
        self._process_loads = list(value)

    @property
    def is_conditioned(self):
        """Boolean to note whether the Room is conditioned."""
        return self._hvac is not None

    def add_default_ideal_air(self):
        """Add a default IdealAirSystem to this Room2D.

        The identifier of this system will be derived from the room identifier
        and will align with the naming convention that EnergyPlus uses for
        templates Ideal Air systems.
        """
        hvac_id = '{} Ideal Loads Air System'.format(self.host.identifier)
        self.hvac = IdealAirSystem(hvac_id)

    def add_process_load(self, process_load):
        """Add a Process load to this Room2D.

        Args:
            process_load: A Process load to add to this Room.
        """
        assert isinstance(process_load, Process), \
            'Expected Process load object. Got {}.'.format(type(process_load))
        process_load.lock()   # lock because we don't duplicate the object
        self._process_loads.append(process_load)

    def remove_process_loads(self):
        """Remove all Process loads from the Room."""
        self._process_loads = []

    @classmethod
    def from_dict(cls, data, host):
        """Create Room2DEnergyProperties from a dictionary.

        Note that the dictionary must be a non-abridged version for this
        classmethod to work.

        Args:
            data: A dictionary representation of Room2DEnergyProperties in the
                format below.
            host: A Room2D object that hosts these properties.

        .. code-block:: python

            {
            "type": 'Room2DEnergyProperties',
            "construction_set": {},  # A ConstructionSet dictionary
            "program_type": {},  # A ProgramType dictionary
            "hvac": {}, # A HVACSystem dictionary
            "shw": {}, # A SHWSystem dictionary
            "daylighting_control": {},  # A DaylightingControl dictionary
            "window_vent_control": {}  # A VentilationControl dictionary
            "process_loads": []  # An array of Process dictionaries
            }
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
        if 'shw' in data and data['shw'] is not None:
            new_prop.shw = SHWSystem.from_dict(data['shw'])
        cls._deserialize_window_vent(new_prop, data)
        if 'process_loads' in data and data['process_loads'] is not None:
            new_prop.process_loads = \
                [Process.from_dict(dat) for dat in data['process_loads']]

        return new_prop

    def apply_properties_from_dict(self, abridged_data, construction_sets,
                                   program_types, hvacs, shws, schedules):
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
            shws: A dictionary of SHWSystems with the identifiers of the systems as
                keys, which will be used to re-assign shw to the Room.
            schedules: A dictionary of Schedules with identifiers of the schedules as
                keys, which will be used to re-assign schedules.
        """
        if 'construction_set' in abridged_data and \
                abridged_data['construction_set'] is not None:
            self.construction_set = construction_sets[abridged_data['construction_set']]
        if 'program_type' in abridged_data and abridged_data['program_type'] is not None:
            self.program_type = program_types[abridged_data['program_type']]
        if 'hvac' in abridged_data and abridged_data['hvac'] is not None:
            self.hvac = hvacs[abridged_data['hvac']]
        if 'shw' in abridged_data and abridged_data['shw'] is not None:
            self.shw = shws[abridged_data['shw']]
        self._deserialize_window_vent(self, abridged_data)
        if 'process_loads' in abridged_data and \
                abridged_data['process_loads'] is not None:
            self.process_loads = []
            for dat in abridged_data['process_loads']:
                if dat['type'] == 'Process':
                    self.process_loads.append(Process.from_dict(dat))
                else:
                    self.process_loads.append(Process.from_dict_abridged(dat, schedules))

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

        # write the shw into the dictionary
        if self._shw is not None:
            base['energy']['shw'] = \
                self._shw.identifier if abridged else self._shw.to_dict()

        # write the window_vent_control and window_vent_opening into the dictionary
        if self._window_vent_control is not None:
            base['energy']['window_vent_control'] = \
                self.window_vent_control.to_dict(abridged=True)
            base['energy']['window_vent_control']['schedule'] = None
        if self._window_vent_opening is not None:
            base['energy']['window_vent_opening'] = self.window_vent_opening.to_dict()

        # write the process_loads into the dictionary
        if len(self._process_loads) != 0:
            base['energy']['process_loads'] = \
                [p.to_dict(abridged) for p in self._process_loads]

        return base

    def to_honeybee(self, new_host):
        """Get a honeybee version of this object.

        Args:
            new_host: A honeybee-core Room object that will host these properties.
        """
        constr_set = self.construction_set  # includes story and building-assigned sets
        hb_constr = constr_set if constr_set is not generic_construction_set else None
        hb_prop = RoomEnergyProperties(
            new_host, self._program_type, hb_constr, self._hvac, self._shw)
        if self._window_vent_control is not None:
            hb_prop.window_vent_control = self.window_vent_control
        if self._window_vent_opening is not None:
            for face in new_host.faces:  # set all apertures to be operable
                for ap in face.apertures:
                    if isinstance(ap.boundary_condition, Outdoors):
                        ap.is_operable = True
            hb_prop.assign_ventilation_opening(self.window_vent_opening)
        if len(self._process_loads) != 0:
            hb_prop.process_loads = self.process_loads
        return hb_prop

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        Args:
            new_host: A new Room2D object that hosts these properties.
                If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        hb_prop = Room2DEnergyProperties(
            _host, self._program_type, self._construction_set, self._hvac, self._shw)
        hb_prop._window_vent_control = self._window_vent_control
        hb_prop._window_vent_opening = self._window_vent_opening
        hb_prop._process_loads = self._process_loads[:]  # copy process load list
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
