# coding=utf-8
"""Building Energy Properties."""
from honeybee_energy.programtype import ProgramType
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.hvac._base import _HVACSystem
from honeybee_energy.hvac.idealair import IdealAirSystem

from honeybee_energy.lib.constructionsets import generic_construction_set


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

    def averaged_program_type(self, name=None, timestep_resolution=1):
        """Get a ProgramType that is averaged across all of the children Room2Ds.

        The weights used in the averaging process are the floor area weights and they
        account for the multipliers on the child Story objects.

        Args:
            name: A name for the new averaged ProgramType object. If None, the
                resulting ProgramType will use the name of the host Building.
                Default: None.
            timestep_resolution: An optional integer for the timestep resolution
                at which the schedules will be averaged. Any schedule details
                smaller than this timestep will be lost in the averaging process.
                Default: 1.
        """
        # get the default name of the ProgramType if None
        name = name if name is not None else '{}_Program'.format(self.host.name)

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
        return ProgramType.average(name, program_types, weights, timestep_resolution)

    def set_all_room_2d_program_type(self, program_type):
        """Set all of the children Room2Ds of this Building to have the same ProgramType.

        Args:
            program_type: A ProgramType to assign to all children Room2Ds.
        """
        assert isinstance(program_type, ProgramType), 'Expected ProgramType for ' \
            'Building set_all_room_2d_program_type. Got {}'.format(type(program_type))
        for room_2d in self.host.unique_room_2ds:
            room_2d.properties.energy.program_type = program_type

    def set_all_room_2d_hvac(self, hvac):
        """Set all children Room2Ds of this Buiding to have the same HVAC system.

        For an HVAC system that is intended to be applied across multiple zones
        (such as a VAVSystem), all Room2Ds will receive the same HVAC instance
        as their HVAC system. In the case of an HVAC that can only be assigned
        to individual zones (such as an IdealAirSystem), the input hvac will be
        duplicated and renamed (with an integer appended to the end) for each
        Room2D to which is it applied.

        Args:
            hvac: An HVAC system with properties that will be assigned to all
                children Room2Ds.
        """
        assert isinstance(hvac, _HVACSystem), 'Expected HVACSystem for Building.' \
            'set_all_room_2d_hvac. Got {}'.format(type(hvac))

        if not hvac.is_single_room:  # apply the same instance to all rooms
            for room_2d in self.host.unique_room_2ds:
                room_2d.properties.energy.hvac = hvac
        else:  # duplicate the HVAC instance as it is applied to rooms
            for i, room_2d in enumerate(self.host.unique_room_2ds):
                new_hvac = hvac.duplicate()
                new_hvac.name = '{}_{}'.format(hvac.name, i)
                room_2d.properties.energy.hvac = new_hvac

    def add_default_ideal_air(self):
        """Add a default IdealAirSystem to all children Room2Ds of this Story.

        The name of the systems will be derived from the room names.
        """
        for room_2d in self.host.unique_room_2ds:
            room_2d.properties.energy.add_default_ideal_air()

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
            construction_sets: A dictionary of ConstructionSets with names of the sets
                as keys, which will be used to re-assign construction_sets.
        """
        if 'construction_set' in abridged_data and \
                abridged_data['construction_set'] is not None:
            self.construction_set = construction_sets[abridged_data['construction_set']]

    def to_dict(self, abridged=False):
        """Return Building energy properties as a dictionary.

        Args:
            abridged: Boolean for whether the full dictionary of the Building should
                be written (False) or just the name of the the individual
                properties (True). Default: False.
        """
        base = {'energy': {}}
        base['energy']['type'] = 'BuildingEnergyProperties' if not \
            abridged else 'BuildingEnergyPropertiesAbridged'

        # write the ConstructionSet into the dictionary
        if self._construction_set is not None:
            base['energy']['construction_set'] = \
                self._construction_set.name if abridged else \
                self._construction_set.to_dict()

        return base

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        new_host: A new Building object that hosts these properties.
            If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        return BuildingEnergyProperties(_host, self._construction_set)

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Building Energy Properties:\n host: {}'.format(self.host.name)
