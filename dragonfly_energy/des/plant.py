# coding=utf-8
"""Heating/Cooling plant in a district thermal system."""
from honeybee.typing import float_positive, float_in_range


class HeatingPlant(object):
    """Represents the heating plant in a district system.

    Args:
        hw_setpoint: A number for the temperature of hot water in the DES
            in degrees C. (Default: 55).
        heating_limit: A number for the nominal district heating load in
            Watts. (Default: 5000).
        hw_mass_flow: A number for the nominal heating water mass flow rate
            in kg/s. (Default: 1.0).
        hw_valve_pressure_drop: A number for the boiler isolation valve pressure
            drop in Pa. (Default: 6000).

    Properties:
        * hw_setpoint
        * heating_limit
        * hw_mass_flow
        * hw_valve_pressure_drop
    """
    __slots__ = ('_hw_setpoint', '_heating_limit', '_hw_mass_flow', '_hw_valve_pressure_drop')

    def __init__(
        self, hw_setpoint=55, heating_limit=5000, hw_mass_flow=1.0,
        hw_valve_pressure_drop=6000
    ):
        """Initialize HeatingPlant."""
        self.hw_setpoint = hw_setpoint
        self.heating_limit = heating_limit
        self.hw_mass_flow = hw_mass_flow
        self.hw_valve_pressure_drop = hw_valve_pressure_drop

    @classmethod
    def from_dict(cls, data):
        """Create a HeatingPlant object from a dictionary

        Args:
            data: A dictionary representation of an HeatingPlant object
                in the format below.

        .. code-block:: python

            {
            'type': 'HeatingPlant',
            'hw_setpoint': 55,  # float for hot water setpoint [C]
            'heating_limit': 5000  # float for system heat flow [W]
            'hw_mass_flow': 1.0,  # float for system mass flow rate [kg/s]
            'hw_valve_pressure_drop': 6000  # float for boiler pressure drop [Pa]
            }
        """
        hw_t = data['hw_setpoint'] if 'hw_setpoint' in data else 55
        heat_f = data['heating_limit'] if 'heating_limit' in data else 5000
        hw_f = data['hw_mass_flow'] if 'hw_mass_flow' in data else 1.0
        hw_p = data['hw_valve_pressure_drop'] if 'hw_valve_pressure_drop' in data else 6000
        return cls(hw_t, heat_f, hw_f, hw_p)

    @property
    def hw_setpoint(self):
        """Get or set a number for the hot water setpoint in degrees C."""
        return self._hw_setpoint

    @hw_setpoint.setter
    def hw_setpoint(self, value):
        self._hw_setpoint = \
            float_in_range(value, 24, 100, 'hot water setpoint')

    @property
    def heating_limit(self):
        """Get or set a number for the nominal system heat flow in Watts."""
        return self._heating_limit

    @heating_limit.setter
    def heating_limit(self, value):
        self._heating_limit = float_positive(value, 'heating plant heating limit')

    @property
    def hw_mass_flow(self):
        """Get or set a number for the system hot water mass flow in kg/s."""
        return self._hw_mass_flow

    @hw_mass_flow.setter
    def hw_mass_flow(self, value):
        self._hw_mass_flow = \
            float_positive(value, 'heating plant hot water mass flow')

    @property
    def hw_valve_pressure_drop(self):
        """Get or set a number for the boiler isolation valve pressure drop in Pa."""
        return self._hw_valve_pressure_drop

    @hw_valve_pressure_drop.setter
    def hw_valve_pressure_drop(self, value):
        self._hw_valve_pressure_drop = \
            float_positive(value, 'heating plant valve pressure drop')

    def to_dict(self):
        """Get HeatingPlant dictionary."""
        base = {'type': 'HeatingPlant'}
        base['hw_setpoint'] = self.hw_setpoint
        base['heating_limit'] = self.heating_limit
        base['hw_mass_flow'] = self.hw_mass_flow
        base['hw_valve_pressure_drop'] = self.hw_valve_pressure_drop
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return HeatingPlant(
            self.hw_setpoint, self.heating_limit, self.hw_mass_flow,
            self.hw_valve_pressure_drop
        )

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent HeatingPlant."""
        return 'HeatingPlant: [temperature: {}C]'.format(self.hw_setpoint)


class CoolingPlant(object):
    """Represents the cooling plant in a district system.

    Args:
        chw_setpoint: A number for the temperature of chilled water in the DES
            in degrees C. (Default: 6).
        cooling_limit: A number for the nominal district cooling load in
            Watts. (Default: 8000).
        chw_mass_flow: A number for the nominal chilled water mass flow rate
            in kg/s. (Default: 10.0).
        min_chw_mass_flow: A number for the minimum chilled water mass flow rate
            in kg/s. (Default: 10.0).
        cw_mass_flow: A number for the nominal condenser water mass flow rate
            in kg/s. (Default: 1.0).
        chw_pump_head: A number for the chilled water pump head in Pa. (Default: 300000).
        cw_pump_head: A number for the condenser water pump head in Pa. (Default: 200000).
        chw_pressure_drop: A number for the nominal chilled water (evaporator)
            side pressure drop in Pa. (Default: 55000).
        cw_pressure_drop: A number for the nominal cooling water (condenser)
            side pressure drop in Pa. (Default: 80000).
        pressure_drop_setpoint: A number for the chilled water circuit pressure
            drop setpoint in Pa. (Default: 50000).
        chw_valve_pressure_drop: A number for the chiller isolation valve
            pressure drop in Pa. (Default: 6000).
        cw_valve_pressure_drop: A number for the cooling tower isolation valve
            pressure drop in Pa. (Default: 6000).
        cooling_tower_fan_power: A number for the cooling tower fan power in
            Watts. (Default: 5000).
        cooling_tower_delta_temperature: A number for the nominal water temperature
            difference of the tower in degrees C. (Default: 7).
        approach_delta_temperature: A number for the approach temperature difference
            in degrees C. (Default: 3).
        cw_inlet_temperature: A number for the nominal cooling water inlet temperature
            in degrees C. (Default: 35).
        outdoor_wb_temperature: A number for the design air wet-bulb temperature
            in degrees C. (Default: 25).

    Properties:
        * chw_setpoint
        * cooling_limit
        * chw_mass_flow
        * min_chw_mass_flow
        * cw_mass_flow
        * chw_pump_head
        * cw_pump_head
        * chw_pressure_drop
        * cw_pressure_drop
        * pressure_drop_setpoint
        * chw_valve_pressure_drop
        * cw_valve_pressure_drop
        * cooling_tower_fan_power
        * cooling_tower_delta_temperature
        * approach_delta_temperature
        * cw_inlet_temperature
        * outdoor_wb_temperature
    """
    __slots__ = (
        '_chw_setpoint', '_cooling_limit',
        '_chw_mass_flow', '_min_chw_mass_flow', '_cw_mass_flow',
        '_chw_pump_head', '_cw_pump_head', '_chw_pressure_drop', '_cw_pressure_drop',
        '_pressure_drop_setpoint', '_chw_valve_pressure_drop', '_cw_valve_pressure_drop',
        '_cooling_tower_fan_power', '_cooling_tower_delta_temperature',
        '_approach_delta_temperature', '_cw_inlet_temperature', '_outdoor_wb_temperature'
    )

    def __init__(
        self, chw_setpoint=6, cooling_limit=8000,
        chw_mass_flow=10, min_chw_mass_flow=10, cw_mass_flow=10,
        chw_pump_head=300000, cw_pump_head=200000,
        chw_pressure_drop=55000, cw_pressure_drop=80000, pressure_drop_setpoint=50000,
        chw_valve_pressure_drop=6000, cw_valve_pressure_drop=6000,
        cooling_tower_fan_power=5000, cooling_tower_delta_temperature=7,
        approach_delta_temperature=3, cw_inlet_temperature=35, outdoor_wb_temperature=25
    ):
        """Initialize CoolingPlant."""
        self.chw_setpoint = chw_setpoint
        self.cooling_limit = cooling_limit
        self.chw_mass_flow = chw_mass_flow
        self.min_chw_mass_flow = min_chw_mass_flow
        self.cw_mass_flow = cw_mass_flow
        self.chw_pump_head = chw_pump_head
        self.cw_pump_head = cw_pump_head
        self.chw_pressure_drop = chw_pressure_drop
        self.cw_pressure_drop = cw_pressure_drop
        self.pressure_drop_setpoint = pressure_drop_setpoint
        self.chw_valve_pressure_drop = chw_valve_pressure_drop
        self.cw_valve_pressure_drop = cw_valve_pressure_drop
        self.cooling_tower_fan_power = cooling_tower_fan_power
        self.cooling_tower_delta_temperature = cooling_tower_delta_temperature
        self.approach_delta_temperature = approach_delta_temperature
        self.cw_inlet_temperature = cw_inlet_temperature
        self.outdoor_wb_temperature = outdoor_wb_temperature

    @classmethod
    def from_dict(cls, data):
        """Create a CoolingPlant object from a dictionary

        Args:
            data: A dictionary representation of an CoolingPlant object
                in the format below.

        .. code-block:: python

            {
            'type': 'CoolingPlant',
            'chw_setpoint': 55,  # float for hot water setpoint [C]
            'cooling_limit': 5000  # float for system cool flow [W]
            'chw_mass_flow': 10.0,  # float for system mass flow rate [kg/s]
            'min_chw_mass_flow': 10.0  # float for minimum mass flow rate [kg/s]
            'cw_mass_flow': 10.0  # float for condenser mass flow rate [kg/s]
            'chw_pump_head': 300000,  # float for chilled water pump head [Pa]
            'cw_pump_head': 200000,  # float for condenser water pump head [Pa]
            'chw_pressure_drop': 55000,  # float for evaporator pressure drop [Pa]
            'cw_pressure_drop': 80000,  # float for condenser pressure drop [Pa]
            'pressure_drop_setpoint': 50000,  # float for pressure drop setpoint [Pa]
            'chw_valve_pressure_drop': 6000,  # float for chilled valve pressure drop [Pa]
            'cw_valve_pressure_drop': 6000,  # float for condenser valve pressure drop [Pa]
            'cooling_tower_fan_power': 5000, # float for cooling tower fan [W]
            'cooling_tower_delta_temperature': 7, # float for tower delta T [dC]
            'approach_delta_temperature': 3, # float for approach delta T [dC]
            'cw_inlet_temperature': 35, # float for condenser water inlet T [C]
            'outdoor_wb_temperature': 25, # float for outdoor wet bulb T [C]
            }
        """
        chw_t = data['chw_setpoint'] if 'chw_setpoint' in data else 55
        cool_f = data['cooling_limit'] if 'cooling_limit' in data else 5000
        chw_f = data['chw_mass_flow'] if 'chw_mass_flow' in data else 10
        min_chw_f = data['min_chw_mass_flow'] if 'min_chw_mass_flow' in data else 10
        cw_f = data['cw_mass_flow'] if 'cw_mass_flow' in data else 10
        chw_p = data['chw_pump_head'] if 'chw_pump_head' in data else 300000
        cw_p = data['cw_pump_head'] if 'cw_pump_head' in data else 200000
        chw_pd = data['chw_pressure_drop'] if 'chw_pressure_drop' in data else 55000
        cw_pd = data['cw_pressure_drop'] if 'cw_pressure_drop' in data else 80000
        pds = data['pressure_drop_setpoint'] if 'pressure_drop_setpoint' in data else 50000
        chw_vpd = data['chw_valve_pressure_drop'] \
            if 'chw_valve_pressure_drop' in data else 6000
        cw_vpd = data['cw_valve_pressure_drop'] \
            if 'cw_valve_pressure_drop' in data else 6000
        ct_fp = data['cooling_tower_fan_power'] \
            if 'cooling_tower_fan_power' in data else 5000
        ct_dt = data['cooling_tower_delta_temperature'] \
            if 'cooling_tower_delta_temperature' in data else 7
        a_dt = data['approach_delta_temperature'] \
            if 'approach_delta_temperature' in data else 3
        cwi_t = data['cw_inlet_temperature'] if 'cw_inlet_temperature' in data else 35
        wb_t = data['outdoor_wb_temperature'] if 'outdoor_wb_temperature' in data else 25
        return cls(
            chw_t, cool_f, chw_f, min_chw_f, cw_f, chw_p, cw_p,
            chw_pd, cw_pd, pds, chw_vpd, cw_vpd, ct_fp, ct_dt, a_dt, cwi_t, wb_t
        )

    @property
    def chw_setpoint(self):
        """Get or set a number for the chilled water setpoint in degrees C."""
        return self._chw_setpoint

    @chw_setpoint.setter
    def chw_setpoint(self, value):
        self._chw_setpoint = float_in_range(value, 0, 20, 'chilled water setpoint')

    @property
    def cooling_limit(self):
        """Get or set a number for the nominal district cooling load in Watts."""
        return self._cooling_limit

    @cooling_limit.setter
    def cooling_limit(self, value):
        self._cooling_limit = float_positive(value, 'cooling plant cooling limit')

    @property
    def chw_mass_flow(self):
        """Get or set a number for the system chilled water mass flow in kg/s."""
        return self._chw_mass_flow

    @chw_mass_flow.setter
    def chw_mass_flow(self, value):
        self._chw_mass_flow = \
            float_positive(value, 'cooling plant chilled water mass flow')

    @property
    def min_chw_mass_flow(self):
        """Get or set a number for the minimum chilled water mass flow in kg/s."""
        return self._min_chw_mass_flow

    @min_chw_mass_flow.setter
    def min_chw_mass_flow(self, value):
        self._min_chw_mass_flow = \
            float_positive(value, 'cooling plant condenser water mass flow')

    @property
    def cw_mass_flow(self):
        """Get or set a number for the system condenser water mass flow in kg/s."""
        return self._cw_mass_flow

    @cw_mass_flow.setter
    def cw_mass_flow(self, value):
        self._cw_mass_flow = \
            float_positive(value, 'cooling plant condenser water mass flow')

    @property
    def chw_pump_head(self):
        """Get or set a number for the system chilled water pump head in Pa."""
        return self._chw_pump_head

    @chw_pump_head.setter
    def chw_pump_head(self, value):
        self._chw_pump_head = \
            float_positive(value, 'cooling plant chilled water pump head')

    @property
    def cw_pump_head(self):
        """Get or set a number for the system condenser water pump head in Pa."""
        return self._cw_pump_head

    @cw_pump_head.setter
    def cw_pump_head(self, value):
        self._cw_pump_head = \
            float_positive(value, 'cooling plant condenser water pump head')

    @property
    def chw_pressure_drop(self):
        """Get or set a number for the evaporator pressure drop in Pa."""
        return self._chw_pressure_drop

    @chw_pressure_drop.setter
    def chw_pressure_drop(self, value):
        self._chw_pressure_drop = \
            float_positive(value, 'cooling plant chilled water pressure drop')

    @property
    def cw_pressure_drop(self):
        """Get or set a number for the condenser pressure drop in Pa."""
        return self._cw_pressure_drop

    @cw_pressure_drop.setter
    def cw_pressure_drop(self, value):
        self._cw_pressure_drop = \
            float_positive(value, 'cooling plant condenser water pressure drop')

    @property
    def pressure_drop_setpoint(self):
        """Get or set a number for the chilled water circuit pressure drop in Pa."""
        return self._pressure_drop_setpoint

    @pressure_drop_setpoint.setter
    def pressure_drop_setpoint(self, value):
        self._pressure_drop_setpoint = \
            float_positive(value, 'cooling plant pressure drop setpoint')

    @property
    def chw_valve_pressure_drop(self):
        """Get or set a number for the chiller isolation valve pressure drop in Pa."""
        return self._chw_valve_pressure_drop

    @chw_valve_pressure_drop.setter
    def chw_valve_pressure_drop(self, value):
        self._chw_valve_pressure_drop = \
            float_positive(value, 'cooling plant chilled water valve pressure drop')

    @property
    def cw_valve_pressure_drop(self):
        """Get or set a number for the cooling tower isolation valve pressure drop in Pa.
        """
        return self._cw_valve_pressure_drop

    @cw_valve_pressure_drop.setter
    def cw_valve_pressure_drop(self, value):
        self._cw_valve_pressure_drop = \
            float_positive(value, 'cooling plant condenser water valve pressure drop')

    @property
    def cooling_tower_fan_power(self):
        """Get or set a number for the cooling tower fan power in Watts."""
        return self._cooling_tower_fan_power

    @cooling_tower_fan_power.setter
    def cooling_tower_fan_power(self, value):
        self._cooling_tower_fan_power = float_positive(value, 'cooling tower fan power')

    @property
    def cooling_tower_delta_temperature(self):
        """Get or set a number for the nominal water temperature difference in degrees C.
        """
        return self._cooling_tower_delta_temperature

    @cooling_tower_delta_temperature.setter
    def cooling_tower_delta_temperature(self, value):
        self._cooling_tower_delta_temperature = \
            float_in_range(value, 0, 20, 'cooling tower delta temperature')

    @property
    def approach_delta_temperature(self):
        """Get or set a number for the approach temperature difference in degrees C."""
        return self._approach_delta_temperature

    @approach_delta_temperature.setter
    def approach_delta_temperature(self, value):
        self._approach_delta_temperature = \
            float_in_range(value, 0, 20, 'approach delta temperature')

    @property
    def cw_inlet_temperature(self):
        """Get or set a number for the condenser water inlet temperature in degrees C.
        """
        return self._cw_inlet_temperature

    @cw_inlet_temperature.setter
    def cw_inlet_temperature(self, value):
        self._cw_inlet_temperature = \
            float_in_range(value, 0, 50, 'condenser water inlet temperature')

    @property
    def outdoor_wb_temperature(self):
        """Get or set a number for the condenser water inlet temperature in degrees C.
        """
        return self._outdoor_wb_temperature

    @outdoor_wb_temperature.setter
    def outdoor_wb_temperature(self, value):
        self._outdoor_wb_temperature = \
            float_in_range(value, 0, 50, 'outdoor wet bulb inlet temperature')

    def to_dict(self):
        """Get CoolingPlant dictionary."""
        base = {'type': 'CoolingPlant'}
        base['chw_setpoint'] = self.chw_setpoint
        base['cooling_limit'] = self.cooling_limit
        base['chw_mass_flow'] = self.chw_mass_flow
        base['min_chw_mass_flow'] = self.min_chw_mass_flow
        base['cw_mass_flow'] = self.cw_mass_flow
        base['chw_pump_head'] = self.chw_pump_head
        base['cw_pump_head'] = self.cw_pump_head
        base['chw_pressure_drop'] = self.chw_pressure_drop
        base['cw_pressure_drop'] = self.cw_pressure_drop
        base['pressure_drop_setpoint'] = self.pressure_drop_setpoint
        base['chw_valve_pressure_drop'] = self.chw_valve_pressure_drop
        base['cw_valve_pressure_drop'] = self.cw_valve_pressure_drop
        base['cooling_tower_fan_power'] = self.cooling_tower_fan_power
        base['cooling_tower_delta_temperature'] = self.cooling_tower_delta_temperature
        base['approach_delta_temperature'] = self.approach_delta_temperature
        base['cw_inlet_temperature'] = self.cw_inlet_temperature
        base['outdoor_wb_temperature'] = self.outdoor_wb_temperature
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return CoolingPlant(
            self.chw_setpoint, self.cooling_limit,
            self.chw_mass_flow, self.min_chw_mass_flow, self.cw_mass_flow,
            self.chw_pump_head, self.cw_pump_head,
            self.chw_pressure_drop, self.cw_pressure_drop, self.pressure_drop_setpoint,
            self.chw_valve_pressure_drop, self.cw_valve_pressure_drop,
            self.cooling_tower_fan_power,
            self.cooling_tower_delta_temperature, self.approach_delta_temperature,
            self.cw_inlet_temperature, self.outdoor_wb_temperature
        )

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent CoolingPlant."""
        return 'CoolingPlant: [temperature: {}C]'.format(self.chw_setpoint)
