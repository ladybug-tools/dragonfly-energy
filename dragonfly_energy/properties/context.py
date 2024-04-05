# coding=utf-8
"""Context Shade Energy Properties."""
from honeybee.shade import Shade
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.schedule.ruleset import ScheduleRuleset
from honeybee_energy.schedule.fixedinterval import ScheduleFixedInterval
from honeybee_energy.properties.shade import ShadeEnergyProperties
from honeybee_energy.properties.shademesh import ShadeMeshEnergyProperties

from honeybee_energy.lib.constructions import generic_context


class ContextShadeEnergyProperties(object):
    """Energy Properties for Dragonfly ContextShade.

    Args:
        host_shade: A dragonfly_core ContextShade object that hosts these properties.
        construction: An optional ShadeConstruction object to set the reflectance
            and specularity of the ContextShade. The default is a completely
            diffuse construction with 0.2 visible and solar reflectance.
        transmittance_schedule: An optional schedule to set the transmittance
            of the shade, which can vary throughout the day or year.  Default
            is a completely opaque object.

    Properties:
        * host
        * construction
        * transmittance_schedule
        * is_construction_set_by_user
    """

    __slots__ = ('_host', '_construction', '_transmittance_schedule')

    def __init__(self, host_shade, construction=None, transmittance_schedule=None):
        """Initialize ContextShade energy properties."""
        self._host = host_shade
        self.construction = construction
        self.transmittance_schedule = transmittance_schedule

    @property
    def host(self):
        """Get the Shade object hosting these properties."""
        return self._host

    @property
    def construction(self):
        """Get or set a ShadeConstruction for the context shade."""
        if self._construction:  # set by user
            return self._construction
        else:
            return generic_context

    @construction.setter
    def construction(self, value):
        if value is not None:
            assert isinstance(value, ShadeConstruction), \
                'Expected ShadeConstruction. Got {}.'.format(type(value))
            value.lock()  # lock editing in case construction has multiple references
        self._construction = value

    @property
    def transmittance_schedule(self):
        """Get or set the transmittance schedule of the shade."""
        return self._transmittance_schedule

    @transmittance_schedule.setter
    def transmittance_schedule(self, value):
        if value is not None:
            assert isinstance(value, (ScheduleRuleset, ScheduleFixedInterval)), \
                'Expected schedule for shade transmittance schedule. ' \
                'Got {}.'.format(type(value))
            if value.schedule_type_limit is not None:
                assert value.schedule_type_limit.unit == 'fraction', 'Transmittance ' \
                    'schedule should be fractional [Dimensionless]. Got a schedule ' \
                    'of unit_type [{}].'.format(value.schedule_type_limit.unit_type)
            value.lock()  # lock editing in case schedule has multiple references
        self._transmittance_schedule = value

    @property
    def is_construction_set_by_user(self):
        """Boolean noting if construction is user-set."""
        return self._construction is not None

    @classmethod
    def from_dict(cls, data, host):
        """Create ContextShadeEnergyProperties from a dictionary.

        Note that the dictionary must be a non-abridged version for this
        classmethod to work.

        Args:
            data: A dictionary representation of ContextShadeEnergyProperties.
            host: A ContextShade object that hosts these properties.
        """
        assert data['type'] == 'ContextShadeEnergyProperties', \
            'Expected ContextShadeEnergyProperties. Got {}.'.format(data['type'])

        new_prop = cls(host)
        if 'construction' in data and data['construction'] is not None:
            new_prop.construction = ShadeConstruction.from_dict(data['construction'])
        if 'transmittance_schedule' in data and \
                data['transmittance_schedule'] is not None:
            sch_dict = data['transmittance_schedule']
            if sch_dict['type'] == 'ScheduleRuleset':
                new_prop.transmittance_schedule = \
                    ScheduleRuleset.from_dict(data['transmittance_schedule'])
            elif sch_dict['type'] == 'ScheduleFixedInterval':
                new_prop.transmittance_schedule = \
                    ScheduleFixedInterval.from_dict(data['transmittance_schedule'])
            else:
                raise ValueError(
                    'Expected non-abridged Schedule dictionary for ContextShade '
                    'transmittance_schedule. Got {}.'.format(sch_dict['type']))
        return new_prop

    def apply_properties_from_dict(self, abridged_data, constructions, schedules):
        """Apply properties from a ContextShadeEnergyPropertiesAbridged dictionary.

        Args:
            abridged_data: A ContextShadeEnergyPropertiesAbridged dictionary (typically
                coming from a Model).
            constructions: A dictionary of constructions with constructions identifiers
                as keys, which will be used to re-assign constructions.
            schedules: A dictionary of schedules with schedule identifiers as keys,
                which will be used to re-assign schedules.
        """
        if 'construction' in abridged_data and abridged_data['construction'] is not None:
            self.construction = constructions[abridged_data['construction']]
        if 'transmittance_schedule' in abridged_data and \
                abridged_data['transmittance_schedule'] is not None:
            self.transmittance_schedule = \
                schedules[abridged_data['transmittance_schedule']]

    def to_dict(self, abridged=False):
        """Return energy properties as a dictionary.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True).
                Default: False.
        """
        base = {'energy': {}}
        base['energy']['type'] = 'ContextShadeEnergyProperties' if not \
            abridged else 'ContextShadeEnergyPropertiesAbridged'
        if self._construction is not None:
            base['energy']['construction'] = self._construction.identifier if abridged \
                else self._construction.to_dict()
        if self.transmittance_schedule is not None:
            base['energy']['transmittance_schedule'] = \
                self.transmittance_schedule.identifier if abridged else \
                self.transmittance_schedule.to_dict()
        return base

    def to_honeybee(self, new_host):
        """Get a honeybee version of this object.

        Args:
            new_host: A honeybee-core Shade object that will host these properties.
        """
        return ShadeEnergyProperties(new_host, self._construction,
                                     self._transmittance_schedule) \
            if isinstance(new_host, Shade) else \
            ShadeMeshEnergyProperties(new_host, self._construction,
                                      self._transmittance_schedule)

    def from_honeybee(self, hb_properties):
        """Transfer energy attributes from a Honeybee Shade to Dragonfly ContextShade.

        Args:
            hb_properties: The ShadeEnergyProperties of the honeybee Shade that is being
                translated to a Dragonfly ContextShade.
        """
        self._construction = hb_properties._construction
        self._transmittance_schedule = hb_properties._transmittance_schedule

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        new_host: A new ContextShade object that hosts these properties.
            If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        return ContextShadeEnergyProperties(_host, self._construction,
                                            self._transmittance_schedule)

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Context Shade Energy Properties: {}'.format(self.host.identifier)
