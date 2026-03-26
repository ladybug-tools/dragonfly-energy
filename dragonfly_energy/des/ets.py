# coding=utf-8
"""Building Energy Transfer Stations (ETS) within district energy systems."""
from honeybee._lockable import lockable
from honeybee.typing import float_positive, float_in_range


@lockable
class HeatExchangerETS(object):
    """Represents a Building Energy Transfer Station (ETS) within a fourth generation DES.

    This ETS uses a fluid-to-fluid heat exchanger between the districts hot
    and chilled water loops and those of the Building.

    Args:
        cooling_supply_temp: A number for the Building's chilled water supply
            temperature in Celsius. (Default: 7C).
        heating_supply_temp: A number for the Building's hot water supply temperature
            in Celsius. This serves both space heating and service hot water
            demand. (Default: 50C).
        exchanger_efficiency: A number between 0 and 1 for the heat exchanger
            efficiency. (Default: 0.8).
        primary_pressure_drop: A number for the heat exchanger primary side
            pressure drop in pascals. (Default: 500).
        secondary_pressure_drop: A number for the heat exchanger secondary side
            pressure drop in pascals. (Default: 500).

    Properties:
        * cooling_supply_temp
        * heating_supply_temp
        * exchanger_efficiency
        * primary_pressure_drop
        * secondary_pressure_drop
    """
    __slots__ = (
        '_cooling_supply_temp', '_heating_supply_temp', '_exchanger_efficiency',
        '_primary_pressure_drop', '_secondary_pressure_drop', '_locked'
    )

    def __init__(
        self, cooling_supply_temp=7, heating_supply_temp=50, exchanger_efficiency=0.8,
        primary_pressure_drop=500, secondary_pressure_drop=500
    ):
        """Initialize HeatExchangerETS."""
        self._locked = False
        self.cooling_supply_temp = cooling_supply_temp
        self.heating_supply_temp = heating_supply_temp
        self.exchanger_efficiency = exchanger_efficiency
        self.primary_pressure_drop = primary_pressure_drop
        self.secondary_pressure_drop = secondary_pressure_drop

    @classmethod
    def from_dict(cls, data):
        """Create a HeatExchangerETS object from a dictionary

        Args:
            data: A dictionary representation of an HeatExchangerETS object
                in the format below.

        .. code-block:: python

            {
            'type': 'HeatExchangerETS',
            'cooling_supply_temp': 5,  # float for building cooling temperature in C
            'heating_supply_temp': 50,  # float for building heating temperature in C
            'exchanger_efficiency': 0.8,  # float for heat exchanger efficiency
            'primary_pressure_drop': 500,  # float for primary side pressure in Pa
            'secondary_pressure_drop': 500  # float for secondary side pressure in Pa
            }
        """
        cst = data['cooling_supply_temp'] if 'cooling_supply_temp' in data else 7
        hst = data['heating_supply_temp'] if 'heating_supply_temp' in data else 50
        eff = data['exchanger_efficiency'] if 'exchanger_efficiency' in data else 0.8
        ppd = data['primary_pressure_drop'] \
            if 'primary_pressure_drop' in data else 500
        spd = data['secondary_pressure_drop'] \
            if 'secondary_pressure_drop' in data else 500
        return cls(cst, hst, eff, ppd, spd)

    @property
    def cooling_supply_temp(self):
        """Get or set the building's chilled water supply temperature in C."""
        return self._cooling_supply_temp

    @cooling_supply_temp.setter
    def cooling_supply_temp(self, value):
        self._cooling_supply_temp = \
            float_in_range(value, 0, 20, 'cooling supply temperature')

    @property
    def heating_supply_temp(self):
        """Get or set the building's heating water supply temperature in C."""
        return self._heating_supply_temp

    @heating_supply_temp.setter
    def heating_supply_temp(self, value):
        self._heating_supply_temp = \
            float_in_range(value, 24, 100, 'heating supply temperature')

    @property
    def exchanger_efficiency(self):
        """Get or set a decimal number for the heat exchanger efficiency."""
        return self._exchanger_efficiency

    @exchanger_efficiency.setter
    def exchanger_efficiency(self, value):
        self._exchanger_efficiency = \
            float_in_range(value, 0, 1, 'heat exchanger efficiency')

    @property
    def primary_pressure_drop(self):
        """Get or set a number for the heat exchanger primary side pressure drop in Pa.
        """
        return self._primary_pressure_drop

    @primary_pressure_drop.setter
    def primary_pressure_drop(self, value):
        self._primary_pressure_drop = \
            float_positive(value, 'heat exchanger primary pressure drop')

    @property
    def secondary_pressure_drop(self):
        """Get or set a number for the heat exchanger secondary side pressure drop in Pa.
        """
        return self._secondary_pressure_drop

    @secondary_pressure_drop.setter
    def secondary_pressure_drop(self, value):
        self._secondary_pressure_drop = \
            float_positive(value, 'heat exchanger secondary pressure drop')

    def to_dict(self):
        """Get HeatExchangerETS dictionary."""
        return {
            'type': 'HeatExchangerETS',
            'cooling_supply_temp': self.cooling_supply_temp,
            'heating_supply_temp': self.heating_supply_temp,
            'exchanger_efficiency': self.exchanger_efficiency,
            'primary_pressure_drop': self.primary_pressure_drop,
            'secondary_pressure_drop': self.secondary_pressure_drop
        }

    def to_des_param_dict(self):
        """Get the HeatExchangerETS as it appears in a DES System Parameter dictionary."""
        return {
            'heat_flow_nominal': 8000,
            'heat_exchanger_efficiency': self.exchanger_efficiency,
            'nominal_mass_flow_district': 0,
            'nominal_mass_flow_building': 0,
            'valve_pressure_drop': 6000,
            'heat_exchanger_secondary_pressure_drop': self.secondary_pressure_drop,
            'heat_exchanger_primary_pressure_drop': self.primary_pressure_drop,
            'cooling_supply_water_temperature_building': self.cooling_supply_temp,
            'heating_supply_water_temperature_building': self.heating_supply_temp,
            'delta_temp_chw_building': 5,
            'delta_temp_chw_district': 8,
            'delta_temp_hw_building': 15,
            'delta_temp_hw_district': 20,
            'cooling_controller_y_max': 1,
            'cooling_controller_y_min': 0,
            'heating_controller_y_max': 1,
            'heating_controller_y_min': 0
        }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return HeatExchangerETS(
            self.cooling_supply_temp, self.heating_supply_temp, self.exchanger_efficiency,
            self.primary_pressure_drop, self.secondary_pressure_drop
        )

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent HeatExchangerETS."""
        return 'HeatExchangerETS: [cooling: {}C] [heating: {}C]'.format(
            self.cooling_supply_temp, self.heating_supply_temp)


@lockable
class HeatPumpETS(object):
    """Represents a Building Energy Transfer Station (ETS) within a fifth generation DES.

    Args:
        cooling_supply_temp: A number for the building's chilled water supply
            temperature in Celsius. (Default: 5C).
        heating_supply_temp: A number for the building's heating water supply
            temperature in Celsius. (Default: 50C).
        shw_supply_temp: A number for the building's service hot water supply
            temperature in Celsius. (Default: 50C).
        cop_cooling: A number for the coefficient of performance (COP) of the
            heat pump producing chilled water. (Default: 3.5).
        cop_heating: A number for the coefficient of performance (COP) of the
            heat pump producing hot water for space heating. (Default: 2.5).
        cop_shw: A number for the coefficient of performance (COP) of the
            heat pump producing service hot water. (Default: 2.5).
        pump_head: A number for the design head pressure of the ETS pump
            in pascals. (Default: 10000).

    Properties:
        * cooling_supply_temp
        * heating_supply_temp
        * shw_supply_temp
        * cop_cooling
        * cop_heating
        * cop_shw
        * pump_head
    """
    __slots__ = (
        '_cooling_supply_temp', '_heating_supply_temp', '_shw_supply_temp',
        '_cop_cooling', '_cop_heating', '_cop_shw', '_pump_head', '_locked'
    )

    def __init__(self, cooling_supply_temp=5, heating_supply_temp=50, shw_supply_temp=50,
                 cop_cooling=3.5, cop_heating=2.5, cop_shw=2.5, pump_head=10000):
        """Initialize HeatPumpETS."""
        self._locked = False
        self.cooling_supply_temp = cooling_supply_temp
        self.heating_supply_temp = heating_supply_temp
        self.shw_supply_temp = shw_supply_temp
        self.cop_cooling = cop_cooling
        self.cop_heating = cop_heating
        self.cop_shw = cop_shw
        self.pump_head = pump_head

    @classmethod
    def from_dict(cls, data):
        """Create a HeatPumpETS object from a dictionary

        Args:
            data: A dictionary representation of an HeatPumpETS object
                in the format below.

        .. code-block:: python

            {
            'type': 'HeatPumpETS',
            'cooling_supply_temp': 5,  # float for building cooling temperature in C
            'heating_supply_temp': 40,  # float for building heating temperature in C
            'shw_supply_temp': 50,  # float for building shw temperature in C
            'cop_cooling': 3.5,  # float for cooling COP
            'cop_heating': 3.0,  # float for heating COP
            'cop_shw': 2.5,  # float for shw COP
            'pump_head': 10000  # float for building-side pump pressure in Pa
            }
        """
        cst = data['cooling_supply_temp'] if 'cooling_supply_temp' in data else 5
        hst = data['heating_supply_temp'] if 'heating_supply_temp' in data else 50
        sst = data['shw_supply_temp'] if 'shw_supply_temp' in data else 50
        cop_cooling = data['cop_cooling'] if 'cop_cooling' in data else 3.5
        cop_heating = data['cop_heating'] if 'cop_heating' in data else 2.5
        cop_shw = data['cop_shw'] if 'cop_shw' in data else 2.5
        pump_head = data['pump_head'] if 'pump_head' in data else 10000
        return cls(cst, hst, sst, cop_cooling, cop_heating, cop_shw, pump_head)

    @property
    def cooling_supply_temp(self):
        """Get or set the building's chilled water supply temperature in C."""
        return self._cooling_supply_temp

    @cooling_supply_temp.setter
    def cooling_supply_temp(self, value):
        self._cooling_supply_temp = \
            float_in_range(value, 0, 20, 'cooling supply temperature')

    @property
    def heating_supply_temp(self):
        """Get or set the building's heating water supply temperature in C."""
        return self._heating_supply_temp

    @heating_supply_temp.setter
    def heating_supply_temp(self, value):
        self._heating_supply_temp = \
            float_in_range(value, 24, 100, 'heating supply temperature')

    @property
    def shw_supply_temp(self):
        """Get or set the building's service hot water supply temperature in C."""
        return self._shw_supply_temp

    @shw_supply_temp.setter
    def shw_supply_temp(self, value):
        self._shw_supply_temp = \
            float_in_range(value, 24, 100, 'service hot water supply temperature')

    @property
    def cop_cooling(self):
        """Get or set a number for the COP of the heat pump producing chilled water."""
        return self._cop_cooling

    @cop_cooling.setter
    def cop_cooling(self, value):
        self._cop_cooling = float_positive(value, 'cooling COP')

    @property
    def cop_heating(self):
        """Get or set a number for the COP of the heat pump producing heating water."""
        return self._cop_heating

    @cop_heating.setter
    def cop_heating(self, value):
        self._cop_heating = float_positive(value, 'heating COP')

    @property
    def cop_shw(self):
        """Get or set a number for the COP of the heat pump producing service hot water.
        """
        return self._cop_shw

    @cop_shw.setter
    def cop_shw(self, value):
        self._cop_shw = float_positive(value, 'service hot water COP')

    @property
    def pump_head(self):
        """Get or set a number for the design head pressure of the ETS pump in pascals.
        """
        return self._pump_head

    @pump_head.setter
    def pump_head(self, value):
        self._pump_head = float_positive(value, 'ETS pump head pressure')

    def to_dict(self):
        """Get HeatPumpETS dictionary."""
        return {
            'type': 'HeatPumpETS',
            'cooling_supply_temp': self.cooling_supply_temp,
            'heating_supply_temp': self.heating_supply_temp,
            'shw_supply_temp': self.shw_supply_temp,
            'cop_cooling': self.cop_cooling,
            'cop_heating': self.cop_heating,
            'cop_shw': self.cop_shw,
            'pump_head': self.pump_head
        }

    def to_des_param_dict(self):
        """Get the HeatPumpETS as it appears in a DES System Parameter dictionary."""
        return {
            'chilled_water_supply_temp': self.cooling_supply_temp,
            'heating_water_supply_temp': self.heating_supply_temp,
            'hot_water_supply_temp': self.shw_supply_temp,
            'cop_heat_pump_cooling': self.cop_cooling,
            'cop_heat_pump_heating': self.cop_heating,
            'cop_heat_pump_hot_water': self.cop_shw,
            'ets_pump_flow_rate': 0.0005,
            'ets_pump_head': self.pump_head,
            'fan_design_flow_rate': 0.25,
            'fan_design_head': 150
        }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return HeatPumpETS(
            self.cooling_supply_temp, self.heating_supply_temp, self.shw_supply_temp,
            self.cop_cooling, self.cop_heating, self.cop_shw, self.pump_head
        )

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent HeatPumpETS."""
        return 'HeatPumpETS: [cooling: {}C] [heating: {}C] [shw: {}C]'.format(
            self.cooling_supply_temp, self.heating_supply_temp, self.shw_supply_temp)
