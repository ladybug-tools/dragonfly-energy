# coding=utf-8
"""Room2D Energy Properties."""
from honeybee_energy.programtype import ProgramType
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.idealair import IdealAirSystem
from honeybee_energy.properties.room import RoomEnergyProperties

from honeybee_energy.lib.constructionsets import generic_construction_set
from honeybee_energy.lib.programtypes import plenum_program


class Room2DEnergyProperties(object):
    """Energy Properties for Dragonfly Room2D.

    Properties:
        * host
        * program_type
        * construction_set
        * hvac
        * is_conditioned
    """

    __slots__ = ('_host', '_program_type', '_construction_set', '_hvac')

    def __init__(self, host, program_type=None, construction_set=None, hvac=None):
        """Initialize Room2D energy properties.

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
        """
        self._host = host
        self.program_type = program_type
        self.construction_set = construction_set
        self.hvac = hvac

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
            assert isinstance(value, IdealAirSystem), \
                'Expected IdealAirSystem for Room2D hvac. Got {}'.format(type(value))
            if value._parent is not None:
                raise ValueError(
                    'IdealAirSystem objects can be assigned to a only one Room2D.\n'
                    'IdealAirSystem cannot be assigned to Room2D "{}" since it is '
                    'already assigned to "{}".\nTry duplicating the IdealAirSystem, '
                    'and then assigning it to this Room2D.'.format(
                        self.host.name, value._parent.name))
            value._parent = self.host
        self._hvac = value

    @property
    def is_conditioned(self):
        """Boolean to note whether the Room is conditioned."""
        return self._hvac is not None

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
            new_prop.hvac = IdealAirSystem.from_dict(data['hvac'])

        return new_prop

    def to_dict(self, abridged=False):
        """Return Room2D energy properties as a dictionary.

        Args:
            abridged: Boolean for whether the full dictionary of the Room2D should
                be written (False) or just the name of the the individual
                properties (True). Default: False.
        """
        base = {'energy': {}}
        base['energy']['type'] = 'Room2DEnergyProperties' if not \
            abridged else 'Room2DEnergyPropertiesAbridged'

        # write the ProgramType into the dictionary
        if self._program_type is not None:
            base['energy']['program_type'] = \
                self._program_type.name if abridged else self._program_type.to_dict()

        # write the ConstructionSet into the dictionary
        if self._construction_set is not None:
            base['energy']['construction_set'] = \
                self._construction_set.name if abridged else \
                self._construction_set.to_dict()

        # write the hvac into the dictionary
        if self._hvac is not None:
            base['energy']['hvac'] = self._hvac.to_dict()

        return base

    def to_honeybee(self, new_host):
        """Get a honeybee version of this object.

        Args:
            new_host: A honeybee-core Room object that will host these properties.
        """
        constr_set = self.construction_set
        hb_constr = constr_set if constr_set is not generic_construction_set else None
        hvac = self.hvac.duplicate() if self.is_conditioned else None
        return RoomEnergyProperties(new_host, self._program_type, hb_constr, hvac)

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        Args:
            new_host: A new Room2D object that hosts these properties.
                If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        hvac = self.hvac.duplicate() if self.is_conditioned else None
        return Room2DEnergyProperties(_host, self._program_type,
                                      self._construction_set, hvac)

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Room2D Energy Properties:\n host: {}'.format(self.host.name)
