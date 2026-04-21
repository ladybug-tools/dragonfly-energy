# coding=utf-8
"""Room2D Energy Properties."""
from ladybug_geometry.geometry3d import Point3D
from honeybee.boundarycondition import Outdoors
from honeybee_energy.properties.room import RoomEnergyProperties
from honeybee_energy.programtype import ProgramType
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.hvac import HVAC_TYPES_DICT
from honeybee_energy.hvac._base import _HVACSystem
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.shw import SHWSystem
from honeybee_energy.load.daylight import DaylightingControl
from honeybee_energy.ventcool.control import VentilationControl
from honeybee_energy.ventcool.opening import VentilationOpening
from honeybee_energy.ventcool.fan import VentilationFan
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
        * people
        * lighting
        * electric_equipment
        * gas_equipment
        * service_hot_water
        * infiltration
        * ventilation
        * setpoint
        * daylighting_control
        * window_vent_control
        * window_vent_opening
        * fans
        * process_loads
        * total_process_load
        * is_conditioned
        * has_window_opening
    """

    __slots__ = (
        '_host', '_program_type', '_construction_set', '_hvac', '_shw',
        '_window_vent_control', '_window_vent_opening', '_fans',
        '_daylighting_control', '_process_loads'
    )

    def __init__(
        self, host, program_type=None, construction_set=None, hvac=None, shw=None
    ):
        """Initialize Room2D energy properties."""
        self._host = host
        self.program_type = program_type
        self.construction_set = construction_set
        self.hvac = hvac
        self.shw = shw
        self._daylighting_control = None  # set to None by default
        self._window_vent_control = None  # set to None by default
        self._window_vent_opening = None  # set to None by default
        self._process_loads = []  # empty by default
        self._fans = []  # empty by default

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
    def people(self):
        """Get the People object to describe the occupancy of the Room."""
        return self.program_type.people

    @property
    def lighting(self):
        """Get the Lighting object to describe the lighting usage of the Room."""
        return self.program_type.lighting

    @property
    def electric_equipment(self):
        """Get the ElectricEquipment object to describe the equipment usage."""
        return self.program_type.electric_equipment

    @property
    def gas_equipment(self):
        """Get the GasEquipment object to describe the equipment usage."""
        return self.program_type.gas_equipment

    @property
    def service_hot_water(self):
        """Get the ServiceHotWater object to describe the hot water usage."""
        return self.program_type.service_hot_water

    @property
    def infiltration(self):
        """Get the Infiltration object to to describe the outdoor air leakage."""
        return self.program_type.infiltration

    @property
    def ventilation(self):
        """Get the Ventilation object for the minimum outdoor air requirement."""
        return self.program_type.ventilation

    @property
    def setpoint(self):
        """Get the Setpoint object for the temperature setpoints of the Room."""
        return self.program_type.setpoint

    @property
    def daylighting_control(self):
        """Get or set a DaylightingControl object to dictate the dimming of lights.

        If None, the lighting will respond only to the schedule and not the
        daylight conditions within the room.
        """
        return self._daylighting_control

    @daylighting_control.setter
    def daylighting_control(self, value):
        if value is not None:
            assert isinstance(value, DaylightingControl), 'Expected DaylightingControl' \
                ' object for Room2D daylighting_control. Got {}'.format(type(value))
            value._parent = self.host
        self._daylighting_control = value

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
            assert isinstance(value, VentilationControl), 'Expected VentilationControl' \
                ' object for Room2D window_vent_control. Got {}'.format(type(value))
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
            assert isinstance(value, VentilationOpening), 'Expected VentilationOpening' \
                ' for Room2D window_vent_opening. Got {}'.format(type(value))
        self._window_vent_opening = value

    @property
    def fans(self):
        """Get or set an array of VentilationFan objects for fans within the room.

        Note that these fans are not connected to the heating or cooling system
        and are meant to represent the intentional circulation of unconditioned
        outdoor air for the purposes of keeping a space cooler, drier or free
        of indoor pollutants (as in the case of kitchen or bathroom exhaust fans).

        For the specification of mechanical ventilation of conditioned outdoor air,
        the Room.ventilation property should be used and the Room should be
        given a HVAC that can meet this specification.
        """
        return tuple(self._fans)

    @fans.setter
    def fans(self, value):
        for val in value:
            assert isinstance(val, VentilationFan), 'Expected VentilationFan ' \
                'object for Room2D fans. Got {}'.format(type(val))
            val.lock()   # lock because we don't duplicate the object
        self._fans = list(value)

    @property
    def total_fan_flow(self):
        """Get a number for the total fan flow in m3/s within the room."""
        return sum([fan.flow_rate for fan in self._fans])

    @property
    def process_loads(self):
        """Get or set an array of Process objects for process loads within the Room2D."""
        return tuple(self._process_loads)

    @process_loads.setter
    def process_loads(self, value):
        for val in value:
            assert isinstance(val, Process), 'Expected Process ' \
                'object for Room2D process_loads. Got {}'.format(type(val))
            val.lock()   # lock because we don't duplicate the object
        self._process_loads = list(value)

    @property
    def total_process_load(self):
        """Get a number for the total process load in W within the room."""
        return sum([load.watts for load in self._process_loads])

    @property
    def is_conditioned(self):
        """Boolean to note whether the Room is conditioned."""
        return self._hvac is not None

    @property
    def has_window_opening(self):
        """Boolean to note whether the Room has operable windows with controls."""
        return self._window_vent_opening is not None

    def add_default_ideal_air(self):
        """Add a default IdealAirSystem to this Room2D.

        The identifier of this system will be derived from the room identifier
        and will align with the naming convention that EnergyPlus uses for
        templates Ideal Air systems.
        """
        hvac_id = '{} Ideal Loads Air System'.format(self.host.identifier)
        self.hvac = IdealAirSystem(hvac_id)

    def add_daylight_control_to_center(
            self, distance_from_floor, illuminance_setpoint=300, control_fraction=1,
            min_power_input=0.3, min_light_output=0.2, off_at_minimum=False,
            tolerance=0.01):
        """Assign a DaylightingControl object to the center of the Room.

        If the Room is concave, the pole of inaccessibility of the floor geometry will
        be used.

        Args:
            distance_from_floor: A number for the distance that the daylight sensor
                is from the floor. Typical values are around 0.8 meters.
            illuminance_setpoint: A number for the illuminance setpoint in lux
                beyond which electric lights are dimmed if there is sufficient
                daylight. (Default: 300 lux).
            control_fraction: A number between 0 and 1 that represents the fraction of
                the Room lights that are dimmed when the illuminance at the sensor
                position is at the specified illuminance. 1 indicates that all lights are
                dim-able while 0 indicates that no lights are dim-able. Deeper rooms
                should have lower control fractions to account for the face that the
                lights in the back of the space do not dim in response to suitable
                daylight at the front of the room. (Default: 1).
            min_power_input: A number between 0 and 1 for the the lowest power the
                lighting system can dim down to, expressed as a fraction of maximum
                input power. (Default: 0.3).
            min_light_output: A number between 0 and 1 the lowest lighting output the
                lighting system can dim down to, expressed as a fraction of maximum
                light output. (Default: 0.2).
            off_at_minimum: Boolean to note whether lights should switch off completely
                when they get to the minimum power input. (Default: False).
            tolerance: The maximum difference between x, y, and z values at which
                vertices are considered equivalent. (Default: 0.01, suitable for
                objects in meters).

        Returns:
            A DaylightingControl object if the sensor was successfully assigned
            to the Room. Will be None if the Room was too short or so concave
            that a sensor could not be assigned.
        """
        # first compute the Room center point and check the distance_from_floor
        if self.host.floor_to_ceiling_height < distance_from_floor:
            return None
        flr_geo = self.host.floor_geometry
        cen_pt, min_pt, max_pt = flr_geo.center, flr_geo.min, flr_geo.max
        if flr_geo.is_convex:
            sensor_pt = Point3D(cen_pt.x, cen_pt.y, min_pt.z + distance_from_floor)
        else:
            min_dim = min((max_pt.x - min_pt.x, max_pt.y - min_pt.y))
            p_tol = min_dim / 100
            sensor_pt = flr_geo.pole_of_inaccessibility(p_tol)
        # create the daylight control sensor at the point
        dl_control = DaylightingControl(
            sensor_pt, illuminance_setpoint, control_fraction,
            min_power_input, min_light_output, off_at_minimum)
        self.daylighting_control = dl_control
        return dl_control

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

    def add_fan(self, fan):
        """Add a VentilationFan to this Room.

        Args:
            fan: A VentilationFan to add to this Room.
        """
        assert isinstance(fan, VentilationFan), \
            'Expected VentilationFan object. Got {}.'.format(type(fan))
        fan.lock()   # lock because we don't duplicate the object
        self._fans.append(fan)

    def remove_fans(self):
        """Remove all VentilationFans from the Room."""
        self._fans = []

    def move(self, moving_vec):
        """Move this object along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the object.
        """
        if self.daylighting_control is not None:
            self.daylighting_control.move(moving_vec)

    def rotate(self, angle, axis, origin):
        """Rotate this object by a certain angle around an axis and origin.

        Args:
            angle: An angle for rotation in degrees.
            axis: Rotation axis as a Vector3D.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        if self.daylighting_control is not None:
            self.daylighting_control.rotate(angle, axis, origin)

    def rotate_xy(self, angle, origin):
        """Rotate this object counterclockwise in the world XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        if self.daylighting_control is not None:
            self.daylighting_control.rotate_xy(angle, origin)

    def reflect(self, plane):
        """Reflect this object across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will
                be reflected.
        """
        if self.daylighting_control is not None:
            self.daylighting_control.reflect(plane)

    def scale(self, factor, origin=None):
        """Scale this object by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        if self.daylighting_control is not None:
            self.daylighting_control.scale(factor, origin)

    def reset_to_default(self):
        """Reset all of the energy properties assigned to this Room2D to the default.

        This includes resetting the program the constructions set, and all other
        energy properties.
        """
        self._program_type = None
        self._construction_set = None
        self._hvac = None
        self._shw = None
        self._daylighting_control = None
        self._window_vent_control = None
        self._process_loads = []
        self._fans = []

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
            "window_vent_opening": {}  # A VentilationOpening dictionary
            "fans": [],  # An array of VentilationFan dictionaries
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
        if 'daylighting_control' in data and data['daylighting_control'] is not None:
            new_prop.daylighting_control = \
                DaylightingControl.from_dict(data['daylighting_control'])
        cls._deserialize_window_vent(new_prop, data, {})
        if 'fans' in data and data['fans'] is not None:
            new_prop.fans = [VentilationFan.from_dict(dat) for dat in data['fans']]
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
        if 'daylighting_control' in abridged_data and \
                abridged_data['daylighting_control'] is not None:
            self.daylighting_control = DaylightingControl.from_dict(
                abridged_data['daylighting_control'])
        self._deserialize_window_vent(self, abridged_data, schedules)
        if 'fans' in abridged_data and abridged_data['fans'] is not None:
            for dat in abridged_data['fans']:
                if dat['type'] == 'VentilationFan':
                    self._fans.append(VentilationFan.from_dict(dat))
                else:
                    self._fans.append(VentilationFan.from_dict_abridged(dat, schedules))
        if 'process_loads' in abridged_data and \
                abridged_data['process_loads'] is not None:
            for dat in abridged_data['process_loads']:
                if dat['type'] == 'Process':
                    self._process_loads.append(Process.from_dict(dat))
                else:
                    self._process_loads.append(
                        Process.from_dict_abridged(dat, schedules)
                    )

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

        # write the daylight control into the dictionary
        if self._daylighting_control is not None:
            base['energy']['daylighting_control'] = self._daylighting_control.to_dict()

        # write the window_vent_control and window_vent_opening into the dictionary
        if self._window_vent_control is not None:
            base['energy']['window_vent_control'] = \
                self.window_vent_control.to_dict(abridged)
        if self._window_vent_opening is not None:
            base['energy']['window_vent_opening'] = self.window_vent_opening.to_dict()

        # write any ventilation fans into the dictionary
        if len(self._fans) != 0:
            base['energy']['fans'] = [f.to_dict(abridged) for f in self._fans]

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
        if self._daylighting_control is not None:
            hb_prop.daylighting_control = self.daylighting_control
        if self._window_vent_control is not None:
            hb_prop.window_vent_control = self.window_vent_control
        if self._window_vent_opening is not None:
            for face in new_host.faces:  # set all apertures to be operable
                for ap in face.apertures:
                    if isinstance(ap.boundary_condition, Outdoors):
                        ap.is_operable = True
            hb_prop.assign_ventilation_opening(self.window_vent_opening)
        if len(self._fans) != 0:
            hb_prop.fans = self.fans
        if len(self._process_loads) != 0:
            hb_prop.process_loads = self.process_loads
        return hb_prop

    def from_honeybee(self, hb_properties):
        """Transfer energy attributes from a Honeybee Room to Dragonfly Room2D.

        Args:
            hb_properties: The RoomEnergyProperties of the honeybee Room that is being
                translated to a Dragonfly Room2D.
        """
        self._program_type = hb_properties._program_type
        self._construction_set = hb_properties._construction_set
        self._hvac = hb_properties._hvac
        self._shw = hb_properties._shw
        self._daylighting_control = hb_properties._daylighting_control
        if hb_properties._window_vent_control is not None:
            self._window_vent_control = hb_properties._window_vent_control
            for face in hb_properties.host.faces:
                for ap in face.apertures:
                    if ap.properties.energy.vent_opening is not None:
                        self._window_vent_opening = ap.properties.energy.vent_opening
                        break
                if self._window_vent_opening is not None:
                    break
        self._fans = hb_properties._fans[:]  # copy the list
        self._process_loads = hb_properties._process_loads[:]  # copy the list

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        Args:
            new_host: A new Room2D object that hosts these properties.
                If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        new_prop = Room2DEnergyProperties(
            _host, self._program_type, self._construction_set, self._hvac, self._shw)
        new_prop._daylighting_control = self._daylighting_control
        new_prop._window_vent_control = self._window_vent_control
        new_prop._window_vent_opening = self._window_vent_opening
        new_prop._fans = self._fans[:]  # copy fans list
        new_prop._process_loads = self._process_loads[:]  # copy process load list
        return new_prop

    @staticmethod
    def _deserialize_window_vent(new_prop, data, schedules):
        """Re-serialize window ventilation objects from a dict and apply to new_prop.

        Args:
            new_prop: A Room2DEnergyProperties to apply the window ventilation to.
            data: A dictionary representation of Room2DEnergyProperties.
        """
        if 'window_vent_control' in data and data['window_vent_control'] is not None:
            wvc = data['window_vent_control']
            new_prop.window_vent_control = \
                VentilationControl.from_dict_abridged(wvc, schedules) \
                if wvc['type'] == 'VentilationControlAbridged' else \
                VentilationControl.from_dict(wvc)
        if 'window_vent_opening' in data and data['window_vent_opening'] is not None:
            new_prop.window_vent_opening = \
                VentilationOpening.from_dict(data['window_vent_opening'])

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Room2D Energy Properties: {}'.format(self.host.identifier)
